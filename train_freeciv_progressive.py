#!/usr/bin/env python3
"""
Progressive FreeCiv Training for Prometheus

Trains Prometheus agent to beat FreeCiv AI at progressively harder difficulties:
1. Novice (baseline)
2. Easy
3. Normal
4. Hard
5. Cheating (AI gets resource bonuses)
6. Experimental (hardest, maximum cheating)

Uses CRLS learning loop to evolve strategies through self-play.
"""

import sys
import json
from datetime import datetime
from typing import Dict, Any

from prometheus.freeciv_agent import FreeCivAgent
from prometheus.freeciv_environment import DifficultyLevel


class ProgressiveTrainer:
    """
    Progressive difficulty trainer for FreeCiv

    Trains agent at each difficulty level until performance threshold met,
    then advances to next difficulty.
    """

    def __init__(self, performance_threshold: float = 0.7, use_simulator: bool = False):
        """
        Args:
            performance_threshold: Win rate required to advance (0.0-1.0)
            use_simulator: Use simulator instead of real FreeCiv server
        """
        self.agent = FreeCivAgent("prometheus_freeciv", use_simulator=use_simulator)
        self.performance_threshold = performance_threshold
        self.use_simulator = use_simulator

        # Difficulty progression
        self.difficulties = [
            DifficultyLevel.NOVICE,
            DifficultyLevel.EASY,
            DifficultyLevel.NORMAL,
            DifficultyLevel.HARD,
            DifficultyLevel.CHEATING,
            DifficultyLevel.EXPERIMENTAL
        ]

        self.current_difficulty_index = 0
        self.training_log = []

    def train_progressive(self, games_per_level: int = 20,
                         max_games_per_level: int = 50):
        """
        Train progressively through difficulty levels

        Args:
            games_per_level: Base number of games per level
            max_games_per_level: Maximum games before forcing advancement
        """
        print("=" * 60)
        print("PROMETHEUS PROGRESSIVE FREECIV TRAINING")
        print("=" * 60)
        print(f"Performance Threshold: {self.performance_threshold * 100:.0f}%")
        print(f"Games per Level: {games_per_level}")
        print("=" * 60)
        print()

        for difficulty_index, difficulty in enumerate(self.difficulties):
            self.current_difficulty_index = difficulty_index

            print(f"\n{'#'*60}")
            print(f"# LEVEL {difficulty_index + 1}/6: {difficulty.value.upper()}")
            print(f"{'#'*60}\n")

            # Train at this level
            result = self._train_at_difficulty(
                difficulty,
                games_per_level,
                max_games_per_level
            )

            # Log results
            self.training_log.append(result)

            # Print result
            self._print_level_result(result)

            # Check if we can advance
            if result['win_rate'] < self.performance_threshold:
                print(f"\n⚠ Performance threshold not met at {difficulty.value}")
                print(f"   Win rate: {result['win_rate']*100:.1f}% < {self.performance_threshold*100:.0f}%")
                print(f"   Continuing to next level anyway...")

        # Final summary
        self._print_final_summary()

    def _train_at_difficulty(self, difficulty: DifficultyLevel,
                            min_games: int, max_games: int) -> Dict[str, Any]:
        """
        Train at specific difficulty level

        Args:
            difficulty: Difficulty level
            min_games: Minimum games to play
            max_games: Maximum games before stopping

        Returns:
            Training results for this level
        """
        start_time = datetime.now()
        games_before = self.agent.total_games
        wins_before = self.agent.win_count

        print(f"Training at {difficulty.value} difficulty...")
        print(f"Target: {self.performance_threshold * 100:.0f}% win rate")
        print()

        # Play minimum games
        for game_num in range(min_games):
            print(f"\nGame {game_num + 1}/{min_games}")

            game_history = self.agent.play_game(
                difficulty=difficulty,
                max_turns=200
            )

            learning_result = self.agent.learn_from_game(game_history)

        # Calculate performance
        games_played = self.agent.total_games - games_before
        wins = self.agent.win_count - wins_before
        win_rate = wins / games_played if games_played > 0 else 0.0

        # Continue until threshold met or max games reached
        while win_rate < self.performance_threshold and games_played < max_games:
            print(f"\nCurrent win rate: {win_rate*100:.1f}% - Continuing...")

            game_history = self.agent.play_game(
                difficulty=difficulty,
                max_turns=200
            )

            learning_result = self.agent.learn_from_game(game_history)

            games_played = self.agent.total_games - games_before
            wins = self.agent.win_count - wins_before
            win_rate = wins / games_played if games_played > 0 else 0.0

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        result = {
            'difficulty': difficulty.value,
            'games_played': games_played,
            'wins': wins,
            'win_rate': win_rate,
            'generation': self.agent.generation,
            'best_score': self.agent.best_score,
            'duration_seconds': duration,
            'threshold_met': win_rate >= self.performance_threshold
        }

        return result

    def _print_level_result(self, result: Dict[str, Any]):
        """Print results for a difficulty level"""
        print(f"\n{'='*60}")
        print(f"LEVEL COMPLETE: {result['difficulty'].upper()}")
        print(f"{'='*60}")
        print(f"Games Played: {result['games_played']}")
        print(f"Wins: {result['wins']}")
        print(f"Win Rate: {result['win_rate']*100:.1f}%")
        print(f"Best Score: {result['best_score']}")
        print(f"Generation: {result['generation']}")
        print(f"Duration: {result['duration_seconds']:.1f}s")
        print(f"Threshold Met: {'✓' if result['threshold_met'] else '✗'}")
        print(f"{'='*60}\n")

    def _print_final_summary(self):
        """Print final training summary"""
        print("\n" + "="*60)
        print("PROGRESSIVE TRAINING COMPLETE")
        print("="*60)
        print()

        # Summary table
        print("Difficulty Level Results:")
        print("-" * 60)
        print(f"{'Level':<15} {'Games':<8} {'Wins':<8} {'Win Rate':<12} {'Status'}")
        print("-" * 60)

        for result in self.training_log:
            status = "✓ PASS" if result['threshold_met'] else "✗ FAIL"
            print(f"{result['difficulty']:<15} "
                  f"{result['games_played']:<8} "
                  f"{result['wins']:<8} "
                  f"{result['win_rate']*100:>6.1f}%     "
                  f"{status}")

        print("-" * 60)
        print()

        # Overall stats
        total_games = sum(r['games_played'] for r in self.training_log)
        total_wins = sum(r['wins'] for r in self.training_log)
        overall_win_rate = total_wins / total_games if total_games > 0 else 0.0

        print("Overall Statistics:")
        print(f"  Total Games: {total_games}")
        print(f"  Total Wins: {total_wins}")
        print(f"  Overall Win Rate: {overall_win_rate*100:.1f}%")
        print(f"  Final Generation: {self.agent.generation}")
        print(f"  Best Score: {self.agent.best_score}")
        print()

        # Check if all levels passed
        all_passed = all(r['threshold_met'] for r in self.training_log)
        if all_passed:
            print("🎉 ALL DIFFICULTY LEVELS PASSED!")
        else:
            failed = [r['difficulty'] for r in self.training_log if not r['threshold_met']]
            print(f"⚠ Failed levels: {', '.join(failed)}")

        print("="*60)

    def save_results(self, filename: str = "freeciv_training_results.json"):
        """Save training results to file"""
        results = {
            'agent_id': self.agent.agent_id,
            'performance_threshold': self.performance_threshold,
            'training_log': self.training_log,
            'final_stats': self.agent.get_stats(),
            'timestamp': datetime.now().isoformat()
        }

        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\nResults saved to {filename}")


