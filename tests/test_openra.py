"""
Tests for the OpenRA integration — Prometheus v0.97

Covers:
  - OpenRAGameState / feature vector (openra_environment.py)
  - _SimulatedOpenRA backend step/reset (openra_environment.py)
  - OpenRAEnvironment public API (openra_environment.py)
  - OpenRAStrategyAgent action selection + evolutionary ops (openra_agent.py)
  - OpenRAAgentAdapter (openra_agent.py)
  - create_openra_agent factory (openra_agent.py)
  - OpenRABenchmark curriculum evaluation (openra_benchmark.py)
  - get_openra_opponent / estimate_openra_training_time (openra_benchmark.py)
  - run_prometheusstar_openra.run_stage() (run_prometheusstar_openra.py)

All tests run without a real OpenRA installation, using only the
bundled SimulatedOpenRA backend.
"""

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Module imports
# ---------------------------------------------------------------------------

from prometheus.openra_environment import (
    ACTION_NAMES,
    FEATURE_SIZE,
    NUM_ACTIONS,
    MAX_STEPS_PER_GAME,
    GameResult,
    OpenRAEnvironment,
    OpenRAGameState,
    _SimulatedOpenRA,
)
from prometheus.openra_agent import (
    OpenRAAgentAdapter,
    OpenRAStrategyAgent,
    _RandomOpenRAAgent,
    create_openra_agent,
)
from benchmarks.openra_benchmark import (
    OPENRA_CURRICULUM,
    OpenRABenchmark,
    OpenRAOpponentConfig,
    RandomOpenRAAgent,
    RushOpenRAAgent,
    EconomyOpenRAAgent,
    estimate_openra_training_time,
    get_openra_opponent,
    run_quick_evaluation,
)


# ===========================================================================
# OpenRAGameState
# ===========================================================================

class TestOpenRAGameState:

    def test_default_construction(self):
        s = OpenRAGameState()
        assert s.credits == 0.0
        assert s.game_result == GameResult.ONGOING

    def test_to_vector_shape(self):
        s = OpenRAGameState()
        v = s.to_vector()
        assert v.shape == (FEATURE_SIZE,)

    def test_to_vector_normalised(self):
        s = OpenRAGameState(
            credits=5000.0,
            own_infantry=20,
            own_vehicles=10,
        )
        v = s.to_vector()
        # credits normalised to 1.0, infantry normalised to 1.0
        assert abs(v[0] - 1.0) < 1e-6
        assert abs(v[2] - 1.0) < 1e-6

    def test_feature_vector_has_no_nan(self):
        s = OpenRAGameState(credits=1000.0, resource_pct=0.5)
        v = s.to_vector()
        assert not np.any(np.isnan(v))

    def test_total_own_strength_zero(self):
        s = OpenRAGameState()
        assert s.total_own_strength() == 0.0

    def test_total_own_strength_nonzero(self):
        s = OpenRAGameState(own_infantry=4, own_vehicles=2, own_aircraft=1, own_buildings=3)
        # 4*1 + 2*2 + 1*3 + 3*5 = 4+4+3+15 = 26
        assert s.total_own_strength() == pytest.approx(26.0)

    def test_total_enemy_strength(self):
        s = OpenRAGameState(enemy_infantry=2, enemy_vehicles=1)
        assert s.total_enemy_strength() == pytest.approx(4.0)

    def test_goal_indicator_fields(self):
        s = OpenRAGameState(game_result=GameResult.VICTORY)
        v = s.to_vector()
        assert v[18] == 1.0   # victory flag
        assert v[19] == 0.0   # defeat flag

    def test_defeat_indicator(self):
        s = OpenRAGameState(game_result=GameResult.DEFEAT)
        v = s.to_vector()
        assert v[18] == 0.0
        assert v[19] == 1.0


# ===========================================================================
# _SimulatedOpenRA
# ===========================================================================

