#!/usr/bin/env python3
"""
Benchmark Prometheus Models

Comprehensive performance testing for Prometheus agents.

Usage:
    python scripts/benchmark_models.py --model models/go_9x9.h5 --all
    python scripts/benchmark_models.py --model models/chess.h5 --metric inference
    python scripts/benchmark_models.py --model models/go_9x9.h5 --metric mcts --output results.json
"""

import argparse
import sys
import time
import json
from pathlib import Path
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def benchmark_inference(model_path, num_runs=100):
    """Benchmark model inference speed."""
    print("\n" + "=" * 70)
    print("BENCHMARK: Inference Speed")
    print("=" * 70)
    print(f"Model: {model_path}")
    print(f"Runs: {num_runs}")
    print()

    import tensorflow as tf

    # Load model
    print("Loading model...")
    model = tf.keras.models.load_model(model_path)
    print(f"Parameters: {model.count_params():,}")

    # Determine input shape from model
    input_shape = model.input_shape
    print(f"Input shape: {input_shape}")

    # Generate dummy input
    if isinstance(input_shape, list):
        input_shape = input_shape[0]  # Take first input

    batch_size = 1
    dummy_input = np.random.rand(batch_size, *input_shape[1:]).astype(np.float32)

    # Warm up
    print("Warming up...")
    for _ in range(10):
        _ = model(dummy_input, training=False)

    # Benchmark
    print("Benchmarking...")
    times = []
    for i in range(num_runs):
        start = time.time()
        _ = model(dummy_input, training=False)
        elapsed = time.time() - start
        times.append(elapsed * 1000)  # Convert to ms

        if (i + 1) % 20 == 0:
            print(f"  Progress: {i+1}/{num_runs}", end='\r')

    print(f"  Progress: {num_runs}/{num_runs}")

    # Statistics
    times = np.array(times)
    results = {
        'mean_ms': float(np.mean(times)),
        'std_ms': float(np.std(times)),
        'min_ms': float(np.min(times)),
        'max_ms': float(np.max(times)),
        'p50_ms': float(np.percentile(times, 50)),
        'p95_ms': float(np.percentile(times, 95)),
        'p99_ms': float(np.percentile(times, 99)),
        'inferences_per_second': float(1000 / np.mean(times)),
    }

    print(f"\nResults:")
    print(f"  Mean: {results['mean_ms']:.2f}ms ± {results['std_ms']:.2f}ms")
    print(f"  p50: {results['p50_ms']:.2f}ms")
    print(f"  p95: {results['p95_ms']:.2f}ms")
    print(f"  p99: {results['p99_ms']:.2f}ms")
    print(f"  Throughput: {results['inferences_per_second']:.1f} inferences/sec")

    return results


def benchmark_mcts(model_path, simulation_counts=[100, 400, 800], num_games=10):
    """Benchmark MCTS performance."""
    print("\n" + "=" * 70)
    print("BENCHMARK: MCTS Performance")
    print("=" * 70)
    print(f"Model: {model_path}")
    print(f"Simulation counts: {simulation_counts}")
    print(f"Games per config: {num_games}")
    print()

    # Determine game type from model path
    if 'go' in str(model_path).lower():
        game_type = 'go'
        board_size = 9 if '9x9' in str(model_path) else 19
    elif 'chess' in str(model_path).lower():
        game_type = 'chess'
        board_size = None
    else:
        print("⚠️  Cannot determine game type from model path")
        return {}

    results = {}

    for sim_count in simulation_counts:
        print(f"\nTesting {sim_count} simulations...")

        if game_type == 'go':
            from prometheus.models.go_models import PrometheusGoAgent, RandomGoAgent
            from prometheus.environments.go import GoEnvironment
            from prometheus.evaluation.benchmark import GoEvaluator
            from prometheus.mcts import add_mcts
            import tensorflow as tf

            # Load model
            agent = PrometheusGoAgent(board_size=board_size)
            agent.model = tf.keras.models.load_model(model_path)

            # Add MCTS
            agent = add_mcts(agent, num_simulations=sim_count)

            # Evaluate
            evaluator = GoEvaluator(board_size=board_size)
            env = GoEnvironment(board_size=board_size)
            baseline = RandomGoAgent(board_size=board_size)

            start_time = time.time()
            result = evaluator.evaluate_matchup(
                agent,
                baseline,
                env,
                num_games=num_games,
                verbose=False
            )
            elapsed = time.time() - start_time

        elif game_type == 'chess':
            from prometheus.models.chess_models import PrometheusChessAgent, RandomChessAgent
            from prometheus.environments.chess_env import ChessEnvironment
            from prometheus.evaluation.chess_evaluator import ChessEvaluator
            from prometheus.mcts import add_mcts
            import tensorflow as tf

            # Load model
            agent = PrometheusChessAgent()
            agent.model = tf.keras.models.load_model(model_path)

            # Add MCTS
            agent = add_mcts(agent, num_simulations=sim_count)

            # Evaluate
            evaluator = ChessEvaluator()
            env = ChessEnvironment()
            baseline = RandomChessAgent()

            start_time = time.time()
            result = evaluator.evaluate_matchup(
                agent,
                baseline,
                env,
                num_games=num_games,
                verbose=False
            )
            elapsed = time.time() - start_time

        # Store results
        results[f'{sim_count}_sims'] = {
            'simulations': sim_count,
            'win_rate': result['agent1_win_rate'],
            'elo': result['agent1_elo'],
            'total_time_seconds': elapsed,
            'time_per_game_seconds': elapsed / num_games,
        }

        print(f"  Win rate: {result['agent1_win_rate']:.1%}")
        print(f"  ELO: {result['agent1_elo']:.0f}")
        print(f"  Time/game: {elapsed/num_games:.1f}s")

    # Print summary
    print(f"\nMCTS Performance Summary:")
    print(f"{'Sims':<10} {'Win Rate':<12} {'ELO':<10} {'Time/Game':<12}")
    print("-" * 44)
    for key, data in results.items():
        print(f"{data['simulations']:<10} {data['win_rate']:<12.1%} "
              f"{data['elo']:<10.0f} {data['time_per_game_seconds']:<12.1f}s")

    return results


