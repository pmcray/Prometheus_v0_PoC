#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Full 50-task benchmark for v0.96c (Option I: Reduced Complexity Penalty)

Expected: Restore baseline (5/50) or better, possibly 6-7/50 if Phase 1 ops help.
"""

import json
import time
from pathlib import Path
from arc_program_synthesizer import ProgramSynthesizer


def run_full_benchmark():
    """Run full 50-task benchmark with v0.96c."""

    print("=" * 80)
    print("🧪 v0.96c Full Benchmark (50 Evaluation Tasks)")
    print("=" * 80)
    print()
    print("Configuration:")
    print("  - 19 operations (15 base + 4 Phase 1)")
    print("  - Complexity penalty: 0.005 (reduced from 0.01)")
    print("  - Beam width: 50")
    print("  - Max depth: 5")
    print()
    print("Expected: 5-7/50 tasks solved (10-14%)")
    print()

    # Load evaluation tasks
    eval_dir = Path('arc_agi_2/data/evaluation')
    task_files = sorted(eval_dir.glob('*.json'))[:50]  # First 50 tasks

    print(f"Found {len(task_files)} tasks")
    print()

    # Initialize synthesizer
    synth = ProgramSynthesizer(
        beam_width=50,
        max_depth=5,
        max_candidates_per_op=3
    )

    results = []
    solved_count = 0
    total_time = 0

    for i, task_file in enumerate(task_files):
        task_id = task_file.stem
        print(f"[{i+1}/{len(task_files)}] Testing {task_id}...")

        # Load task
        with open(task_file, 'r') as f:
            task_data = json.load(f)

        task = {'train': task_data['train']}

        # Synthesize
        start = time.time()
        try:
            program = synth.synthesize(task, constraints={}, biased_operations=None)
            fitness = synth._evaluate(program, task['train'])
            elapsed = time.time() - start
            solved = fitness >= 0.95

            if solved:
                solved_count += 1
                print(f"  ✅ SOLVED! Fitness: {fitness:.3f}, Program: {program.to_pattern()}")
            else:
                print(f"  Fitness: {fitness:.3f}")

            results.append({
                'task_id': task_id,
                'fitness': float(fitness),
                'solved': bool(solved),
                'program': program.to_pattern(),
                'time': float(elapsed)
            })

        except Exception as e:
            elapsed = time.time() - start
            print(f"  ❌ ERROR: {str(e)[:100]}")
            results.append({
                'task_id': task_id,
                'fitness': 0.0,
                'solved': False,
                'program': [],
                'time': float(elapsed),
                'error': str(e)
            })

        total_time += elapsed
        print(f"  Time: {elapsed:.1f}s, Total solved: {solved_count}/{i+1}")
        print()

    # Summary
    print("=" * 80)
    print("📊 FINAL RESULTS")
    print("=" * 80)
    print()
    print(f"Tasks solved: {solved_count}/{len(task_files)} ({100*solved_count/len(task_files):.1f}%)")
    print(f"Average time per task: {total_time/len(task_files):.1f}s")
    print(f"Total time: {total_time/60:.1f} minutes")
    print()

    # Comparison with baselines
    print("Comparison with Previous Versions:")
    print("-" * 80)
    print(f"{'Version':<15} {'Tasks Solved':<15} {'Solve Rate':<15} {'Note':<30}")
    print("-" * 80)
    print(f"{'v0.95':<15} {'5/50':<15} {'10.0%':<15} {'Baseline (15 ops)':<30}")
    print(f"{'v0.96':<15} {'4/50':<15} {'8.0%':<15} {'Regression (25 ops)':<30}")
    print(f"{'v0.96a':<15} {'4/50':<15} {'8.0%':<15} {'Cleanup (21 ops)':<30}")
    print(f"{'v0.96b':<15} {'4/50':<15} {'8.0%':<15} {'Remove tying ops (19 ops)':<30}")
    print(f"{'v0.96c':<15} {f'{solved_count}/50':<15} {f'{100*solved_count/len(task_files):.1f}%':<15} {'Option I (penalty=0.005)':<30}")
    print()

    # Assessment
    print("🎯 ASSESSMENT")
    print("-" * 80)
    if solved_count >= 5:
        if solved_count > 5:
            print(f"✅ SUCCESS! Baseline restored AND improved (+{solved_count-5} tasks)")
            print(f"   Option I (complexity penalty reduction) WORKED!")
            print(f"   Phase 1 operations helped solve {solved_count-5} additional tasks.")
        else:
            print("✅ SUCCESS! Baseline restored (5/50)")
            print("   Option I (complexity penalty reduction) WORKED!")
            print("   No additional gains from Phase 1 ops, but no regression.")
    elif solved_count == 4:
        print("⚠️  NEUTRAL. Still at v0.96 level (4/50)")
        print("   Penalty fix helped task 3e6067c3, but lost another task elsewhere.")
        print("   Need to investigate which task was lost.")
    else:
        print(f"❌ REGRESSION. Solved only {solved_count}/50 tasks")
        print(f"   Unexpected - penalty should have helped.")

    print()

    # Save results
    output_file = 'arc_v096c_option_i_50tasks.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"💾 Results saved: {output_file}")
    print()

    # List solved tasks
    if solved_count > 0:
        print("Solved Tasks:")
        print("-" * 80)
        for r in results:
            if r['solved']:
                prog_str = ', '.join(r['program'][:2]) if len(r['program']) > 2 else ', '.join(r['program'])
                print(f"  {r['task_id']}: {r['fitness']:.3f} - {prog_str}")
        print()

    return results


if __name__ == '__main__':
    run_full_benchmark()
    print("=" * 80)
    print("✅ Benchmark complete!")
    print("=" * 80)
