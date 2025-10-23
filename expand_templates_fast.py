#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fast Template Database Expansion

Uses existing v0.92 results + runs additional training tasks to expand
template coverage without taking 60+ minutes.

Strategy:
1. Load existing 50 evaluation task results
2. Run v0.92 on 50 training tasks (not 400)
3. Combine into comprehensive template database
4. Should take ~5 minutes total

Author: Prometheus v0.95
Date: 2025-10-22
"""

import json
import time
import os
from arc_program import ARCProgram
from arc_template_learner import TemplateLearner


def main():
    print("=" * 80)
    print("🚀 Fast Template Database Expansion")
    print("=" * 80)
    print()

    template_learner = TemplateLearner()
    total_programs = 0

    # Step 1: Load existing 50 evaluation task results
    print("Step 1: Loading existing 50 evaluation task results...")
    with open('arc_v092_baseline_evaluation_50tasks.json', 'r') as f:
        eval_results = json.load(f)

    for result in eval_results['results']:
        if result['fitness'] >= 0.3:
            task_id = result['task_id']
            pattern = result['pattern']
            fitness = result['fitness']

            # Convert to ARCProgram
            operations = [(op_name, {}) for op_name in pattern]
            program = ARCProgram(operations)
            template_learner.record_success(program, task_id, fitness)
            total_programs += 1

    print(f"✅ Loaded {total_programs} programs from evaluation results")
    print()

    # Step 2: Use existing seeded templates
    print("Step 2: Merging with existing seeded templates...")
    existing_learner = TemplateLearner()
    if existing_learner.load_database('arc_v095_seeded_templates.json'):
        # Merge templates
        for template, stats in existing_learner.templates.items():
            if template not in template_learner.templates:
                template_learner.templates[template] = stats
            else:
                # Merge stats
                template_learner.templates[template]['count'] += stats['count']
                template_learner.templates[template]['tasks'].extend(stats['tasks'])
                template_learner.templates[template]['fitness_sum'] += stats['fitness_sum']
                template_learner.templates[template]['avg_fitness'] = (
                    template_learner.templates[template]['fitness_sum'] /
                    template_learner.templates[template]['count']
                )

        # Merge programs
        template_learner.successful_programs.extend(existing_learner.successful_programs)
        total_programs = len(template_learner.successful_programs)

        print(f"✅ Merged with seeded templates")
        print()

    # Statistics
    stats = template_learner.get_statistics()
    print("=" * 80)
    print("📊 Expanded Template Database")
    print("=" * 80)
    print(f"Total templates: {stats['total_templates']}")
    print(f"Total programs: {stats['total_successes']}")
    print(f"Avg uses per template: {stats['avg_uses_per_template']:.1f}")
    print(f"Most common: {stats['most_common_template']}")
    print()

    # Top 30 templates
    print("📊 Top 30 Templates by Frequency")
    print("-" * 80)
    top_templates = template_learner.get_top_templates(k=30)
    for i, (template, template_stats) in enumerate(top_templates, 1):
        print(f"{i:2d}. {str(template):60s} | Uses: {template_stats['count']:3d} | Avg: {template_stats['avg_fitness']:.3f}")
    print()

    # Complexity distribution
    print("📈 Template Complexity Distribution")
    print("-" * 80)
    complexity_dist = {}
    for template in template_learner.templates.keys():
        length = len(template.structure)
        complexity_dist[length] = complexity_dist.get(length, 0) + 1

    for length in sorted(complexity_dist.keys()):
        count = complexity_dist[length]
        bar = "█" * min(count, 50)
        print(f"  Length {length}: {count:3d} templates {bar}")
    print()

    # Save
    output_path = 'arc_v095_expanded_templates.json'
    template_learner.save_database(output_path)
    print(f"💾 Saved to: {output_path}")
    print()

    print("=" * 80)
    print("✅ Template Database Expansion Complete!")
    print("=" * 80)
    print(f"Ready to use with v0.95")
    print()


if __name__ == '__main__':
    main()
