"""
WP20: Temporal Synthesis Planner
==================================

Adds K-step lookahead to the CRLS synthesis loop, closing the final
Hofstadterian beat: the loop now *plans into the future* rather than merely
reacting to the past.

The gap in WP17–19
------------------
WP17 chooses a synthesis action heuristically (threshold on accuracy drop).
WP19 improves that choice by observational ATE from past records — what
*has* worked. But neither can answer:

  "If I apply DEMOTE_WORST now and BOOST_UPWARD in two generations, what
   does accuracy look like at generation G+3?"

The ATE from WP19 is a *single-step* effect.  The trajectory dynamics
(how one action changes the probability distribution that then feeds into
the next generation's puzzles) are completely ignored.

WP20 fix
--------
``SynthesisTrajectoryModel`` learns the transition function

    f(state_t, action) → state_{t+1}

from the accumulated SynthesisRecord history (the same data WP19 uses).
Each record provides a (before_state, action, after_state) triple.  The
model uses a velocity-extrapolation approach inspired by v0.120's TGN:

    predicted_acc_{t+1} ≈ acc_t + ATE(action) + baseline_drift

but then propagates the *probability distribution* forward using the
observed probability deltas per action, so that the K-step rollout
simulates realistic distribution evolution — not just accuracy.

``RolloutPlanner`` searches the action space K steps ahead:
  - For each candidate action A at step 0, simulate the trajectory
    under A followed by the greedy best action at each subsequent step.
  - Score each A by its discounted cumulative accuracy gain:
      G(A) = Σ_{k=1}^{K}  γ^k * (predicted_acc_{t+k} − baseline_acc_{t+k})
  - Return the A with the highest G(A).

``TemporalCRLS`` inherits CausalCRLS and overrides end_of_generation:
  1. Ask RolloutPlanner for a K-step plan.
  2. If the planner has insufficient data, fall back to WP19's ATE recommend.
  3. Log whether the rollout or the fallback was used.

Theoretical grounding
---------------------
Sutton & Barto (2018, RL §8): Dyna architecture — "plan, act, learn" —
where a learned world model is used to generate simulated experience that
improves the policy.  WP20 implements this for the meta-policy (synthesis
action selection) rather than the object-level policy (tactic selection).

Bellman (1957): The principle of optimality — an optimal K-step policy
has the property that, whatever the first action taken, the remaining
steps also constitute an optimal policy.  The ``RolloutPlanner`` approximates
this via greedy rollout, which is near-optimal for short horizons K ≤ 5.

Classes
-------
SynthesisStateSnapshot      Lean state vector: probs + upward_rate + accuracy
TrajectoryTransition        One (state, action, next_state) training triple
SynthesisTrajectoryModel    Learns and predicts state transitions per action
RolloutResult               Output of RolloutPlanner: best action + trajectory
RolloutPlanner              K-step lookahead over the action space
TemporalCRLS                CausalCRLS + rollout planning
verify_wp20_exit_criteria   Six-criterion verifier
"""

from __future__ import annotations

import logging
import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from prometheus.meta_learner import MetaLearner
from prometheus.safety.checks import GodelianSafetyGovernor, SafetyStatus
from prometheus.v0_114_crls_strange_loop import (
    FailureEpisode,
    FailureType,
    MetaCognitionLayer,
)
from prometheus.wp17_crls_synthesis import (
    CRLSSynthesiser,
    SynthesisAction,
    SynthesisRecord,
)
from prometheus.wp19_causal_evaluator import (
    CausalActionEvaluator,
    CausalCRLS,
    CausalRecommendation,
)

logger = logging.getLogger(__name__)

# Minimum transitions per action before the trajectory model is trusted
_MIN_TRANSITIONS = 3


# ---------------------------------------------------------------------------
# State representation
# ---------------------------------------------------------------------------

@dataclass
class SynthesisStateSnapshot:
    """
    Lean state vector for the synthesis trajectory model.

    Captures everything the trajectory model needs to predict
    the next state: current strategy probabilities, upward_rate, and
    the accuracy just achieved.

    Parameters
    ----------
    generation : int
    probs : dict  strategy → probability
    upward_rate : float
    accuracy : float   accuracy at this generation
    """
    generation:  int
    probs:       Dict[str, float]
    upward_rate: float
    accuracy:    float

    @classmethod
    def from_meta_and_acc(
        cls,
        generation:  int,
        meta:        MetaLearner,
        accuracy:    float,
    ) -> "SynthesisStateSnapshot":
        return cls(
            generation  = generation,
            probs       = meta.get_strategy_probabilities(),
            upward_rate = meta.upward_rate,
            accuracy    = accuracy,
        )

    def as_vector(self) -> List[float]:
        """Flat feature vector: sorted probs + upward_rate + accuracy."""
        return [v for _, v in sorted(self.probs.items())] + [self.upward_rate, self.accuracy]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation":  self.generation,
            "probs":       self.probs,
            "upward_rate": self.upward_rate,
            "accuracy":    self.accuracy,
        }