class TestSimulatedOpenRA:

    def _make_sim(self, difficulty="easy", seed=0):
        return _SimulatedOpenRA(difficulty=difficulty, seed=seed)

    def test_reset_returns_game_state(self):
        sim = self._make_sim()
        state = sim.reset()
        assert isinstance(state, OpenRAGameState)

    def test_reset_credits_nonzero(self):
        sim = self._make_sim()
        state = sim.reset()
        assert state.credits > 0

    def test_step_returns_four_tuple(self):
        sim = self._make_sim()
        sim.reset()
        result = sim.step(0)  # no-op
        assert len(result) == 4
        new_state, reward, done, info = result
        assert isinstance(new_state, OpenRAGameState)
        assert isinstance(reward, float)
        assert isinstance(done, bool)
        assert isinstance(info, dict)

    def test_step_advances_game_step(self):
        sim = self._make_sim()
        sim.reset()
        state, _, _, _ = sim.step(0)
        assert state.game_step == 1

    def test_step_all_actions_do_not_crash(self):
        for action in range(NUM_ACTIONS):
            sim = self._make_sim(seed=action)
            sim.reset()
            state, reward, done, info = sim.step(action)
            assert isinstance(state, OpenRAGameState)

    def test_economy_tick_increases_credits(self):
        sim = self._make_sim()
        state = sim.reset()
        initial_credits = state.credits
        # Step with no-op many times to let economy run
        for _ in range(20):
            state, _, _, _ = sim.step(0)
        # Credits should increase (harvester active)
        assert state.credits >= initial_credits

    def test_termination_defeat(self):
        """Force defeat by driving own buildings to 0."""
        sim = self._make_sim()
        sim.reset()
        # Manually set own buildings to 0 to trigger defeat
        sim.state.own_buildings = 0
        _, _, done, _ = sim.step(0)
        assert done
        assert sim.state.game_result == GameResult.DEFEAT

    def test_termination_victory(self):
        sim = self._make_sim()
        sim.reset()
        sim.state.enemy_buildings = 0
        _, _, done, _ = sim.step(0)
        assert done
        assert sim.state.game_result == GameResult.VICTORY

    def test_max_steps_terminates_game(self):
        sim = self._make_sim(difficulty="easy", seed=99)
        sim.reset()
        sim._step_count = MAX_STEPS_PER_GAME - 1
        _, _, done, _ = sim.step(0)
        assert done

    def test_combat_roll_returns_non_negative(self):
        sim = self._make_sim()
        sim.reset()
        for _ in range(10):
            result = sim._combat_roll(5.0, 5.0)
            assert result >= 0

    def test_difficulty_easy_vs_hard_enemy_speed(self):
        """Hard AI builds units faster than Easy AI."""
        easy = self._make_sim(difficulty="easy", seed=1)
        hard = self._make_sim(difficulty="hard", seed=1)
        easy.reset(); hard.reset()

        for _ in range(200):
            easy.step(0)
            hard.step(0)

        # Hard AI should have produced more enemy units
        assert hard.state.enemy_infantry >= easy.state.enemy_infantry


# ===========================================================================
# OpenRAEnvironment
# ===========================================================================

class TestOpenRAEnvironment:

    def _env(self, difficulty="easy", seed=0):
        return OpenRAEnvironment(difficulty=difficulty, seed=seed, verbose=False)

    def test_reset_returns_game_state(self):
        env = self._env()
        state = env.reset()
        assert isinstance(state, OpenRAGameState)

    def test_step_requires_reset(self):
        env = self._env()
        with pytest.raises(RuntimeError):
            env.step(0)

    def test_step_returns_new_state(self):
        env = self._env()
        env.reset()
        state, reward, done, info = env.step(1)
        assert isinstance(state, OpenRAGameState)

    def test_get_observation_shape(self):
        env = self._env()
        env.reset()
        obs = env.get_observation()
        assert obs.shape == (FEATURE_SIZE,)

    def test_get_observation_before_reset_all_zeros(self):
        env = self._env()
        obs = env.get_observation()
        assert np.allclose(obs, 0.0)

    def test_num_actions(self):
        env = self._env()
        assert env.num_actions == NUM_ACTIONS

    def test_observation_size(self):
        env = self._env()
        assert env.observation_size == FEATURE_SIZE

    def test_render_returns_string(self):
        env = self._env()
        env.reset()
        rendered = env.render()
        assert isinstance(rendered, str)
        assert "OpenRA" in rendered

    def test_render_before_reset(self):
        env = self._env()
        result = env.render()
        assert "No active game" in result

    def test_total_episodes_increments(self):
        env = self._env(seed=7)
        assert env.total_episodes == 0
        env.reset()
        # Force immediate game end
        env._backend.state.enemy_buildings = 0
        _, _, done, info = env.step(0)
        if done:
            assert env.total_episodes == 1

    def test_full_episode_runs_to_completion(self):
        """Roll out a full episode without crashing."""
        env = self._env(seed=5)
        state = env.reset()
        done = False
        steps = 0
        while not done and steps < MAX_STEPS_PER_GAME:
            action = np.random.randint(0, NUM_ACTIONS)
            state, reward, done, info = env.step(action)
            steps += 1
        assert done or steps == MAX_STEPS_PER_GAME


