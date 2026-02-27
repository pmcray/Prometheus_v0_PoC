"""
WP27 Test Suite: Formal Invariant Verification
===============================================

Eight test classes:

TestInvariantSpec           Unit tests for InvariantSpec predicate + enforcement
TestInvariantCheckResult    Unit tests for InvariantCheckResult dataclass
TestInvariantRecord         Unit tests for InvariantRecord dataclass
TestInvariantRegistry       Registry CRUD, check(), check_all_actions()
TestBuiltinInvariants       Each of the four built-in invariants fires correctly
TestInvariantGuard          Gate mechanics: block, flag, pass
TestInvariantCRLS           Integration: all 10 layers, guard active
TestWP27ExitCriteria        Six-criterion verifier
"""

import math
import random
from typing import Callable, Dict, List, Optional, Tuple

import pytest

from prometheus.environments.go import GoBoard
from prometheus.wp17_crls_synthesis import SynthesisAction, SynthesisRecord
from prometheus.wp19_causal_evaluator import CausalRecommendation
from prometheus.wp20_temporal_planner import RolloutResult, SynthesisStateSnapshot
from prometheus.wp21_meta_gradient import MetaGradStep
from prometheus.wp22_bandit_exploration import BanditMode, ExplorationRecord
from prometheus.wp23_policy_distillation import DistillationRecord
from prometheus.wp24_ensemble_uncertainty import EnsembleRecord
from prometheus.wp25_ewc_forgetting import ForgettingRecord
from prometheus.wp26_hierarchical_decomp import DecompositionRecord
from prometheus.wp27_formal_invariants import (
    EnforcementMode,
    InvariantCheckResult,
    InvariantCRLS,
    InvariantGuard,
    InvariantRecord,
    InvariantRegistry,
    InvariantSpec,
    make_acc_drop_guard_invariant,
    make_default_registry,
    make_entropy_floor_invariant,
    make_prob_floor_invariant,
    make_upward_rate_bounds_invariant,
    verify_wp27_exit_criteria,
)


# ===========================================================================
# Shared helpers
# ===========================================================================

TACTICS = ["capture_atari", "ladder", "ko_fight",
           "territory_claim", "connect_groups", "random_legal"]


def _dummy_state(
    accuracy:    float = 0.50,
    upward_rate: float = 0.20,
    generation:  int   = 5,
    probs:       Optional[Dict[str, float]] = None,
) -> SynthesisStateSnapshot:
    if probs is None:
        n = len(TACTICS)
        probs = {s: 1.0 / n for s in TACTICS}
    return SynthesisStateSnapshot(
        generation  = generation,
        accuracy    = accuracy,
        upward_rate = upward_rate,
        probs       = probs,
    )


def _low_entropy_state() -> SynthesisStateSnapshot:
    """State where one strategy dominates → low entropy."""
    probs = {s: 0.02 for s in TACTICS}
    probs["capture_atari"] = 0.90
    total = sum(probs.values())
    probs = {k: v / total for k, v in probs.items()}
    return _dummy_state(probs=probs)


def _near_zero_min_prob_state() -> SynthesisStateSnapshot:
    """State where one strategy is near zero → DEMOTE_WORST would violate floor."""
    probs = {s: 0.19 for s in TACTICS}
    probs["random_legal"] = 0.01   # already very low
    total = sum(probs.values())
    probs = {k: v / total for k, v in probs.items()}
    return _dummy_state(probs=probs)


def _high_rate_state() -> SynthesisStateSnapshot:
    """State with upward_rate=0.70 → BOOST_UPWARD (×1.5) would give 1.05 > 1.0."""
    return _dummy_state(upward_rate=0.70)


def _atari_board() -> Tuple[GoBoard, int, Tuple[int, int]]:
    board = GoBoard(size=9)
    board.board[4][4] = GoBoard.WHITE
    board.board[4][3] = GoBoard.BLACK
    board.board[4][5] = GoBoard.BLACK
    board.board[5][4] = GoBoard.BLACK
    board.current_player = GoBoard.BLACK
    return board, GoBoard.BLACK, (3, 4)


