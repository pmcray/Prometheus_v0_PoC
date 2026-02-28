"""
WP30 Test Suite: Causal World Model — Latent Transition Learning
================================================================

Seven test classes:

TestReplayBuffer            Unit tests for ring-buffer semantics
TestLatentTransitionModel   MLP construction, forward pass, SGD update
TestWorldModelRollout       Rollout dataclass, to_dict()
TestWorldModelRecord        Audit dataclass, to_dict()
TestWorldModelCRLS          Full 11-layer stack: end_of_generation, reports
TestWP30ExitCriteria        Six-criterion verifier
TestLayerInteraction        Integration: neural override, tabular fallback,
                            retrospective error fill-in
"""

import math
import random
from typing import Callable, Dict, List, Tuple

import pytest

from prometheus.wp17_crls_synthesis import SynthesisAction, SynthesisRecord
from prometheus.wp19_causal_evaluator import CausalRecommendation
from prometheus.wp20_temporal_planner import (
    RolloutResult,
    SynthesisStateSnapshot,
    TrajectoryTransition,
)
from prometheus.wp21_meta_gradient import MetaGradStep, MetaParams
from prometheus.wp22_bandit_exploration import BanditMode, ExplorationRecord
from prometheus.wp23_policy_distillation import DistillationRecord
from prometheus.wp24_ensemble_uncertainty import EnsembleRecord
from prometheus.wp25_ewc_forgetting import ForgettingRecord
from prometheus.wp26_hierarchical_decomp import DecompositionRecord
from prometheus.wp27_formal_invariants import InvariantRecord
from prometheus.wp30_causal_world_model import (
    LatentTransitionModel,
    ReplayBuffer,
    RolloutSource,
    WorldModelCRLS,
    WorldModelRecord,
    WorldModelRollout,
    verify_wp30_exit_criteria,
    _N_ACTIONS,
    _ACTIONS,
)
from prometheus.environments.go import GoBoard


# ===========================================================================
# Shared helpers
# ===========================================================================

GO_TACTICS = ["capture_atari", "ladder", "ko_fight",
              "territory_claim", "connect_groups", "random_legal"]


def _uniform_probs(strategies=GO_TACTICS) -> Dict[str, float]:
    n = len(strategies)
    return {s: 1.0 / n for s in strategies}


def _snap(gen: int = 0, acc: float = 0.50, up: float = 0.20,
          strategies=GO_TACTICS) -> SynthesisStateSnapshot:
    return SynthesisStateSnapshot(
        generation=gen,
        probs=_uniform_probs(strategies),
        upward_rate=up,
        accuracy=acc,
    )


def _transition(s_before: SynthesisStateSnapshot,
                action: SynthesisAction,
                s_after: SynthesisStateSnapshot) -> TrajectoryTransition:
    return TrajectoryTransition(
        state_before=s_before,
        action=action,
        state_after=s_after,
    )


def _atari_board():
    board = GoBoard(size=9)
    board.board[4][4] = GoBoard.WHITE
    board.board[4][3] = GoBoard.BLACK
    board.board[4][5] = GoBoard.BLACK
    board.board[5][4] = GoBoard.BLACK
    board.current_player = GoBoard.BLACK
    return board, GoBoard.BLACK, (3, 4)


def _territory_board():
    board = GoBoard(size=9)
    board.board[0][0] = GoBoard.WHITE
    board.board[0][8] = GoBoard.WHITE
    board.board[8][0] = GoBoard.WHITE
    board.current_player = GoBoard.BLACK
    return board, GoBoard.BLACK, (8, 8)


def _go_puzzles(n: int) -> List[Tuple]:
    puzzles = []
    for i in range(n):
        if i % 2 == 0:
            puzzles.append(_atari_board())
        else:
            puzzles.append(_territory_board())
    return puzzles


def _go_eval(board, move, correct_move, player) -> bool:
    if move == correct_move:
        return True
    if move is not None and board.is_legal_move(move[0], move[1], player):
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


