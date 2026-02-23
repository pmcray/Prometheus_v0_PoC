#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seed v0.95 Template Database from v0.92 Benchmark Results

This script extracts the 6 key templates identified in the v0.92 50-task
benchmark and seeds the v0.95 template learner for transfer learning.

Templates extracted:
1. Single crop (19 tasks, avg fitness 0.407)
2. Flip operations (7 tasks, avg fitness 0.418)
3. Crop + fill (5 tasks, avg fitness 0.443)
4. Scale + downsample (2 tasks, avg fitness 0.459)
5. Flip + extract (1 task, fitness 0.466)
6. Rotate + extract (1 task, fitness 0.463)

Author: Prometheus v0.95
Date: 2025-10-22
"""

import json
from arc_program import ARCProgram
from arc_template_learner import TemplateLearner
from arc_parametric_meta_learner import ParametricMetaLearner


def create_seeded_templates():
    """
    Create and seed template database from v0.92 benchmark findings.

    Returns:
        TemplateLearner with seeded templates
    """
    template_learner = TemplateLearner()

    # Load v0.92 benchmark results
    with open('arc_v092_baseline_evaluation_50tasks.json', 'r') as f:
        v092_results = json.load(f)

    print("=" * 80)
    print("🌱 Seeding v0.95 Template Database from v0.92 Results")
    print("=" * 80)
    print(f"Source: 50 evaluation tasks")
    print(f"Templates to extract: 6 key patterns\n")

    # Process each task result and record as successful program
    templates_added = 0

    for result in v092_results['results']:
        task_id = result['task_id']
        pattern = result['pattern']
        fitness = result['fitness']

        # Convert pattern (list of strings) to ARCProgram
        # Since v0.92 used fixed primitives, we create programs with empty params
        operations = [(op_name, {}) for op_name in pattern]
        program = ARCProgram(operations)

        # Record as success (using fitness threshold 0.3 to capture meaningful patterns)
        if fitness >= 0.3:
            template_learner.record_success(program, task_id, fitness)
            templates_added += 1

    print(f"✅ Recorded {templates_added} successful programs")
    print(f"✅ Extracted {len(template_learner.templates)} unique templates\n")

    # Display top templates
    print("-" * 80)
    print("📊 Top 10 Templates (by frequency)")
    print("-" * 80)

    top_templates = template_learner.get_top_templates(k=10)
    for i, (template, stats) in enumerate(top_templates, 1):
        print(f"{i:2d}. {template}")
        print(f"    Uses: {stats['count']}, Avg Fitness: {stats['avg_fitness']:.3f}")
        print(f"    Tasks: {', '.join(stats['tasks'][:5])}")
        print()

    # Save database
    template_learner.save_database('arc_v095_seeded_templates.json')
    print("💾 Saved template database to: arc_v095_seeded_templates.json")

    # Statistics
    stats = template_learner.get_statistics()
    print("\n" + "=" * 80)
    print("📈 Template Database Statistics")
    print("=" * 80)
    print(f"Total templates: {stats['total_templates']}")
    print(f"Total successes: {stats['total_successes']}")
    print(f"Avg uses per template: {stats['avg_uses_per_template']:.1f}")
    print(f"Most common template: {stats['most_common_template']}")
    print("=" * 80)

    return template_learner


def seed_parametric_meta_learner():
    """
    Seed parametric meta-learner with parameter distributions from v0.92.

    Since v0.92 used fixed primitives, we'll use default parameter distributions
    but can track constraints for future learning.

    Returns:
        ParametricMetaLearner instance
    """
    meta_learner = ParametricMetaLearner()

    print("\n🧠 Initializing Parametric Meta-Learner")
    print("Note: v0.92 used fixed primitives, so parameter learning starts fresh")
    print("Future tasks will populate parameter distributions based on successes")

    return meta_learner


if __name__ == '__main__':
    # Create seeded databases
    template_learner = create_seeded_templates()
    meta_learner = seed_parametric_meta_learner()

    print("\n✅ v0.95 Template Database Seeding Complete!")
    print("\nNext steps:")
    print("1. Implement enhanced crop(mode=...) parametric search")
    print("2. Test v0.95 on top 7 crop tasks")
    print("3. Measure template transfer effectiveness")