def _territory_board() -> Tuple[GoBoard, int, Tuple[int, int]]:
    board = GoBoard(size=9)
    board.board[0][0] = GoBoard.WHITE
    board.board[0][8] = GoBoard.WHITE
    board.board[8][0] = GoBoard.WHITE
    board.current_player = GoBoard.BLACK
    return board, GoBoard.BLACK, (8, 8)


def _go_puzzles(n: int) -> List[Tuple]:
    return [(_atari_board() if i % 2 == 0 else _territory_board())
            for i in range(n)]


def _go_eval(board, move, correct_move, player) -> bool:
    if move == correct_move:
        return True
    if move[0] >= 0 and board.is_legal_move(move[0], move[1], player):
        if len(board.would_capture(move[0], move[1], player)) > 0:
            return True
    return False


def _go_tactic_fns() -> Dict[str, Callable]:
    def capture_atari(board, player):
        for r in range(board.size):
            for c in range(board.size):
                if board.is_legal_move(r, c, player):
                    if board.would_capture(r, c, player):
                        return (r, c)
        legal = board.get_legal_moves(player)
        return legal[0] if legal else None

    def ladder(board, player):
        legal = board.get_legal_moves(player)
        for m in legal:
            if board.would_capture(m[0], m[1], player):
                return m
        return legal[0] if legal else None

    def ko_fight(board, player):
        legal = board.get_legal_moves(player)
        return legal[0] if legal else None

    def territory_claim(board, player):
        legal = board.get_legal_moves(player)
        return legal[-1] if legal else None

    def connect_groups(board, player):
        legal = board.get_legal_moves(player)
        mid = len(legal) // 2
        return legal[mid] if legal else None

    def random_legal(board, player):
        legal = board.get_legal_moves(player)
        return random.choice(legal) if legal else None

    return {
        "capture_atari":   capture_atari,
        "ladder":          ladder,
        "ko_fight":        ko_fight,
        "territory_claim": territory_claim,
        "connect_groups":  connect_groups,
        "random_legal":    random_legal,
    }


def _make_crls(
    seed: int = 42,
    n_members: int = 3,
    invariant_registry: Optional[InvariantRegistry] = None,
    inv_p_floor: float = 0.02,
    inv_h_min:   float = 0.30,
    inv_rate_max: float = 1.0,
    inv_delta_max: float = 0.30,
) -> InvariantCRLS:
    random.seed(seed)
    return InvariantCRLS(
        strategies                  = TACTICS,
        upward_rate                 = 0.0,
        downward_rate               = 0.0,
        synthesiser_kwargs          = {"acc_drop_threshold": 0.0},
        min_trials_to_override      = 3,
        override_tolerance          = 0.02,
        rollout_horizon             = 3,
        rollout_discount            = 0.90,
        min_transitions             = 3,
        meta_step_size              = 0.02,
        meta_min_transitions        = 4,
        bandit_mode                 = BanditMode.UCB1,
        exploration_coeff           = 1.0,
        force_explore_unseen        = True,
        distill_lr                  = 0.10,
        distill_min_steps           = 5,
        distill_confidence          = 0.40,
        ensemble_n_members          = n_members,
        ensemble_lr                 = 0.10,
        ensemble_l2                 = 1e-4,
        ensemble_init_noise         = 0.01,
        ensemble_min_steps          = 5,
        ensemble_max_jsd            = 1.0,
        ensemble_min_conf           = 0.0,
        ensemble_seed               = seed,
        ewc_lambda                  = 1.0,
        fisher_sample_size          = 20,
        forgetting_threshold        = 0.05,
        ema_alpha                   = 0.5,
        ewc_min_steps_before_detect = 5,
        decomp_min_bucket_size      = 1,
        decomp_confidence_base      = 0.80,
        decomp_override_threshold   = 1.01,
        invariant_registry          = invariant_registry,
        inv_p_floor                 = inv_p_floor,
        inv_h_min                   = inv_h_min,
        inv_rate_max                = inv_rate_max,
        inv_delta_max               = inv_delta_max,
    )


def _run_n_gens(crls: InvariantCRLS, n: int) -> None:
    puzzles    = _go_puzzles(10)
    tactic_fns = _go_tactic_fns()
    for _ in range(n):
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        crls.end_of_generation(regime="test")


# ===========================================================================
# TestInvariantSpec
# ===========================================================================

