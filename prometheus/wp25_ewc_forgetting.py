"""
WP25: Forgetting Detection & Elastic Weight Consolidation
==========================================================

Protects the WP23/24 student ensemble from catastrophic forgetting when the
teacher's action distribution shifts, by adding an Elastic Weight
Consolidation (EWC) regularisation term to every SGD update.

The gap in WP23–24
--------------------
Both the WP23 ``StudentPolicy`` and the WP24 ``EnsembleDistiller`` members
train online with SGD + L2 regularisation.  L2 regularises weights toward
**zero** — it has no memory of which weights were important for past tasks.

When the WP22 teacher undergoes a regime shift (e.g., switching from
``PROMOTE_BEST`` to ``RESET_UNIFORM`` after the bandit explores a new arm),
the gradient signal changes sign for the previously dominant class.  SGD
with L2 rapidly overwrites the weights that encoded past behaviour,
producing a sharp *forgetting event*: loss on the previous distribution
spikes even as loss on the new distribution falls.

McCloskey & Cohen (1989) named this *catastrophic interference*.
French (1999) reviewed the field and concluded that any sequential learner
with shared representations is susceptible unless it explicitly protects
previously important parameters.

WP25 fix: Elastic Weight Consolidation
----------------------------------------
Kirkpatrick et al. (2017) proved that the optimal Bayesian continual learner
imposes a Gaussian prior centred on the previous task's MAP solution θ* with
precision equal to the Fisher Information F:

    log p(θ | D_1, D_2) ∝ log p(D_2 | θ) − (λ/2) Σ_i F_i (θ_i − θ*_i)²

The diagonal Fisher F_i ≈ E[(∂ log p(a|s;θ)/∂θ_i)²] measures how much
changing weight i hurts performance on past data.  In our softmax linear
student:

    F_i  ≈  (1/N) Σ_{t=1}^{N}  (∂ log P_student(a_t | s_t; θ) / ∂θ_i)²
         =  (1/N) Σ_t  [(P_a_t(t) − 1)² · φ(s_t)²]_i

where a_t is the teacher label at step t and φ(s_t) is the feature vector.

After a *consolidation checkpoint* (triggered by detecting a distribution
shift), the system:
  1. Estimates the diagonal Fisher from recent training history.
  2. Records θ* = current weights.
  3. Adds the EWC penalty to subsequent SGD updates:
       θ ← θ − η · [ ∇_θ L_CE  +  λ · F ⊙ (θ − θ*) ]

**Forgetting detection** is the trigger.  We maintain a short rolling window
of per-step losses; a *forgetting event* is declared when the current
smoothed loss exceeds the historical minimum by more than
``forgetting_threshold`` nats.  This is a lightweight proxy for the
per-task loss metric used in Chaudhry et al. (2018).

``EWCStudentPolicy`` extends ``StudentPolicy`` with:
  - diagonal Fisher estimation from a training buffer
  - EWC penalty in ``update()``
  - consolidation checkpointing (``consolidate()``)
  - forgetting detection (``detect_forgetting()``)

``EWCEnsembleCRLS`` inherits ``EnsembleCRLS`` and replaces the base
``EnsembleDistiller`` members with ``EWCStudentPolicy`` instances, and wires
the forgetting detector into ``end_of_generation()``.

Layer hierarchy after WP25:

    Layer 8  EWC guard (WP25)  — detects forgetting, triggers consolidation
    Layer 7  EnsembleDistiller (WP24) — ensemble JSD gate
    Layer 6  PolicyDistiller (WP23)   — single-student baseline
    Layer 5  BanditPolicy (WP22)      — explore/exploit
    Layer 4  MetaGradientOptimiser (WP21)
    Layer 3  RolloutPlanner (WP20)
    Layer 2  CausalActionEvaluator (WP19)
    Layer 1  WP17 heuristic

Theoretical grounding
---------------------
Kirkpatrick et al. (2017): "Overcoming catastrophic forgetting in neural
networks" — the original EWC paper.  Diagonal Fisher is shown to be a
computationally tractable importance measure that closely approximates the
full Laplace posterior precision.

McCloskey & Cohen (1989): "Catastrophic interference in connectionist
networks" — foundational characterisation of forgetting in sequential
learners.

Chaudhry et al. (2018): "Riemannian walk for incremental learning" — extends
EWC to multi-task sequences with per-task Fisher accumulation; WP25 uses a
simplified single-checkpoint variant.

Huszár (2018): "Note on the quadratic penalties in elastic weight
consolidation" — clarifies that the EWC penalty is a Laplace approximation
to the previous task's posterior, motivating the Fisher diagonal choice.

Classes
-------
EWCStudentPolicy        StudentPolicy + Fisher estimation + EWC penalty
ForgettingDetector      Rolling-window forgetting event detector
ForgettingRecord        Audit record for one forgetting / consolidation event
EWCEnsembleDistiller    EnsembleDistiller whose members are EWCStudentPolicy
EWCEnsembleCRLS         EnsembleCRLS + WP25 forgetting detection + EWC
verify_wp25_exit_criteria   Six-criterion verifier
"""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

