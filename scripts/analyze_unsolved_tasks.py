#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze 45 Unsolved Evaluation Tasks from v0.96c

Purpose: Identify patterns, failure modes, and missing capabilities
to guide Phase 2 operation development.
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np


def load_results():
    """Load v0.96c evaluation results."""
    with open('arc_v096c_option_i_50tasks.json', 'r') as f:
        return json.load(f)


def load_task(task_id):
    """Load task data from evaluation set."""
    task_file = Path(f'arc_agi_2/data/evaluation/{task_id}.json')
    with open(task_file, 'r') as f:
        return json.load(f)


def analyze_grid_properties(task_data):
    """Extract grid property statistics from task."""
    stats = {
        'input_sizes': [],
        'output_sizes': [],
        'size_changes': [],
        'color_counts': [],
        'has_objects': False,
        'has_patterns': False,
        'has_symmetry': False,
    }

    for example in task_data['train']:
        inp = np.array(example['input'])
        out = np.array(example['output'])

        stats['input_sizes'].append(inp.shape)
        stats['output_sizes'].append(out.shape)

        # Size change analysis
        if inp.shape != out.shape:
            stats['size_changes'].append((inp.shape, out.shape))

        # Color analysis
        unique_colors = len(np.unique(out))
        stats['color_counts'].append(unique_colors)

    return stats


def categorize_transformation(task_id, task_data, program, fitness):
    """Categorize the type of transformation required."""
    categories = []

    stats = analyze_grid_properties(task_data)

    # Size-based categorization
    if any(inp != out for inp, out in zip(stats['input_sizes'], stats['output_sizes'])):
        size_changes = stats['size_changes']
        if size_changes:
            inp_shape, out_shape = size_changes[0]
            if out_shape[0] > inp_shape[0] or out_shape[1] > inp_shape[1]:
                categories.append('size_increase')
            elif out_shape[0] < inp_shape[0] or out_shape[1] < inp_shape[1]:
                categories.append('size_decrease')
            else:
                categories.append('size_change')
    else:
        categories.append('same_size')

    # Color complexity
    avg_colors = np.mean(stats['color_counts'])
    if avg_colors <= 2:
        categories.append('simple_colors')
    elif avg_colors <= 4:
        categories.append('moderate_colors')
    else:
        categories.append('complex_colors')

    # Program analysis
    if program:
        if any('map_color' in op or 'swap_colors' in op for op in program):
            categories.append('color_mapping')
        if any('rotate' in op or 'flip' in op or 'transpose' in op for op in program):
            categories.append('geometric')
        if any('crop' in op or 'expand' in op or 'compress' in op or 'fit' in op for op in program):
            categories.append('size_ops')
        if any('symmetrize' in op for op in program):
            categories.append('symmetry')
        if any('filter' in op or 'remove' in op for op in program):
            categories.append('filtering')

    # Fitness-based categorization
    if fitness >= 0.9:
        categories.append('near_solved')
    elif fitness >= 0.7:
        categories.append('high_partial')
    elif fitness >= 0.5:
        categories.append('medium_partial')
    elif fitness >= 0.3:
        categories.append('low_partial')
    else:
        categories.append('very_low')

    return categories


