"""
Integration Tests for Prometheus

Tests how modules work together:
- Training pipeline end-to-end
- Evaluation workflow
- Transfer learning
- Deployment preparation
- Visualization integration

Run with: pytest tests/test_integration.py -v
"""

import pytest
import numpy as np
import tempfile
import os
from pathlib import Path

from prometheus.models.go_models import (
    PrometheusGoAgent,
    StaticGoAgent,
    RandomGoAgent,
    create_go_policy_value_network
)
from prometheus.models.go_mcts import GoMCTSAgent
from prometheus.environments.go import GoEnvironment, GoBoard
from prometheus.training.go_training import train_go_agent, play_go_match
from prometheus.evaluation.benchmark import GoEvaluator, ELOCalculator
from prometheus.analysis.game_analyzer import GoGameAnalyzer, BatchAnalyzer
from prometheus.visualization.training_dashboard import TrainingDashboard, ComparisonDashboard
from prometheus.transfer.transfer_learning import BoardSizeTransfer, FineTuner
from prometheus.optimization.performance import (
    PositionCache,
    CachedAgent,
    ModelOptimizer,
    MemoryManager
)
from prometheus.configs.pretrained_models import ModelBuilder, get_model_config


class TestTrainingPipeline:
    """Test complete training workflow."""

    def test_basic_training(self):
        """Test agent can be trained end-to-end."""
        # Create agent
        agent = PrometheusGoAgent(board_size=9)
        initial_gen = agent.generation

        # Train for a few games
        trained_agent = train_go_agent(agent, num_games=3, verbose=False)

        # Verify training occurred
        assert trained_agent.generation > initial_gen
        assert trained_agent.model is not None

    def test_training_with_evaluation(self):
        """Test training + evaluation workflow."""
        # Train agent
        agent = PrometheusGoAgent(board_size=9)
        trained_agent = train_go_agent(agent, num_games=5, verbose=False)

        # Evaluate
        evaluator = GoEvaluator(board_size=9)
        env = GoEnvironment(board_size=9)
        baseline = RandomGoAgent(board_size=9)

        result = evaluator.evaluate_matchup(
            trained_agent, baseline, env,
            num_games=5,
            verbose=False
        )

        # Verify results structure
        assert 'agent1_wins' in result
        assert 'agent2_wins' in result
        assert 'draws' in result
        assert 'agent1_elo' in result
        assert result['agent1_wins'] + result['agent2_wins'] + result['draws'] == 5

    def test_training_with_dashboard(self):
        """Test training with visualization integration."""
        agent = PrometheusGoAgent(board_size=9)
        dashboard = TrainingDashboard(window_size=10)

        # Train with dashboard updates
        for i in range(3):
            agent = train_go_agent(agent, num_games=1, verbose=False)

            # Update dashboard
            dashboard.update({
                'generation': agent.generation,
                'policy_loss': np.random.rand(),
                'value_loss': np.random.rand()
            })

        # Verify dashboard has data
        assert len(dashboard.metrics['generation']) > 0


class TestEvaluationWorkflow:
    """Test evaluation and benchmarking."""

    def test_elo_calculation(self):
        """Test ELO rating system."""
        calc = ELOCalculator(initial_rating=1200)

        # Play games and update ratings
        calc.update_ratings('agent1', 'agent2', 1.0)  # agent1 wins
        calc.update_ratings('agent1', 'agent2', 0.0)  # agent2 wins

        rating1 = calc.get_rating('agent1')
        rating2 = calc.get_rating('agent2')

        # Ratings should be close to initial (1 win each)
        assert 1150 < rating1 < 1250
        assert 1150 < rating2 < 1250

    def test_tournament(self):
        """Test round-robin tournament."""
        # Create agents
        agent1 = RandomGoAgent(board_size=9)
        agent1.name = "Random1"

        agent2 = RandomGoAgent(board_size=9)
        agent2.name = "Random2"

        agent3 = RandomGoAgent(board_size=9)
        agent3.name = "Random3"

        # Run mini tournament
        evaluator = GoEvaluator(board_size=9)
        env = GoEnvironment(board_size=9)

        results = evaluator.tournament(
            [agent1, agent2, agent3],
            env,
            games_per_matchup=2,
            verbose=False
        )

        # Verify results structure
        assert 'standings' in results
        assert len(results['standings']) == 3
        assert 'matchups' in results

    def test_statistical_significance(self):
        """Test statistical significance calculation."""
        evaluator = GoEvaluator(board_size=9)

        # Create mock result
        mock_result = {
            'agent1_wins': 60,
            'agent2_wins': 40,
            'draws': 0,
            'agent1_win_rate': 0.6,
            'agent2_win_rate': 0.4
        }

        stats = evaluator.calculate_statistical_significance(mock_result)

        # Verify stats structure
        assert 'p_value' in stats
        assert 'significant' in stats
        assert 'agent1_ci' in stats
        assert 'agent2_ci' in stats