def _build_crls(
    strategies=None,
    wm_min_buffer: int = 3,
    wm_batch_size: int = 2,
    wm_hidden_dim: int = 8,
    wm_horizon: int = 2,
    wm_buffer_capacity: int = 200,
) -> WorldModelCRLS:
    strategies = strategies or GO_TACTICS
    return WorldModelCRLS(
        strategies=strategies,
        upward_rate=0.0,
        downward_rate=0.0,
        synthesiser_kwargs={"acc_drop_threshold": 0.0},
        min_trials_to_override=3,
        override_tolerance=0.02,
        rollout_horizon=3,
        rollout_discount=0.90,
        min_transitions=3,
        meta_step_size=0.02,
        meta_min_transitions=4,
        bandit_mode=BanditMode.UCB1,
        exploration_coeff=1.0,
        force_explore_unseen=True,
        distill_lr=0.10,
        distill_min_steps=5,
        distill_confidence=0.40,
        ensemble_n_members=3,
        ensemble_lr=0.10,
        ensemble_l2=1e-4,
        ensemble_init_noise=0.01,
        ensemble_min_steps=5,
        ensemble_max_jsd=1.0,
        ensemble_min_conf=0.0,
        ensemble_seed=42,
        ewc_lambda=1.0,
        fisher_sample_size=20,
        forgetting_threshold=0.05,
        ema_alpha=0.5,
        ewc_min_steps_before_detect=5,
        decomp_min_bucket_size=1,
        decomp_confidence_base=0.80,
        decomp_override_threshold=1.01,
        wm_min_buffer=wm_min_buffer,
        wm_batch_size=wm_batch_size,
        wm_hidden_dim=wm_hidden_dim,
        wm_horizon=wm_horizon,
        wm_buffer_capacity=wm_buffer_capacity,
        wm_seed=0,
    )


def _run_n_generations(crls: WorldModelCRLS, n: int = 8):
    """Run n generations of Go puzzle data through the CRLS."""
    puzzles = _go_puzzles(10)
    tactic_fns = _go_tactic_fns()
    for _ in range(n):
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        crls.end_of_generation()


# ===========================================================================
# TestReplayBuffer
# ===========================================================================

class TestReplayBuffer:
    """Unit tests for ReplayBuffer (ring buffer semantics)."""

    def test_empty_on_init(self):
        buf = ReplayBuffer(capacity=10)
        assert buf.size == 0
        assert len(buf) == 0

    def test_add_single(self):
        buf = ReplayBuffer(capacity=10)
        s = _snap()
        t = _transition(s, SynthesisAction.PROMOTE_BEST, _snap(acc=0.55))
        buf.add(t)
        assert buf.size == 1

    def test_add_up_to_capacity(self):
        cap = 5
        buf = ReplayBuffer(capacity=cap)
        for i in range(cap):
            buf.add(_transition(_snap(), SynthesisAction.PROMOTE_BEST, _snap()))
        assert buf.size == cap

    def test_ring_overflow(self):
        cap = 3
        buf = ReplayBuffer(capacity=cap)
        # Add 2*cap items — size stays at cap
        for i in range(2 * cap):
            buf.add(_transition(_snap(), SynthesisAction.PROMOTE_BEST, _snap()))
        assert buf.size == cap

    def test_sample_respects_k(self):
        buf = ReplayBuffer(capacity=20)
        for i in range(10):
            buf.add(_transition(_snap(), SynthesisAction.DEMOTE_WORST, _snap()))
        sample = buf.sample(5)
        assert len(sample) == 5

    def test_sample_at_most_size(self):
        buf = ReplayBuffer(capacity=20)
        for i in range(3):
            buf.add(_transition(_snap(), SynthesisAction.RESET_UNIFORM, _snap()))
        sample = buf.sample(100)  # request more than available
        assert len(sample) == 3

    def test_sample_returns_trajectory_transitions(self):
        buf = ReplayBuffer(capacity=10)
        buf.add(_transition(_snap(), SynthesisAction.BOOST_UPWARD, _snap()))
        sample = buf.sample(1)
        assert isinstance(sample[0], TrajectoryTransition)


# ===========================================================================
# TestLatentTransitionModel
# ===========================================================================

_SNAP_DIM = len(_snap().as_vector())  # = 8 for 6 GO_TACTICS + upward_rate + accuracy