from prometheus.wp17_crls_synthesis import SynthesisAction, SynthesisRecord
from prometheus.wp19_causal_evaluator import CausalRecommendation
from prometheus.wp20_temporal_planner import RolloutResult, SynthesisStateSnapshot
from prometheus.wp21_meta_gradient import MetaGradStep, MetaParams
from prometheus.wp22_bandit_exploration import BanditMode, ExplorationRecord
from prometheus.wp23_policy_distillation import (
    DistillationRecord,
    StudentPolicy,
    _ACTIONS,
    _ACTION_INDEX,
    _FEAT_DIM,
    _N_ACTIONS,
    _extract_features,
)
from prometheus.wp24_ensemble_uncertainty import (
    EnsembleCRLS,
    EnsembleDistiller,
    EnsembleRecord,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ForgettingRecord  —  audit record for one forgetting / consolidation event
# ---------------------------------------------------------------------------

@dataclass
class ForgettingRecord:
    """
    Audit record for a forgetting event and the resulting EWC consolidation.

    Attributes
    ----------
    generation : int
    smoothed_loss : float
        Exponentially smoothed loss at the time of detection.
    historical_min_loss : float
        The best (lowest) smoothed loss seen up to this point.
    forgetting_delta : float
        smoothed_loss − historical_min_loss (> forgetting_threshold → event).
    consolidation_triggered : bool
        Whether a new EWC checkpoint was laid down at this event.
    ewc_lambda : float
        The EWC regularisation coefficient active at this event.
    n_fisher_samples : int
        Number of training samples used to estimate the Fisher diagonal.
    fisher_norm : float
        L2 norm of the Fisher diagonal vector — indicates which parameters
        are most constrained.
    timestamp : float
    """
    generation:               int
    smoothed_loss:            float
    historical_min_loss:      float
    forgetting_delta:         float
    consolidation_triggered:  bool
    ewc_lambda:               float
    n_fisher_samples:         int
    fisher_norm:              float
    timestamp:                float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation":              self.generation,
            "smoothed_loss":           self.smoothed_loss,
            "historical_min_loss":     self.historical_min_loss,
            "forgetting_delta":        self.forgetting_delta,
            "consolidation_triggered": self.consolidation_triggered,
            "ewc_lambda":              self.ewc_lambda,
            "n_fisher_samples":        self.n_fisher_samples,
            "fisher_norm":             self.fisher_norm,
        }


# ---------------------------------------------------------------------------
# EWCStudentPolicy  —  StudentPolicy + Fisher + EWC penalty
# ---------------------------------------------------------------------------

