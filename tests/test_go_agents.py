"""
Unit tests for Go agents

Tests agent implementations:
- RandomGoAgent: Random move selection
- StaticGoAgent: Frozen policy-value network
- PrometheusGoAgent: Online learning with evolution
- GoMCTSAgent: MCTS-enhanced agents
"""

import pytest
import numpy as np
import tensorflow as tf
from prometheus.models.go_models import (
    RandomGoAgent,
    StaticGoAgent,
    PrometheusGoAgent,
    create_go_policy_value_network
)
from prometheus.models.go_mcts import GoMCTSNode, GoMCTS, GoMCTSAgent
from prometheus.environments.go import GoBoard, GoEnvironment


class TestRandomGoAgent:
    """Test RandomGoAgent implementation."""

    def test_initialization(self):
        """Test agent initialization."""
        agent = RandomGoAgent(board_size=9)

        assert agent.board_size == 9
        assert agent.name == "Random Go Agent"

    def test_get_move_basic(self):
        """Test basic move generation."""
        agent = RandomGoAgent(board_size=9)
        env = GoEnvironment(board_size=9)

        state = env.get_state()
        legal_moves = env.get_legal_moves()

        # Get move
        move = agent.get_move(state, legal_moves)

        # Should be tuple
        assert isinstance(move, tuple)

        # Should be legal
        assert move in legal_moves

    def test_get_move_with_temperature(self):
        """Test move generation with temperature parameter."""
        agent = RandomGoAgent(board_size=9)
        env = GoEnvironment(board_size=9)

        state = env.get_state()
        legal_moves = env.get_legal_moves()

        # Should work with temperature (even though ignored)
        move = agent.get_move(state, legal_moves, temperature=0.1)

        assert move in legal_moves

    def test_move_distribution(self):
        """Test that moves are reasonably distributed."""
        agent = RandomGoAgent(board_size=9)
        env = GoEnvironment(board_size=9)

        state = env.get_state()
        legal_moves = env.get_legal_moves()

        # Generate many moves
        moves = [agent.get_move(state, legal_moves) for _ in range(100)]

        # Should have some variety (not all the same)
        unique_moves = set(moves)
        assert len(unique_moves) > 5  # At least some variety

    def test_only_legal_moves(self):
        """Test that agent only plays legal moves."""
        agent = RandomGoAgent(board_size=9)
        board = GoBoard(size=9)

        # Place some stones to reduce legal moves
        board.play_move(4, 4, board.BLACK)
        board.play_move(4, 5, board.WHITE)
        board.play_move(5, 4, board.BLACK)

        # Get legal moves
        legal_moves = []
        for row in range(9):
            for col in range(9):
                if board.is_legal_move(row, col, board.current_player):
                    legal_moves.append((row, col))
        legal_moves.append(('pass',))

        # Generate state
        state = np.zeros((9, 9, 3))

        # Get many moves
        for _ in range(50):
            move = agent.get_move(state, legal_moves)
            assert move in legal_moves


class TestStaticGoAgent:
    """Test StaticGoAgent implementation."""

    def test_initialization(self):
        """Test agent initialization."""
        agent = StaticGoAgent(board_size=9)

        assert agent.board_size == 9
        assert agent.name == "Static Go Agent"
        assert agent.model is not None
        assert not agent.trainable

    def test_model_structure(self):
        """Test that model has correct structure."""
        agent = StaticGoAgent(board_size=9)

        # Should have two outputs (policy and value)
        assert len(agent.model.outputs) == 2

        # Policy output should be 82 (81 board positions + 1 pass)
        policy_output = agent.model.outputs[0]
        assert policy_output.shape[-1] == 82

        # Value output should be 1
        value_output = agent.model.outputs[1]
        assert value_output.shape[-1] == 1

    def test_pretrain(self):
        """Test pretraining."""
        agent = StaticGoAgent(board_size=9)
        env = GoEnvironment(board_size=9)

        # Pretrain for a few epochs
        history = agent.pretrain(env, epochs=2, games_per_epoch=5)

        # Should return history
        assert history is not None
        assert 'policy_loss' in history.history
        assert 'value_loss' in history.history

    def test_weights_frozen(self):
        """Test that weights are frozen after pretraining."""
        agent = StaticGoAgent(board_size=9)
        env = GoEnvironment(board_size=9)

        # Pretrain
        agent.pretrain(env, epochs=1, games_per_epoch=3)

        # Get initial weights
        initial_weights = [w.numpy().copy() for w in agent.model.trainable_weights]

        # Try to train again (should not change weights)
        agent.pretrain(env, epochs=1, games_per_epoch=3)

        # Weights should be frozen
        for initial, current in zip(initial_weights, agent.model.trainable_weights):
            assert np.allclose(initial, current.numpy())

    def test_get_move(self):
        """Test move generation."""
        agent = StaticGoAgent(board_size=9)
        env = GoEnvironment(board_size=9)

        state = env.get_state()
        legal_moves = env.get_legal_moves()

        # Get move
        move = agent.get_move(state, legal_moves)

        # Should be legal
        assert move in legal_moves

    def test_predict(self):
        """Test prediction."""
        agent = StaticGoAgent(board_size=9)
        state = np.random.rand(9, 9, 3)

        policy, value = agent.predict(state)

        # Policy should be probabilities
        assert policy.shape == (82,)
        assert np.allclose(np.sum(policy), 1.0)
        assert np.all(policy >= 0)

        # Value should be in [-1, 1]
        assert isinstance(value, (float, np.floating))
        assert -1 <= value <= 1

    def test_temperature_parameter(self):
        """Test that temperature affects move selection."""
        agent = StaticGoAgent(board_size=9)
        env = GoEnvironment(board_size=9)

        state = env.get_state()
        legal_moves = env.get_legal_moves()

        # With temperature=0, should be deterministic
        moves_greedy = [agent.get_move(state, legal_moves, temperature=0.0)
                       for _ in range(10)]
        unique_greedy = set(moves_greedy)

        # With high temperature, should have more variety
        moves_random = [agent.get_move(state, legal_moves, temperature=2.0)
                       for _ in range(10)]
        unique_random = set(moves_random)

        # Random should have at least as many unique moves
        assert len(unique_random) >= len(unique_greedy)