# ===========================================================================
# OpenRAStrategyAgent
# ===========================================================================

class TestOpenRAStrategyAgent:

    def test_default_params_in_unit_interval(self):
        agent = OpenRAStrategyAgent()
        for k, v in agent.params.items():
            assert 0.0 <= v <= 1.0, f"{k} out of range: {v}"

    def test_custom_params_clamped(self):
        agent = OpenRAStrategyAgent({"aggression": 2.0, "economy_focus": -1.0})
        assert agent.params["aggression"] == 1.0
        assert agent.params["economy_focus"] == 0.0

    def test_select_action_returns_valid(self):
        agent = OpenRAStrategyAgent()
        env = OpenRAEnvironment(difficulty="easy")
        state = env.reset()
        for _ in range(30):
            action = agent.select_action(state)
            assert 0 <= action < NUM_ACTIONS
            state, _, done, _ = env.step(action)
            if done:
                break

    def test_select_action_accepts_ndarray(self):
        agent = OpenRAStrategyAgent()
        obs = np.zeros(FEATURE_SIZE)
        action = agent.select_action(obs)
        assert 0 <= action < NUM_ACTIONS

    def test_select_action_accepts_dict(self):
        agent = OpenRAStrategyAgent()
        obs = {"credits": 500, "own_infantry": 3, "enemy_infantry": 2,
               "own_buildings": 2, "enemy_buildings": 3,
               "own_vehicles": 0, "own_aircraft": 0, "own_harvesters": 1,
               "enemy_vehicles": 0, "enemy_aircraft": 0}
        action = agent.select_action(obs)
        assert 0 <= action < NUM_ACTIONS

    def test_select_action_accepts_none(self):
        agent = OpenRAStrategyAgent()
        action = agent.select_action(None)
        assert action == 0  # no-op

    def test_reset_clears_game_step(self):
        agent = OpenRAStrategyAgent()
        for _ in range(10):
            agent.select_action(OpenRAGameState())
        assert agent.game_step == 10
        agent.reset()
        assert agent.game_step == 0

    def test_win_rate_zero_before_games(self):
        agent = OpenRAStrategyAgent()
        assert agent.win_rate == 0.0

    def test_win_rate_after_recording(self):
        agent = OpenRAStrategyAgent()
        agent.record_result(GameResult.VICTORY)
        agent.record_result(GameResult.VICTORY)
        agent.record_result(GameResult.DEFEAT)
        assert agent.win_rate == pytest.approx(2 / 3)

    def test_mutate_returns_new_agent(self):
        agent = OpenRAStrategyAgent()
        mutant = agent.mutate(mutation_rate=0.5)
        assert isinstance(mutant, OpenRAStrategyAgent)
        assert mutant is not agent

    def test_mutate_params_in_range(self):
        agent = OpenRAStrategyAgent()
        for _ in range(20):
            mutant = agent.mutate(mutation_rate=1.0)
            for k, v in mutant.params.items():
                assert 0.0 <= v <= 1.0, f"{k}={v} out of range after mutation"

    def test_crossover_returns_new_agent(self):
        a1 = OpenRAStrategyAgent({"aggression": 0.9})
        a2 = OpenRAStrategyAgent({"aggression": 0.1})
        child = a1.crossover(a2)
        assert isinstance(child, OpenRAStrategyAgent)
        # aggression should be either 0.9 or 0.1 (uniform crossover)
        assert child.params["aggression"] in (0.9, 0.1)

    def test_crossover_params_in_range(self):
        a1 = OpenRAStrategyAgent()
        a2 = OpenRAStrategyAgent()
        child = a1.crossover(a2)
        for k, v in child.params.items():
            assert 0.0 <= v <= 1.0

    def test_to_dict_and_from_dict(self):
        agent = OpenRAStrategyAgent({"aggression": 0.7, "defense_bias": 0.3})
        agent._wins = 5
        d = agent.to_dict()
        loaded = OpenRAStrategyAgent.from_dict(d)
        assert loaded.params["aggression"] == pytest.approx(0.7)
        assert loaded._wins == 5

    def test_get_strategy_description(self):
        agent = OpenRAStrategyAgent()
        desc = agent.get_strategy_description()
        assert "aggression" in desc
        assert "economy_focus" in desc

    def test_repr(self):
        agent = OpenRAStrategyAgent()
        r = repr(agent)
        assert "OpenRAStrategyAgent" in r


