#!/usr/bin/env python3
"""
Hyperparameter Tuning for Prometheus

Automatically search for optimal hyperparameters using grid search,
random search, or Bayesian optimization.

Usage:
    # Grid search for MCTS parameters
    python scripts/tune_hyperparameters.py \\
        --model models/pretrained/go_9x9.h5 \\
        --param mcts_sims --values 100 200 400 800 \\
        --param c_puct --values 0.5 1.0 1.5 2.0 \\
        --num-games 20

    # Random search for training hyperparameters
    python scripts/tune_hyperparameters.py \\
        --search random \\
        --param learning_rate --range 0.0001 0.01 log \\
        --param batch_size --values 16 32 64 \\
        --trials 10

    # Quick MCTS tuning
    python scripts/tune_hyperparameters.py \\
        --quick-mcts \\
        --model models/pretrained/chess.h5 \\
        --game chess
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
import itertools
import numpy as np


class HyperparameterTuner:
    """Hyperparameter tuning engine."""

    def __init__(
        self,
        model_path: str = None,
        game: str = "go",
        board_size: int = 9,
        num_games: int = 20,
        opponent: str = "random",
        verbose: bool = False
    ):
        self.model_path = model_path
        self.game = game
        self.board_size = board_size
        self.num_games = num_games
        self.opponent = opponent
        self.verbose = verbose

        self.results = []

    def evaluate_config(self, config: Dict[str, Any]) -> Dict[str, float]:
        """
        Evaluate a hyperparameter configuration.

        Args:
            config: Dictionary of hyperparameter values

        Returns:
            Dictionary with performance metrics
        """
        if self.verbose:
            print(f"\nEvaluating config: {config}")

        # Import compare_models functionality
        from scripts.compare_models import compare_models

        # Extract MCTS parameters
        mcts_sims = config.get('mcts_sims', 0)
        c_puct = config.get('c_puct', 1.0)

        # Run comparison
        results = compare_models(
            model1_path=self.model_path,
            model2_path=self.opponent,
            game=self.game,
            board_size=self.board_size,
            num_games=self.num_games,
            mcts1_sims=mcts_sims,
            mcts2_sims=0,
            verbose=False,
        )

        # Extract metrics
        metrics = {
            'win_rate': results['results']['win_rate'],
            'elo_diff': results['results']['elo_difference'],
            'avg_game_time': results['timing']['avg_game_time_s'],
            'total_time': results['timing']['total_time_s'],
        }

        # Calculate score (win rate weighted by time efficiency)
        # Prefer high win rate but penalize slow configurations
        time_penalty = min(1.0, 10.0 / results['timing']['avg_game_time_s'])
        metrics['score'] = metrics['win_rate'] * (0.7 + 0.3 * time_penalty)

        if self.verbose:
            print(f"  Win rate: {metrics['win_rate']:.1%}")
            print(f"  ELO diff: {metrics['elo_diff']:+.0f}")
            print(f"  Avg time: {metrics['avg_game_time']:.2f}s")
            print(f"  Score: {metrics['score']:.3f}")

        return metrics

    def grid_search(self, param_grid: Dict[str, List[Any]]) -> List[Dict]:
        """
        Grid search over hyperparameters.

        Args:
            param_grid: Dictionary mapping parameter names to lists of values

        Returns:
            List of (config, metrics) tuples sorted by score
        """
        print("=" * 80)
        print("GRID SEARCH")
        print("=" * 80)

        # Generate all combinations
        param_names = list(param_grid.keys())
        param_values = [param_grid[name] for name in param_names]
        all_configs = [
            dict(zip(param_names, values))
            for values in itertools.product(*param_values)
        ]

        print(f"\nSearching {len(all_configs)} configurations...")
        print(f"Parameters: {', '.join(param_names)}")
        print(f"Games per config: {self.num_games}")
        print()

        # Evaluate each configuration
        results = []
        for i, config in enumerate(all_configs, 1):
            print(f"[{i}/{len(all_configs)}] Testing: {config}")
            start_time = time.time()

            metrics = self.evaluate_config(config)
            elapsed = time.time() - start_time

            results.append({
                'config': config,
                'metrics': metrics,
                'elapsed_time': elapsed,
            })

            print(f"  → Score: {metrics['score']:.3f} (took {elapsed:.1f}s)")

        # Sort by score
        results.sort(key=lambda x: x['metrics']['score'], reverse=True)

        return results

    def random_search(
        self,
        param_distributions: Dict[str, Dict],
        n_trials: int = 10
    ) -> List[Dict]:
        """
        Random search over hyperparameters.

        Args:
            param_distributions: Dict mapping param names to distribution specs
                Example: {
                    'mcts_sims': {'type': 'choice', 'values': [100, 200, 400]},
                    'c_puct': {'type': 'uniform', 'low': 0.5, 'high': 2.0},
                    'learning_rate': {'type': 'loguniform', 'low': 1e-4, 'high': 1e-2},
                }
            n_trials: Number of random configurations to try

        Returns:
            List of (config, metrics) tuples sorted by score
        """
        print("=" * 80)
        print("RANDOM SEARCH")
        print("=" * 80)

        print(f"\nSearching {n_trials} random configurations...")
        print(f"Parameters: {', '.join(param_distributions.keys())}")
        print()

        results = []
        for trial in range(n_trials):
            # Sample configuration
            config = {}
            for param_name, dist_spec in param_distributions.items():
                dist_type = dist_spec['type']

                if dist_type == 'choice':
                    value = np.random.choice(dist_spec['values'])
                elif dist_type == 'uniform':
                    value = np.random.uniform(dist_spec['low'], dist_spec['high'])
                elif dist_type == 'loguniform':
                    log_low = np.log10(dist_spec['low'])
                    log_high = np.log10(dist_spec['high'])
                    value = 10 ** np.random.uniform(log_low, log_high)
                elif dist_type == 'int_uniform':
                    value = np.random.randint(dist_spec['low'], dist_spec['high'] + 1)
                else:
                    raise ValueError(f"Unknown distribution type: {dist_type}")

                config[param_name] = value

            print(f"[{trial + 1}/{n_trials}] Testing: {config}")
            start_time = time.time()

            metrics = self.evaluate_config(config)
            elapsed = time.time() - start_time

            results.append({
                'config': config,
                'metrics': metrics,
                'elapsed_time': elapsed,
            })

            print(f"  → Score: {metrics['score']:.3f} (took {elapsed:.1f}s)")

        # Sort by score
        results.sort(key=lambda x: x['metrics']['score'], reverse=True)

        return results


def quick_mcts_tuning(
    model_path: str,
    game: str = "go",
    board_size: int = 9,
    num_games: int = 10
) -> Dict:
    """
    Quick MCTS hyperparameter tuning preset.

    Tests common MCTS simulation counts to find optimal setting.

    Args:
        model_path: Path to model
        game: Game type
        board_size: Board size for Go
        num_games: Games per configuration

    Returns:
        Best configuration dict
    """
    print("=" * 80)
    print("QUICK MCTS TUNING")
    print("=" * 80)

    tuner = HyperparameterTuner(
        model_path=model_path,
        game=game,
        board_size=board_size,
        num_games=num_games,
        opponent="random",
        verbose=True
    )

    # Test common simulation counts
    param_grid = {
        'mcts_sims': [0, 50, 100, 200, 400, 800],
        'c_puct': [1.0],  # Keep c_puct at default
    }

    results = tuner.grid_search(param_grid)

    # Print summary
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    print("\nTop 5 configurations:\n")
    for i, result in enumerate(results[:5], 1):
        config = result['config']
        metrics = result['metrics']
        print(f"{i}. MCTS sims: {config['mcts_sims']:4d} | "
              f"Win rate: {metrics['win_rate']:6.1%} | "
              f"ELO: {metrics['elo_diff']:+5.0f} | "
              f"Time: {metrics['avg_game_time']:5.1f}s | "
              f"Score: {metrics['score']:.3f}")

    # Recommendation
    best = results[0]
    print(f"\n🎯 RECOMMENDATION:")
    print(f"   Use {best['config']['mcts_sims']} MCTS simulations")
    print(f"   Expected win rate: {best['metrics']['win_rate']:.1%}")
    print(f"   Expected ELO gain: {best['metrics']['elo_diff']:+.0f}")
    print(f"   Avg game time: {best['metrics']['avg_game_time']:.1f}s")

    return best


def main():
    parser = argparse.ArgumentParser(
        description="Hyperparameter tuning for Prometheus models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Model and game settings
    parser.add_argument('--model', type=str,
                        help='Path to model to tune')
    parser.add_argument('--game', default='go', choices=['go', 'chess'],
                        help='Game type')
    parser.add_argument('--board-size', type=int, default=9,
                        help='Board size for Go')
    parser.add_argument('--num-games', type=int, default=20,
                        help='Games per configuration')
    parser.add_argument('--opponent', default='random',
                        help='Opponent for evaluation (default: random)')

    # Search method
    parser.add_argument('--search', default='grid', choices=['grid', 'random'],
                        help='Search method (default: grid)')
    parser.add_argument('--trials', type=int, default=10,
                        help='Number of trials for random search')

    # Quick presets
    parser.add_argument('--quick-mcts', action='store_true',
                        help='Quick MCTS tuning preset')

    # Parameters (can specify multiple)
    parser.add_argument('--param', action='append', nargs='+',
                        help='Parameter specification (see examples)')

    # Output
    parser.add_argument('--output', type=str,
                        help='Output path for results JSON')
    parser.add_argument('--verbose', action='store_true',
                        help='Verbose output')

    args = parser.parse_args()

    # Quick MCTS tuning
    if args.quick_mcts:
        if not args.model:
            print("Error: --model required for --quick-mcts")
            return 1

        best = quick_mcts_tuning(
            model_path=args.model,
            game=args.game,
            board_size=args.board_size,
            num_games=args.num_games
        )

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(best, f, indent=2)
            print(f"\n✓ Results saved to: {args.output}")

        return 0

    # Regular tuning
    if not args.model:
        print("Error: --model required")
        parser.print_help()
        return 1

    if not args.param:
        print("Error: --param required (or use --quick-mcts)")
        parser.print_help()
        return 1

    # Parse parameter specifications
    param_grid = {}
    for param_spec in args.param:
        param_name = param_spec[0]
        if len(param_spec) < 2:
            print(f"Error: Invalid parameter specification for {param_name}")
            return 1

        # Check if it's a list of values
        if all(arg.replace('.', '').replace('-', '').isdigit() for arg in param_spec[1:]):
            values = [float(v) if '.' in v else int(v) for v in param_spec[1:]]
            param_grid[param_name] = values
        else:
            print(f"Error: Invalid values for {param_name}")
            return 1

    # Create tuner
    tuner = HyperparameterTuner(
        model_path=args.model,
        game=args.game,
        board_size=args.board_size,
        num_games=args.num_games,
        opponent=args.opponent,
        verbose=args.verbose
    )

    # Run search
    if args.search == 'grid':
        results = tuner.grid_search(param_grid)
    else:  # random
        # Convert param_grid to distributions
        param_distributions = {}
        for param_name, values in param_grid.items():
            param_distributions[param_name] = {
                'type': 'choice',
                'values': values
            }
        results = tuner.random_search(param_distributions, n_trials=args.trials)

    # Print results
    print("\n" + "=" * 80)
    print("BEST CONFIGURATIONS")
    print("=" * 80)

    for i, result in enumerate(results[:5], 1):
        print(f"\n{i}. Config: {result['config']}")
        print(f"   Score: {result['metrics']['score']:.3f}")
        print(f"   Win rate: {result['metrics']['win_rate']:.1%}")
        print(f"   ELO: {result['metrics']['elo_diff']:+.0f}")

    # Save results
    if args.output:
        output_data = {
            'search_method': args.search,
            'model': args.model,
            'game': args.game,
            'num_games': args.num_games,
            'results': results
        }
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"\n✓ Results saved to: {args.output}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
