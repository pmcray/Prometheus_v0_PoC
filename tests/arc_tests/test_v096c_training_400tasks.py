#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Full 400-task TRAINING evaluation for v0.96c (Option I: Reduced Complexity Penalty)

Purpose: Measure true baseline performance on training set.
Expected: Higher than 10% (eval is harder than training).
"""

import json
import time
from pathlib import Path
from arc_program_synthesizer import ProgramSynthesizer


def run_training_benchmark():
    """Run full 400-task benchmark on TRAINING set with v0.96c."""

    print("=" * 80)
    print("🧪 v0.96c Full TRAINING Benchmark (400 Tasks)")
    print("=" * 80)
    print()
    print("Configuration:")
    print("  - 19 operations (15 base + 4 Phase 1)")
    print("  - Complexity penalty: 0.005 (reduced from 0.01)")
    print("  - Beam width: 50")
    print("  - Max depth: 5")
    print()
    print("Purpose: Measure true performance on training set")
    print("Expected: 15-25% (training easier than evaluation)")
    print()

    # Load training tasks
    train_dir = Path('arc_agi_2/data/training')
    task_files = sorted(train_dir.glob('*.json'))  # All 400 tasks

    print(f"Found {len(task_files)} training tasks")
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
        print(f"  Time: {elapsed:.1f}s, Total solved: {solved_count}/{i+1} ({100*solved_count/(i+1):.1f}%)")

        # Save progress every 50 tasks
        if (i + 1) % 50 == 0:
            temp_output = f'arc_v096c_training_400tasks_progress_{i+1}.json'
            with open(temp_output, 'w') as f:
                json.dump({
                    'tasks_completed': i + 1,
                    'tasks_solved': solved_count,
                    'solve_rate': solved_count / (i + 1),
                    'results': results
                }, f, indent=2)
            print(f"  💾 Progress saved: {temp_output}")

        print()

    # Summary
    print("=" * 80)
    print("📊 FINAL RESULTS - TRAINING SET")
    print("=" * 80)
    print()
    print(f"Tasks solved: {solved_count}/{len(task_files)} ({100*solved_count/len(task_files):.1f}%)")
    print(f"Average time per task: {total_time/len(task_files):.1f}s")
    print(f"Total time: {total_time/60:.1f} minutes ({total_time/3600:.1f} hours)")
    print()

    # Comparison
    print("Comparison with Previous Results:")
    print("-" * 80)
    print(f"{'Dataset':<20} {'Version':<15} {'Solve Rate':<15} {'Note':<30}")
    print("-" * 80)
    print(f"{'Evaluation (50)':<20} {'v0.95':<15} {'10.0% (5/50)':<15} {'Baseline':<30}")
    print(f"{'Evaluation (50)':<20} {'v0.96c':<15} {'10.0% (5/50)':<15} {'Option I (restored)':<30}")
    print(f"{'Training (400)':<20} {'v0.96c':<15} {f'{100*solved_count/len(task_files):.1f}% ({solved_count}/400)':<15} {'Current run':<30}")
    print()

    # Assessment
    print("🎯 ASSESSMENT")
    print("-" * 80)
    solve_rate = solved_count / len(task_files)
    if solve_rate >= 0.25:
        print(f"✅ EXCELLENT! {solve_rate*100:.1f}% solve rate on training set")
        print(f"   Training performance significantly higher than eval (10%), as expected.")
    elif solve_rate >= 0.15:
        print(f"✅ GOOD! {solve_rate*100:.1f}% solve rate on training set")
        print(f"   Training performance moderately higher than eval (10%).")
    elif solve_rate >= 0.10:
        print(f"🟨 MODERATE. {solve_rate*100:.1f}% solve rate on training set")
        print(f"   Training performance similar to eval (10%). Expected higher.")
    else:
        print(f"⚠️  CONCERN. Only {solve_rate*100:.1f}% solve rate on training set")
        print(f"   Training should be easier than eval. Investigate.")
    print()

    # Save final results
    output_file = 'arc_v096c_training_400tasks.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"💾 Results saved: {output_file}")
    print()

    # List top 20 solved tasks
    if solved_count > 0:
        solved_tasks = [r for r in results if r['solved']]
        print(f"First 20 Solved Tasks (of {solved_count}):")
        print("-" * 80)
        for r in solved_tasks[:20]:
            prog_str = ', '.join(r['program'][:2]) if len(r['program']) > 2 else ', '.join(r['program'])
            print(f"  {r['task_id']}: {r['fitness']:.3f} - {prog_str}")
        if solved_count > 20:
            print(f"  ... and {solved_count - 20} more")
        print()

    return results


if __name__ == '__main__':
    run_training_benchmark()
    print("=" * 80)
    print("✅ Training benchmark complete!")
    print("=" * 80)
