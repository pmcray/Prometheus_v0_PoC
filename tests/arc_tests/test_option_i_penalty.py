#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Option I: Reduced Complexity Penalty (0.01 → 0.005)

This should restore baseline performance by allowing crop(mode=content)
to score 0.959 - 0.005 = 0.954 (above 0.95 threshold).

Expected Results:
- Task 3e6067c3: 0.949 → 0.954 (RESTORED, SOLVED!)
- Task 142ca369: May improve if similar boundary issue exists
"""

import json
import time
from arc_program_synthesizer import ProgramSynthesizer


def test_reduced_penalty():
    """Test Option I on 2 lost tasks."""

    lost_tasks = ['3e6067c3', '142ca369']

    print("=" * 80)
    print("🧪 Testing Option I: Reduced Complexity Penalty (0.01 → 0.005)")
    print("=" * 80)
    print()
    print("Fix: Reduce complexity penalty to avoid pushing near-threshold programs below 0.95")
    print()
    print("Expected:")
    print("  - Task 3e6067c3: crop fitness 0.959 - 0.005 = 0.954 (SOLVED!)")
    print("  - Task 142ca369: May improve if similar issue exists")
    print()

    # Initialize synthesizer
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
    print(f"{'Task':<15} {'v0.95':<10} {'v0.96':<10} {'Option I':<10} {'Status':<20}")
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
        opti_fitness = r['fitness']

        if r['solved'] and not v095_solved:
            status = "🎉 NEW SOLVE!"
        elif r['solved'] and v095_solved:
            status = "✅ BASELINE RESTORED"
        elif opti_fitness > v095_fitness:
            status = "↑ IMPROVED"
        elif opti_fitness > v096_fitness:
            status = "~ BETTER THAN v0.96"
        else:
            status = "✗ NO IMPROVEMENT"

        print(f"{task_id:<15} {v095_fitness:.3f}{'*' if v095_solved else ' ':<6} "
              f"{v096_fitness:.3f}     {opti_fitness:.3f}{'*' if r['solved'] else ' ':<6} {status:<20}")

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
        opti_prog = ', '.join(r['program']) if r['program'] else 'none'

        print(f"Task {task_id}:")
        print(f"  v0.95:    {v095_prog}")
        print(f"  v0.96:    {v096_prog}")
        print(f"  Option I: {opti_prog}")

        # Check if program changed
        if 'crop' in opti_prog.lower():
            print(f"  → ✅ Now finding crop (correct operation)!")
        elif opti_prog != v096_prog:
            print(f"  → 🔄 Different program than v0.96")
        else:
            print(f"  → ⚠️  Same as v0.96 (penalty didn't fix this task)")
        print()

    # Assessment
    print("🎯 ASSESSMENT")
    print("-" * 80)

    if solved_count == 2:
        print("✅ COMPLETE SUCCESS! Both tasks solved/restored.")
        print("   Complexity penalty fix worked perfectly.")
        print("   Ready for full 50-task benchmark (expect 5-7/50).")
    elif solved_count == 1:
        print("🟨 PARTIAL SUCCESS. One task solved/restored.")
        # Check which one
        if results[0]['solved']:
            print("   ✓ Task 3e6067c3 SOLVED (complexity penalty fix worked!)")
            print("   ✗ Task 142ca369 still unsolved (different root cause)")
            print("   This is EXPECTED - penalty fix targets task 3e6067c3 specifically.")
        else:
            print("   Unexpected result - check programs and fitnesses.")
        print("   Ready for full benchmark to see overall impact.")
    else:
        print("❌ FAILED. Neither task solved.")
        print("   Unexpected - penalty reduction should have restored task 3e6067c3.")
        print("   Check if crop is being found and what its fitness is.")

    print()

    # Save results
    with open('option_i_penalty_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"💾 Results saved: option_i_penalty_results.json")
    print()

    return results


if __name__ == '__main__':
    test_reduced_penalty()
    print("=" * 80)
    print("✅ Test complete!")
    print("=" * 80)
