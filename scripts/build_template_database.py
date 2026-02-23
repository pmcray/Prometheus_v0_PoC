#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build Comprehensive Template Database from ARC Training Tasks

Runs v0.92 on all 400 training tasks to extract diverse templates
for v0.95 template transfer learning.

Strategy:
1. Run v0.92 on all training tasks
2. Collect patterns with fitness >= 0.3 (meaningful progress)
3. Extract templates from successful patterns
4. Build comprehensive template database

Expected outcome:
- 50-100 unique templates
- 200-300 successful programs
- 60-70% coverage on evaluation tasks

Author: Prometheus v0.95
Date: 2025-10-22
"""

import json
import time
import os
from prometheus_arc_v092_baseline import PrometheusARC_v092_Baseline
from arc_template_learner import TemplateLearner
from arc_program import ARCProgram


def load_all_training_tasks():
    """Load all training task IDs."""
    training_dir = 'arc_agi_2/data/training'
    task_files = [f for f in os.listdir(training_dir) if f.endswith('.json')]
    task_ids = [f.replace('.json', '') for f in task_files]
    return sorted(task_ids)


def run_v092_on_training_set(max_tasks=400, fitness_threshold=0.3):
    """
    Run v0.92 on training tasks and collect successful patterns.

    Args:
        max_tasks: Maximum number of tasks to process
        fitness_threshold: Minimum fitness to consider successful

    Returns:
        List of (task_id, pattern, fitness) tuples
    """
    print("=" * 80)
    print("🏗️  Building Template Database from Training Tasks")
    print("=" * 80)
    print(f"Max tasks: {max_tasks}")
    print(f"Fitness threshold: {fitness_threshold}")
    print("=" * 80)
    print()

    # Load training task IDs
    task_ids = load_all_training_tasks()
    if len(task_ids) > max_tasks:
        task_ids = task_ids[:max_tasks]

    print(f"📝 Found {len(task_ids)} training tasks")
    print()

    # Initialize solver
    solver = PrometheusARC_v092_Baseline()

    # Results
    results = []
    successful_count = 0

    start_time = time.time()

    for i, task_id in enumerate(task_ids, 1):
        # Load task
        filepath = f'arc_agi_2/data/training/{task_id}.json'
        with open(filepath, 'r') as f:
            task_data = json.load(f)

        train_examples = task_data['train']
        test_examples = task_data.get('test', [])

        # Solve with v0.92
        try:
            result = solver.solve_task(train_examples, test_examples, task_id)

            fitness = result.get('fitness', 0.0)
            pattern = result.get('pattern', [])

            # Record if meaningful progress
            if fitness >= fitness_threshold:
                results.append((task_id, pattern, fitness))
                successful_count += 1
                status = "✓"
            else:
                status = "✗"

            # Progress update every 10 tasks
            if i % 10 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed
                remaining = (len(task_ids) - i) / rate if rate > 0 else 0

                print(f"[{i}/{len(task_ids)}] {status} {task_id}: {fitness:.3f} {pattern[:2]}{'...' if len(pattern) > 2 else ''}")
                print(f"  Progress: {100*i/len(task_ids):.1f}% | "
                      f"Success: {successful_count}/{i} ({100*successful_count/i:.1f}%) | "
                      f"ETA: {remaining/60:.1f}min")
                print()

        except Exception as e:
            print(f"[{i}/{len(task_ids)}] ✗ {task_id}: ERROR - {str(e)}")

    total_time = time.time() - start_time

    print()
    print("=" * 80)
    print("📊 Training Set Results")
    print("=" * 80)
    print(f"Tasks processed: {len(task_ids)}")
    print(f"Successful (fitness ≥ {fitness_threshold}): {successful_count} ({100*successful_count/len(task_ids):.1f}%)")
    print(f"Total time: {total_time/60:.1f} min ({total_time/len(task_ids):.1f}s per task)")
    print("=" * 80)
    print()

    return results


def build_template_database(results, output_path='arc_v095_comprehensive_templates.json'):
    """
    Build template database from v0.92 results.

    Args:
        results: List of (task_id, pattern, fitness) tuples
        output_path: Where to save template database

    Returns:
        TemplateLearner with comprehensive templates
    """
    print("🧠 Building Template Database...")
    print()

    template_learner = TemplateLearner()

    for task_id, pattern, fitness in results:
        # Convert pattern to ARCProgram
        operations = [(op_name, {}) for op_name in pattern]
        program = ARCProgram(operations)

        # Record success
        template_learner.record_success(program, task_id, fitness)

    # Statistics
    stats = template_learner.get_statistics()
    print(f"✅ Built template database:")
    print(f"   Total templates: {stats['total_templates']}")
    print(f"   Total programs: {stats['total_successes']}")
    print(f"   Avg uses per template: {stats['avg_uses_per_template']:.1f}")
    print(f"   Most common: {stats['most_common_template']}")
    print()

    # Top 20 templates
    print("📊 Top 20 Templates by Frequency")
    print("-" * 80)
    top_templates = template_learner.get_top_templates(k=20)
    for i, (template, template_stats) in enumerate(top_templates, 1):
        print(f"{i:2d}. {str(template):60s} | Uses: {template_stats['count']:3d} | Avg: {template_stats['avg_fitness']:.3f}")
    print()

    # Save database
    template_learner.save_database(output_path)
    print(f"💾 Saved to: {output_path}")
    print()

    return template_learner


def analyze_coverage(template_learner):
    """Analyze template coverage statistics."""
    print("📈 Template Coverage Analysis")
    print("-" * 80)

    templates = template_learner.templates

    # Complexity distribution
    complexity_dist = {}
    for template in templates.keys():
        length = len(template.structure)
        complexity_dist[length] = complexity_dist.get(length, 0) + 1

    print("Template Complexity Distribution:")
    for length in sorted(complexity_dist.keys()):
        count = complexity_dist[length]
        bar = "█" * (count // 2)
        print(f"  Length {length}: {count:3d} templates {bar}")
    print()

    # Most common operations
    op_counts = {}
    for template in templates.keys():
        for op_name, _ in template.structure:
            op_counts[op_name] = op_counts.get(op_name, 0) + 1

    print("Top 15 Operations in Templates:")
    sorted_ops = sorted(op_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    for op_name, count in sorted_ops:
        print(f"  {op_name:20s}: {count:3d} uses")
    print()


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("🚀 Template Database Builder for v0.95")
    print("=" * 80)
    print()

    # Step 1: Run v0.92 on training tasks
    print("Step 1: Running v0.92 on training tasks...")
    print("(This will take ~20-30 minutes for 400 tasks)")
    print()

    results = run_v092_on_training_set(max_tasks=400, fitness_threshold=0.3)

    # Save raw results
    with open('arc_training_v092_results.json', 'w') as f:
        json.dump({
            'results': [
                {'task_id': tid, 'pattern': pat, 'fitness': fit}
                for tid, pat, fit in results
            ]
        }, f, indent=2)

    print(f"💾 Saved raw results to: arc_training_v092_results.json")
    print()

    # Step 2: Build template database
    print("Step 2: Building template database...")
    print()

    template_learner = build_template_database(results)

    # Step 3: Analyze coverage
    print("Step 3: Analyzing template coverage...")
    print()

    analyze_coverage(template_learner)

    # Done
    print("=" * 80)
    print("✅ Template Database Build Complete!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Load comprehensive templates in v0.95")
    print("2. Run v0.95 on 50 evaluation tasks")
    print("3. Measure improved coverage and solve rate")
    print()