class TestAnalysisWorkflow:
    """Test game analysis integration."""

    def test_game_analysis(self):
        """Test analyzing a game."""
        # Play a quick game
        env = GoEnvironment(board_size=9)
        agent1 = RandomGoAgent(board_size=9)
        agent2 = RandomGoAgent(board_size=9)

        result = play_go_match(agent1, agent2, env, num_games=1, verbose=False)
        game_result = result['games'][0]

        # Analyze game
        analyzer = GoGameAnalyzer()
        analysis = analyzer.analyze_game(game_result)

        # Verify analysis structure
        assert 'total_moves' in analysis
        assert 'winner' in analysis
        assert 'statistics' in analysis
        assert 'phases' in analysis

    def test_batch_analysis(self):
        """Test batch analysis of multiple games."""
        # Play a few games
        env = GoEnvironment(board_size=9)
        agent = RandomGoAgent(board_size=9)

        games = []
        for _ in range(3):
            result = play_go_match(agent, agent, env, num_games=1, verbose=False)
            games.extend(result['games'])

        # Batch analysis
        analyzer = GoGameAnalyzer()
        batch = BatchAnalyzer(analyzer)

        for game in games:
            batch.add_game(game)

        report = batch.get_aggregate_report()

        # Verify report structure
        assert 'total_games' in report
        assert report['total_games'] == 3


class TestTransferLearning:
    """Test transfer learning workflows."""

    def test_board_size_transfer(self):
        """Test transferring between board sizes."""
        # Create and "train" source agent
        source_agent = PrometheusGoAgent(board_size=9)

        # Get source model
        source_model = source_agent.model

        # Transfer to larger board
        transfer = BoardSizeTransfer()
        target_model = transfer.transfer(
            source_model,
            source_size=9,
            target_size=13
        )

        # Verify target model created
        assert target_model is not None
        assert target_model.input_shape[1:3] == (13, 13)

    def test_fine_tuning(self):
        """Test fine-tuning workflow."""
        agent = PrometheusGoAgent(board_size=9)

        # Configure for fine-tuning
        tuner = FineTuner(agent.model)
        tuner.configure_fine_tuning(base_lr=1e-5)

        # Count trainable layers
        trainable = sum(1 for layer in agent.model.layers if layer.trainable)

        # Should have some trainable layers
        assert trainable > 0


class TestOptimizationWorkflow:
    """Test optimization and performance features."""

    def test_position_caching(self):
        """Test position cache integration."""
        agent = RandomGoAgent(board_size=9)
        cache = PositionCache(max_size=100)
        cached_agent = CachedAgent(agent, cache)

        env = GoEnvironment(board_size=9)
        state = env.get_state()

        # First call - miss
        initial_misses = cache.misses
        move1 = cached_agent.get_move(state, env.get_legal_moves())

        assert cache.misses == initial_misses + 1

        # Note: For RandomAgent, predictions aren't deterministic,
        # so we can't test cache hits reliably. This tests the integration.

    def test_model_builder(self):
        """Test ModelBuilder fluent API."""
        # Build Go agent
        agent = (ModelBuilder()
            .go(board_size=9)
            .strength('medium')
            .prometheus()
            .build())

        assert agent is not None
        assert agent.board_size == 9
        assert agent.trainable == True

    def test_config_loading(self):
        """Test loading preset configurations."""
        config = get_model_config('go_9x9_medium')

        assert 'board_size' in config
        assert 'num_filters' in config
        assert config['board_size'] == 9


