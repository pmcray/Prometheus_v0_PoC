#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze Failed ARC Tasks to Identify Missing Operations

Systematically analyzes 45 unsolved tasks from v0.95 benchmark to identify:
1. What patterns/transformations are needed
2. What operations are missing from current set
3. Priority ranking for new operations

Author: Prometheus Option E
Date: 2025-10-23
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict


def load_task(task_id: str, split='evaluation') -> dict:
    """Load task data."""
    task_file = f'arc_agi_2/data/{split}/{task_id}.json'
    with open(task_file, 'r') as f:
        return json.load(f)


def analyze_task_patterns(task_id: str, task_data: dict) -> dict:
    """
    Analyze a task to identify required transformations.

    Returns dict with detected patterns.
    """
    train_examples = task_data['train']

    if not train_examples:
        return {'error': 'No training examples'}

    patterns = {
        'task_id': task_id,
        'num_examples': len(train_examples),
        'transformations': []
    }

    for i, example in enumerate(train_examples):
        input_grid = np.array(example['input'])
        output_grid = np.array(example['output'])

        # Analyze transformation
        trans = analyze_transformation(input_grid, output_grid)
        patterns['transformations'].append(trans)

    # Find common patterns across examples
    patterns['common_patterns'] = find_common_patterns(patterns['transformations'])

    return patterns


def analyze_transformation(input_grid: np.ndarray, output_grid: np.ndarray) -> dict:
    """
    Analyze a single input→output transformation.

    Returns dict describing the transformation.
    """
    trans = {}

    # Size analysis
    trans['size_change'] = {
        'input_shape': input_grid.shape,
        'output_shape': output_grid.shape,
        'same_size': input_grid.shape == output_grid.shape
    }

    # Color analysis
    input_colors = set(input_grid.flatten())
    output_colors = set(output_grid.flatten())

    trans['color_change'] = {
        'input_colors': sorted(input_colors),
        'output_colors': sorted(output_colors),
        'num_input_colors': len(input_colors),
        'num_output_colors': len(output_colors),
        'new_colors': sorted(output_colors - input_colors),
        'removed_colors': sorted(input_colors - output_colors)
    }

    # If same size, analyze pixel-level changes
    if input_grid.shape == output_grid.shape:
        trans['pixel_changes'] = analyze_pixel_changes(input_grid, output_grid)

    # Structural analysis
    trans['structure'] = analyze_structure(input_grid, output_grid)

    return trans


def analyze_pixel_changes(input_grid: np.ndarray, output_grid: np.ndarray) -> dict:
    """Analyze pixel-level changes."""
    changed_mask = (input_grid != output_grid)
    num_changed = np.sum(changed_mask)
    total_pixels = input_grid.size

    changes = {
        'num_changed': int(num_changed),
        'pct_changed': float(num_changed / total_pixels),
        'all_changed': num_changed == total_pixels,
        'none_changed': num_changed == 0
    }

    # Analyze change patterns
    if 0 < num_changed < total_pixels:
        # Partial change - what's the pattern?
        changes['change_pattern'] = analyze_change_pattern(input_grid, output_grid, changed_mask)

    return changes


def analyze_change_pattern(input_grid: np.ndarray, output_grid: np.ndarray,
                           changed_mask: np.ndarray) -> str:
    """Identify pattern in what changed."""
    # Check if changes are localized
    changed_positions = np.argwhere(changed_mask)

    if len(changed_positions) == 0:
        return 'none'

    # Check if changes form connected regions
    from scipy import ndimage
    labeled, num_features = ndimage.label(changed_mask)

    if num_features == 1:
        return 'single_region'
    elif num_features > 1:
        return f'multiple_regions_{num_features}'

    return 'scattered'


def analyze_structure(input_grid: np.ndarray, output_grid: np.ndarray) -> dict:
    """Analyze structural properties."""
    struct = {}

    # Object detection (connected components)
    from scipy import ndimage

    for name, grid in [('input', input_grid), ('output', output_grid)]:
        # Count objects (non-zero connected components)
        binary = (grid != 0).astype(int)
        labeled, num_objects = ndimage.label(binary)

        struct[f'{name}_num_objects'] = num_objects

        # Analyze object properties
        if num_objects > 0:
            object_sizes = []
            for obj_id in range(1, num_objects + 1):
                obj_mask = (labeled == obj_id)
                object_sizes.append(np.sum(obj_mask))

            struct[f'{name}_object_sizes'] = object_sizes
            struct[f'{name}_avg_object_size'] = float(np.mean(object_sizes))

    # Symmetry analysis
    struct['input_symmetry'] = check_symmetry(input_grid)
    struct['output_symmetry'] = check_symmetry(output_grid)

    return struct


