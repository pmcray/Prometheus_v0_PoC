#!/usr/bin/env python3
"""
Proof-of-Concept: Targeted Primitive Selection for TRM Phase 3

Demonstrates pixel-level difference analysis and targeted primitive selection
on 1-2 high-fitness tasks that are close to perfect (98%+).

Goal: Show that analyzing failure patterns can select focused primitives
that push tasks from 98% → 100%.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from prometheus_arc_fuzzy_fitness import PrometheusARCFuzzyFitness, PrimitiveOperation

# Test on 2 best high-fitness tasks
TEST_TASKS = [
    "0b17323b",  # 96.89% baseline → 98.89% Phase 2 (best result)
    "15113be4",  # 96.11% baseline → 98.11% Phase 2 (2nd best)
]

def analyze_pixel_differences(predicted: np.ndarray, expected: np.ndarray) -> Dict:
    """
    Analyze pixel-level differences to determine failure type.

    Returns:
        - total_pixels: total number of pixels
        - wrong_pixels: number of incorrect pixels
        - error_rate: percentage of wrong pixels
        - failure_type: 'single_pixel', 'boundary', 'symmetry', or 'scaling'
        - error_locations: (y, x) coordinates of errors
    """
    if predicted.shape != expected.shape:
        return {
            'total_pixels': expected.size,
            'wrong_pixels': expected.size,
            'error_rate': 1.0,
            'failure_type': 'scaling',
            'error_locations': []
        }

    # Find all pixel differences
    diff_mask = predicted != expected
    wrong_pixels = np.sum(diff_mask)
    total_pixels = expected.size
    error_rate = wrong_pixels / total_pixels if total_pixels > 0 else 0.0

    # Get error locations
    error_locs = list(zip(*np.where(diff_mask)))

    # Classify failure type
    if error_rate < 0.05:  # < 5% error
        failure_type = 'single_pixel'
    else:
        # Check if errors are on boundaries
        h, w = expected.shape
        boundary_errors = sum(1 for y, x in error_locs
                             if y == 0 or y == h-1 or x == 0 or x == w-1)
        boundary_ratio = boundary_errors / wrong_pixels if wrong_pixels > 0 else 0

        if boundary_ratio > 0.5:
            failure_type = 'boundary'
        else:
            # Check for symmetry patterns (errors clustered on one side)
            if len(error_locs) > 0:
                y_coords = [y for y, x in error_locs]
                left_errors = sum(1 for y, x in error_locs if x < w // 2)
                right_errors = sum(1 for y, x in error_locs if x >= w // 2)
                if abs(left_errors - right_errors) / wrong_pixels > 0.6:
                    failure_type = 'symmetry'
                else:
                    failure_type = 'scaling'
            else:
                failure_type = 'single_pixel'

    return {
        'total_pixels': total_pixels,
        'wrong_pixels': wrong_pixels,
        'error_rate': error_rate,
        'failure_type': failure_type,
        'error_locations': error_locs[:10]  # Show first 10
    }

def select_targeted_primitives(failure_analysis: Dict,
                               all_primitives: List[PrimitiveOperation]) -> List[str]:
    """
    Select a focused set of primitives based on failure type.

    Phase 2 problem: Evolves from all 25 primitives → gets stuck on ['identity']
    Phase 3 solution: Restrict to 3-5 targeted primitives based on failure pattern
    """
    failure_type = failure_analysis['failure_type']

    if failure_type == 'single_pixel':
        # Micro-adjustments for <5% error
        targeted = ['identity', 'fill_zeros', 'remove_bg', 'fill_ones']
    elif failure_type == 'boundary':
        # Edge/border operations
        targeted = ['border', 'extend_edges', 'crop', 'pad_1', 'trim']
    elif failure_type == 'symmetry':
        # Reflection/symmetry operations
        targeted = ['flip_h', 'flip_v', 'transpose', 'diag_flip', 'rotate_90']
    elif failure_type == 'scaling':
        # Size operations
        targeted = ['scale_2x', 'scale_3x', 'tile_2x2', 'downsample']
    else:
        # Fallback to Phase 2 (all primitives)
        targeted = [p.name for p in all_primitives]

    return targeted

def evaluate_pattern(pattern: List[str], examples: List[Dict],
                    primitives: List[PrimitiveOperation]) -> float:
    """Evaluate a pattern on training examples using fuzzy fitness."""
    from prometheus_arc_fuzzy_fitness import CompositePattern

    # Build pattern from operation names
    ops = []
    for op_name in pattern:
        matching = [p for p in primitives if p.name == op_name]
        if matching:
            ops.append(matching[0])

    if not ops:
        return 0.0

    composite = CompositePattern(operations=ops, generation=0)

    # Evaluate on all examples
    total_fitness = 0.0
    for ex in examples:
        input_grid = np.array(ex['input'])
        expected = np.array(ex['output'])

        try:
            output = composite.apply(input_grid)
            if output is None:
                continue

            # Fuzzy fitness
            if output.shape != expected.shape:
                fitness = 0.0
            else:
                correct = np.sum(output == expected)
                total = expected.size
                fitness = correct / total if total > 0 else 0.0

            total_fitness += fitness
        except:
            continue

    return total_fitness / len(examples) if examples else 0.0

def main():
    print("=" * 80)
    print("🔬 Targeted Primitive Selection - Proof of Concept")
    print("=" * 80)
    print(f"Tasks: {len(TEST_TASKS)}")
    print(f"Goal: Demonstrate failure analysis → targeted primitives")
    print("=" * 80)
    print()

    # Load tasks
    arc_data = {}
    for task_id in TEST_TASKS:
        for split in ['training', 'evaluation']:
            task_file = Path(f"arc_agi_2/data/{split}/{task_id}.json")
            if task_file.exists():
                with open(task_file, 'r') as f:
                    arc_data[task_id] = json.load(f)
                break

    print(f"Loaded {len(arc_data)}/{len(TEST_TASKS)} tasks\n")

    # Initialize solver to get primitives
    solver = PrometheusARCFuzzyFitness(
        population_size=50,
        max_pattern_length=5
    )
    all_primitives = solver.primitives

    # Analyze each task
    for task_id, task_data in arc_data.items():
        print(f"\n{'='*80}")
        print(f"📊 Task: {task_id}")
        print(f"{'='*80}")

        train_examples = task_data['train']

        # Step 1: Get Phase 2 baseline pattern (from previous results)
        # For this POC, we'll use a simple pattern that gets ~98% fitness
        baseline_patterns = {
            "0b17323b": ['identity', 'identity'],
            "15113be4": ['identity', 'identity']
        }
        baseline_pattern = baseline_patterns.get(task_id, ['identity'])

        # Evaluate baseline
        baseline_fitness = evaluate_pattern(baseline_pattern, train_examples, all_primitives)
        print(f"\n1️⃣ Phase 2 Baseline:")
        print(f"   Pattern: {baseline_pattern}")
        print(f"   Fitness: {baseline_fitness:.4f} ({baseline_fitness*100:.2f}%)")

        # Step 2: Analyze pixel-level failures
        print(f"\n2️⃣ Failure Analysis:")

        # Get predictions from baseline pattern
        from prometheus_arc_fuzzy_fitness import CompositePattern
        ops = []
        for op_name in baseline_pattern:
            matching = [p for p in all_primitives if p.name == op_name]
            if matching:
                ops.append(matching[0])

        baseline_composite = CompositePattern(operations=ops, generation=0)

        # Analyze failures on each training example
        all_failures = []
        for i, ex in enumerate(train_examples):
            input_grid = np.array(ex['input'])
            expected = np.array(ex['output'])

            try:
                predicted = baseline_composite.apply(input_grid)
                if predicted is not None:
                    failure = analyze_pixel_differences(predicted, expected)
                    failure['example_idx'] = i
                    all_failures.append(failure)

                    print(f"   Example {i+1}: {failure['wrong_pixels']}/{failure['total_pixels']} wrong pixels "
                          f"({failure['error_rate']*100:.2f}%) - Type: {failure['failure_type']}")
            except Exception as e:
                print(f"   Example {i+1}: Error - {e}")

        # Step 3: Select targeted primitives
        if all_failures:
            # Use most common failure type
            failure_types = [f['failure_type'] for f in all_failures]
            most_common = max(set(failure_types), key=failure_types.count)
            representative_failure = {'failure_type': most_common}

            targeted_prims = select_targeted_primitives(representative_failure, all_primitives)

            print(f"\n3️⃣ Targeted Primitive Selection:")
            print(f"   Failure type: {most_common}")
            print(f"   Phase 2: All 25 primitives → stuck on ['identity']")
            print(f"   Phase 3: {len(targeted_prims)} targeted primitives → {targeted_prims}")
            print(f"   Reduction: {len(all_primitives)} → {len(targeted_prims)} "
                  f"({100 - len(targeted_prims)/len(all_primitives)*100:.0f}% reduction)")

            # Step 4: Test a few targeted patterns
            print(f"\n4️⃣ Testing Targeted Patterns:")

            # Try some simple patterns with targeted primitives
            test_patterns = [
                [targeted_prims[0]],
                [targeted_prims[0], targeted_prims[0]],
                baseline_pattern + [targeted_prims[0]],
                [targeted_prims[0]] + baseline_pattern,
            ]

            if len(targeted_prims) > 1:
                test_patterns.extend([
                    [targeted_prims[1]],
                    [targeted_prims[0], targeted_prims[1]],
                    baseline_pattern + [targeted_prims[1]],
                ])

            best_fitness = baseline_fitness
            best_pattern = baseline_pattern

            for pattern in test_patterns:
                fitness = evaluate_pattern(pattern, train_examples, all_primitives)
                improvement = fitness - baseline_fitness
                status = "✓" if fitness > baseline_fitness else " "

                if fitness > best_fitness:
                    best_fitness = fitness
                    best_pattern = pattern

                print(f"   {status} {pattern}: {fitness:.4f} ({fitness*100:.2f}%) "
                      f"[{improvement:+.4f}]")

            # Summary
            print(f"\n5️⃣ Result:")
            if best_fitness > baseline_fitness:
                print(f"   ✅ Improvement found!")
                print(f"   Best pattern: {best_pattern}")
                print(f"   {baseline_fitness:.4f} → {best_fitness:.4f} "
                      f"(+{(best_fitness-baseline_fitness)*100:.2f}%)")
                if best_fitness >= 1.0:
                    print(f"   🎯 SOLVED! Reached 100%!")
            else:
                print(f"   ⚠️  No improvement in this quick test")
                print(f"   (Full evolution with targeted primitives may still improve)")

        print()

    print("=" * 80)
    print("📝 Proof-of-Concept Summary")
    print("=" * 80)
    print()
    print("✅ Demonstrated:")
    print("   1. Pixel-level failure analysis (single_pixel, boundary, symmetry, scaling)")
    print("   2. Targeted primitive selection (25 → 4-5 primitives)")
    print("   3. Quick pattern testing with targeted primitives")
    print()
    print("📊 Key Insight:")
    print("   Phase 2: Broad evolution (all 25 primitives) → stuck on ['identity']")
    print("   Phase 3: Targeted evolution (4-5 primitives) → focused on specific fixes")
    print()
    print("🎯 Next Step:")
    print("   Implement full Phase 3 v0.87 with:")
    print("   - Failure analysis in refinement loop")
    print("   - Restricted primitive pool for correction synthesis")
    print("   - Test on all 11 high-fitness tasks")
    print()

if __name__ == '__main__':
    main()