class TestInvariantSpec:
    def test_construction_valid(self):
        spec = InvariantSpec(
            name        = "TEST_SPEC",
            predicate   = lambda s, a: True,
            description = "Always passes",
        )
        assert spec.name == "TEST_SPEC"
        assert spec.enforcement_mode == EnforcementMode.BLOCK

    def test_custom_enforcement_mode(self):
        spec = InvariantSpec(
            name             = "FLAG_SPEC",
            predicate        = lambda s, a: False,
            enforcement_mode = EnforcementMode.FLAG,
        )
        assert spec.enforcement_mode == EnforcementMode.FLAG

    def test_check_passes(self):
        spec  = InvariantSpec("PASS", lambda s, a: True)
        state = _dummy_state()
        assert spec.check(state, SynthesisAction.PROMOTE_BEST) is True

    def test_check_fails(self):
        spec  = InvariantSpec("FAIL", lambda s, a: False)
        state = _dummy_state()
        assert spec.check(state, SynthesisAction.DEMOTE_WORST) is False

    def test_exception_in_predicate_treated_as_violation(self):
        def bad_pred(s, a):
            raise RuntimeError("boom")
        spec  = InvariantSpec("BAD", bad_pred)
        state = _dummy_state()
        assert spec.check(state, SynthesisAction.PROMOTE_BEST) is False

    def test_predicate_receives_state_and_action(self):
        received = {}
        def capturing_pred(s, a):
            received["state"]  = s
            received["action"] = a
            return True
        spec  = InvariantSpec("CAP", capturing_pred)
        state = _dummy_state(accuracy=0.77)
        spec.check(state, SynthesisAction.RESET_UNIFORM)
        assert received["state"] is state
        assert received["action"] == SynthesisAction.RESET_UNIFORM


# ===========================================================================
# TestInvariantCheckResult
# ===========================================================================

class TestInvariantCheckResult:
    def _make_result(self, blocked=False, flagged=False, violated=None):
        return InvariantCheckResult(
            state_snapshot  = {"accuracy": 0.5, "entropy": 1.0},
            action          = SynthesisAction.PROMOTE_BEST,
            passed          = ["A", "B"] if not violated else [],
            violated        = violated or [],
            blocked         = blocked,
            flagged         = flagged,
            fallback_action = SynthesisAction.RESET_UNIFORM if blocked else None,
        )

    def test_all_passed_when_no_violations(self):
        r = self._make_result()
        assert r.all_passed is True

    def test_not_all_passed_when_violated(self):
        r = self._make_result(blocked=True, violated=["SPEC_X"])
        assert r.all_passed is False

    def test_to_dict_has_required_keys(self):
        r = self._make_result()
        d = r.to_dict()
        for key in ("action", "passed", "violated", "blocked",
                    "flagged", "fallback_action"):
            assert key in d

    def test_fallback_none_when_not_blocked(self):
        r = self._make_result(blocked=False)
        assert r.fallback_action is None
        assert r.to_dict()["fallback_action"] is None

    def test_fallback_set_when_blocked(self):
        r = self._make_result(blocked=True, violated=["X"])
        assert r.fallback_action == SynthesisAction.RESET_UNIFORM


# ===========================================================================
# TestInvariantRecord
# ===========================================================================

class TestInvariantRecord:
    def _make_record(self, blocked=False):
        result = InvariantCheckResult(
            state_snapshot  = {},
            action          = SynthesisAction.DEMOTE_WORST,
            passed          = [],
            violated        = ["P"] if blocked else [],
            blocked         = blocked,
            flagged         = False,
            fallback_action = SynthesisAction.RESET_UNIFORM if blocked else None,
        )
        return InvariantRecord(
            generation      = 3,
            proposed_action = SynthesisAction.DEMOTE_WORST,
            applied_action  = (SynthesisAction.RESET_UNIFORM
                               if blocked else SynthesisAction.DEMOTE_WORST),
            check_result    = result,
            n_specs_checked = 4,
            n_violations    = 1 if blocked else 0,
            was_blocked     = blocked,
        )

    def test_construction_not_blocked(self):
        r = self._make_record(blocked=False)
        assert r.was_blocked is False
        assert r.applied_action == r.proposed_action

    def test_construction_blocked(self):
        r = self._make_record(blocked=True)
        assert r.was_blocked is True
        assert r.applied_action != r.proposed_action

    def test_to_dict_has_required_keys(self):
        r = self._make_record()
        d = r.to_dict()
        for key in ("generation", "proposed_action", "applied_action",
                    "n_specs_checked", "n_violations", "was_blocked"):
            assert key in d

    def test_timestamp_auto_populated(self):
        r = self._make_record()
        assert r.timestamp > 0.0