class TestMCTSIntegration:
    """Test MCTS integration with agents."""

    def test_mcts_wrapper(self):
        """Test MCTS wrapping an agent."""
        base_agent = RandomGoAgent(board_size=9)
        mcts_agent = GoMCTSAgent(base_agent, num_simulations=10)

        # Verify wrapper properties
        assert mcts_agent.base_agent == base_agent
        assert mcts_agent.num_simulations == 10

    def test_mcts_move_generation(self):
        """Test MCTS can generate moves."""
        base_agent = RandomGoAgent(board_size=9)
        mcts_agent = GoMCTSAgent(base_agent, num_simulations=5)

        env = GoEnvironment(board_size=9)
        state = env.get_state()
        legal_moves = env.get_legal_moves()

        # Should be able to get a move
        move = mcts_agent.get_move(state, legal_moves)

        assert move in legal_moves


class TestModelPersistence:
    """Test saving and loading models."""

    def test_save_and_load(self):
        """Test model can be saved and loaded."""
        import tensorflow as tf

        agent = PrometheusGoAgent(board_size=9)

        # Save to temporary file
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, 'test_model.h5')

            # Save
            agent.model.save(model_path)

            # Load
            loaded_model = tf.keras.models.load_model(model_path)

            # Verify structure matches
            assert loaded_model.input_shape == agent.model.input_shape
            assert len(loaded_model.layers) == len(agent.model.layers)

    def test_model_builder_creates_saveable_models(self):
        """Test models from ModelBuilder can be saved."""
        import tensorflow as tf

        agent = (ModelBuilder()
            .go(board_size=9)
            .strength('light')
            .prometheus()
            .build())

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, 'builder_model.h5')

            # Should save without errors
            agent.model.save(model_path)

            # Should load without errors
            loaded = tf.keras.models.load_model(model_path)

            assert loaded is not None


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""

    def test_complete_pipeline(self):
        """Test train → evaluate → save → load → deploy workflow."""
        import tensorflow as tf

        # 1. Train
        agent = PrometheusGoAgent(board_size=9)
        trained = train_go_agent(agent, num_games=2, verbose=False)

        # 2. Evaluate
        evaluator = GoEvaluator(board_size=9)
        env = GoEnvironment(board_size=9)
        baseline = RandomGoAgent(board_size=9)

        result = evaluator.evaluate_matchup(
            trained, baseline, env,
            num_games=2,
            verbose=False
        )

        assert 'agent1_elo' in result

        # 3. Save
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, 'pipeline_model.h5')
            trained.model.save(model_path)

            # 4. Load
            new_agent = PrometheusGoAgent(board_size=9)
            new_agent.model = tf.keras.models.load_model(model_path)

            # 5. Verify loaded agent works
            state = env.reset()
            legal_moves = env.get_legal_moves()
            move = new_agent.get_move(state, legal_moves)

            assert move in legal_moves

    def test_transfer_learning_pipeline(self):
        """Test train small → transfer → train large workflow."""
        # 1. Train small model
        small_agent = PrometheusGoAgent(board_size=9)
        small_trained = train_go_agent(small_agent, num_games=2, verbose=False)

        # 2. Transfer to large board
        transfer = BoardSizeTransfer()
        large_model = transfer.transfer(
            small_trained.model,
            source_size=9,
            target_size=13
        )

        # 3. Create large agent
        large_agent = PrometheusGoAgent(board_size=13)
        large_agent.model = large_model

        # 4. Verify large agent works
        env = GoEnvironment(board_size=13)
        state = env.reset()
        legal_moves = env.get_legal_moves()
        move = large_agent.get_move(state, legal_moves)

        assert move in legal_moves


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
