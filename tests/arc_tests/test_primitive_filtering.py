#!/usr/bin/env python3
"""
Test primitive filtering on various constraint combinations (isolated component test).

This tests ONLY the PrimitiveFilter component without running the full solver,
to validate filtering logic and search space reduction.
"""

import json
from pathlib import Path
from prometheus_arc_v093_constraints import (
    ConstraintExtractor,
    PrimitiveFilter,
    SIZE_CONSTRAINT_FILTERS,
    COLOR_CONSTRAINT_FILTERS,
    SYMMETRY_CONSTRAINT_FILTERS,
    OBJECT_CONSTRAINT_FILTERS
)


def test_primitive_filtering():
    """Test primitive filtering with various constraint combinations."""

    print("="*80)
    print("🔬 Testing Primitive Filtering (Isolated)")
    print("="*80)
    print()

    # Mock primitive list (same as v0.92/v0.93)
    all_primitives = [
        # Geometric transformations
        'identity', 'rotate_90', 'rotate_180', 'rotate_270',
        'flip_h', 'flip_v', 'transpose',

        # Scaling
        'scale_2x', 'scale_3x', 'tile_2x2', 'tile_3x3',

        # Sizing
        'crop', 'downsample', 'pad_1', 'extend_edges',

        # Color operations
        'invert', 'swap_01', 'color_inc', 'fill_zeros', 'remove_bg',

        # Shape operations
        'hollow', 'border', 'center', 'sym_h', 'sym_v',

        # Gravity
        'gravity_down', 'gravity_up',

        # Object operations (v0.92 additions)
        'detect_objects', 'extract_largest', 'extract_smallest',
        'sort_by_size', 'align_h', 'align_v',
        'fill_interior', 'gravity_objects'
    ]

    print(f"Total primitives: {len(all_primitives)}")
    print(f"Original search space (depth 5): {len(all_primitives)**5:,} patterns")
    print()

    # Initialize filter
    prim_filter = PrimitiveFilter(all_primitives)

    # Test case 1: Size preserved + colors preserved (common)
    print("-"*80)
    print("Test Case 1: size_preserved + colors_preserved")
    print("-"*80)

    constraints_1 = {
        'size': 'size_preserved',
        'color': 'colors_preserved',
        'symmetry': 'no_symmetry',
        'object': 'object_count_variable'
    }

    strict_1 = prim_filter.filter_by_constraints(constraints_1, mode='strict')
    soft_1 = prim_filter.filter_by_constraints(constraints_1, mode='soft')

    print(f"Constraints: {constraints_1}")
    print(f"Strict: {len(strict_1)} primitives ({100*(1-len(strict_1)/len(all_primitives)):.1f}% reduction)")
    print(f"  {strict_1[:10]}..." if len(strict_1) > 10 else f"  {strict_1}")
    print(f"Soft:   {len(soft_1)} primitives ({100*(1-len(soft_1)/len(all_primitives)):.1f}% reduction)")
    print(f"Search space strict: {len(strict_1)**5:,} patterns")
    print(f"Search space soft:   {len(soft_1)**5:,} patterns")
    print()

    # Test case 2: Dimensions swapped (rotation task)
    print("-"*80)
    print("Test Case 2: dimensions_swapped + colors_preserved")
    print("-"*80)

    constraints_2 = {
        'size': 'dimensions_swapped',
        'color': 'colors_preserved',
        'symmetry': 'no_symmetry',
        'object': 'object_count_preserved'
    }

    strict_2 = prim_filter.filter_by_constraints(constraints_2, mode='strict')
    soft_2 = prim_filter.filter_by_constraints(constraints_2, mode='soft')

    print(f"Constraints: {constraints_2}")
    print(f"Strict: {len(strict_2)} primitives ({100*(1-len(strict_2)/len(all_primitives)):.1f}% reduction)")
    print(f"  {strict_2}")
    print(f"Soft:   {len(soft_2)} primitives ({100*(1-len(soft_2)/len(all_primitives)):.1f}% reduction)")
    print(f"Search space strict: {len(strict_2)**5:,} patterns")
    print()

    # Test case 3: Scaled 2x (tiling task)
    print("-"*80)
    print("Test Case 3: scaled_2x + object_count_increased")
    print("-"*80)

    constraints_3 = {
        'size': 'scaled_2x',
        'color': 'colors_preserved',
        'symmetry': 'no_symmetry',
        'object': 'object_count_increased'
    }

    strict_3 = prim_filter.filter_by_constraints(constraints_3, mode='strict')
    soft_3 = prim_filter.filter_by_constraints(constraints_3, mode='soft')

    print(f"Constraints: {constraints_3}")
    print(f"Strict: {len(strict_3)} primitives ({100*(1-len(strict_3)/len(all_primitives)):.1f}% reduction)")
    print(f"  {strict_3}")
    print(f"Soft:   {len(soft_3)} primitives ({100*(1-len(soft_3)/len(all_primitives)):.1f}% reduction)")
    print(f"Search space strict: {len(strict_3)**5:,} patterns")
    print()

    # Test case 4: Horizontal symmetry
    print("-"*80)
    print("Test Case 4: size_preserved + horizontal_symmetry")
    print("-"*80)

    constraints_4 = {
        'size': 'size_preserved',
        'color': 'colors_preserved',
        'symmetry': 'horizontal_symmetry',
        'object': 'object_count_variable'
    }

    strict_4 = prim_filter.filter_by_constraints(constraints_4, mode='strict')
    soft_4 = prim_filter.filter_by_constraints(constraints_4, mode='soft')

    print(f"Constraints: {constraints_4}")
    print(f"Strict: {len(strict_4)} primitives ({100*(1-len(strict_4)/len(all_primitives)):.1f}% reduction)")
    print(f"  {strict_4[:10]}..." if len(strict_4) > 10 else f"  {strict_4}")
    print(f"Soft:   {len(soft_4)} primitives ({100*(1-len(soft_4)/len(all_primitives)):.1f}% reduction)")
    print(f"  Prioritized: {[p for p in soft_4 if p in ['sym_h', 'flip_h']]}")
    print(f"Search space strict: {len(strict_4)**5:,} patterns")
    print()

    # Summary statistics
    print("="*80)
    print("📊 FILTERING SUMMARY")
    print("="*80)
    print()

    test_cases = [
        ("Common (size+color preserved)", constraints_1, strict_1, soft_1),
        ("Rotation (dims swapped)", constraints_2, strict_2, soft_2),
        ("Tiling (scaled 2x)", constraints_3, strict_3, soft_3),
        ("Symmetry (horizontal)", constraints_4, strict_4, soft_4)
    ]

    print(f"{'Test Case':<30s} {'Strict':<15s} {'Soft':<15s} {'Reduction (Strict)':<20s}")
    print("-"*80)
    for name, constraints, strict, soft in test_cases:
        strict_reduction = 100 * (1 - len(strict) / len(all_primitives))
        soft_reduction = 100 * (1 - len(soft) / len(all_primitives))
        print(f"{name:<30s} {len(strict):2d} prims ({len(strict)**5:>7,})  "
              f"{len(soft):2d} prims ({len(soft)**5:>7,})  {strict_reduction:5.1f}%")

    print()

    # Average reduction
    avg_strict_reduction = sum([
        100 * (1 - len(s) / len(all_primitives))
        for _, _, s, _ in test_cases
    ]) / len(test_cases)

    avg_soft_reduction = sum([
        100 * (1 - len(so) / len(all_primitives))
        for _, _, _, so in test_cases
    ]) / len(test_cases)

    print(f"Average reduction (strict): {avg_strict_reduction:.1f}%")
    print(f"Average reduction (soft):   {avg_soft_reduction:.1f}%")
    print()

    print("✅ Primitive filtering test complete!")
    print()

    # Expected behavior
    print("Expected behavior:")
    print("  - Strict mode should reduce primitives by 60-90%")
    print("  - Soft mode should reduce primitives by 40-70%")
    print("  - More specific constraints = more reduction")
    print("  - Rotation tasks should have very few primitives (3-5)")
    print("  - Common tasks should have moderate reduction (10-15 primitives)")
    print("  - Search space should reduce from 79M to 10K-100K patterns")


