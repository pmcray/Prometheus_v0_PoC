#!/usr/bin/env python3
"""
Profile v0.94 meta-learning to find performance bottleneck.
"""

import cProfile
import pstats
import io
import time
from prometheus_arc_v094_metalearning import PrometheusARC_v094_MetaLearning
import json

def profile_single_task():
    """Profile a single task execution."""

    # Initialize solver
    solver = PrometheusARC_v094_MetaLearning(
        database_path='arc_learned_patterns_v094.json'
    )

    # Load a task from evaluation set
    with open('arc_agi_2/data/evaluation/0934a4d8.json', 'r') as f:
        task_data = json.load(f)

    train_examples = task_data['train']
    test_examples = task_data['test']

    print("=" * 60)
    print("PROFILING v0.94 META-LEARNING")
    print("=" * 60)
    print(f"Task: 0934a4d8")
    print(f"Train examples: {len(train_examples)}")
    print(f"Test examples: {len(test_examples)}")
    print()

    # Profile the solve_task method
    profiler = cProfile.Profile()

    start_time = time.time()
    profiler.enable()

    result = solver.solve_task(train_examples, test_examples, '0934a4d8')

    profiler.disable()
    end_time = time.time()

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total time: {end_time - start_time:.2f}s")
    print(f"Fitness: {result['fitness']:.4f}")
    print(f"Pattern: {result['pattern']}")
    print(f"Filter mode: {result.get('filter_mode', 'unknown')}")
    print(f"Filtered primitives: {result.get('filtered_primitives', 'unknown')}")
    print()

    # Print profiling statistics
    print("=" * 60)
    print("TOP 30 TIME-CONSUMING FUNCTIONS")
    print("=" * 60)

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(30)
    print(s.getvalue())

    print()
    print("=" * 60)
    print("FUNCTIONS BY TOTAL TIME (internal time)")
    print("=" * 60)

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('time')
    ps.print_stats(30)
    print(s.getvalue())

if __name__ == '__main__':
    profile_single_task()
