#!/usr/bin/env python3
"""
Train Pre-trained Models for Prometheus

This script trains baseline models that users can download and use immediately.

Usage:
    python scripts/train_pretrained_models.py --all
    python scripts/train_pretrained_models.py --model go-9x9
    python scripts/train_pretrained_models.py --model chess --games 500
"""

import argparse
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def train_go_9x9(num_games=200, use_mcts=True):
    """Train 9x9 Go model."""
    print("=" * 70)
    print("TRAINING: Go 9×9")
    print("=" * 70)
    print(f"Games: {num_games}")
    print(f"MCTS: {use_mcts}")
    print()

    from prometheus.models.go_models import PrometheusGoAgent, RandomGoAgent
    from prometheus.environments.go import GoEnvironment
    from prometheus.training.go_training import train_go_agent
    from prometheus.evaluation.benchmark import GoEvaluator
    from prometheus.configs import ModelBuilder

    # Create agent
    print("1. Creating agent...")
    agent = (
        ModelBuilder()
        .go(board_size=9)
        .strength('medium')
        .prometheus()
        .build()
    )
    print(f"   Parameters: {agent.model.count_params():,}")

    # Add MCTS
    if use_mcts:
        from prometheus.mcts import add_mcts
        agent = add_mcts(agent, num_simulations=400, preset='standard')
        print("   MCTS enabled: 400 simulations")

    # Train
    print("\n2. Training...")
    start_time = time.time()
    trained_agent = train_go_agent(
        agent,
        num_games=num_games,
        verbose=True
    )
    train_time = time.time() - start_time
    print(f"   Training time: {train_time/60:.1f} minutes")

    # Evaluate
    print("\n3. Evaluating...")
    evaluator = GoEvaluator(board_size=9)
    env = GoEnvironment(board_size=9)
    baseline = RandomGoAgent(board_size=9)

    result = evaluator.evaluate_matchup(
        trained_agent,
        baseline,
        env,
        num_games=50,
        verbose=True
    )

    print(f"\n   Win rate: {result['agent1_win_rate']:.1%}")
    print(f"   ELO: {result['agent1_elo']:.0f}")
    print(f"   Record: {result['agent1_wins']}-{result['agent2_wins']}-{result['draws']}")

    # Save
    output_path = Path('models/pretrained/go_9x9.h5')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    trained_agent.model.save(str(output_path))
    print(f"\n✓ Model saved: {output_path}")

    # Save metadata
    import json
    metadata = {
        'model': 'go_9x9',
        'board_size': 9,
        'training_games': num_games,
        'training_time_minutes': train_time / 60,
        'mcts_enabled': use_mcts,
        'mcts_simulations': 400 if use_mcts else 0,
        'win_rate_vs_random': result['agent1_win_rate'],
        'elo': result['agent1_elo'],
        'parameters': agent.model.count_params(),
        'strength': 'medium',
    }

    metadata_path = output_path.parent / 'go_9x9_metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Metadata saved: {metadata_path}")

    return output_path, metadata


def train_go_19x19_transfer(source_model=None, num_games=100):
    """Train 19x19 Go model via transfer learning."""
    print("=" * 70)
    print("TRAINING: Go 19×19 (Transfer Learning)")
    print("=" * 70)
    print(f"Fine-tuning games: {num_games}")
    print()

    from prometheus.models.go_models import PrometheusGoAgent, RandomGoAgent
    from prometheus.environments.go import GoEnvironment
    from prometheus.training.go_training import train_go_agent
    from prometheus.evaluation.benchmark import GoEvaluator
    from prometheus.transfer import BoardSizeTransfer, FineTuner
    import tensorflow as tf

    # Load source model
    if source_model is None:
        source_model = 'models/pretrained/go_9x9.h5'

    print(f"1. Loading source model: {source_model}")
    source = tf.keras.models.load_model(source_model)
    print(f"   Parameters: {source.count_params():,}")

    # Transfer to 19x19
    print("\n2. Transferring to 19×19...")
    transfer = BoardSizeTransfer()
    target_model = transfer.transfer(
        source,
        source_size=9,
        target_size=19
    )
    print(f"   Target parameters: {target_model.count_params():,}")

    # Create agent
    agent_19 = PrometheusGoAgent(board_size=19)
    agent_19.model = target_model

    # Configure fine-tuning
    print("\n3. Configuring fine-tuning...")
    tuner = FineTuner(agent_19.model)
    tuner.configure_fine_tuning(
        base_lr=1e-4,
        unfreeze_from_layer=-15
    )

    # Fine-tune
    print("\n4. Fine-tuning...")
    start_time = time.time()
    finetuned_19 = train_go_agent(
        agent_19,
        num_games=num_games,
        verbose=True
    )
    train_time = time.time() - start_time
    print(f"   Fine-tuning time: {train_time/60:.1f} minutes")

    # Evaluate
    print("\n5. Evaluating...")
    evaluator = GoEvaluator(board_size=19)
    env = GoEnvironment(board_size=19)
    baseline = RandomGoAgent(board_size=19)

    result = evaluator.evaluate_matchup(
        finetuned_19,
        baseline,
        env,
        num_games=30,
        verbose=True
    )

    print(f"\n   Win rate: {result['agent1_win_rate']:.1%}")
    print(f"   ELO: {result['agent1_elo']:.0f}")

    # Save
    output_path = Path('models/pretrained/go_19x19.h5')
    finetuned_19.model.save(str(output_path))
    print(f"\n✓ Model saved: {output_path}")

    # Save metadata
    import json
    metadata = {
        'model': 'go_19x19',
        'board_size': 19,
        'transfer_source': str(source_model),
        'fine_tuning_games': num_games,
        'training_time_minutes': train_time / 60,
        'win_rate_vs_random': result['agent1_win_rate'],
        'elo': result['agent1_elo'],
        'parameters': finetuned_19.model.count_params(),
        'strength': 'medium',
    }

    metadata_path = output_path.parent / 'go_19x19_metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Metadata saved: {metadata_path}")

    return output_path, metadata