# ===========================================================================
# TestInvariantRegistry
# ===========================================================================

class TestInvariantRegistry:
    def test_empty_registry_construction(self):
        reg = InvariantRegistry()
        assert reg.n_specs == 0

    def test_register_adds_spec(self):
        reg  = InvariantRegistry()
        spec = InvariantSpec("S1", lambda s, a: True)
        reg.register(spec)
        assert reg.n_specs == 1

    def test_duplicate_name_raises(self):
        reg = InvariantRegistry()
        reg.register(InvariantSpec("DUP", lambda s, a: True))
        with pytest.raises(ValueError, match="duplicate"):
            reg.register(InvariantSpec("DUP", lambda s, a: False))

    def test_check_all_pass(self):
        reg = InvariantRegistry()
        reg.register(InvariantSpec("A", lambda s, a: True))
        reg.register(InvariantSpec("B", lambda s, a: True))
        result = reg.check(_dummy_state(), SynthesisAction.PROMOTE_BEST)
        assert result.all_passed
        assert not result.blocked
        assert not result.flagged

    def test_check_block_mode_violation(self):
        reg = InvariantRegistry()
        reg.register(InvariantSpec("BLOCK_SPEC", lambda s, a: False,
                                   enforcement_mode=EnforcementMode.BLOCK))
        result = reg.check(_dummy_state(), SynthesisAction.DEMOTE_WORST)
        assert result.blocked
        assert "BLOCK_SPEC" in result.violated

    def test_check_flag_mode_violation(self):
        reg = InvariantRegistry()
        reg.register(InvariantSpec("FLAG_SPEC", lambda s, a: False,
                                   enforcement_mode=EnforcementMode.FLAG))
        result = reg.check(_dummy_state(), SynthesisAction.PROMOTE_BEST)
        assert not result.blocked
        assert result.flagged
        assert "FLAG_SPEC" in result.violated

    def test_check_all_actions_returns_four_results(self):
        reg = InvariantRegistry()
        reg.register(InvariantSpec("S", lambda s, a: True))
        results = reg.check_all_actions(_dummy_state())
        assert len(results) == len(list(SynthesisAction))
        for action in SynthesisAction:
            assert action.value in results

    def test_get_summary_keys(self):
        reg = make_default_registry()
        s   = reg.get_summary()
        for key in ("n_specs", "spec_names", "fallback", "enforcement_modes"):
            assert key in s

    def test_fallback_action_in_result_when_blocked(self):
        reg = InvariantRegistry(fallback_action=SynthesisAction.BOOST_UPWARD)
        reg.register(InvariantSpec("X", lambda s, a: False))
        result = reg.check(_dummy_state(), SynthesisAction.DEMOTE_WORST)
        assert result.fallback_action == SynthesisAction.BOOST_UPWARD


# ===========================================================================
# TestBuiltinInvariants
# ===========================================================================

