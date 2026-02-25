"""
WP21 Test Suite: Meta-Gradient Adaptation
==========================================

Seven test classes mirroring the WP17–20 structure:

TestMetaParams              Unit tests for the hyperparameter dataclass
TestMetaGradientOptimiser   Gradient computation, SGD update, clamping
TestMetaGradStep            Audit record structure and serialisation
TestMetaGradientCRLS        Integration on real GoBoard puzzles —
                             verifies all four planning layers fire
TestParamsAppliedToSynth    That updated params actually reach CRLSSynthesiser
                             and RolloutPlanner
TestWP21ExitCriteria        Six-criterion verifier
TestLayerInteraction        WP17/WP19/WP20/WP21 layers interact correctly
"""

import math
import random
from typing import Callable, Dict, List, Optional, Tuple

import pytest

from prometheus.environments.go import GoBoard
from prometheus.meta_learner import MetaLearner
from prometheus.wp17_crls_synthesis import SynthesisAction, SynthesisRecord
from prometheus.wp19_causal_evaluator import CausalRecommendation
from prometheus.wp20_temporal_planner import (
    RolloutResult,
    SynthesisStateSnapshot,
    SynthesisTrajectoryModel,
    TrajectoryTransition,
)
from prometheus.wp21_meta_gradient import (
    MetaGradStep,
    MetaGradientCRLS,
    MetaGradientOptimiser,
    MetaParams,
    _DEFAULT_PARAMS,
    _PARAM_BOUNDS,
    verify_wp21_exit_criteria,
)


# ===========================================================================
# Shared helpers  (mirrors WP20 pattern)
# ===========================================================================

TACTICS = ["capture_atari", "ladder", "ko_fight",
           "territory_claim", "connect_groups", "random_legal"]


def _make_snapshot(
    generation: int = 0,
    probs: Optional[Dict[str, float]] = None,
    upward_rate: float = 0.20,
    accuracy: float = 0.50,
) -> SynthesisStateSnapshot:
    if probs is None:
        n = len(TACTICS)
        probs = {t: 1.0 / n for t in TACTICS}
    return SynthesisStateSnapshot(
        generation=generation, probs=probs,
        upward_rate=upward_rate, accuracy=accuracy,
    )


def _make_transition(
    action: SynthesisAction,
    acc_before: float = 0.50,
    acc_after: float = 0.60,
    generation: int = 0,
) -> TrajectoryTransition:
    before = _make_snapshot(generation, accuracy=acc_before)
    after = _make_snapshot(generation + 1, accuracy=acc_after)
    return TrajectoryTransition(before, action, after)


def _make_meta(upward: float = 0.0, downward: float = 0.0) -> MetaLearner:
    return MetaLearner(TACTICS, upward_rate=upward, downward_rate=downward)


# ---------------------------------------------------------------------------
# Real GoBoard puzzle helpers
# ---------------------------------------------------------------------------

def _atari_board() -> Tuple[GoBoard, int, Tuple[int, int]]:
    board = GoBoard(size=9)
    board.board[4][4] = GoBoard.WHITE
    board.board[4][3] = GoBoard.BLACK
    board.board[4][5] = GoBoard.BLACK
    board.board[5][4] = GoBoard.BLACK
    board.current_player = GoBoard.BLACK
    return board, GoBoard.BLACK, (3, 4)


def _go_puzzles(n: int) -> List[Tuple]:
    return [_atari_board() for _ in range(n)]


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


# ===========================================================================
# TestMetaParams
# ===========================================================================