def train_chess(num_games=200, use_mcts=True):
    """Train Chess model."""
    print("=" * 70)
    print("TRAINING: Chess")
    print("=" * 70)
    print(f"Games: {num_games}")
    print(f"MCTS: {use_mcts}")
    print()

    from prometheus.models.chess_models import PrometheusChessAgent, RandomChessAgent
    from prometheus.environments.chess_env import ChessEnvironment
    from prometheus.training.chess_training import train_chess_agent
    from prometheus.evaluation.chess_evaluator import ChessEvaluator
    from prometheus.configs import ModelBuilder

    # Create agent
    print("1. Creating agent...")
    agent = (
        ModelBuilder()
        .chess()
        .strength('medium')
        .prometheus()
        .build()
    )
    print(f"   Parameters: {agent.model.count_params():,}")

    # Add MCTS
    if use_mcts:
        from prometheus.mcts import add_mcts
        agent = add_mcts(agent, num_simulations=400, preset='standard')
        print("   MCTS enabled: 400 simulations")

    # Train
    print("\n2. Training...")
    start_time = time.time()
    trained_agent = train_chess_agent(
        agent,
        num_games=num_games,
        verbose=True
    )
    train_time = time.time() - start_time
    print(f"   Training time: {train_time/60:.1f} minutes")

    # Evaluate
    print("\n3. Evaluating...")
    evaluator = ChessEvaluator()
    env = ChessEnvironment()
    baseline = RandomChessAgent()

    result = evaluator.evaluate_matchup(
        trained_agent,
        baseline,
        env,
        num_games=50,
        verbose=True
    )

    print(f"\n   Win rate: {result['agent1_win_rate']:.1%}")
    print(f"   ELO: {result['agent1_elo']:.0f}")

    # Save
    output_path = Path('models/pretrained/chess.h5')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    trained_agent.model.save(str(output_path))
    print(f"\n✓ Model saved: {output_path}")

    # Save metadata
    import json
    metadata = {
        'model': 'chess',
        'training_games': num_games,
        'training_time_minutes': train_time / 60,
        'mcts_enabled': use_mcts,
        'mcts_simulations': 400 if use_mcts else 0,
        'win_rate_vs_random': result['agent1_win_rate'],
        'elo': result['agent1_elo'],
        'parameters': agent.model.count_params(),
        'strength': 'medium',
    }

    metadata_path = output_path.parent / 'chess_metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Metadata saved: {metadata_path}")

    return output_path, metadata


def main():
    parser = argparse.ArgumentParser(description='Train pre-trained Prometheus models')
    parser.add_argument('--all', action='store_true',
                       help='Train all models (Go 9x9, Go 19x19, Chess)')
    parser.add_argument('--model', choices=['go-9x9', 'go-19x19', 'chess'],
                       help='Specific model to train')
    parser.add_argument('--games', type=int, default=200,
                       help='Number of training games')
    parser.add_argument('--no-mcts', action='store_true',
                       help='Disable MCTS during training')

    args = parser.parse_args()

    if not args.all and not args.model:
        parser.print_help()
        sys.exit(1)

    results = {}

    try:
        if args.all or args.model == 'go-9x9':
            path, metadata = train_go_9x9(args.games, not args.no_mcts)
            results['go-9x9'] = {'path': path, 'metadata': metadata}

        if args.all or args.model == 'go-19x19':
            # Use trained 9x9 if available
            source = 'models/pretrained/go_9x9.h5' if Path('models/pretrained/go_9x9.h5').exists() else None
            path, metadata = train_go_19x19_transfer(source, args.games // 2)
            results['go-19x19'] = {'path': path, 'metadata': metadata}

        if args.all or args.model == 'chess':
            path, metadata = train_chess(args.games, not args.no_mcts)
            results['chess'] = {'path': path, 'metadata': metadata}

        # Print summary
        print("\n" + "=" * 70)
        print("TRAINING COMPLETE!")
        print("=" * 70)
        for model_name, data in results.items():
            print(f"\n{model_name}:")
            print(f"  Path: {data['path']}")
            print(f"  ELO: {data['metadata']['elo']:.0f}")
            print(f"  Win rate: {data['metadata']['win_rate_vs_random']:.1%}")

    except KeyboardInterrupt:
        print("\n\n⚠️  Training interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
