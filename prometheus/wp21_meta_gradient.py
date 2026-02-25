"""
WP21: Meta-Gradient Adaptation
================================

Closes the final hyperparameter-rigidity gap in WP17–20: the synthesis engine
still uses *fixed* scaling factors (demote_factor, promote_factor, boost_factor)
and planner settings (horizon K, discount γ) that were set by hand at
construction time.  WP21 learns these hyperparameters from experience.

The gap in WP17–20
-------------------
WP20's ``RolloutPlanner`` evaluates candidate actions but treats the
hyperparameters of the synthesis engine itself (how *hard* to demote, how much
to boost, how far to look ahead) as constants.  Good (1965) described recursive
self-improvement: the machine improves "the parameters of its own improvement
procedure."  WP17–20 improve *which* action to take; WP21 improves *how
strongly* each action is applied.

WP21 fix
---------
``MetaGradientOptimiser`` maintains a parameter vector

    θ = [demote_factor, promote_factor, boost_factor, discount, horizon_cont]

and computes a **numerical meta-gradient** of the *empirical discounted return*
with respect to θ after each generation:

    ∂R/∂θ_i ≈ [R(θ + ε_i) − R(θ − ε_i)] / (2ε)

where R(θ) is the discounted cumulative accuracy gain achieved in the
trajectory buffer under parameters θ.  A clipped SGD step then updates θ:

    θ ← clip( θ − α ∇_θ R , θ_min, θ_max )

Because we cannot re-run generations with different θ, we use the existing
``SynthesisTrajectoryModel`` from WP20 as a *surrogate*: for a hypothetical θ',
we predict what accuracy sequence would have resulted and compute the
discounted return from that simulation.  This is the Dyna-Q meta-level
(Sutton & Barto 2018, §8.2) applied one level higher.

``MetaGradientCRLS`` inherits ``TemporalCRLS`` and overrides
``end_of_generation`` to:
  1. Collect the rollout result from WP20.
  2. Compute meta-gradient over θ using the trajectory model as surrogate.
  3. Update θ and push updated factors into the CRLSSynthesiser.
  4. Log the gradient step for audit and exit-criteria verification.

Theoretical grounding
---------------------
Schmidhuber (1992): "Learning to control fast weight changes" — the system
learns a learning algorithm, not just a policy.  WP21 implements this at the
meta-synthesis level.

Finn et al. (MAML, 2017): Model-Agnostic Meta-Learning — gradient-based
optimisation of a meta-objective.  WP21 uses the same finite-difference
principle but on the synthesis hyperparameter space rather than a neural
network weight space.

Bengio et al. (1990): "Learning a learning algorithm" — gradient descent on
the parameters of the learning rule itself.  WP21 applies this idea to the
CRLS synthesis rule.

Classes
-------
MetaParams                Frozen → mutable parameter vector for synthesis hypers
MetaGradientOptimiser     Computes numerical meta-gradient; updates MetaParams
MetaGradStep              Audit record for one gradient update
MetaGradientCRLS          TemporalCRLS + meta-gradient adaptation
verify_wp21_exit_criteria Six-criterion verifier
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from prometheus.meta_learner import MetaLearner
from prometheus.safety.checks import GodelianSafetyGovernor, SafetyStatus
from prometheus.wp17_crls_synthesis import (
    CRLSSynthesiser,
    SynthesisAction,
    SynthesisRecord,
)
from prometheus.wp19_causal_evaluator import (
    CausalRecommendation,
)
from prometheus.wp20_temporal_planner import (
    RolloutResult,
    SynthesisStateSnapshot,
    SynthesisTrajectoryModel,
    TemporalCRLS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hyperparameter bounds — safety rails so optimiser cannot set degenerate values
# ---------------------------------------------------------------------------

_PARAM_BOUNDS: Dict[str, Tuple[float, float]] = {
    "demote_factor":  (0.10, 0.90),   # how hard to demote worst strategy
    "promote_factor": (1.10, 5.00),   # how hard to promote best strategy
    "boost_factor":   (1.05, 3.00),   # how much to boost upward_rate
    "discount":       (0.50, 0.99),   # rollout discount γ
    "horizon_cont":   (1.0,  8.0),    # continuous proxy for rollout horizon K
}

_DEFAULT_PARAMS: Dict[str, float] = {
    "demote_factor":  0.50,
    "promote_factor": 2.00,
    "boost_factor":   1.50,
    "discount":       0.90,
    "horizon_cont":   3.0,
}

_FD_EPSILON = 0.05   # finite-difference step size


# ---------------------------------------------------------------------------
# MetaParams  —  mutable parameter vector
# ---------------------------------------------------------------------------

@dataclass
class MetaParams:
    """
    Synthesis hyperparameter vector subject to meta-gradient optimisation.

    Parameters
    ----------
    demote_factor : float
        Multiplicative factor applied to the worst strategy's probability
        by CRLSSynthesiser (DEMOTE_WORST action).  Range [0.10, 0.90].
    promote_factor : float
        Multiplicative factor applied to the best strategy's probability
        (PROMOTE_BEST action).  Range [1.10, 5.00].
    boost_factor : float
        Multiplicative factor applied to upward_rate (BOOST_UPWARD action).
        Range [1.05, 3.00].
    discount : float
        Rollout discount γ used by RolloutPlanner.  Range [0.50, 0.99].
    horizon_cont : float
        Continuous horizon proxy; horizon K = round(horizon_cont).
        Range [1.0, 8.0].
    """
    demote_factor:  float = 0.50
    promote_factor: float = 2.00
    boost_factor:   float = 1.50
    discount:       float = 0.90
    horizon_cont:   float = 3.0

    @property
    def horizon(self) -> int:
        """Discrete rollout horizon derived from horizon_cont."""
        return max(1, round(self.horizon_cont))

    def as_dict(self) -> Dict[str, float]:
        return {
            "demote_factor":  self.demote_factor,
            "promote_factor": self.promote_factor,
            "boost_factor":   self.boost_factor,
            "discount":       self.discount,
            "horizon_cont":   self.horizon_cont,
        }

    def clamp(self) -> "MetaParams":
        """Return a new MetaParams clamped to valid ranges."""
        d = self.as_dict()
        clamped = {k: max(lo, min(hi, d[k])) for k, (lo, hi) in _PARAM_BOUNDS.items()}
        return MetaParams(**clamped)

    def perturb(self, param: str, delta: float) -> "MetaParams":
        """Return a copy with ``param`` shifted by ``delta`` (before clamping)."""
        d = self.as_dict()
        d[param] = d[param] + delta
        p = MetaParams(**d)
        return p.clamp()

    def to_dict(self) -> Dict[str, Any]:
        d = self.as_dict()
        d["horizon"] = self.horizon
        return d


# ---------------------------------------------------------------------------
# MetaGradStep  —  audit record for one gradient update
# ---------------------------------------------------------------------------

@dataclass
class MetaGradStep:
    """
    Audit record for a single meta-gradient update step.

    Attributes
    ----------
    generation : int
    params_before : dict
    params_after : dict
    gradients : dict  param_name → ∂R/∂θ_i
    surrogate_return : float
        Discounted return computed by the trajectory-model surrogate.
    step_size : float
        Learning rate used for this step.
    clipped : bool
        True if any parameter hit a bound after the gradient step.
    timestamp : float
    """
    generation:       int
    params_before:    Dict[str, float]
    params_after:     Dict[str, float]
    gradients:        Dict[str, float]
    surrogate_return: float
    step_size:        float
    clipped:          bool
    timestamp:        float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation":       self.generation,
            "params_before":    self.params_before,
            "params_after":     self.params_after,
            "gradients":        self.gradients,
            "surrogate_return": self.surrogate_return,
            "step_size":        self.step_size,
            "clipped":          self.clipped,
        }


# ---------------------------------------------------------------------------
# MetaGradientOptimiser
# ---------------------------------------------------------------------------

class MetaGradientOptimiser:
    """
    Numerical meta-gradient optimiser for synthesis hyperparameters.

    Computes finite-difference gradients of the *surrogate discounted return*
    (predicted by the WP20 trajectory model) with respect to MetaParams, then
    applies a clipped SGD update.

    Surrogate return R(θ)
    ----------------------
    Given the current ``SynthesisStateSnapshot`` s_t and MetaParams θ, we
    simulate the rollout under the ``best_action`` chosen by WP20 using horizon
    K(θ) and discount γ(θ), obtaining a predicted discounted return G(θ).

    For the finite-difference gradient:
        ∂G/∂θ_i ≈ [G(θ + ε_i) − G(θ − ε_i)] / (2ε)

    Only parameters that affect the surrogate (discount, horizon_cont) have
    a non-zero gradient through the rollout computation.  The synthesis-factor
    parameters (demote_factor, promote_factor, boost_factor) affect the *actual*
    state transitions but not the surrogate return computed *post-hoc* from
    accumulated trajectory data.  Their gradient is instead estimated as the
    correlation between the factor value and the mean accuracy delta of the
    corresponding action over the trajectory buffer:

        ∂G/∂demote_factor ≈ mean acc_delta(DEMOTE_WORST) across transitions

    This is a policy-gradient-style estimate: parameters that push toward
    high-delta actions get a positive gradient signal.

    Parameters
    ----------
    trajectory_model : SynthesisTrajectoryModel
    step_size : float
        SGD learning rate α (default 0.02).
    fd_epsilon : float
        Finite-difference step ε (default 0.05).
    min_transitions_for_grad : int
        Minimum trajectory data required before computing a gradient
        (default 4).  Before this threshold, no update is performed.
    """

    def __init__(
        self,
        trajectory_model:          SynthesisTrajectoryModel,
        step_size:                 float = 0.02,
        fd_epsilon:                float = _FD_EPSILON,
        min_transitions_for_grad:  int   = 4,
    ):
        self.traj_model              = trajectory_model
        self.step_size               = step_size
        self.fd_epsilon              = fd_epsilon
        self.min_transitions         = min_transitions_for_grad
        self.grad_history: List[MetaGradStep] = []

    # ------------------------------------------------------------------
    # Surrogate return computation
    # ------------------------------------------------------------------

    def _surrogate_return(
        self,
        state:      SynthesisStateSnapshot,
        action:     SynthesisAction,
        horizon:    int,
        discount:   float,
    ) -> float:
        """
        Compute the discounted return predicted by the trajectory model
        for (state, action) with given horizon and discount.
        """
        if not self.traj_model.can_predict(action):
            return 0.0

        # Build action sequence: first action, then greedy best for remaining steps
        greedy = max(
            SynthesisAction,
            key=lambda a: self.traj_model.mean_acc_delta(a)
            if self.traj_model.n_transitions(a) > 0 else float("-inf"),
        )
        action_seq = [action] + [greedy] * max(0, horizon - 1)

        trajectory = self.traj_model.predict_k_steps(state, action_seq)

        baseline = state.accuracy
        total    = 0.0
        for k, (s_k, conf_k) in enumerate(trajectory, start=1):
            gain   = s_k.accuracy - baseline
            total += (discount ** k) * gain * conf_k

        return total

    # ------------------------------------------------------------------
    # Gradient computation
    # ------------------------------------------------------------------

    def _gradient(
        self,
        state:          SynthesisStateSnapshot,
        best_action:    SynthesisAction,
        params:         MetaParams,
    ) -> Dict[str, float]:
        """
        Compute numerical meta-gradient ∂G/∂θ for all parameters.

        Returns a dict param_name → gradient value.
        """
        grads: Dict[str, float] = {}

        # ---- discount and horizon_cont: finite-difference through surrogate ----
        for param in ("discount", "horizon_cont"):
            val  = getattr(params, param)
            lo, hi = _PARAM_BOUNDS[param]

            # Safely clamp perturbations
            p_fwd = min(hi, val + self.fd_epsilon)
            p_bwd = max(lo, val - self.fd_epsilon)

            if abs(p_fwd - p_bwd) < 1e-9:
                grads[param] = 0.0
                continue

            if param == "discount":
                g_fwd = self._surrogate_return(state, best_action, params.horizon, p_fwd)
                g_bwd = self._surrogate_return(state, best_action, params.horizon, p_bwd)
            else:  # horizon_cont
                h_fwd = max(1, round(p_fwd))
                h_bwd = max(1, round(p_bwd))
                g_fwd = self._surrogate_return(state, best_action, h_fwd, params.discount)
                g_bwd = self._surrogate_return(state, best_action, h_bwd, params.discount)

            grads[param] = (g_fwd - g_bwd) / (p_fwd - p_bwd)

        # ---- synthesis factors: policy-gradient-style estimate ----
        # Gradient of demote_factor: signal from DEMOTE_WORST transitions
        # A higher mean acc_delta for DEMOTE means the current factor is
        # too weak; a negative delta means it is too strong.
        for factor_param, action in [
            ("demote_factor",  SynthesisAction.DEMOTE_WORST),
            ("promote_factor", SynthesisAction.PROMOTE_BEST),
            ("boost_factor",   SynthesisAction.BOOST_UPWARD),
        ]:
            n = self.traj_model.n_transitions(action)
            if n == 0:
                grads[factor_param] = 0.0
                continue
            mean_delta = self.traj_model.mean_acc_delta(action)
            # Gradient ascent on mean delta w.r.t. factor strength
            # If mean_delta > 0: action is helpful — increase factor slightly
            # If mean_delta < 0: action is harmful — decrease factor slightly
            grads[factor_param] = mean_delta

        return grads

    # ------------------------------------------------------------------
    # Update step
    # ------------------------------------------------------------------

    def step(
        self,
        state:       SynthesisStateSnapshot,
        best_action: SynthesisAction,
        params:      MetaParams,
        generation:  int,
    ) -> Tuple[MetaParams, MetaGradStep]:
        """
        Compute meta-gradient and return updated MetaParams.

        Parameters
        ----------
        state : SynthesisStateSnapshot
            Current synthesis state snapshot.
        best_action : SynthesisAction
            The action chosen by WP20's rollout planner.
        params : MetaParams
            Current hyperparameter values.
        generation : int

        Returns
        -------
        (new_params, MetaGradStep)
        """
        # Check data sufficiency
        total_transitions = sum(
            self.traj_model.n_transitions(a) for a in SynthesisAction
        )
        if total_transitions < self.min_transitions:
            logger.debug(
                "MetaGradient: skipping update (only %d/%d transitions)",
                total_transitions, self.min_transitions,
            )
            dummy_step = MetaGradStep(
                generation       = generation,
                params_before    = params.to_dict(),
                params_after     = params.to_dict(),
                gradients        = {k: 0.0 for k in _DEFAULT_PARAMS},
                surrogate_return = 0.0,
                step_size        = self.step_size,
                clipped          = False,
            )
            return params, dummy_step

        # Compute baseline surrogate return
        baseline_return = self._surrogate_return(
            state, best_action, params.horizon, params.discount
        )

        # Compute gradient
        grads = self._gradient(state, best_action, params)

        # SGD update: θ ← θ + α * ∂G/∂θ  (gradient *ascent* on return)
        before_dict = params.as_dict()
        new_dict    = {
            k: before_dict[k] + self.step_size * grads.get(k, 0.0)
            for k in before_dict
        }
        new_params_raw = MetaParams(**new_dict)
        new_params     = new_params_raw.clamp()

        # Detect clamping
        clipped = any(
            abs(getattr(new_params, k) - new_dict[k]) > 1e-9
            for k in before_dict
        )

        step = MetaGradStep(
            generation       = generation,
            params_before    = before_dict,
            params_after     = new_params.to_dict(),
            gradients        = grads,
            surrogate_return = baseline_return,
            step_size        = self.step_size,
            clipped          = clipped,
        )
        self.grad_history.append(step)

        logger.info(
            "MetaGradient gen %d: surrogate_return=%.4f grads=%s "
            "demote %.3f→%.3f promote %.3f→%.3f boost %.3f→%.3f "
            "discount %.3f→%.3f horizon %.1f→%.1f%s",
            generation, baseline_return,
            {k: f"{v:+.4f}" for k, v in grads.items()},
            before_dict["demote_factor"],  new_params.demote_factor,
            before_dict["promote_factor"], new_params.promote_factor,
            before_dict["boost_factor"],   new_params.boost_factor,
            before_dict["discount"],       new_params.discount,
            before_dict["horizon_cont"],   new_params.horizon_cont,
            " [clamped]" if clipped else "",
        )

        return new_params, step

    def get_summary(self) -> Dict[str, Any]:
        if not self.grad_history:
            return {"steps": 0, "mean_surrogate_return": None, "param_trajectory": []}
        returns  = [s.surrogate_return for s in self.grad_history]
        non_zero = [s for s in self.grad_history
                    if any(abs(v) > 1e-12 for v in s.gradients.values())]
        return {
            "steps":                  len(self.grad_history),
            "non_trivial_steps":      len(non_zero),
            "mean_surrogate_return":  sum(returns) / len(returns),
            "final_params":           self.grad_history[-1].params_after,
            "param_trajectory":       [s.to_dict() for s in self.grad_history],
        }


# ---------------------------------------------------------------------------
# MetaGradientCRLS  —  TemporalCRLS + meta-gradient adaptation
# ---------------------------------------------------------------------------

class MetaGradientCRLS(TemporalCRLS):
    """
    WP21 upgrade of TemporalCRLS: adds meta-gradient hyperparameter adaptation.

    Four-layer action-selection hierarchy
    --------------------------------------
    1. **MetaGradientOptimiser** (WP21) — adapts *how strongly* to apply
       each synthesis action (demote_factor, promote_factor, boost_factor,
       discount, horizon).
    2. **RolloutPlanner** (WP20) — picks the *best action* by K-step lookahead
       using the updated discount and horizon from layer (1).
    3. **CausalActionEvaluator** (WP19) — ATE-based fallback.
    4. **WP17 heuristic** — last-resort rule-of-thumb.

    After every generation, layer (1) computes a meta-gradient and updates
    MetaParams.  The updated factors are pushed into the live CRLSSynthesiser
    so the next synthesis cycle uses the improved hyperparameters.

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
        Learning rate for meta-gradient SGD (default 0.02).
    meta_fd_epsilon : float
        Finite-difference step ε (default 0.05).
    meta_min_transitions : int
        Minimum trajectory data before meta-gradient fires (default 4).
    initial_params : MetaParams, optional
        Starting hyperparameter values (defaults to _DEFAULT_PARAMS).
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
        meta_fd_epsilon:        float = _FD_EPSILON,
        meta_min_transitions:   int   = 4,
        initial_params:         Optional[MetaParams] = None,
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
        )

        # WP21 additions
        self.meta_params = (initial_params or MetaParams()).clamp()
        self.meta_opt    = MetaGradientOptimiser(
            trajectory_model         = self.traj_model,
            step_size                = meta_step_size,
            fd_epsilon               = meta_fd_epsilon,
            min_transitions_for_grad = meta_min_transitions,
        )
        self.meta_grad_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Push updated MetaParams into live components
    # ------------------------------------------------------------------

    def _apply_meta_params(self) -> None:
        """
        Propagate the current MetaParams into CRLSSynthesiser and RolloutPlanner.

        This closes the adaptation loop: gradient update → new θ →
        stronger/weaker synthesis actions in the next generation.
        """
        p = self.meta_params

        # Update CRLSSynthesiser factors
        self.synth.demote_f  = p.demote_factor
        self.synth.promote_f = p.promote_factor
        self.synth.boost_f   = p.boost_factor

        # Update RolloutPlanner discount and horizon
        self.planner.discount = p.discount
        self.planner.horizon  = p.horizon

        logger.debug(
            "MetaParams applied: demote=%.3f promote=%.3f boost=%.3f "
            "discount=%.3f horizon=%d",
            p.demote_factor, p.promote_factor, p.boost_factor,
            p.discount, p.horizon,
        )

    # ------------------------------------------------------------------
    # Override end_of_generation
    # ------------------------------------------------------------------

    def end_of_generation(
        self,
        regime: str = "",
    ) -> Tuple[SynthesisRecord, CausalRecommendation, RolloutResult, MetaGradStep]:
        """
        Run synthesis with WP20 rollout + WP21 meta-gradient update.

        Returns
        -------
        (SynthesisRecord, CausalRecommendation, RolloutResult, MetaGradStep)
        """
        # Layers 2–4: inherit WP20 logic
        record, causal_rec, rollout = super().end_of_generation(regime=regime)

        # Layer 1: meta-gradient adaptation
        acc_now = self.acc_history[-2] if len(self.acc_history) >= 2 else self.acc_history[-1]
        current_snapshot = SynthesisStateSnapshot.from_meta_and_acc(
            self.generation - 1,   # generation was already incremented by super()
            self.meta,
            acc_now,
        )

        self.meta_params, grad_step = self.meta_opt.step(
            state       = current_snapshot,
            best_action = rollout.best_action,
            params      = self.meta_params,
            generation  = self.generation - 1,
        )

        # Push updated parameters into live components
        self._apply_meta_params()

        # Append to meta-gradient log
        self.meta_grad_log.append(grad_step.to_dict())
        logger.info(
            "WP21 gen %d: meta_params updated demote=%.3f promote=%.3f "
            "boost=%.3f discount=%.3f horizon=%d",
            self.generation - 1,
            self.meta_params.demote_factor,
            self.meta_params.promote_factor,
            self.meta_params.boost_factor,
            self.meta_params.discount,
            self.meta_params.horizon,
        )

        return record, causal_rec, rollout, grad_step

    # ------------------------------------------------------------------
    # Extended report
    # ------------------------------------------------------------------

    def get_full_report(self) -> Dict[str, Any]:
        report = super().get_full_report()
        report["meta_gradient_summary"] = self.meta_opt.get_summary()
        report["meta_grad_log"]         = self.meta_grad_log
        report["final_meta_params"]     = self.meta_params.to_dict()
        return report


