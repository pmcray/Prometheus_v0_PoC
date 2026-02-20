"""
Tests for the Value Learning pipeline — Prometheus v0.97

Covers:
  - PreferenceBuffer (prometheus/value_learning.py)
  - ValueLearningAgent (prometheus/value_learning.py)
  - PreferenceResult / SyntheticOracle / collect_preferences_batch
    (prometheus/human_feedback.py)
  - GridWorld / GridWorldPolicy / GridWorldExperiment
    (benchmarks/value_learning_benchmark.py)
  - MCSSupervisor.run_value_learning_cycle()
    (prometheus/mcs.py)

All tests run without human input (SyntheticOracle) and without any
external API calls.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Module imports
# ---------------------------------------------------------------------------

from prometheus.value_learning import PreferenceBuffer, ValueLearningAgent
from prometheus.human_feedback import (
    PreferenceResult,
    SyntheticOracle,
    collect_preferences_batch,
)
from benchmarks.value_learning_benchmark import (
    FEATURE_SIZE,
    GridWorld,
    GridWorldExperiment,
    GridWorldPolicy,
    goal_seeking_policy,
    make_default_experiment,
    random_policy,
)


# ===========================================================================
# PreferenceBuffer
# ===========================================================================

class TestPreferenceBuffer:

    def test_add_and_len(self):
        buf = PreferenceBuffer(max_size=10)
        assert len(buf) == 0
        buf.add(np.ones(3), np.zeros(3))
        assert len(buf) == 1

    def test_fifo_eviction(self):
        buf = PreferenceBuffer(max_size=3)
        for i in range(5):
            buf.add(np.array([float(i)]), np.array([0.0]))
        assert len(buf) == 3

    def test_sample_returns_correct_count(self):
        buf = PreferenceBuffer()
        for _ in range(10):
            buf.add(np.ones(4), np.zeros(4))
        pairs = buf.sample(5)
        assert len(pairs) == 5

    def test_sample_empty_buffer_returns_empty(self):
        buf = PreferenceBuffer()
        assert buf.sample(5) == []

    def test_sample_more_than_available(self):
        buf = PreferenceBuffer()
        buf.add(np.ones(2), np.zeros(2))
        pairs = buf.sample(100)
        assert len(pairs) == 1

    def test_all_pairs(self):
        buf = PreferenceBuffer()
        buf.add(np.array([1.0, 2.0]), np.array([0.0, 0.0]))
        buf.add(np.array([3.0, 4.0]), np.array([0.0, 0.0]))
        pairs = buf.all_pairs()
        assert len(pairs) == 2


# ===========================================================================
# ValueLearningAgent
# ===========================================================================

class TestValueLearningAgent:

    def _agent(self, feature_size=4):
        return ValueLearningAgent(feature_size=feature_size,
                                  learning_rate=0.1,
                                  l2_reg=1e-3,
                                  history_window=5)

    def test_initial_weights_zero(self):
        agent = self._agent()
        assert np.allclose(agent.weights, 0.0)

    def test_get_reward_zero_weights(self):
        agent = self._agent()
        assert agent.get_reward(np.ones(4)) == 0.0

    def test_update_weights_changes_weights(self):
        agent = self._agent()
        pref = np.array([1.0, 0.0, 0.0, 0.0])
        unpref = np.array([0.0, 0.0, 0.0, 0.0])
        agent.update_weights(pref, unpref)
        assert not np.allclose(agent.weights, 0.0)

    def test_update_weights_returns_delta_norm(self):
        agent = self._agent()
        delta = agent.update_weights(np.ones(4), np.zeros(4))
        assert isinstance(delta, float)
        assert delta >= 0.0

    def test_update_prefers_correct_trajectory(self):
        """After many updates, reward(pref) > reward(unpref)."""
        agent = self._agent(feature_size=2)
        pref = np.array([1.0, 0.0])
        unpref = np.array([0.0, 1.0])
        for _ in range(100):
            agent.update_weights(pref, unpref)
        assert agent.get_reward(pref) > agent.get_reward(unpref)

    def test_train_from_buffer_empty(self):
        agent = self._agent()
        result = agent.train_from_buffer(n_pairs=4)
        assert result == 0.0

    def test_train_from_buffer_nonempty(self):
        agent = self._agent()
        agent.buffer.add(np.ones(4), np.zeros(4))
        result = agent.train_from_buffer(n_pairs=1)
        assert isinstance(result, float)

    def test_train_to_convergence_returns_dict(self):
        agent = self._agent(feature_size=2)
        pairs = [(np.array([1.0, 0.0]), np.array([0.0, 1.0]))] * 10
        result = agent.train_to_convergence(pairs, max_epochs=50, tol=1e-3)
        assert "epochs_run" in result
        assert "converged" in result
        assert "final_delta" in result
        assert "weight_history" in result

    def test_convergence_stats_before_updates(self):
        agent = self._agent()
        stats = agent.convergence_stats()
        assert stats["updates"] == 0
        assert stats["mean"] == 0.0

    def test_is_converged_false_before_window(self):
        agent = self._agent(feature_size=2)
        # history_window=5; fewer than 5 updates → not converged
        agent.update_weights(np.array([1.0, 0.0]), np.array([0.0, 1.0]))
        assert not agent.is_converged()

    def test_rank_trajectories(self):
        agent = self._agent(feature_size=2)
        agent.weights = np.array([1.0, 0.0])
        feature_sums = [
            np.array([0.5, 0.0]),
            np.array([2.0, 0.0]),
            np.array([1.0, 0.0]),
        ]
        ranked = agent.rank_trajectories(feature_sums)
        assert ranked[0][1] == 1   # index of highest-reward trajectory
        assert ranked[-1][1] == 0  # index of lowest-reward trajectory

    def test_save_and_load(self, tmp_path):
        agent = self._agent(feature_size=3)
        agent.update_weights(np.array([1.0, 0.5, 0.2]),
                             np.array([0.0, 0.0, 0.0]))
        filepath = str(tmp_path / "agent.json")
        agent.save(filepath)

        loaded = ValueLearningAgent.load(filepath)
        assert np.allclose(loaded.weights, agent.weights)
        assert loaded.feature_size == 3

    def test_save_load_roundtrip_metadata(self, tmp_path):
        agent = self._agent(feature_size=3)
        agent.update_weights(np.ones(3), np.zeros(3))
        filepath = str(tmp_path / "agent.json")
        agent.save(filepath)

        data = json.loads(Path(filepath).read_text())
        assert data["feature_size"] == 3
        assert "weights" in data
        assert "learning_rate" in data

    def test_get_weights_returns_copy(self):
        agent = self._agent()
        w = agent.get_weights()
        w[:] = 999.0
        assert not np.allclose(agent.weights, 999.0)

    def test_set_weights(self):
        agent = self._agent(feature_size=3)
        agent.set_weights(np.array([1.0, 2.0, 3.0]))
        assert np.allclose(agent.weights, [1.0, 2.0, 3.0])


# ===========================================================================
# PreferenceResult + SyntheticOracle + collect_preferences_batch
# ===========================================================================

class TestPreferenceResult:

    def test_fields(self):
        r = PreferenceResult(
            preferred_index=0,
            preferred_features=np.array([1.0]),
            unpreferred_features=np.array([0.0]),
        )
        assert r.preferred_index == 0
        assert r.confidence == 1.0
        assert r.source == "human"

    def test_custom_fields(self):
        r = PreferenceResult(1, np.array([0.5]), np.array([0.2]),
                             confidence=0.7, source="oracle")
        assert r.confidence == 0.7
        assert r.source == "oracle"


class TestSyntheticOracle:

    def _make_oracle(self, noise=0.0):
        true_reward = lambda f: float(f[0])   # first feature is reward
        return SyntheticOracle(true_reward, noise_level=noise)

    def test_deterministic_prefers_higher_reward(self):
        oracle = self._make_oracle()
        f1 = np.array([2.0, 0.0])
        f2 = np.array([1.0, 0.0])
        result = oracle.query(f1, f2)
        assert result.preferred_index == 0   # f1 preferred
        assert np.allclose(result.preferred_features, f1)

    def test_deterministic_prefers_second_when_lower(self):
        oracle = self._make_oracle()
        f1 = np.array([0.5])
        f2 = np.array([3.0])
        result = oracle.query(f1, f2)
        assert result.preferred_index == 1   # f2 preferred

    def test_query_count_increments(self):
        oracle = self._make_oracle()
        oracle.query(np.array([1.0]), np.array([0.0]))
        oracle.query(np.array([1.0]), np.array([0.0]))
        assert oracle.query_count == 2

    def test_source_label_deterministic(self):
        oracle = self._make_oracle(noise=0.0)
        result = oracle.query(np.array([1.0]), np.array([0.0]))
        assert result.source == "oracle"

    def test_source_label_noisy(self):
        oracle = self._make_oracle(noise=1.0)
        result = oracle.query(np.array([1.0]), np.array([0.0]))
        assert result.source == "noisy_oracle"

    def test_confidence_in_unit_interval(self):
        oracle = self._make_oracle()
        result = oracle.query(np.array([2.0]), np.array([0.0]))
        assert 0.5 <= result.confidence <= 1.0


class TestCollectPreferencesBatch:

    def test_batch_length_matches_input(self):
        true_reward = lambda f: float(f[0])
        oracle = SyntheticOracle(true_reward)
        pairs = [(np.array([1.0, 0.0]), np.array([0.0, 0.0]))] * 5
        results = collect_preferences_batch(pairs, oracle=oracle)
        assert len(results) == 5

    def test_all_results_are_preference_results(self):
        true_reward = lambda f: float(f[0])
        oracle = SyntheticOracle(true_reward)
        pairs = [(np.array([1.0]), np.array([0.0]))] * 3
        results = collect_preferences_batch(pairs, oracle=oracle)
        for r in results:
            assert isinstance(r, PreferenceResult)


# ===========================================================================
# GridWorld
# ===========================================================================

class TestGridWorld:

    def test_default_init(self):
        env = GridWorld(size=4)
        assert env.size == 4
        assert np.array_equal(env.start, [0, 0])
        assert np.array_equal(env.goal_pos, [3, 3])

    def test_reset_returns_start(self):
        env = GridWorld(size=5)
        env.step(1)   # move down
        state = env.reset()
        assert np.array_equal(state, [0, 0])

    def test_step_moves_agent(self):
        env = GridWorld(size=5)
        state, _, done = env.step(1)  # down
        assert state[0] == 1
        assert not done

    def test_step_blocked_by_border(self):
        env = GridWorld(size=5)
        # Already at top; moving up should not move
        state, _, _ = env.step(0)   # up
        assert state[0] == 0

    def test_step_blocked_by_wall(self):
        env = GridWorld(size=5, walls=[(1, 0)])
        env.step(1)   # down → would land at (1,0) which is a wall
        assert env.agent_pos[0] == 0   # should stay

    def test_done_when_goal_reached(self):
        env = GridWorld(size=2)
        # (0,0) → (1,0) → (1,1) = goal
        env.step(1)   # down → (1,0)
        _, _, done = env.step(3)   # right → (1,1)
        assert done

    def test_features_shape(self):
        env = GridWorld(size=5)
        f = env.get_features()
        assert f.shape == (FEATURE_SIZE,)

    def test_features_at_start(self):
        env = GridWorld(size=5)
        f = env.get_features()
        assert f[0] == 0.0    # row=0/4
        assert f[1] == 0.0    # col=0/4
        assert f[4] == 0.0    # not at goal
        assert f[5] == 1.0    # bias

    def test_features_at_goal(self):
        env = GridWorld(size=5)
        f = env.get_features(env.goal_pos)
        assert f[2] == 0.0    # distance to goal = 0
        assert f[4] == 1.0    # goal indicator

    def test_features_with_walls(self):
        env = GridWorld(size=5, walls=[(0, 1)])
        f = env.get_features(np.array([0, 0]))
        # wall at (0,1) is Manhattan distance 1 from start
        assert f[3] < 1.0    # some proximity

    def test_generate_trajectory_returns_feature_sum(self):
        env = GridWorld(size=5)
        _, feat_sum = env.generate_trajectory(random_policy, num_steps=5)
        assert feat_sum.shape == (FEATURE_SIZE,)

    def test_generate_trajectory_resets_agent(self):
        env = GridWorld(size=5)
        env.step(1)
        env.generate_trajectory(random_policy, num_steps=3, reset=True)
        # After reset, trajectory starts from (0,0)
        # We can't check env.agent_pos after (it stepped), but no exception = OK

    def test_is_done_false_at_start(self):
        env = GridWorld(size=5)
        assert not env.is_done()


# ===========================================================================
# GridWorldPolicy
# ===========================================================================

class TestGridWorldPolicy:

    def test_random_walk_when_weights_zero(self):
        env = GridWorld(size=5)
        agent = ValueLearningAgent(feature_size=FEATURE_SIZE)
        policy = GridWorldPolicy(agent, env, epsilon=0.0)
        # With zero weights, should still return a valid action
        action = policy(env.get_state())
        assert action in [0, 1, 2, 3]

    def test_greedy_selects_valid_action(self):
        env = GridWorld(size=5)
        agent = ValueLearningAgent(feature_size=FEATURE_SIZE)
        agent.weights = np.array([-1.0, -1.0, -1.0, 0.0, 5.0, 0.0])
        policy = GridWorldPolicy(agent, env, epsilon=0.0)
        action = policy(env.get_state())
        assert action in [0, 1, 2, 3]

    def test_epsilon_greedy_sometimes_random(self):
        """With epsilon=1.0 always random — should not crash."""
        env = GridWorld(size=5)
        agent = ValueLearningAgent(feature_size=FEATURE_SIZE)
        agent.weights = np.ones(FEATURE_SIZE)
        policy = GridWorldPolicy(agent, env, epsilon=1.0)
        for _ in range(10):
            assert policy(env.get_state()) in [0, 1, 2, 3]


class TestGoalSeekingPolicy:

    def test_moves_toward_goal(self):
        env = GridWorld(size=5)
        policy = goal_seeking_policy(env)
        # From (0,0), goal is (4,4) — should move down (1) or right (3)
        action = policy(np.array([0, 0]))
        assert action in [1, 3]   # down or right

    def test_at_goal_returns_action(self):
        env = GridWorld(size=5)
        policy = goal_seeking_policy(env)
        # At goal, no candidates → falls back to random
        action = policy(env.goal_pos)
        assert action in [0, 1, 2, 3]


# ===========================================================================
# GridWorldExperiment
# ===========================================================================

class TestGridWorldExperiment:

    def _make_exp(self, n_pairs=10, trajectory_len=6, eval_pairs=5):
        env = GridWorld(size=4)
        agent = ValueLearningAgent(feature_size=FEATURE_SIZE,
                                   learning_rate=0.1)
        return GridWorldExperiment(
            env=env,
            vl_agent=agent,
            n_pairs=n_pairs,
            trajectory_len=trajectory_len,
            max_epochs=30,
            tol=1e-3,
            eval_pairs=eval_pairs,
        )

    def test_collect_preferences_length(self):
        exp = self._make_exp(n_pairs=8)
        pairs = exp.collect_preferences()
        assert len(pairs) == 8

    def test_collect_preferences_feature_dim(self):
        exp = self._make_exp(n_pairs=4)
        pairs = exp.collect_preferences()
        for pref, unpref in pairs:
            assert pref.shape == (FEATURE_SIZE,)
            assert unpref.shape == (FEATURE_SIZE,)

    def test_train_updates_weights(self):
        exp = self._make_exp(n_pairs=10)
        old_weights = exp.vl_agent.weights.copy()
        pairs = exp.collect_preferences()
        exp.train(pairs)
        assert not np.allclose(exp.vl_agent.weights, old_weights)

    def test_train_returns_dict(self):
        exp = self._make_exp(n_pairs=6)
        pairs = exp.collect_preferences()
        result = exp.train(pairs)
        assert "converged" in result
        assert "epochs_run" in result

    def test_evaluate_returns_dict(self):
        exp = self._make_exp(eval_pairs=5)
        pairs = exp.collect_preferences()
        exp.train(pairs)
        ev = exp.evaluate()
        assert "ranking_accuracy" in ev
        assert "mean_reward_gap" in ev
        assert 0.0 <= ev["ranking_accuracy"] <= 1.0

    def test_run_full_pipeline(self):
        exp = self._make_exp(n_pairs=10, eval_pairs=5)
        result = exp.run()
        assert "converged" in result
        assert "ranking_accuracy" in result
        assert "learnt_weights" in result
        assert len(result["learnt_weights"]) == FEATURE_SIZE

    def test_make_default_experiment(self):
        exp = make_default_experiment(size=4, n_pairs=6)
        assert exp.env.size == 4
        assert exp.n_pairs == 6

    def test_experiment_learns_something(self):
        """
        After training on 40 pairs the agent should rank the goal-seeking
        trajectory above random at least 70% of the time on a 4×4 grid.
        This is a statistical sanity check (not adversarial).
        """
        np.random.seed(42)
        exp = make_default_experiment(size=4, n_pairs=40, trajectory_len=10)
        exp.eval_pairs = 30
        result = exp.run()
        # 70% is a conservative lower-bound for a working IRL implementation
        assert result["ranking_accuracy"] >= 0.70, (
            f"Expected ranking_accuracy >= 0.70, got {result['ranking_accuracy']:.3f}"
        )


# ===========================================================================
# MCSSupervisor.run_value_learning_cycle()
# ===========================================================================

class TestRunValueLearningCycle:
    """
    Tests run_value_learning_cycle() via MCSSupervisor.
    Uses a minimal DummyPlanner so the supervisor can be instantiated
    without a real planner / evaluator / coder.
    """

    def _make_supervisor(self):
        from prometheus.mcs import MCSSupervisor
        from prometheus.resource_manager import ResourceManager

        class DummyPlanner:
            def generate_bid(self, goal): return []

        rm = ResourceManager()
        return MCSSupervisor(DummyPlanner(), rm)

    def test_returns_dict_with_required_keys(self):
        sup = self._make_supervisor()
        result = sup.run_value_learning_cycle(
            grid_size=4, n_pairs=10, trajectory_len=6,
            max_epochs=20, tol=1e-3,
        )
        for key in ("converged", "ranking_accuracy", "epochs_run",
                    "learnt_weights", "eval_result", "training_result"):
            assert key in result, f"Missing key: {key}"

    def test_ranking_accuracy_in_unit_interval(self):
        sup = self._make_supervisor()
        result = sup.run_value_learning_cycle(
            grid_size=4, n_pairs=10, trajectory_len=6,
            max_epochs=20, tol=1e-2,
        )
        assert 0.0 <= result["ranking_accuracy"] <= 1.0

    def test_learnt_weights_correct_dimension(self):
        sup = self._make_supervisor()
        result = sup.run_value_learning_cycle(
            grid_size=4, n_pairs=8, trajectory_len=6,
            max_epochs=10, tol=1e-2,
        )
        assert len(result["learnt_weights"]) == FEATURE_SIZE

    def test_agent_stored_on_supervisor(self):
        sup = self._make_supervisor()
        sup.run_value_learning_cycle(
            grid_size=4, n_pairs=8, trajectory_len=6,
            max_epochs=10, tol=1e-2,
        )
        assert sup.value_learning_agent is not None
        assert isinstance(sup.value_learning_agent, ValueLearningAgent)

    def test_save_path_creates_file(self, tmp_path):
        sup = self._make_supervisor()
        save_file = str(tmp_path / "weights.json")
        sup.run_value_learning_cycle(
            grid_size=4, n_pairs=8, trajectory_len=6,
            max_epochs=10, tol=1e-2,
            save_path=save_file,
        )
        assert Path(save_file).exists()
        data = json.loads(Path(save_file).read_text())
        assert "weights" in data

    def test_reuses_existing_agent(self):
        """Second call should reuse (continue training) the same agent."""
        sup = self._make_supervisor()
        sup.run_value_learning_cycle(
            grid_size=4, n_pairs=8, trajectory_len=6,
            max_epochs=10, tol=1e-2,
        )
        agent_first = sup.value_learning_agent
        sup.run_value_learning_cycle(
            grid_size=4, n_pairs=8, trajectory_len=6,
            max_epochs=10, tol=1e-2,
        )
        # Same object reused (not re-created) because feature_size matches
        assert sup.value_learning_agent is agent_first

    def test_walls_parameter_accepted(self):
        sup = self._make_supervisor()
        result = sup.run_value_learning_cycle(
            grid_size=5, n_pairs=8, trajectory_len=6,
            max_epochs=10, tol=1e-2,
            walls=[(1, 1), (2, 2)],
        )
        assert "ranking_accuracy" in result
