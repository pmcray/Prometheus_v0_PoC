#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v0.96 Full 50-Task Evaluation with Phase 1 Operations

Tests v0.96 (25 operations with task-aware parameters) on 50 evaluation tasks.

Expected improvements over v0.95 baseline (5/50 solved):
- Phase 1 operations: 10 new high-priority operations
- Task-aware parameter generation
- Target: 7-9 tasks solved (14-18% solve rate)

Author: Prometheus Option E Phase 1
Date: 2025-10-23
"""

import json
import time
import numpy as np
from pathlib import Path
from arc_program_synthesizer import ProgramSynthesizer
from arc_parametric_operations import PARAMETRIC_OPERATIONS


def load_task(task_id: str, split='evaluation') -> dict:
    """Load task data."""
    task_file = f'arc_agi_2/data/{split}/{task_id}.json'
    with open(task_file, 'r') as f:
        return json.load(f)


def load_evaluation_tasks(n=50):
    """Load first N evaluation task IDs."""
    eval_dir = Path('arc_agi_2/data/evaluation')
    task_files = sorted(eval_dir.glob('*.json'))
    return [f.stem for f in task_files[:n]]


def run_v096_full_evaluation():
    """
    Run v0.96 on 50 evaluation tasks with Phase 1 operations.
    """
    print("=" * 80)
    print("🚀 v0.96 Full Evaluation: 50 Tasks with Phase 1 Operations")
    print("=" * 80)
    print()
    print(f"Operations available: {len(PARAMETRIC_OPERATIONS)}")
    print()

    # Try to load v0.95 baseline for comparison (may not exist)
    v095_baseline = None
    v095_by_task = {}
    try:
        baseline_files = [
            'arc_v095_final_50tasks_evaluation.json',
            'arc_v092_baseline_evaluation_50tasks.json'
        ]
        for baseline_file in baseline_files:
            if Path(baseline_file).exists():
                print(f"📊 Loading baseline from {baseline_file}...")
                with open(baseline_file, 'r') as f:
                    v095_baseline = json.load(f)
                v095_by_task = {r['task_id']: r for r in v095_baseline['results']}
                baseline_solved = v095_baseline['summary']['solved']
                print(f"   Baseline: {baseline_solved} solved")
                print()
                break
    except Exception as e:
        print(f"⚠️  Could not load baseline: {e}")
        print("   Will report results without comparison")
        print()

    # Initialize synthesizer
    print("🔧 Initializing v0.96a synthesizer...")
    synthesizer = ProgramSynthesizer(
        beam_width=100,  # Increased from 50 to compensate for 21 operations
        max_depth=5,
        max_candidates_per_op=3
    )
    print("   ✅ v0.96a initialized (beam_width=100)")
    print()

    # Load task IDs
    task_ids = load_evaluation_tasks(50)
    print(f"📝 Loaded {len(task_ids)} evaluation tasks")
    print()

    # Run evaluation
    print("=" * 80)
    print("🏃 Running Evaluation")
    print("=" * 80)
    print()

    results = []
    start_time = time.time()

    solved_count = 0
    improved_count = 0

    for i, task_id in enumerate(task_ids, 1):
        task_start = time.time()

        # Load task
        task_data = load_task(task_id)
        task = {'train': task_data['train']}

        print(f"[{i:2d}/50] {task_id}...", end=' ', flush=True)

        # Synthesize program
        try:
            program = synthesizer.synthesize(task, constraints={}, biased_operations=None)

            # Evaluate to get fitness
            fitness = synthesizer._evaluate(program, task['train'])

            pattern = program.to_pattern()
        except Exception as e:
            print(f"ERROR: {e}")
            fitness = 0.0
            pattern = []

        task_time = time.time() - task_start

        # Check if solved
        solved = fitness >= 0.95

        # Compare to baseline if available
        baseline_fitness = 0.0
        if task_id in v095_by_task:
            baseline_fitness = v095_by_task[task_id].get('fitness', 0.0)

        improvement = fitness - baseline_fitness

        # Track stats
        if solved:
            solved_count += 1
            if baseline_fitness < 0.95:
                status = "✓ NEW SOLVE"
            else:
                status = "✓ SOLVED"
        elif improvement > 0.1:
            improved_count += 1
            status = f"↑ IMPROVED"
        elif fitness >= 0.80:
            status = "~ HIGH"
        elif fitness >= 0.50:
            status = "~ MED"
        else:
            status = "✗ LOW"

        if v095_by_task:
            print(f"{status}: {fitness:.3f} (baseline: {baseline_fitness:.3f}, Δ{improvement:+.3f}) in {task_time:.1f}s")
        else:
            print(f"{status}: {fitness:.3f} in {task_time:.1f}s")

        # Store result
        results.append({
            'task_id': task_id,
            'fitness': float(fitness),
            'solved': bool(solved),
            'time': float(task_time),
            'program': pattern,
            'baseline_fitness': float(baseline_fitness),
            'improvement': float(improvement)
        })

    total_time = time.time() - start_time

    print()
    print("=" * 80)
    print("📊 FINAL RESULTS")
    print("=" * 80)
    print(f"Solved: {solved_count}/50 ({solved_count/50*100:.1f}%)")
    if v095_baseline:
        print(f"Improved over baseline: {improved_count}/50 ({improved_count/50*100:.1f}%)")
    print(f"Average fitness: {np.mean([r['fitness'] for r in results]):.3f}")
    print(f"Total time: {total_time:.1f}s ({total_time/50:.1f}s per task)")
    print()

    # vs baseline comparison
    if v095_baseline:
        baseline_solved = v095_baseline['summary']['solved']
        baseline_avg = sum(v095_by_task[tid].get('fitness', 0.0) for tid in task_ids) / len(task_ids)
        v096_avg = sum(r['fitness'] for r in results) / len(results)

        print("📈 vs BASELINE COMPARISON")
        print("-" * 80)
        print(f"Solve rate:")
        print(f"  Baseline: {baseline_solved}/50 ({baseline_solved/50*100:.1f}%)")
        print(f"  v0.96:    {solved_count}/50 ({solved_count/50*100:.1f}%)")
        print(f"  Change:   {solved_count - baseline_solved:+d} tasks")
        print()
        print(f"Average fitness:")
        print(f"  Baseline: {baseline_avg:.3f}")
        print(f"  v0.96:    {v096_avg:.3f}")
        print(f"  Change:   {v096_avg - baseline_avg:+.3f}")
        print()

    # Solved tasks
    solved_tasks = [r for r in results if r['solved']]
    if solved_tasks:
        print("✅ SOLVED TASKS")
        print("-" * 80)
        for r in solved_tasks:
            is_new = r['baseline_fitness'] < 0.95
            new_marker = " (NEW!)" if is_new else ""
            print(f"{r['task_id']}: {r['fitness']:.3f}{new_marker}")
            print(f"  Program: {r['program']}")
        print()

    # Close calls
    close_calls = [r for r in results if 0.80 <= r['fitness'] < 0.95]
    if close_calls:
        print("🔍 CLOSE CALLS (0.80-0.95)")
        print("-" * 80)
        for r in close_calls:
            print(f"{r['task_id']}: {r['fitness']:.3f} (gap: {0.95 - r['fitness']:.3f})")
        print()

    # Target assessment
    print("🎯 TARGET ASSESSMENT")
    print("-" * 80)
    print(f"Option E Phase 1 Target: 14-18% solve rate (7-9 tasks)")
    print(f"Achieved: {solved_count/50*100:.1f}% ({solved_count} tasks)")

    if solved_count >= 7:
        print("✅ TARGET MET!")
        print("   Phase 1 operations successfully broke through 10% ceiling")
    elif solved_count >= 5:
        print("🟨 Partial success - some improvement over baseline")
        print("   May need Phase 2 operations or bug fixes")
    else:
        print("❌ Below target - needs investigation")
    print()

    # Save results
    output_data = {
        'version': 'v0.96_phase1',
        'num_operations': len(PARAMETRIC_OPERATIONS),
        'phase1_operations': [
            'expand_to_size', 'compress_to_fit', 'crop_to_content',
            'resize_with_padding', 'fit_to_canvas',
            'isolate_color', 'extract_color', 'filter_by_color',
            'remove_color', 'keep_colors'
        ],
        'results': results,
        'summary': {
            'solved': solved_count,
            'improved': improved_count,
            'avg_fitness': float(np.mean([r['fitness'] for r in results])),
            'total_time': total_time,
            'avg_time_per_task': total_time / 50
        }
    }

    if v095_baseline:
        output_data['comparison'] = {
            'baseline_version': v095_baseline.get('version', 'unknown'),
            'baseline_solved': baseline_solved,
            'baseline_avg_fitness': baseline_avg,
            'improvement_solved': solved_count - baseline_solved,
            'improvement_fitness': v096_avg - baseline_avg
        }

    output_file = 'arc_v096_phase1_50tasks_evaluation.json'
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"💾 Results saved: {output_file}")
    print()

    return output_data


if __name__ == '__main__':
    run_v096_full_evaluation()
    print("=" * 80)
    print("🎉 Evaluation complete!")
    print("=" * 80)
