"""
WP23: Policy Distillation
=========================

Compresses the five-layer WP17–22 expert stack into a lightweight *student
policy* that approximates the teacher's action distribution without running
the full causal / rollout / meta-gradient / bandit pipeline every generation.

The gap in WP17–22
--------------------
The BanditCRLS teacher (WP22) runs five planning layers end-to-end each
generation.  While each layer is individually cheap, the combined cost scales
with:
  - trajectory-model queries (WP20 rollout over K steps × |actions|),
  - finite-difference meta-gradient (5 parameters × 2 surrogate calls each),
  - bandit score computation (|SynthesisAction| UCB / Thompson evaluations).

As the synthesis stack is deployed at scale — or embedded in a resource-
constrained loop — this overhead accumulates.  More fundamentally, after many
generations the teacher's *behaviour* becomes predictable: it has converged
on a near-optimal action distribution.  Continuing to re-compute the full
pipeline yields diminishing returns while paying full cost.

Hinton et al. (2015) formalised this as **knowledge distillation**: train a
compact student to mimic a teacher's *soft* output distribution (rather than
hard labels), transferring the teacher's generalisation without its cost.

WP23 fix
---------
``PolicyDistiller`` observes every (state, teacher_action) pair produced by
BanditCRLS and fits a *student linear model*:

    P_student(a | s) = softmax( W · φ(s) )

where:
  φ(s) ∈ ℝ^d  is a fixed feature vector extracted from SynthesisStateSnapshot
  W ∈ ℝ^{|A| × d}  is the student weight matrix (one row per SynthesisAction)

Training uses online **cross-entropy minimisation** via stochastic gradient
descent:
    L = −log P_student( a_teacher | s )
    W ← W + η · ∇_W (−L)

The gradient for the one-hot teacher label against the softmax is simply:
    ∇_{W_a} L = (P_a − 1{a = a_teacher}) · φ(s)

This is the standard multinomial logistic regression online update rule
(Bottou 1998; Bishop 2006, §4.3).

A ``DistillationRecord`` captures every training step for full auditability.

``DistilledCRLS`` inherits ``BanditCRLS`` and adds a sixth layer:

    Layer 6  PolicyDistiller (WP23) — student; replaces teacher when confident
    Layer 5  BanditPolicy (WP22)    — explore/exploit
    Layer 4  MetaGradientOptimiser (WP21) — adapt hyper-parameters
    Layer 3  RolloutPlanner (WP20)  — K-step lookahead
    Layer 2  CausalActionEvaluator (WP19) — ATE-based recommendation
    Layer 1  WP17 heuristic         — rule-of-thumb fallback

The student fires *in place of* layers 1–5 when its confidence
(max softmax probability) exceeds ``confidence_threshold`` **and** it has
been trained on at least ``min_training_steps`` examples.  Otherwise the full
teacher pipeline runs and its output is added to the student's training set.

This gives a natural curriculum:
  early generations  → teacher runs, student learns
  later generations  → student takes over, teacher only audits

The teacher still computes a soft label for every generation (even when the
student leads) so the distillation training signal never stops.

Confidence gate
---------------
``PolicyDistiller.should_lead(state)`` returns True iff:
    - training_steps ≥ min_training_steps
    - max(P_student(· | s)) ≥ confidence_threshold

When the student leads:
    - ``DistillationRecord.student_led = True``
    - The student's argmax action is used as ``final_action``
    - The teacher pipeline *still runs* in the background to compute the
      soft label and update the student weights

When the student does not lead:
    - The teacher's action is used (WP22 bandit output)
    - The teacher output is used as training signal for the student

Theoretical grounding
---------------------
Hinton, Vinyals & Dean (2015): "Distilling the Knowledge in a Neural Network"
— soft targets from the teacher carry more information per example than hard
labels; distillation typically requires ≪10× the training data of direct
supervised learning.

Bucilua, Caruana & Niculescu-Mizil (2006): "Model compression" — the original
model-compression paper; compact student matches large ensemble performance.

Bottou (1998): "Online learning and stochastic approximations" — SGD converges
to the MLE for logistic regression under mild regularity conditions.

Lopez-Paz et al. (2016): "Unifying distillation and privileged information" —
formalises distillation as a special case of learning with privileged
information (LUPI), motivating WP23's teacher-in-the-loop architecture.

Classes
-------
DistillationRecord      Audit record for one distillation training step
StudentPolicy           Online softmax student; trains on (state, action) pairs
PolicyDistiller         Wraps StudentPolicy with confidence gate + summary
DistilledCRLS           BanditCRLS + WP23 distillation layer
verify_wp23_exit_criteria   Six-criterion verifier
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from prometheus.wp17_crls_synthesis import SynthesisAction, SynthesisRecord
from prometheus.wp19_causal_evaluator import CausalRecommendation
from prometheus.wp20_temporal_planner import RolloutResult, SynthesisStateSnapshot
from prometheus.wp21_meta_gradient import MetaGradStep, MetaParams
from prometheus.wp22_bandit_exploration import BanditCRLS, BanditMode, ExplorationRecord

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature extraction  φ(s) : SynthesisStateSnapshot → ℝ^d
# ---------------------------------------------------------------------------

_ACTIONS: List[SynthesisAction] = list(SynthesisAction)
_N_ACTIONS: int = len(_ACTIONS)
_ACTION_INDEX: Dict[SynthesisAction, int] = {a: i for i, a in enumerate(_ACTIONS)}


def _extract_features(state: SynthesisStateSnapshot) -> List[float]:
    """
    Extract a fixed-length feature vector from a SynthesisStateSnapshot.

    Feature vector φ(s) ∈ ℝ^(3 + |A|) where |A| = number of SynthesisActions:
      [0]       accuracy              (scalar)
      [1]       upward_rate           (scalar)
      [2]       generation / 100.0   (normalised generation counter)
      [3..3+|A|] strategy probability for each action's corresponding
                  strategy (strategy probs mapped by position if available,
                  else uniform padding)

    The feature vector is kept simple (no non-linearities) so that the linear
    student has an interpretable weight matrix and the distillation loop remains
    computationally negligible.
    """
    feat: List[float] = [
        state.accuracy,
        state.upward_rate,
        state.generation / 100.0,
    ]

    # Strategy probability features (one per SynthesisAction slot)
    # We use the sorted strategy probabilities to fill up to |A| slots.
    # This gives the student a view of the current strategy distribution.
    prob_values = list(state.probs.values()) if state.probs else []
    # Pad / truncate to exactly _N_ACTIONS entries
    prob_values = (prob_values + [0.0] * _N_ACTIONS)[:_N_ACTIONS]
    feat.extend(prob_values)

    return feat


_FEAT_DIM: int = 3 + _N_ACTIONS   # must match _extract_features output length


# ---------------------------------------------------------------------------
# DistillationRecord  —  audit record for one training step
# ---------------------------------------------------------------------------

@dataclass
class DistillationRecord:
    """
    Audit record for a single policy-distillation training step.

    Attributes
    ----------
    generation : int
    teacher_action : SynthesisAction
        Action chosen by the WP22 teacher (the training label).
    student_probs : dict
        action.value → softmax probability before the update.
    student_action : SynthesisAction
        The student's argmax action before the update.
    student_led : bool
        True if the student's action was used (not the teacher's).
    confidence : float
        max(student_probs) before the update.
    loss : float
        Cross-entropy loss −log P_student(teacher_action | state).
    training_step : int
        Cumulative number of SGD updates applied so far (after this step).
    timestamp : float
    """
    generation:     int
    teacher_action: SynthesisAction
    student_probs:  Dict[str, float]
    student_action: SynthesisAction
    student_led:    bool
    confidence:     float
    loss:           float
    training_step:  int
    timestamp:      float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation":     self.generation,
            "teacher_action": self.teacher_action.value,
            "student_probs":  self.student_probs,
            "student_action": self.student_action.value,
            "student_led":    self.student_led,
            "confidence":     self.confidence,
            "loss":           self.loss,
            "training_step":  self.training_step,
        }


# ---------------------------------------------------------------------------
# StudentPolicy  —  online softmax linear model
# ---------------------------------------------------------------------------

class StudentPolicy:
    """
    Online softmax linear student policy.

    Models P(a | s) = softmax(W · φ(s)) where W ∈ ℝ^{|A| × d}.

    Trained via online SGD on cross-entropy loss with the teacher's hard-label
    action as the target.

    Parameters
    ----------
    learning_rate : float
        SGD step size η (default 0.05).
    l2_reg : float
        L2 regularisation coefficient λ (default 1e-4).
        Regularises W toward zero, preventing over-fitting to early data.
    """

    def __init__(
        self,
        learning_rate: float = 0.05,
        l2_reg:        float = 1e-4,
    ):
        self.lr       = learning_rate
        self.l2       = l2_reg
        # Weight matrix W[action_index][feature_index] initialised to zero
        self._W: List[List[float]] = [
            [0.0] * _FEAT_DIM for _ in range(_N_ACTIONS)
        ]
        self.training_steps: int = 0

    # ------------------------------------------------------------------
    # Forward pass
    # ------------------------------------------------------------------

    def logits(self, features: List[float]) -> List[float]:
        """Compute raw logits  z_a = W[a] · φ(s)."""
        return [
            sum(self._W[i][j] * features[j] for j in range(_FEAT_DIM))
            for i in range(_N_ACTIONS)
        ]

    def softmax_probs(self, features: List[float]) -> List[float]:
        """Return softmax probabilities over actions given feature vector."""
        z = self.logits(features)
        z_max = max(z)
        exps = [math.exp(zi - z_max) for zi in z]
        total = sum(exps)
        return [e / total for e in exps]

    def predict(self, state: SynthesisStateSnapshot) -> Tuple[SynthesisAction, float, Dict[str, float]]:
        """
        Predict the best action and return (action, confidence, prob_dict).

        Parameters
        ----------
        state : SynthesisStateSnapshot

        Returns
        -------
        (best_action, confidence, {action.value → prob})
        """
        phi  = _extract_features(state)
        probs = self.softmax_probs(phi)
        best_idx    = max(range(_N_ACTIONS), key=lambda i: probs[i])
        best_action = _ACTIONS[best_idx]
        confidence  = probs[best_idx]
        prob_dict   = {_ACTIONS[i].value: probs[i] for i in range(_N_ACTIONS)}
        return best_action, confidence, prob_dict

    # ------------------------------------------------------------------
    # Backward pass (online SGD)
    # ------------------------------------------------------------------

    def update(
        self,
        state:          SynthesisStateSnapshot,
        teacher_action: SynthesisAction,
    ) -> float:
        """
        Perform one online SGD step to minimise cross-entropy against teacher_action.

        Returns
        -------
        float
            Cross-entropy loss before the update.
        """
        phi   = _extract_features(state)
        probs = self.softmax_probs(phi)
        t_idx = _ACTION_INDEX[teacher_action]

        # Loss: −log P_student(teacher_action | state)
        loss = -math.log(max(probs[t_idx], 1e-12))

        # Gradient of cross-entropy w.r.t. W[a]:
        #   ∇_{W_a} L = (P_a − 1{a == teacher}) · φ(s)
        for i in range(_N_ACTIONS):
            indicator = 1.0 if i == t_idx else 0.0
            grad_scalar = probs[i] - indicator
            for j in range(_FEAT_DIM):
                # SGD gradient ascent on negative loss = gradient *descent* on loss
                # Also apply L2 regularisation: ∇ regulariser = λ W[i][j]
                self._W[i][j] -= self.lr * (grad_scalar * phi[j] + self.l2 * self._W[i][j])

        self.training_steps += 1
        return loss

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def weight_norm(self) -> float:
        """Frobenius norm of W — useful for monitoring training dynamics."""
        return math.sqrt(sum(w ** 2 for row in self._W for w in row))

    def get_weight_matrix(self) -> List[List[float]]:
        """Return a copy of the weight matrix W."""
        return [list(row) for row in self._W]


# ---------------------------------------------------------------------------
# PolicyDistiller  —  confidence gate + distillation summary
# ---------------------------------------------------------------------------

class PolicyDistiller:
    """
    Wraps ``StudentPolicy`` with a confidence gate.

    ``should_lead(state)`` returns True iff:
        1. ``student.training_steps >= min_training_steps``
        2. ``max(P_student(· | state)) >= confidence_threshold``

    When the student leads, the teacher still runs (to produce a soft label
    and update the student), so the distillation signal is continuous.

    Parameters
    ----------
    learning_rate : float
        SGD step size for the student (default 0.05).
    l2_reg : float
        L2 regularisation coefficient (default 1e-4).
    min_training_steps : int
        Minimum number of SGD updates before the student is allowed to lead
        (default 10).  Prevents the student from leading on random weights.
    confidence_threshold : float
        Minimum max-softmax-probability required to let the student lead
        (default 0.50).
    """

    def __init__(
        self,
        learning_rate:        float = 0.05,
        l2_reg:               float = 1e-4,
        min_training_steps:   int   = 10,
        confidence_threshold: float = 0.50,
    ):
        self.student              = StudentPolicy(learning_rate=learning_rate, l2_reg=l2_reg)
        self.min_training_steps   = min_training_steps
        self.confidence_threshold = confidence_threshold
        self.distillation_log:    List[DistillationRecord] = []

    # ------------------------------------------------------------------
    # Confidence gate
    # ------------------------------------------------------------------

    def should_lead(self, state: SynthesisStateSnapshot) -> bool:
        """Return True if the student is ready and confident enough to lead."""
        if self.student.training_steps < self.min_training_steps:
            return False
        _, confidence, _ = self.student.predict(state)
        return confidence >= self.confidence_threshold

    # ------------------------------------------------------------------
    # Train-and-record
    # ------------------------------------------------------------------

    def train(
        self,
        state:          SynthesisStateSnapshot,
        teacher_action: SynthesisAction,
        generation:     int,
        student_led:    bool,
    ) -> DistillationRecord:
        """
        Record the teacher label, update the student, and return an audit record.

        Parameters
        ----------
        state : SynthesisStateSnapshot
            Current synthesis state (feature source).
        teacher_action : SynthesisAction
            The action the teacher (WP22 bandit) chose.
        generation : int
        student_led : bool
            Whether the student's action was the one actually applied.

        Returns
        -------
        DistillationRecord
        """
        # Snapshot pre-update probabilities for the record
        student_action, confidence, prob_dict_before = self.student.predict(state)

        # SGD update
        loss = self.student.update(state, teacher_action)

        rec = DistillationRecord(
            generation     = generation,
            teacher_action = teacher_action,
            student_probs  = prob_dict_before,
            student_action = student_action,
            student_led    = student_led,
            confidence     = confidence,
            loss           = loss,
            training_step  = self.student.training_steps,
        )
        self.distillation_log.append(rec)

        logger.info(
            "PolicyDistiller gen %d: teacher=%s student=%s led=%s "
            "conf=%.3f loss=%.4f step=%d",
            generation,
            teacher_action.value, student_action.value, student_led,
            confidence, loss, self.student.training_steps,
        )
        return rec

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_summary(self) -> Dict[str, Any]:
        log = self.distillation_log
        if not log:
            return {
                "training_steps":           0,
                "student_led_count":        0,
                "teacher_led_count":        0,
                "student_led_rate":         0.0,
                "mean_loss":                None,
                "mean_confidence":          None,
                "weight_norm":              self.student.weight_norm(),
                "distillation_log":         [],
            }
        losses      = [r.loss for r in log]
        confs       = [r.confidence for r in log]
        led_count   = sum(1 for r in log if r.student_led)
        return {
            "training_steps":           self.student.training_steps,
            "student_led_count":        led_count,
            "teacher_led_count":        len(log) - led_count,
            "student_led_rate":         led_count / len(log),
            "mean_loss":                sum(losses) / len(losses),
            "final_loss":               losses[-1],
            "mean_confidence":          sum(confs) / len(confs),
            "final_confidence":         confs[-1],
            "weight_norm":              self.student.weight_norm(),
            "distillation_log":         [r.to_dict() for r in log],
        }


# ---------------------------------------------------------------------------
# DistilledCRLS  —  BanditCRLS + WP23 distillation layer
# ---------------------------------------------------------------------------

class DistilledCRLS(BanditCRLS):
    """
    WP23 upgrade of BanditCRLS: adds a policy-distillation student layer.

    Six-layer action-selection hierarchy
    -------------------------------------
    6. **PolicyDistiller** (WP23) — student policy; leads when confident
    5. **BanditPolicy** (WP22)    — explore/exploit
    4. **MetaGradientOptimiser** (WP21) — adapt hyperparameters
    3. **RolloutPlanner** (WP20)  — K-step lookahead
    2. **CausalActionEvaluator** (WP19) — ATE-based recommendation
    1. **WP17 heuristic**         — rule-of-thumb fallback

    The student observes every teacher (WP22) decision and trains online.
    Once it meets the confidence threshold it takes over, while the teacher
    continues to generate training labels in the background.

    Parameters
    ----------
    (all BanditCRLS parameters, plus:)
    distill_lr : float
        Student SGD learning rate (default 0.05).
    distill_l2 : float
        Student L2 regularisation (default 1e-4).
    distill_min_steps : int
        Min training steps before student can lead (default 10).
    distill_confidence : float
        Min student confidence required to lead (default 0.50).
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
        # WP23 additions
        distill_lr:              float = 0.05,
        distill_l2:              float = 1e-4,
        distill_min_steps:       int   = 10,
        distill_confidence:      float = 0.50,
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
        )

        # WP23 addition
        self.distiller = PolicyDistiller(
            learning_rate        = distill_lr,
            l2_reg               = distill_l2,
            min_training_steps   = distill_min_steps,
            confidence_threshold = distill_confidence,
        )
        self.distillation_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Override end_of_generation to add distillation layer
    # ------------------------------------------------------------------

    def end_of_generation(
        self,
        regime: str = "",
    ) -> Tuple[SynthesisRecord, CausalRecommendation, RolloutResult,
               MetaGradStep, ExplorationRecord, DistillationRecord]:
        """
        Run synthesis with all six layers: WP17→WP19→WP20→WP21→WP22→WP23.

        The WP22 teacher pipeline always runs to completion.  If the student
        is confident enough its argmax action is used as the *applied* action
        (student_led=True); otherwise the WP22 bandit action is used
        (student_led=False).  Either way the teacher action is the distillation
        training label.

        Returns
        -------
        (SynthesisRecord, CausalRecommendation, RolloutResult,
         MetaGradStep, ExplorationRecord, DistillationRecord)
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
        teacher_action = bandit_rec.explore_action   # WP22 output = teacher label

        # ----------------------------------------------------------------
        # Step 2: WP23 student decision
        # ----------------------------------------------------------------
        student_leads = self.distiller.should_lead(current_snapshot)

        if student_leads:
            student_action, _, _ = self.distiller.student.predict(current_snapshot)
            final_action = student_action
            chosen_trigger = (
                f"[distilled STUDENT] conf={self.distiller.student.predict(current_snapshot)[1]:.3f} "
                f"student={student_action.value} "
                f"teacher={teacher_action.value}; "
                f"step={self.distiller.student.training_steps}"
            )
        else:
            final_action   = teacher_action
            if bandit_rec.is_exploration:
                chosen_trigger = (
                    f"[bandit {self.bandit.mode.value} EXPLORE] "
                    f"exploit={exploit_action.value} → explore={teacher_action.value}; "
                    f"n_trials={bandit_rec.n_trials.get(teacher_action.value, 0)}; "
                    f"ucb={bandit_rec.ucb_scores.get(teacher_action.value, 0):.4f}"
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

        # ----------------------------------------------------------------
        # Step 3: apply final_action through safety gate
        # ----------------------------------------------------------------
        record = self._synthesise_with_action(
            final_action, chosen_trigger, acc_now, acc_prev
        )

        # ----------------------------------------------------------------
        # Step 4: train student on teacher label (always)
        # ----------------------------------------------------------------
        distill_rec = self.distiller.train(
            state          = current_snapshot,
            teacher_action = teacher_action,
            generation     = self.generation,
            student_led    = student_leads,
        )

        # ----------------------------------------------------------------
        # Step 5: housekeeping
        # ----------------------------------------------------------------
        self._pending_exploration     = bandit_rec
        self._pending_transition_record = record

        self._log_pending_transition_record(record)
        self.meta_grad_log.append(grad_step.to_dict())
        self.bandit_log.append(bandit_rec.to_dict())
        self.distillation_log.append(distill_rec.to_dict())

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
            "student_led":       student_leads,
            "student_action":    distill_rec.student_action.value,
            "distill_conf":      distill_rec.confidence,
            "distill_loss":      distill_rec.loss,
            "safety":            record.safety_status,
        })
        self.rollout_log.append(rollout.to_dict())

        self.generation += 1
        return record, causal_rec, rollout, grad_step, bandit_rec, distill_rec

    # ------------------------------------------------------------------
    # Extended report
    # ------------------------------------------------------------------

    def get_full_report(self) -> Dict[str, Any]:
        report = super().get_full_report()
        report["distillation_summary"] = self.distiller.get_summary()
        report["distillation_log"]     = self.distillation_log
        return report


# ---------------------------------------------------------------------------
# Exit-criteria verifier
# ---------------------------------------------------------------------------

def verify_wp23_exit_criteria(crls: DistilledCRLS) -> Dict[str, bool]:
    """
    Verify WP23 exit criteria.

    Criteria
    --------
    student_constructed         StudentPolicy exists with correct weight shape
    student_trained             At least ``min_training_steps`` SGD steps taken
    loss_decreased              Mean loss of latter half < mean loss of first half
    student_led_at_least_once   Student led at least one generation
    teacher_label_always_recorded  Every generation has a DistillationRecord
    safety_preserved            All proposals safety-gated; no UNSAFE action applied

    Returns
    -------
    dict mapping criterion name → bool
    """
    report  = crls.get_full_report()
    dsumm   = report["distillation_summary"]
    safety  = report["safety_statistics"]
    dlog    = report["distillation_log"]

    # --- student_constructed ---
    student = crls.distiller.student
    student_ok = (
        isinstance(student, StudentPolicy)
        and len(student._W) == _N_ACTIONS
        and all(len(row) == _FEAT_DIM for row in student._W)
    )

    # --- student_trained ---
    student_trained = dsumm.get("training_steps", 0) >= crls.distiller.min_training_steps

    # --- loss_decreased ---
    losses = [r["loss"] for r in dlog] if dlog else []
    if len(losses) >= 4:
        mid  = len(losses) // 2
        loss_decreased = (sum(losses[mid:]) / len(losses[mid:])
                          < sum(losses[:mid]) / len(losses[:mid]))
    else:
        loss_decreased = False   # not enough data yet

    # --- student_led_at_least_once ---
    student_led = dsumm.get("student_led_count", 0) > 0

    # --- teacher_label_always_recorded ---
    teacher_recorded = len(dlog) == len(crls.gen_log)

    # --- safety_preserved ---
    safety_preserved = (
        safety["total_decisions"] > 0
        and safety.get("unsafe_decisions", 0) == 0
    )

    criteria = {
        "student_constructed":            student_ok,
        "student_trained":                student_trained,
        "loss_decreased":                 loss_decreased,
        "student_led_at_least_once":      student_led,
        "teacher_label_always_recorded":  teacher_recorded,
        "safety_preserved":               safety_preserved,
    }

    logger.info("WP23 exit criteria: %s", criteria)
    return criteria