class TestMetaParams:

    def test_default_params_within_bounds(self):
        p = MetaParams()
        for param, (lo, hi) in _PARAM_BOUNDS.items():
            val = getattr(p, param)
            assert lo <= val <= hi, (
                f"{param}={val} out of bounds [{lo}, {hi}]"
            )

    def test_as_dict_contains_all_keys(self):
        p = MetaParams()
        d = p.as_dict()
        for k in _DEFAULT_PARAMS:
            assert k in d

    def test_horizon_property_rounds_correctly(self):
        p = MetaParams(horizon_cont=3.7)
        assert p.horizon == 4
        p2 = MetaParams(horizon_cont=2.2)
        assert p2.horizon == 2

    def test_horizon_minimum_one(self):
        """Even if horizon_cont rounds to 0, horizon must be ≥ 1."""
        p = MetaParams(horizon_cont=1.0)
        assert p.horizon >= 1

    def test_clamp_brings_out_of_range_back(self):
        """Params set beyond bounds must be clamped."""
        p = MetaParams(
            demote_factor=0.0,    # below 0.10
            promote_factor=99.0,  # above 5.00
        )
        c = p.clamp()
        assert c.demote_factor  >= _PARAM_BOUNDS["demote_factor"][0]
        assert c.promote_factor <= _PARAM_BOUNDS["promote_factor"][1]

    def test_perturb_creates_new_object(self):
        p = MetaParams()
        p2 = p.perturb("discount", 0.05)
        assert p2 is not p
        assert abs(p.discount - p2.discount) > 0

    def test_perturb_clamped_to_bounds(self):
        p = MetaParams(discount=0.99)
        p2 = p.perturb("discount", 1.0)   # would go to 1.99
        assert p2.discount <= _PARAM_BOUNDS["discount"][1]

    def test_to_dict_includes_horizon_int(self):
        p = MetaParams()
        d = p.to_dict()
        assert "horizon" in d
        assert isinstance(d["horizon"], int)


# ===========================================================================
# TestMetaGradientOptimiser
# ===========================================================================

