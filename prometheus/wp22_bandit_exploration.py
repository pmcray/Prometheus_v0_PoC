"""
WP22: Multi-Armed Bandit Exploration Policy
============================================

Adds principled explore/exploit balancing to the synthesis action-selection
stack, closing the final gap left by WP17–21.

The gap in WP17–21
-------------------
WP19's ``CausalActionEvaluator`` selects the action with the highest estimated
ATE — a pure *exploitation* strategy.  WP20's rollout planner and WP21's
meta-gradient both also exploit the data already in the trajectory model.
None of them reason about *which actions are under-sampled* and therefore
whose estimates carry the highest uncertainty.

Concretely: if ``RESET_UNIFORM`` has only been tried once while
``DEMOTE_WORST`` has been tried twenty times, WP19 might keep picking
``DEMOTE_WORST`` forever, never discovering that ``RESET_UNIFORM`` is
actually far better in the current regime.  The system gets trapped in a
*local exploitation trap*.

Auer et al. (2002, UCB1) prove that no algorithm can avoid exploration
entirely without incurring linear regret.  WP22 applies their result to the
synthesis action space.

WP22 fix
---------
``BanditPolicy`` wraps the ``ActionOutcomeTable`` from WP19 and computes an
**Upper Confidence Bound** (UCB1) score for each synthesis action:

    UCB(A, t) = μ̂(A) + c · √( ln(t) / n(A) )

where:
  μ̂(A)  = estimated mean reward for action A (ATE from WP19)
  t      = total number of trials so far (all actions combined)
  n(A)   = number of trials for action A (0 → treated as 1 for the formula)
  c      = exploration coefficient (default 1.0; tune via WP21)

The action with the highest UCB score is selected.

A second policy, **ThompsonSamplingPolicy**, samples a reward from the
posterior Beta(α, β) where:
  α = 1 + positive_outcomes(A)      (successes)
  β = 1 + negative_outcomes(A)      (failures)

and selects the action with the highest sample.  This is better calibrated
for small-sample regimes.

``BanditCRLS`` inherits ``MetaGradientCRLS`` and inserts the bandit policy as
a fifth layer *above* WP21:

    Layer 5  BanditPolicy (WP22) — explores under-sampled actions
    Layer 4  MetaGradientOptimiser (WP21) — adapts hyper-parameters
    Layer 3  RolloutPlanner (WP20) — K-step lookahead
    Layer 2  CausalActionEvaluator (WP19) — ATE-based recommendation
    Layer 1  WP17 heuristic — rule-of-thumb fallback

The bandit layer fires only when the *UCB-selected action differs* from the
WP20/21 recommendation (i.e. the bandit sees an exploration opportunity).  If
they agree, the combined recommendation passes through unchanged and the bandit
incurs no cost.

Integration contract
--------------------
- ``BanditPolicy.select()`` receives the *exploitation recommendation* from the
  layer below (WP20/21) and the current ``ActionOutcomeTable`` counts, and
  returns either the exploitation action (if UCB agrees) or an exploration
  action (if UCB disagrees).
- Every chosen action is registered with ``BanditPolicy.observe()`` after the
  generation completes and ``acc_after`` is known.
- ``ExplorationRecord`` captures the full audit trail for each bandit decision.

Theoretical grounding
---------------------
Auer, Cesa-Bianchi & Fischer (2002): "Finite-time analysis of the multiarmed
bandit problem" — UCB1 achieves O(log t) regret, the theoretical minimum for
any deterministic policy.

Thompson (1933) / Chapelle & Li (2011): Thompson Sampling — Bayesian
posterior sampling achieves near-optimal regret with low computational cost
and strong empirical performance in small-data regimes.

Lattimore & Szepesvári (2020, Bandit Algorithms, §7): the exploration
coefficient c trades off regret bound tightness vs practical convergence
speed.  WP21's meta-gradient can adapt c over time.

Classes
-------
BanditPolicy            UCB1 or Thompson Sampling selector
ExplorationRecord       Audit record for one bandit decision
BanditCRLS              MetaGradientCRLS + bandit exploration layer
verify_wp22_exit_criteria   Six-criterion verifier
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from prometheus.wp17_crls_synthesis import SynthesisAction, SynthesisRecord
from prometheus.wp19_causal_evaluator import ActionOutcomeTable, CausalRecommendation
from prometheus.wp20_temporal_planner import RolloutResult, SynthesisStateSnapshot
from prometheus.wp21_meta_gradient import MetaGradStep, MetaGradientCRLS, MetaParams

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Policy mode enum
# ---------------------------------------------------------------------------

class BanditMode(Enum):
    UCB1             = "ucb1"
    THOMPSON         = "thompson"


# ---------------------------------------------------------------------------
# ExplorationRecord  —  audit trail for one bandit decision
# ---------------------------------------------------------------------------

@dataclass
class ExplorationRecord:
    """
    Audit record for a single bandit action-selection decision.

    Attributes
    ----------
    generation : int
    mode : BanditMode
    exploit_action : SynthesisAction
        Action recommended by the layer below (WP20/21).
    explore_action : SynthesisAction
        Action chosen by the bandit (may equal exploit_action).
    is_exploration : bool
        True when the bandit chose a *different* action from the exploit layer.
    ucb_scores : dict
        action.value → UCB score (or Thompson sample) at decision time.
    n_trials : dict
        action.value → n_trials at decision time.
    total_t : int
        Total trials across all actions at decision time.
    reward : float or None
        Observed accuracy improvement (filled in after generation completes).
    timestamp : float
    """
    generation:     int
    mode:           BanditMode
    exploit_action: SynthesisAction
    explore_action: SynthesisAction
    is_exploration: bool
    ucb_scores:     Dict[str, float]
    n_trials:       Dict[str, int]
    total_t:        int
    reward:         Optional[float] = None
    timestamp:      float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation":     self.generation,
            "mode":           self.mode.value,
            "exploit_action": self.exploit_action.value,
            "explore_action": self.explore_action.value,
            "is_exploration": self.is_exploration,
            "ucb_scores":     self.ucb_scores,
            "n_trials":       self.n_trials,
            "total_t":        self.total_t,
            "reward":         self.reward,
        }


# ---------------------------------------------------------------------------
# BanditPolicy
# ---------------------------------------------------------------------------

class BanditPolicy:
    """
    Multi-armed bandit policy over synthesis actions.

    Supports two modes:

    UCB1 (Auer et al. 2002)
    -----------------------
    Score(A) = μ̂(A) + c · √( ln(t) / max(1, n(A)) )

    where μ̂(A) is the mean observed reward for action A (accuracy improvement
    = acc_after − acc_before), t is the total number of observations across all
    actions, and n(A) is the number of observations for A.

    Thompson Sampling (Thompson 1933; Chapelle & Li 2011)
    ------------------------------------------------------
    Model each action's reward as a Gaussian with unknown mean.
    Approximate posterior: N(μ̂(A), σ²(A) / n(A))  where σ²(A) is the
    sample variance (defaulting to a prior_variance when n(A) = 0).
    Draw a sample from each action's posterior and pick the argmax.

    In both modes, actions with *zero* observations are always tried before
    repeated actions (forced exploration for untried arms).

    Parameters
    ----------
    mode : BanditMode
        UCB1 or THOMPSON (default UCB1).
    exploration_coeff : float
        UCB1 exploration coefficient c (default 1.0).
    prior_variance : float
        Thompson prior variance for unseen actions (default 1.0).
    force_explore_unseen : bool
        If True, always try every action at least once before using UCB/Thompson
        (default True).
    """

    def __init__(
        self,
        mode:                 BanditMode = BanditMode.UCB1,
        exploration_coeff:    float = 1.0,
        prior_variance:       float = 1.0,
        force_explore_unseen: bool  = True,
    ):
        self.mode                 = mode
        self.c                    = exploration_coeff
        self.prior_var            = prior_variance
        self.force_explore_unseen = force_explore_unseen

        # action → list of observed rewards (accuracy improvements)
        self._rewards: Dict[SynthesisAction, List[float]] = {
            a: [] for a in SynthesisAction
        }
        self.exploration_log: List[ExplorationRecord] = []

    # ------------------------------------------------------------------
    # Statistics helpers
    # ------------------------------------------------------------------

    def n_trials(self, action: SynthesisAction) -> int:
        return len(self._rewards[action])

    def total_trials(self) -> int:
        return sum(len(v) for v in self._rewards.values())

    def mean_reward(self, action: SynthesisAction) -> float:
        r = self._rewards[action]
        return sum(r) / len(r) if r else 0.0

    def reward_variance(self, action: SynthesisAction) -> float:
        r = self._rewards[action]
        if len(r) < 2:
            return self.prior_var
        mu = sum(r) / len(r)
        return sum((x - mu) ** 2 for x in r) / (len(r) - 1)

    # ------------------------------------------------------------------
    # Score computation
    # ------------------------------------------------------------------

    def _ucb_score(self, action: SynthesisAction, total_t: int) -> float:
        n = self.n_trials(action)
        mu = self.mean_reward(action)
        if n == 0:
            return float("inf")   # unseen arm always has infinite UCB
        return mu + self.c * math.sqrt(math.log(max(1, total_t)) / n)

    def _thompson_sample(self, action: SynthesisAction) -> float:
        n  = self.n_trials(action)
        mu = self.mean_reward(action)
        var = self.reward_variance(action)
        # Sample from N(mu, var/max(1, n))
        std = math.sqrt(var / max(1, n))
        return random.gauss(mu, std)

    def scores(
        self,
        candidates: Optional[List[SynthesisAction]] = None,
    ) -> Dict[SynthesisAction, float]:
        """Return score for each candidate action under the current mode."""
        if candidates is None:
            candidates = list(SynthesisAction)
        t = self.total_trials()
        if self.mode == BanditMode.UCB1:
            return {a: self._ucb_score(a, t) for a in candidates}
        else:  # THOMPSON
            return {a: self._thompson_sample(a) for a in candidates}

    # ------------------------------------------------------------------
    # Action selection
    # ------------------------------------------------------------------

    def select(
        self,
        exploit_action: SynthesisAction,
        generation:     int,
        candidates:     Optional[List[SynthesisAction]] = None,
    ) -> ExplorationRecord:
        """
        Choose an action balancing exploration and exploitation.

        Parameters
        ----------
        exploit_action : SynthesisAction
            The action recommended by the layer below (WP20/21).
        generation : int
        candidates : list, optional
            Actions to consider (default: all SynthesisActions).

        Returns
        -------
        ExplorationRecord
            Contains the chosen action (explore_action) and full audit info.
        """
        if candidates is None:
            candidates = list(SynthesisAction)

        t = self.total_trials()

        # --- Forced exploration: try every arm at least once first ---
        if self.force_explore_unseen:
            unseen = [a for a in candidates if self.n_trials(a) == 0]
            if unseen:
                # Pick the first unseen action (deterministic for reproducibility)
                chosen = unseen[0]
                score_dict = {a: (float("inf") if a == chosen else 0.0)
                              for a in candidates}
                rec = ExplorationRecord(
                    generation     = generation,
                    mode           = self.mode,
                    exploit_action = exploit_action,
                    explore_action = chosen,
                    is_exploration = (chosen != exploit_action),
                    ucb_scores     = {a.value: score_dict[a] for a in candidates},
                    n_trials       = {a.value: self.n_trials(a) for a in candidates},
                    total_t        = t,
                )
                self.exploration_log.append(rec)
                return rec

        # --- Main UCB / Thompson selection ---
        score_dict = self.scores(candidates)
        chosen = max(candidates, key=lambda a: score_dict[a])

        rec = ExplorationRecord(
            generation     = generation,
            mode           = self.mode,
            exploit_action = exploit_action,
            explore_action = chosen,
            is_exploration = (chosen != exploit_action),
            ucb_scores     = {a.value: score_dict[a] for a in candidates},
            n_trials       = {a.value: self.n_trials(a) for a in candidates},
            total_t        = t,
        )
        self.exploration_log.append(rec)
        logger.info(
            "BanditPolicy gen %d [%s]: exploit=%s → explore=%s%s (t=%d)",
            generation, self.mode.value,
            exploit_action.value, chosen.value,
            " [EXPLORATION]" if rec.is_exploration else "",
            t,
        )
        return rec

    # ------------------------------------------------------------------
    # Reward observation
    # ------------------------------------------------------------------

    def observe(self, action: SynthesisAction, reward: float) -> None:
        """
        Register an observed reward after a synthesis action completes.

        Parameters
        ----------
        action : SynthesisAction
        reward : float
            Observed accuracy improvement (acc_after − acc_before).
        """
        self._rewards[action].append(reward)
        # Back-fill reward onto the most recent ExplorationRecord for this action
        for rec in reversed(self.exploration_log):
            if rec.explore_action == action and rec.reward is None:
                rec.reward = reward
                break
        logger.debug(
            "BanditPolicy.observe: %s reward=%.4f (n=%d mean=%.4f)",
            action.value, reward,
            self.n_trials(action), self.mean_reward(action),
        )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_summary(self) -> Dict[str, Any]:
        t          = self.total_trials()
        explorations = [r for r in self.exploration_log if r.is_exploration]
        return {
            "mode":               self.mode.value,
            "exploration_coeff":  self.c,
            "total_t":            t,
            "exploration_count":  len(explorations),
            "exploitation_count": len(self.exploration_log) - len(explorations),
            "exploration_rate":   (len(explorations) / len(self.exploration_log)
                                   if self.exploration_log else 0.0),
            "mean_reward_per_action": {
                a.value: self.mean_reward(a)
                for a in SynthesisAction
                if self.n_trials(a) > 0
            },
            "n_trials_per_action": {
                a.value: self.n_trials(a) for a in SynthesisAction
            },
            "exploration_log": [r.to_dict() for r in self.exploration_log],
        }


# ---------------------------------------------------------------------------
# BanditCRLS — MetaGradientCRLS + bandit exploration layer
# ---------------------------------------------------------------------------

class BanditCRLS(MetaGradientCRLS):
    """
    WP22 upgrade of MetaGradientCRLS: adds multi-armed bandit exploration.

    Five-layer action-selection hierarchy
    --------------------------------------
    5. **BanditPolicy** (WP22) — explores under-sampled synthesis actions
    4. **MetaGradientOptimiser** (WP21) — adapts synthesis hyperparameters
    3. **RolloutPlanner** (WP20) — K-step lookahead action
    2. **CausalActionEvaluator** (WP19) — ATE-based recommendation
    1. **WP17 heuristic** — rule-of-thumb fallback

    When the bandit selects a *different* action from WP20/21, that exploration
    action is used instead, and the bandit records the subsequent accuracy
    change as the observed reward.

    Parameters
    ----------
    strategies : list[str]
    upward_rate, downward_rate : float
    synthesiser_kwargs : dict
    min_trials_to_override : int
    override_tolerance : float
    rollout_horizon : int
    rollout_discount : float
    min_transitions : int
    meta_step_size : float
    meta_fd_epsilon : float
    meta_min_transitions : int
    initial_params : MetaParams, optional
    bandit_mode : BanditMode
        UCB1 or THOMPSON (default UCB1).
    exploration_coeff : float
        UCB1 exploration coefficient c (default 1.0).
    prior_variance : float
        Thompson prior variance for unseen actions (default 1.0).
    force_explore_unseen : bool
        Always try every action at least once (default True).
    """

    def __init__(
        self,
        strategies:             List[str],
        upward_rate:            float = 0.20,
        downward_rate:          float = 0.15,
        synthesiser_kwargs:     Optional[Dict[str, Any]] = None,
        min_trials_to_override: int   = 3,
        override_tolerance:     float = 0.02,
        rollout_horizon:        int   = 3,
        rollout_discount:       float = 0.90,
        min_transitions:        int   = 3,
        meta_step_size:         float = 0.02,
        meta_fd_epsilon:        float = 0.05,
        meta_min_transitions:   int   = 4,
        initial_params:         Optional[MetaParams] = None,
        bandit_mode:            BanditMode = BanditMode.UCB1,
        exploration_coeff:      float = 1.0,
        prior_variance:         float = 1.0,
        force_explore_unseen:   bool  = True,
    ):
        super().__init__(
            strategies             = strategies,
            upward_rate            = upward_rate,
            downward_rate          = downward_rate,
            synthesiser_kwargs     = synthesiser_kwargs,
            min_trials_to_override = min_trials_to_override,
            override_tolerance     = override_tolerance,
            rollout_horizon        = rollout_horizon,
            rollout_discount       = rollout_discount,
            min_transitions        = min_transitions,
            meta_step_size         = meta_step_size,
            meta_fd_epsilon        = meta_fd_epsilon,
            meta_min_transitions   = meta_min_transitions,
            initial_params         = initial_params,
        )

        # WP22 addition
        self.bandit = BanditPolicy(
            mode                 = bandit_mode,
            exploration_coeff    = exploration_coeff,
            prior_variance       = prior_variance,
            force_explore_unseen = force_explore_unseen,
        )
        self.bandit_log: List[Dict[str, Any]] = []
        # Track the pending exploration record so we can fill in the reward
        self._pending_exploration: Optional[ExplorationRecord] = None

    # ------------------------------------------------------------------
    # Override end_of_generation to add bandit layer
    # ------------------------------------------------------------------

    def end_of_generation(
        self,
        regime: str = "",
    ) -> Tuple[SynthesisRecord, CausalRecommendation, RolloutResult,
               MetaGradStep, ExplorationRecord]:
        """
        Run synthesis with all five layers: WP17 → WP19 → WP20 → WP21 → WP22.

        Returns
        -------
        (SynthesisRecord, CausalRecommendation, RolloutResult,
         MetaGradStep, ExplorationRecord)
        """
        # --- Layers 1-4: inherit WP21 logic, but capture the WP20 rollout
        #     recommendation *before* we may override it with the bandit ---
        acc_now  = self.acc_history[-1]
        acc_prev = self.acc_history[-2] if len(self.acc_history) >= 2 else None

        # Layer 1: WP17 heuristic
        heuristic_action, heuristic_trigger = self.synth._choose_action(
            acc_now, acc_prev, self.metacog.get_pattern_summary()
        )

        # Layer 2: WP19 causal
        causal_rec = self.evaluator.recommend(heuristic_action, heuristic_trigger)

        # Layer 3: WP20 rollout
        current_snapshot = SynthesisStateSnapshot.from_meta_and_acc(
            self.generation, self.meta, acc_now
        )
        rollout = self.planner.plan(
            current_state    = current_snapshot,
            heuristic_action = causal_rec.action,
        )

        # Layer 4: WP21 meta-gradient — update MetaParams
        self.meta_params, grad_step = self.meta_opt.step(
            state       = current_snapshot,
            best_action = rollout.best_action,
            params      = self.meta_params,
            generation  = self.generation,
        )
        self._apply_meta_params()

        # Layer 5: WP22 bandit — explore or exploit
        exploit_action = rollout.best_action   # WP20/21 recommendation
        bandit_rec = self.bandit.select(
            exploit_action = exploit_action,
            generation     = self.generation,
        )
        final_action = bandit_rec.explore_action

        # Build trigger string for the synthesis record
        if bandit_rec.is_exploration:
            chosen_trigger = (
                f"[bandit {self.bandit.mode.value} EXPLORE] "
                f"exploit={exploit_action.value} → explore={final_action.value}; "
                f"n_trials={bandit_rec.n_trials.get(final_action.value, 0)}; "
                f"ucb={bandit_rec.ucb_scores.get(final_action.value, 0):.4f}"
            )
        else:
            rollout_trigger = (
                f"[rollout K={rollout.horizon}] "
                f"best={rollout.best_action.value} "
                f"return={rollout.expected_return:+.4f}; "
                f"causal_fallback={causal_rec.trigger}"
            ) if not rollout.fallback_used else causal_rec.trigger
            chosen_trigger = (
                f"[bandit {self.bandit.mode.value} EXPLOIT] "
                f"{rollout_trigger}"
            )

        # Apply the (possibly bandit-overridden) action through safety gate
        record = self._synthesise_with_action(
            final_action, chosen_trigger, acc_now, acc_prev
        )

        # Store pending exploration so we can fill reward after next gen
        self._pending_exploration = bandit_rec

        # Log everything
        self._log_pending_transition_record(record)
        self.meta_grad_log.append(grad_step.to_dict())
        self.bandit_log.append(bandit_rec.to_dict())

        self.gen_log.append({
            "generation":        self.generation,
            "regime":            regime,
            "acc":               acc_now,
            "heuristic":         heuristic_action.value,
            "causal_action":     causal_rec.action.value,
            "rollout_action":    rollout.best_action.value,
            "rollout_fallback":  rollout.fallback_used,
            "override":          causal_rec.override,
            "ate":               causal_rec.ate_estimate.ate if causal_rec.ate_estimate else None,
            "expected_return":   rollout.expected_return,
            "bandit_action":     final_action.value,
            "bandit_explore":    bandit_rec.is_exploration,
            "safety":            record.safety_status,
        })
        self.rollout_log.append(rollout.to_dict())

        self.generation += 1
        return record, causal_rec, rollout, grad_step, bandit_rec

    def _log_pending_transition_record(self, record: SynthesisRecord) -> None:
        """Store record for trajectory model ingestion next generation."""
        self._pending_transition_record = record

    # ------------------------------------------------------------------
    # Override run_generation to complete bandit reward and trajectory
    # ------------------------------------------------------------------

    def run_generation(
        self,
        puzzles:     List[Tuple],
        tactic_fns:  Dict[str, Any],
        evaluate_fn: Callable,
    ) -> float:
        """Play all puzzles; complete pending bandit reward and WP20 transition."""
        # Complete the pending trajectory transition from last end_of_generation
        if (hasattr(self, "_pending_transition_record")
                and self._pending_transition_record is not None):
            pending = self._pending_transition_record
            self._pending_transition_record = None
            if self.acc_history:
                next_acc = self._eval_batch(
                    puzzles, tactic_fns, evaluate_fn, update=False
                )
                pending.acc_after  = next_acc
                pending.improvement = next_acc - pending.acc_before

                # Feed WP20 trajectory model
                self.traj_model.ingest_record_pair(pending)
                # Feed WP19 evaluator
                self.evaluator.update(pending)

                # Feed WP22 bandit reward
                if (self._pending_exploration is not None
                        and pending.improvement is not None):
                    self.bandit.observe(
                        pending.action, pending.improvement
                    )
                    self._pending_exploration = None

        acc = self._run_puzzles(puzzles, tactic_fns, evaluate_fn)
        self.acc_history.append(acc)
        return acc

    def _run_puzzles(
        self,
        puzzles:     List[Tuple],
        tactic_fns:  Dict[str, Any],
        evaluate_fn: Callable,
    ) -> float:
        """Run all puzzles with MetaLearner updates."""
        from prometheus.v0_114_crls_strange_loop import FailureEpisode, FailureType
        correct = 0
        for i, (board, player, correct_move) in enumerate(puzzles):
            strategy = self.meta.select_strategy()
            move     = tactic_fns[strategy](board, player)
            if move is None or not board.is_legal_move(move[0], move[1], player):
                legal    = board.get_legal_moves(player)
                move     = legal[0] if legal else (-1, -1)
                strategy = list(tactic_fns.keys())[-1]

            success = evaluate_fn(board, move, correct_move, player)
            if success:
                self.meta.update_on_success(strategy)
                correct += 1
            else:
                self.meta.update_on_failure(strategy)
                self.metacog.observe_failure(FailureEpisode(
                    turn             = i,
                    failure_type     = FailureType.STRATEGIC_ERROR,
                    context          = {"strategy": strategy},
                    action_taken     = strategy,
                    expected_outcome = 1.0,
                    actual_outcome   = 0.0,
                    causal_diagnosis = f"strategy '{strategy}' failed",
                ))
        return correct / len(puzzles)

    # ------------------------------------------------------------------
    # Extended report
    # ------------------------------------------------------------------

    def get_full_report(self) -> Dict[str, Any]:
        report = super().get_full_report()
        report["bandit_summary"] = self.bandit.get_summary()
        report["bandit_log"]     = self.bandit_log
        return report


# ---------------------------------------------------------------------------
# Exit-criteria verifier
# ---------------------------------------------------------------------------

def verify_wp22_exit_criteria(crls: BanditCRLS) -> Dict[str, bool]:
    """
    Verify WP22 exit criteria.

    Criteria
    --------
    bandit_constructed          BanditPolicy exists with valid mode
    all_actions_explored        Every SynthesisAction tried at least once
    exploration_occurred        At least one bandit decision was an exploration
    rewards_observed            At least one reward has been fed back
    exploitation_occurs         At least one decision was exploitation (not forced)
    safety_preserved            All proposals safety-gated; no UNSAFE action applied

    Returns
    -------
    dict mapping criterion name → bool
    """
    report  = crls.get_full_report()
    bsumm   = report["bandit_summary"]
    safety  = report["safety_statistics"]
    glog    = report["generation_log"]

    # --- bandit_constructed ---
    bandit_ok = isinstance(crls.bandit, BanditPolicy)

    # --- all_actions_explored ---
    all_explored = all(
        bsumm["n_trials_per_action"].get(a.value, 0) > 0
        for a in SynthesisAction
    )

    # --- exploration_occurred ---
    exploration_occurred = bsumm["exploration_count"] > 0

    # --- rewards_observed ---
    rewards_observed = bsumm["total_t"] > 0 and any(
        bsumm["n_trials_per_action"].get(a.value, 0) > 0
        for a in SynthesisAction
    )

    # --- exploitation_occurs ---
    exploitation_occurs = bsumm["exploitation_count"] > 0

    # --- safety_preserved ---
    safety_preserved = (
        safety["total_decisions"] > 0
        and safety.get("unsafe_decisions", 0) == 0
    )

    criteria = {
        "bandit_constructed":   bandit_ok,
        "all_actions_explored": all_explored,
        "exploration_occurred": exploration_occurred,
        "rewards_observed":     rewards_observed,
        "exploitation_occurs":  exploitation_occurs,
        "safety_preserved":     safety_preserved,
    }

    logger.info("WP22 exit criteria: %s", criteria)
    return criteria