class EWCStudentPolicy(StudentPolicy):
    """
    Online softmax student with Elastic Weight Consolidation.

    Extends ``StudentPolicy`` with:
      - A diagonal Fisher estimate ``_F[action][feature]`` accumulated
        from a rolling training buffer.
      - A weight snapshot ``_theta_star[action][feature]`` taken at the
        last consolidation checkpoint.
      - An EWC penalty added to every ``update()`` call:
          penalty_grad[i][j] = ewc_lambda · F[i][j] · (W[i][j] − θ*[i][j])

    Parameters
    ----------
    learning_rate : float
    l2_reg : float
    ewc_lambda : float
        EWC regularisation strength λ (default 1.0).
        Higher → stronger protection of consolidated weights.
    fisher_sample_size : int
        Number of recent (state, action) pairs used to estimate Fisher
        (default 50).  Kept in a rolling deque; oldest entries are dropped.
    """

    def __init__(
        self,
        learning_rate:      float = 0.05,
        l2_reg:             float = 1e-4,
        ewc_lambda:         float = 1.0,
        fisher_sample_size: int   = 50,
    ):
        super().__init__(learning_rate=learning_rate, l2_reg=l2_reg)
        self.ewc_lambda         = ewc_lambda
        self.fisher_sample_size = fisher_sample_size

        # Diagonal Fisher  F[action_idx][feat_idx]  — starts at zero (no penalty)
        self._F: List[List[float]] = [
            [0.0] * _FEAT_DIM for _ in range(_N_ACTIONS)
        ]
        # Weight snapshot at last consolidation  θ*
        self._theta_star: List[List[float]] = [
            [0.0] * _FEAT_DIM for _ in range(_N_ACTIONS)
        ]
        # Rolling buffer of (phi, teacher_action_idx) for Fisher estimation
        self._buffer: Deque[Tuple[List[float], int]] = deque(
            maxlen=fisher_sample_size
        )
        # Whether a consolidation checkpoint has been set at least once
        self._consolidated: bool = False

    # ------------------------------------------------------------------
    # Override update() to add EWC penalty
    # ------------------------------------------------------------------

    def update(
        self,
        state:          SynthesisStateSnapshot,
        teacher_action: SynthesisAction,
    ) -> float:
        """
        SGD step with cross-entropy + L2 + EWC penalty.

        The EWC term is:
            penalty_grad[i][j] = ewc_lambda · F[i][j] · (W[i][j] − θ*[i][j])

        Returns cross-entropy loss (before update) as in the base class.
        """
        phi   = _extract_features(state)
        probs = self.softmax_probs(phi)
        t_idx = _ACTION_INDEX[teacher_action]

        # Loss for return value
        loss = -math.log(max(probs[t_idx], 1e-12))

        # Gradient of cross-entropy: (P_a − 1{a == teacher}) · φ
        for i in range(_N_ACTIONS):
            indicator   = 1.0 if i == t_idx else 0.0
            ce_grad     = probs[i] - indicator
            for j in range(_FEAT_DIM):
                l2_grad  = self.l2 * self._W[i][j]
                ewc_grad = (self.ewc_lambda * self._F[i][j]
                            * (self._W[i][j] - self._theta_star[i][j])
                            if self._consolidated else 0.0)
                self._W[i][j] -= self.lr * (
                    ce_grad * phi[j] + l2_grad + ewc_grad
                )

        # Store in buffer for Fisher estimation
        self._buffer.append((phi, t_idx))
        self.training_steps += 1
        return loss

    # ------------------------------------------------------------------
    # Fisher estimation
    # ------------------------------------------------------------------

    def estimate_fisher(self) -> None:
        """
        Estimate the diagonal Fisher from the rolling training buffer.

        For softmax cross-entropy:
            F[i][j] ≈ (1/N) Σ_t (P_{a_t}(t) − 1)² · φ(s_t)_j²
                     = (1/N) Σ_t (1 − P_{teacher,t})² · φ_j²

        This is the expected squared gradient of log P under the model's own
        distribution, evaluated at the teacher labels.
        """
        if not self._buffer:
            return

        N = len(self._buffer)
        # Reset Fisher
        self._F = [[0.0] * _FEAT_DIM for _ in range(_N_ACTIONS)]

        for phi, t_idx in self._buffer:
            probs = self.softmax_probs(phi)
            for i in range(_N_ACTIONS):
                indicator  = 1.0 if i == t_idx else 0.0
                grad_sq    = (probs[i] - indicator) ** 2
                for j in range(_FEAT_DIM):
                    self._F[i][j] += grad_sq * phi[j] ** 2

        # Average
        for i in range(_N_ACTIONS):
            for j in range(_FEAT_DIM):
                self._F[i][j] /= N

    # ------------------------------------------------------------------
    # Consolidation checkpoint
    # ------------------------------------------------------------------

    def consolidate(self) -> float:
        """
        Lay down an EWC checkpoint:
          1. Estimate the diagonal Fisher from the current training buffer.
          2. Snapshot the current weights as θ*.

        Returns the Fisher diagonal norm (diagnostic).
        """
        self.estimate_fisher()
        self._theta_star = [list(row) for row in self._W]
        self._consolidated = True
        f_norm = math.sqrt(sum(
            self._F[i][j] ** 2
            for i in range(_N_ACTIONS)
            for j in range(_FEAT_DIM)
        ))
        logger.debug(
            "EWCStudentPolicy.consolidate: fisher_norm=%.4f steps=%d",
            f_norm, self.training_steps,
        )
        return f_norm

    def fisher_norm(self) -> float:
        """L2 norm of the diagonal Fisher vector."""
        return math.sqrt(sum(
            self._F[i][j] ** 2
            for i in range(_N_ACTIONS)
            for j in range(_FEAT_DIM)
        ))

    def is_consolidated(self) -> bool:
        """True after at least one consolidation checkpoint."""
        return self._consolidated