def check_symmetry(grid: np.ndarray) -> dict:
    """Check for symmetry in grid."""
    sym = {}

    # Horizontal symmetry
    sym['horizontal'] = np.array_equal(grid, np.flipud(grid))

    # Vertical symmetry
    sym['vertical'] = np.array_equal(grid, np.fliplr(grid))

    # Diagonal symmetry (if square)
    if grid.shape[0] == grid.shape[1]:
        sym['diagonal'] = np.array_equal(grid, grid.T)

    return sym


def find_common_patterns(transformations: list) -> dict:
    """Find patterns common across all transformations."""
    common = {}

    if not transformations:
        return common

    # Check size consistency
    same_size_all = all(t['size_change']['same_size'] for t in transformations)
    common['consistent_size'] = same_size_all

    # Check color pattern consistency
    all_add_colors = all(len(t['color_change']['new_colors']) > 0 for t in transformations)
    all_remove_colors = all(len(t['color_change']['removed_colors']) > 0 for t in transformations)

    common['adds_colors'] = all_add_colors
    common['removes_colors'] = all_remove_colors

    # Check object count changes
    if all('structure' in t for t in transformations):
        input_objs = [t['structure'].get('input_num_objects', 0) for t in transformations]
        output_objs = [t['structure'].get('output_num_objects', 0) for t in transformations]

        # Do all examples increase/decrease object count?
        all_increase = all(out > inp for inp, out in zip(input_objs, output_objs))
        all_decrease = all(out < inp for inp, out in zip(input_objs, output_objs))

        common['object_count_increase'] = all_increase
        common['object_count_decrease'] = all_decrease

    return common


def classify_task_type(patterns: dict) -> list:
    """
    Classify what type of task this is based on patterns.

    Returns list of likely task types.
    """
    types = []
    common = patterns['common_patterns']

    # Check for object manipulation
    if common.get('object_count_increase'):
        types.append('object_duplication')
    elif common.get('object_count_decrease'):
        types.append('object_merging')

    # Check for color manipulation
    if common.get('adds_colors'):
        types.append('color_generation')
    elif common.get('removes_colors'):
        types.append('color_filtering')

    # Check transformations
    if patterns['transformations']:
        first_trans = patterns['transformations'][0]

        # Size changes
        if not common.get('consistent_size'):
            types.append('size_change')

        # Structural changes
        if first_trans.get('structure'):
            struct = first_trans['structure']
            if struct.get('output_symmetry', {}).get('horizontal'):
                types.append('symmetrization')

    # Default
    if not types:
        types.append('unknown')

    return types


def infer_missing_operations(task_types: list) -> list:
    """
    Infer what operations might be needed based on task types.

    Returns list of operation suggestions.
    """
    suggestions = []

    for task_type in task_types:
        if task_type == 'object_duplication':
            suggestions.extend([
                'replicate_objects',
                'tile_by_count',
                'reflect_objects'
            ])
        elif task_type == 'object_merging':
            suggestions.extend([
                'merge_adjacent',
                'group_by_property',
                'combine_overlapping'
            ])
        elif task_type == 'color_generation':
            suggestions.extend([
                'interpolate_colors',
                'apply_pattern_colors',
                'color_by_position'
            ])
        elif task_type == 'color_filtering':
            suggestions.extend([
                'extract_color',
                'filter_by_color',
                'isolate_color'
            ])
        elif task_type == 'size_change':
            suggestions.extend([
                'expand_to_size',
                'compress_to_fit',
                'crop_to_content'
            ])
        elif task_type == 'symmetrization':
            suggestions.extend([
                'make_symmetric',
                'mirror_pattern',
                'complete_symmetry'
            ])

    return list(set(suggestions))  # Remove duplicates