@dataclass
class TrajectoryTransition:
    """
    One (state_before, action, state_after) training triple extracted
    from a completed SynthesisRecord.
    """
    state_before: SynthesisStateSnapshot
    action:       SynthesisAction
    state_after:  SynthesisStateSnapshot

    @property
    def acc_delta(self) -> float:
        return self.state_after.accuracy - self.state_before.accuracy

    @property
    def prob_deltas(self) -> Dict[str, float]:
        """Per-strategy probability change."""
        before = self.state_before.probs
        after  = self.state_after.probs
        return {s: after.get(s, 0.0) - before.get(s, 0.0) for s in before}


# ---------------------------------------------------------------------------
# SynthesisTrajectoryModel
# ---------------------------------------------------------------------------

class SynthesisTrajectoryModel:
    """
    Learns the transition function  f(state_t, action) → state_{t+1}
    from accumulated TrajectoryTransition history.

    Prediction mechanism (v0.120-inspired velocity extrapolation)
    -------------------------------------------------------------
    For action A with n_A observed transitions:

      mean_acc_delta(A)   = mean of [t.acc_delta  for t in transitions(A)]
      mean_prob_delta(A)  = mean of [t.prob_deltas for t in transitions(A)]
                            (per strategy)

    Given current state s_t, predicted next state under A:

      predicted_acc  = s_t.accuracy + mean_acc_delta(A)
      predicted_prob = normalise(s_t.probs + mean_prob_delta(A))
                       clipped to [min_prob, max_prob]

    For multi-step prediction beyond 1 step, we compose the single-step
    model: the predicted state at step k+1 uses the predicted state at k.
    Confidence degrades as  conf_k = conf_1 * decay^(k-1)  (default decay=0.85).

    Parameters
    ----------
    min_transitions : int
        Minimum transitions per action before we trust predictions.
    confidence_decay : float
        Per-step confidence multiplier for multi-step predictions.
    min_prob : float
        Probability floor after delta application.
    """

    def __init__(
        self,
        min_transitions:  int   = _MIN_TRANSITIONS,
        confidence_decay: float = 0.85,
        min_prob:         float = 0.02,
    ):
        self.min_transitions  = min_transitions
        self.confidence_decay = confidence_decay
        self.min_prob         = min_prob

        # action → list[TrajectoryTransition]
        self._transitions: Dict[SynthesisAction, List[TrajectoryTransition]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def ingest(self, transition: TrajectoryTransition) -> None:
        """Add one transition to the model."""
        self._transitions[transition.action].append(transition)
        logger.debug(
            "TrajectoryModel: ingested %s (n=%d acc_delta=%+.3f)",
            transition.action.value,
            len(self._transitions[transition.action]),
            transition.acc_delta,
        )

    def ingest_record_pair(
        self,
        record:       SynthesisRecord,
        meta_before:  Optional[MetaLearner] = None,
    ) -> Optional[TrajectoryTransition]:
        """
        Build a TrajectoryTransition from a completed SynthesisRecord.

        ``record.before_probs`` / ``record.after_probs`` provide the
        probability snapshots; ``record.acc_before`` / ``record.acc_after``
        provide the accuracy.  Returns None if acc_after is not yet known.
        """
        if record.acc_after is None:
            return None

        state_before = SynthesisStateSnapshot(
            generation  = record.generation,
            probs       = dict(record.before_probs),
            upward_rate = record.before_upward,
            accuracy    = record.acc_before,
        )
        state_after = SynthesisStateSnapshot(
            generation  = record.generation + 1,
            probs       = dict(record.after_probs),
            upward_rate = record.after_upward,
            accuracy    = record.acc_after,
        )
        t = TrajectoryTransition(state_before, record.action, state_after)
        self.ingest(t)
        return t

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def can_predict(self, action: SynthesisAction) -> bool:
        return len(self._transitions[action]) >= self.min_transitions

    def mean_acc_delta(self, action: SynthesisAction) -> float:
        ts = self._transitions[action]
        if not ts:
            return 0.0
        return sum(t.acc_delta for t in ts) / len(ts)

    def mean_prob_deltas(self, action: SynthesisAction) -> Dict[str, float]:
        ts = self._transitions[action]
        if not ts:
            return {}
        strategies = list(ts[0].state_before.probs.keys())
        return {
            s: sum(t.prob_deltas.get(s, 0.0) for t in ts) / len(ts)
            for s in strategies
        }

    def predict_one_step(
        self,
        state:      SynthesisStateSnapshot,
        action:     SynthesisAction,
        generation: int,
    ) -> Tuple[SynthesisStateSnapshot, float]:
        """
        Predict state at generation+1 given action at current state.

        Returns
        -------
        (predicted_state, confidence)
        """
        n = len(self._transitions[action])
        if n == 0:
            # No data — return unchanged state with zero confidence
            return (
                SynthesisStateSnapshot(generation + 1, state.probs.copy(),
                                       state.upward_rate, state.accuracy),
                0.0,
            )

        # Accuracy delta
        predicted_acc = state.accuracy + self.mean_acc_delta(action)
        predicted_acc = max(0.0, min(1.0, predicted_acc))

        # Probability deltas
        mean_deltas = self.mean_prob_deltas(action)
        new_probs = {
            s: max(self.min_prob, state.probs.get(s, 0.0) + mean_deltas.get(s, 0.0))
            for s in state.probs
        }
        # Normalise
        total = sum(new_probs.values())
        if total > 0:
            new_probs = {s: p / total for s, p in new_probs.items()}

        # Upward rate (BOOST_UPWARD changes it)
        if action == SynthesisAction.BOOST_UPWARD:
            ts = self._transitions[action]
            mean_upward_after = sum(t.state_after.upward_rate for t in ts) / len(ts)
            new_upward = mean_upward_after
        else:
            new_upward = state.upward_rate

        # Confidence: saturates asymptotically as n grows
        confidence = 1.0 - 1.0 / (1.0 + n)

        predicted_state = SynthesisStateSnapshot(
            generation  = generation + 1,
            probs       = new_probs,
            upward_rate = new_upward,
            accuracy    = predicted_acc,
        )
        return predicted_state, confidence

    def predict_k_steps(
        self,
        initial_state: SynthesisStateSnapshot,
        action_sequence: List[SynthesisAction],
    ) -> List[Tuple[SynthesisStateSnapshot, float]]:
        """
        Roll out a sequence of actions from ``initial_state``.

        Returns a list of (predicted_state, confidence) at each step.
        Confidence decays multiplicatively each step.
        """
        trajectory: List[Tuple[SynthesisStateSnapshot, float]] = []
        state = initial_state
        cumulative_conf = 1.0

        for k, action in enumerate(action_sequence):
            next_state, step_conf = self.predict_one_step(
                state, action, state.generation
            )
            cumulative_conf *= step_conf * (self.confidence_decay ** k)
            trajectory.append((next_state, cumulative_conf))
            state = next_state

        return trajectory

    def n_transitions(self, action: SynthesisAction) -> int:
        return len(self._transitions[action])

    def get_summary(self) -> Dict[str, Any]:
        return {
            "transitions_per_action": {
                a.value: self.n_transitions(a) for a in SynthesisAction
            },
            "mean_acc_delta_per_action": {
                a.value: self.mean_acc_delta(a) for a in SynthesisAction
                if self.n_transitions(a) > 0
            },
            "can_predict": {
                a.value: self.can_predict(a) for a in SynthesisAction
            },
        }


# ---------------------------------------------------------------------------
# RolloutPlanner
# ---------------------------------------------------------------------------

@dataclass
class RolloutResult:
    """
    Output of RolloutPlanner.plan().

    Attributes
    ----------
    best_action : SynthesisAction
        The action recommended by K-step lookahead.
    expected_return : float
        Discounted cumulative accuracy gain under best_action.
    trajectory : list[(SynthesisStateSnapshot, confidence)]
        Simulated future states under best_action.
    horizon : int
        Number of steps in the rollout.
    fallback_used : bool
        True if trajectory model had insufficient data and we fell back
        to a simpler heuristic.
    action_returns : dict
        action.value → expected_return for all evaluated actions.
    """
    best_action:     SynthesisAction
    expected_return: float
    trajectory:      List[Tuple[SynthesisStateSnapshot, float]]
    horizon:         int
    fallback_used:   bool
    action_returns:  Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "best_action":     self.best_action.value,
            "expected_return": self.expected_return,
            "horizon":         self.horizon,
            "fallback_used":   self.fallback_used,
            "action_returns":  self.action_returns,
            "trajectory_accs": [s.accuracy for s, _ in self.trajectory],
            "trajectory_confs": [c for _, c in self.trajectory],
        }


