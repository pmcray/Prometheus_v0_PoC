#!/usr/bin/env python3
"""
Example: Transfer Learning Between Board Sizes

This script demonstrates transfer learning:
1. Load trained model for small board
2. Transfer to larger board
3. Fine-tune on larger board
4. Evaluate improvement

Usage:
    python examples/transfer_learning.py \
        --source models/go_9x9.h5 \
        --target-size 19 \
        --output models/go_19x19.h5
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tensorflow as tf
from prometheus.transfer import BoardSizeTransfer, FineTuner
from prometheus.models.go_models import PrometheusGoAgent, RandomGoAgent
from prometheus.training.go_training import train_go_agent
from prometheus.evaluation.benchmark import GoEvaluator
from prometheus.environments.go import GoEnvironment


def main():
    """Main transfer learning pipeline."""
    parser = argparse.ArgumentParser(
        description='Transfer learning between board sizes'
    )

    parser.add_argument(
        '--source',
        type=str,
        required=True,
        help='Source model path (.h5 file)'
    )

    parser.add_argument(
        '--source-size',
        type=int,
        default=9,
        choices=[9, 13, 19],
        help='Source board size (default: 9)'
    )

    parser.add_argument(
        '--target-size',
        type=int,
        default=19,
        choices=[9, 13, 19],
        help='Target board size (default: 19)'
    )

    parser.add_argument(
        '--fine-tune-games',
        type=int,
        default=50,
        help='Number of fine-tuning games (default: 50)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Output model path (default: models/go_TARGET.h5)'
    )

    parser.add_argument(
        '--evaluate',
        action='store_true',
        help='Evaluate before and after transfer'
    )

    args = parser.parse_args()

    if not Path(args.source).exists():
        print(f"Error: Source model not found: {args.source}")
        return 1

    if args.source_size >= args.target_size:
        print("Error: Target size must be larger than source size")
        return 1

    print("="*70)
    print("TRANSFER LEARNING PIPELINE")
    print("="*70)

    # 1. Load source model
    print(f"\n1. Loading source model...")
    print(f"   Source: {args.source}")
    print(f"   Board size: {args.source_size}x{args.source_size}")

    source_model = tf.keras.models.load_model(args.source)
    print(f"   ✓ Loaded: {source_model.count_params():,} parameters")

    # 2. Transfer to target size
    print(f"\n2. Transferring to {args.target_size}x{args.target_size}...")

    transfer = BoardSizeTransfer()
    target_model = transfer.transfer(
        source_model,
        source_size=args.source_size,
        target_size=args.target_size
    )

    print(f"   ✓ Transfer complete")
    print(f"   ✓ Target model: {target_model.count_params():,} parameters")

    # 3. Create target agent
    print(f"\n3. Creating target agent...")

    target_agent = PrometheusGoAgent(board_size=args.target_size)
    target_agent.model = target_model
    print(f"   ✓ Agent created")

    # 4. Evaluate before fine-tuning (optional)
    if args.evaluate:
        print(f"\n4. Evaluating before fine-tuning...")

        evaluator = GoEvaluator(board_size=args.target_size)
        env = GoEnvironment(board_size=args.target_size)
        baseline = RandomGoAgent(board_size=args.target_size)

        result_before = evaluator.evaluate_matchup(
            target_agent, baseline, env,
            num_games=20,
            verbose=False
        )

        print(f"   Before fine-tuning:")
        print(f"   Win rate: {result_before['agent1_win_rate']:.1%}")
        print(f"   ELO: {result_before['agent1_elo']:.0f}")

    # 5. Fine-tune on target board size
    if args.fine_tune_games > 0:
        print(f"\n5. Fine-tuning ({args.fine_tune_games} games)...")

        # Configure for fine-tuning with low learning rate
        tuner = FineTuner(target_agent.model)
        tuner.configure_fine_tuning(
            base_lr=1e-5,  # Low learning rate
            unfreeze_from_layer=-10  # Unfreeze last 10 layers
        )

        # Train
        target_agent = train_go_agent(
            target_agent,
            num_games=args.fine_tune_games,
            verbose=True
        )

        print(f"   ✓ Fine-tuning complete")
        print(f"   ✓ Generation: {target_agent.generation}")

    # 6. Evaluate after fine-tuning (optional)
    if args.evaluate and args.fine_tune_games > 0:
        print(f"\n6. Evaluating after fine-tuning...")

        result_after = evaluator.evaluate_matchup(
            target_agent, baseline, env,
            num_games=20,
            verbose=False
        )

        print(f"   After fine-tuning:")
        print(f"   Win rate: {result_after['agent1_win_rate']:.1%}")
        print(f"   ELO: {result_after['agent1_elo']:.0f}")

        # Show improvement
        elo_improvement = result_after['agent1_elo'] - result_before['agent1_elo']
        wr_improvement = result_after['agent1_win_rate'] - result_before['agent1_win_rate']

        print(f"\n   Improvement:")
        print(f"   ELO: {elo_improvement:+.0f}")
        print(f"   Win rate: {wr_improvement:+.1%}")

    # 7. Save model
    output_path = args.output or f"models/go_{args.target_size}x{args.target_size}_transferred.h5"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n7. Saving model...")
    target_agent.model.save(str(output_path))
    print(f"   ✓ Saved: {output_path}")

    # Summary
    print("\n" + "="*70)
    print("TRANSFER COMPLETE")
    print("="*70)
    print(f"Source: {args.source_size}x{args.source_size}")
    print(f"Target: {args.target_size}x{args.target_size}")
    print(f"Output: {output_path}")

    if args.evaluate:
        print(f"\nPerformance:")
        print(f"  Before: {result_before['agent1_win_rate']:.1%} win rate, {result_before['agent1_elo']:.0f} ELO")
        if args.fine_tune_games > 0:
            print(f"  After:  {result_after['agent1_win_rate']:.1%} win rate, {result_after['agent1_elo']:.0f} ELO")
            print(f"  Gain:   {wr_improvement:+.1%} win rate, {elo_improvement:+.0f} ELO")

    print("\nNext steps:")
    print(f"  1. Train more: python examples/train_go_agent.py --board-size {args.target_size}")
    print(f"  2. Deploy: python scripts/deploy_ogs_bot.py --model {output_path}")
    print(f"  3. Evaluate: python examples/evaluate_agents.py --agents {output_path}")
    print("="*70 + "\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