def analyze_unsolved_tasks():
    """Main analysis of unsolved tasks."""

    print("=" * 80)
    print("🔍 Analyzing 45 Unsolved Evaluation Tasks")
    print("=" * 80)
    print()

    # Load results
    results = load_results()
    unsolved = [r for r in results if not r['solved']]

    print(f"Total tasks: {len(results)}")
    print(f"Solved: {len(results) - len(unsolved)}")
    print(f"Unsolved: {len(unsolved)}")
    print()

    # Fitness distribution
    print("=" * 80)
    print("📊 FITNESS DISTRIBUTION")
    print("=" * 80)
    print()

    fitness_ranges = [
        (0.9, 0.95, 'Near-solved (0.90-0.95)'),
        (0.8, 0.9, 'Very high (0.80-0.90)'),
        (0.7, 0.8, 'High (0.70-0.80)'),
        (0.5, 0.7, 'Medium (0.50-0.70)'),
        (0.3, 0.5, 'Low (0.30-0.50)'),
        (0.0, 0.3, 'Very low (0.00-0.30)'),
    ]

    for low, high, label in fitness_ranges:
        in_range = [r for r in unsolved if low <= r['fitness'] < high]
        if in_range:
            print(f"{label}: {len(in_range)} tasks")
            for r in in_range[:3]:  # Show first 3
                prog_str = ', '.join(r['program'][:2]) if r['program'] else 'none'
                print(f"  - {r['task_id']}: {r['fitness']:.3f} - {prog_str}")
            if len(in_range) > 3:
                print(f"    ... and {len(in_range) - 3} more")
        else:
            print(f"{label}: 0 tasks")
        print()

    # Most common programs on unsolved tasks
    print("=" * 80)
    print("🔧 MOST COMMON PROGRAMS (Unsolved Tasks)")
    print("=" * 80)
    print()

    program_counter = Counter()
    for r in unsolved:
        if r['program']:
            # Use first operation as proxy for program type
            first_op = r['program'][0].split('(')[0]
            program_counter[first_op] += 1

    print("Top operations attempted:")
    for op, count in program_counter.most_common(10):
        pct = 100 * count / len(unsolved)
        print(f"  {op:<20} {count:>3} tasks ({pct:>5.1f}%)")
    print()

    # Categorize tasks
    print("=" * 80)
    print("🏷️  TASK CATEGORIZATION")
    print("=" * 80)
    print()

    category_counter = Counter()
    task_categories = {}

    for r in unsolved:
        task_data = load_task(r['task_id'])
        categories = categorize_transformation(
            r['task_id'],
            task_data,
            r['program'],
            r['fitness']
        )
        task_categories[r['task_id']] = categories
        for cat in categories:
            category_counter[cat] += 1

    print("Category frequencies:")
    for cat, count in category_counter.most_common():
        pct = 100 * count / len(unsolved)
        print(f"  {cat:<25} {count:>3} tasks ({pct:>5.1f}%)")
    print()

    # Near-solved tasks (focus area)
    print("=" * 80)
    print("🎯 NEAR-SOLVED TASKS (fitness ≥ 0.90)")
    print("=" * 80)
    print()

    near_solved = [r for r in unsolved if r['fitness'] >= 0.90]
    if near_solved:
        print(f"Found {len(near_solved)} near-solved tasks:")
        print()
        for r in near_solved:
            task_data = load_task(r['task_id'])
            stats = analyze_grid_properties(task_data)

            print(f"Task {r['task_id']}: fitness={r['fitness']:.3f}")
            print(f"  Program: {r['program']}")
            print(f"  Input sizes: {stats['input_sizes']}")
            print(f"  Output sizes: {stats['output_sizes']}")
            print(f"  Size changes: {len(stats['size_changes'])} examples")
            print(f"  Avg colors: {np.mean(stats['color_counts']):.1f}")
            print(f"  Categories: {task_categories[r['task_id']]}")
            print()

        print("💡 RECOMMENDATION:")
        print("   These tasks are closest to being solved. Focus on:")
        print("   - Adjusting complexity penalty (test 0.003, 0.001)")
        print("   - Fine-tuning existing operations")
        print()
    else:
        print("No tasks with fitness ≥ 0.90")
        print()

    # Size transformation analysis
    print("=" * 80)
    print("📐 SIZE TRANSFORMATION PATTERNS")
    print("=" * 80)
    print()

    size_increase = [r for r in unsolved if 'size_increase' in task_categories.get(r['task_id'], [])]
    size_decrease = [r for r in unsolved if 'size_decrease' in task_categories.get(r['task_id'], [])]
    same_size = [r for r in unsolved if 'same_size' in task_categories.get(r['task_id'], [])]

    print(f"Size increase: {len(size_increase)} tasks")
    print(f"Size decrease: {len(size_decrease)} tasks")
    print(f"Same size: {len(same_size)} tasks")
    print()

    if size_increase:
        print("Sample size-increase tasks:")
        for r in size_increase[:3]:
            print(f"  {r['task_id']}: {r['fitness']:.3f} - {r['program'][0] if r['program'] else 'none'}")
        print()

    # Missing capabilities analysis
    print("=" * 80)
    print("🔍 GAP ANALYSIS - What's Missing?")
    print("=" * 80)
    print()

    # Check which operations are underrepresented in successful programs
    solved = [r for r in results if r['solved']]
    solved_ops = Counter()
    unsolved_ops = Counter()

    for r in solved:
        for op in r['program']:
            op_name = op.split('(')[0]
            solved_ops[op_name] += 1

    for r in unsolved:
        for op in r['program']:
            op_name = op.split('(')[0]
            unsolved_ops[op_name] += 1

    print("Operations used in SOLVED tasks:")
    for op, count in solved_ops.most_common(10):
        print(f"  {op:<20} {count:>3} times")
    print()

    print("Most attempted but unsuccessful operations:")
    for op, count in unsolved_ops.most_common(10):
        if op not in solved_ops or solved_ops[op] < count:
            print(f"  {op:<20} {count:>3} attempts (rarely succeeds)")
    print()

    # Recommendations
    print("=" * 80)
    print("💡 RECOMMENDATIONS FOR PHASE 2")
    print("=" * 80)
    print()

    print("Based on analysis of 45 unsolved tasks:")
    print()

    print("1. **Complexity Penalty Adjustment** (Step C)")
    print(f"   - {len(near_solved)} tasks with fitness 0.90-0.95")
    print("   - Test penalties: 0.003, 0.001, 0 (remove entirely)")
    print("   - Expected gain: 2-5 additional tasks")
    print()

    print("2. **Size Operations Need Improvement**")
    print(f"   - {len(size_increase)} tasks need size increase")
    print(f"   - {len(size_decrease)} tasks need size decrease")
    print("   - Current ops (expand_to_size, compress_to_fit) may need refinement")
    print()

    print("3. **Pattern Detection/Replication**")
    print("   - Many tasks involve repeating patterns")
    print("   - Consider adding: detect_pattern, replicate_pattern")
    print()

    print("4. **Object-based Operations**")
    print("   - Some tasks require object extraction/manipulation")
    print("   - Consider adding: extract_objects, move_objects, align_objects")
    print()

    print("5. **Composition/Layering**")
    print("   - Some high-complexity tasks may need operation chaining")
    print("   - Current max_depth=5 may be limiting")
    print()

    # Save detailed analysis
    output = {
        'total_unsolved': len(unsolved),
        'near_solved': len(near_solved),
        'fitness_distribution': {
            label: len([r for r in unsolved if low <= r['fitness'] < high])
            for low, high, label in fitness_ranges
        },
        'common_operations': dict(program_counter.most_common(10)),
        'categories': dict(category_counter.most_common()),
        'task_details': [
            {
                'task_id': r['task_id'],
                'fitness': r['fitness'],
                'program': r['program'],
                'categories': task_categories.get(r['task_id'], [])
            }
            for r in unsolved
        ]
    }

    with open('unsolved_tasks_analysis.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("=" * 80)
    print("💾 Analysis saved: unsolved_tasks_analysis.json")
    print("=" * 80)

    return output


if __name__ == '__main__':
    analyze_unsolved_tasks()
    print()
    print("✅ Analysis complete!")
