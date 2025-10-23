#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v0.95 Final 50-Task Evaluation with 75 Templates

Tests v0.95 with expanded template database (75 templates from 400 training tasks).

Expected improvements:
- 5x more template coverage (15 → 75 templates)
- Better template matching
- Higher solve rate (target: 12-15 tasks, 24-30%)

Author: Prometheus v0.95
Date: 2025-10-22
"""

import json
import time
from pathlib import Path
from prometheus_arc_v095_synthesis import PrometheusARC_v095_Synthesis


def load_evaluation_tasks(n=50):
    """Load first N evaluation task IDs."""
    eval_dir = Path('arc_agi_2/data/evaluation')
    task_files = sorted(eval_dir.glob('*.json'))
    return [f.stem for f in task_files[:n]]


def run_final_50_task_evaluation():
    """
    Run v0.95 on 50 evaluation tasks with expanded 75-template database.
    """
    print("=" * 80)
    print("🚀 v0.95 Final Evaluation: 50 Tasks with 75 Templates")
    print("=" * 80)
    print()

    # Load v0.92 baseline for comparison
    print("📊 Loading v0.92 baseline results...")
    with open('arc_v092_baseline_evaluation_50tasks.json', 'r') as f:
        v092_results = json.load(f)

    v092_by_task = {r['task_id']: r for r in v092_results['results']}
    print(f"   v0.92 baseline: {v092_results['summary']['solved']} solved")
    print()

    # Initialize v0.95 with expanded template database
    print("🔧 Initializing v0.95 with 75-template database...")
    solver = PrometheusARC_v095_Synthesis(
        template_db_path='arc_v095_training_400_templates.json',
        use_llm=False,
        beam_width=50,
        max_depth=5
    )
    print("   ✅ v0.95 initialized")
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
        task_file = f'arc_agi_2/data/evaluation/{task_id}.json'
        with open(task_file, 'r') as f:
            task_data = json.load(f)

        train_examples = task_data['train']
        test_examples = task_data['test']

        # Solve with v0.95
        result = solver.solve_task(train_examples, test_examples, task_id)

        task_time = time.time() - task_start

        fitness = result.get('fitness', 0.0)
        success = fitness >= 0.95
        method = result.get('v095_method', 'unknown')
        pattern = result.get('pattern', [])

        # Compare to v0.92
        v092_fitness = v092_by_task[task_id]['fitness'] if task_id in v092_by_task else 0.0
        improvement = fitness - v092_fitness

        # Track stats
        if success:
            solved_count += 1
            status = "✓ SOLVED"
        elif improvement > 0.1:
            improved_count += 1
            status = "↑ IMPROVED"
        else:
            status = "✗"

        print(f"[{i:2d}/50] {status} {task_id}: {fitness:.3f} (v0.92: {v092_fitness:.3f}, Δ{improvement:+.3f}) via {method} in {task_time:.1f}s")

        # Store result
        results.append({
            'task_id': task_id,
            'fitness': float(fitness),
            'success': bool(success),
            'method': method,
            'pattern': pattern,
            'time': float(task_time),
            'v092_fitness': float(v092_fitness),
            'improvement': float(improvement)
        })

    total_time = time.time() - start_time

    print()
    print("=" * 80)
    print("📊 FINAL RESULTS")
    print("=" * 80)
    print(f"Solved: {solved_count}/50 ({solved_count/50*100:.1f}%)")
    print(f"Improved over v0.92: {improved_count}/50 ({improved_count/50*100:.1f}%)")
    print(f"Total time: {total_time:.1f}s ({total_time/50:.1f}s per task)")
    print()

    # Method breakdown
    method_stats = {}
    for r in results:
        method = r['method']
        if method not in method_stats:
            method_stats[method] = {'count': 0, 'solved': 0, 'total_fitness': 0.0}

        method_stats[method]['count'] += 1
        method_stats[method]['total_fitness'] += r['fitness']
        if r['success']:
            method_stats[method]['solved'] += 1

    print("🔬 METHOD BREAKDOWN")
    print("-" * 80)
    for method in sorted(method_stats.keys()):
        stats = method_stats[method]
        avg_fitness = stats['total_fitness'] / stats['count']
        print(f"{method:20s}: {stats['count']:2d} tasks | {stats['solved']:2d} solved | avg fitness: {avg_fitness:.3f}")
    print()

    # vs v0.92 comparison
    v092_avg = sum(v092_by_task[tid]['fitness'] for tid in task_ids) / len(task_ids)
    v095_avg = sum(r['fitness'] for r in results) / len(results)

    print("📈 vs v0.92 COMPARISON")
    print("-" * 80)
    print(f"Solve rate:")
    print(f"  v0.92: {v092_results['summary']['solved']}/50 ({v092_results['summary']['solved']/50*100:.1f}%)")
    print(f"  v0.95: {solved_count}/50 ({solved_count/50*100:.1f}%)")
    print(f"  Change: {solved_count - v092_results['summary']['solved']:+d} tasks")
    print()
    print(f"Average fitness:")
    print(f"  v0.92: {v092_avg:.3f}")
    print(f"  v0.95: {v095_avg:.3f}")
    print(f"  Change: {v095_avg - v092_avg:+.3f}")
    print()

    # Target assessment
    print("🎯 TARGET ASSESSMENT")
    print("-" * 80)
    print(f"Option C Target: 20-30% solve rate (10-15 tasks)")
    print(f"Achieved: {solved_count/50*100:.1f}% ({solved_count} tasks)")
    if solved_count >= 10:
        print("✅ TARGET MET!")
    elif solved_count >= 7:
        print("🟨 Close to target")
    else:
        print("❌ Below target")
    print()

    # Save results
    output_data = {
        'version': 'v0.95_final',
        'template_database': 'arc_v095_training_400_templates.json',
        'num_templates': 75,
        'results': results,
        'summary': {
            'solved': solved_count,
            'improved': improved_count,
            'avg_fitness': v095_avg,
            'total_time': total_time,
            'avg_time_per_task': total_time / 50
        },
        'method_breakdown': method_stats,
        'comparison': {
            'v092_solved': v092_results['summary']['solved'],
            'v092_avg_fitness': v092_avg,
            'improvement_solved': solved_count - v092_results['summary']['solved'],
            'improvement_fitness': v095_avg - v092_avg
        }
    }

    output_file = 'arc_v095_final_50tasks_evaluation.json'
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"💾 Results saved: {output_file}")
    print()

    return output_data


if __name__ == '__main__':
    run_final_50_task_evaluation()
    print("=" * 80)
    print("🎉 Evaluation complete!")
    print("=" * 80)
