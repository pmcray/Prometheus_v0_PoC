"""
WP24: Ensemble Disagreement & Uncertainty-Aware Action Selection
================================================================

Replaces the WP23 single-student confidence gate with a principled
**ensemble uncertainty** estimate, closing the overconfidence failure mode
that arises when one softmax model assigns spuriously high probability to an
action in a sparse-data region.

The gap in WP23
----------------
WP23's ``PolicyDistiller`` uses ``max(P_student(· | s))`` as its confidence
signal.  A single softmax model is systematically overconfident: the logistic
function saturates, and on states far from the training distribution the model
still produces a peaked distribution — often pointing confidently at the wrong
action.

Gal & Ghahramani (2016) quantified this: a single softmax student has no
mechanism to express *epistemic* (model) uncertainty — the uncertainty that
arises from having seen too little data.  For synthesis action selection, this
means the student could take over from the teacher on a novel state and apply
the wrong action with high apparent confidence.

WP24 fix
---------
Train a **small ensemble** of M independent ``StudentPolicy`` members, each
initialised with a different random seed (weight perturbation).  At every
generation each member makes a prediction independently.  The ensemble
provides two complementary uncertainty signals:

1. **Mean entropy** — H̄ = (1/M) Σ_m H(P_m(· | s))
   The average per-member entropy.  High if individual members are uncertain.

2. **Disagreement** (Jensen–Shannon divergence from the mean)
   JSD(P_1, …, P_M) = H(P̄) − (1/M) Σ_m H(P_m)
   where P̄ = (1/M) Σ_m P_m is the ensemble mean distribution.
   JSD = 0 when all members agree; positive when they disagree.
   This captures *epistemic* uncertainty — the spread of beliefs across
   differently-trained models.

Lakshminarayanan et al. (2017) showed that a simple ensemble of M=5 models
provides better-calibrated uncertainty than MC-Dropout or single softmax, and
Ovadia et al. (2019) confirmed this holds under distribution shift.

The **ensemble confidence gate** fires when:
    - All members have ≥ ``min_training_steps`` training updates.
    - JSD ≤ ``max_jsd_threshold``   (members agree)
    - mean(max(P_m(· | s))) ≥ ``min_mean_confidence``  (members are decisive)

The **ensemble action** is the argmax of the mean probability P̄.

``EnsembleCRLS`` inherits ``DistilledCRLS`` and replaces the single
``PolicyDistiller`` with an ``EnsembleDistiller``:

    Layer 7  EnsembleDistiller (WP24) — leads when JSD is low + confident
    Layer 6  PolicyDistiller (WP23)   — single-student baseline (still runs)
    Layer 5  BanditPolicy (WP22)      — explore/exploit
    Layer 4  MetaGradientOptimiser (WP21) — adapt hyper-parameters
    Layer 3  RolloutPlanner (WP20)    — K-step lookahead
    Layer 2  CausalActionEvaluator (WP19) — ATE-based recommendation
    Layer 1  WP17 heuristic           — rule-of-thumb fallback

The single WP23 student still trains in parallel (its loss provides a
complementary diagnostic), but the *ensemble* makes the leading/non-leading
decision.

``EnsembleRecord`` captures per-generation uncertainty metrics for full
auditability and downstream analysis.

Theoretical grounding
---------------------
Lakshminarayanan, Pritzel & Blundell (2017): "Simple and scalable predictive
uncertainty estimation using deep ensembles" — M=5 independent models with
random initialisation provides well-calibrated uncertainty at low cost; the
key insight is that diversity of initialisation drives useful disagreement.

Ovadia et al. (2019): "Can you trust your model's uncertainty?" — evaluated
ensemble methods under dataset shift; ensembles are the most reliable
uncertainty estimator across diverse shift types.

Gal & Ghahramani (2016): "Dropout as a Bayesian approximation" — formalises
epistemic vs aleatoric uncertainty; WP24's JSD corresponds to the epistemic
component in their decomposition.

Jensen & Shannon (1991): the JS divergence is the symmetrised, bounded
(∈ [0, ln 2] for natural log) variant of KL divergence; it is the correct
measure of pairwise agreement between probability distributions.

Classes
-------
EnsembleRecord          Audit record for one ensemble decision
EnsembleDistiller       M-member ensemble with JSD-based confidence gate
EnsembleCRLS            DistilledCRLS + WP24 ensemble layer
verify_wp24_exit_criteria   Six-criterion verifier
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from prometheus.wp17_crls_synthesis import SynthesisAction, SynthesisRecord
from prometheus.wp19_causal_evaluator import CausalRecommendation
from prometheus.wp20_temporal_planner import RolloutResult, SynthesisStateSnapshot
from prometheus.wp21_meta_gradient import MetaGradStep, MetaParams
from prometheus.wp22_bandit_exploration import BanditMode, ExplorationRecord
from prometheus.wp23_policy_distillation import (
    DistillationRecord,
    DistilledCRLS,
    PolicyDistiller,
    StudentPolicy,
    _ACTIONS,
    _ACTION_INDEX,
    _FEAT_DIM,
    _N_ACTIONS,
    _extract_features,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Entropy and JSD helpers
# ---------------------------------------------------------------------------

def _entropy(probs: List[float]) -> float:
    """Shannon entropy H(p) = -Σ p_i log(p_i) (nats)."""
    h = 0.0
    for p in probs:
        if p > 1e-12:
            h -= p * math.log(p)
    return h


def _mean_probs(prob_lists: List[List[float]]) -> List[float]:
    """Element-wise mean of a list of probability vectors."""
    m = len(prob_lists)
    return [sum(prob_lists[k][i] for k in range(m)) / m
            for i in range(_N_ACTIONS)]


def _jsd(prob_lists: List[List[float]]) -> float:
    """
    Jensen–Shannon divergence of M probability distributions.

    JSD(P_1, …, P_M) = H(P̄) − (1/M) Σ_m H(P_m)

    where P̄ = mean distribution.  Result ∈ [0, ln(M)] (nats).
    Normalised to [0, 1] by dividing by ln(M) (or left as-is if M=1).
    """
    if len(prob_lists) == 1:
        return 0.0
    p_mean = _mean_probs(prob_lists)
    h_mean = _entropy(p_mean)
    h_avg  = sum(_entropy(p) for p in prob_lists) / len(prob_lists)
    raw    = h_mean - h_avg   # ≥ 0 by Jensen's inequality
    # Normalise by max possible JSD = ln(M)
    max_jsd = math.log(len(prob_lists))
    return raw / max_jsd if max_jsd > 0 else 0.0


# ---------------------------------------------------------------------------
# EnsembleRecord  —  audit record for one ensemble decision
# ---------------------------------------------------------------------------

@dataclass
class EnsembleRecord:
    """
    Audit record for a single ensemble uncertainty evaluation.

    Attributes
    ----------
    generation : int
    member_actions : list[str]
        Argmax action of each ensemble member (action.value strings).
    member_confidences : list[float]
        Max-softmax confidence of each member.
    mean_probs : dict
        action.value → ensemble mean probability P̄_a.
    ensemble_action : SynthesisAction
        argmax of P̄ — the ensemble's consensus action.
    jsd : float
        Jensen–Shannon divergence ∈ [0, 1]; 0 = perfect agreement.
    mean_entropy : float
        Mean per-member entropy (nats).
    ensemble_led : bool
        True if the ensemble's action was used instead of the teacher's.
    teacher_action : SynthesisAction
        The WP22 teacher's action (for comparison).
    timestamp : float
    """
    generation:         int
    member_actions:     List[str]
    member_confidences: List[float]
    mean_probs:         Dict[str, float]
    ensemble_action:    SynthesisAction
    jsd:                float
    mean_entropy:       float
    ensemble_led:       bool
    teacher_action:     SynthesisAction
    timestamp:          float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation":         self.generation,
            "member_actions":     self.member_actions,
            "member_confidences": self.member_confidences,
            "mean_probs":         self.mean_probs,
            "ensemble_action":    self.ensemble_action.value,
            "jsd":                self.jsd,
            "mean_entropy":       self.mean_entropy,
            "ensemble_led":       self.ensemble_led,
            "teacher_action":     self.teacher_action.value,
        }


# ---------------------------------------------------------------------------
# EnsembleDistiller  —  M-member ensemble with JSD-based confidence gate
# ---------------------------------------------------------------------------

class EnsembleDistiller:
    """
    Ensemble of M independent ``StudentPolicy`` members.

    Each member is initialised with a small random weight perturbation
    (scale ``init_noise``) so that they diverge during online training despite
    seeing the same data sequence.  This is the simplest form of ensemble
    diversity (random initialisation) used by Lakshminarayanan et al. (2017).

    The confidence gate fires when:
        - All members have ≥ ``min_training_steps`` updates.
        - JSD(P_1, …, P_M)(state) ≤ ``max_jsd_threshold``.
        - mean(max(P_m(· | state))) ≥ ``min_mean_confidence``.

    Parameters
    ----------
    n_members : int
        Number of ensemble members M (default 5).
    learning_rate : float
        SGD learning rate shared by all members (default 0.05).
    l2_reg : float
        L2 regularisation shared by all members (default 1e-4).
    init_noise : float
        Std-dev of Gaussian noise added to each member's initial weights
        (default 0.01).  Drives ensemble diversity from generation 1.
    min_training_steps : int
        Minimum training steps per member before ensemble can lead (default 10).
    max_jsd_threshold : float
        Maximum allowed JSD for the ensemble to lead (default 0.15).
        At JSD=0 all members agree perfectly; at JSD=1 they maximally disagree.
    min_mean_confidence : float
        Minimum required mean max-probability across members (default 0.40).
    seed : int, optional
        Random seed for reproducible member initialisation.
    """

    def __init__(
        self,
        n_members:           int   = 5,
        learning_rate:       float = 0.05,
        l2_reg:              float = 1e-4,
        init_noise:          float = 0.01,
        min_training_steps:  int   = 10,
        max_jsd_threshold:   float = 0.15,
        min_mean_confidence: float = 0.40,
        seed:                Optional[int] = None,
    ):
        self.n_members           = n_members
        self.min_training_steps  = min_training_steps
        self.max_jsd_threshold   = max_jsd_threshold
        self.min_mean_confidence = min_mean_confidence

        rng = random.Random(seed)

        # Initialise members with small random weight perturbations
        self.members: List[StudentPolicy] = []
        for _ in range(n_members):
            m = StudentPolicy(learning_rate=learning_rate, l2_reg=l2_reg)
            # Add small random noise to break symmetry
            for i in range(_N_ACTIONS):
                for j in range(_FEAT_DIM):
                    m._W[i][j] = rng.gauss(0.0, init_noise)
            self.members.append(m)

        self.ensemble_log: List[EnsembleRecord] = []

    # ------------------------------------------------------------------
    # Forward pass — ensemble prediction
    # ------------------------------------------------------------------

    def predict_all(
        self, state: SynthesisStateSnapshot
    ) -> Tuple[List[List[float]], List[float]]:
        """
        Get probability vectors and max-confidences from all members.

        Returns
        -------
        (prob_lists, confidences)
            prob_lists : list of M probability vectors (each length |A|)
            confidences : list of M max-probabilities
        """
        phi = _extract_features(state)
        prob_lists = []
        confidences = []
        for m in self.members:
            probs = m.softmax_probs(phi)
            prob_lists.append(probs)
            confidences.append(max(probs))
        return prob_lists, confidences

    def predict_ensemble(
        self, state: SynthesisStateSnapshot
    ) -> Tuple[SynthesisAction, float, float, Dict[str, float]]:
        """
        Compute ensemble mean prediction, JSD, and mean entropy.

        Returns
        -------
        (ensemble_action, jsd, mean_entropy, mean_prob_dict)
        """
        prob_lists, confidences = self.predict_all(state)
        p_mean  = _mean_probs(prob_lists)
        jsd     = _jsd(prob_lists)
        h_avg   = sum(_entropy(p) for p in prob_lists) / len(prob_lists)
        best_i  = max(range(_N_ACTIONS), key=lambda i: p_mean[i])
        action  = _ACTIONS[best_i]
        p_dict  = {_ACTIONS[i].value: p_mean[i] for i in range(_N_ACTIONS)}
        return action, jsd, h_avg, p_dict

    # ------------------------------------------------------------------
    # Confidence gate
    # ------------------------------------------------------------------

    def should_lead(self, state: SynthesisStateSnapshot) -> bool:
        """
        Return True iff the ensemble is ready, agrees, and is decisive.

        Conditions (all must hold):
          1. Every member has ≥ min_training_steps updates.
          2. JSD ≤ max_jsd_threshold.
          3. mean(max(P_m)) ≥ min_mean_confidence.
        """
        # Condition 1: all members trained enough
        if any(m.training_steps < self.min_training_steps for m in self.members):
            return False

        prob_lists, confidences = self.predict_all(state)

        # Condition 2: low inter-member disagreement
        jsd = _jsd(prob_lists)
        if jsd > self.max_jsd_threshold:
            return False

        # Condition 3: members are individually decisive
        mean_conf = sum(confidences) / len(confidences)
        if mean_conf < self.min_mean_confidence:
            return False

        return True

    # ------------------------------------------------------------------
    # Training — update all members on teacher label
    # ------------------------------------------------------------------

    def train_all(
        self,
        state:          SynthesisStateSnapshot,
        teacher_action: SynthesisAction,
    ) -> List[float]:
        """
        Update every ensemble member on (state, teacher_action).

        Returns
        -------
        list of per-member cross-entropy losses
        """
        return [m.update(state, teacher_action) for m in self.members]

    # ------------------------------------------------------------------
    # Record construction
    # ------------------------------------------------------------------

    def make_record(
        self,
        state:          SynthesisStateSnapshot,
        teacher_action: SynthesisAction,
        ensemble_led:   bool,
        generation:     int,
    ) -> EnsembleRecord:
        """
        Snapshot current ensemble state into an EnsembleRecord.
        Call *before* training so that the record reflects pre-update beliefs.
        """
        prob_lists, confidences = self.predict_all(state)
        ensemble_action, jsd, mean_entropy, mean_prob_dict = self.predict_ensemble(state)
        member_actions = [_ACTIONS[max(range(_N_ACTIONS), key=lambda i: p[i])].value
                          for p in prob_lists]
        rec = EnsembleRecord(
            generation         = generation,
            member_actions     = member_actions,
            member_confidences = confidences,
            mean_probs         = mean_prob_dict,
            ensemble_action    = ensemble_action,
            jsd                = jsd,
            mean_entropy       = mean_entropy,
            ensemble_led       = ensemble_led,
            teacher_action     = teacher_action,
        )
        self.ensemble_log.append(rec)
        return rec

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_summary(self) -> Dict[str, Any]:
        log = self.ensemble_log
        if not log:
            return {
                "n_members":              self.n_members,
                "total_decisions":        0,
                "ensemble_led_count":     0,
                "ensemble_led_rate":      0.0,
                "mean_jsd":               None,
                "mean_entropy":           None,
                "member_training_steps":  [m.training_steps for m in self.members],
                "ensemble_log":           [],
            }
        jsds    = [r.jsd for r in log]
        entrs   = [r.mean_entropy for r in log]
        led     = sum(1 for r in log if r.ensemble_led)
        return {
            "n_members":              self.n_members,
            "total_decisions":        len(log),
            "ensemble_led_count":     led,
            "ensemble_led_rate":      led / len(log),
            "mean_jsd":               sum(jsds) / len(jsds),
            "final_jsd":              jsds[-1],
            "mean_entropy":           sum(entrs) / len(entrs),
            "final_entropy":          entrs[-1],
            "member_training_steps":  [m.training_steps for m in self.members],
            "ensemble_log":           [r.to_dict() for r in log],
        }


# ---------------------------------------------------------------------------
# EnsembleCRLS  —  DistilledCRLS + WP24 ensemble layer
# ---------------------------------------------------------------------------

class EnsembleCRLS(DistilledCRLS):
    """
    WP24 upgrade of DistilledCRLS: adds ensemble uncertainty estimation.

    Seven-layer action-selection hierarchy
    ---------------------------------------
    7. **EnsembleDistiller** (WP24) — leads when JSD is low + mean conf high
    6. **PolicyDistiller** (WP23)   — single-student baseline (still trains)
    5. **BanditPolicy** (WP22)      — explore/exploit
    4. **MetaGradientOptimiser** (WP21) — adapt hyper-parameters
    3. **RolloutPlanner** (WP20)    — K-step lookahead
    2. **CausalActionEvaluator** (WP19) — ATE-based recommendation
    1. **WP17 heuristic**           — rule-of-thumb fallback

    Both the WP23 single student and the WP24 ensemble train on every
    teacher decision.  The ensemble's JSD gate decides which system leads;
    the WP23 student provides a complementary confidence signal and a
    diagnostic comparison point.

    When the ensemble leads its action is used; when it does not, the WP23
    student decision (which may itself defer to the teacher) is used unchanged.

    Parameters
    ----------
    (all DistilledCRLS parameters, plus:)
    ensemble_n_members : int
        Number of ensemble members (default 5).
    ensemble_lr : float
        Ensemble member SGD learning rate (default 0.05).
    ensemble_l2 : float
        Ensemble member L2 regularisation (default 1e-4).
    ensemble_init_noise : float
        Std-dev of initial weight perturbation for diversity (default 0.01).
    ensemble_min_steps : int
        Min training steps per member before ensemble can lead (default 10).
    ensemble_max_jsd : float
        Maximum JSD allowed for ensemble to lead (default 0.15).
    ensemble_min_conf : float
        Minimum mean member confidence for ensemble to lead (default 0.40).
    ensemble_seed : int, optional
        Seed for reproducible member initialisation.
    """

    def __init__(
        self,
        strategies:              List[str],
        upward_rate:             float = 0.20,
        downward_rate:           float = 0.15,
        synthesiser_kwargs:      Optional[Dict[str, Any]] = None,
        min_trials_to_override:  int   = 3,
        override_tolerance:      float = 0.02,
        rollout_horizon:         int   = 3,
        rollout_discount:        float = 0.90,
        min_transitions:         int   = 3,
        meta_step_size:          float = 0.02,
        meta_fd_epsilon:         float = 0.05,
        meta_min_transitions:    int   = 4,
        initial_params:          Optional[MetaParams] = None,
        bandit_mode:             BanditMode = BanditMode.UCB1,
        exploration_coeff:       float = 1.0,
        prior_variance:          float = 1.0,
        force_explore_unseen:    bool  = True,
        distill_lr:              float = 0.05,
        distill_l2:              float = 1e-4,
        distill_min_steps:       int   = 10,
        distill_confidence:      float = 0.50,
        # WP24 additions
        ensemble_n_members:      int   = 5,
        ensemble_lr:             float = 0.05,
        ensemble_l2:             float = 1e-4,
        ensemble_init_noise:     float = 0.01,
        ensemble_min_steps:      int   = 10,
        ensemble_max_jsd:        float = 0.15,
        ensemble_min_conf:       float = 0.40,
        ensemble_seed:           Optional[int] = None,
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
            bandit_mode            = bandit_mode,
            exploration_coeff      = exploration_coeff,
            prior_variance         = prior_variance,
            force_explore_unseen   = force_explore_unseen,
            distill_lr             = distill_lr,
            distill_l2             = distill_l2,
            distill_min_steps      = distill_min_steps,
            distill_confidence     = distill_confidence,
        )

        # WP24 addition
        self.ensemble = EnsembleDistiller(
            n_members           = ensemble_n_members,
            learning_rate       = ensemble_lr,
            l2_reg              = ensemble_l2,
            init_noise          = ensemble_init_noise,
            min_training_steps  = ensemble_min_steps,
            max_jsd_threshold   = ensemble_max_jsd,
            min_mean_confidence = ensemble_min_conf,
            seed                = ensemble_seed,
        )
        self.ensemble_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Override end_of_generation to add ensemble layer
    # ------------------------------------------------------------------

    def end_of_generation(
        self,
        regime: str = "",
    ) -> Tuple[SynthesisRecord, CausalRecommendation, RolloutResult,
               MetaGradStep, ExplorationRecord, DistillationRecord,
               EnsembleRecord]:
        """
        Run synthesis with all seven layers: WP17→WP19→WP20→WP21→WP22→WP23→WP24.

        Layers 1–6 execute in full (same as DistilledCRLS).  The WP24 ensemble
        then decides whether to override the WP23/teacher choice with the
        ensemble consensus.

        Returns
        -------
        (SynthesisRecord, CausalRecommendation, RolloutResult,
         MetaGradStep, ExplorationRecord, DistillationRecord, EnsembleRecord)
        """
        # ----------------------------------------------------------------
        # Step 1: run layers 1–5 (WP17 → WP22) — always executes
        # ----------------------------------------------------------------
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

        # Layer 4: WP21 meta-gradient
        self.meta_params, grad_step = self.meta_opt.step(
            state       = current_snapshot,
            best_action = rollout.best_action,
            params      = self.meta_params,
            generation  = self.generation,
        )
        self._apply_meta_params()

        # Layer 5: WP22 bandit
        exploit_action = rollout.best_action
        bandit_rec = self.bandit.select(
            exploit_action = exploit_action,
            generation     = self.generation,
        )
        teacher_action = bandit_rec.explore_action

        # ----------------------------------------------------------------
        # Step 2: WP23 single-student decision (same logic as DistilledCRLS)
        # ----------------------------------------------------------------
        student_leads = self.distiller.should_lead(current_snapshot)
        if student_leads:
            wp23_action, _, _ = self.distiller.student.predict(current_snapshot)
        else:
            wp23_action = teacher_action

        # ----------------------------------------------------------------
        # Step 3: WP24 ensemble decision
        # ----------------------------------------------------------------
        ensemble_leads = self.ensemble.should_lead(current_snapshot)

        # Build pre-update EnsembleRecord
        ensemble_rec = self.ensemble.make_record(
            state          = current_snapshot,
            teacher_action = teacher_action,
            ensemble_led   = ensemble_leads,
            generation     = self.generation,
        )

        if ensemble_leads:
            final_action = ensemble_rec.ensemble_action
            chosen_trigger = (
                f"[ensemble WP24 LEAD] "
                f"jsd={ensemble_rec.jsd:.4f} "
                f"mean_conf={sum(ensemble_rec.member_confidences)/len(ensemble_rec.member_confidences):.3f} "
                f"ensemble={final_action.value} teacher={teacher_action.value}; "
                f"M={self.ensemble.n_members} steps={self.ensemble.members[0].training_steps}"
            )
        elif student_leads:
            final_action = wp23_action
            chosen_trigger = (
                f"[distilled STUDENT wp23] "
                f"conf={self.distiller.student.predict(current_snapshot)[1]:.3f} "
                f"student={wp23_action.value} teacher={teacher_action.value}; "
                f"jsd={ensemble_rec.jsd:.4f} [ensemble not confident]"
            )
        else:
            final_action = teacher_action
            if bandit_rec.is_exploration:
                chosen_trigger = (
                    f"[bandit {self.bandit.mode.value} EXPLORE] "
                    f"exploit={exploit_action.value} → explore={teacher_action.value}; "
                    f"n_trials={bandit_rec.n_trials.get(teacher_action.value, 0)}; "
                    f"jsd={ensemble_rec.jsd:.4f}"
                )
            else:
                rollout_trigger = (
                    f"[rollout K={rollout.horizon}] "
                    f"best={rollout.best_action.value} "
                    f"return={rollout.expected_return:+.4f}"
                ) if not rollout.fallback_used else causal_rec.trigger
                chosen_trigger = (
                    f"[bandit {self.bandit.mode.value} EXPLOIT] "
                    f"{rollout_trigger}; "
                    f"jsd={ensemble_rec.jsd:.4f}"
                )

        # ----------------------------------------------------------------
        # Step 4: apply final_action through safety gate
        # ----------------------------------------------------------------
        record = self._synthesise_with_action(
            final_action, chosen_trigger, acc_now, acc_prev
        )

        # ----------------------------------------------------------------
        # Step 5: train WP23 student and WP24 ensemble on teacher label
        # ----------------------------------------------------------------
        distill_rec = self.distiller.train(
            state          = current_snapshot,
            teacher_action = teacher_action,
            generation     = self.generation,
            student_led    = student_leads and not ensemble_leads,
        )
        self.ensemble.train_all(current_snapshot, teacher_action)

        # ----------------------------------------------------------------
        # Step 6: housekeeping
        # ----------------------------------------------------------------
        self._pending_exploration       = bandit_rec
        self._pending_transition_record = record

        self._log_pending_transition_record(record)
        self.meta_grad_log.append(grad_step.to_dict())
        self.bandit_log.append(bandit_rec.to_dict())
        self.distillation_log.append(distill_rec.to_dict())
        self.ensemble_log.append(ensemble_rec.to_dict())

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
            "bandit_action":     teacher_action.value,
            "bandit_explore":    bandit_rec.is_exploration,
            "student_led":       student_leads and not ensemble_leads,
            "student_action":    distill_rec.student_action.value,
            "distill_conf":      distill_rec.confidence,
            "distill_loss":      distill_rec.loss,
            "ensemble_led":      ensemble_leads,
            "ensemble_action":   ensemble_rec.ensemble_action.value,
            "ensemble_jsd":      ensemble_rec.jsd,
            "ensemble_entropy":  ensemble_rec.mean_entropy,
            "safety":            record.safety_status,
        })
        self.rollout_log.append(rollout.to_dict())

        self.generation += 1
        return record, causal_rec, rollout, grad_step, bandit_rec, distill_rec, ensemble_rec

    # ------------------------------------------------------------------
    # Extended report
    # ------------------------------------------------------------------

    def get_full_report(self) -> Dict[str, Any]:
        report = super().get_full_report()
        report["ensemble_summary"] = self.ensemble.get_summary()
        report["ensemble_log"]     = self.ensemble_log
        return report


# ---------------------------------------------------------------------------
# Exit-criteria verifier
# ---------------------------------------------------------------------------

def verify_wp24_exit_criteria(crls: EnsembleCRLS) -> Dict[str, bool]:
    """
    Verify WP24 exit criteria.

    Criteria
    --------
    ensemble_constructed        EnsembleDistiller exists with correct member count
    all_members_trained         Every member has ≥ min_training_steps updates
    jsd_computed                At least one EnsembleRecord has a valid JSD value
    jsd_decreases               Mean JSD in the latter half < mean JSD in the first half
    ensemble_led_at_least_once  Ensemble led at least one generation
    safety_preserved            All proposals safety-gated; no UNSAFE action applied

    Returns
    -------
    dict mapping criterion name → bool
    """
    report  = crls.get_full_report()
    esumm   = report["ensemble_summary"]
    safety  = report["safety_statistics"]
    elog    = report["ensemble_log"]

    # --- ensemble_constructed ---
    ens = crls.ensemble
    ensemble_ok = (
        isinstance(ens, EnsembleDistiller)
        and len(ens.members) == ens.n_members
        and all(isinstance(m, StudentPolicy) for m in ens.members)
    )

    # --- all_members_trained ---
    all_trained = all(
        m.training_steps >= ens.min_training_steps
        for m in ens.members
    )

    # --- jsd_computed ---
    jsd_computed = (
        len(elog) > 0
        and all(isinstance(r.get("jsd"), float) for r in elog)
    )

    # --- jsd_decreases ---
    jsds = [r["jsd"] for r in elog] if elog else []
    if len(jsds) >= 4:
        mid = len(jsds) // 2
        jsd_decreases = (
            sum(jsds[mid:]) / len(jsds[mid:])
            < sum(jsds[:mid]) / len(jsds[:mid])
        )
    else:
        jsd_decreases = False

    # --- ensemble_led_at_least_once ---
    ensemble_led = esumm.get("ensemble_led_count", 0) > 0

    # --- safety_preserved ---
    safety_preserved = (
        safety["total_decisions"] > 0
        and safety.get("unsafe_decisions", 0) == 0
    )

    criteria = {
        "ensemble_constructed":       ensemble_ok,
        "all_members_trained":        all_trained,
        "jsd_computed":               jsd_computed,
        "jsd_decreases":              jsd_decreases,
        "ensemble_led_at_least_once": ensemble_led,
        "safety_preserved":           safety_preserved,
    }

    logger.info("WP24 exit criteria: %s", criteria)
    return criteria
