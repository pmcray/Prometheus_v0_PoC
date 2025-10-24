#!/usr/bin/env python3
"""
Test constraint extraction on ARC tasks (isolated component test).

This tests ONLY the ConstraintExtractor component without running
the full solver, to validate constraint extraction logic.
"""

import json
import numpy as np
from pathlib import Path
from prometheus_arc_v093_constraints import ConstraintExtractor


def test_constraint_extraction(num_tasks=10):
    """Test constraint extraction on N tasks."""

    print("="*80)
    print("🔬 Testing Constraint Extraction (Isolated)")
    print("="*80)
    print()

    # Load tasks
    task_dir = Path("arc_agi_2/data/evaluation")
    if not task_dir.exists():
        print(f"Error: {task_dir} not found")
        return

    task_files = sorted(task_dir.glob("*.json"))[:num_tasks]

    if not task_files:
        print("Error: No task files found")
        return

    print(f"Testing on {len(task_files)} tasks")
    print()

    # Initialize extractor
    extractor = ConstraintExtractor()

    # Track constraint distribution
    from collections import Counter
    size_constraints = []
    color_constraints = []
    symmetry_constraints = []
    object_constraints = []

    # Extract constraints for each task
    for i, task_file in enumerate(task_files, 1):
        with open(task_file, 'r') as f:
            task_data = json.load(f)

        task_id = task_file.stem

        print(f"[{i}/{len(task_files)}] Task {task_id}")

        try:
            # Extract constraints
            constraints = extractor.extract_all_constraints(task_data)

            # Print results
            print(f"  Size:      {constraints['size']}")
            print(f"  Color:     {constraints['color']}")
            print(f"  Symmetry:  {constraints['symmetry']}")
            print(f"  Object:    {constraints['object']}")
            print()

            # Track for statistics
            size_constraints.append(constraints['size'])
            color_constraints.append(constraints['color'])
            symmetry_constraints.append(constraints['symmetry'])
            object_constraints.append(constraints['object'])

        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            print()

    # Print statistics
    print("="*80)
    print("📊 CONSTRAINT DISTRIBUTION")
    print("="*80)
    print()

    print("Size Constraints:")
    for constraint, count in Counter(size_constraints).most_common():
        pct = 100 * count / len(size_constraints)
        print(f"  {constraint:25s} {count:2d} ({pct:5.1f}%)")
    print()

    print("Color Constraints:")
    for constraint, count in Counter(color_constraints).most_common():
        pct = 100 * count / len(color_constraints)
        print(f"  {constraint:25s} {count:2d} ({pct:5.1f}%)")
    print()

    print("Symmetry Constraints:")
    for constraint, count in Counter(symmetry_constraints).most_common():
        pct = 100 * count / len(symmetry_constraints)
        print(f"  {constraint:25s} {count:2d} ({pct:5.1f}%)")
    print()

    print("Object Constraints:")
    for constraint, count in Counter(object_constraints).most_common():
        pct = 100 * count / len(object_constraints)
        print(f"  {constraint:25s} {count:2d} ({pct:5.1f}%)")
    print()

    # Calculate "specificity" (non-variable constraints)
    total_constraints = len(size_constraints) * 4
    variable_count = sum([
        size_constraints.count('size_variable'),
        color_constraints.count('colors_variable'),
        symmetry_constraints.count('no_symmetry'),
        object_constraints.count('object_count_variable')
    ])

    specific_count = total_constraints - variable_count
    specificity = 100 * specific_count / total_constraints

    print(f"Constraint Specificity: {specificity:.1f}%")
    print(f"  (Non-variable constraints / total constraints)")
    print()

    print("✅ Constraint extraction test complete!")
    print()

    # Expected behavior
    print("Expected behavior:")
    print("  - Most tasks should have 'size_preserved' (common in ARC)")
    print("  - Color constraints should vary (preserved, mapped, reduced)")
    print("  - Most tasks should have 'no_symmetry' (symmetry is rare)")
    print("  - Object constraints should vary widely")
    print("  - Specificity should be 40-60% (balance of constraints)")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test constraint extraction')
    parser.add_argument('--num-tasks', type=int, default=10,
                       help='Number of tasks to test')

    args = parser.parse_args()

    test_constraint_extraction(args.num_tasks)