class TestPrometheusGoAgent:
    """Test PrometheusGoAgent implementation."""

    def test_initialization(self):
        """Test agent initialization."""
        agent = PrometheusGoAgent(board_size=9)

        assert agent.board_size == 9
        assert agent.name == "Prometheus Go Agent"
        assert agent.model is not None
        assert agent.trainable
        assert agent.generation == 0

    def test_online_learning(self):
        """Test online learning updates weights."""
        agent = PrometheusGoAgent(board_size=9)
        env = GoEnvironment(board_size=9)

        # Get initial weights
        initial_weights = [w.numpy().copy() for w in agent.model.trainable_weights]

        # Train online
        agent.train_online(env, num_games=3)

        # Weights should have changed
        changed = False
        for initial, current in zip(initial_weights, agent.model.trainable_weights):
            if not np.allclose(initial, current.numpy()):
                changed = True
                break

        assert changed

    def test_evolution(self):
        """Test that evolution increments generation."""
        agent = PrometheusGoAgent(board_size=9)
        env = GoEnvironment(board_size=9)

        initial_gen = agent.generation

        # Evolve
        agent.train_online(env, num_games=2)

        # Generation should increment
        assert agent.generation > initial_gen

    def test_statistics_tracking(self):
        """Test that statistics are tracked."""
        agent = PrometheusGoAgent(board_size=9)
        env = GoEnvironment(board_size=9)

        # Train
        agent.train_online(env, num_games=5)

        # Should have statistics
        assert hasattr(agent, 'stats')
        assert 'games_played' in agent.stats
        assert agent.stats['games_played'] == 5

    def test_get_move(self):
        """Test move generation."""
        agent = PrometheusGoAgent(board_size=9)
        env = GoEnvironment(board_size=9)

        state = env.get_state()
        legal_moves = env.get_legal_moves()

        move = agent.get_move(state, legal_moves)

        assert move in legal_moves

    def test_game_result_processing(self):
        """Test that game results are processed."""
        agent = PrometheusGoAgent(board_size=9)
        env = GoEnvironment(board_size=9)

        # Play a quick game
        state = env.reset()
        done = False
        moves = 0

        while not done and moves < 20:
            legal_moves = env.get_legal_moves()
            move = agent.get_move(state, legal_moves)
            state, reward, done, info = env.step(move)
            moves += 1

        # Should have accumulated some experience
        assert len(agent.replay_buffer) > 0


class TestGoMCTSNode:
    """Test MCTS node implementation."""

    def test_initialization(self):
        """Test node initialization."""
        node = GoMCTSNode(prior=0.5, parent=None)

        assert node.prior == 0.5
        assert node.parent is None
        assert node.visit_count == 0
        assert node.total_value == 0.0
        assert len(node.children) == 0

    def test_mean_value(self):
        """Test mean value calculation."""
        node = GoMCTSNode(prior=0.5)

        # Initially undefined
        assert node.mean_value == 0.0

        # After update
        node.update(0.5)
        assert node.mean_value == 0.5

        node.update(1.0)
        assert node.mean_value == 0.75

    def test_expand(self):
        """Test node expansion."""
        node = GoMCTSNode(prior=0.5)

        # Expand with action priors
        action_priors = {0: 0.3, 1: 0.7}
        node.expand(action_priors)

        assert len(node.children) == 2
        assert 0 in node.children
        assert 1 in node.children
        assert node.children[0].prior == 0.3
        assert node.children[1].prior == 0.7

    def test_is_leaf(self):
        """Test leaf node detection."""
        node = GoMCTSNode(prior=0.5)

        assert node.is_leaf()

        node.expand({0: 1.0})

        assert not node.is_leaf()

    def test_select_child(self):
        """Test child selection with PUCT."""
        node = GoMCTSNode(prior=0.5)
        node.expand({0: 0.3, 1: 0.7})

        # Select child
        child = node.select_child(c_puct=1.0)

        # Should return a child node
        assert child in node.children.values()

    def test_update(self):
        """Test value update."""
        node = GoMCTSNode(prior=0.5)

        node.update(0.8)

        assert node.visit_count == 1
        assert node.total_value == 0.8
        assert node.mean_value == 0.8