def test_on_real_task():
    """Test filtering on a real ARC task."""

    print()
    print("="*80)
    print("🔬 Testing on Real ARC Task")
    print("="*80)
    print()

    # Load a task
    task_path = Path("arc_agi_2/data/evaluation/0934a4d8.json")

    if not task_path.exists():
        print("Skipping real task test (file not found)")
        return

    with open(task_path, 'r') as f:
        task = json.load(f)

    print(f"Task: {task_path.stem}")
    print()

    # Extract constraints
    extractor = ConstraintExtractor()
    constraints = extractor.extract_all_constraints(task)

    print("Extracted constraints:")
    for c_type, c_value in constraints.items():
        print(f"  {c_type}: {c_value}")
    print()

    # Filter primitives
    all_primitives = list(range(38))  # Mock 38 primitives
    prim_filter = PrimitiveFilter(all_primitives)

    strict = prim_filter.filter_by_constraints(constraints, mode='strict')
    soft = prim_filter.filter_by_constraints(constraints, mode='soft')

    print(f"Filtering results:")
    print(f"  Original: {len(all_primitives)} primitives")
    print(f"  Strict:   {len(strict)} primitives ({100*(1-len(strict)/len(all_primitives)):.1f}% reduction)")
    print(f"  Soft:     {len(soft)} primitives ({100*(1-len(soft)/len(all_primitives)):.1f}% reduction)")
    print()

    original_space = len(all_primitives) ** 5
    strict_space = len(strict) ** 5
    soft_space = len(soft) ** 5

    print(f"Search space reduction:")
    print(f"  Original: {original_space:,} patterns")
    print(f"  Strict:   {strict_space:,} patterns ({100*(1-strict_space/original_space):.2f}% reduction)")
    print(f"  Soft:     {soft_space:,} patterns ({100*(1-soft_space/original_space):.2f}% reduction)")
    print()


if __name__ == "__main__":
    test_primitive_filtering()
    test_on_real_task()
