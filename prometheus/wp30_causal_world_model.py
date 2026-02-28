"""
WP30: Causal World Model — Latent Transition Learning
======================================================

Closes the **generalisation gap** in WP20's trajectory model.

The gap in WP20
---------------
``SynthesisTrajectoryModel`` (WP20) learns transition statistics as
*per-action sample means*:

    predicted_acc_{t+1} = acc_t + mean_delta(action)

This is tabular: it stores one number per (action, stat) pair and has no
ability to generalise *across states*.  Two problems:

1. **State-blindness**: the model predicts the same accuracy delta for
   DEMOTE_WORST regardless of whether min(probs) is 0.35 (safe) or 0.05
   (near-collapse).  The actual delta in these two situations is very
   different.

2. **Extrapolation failure**: with only 3–10 transitions per action (the
   default), the tabular mean is a high-variance estimator and cannot
   extrapolate to unseen states.

WP30 fix
--------
``LatentTransitionModel`` — a compact multi-layer perceptron (MLP) that
learns the mapping

    (φ(s_t), a_one_hot) → Δs

where:
  - φ(s_t) is the state feature vector (SynthesisStateSnapshot.as_vector())
  - a_one_hot is a 4-dim one-hot vector over SynthesisAction
  - Δs = (Δacc, Δupward_rate, Δprob[0], ..., Δprob[N])

The MLP is trained online via mini-batch SGD: every time a new
``TrajectoryTransition`` is observed, it is appended to a replay buffer
and a mini-batch gradient step is taken.

``WorldModelRollout`` replaces ``RolloutPlanner``'s tabular predictions
with MLP predictions when the replay buffer is large enough (≥ ``min_buffer``).
For shorter horizons or smaller buffers, it falls back to WP20's tabular model.

``WorldModelRecord`` — per-generation audit: predicted vs actual accuracy,
prediction error (MAE), rollout source (neural / tabular / fallback).

``WorldModelCRLS(InvariantCRLS)`` — 11th layer in the stack:
  - Wraps WP27 ``InvariantCRLS`` (which already wraps WP26→WP17)
  - On each generation, updates the replay buffer + takes a gradient step
  - Uses ``WorldModelRollout`` for action selection when possible
  - Falls back gracefully to WP27's action when neural model is untrained
  - Amends gen_log with wp30_* fields
  - Returns 11-tuple (9-tuple from WP26, InvariantRecord, WorldModelRecord)

``verify_wp30_exit_criteria`` — six-criterion verifier.

Theoretical grounding
---------------------
Ha & Schmidhuber (2018) World Models: a compact latent-space transition
model allows "dreaming" (planning in latent space) before acting in the
real environment.  WP30 applies this to the *meta-policy* (synthesis
action selection) rather than the object-level policy.

Sutton & Barto (2018) §8 Dyna-Q: an agent maintains an internal model of
the environment and uses it to generate synthetic experience for planning.
``WorldModelCRLS`` is a meta-level Dyna agent.

Rumelhart, Hinton & Williams (1986) back-propagation: the MLP transition
model is trained end-to-end by gradient descent on one-step prediction error,
providing a differentiable causal world model.

Good (1965): an ultraintelligent machine that *models* its own improvement
dynamics can plan its self-modifications rather than reacting to them.  A
world model of the meta-MDP is a prerequisite for deliberate intelligence
explosion.

Classes
-------
ReplayBuffer            Fixed-capacity ring buffer of TrajectoryTransition
LatentTransitionModel   MLP: (φ(s), a_one_hot) → Δs; online SGD
WorldModelRollout       K-step lookahead using neural model (or tabular fallback)
WorldModelRecord        Per-generation audit: prediction MAE, rollout source
WorldModelCRLS          InvariantCRLS + WP30 neural world model layer
verify_wp30_exit_criteria  Six-criterion verifier
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from prometheus.wp17_crls_synthesis import SynthesisAction, SynthesisRecord
from prometheus.wp20_temporal_planner import (
    SynthesisStateSnapshot,
    SynthesisTrajectoryModel,
    TrajectoryTransition,
)
from prometheus.wp21_meta_gradient import MetaGradStep, MetaParams
from prometheus.wp22_bandit_exploration import BanditMode, ExplorationRecord
from prometheus.wp23_policy_distillation import DistillationRecord
from prometheus.wp24_ensemble_uncertainty import EnsembleRecord
from prometheus.wp25_ewc_forgetting import ForgettingRecord
from prometheus.wp26_hierarchical_decomp import DecompositionRecord, HierarchicalCRLS
from prometheus.wp27_formal_invariants import (
    InvariantCRLS,
    InvariantRecord,
    InvariantRegistry,
)
from prometheus.wp19_causal_evaluator import CausalRecommendation
from prometheus.wp20_temporal_planner import RolloutResult

logger = logging.getLogger(__name__)

# Number of SynthesisAction members
_N_ACTIONS = len(SynthesisAction)
_ACTIONS = list(SynthesisAction)
_ACTION_INDEX = {a: i for i, a in enumerate(_ACTIONS)}


# ---------------------------------------------------------------------------
# ReplayBuffer
# ---------------------------------------------------------------------------

class ReplayBuffer:
    """
    Fixed-capacity ring buffer of ``TrajectoryTransition`` instances.

    When full, new transitions overwrite the oldest (FIFO eviction).

    Parameters
    ----------
    capacity : int
        Maximum number of transitions to store (default 1000).
    """

    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self._buf: List[TrajectoryTransition] = []
        self._pos: int = 0

    def add(self, transition: TrajectoryTransition) -> None:
        if len(self._buf) < self.capacity:
            self._buf.append(transition)
        else:
            self._buf[self._pos] = transition
        self._pos = (self._pos + 1) % self.capacity

    def sample(self, n: int) -> List[TrajectoryTransition]:
        k = min(n, len(self._buf))
        return random.sample(self._buf, k)

    @property
    def size(self) -> int:
        return len(self._buf)

    def __len__(self) -> int:
        return len(self._buf)


# ---------------------------------------------------------------------------
# LatentTransitionModel  —  compact MLP (pure Python, no torch dependency)
# ---------------------------------------------------------------------------

class LatentTransitionModel:
    """
    Two-layer MLP that learns the transition function

        (φ(s_t), a_one_hot) → Δs

    where Δs = (Δacc, Δupward_rate, Δprob_0, ..., Δprob_{N-1}).

    Implemented as a pure-Python MLP (no PyTorch/NumPy dependency) using
    lists-of-lists for weight matrices and manual backprop.  This keeps the
    entire Prometheus package dependency-free while still providing a
    genuine neural generalisation.

    Architecture
    ------------
    Input  dim  = len(φ(s)) + N_ACTIONS   (state features + action one-hot)
    Hidden dim  = hidden_dim               (default 32)
    Output dim  = len(φ(s))               (predicted Δs, same dim as state)

    Activation: tanh in hidden layer; linear output.

    Training
    --------
    Mini-batch SGD with L2 regularisation.  One gradient step per call to
    ``update()``.

    Parameters
    ----------
    state_dim : int
        Dimension of SynthesisStateSnapshot.as_vector().
    hidden_dim : int
        Hidden layer width (default 32).
    lr : float
        Learning rate (default 0.01).
    l2 : float
        L2 weight decay coefficient (default 1e-4).
    seed : int
        Random seed for weight initialisation.
    """

    def __init__(
        self,
        state_dim:  int,
        hidden_dim: int = 32,
        lr:         float = 0.01,
        l2:         float = 1e-4,
        seed:       int   = 0,
    ):
        self.state_dim  = state_dim
        self.hidden_dim = hidden_dim
        self.lr         = lr
        self.l2         = l2
        self._rng       = random.Random(seed)

        input_dim  = state_dim + _N_ACTIONS
        output_dim = state_dim

        # Xavier initialisation
        def _xavier(fan_in: int, fan_out: int) -> List[List[float]]:
            lim = math.sqrt(6.0 / (fan_in + fan_out))
            return [
                [self._rng.uniform(-lim, lim) for _ in range(fan_in)]
                for _ in range(fan_out)
            ]

        # Layer 1: input_dim → hidden_dim
        self.W1: List[List[float]] = _xavier(input_dim,  hidden_dim)
        self.b1: List[float]       = [0.0] * hidden_dim
        # Layer 2: hidden_dim → output_dim
        self.W2: List[List[float]] = _xavier(hidden_dim, output_dim)
        self.b2: List[float]       = [0.0] * output_dim

        self.n_steps:    int   = 0
        self.total_loss: float = 0.0

    # ------------------------------------------------------------------
    # Forward pass
    # ------------------------------------------------------------------

    @staticmethod
    def _matmul_vec(W: List[List[float]], x: List[float]) -> List[float]:
        """y = W @ x  where W[i] is the i-th row."""
        return [sum(W[i][j] * x[j] for j in range(len(x))) for i in range(len(W))]

    @staticmethod
    def _tanh(v: List[float]) -> List[float]:
        return [math.tanh(x) for x in v]

    @staticmethod
    def _tanh_deriv(tanh_out: List[float]) -> List[float]:
        """d tanh / d x = 1 - tanh²(x)"""
        return [1.0 - y * y for y in tanh_out]

    def _forward(
        self,
        phi_s: List[float],
        a_onehot: List[float],
    ) -> Tuple[List[float], List[float], List[float]]:
        """
        Forward pass.
        Returns (delta_pred, h_tanh, pre_act_h).
        """
        x = phi_s + a_onehot
        pre_h = [
            sum(self.W1[i][j] * x[j] for j in range(len(x))) + self.b1[i]
            for i in range(self.hidden_dim)
        ]
        h = self._tanh(pre_h)
        delta = [
            sum(self.W2[i][j] * h[j] for j in range(self.hidden_dim)) + self.b2[i]
            for i in range(self.state_dim)
        ]
        return delta, h, pre_h

    # ------------------------------------------------------------------
    # Predict
    # ------------------------------------------------------------------

    def predict(
        self,
        state: SynthesisStateSnapshot,
        action: SynthesisAction,
    ) -> List[float]:
        """Predict Δs for (state, action)."""
        phi = state.as_vector()
        a_oh = [0.0] * _N_ACTIONS
        a_oh[_ACTION_INDEX[action]] = 1.0
        delta, _, _ = self._forward(phi, a_oh)
        return delta

    def predict_next_accuracy(
        self,
        state: SynthesisStateSnapshot,
        action: SynthesisAction,
    ) -> float:
        """Convenience: return predicted accuracy after applying action."""
        delta = self.predict(state, action)
        # Accuracy is the last element of as_vector()
        return state.accuracy + delta[-1]

    # ------------------------------------------------------------------
    # Update (SGD mini-batch)
    # ------------------------------------------------------------------

    def update(
        self,
        transitions: List[TrajectoryTransition],
    ) -> float:
        """
        One mini-batch SGD step on ``transitions``.

        Returns mean squared error loss on the batch.
        """
        if not transitions:
            return 0.0

        total_loss = 0.0
        # Accumulate gradients
        dW1 = [[0.0] * len(self.W1[0]) for _ in range(self.hidden_dim)]
        db1 = [0.0] * self.hidden_dim
        dW2 = [[0.0] * len(self.W2[0]) for _ in range(self.state_dim)]
        db2 = [0.0] * self.state_dim

        for t in transitions:
            phi    = t.state_before.as_vector()
            phi_nt = t.state_after.as_vector()
            a_oh   = [0.0] * _N_ACTIONS
            a_oh[_ACTION_INDEX[t.action]] = 1.0

            x = phi + a_oh
            delta_pred, h, pre_h = self._forward(phi, a_oh)

            # True delta
            delta_true = [phi_nt[i] - phi[i] for i in range(self.state_dim)]

            # MSE loss contribution
            residuals = [delta_pred[i] - delta_true[i] for i in range(self.state_dim)]
            total_loss += sum(r * r for r in residuals) / self.state_dim

            # Backprop: output layer
            # dL/d(delta_i) = 2*(delta_pred_i - delta_true_i) / state_dim
            grad_out = [2.0 * residuals[i] / self.state_dim for i in range(self.state_dim)]
            for i in range(self.state_dim):
                for j in range(self.hidden_dim):
                    dW2[i][j] += grad_out[i] * h[j]
                db2[i] += grad_out[i]

            # Backprop: hidden layer
            grad_h = [
                sum(self.W2[i][j] * grad_out[i] for i in range(self.state_dim))
                for j in range(self.hidden_dim)
            ]
            dtanh = self._tanh_deriv(h)
            grad_pre = [grad_h[j] * dtanh[j] for j in range(self.hidden_dim)]
            for i in range(self.hidden_dim):
                for j in range(len(x)):
                    dW1[i][j] += grad_pre[i] * x[j]
                db1[i] += grad_pre[i]

        n = len(transitions)
        scale = 1.0 / n

        # Apply gradient + L2
        for i in range(self.state_dim):
            for j in range(self.hidden_dim):
                self.W2[i][j] -= self.lr * (scale * dW2[i][j] + self.l2 * self.W2[i][j])
            self.b2[i] -= self.lr * scale * db2[i]

        for i in range(self.hidden_dim):
            for j in range(len(self.W1[i])):
                self.W1[i][j] -= self.lr * (scale * dW1[i][j] + self.l2 * self.W1[i][j])
            self.b1[i] -= self.lr * scale * db1[i]

        loss = total_loss / n
        self.n_steps += 1
        self.total_loss += loss
        return loss

    @property
    def mean_loss(self) -> float:
        return self.total_loss / max(1, self.n_steps)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "state_dim":  self.state_dim,
            "hidden_dim": self.hidden_dim,
            "lr":         self.lr,
            "l2":         self.l2,
            "n_steps":    self.n_steps,
            "mean_loss":  round(self.mean_loss, 6),
        }


# ---------------------------------------------------------------------------
# WorldModelRollout  —  K-step lookahead using neural model or tabular fallback
# ---------------------------------------------------------------------------

class RolloutSource(Enum):
    NEURAL   = "neural"
    TABULAR  = "tabular"
    FALLBACK = "fallback"


@dataclass
class WorldModelRollout:
    """
    Result of a K-step world-model-guided rollout.

    Attributes
    ----------
    best_action : SynthesisAction
        The action recommended by the rollout.
    predicted_return : float
        Discounted cumulative accuracy gain under the best action.
    horizon : int
        Number of steps simulated.
    source : RolloutSource
        Whether the neural model, WP20 tabular model, or the fallback was used.
    action_values : dict
        Predicted return for each candidate action.
    mae_estimate : float
        Mean absolute error of the model's one-step predictions on the
        replay buffer sample (if neural).
    """
    best_action:      SynthesisAction
    predicted_return: float
    horizon:          int
    source:           RolloutSource
    action_values:    Dict[str, float]
    mae_estimate:     float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "best_action":      self.best_action.value,
            "predicted_return": round(self.predicted_return, 4),
            "horizon":          self.horizon,
            "source":           self.source.value,
            "action_values":    {k: round(v, 4) for k, v in self.action_values.items()},
            "mae_estimate":     round(self.mae_estimate, 6),
        }


# ---------------------------------------------------------------------------
# WorldModelRecord  —  per-generation audit
# ---------------------------------------------------------------------------

@dataclass
class WorldModelRecord:
    """
    Audit record for one WorldModelCRLS generation.

    Attributes
    ----------
    generation : int
    proposed_action : SynthesisAction
        Action recommended by the world model rollout (before invariant check).
    applied_action : SynthesisAction
        Action that was actually applied (may differ after WP27 block).
    predicted_accuracy : float
        The model's one-step accuracy prediction.
    actual_accuracy : float
        Observed accuracy at the next generation (filled in retrospectively
        once available; 0.0 until then).
    prediction_error : float
        |predicted - actual| (computed when actual is known; 0.0 until then).
    rollout : WorldModelRollout
    replay_buffer_size : int
    model_n_steps : int
        Number of SGD steps taken so far.
    model_loss : float
        Loss on this generation's mini-batch update.
    timestamp : float
    """
    generation:         int
    proposed_action:    SynthesisAction
    applied_action:     SynthesisAction
    predicted_accuracy: float
    actual_accuracy:    float
    prediction_error:   float
    rollout:            WorldModelRollout
    replay_buffer_size: int
    model_n_steps:      int
    model_loss:         float
    timestamp:          float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation":         self.generation,
            "proposed_action":    self.proposed_action.value,
            "applied_action":     self.applied_action.value,
            "predicted_accuracy": round(self.predicted_accuracy, 4),
            "actual_accuracy":    round(self.actual_accuracy, 4),
            "prediction_error":   round(self.prediction_error, 4),
            "rollout":            self.rollout.to_dict(),
            "replay_buffer_size": self.replay_buffer_size,
            "model_n_steps":      self.model_n_steps,
            "model_loss":         round(self.model_loss, 6),
        }


# ---------------------------------------------------------------------------
# WorldModelCRLS  —  InvariantCRLS + WP30 neural world model
# ---------------------------------------------------------------------------

class WorldModelCRLS(InvariantCRLS):
    """
    WP30 upgrade of InvariantCRLS: adds a neural causal world model.

    The world model sits **above** all previous layers (WP17–27) and
    uses the neural ``LatentTransitionModel`` to plan K steps ahead when
    the replay buffer is large enough.  When the buffer is too small, it
    falls back to WP20's tabular predictions; when even those are
    unavailable, it defers to whatever action WP27 recommends.

    Parameters
    ----------
    (all InvariantCRLS parameters, plus:)
    wm_hidden_dim : int
        MLP hidden layer width (default 32).
    wm_lr : float
        World model learning rate (default 0.01).
    wm_l2 : float
        World model L2 weight decay (default 1e-4).
    wm_buffer_capacity : int
        Replay buffer capacity (default 1000).
    wm_min_buffer : int
        Minimum replay buffer size before neural rollout is trusted
        (default 10).
    wm_batch_size : int
        Mini-batch size per SGD step (default 8).
    wm_horizon : int
        Rollout horizon K (default 3).
    wm_discount : float
        Discount factor γ for multi-step returns (default 0.90).
    wm_neural_override_threshold : float
        Minimum predicted return advantage over fallback before the neural
        model overrides WP27's action (default 0.01).
    wm_seed : int
        Seed for MLP weight initialisation (default 42).
    """

    def __init__(
        self,
        strategies: List[str],
        # --- pass-through all InvariantCRLS params ---
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
        ewc_lambda:                  float = 1.0,
        fisher_sample_size:          int   = 50,
        forgetting_threshold:        float = 0.20,
        ema_alpha:                   float = 0.20,
        ewc_min_steps_before_detect: int   = 10,
        decomp_min_bucket_size:      int   = 1,
        decomp_confidence_base:      float = 0.80,
        decomp_override_threshold:   float = 0.85,
        invariant_registry:          Optional[InvariantRegistry] = None,
        inv_p_floor:                 float = 0.02,
        inv_h_min:                   float = 0.30,
        inv_rate_max:                float = 1.0,
        inv_delta_max:               float = 0.30,
        inv_fallback:                SynthesisAction = SynthesisAction.RESET_UNIFORM,
        # --- WP30 additions ---
        wm_hidden_dim:               int   = 32,
        wm_lr:                       float = 0.01,
        wm_l2:                       float = 1e-4,
        wm_buffer_capacity:          int   = 1000,
        wm_min_buffer:               int   = 10,
        wm_batch_size:               int   = 8,
        wm_horizon:                  int   = 3,
        wm_discount:                 float = 0.90,
        wm_neural_override_threshold: float = 0.01,
        wm_seed:                     int   = 42,
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
            invariant_registry          = invariant_registry,
            inv_p_floor                 = inv_p_floor,
            inv_h_min                   = inv_h_min,
            inv_rate_max                = inv_rate_max,
            inv_delta_max               = inv_delta_max,
            inv_fallback                = inv_fallback,
        )

        # Compute state_dim from a dummy snapshot
        _dummy_probs = {s: 1.0 / len(strategies) for s in strategies}
        _dummy = SynthesisStateSnapshot(0, _dummy_probs, 0.20, 0.50)
        self._state_dim = len(_dummy.as_vector())

        # WP30 components
        self.wm_min_buffer              = wm_min_buffer
        self.wm_batch_size              = wm_batch_size
        self.wm_horizon                 = wm_horizon
        self.wm_discount                = wm_discount
        self.wm_neural_override_threshold = wm_neural_override_threshold

        self.replay_buffer    = ReplayBuffer(capacity=wm_buffer_capacity)
        self.transition_model = LatentTransitionModel(
            state_dim  = self._state_dim,
            hidden_dim = wm_hidden_dim,
            lr         = wm_lr,
            l2         = wm_l2,
            seed       = wm_seed,
        )
        # WP20 tabular model (fallback)
        self._tabular_model   = SynthesisTrajectoryModel(
            min_transitions  = min_transitions,
        )

        self.wm_log: List[Dict[str, Any]] = []
        self._prev_snapshot: Optional[SynthesisStateSnapshot] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _action_one_hot(self, action: SynthesisAction) -> List[float]:
        oh = [0.0] * _N_ACTIONS
        oh[_ACTION_INDEX[action]] = 1.0
        return oh

    def _neural_rollout(
        self,
        state: SynthesisStateSnapshot,
    ) -> WorldModelRollout:
        """
        K-step neural rollout.  For each candidate first action A,
        simulate K steps using the neural model, computing the discounted
        accuracy gain.
        """
        action_values: Dict[str, float] = {}
        baseline_acc = state.accuracy

        for a in _ACTIONS:
            total_return = 0.0
            cur_state_vec = state.as_vector()
            cur_acc = state.accuracy
            discount = 1.0

            for k in range(self.wm_horizon):
                step_action = a if k == 0 else self._greedy_neural_action(
                    cur_state_vec, cur_acc
                )
                a_oh = [0.0] * _N_ACTIONS
                a_oh[_ACTION_INDEX[step_action]] = 1.0

                # Build a temporary snapshot for prediction
                tmp_probs = {
                    s: max(0.01, cur_state_vec[i])
                    for i, s in enumerate(sorted(state.probs.keys()))
                }
                tmp_snap = SynthesisStateSnapshot(
                    generation  = state.generation + k,
                    probs       = tmp_probs,
                    upward_rate = cur_state_vec[len(state.probs)],
                    accuracy    = cur_acc,
                )
                delta = self.transition_model.predict(tmp_snap, step_action)
                next_acc = cur_acc + delta[-1]
                discount *= self.wm_discount
                total_return += discount * (next_acc - baseline_acc)

                # Propagate state
                next_vec = [cur_state_vec[i] + delta[i] for i in range(self._state_dim)]
                cur_acc = next_acc
                cur_state_vec = next_vec

            action_values[a.value] = total_return

        best_a = max(_ACTIONS, key=lambda a: action_values[a.value])

        # Estimate MAE on a buffer sample
        mae = 0.0
        if self.replay_buffer.size > 0:
            sample = self.replay_buffer.sample(min(16, self.replay_buffer.size))
            errors = []
            for t in sample:
                pred_acc = self.transition_model.predict_next_accuracy(
                    t.state_before, t.action
                )
                errors.append(abs(pred_acc - t.state_after.accuracy))
            mae = sum(errors) / len(errors) if errors else 0.0

        return WorldModelRollout(
            best_action      = best_a,
            predicted_return = action_values[best_a.value],
            horizon          = self.wm_horizon,
            source           = RolloutSource.NEURAL,
            action_values    = action_values,
            mae_estimate     = mae,
        )

    def _greedy_neural_action(
        self,
        state_vec: List[float],
        cur_acc: float,
    ) -> SynthesisAction:
        """One-step greedy action from a state vector (for multi-step rollout)."""
        best_a   = _ACTIONS[0]
        best_acc = -float("inf")
        for a in _ACTIONS:
            # Quick single-step estimate using just the accuracy delta
            tmp_probs = {}
            n_strats = self._state_dim - 2  # probs + upward_rate + accuracy
            for i in range(n_strats):
                tmp_probs[str(i)] = max(0.01, state_vec[i])
            tmp = SynthesisStateSnapshot(0, tmp_probs, state_vec[-2], cur_acc)
            pred = self.transition_model.predict_next_accuracy(tmp, a)
            if pred > best_acc:
                best_acc = pred
                best_a   = a
        return best_a

    def _tabular_rollout(
        self,
        state: SynthesisStateSnapshot,
        fallback_action: SynthesisAction,
    ) -> WorldModelRollout:
        """Fallback: use WP20 tabular model if it has enough data."""
        action_values: Dict[str, float] = {}
        for a in _ACTIONS:
            if self._tabular_model.can_predict(a):
                next_state, _reward = self._tabular_model.predict_one_step(
                    state, a, state.generation
                )
                action_values[a.value] = next_state.accuracy - state.accuracy
            else:
                action_values[a.value] = 0.0

        has_data = any(self._tabular_model.can_predict(a) for a in _ACTIONS)
        if has_data:
            best_a  = max(_ACTIONS, key=lambda a: action_values[a.value])
            source  = RolloutSource.TABULAR
        else:
            best_a  = fallback_action
            source  = RolloutSource.FALLBACK
            action_values[fallback_action.value] = 0.0

        return WorldModelRollout(
            best_action      = best_a,
            predicted_return = action_values[best_a.value],
            horizon          = 1,
            source           = source,
            action_values    = action_values,
            mae_estimate     = 0.0,
        )

    # ------------------------------------------------------------------
    # Override end_of_generation
    # ------------------------------------------------------------------

    def end_of_generation(
        self,
        regime: str = "",
    ) -> Tuple:
        """
        Run all layers 1–10 (WP17→WP27), then apply WP30 neural world model.

        Returns 11-tuple:
            (synth_rec, causal_rec, rollout, grad_step, explore_rec,
             distill_rec, ensemble_rec, forgetting_rec, decomp_rec,
             inv_rec, wm_rec)
        """
        # ------------------------------------------------------------------
        # Layers 1–10: WP17→WP27
        # ------------------------------------------------------------------
        ten_tuple = super().end_of_generation(regime=regime)
        (synth_rec, causal_rec, rollout, grad_step,
         explore_rec, distill_rec, ensemble_rec, forgetting_rec,
         decomp_rec, inv_rec) = ten_tuple

        gen = self.generation - 1
        acc_now = self.acc_history[-1] if self.acc_history else 0.0

        current_snapshot = SynthesisStateSnapshot.from_meta_and_acc(
            gen, self.meta, acc_now
        )

        # ------------------------------------------------------------------
        # Layer 11 (WP30): add transition to replay buffer + update model
        # ------------------------------------------------------------------
        if self._prev_snapshot is not None:
            transition = TrajectoryTransition(
                state_before = self._prev_snapshot,
                action       = synth_rec.action,
                state_after  = current_snapshot,
            )
            self.replay_buffer.add(transition)
            # Also feed WP20 tabular model
            self._tabular_model.ingest(transition)

        # Mini-batch SGD step
        model_loss = 0.0
        if self.replay_buffer.size >= self.wm_batch_size:
            batch      = self.replay_buffer.sample(self.wm_batch_size)
            model_loss = self.transition_model.update(batch)

        # ------------------------------------------------------------------
        # World model rollout for action recommendation
        # ------------------------------------------------------------------
        if self.replay_buffer.size >= self.wm_min_buffer:
            wm_rollout = self._neural_rollout(current_snapshot)
        else:
            wm_rollout = self._tabular_rollout(
                current_snapshot,
                fallback_action = inv_rec.applied_action,
            )

        # Decide whether to accept the neural recommendation
        # (only if it has a clear advantage over the status quo)
        proposed  = wm_rollout.best_action
        advantage = wm_rollout.predicted_return
        if (
            wm_rollout.source == RolloutSource.NEURAL
            and advantage >= self.wm_neural_override_threshold
            and proposed != inv_rec.applied_action
        ):
            applied = proposed
            logger.info(
                "WP30 gen %d: neural world model OVERRIDES WP27 action %s → %s "
                "(predicted_return=%.4f)",
                gen, inv_rec.applied_action.value, proposed.value, advantage,
            )
        else:
            applied = inv_rec.applied_action

        # Predicted accuracy under applied action
        predicted_acc = self.transition_model.predict_next_accuracy(
            current_snapshot, applied
        ) if self.replay_buffer.size >= self.wm_min_buffer else current_snapshot.accuracy

        wm_rec = WorldModelRecord(
            generation         = gen,
            proposed_action    = proposed,
            applied_action     = applied,
            predicted_accuracy = predicted_acc,
            actual_accuracy    = acc_now,   # current; retrospective update below
            prediction_error   = 0.0,       # filled in next generation
            rollout            = wm_rollout,
            replay_buffer_size = self.replay_buffer.size,
            model_n_steps      = self.transition_model.n_steps,
            model_loss         = model_loss,
        )

        # Retrospective: fill in previous record's actual_accuracy + error
        if self.wm_log:
            prev_dict = self.wm_log[-1]
            prev_dict["actual_accuracy"]  = acc_now
            prev_dict["prediction_error"] = abs(
                prev_dict["predicted_accuracy"] - acc_now
            )

        self.wm_log.append(wm_rec.to_dict())
        self._prev_snapshot = current_snapshot

        # Amend gen_log
        if self.gen_log:
            self.gen_log[-1]["wp30_wm_action"]      = proposed.value
            self.gen_log[-1]["wp30_applied"]         = applied.value
            self.gen_log[-1]["wp30_rollout_source"]  = wm_rollout.source.value
            self.gen_log[-1]["wp30_predicted_acc"]   = round(predicted_acc, 4)
            self.gen_log[-1]["wp30_model_loss"]      = round(model_loss, 6)
            self.gen_log[-1]["wp30_buffer_size"]     = self.replay_buffer.size

        return (synth_rec, causal_rec, rollout, grad_step,
                explore_rec, distill_rec, ensemble_rec, forgetting_rec,
                decomp_rec, inv_rec, wm_rec)

    # ------------------------------------------------------------------
    # Extended report
    # ------------------------------------------------------------------

    def get_full_report(self) -> Dict[str, Any]:
        report = super().get_full_report()
        report["world_model_summary"] = self.transition_model.get_summary()
        report["world_model_log"]     = self.wm_log
        report["replay_buffer_size"]  = self.replay_buffer.size
        return report


# ---------------------------------------------------------------------------
# Exit-criteria verifier
# ---------------------------------------------------------------------------

def verify_wp30_exit_criteria(crls: WorldModelCRLS) -> Dict[str, bool]:
    """
    Verify WP30 exit criteria.

    Criteria
    --------
    replay_buffer_populated   Buffer has ≥1 transition
    model_trained             LatentTransitionModel has taken ≥1 SGD step
    rollout_produced          At least one WorldModelRecord was created
    prediction_logged         gen_log entries have wp30_* keys
    neural_or_tabular_used    At least one rollout used NEURAL or TABULAR source
    safety_preserved          Gödelian safety: total_decisions>0, unsafe_count==0
    """
    report   = crls.get_full_report()
    wm_log   = report.get("world_model_log",     [])
    safety   = report.get("safety_statistics",   {})
    gen_log  = report.get("generation_log",      [])

    buffer_ok  = crls.replay_buffer.size >= 1
    trained_ok = crls.transition_model.n_steps >= 1
    rollout_ok = len(wm_log) >= 1

    logged_ok = any("wp30_wm_action" in g for g in gen_log)

    non_fallback_ok = any(
        r.get("rollout", {}).get("source") in ("neural", "tabular")
        for r in wm_log
    )

    safety_ok = (
        safety.get("total_decisions", 0) > 0
        and safety.get("unsafe_count", 0) == 0
    )

    return {
        "replay_buffer_populated": buffer_ok,
        "model_trained":           trained_ok,
        "rollout_produced":        rollout_ok,
        "prediction_logged":       logged_ok,
        "neural_or_tabular_used":  non_fallback_ok,
        "safety_preserved":        safety_ok,
    }
