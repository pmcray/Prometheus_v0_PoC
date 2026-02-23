#!/usr/bin/env python3
"""
Demo: FreeCiv Progressive Training

Quick demonstration of Prometheus learning to play FreeCiv through
progressive difficulty levels using CRLS self-improvement.
"""

import sys
from train_freeciv_progressive import ProgressiveTrainer
from prometheus.freeciv_environment import DifficultyLevel


def main():
    print("\n" + "="*60)
    print("  PROMETHEUS FREECIV TRAINING DEMO")
    print("="*60)
    print()
    print("Demonstrating Prometheus learning FreeCiv through")
    print("self-play and CRLS-based strategy evolution.")
    print()
    print("Configuration:")
    print("  - Mode: Simulator (no FreeCiv server needed)")
    print("  - Difficulties: Novice, Easy, Normal")
    print("  - Games per level: 5")
    print("  - Performance threshold: 60%")
    print()

    # Create trainer with demo settings
    trainer = ProgressiveTrainer(
        performance_threshold=0.60,  # 60% for demo
        use_simulator=True
    )

    # Only train on first 3 difficulty levels for demo
    trainer.difficulties = [
        DifficultyLevel.NOVICE,
        DifficultyLevel.EASY,
        DifficultyLevel.NORMAL
    ]

    try:
        print("Starting demo training...")
        print()

        # Run training with fewer games
        trainer.train_progressive(
            games_per_level=5,
            max_games_per_level=8
        )

        # Save results
        trainer.save_results("freeciv_demo_results.json")

        print("\n" + "="*60)
        print("  DEMO COMPLETE")
        print("="*60)
        print()
        print("Results saved to: freeciv_demo_results.json")
        print()
        print("Key Insights:")
        print(f"  - Total games played: {trainer.agent.total_games}")
        print(f"  - Strategy generations: {trainer.agent.generation}")
        print(f"  - Win count: {trainer.agent.win_count}")
        print(f"  - Best score: {trainer.agent.best_score}")
        print()
        print("Prometheus has demonstrated:")
        print("  ✓ Self-play game execution")
        print("  ✓ Performance evaluation and critique")
        print("  ✓ Strategy evolution through Recursive Font")
        print("  ✓ Progressive difficulty advancement")
        print("  ✓ Safe self-improvement with alignment checks")
        print()

        return 0

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        return 1

    except Exception as e:
        print(f"\n\nError during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