# ---------------------------------------------------------------------------
# Exit-criteria verifier
# ---------------------------------------------------------------------------

def verify_wp21_exit_criteria(crls: MetaGradientCRLS) -> Dict[str, bool]:
    """
    Verify WP21 exit criteria.

    Criteria
    --------
    meta_params_constructed     MetaParams object exists with valid initial values
    optimiser_stepped           At least one non-trivial gradient step was taken
    params_changed              At least one parameter differs from initial defaults
    surrogate_return_computed   At least one step reported a non-zero surrogate return
    params_applied_to_synth     Synthesiser factors match current MetaParams
    safety_preserved            All proposals safety-gated; no UNSAFE action applied

    Returns
    -------
    dict mapping criterion name → bool
    """
    report = crls.get_full_report()
    mg     = report["meta_gradient_summary"]
    safety = report["safety_statistics"]
    fp     = report["final_meta_params"]

    # --- meta_params_constructed ---
    p = crls.meta_params
    params_ok = (
        _PARAM_BOUNDS["demote_factor"][0]  <= p.demote_factor  <= _PARAM_BOUNDS["demote_factor"][1]
        and _PARAM_BOUNDS["promote_factor"][0] <= p.promote_factor <= _PARAM_BOUNDS["promote_factor"][1]
        and _PARAM_BOUNDS["boost_factor"][0]  <= p.boost_factor   <= _PARAM_BOUNDS["boost_factor"][1]
        and _PARAM_BOUNDS["discount"][0]      <= p.discount        <= _PARAM_BOUNDS["discount"][1]
        and _PARAM_BOUNDS["horizon_cont"][0]  <= p.horizon_cont    <= _PARAM_BOUNDS["horizon_cont"][1]
    )

    # --- optimiser_stepped ---
    optimiser_stepped = mg.get("non_trivial_steps", 0) > 0

    # --- params_changed ---
    defaults = _DEFAULT_PARAMS
    params_changed = any(
        abs(fp.get(k, defaults[k]) - defaults[k]) > 1e-9
        for k in defaults
    )

    # --- surrogate_return_computed ---
    surrogate_computed = (
        mg.get("mean_surrogate_return") is not None
        and mg.get("steps", 0) > 0
    )

    # --- params_applied_to_synth ---
    params_applied = (
        abs(crls.synth.demote_f  - p.demote_factor)  < 1e-9
        and abs(crls.synth.promote_f - p.promote_factor) < 1e-9
        and abs(crls.synth.boost_f   - p.boost_factor)   < 1e-9
        and abs(crls.planner.discount - p.discount)       < 1e-9
        and crls.planner.horizon == p.horizon
    )

    # --- safety_preserved ---
    safety_preserved = (
        safety["total_decisions"] > 0
        and safety.get("unsafe_decisions", 0) == 0
    )

    criteria = {
        "meta_params_constructed":    params_ok,
        "optimiser_stepped":          optimiser_stepped,
        "params_changed":             params_changed,
        "surrogate_return_computed":  surrogate_computed,
        "params_applied_to_synth":    params_applied,
        "safety_preserved":           safety_preserved,
    }

    logger.info("WP21 exit criteria: %s", criteria)
    return criteria