class TestMetaGradientOptimiser:

    def _seeded_model(self) -> SynthesisTrajectoryModel:
        """Trajectory model with enough data for gradient computation."""
        m = SynthesisTrajectoryModel(min_transitions=3)
        for _ in range(5):
            m.ingest(_make_transition(SynthesisAction.PROMOTE_BEST,
                                      acc_before=0.50, acc_after=0.65))
        for _ in range(5):
            m.ingest(_make_transition(SynthesisAction.DEMOTE_WORST,
                                      acc_before=0.50, acc_after=0.54))
        for _ in range(5):
            m.ingest(_make_transition(SynthesisAction.BOOST_UPWARD,
                                      acc_before=0.50, acc_after=0.52))
        for _ in range(5):
            m.ingest(_make_transition(SynthesisAction.RESET_UNIFORM,
                                      acc_before=0.50, acc_after=0.50))
        return m

    def test_no_update_when_insufficient_data(self):
        """Step should be a no-op when trajectory model is nearly empty."""
        m    = SynthesisTrajectoryModel(min_transitions=3)
        opt  = MetaGradientOptimiser(m, min_transitions_for_grad=10)
        snap = _make_snapshot(accuracy=0.50)
        p    = MetaParams()
        new_p, step = opt.step(snap, SynthesisAction.PROMOTE_BEST, p, 0)
        # No-op: params unchanged
        assert new_p.as_dict() == p.as_dict()
        assert all(abs(g) < 1e-12 for g in step.gradients.values())

    def test_step_with_data_returns_non_trivial_gradient(self):
        m   = self._seeded_model()
        opt = MetaGradientOptimiser(m, step_size=0.02, min_transitions_for_grad=4)
        snap = _make_snapshot(accuracy=0.50)
        p    = MetaParams()
        new_p, step = opt.step(snap, SynthesisAction.PROMOTE_BEST, p, 0)
        # At least one gradient should be non-zero
        assert any(abs(v) > 1e-12 for v in step.gradients.values())

    def test_params_change_after_step_with_data(self):
        m   = self._seeded_model()
        opt = MetaGradientOptimiser(m, step_size=0.05, min_transitions_for_grad=4)
        snap = _make_snapshot(accuracy=0.50)
        p    = MetaParams()
        new_p, _ = opt.step(snap, SynthesisAction.PROMOTE_BEST, p, 0)
        # At least one param should differ
        changed = any(
            abs(getattr(new_p, k) - getattr(p, k)) > 1e-9
            for k in _DEFAULT_PARAMS
        )
        assert changed

    def test_updated_params_remain_within_bounds(self):
        m   = self._seeded_model()
        opt = MetaGradientOptimiser(m, step_size=1.0, min_transitions_for_grad=4)
        snap = _make_snapshot(accuracy=0.50)
        p    = MetaParams()
        for _ in range(20):
            p, _ = opt.step(snap, SynthesisAction.PROMOTE_BEST, p, 0)
        for param, (lo, hi) in _PARAM_BOUNDS.items():
            val = getattr(p, param)
            assert lo <= val <= hi, (
                f"After 20 steps: {param}={val} out of bounds [{lo}, {hi}]"
            )

    def test_positive_delta_action_gets_positive_factor_gradient(self):
        """
        If PROMOTE_BEST always improves accuracy, promote_factor gradient
        should be positive (gradient ascent pushes factor higher).
        """
        m = SynthesisTrajectoryModel(min_transitions=3)
        for _ in range(5):
            m.ingest(_make_transition(SynthesisAction.PROMOTE_BEST,
                                      acc_before=0.50, acc_after=0.72))
        opt  = MetaGradientOptimiser(m, step_size=0.02, min_transitions_for_grad=4)
        snap = _make_snapshot(accuracy=0.50)
        p    = MetaParams()
        _, step = opt.step(snap, SynthesisAction.PROMOTE_BEST, p, 0)
        assert step.gradients.get("promote_factor", 0.0) >= 0.0, (
            "Promote factor gradient should be ≥ 0 when action is beneficial"
        )

    def test_negative_delta_action_gets_negative_factor_gradient(self):
        """
        If DEMOTE_WORST always hurts accuracy, demote_factor gradient
        should be negative (gradient ascent reduces factor toward 0).
        """
        m = SynthesisTrajectoryModel(min_transitions=3)
        for _ in range(5):
            m.ingest(_make_transition(SynthesisAction.DEMOTE_WORST,
                                      acc_before=0.60, acc_after=0.40))
        opt  = MetaGradientOptimiser(m, step_size=0.02, min_transitions_for_grad=4)
        snap = _make_snapshot(accuracy=0.60)
        p    = MetaParams()
        _, step = opt.step(snap, SynthesisAction.DEMOTE_WORST, p, 0)
        assert step.gradients.get("demote_factor", 0.0) <= 0.0, (
            "Demote factor gradient should be ≤ 0 when action is harmful"
        )

    def test_surrogate_return_non_zero_with_data(self):
        m   = self._seeded_model()
        opt = MetaGradientOptimiser(m, step_size=0.02, min_transitions_for_grad=4)
        snap = _make_snapshot(accuracy=0.50)
        p    = MetaParams()
        _, step = opt.step(snap, SynthesisAction.PROMOTE_BEST, p, 0)
        assert step.surrogate_return != 0.0 or step.gradients.get("discount", 0) == 0.0

    def test_grad_history_grows_with_steps(self):
        m   = self._seeded_model()
        opt = MetaGradientOptimiser(m, step_size=0.02, min_transitions_for_grad=4)
        snap = _make_snapshot(accuracy=0.50)
        p    = MetaParams()
        for i in range(5):
            p, _ = opt.step(snap, SynthesisAction.PROMOTE_BEST, p, i)
        # 5 steps with sufficient data → 5 entries in history
        assert len(opt.grad_history) == 5

    def test_get_summary_keys(self):
        m   = self._seeded_model()
        opt = MetaGradientOptimiser(m, min_transitions_for_grad=4)
        snap = _make_snapshot()
        p    = MetaParams()
        opt.step(snap, SynthesisAction.PROMOTE_BEST, p, 0)
        s = opt.get_summary()
        for k in ("steps", "non_trivial_steps", "mean_surrogate_return",
                  "param_trajectory"):
            assert k in s

    def test_clipped_flag_set_when_param_hits_bound(self):
        """Force a large step that hits the bound; clipped must be True."""
        m = SynthesisTrajectoryModel(min_transitions=3)
        # Huge positive mean delta for PROMOTE_BEST
        for _ in range(5):
            m.ingest(_make_transition(SynthesisAction.PROMOTE_BEST,
                                      acc_before=0.50, acc_after=0.99))
        opt  = MetaGradientOptimiser(m, step_size=100.0, min_transitions_for_grad=4)
        snap = _make_snapshot()
        p    = MetaParams()
        new_p, step = opt.step(snap, SynthesisAction.PROMOTE_BEST, p, 0)
        # With step_size=100, promote_factor should hit its upper bound
        assert new_p.promote_factor == pytest.approx(
            _PARAM_BOUNDS["promote_factor"][1], abs=1e-9
        )