def benchmark_memory(model_path):
    """Benchmark memory usage."""
    print("\n" + "=" * 70)
    print("BENCHMARK: Memory Usage")
    print("=" * 70)
    print(f"Model: {model_path}")
    print()

    import tensorflow as tf
    import psutil
    import os

    # Get process
    process = psutil.Process(os.getpid())

    # Memory before loading
    mem_before = process.memory_info().rss / 1024 / 1024  # MB

    # Load model
    print("Loading model...")
    model = tf.keras.models.load_model(model_path)

    # Memory after loading
    mem_after = process.memory_info().rss / 1024 / 1024  # MB

    # Model size
    model_file_size = Path(model_path).stat().st_size / 1024 / 1024  # MB

    # Get model memory
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir) / 'temp_model'
        model.save(temp_path)
        saved_size = sum(f.stat().st_size for f in Path(tmpdir).rglob('*') if f.is_file()) / 1024 / 1024

    results = {
        'model_file_size_mb': float(model_file_size),
        'memory_before_mb': float(mem_before),
        'memory_after_mb': float(mem_after),
        'memory_delta_mb': float(mem_after - mem_before),
        'parameters': int(model.count_params()),
        'saved_model_size_mb': float(saved_size),
    }

    print(f"\nResults:")
    print(f"  Model file size: {results['model_file_size_mb']:.2f} MB")
    print(f"  Parameters: {results['parameters']:,}")
    print(f"  Memory before: {results['memory_before_mb']:.2f} MB")
    print(f"  Memory after: {results['memory_after_mb']:.2f} MB")
    print(f"  Memory delta: {results['memory_delta_mb']:.2f} MB")

    return results


def main():
    parser = argparse.ArgumentParser(description='Benchmark Prometheus models')
    parser.add_argument('--model', required=True,
                       help='Path to model file (.h5)')
    parser.add_argument('--metric', nargs='+',
                       choices=['inference', 'mcts', 'memory', 'all'],
                       default=['all'],
                       help='Metrics to benchmark')
    parser.add_argument('--num-runs', type=int, default=100,
                       help='Number of inference benchmark runs')
    parser.add_argument('--mcts-sims', nargs='+', type=int,
                       default=[100, 400, 800],
                       help='MCTS simulation counts to test')
    parser.add_argument('--mcts-games', type=int, default=10,
                       help='Games per MCTS configuration')
    parser.add_argument('--output', type=str,
                       help='Save results to JSON file')

    args = parser.parse_args()

    # Check model exists
    if not Path(args.model).exists():
        print(f"❌ Model not found: {args.model}")
        sys.exit(1)

    results = {
        'model_path': str(args.model),
        'timestamp': time.time(),
    }

    try:
        # Run benchmarks
        metrics = args.metric
        if 'all' in metrics:
            metrics = ['inference', 'mcts', 'memory']

        if 'inference' in metrics:
            results['inference'] = benchmark_inference(args.model, args.num_runs)

        if 'mcts' in metrics:
            results['mcts'] = benchmark_mcts(args.model, args.mcts_sims, args.mcts_games)

        if 'memory' in metrics:
            results['memory'] = benchmark_memory(args.model)

        # Save results
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n✓ Results saved: {output_path}")

        print("\n" + "=" * 70)
        print("✓ BENCHMARKING COMPLETE")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
