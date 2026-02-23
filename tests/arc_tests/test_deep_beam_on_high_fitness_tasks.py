#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Deep Beam Search on High-Fitness Tasks

Tests the 9 tasks that achieved 0.90-0.95 fitness with standard beam search
to see if deep beam search can push them over 0.95 threshold.

Target: 9 tasks at 0.90-0.95 → at least 4-5 should solve with deep beam

Author: Prometheus Option D
Date: 2025-10-22
"""

import json
import time
import numpy as np
from pathlib import Path
from arc_deep_beam_search import DeepBeamSearch


def load_task(task_id: str) -> dict:
    """Load task data."""
    task_file = f'arc_agi_2/data/evaluation/{task_id}.json'
    with open(task_file, 'r') as f:
        return json.load(f)


def test_deep_beam_on_high_fitness_tasks():
    """
    Test deep beam search on the 9 tasks that scored 0.90-0.95.
    """
    print("=" * 80)
    print("🚀 Testing Deep Beam Search on High-Fitness Tasks")
    print("=" * 80)
    print()

    # The 9 high-fitness tasks from Option C results
    high_fitness_tasks = [
        ('53fb4810', 0.947),
        ('3dc255db', 0.932),
        ('31f7f899', 0.923),
        ('16b78196', 0.908),
        ('62593bfd', 0.908),
        ('28a6681f', 0.907),
        ('1818057f', 0.904),
        ('142ca369', 0.903),
        ('2c181942', 0.900)
    ]

    print(f"Testing {len(high_fitness_tasks)} high-fitness tasks (0.90-0.95)")
    print("Target: Push at least 4-5 tasks over 0.95 threshold")
    print()

    # Initialize deep beam search
    searcher = DeepBeamSearch(
        beam_width=100,   # Doubled from standard
        max_depth=10,      # Doubled from standard
        max_candidates_per_op=3
    )

    results = []
    solved_count = 0
    start_time = time.time()

    for i, (task_id, prev_fitness) in enumerate(high_fitness_tasks, 1):
        task_start = time.time()

        # Load task
        task_data = load_task(task_id)
        train_examples = task_data['train']

        # Prepare task dict
        task = {'train': train_examples}

        print(f"[{i}/9] {task_id} (prev: {prev_fitness:.3f})")

        # Run deep beam search
        program, fitness = searcher.synthesize(task, constraints={}, biased_operations=None)

        task_time = time.time() - task_start

        # Check if solved
        solved = fitness >= 0.95
        if solved:
            solved_count += 1
            status = "✓ SOLVED"
        elif fitness > prev_fitness:
            status = "↑ IMPROVED"
        else:
            status = "✗"

        improvement = fitness - prev_fitness

        print(f"  {status}: {fitness:.3f} (Δ{improvement:+.3f}) in {task_time:.1f}s")
        print(f"  Program: {program.to_pattern()}")
        print()

        results.append({
            'task_id': task_id,
            'prev_fitness': float(prev_fitness),
            'new_fitness': float(fitness),
            'improvement': float(improvement),
            'solved': bool(solved),
            'time': float(task_time),
            'program': program.to_pattern()
        })

    total_time = time.time() - start_time

    print("=" * 80)
    print("📊 RESULTS")
    print("=" * 80)
    print(f"Solved: {solved_count}/9 ({solved_count/9*100:.1f}%)")
    print(f"Average improvement: {np.mean([r['improvement'] for r in results]):.3f}")
    print(f"Total time: {total_time:.1f}s ({total_time/9:.1f}s per task)")
    print()

    # Detailed breakdown
    print("Detailed Results:")
    print("-" * 80)
    for r in results:
        status_symbol = "✓" if r['solved'] else "↑" if r['improvement'] > 0 else "✗"
        print(f"{status_symbol} {r['task_id']}: {r['prev_fitness']:.3f} → {r['new_fitness']:.3f} (Δ{r['improvement']:+.3f})")

    print()

    # Save results
    output_data = {
        'description': 'Deep beam search on 9 high-fitness tasks',
        'results': results,
        'summary': {
            'solved': solved_count,
            'total': len(high_fitness_tasks),
            'solve_rate': solved_count / len(high_fitness_tasks),
            'avg_improvement': float(np.mean([r['improvement'] for r in results])),
            'total_time': total_time
        }
    }

    with open('deep_beam_high_fitness_results.json', 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"💾 Results saved: deep_beam_high_fitness_results.json")
    print()

    # Assessment
    print("🎯 TARGET ASSESSMENT")
    print("-" * 80)
    print(f"Target: 4-5 tasks solved")
    print(f"Achieved: {solved_count} tasks solved")
    if solved_count >= 4:
        print("✅ TARGET MET!")
    else:
        print(f"{'🟨 Close' if solved_count >= 2 else '❌ Below target'}")

    return output_data


if __name__ == '__main__':
    test_deep_beam_on_high_fitness_tasks()
    print()
    print("=" * 80)
    print("🎉 Test complete!")
    print("=" * 80)