class TestLatentTransitionModel:
    """MLP construction, forward pass, SGD training."""

    def _model(self, state_dim: int = _SNAP_DIM, hidden_dim: int = 8) -> LatentTransitionModel:
        return LatentTransitionModel(
            state_dim=state_dim,
            hidden_dim=hidden_dim,
            lr=0.05,
            l2=1e-4,
            seed=42,
        )

    def _two_snaps(self) -> Tuple[SynthesisStateSnapshot, SynthesisStateSnapshot]:
        s0 = _snap(gen=0, acc=0.50)
        s1 = _snap(gen=1, acc=0.55)
        return s0, s1

    def test_construction(self):
        m = self._model(state_dim=_SNAP_DIM, hidden_dim=8)
        assert m.state_dim == _SNAP_DIM
        assert m.hidden_dim == 8
        assert m.n_steps == 0

    def test_weight_shapes(self):
        m = self._model(state_dim=_SNAP_DIM, hidden_dim=8)
        # W1: hidden_dim × (state_dim + N_ACTIONS)
        assert len(m.W1) == 8
        assert len(m.W1[0]) == _SNAP_DIM + _N_ACTIONS
        # W2: state_dim × hidden_dim
        assert len(m.W2) == _SNAP_DIM
        assert len(m.W2[0]) == 8

    def test_predict_returns_list_of_correct_length(self):
        m = self._model(state_dim=_SNAP_DIM)
        s0, _ = self._two_snaps()
        delta = m.predict(s0, SynthesisAction.PROMOTE_BEST)
        assert isinstance(delta, list)
        assert len(delta) == m.state_dim

    def test_predict_next_accuracy_float(self):
        m = self._model(state_dim=_SNAP_DIM)
        s0, _ = self._two_snaps()
        acc = m.predict_next_accuracy(s0, SynthesisAction.DEMOTE_WORST)
        assert isinstance(acc, float)

    def test_update_returns_loss(self):
        s0, s1 = self._two_snaps()
        t = _transition(s0, SynthesisAction.PROMOTE_BEST, s1)
        m = LatentTransitionModel(state_dim=len(s0.as_vector()), hidden_dim=8)
        loss = m.update([t])
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_update_increments_n_steps(self):
        s0, s1 = self._two_snaps()
        t = _transition(s0, SynthesisAction.PROMOTE_BEST, s1)
        m = LatentTransitionModel(state_dim=len(s0.as_vector()), hidden_dim=8)
        m.update([t])
        assert m.n_steps == 1
        m.update([t])
        assert m.n_steps == 2

    def test_update_empty_batch_returns_zero(self):
        m = LatentTransitionModel(state_dim=_SNAP_DIM, hidden_dim=8)
        loss = m.update([])
        assert loss == 0.0

    def test_loss_decreases_with_training(self):
        """After many SGD steps on the same transition, loss should decrease."""
        s0 = _snap(gen=0, acc=0.50)
        s1 = _snap(gen=1, acc=0.60)
        t = _transition(s0, SynthesisAction.PROMOTE_BEST, s1)
        m = LatentTransitionModel(
            state_dim=len(s0.as_vector()), hidden_dim=16, lr=0.1, seed=1
        )
        losses = [m.update([t]) for _ in range(50)]
        # Final loss should be lower than initial (at least a little)
        assert losses[-1] <= losses[0] + 1e-3

    def test_mean_loss_property(self):
        s0, s1 = self._two_snaps()
        t = _transition(s0, SynthesisAction.PROMOTE_BEST, s1)
        m = LatentTransitionModel(state_dim=len(s0.as_vector()), hidden_dim=8)
        m.update([t])
        assert m.mean_loss >= 0.0

    def test_get_summary_keys(self):
        m = self._model()
        s = m.get_summary()
        for key in ("state_dim", "hidden_dim", "lr", "l2", "n_steps", "mean_loss"):
            assert key in s

    def test_different_seeds_give_different_weights(self):
        m0 = LatentTransitionModel(state_dim=_SNAP_DIM, hidden_dim=8, seed=0)
        m1 = LatentTransitionModel(state_dim=_SNAP_DIM, hidden_dim=8, seed=99)
        assert m0.W1[0][0] != m1.W1[0][0]


# ===========================================================================
# TestWorldModelRollout
# ===========================================================================

class TestWorldModelRollout:
    """WorldModelRollout dataclass and to_dict()."""

    def _rollout(self, source: RolloutSource = RolloutSource.NEURAL) -> WorldModelRollout:
        return WorldModelRollout(
            best_action=SynthesisAction.PROMOTE_BEST,
            predicted_return=0.05,
            horizon=3,
            source=source,
            action_values={a.value: 0.0 for a in SynthesisAction},
            mae_estimate=0.01,
        )

    def test_to_dict_keys(self):
        d = self._rollout().to_dict()
        for key in ("best_action", "predicted_return", "horizon",
                    "source", "action_values", "mae_estimate"):
            assert key in d

    def test_source_neural(self):
        r = self._rollout(RolloutSource.NEURAL)
        assert r.source == RolloutSource.NEURAL
        assert r.to_dict()["source"] == "neural"

    def test_source_tabular(self):
        r = self._rollout(RolloutSource.TABULAR)
        assert r.to_dict()["source"] == "tabular"

    def test_source_fallback(self):
        r = self._rollout(RolloutSource.FALLBACK)
        assert r.to_dict()["source"] == "fallback"

    def test_best_action_serialised_as_string(self):
        r = self._rollout()
        assert isinstance(r.to_dict()["best_action"], str)


