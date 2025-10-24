#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Different Complexity Penalty Values (Step C)

Purpose: Find optimal complexity penalty by testing on near-solved tasks.
Target: 8 tasks with fitness 0.90-0.95 from Step B analysis.

Penalty values to test:
- 0.005 (current v0.96c)
- 0.003 (medium reduction)
- 0.001 (minimal penalty)
- 0.000 (no penalty)
"""

import json
import time
from pathlib import Path
from arc_program_synthesizer import ProgramSynthesizer
import tempfile
import shutil


# Near-solved tasks from Step B analysis
NEAR_SOLVED_TASKS = [
    '16b78196',  # 0.909 - remove_color
    '28a6681f',  # 0.902 - map_color
    '2c181942',  # 0.901 - symmetrize
    '31f7f899',  # 0.918 - flip
    '3dc255db',  # 0.927 - map_color
    '4c416de3',  # 0.945 - map_color
    '53fb4810',  # 0.942 - map_color
    '62593bfd',  # 0.915 - remove_color
]


def modify_synthesizer_penalty(penalty_value):
    """Temporarily modify the complexity penalty in arc_program_synthesizer.py."""
    synthesizer_file = Path('arc_program_synthesizer.py')

    # Read current content
    with open(synthesizer_file, 'r') as f:
        content = f.read()

    # Find and replace the complexity penalty line
    import re

    # Pattern: complexity_penalty = X.XXX * len(program)
    pattern = r'complexity_penalty = 0\.\d+ \* len\(program\)'
    replacement = f'complexity_penalty = {penalty_value:.3f} * len(program)'

    new_content = re.sub(pattern, replacement, content)

    return content, new_content


def test_penalty_value(penalty, tasks):
    """Test a specific penalty value on the task set."""

    print(f"\n{'='*80}")
    print(f"Testing Penalty = {penalty:.3f}")
    print(f"{'='*80}\n")

    # Temporarily modify the penalty
    synthesizer_file = Path('arc_program_synthesizer.py')
    original_content, modified_content = modify_synthesizer_penalty(penalty)

    # Backup original
    backup_file = synthesizer_file.with_suffix('.py.backup')
    shutil.copy(synthesizer_file, backup_file)

    try:
        # Write modified version
        with open(synthesizer_file, 'w') as f:
            f.write(modified_content)

        # Re-import to get updated penalty
        import importlib
        import arc_program_synthesizer
        importlib.reload(arc_program_synthesizer)
        from arc_program_synthesizer import ProgramSynthesizer as PS

        # Initialize synthesizer
        synth = PS(
            beam_width=50,
            max_depth=5,
            max_candidates_per_op=3
        )

        results = []
        solved_count = 0

        for i, task_id in enumerate(tasks):
            print(f"[{i+1}/{len(tasks)}] Testing {task_id}...")

            # Load task
            task_file = Path(f'arc_agi_2/data/evaluation/{task_id}.json')
            with open(task_file, 'r') as f:
                task_data = json.load(f)

            task = {'train': task_data['train']}

            # Synthesize
            start = time.time()
            program = synth.synthesize(task, constraints={}, biased_operations=None)
            elapsed = time.time() - start

            # Evaluate
            fitness = synth._evaluate(program, task['train'])
            solved = fitness >= 0.95

            if solved:
                solved_count += 1
                print(f"  ✅ SOLVED! Fitness: {fitness:.6f}")
            else:
                print(f"  Fitness: {fitness:.6f}")

            print(f"  Program: {program.to_pattern()}")
            print(f"  Time: {elapsed:.1f}s")
            print()

            results.append({
                'task_id': task_id,
                'penalty': penalty,
                'fitness': float(fitness),
                'solved': bool(solved),
                'program': program.to_pattern(),
                'time': float(elapsed)
            })

        print(f"Penalty {penalty:.3f}: Solved {solved_count}/{len(tasks)} tasks")

        return results, solved_count

    finally:
        # Restore original file
        shutil.copy(backup_file, synthesizer_file)
        backup_file.unlink()

        # Reload original
        import importlib
        import arc_program_synthesizer
        importlib.reload(arc_program_synthesizer)


def run_penalty_sweep():
    """Run full penalty sweep experiment."""

    print("="*80)
    print("🧪 Complexity Penalty Sweep (Step C)")
    print("="*80)
    print()
    print(f"Testing {len(NEAR_SOLVED_TASKS)} near-solved tasks (fitness 0.90-0.95)")
    print()
    print("Penalty values:")
    print("  - 0.005 (current v0.96c baseline)")
    print("  - 0.003 (moderate reduction)")
    print("  - 0.001 (minimal penalty)")
    print("  - 0.000 (no penalty)")
    print()

    penalties = [0.005, 0.003, 0.001, 0.000]
    all_results = []

    summary = {}

    for penalty in penalties:
        results, solved_count = test_penalty_value(penalty, NEAR_SOLVED_TASKS)
        all_results.extend(results)
        summary[penalty] = {
            'solved': solved_count,
            'solve_rate': solved_count / len(NEAR_SOLVED_TASKS)
        }

    # Summary
    print("\n" + "="*80)
    print("📊 PENALTY SWEEP RESULTS")
    print("="*80)
    print()

    print(f"{'Penalty':<15} {'Solved':<15} {'Rate':<15} {'vs v0.96c':<20}")
    print("-"*80)

    baseline_solved = summary[0.005]['solved']

    for penalty in penalties:
        solved = summary[penalty]['solved']
        rate = summary[penalty]['solve_rate']

        if penalty == 0.005:
            comparison = "(baseline)"
        else:
            delta = solved - baseline_solved
            if delta > 0:
                comparison = f"+{delta} tasks ✅"
            elif delta < 0:
                comparison = f"{delta} tasks ⚠️"
            else:
                comparison = "no change"

        print(f"{penalty:<15.3f} {f'{solved}/{len(NEAR_SOLVED_TASKS)}':<15} {f'{rate*100:.1f}%':<15} {comparison:<20}")

    print()

    # Best penalty
    best_penalty = max(summary.keys(), key=lambda p: summary[p]['solved'])
    best_solved = summary[best_penalty]['solved']

    print("🎯 RECOMMENDATION")
    print("-"*80)

    if best_penalty == 0.005:
        print(f"✅ Current penalty (0.005) is optimal.")
        print(f"   Solved {best_solved}/{len(NEAR_SOLVED_TASKS)} near-solved tasks.")
        print(f"   No further penalty reduction recommended.")
    else:
        print(f"✅ Best penalty: {best_penalty:.3f}")
        print(f"   Solved {best_solved}/{len(NEAR_SOLVED_TASKS)} near-solved tasks")
        print(f"   (+{best_solved - baseline_solved} vs current penalty)")
        print()
        print(f"💡 NEXT STEP: Update arc_program_synthesizer.py")
        print(f"   Change: complexity_penalty = 0.005 * len(program)")
        print(f"   To:     complexity_penalty = {best_penalty:.3f} * len(program)")
        print()
        print(f"   Expected impact on full 50-task eval:")
        print(f"   - Current: 5/50 (10.0%)")
        print(f"   - Projected: {5 + (best_solved - baseline_solved)}/50 ({(5 + best_solved - baseline_solved)/50*100:.1f}%)")

    print()

    # Task-level details
    print("="*80)
    print("📋 TASK-LEVEL RESULTS")
    print("="*80)
    print()

    # Group by task
    task_results = {}
    for r in all_results:
        task_id = r['task_id']
        if task_id not in task_results:
            task_results[task_id] = []
        task_results[task_id].append(r)

    for task_id in NEAR_SOLVED_TASKS:
        print(f"Task {task_id}:")
        task_data = task_results[task_id]

        for r in sorted(task_data, key=lambda x: x['penalty']):
            status = "✅" if r['solved'] else "  "
            print(f"  {status} penalty={r['penalty']:.3f}: fitness={r['fitness']:.6f} - {r['program'][0] if r['program'] else 'none'}")

        # Check if penalty helped
        fitnesses = {r['penalty']: r['fitness'] for r in task_data}
        if fitnesses[0.000] > fitnesses[0.005]:
            improvement = fitnesses[0.000] - fitnesses[0.005]
            print(f"     → Removing penalty improves fitness by {improvement:.6f}")

        print()

    # Save results
    output = {
        'penalty_values': penalties,
        'summary': {
            str(p): {
                'solved': summary[p]['solved'],
                'solve_rate': summary[p]['solve_rate']
            }
            for p in penalties
        },
        'best_penalty': best_penalty,
        'best_solved': best_solved,
        'baseline_solved': baseline_solved,
        'all_results': all_results
    }

    with open('penalty_sweep_results.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("="*80)
    print("💾 Results saved: penalty_sweep_results.json")
    print("="*80)

    return output


if __name__ == '__main__':
    run_penalty_sweep()
    print("\n✅ Penalty sweep complete!")
