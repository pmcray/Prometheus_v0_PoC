#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script: Print ALL depth-1 program fitnesses for task 3e6067c3.

This will show us if crop is actually getting 0.959 or if it's also getting 0.949.
"""

import json
import numpy as np
from arc_program import ARCProgram
from arc_parametric_operations import (
    build_operation_map,
    get_parameter_candidates,
    PARAMETRIC_OPERATIONS
)


def compute_similarity(predicted: np.ndarray, expected: np.ndarray) -> float:
    """Compute similarity between predicted and expected grids."""
    # Perfect match
    if predicted.shape == expected.shape and np.array_equal(predicted, expected):
        return 1.0

    # Size mismatch penalty
    if predicted.shape != expected.shape:
        min_h = min(predicted.shape[0], expected.shape[0])
        min_w = min(predicted.shape[1], expected.shape[1])

        if min_h == 0 or min_w == 0:
            return 0.0

        pred_crop = predicted[:min_h, :min_w]
        exp_crop = expected[:min_h, :min_w]

        matching_pixels = np.sum(pred_crop == exp_crop)
        total_pixels = exp_crop.size

        similarity = (matching_pixels / total_pixels) * 0.5
        return similarity

    # Same size: pure pixel similarity
    matching_pixels = np.sum(predicted == expected)
    total_pixels = expected.size

    return matching_pixels / total_pixels if total_pixels > 0 else 0.0


def evaluate_program(program: ARCProgram, train_examples, operation_map):
    """Evaluate program on training examples."""
    if not train_examples or len(program) == 0:
        return 0.0

    total_similarity = 0.0

    for example in train_examples:
        try:
            if isinstance(example, dict):
                input_grid = np.array(example['input'])
                expected_output = np.array(example['output'])
            else:
                input_grid, expected_output = example

            predicted = program.execute(input_grid, operation_map)
            similarity = compute_similarity(predicted, expected_output)
            total_similarity += similarity
        except Exception as e:
            total_similarity += 0.0

    # Average similarity across examples
    fitness = total_similarity / len(train_examples)

    # Small complexity penalty
    complexity_penalty = 0.01 * len(program)

    return max(0.0, fitness - complexity_penalty)


def debug_depth1():
    """Debug depth-1 programs for task 3e6067c3."""

    print("=" * 80)
    print("🔍 Debugging Depth-1 Programs for Task 3e6067c3")
    print("=" * 80)
    print()

    # Load task
    task_id = '3e6067c3'
    with open(f'arc_agi_2/data/evaluation/{task_id}.json', 'r') as f:
        task_data = json.load(f)

    task = {'train': task_data['train']}
    operation_map = build_operation_map()

    # Get all operations
    all_ops = list(PARAMETRIC_OPERATIONS.keys())
    print(f"Total operations: {len(all_ops)}")
    print()

    # Test each operation with up to 3 parameter sets
    results = []

    for op_name in all_ops:
        # Get parameter candidates
        param_sets = get_parameter_candidates(op_name, task, constraints={})[:3]

        for params in param_sets:
            # Create program
            program = ARCProgram([])
            program.add_operation(op_name, params)

            # Evaluate
            try:
                fitness = evaluate_program(program, task['train'], operation_map)
                results.append((fitness, op_name, params, program.to_pattern()[0]))
            except Exception as e:
                # Failed to execute
                pass

    # Sort by fitness
    results.sort(reverse=True, key=lambda x: x[0])

    print("Top 20 depth-1 programs:")
    print("-" * 80)
    print(f"{'Fitness':<10} {'Operation':<20} {'Program':<40}")
    print("-" * 80)

    for i, (fitness, op_name, params, prog_str) in enumerate(results[:20]):
        print(f"{fitness:.6f}   {op_name:<20} {prog_str[:40]}")

    print()
    print("-" * 80)

    # Check specifically for crop
    crop_results = [r for r in results if r[1] == 'crop']
    if crop_results:
        print()
        print("Crop programs found:")
        for fitness, op_name, params, prog_str in crop_results:
            print(f"  {fitness:.6f}  {prog_str}")
    else:
        print()
        print("⚠️  NO CROP PROGRAMS FOUND!")

    # Check for map_color
    map_color_results = [r for r in results if r[1] == 'map_color']
    if map_color_results:
        print()
        print("Map_color programs found:")
        for fitness, op_name, params, prog_str in map_color_results[:5]:
            print(f"  {fitness:.6f}  {prog_str}")

    print()
    print("=" * 80)
    print("🎯 ANALYSIS")
    print("=" * 80)

    if crop_results:
        best_crop = crop_results[0]
        print(f"Best crop fitness: {best_crop[0]:.6f}")
    else:
        print("Best crop fitness: N/A (not found)")

    if map_color_results:
        best_map = map_color_results[0]
        print(f"Best map_color fitness: {best_map[0]:.6f}")

    print()
    print("Expected from v0.95:")
    print("  crop(mode=content): 0.959")
    print()

    if crop_results and crop_results[0][0] > 0.95:
        print("✅ Crop IS working and has high fitness!")
        print("   The problem must be in beam selection, not evaluation.")
    elif crop_results:
        print(f"⚠️  Crop found but fitness is {crop_results[0][0]:.3f}, not 0.959")
        print("   Either parameter generation is wrong or evaluation changed.")
    else:
        print("❌ Crop NOT being evaluated at all!")
        print("   Parameter generation must be failing.")

    print()


if __name__ == '__main__':
    debug_depth1()