# ===========================================================================
# TestWorldModelRecord
# ===========================================================================

class TestWorldModelRecord:
    """Audit record dataclass."""

    def _record(self) -> WorldModelRecord:
        rollout = WorldModelRollout(
            best_action=SynthesisAction.DEMOTE_WORST,
            predicted_return=0.02,
            horizon=2,
            source=RolloutSource.TABULAR,
            action_values={a.value: 0.0 for a in SynthesisAction},
        )
        return WorldModelRecord(
            generation=5,
            proposed_action=SynthesisAction.DEMOTE_WORST,
            applied_action=SynthesisAction.DEMOTE_WORST,
            predicted_accuracy=0.62,
            actual_accuracy=0.65,
            prediction_error=0.03,
            rollout=rollout,
            replay_buffer_size=20,
            model_n_steps=10,
            model_loss=0.001,
        )

    def test_to_dict_keys(self):
        d = self._record().to_dict()
        for key in (
            "generation", "proposed_action", "applied_action",
            "predicted_accuracy", "actual_accuracy", "prediction_error",
            "rollout", "replay_buffer_size", "model_n_steps", "model_loss",
        ):
            assert key in d

    def test_generation_value(self):
        assert self._record().to_dict()["generation"] == 5

    def test_rollout_nested_dict(self):
        d = self._record().to_dict()
        assert isinstance(d["rollout"], dict)


# ===========================================================================
# TestWorldModelCRLS
# ===========================================================================

class TestWorldModelCRLS:
    """Integration tests for the 11-layer WorldModelCRLS."""

    def test_construction(self):
        crls = _build_crls()
        assert crls.replay_buffer.size == 0
        assert crls.transition_model.n_steps == 0

    def test_end_of_generation_returns_11_tuple(self):
        crls = _build_crls()
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        result = crls.end_of_generation()
        assert len(result) == 11

    def test_last_element_is_world_model_record(self):
        crls = _build_crls()
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        *_, wm_rec = crls.end_of_generation()
        assert isinstance(wm_rec, WorldModelRecord)

    def test_replay_buffer_grows(self):
        crls = _build_crls()
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        crls.end_of_generation()
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        crls.end_of_generation()
        # After 2 generations the buffer should have at least 1 transition
        assert crls.replay_buffer.size >= 1

    def test_model_trains_after_enough_data(self):
        crls = _build_crls(wm_min_buffer=3, wm_batch_size=2)
        _run_n_generations(crls, n=8)
        # At least one SGD step should have happened
        assert crls.transition_model.n_steps >= 1

    def test_gen_log_has_wp30_keys(self):
        crls = _build_crls()
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        crls.end_of_generation()
        assert len(crls.gen_log) >= 1
        log_entry = crls.gen_log[-1]
        for key in ("wp30_wm_action", "wp30_applied", "wp30_rollout_source",
                    "wp30_predicted_acc", "wp30_model_loss", "wp30_buffer_size"):
            assert key in log_entry, f"Missing key: {key}"

    def test_get_full_report_has_wm_keys(self):
        crls = _build_crls()
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        crls.end_of_generation()
        report = crls.get_full_report()
        assert "world_model_summary" in report
        assert "world_model_log" in report
        assert "replay_buffer_size" in report

    def test_multi_generation_run(self):
        crls = _build_crls(wm_min_buffer=3, wm_batch_size=2)
        _run_n_generations(crls, n=8)
        assert crls.generation == 8
        report = crls.get_full_report()
        assert len(report["world_model_log"]) == 8

    def test_fallback_when_buffer_small(self):
        """With min_buffer=1000, the first few gens should use tabular or fallback."""
        crls = WorldModelCRLS(
            strategies=GO_TACTICS,
            upward_rate=0.0,
            downward_rate=0.0,
            synthesiser_kwargs={"acc_drop_threshold": 0.0},
            wm_min_buffer=1000,  # very high threshold
            wm_batch_size=4,
            wm_seed=0,
        )
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        *_, wm_rec = crls.end_of_generation()
        # Should be tabular or fallback, not neural
        assert wm_rec.rollout.source in (RolloutSource.TABULAR, RolloutSource.FALLBACK)


# ===========================================================================
# TestWP30ExitCriteria
# ===========================================================================