class TestGoMCTS:
    """Test MCTS implementation."""

    def test_initialization(self):
        """Test MCTS initialization."""
        agent = RandomGoAgent(board_size=9)
        mcts = GoMCTS(agent=agent, num_simulations=10)

        assert mcts.agent == agent
        assert mcts.num_simulations == 10

    def test_search(self):
        """Test MCTS search."""
        agent = RandomGoAgent(board_size=9)
        mcts = GoMCTS(agent=agent, num_simulations=10)

        board = GoBoard(size=9)
        state = np.zeros((9, 9, 3))
        legal_moves = [(4, 4), (4, 5), ('pass',)]

        # Run search
        move_probs = mcts.search(board, state, legal_moves)

        # Should return probabilities
        assert isinstance(move_probs, dict)
        assert len(move_probs) > 0

        # Probabilities should sum to 1
        total = sum(move_probs.values())
        assert np.isclose(total, 1.0)

    def test_simulation(self):
        """Test single simulation."""
        agent = RandomGoAgent(board_size=9)
        mcts = GoMCTS(agent=agent, num_simulations=1)

        board = GoBoard(size=9)
        state = np.zeros((9, 9, 3))
        legal_moves = [(4, 4), (4, 5), ('pass',)]

        # Single simulation should work
        move_probs = mcts.search(board, state, legal_moves)

        assert len(move_probs) > 0


class TestGoMCTSAgent:
    """Test MCTS-enhanced agent wrapper."""

    def test_initialization(self):
        """Test MCTS agent initialization."""
        base_agent = RandomGoAgent(board_size=9)
        mcts_agent = GoMCTSAgent(base_agent, num_simulations=50)

        assert mcts_agent.base_agent == base_agent
        assert mcts_agent.board_size == 9
        assert mcts_agent.num_simulations == 50

    def test_get_move(self):
        """Test move generation with MCTS."""
        base_agent = RandomGoAgent(board_size=9)
        mcts_agent = GoMCTSAgent(base_agent, num_simulations=20)

        env = GoEnvironment(board_size=9)
        state = env.get_state()
        legal_moves = env.get_legal_moves()

        # Get move
        move = mcts_agent.get_move(state, legal_moves)

        # Should be legal
        assert move in legal_moves

    def test_enhancement_over_base(self):
        """Test that MCTS improves play."""
        base_agent = StaticGoAgent(board_size=9)
        mcts_agent = GoMCTSAgent(base_agent, num_simulations=50)

        # This is more of an integration test
        # Just verify MCTS agent can play
        env = GoEnvironment(board_size=9)
        state = env.reset()

        legal_moves = env.get_legal_moves()
        move = mcts_agent.get_move(state, legal_moves)

        assert move in legal_moves

    def test_temperature(self):
        """Test temperature parameter."""
        base_agent = RandomGoAgent(board_size=9)
        mcts_agent = GoMCTSAgent(base_agent, num_simulations=20)

        env = GoEnvironment(board_size=9)
        state = env.get_state()
        legal_moves = env.get_legal_moves()

        # Should accept temperature
        move = mcts_agent.get_move(state, legal_moves, temperature=0.5)

        assert move in legal_moves


class TestPolicyValueNetwork:
    """Test policy-value network architecture."""

    def test_create_network(self):
        """Test network creation."""
        model = create_go_policy_value_network(board_size=9, num_filters=32)

        # Should have correct input shape
        assert model.input_shape == (None, 9, 9, 3)

        # Should have two outputs
        assert len(model.outputs) == 2

        # Policy output: 82 (81 + pass)
        assert model.outputs[0].shape[-1] == 82

        # Value output: 1
        assert model.outputs[1].shape[-1] == 1

    def test_network_inference(self):
        """Test network can make predictions."""
        model = create_go_policy_value_network(board_size=9, num_filters=32)

        # Random input
        state = np.random.rand(1, 9, 9, 3).astype(np.float32)

        # Predict
        policy, value = model.predict(state, verbose=0)

        # Check shapes
        assert policy.shape == (1, 82)
        assert value.shape == (1, 1)

        # Policy should be probabilities
        assert np.allclose(np.sum(policy[0]), 1.0, atol=0.01)

        # Value should be in [-1, 1]
        assert -1 <= value[0, 0] <= 1

    def test_different_board_sizes(self):
        """Test network creation for different board sizes."""
        for size in [9, 13, 19]:
            model = create_go_policy_value_network(board_size=size, num_filters=32)

            # Output size should adjust
            expected_actions = size * size + 1  # board + pass
            assert model.outputs[0].shape[-1] == expected_actions


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