# ===========================================================================
# OpenRAAgentAdapter
# ===========================================================================

class TestOpenRAAgentAdapter:

    def _make_adapter(self):
        class StubAgent:
            weights = np.ones(FEATURE_SIZE) * 0.5
            def reset(self): pass

        return OpenRAAgentAdapter(StubAgent())

    def test_select_action_valid(self):
        adapter = self._make_adapter()
        env = OpenRAEnvironment(difficulty="easy")
        state = env.reset()
        action = adapter.select_action(state)
        assert 0 <= action < NUM_ACTIONS

    def test_reset_clears_step(self):
        adapter = self._make_adapter()
        adapter.game_step = 5
        adapter.reset()
        assert adapter.game_step == 0

    def test_repr(self):
        adapter = self._make_adapter()
        assert "OpenRAAgentAdapter" in repr(adapter)


# ===========================================================================
# create_openra_agent factory
# ===========================================================================

class TestCreateOpenRAAgent:

    def test_strategy_type(self):
        agent = create_openra_agent("strategy")
        assert isinstance(agent, OpenRAStrategyAgent)

    def test_random_type(self):
        agent = create_openra_agent("random")
        action = agent.select_action(None)
        assert 0 <= action < NUM_ACTIONS

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError):
            create_openra_agent("bogus_type")

    def test_strategy_with_params(self):
        agent = create_openra_agent("strategy", strategy_params={"aggression": 0.9})
        assert agent.params["aggression"] == pytest.approx(0.9)


# ===========================================================================
# OpenRABenchmark
# ===========================================================================

class TestOpenRABenchmark:

    def _bench(self, difficulty="easy", seed=0):
        return OpenRABenchmark(difficulty=difficulty, num_games=3, max_steps=200, seed=seed)

    def test_evaluate_returns_dict(self):
        bench = self._bench()
        agent = RandomOpenRAAgent()
        result = bench.evaluate_agent(agent, num_games=2)
        assert "win_rate" in result
        assert "avg_reward" in result
        assert "games_played" in result

    def test_games_played_matches_request(self):
        bench = self._bench()
        agent = RandomOpenRAAgent()
        result = bench.evaluate_agent(agent, num_games=3)
        assert result["games_played"] == 3

    def test_win_rate_in_unit_interval(self):
        bench = self._bench()
        agent = RandomOpenRAAgent()
        result = bench.evaluate_agent(agent, num_games=3)
        assert 0.0 <= result["win_rate"] <= 1.0

    def test_wins_plus_losses_plus_draws_equals_total(self):
        bench = self._bench()
        agent = RandomOpenRAAgent()
        result = bench.evaluate_agent(agent, num_games=4)
        total = result["wins"] + result["losses"] + result["draws"]
        assert total == result["games_played"]

    def test_game_summaries_length(self):
        bench = self._bench()
        agent = RandomOpenRAAgent()
        result = bench.evaluate_agent(agent, num_games=3)
        assert len(result["game_summaries"]) == 3

    def test_difficulty_field(self):
        bench = self._bench(difficulty="hard")
        result = bench.evaluate_agent(RandomOpenRAAgent(), num_games=2)
        assert result["difficulty"] == "hard"

    def test_rush_agent_runs(self):
        bench = self._bench()
        agent = RushOpenRAAgent()
        result = bench.evaluate_agent(agent, num_games=2)
        assert isinstance(result["win_rate"], float)

    def test_economy_agent_runs(self):
        bench = self._bench()
        agent = EconomyOpenRAAgent()
        result = bench.evaluate_agent(agent, num_games=2)
        assert isinstance(result["win_rate"], float)

    def test_strategy_agent_runs(self):
        bench = self._bench()
        agent = OpenRAStrategyAgent()
        result = bench.evaluate_agent(agent, num_games=2)
        assert isinstance(result["win_rate"], float)

    def test_advance_difficulty(self):
        bench = self._bench(difficulty="easy")
        advanced = bench.advance_difficulty()
        assert advanced
        assert bench.difficulty == "medium"

    def test_advance_from_expert_returns_false(self):
        bench = self._bench(difficulty="expert")
        advanced = bench.advance_difficulty()
        assert not advanced
        assert bench.difficulty == "expert"

    def test_meets_target_false_for_random(self):
        """A random agent is very unlikely to meet the expert target."""
        bench = self._bench(difficulty="expert", seed=1)
        # Force the result
        result = {"win_rate": 0.10}
        assert not bench.meets_target(result)

    def test_meets_target_true(self):
        bench = self._bench(difficulty="easy")
        result = {"win_rate": 0.90}
        assert bench.meets_target(result)