class TestBuiltinInvariants:
    # ---- PROB_FLOOR ----
    def test_prob_floor_passes_for_non_demote(self):
        spec  = make_prob_floor_invariant(p_floor=0.05)
        state = _near_zero_min_prob_state()
        for action in [SynthesisAction.PROMOTE_BEST,
                       SynthesisAction.RESET_UNIFORM,
                       SynthesisAction.BOOST_UPWARD]:
            assert spec.check(state, action) is True

    def test_prob_floor_blocks_demote_when_floor_would_be_violated(self):
        # p_floor=0.05; near-zero state has min ~0.01 → simulated 0.005 < 0.05
        spec  = make_prob_floor_invariant(p_floor=0.05)
        state = _near_zero_min_prob_state()
        assert spec.check(state, SynthesisAction.DEMOTE_WORST) is False

    def test_prob_floor_passes_demote_when_safe(self):
        # Uniform state: min_p = 1/6 ≈ 0.167 → simulated 0.083 > 0.02
        spec  = make_prob_floor_invariant(p_floor=0.02)
        state = _dummy_state()
        assert spec.check(state, SynthesisAction.DEMOTE_WORST) is True

    # ---- ENTROPY_FLOOR ----
    def test_entropy_floor_passes_for_non_promote(self):
        spec  = make_entropy_floor_invariant(h_min=0.5)
        state = _low_entropy_state()
        for action in [SynthesisAction.DEMOTE_WORST,
                       SynthesisAction.RESET_UNIFORM,
                       SynthesisAction.BOOST_UPWARD]:
            assert spec.check(state, action) is True

    def test_entropy_floor_blocks_promote_when_already_low_entropy(self):
        # h_min=2.0 nats; low-entropy state would drop further after PROMOTE
        spec  = make_entropy_floor_invariant(h_min=2.0)
        state = _low_entropy_state()
        assert spec.check(state, SynthesisAction.PROMOTE_BEST) is False

    def test_entropy_floor_passes_promote_on_uniform(self):
        # Uniform 6-strategy state: entropy ≈ ln(6) ≈ 1.79 nats.
        # After PROMOTE_BEST: still > 0.30 nats.
        spec  = make_entropy_floor_invariant(h_min=0.30)
        state = _dummy_state()
        assert spec.check(state, SynthesisAction.PROMOTE_BEST) is True

    # ---- UPWARD_RATE_BOUNDS ----
    def test_upward_rate_passes_for_non_boost(self):
        spec  = make_upward_rate_bounds_invariant(rate_max=1.0)
        state = _high_rate_state()
        for action in [SynthesisAction.PROMOTE_BEST,
                       SynthesisAction.DEMOTE_WORST,
                       SynthesisAction.RESET_UNIFORM]:
            assert spec.check(state, action) is True

    def test_upward_rate_blocks_boost_when_over_max(self):
        # upward_rate=0.70 × 1.5 = 1.05 > 1.0
        spec  = make_upward_rate_bounds_invariant(rate_max=1.0)
        state = _high_rate_state()
        assert spec.check(state, SynthesisAction.BOOST_UPWARD) is False

    def test_upward_rate_passes_boost_when_safe(self):
        # upward_rate=0.20 × 1.5 = 0.30 < 1.0
        spec  = make_upward_rate_bounds_invariant(rate_max=1.0)
        state = _dummy_state(upward_rate=0.20)
        assert spec.check(state, SynthesisAction.BOOST_UPWARD) is True

    # ---- ACC_DROP_GUARD ----
    def test_acc_drop_guard_passes_first_call(self):
        spec  = make_acc_drop_guard_invariant(delta_max=0.20)
        state = _dummy_state(accuracy=0.60)
        assert spec.check(state, SynthesisAction.PROMOTE_BEST) is True  # no prev

    def test_acc_drop_guard_passes_small_drop(self):
        spec  = make_acc_drop_guard_invariant(delta_max=0.20)
        s1    = _dummy_state(accuracy=0.70)
        s2    = _dummy_state(accuracy=0.60)
        spec.check(s1, SynthesisAction.PROMOTE_BEST)   # sets prev
        assert spec.check(s2, SynthesisAction.PROMOTE_BEST) is True  # drop=0.10 < 0.20

    def test_acc_drop_guard_flags_large_drop(self):
        spec  = make_acc_drop_guard_invariant(delta_max=0.10)
        s1    = _dummy_state(accuracy=0.80)
        s2    = _dummy_state(accuracy=0.55)
        spec.check(s1, SynthesisAction.PROMOTE_BEST)
        assert spec.check(s2, SynthesisAction.PROMOTE_BEST) is False  # drop=0.25 > 0.10

    def test_acc_drop_guard_is_flag_mode(self):
        spec = make_acc_drop_guard_invariant()
        assert spec.enforcement_mode == EnforcementMode.FLAG

    # ---- Default registry ----
    def test_default_registry_has_four_specs(self):
        reg = make_default_registry()
        assert reg.n_specs == 4

    def test_default_registry_spec_names(self):
        reg   = make_default_registry()
        names = reg.get_summary()["spec_names"]
        assert "PROB_FLOOR"       in names
        assert "ENTROPY_FLOOR"    in names
        assert "UPWARD_RATE_BOUNDS" in names
        assert "ACC_DROP_GUARD"   in names


