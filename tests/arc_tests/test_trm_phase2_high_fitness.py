#!/usr/bin/env python3
"""
Test TRM Phase 2 on 11 high-fitness tasks (90-100% baseline fitness).

These tasks are most likely to be refined from near-perfect to perfect with
TRM's recursive refinement approach.
"""

import json
import sys
import time
from pathlib import Path
from prometheus_arc_recursive_refinement import PrometheusARCRecursiveRefinement

# 11 EXCELLENT candidates (90-100% baseline fitness)
HIGH_FITNESS_TASKS = [
    "0b17323b",  # 96.89%
    "15113be4",  # 96.11%
    "18419cfa",  # 95.82%
    "11e1fe23",  # 94.82%
    "14754a24",  # 94.08%
    "0c786b71",  # 94.00%
    "1acc24af",  # 91.58%
    "1d0a4b61",  # 91.33%
    "09c534e7",  # 91.13%
    "070dd51e",  # 90.67%
    "16b78196",  # 90.44%
]

def main():
    print("=" * 80)
    print("🔬 TRM Phase 2 - High-Fitness Tasks (v0.86)")
    print("=" * 80)
    print(f"Tasks: {len(HIGH_FITNESS_TASKS)}")
    print(f"Baseline fitness: 90-97% (near-perfect)")
    print(f"Target: Refine 2-3 tasks from 90-95% → 100%")
    print(f"Max refinement cycles: 3")
    print(f"Population: 100")
    print(f"Max pattern length: 5")
    print("=" * 80)
    print()

    # Load high-fitness tasks from both training and evaluation directories
    arc_data = {}
    for task_id in HIGH_FITNESS_TASKS:
        # Try training first, then evaluation
        for split in ['training', 'evaluation']:
            task_file = Path(f"arc_agi_2/data/{split}/{task_id}.json")
            if task_file.exists():
                with open(task_file, 'r') as f:
                    arc_data[task_id] = json.load(f)
                break
        else:
            print(f"Warning: Task {task_id} not found in training or evaluation")

    print(f"Loaded {len(arc_data)}/{len(HIGH_FITNESS_TASKS)} high-fitness tasks\n")

    # Initialize solver
    solver = PrometheusARCRecursiveRefinement(
        population_size=100,
        max_pattern_length=5,
        max_refinement_cycles=3,
        correction_generations=50,
        use_fuzzy=True
    )

    # Solve tasks (same structure as main TRM script)
    task_ids = list(arc_data.keys())
    results = []
    solved_count = 0
    start_time = time.time()

    for i, task_id in enumerate(task_ids, 1):
        task = arc_data[task_id]
        train_examples = task['train']
        test_examples = task['test']

        print(f"[{i}/{len(task_ids)}] Task {task_id}")

        try:
            result = solver.solve_task(
                train_examples,
                test_examples,
                task_id,
                max_generations=100
            )

            success = result['fitness'] >= 1.0
            if success:
                solved_count += 1

            result_summary = {
                'task_id': task_id,
                'solved': bool(success),
                'fitness': float(result['fitness']),
                'pattern': result['pattern'],
                'refinement_cycles': int(result['refinement_cycles']),
                'improvements': [
                    {
                        'cycle': int(step.cycle),
                        'fitness_gain': float(step.fitness_after - step.fitness_before),
                        'failures_fixed': int(step.failures_fixed)
                    }
                    for step in result['history']
                ]
            }
            results.append(result_summary)

            status = "✓ SOLVED" if success else f"✗ Failed (fitness: {result['fitness']:.4f})"
            print(f"  {status}")
            print(f"  Pattern: {result['pattern']}")
            print(f"  Refinement cycles: {result['refinement_cycles']}")
            print()

        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({
                'task_id': task_id,
                'solved': False,
                'error': str(e)
            })
            print()

    # Summary
    elapsed = time.time() - start_time

    # Print summary
    print("=" * 80)
    print("📊 RESULTS")
    print("=" * 80)
    print(f"Solved: {solved_count}/{len(task_ids)} ({solved_count/len(task_ids)*100:.2f}%)")
    print(f"Time: {elapsed:.1f}s ({elapsed/len(task_ids):.1f}s per task)")
    print()

    # Refinement statistics
    total_cycles = sum(r.get('refinement_cycles', 0) for r in results)
    total_improvements = sum(len(r.get('improvements', [])) for r in results)
    avg_cycles = total_cycles / len(results) if results else 0

    print("🔄 Refinement Statistics:")
    print(f"  Total cycles run: {total_cycles}")
    print(f"  Successful improvements: {total_improvements}")
    print(f"  Avg cycles per task: {avg_cycles:.1f}")
    print()

    # Save results
    output_file = 'arc_trm_phase2_high_fitness_results.json'
    with open(output_file, 'w') as f:
        json.dump({
            'config': {
                'task_ids': HIGH_FITNESS_TASKS,
                'num_tasks': len(task_ids),
                'generations': 100,
                'max_cycles': 3,
                'population': 100
            },
            'summary': {
                'solved': solved_count,
                'total': len(task_ids),
                'accuracy': solved_count / len(task_ids) if task_ids else 0,
                'time': elapsed,
                'avg_time_per_task': elapsed / len(task_ids) if task_ids else 0
            },
            'results': results
        }, f, indent=2)

    print(f"✅ Results saved to {output_file}")
    print()

    # Detailed analysis
    print("=" * 80)
    print("📊 DETAILED ANALYSIS")
    print("=" * 80)

    # Find tasks that were refined to 100%
    refined_to_perfect = [r for r in results if r.get('solved')]
    improved = [r for r in results if not r.get('solved') and r.get('refinement_cycles', 0) > 0]

    if refined_to_perfect:
        print(f"\n🎯 REFINED TO 100% ({len(refined_to_perfect)} tasks):")
        for task in refined_to_perfect:
            print(f"  {task['task_id']}: "
                  f"fitness={task['fitness']:.2%}, "
                  f"cycles={task['refinement_cycles']}")

    if improved:
        print(f"\n📈 IMPROVED BUT NOT PERFECT ({len(improved)} tasks):")
        for task in improved[:5]:  # Show top 5
            print(f"  {task['task_id']}: "
                  f"fitness={task['fitness']:.2%}, "
                  f"cycles={task['refinement_cycles']}")

    print()

if __name__ == '__main__':
    main()