class RolloutPlanner:
    """
    K-step lookahead over synthesis actions.

    For each candidate action A:
      1. Simulate K steps: [A, greedy_best, greedy_best, …]
         where greedy_best at each step is the action with the
         highest mean_acc_delta known so far.
      2. Compute discounted return:
           G(A) = Σ_{k=1}^{K}  γ^k * (predicted_acc_k − state.accuracy)
         weighted by trajectory confidence.
      3. Return the A with max G(A).

    Fallback: if fewer than ``min_actions_with_data`` candidate actions
    have sufficient transitions, skip rollout and return the heuristic.

    Parameters
    ----------
    trajectory_model : SynthesisTrajectoryModel
    horizon : int
        K steps to simulate (default 3).
    discount : float
        γ per step (default 0.90).
    min_actions_with_data : int
        Minimum number of distinct actions with enough data to plan.
    """

    def __init__(
        self,
        trajectory_model:       SynthesisTrajectoryModel,
        horizon:                int   = 3,
        discount:               float = 0.90,
        min_actions_with_data:  int   = 2,
    ):
        self.model             = trajectory_model
        self.horizon           = horizon
        self.discount          = discount
        self.min_actions_data  = min_actions_with_data

    def _greedy_action(self, candidates: List[SynthesisAction]) -> SynthesisAction:
        """Return the action with highest mean_acc_delta among candidates."""
        scored = [
            (a, self.model.mean_acc_delta(a))
            for a in candidates
            if self.model.n_transitions(a) > 0
        ]
        if not scored:
            return SynthesisAction.NO_ACTION
        return max(scored, key=lambda x: x[1])[0]

    def _rollout_action(
        self,
        initial_state:  SynthesisStateSnapshot,
        first_action:   SynthesisAction,
        candidates:     List[SynthesisAction],
    ) -> Tuple[float, List[Tuple[SynthesisStateSnapshot, float]]]:
        """
        Simulate K steps: first_action followed by greedy best.
        Returns (discounted_return, trajectory).
        """
        action_sequence = [first_action]
        for _ in range(self.horizon - 1):
            action_sequence.append(self._greedy_action(candidates))

        trajectory = self.model.predict_k_steps(initial_state, action_sequence)

        baseline_acc = initial_state.accuracy
        discounted_return = 0.0
        for k, (state_k, conf_k) in enumerate(trajectory, start=1):
            gain = state_k.accuracy - baseline_acc
            discounted_return += (self.discount ** k) * gain * conf_k

        return discounted_return, trajectory

    def plan(
        self,
        current_state:    SynthesisStateSnapshot,
        heuristic_action: SynthesisAction,
        candidates:       Optional[List[SynthesisAction]] = None,
    ) -> RolloutResult:
        """
        Run K-step lookahead and return the best action.

        Parameters
        ----------
        current_state : SynthesisStateSnapshot
        heuristic_action : SynthesisAction
            Fallback action if insufficient data for rollout.
        candidates : list, optional
            Actions to evaluate (default: all non-NO_ACTION actions).

        Returns
        -------
        RolloutResult
        """
        if candidates is None:
            candidates = list(SynthesisAction)   # include NO_ACTION as baseline

        # Check data sufficiency
        actions_with_data = [
            a for a in candidates if self.model.can_predict(a)
        ]

        if len(actions_with_data) < self.min_actions_data:
            # Fallback: insufficient data for rollout
            logger.debug(
                "RolloutPlanner: fallback (only %d/%d actions have data)",
                len(actions_with_data), self.min_actions_data,
            )
            return RolloutResult(
                best_action     = heuristic_action,
                expected_return = 0.0,
                trajectory      = [],
                horizon         = self.horizon,
                fallback_used   = True,
                action_returns  = {},
            )

        # Evaluate all candidates with sufficient data
        action_returns: Dict[str, float] = {}
        best_action     = heuristic_action
        best_return     = float("-inf")
        best_trajectory: List[Tuple[SynthesisStateSnapshot, float]] = []

        for action in actions_with_data:
            ret, traj = self._rollout_action(current_state, action, candidates)
            action_returns[action.value] = ret
            if ret > best_return:
                best_return     = ret
                best_action     = action
                best_trajectory = traj

        logger.info(
            "RolloutPlanner: best=%s return=%.4f horizon=%d (from %d candidates)",
            best_action.value, best_return, self.horizon, len(actions_with_data),
        )

        return RolloutResult(
            best_action     = best_action,
            expected_return = best_return,
            trajectory      = best_trajectory,
            horizon         = self.horizon,
            fallback_used   = False,
            action_returns  = action_returns,
        )