# ===========================================================================
# TestInvariantGuard
# ===========================================================================

class TestInvariantGuard:
    def _make_guard(self) -> InvariantGuard:
        return InvariantGuard(make_default_registry())

    def test_guard_passes_clean_action(self):
        guard  = self._make_guard()
        state  = _dummy_state()
        action, rec = guard.evaluate(state, SynthesisAction.PROMOTE_BEST, generation=0)
        assert action == SynthesisAction.PROMOTE_BEST
        assert rec.was_blocked is False

    def test_guard_blocks_violating_action(self):
        # Build a registry that always blocks
        reg = InvariantRegistry(fallback_action=SynthesisAction.RESET_UNIFORM)
        reg.register(InvariantSpec("ALWAYS_BLOCK", lambda s, a: False,
                                   enforcement_mode=EnforcementMode.BLOCK))
        guard  = InvariantGuard(reg)
        state  = _dummy_state()
        action, rec = guard.evaluate(state, SynthesisAction.DEMOTE_WORST, generation=0)
        assert action == SynthesisAction.RESET_UNIFORM
        assert rec.was_blocked is True

    def test_guard_flags_without_blocking(self):
        reg = InvariantRegistry()
        reg.register(InvariantSpec("FLAG_ONLY", lambda s, a: False,
                                   enforcement_mode=EnforcementMode.FLAG))
        guard  = InvariantGuard(reg)
        state  = _dummy_state()
        action, rec = guard.evaluate(state, SynthesisAction.PROMOTE_BEST, generation=0)
        assert action == SynthesisAction.PROMOTE_BEST
        assert rec.was_blocked is False
        assert rec.check_result.flagged is True

    def test_guard_log_grows(self):
        guard = self._make_guard()
        state = _dummy_state()
        for i in range(5):
            guard.evaluate(state, SynthesisAction.PROMOTE_BEST, generation=i)
        assert len(guard.guard_log) == 5

    def test_get_summary_empty(self):
        guard = self._make_guard()
        s = guard.get_summary()
        assert s["n_checks"] == 0

    def test_get_summary_after_checks(self):
        guard = self._make_guard()
        state = _dummy_state()
        for i in range(3):
            guard.evaluate(state, SynthesisAction.PROMOTE_BEST, generation=i)
        s = guard.get_summary()
        assert s["n_checks"] == 3
        assert "block_rate" in s
        assert "flag_rate"  in s

    def test_n_blocks_increments(self):
        reg = InvariantRegistry()
        reg.register(InvariantSpec("BLOCK_ALL", lambda s, a: False,
                                   enforcement_mode=EnforcementMode.BLOCK))
        guard = InvariantGuard(reg)
        state = _dummy_state()
        for i in range(3):
            guard.evaluate(state, SynthesisAction.DEMOTE_WORST, generation=i)
        assert guard._n_blocks == 3


# ===========================================================================
# TestInvariantCRLS
# ===========================================================================