def main():
    """Main training script"""
    print("\n" + "="*60)
    print("PROMETHEUS FREECIV PROGRESSIVE TRAINING")
    print("="*60)
    print()

    # Configuration
    PERFORMANCE_THRESHOLD = 0.70  # 70% win rate to advance
    GAMES_PER_LEVEL = 20
    MAX_GAMES_PER_LEVEL = 50
    USE_SIMULATOR = True  # Use simulator by default (no FreeCiv server needed)

    print("Configuration:")
    print(f"  Performance Threshold: {PERFORMANCE_THRESHOLD * 100:.0f}%")
    print(f"  Games per Level: {GAMES_PER_LEVEL}")
    print(f"  Max Games per Level: {MAX_GAMES_PER_LEVEL}")
    print(f"  Mode: {'Simulator' if USE_SIMULATOR else 'Real FreeCiv Server'}")
    print()

    input("Press Enter to start training...")

    # Create trainer
    trainer = ProgressiveTrainer(
        performance_threshold=PERFORMANCE_THRESHOLD,
        use_simulator=USE_SIMULATOR
    )

    try:
        # Run progressive training
        trainer.train_progressive(
            games_per_level=GAMES_PER_LEVEL,
            max_games_per_level=MAX_GAMES_PER_LEVEL
        )

        # Save results
        trainer.save_results()

        return 0

    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user")
        trainer.save_results("freeciv_training_interrupted.json")
        return 1

    except Exception as e:
        print(f"\n\nError during training: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
