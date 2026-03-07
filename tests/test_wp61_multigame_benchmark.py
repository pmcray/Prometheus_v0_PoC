"""
WP61 Test Suite: Multi-Game Self-Play Benchmark Suite
======================================================

TestGameConfig            Dataclass fields and to_dict()
TestGameEngine            Board init, legal moves, apply move
TestPolicies              RandomPolicy, MinimaxPolicy, PrometheusPolicy
TestMultiGameBenchmark    run, report structure
TestBenchmarkReport       Report dict keys, win rates, elo trajectory
TestWP61ExitCriteria      Six-criterion verifier
TestIntegration           End-to-end: benchmark → report
"""

import pytest

from prometheus.wp61_multigame_benchmark import (
    CHESS9_CONFIG,
    CONNECT4_CONFIG,
    GO9_CONFIG,
    TICTACTOE_CONFIG,
    BenchmarkReport,
    BenchmarkResult,
    GameConfig,
    GameEngine,
    GameState,
    MinimaxPolicy,
    MultiGameBenchmark,
    PrometheusPolicy,
    RandomPolicy,
    verify_wp61_exit_criteria,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bench(n_matches: int = 2, minimax_depth: int = 1, seed: int = 42) -> MultiGameBenchmark:
    return MultiGameBenchmark(
        configs=[TICTACTOE_CONFIG],
        n_matches=n_matches,
        minimax_depth=minimax_depth,
        seed=seed,
    )


# ===========================================================================
# TestGameConfig
# ===========================================================================

class TestGameConfig:
    def test_tictactoe_name(self):
        assert TICTACTOE_CONFIG.name == "tictactoe"

    def test_connect4_board_size(self):
        assert CONNECT4_CONFIG.board_size >= 6

    def test_to_dict_has_keys(self):
        d = TICTACTOE_CONFIG.to_dict()
        assert isinstance(d, dict)
        assert len(d) > 0

    def test_custom_config(self):
        # GameConfig: name, board_size, branching_factor, win_length, max_moves
        cfg = GameConfig(
            name="test_game",
            board_size=4,
            branching_factor=9.0,
            win_length=3,
            max_moves=50,
        )
        assert cfg.board_size == 4
        assert cfg.name == "test_game"


# ===========================================================================
# TestGameEngine
# ===========================================================================

class TestGameEngine:
    def test_new_game_returns_state(self):
        engine = GameEngine(TICTACTOE_CONFIG)
        state = engine.new_game()
        assert isinstance(state, GameState)
        assert state.current_player == 0
        assert not state.done

    def test_legal_moves_full_board(self):
        engine = GameEngine(TICTACTOE_CONFIG)
        state = engine.new_game()
        moves = engine.legal_moves(state)
        assert len(moves) == 9  # 3x3 board fully empty

    def test_apply_move_changes_player(self):
        engine = GameEngine(TICTACTOE_CONFIG)
        state = engine.new_game()
        first_player = state.current_player
        state2 = engine.apply_move(state, engine.legal_moves(state)[0])
        assert state2.current_player != first_player

    def test_legal_moves_decrease_after_move(self):
        engine = GameEngine(TICTACTOE_CONFIG)
        state = engine.new_game()
        before = len(engine.legal_moves(state))
        state = engine.apply_move(state, engine.legal_moves(state)[0])
        after = len(engine.legal_moves(state))
        assert after == before - 1

    def test_state_to_dict(self):
        engine = GameEngine(TICTACTOE_CONFIG)
        state = engine.new_game()
        d = state.to_dict()
        assert isinstance(d, dict)
        assert len(d) > 0

    def test_game_completes(self):
        engine = GameEngine(TICTACTOE_CONFIG, seed=0)
        policy = RandomPolicy(seed=0)
        state = engine.new_game()
        for _ in range(100):
            if state.done:
                break
            moves = engine.legal_moves(state)
            if not moves:
                break
            move = policy.select_action(state, moves)
            state = engine.apply_move(state, move)
        assert state.done or state.move_count > 0

    def test_game_state_has_board(self):
        engine = GameEngine(TICTACTOE_CONFIG)
        state = engine.new_game()
        assert hasattr(state, "board")
        assert state.board is not None


# ===========================================================================
# TestPolicies
# ===========================================================================

class TestPolicies:
    def _engine_state(self):
        engine = GameEngine(TICTACTOE_CONFIG)
        return engine, engine.new_game()

    def test_random_policy_returns_legal_move(self):
        engine, state = self._engine_state()
        policy = RandomPolicy(seed=0)
        move = policy.select_action(state, engine.legal_moves(state))
        assert move in engine.legal_moves(state)

    def test_minimax_policy_returns_legal_move(self):
        engine, state = self._engine_state()
        policy = MinimaxPolicy(depth=1, seed=0)
        move = policy.select_action(state, engine.legal_moves(state))
        assert move in engine.legal_moves(state)

    def test_prometheus_policy_returns_legal_move(self):
        engine, state = self._engine_state()
        policy = PrometheusPolicy(seed=0)
        move = policy.select_action(state, engine.legal_moves(state))
        assert move in engine.legal_moves(state)

    def test_random_policy_is_deterministic_with_seed(self):
        engine, state = self._engine_state()
        p1 = RandomPolicy(seed=7)
        p2 = RandomPolicy(seed=7)
        m1 = p1.select_action(state, engine.legal_moves(state))
        m2 = p2.select_action(state, engine.legal_moves(state))
        assert m1 == m2

    def test_policies_have_name(self):
        assert isinstance(RandomPolicy().name, str)
        assert isinstance(MinimaxPolicy().name, str)
        assert isinstance(PrometheusPolicy().name, str)


# ===========================================================================
# TestMultiGameBenchmark
# ===========================================================================

class TestMultiGameBenchmark:
    def test_run_returns_report(self):
        bench = _bench(n_matches=2)
        report = bench.run()
        assert isinstance(report, BenchmarkReport)

    def test_n_matches_total(self):
        bench = _bench(n_matches=4)
        report = bench.run()
        assert report.n_matches_total >= 4

    def test_win_rates_dict(self):
        bench = _bench(n_matches=4)
        report = bench.run()
        assert isinstance(report.win_rates, dict)
        for game, rate in report.win_rates.items():
            assert 0.0 <= rate <= 1.0, f"Win rate out of range for {game}"

    def test_elo_trajectory_dict(self):
        bench = _bench(n_matches=4)
        report = bench.run()
        assert isinstance(report.elo_trajectory, dict)
        assert len(report.elo_trajectory) >= 1

    def test_multiple_games(self):
        bench = MultiGameBenchmark(
            configs=[TICTACTOE_CONFIG, CONNECT4_CONFIG],
            n_matches=2,
            minimax_depth=1,
            seed=0,
        )
        report = bench.run()
        assert len(report.win_rates) >= 2

    def test_cross_game_transfer_matrix(self):
        bench = _bench(n_matches=2)
        report = bench.run()
        assert hasattr(report, "cross_game_transfer")
        assert isinstance(report.cross_game_transfer, dict)

    def test_explosion_slope_float(self):
        bench = _bench(n_matches=4)
        report = bench.run()
        assert isinstance(report.intelligence_explosion_slope, float)


# ===========================================================================
# TestBenchmarkReport
# ===========================================================================

class TestBenchmarkReport:
    def _report(self) -> BenchmarkReport:
        return _bench(n_matches=4).run()

    def test_to_dict_keys(self):
        d = self._report().to_dict()
        assert "n_matches_total" in d
        assert "win_rates" in d
        assert "elo_trajectory" in d

    def test_results_list(self):
        report = self._report()
        assert isinstance(report.results, list)

    def test_total_time_s_nonneg(self):
        report = self._report()
        assert report.total_time_s >= 0.0


# ===========================================================================
# TestWP61ExitCriteria
# ===========================================================================

class TestWP61ExitCriteria:
    def _report(self) -> BenchmarkReport:
        return MultiGameBenchmark(n_matches=4, minimax_depth=1, seed=0).run()

    def test_returns_dict(self):
        assert isinstance(verify_wp61_exit_criteria(), dict)

    def test_six_criteria(self):
        assert len(verify_wp61_exit_criteria()) == 6

    def test_all_pass_with_report(self):
        report = self._report()
        result = verify_wp61_exit_criteria(report)
        for k, v in result.items():
            assert v, f"Criterion failed: '{k}'"

    def test_no_report_still_returns_dict(self):
        result = verify_wp61_exit_criteria(None)
        assert isinstance(result, dict)
        assert len(result) == 6


# ===========================================================================
# TestIntegration
# ===========================================================================

class TestIntegration:
    def test_end_to_end_tictactoe(self):
        bench = MultiGameBenchmark(
            configs=[TICTACTOE_CONFIG],
            n_matches=6,
            minimax_depth=1,
            seed=1,
        )
        report = bench.run()
        assert report.n_matches_total >= 6
        assert len(report.elo_trajectory) >= 1

    def test_criteria_pass_after_full_run(self):
        bench = MultiGameBenchmark(n_matches=4, minimax_depth=1, seed=0)
        report = bench.run()
        result = verify_wp61_exit_criteria(report)
        assert all(result.values()), f"Some criteria failed: {result}"
