#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test v0.95 on Top 7 Crop Tasks

Tests parametric program synthesis on the 7 highest-fitness crop tasks
identified in v0.92 benchmark:

1. Task 135a2760: 0.491 with ['crop']
2. Task 409aa875: 0.487 with ['crop']
3. Task 332f06d7: 0.481 with ['crop', 'fill_zeros']
4. Task 3e6067c3: 0.479 with ['crop']
5. Task 4c416de3: 0.475 with ['crop']
6. Task 53fb4810: 0.473 with ['crop']
7. Task 2c181942: 0.467 with ['crop', 'fill_interior']

Target: Solve at least 1-3 tasks with v0.95 parametric synthesis

Author: Prometheus v0.95
Date: 2025-10-22
"""

import json
import time
import numpy as np
from prometheus_arc_v095_synthesis import PrometheusARC_v095_Synthesis

# Top 7 crop tasks from v0.92 benchmark
TOP_CROP_TASKS = [
    '135a2760',  # 0.491
    '409aa875',  # 0.487
    '332f06d7',  # 0.481
    '3e6067c3',  # 0.479
    '4c416de3',  # 0.475
    '53fb4810',  # 0.473
    '2c181942',  # 0.467
]


def load_task(task_id: str, split: str = 'evaluation'):
    """Load task from ARC dataset."""
    filepath = f'arc_agi_2/data/{split}/{task_id}.json'
    with open(filepath, 'r') as f:
        return json.load(f)


def run_crop_task_tests():
    """Test v0.95 on top 7 crop tasks."""
    print("=" * 80)
    print("🧪 Testing v0.95 on Top 7 Crop Tasks")
    print("=" * 80)
    print(f"Tasks: {len(TOP_CROP_TASKS)}")
    print(f"Target: Solve 1-3 tasks (threshold 0.95)")
    print(f"Strategy: Template transfer → Beam search → v0.92 fallback")
    print("=" * 80)
    print()

    # Initialize solver
    solver = PrometheusARC_v095_Synthesis(
        template_db_path='arc_v095_seeded_templates.json',
        use_llm=False,
        beam_width=50,
        max_depth=5
    )

    # Load seeded templates
    solver.template_learner.load_database('arc_v095_seeded_templates.json')
    print(f"✅ Loaded {len(solver.template_learner.templates)} templates")
    print()

    results = []
    solved_count = 0
    improved_count = 0

    start_time = time.time()

    for i, task_id in enumerate(TOP_CROP_TASKS, 1):
        print(f"[{i}/{len(TOP_CROP_TASKS)}] Task {task_id}")
        print("-" * 80)

        # Load task
        task_data = load_task(task_id)
        train_examples = task_data['train']
        test_examples = task_data['test']

        # Get v0.92 baseline fitness from benchmark
        with open('arc_v092_baseline_evaluation_50tasks.json', 'r') as f:
            v092_results = json.load(f)
        v092_result = next((r for r in v092_results['results'] if r['task_id'] == task_id), None)
        baseline_fitness = v092_result['fitness'] if v092_result else 0.0
        baseline_pattern = v092_result['pattern'] if v092_result else []

        print(f"  v0.92 baseline: {baseline_fitness:.3f} with {baseline_pattern}")

        # Solve with v0.95
        task_start = time.time()
        result = solver.solve_task(train_examples, test_examples, task_id)
        task_time = time.time() - task_start

        fitness = result.get('fitness', 0.0) if result else 0.0
        success = fitness >= 0.95  # Success defined as fitness >= 0.95
        method = result.get('v095_method', result.get('method', 'unknown'))
        pattern = result.get('pattern', [])

        # Check improvement
        improved = fitness > baseline_fitness

        print(f"  v0.95 result: {fitness:.3f} with {pattern}")
        print(f"  Method: {method}")
        print(f"  Improvement: {'+' if improved else ''}{(fitness - baseline_fitness):.3f}")
        print(f"  Time: {task_time:.1f}s")

        if success:
            print(f"  ✅ SOLVED! (fitness {fitness:.3f})")
            solved_count += 1
        elif improved:
            print(f"  ⬆️  Improved over v0.92 baseline")
            improved_count += 1
        else:
            print(f"  ➡️  Same or worse than baseline")

        print()

        results.append({
            'task_id': task_id,
            'success': bool(success),  # Convert numpy bool to Python bool
            'fitness': float(fitness),
            'pattern': pattern,
            'method': method,
            'baseline_fitness': float(baseline_fitness),
            'improvement': float(fitness - baseline_fitness),
            'time': float(task_time)
        })

    total_time = time.time() - start_time

    # Summary
    print("=" * 80)
    print("📊 RESULTS SUMMARY")
    print("=" * 80)
    print(f"Solved: {solved_count}/{len(TOP_CROP_TASKS)} ({100*solved_count/len(TOP_CROP_TASKS):.1f}%)")
    print(f"Improved: {improved_count}/{len(TOP_CROP_TASKS)} ({100*improved_count/len(TOP_CROP_TASKS):.1f}%)")
    print(f"Total time: {total_time:.1f}s ({total_time/len(TOP_CROP_TASKS):.1f}s per task)")
    print()

    # Target achievement
    print("🎯 TARGET ACHIEVEMENT")
    print("-" * 80)
    if solved_count >= 1:
        print(f"✅ TARGET MET: Solved {solved_count} task(s) (target was 1-3)")
    else:
        print(f"❌ TARGET NOT MET: Solved {solved_count} tasks (target was 1-3)")

    # Best improvements
    print()
    print("📈 TOP IMPROVEMENTS")
    print("-" * 80)
    sorted_results = sorted(results, key=lambda x: x['improvement'], reverse=True)
    for i, r in enumerate(sorted_results[:5], 1):
        print(f"{i}. Task {r['task_id']}: {r['baseline_fitness']:.3f} → {r['fitness']:.3f} "
              f"({r['improvement']:+.3f}) via {r['method']}")

    # Method breakdown
    print()
    print("🔬 METHOD BREAKDOWN")
    print("-" * 80)
    method_counts = {}
    for r in results:
        method = r['method']
        if method not in method_counts:
            method_counts[method] = {'count': 0, 'solved': 0, 'avg_fitness': 0.0}
        method_counts[method]['count'] += 1
        if r['success']:
            method_counts[method]['solved'] += 1
        method_counts[method]['avg_fitness'] += r['fitness']

    for method, stats in method_counts.items():
        avg = stats['avg_fitness'] / stats['count']
        print(f"{method}: {stats['count']} tasks, {stats['solved']} solved, avg fitness {avg:.3f}")

    # Save results
    output = {
        'version': 'v0.95',
        'test_set': 'top_7_crop_tasks',
        'summary': {
            'solved': solved_count,
            'total': len(TOP_CROP_TASKS),
            'improved': improved_count,
            'accuracy': solved_count / len(TOP_CROP_TASKS),
            'time': total_time
        },
        'results': results
    }

    with open('arc_v095_crop_tasks_test.json', 'w') as f:
        json.dump(output, f, indent=2)

    print()
    print("💾 Results saved to: arc_v095_crop_tasks_test.json")
    print("=" * 80)

    return solved_count >= 1  # Return True if target met


if __name__ == '__main__':
    target_met = run_crop_task_tests()

    if target_met:
        print("\n🎉 SUCCESS! v0.95 achieved the target of solving 1-3 tasks!")
    else:
        print("\n📊 v0.95 did not solve any tasks, but may have improved over baseline")
        print("   Next steps: Enhance parametric search or increase beam width")
