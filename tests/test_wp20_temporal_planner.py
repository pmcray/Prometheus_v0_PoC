"""
WP20 Test Suite: Temporal Synthesis Planner
=============================================

Six test classes mirroring the WP17–19 structure:

TestSynthesisStateSnapshot      Unit tests for state vector dataclass
TestSynthesisTrajectoryModel    Transition ingestion, prediction accuracy,
                                 multi-step rollout
TestRolloutPlanner              Fallback logic, greedy rollout, discount
TestTemporalCRLS                Integration on real GoBoard puzzles —
                                 verifies all three planning layers fire
TestWP20ExitCriteria            Six-criterion verifier
TestLayerInteraction            That WP17/WP19/WP20 layers interact correctly
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
    RolloutPlanner,
    RolloutResult,
    SynthesisStateSnapshot,
    SynthesisTrajectoryModel,
    TemporalCRLS,
    TrajectoryTransition,
    verify_wp20_exit_criteria,
)


# ===========================================================================
# Shared helpers
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
    acc_after: float  = 0.60,
    generation: int   = 0,
) -> TrajectoryTransition:
    n = len(TACTICS)
    base_p = 1.0 / n
    before = _make_snapshot(generation, accuracy=acc_before)
    after  = _make_snapshot(generation + 1, accuracy=acc_after)
    return TrajectoryTransition(before, action, after)


def _make_record(
    action: SynthesisAction,
    acc_before: float,
    improvement: float,
    generation: int = 0,
) -> SynthesisRecord:
    acc_after = acc_before + improvement
    return SynthesisRecord(
        generation    = generation,
        action        = action,
        trigger       = "test",
        before_probs  = {t: 1.0 / len(TACTICS) for t in TACTICS},
        after_probs   = {t: 1.0 / len(TACTICS) for t in TACTICS},
        before_upward = 0.20,
        after_upward  = 0.20,
        safety_status = "provably_safe",
        safety_reason = "rule_add",
        acc_before    = acc_before,
        acc_after     = acc_after,
        improvement   = improvement,
    )


def _make_meta(upward: float = 0.0, downward: float = 0.0) -> MetaLearner:
    return MetaLearner(TACTICS, upward_rate=upward, downward_rate=downward)


# ---------------------------------------------------------------------------
# Real GoBoard puzzle helpers (mirror WP17/19 pattern)
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
# TestSynthesisStateSnapshot
# ===========================================================================

class TestSynthesisStateSnapshot:

    def test_from_meta_and_acc(self):
        meta = _make_meta()
        snap = SynthesisStateSnapshot.from_meta_and_acc(0, meta, 0.65)
        assert snap.generation == 0
        assert snap.accuracy   == pytest.approx(0.65)
        assert abs(sum(snap.probs.values()) - 1.0) < 1e-9

    def test_as_vector_length(self):
        snap = _make_snapshot(probs={t: 1/6 for t in TACTICS})
        vec  = snap.as_vector()
        # 6 probs + upward_rate + accuracy = 8
        assert len(vec) == len(TACTICS) + 2

    def test_as_vector_ends_with_acc(self):
        snap = _make_snapshot(accuracy=0.77)
        vec  = snap.as_vector()
        assert vec[-1] == pytest.approx(0.77)

    def test_to_dict_keys(self):
        snap = _make_snapshot()
        d    = snap.to_dict()
        for k in ("generation", "probs", "upward_rate", "accuracy"):
            assert k in d

    def test_probs_sum_to_one(self):
        snap = _make_snapshot()
        assert abs(sum(snap.probs.values()) - 1.0) < 1e-9


# ===========================================================================
# TestSynthesisTrajectoryModel
# ===========================================================================

class TestSynthesisTrajectoryModel:

    def _model_with_data(
        self,
        action: SynthesisAction,
        deltas: List[float],
        min_transitions: int = 3,
    ) -> SynthesisTrajectoryModel:
        m = SynthesisTrajectoryModel(min_transitions=min_transitions)
        for d in deltas:
            m.ingest(_make_transition(action, acc_before=0.50, acc_after=0.50 + d))
        return m

    def test_ingest_adds_transition(self):
        m = SynthesisTrajectoryModel()
        m.ingest(_make_transition(SynthesisAction.DEMOTE_WORST))
        assert m.n_transitions(SynthesisAction.DEMOTE_WORST) == 1

    def test_mean_acc_delta_correct(self):
        m = self._model_with_data(
            SynthesisAction.PROMOTE_BEST, [0.10, 0.12, 0.08]
        )
        expected = 0.10
        assert abs(m.mean_acc_delta(SynthesisAction.PROMOTE_BEST) - expected) < 0.01

    def test_mean_acc_delta_zero_for_unseen_action(self):
        m = SynthesisTrajectoryModel()
        assert m.mean_acc_delta(SynthesisAction.RESET_UNIFORM) == 0.0

    def test_can_predict_false_below_min(self):
        m = SynthesisTrajectoryModel(min_transitions=3)
        m.ingest(_make_transition(SynthesisAction.BOOST_UPWARD))
        m.ingest(_make_transition(SynthesisAction.BOOST_UPWARD))
        assert not m.can_predict(SynthesisAction.BOOST_UPWARD)

    def test_can_predict_true_at_min(self):
        m = SynthesisTrajectoryModel(min_transitions=3)
        for _ in range(3):
            m.ingest(_make_transition(SynthesisAction.BOOST_UPWARD))
        assert m.can_predict(SynthesisAction.BOOST_UPWARD)

    def test_predict_one_step_accuracy(self):
        """Predicted accuracy should match observed mean delta."""
        m = self._model_with_data(SynthesisAction.DEMOTE_WORST, [0.10, 0.10, 0.10])
        snap = _make_snapshot(accuracy=0.50)
        pred_state, conf = m.predict_one_step(snap, SynthesisAction.DEMOTE_WORST, 0)
        assert abs(pred_state.accuracy - 0.60) < 0.01
        assert conf > 0.0

    def test_predict_one_step_probs_sum_to_one(self):
        m = self._model_with_data(SynthesisAction.DEMOTE_WORST, [0.05, 0.05, 0.05])
        snap = _make_snapshot(accuracy=0.50)
        pred_state, _ = m.predict_one_step(snap, SynthesisAction.DEMOTE_WORST, 0)
        assert abs(sum(pred_state.probs.values()) - 1.0) < 1e-9

    def test_predict_one_step_zero_confidence_no_data(self):
        m = SynthesisTrajectoryModel()
        snap = _make_snapshot(accuracy=0.50)
        _, conf = m.predict_one_step(snap, SynthesisAction.RESET_UNIFORM, 0)
        assert conf == 0.0

    def test_predict_k_steps_returns_k_states(self):
        m = self._model_with_data(SynthesisAction.DEMOTE_WORST, [0.05]*5)
        snap = _make_snapshot(accuracy=0.50)
        sequence = [SynthesisAction.DEMOTE_WORST] * 3
        traj = m.predict_k_steps(snap, sequence)
        assert len(traj) == 3

    def test_multi_step_accuracy_increases_monotonically(self):
        """If each action has positive delta, accuracy should rise."""
        m = self._model_with_data(SynthesisAction.PROMOTE_BEST, [0.10]*4)
        snap = _make_snapshot(accuracy=0.40)
        sequence = [SynthesisAction.PROMOTE_BEST] * 3
        traj = m.predict_k_steps(snap, sequence)
        accs = [s.accuracy for s, _ in traj]
        for i in range(1, len(accs)):
            assert accs[i] >= accs[i - 1] - 1e-9

    def test_confidence_decays_over_horizon(self):
        m = SynthesisTrajectoryModel(min_transitions=1, confidence_decay=0.85)
        for _ in range(3):
            m.ingest(_make_transition(SynthesisAction.DEMOTE_WORST))
        snap = _make_snapshot(accuracy=0.50)
        sequence = [SynthesisAction.DEMOTE_WORST] * 3
        traj = m.predict_k_steps(snap, sequence)
        confs = [c for _, c in traj]
        # Should be non-increasing
        for i in range(1, len(confs)):
            assert confs[i] <= confs[i - 1] + 1e-9

    def test_ingest_record_pair_builds_transition(self):
        m   = SynthesisTrajectoryModel()
        rec = _make_record(SynthesisAction.BOOST_UPWARD, 0.50, 0.12)
        t   = m.ingest_record_pair(rec)
        assert t is not None
        assert m.n_transitions(SynthesisAction.BOOST_UPWARD) == 1

    def test_ingest_record_pair_none_when_incomplete(self):
        m   = SynthesisTrajectoryModel()
        rec = SynthesisRecord(
            generation=0, action=SynthesisAction.DEMOTE_WORST, trigger="x",
            before_probs={t: 1/6 for t in TACTICS},
            after_probs ={t: 1/6 for t in TACTICS},
            before_upward=0.2, after_upward=0.2,
            safety_status="provably_safe", safety_reason="ok",
            acc_before=0.5, acc_after=None, improvement=None,
        )
        t = m.ingest_record_pair(rec)
        assert t is None

    def test_get_summary_structure(self):
        m = self._model_with_data(SynthesisAction.DEMOTE_WORST, [0.05, 0.06, 0.07])
        s = m.get_summary()
        assert "transitions_per_action"    in s
        assert "mean_acc_delta_per_action" in s
        assert "can_predict"               in s


# ===========================================================================
# TestRolloutPlanner
# ===========================================================================

class TestRolloutPlanner:

    def _make_planner(self, horizon: int = 3) -> Tuple[SynthesisTrajectoryModel, RolloutPlanner]:
        m = SynthesisTrajectoryModel(min_transitions=3)
        p = RolloutPlanner(m, horizon=horizon, discount=0.90, min_actions_with_data=2)
        return m, p

    def _seed_model(
        self,
        model: SynthesisTrajectoryModel,
        action: SynthesisAction,
        delta: float,
        n: int = 4,
    ) -> None:
        for _ in range(n):
            model.ingest(_make_transition(action, acc_before=0.50, acc_after=0.50 + delta))

    def test_fallback_when_insufficient_data(self):
        m, p = self._make_planner()
        # Only 1 action has data → fallback
        self._seed_model(m, SynthesisAction.DEMOTE_WORST, 0.10, n=4)
        snap   = _make_snapshot(accuracy=0.50)
        result = p.plan(snap, SynthesisAction.DEMOTE_WORST)
        assert result.fallback_used is True
        assert result.best_action == SynthesisAction.DEMOTE_WORST

    def test_no_fallback_with_two_actions(self):
        m, p = self._make_planner()
        self._seed_model(m, SynthesisAction.DEMOTE_WORST, 0.05, n=4)
        self._seed_model(m, SynthesisAction.PROMOTE_BEST, 0.12, n=4)
        snap   = _make_snapshot(accuracy=0.50)
        result = p.plan(snap, SynthesisAction.DEMOTE_WORST)
        assert result.fallback_used is False

    def test_higher_delta_action_wins(self):
        """PROMOTE_BEST has much higher delta → should be chosen."""
        m, p = self._make_planner()
        self._seed_model(m, SynthesisAction.DEMOTE_WORST, 0.03, n=4)
        self._seed_model(m, SynthesisAction.PROMOTE_BEST, 0.15, n=4)
        snap   = _make_snapshot(accuracy=0.50)
        result = p.plan(snap, SynthesisAction.DEMOTE_WORST)
        assert result.best_action == SynthesisAction.PROMOTE_BEST

    def test_negative_delta_action_not_chosen(self):
        """A harmful action should not beat a neutral one."""
        m, p = self._make_planner()
        self._seed_model(m, SynthesisAction.DEMOTE_WORST, -0.10, n=4)  # harmful
        self._seed_model(m, SynthesisAction.PROMOTE_BEST,  0.05, n=4)  # helpful
        snap   = _make_snapshot(accuracy=0.50)
        result = p.plan(snap, SynthesisAction.PROMOTE_BEST)
        assert result.best_action != SynthesisAction.DEMOTE_WORST

    def test_expected_return_positive_for_helpful_action(self):
        m, p = self._make_planner()
        self._seed_model(m, SynthesisAction.DEMOTE_WORST, 0.10, n=4)
        self._seed_model(m, SynthesisAction.PROMOTE_BEST, 0.08, n=4)
        snap   = _make_snapshot(accuracy=0.50)
        result = p.plan(snap, SynthesisAction.DEMOTE_WORST)
        assert result.expected_return > 0.0

    def test_action_returns_populated_on_success(self):
        m, p = self._make_planner()
        self._seed_model(m, SynthesisAction.DEMOTE_WORST, 0.08, n=4)
        self._seed_model(m, SynthesisAction.BOOST_UPWARD, 0.06, n=4)
        snap   = _make_snapshot(accuracy=0.50)
        result = p.plan(snap, SynthesisAction.DEMOTE_WORST)
        assert len(result.action_returns) >= 2

    def test_trajectory_length_equals_horizon(self):
        m, p = self._make_planner(horizon=3)
        self._seed_model(m, SynthesisAction.DEMOTE_WORST, 0.05, n=4)
        self._seed_model(m, SynthesisAction.PROMOTE_BEST, 0.07, n=4)
        snap   = _make_snapshot(accuracy=0.50)
        result = p.plan(snap, SynthesisAction.DEMOTE_WORST)
        if not result.fallback_used:
            assert len(result.trajectory) == 3

    def test_to_dict_structure(self):
        m, p = self._make_planner()
        self._seed_model(m, SynthesisAction.DEMOTE_WORST, 0.05, n=4)
        self._seed_model(m, SynthesisAction.PROMOTE_BEST, 0.10, n=4)
        snap   = _make_snapshot(accuracy=0.50)
        result = p.plan(snap, SynthesisAction.DEMOTE_WORST)
        d      = result.to_dict()
        for key in ("best_action", "expected_return", "horizon",
                    "fallback_used", "action_returns"):
            assert key in d


# ===========================================================================
# TestTemporalCRLS — integration on real GoBoard puzzles
# ===========================================================================

class TestTemporalCRLS:

    def _make_crls(self, seed: int = 42) -> TemporalCRLS:
        random.seed(seed)
        return TemporalCRLS(
            strategies             = TACTICS,
            upward_rate            = 0.0,
            downward_rate          = 0.0,
            synthesiser_kwargs     = {"acc_drop_threshold": 0.0},
            min_trials_to_override = 3,
            override_tolerance     = 0.02,
            rollout_horizon        = 3,
            rollout_discount       = 0.90,
            min_transitions        = 3,
        )

    def test_run_generation_returns_valid_accuracy(self):
        crls = self._make_crls()
        acc  = crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        assert 0.0 <= acc <= 1.0

    def test_end_of_generation_returns_triple(self):
        crls = self._make_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        result = crls.end_of_generation()
        record, causal_rec, rollout = result
        assert isinstance(record, SynthesisRecord)
        assert isinstance(causal_rec, CausalRecommendation)
        assert isinstance(rollout, RolloutResult)

    def test_rollout_log_populated_after_generations(self):
        crls = self._make_crls()
        for _ in range(4):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert len(crls.rollout_log) == 4

    def test_gen_log_has_three_layer_fields(self):
        crls = self._make_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        entry = crls.gen_log[0]
        for field in ("heuristic", "causal_action", "rollout_action",
                      "rollout_fallback"):
            assert field in entry, f"Missing field: {field}"

    def test_trajectory_model_gets_transitions_over_time(self):
        crls = self._make_crls()
        for _ in range(8):
            crls.run_generation(_go_puzzles(25), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()

        total = sum(
            crls.traj_model.n_transitions(a)
            for a in SynthesisAction
        )
        assert total > 0, "Trajectory model should have at least one transition"

    def test_no_unsafe_synthesis_applied(self):
        crls = self._make_crls()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        for rec in crls.synth.records:
            if rec.action != SynthesisAction.NO_ACTION:
                assert rec.safety_status != "provably_unsafe"

    def test_full_report_has_wp20_keys(self):
        crls = self._make_crls()
        for _ in range(3):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        report = crls.get_full_report()
        assert "trajectory_model_summary" in report
        assert "rollout_log"              in report

    def test_rollout_overrides_when_data_sufficient(self):
        """
        Seed trajectory model synthetically so PROMOTE_BEST is clearly best,
        force a big accuracy drop so heuristic picks DEMOTE_WORST,
        verify rollout overrides.
        """
        random.seed(5)
        crls = TemporalCRLS(
            strategies             = TACTICS,
            upward_rate            = 0.0,
            downward_rate          = 0.0,
            synthesiser_kwargs     = {"acc_drop_threshold": 0.0},
            min_trials_to_override = 3,
            override_tolerance     = 0.01,
            rollout_horizon        = 2,
            rollout_discount       = 0.90,
            min_transitions        = 3,
        )

        # Seed trajectory model: PROMOTE_BEST much better than DEMOTE_WORST
        for _ in range(4):
            crls.traj_model.ingest(
                _make_transition(SynthesisAction.PROMOTE_BEST,
                                 acc_before=0.5, acc_after=0.70)
            )
        for _ in range(4):
            crls.traj_model.ingest(
                _make_transition(SynthesisAction.DEMOTE_WORST,
                                 acc_before=0.5, acc_after=0.52)
            )

        # Run a generation, then fake a big drop so heuristic picks DEMOTE_WORST
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.acc_history.append(0.20)   # simulate big drop

        _, _, rollout = crls.end_of_generation()
        if not rollout.fallback_used:
            assert rollout.best_action == SynthesisAction.PROMOTE_BEST, (
                "Rollout should override DEMOTE_WORST with PROMOTE_BEST"
            )


# ===========================================================================
# TestWP20ExitCriteria
# ===========================================================================

class TestWP20ExitCriteria:

    def _make_converged_crls(self, seed: int = 9) -> TemporalCRLS:
        random.seed(seed)
        crls = TemporalCRLS(
            strategies             = TACTICS,
            upward_rate            = 0.0,
            downward_rate          = 0.0,
            synthesiser_kwargs     = {"acc_drop_threshold": 0.0},
            min_trials_to_override = 3,
            override_tolerance     = 0.02,
            rollout_horizon        = 3,
            rollout_discount       = 0.90,
            min_transitions        = 3,
        )

        tactic_fns = _go_tactic_fns()
        for _ in range(20):
            crls.run_generation(_go_puzzles(30), tactic_fns, _go_eval)
            crls.end_of_generation()

        return crls

    def test_trajectory_model_trained(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp20_exit_criteria(crls)
        assert criteria["trajectory_model_trained"], (
            "Trajectory model must have ≥ min_transitions for at least one action"
        )

    def test_layers_all_active(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp20_exit_criteria(crls)
        assert criteria["layers_all_active"], (
            "All three planning layers (WP17/WP19/WP20) must be logged"
        )

    def test_safety_preserved(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp20_exit_criteria(crls)
        assert criteria["safety_preserved"], (
            "All synthesis proposals must be safety-evaluated; none UNSAFE applied"
        )

    def test_rollout_planned_after_enough_data(self):
        """After 12 generations, at least one non-fallback rollout should occur."""
        crls     = self._make_converged_crls()
        criteria = verify_wp20_exit_criteria(crls)
        assert criteria["rollout_planned"], (
            "At least one non-fallback rollout must have been executed"
        )

    def test_all_criteria_pass(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp20_exit_criteria(crls)
        failing  = [k for k, v in criteria.items() if not v]
        assert not failing, f"WP20 exit criteria failed: {failing}"


# ===========================================================================
# TestLayerInteraction — WP17 / WP19 / WP20 interact correctly
# ===========================================================================

class TestLayerInteraction:

    def test_fallback_chain_wp20_to_wp19_to_wp17(self):
        """
        With zero data in all layers, the recommendation must be the WP17
        heuristic (all layers fall back gracefully).
        """
        crls = TemporalCRLS(
            strategies             = TACTICS,
            upward_rate            = 0.0,
            downward_rate          = 0.0,
            min_trials_to_override = 100,   # WP19 never overrides
            min_transitions        = 100,    # WP20 never plans
        )
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        record, causal_rec, rollout = crls.end_of_generation()

        # Both WP19 and WP20 should fall back
        assert not causal_rec.override
        assert rollout.fallback_used

    def test_rollout_result_action_appears_in_record(self):
        """
        The action in the synthesis record must match the rollout or causal
        recommendation (or NO_ACTION if safety blocked).
        """
        crls = TemporalCRLS(
            strategies         = TACTICS,
            upward_rate        = 0.0,
            downward_rate      = 0.0,
            min_transitions    = 1,
            rollout_horizon    = 2,
        )
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)

        # Seed enough data
        for _ in range(2):
            crls.traj_model.ingest(
                _make_transition(SynthesisAction.PROMOTE_BEST, 0.5, 0.65)
            )
        for _ in range(2):
            crls.traj_model.ingest(
                _make_transition(SynthesisAction.DEMOTE_WORST, 0.5, 0.55)
            )

        record, causal_rec, rollout = crls.end_of_generation()
        # Record must use rollout action (or NO_ACTION if safety-blocked)
        valid_actions = {rollout.best_action, SynthesisAction.NO_ACTION}
        assert record.action in valid_actions

    def test_wp19_evaluator_receives_completed_records(self):
        """
        WP19 evaluator's outcome table must grow as generations complete.
        """
        crls = TemporalCRLS(
            strategies    = TACTICS,
            upward_rate   = 0.0,
            downward_rate = 0.0,
            min_transitions = 2,
        )
        tactic_fns = _go_tactic_fns()
        for _ in range(6):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()

        total_obs = sum(
            crls.evaluator.table.n_trials(a) for a in SynthesisAction
        )
        assert total_obs > 0, "WP19 evaluator must receive observations"