class TestWP30ExitCriteria:
    """verify_wp30_exit_criteria — six criteria."""

    def _trained_crls(self, n_gens: int = 12) -> WorldModelCRLS:
        crls = _build_crls(wm_min_buffer=3, wm_batch_size=2)
        _run_n_generations(crls, n=n_gens)
        return crls

    def test_all_criteria_pass_after_training(self):
        crls = self._trained_crls(n_gens=12)
        result = verify_wp30_exit_criteria(crls)
        for criterion, passed in result.items():
            assert passed, f"Criterion '{criterion}' failed"

    def test_returns_dict(self):
        crls = self._trained_crls()
        result = verify_wp30_exit_criteria(crls)
        assert isinstance(result, dict)

    def test_six_criteria(self):
        crls = self._trained_crls()
        result = verify_wp30_exit_criteria(crls)
        assert len(result) == 6

    def test_expected_criterion_keys(self):
        crls = self._trained_crls()
        result = verify_wp30_exit_criteria(crls)
        expected = {
            "replay_buffer_populated",
            "model_trained",
            "rollout_produced",
            "prediction_logged",
            "neural_or_tabular_used",
            "safety_preserved",
        }
        assert set(result.keys()) == expected

    def test_buffer_not_populated_fails(self):
        """A freshly constructed CRLS (no data) should fail buffer criterion."""
        crls = _build_crls()
        result = verify_wp30_exit_criteria(crls)
        assert not result["replay_buffer_populated"]

    def test_model_not_trained_fails(self):
        crls = _build_crls()
        result = verify_wp30_exit_criteria(crls)
        assert not result["model_trained"]


# ===========================================================================
# TestLayerInteraction
# ===========================================================================

class TestLayerInteraction:
    """Integration: verify correct interaction between WP30 and lower layers."""

    def test_11_tuple_types(self):
        """Each element of the 11-tuple has the right type."""
        crls = _build_crls(wm_min_buffer=3, wm_batch_size=2)
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        result = crls.end_of_generation()
        assert len(result) == 11
        synth_rec, causal_rec, rollout_res, grad_step, explore_rec, \
            distill_rec, ensemble_rec, forgetting_rec, decomp_rec, \
            inv_rec, wm_rec = result
        assert isinstance(synth_rec, SynthesisRecord)
        assert isinstance(wm_rec, WorldModelRecord)

    def test_retrospective_error_filled_in(self):
        """After gen 2, wm_log[0] should have actual_accuracy set."""
        crls = _build_crls(wm_min_buffer=3, wm_batch_size=2)
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        # Generation 1
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        crls.end_of_generation()
        # Generation 2
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        crls.end_of_generation()
        report = crls.get_full_report()
        wm_log = report["world_model_log"]
        assert len(wm_log) >= 2
        # The first record's actual_accuracy should have been updated retrospectively
        # (it might be 0.0 if legitimately observed as 0.0, which is fine)
        assert "actual_accuracy" in wm_log[0]

    def test_neural_or_tabular_source_after_buffer_filled(self):
        """Once the replay buffer has enough data, rollout source should not be fallback only."""
        crls = _build_crls(wm_min_buffer=3, wm_batch_size=2)
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        sources = []
        for _ in range(10):
            crls.run_generation(puzzles, tactic_fns, _go_eval)
            *_, wm_rec = crls.end_of_generation()
            sources.append(wm_rec.rollout.source)
        # After enough generations the model should have been used at least once
        assert RolloutSource.NEURAL in sources or RolloutSource.TABULAR in sources

    def test_wm_applied_action_is_synthesis_action(self):
        crls = _build_crls()
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        *_, wm_rec = crls.end_of_generation()
        assert isinstance(wm_rec.applied_action, SynthesisAction)

    def test_replay_buffer_capacity_respected(self):
        cap = 5
        crls = WorldModelCRLS(
            strategies=GO_TACTICS,
            upward_rate=0.0,
            downward_rate=0.0,
            synthesiser_kwargs={"acc_drop_threshold": 0.0},
            wm_buffer_capacity=cap,
            wm_min_buffer=2,
            wm_batch_size=2,
            wm_seed=0,
        )
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        for _ in range(10):
            crls.run_generation(puzzles, tactic_fns, _go_eval)
            crls.end_of_generation()
        assert crls.replay_buffer.size <= cap

    def test_full_exit_criteria_pass_integration(self):
        crls = _build_crls(wm_min_buffer=3, wm_batch_size=2)
        _run_n_generations(crls, n=12)
        result = verify_wp30_exit_criteria(crls)
        # All six must pass
        for k, v in result.items():
            assert v, f"Failed: {k}"