# ===========================================================================
# Curriculum helpers
# ===========================================================================

class TestCurriculumHelpers:

    def test_get_openra_opponent_stage0(self):
        cfg = get_openra_opponent(0)
        assert isinstance(cfg, OpenRAOpponentConfig)
        assert cfg.difficulty == "easy"

    def test_get_openra_opponent_stage3(self):
        cfg = get_openra_opponent(3)
        assert cfg.difficulty == "expert"

    def test_get_openra_opponent_out_of_range(self):
        with pytest.raises(ValueError):
            get_openra_opponent(99)

    def test_curriculum_has_four_stages(self):
        assert len(OPENRA_CURRICULUM) == 4

    def test_curriculum_ordered_by_difficulty(self):
        difficulties = [c.difficulty for c in OPENRA_CURRICULUM]
        assert difficulties == ["easy", "medium", "hard", "expert"]

    def test_target_win_rates_descending(self):
        targets = [c.target_win_rate for c in OPENRA_CURRICULUM]
        for i in range(len(targets) - 1):
            assert targets[i] > targets[i + 1]

    def test_estimate_training_time(self):
        est = estimate_openra_training_time(
            population_size=8,
            generations=10,
            games_per_eval=4,
            seconds_per_game=15,
        )
        assert "total_games" in est
        assert est["total_games"] == 8 * 10 * 4
        assert "total_hours" in est
        assert est["total_minutes"] == pytest.approx(est["total_hours"] * 60)

    def test_run_quick_evaluation(self):
        agent = OpenRAStrategyAgent()
        result = run_quick_evaluation(agent, difficulty="easy",
                                      num_games=2, verbose=False)
        assert "win_rate" in result
        assert 0.0 <= result["win_rate"] <= 1.0


# ===========================================================================
# run_prometheusstar_openra
# ===========================================================================

class TestRunPrometheusStarOpenRA:
    """Integration tests for the curriculum runner (abbreviated stages)."""

    def test_run_stage_returns_dict(self):
        from run_prometheusstar_openra import run_stage
        cfg = {
            "stage": 1,
            "name": "Test",
            "difficulty": "easy",
            "population": 3,
            "generations": 2,
            "games_per_eval": 2,
            "mutation_rate": 0.2,
            "target": 0.70,
        }
        result = run_stage(cfg, seed=0, verbose=False)
        assert "best_win_rate" in result
        assert "target_met" in result
        assert "generation_log" in result
        assert len(result["generation_log"]) <= 2

    def test_run_stage_best_win_rate_in_unit_interval(self):
        from run_prometheusstar_openra import run_stage
        cfg = {
            "stage": 1,
            "name": "Test",
            "difficulty": "easy",
            "population": 2,
            "generations": 2,
            "games_per_eval": 2,
            "mutation_rate": 0.2,
            "target": 0.70,
        }
        result = run_stage(cfg, seed=7, verbose=False)
        assert 0.0 <= result["best_win_rate"] <= 1.0

    def test_main_runs_one_stage(self):
        from run_prometheusstar_openra import main
        results = main(
            max_stages=1,
            population=3,
            generations=2,
            games_per_eval=2,
            seed=0,
            plot=False,
            verbose=False,
        )
        assert len(results) == 1
        assert "best_win_rate" in results[0]

    def test_main_stops_at_max_stages(self):
        from run_prometheusstar_openra import main
        results = main(
            max_stages=2,
            population=2,
            generations=2,
            games_per_eval=2,
            seed=0,
            plot=False,
            verbose=False,
        )
        # Either 1 or 2 stages (stops if target not met)
        assert 1 <= len(results) <= 2