class TestInvariantCRLS:
    def test_construction_succeeds(self):
        crls = _make_crls()
        assert isinstance(crls, InvariantCRLS)

    def test_registry_attached(self):
        crls = _make_crls()
        assert isinstance(crls.invariant_registry, InvariantRegistry)
        assert crls.invariant_registry.n_specs >= 1

    def test_guard_attached(self):
        crls = _make_crls()
        assert isinstance(crls.invariant_guard, InvariantGuard)
        assert crls.invariant_guard.registry is crls.invariant_registry

    def test_run_generation_returns_float(self):
        crls   = _make_crls()
        puzzles = _go_puzzles(6)
        acc    = crls.run_generation(puzzles, _go_tactic_fns(), _go_eval)
        assert 0.0 <= acc <= 1.0

    def test_end_of_generation_returns_10_tuple(self):
        crls   = _make_crls()
        puzzles = _go_puzzles(6)
        crls.run_generation(puzzles, _go_tactic_fns(), _go_eval)
        result = crls.end_of_generation(regime="test")
        assert len(result) == 10

    def test_10th_element_is_invariant_record(self):
        crls   = _make_crls()
        puzzles = _go_puzzles(6)
        crls.run_generation(puzzles, _go_tactic_fns(), _go_eval)
        result = crls.end_of_generation()
        assert isinstance(result[9], InvariantRecord)

    def test_invariant_log_populated(self):
        crls = _make_crls()
        _run_n_gens(crls, 5)
        assert len(crls.invariant_log) == 5

    def test_gen_log_has_wp27_fields(self):
        crls = _make_crls()
        _run_n_gens(crls, 3)
        for entry in crls.gen_log:
            assert "wp27_proposed" in entry
            assert "wp27_applied"  in entry
            assert "wp27_blocked"  in entry
            assert "wp27_flagged"  in entry
            assert "wp27_violated" in entry

    def test_full_report_has_invariant_keys(self):
        crls = _make_crls()
        _run_n_gens(crls, 3)
        report = crls.get_full_report()
        assert "invariant_summary"  in report
        assert "invariant_log"      in report
        assert "invariant_registry" in report

    def test_no_unsafe_synthesis_applied(self):
        crls = _make_crls()
        _run_n_gens(crls, 5)
        stats = crls.get_full_report()["safety_statistics"]
        assert stats["unsafe_count"] == 0

    def test_all_9_earlier_layers_still_present(self):
        crls = _make_crls()
        _run_n_gens(crls, 3)
        result_9_elements = crls.get_full_report()
        for key in ("distillation_summary", "ensemble_summary",
                    "ewc_summary", "decomposition_summary"):
            assert key in result_9_elements

    def test_custom_registry_accepted(self):
        reg = InvariantRegistry()
        reg.register(InvariantSpec("CUSTOM", lambda s, a: True))
        crls = _make_crls(invariant_registry=reg)
        assert crls.invariant_registry is reg

    def test_block_fires_when_invariant_always_violated(self):
        """A registry that always blocks should produce was_blocked=True records."""
        reg = InvariantRegistry(fallback_action=SynthesisAction.RESET_UNIFORM)
        reg.register(InvariantSpec("ALWAYS_BLOCK", lambda s, a: False,
                                   enforcement_mode=EnforcementMode.BLOCK))
        crls = _make_crls(invariant_registry=reg)
        _run_n_gens(crls, 3)
        blocked_count = sum(1 for r in crls.invariant_log if r["was_blocked"])
        assert blocked_count == 3


# ===========================================================================
# TestWP27ExitCriteria
# ===========================================================================

class TestWP27ExitCriteria:
    def _crls_after_n_gens(self, n: int = 10) -> InvariantCRLS:
        crls = _make_crls()
        _run_n_gens(crls, n)
        return crls

    def test_registry_constructed(self):
        crls   = self._crls_after_n_gens()
        result = verify_wp27_exit_criteria(crls)
        assert result["registry_constructed"] is True

    def test_guard_constructed(self):
        crls   = self._crls_after_n_gens()
        result = verify_wp27_exit_criteria(crls)
        assert result["guard_constructed"] is True

    def test_invariants_checked(self):
        crls   = self._crls_after_n_gens()
        result = verify_wp27_exit_criteria(crls)
        assert result["invariants_checked"] is True

    def test_all_actions_safety_gated(self):
        crls   = self._crls_after_n_gens()
        result = verify_wp27_exit_criteria(crls)
        assert result["all_actions_safety_gated"] is True

    def test_block_or_flag_observed(self):
        crls   = self._crls_after_n_gens()
        result = verify_wp27_exit_criteria(crls)
        assert result["block_or_flag_observed"] is True

    def test_safety_preserved(self):
        crls   = self._crls_after_n_gens()
        result = verify_wp27_exit_criteria(crls)
        assert result["safety_preserved"] is True

    def test_all_criteria_keys_present(self):
        crls   = self._crls_after_n_gens()
        result = verify_wp27_exit_criteria(crls)
        expected = {
            "registry_constructed",
            "guard_constructed",
            "invariants_checked",
            "all_actions_safety_gated",
            "block_or_flag_observed",
            "safety_preserved",
        }
        assert set(result.keys()) == expected
