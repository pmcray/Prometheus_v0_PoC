#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test diversity-aware beam search on the 2 lost tasks.

Tests if Option F fixes the greedy local optima problem that caused:
- Task 3e6067c3: 0.959 (v0.95) → 0.949 (v0.96)
- Task 142ca369: 0.903 (v0.95) → 0.893 (v0.96)

Expected: Both tasks should now find better programs (crop, transpose, etc.)
instead of getting stuck on map_color.
"""

import json
import time
from arc_program_synthesizer import ProgramSynthesizer

def test_lost_tasks():
    """Test diversity fix on 2 lost tasks."""

    lost_tasks = ['3e6067c3', '142ca369']

    print("=" * 80)
    print("🧪 Testing Diversity-Aware Beam Search (Option F)")
    print("=" * 80)
    print()
    print("Testing on 2 tasks that regressed in v0.96:")
    print("  - 3e6067c3: v0.95 solved (0.959), v0.96 failed (0.949)")
    print("  - 142ca369: v0.95 near (0.903), v0.96 regressed (0.893)")
    print()

    # Initialize synthesizer with diversity
    synth = ProgramSynthesizer(
        beam_width=50,
        max_depth=5,
        max_candidates_per_op=3
    )

    results = []

    for task_id in lost_tasks:
        print(f"Testing {task_id}...")
        print("-" * 80)

        # Load task
        with open(f'arc_agi_2/data/evaluation/{task_id}.json', 'r') as f:
            task_data = json.load(f)

        task = {'train': task_data['train']}

        # Synthesize
        start = time.time()
        program = synth.synthesize(task, constraints={}, biased_operations=None)
        elapsed = time.time() - start

        # Evaluate
        fitness = synth._evaluate(program, task['train'])

        # Check if solved
        solved = fitness >= 0.95
        status = "✅ SOLVED" if solved else "❌ NOT SOLVED"

        print(f"  {status}")
        print(f"  Fitness: {fitness:.6f}")
        print(f"  Program: {program.to_pattern()}")
        print(f"  Time: {elapsed:.1f}s")
        print()

        results.append({
            'task_id': task_id,
            'fitness': float(fitness),
            'solved': bool(solved),
            'program': program.to_pattern(),
            'time': float(elapsed)
        })

    print("=" * 80)
    print("📊 RESULTS")
    print("=" * 80)
    print()

    solved_count = sum(1 for r in results if r['solved'])
    print(f"Solved: {solved_count}/2")
    print()

    print("Comparison:")
    print("-" * 80)
    print(f"{'Task':<15} {'v0.95':<10} {'v0.96':<10} {'Option F':<10} {'Status':<15}")
    print("-" * 80)

    baselines = {
        '3e6067c3': (0.959, True),
        '142ca369': (0.903, False)
    }

    v096_results = {
        '3e6067c3': 0.949,
        '142ca369': 0.893
    }

    for r in results:
        task_id = r['task_id']
        v095_fitness, v095_solved = baselines[task_id]
        v096_fitness = v096_results[task_id]
        optf_fitness = r['fitness']

        if r['solved'] and not v095_solved:
            status = "🎉 NEW SOLVE!"
        elif r['solved']:
            status = "✅ RESTORED"
        elif optf_fitness > v095_fitness:
            status = "↑ IMPROVED"
        elif optf_fitness > v096_fitness:
            status = "~ BETTER"
        else:
            status = "✗ SAME"

        print(f"{task_id:<15} {v095_fitness:.3f}{'*' if v095_solved else ' ':<6} {v096_fitness:.3f}     {optf_fitness:.3f}{'*' if r['solved'] else ' ':<6} {status:<15}")

    print()
    print("Legend: * = solved (≥0.95 fitness)")
    print()

    # Assessment
    print("🎯 ASSESSMENT")
    print("-" * 80)

    if solved_count == 2:
        print("✅ SUCCESS! Both tasks solved/restored.")
        print("   Diversity-aware beam search fixes the regression.")
        print("   Ready for full 50-task benchmark.")
    elif solved_count == 1:
        print("🟨 PARTIAL SUCCESS. One task solved/restored.")
        print("   Some improvement, but may need tuning.")
    else:
        print("❌ FAILED. Neither task solved.")
        print("   Diversity alone doesn't fix the problem.")
        print("   Need different approach.")

    print()

    # Save results
    with open('diversity_fix_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"💾 Results saved: diversity_fix_test_results.json")
    print()

    return results


if __name__ == '__main__':
    test_lost_tasks()
    print("=" * 80)
    print("✅ Test complete!")
    print("=" * 80)