# ---------------------------------------------------------------------------
# TemporalCRLS — CausalCRLS + rollout planning
# ---------------------------------------------------------------------------

class TemporalCRLS(CausalCRLS):
    """
    WP20 upgrade of CausalCRLS: adds K-step rollout planning.

    Hierarchy of action selection
    --------------------------------
    1. **RolloutPlanner** (WP20) — asks: which action maximises discounted
       future accuracy over K generations?
    2. **CausalActionEvaluator** (WP19) — asks: which action has the highest
       observed ATE minus baseline drift?
    3. **WP17 heuristic** — asks: what rule-of-thumb fits the current drop?

    Layer (1) overrides (2) once sufficient trajectory data exists;
    layer (2) overrides (3) once sufficient observational data exists;
    layer (3) is always available as a last resort.

    Parameters
    ----------
    strategies : list[str]
    upward_rate, downward_rate : float
    synthesiser_kwargs : dict
    min_trials_to_override : int   (WP19 threshold)
    override_tolerance : float     (WP19 tolerance)
    rollout_horizon : int          (WP20 K)
    rollout_discount : float       (WP20 γ)
    min_transitions : int          (WP20 min per action)
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
        min_transitions:        int   = _MIN_TRANSITIONS,
    ):
        super().__init__(
            strategies             = strategies,
            upward_rate            = upward_rate,
            downward_rate          = downward_rate,
            synthesiser_kwargs     = synthesiser_kwargs,
            min_trials_to_override = min_trials_to_override,
            override_tolerance     = override_tolerance,
        )
        # WP20 additions
        self.traj_model = SynthesisTrajectoryModel(
            min_transitions  = min_transitions,
            confidence_decay = 0.85,
        )
        self.planner = RolloutPlanner(
            trajectory_model      = self.traj_model,
            horizon               = rollout_horizon,
            discount              = rollout_discount,
            min_actions_with_data = 2,
        )
        self.rollout_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Override end_of_generation to add rollout layer
    # ------------------------------------------------------------------

    def end_of_generation(
        self,
        regime: str = "",
    ) -> Tuple[SynthesisRecord, CausalRecommendation, RolloutResult]:
        """
        Run synthesis with rollout planning.

        Returns
        -------
        (SynthesisRecord, CausalRecommendation, RolloutResult)
        """
        acc_now  = self.acc_history[-1]
        acc_prev = self.acc_history[-2] if len(self.acc_history) >= 2 else None

        # --- Layer 3: WP17 heuristic ---
        heuristic_action, heuristic_trigger = self.synth._choose_action(
            acc_now, acc_prev, self.metacog.get_pattern_summary()
        )

        # --- Layer 2: WP19 causal ---
        causal_rec = self.evaluator.recommend(heuristic_action, heuristic_trigger)

        # --- Layer 1: WP20 rollout ---
        current_snapshot = SynthesisStateSnapshot.from_meta_and_acc(
            self.generation, self.meta, acc_now
        )
        rollout = self.planner.plan(
            current_state    = current_snapshot,
            heuristic_action = causal_rec.action,   # planner's fallback = WP19 choice
        )

        # Final action: rollout if not fallback, else causal
        chosen_action  = rollout.best_action
        chosen_trigger = (
            f"[rollout K={rollout.horizon}] "
            f"best={rollout.best_action.value} "
            f"return={rollout.expected_return:+.4f}; "
            f"causal_fallback={causal_rec.trigger}"
        ) if not rollout.fallback_used else causal_rec.trigger

        record = self._synthesise_with_action(chosen_action, chosen_trigger, acc_now, acc_prev)

        # Ingest the record into the trajectory model (next gen will complete it)
        # We register a pending transition that will be completed after next gen
        self._pending_transition_record = record

        self.gen_log.append({
            "generation":    self.generation,
            "regime":        regime,
            "acc":           acc_now,
            "heuristic":     heuristic_action.value,
            "causal_action": causal_rec.action.value,
            "rollout_action": rollout.best_action.value,
            "rollout_fallback": rollout.fallback_used,
            "override":      causal_rec.override,
            "ate":           causal_rec.ate_estimate.ate if causal_rec.ate_estimate else None,
            "expected_return": rollout.expected_return,
            "safety":        record.safety_status,
        })
        self.rollout_log.append(rollout.to_dict())

        self.generation += 1
        return record, causal_rec, rollout

    # ------------------------------------------------------------------
    # Override run_generation to ingest completed trajectory transitions
    # ------------------------------------------------------------------

    def run_generation(
        self,
        puzzles:     List[Tuple],
        tactic_fns:  Dict[str, Any],
        evaluate_fn: Callable,
    ) -> float:
        """Play all puzzles; complete pending trajectory transition."""
        # Complete the pending transition from last end_of_generation
        if (hasattr(self, "_pending_transition_record")
                and self._pending_transition_record is not None):
            # record_next_generation_acc will fill acc_after on the WP17 record;
            # we then build the transition once acc is known
            pending = self._pending_transition_record
            self._pending_transition_record = None
            # Run one evaluation pass to measure accuracy *before* updating
            if self.acc_history:
                next_acc = self._eval_batch(puzzles, tactic_fns, evaluate_fn, update=False)
                pending.acc_after  = next_acc
                pending.improvement = next_acc - pending.acc_before
                # Ingest into trajectory model
                self.traj_model.ingest_record_pair(pending)
                # Also feed WP19 evaluator
                self.evaluator.update(pending)

        acc = super().run_generation(puzzles, tactic_fns, evaluate_fn)
        return acc

    def get_full_report(self) -> Dict[str, Any]:
        report = super().get_full_report()
        report["trajectory_model_summary"] = self.traj_model.get_summary()
        report["rollout_log"]              = self.rollout_log
        return report


# ---------------------------------------------------------------------------
# Exit-criteria verifier
# ---------------------------------------------------------------------------

def verify_wp20_exit_criteria(crls: TemporalCRLS) -> Dict[str, bool]:
    """
    Verify WP20 exit criteria.

    Criteria
    --------
    trajectory_model_trained   At least one action has ≥ min_transitions
    rollout_planned            At least one non-fallback rollout was executed
    rollout_beats_heuristic    Rollout-chosen action ≠ heuristic at least once
    discounted_return_positive At least one rollout had positive expected return
    safety_preserved           All proposals safety-gated; no UNSAFE applied
    layers_all_active          WP17 heuristic, WP19 ATE, WP20 rollout all logged

    Returns
    -------
    dict mapping criterion name → bool
    """
    report  = crls.get_full_report()
    traj    = report["trajectory_model_summary"]
    rlog    = report["rollout_log"]
    glog    = report["generation_log"]
    safety  = report["safety_statistics"]

    # --- trajectory_model_trained ---
    traj_trained = any(
        v >= crls.traj_model.min_transitions
        for v in traj["transitions_per_action"].values()
    )

    # --- rollout_planned ---
    non_fallback = [r for r in rlog if not r["fallback_used"]]
    rollout_planned = len(non_fallback) > 0

    # --- rollout_beats_heuristic ---
    rollout_beats = any(
        entry.get("rollout_action") != entry.get("heuristic")
        for entry in glog
        if not entry.get("rollout_fallback", True)
    )

    # --- discounted_return_positive ---
    positive_return = any(
        r["expected_return"] > 1e-6 for r in rlog if not r["fallback_used"]
    )

    # --- safety_preserved ---
    safety_preserved = (
        safety["total_decisions"] > 0
        and safety.get("unsafe_decisions", 0) == 0
    )

    # --- layers_all_active ---
    layers_active = (
        len(glog) > 0
        and all("heuristic" in e and "causal_action" in e and "rollout_action" in e
                for e in glog)
    )

    criteria = {
        "trajectory_model_trained":   traj_trained,
        "rollout_planned":            rollout_planned,
        "rollout_beats_heuristic":    rollout_beats,
        "discounted_return_positive": positive_return,
        "safety_preserved":           safety_preserved,
        "layers_all_active":          layers_active,
    }

    logger.info("WP20 exit criteria: %s", criteria)
    return criteria
