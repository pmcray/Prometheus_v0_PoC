#!/usr/bin/env python3
"""
Example: Train a Go Agent from Scratch

This script demonstrates the complete workflow for training a Go agent:
1. Create agent with preset configuration
2. Train via self-play
3. Evaluate against baseline
4. Save model for deployment

Usage:
    python examples/train_go_agent.py --board-size 9 --num-games 100
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from prometheus.configs import ModelBuilder, create_mcts_agent
from prometheus.training.go_training import train_go_agent
from prometheus.evaluation.benchmark import GoEvaluator
from prometheus.environments.go import GoEnvironment
from prometheus.models.go_models import RandomGoAgent
from prometheus.visualization.training_dashboard import TrainingDashboard


def main():
    """Main training pipeline."""
    parser = argparse.ArgumentParser(
        description='Train a Go agent from scratch',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--board-size',
        type=int,
        default=9,
        choices=[9, 13, 19],
        help='Board size (default: 9)'
    )

    parser.add_argument(
        '--num-games',
        type=int,
        default=100,
        help='Number of training games (default: 100)'
    )

    parser.add_argument(
        '--strength',
        type=str,
        default='medium',
        choices=['light', 'medium', 'strong'],
        help='Agent strength (default: medium)'
    )

    parser.add_argument(
        '--mcts',
        action='store_true',
        help='Enable MCTS enhancement'
    )

    parser.add_argument(
        '--mcts-sims',
        type=int,
        default=400,
        help='MCTS simulations per move (default: 400)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='models/go_agent.h5',
        help='Output model path (default: models/go_agent.h5)'
    )

    parser.add_argument(
        '--evaluate',
        action='store_true',
        help='Evaluate against random baseline after training'
    )

    parser.add_argument(
        '--eval-games',
        type=int,
        default=50,
        help='Number of evaluation games (default: 50)'
    )

    parser.add_argument(
        '--visualize',
        action='store_true',
        help='Show training dashboard'
    )

    args = parser.parse_args()

    print("="*70)
    print("GO AGENT TRAINING PIPELINE")
    print("="*70)

    # 1. Create agent
    print(f"\n1. Creating agent...")
    print(f"   Board size: {args.board_size}x{args.board_size}")
    print(f"   Strength: {args.strength}")
    print(f"   MCTS: {'Yes' if args.mcts else 'No'}")

    agent = (ModelBuilder()
        .go(board_size=args.board_size)
        .strength(args.strength)
        .prometheus()
        .build())

    print(f"   ✓ Agent created: {agent.model.count_params():,} parameters")

    # 2. Setup visualization
    dashboard = None
    if args.visualize:
        dashboard = TrainingDashboard()
        print("   ✓ Training dashboard initialized")

    # 3. Train
    print(f"\n2. Training ({args.num_games} games)...")
    print("   This may take a while...")

    trained_agent = train_go_agent(
        agent,
        num_games=args.num_games,
        verbose=True
    )

    print(f"   ✓ Training complete")
    print(f"   ✓ Final generation: {trained_agent.generation}")

    # 4. Add MCTS if requested
    if args.mcts:
        print(f"\n3. Adding MCTS ({args.mcts_sims} simulations)...")

        from prometheus.configs import get_mcts_preset
        preset = None
        if args.mcts_sims <= 100:
            preset = 'fast'
        elif args.mcts_sims <= 400:
            preset = 'standard'
        elif args.mcts_sims <= 800:
            preset = 'strong'
        else:
            preset = 'alphazero'

        trained_agent = create_mcts_agent(trained_agent, preset_name=preset)
        print(f"   ✓ MCTS enabled (preset: {preset})")
        print(f"   ✓ Expected +300-500 ELO improvement")

    # 5. Evaluate
    if args.evaluate:
        print(f"\n4. Evaluating ({args.eval_games} games vs random)...")

        evaluator = GoEvaluator(board_size=args.board_size)
        env = GoEnvironment(board_size=args.board_size)
        baseline = RandomGoAgent(board_size=args.board_size)

        result = evaluator.evaluate_matchup(
            trained_agent,
            baseline,
            env,
            num_games=args.eval_games,
            verbose=False
        )

        print(f"\n   Results:")
        print(f"   Win rate: {result['agent1_win_rate']:.1%}")
        print(f"   ELO rating: {result['agent1_elo']:.0f}")
        print(f"   Wins: {result['agent1_wins']}")
        print(f"   Losses: {result['agent2_wins']}")
        print(f"   Draws: {result['draws']}")

        # Statistical significance
        stats = evaluator.calculate_statistical_significance(result)
        print(f"\n   Statistical Significance:")
        print(f"   p-value: {stats['p_value']:.4f}")
        print(f"   Significant: {stats['significant']}")
        print(f"   95% CI: [{stats['agent1_ci'][0]:.1%}, {stats['agent1_ci'][1]:.1%}]")

    # 6. Save model
    print(f"\n5. Saving model...")

    # Create output directory if needed
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save base agent model
    if args.mcts:
        # Save base agent, not MCTS wrapper
        trained_agent.base_agent.model.save(str(output_path))
    else:
        trained_agent.model.save(str(output_path))

    print(f"   ✓ Model saved: {output_path}")

    # 7. Show dashboard
    if args.visualize and dashboard:
        print(f"\n6. Displaying training dashboard...")
        dashboard.plot()

    # Summary
    print("\n" + "="*70)
    print("TRAINING COMPLETE")
    print("="*70)
    print(f"Model: {output_path}")
    print(f"Board size: {args.board_size}x{args.board_size}")
    print(f"Generation: {trained_agent.generation if not args.mcts else trained_agent.base_agent.generation}")

    if args.evaluate:
        print(f"ELO: {result['agent1_elo']:.0f}")
        print(f"Win rate: {result['agent1_win_rate']:.1%}")

    print("\nNext steps:")
    print(f"  1. Deploy: python scripts/deploy_ogs_bot.py --model {output_path}")
    print(f"  2. Analyze: Use GoGameAnalyzer to analyze games")
    print(f"  3. Transfer: Transfer to larger board size")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