def analyze_all_failed_tasks():
    """
    Analyze all 45 unsolved tasks from v0.95.
    """
    print("=" * 80)
    print("🔍 Analyzing Failed Tasks to Identify Missing Operations")
    print("=" * 80)
    print()

    # Load v0.95 results to get unsolved tasks
    results_file = 'arc_v095_final_50tasks_evaluation.json'

    if not Path(results_file).exists():
        print(f"❌ Results file not found: {results_file}")
        print("Using default 50 evaluation tasks instead...")

        # Get first 50 evaluation tasks
        eval_dir = Path('arc_agi_2/data/evaluation')
        all_tasks = sorted([f.stem for f in eval_dir.glob('*.json')])[:50]
        unsolved = all_tasks  # Assume all unsolved for now
    else:
        with open(results_file, 'r') as f:
            results = json.load(f)

        # Get unsolved tasks (fitness < 0.95)
        unsolved = [
            r['task_id'] for r in results['results']
            if r['fitness'] < 0.95
        ]

    print(f"Analyzing {len(unsolved)} unsolved tasks...")
    print()

    # Analyze each task
    all_patterns = []
    all_types = []
    all_suggestions = []

    for i, task_id in enumerate(unsolved, 1):
        print(f"[{i}/{len(unsolved)}] {task_id}")

        try:
            # Load task
            task_data = load_task(task_id)

            # Analyze patterns
            patterns = analyze_task_patterns(task_id, task_data)

            # Classify task type
            task_types = classify_task_type(patterns)

            # Infer missing operations
            suggestions = infer_missing_operations(task_types)

            # Store
            patterns['task_types'] = task_types
            patterns['operation_suggestions'] = suggestions
            all_patterns.append(patterns)
            all_types.extend(task_types)
            all_suggestions.extend(suggestions)

            print(f"  Types: {', '.join(task_types)}")
            print(f"  Suggestions: {', '.join(suggestions[:3])}...")
            print()

        except Exception as e:
            print(f"  ❌ Error: {e}")
            print()

    # Aggregate results
    print("=" * 80)
    print("📊 AGGREGATED ANALYSIS")
    print("=" * 80)
    print()

    # Most common task types
    type_counts = Counter(all_types)
    print("Most Common Task Types:")
    for task_type, count in type_counts.most_common(10):
        print(f"  {task_type:30s} {count:3d} tasks ({count/len(unsolved)*100:.1f}%)")
    print()

    # Most suggested operations
    suggestion_counts = Counter(all_suggestions)
    print("Most Suggested Operations:")
    for operation, count in suggestion_counts.most_common(20):
        print(f"  {operation:30s} {count:3d} tasks ({count/len(unsolved)*100:.1f}%)")
    print()

    # Save detailed results
    output_data = {
        'num_tasks_analyzed': len(unsolved),
        'task_patterns': all_patterns,
        'task_type_counts': dict(type_counts),
        'operation_suggestions': dict(suggestion_counts),
        'priority_operations': [op for op, _ in suggestion_counts.most_common(30)]
    }

    output_file = 'failed_tasks_analysis.json'
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"💾 Detailed analysis saved: {output_file}")
    print()

    # High-level summary
    print("=" * 80)
    print("🎯 PRIORITY OPERATIONS TO IMPLEMENT")
    print("=" * 80)
    print()

    priority_ops = [op for op, _ in suggestion_counts.most_common(30)]

    # Group by category
    categories = {
        'Object Operations': [],
        'Color Operations': [],
        'Pattern Operations': [],
        'Size Operations': [],
        'Structural Operations': []
    }

    for op in priority_ops:
        if any(word in op for word in ['object', 'merge', 'group', 'combine']):
            categories['Object Operations'].append(op)
        elif any(word in op for word in ['color', 'interpolate']):
            categories['Color Operations'].append(op)
        elif any(word in op for word in ['pattern', 'tile', 'reflect', 'replicate']):
            categories['Pattern Operations'].append(op)
        elif any(word in op for word in ['size', 'expand', 'compress', 'crop']):
            categories['Size Operations'].append(op)
        elif any(word in op for word in ['symmetric', 'mirror', 'complete']):
            categories['Structural Operations'].append(op)

    for category, ops in categories.items():
        if ops:
            print(f"{category}:")
            for op in ops[:5]:  # Top 5 per category
                count = suggestion_counts[op]
                print(f"  - {op:30s} ({count} tasks)")
            print()

    return output_data


if __name__ == '__main__':
    analyze_all_failed_tasks()
    print()
    print("=" * 80)
    print("✅ Analysis complete!")
    print("=" * 80)