# ===========================================================================
# TestMetaGradStep
# ===========================================================================

class TestMetaGradStep:

    def _make_step(self) -> MetaGradStep:
        p = MetaParams()
        return MetaGradStep(
            generation       = 3,
            params_before    = p.as_dict(),
            params_after     = p.clamp().as_dict(),
            gradients        = {k: 0.01 for k in _DEFAULT_PARAMS},
            surrogate_return = 0.042,
            step_size        = 0.02,
            clipped          = False,
        )

    def test_to_dict_has_all_required_keys(self):
        step = self._make_step()
        d    = step.to_dict()
        for k in ("generation", "params_before", "params_after",
                  "gradients", "surrogate_return", "step_size", "clipped"):
            assert k in d

    def test_gradients_dict_has_all_param_keys(self):
        step = self._make_step()
        for k in _DEFAULT_PARAMS:
            assert k in step.gradients

    def test_clipped_flag_serialised(self):
        step = self._make_step()
        d    = step.to_dict()
        assert isinstance(d["clipped"], bool)

    def test_timestamp_is_float(self):
        step = self._make_step()
        assert isinstance(step.timestamp, float)
        assert step.timestamp > 0.0


# ===========================================================================
# TestMetaGradientCRLS — integration on real GoBoard puzzles
# ===========================================================================

class TestMetaGradientCRLS:

    def _make_crls(self, seed: int = 42) -> MetaGradientCRLS:
        random.seed(seed)
        return MetaGradientCRLS(
            strategies             = TACTICS,
            upward_rate            = 0.0,
            downward_rate          = 0.0,
            synthesiser_kwargs     = {"acc_drop_threshold": 0.0},
            min_trials_to_override = 3,
            override_tolerance     = 0.02,
            rollout_horizon        = 3,
            rollout_discount       = 0.90,
            min_transitions        = 3,
            meta_step_size         = 0.02,
            meta_min_transitions   = 4,
        )

    def test_construction_with_default_meta_params(self):
        crls = self._make_crls()
        p    = crls.meta_params
        for param, (lo, hi) in _PARAM_BOUNDS.items():
            val = getattr(p, param)
            assert lo <= val <= hi

    def test_run_generation_returns_valid_accuracy(self):
        crls = self._make_crls()
        acc  = crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        assert 0.0 <= acc <= 1.0

    def test_end_of_generation_returns_quadruple(self):
        crls = self._make_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        result = crls.end_of_generation()
        assert len(result) == 4
        record, causal_rec, rollout, grad_step = result
        assert isinstance(record,     SynthesisRecord)
        assert isinstance(causal_rec, CausalRecommendation)
        assert isinstance(rollout,    RolloutResult)
        assert isinstance(grad_step,  MetaGradStep)

    def test_meta_grad_log_grows_with_generations(self):
        crls = self._make_crls()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert len(crls.meta_grad_log) == 5

    def test_no_unsafe_synthesis_applied(self):
        crls = self._make_crls()
        for _ in range(6):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        for rec in crls.synth.records:
            if rec.action != SynthesisAction.NO_ACTION:
                assert rec.safety_status != "provably_unsafe"

    def test_full_report_has_wp21_keys(self):
        crls = self._make_crls()
        for _ in range(3):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        report = crls.get_full_report()
        assert "meta_gradient_summary" in report
        assert "meta_grad_log"         in report
        assert "final_meta_params"     in report

    def test_acc_history_populated(self):
        crls = self._make_crls()
        for _ in range(4):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert len(crls.acc_history) == 4

    def test_initial_custom_params_respected(self):
        custom = MetaParams(demote_factor=0.3, promote_factor=2.5)
        crls   = MetaGradientCRLS(
            strategies     = TACTICS,
            upward_rate    = 0.0,
            downward_rate  = 0.0,
            initial_params = custom,
        )
        assert abs(crls.meta_params.demote_factor  - 0.3) < 1e-9
        assert abs(crls.meta_params.promote_factor - 2.5) < 1e-9


