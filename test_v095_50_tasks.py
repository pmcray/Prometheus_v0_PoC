#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v0.95 Comprehensive 50-Task Evaluation

Tests v0.95 with expanded template database on same 50 evaluation tasks
as v0.92 benchmark for direct comparison.

Target: 5-10% solve rate (3-5 tasks)

Author: Prometheus v0.95
Date: 2025-10-22
"""

import json
import time
from prometheus_arc_v095_synthesis import PrometheusARC_v095_Synthesis


def run_50_task_evaluation():
    """Run v0.95 on 50 evaluation tasks."""
    print("=" * 80)
    print("🧪 v0.95 Comprehensive 50-Task Evaluation")
    print("=" * 80)
    print(f"Test set: Same 50 evaluation tasks as v0.92 benchmark")
    print(f"Templates: Expanded database (63 programs, 14 templates)")
    print(f"Target: 5-10% solve rate (3-5 tasks)")
    print("=" * 80)
    print()

    # Initialize solver with expanded templates
    solver = PrometheusARC_v095_Synthesis(
        template_db_path='arc_v095_expanded_templates.json',
        use_llm=False,
        beam_width=50,
        max_depth=5
    )

    # Load task IDs from v0.92 benchmark
    with open('arc_v092_baseline_evaluation_50tasks.json', 'r') as f:
        v092_data = json.load(f)

    task_ids = [r['task_id'] for r in v092_data['results']]

    print(f"✅ Loaded {len(solver.template_learner.templates)} templates")
    print(f"✅ Loaded {len(task_ids)} tasks")
    print()

    results = []
    solved_count = 0
    improved_count = 0
    method_counts = {'template_transfer': 0, 'beam_search': 0, 'v092_fallback': 0}

    start_time = time.time()

    for i, task_id in enumerate(task_ids, 1):
        print(f"[{i}/{len(task_ids)}] Task {task_id}")

        # Load task
        filepath = f'arc_agi_2/data/evaluation/{task_id}.json'
        with open(filepath, 'r') as f:
            task_data = json.load(f)

        train_examples = task_data['train']
        test_examples = task_data.get('test', [])

        # Get v0.92 baseline
        v092_result = next((r for r in v092_data['results'] if r['task_id'] == task_id), None)
        baseline_fitness = v092_result['fitness'] if v092_result else 0.0

        # Solve with v0.95
        task_start = time.time()
        result = solver.solve_task(train_examples, test_examples, task_id)
        task_time = time.time() - task_start

        fitness = result.get('fitness', 0.0)
        success = fitness >= 0.95
        method = result.get('v095_method', 'unknown')
        pattern = result.get('pattern', [])
        improved = fitness > baseline_fitness

        # Track method
        if method in method_counts:
            method_counts[method] += 1

        # Status
        if success:
            print(f"  ✅ SOLVED! {fitness:.3f} via {method}")
            solved_count += 1
        elif improved:
            print(f"  ⬆️  Improved: {baseline_fitness:.3f} → {fitness:.3f} via {method}")
            improved_count += 1
        else:
            print(f"  ➡️  {fitness:.3f} via {method}")

        results.append({
            'task_id': task_id,
            'success': bool(success),
            'fitness': float(fitness),
            'pattern': pattern,
            'method': method,
            'baseline_fitness': float(baseline_fitness),
            'improvement': float(fitness - baseline_fitness),
            'time': float(task_time)
        })

    total_time = time.time() - start_time

    # Summary
    print()
    print("=" * 80)
    print("📊 RESULTS SUMMARY")
    print("=" * 80)
    print(f"Solved: {solved_count}/{len(task_ids)} ({100*solved_count/len(task_ids):.1f}%)")
    print(f"Improved over v0.92: {improved_count}/{len(task_ids)} ({100*improved_count/len(task_ids):.1f}%)")
    print(f"Total time: {total_time:.1f}s ({total_time/len(task_ids):.1f}s per task)")
    print()

    # Target achievement
    print("🎯 TARGET ACHIEVEMENT")
    print("-" * 80)
    target_min, target_max = 3, 5
    if solved_count >= target_min:
        print(f"✅ TARGET MET: Solved {solved_count} tasks (target was {target_min}-{target_max})")
    else:
        print(f"❌ TARGET NOT MET: Solved {solved_count} tasks (target was {target_min}-{target_max})")
    print()

    # Method breakdown
    print("🔬 METHOD BREAKDOWN")
    print("-" * 80)
    for method, count in sorted(method_counts.items(), key=lambda x: x[1], reverse=True):
        solved_by_method = sum(1 for r in results if r['method'] == method and r['success'])
        avg_fitness = sum(r['fitness'] for r in results if r['method'] == method) / count if count > 0 else 0
        print(f"{method:20s}: {count:2d} tasks | {solved_by_method:2d} solved | avg fitness: {avg_fitness:.3f}")
    print()

    # vs v0.92 comparison
    print("📈 vs v0.92 COMPARISON")
    print("-" * 80)
    v092_solved = sum(1 for r in v092_data['results'] if r['fitness'] >= 0.95)
    v092_avg = sum(r['fitness'] for r in v092_data['results']) / len(v092_data['results'])
    v095_avg = sum(r['fitness'] for r in results) / len(results)

    print(f"Solve rate:")
    print(f"  v0.92: {v092_solved}/{len(task_ids)} ({100*v092_solved/len(task_ids):.1f}%)")
    print(f"  v0.95: {solved_count}/{len(task_ids)} ({100*solved_count/len(task_ids):.1f}%)")
    print(f"  Change: {solved_count - v092_solved:+d} tasks")
    print()
    print(f"Average fitness:")
    print(f"  v0.92: {v092_avg:.3f}")
    print(f"  v0.95: {v095_avg:.3f}")
    print(f"  Change: {v095_avg - v092_avg:+.3f}")
    print()

    # Save results
    output = {
        'version': 'v0.95',
        'template_db': 'arc_v095_expanded_templates.json',
        'config': {
            'beam_width': 50,
            'max_depth': 5,
            'use_llm': False
        },
        'summary': {
            'solved': solved_count,
            'total': len(task_ids),
            'improved': improved_count,
            'accuracy': solved_count / len(task_ids),
            'time': total_time,
            'avg_fitness': v095_avg
        },
        'method_counts': method_counts,
        'results': results
    }

    with open('arc_v095_50tasks_evaluation.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"💾 Results saved to: arc_v095_50tasks_evaluation.json")
    print("=" * 80)

    return solved_count >= target_min


if __name__ == '__main__':
    target_met = run_50_task_evaluation()

    if target_met:
        print("\n🎉 SUCCESS! v0.95 achieved the target!")
    else:
        print("\n📊 v0.95 completed evaluation - check results for insights")