# ---------------------------------------------------------------------------
# ForgettingDetector  —  rolling-window forgetting event detector
# ---------------------------------------------------------------------------

class ForgettingDetector:
    """
    Lightweight online forgetting detector based on smoothed-loss monitoring.

    Maintains an exponentially smoothed loss estimate and tracks the
    historical minimum.  A *forgetting event* is declared when:

        smoothed_loss − historical_min > forgetting_threshold

    Parameters
    ----------
    forgetting_threshold : float
        Loss increase (nats) above the historical minimum that triggers a
        forgetting event (default 0.20).
    ema_alpha : float
        Exponential moving average decay for loss smoothing (default 0.2).
        Lower → more smoothing, slower response; higher → noisier, faster.
    min_steps_before_detect : int
        Minimum training steps before forgetting detection is active
        (default 10).  Prevents spurious events during cold-start.
    """

    def __init__(
        self,
        forgetting_threshold:    float = 0.20,
        ema_alpha:               float = 0.20,
        min_steps_before_detect: int   = 10,
    ):
        self.threshold      = forgetting_threshold
        self.alpha          = ema_alpha
        self.min_steps      = min_steps_before_detect
        self._smoothed_loss: Optional[float] = None
        self._historical_min: float = float("inf")
        self._step: int = 0
        self.forgetting_log: List[Dict[str, Any]] = []

    def update(self, loss: float) -> bool:
        """
        Feed a new loss value and check for forgetting.

        Returns
        -------
        bool
            True if a forgetting event is detected at this step.
        """
        self._step += 1

        # EMA update
        if self._smoothed_loss is None:
            self._smoothed_loss = loss
        else:
            self._smoothed_loss = (
                self.alpha * loss + (1.0 - self.alpha) * self._smoothed_loss
            )

        # Update historical minimum
        if self._smoothed_loss < self._historical_min:
            self._historical_min = self._smoothed_loss

        # Only detect after warm-up
        if self._step < self.min_steps:
            return False

        delta = self._smoothed_loss - self._historical_min
        is_forgetting = delta > self.threshold

        if is_forgetting:
            logger.info(
                "ForgettingDetector: event at step %d — "
                "smoothed=%.4f min=%.4f delta=%.4f > threshold=%.4f",
                self._step, self._smoothed_loss,
                self._historical_min, delta, self.threshold,
            )

        return is_forgetting

    @property
    def smoothed_loss(self) -> Optional[float]:
        return self._smoothed_loss

    @property
    def historical_min(self) -> float:
        return self._historical_min

    def get_summary(self) -> Dict[str, Any]:
        return {
            "steps":            self._step,
            "smoothed_loss":    self._smoothed_loss,
            "historical_min":   self._historical_min,
            "forgetting_delta": (
                (self._smoothed_loss - self._historical_min)
                if self._smoothed_loss is not None else None
            ),
        }


# ---------------------------------------------------------------------------
# EWCEnsembleDistiller  —  EnsembleDistiller with EWCStudentPolicy members
# ---------------------------------------------------------------------------

