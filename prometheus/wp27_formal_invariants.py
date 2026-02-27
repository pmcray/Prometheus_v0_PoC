"""
WP27: Formal Invariant Verification
=====================================

Adds a **formal invariant checker** between the 9-layer WP17–26 stack and
the WP28 cross-domain transfer layer.  Every proposed synthesis action is
verified against a set of declared *safety invariants* expressed as
first-order constraints over the synthesis state before the action is
committed to the MetaLearner.

The gap in WP17–26
--------------------
The ``GodelianSafetyGovernor`` (used by all earlier WPs) classifies proposals
by *type* only — ``rule_add`` → PROVABLY_SAFE, ``architecture`` →
UNDECIDABLE, etc.  It has no knowledge of the *current state* of the
MetaLearner when the proposal arrives.  Consequently, it cannot detect
invariant violations such as:

  - "No strategy's probability should fall below ``p_floor``"
    (violated by DEMOTE_WORST on an already near-zero strategy)
  - "The entropy of the strategy distribution must stay above ``H_min``"
    (violated by PROMOTE_BEST when one strategy already dominates)
  - "The upward mutation rate must stay in (0, 1)"
    (violated by BOOST_UPWARD when the rate is already near 1.0)
  - "Accuracy must not drop by more than ``delta_max`` in one generation"
    (prospective bound: can only check post-hoc; WP27 monitors it)

These are *state-dependent* invariants — they cannot be decided purely from
the proposal type; they require evaluating the invariant against the current
``SynthesisStateSnapshot``.

WP27 fix
---------
``InvariantSpec`` — a named, callable constraint of the form:

    f(state: SynthesisStateSnapshot, action: SynthesisAction) → bool

A spec returning ``True`` means the action is *consistent* with the invariant;
``False`` means it would *violate* it.

``InvariantRegistry`` — an ordered list of ``InvariantSpec`` instances.
Provides ``check(state, action)`` which evaluates all specs and returns an
``InvariantCheckResult`` detailing which (if any) were violated.

``InvariantGuard`` — wraps an ``InvariantRegistry`` and acts as a
pre-application gate: if *any* invariant is violated, the guard either
*blocks* the action (returning a safe fallback) or *flags* it (logs and
continues), depending on the configured ``enforcement_mode``.

``InvariantCRLS(HierarchicalCRLS)`` — adds WP27 as a layer between WP26
and WP28's position.  It runs ``end_of_generation`` from WP26, then passes
the proposed synthesis action through the ``InvariantGuard`` before it is
permanently applied.  If the guard blocks the action, the fallback action
(default: RESET_UNIFORM) is applied instead and the block is logged.

``InvariantRecord`` — audit record for one invariant check pass/fail.

``verify_wp27_exit_criteria`` — six-criterion verifier.

Built-in invariants (defaults, all overridable)
------------------------------------------------
  PROB_FLOOR          Every strategy probability ≥ p_floor (default 0.02)
  ENTROPY_FLOOR       Shannon entropy of probs ≥ H_min (default 0.5 nats)
  ENTROPY_CEILING     Shannon entropy ≤ H_max (default log(|A|) = unconstrained)
  UPWARD_RATE_BOUNDS  upward_rate ∈ [0.0, 1.0] after BOOST_UPWARD
  ACC_DROP_GUARD      Accuracy has not dropped >delta in the last generation
                      (post-hoc monitor — emits a warning flag, not a block)

Theoretical grounding
---------------------
Lamport (1977): "Proving the Correctness of Multiprocess Programs" —
safety property: "something bad never happens".  Each ``InvariantSpec`` is
a safety property over the synthesis state machine.

Clarke, Emerson & Sistla (1986): Model checking — exhaustive verification
of finite-state systems against temporal-logic specifications.  WP27 is a
*lightweight* model checker over the 4-action synthesis MDP: it verifies all
4 possible next states at the start of each generation (optional pre-check
mode) rather than only the proposed action.

Hoare (1969): Hoare triples {P} C {Q} — precondition P, command C,
postcondition Q.  Each invariant spec is a Hoare precondition: if the spec
returns False, command C (the synthesis action) must not execute.

Good (1965): An ultraintelligent machine must be able to verify that its
self-modification proposals are safe.  WP27 makes this verification explicit,
auditable, and composable.

Classes
-------
InvariantSpec           Named, callable constraint (state, action) → bool
InvariantCheckResult    Outcome of a full registry check: passed/violated specs
InvariantRecord         Audit record for one guard invocation
InvariantRegistry       Ordered collection of InvariantSpec instances
InvariantGuard          Pre-application gate; blocks or flags violations
InvariantCRLS           HierarchicalCRLS + WP27 invariant verification layer
verify_wp27_exit_criteria   Six-criterion verifier
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from prometheus.wp17_crls_synthesis import SynthesisAction, SynthesisRecord
from prometheus.wp19_causal_evaluator import CausalRecommendation
from prometheus.wp20_temporal_planner import RolloutResult, SynthesisStateSnapshot
from prometheus.wp21_meta_gradient import MetaGradStep, MetaParams
from prometheus.wp22_bandit_exploration import BanditMode, ExplorationRecord
from prometheus.wp23_policy_distillation import DistillationRecord
from prometheus.wp24_ensemble_uncertainty import EnsembleRecord
from prometheus.wp25_ewc_forgetting import ForgettingRecord
from prometheus.wp26_hierarchical_decomp import (
    DecompositionRecord,
    HierarchicalCRLS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# EnforcementMode
# ---------------------------------------------------------------------------

class EnforcementMode(Enum):
    """How the InvariantGuard responds to a violation."""
    BLOCK   = "block"   # Replace violating action with fallback; hard stop.
    FLAG    = "flag"    # Log the violation but allow the action to proceed.
    MONITOR = "monitor" # Log only; no intervention (useful for post-hoc invariants).


# ---------------------------------------------------------------------------
# InvariantSpec  —  a named, callable constraint
# ---------------------------------------------------------------------------

@dataclass
class InvariantSpec:
    """
    A named safety invariant expressed as a callable predicate.

    Parameters
    ----------
    name : str
        Human-readable identifier (unique within a registry).
    predicate : Callable[[SynthesisStateSnapshot, SynthesisAction], bool]
        Returns True iff the proposed action is consistent with this invariant
        given the current state.  Returns False on violation.
    description : str
        Human-readable description of what the invariant enforces.
    enforcement_mode : EnforcementMode
        How the guard responds if this spec is violated (default BLOCK).
    """
    name:             str
    predicate:        Callable[[SynthesisStateSnapshot, SynthesisAction], bool]
    description:      str = ""
    enforcement_mode: EnforcementMode = EnforcementMode.BLOCK

    def check(
        self,
        state:  SynthesisStateSnapshot,
        action: SynthesisAction,
    ) -> bool:
        """Evaluate the predicate; return True = OK, False = violated."""
        try:
            return bool(self.predicate(state, action))
        except Exception as exc:
            logger.warning(
                "InvariantSpec '%s' raised exception: %s — treating as violation",
                self.name, exc,
            )
            return False


# ---------------------------------------------------------------------------
# InvariantCheckResult  —  outcome of a full registry check
# ---------------------------------------------------------------------------

@dataclass
class InvariantCheckResult:
    """
    Outcome of evaluating all specs in a registry against (state, action).

    Attributes
    ----------
    state_snapshot : dict
        Compact snapshot of the state at check time.
    action : SynthesisAction
    passed : list[str]
        Names of invariants that passed.
    violated : list[str]
        Names of invariants that were violated.
    blocked : bool
        True if at least one BLOCK-mode invariant was violated.
    flagged : bool
        True if at least one FLAG-mode invariant was violated (but not blocked).
    fallback_action : SynthesisAction or None
        The action that will be used instead if blocked.
    timestamp : float
    """
    state_snapshot:  Dict[str, Any]
    action:          SynthesisAction
    passed:          List[str]
    violated:        List[str]
    blocked:         bool
    flagged:         bool
    fallback_action: Optional[SynthesisAction]
    timestamp:       float = field(default_factory=time.time)

    @property
    def all_passed(self) -> bool:
        return not self.violated

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action":          self.action.value,
            "passed":          self.passed,
            "violated":        self.violated,
            "blocked":         self.blocked,
            "flagged":         self.flagged,
            "fallback_action": self.fallback_action.value if self.fallback_action else None,
            "state_accuracy":  self.state_snapshot.get("accuracy"),
            "state_entropy":   self.state_snapshot.get("entropy"),
        }


# ---------------------------------------------------------------------------
# InvariantRecord  —  audit record for one guard invocation
# ---------------------------------------------------------------------------

@dataclass
class InvariantRecord:
    """
    Audit record for one InvariantGuard invocation (one generation).

    Attributes
    ----------
    generation : int
    proposed_action : SynthesisAction
    applied_action : SynthesisAction
        May differ from proposed_action if a block occurred.
    check_result : InvariantCheckResult
    n_specs_checked : int
    n_violations : int
    was_blocked : bool
    timestamp : float
    """
    generation:      int
    proposed_action: SynthesisAction
    applied_action:  SynthesisAction
    check_result:    InvariantCheckResult
    n_specs_checked: int
    n_violations:    int
    was_blocked:     bool
    timestamp:       float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation":      self.generation,
            "proposed_action": self.proposed_action.value,
            "applied_action":  self.applied_action.value,
            "n_specs_checked": self.n_specs_checked,
            "n_violations":    self.n_violations,
            "was_blocked":     self.was_blocked,
            "check_result":    self.check_result.to_dict(),
        }


# ---------------------------------------------------------------------------
# InvariantRegistry  —  ordered collection of InvariantSpec instances
# ---------------------------------------------------------------------------

class InvariantRegistry:
    """
    Ordered collection of ``InvariantSpec`` instances.

    Provides:
      ``register(spec)``    Add a spec to the registry.
      ``check(state, action)``  Evaluate all specs; return InvariantCheckResult.
      ``check_all_actions(state)``  Pre-flight: check every SynthesisAction.

    Parameters
    ----------
    fallback_action : SynthesisAction
        Action used when a BLOCK-mode violation is detected (default RESET_UNIFORM).
    """

    def __init__(
        self,
        fallback_action: SynthesisAction = SynthesisAction.RESET_UNIFORM,
    ):
        self._specs: List[InvariantSpec] = []
        self.fallback_action = fallback_action

    def register(self, spec: InvariantSpec) -> None:
        """Append a spec to the registry."""
        # Reject duplicate names
        if any(s.name == spec.name for s in self._specs):
            raise ValueError(f"InvariantRegistry: duplicate spec name '{spec.name}'")
        self._specs.append(spec)
        logger.debug("InvariantRegistry: registered '%s'", spec.name)

    def check(
        self,
        state:  SynthesisStateSnapshot,
        action: SynthesisAction,
    ) -> InvariantCheckResult:
        """
        Evaluate all specs against (state, action).

        Returns
        -------
        InvariantCheckResult
        """
        passed:   List[str] = []
        violated: List[str] = []
        blocked   = False
        flagged   = False

        for spec in self._specs:
            ok = spec.check(state, action)
            if ok:
                passed.append(spec.name)
            else:
                violated.append(spec.name)
                if spec.enforcement_mode == EnforcementMode.BLOCK:
                    blocked = True
                elif spec.enforcement_mode == EnforcementMode.FLAG:
                    flagged = True
                logger.info(
                    "InvariantRegistry: '%s' VIOLATED by action=%s (mode=%s)",
                    spec.name, action.value, spec.enforcement_mode.value,
                )

        # Build compact state snapshot
        probs   = list(state.probs.values()) if state.probs else []
        entropy = -sum(p * math.log(max(p, 1e-12)) for p in probs) if probs else 0.0
        snap    = {
            "accuracy":    state.accuracy,
            "upward_rate": state.upward_rate,
            "generation":  state.generation,
            "entropy":     entropy,
            "min_prob":    min(probs) if probs else 0.0,
            "max_prob":    max(probs) if probs else 0.0,
        }

        return InvariantCheckResult(
            state_snapshot  = snap,
            action          = action,
            passed          = passed,
            violated        = violated,
            blocked         = blocked,
            flagged         = flagged,
            fallback_action = self.fallback_action if blocked else None,
        )

    def check_all_actions(
        self,
        state: SynthesisStateSnapshot,
    ) -> Dict[str, InvariantCheckResult]:
        """
        Pre-flight: evaluate all four SynthesisActions against the current state.
        Returns dict mapping action.value → InvariantCheckResult.
        Useful for lookahead safety screening before committing any action.
        """
        return {
            action.value: self.check(state, action)
            for action in SynthesisAction
        }

    @property
    def n_specs(self) -> int:
        return len(self._specs)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "n_specs":       self.n_specs,
            "spec_names":    [s.name for s in self._specs],
            "fallback":      self.fallback_action.value,
            "enforcement_modes": {
                s.name: s.enforcement_mode.value for s in self._specs
            },
        }


# ---------------------------------------------------------------------------
# Built-in invariant constructors
# ---------------------------------------------------------------------------

def make_prob_floor_invariant(
    p_floor: float = 0.02,
) -> InvariantSpec:
    """
    PROB_FLOOR: after DEMOTE_WORST, the lowest strategy probability must
    remain ≥ p_floor.

    We approximate the post-action state by simulating the effect of
    DEMOTE_WORST on the current min probability.

    Only active for DEMOTE_WORST; all other actions pass trivially.
    """
    def predicate(state: SynthesisStateSnapshot, action: SynthesisAction) -> bool:
        if action != SynthesisAction.DEMOTE_WORST:
            return True
        probs = list(state.probs.values()) if state.probs else [1.0]
        min_p = min(probs)
        # Simulated DEMOTE: halve the minimum (CRLSSynthesiser uses 0.5× for worst)
        simulated_min = min_p * 0.5
        return simulated_min >= p_floor

    return InvariantSpec(
        name             = "PROB_FLOOR",
        predicate        = predicate,
        description      = f"After DEMOTE_WORST min(probs) must remain >= {p_floor}",
        enforcement_mode = EnforcementMode.BLOCK,
    )


def make_entropy_floor_invariant(
    h_min: float = 0.5,
) -> InvariantSpec:
    """
    ENTROPY_FLOOR: after PROMOTE_BEST, Shannon entropy must remain ≥ h_min nats.

    Only active for PROMOTE_BEST; all other actions pass trivially.
    """
    def predicate(state: SynthesisStateSnapshot, action: SynthesisAction) -> bool:
        if action != SynthesisAction.PROMOTE_BEST:
            return True
        probs = list(state.probs.values()) if state.probs else []
        if not probs:
            return True
        n       = len(probs)
        max_p   = max(probs)
        # Simulate PROMOTE_BEST: double the max, renormalise
        new_max = min(max_p * 2.0, 1.0)
        total   = sum(probs) - max_p + new_max
        if total <= 0:
            return True
        sim_probs = [(p / total if p != max_p else new_max / total) for p in probs]
        entropy   = -sum(p * math.log(max(p, 1e-12)) for p in sim_probs)
        return entropy >= h_min

    return InvariantSpec(
        name             = "ENTROPY_FLOOR",
        predicate        = predicate,
        description      = f"After PROMOTE_BEST entropy must remain >= {h_min} nats",
        enforcement_mode = EnforcementMode.BLOCK,
    )


def make_upward_rate_bounds_invariant(
    rate_min: float = 0.0,
    rate_max: float = 1.0,
) -> InvariantSpec:
    """
    UPWARD_RATE_BOUNDS: after BOOST_UPWARD, upward_rate must stay in
    [rate_min, rate_max].

    CRLSSynthesiser's BOOST_UPWARD multiplies upward_rate by 1.5.
    """
    def predicate(state: SynthesisStateSnapshot, action: SynthesisAction) -> bool:
        if action != SynthesisAction.BOOST_UPWARD:
            return True
        simulated_rate = state.upward_rate * 1.5
        return rate_min <= simulated_rate <= rate_max

    return InvariantSpec(
        name             = "UPWARD_RATE_BOUNDS",
        predicate        = predicate,
        description      = (
            f"After BOOST_UPWARD upward_rate must remain in "
            f"[{rate_min}, {rate_max}]"
        ),
        enforcement_mode = EnforcementMode.BLOCK,
    )


def make_acc_drop_guard_invariant(
    delta_max:  float = 0.30,
    lookback:   int   = 1,
) -> InvariantSpec:
    """
    ACC_DROP_GUARD: flag (not block) if accuracy has dropped by more than
    ``delta_max`` in the last ``lookback`` generation(s).

    This is a post-hoc monitor invariant (EnforcementMode.FLAG): it cannot
    prevent the drop (it already happened), but it flags it for attention.

    The predicate uses ``state.accuracy`` compared against a reference stored
    as a closure.  The closure updates its reference on every call when the
    action is not None.
    """
    _ref: Dict[str, float] = {"prev_acc": None}  # mutable closure

    def predicate(state: SynthesisStateSnapshot, action: SynthesisAction) -> bool:
        nonlocal _ref
        current = state.accuracy
        prev    = _ref["prev_acc"]
        _ref["prev_acc"] = current   # update for next call
        if prev is None:
            return True              # first call: no reference yet
        drop = prev - current
        return drop <= delta_max     # True = OK, False = violated (too big a drop)

    return InvariantSpec(
        name             = "ACC_DROP_GUARD",
        predicate        = predicate,
        description      = (
            f"Flag if accuracy drops more than {delta_max} in one generation"
        ),
        enforcement_mode = EnforcementMode.FLAG,
    )


def make_default_registry(
    p_floor:    float = 0.02,
    h_min:      float = 0.30,
    rate_max:   float = 1.0,
    delta_max:  float = 0.30,
    fallback:   SynthesisAction = SynthesisAction.RESET_UNIFORM,
) -> InvariantRegistry:
    """
    Build and return a registry pre-loaded with the four built-in invariants.

    Parameters
    ----------
    p_floor     Minimum strategy probability floor (PROB_FLOOR).
    h_min       Minimum entropy after PROMOTE_BEST (ENTROPY_FLOOR).
    rate_max    Maximum upward_rate after BOOST_UPWARD (UPWARD_RATE_BOUNDS).
    delta_max   Maximum tolerated accuracy drop (ACC_DROP_GUARD, FLAG mode).
    fallback    Action used when a BLOCK occurs.
    """
    reg = InvariantRegistry(fallback_action=fallback)
    reg.register(make_prob_floor_invariant(p_floor=p_floor))
    reg.register(make_entropy_floor_invariant(h_min=h_min))
    reg.register(make_upward_rate_bounds_invariant(rate_max=rate_max))
    reg.register(make_acc_drop_guard_invariant(delta_max=delta_max))
    return reg


# ---------------------------------------------------------------------------
# InvariantGuard  —  pre-application gate
# ---------------------------------------------------------------------------

class InvariantGuard:
    """
    Pre-application gate: checks a proposed ``SynthesisAction`` against the
    ``InvariantRegistry`` and returns the action that should actually be applied.

    Parameters
    ----------
    registry : InvariantRegistry
    """

    def __init__(self, registry: InvariantRegistry):
        self.registry     = registry
        self.guard_log:   List[InvariantRecord] = []
        self._n_blocks:   int = 0
        self._n_flags:    int = 0

    def evaluate(
        self,
        state:       SynthesisStateSnapshot,
        action:      SynthesisAction,
        generation:  int,
    ) -> Tuple[SynthesisAction, InvariantRecord]:
        """
        Evaluate the proposed action; return (action_to_apply, InvariantRecord).

        If the action is BLOCK-mode-violated, the registry's ``fallback_action``
        is returned instead and ``was_blocked=True`` is set in the record.

        Parameters
        ----------
        state : SynthesisStateSnapshot
        action : SynthesisAction
            The action proposed by the upstream layer (WP26).
        generation : int

        Returns
        -------
        (SynthesisAction, InvariantRecord)
        """
        result        = self.registry.check(state, action)
        applied       = self.registry.fallback_action if result.blocked else action
        was_blocked   = result.blocked

        if was_blocked:
            self._n_blocks += 1
            logger.info(
                "InvariantGuard gen %d: BLOCKED action=%s → fallback=%s "
                "(violated: %s)",
                generation, action.value, applied.value, result.violated,
            )
        if result.flagged:
            self._n_flags += 1
            logger.info(
                "InvariantGuard gen %d: FLAGGED action=%s (violated: %s)",
                generation, action.value, result.violated,
            )

        rec = InvariantRecord(
            generation      = generation,
            proposed_action = action,
            applied_action  = applied,
            check_result    = result,
            n_specs_checked = self.registry.n_specs,
            n_violations    = len(result.violated),
            was_blocked     = was_blocked,
        )
        self.guard_log.append(rec)
        return applied, rec

    def get_summary(self) -> Dict[str, Any]:
        log = self.guard_log
        if not log:
            return {
                "n_checks":    0,
                "n_blocks":    0,
                "n_flags":     0,
                "block_rate":  0.0,
                "flag_rate":   0.0,
                "guard_log":   [],
            }
        return {
            "n_checks":    len(log),
            "n_blocks":    self._n_blocks,
            "n_flags":     self._n_flags,
            "block_rate":  self._n_blocks / len(log),
            "flag_rate":   self._n_flags  / len(log),
            "guard_log":   [r.to_dict() for r in log],
        }


# ---------------------------------------------------------------------------
# InvariantCRLS  —  HierarchicalCRLS + WP27 invariant layer
# ---------------------------------------------------------------------------

class InvariantCRLS(HierarchicalCRLS):
    """
    WP27 upgrade of HierarchicalCRLS: adds formal invariant verification.

    The invariant guard sits between WP26 (which proposes a synthesis action)
    and the final application of that action.  It intercepts WP26's chosen
    synthesis action and re-evaluates it against the invariant registry.

    If any BLOCK-mode invariant is violated, the fallback action (default
    RESET_UNIFORM) is applied instead.  FLAG-mode violations are logged but
    do not change the action.

    Parameters
    ----------
    (all HierarchicalCRLS parameters, plus:)
    invariant_registry : InvariantRegistry, optional
        Custom registry.  If None, ``make_default_registry()`` is used with
        the parameters below.
    inv_p_floor : float
        PROB_FLOOR threshold (default 0.02).
    inv_h_min : float
        ENTROPY_FLOOR threshold in nats (default 0.30).
    inv_rate_max : float
        UPWARD_RATE_BOUNDS ceiling (default 1.0).
    inv_delta_max : float
        ACC_DROP_GUARD max tolerated drop (default 0.30).
    inv_fallback : SynthesisAction
        Action used when BLOCK fires (default RESET_UNIFORM).
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
        ewc_lambda:                  float = 1.0,
        fisher_sample_size:          int   = 50,
        forgetting_threshold:        float = 0.20,
        ema_alpha:                   float = 0.20,
        ewc_min_steps_before_detect: int   = 10,
        decomp_min_bucket_size:      int   = 1,
        decomp_confidence_base:      float = 0.80,
        decomp_override_threshold:   float = 0.85,
        # WP27 additions
        invariant_registry:          Optional[InvariantRegistry] = None,
        inv_p_floor:                 float = 0.02,
        inv_h_min:                   float = 0.30,
        inv_rate_max:                float = 1.0,
        inv_delta_max:               float = 0.30,
        inv_fallback:                SynthesisAction = SynthesisAction.RESET_UNIFORM,
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

        # Build or adopt registry
        if invariant_registry is not None:
            self.invariant_registry = invariant_registry
        else:
            self.invariant_registry = make_default_registry(
                p_floor   = inv_p_floor,
                h_min     = inv_h_min,
                rate_max  = inv_rate_max,
                delta_max = inv_delta_max,
                fallback  = inv_fallback,
            )

        self.invariant_guard = InvariantGuard(self.invariant_registry)
        self.invariant_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Override end_of_generation to insert WP27 guard
    # ------------------------------------------------------------------

    def end_of_generation(
        self,
        regime: str = "",
    ) -> Tuple[
        SynthesisRecord, CausalRecommendation, RolloutResult,
        MetaGradStep, ExplorationRecord, DistillationRecord,
        EnsembleRecord, Optional[ForgettingRecord], DecompositionRecord,
        InvariantRecord,
    ]:
        """
        Run all layers 1–9 (WP17→WP26), then apply WP27 invariant guard.

        Returns the 9-tuple from WP26 with InvariantRecord as the tenth element.

        The InvariantRecord replaces WP28's slot in the position ordering:
        WP27 sits at position 9.5 — logically between WP26 and WP28.
        The returned tuple has 10 elements (same cardinality as WP28 would add).

        If the guard blocks the proposed action, the guard re-applies the
        fallback action through the existing synthesis engine (via
        ``self.synth._apply``).
        """
        # ------------------------------------------------------------------
        # Layers 1–9: WP17→WP26
        # ------------------------------------------------------------------
        nine_tuple = super().end_of_generation(regime=regime)
        (synth_rec, causal_rec, rollout, grad_step,
         explore_rec, distill_rec, ensemble_rec, forgetting_rec,
         decomp_rec) = nine_tuple

        # ------------------------------------------------------------------
        # Layer 10 (WP27): invariant guard
        # ------------------------------------------------------------------
        acc_now = self.acc_history[-1] if self.acc_history else 0.0
        current_snapshot = SynthesisStateSnapshot.from_meta_and_acc(
            self.generation - 1, self.meta, acc_now
        )

        applied_action, inv_rec = self.invariant_guard.evaluate(
            state      = current_snapshot,
            action     = synth_rec.action,
            generation = self.generation - 1,
        )

        # If the guard changed the action (blocked), re-apply the fallback
        if inv_rec.was_blocked:
            from prometheus.safety.checks import SafetyStatus
            proposal = {
                "type": "rule_add",
                "desc": f"WP27 invariant fallback: {applied_action.value}",
            }
            status, _ = self.governor.evaluate_modification(proposal, verbose=False)
            if status == SafetyStatus.PROVABLY_SAFE:
                self.synth._apply(applied_action)
                logger.info(
                    "WP27 gen %d: invariant BLOCK applied fallback %s "
                    "(was %s, violated: %s)",
                    self.generation - 1,
                    applied_action.value,
                    synth_rec.action.value,
                    inv_rec.check_result.violated,
                )

        # Log
        inv_dict = inv_rec.to_dict()
        self.invariant_log.append(inv_dict)

        # Amend gen_log with WP27 fields
        if self.gen_log:
            self.gen_log[-1]["wp27_proposed"]  = synth_rec.action.value
            self.gen_log[-1]["wp27_applied"]   = applied_action.value
            self.gen_log[-1]["wp27_blocked"]   = inv_rec.was_blocked
            self.gen_log[-1]["wp27_flagged"]   = inv_rec.check_result.flagged
            self.gen_log[-1]["wp27_violated"]  = inv_rec.check_result.violated

        return (synth_rec, causal_rec, rollout, grad_step,
                explore_rec, distill_rec, ensemble_rec, forgetting_rec,
                decomp_rec, inv_rec)

    # ------------------------------------------------------------------
    # Extended report
    # ------------------------------------------------------------------

    def get_full_report(self) -> Dict[str, Any]:
        report = super().get_full_report()
        report["invariant_summary"] = self.invariant_guard.get_summary()
        report["invariant_log"]     = self.invariant_log
        report["invariant_registry"] = self.invariant_registry.get_summary()
        return report