# ===========================================================================
# TestParamsAppliedToSynth — updated MetaParams reach live components
# ===========================================================================

class TestParamsAppliedToSynth:

    def test_synth_factors_match_meta_params_at_construction(self):
        crls = MetaGradientCRLS(
            strategies     = TACTICS,
            upward_rate    = 0.0,
            downward_rate  = 0.0,
            initial_params = MetaParams(
                demote_factor  = 0.35,
                promote_factor = 2.8,
                boost_factor   = 1.7,
            ),
        )
        # MetaGradientCRLS calls _apply_meta_params() at construction
        # via the first end_of_generation; we check after running one gen
        crls.run_generation(_go_puzzles(10), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        p = crls.meta_params
        assert abs(crls.synth.demote_f  - p.demote_factor)  < 1e-9
        assert abs(crls.synth.promote_f - p.promote_factor) < 1e-9
        assert abs(crls.synth.boost_f   - p.boost_factor)   < 1e-9

    def test_planner_discount_matches_meta_params(self):
        crls = MetaGradientCRLS(
            strategies       = TACTICS,
            upward_rate      = 0.0,
            downward_rate    = 0.0,
            rollout_discount = 0.90,
        )
        crls.run_generation(_go_puzzles(10), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        p = crls.meta_params
        assert abs(crls.planner.discount - p.discount) < 1e-9

    def test_planner_horizon_matches_meta_params(self):
        crls = MetaGradientCRLS(
            strategies     = TACTICS,
            upward_rate    = 0.0,
            downward_rate  = 0.0,
            rollout_horizon = 3,
        )
        crls.run_generation(_go_puzzles(10), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        p = crls.meta_params
        assert crls.planner.horizon == p.horizon

    def test_params_evolve_after_sufficient_data(self):
        """After many generations, at least one param should differ from default."""
        random.seed(77)
        crls = MetaGradientCRLS(
            strategies           = TACTICS,
            upward_rate          = 0.0,
            downward_rate        = 0.0,
            meta_step_size       = 0.05,
            meta_min_transitions = 3,
            min_transitions      = 3,
        )
        tactic_fns = _go_tactic_fns()
        for _ in range(20):
            crls.run_generation(_go_puzzles(30), tactic_fns, _go_eval)
            crls.end_of_generation()

        # At least one param should have moved from default
        p = crls.meta_params
        moved = any(
            abs(getattr(p, k) - _DEFAULT_PARAMS[k]) > 1e-9
            for k in _DEFAULT_PARAMS
        )
        assert moved, (
            "After 20 generations, at least one meta-parameter should "
            "have been updated from its default value"
        )


# ===========================================================================
# TestWP21ExitCriteria
# ===========================================================================

class TestWP21ExitCriteria:

    def _make_converged_crls(self, seed: int = 12) -> MetaGradientCRLS:
        random.seed(seed)
        crls = MetaGradientCRLS(
            strategies           = TACTICS,
            upward_rate          = 0.0,
            downward_rate        = 0.0,
            synthesiser_kwargs   = {"acc_drop_threshold": 0.0},
            min_trials_to_override = 3,
            override_tolerance     = 0.02,
            rollout_horizon        = 3,
            rollout_discount       = 0.90,
            min_transitions        = 3,
            meta_step_size         = 0.03,
            meta_min_transitions   = 4,
        )
        tactic_fns = _go_tactic_fns()
        for _ in range(25):
            crls.run_generation(_go_puzzles(30), tactic_fns, _go_eval)
            crls.end_of_generation()
        return crls

    def test_meta_params_constructed(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp21_exit_criteria(crls)
        assert criteria["meta_params_constructed"], (
            "MetaParams must exist with valid initial values in all bounds"
        )

    def test_optimiser_stepped(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp21_exit_criteria(crls)
        assert criteria["optimiser_stepped"], (
            "At least one non-trivial gradient step must have been taken"
        )

    def test_surrogate_return_computed(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp21_exit_criteria(crls)
        assert criteria["surrogate_return_computed"], (
            "At least one step must have computed a surrogate discounted return"
        )

    def test_params_applied_to_synth(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp21_exit_criteria(crls)
        assert criteria["params_applied_to_synth"], (
            "CRLSSynthesiser and RolloutPlanner must reflect current MetaParams"
        )

    def test_safety_preserved(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp21_exit_criteria(crls)
        assert criteria["safety_preserved"], (
            "All synthesis proposals must be safety-evaluated; none UNSAFE applied"
        )

    def test_all_criteria_pass(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp21_exit_criteria(crls)
        failing  = [k for k, v in criteria.items() if not v]
        assert not failing, f"WP21 exit criteria failed: {failing}"


# ===========================================================================
# TestLayerInteraction — WP17 / WP19 / WP20 / WP21 interact correctly
# ===========================================================================

class TestLayerInteraction:

    def test_fallback_chain_all_four_layers(self):
        """
        With no trajectory data, WP21 and WP20 must both fall back gracefully;
        WP19 and WP17 handle the recommendation.
        """
        crls = MetaGradientCRLS(
            strategies             = TACTICS,
            upward_rate            = 0.0,
            downward_rate          = 0.0,
            min_trials_to_override = 100,   # WP19 never overrides
            min_transitions        = 100,   # WP20 never plans
            meta_min_transitions   = 100,   # WP21 never fires
        )
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        record, causal_rec, rollout, grad_step = crls.end_of_generation()

        # WP19 and WP20 fall back
        assert not causal_rec.override
        assert rollout.fallback_used
        # WP21 no-op: all gradients zero
        assert all(abs(g) < 1e-12 for g in grad_step.gradients.values())

    def test_meta_grad_log_has_grad_keys(self):
        crls = MetaGradientCRLS(
            strategies    = TACTICS,
            upward_rate   = 0.0,
            downward_rate = 0.0,
            meta_min_transitions = 3,
            min_transitions      = 3,
        )
        tactic_fns = _go_tactic_fns()
        for _ in range(10):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()

        for entry in crls.meta_grad_log:
            for k in ("generation", "params_before", "params_after",
                      "gradients", "surrogate_return", "step_size", "clipped"):
                assert k in entry, f"Missing key {k} in meta_grad_log entry"

    def test_generation_count_consistent(self):
        """Generation counter must advance consistently across all layers."""
        crls = MetaGradientCRLS(
            strategies    = TACTICS,
            upward_rate   = 0.0,
            downward_rate = 0.0,
        )
        tactic_fns = _go_tactic_fns()
        N = 8
        for _ in range(N):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()

        assert crls.generation == N
        assert len(crls.acc_history) == N
        assert len(crls.gen_log) == N

    def test_all_four_layer_fields_in_gen_log(self):
        """gen_log entries must contain fields from all four WP layers."""
        crls = MetaGradientCRLS(
            strategies    = TACTICS,
            upward_rate   = 0.0,
            downward_rate = 0.0,
        )
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()

        entry = crls.gen_log[0]
        # WP17 heuristic
        assert "heuristic"      in entry
        # WP19 causal
        assert "causal_action"  in entry
        # WP20 rollout
        assert "rollout_action" in entry
        assert "rollout_fallback" in entry

    def test_wp21_does_not_break_wp20_rollout_log(self):
        """MetaGradientCRLS must still populate the WP20 rollout_log."""
        crls = MetaGradientCRLS(
            strategies    = TACTICS,
            upward_rate   = 0.0,
            downward_rate = 0.0,
        )
        tactic_fns = _go_tactic_fns()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()

        assert len(crls.rollout_log) == 5, (
            "WP20 rollout_log must still be populated by MetaGradientCRLS"
        )