class EWCEnsembleDistiller(EnsembleDistiller):
    """
    EnsembleDistiller whose members are ``EWCStudentPolicy`` instances.

    Each member has its own ``ForgettingDetector`` and EWC state.
    When ``consolidate_all()`` is called, every member lays down a checkpoint.

    Parameters
    ----------
    (all EnsembleDistiller parameters, plus:)
    ewc_lambda : float
        EWC regularisation strength λ (default 1.0).
    fisher_sample_size : int
        Rolling buffer size for Fisher estimation per member (default 50).
    forgetting_threshold : float
        Smoothed-loss delta that triggers a forgetting event (default 0.20).
    ema_alpha : float
        EMA decay for per-member loss smoothing (default 0.20).
    min_steps_before_detect : int
        Warm-up steps before forgetting detection activates (default 10).
    """

    def __init__(
        self,
        n_members:               int   = 5,
        learning_rate:           float = 0.05,
        l2_reg:                  float = 1e-4,
        init_noise:              float = 0.01,
        min_training_steps:      int   = 10,
        max_jsd_threshold:       float = 0.15,
        min_mean_confidence:     float = 0.40,
        seed:                    Optional[int] = None,
        ewc_lambda:              float = 1.0,
        fisher_sample_size:      int   = 50,
        forgetting_threshold:    float = 0.20,
        ema_alpha:               float = 0.20,
        min_steps_before_detect: int   = 10,
    ):
        # We bypass EnsembleDistiller.__init__'s member creation and do it ourselves
        # so members are EWCStudentPolicy instead of StudentPolicy.
        import random as _random
        # Store base params needed by parent
        self.n_members           = n_members
        self.min_training_steps  = min_training_steps
        self.max_jsd_threshold   = max_jsd_threshold
        self.min_mean_confidence = min_mean_confidence

        rng = _random.Random(seed)

        self.members: List[EWCStudentPolicy] = []
        for _ in range(n_members):
            m = EWCStudentPolicy(
                learning_rate      = learning_rate,
                l2_reg             = l2_reg,
                ewc_lambda         = ewc_lambda,
                fisher_sample_size = fisher_sample_size,
            )
            # Add small random noise for diversity
            for i in range(_N_ACTIONS):
                for j in range(_FEAT_DIM):
                    m._W[i][j] = rng.gauss(0.0, init_noise)
            self.members.append(m)

        self.ensemble_log: List[EnsembleRecord] = []

        # WP25 additions: per-member detectors
        self.detectors: List[ForgettingDetector] = [
            ForgettingDetector(
                forgetting_threshold    = forgetting_threshold,
                ema_alpha               = ema_alpha,
                min_steps_before_detect = min_steps_before_detect,
            )
            for _ in range(n_members)
        ]
        self.ewc_lambda = ewc_lambda

    # ------------------------------------------------------------------
    # Override train_all to feed per-member detectors
    # ------------------------------------------------------------------

    def train_all(
        self,
        state:          SynthesisStateSnapshot,
        teacher_action: SynthesisAction,
    ) -> Tuple[List[float], List[bool]]:
        """
        Update every EWC member; return (losses, forgetting_flags).

        Returns
        -------
        losses : list[float]
            Per-member cross-entropy losses.
        forgetting_flags : list[bool]
            True for members that detected a forgetting event this step.
        """
        losses: List[float]  = []
        flags:  List[bool]   = []
        for m, det in zip(self.members, self.detectors):
            loss = m.update(state, teacher_action)
            losses.append(loss)
            flags.append(det.update(loss))
        return losses, flags

    # ------------------------------------------------------------------
    # Consolidation
    # ------------------------------------------------------------------

    def consolidate_all(self) -> List[float]:
        """
        Lay down EWC checkpoints for all members.

        Returns per-member Fisher norms.
        """
        return [m.consolidate() for m in self.members]

    def n_consolidated(self) -> int:
        """Number of members that have been consolidated at least once."""
        return sum(1 for m in self.members if m.is_consolidated())

    def mean_fisher_norm(self) -> float:
        """Mean diagonal Fisher norm across all members."""
        norms = [m.fisher_norm() for m in self.members]
        return sum(norms) / len(norms) if norms else 0.0

    # ------------------------------------------------------------------
    # Forgetting summary
    # ------------------------------------------------------------------

    def forgetting_summary(self) -> Dict[str, Any]:
        return {
            "n_members":          self.n_members,
            "n_consolidated":     self.n_consolidated(),
            "ewc_lambda":         self.ewc_lambda,
            "mean_fisher_norm":   self.mean_fisher_norm(),
            "member_steps":       [m.training_steps for m in self.members],
            "detectors":          [d.get_summary() for d in self.detectors],
        }


# ---------------------------------------------------------------------------
# EWCEnsembleCRLS  —  EnsembleCRLS + WP25 forgetting detection + EWC
# ---------------------------------------------------------------------------