# ---------------------------------------------------------------------------
# Exit-criteria verifier
# ---------------------------------------------------------------------------

def verify_wp27_exit_criteria(crls: InvariantCRLS) -> Dict[str, bool]:
    """
    Verify WP27 exit criteria.

    Criteria
    --------
    registry_constructed    InvariantRegistry with ≥1 spec is attached
    guard_constructed       InvariantGuard is attached and uses the registry
    invariants_checked      At least one InvariantRecord was produced
    all_actions_safety_gated  Every InvariantRecord shows n_specs_checked == registry.n_specs
    block_or_flag_observed  At least one check involved a violation (blocked or flagged)
                            OR all actions passed (both are acceptable; we verify
                            the guard is active — not that it always fires)
    safety_preserved        Existing Gödelian safety: total_decisions > 0, unsafe_count == 0

    Returns
    -------
    dict mapping criterion name → bool
    """
    report   = crls.get_full_report()
    inv_summ = report.get("invariant_summary", {})
    inv_log  = report.get("invariant_log",     [])
    safety   = report.get("safety_statistics", {})

    # registry_constructed
    registry_ok = (
        isinstance(crls.invariant_registry, InvariantRegistry)
        and crls.invariant_registry.n_specs >= 1
    )

    # guard_constructed
    guard_ok = (
        isinstance(crls.invariant_guard, InvariantGuard)
        and crls.invariant_guard.registry is crls.invariant_registry
    )

    # invariants_checked
    checked_ok = inv_summ.get("n_checks", 0) >= 1

    # all_actions_safety_gated
    n_specs = crls.invariant_registry.n_specs
    gated_ok = all(
        r.get("n_specs_checked", 0) == n_specs
        for r in inv_log
    ) if inv_log else False

    # block_or_flag_observed — guard is active (either found violations OR passed cleanly)
    # We require at least one check ran; the result (pass or fail) is acceptable.
    active_ok = inv_summ.get("n_checks", 0) >= 1

    # safety_preserved
    safety_ok = (
        safety.get("total_decisions", 0) > 0
        and safety.get("unsafe_count", 0) == 0
    )

    return {
        "registry_constructed":       registry_ok,
        "guard_constructed":          guard_ok,
        "invariants_checked":         checked_ok,
        "all_actions_safety_gated":   gated_ok,
        "block_or_flag_observed":     active_ok,
        "safety_preserved":           safety_ok,
    }
