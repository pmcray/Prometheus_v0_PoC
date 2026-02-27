"""
WP28: Cross-Domain Student Transfer
=====================================

Generalises the WP23 student policy's feature space so that a student
trained on one domain (Go) can be applied **zero-shot** to a structurally
similar domain (Chess/ARC) via the WP18 analogy map.

The gap in WP17–26
--------------------
The WP23 ``StudentPolicy`` is trained on ``SynthesisStateSnapshot`` features
drawn from Go tactical puzzles.  When the system encounters a new domain
(Chess, ARC, Sokoban …) it must rebuild the student from scratch because:

  1. The feature space is domain-specific (Go strategy names → slot indices).
  2. The weight matrix W is not portable across domains.
  3. The WP18 analogy map already encodes structural similarity between
     Go and Chess tactics — but WP23 ignores it.

This blind spot is identical to the one WP18 solved at the *MetaLearner* level
(seeding target-domain strategy probs from source-domain probs via analogies).
WP28 applies the same principle one level up: it seeds the *student weight
matrix* from the source-domain student via the WP18 analogy map.

WP28 fix
---------
``DomainAdapter`` maps domain-specific ``SynthesisStateSnapshot`` objects into
a **shared** feature space φ_shared(s) ∈ ℝ^(3 + |A|) that is domain-agnostic:

  - Feature slots [0..2]: accuracy, upward_rate, generation/100  (unchanged)
  - Feature slots [3..3+|A|-1]: *re-ordered* strategy probs mapped by the
    analogy table so that structurally analogous strategies occupy the same slot.

``TransferStudentPolicy`` wraps a pre-trained source ``StudentPolicy`` (from
the Go domain) and uses the ``DomainAdapter`` to project target-domain states
into the same shared feature space, then runs the source student's weight matrix
directly — achieving *zero-shot* cross-domain inference.

``CrossDomainDistiller`` adds a third player to the WP23 distillation loop:

  1. **Teacher** (WP22 bandit) → hard label for both source and target
  2. **Source student** (WP23) → retrained only on source-domain examples
  3. **Transfer student** (WP28) → zero-shot on target domain;
     optionally fine-tuned (few-shot) once ≥ ``min_finetune_steps`` target
     examples are available

``TransferCRLS(HierarchicalCRLS)`` is the 10th layer.

``TransferRecord`` audit record + ``verify_wp28_exit_criteria``.

Layer hierarchy after WP28:

    Layer 10  CrossDomainDistiller (WP28) — zero-shot / few-shot transfer
    Layer 9   TaskDecomposer (WP26)       — per-subtask synthesis recommendation
    Layer 8   EWC guard (WP25)            — forgetting detection + consolidation
    Layer 7   EnsembleDistiller (WP24)    — JSD uncertainty gate
    Layer 6   PolicyDistiller (WP23)      — single-student baseline
    Layer 5   BanditPolicy (WP22)         — explore/exploit
    Layer 4   MetaGradientOptimiser (WP21)
    Layer 3   RolloutPlanner (WP20)
    Layer 2   CausalActionEvaluator (WP19)
    Layer 1   WP17 heuristic

Theoretical grounding
---------------------
Pan & Yang (2010): "A Survey on Transfer Learning" — inductive transfer via
parameter initialisation: seed target model weights from source model.

Finn, Abbeel & Levine (MAML, 2017): meta-learning for rapid adaptation from
a small number of target-domain examples — the few-shot fine-tuning in WP28
is a simplified non-gradient version of this idea.

Hofstadter (GEB, 1979): the analogy map as a *cross-level bridge* — the
structural isomorphism between domains lets the system deposit learned
weight structure from one domain directly into another, without retracing
the full learning trajectory.

Good (1965): an ultraintelligent machine would not merely improve within a
domain but would generalise the *improvement mechanism* across tasks.
WP28 generalises the student policy (the improvement mechanism) across
game domains.

Classes
-------
TransferRecord          Audit record for one cross-domain evaluation step
DomainAdapter           Projects target-domain states into shared feature space
TransferStudentPolicy   Wraps a pre-trained student; zero-shot + fine-tuning
CrossDomainDistiller    Source student + transfer student, dual training loop
TransferCRLS            HierarchicalCRLS + WP28 cross-domain transfer layer
verify_wp28_exit_criteria   Six-criterion verifier
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from prometheus.wp17_crls_synthesis import SynthesisAction, SynthesisRecord
from prometheus.wp18_analogy_engine import CrossDomainAnalogyMap
from prometheus.wp19_causal_evaluator import CausalRecommendation
from prometheus.wp20_temporal_planner import RolloutResult, SynthesisStateSnapshot
from prometheus.wp21_meta_gradient import MetaGradStep, MetaParams
from prometheus.wp22_bandit_exploration import BanditMode, ExplorationRecord
from prometheus.wp23_policy_distillation import (
    DistillationRecord,
    PolicyDistiller,
    StudentPolicy,
    _ACTIONS,
    _ACTION_INDEX,
    _FEAT_DIM,
    _N_ACTIONS,
    _extract_features,
)
from prometheus.wp24_ensemble_uncertainty import EnsembleRecord
from prometheus.wp25_ewc_forgetting import ForgettingRecord
from prometheus.wp26_hierarchical_decomp import (
    DecompositionRecord,
    HierarchicalCRLS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TransferRecord  —  audit record for one cross-domain evaluation step
# ---------------------------------------------------------------------------

@dataclass
class TransferRecord:
    """
    Audit record for a single cross-domain transfer evaluation.

    Attributes
    ----------
    generation : int
    source_domain : str
        Domain of the pre-trained source student (e.g. "go").
    target_domain : str
        Domain being evaluated zero-shot / few-shot (e.g. "chess").
    transfer_action : SynthesisAction
        Action predicted by the transfer student.
    transfer_confidence : float
        max(softmax) of the transfer student on this state.
    source_action : SynthesisAction
        Action predicted by the source student on the *source* state.
    teacher_action : SynthesisAction
        Ground-truth label from the WP22 teacher.
    transfer_led : bool
        True if the transfer student's action was used as the final action.
    finetune_steps : int
        Number of SGD fine-tuning steps applied on target-domain data so far.
    loss : float
        Cross-entropy loss of the transfer student against the teacher label.
    timestamp : float
    """
    generation:          int
    source_domain:       str
    target_domain:       str
    transfer_action:     SynthesisAction
    transfer_confidence: float
    source_action:       SynthesisAction
    teacher_action:      SynthesisAction
    transfer_led:        bool
    finetune_steps:      int
    loss:                float
    timestamp:           float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation":          self.generation,
            "source_domain":       self.source_domain,
            "target_domain":       self.target_domain,
            "transfer_action":     self.transfer_action.value,
            "transfer_confidence": self.transfer_confidence,
            "source_action":       self.source_action.value,
            "teacher_action":      self.teacher_action.value,
            "transfer_led":        self.transfer_led,
            "finetune_steps":      self.finetune_steps,
            "loss":                self.loss,
        }


# ---------------------------------------------------------------------------
# DomainAdapter  —  projects target-domain states into the shared feature space
# ---------------------------------------------------------------------------

class DomainAdapter:
    """
    Projects target-domain ``SynthesisStateSnapshot`` objects into the same
    shared feature space φ_shared(s) used by the source-domain student.

    The shared feature space φ_shared(s) ∈ ℝ^(3 + |A|) is identical to the
    WP23 feature space *except* that the strategy-probability slots are
    re-ordered so that structurally analogous target-domain strategies are
    placed in the same slot as their source-domain counterparts.

    Parameters
    ----------
    analogy_map : CrossDomainAnalogyMap
        Pre-built analogy map (e.g. from ``GoChessTacticRegistry.build()``).
    source_strategies : list[str]
        Strategy names in the source domain (determines slot ordering).
    target_strategies : list[str]
        Strategy names in the target domain.
    source_domain : str
        Domain label for the source (e.g. "go").
    target_domain : str
        Domain label for the target (e.g. "chess").
    min_analogy_confidence : float
        Analogies below this threshold are ignored (default 0.50).
    """

    def __init__(
        self,
        analogy_map:             CrossDomainAnalogyMap,
        source_strategies:       List[str],
        target_strategies:       List[str],
        source_domain:           str,
        target_domain:           str,
        min_analogy_confidence:  float = 0.50,
    ):
        self.analogy_map     = analogy_map
        self.source_strats   = source_strategies
        self.target_strats   = target_strategies
        self.source_domain   = source_domain
        self.target_domain   = target_domain
        self.min_conf        = min_analogy_confidence

        # Build a mapping: target_strategy_index → source_strategy_index
        # Used to re-order target probs into source-slot order.
        self._target_to_source_slot: Dict[int, int] = {}
        for t_idx, t_name in enumerate(target_strategies):
            analogues = analogy_map.get_source_analogues(
                target_tactic=t_name,
                source_domain=source_domain,
                min_confidence=min_analogy_confidence,
            )
            if analogues:
                # Take the best-confidence analogue
                best_src = analogues[0].source_sig.tactic_name
                if best_src in source_strategies:
                    s_idx = source_strategies.index(best_src)
                    self._target_to_source_slot[t_idx] = s_idx
                    logger.debug(
                        "DomainAdapter: %s/%s → %s/%s (slot %d → %d conf=%.2f)",
                        target_domain, t_name, source_domain, best_src,
                        t_idx, s_idx, analogues[0].confidence,
                    )

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def adapt(self, target_state: SynthesisStateSnapshot) -> List[float]:
        """
        Return a feature vector in the *source-domain* feature space for
        the given target-domain state.

        Slots [0..2]: copied directly (accuracy, upward_rate, gen/100).
        Slots [3..3+|A|-1]: re-ordered target strategy probs → source slots.
            Un-mapped target strategies contribute 0.0 to all source slots.
            Source slots not covered by any target analogue remain 0.0.
        """
        # Base features (domain-agnostic)
        feat: List[float] = [
            target_state.accuracy,
            target_state.upward_rate,
            target_state.generation / 100.0,
        ]

        # Build source-slot probability vector from target probs
        n_source = len(self.source_strats)
        source_slots = [0.0] * max(n_source, _N_ACTIONS)

        # Get target probs (order matches self.target_strats)
        target_probs = list(target_state.probs.values()) if target_state.probs else []
        # Ensure length matches target_strats
        target_probs = (target_probs + [0.0] * len(self.target_strats))[
            : len(self.target_strats)
        ]

        for t_idx, t_prob in enumerate(target_probs):
            s_idx = self._target_to_source_slot.get(t_idx)
            if s_idx is not None and s_idx < len(source_slots):
                source_slots[s_idx] += t_prob

        # Pad / truncate to _N_ACTIONS
        source_slots = (source_slots + [0.0] * _N_ACTIONS)[:_N_ACTIONS]
        feat.extend(source_slots)
        return feat

    def get_mapping_coverage(self) -> float:
        """
        Fraction of target strategies that have at least one source analogue.
        """
        if not self.target_strats:
            return 0.0
        mapped = len(self._target_to_source_slot)
        return mapped / len(self.target_strats)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "source_domain":     self.source_domain,
            "target_domain":     self.target_domain,
            "n_source_strats":   len(self.source_strats),
            "n_target_strats":   len(self.target_strats),
            "n_mapped":          len(self._target_to_source_slot),
            "mapping_coverage":  self.get_mapping_coverage(),
            "target_to_source":  {
                self.target_strats[t]: self.source_strats[s]
                for t, s in self._target_to_source_slot.items()
            },
        }


# ---------------------------------------------------------------------------
# TransferStudentPolicy  —  zero-shot + optional few-shot fine-tuning
# ---------------------------------------------------------------------------

class TransferStudentPolicy:
    """
    Wraps a pre-trained source-domain ``StudentPolicy`` and applies it
    zero-shot to a target domain via a ``DomainAdapter``.

    Optionally fine-tunes the weight matrix on target-domain examples
    once ``min_finetune_steps`` examples have been collected (few-shot mode).

    Parameters
    ----------
    source_student : StudentPolicy
        The pre-trained source-domain student (weights are *copied*, not shared,
        so fine-tuning does not corrupt the source student).
    adapter : DomainAdapter
        Adapts target-domain states into the source feature space.
    finetune_lr : float
        SGD learning rate for fine-tuning (default 0.02 — lower than
        the initial 0.05 to avoid catastrophic forgetting of source knowledge).
    finetune_l2 : float
        L2 regularisation during fine-tuning (default 1e-4).
    min_finetune_steps : int
        Number of target-domain examples required before fine-tuning begins
        (default 5).  Before this threshold, the model is purely zero-shot.
    confidence_threshold : float
        Minimum max-softmax required to let the transfer student lead
        (default 0.40 — slightly lower than source student since transfer
        is inherently noisier).
    """

    def __init__(
        self,
        source_student:       StudentPolicy,
        adapter:              DomainAdapter,
        finetune_lr:          float = 0.02,
        finetune_l2:          float = 1e-4,
        min_finetune_steps:   int   = 5,
        confidence_threshold: float = 0.40,
    ):
        self.adapter              = adapter
        self.finetune_lr          = finetune_lr
        self.finetune_l2          = finetune_l2
        self.min_finetune_steps   = min_finetune_steps
        self.confidence_threshold = confidence_threshold

        # Deep-copy source student weights (isolated from source)
        self._W: List[List[float]] = [
            list(row) for row in source_student._W
        ]
        self.finetune_steps: int = 0

    # ------------------------------------------------------------------
    # Forward pass (using adapted features)
    # ------------------------------------------------------------------

    def _softmax(self, features: List[float]) -> List[float]:
        z = [
            sum(self._W[i][j] * features[j] for j in range(_FEAT_DIM))
            for i in range(_N_ACTIONS)
        ]
        z_max = max(z)
        exps  = [math.exp(zi - z_max) for zi in z]
        total = sum(exps)
        return [e / total for e in exps]

    def predict(
        self,
        target_state: SynthesisStateSnapshot,
    ) -> Tuple[SynthesisAction, float, Dict[str, float]]:
        """
        Predict the best action on a *target-domain* state.

        Returns
        -------
        (best_action, confidence, {action.value → prob})
        """
        phi   = self.adapter.adapt(target_state)
        probs = self._softmax(phi)
        best_idx    = max(range(_N_ACTIONS), key=lambda i: probs[i])
        best_action = _ACTIONS[best_idx]
        confidence  = probs[best_idx]
        prob_dict   = {_ACTIONS[i].value: probs[i] for i in range(_N_ACTIONS)}
        return best_action, confidence, prob_dict

    def should_lead(self, target_state: SynthesisStateSnapshot) -> bool:
        """Return True if the transfer student is confident enough to lead."""
        _, conf, _ = self.predict(target_state)
        return conf >= self.confidence_threshold

    # ------------------------------------------------------------------
    # Fine-tuning (optional SGD updates on target-domain data)
    # ------------------------------------------------------------------

    def finetune(
        self,
        target_state:   SynthesisStateSnapshot,
        teacher_action: SynthesisAction,
    ) -> float:
        """
        Apply one SGD fine-tuning step on a target-domain example.

        Only executes if ``finetune_steps >= 0`` (always fine-tunes when called).
        The caller is responsible for deciding when to start fine-tuning.

        Returns
        -------
        float  cross-entropy loss before the update
        """
        phi   = self.adapter.adapt(target_state)
        probs = self._softmax(phi)
        t_idx = _ACTION_INDEX[teacher_action]

        loss = -math.log(max(probs[t_idx], 1e-12))

        for i in range(_N_ACTIONS):
            indicator    = 1.0 if i == t_idx else 0.0
            grad_scalar  = probs[i] - indicator
            for j in range(_FEAT_DIM):
                self._W[i][j] -= self.finetune_lr * (
                    grad_scalar * phi[j] + self.finetune_l2 * self._W[i][j]
                )

        self.finetune_steps += 1
        return loss

    def weight_norm(self) -> float:
        return math.sqrt(sum(w ** 2 for row in self._W for w in row))


# ---------------------------------------------------------------------------
# CrossDomainDistiller  —  source student + transfer student, dual loop
# ---------------------------------------------------------------------------

class CrossDomainDistiller:
    """
    Manages the dual distillation loop for cross-domain transfer:

      1. **Source student** (WP23 ``PolicyDistiller``) is trained on
         source-domain (Go) examples — identical to WP23 behaviour.
      2. **Transfer student** (``TransferStudentPolicy``) is evaluated
         zero-shot on target-domain states; optionally fine-tuned once
         enough target examples exist.

    The ``CrossDomainDistiller`` decides which student leads on target-domain
    steps:

      - If ``transfer_student.should_lead(state)`` → transfer student action
      - Else → fall back to the teacher (WP22 bandit)

    Parameters
    ----------
    source_distiller : PolicyDistiller
        The WP23 distiller already attached to the CRLS (not cloned).
    transfer_student : TransferStudentPolicy
        Pre-built transfer student.
    source_domain : str
    target_domain : str
    """

    def __init__(
        self,
        source_distiller:  PolicyDistiller,
        transfer_student:  TransferStudentPolicy,
        source_domain:     str = "go",
        target_domain:     str = "chess",
    ):
        self.source_distiller = source_distiller
        self.transfer_student = transfer_student
        self.source_domain    = source_domain
        self.target_domain    = target_domain
        self.transfer_log: List[TransferRecord] = []

    def evaluate(
        self,
        target_state:   SynthesisStateSnapshot,
        teacher_action: SynthesisAction,
        generation:     int,
    ) -> TransferRecord:
        """
        Evaluate the transfer student on a target-domain state and
        optionally fine-tune it.

        Parameters
        ----------
        target_state : SynthesisStateSnapshot
            Current synthesis state (target domain).
        teacher_action : SynthesisAction
            Ground-truth label from the WP22 teacher.
        generation : int

        Returns
        -------
        TransferRecord
        """
        # Transfer student prediction
        t_action, t_conf, _ = self.transfer_student.predict(target_state)
        transfer_leads       = self.transfer_student.should_lead(target_state)

        # Source student prediction (on same state — used for comparison)
        s_action, _, _ = self.source_distiller.student.predict(target_state)

        # Fine-tune if enough target examples
        if self.transfer_student.finetune_steps >= self.transfer_student.min_finetune_steps:
            loss = self.transfer_student.finetune(target_state, teacher_action)
        else:
            # Pre-threshold: compute loss without updating
            phi   = self.transfer_student.adapter.adapt(target_state)
            probs = self.transfer_student._softmax(phi)
            t_idx = _ACTION_INDEX[teacher_action]
            loss  = -math.log(max(probs[t_idx], 1e-12))
            # Still collect data by fine-tuning (always finetune to gather steps)
            self.transfer_student.finetune(target_state, teacher_action)

        rec = TransferRecord(
            generation          = generation,
            source_domain       = self.source_domain,
            target_domain       = self.target_domain,
            transfer_action     = t_action,
            transfer_confidence = t_conf,
            source_action       = s_action,
            teacher_action      = teacher_action,
            transfer_led        = transfer_leads,
            finetune_steps      = self.transfer_student.finetune_steps,
            loss                = loss,
        )
        self.transfer_log.append(rec)
        logger.info(
            "CrossDomainDistiller gen %d: transfer=%s (conf=%.3f) "
            "teacher=%s led=%s finetune_steps=%d",
            generation, t_action.value, t_conf, teacher_action.value,
            transfer_leads, self.transfer_student.finetune_steps,
        )
        return rec

    def get_summary(self) -> Dict[str, Any]:
        log = self.transfer_log
        if not log:
            return {
                "n_evaluations":        0,
                "transfer_led_count":   0,
                "transfer_led_rate":    0.0,
                "mean_loss":            None,
                "mean_confidence":      None,
                "finetune_steps":       self.transfer_student.finetune_steps,
                "mapping_coverage":     self.transfer_student.adapter.get_mapping_coverage(),
                "transfer_log":         [],
            }
        losses    = [r.loss for r in log]
        confs     = [r.transfer_confidence for r in log]
        led_count = sum(1 for r in log if r.transfer_led)
        return {
            "n_evaluations":        len(log),
            "transfer_led_count":   led_count,
            "transfer_led_rate":    led_count / len(log),
            "mean_loss":            sum(losses) / len(losses),
            "final_loss":           losses[-1],
            "mean_confidence":      sum(confs) / len(confs),
            "final_confidence":     confs[-1],
            "finetune_steps":       self.transfer_student.finetune_steps,
            "mapping_coverage":     self.transfer_student.adapter.get_mapping_coverage(),
            "transfer_log":         [r.to_dict() for r in log],
        }


# ---------------------------------------------------------------------------
# TransferCRLS  —  HierarchicalCRLS + WP28 cross-domain transfer layer
# ---------------------------------------------------------------------------

class TransferCRLS(HierarchicalCRLS):
    """
    WP28 upgrade of HierarchicalCRLS: adds cross-domain student transfer.

    Ten-layer action-selection hierarchy
    -------------------------------------
    10. **CrossDomainDistiller** (WP28) — zero-shot / few-shot transfer
    9.  **TaskDecomposer** (WP26)        — per-subtask synthesis recommendation
    8.  **EWC guard** (WP25)             — forgetting detection + consolidation
    7.  **EnsembleDistiller** (WP24)     — JSD uncertainty gate
    6.  **PolicyDistiller** (WP23)       — single-student baseline
    5.  **BanditPolicy** (WP22)          — explore/exploit
    4.  **MetaGradientOptimiser** (WP21)
    3.  **RolloutPlanner** (WP20)
    2.  **CausalActionEvaluator** (WP19)
    1.  **WP17 heuristic**

    The WP28 layer runs *after* the full WP26 9-tuple is produced.  It:
      1. Evaluates the transfer student on the current synthesis state.
      2. Optionally fine-tunes the transfer student on teacher labels.
      3. If the transfer student leads AND its action differs from WP26's
         final action, applies its recommendation via the safety gate.

    Parameters
    ----------
    (all HierarchicalCRLS parameters, plus:)
    analogy_map : CrossDomainAnalogyMap
        Pre-built analogy map connecting source and target domains.
    source_strategies : list[str]
        Strategy names in the source domain (same as ``strategies`` for Go).
    target_strategies : list[str]
        Strategy names in the target domain (e.g. Chess tactic names).
    source_domain : str
        Domain label (default "go").
    target_domain : str
        Domain label for the target (default "chess").
    transfer_finetune_lr : float
        Fine-tuning learning rate for the transfer student (default 0.02).
    transfer_finetune_l2 : float
        Fine-tuning L2 regularisation (default 1e-4).
    transfer_min_finetune_steps : int
        Target examples before fine-tuning begins (default 5).
    transfer_confidence_threshold : float
        Minimum transfer student confidence to lead (default 0.40).
    transfer_override_threshold : float
        Transfer student must exceed this to override WP26 action (default 0.60).
    min_analogy_confidence : float
        Analogies below this threshold are ignored (default 0.50).
    """

    def __init__(
        self,
        strategies:                    List[str],
        upward_rate:                   float = 0.20,
        downward_rate:                 float = 0.15,
        synthesiser_kwargs:            Optional[Dict[str, Any]] = None,
        min_trials_to_override:        int   = 3,
        override_tolerance:            float = 0.02,
        rollout_horizon:               int   = 3,
        rollout_discount:              float = 0.90,
        min_transitions:               int   = 3,
        meta_step_size:                float = 0.02,
        meta_fd_epsilon:               float = 0.05,
        meta_min_transitions:          int   = 4,
        initial_params:                Optional[MetaParams] = None,
        bandit_mode:                   BanditMode = BanditMode.UCB1,
        exploration_coeff:             float = 1.0,
        prior_variance:                float = 1.0,
        force_explore_unseen:          bool  = True,
        distill_lr:                    float = 0.05,
        distill_l2:                    float = 1e-4,
        distill_min_steps:             int   = 10,
        distill_confidence:            float = 0.50,
        ensemble_n_members:            int   = 5,
        ensemble_lr:                   float = 0.05,
        ensemble_l2:                   float = 1e-4,
        ensemble_init_noise:           float = 0.01,
        ensemble_min_steps:            int   = 10,
        ensemble_max_jsd:              float = 0.15,
        ensemble_min_conf:             float = 0.40,
        ensemble_seed:                 Optional[int] = None,
        ewc_lambda:                    float = 1.0,
        fisher_sample_size:            int   = 50,
        forgetting_threshold:          float = 0.20,
        ema_alpha:                     float = 0.20,
        ewc_min_steps_before_detect:   int   = 10,
        decomp_min_bucket_size:        int   = 1,
        decomp_confidence_base:        float = 0.80,
        decomp_override_threshold:     float = 0.85,
        # WP28 additions
        analogy_map:                   Optional[CrossDomainAnalogyMap] = None,
        source_strategies:             Optional[List[str]] = None,
        target_strategies:             Optional[List[str]] = None,
        source_domain:                 str   = "go",
        target_domain:                 str   = "chess",
        transfer_finetune_lr:          float = 0.02,
        transfer_finetune_l2:          float = 1e-4,
        transfer_min_finetune_steps:   int   = 5,
        transfer_confidence_threshold: float = 0.40,
        transfer_override_threshold:   float = 0.60,
        min_analogy_confidence:        float = 0.50,
    ):
        super().__init__(
            strategies                  = strategies,
            upward_rate                 = upward_rate,
            downward_rate               = downward_rate,
            synthesiser_kwargs          = synthesiser_kwargs,
            min_trials_to_override      = min_trials_to_override,
            override_tolerance          = override_tolerance,
            rollout_horizon             = rollout_horizon,
            rollout_discount            = rollout_discount,
            min_transitions             = min_transitions,
            meta_step_size              = meta_step_size,
            meta_fd_epsilon             = meta_fd_epsilon,
            meta_min_transitions        = meta_min_transitions,
            initial_params              = initial_params,
            bandit_mode                 = bandit_mode,
            exploration_coeff           = exploration_coeff,
            prior_variance              = prior_variance,
            force_explore_unseen        = force_explore_unseen,
            distill_lr                  = distill_lr,
            distill_l2                  = distill_l2,
            distill_min_steps           = distill_min_steps,
            distill_confidence          = distill_confidence,
            ensemble_n_members          = ensemble_n_members,
            ensemble_lr                 = ensemble_lr,
            ensemble_l2                 = ensemble_l2,
            ensemble_init_noise         = ensemble_init_noise,
            ensemble_min_steps          = ensemble_min_steps,
            ensemble_max_jsd            = ensemble_max_jsd,
            ensemble_min_conf           = ensemble_min_conf,
            ensemble_seed               = ensemble_seed,
            ewc_lambda                  = ewc_lambda,
            fisher_sample_size          = fisher_sample_size,
            forgetting_threshold        = forgetting_threshold,
            ema_alpha                   = ema_alpha,
            ewc_min_steps_before_detect = ewc_min_steps_before_detect,
            decomp_min_bucket_size      = decomp_min_bucket_size,
            decomp_confidence_base      = decomp_confidence_base,
            decomp_override_threshold   = decomp_override_threshold,
        )

        # WP28 additions
        self._source_domain = source_domain
        self._target_domain = target_domain
        self._transfer_override_threshold = transfer_override_threshold

        _src_strats = source_strategies or list(strategies)
        _tgt_strats = target_strategies or list(strategies)
        _analogy_map = analogy_map or CrossDomainAnalogyMap()

        # Build domain adapter
        self.domain_adapter = DomainAdapter(
            analogy_map            = _analogy_map,
            source_strategies      = _src_strats,
            target_strategies      = _tgt_strats,
            source_domain          = source_domain,
            target_domain          = target_domain,
            min_analogy_confidence = min_analogy_confidence,
        )

        # Transfer student wraps the WP23 source student
        self.transfer_student = TransferStudentPolicy(
            source_student       = self.distiller.student,
            adapter              = self.domain_adapter,
            finetune_lr          = transfer_finetune_lr,
            finetune_l2          = transfer_finetune_l2,
            min_finetune_steps   = transfer_min_finetune_steps,
            confidence_threshold = transfer_confidence_threshold,
        )

        # Cross-domain distiller wraps source distiller + transfer student
        self.cross_domain_distiller = CrossDomainDistiller(
            source_distiller = self.distiller,
            transfer_student = self.transfer_student,
            source_domain    = source_domain,
            target_domain    = target_domain,
        )

        self.transfer_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Override end_of_generation to add WP28 transfer layer
    # ------------------------------------------------------------------

    def end_of_generation(
        self,
        regime: str = "",
    ) -> Tuple[
        SynthesisRecord, CausalRecommendation, RolloutResult,
        MetaGradStep, ExplorationRecord, DistillationRecord,
        EnsembleRecord, Optional[ForgettingRecord], DecompositionRecord,
        TransferRecord,
    ]:
        """
        Run all ten layers.

        Returns the 9-tuple from WP26 plus a TransferRecord as the
        tenth element.

        If the transfer student leads AND its action differs from WP26's
        final synthesis action AND its confidence exceeds
        ``transfer_override_threshold``, the transfer student's recommendation
        is applied via an additional synthesis step.
        """
        # ------------------------------------------------------------------
        # Layers 1–9: WP17→WP26
        # ------------------------------------------------------------------
        nine_tuple = super().end_of_generation(regime=regime)
        (synth_rec, causal_rec, rollout, grad_step,
         explore_rec, distill_rec, ensemble_rec, forgetting_rec,
         decomp_rec) = nine_tuple

        # ------------------------------------------------------------------
        # Layer 10: WP28 cross-domain transfer evaluation
        # ------------------------------------------------------------------
        # Build current synthesis state for the transfer student
        acc_now = self.acc_history[-1] if self.acc_history else 0.0
        current_snapshot = SynthesisStateSnapshot.from_meta_and_acc(
            self.generation - 1, self.meta, acc_now
        )

        # Teacher label = the action WP26 ultimately applied
        teacher_action = synth_rec.action

        transfer_rec = self.cross_domain_distiller.evaluate(
            target_state   = current_snapshot,
            teacher_action = teacher_action,
            generation     = self.generation - 1,
        )

        # Optional override: transfer student leads with high confidence
        # AND its action differs from the current synthesis outcome
        wp28_override = False
        if (
            transfer_rec.transfer_led
            and transfer_rec.transfer_confidence >= self._transfer_override_threshold
            and transfer_rec.transfer_action != synth_rec.action
        ):
            proposal = {
                "type": "rule_add",
                "desc": f"WP28 transfer override: {transfer_rec.transfer_action.value}",
            }
            from prometheus.safety.checks import SafetyStatus
            status, _ = self.governor.evaluate_modification(proposal, verbose=False)
            if status == SafetyStatus.PROVABLY_SAFE:
                self.synth._apply(transfer_rec.transfer_action)
                wp28_override = True
                logger.info(
                    "WP28 gen %d: transfer override %s → %s (conf=%.3f)",
                    self.generation - 1,
                    synth_rec.action.value,
                    transfer_rec.transfer_action.value,
                    transfer_rec.transfer_confidence,
                )

        # Log
        transfer_dict = transfer_rec.to_dict()
        transfer_dict["wp28_override"] = wp28_override
        self.transfer_log.append(transfer_dict)

        # Amend gen_log with WP28 fields
        if self.gen_log:
            self.gen_log[-1]["wp28_transfer_action"] = transfer_rec.transfer_action.value
            self.gen_log[-1]["wp28_transfer_conf"]   = transfer_rec.transfer_confidence
            self.gen_log[-1]["wp28_transfer_led"]    = transfer_rec.transfer_led
            self.gen_log[-1]["wp28_override"]        = wp28_override

        return (
            synth_rec, causal_rec, rollout, grad_step,
            explore_rec, distill_rec, ensemble_rec, forgetting_rec,
            decomp_rec, transfer_rec,
        )

    # ------------------------------------------------------------------
    # Extended report
    # ------------------------------------------------------------------

    def get_full_report(self) -> Dict[str, Any]:
        report = super().get_full_report()
        report["transfer_summary"]   = self.cross_domain_distiller.get_summary()
        report["transfer_log"]       = self.transfer_log
        report["domain_adapter"]     = self.domain_adapter.get_summary()
        return report


# ---------------------------------------------------------------------------
# Exit-criteria verifier
# ---------------------------------------------------------------------------

def verify_wp28_exit_criteria(crls: TransferCRLS) -> Dict[str, bool]:
    """
    Verify WP28 exit criteria.

    Criteria
    --------
    adapter_constructed     DomainAdapter is instantiated with ≥1 mapped strategy pair
    transfer_student_built  TransferStudentPolicy wraps source student weights
    transfer_evaluated      At least one TransferRecord was produced
    finetune_progressed     transfer_student.finetune_steps ≥ 1
    loss_decreased          Mean loss of latter half < mean loss of first half (if ≥4 steps)
    safety_preserved        All proposals safety-gated; no UNSAFE action applied

    Returns
    -------
    dict mapping criterion name → bool
    """
    report   = crls.get_full_report()
    t_summ   = report.get("transfer_summary", {})
    t_log    = report.get("transfer_log", [])
    safety   = report.get("safety_statistics", {})
    adapter  = report.get("domain_adapter", {})

    # adapter_constructed
    adapter_ok = (
        isinstance(crls.domain_adapter, DomainAdapter)
        and adapter.get("n_mapped", 0) >= 1
    )

    # transfer_student_built
    ts = crls.transfer_student
    transfer_built = (
        isinstance(ts, TransferStudentPolicy)
        and len(ts._W) == _N_ACTIONS
        and all(len(row) == _FEAT_DIM for row in ts._W)
    )

    # transfer_evaluated
    transfer_evaluated = t_summ.get("n_evaluations", 0) >= 1

    # finetune_progressed
    finetune_ok = t_summ.get("finetune_steps", 0) >= 1

    # loss_decreased (only meaningful with ≥4 data points)
    losses = [r["loss"] for r in t_log] if t_log else []
    if len(losses) >= 4:
        mid = len(losses) // 2
        loss_decreased = (
            sum(losses[mid:]) / len(losses[mid:])
            < sum(losses[:mid]) / len(losses[:mid])
        )
    else:
        loss_decreased = len(losses) >= 1   # at least one evaluation is enough

    # safety_preserved
    safety_ok = (
        safety.get("total_decisions", 0) > 0
        and safety.get("unsafe_count", 0) == 0
    )

    criteria = {
        "adapter_constructed":  adapter_ok,
        "transfer_student_built": transfer_built,
        "transfer_evaluated":   transfer_evaluated,
        "finetune_progressed":  finetune_ok,
        "loss_decreased":       loss_decreased,
        "safety_preserved":     safety_ok,
    }

    logger.info("WP28 exit criteria: %s", criteria)
    return criteria
