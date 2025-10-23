#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test v0.96 Phase 1 Operations on Subset of Tasks

Quick test of 10 Phase 1 operations on 10 tasks (5 size change + 5 color filtering)
to validate improvements before full benchmark.

Expected: At least 2-3 new tasks solved compared to v0.95 baseline.

Author: Prometheus Option E Phase 1
Date: 2025-10-23
"""

import json
import time
import numpy as np
from pathlib import Path
from arc_program_synthesizer import ProgramSynthesizer
from arc_parametric_operations import build_operation_map, PARAMETRIC_OPERATIONS


def load_task(task_id: str, split='evaluation') -> dict:
    """Load task data."""
    task_file = f'arc_agi_2/data/{split}/{task_id}.json'
    with open(task_file, 'r') as f:
        return json.load(f)


def test_phase1_operations():
    """
    Test Phase 1 operations on subset of tasks.

    Tests 10 tasks:
    - 5 size change tasks
    - 5 color filtering tasks
    """
    print("=" * 80)
    print("🧪 Testing v0.96 Phase 1 Operations")
    print("=" * 80)
    print()
    print(f"Operations available: {len(PARAMETRIC_OPERATIONS)}")
    print()

    # Test tasks (from failed task analysis)
    test_tasks = {
        'size_change': [
            '0934a4d8',  # Size + color filtering
            '269e22fb',  # Size change
            '2d0172a1',  # Size change
            '38007db0',  # Size change
            '3a25b0d8'   # Size change
        ],
        'color_filtering': [
            '446ef5d2',  # Color filtering only
            '5545f144',  # Color + size
            '58490d8a',  # Color + size
            '5961cc34',  # Color + symmetry
            '5dbc8537'   # Color + size
        ]
    }

    all_tasks = test_tasks['size_change'] + test_tasks['color_filtering']

    print(f"Testing {len(all_tasks)} tasks:")
    print(f"  - 5 size change tasks")
    print(f"  - 5 color filtering tasks")
    print()

    # Initialize synthesizer
    synthesizer = ProgramSynthesizer(
        beam_width=50,
        max_depth=5,
        max_candidates_per_op=3
    )

    results = []
    solved_count = 0
    start_time = time.time()

    for i, task_id in enumerate(all_tasks, 1):
        task_start = time.time()

        # Load task
        task_data = load_task(task_id)
        task = {'train': task_data['train']}

        # Determine task type
        if task_id in test_tasks['size_change']:
            task_type = 'size'
        else:
            task_type = 'color'

        print(f"[{i}/{len(all_tasks)}] {task_id} ({task_type})")

        # Synthesize program
        program = synthesizer.synthesize(task, constraints={}, biased_operations=None)

        # Evaluate to get fitness
        fitness = synthesizer._evaluate(program, task['train'])

        task_time = time.time() - task_start

        # Check if solved
        solved = fitness >= 0.95
        if solved:
            solved_count += 1
            status = "✓ SOLVED"
        elif fitness >= 0.80:
            status = "↑ HIGH"
        elif fitness >= 0.50:
            status = "~ MED"
        else:
            status = "✗ LOW"

        print(f"  {status}: {fitness:.3f} in {task_time:.1f}s")
        print(f"  Program: {program.to_pattern()}")
        print()

        results.append({
            'task_id': task_id,
            'task_type': task_type,
            'fitness': float(fitness),
            'solved': bool(solved),
            'time': float(task_time),
            'program': program.to_pattern()
        })

    total_time = time.time() - start_time

    print("=" * 80)
    print("📊 RESULTS")
    print("=" * 80)
    print(f"Solved: {solved_count}/{len(all_tasks)} ({solved_count/len(all_tasks)*100:.1f}%)")
    print(f"Average fitness: {np.mean([r['fitness'] for r in results]):.3f}")
    print(f"Total time: {total_time:.1f}s ({total_time/len(all_tasks):.1f}s per task)")
    print()

    # Breakdown by type
    size_results = [r for r in results if r['task_type'] == 'size']
    color_results = [r for r in results if r['task_type'] == 'color']

    size_solved = sum(1 for r in size_results if r['solved'])
    color_solved = sum(1 for r in color_results if r['solved'])

    print("By Task Type:")
    print(f"  Size change: {size_solved}/5 solved ({size_solved/5*100:.0f}%), avg fitness: {np.mean([r['fitness'] for r in size_results]):.3f}")
    print(f"  Color filtering: {color_solved}/5 solved ({color_solved/5*100:.0f}%), avg fitness: {np.mean([r['fitness'] for r in color_results]):.3f}")
    print()

    # Detailed results
    print("Detailed Results:")
    print("-" * 80)
    for r in results:
        status_symbol = "✓" if r['solved'] else "↑" if r['fitness'] >= 0.80 else "~" if r['fitness'] >= 0.50 else "✗"
        print(f"{status_symbol} {r['task_id']:12s} ({r['task_type']:5s}): {r['fitness']:.3f}")

    print()

    # Save results
    output_data = {
        'description': 'v0.96 Phase 1 test on 10 tasks',
        'num_operations': len(PARAMETRIC_OPERATIONS),
        'results': results,
        'summary': {
            'solved': solved_count,
            'total': len(all_tasks),
            'solve_rate': solved_count / len(all_tasks),
            'avg_fitness': float(np.mean([r['fitness'] for r in results])),
            'total_time': total_time,
            'size_solved': size_solved,
            'color_solved': color_solved
        }
    }

    with open('v096_phase1_10tasks_results.json', 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"💾 Results saved: v096_phase1_10tasks_results.json")
    print()

    # Assessment
    print("🎯 ASSESSMENT")
    print("-" * 80)
    print(f"v0.95 baseline: ~10% solve rate (5/50 tasks)")
    print(f"v0.96 Phase 1: {solved_count}/{len(all_tasks)} on targeted tasks")
    print()

    if solved_count >= 2:
        print("✅ Promising! Phase 1 operations are helping.")
        print("   Ready to run full 50-task benchmark.")
    else:
        print("⚠️ Limited improvement. May need to:")
        print("   - Adjust parameter candidates")
        print("   - Increase beam width/depth")
        print("   - Debug specific task failures")

    return output_data


if __name__ == '__main__':
    test_phase1_operations()
    print()
    print("=" * 80)
    print("✅ Test complete!")
    print("=" * 80)
