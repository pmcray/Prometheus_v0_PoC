#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Option G: Tie-breaking by operation preference.

Tests if adding operation priority fixes the regression on 2 lost tasks:
- Task 3e6067c3: Should find crop (0.959) instead of map_color (0.949)
- Task 142ca369: Should find transpose+transpose (0.903) instead of map_color (0.893)

Expected: Both tasks should now restore to v0.95 baseline or better.
"""

import json
import time
from arc_program_synthesizer import ProgramSynthesizer


def test_tiebreaking_fix():
    """Test Option G on 2 lost tasks."""

    lost_tasks = ['3e6067c3', '142ca369']

    print("=" * 80)
    print("🧪 Testing Option G: Tie-Breaking by Operation Preference")
    print("=" * 80)
    print()
    print("Testing on 2 tasks that regressed in v0.96:")
    print("  - 3e6067c3: v0.95 solved (0.959 with crop), v0.96 failed (0.949 with map_color)")
    print("  - 142ca369: v0.95 near (0.903 with transpose×2), v0.96 regressed (0.893 with map_color)")
    print()
    print("Option G Fix: Prefer crop (priority=1) over map_color (priority=10) when fitness ties")
    print()

    # Initialize synthesizer with diversity + tie-breaking
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
    print(f"{'Task':<15} {'v0.95':<10} {'v0.96':<10} {'Option G':<10} {'Status':<20}")
    print("-" * 80)

    baselines = {
        '3e6067c3': (0.959, True, 'crop'),
        '142ca369': (0.903, False, 'transpose×2')
    }

    v096_results = {
        '3e6067c3': (0.949, 'map_color'),
        '142ca369': (0.893, 'map_color')
    }

    for r in results:
        task_id = r['task_id']
        v095_fitness, v095_solved, v095_prog = baselines[task_id]
        v096_fitness, v096_prog = v096_results[task_id]
        optg_fitness = r['fitness']
        optg_prog = r['program'][0] if r['program'] else 'none'

        if r['solved'] and not v095_solved:
            status = "🎉 NEW SOLVE!"
        elif r['solved']:
            status = "✅ RESTORED"
        elif optg_fitness > v095_fitness:
            status = "↑ IMPROVED"
        elif optg_fitness > v096_fitness:
            status = "~ BETTER THAN v0.96"
        elif abs(optg_fitness - v095_fitness) < 0.001:
            status = "✓ BASELINE RESTORED"
        else:
            status = "✗ STILL REGRESSED"

        print(f"{task_id:<15} {v095_fitness:.3f}{'*' if v095_solved else ' ':<6} "
              f"{v096_fitness:.3f}     {optg_fitness:.3f}{'*' if r['solved'] else ' ':<6} {status:<20}")

    print()
    print("Legend: * = solved (≥0.95 fitness)")
    print()

    # Program comparison
    print("Program Comparison:")
    print("-" * 80)
    for r in results:
        task_id = r['task_id']
        _, _, v095_prog = baselines[task_id]
        _, v096_prog = v096_results[task_id]
        optg_prog = ', '.join(r['program']) if r['program'] else 'none'

        print(f"Task {task_id}:")
        print(f"  v0.95:    {v095_prog}")
        print(f"  v0.96:    {v096_prog}")
        print(f"  Option G: {optg_prog}")
        print()

    # Assessment
    print("🎯 ASSESSMENT")
    print("-" * 80)

    if solved_count == 2:
        print("✅ SUCCESS! Both tasks solved/restored.")
        print("   Tie-breaking by operation priority fixes the regression.")
        print("   Ready for full 50-task benchmark.")
    elif solved_count == 1:
        print("🟨 PARTIAL SUCCESS. One task solved/restored.")
        if results[0]['fitness'] >= baselines['3e6067c3'][0] - 0.01:
            print("   Task 3e6067c3 fitness restored - tie-breaking working!")
        print("   May need additional tuning for full fix.")
    else:
        # Check if fitness restored even if not solved
        task1_restored = abs(results[0]['fitness'] - baselines['3e6067c3'][0]) < 0.01
        task2_improved = results[1]['fitness'] > v096_results['142ca369'][0]

        if task1_restored or task2_improved:
            print("🟨 PARTIAL FIX. Fitness improved but not fully solved.")
            print(f"   Task 3e6067c3 baseline restored: {task1_restored}")
            print(f"   Task 142ca369 improved: {task2_improved}")
            if task1_restored:
                print("   ✓ Tie-breaking IS working (crop now preferred over map_color)")
                print("   May need deeper search or more operations for full solve.")
        else:
            print("❌ FAILED. Tie-breaking didn't fix the problem.")
            print("   Need different approach.")

    print()

    # Save results
    with open('option_g_tiebreaking_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"💾 Results saved: option_g_tiebreaking_results.json")
    print()

    return results


if __name__ == '__main__':
    test_tiebreaking_fix()
    print("=" * 80)
    print("✅ Test complete!")
    print("=" * 80)