class EWCEnsembleCRLS(EnsembleCRLS):
    """
    WP25 upgrade of EnsembleCRLS: replaces the ensemble members with
    EWC-regularised students and wires a forgetting detector into the
    generation loop.

    Eight-layer action-selection hierarchy
    ----------------------------------------
    8. **EWC guard** (WP25)         — detects forgetting; triggers consolidation
    7. **EnsembleDistiller** (WP24) — ensemble JSD gate
    6. **PolicyDistiller** (WP23)   — single-student baseline
    5. **BanditPolicy** (WP22)      — explore/exploit
    4. **MetaGradientOptimiser** (WP21)
    3. **RolloutPlanner** (WP20)
    2. **CausalActionEvaluator** (WP19)
    1. **WP17 heuristic**

    When a forgetting event is detected in any ensemble member, the system:
      1. Consolidates *all* members (new EWC checkpoint).
      2. Appends a ``ForgettingRecord`` to ``forgetting_log``.

    If no forgetting is detected, EWC still runs (consolidated weights act
    as a soft prior) but no new checkpoint is laid.

    Parameters
    ----------
    (all EnsembleCRLS parameters, plus:)
    ewc_lambda : float
        EWC regularisation strength λ (default 1.0).
    fisher_sample_size : int
        Rolling buffer size for Fisher estimation (default 50).
    forgetting_threshold : float
        Smoothed-loss delta that triggers a forgetting event (default 0.20).
    ema_alpha : float
        EMA decay for per-member loss smoothing (default 0.20).
    ewc_min_steps_before_detect : int
        Warm-up steps before forgetting detection activates (default 10).
    """

    def __init__(
        self,
        strategies:                  List[str],
        upward_rate:                 float = 0.20,
        downward_rate:               float = 0.15,
        synthesiser_kwargs:          Optional[Dict[str, Any]] = None,
        min_trials_to_override:      int   = 3,
        override_tolerance:          float = 0.02,
        rollout_horizon:             int   = 3,
        rollout_discount:            float = 0.90,
        min_transitions:             int   = 3,
        meta_step_size:              float = 0.02,
        meta_fd_epsilon:             float = 0.05,
        meta_min_transitions:        int   = 4,
        initial_params:              Optional[MetaParams] = None,
        bandit_mode:                 BanditMode = BanditMode.UCB1,
        exploration_coeff:           float = 1.0,
        prior_variance:              float = 1.0,
        force_explore_unseen:        bool  = True,
        distill_lr:                  float = 0.05,
        distill_l2:                  float = 1e-4,
        distill_min_steps:           int   = 10,
        distill_confidence:          float = 0.50,
        ensemble_n_members:          int   = 5,
        ensemble_lr:                 float = 0.05,
        ensemble_l2:                 float = 1e-4,
        ensemble_init_noise:         float = 0.01,
        ensemble_min_steps:          int   = 10,
        ensemble_max_jsd:            float = 0.15,
        ensemble_min_conf:           float = 0.40,
        ensemble_seed:               Optional[int] = None,
        # WP25 additions
        ewc_lambda:                  float = 1.0,
        fisher_sample_size:          int   = 50,
        forgetting_threshold:        float = 0.20,
        ema_alpha:                   float = 0.20,
        ewc_min_steps_before_detect: int   = 10,
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
            ensemble_n_members     = ensemble_n_members,
            ensemble_lr            = ensemble_lr,
            ensemble_l2            = ensemble_l2,
            ensemble_init_noise    = ensemble_init_noise,
            ensemble_min_steps     = ensemble_min_steps,
            ensemble_max_jsd       = ensemble_max_jsd,
            ensemble_min_conf      = ensemble_min_conf,
            ensemble_seed          = ensemble_seed,
        )

        # WP25: replace the EnsembleDistiller with an EWC-aware one
        self.ensemble = EWCEnsembleDistiller(
            n_members               = ensemble_n_members,
            learning_rate           = ensemble_lr,
            l2_reg                  = ensemble_l2,
            init_noise              = ensemble_init_noise,
            min_training_steps      = ensemble_min_steps,
            max_jsd_threshold       = ensemble_max_jsd,
            min_mean_confidence     = ensemble_min_conf,
            seed                    = ensemble_seed,
            ewc_lambda              = ewc_lambda,
            fisher_sample_size      = fisher_sample_size,
            forgetting_threshold    = forgetting_threshold,
            ema_alpha               = ema_alpha,
            min_steps_before_detect = ewc_min_steps_before_detect,
        )
        self.forgetting_log: List[Dict[str, Any]] = []
        self._ewc_lambda          = ewc_lambda
        self._forgetting_threshold = forgetting_threshold

    # ------------------------------------------------------------------
    # Override end_of_generation to add EWC layer
    # ------------------------------------------------------------------

    def end_of_generation(
        self,
        regime: str = "",
    ) -> Tuple[SynthesisRecord, CausalRecommendation, RolloutResult,
               MetaGradStep, ExplorationRecord, DistillationRecord,
               EnsembleRecord, Optional[ForgettingRecord]]:
        """
        Run synthesis with all eight layers.

        The EWC guard fires *after* the ensemble makes its decision:
          - Train the WP24 ensemble (EWC members).
          - If any member detects a forgetting event → consolidate all.
          - Record in ForgettingRecord.

        Returns
        -------
        (SynthesisRecord, CausalRecommendation, RolloutResult,
         MetaGradStep, ExplorationRecord, DistillationRecord,
         EnsembleRecord, ForgettingRecord or None)
        """
        # ----------------------------------------------------------------
        # Layers 1–5: WP17→WP22 (same as EnsembleCRLS)
        # ----------------------------------------------------------------
        acc_now  = self.acc_history[-1]
        acc_prev = self.acc_history[-2] if len(self.acc_history) >= 2 else None

        heuristic_action, heuristic_trigger = self.synth._choose_action(
            acc_now, acc_prev, self.metacog.get_pattern_summary()
        )
        causal_rec = self.evaluator.recommend(heuristic_action, heuristic_trigger)
        current_snapshot = SynthesisStateSnapshot.from_meta_and_acc(
            self.generation, self.meta, acc_now
        )
        rollout = self.planner.plan(
            current_state    = current_snapshot,
            heuristic_action = causal_rec.action,
        )
        self.meta_params, grad_step = self.meta_opt.step(
            state       = current_snapshot,
            best_action = rollout.best_action,
            params      = self.meta_params,
            generation  = self.generation,
        )
        self._apply_meta_params()

        exploit_action = rollout.best_action
        bandit_rec = self.bandit.select(
            exploit_action = exploit_action,
            generation     = self.generation,
        )
        teacher_action = bandit_rec.explore_action

        # ----------------------------------------------------------------
        # Layer 6: WP23 single student
        # ----------------------------------------------------------------
        student_leads = self.distiller.should_lead(current_snapshot)
        wp23_action = (
            self.distiller.student.predict(current_snapshot)[0]
            if student_leads else teacher_action
        )

        # ----------------------------------------------------------------
        # Layer 7: WP24 ensemble decision
        # ----------------------------------------------------------------
        ensemble_leads = self.ensemble.should_lead(current_snapshot)
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
                f"ensemble={final_action.value} teacher={teacher_action.value}; "
                f"ewc_lambda={self._ewc_lambda} "
                f"fisher_norm={self.ensemble.mean_fisher_norm():.4f}"
            )
        elif student_leads:
            final_action = wp23_action
            chosen_trigger = (
                f"[distilled STUDENT wp23] "
                f"jsd={ensemble_rec.jsd:.4f} [ensemble not ready]"
            )
        else:
            final_action = teacher_action
            chosen_trigger = (
                f"[bandit {self.bandit.mode.value}] "
                f"jsd={ensemble_rec.jsd:.4f} ewc_lambda={self._ewc_lambda}"
            )

        # ----------------------------------------------------------------
        # Apply action through safety gate
        # ----------------------------------------------------------------
        record = self._synthesise_with_action(
            final_action, chosen_trigger, acc_now, acc_prev
        )

        # ----------------------------------------------------------------
        # Layer 8: WP25 — train EWC ensemble; detect forgetting
        # ----------------------------------------------------------------
        # Train WP23 single student
        distill_rec = self.distiller.train(
            state          = current_snapshot,
            teacher_action = teacher_action,
            generation     = self.generation,
            student_led    = student_leads and not ensemble_leads,
        )

        # Train WP24/25 EWC ensemble members; collect forgetting flags
        losses, forgetting_flags = self.ensemble.train_all(
            current_snapshot, teacher_action
        )

        # Check if any member detected forgetting
        any_forgetting = any(forgetting_flags)
        forgetting_rec: Optional[ForgettingRecord] = None

        if any_forgetting:
            fisher_norms = self.ensemble.consolidate_all()
            mean_fn      = sum(fisher_norms) / len(fisher_norms)
            det           = self.ensemble.detectors[0]  # representative
            forgetting_rec = ForgettingRecord(
                generation              = self.generation,
                smoothed_loss           = det.smoothed_loss or 0.0,
                historical_min_loss     = det.historical_min,
                forgetting_delta        = (
                    (det.smoothed_loss or 0.0) - det.historical_min
                ),
                consolidation_triggered = True,
                ewc_lambda              = self._ewc_lambda,
                n_fisher_samples        = min(
                    self.ensemble.members[0].fisher_sample_size,
                    self.ensemble.members[0].training_steps,
                ),
                fisher_norm             = mean_fn,
            )
            self.forgetting_log.append(forgetting_rec.to_dict())
            logger.info(
                "WP25 gen %d: forgetting detected → EWC consolidation; "
                "fisher_norm=%.4f lambda=%.2f",
                self.generation, mean_fn, self._ewc_lambda,
            )

        # ----------------------------------------------------------------
        # Housekeeping
        # ----------------------------------------------------------------
        self._pending_exploration       = bandit_rec
        self._pending_transition_record = record

        self._log_pending_transition_record(record)
        self.meta_grad_log.append(grad_step.to_dict())
        self.bandit_log.append(bandit_rec.to_dict())
        self.distillation_log.append(distill_rec.to_dict())
        self.ensemble_log.append(ensemble_rec.to_dict())

        self.gen_log.append({
            "generation":         self.generation,
            "regime":             regime,
            "acc":                acc_now,
            "heuristic":          heuristic_action.value,
            "causal_action":      causal_rec.action.value,
            "rollout_action":     rollout.best_action.value,
            "rollout_fallback":   rollout.fallback_used,
            "override":           causal_rec.override,
            "ate":                causal_rec.ate_estimate.ate if causal_rec.ate_estimate else None,
            "expected_return":    rollout.expected_return,
            "bandit_action":      teacher_action.value,
            "bandit_explore":     bandit_rec.is_exploration,
            "student_led":        student_leads and not ensemble_leads,
            "student_action":     distill_rec.student_action.value,
            "distill_conf":       distill_rec.confidence,
            "distill_loss":       distill_rec.loss,
            "ensemble_led":       ensemble_leads,
            "ensemble_action":    ensemble_rec.ensemble_action.value,
            "ensemble_jsd":       ensemble_rec.jsd,
            "ensemble_entropy":   ensemble_rec.mean_entropy,
            "ewc_forgetting":     any_forgetting,
            "ewc_fisher_norm":    self.ensemble.mean_fisher_norm(),
            "ewc_consolidated":   self.ensemble.n_consolidated(),
            "safety":             record.safety_status,
        })
        self.rollout_log.append(rollout.to_dict())

        self.generation += 1
        return (record, causal_rec, rollout, grad_step,
                bandit_rec, distill_rec, ensemble_rec, forgetting_rec)

    # ------------------------------------------------------------------
    # Extended report
    # ------------------------------------------------------------------

    def get_full_report(self) -> Dict[str, Any]:
        report = super().get_full_report()
        report["ewc_summary"]     = self.ensemble.forgetting_summary()
        report["forgetting_log"]  = self.forgetting_log
        return report


# ---------------------------------------------------------------------------
# Exit-criteria verifier
# ---------------------------------------------------------------------------

def verify_wp25_exit_criteria(crls: EWCEnsembleCRLS) -> Dict[str, bool]:
    """
    Verify WP25 exit criteria.

    Criteria
    --------
    ewc_members_constructed     All ensemble members are EWCStudentPolicy
    ewc_penalty_active          At least one member has been consolidated
    forgetting_detected         At least one forgetting event was recorded
    consolidation_triggered     EWC checkpoint was laid after a forgetting event
    fisher_norm_positive        Consolidated members have non-zero Fisher norm
    safety_preserved            All proposals safety-gated; no UNSAFE action applied

    Returns
    -------
    dict mapping criterion name → bool
    """
    report = crls.get_full_report()
    esumm  = report["ewc_summary"]
    safety = report["safety_statistics"]
    flog   = report["forgetting_log"]

    # --- ewc_members_constructed ---
    ewc_ok = all(isinstance(m, EWCStudentPolicy) for m in crls.ensemble.members)

    # --- ewc_penalty_active ---
    penalty_active = esumm.get("n_consolidated", 0) > 0

    # --- forgetting_detected ---
    forgetting_detected = len(flog) > 0

    # --- consolidation_triggered ---
    consolidation_triggered = any(r.get("consolidation_triggered", False) for r in flog)

    # --- fisher_norm_positive ---
    fisher_positive = esumm.get("mean_fisher_norm", 0.0) > 0.0

    # --- safety_preserved ---
    safety_preserved = (
        safety["total_decisions"] > 0
        and safety.get("unsafe_decisions", 0) == 0
    )

    criteria = {
        "ewc_members_constructed":  ewc_ok,
        "ewc_penalty_active":       penalty_active,
        "forgetting_detected":      forgetting_detected,
        "consolidation_triggered":  consolidation_triggered,
        "fisher_norm_positive":     fisher_positive,
        "safety_preserved":         safety_preserved,
    }

    logger.info("WP25 exit criteria: %s", criteria)
    return criteria
