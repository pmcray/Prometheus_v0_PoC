#!/usr/bin/env python3
"""
Analyze which 4 tasks we solved on evaluation set and why.
Compare to training set failures to understand generalization gap.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict

def load_evaluation_results():
    """Load evaluation results"""
    with open('arc_evolution_results/evolution_evaluation_results.json', 'r') as f:
        return json.load(f)

def load_task(task_id: str, split='evaluation'):
    """Load a task from the dataset"""
    data_dir = Path('arc_agi_official/data')
    task_dir = data_dir / split
    task_file = task_dir / f"{task_id}.json"

    with open(task_file, 'r') as f:
        return json.load(f)

def analyze_solved_tasks():
    """Analyze the 4 tasks we solved on evaluation"""
    results = load_evaluation_results()

    solved_tasks = []
    for result in results['results']:
        if result.get('fitness', 0) >= 0.99:
            solved_tasks.append(result)

    print("="*80)
    print("🎯 EVALUATION SET: Tasks Solved (4/400)")
    print("="*80)

    for i, task_result in enumerate(solved_tasks, 1):
        task_id = task_result['task_id']
        pattern = task_result['pattern']
        fitness = task_result['fitness']

        print(f"\n{i}. Task {task_id}")
        print(f"   Pattern: {pattern}")
        print(f"   Fitness: {fitness:.3f}")

        # Load and analyze task
        task = load_task(task_id)
        train_pairs = task['train']

        # Analyze complexity
        input_shapes = [np.array(pair['input']).shape for pair in train_pairs]
        output_shapes = [np.array(pair['output']).shape for pair in train_pairs]

        print(f"   Training pairs: {len(train_pairs)}")
        print(f"   Input shapes: {input_shapes}")
        print(f"   Output shapes: {output_shapes}")

        # Check if shape-preserving
        shape_preserving = all(inp == out for inp, out in zip(input_shapes, output_shapes))
        print(f"   Shape-preserving: {shape_preserving}")

        # Count colors
        all_colors = set()
        for pair in train_pairs:
            all_colors.update(np.unique(np.array(pair['input'])))
            all_colors.update(np.unique(np.array(pair['output'])))
        print(f"   Unique colors used: {len(all_colors)}")

    return solved_tasks

def compare_to_training_solved():
    """Compare evaluation solutions to training solutions"""
    print(f"\n{'='*80}")
    print("📊 COMPARISON: Evaluation vs Training Solutions")
    print("="*80)

    # Load training results
    with open('arc_evolution_results/evolution_training_results.json', 'r') as f:
        training_results = json.load(f)

    training_solved = []
    for result in training_results['results']:
        if result.get('fitness', 0) >= 0.99:
            training_solved.append(result)

    # Extract pattern types
    eval_patterns = {}
    with open('arc_evolution_results/evolution_evaluation_results.json', 'r') as f:
        eval_results = json.load(f)
        for result in eval_results['results']:
            if result.get('fitness', 0) >= 0.99:
                pattern = str(result['pattern'])
                eval_patterns[result['task_id']] = pattern

    training_patterns = {}
    for result in training_results['results']:
        if result.get('fitness', 0) >= 0.99:
            pattern = str(result['pattern'])
            training_patterns[result['task_id']] = pattern

    # Analyze pattern overlap
    from collections import Counter

    eval_pattern_counts = Counter(eval_patterns.values())
    training_pattern_counts = Counter(training_patterns.values())

    print(f"\nEvaluation patterns (4 tasks):")
    for pattern, count in eval_pattern_counts.most_common():
        print(f"   {pattern}: {count} tasks")

    print(f"\nTraining patterns (30 tasks, top 10):")
    for pattern, count in training_pattern_counts.most_common(10):
        print(f"   {pattern}: {count} tasks")

    # Check for overlap
    common_patterns = set(eval_patterns.values()) & set(training_patterns.values())
    print(f"\nPattern overlap: {len(common_patterns)} patterns used in both sets")
    for pattern in common_patterns:
        eval_count = eval_pattern_counts[pattern]
        train_count = training_pattern_counts[pattern]
        print(f"   {pattern}")
        print(f"      Eval: {eval_count} tasks, Training: {train_count} tasks")

def analyze_generalization_gap():
    """Analyze why 26/30 training solutions didn't generalize"""
    print(f"\n{'='*80}")
    print("🔍 GENERALIZATION GAP ANALYSIS")
    print("="*80)

    print(f"\nKey Statistics:")
    print(f"   Training solved: 30/400 (7.5%)")
    print(f"   Evaluation solved: 4/400 (1.0%)")
    print(f"   Generalization rate: 13.3% (4/30 solutions work on eval)")
    print(f"   Failed to generalize: 26/30 (86.7%)")

    print(f"\nPossible Causes:")
    print(f"1. Pattern Overfitting")
    print(f"   - Evolution found patterns that work on training by chance")
    print(f"   - Complex 3-5 operation chains may be memorizing specific tasks")
    print(f"   - Need simpler patterns (1-2 ops) for better generalization")

    print(f"\n2. Primitive Specificity")
    print(f"   - 38 primitives may be too training-specific")
    print(f"   - Hand-designed based on training set observations")
    print(f"   - Eval set may require different primitive types")

    print(f"\n3. No Regularization")
    print(f"   - Evolution optimizes pure training accuracy")
    print(f"   - Complexity penalty (0.01 per op) too weak")
    print(f"   - No validation set for early stopping")

    print(f"\n4. Search Space Size")
    print(f"   - 38^5 = 79M possible 5-op patterns")
    print(f"   - 38^3 = 54K possible 3-op patterns")
    print(f"   - Vast search space encourages overfitting")

    print(f"\nRecommended Fixes:")
    print(f"✓ Limit pattern length to 1-2 operations (force simpler solutions)")
    print(f"✓ Increase complexity penalty to 0.1 per operation")
    print(f"✓ Use validation split (e.g., 300 train / 100 validation)")
    print(f"✓ Test on evaluation set after each improvement")
    print(f"✓ Focus on primitives that solve eval tasks, not training tasks")

def main():
    print("\n🔬 Evaluation Set Failure Analysis")
    print("="*80)

    # Analyze what we solved
    solved_tasks = analyze_solved_tasks()

    # Compare to training
    compare_to_training_solved()

    # Analyze generalization gap
    analyze_generalization_gap()

    print(f"\n{'='*80}")
    print("💡 KEY INSIGHT")
    print("="*80)
    print("\nThe 4 tasks we solved on evaluation all use SIMPLE patterns:")
    print("  - checkerboard (single primitive)")
    print("  - scale_2x (single primitive)")
    print("  - downsample (repeated primitive)")
    print("  - fill_zeros + hollow (2-op composition)")

    print("\nComplex 3-5 operation patterns from training DON'T generalize.")
    print("This suggests we should:")
    print("  1. Favor simpler solutions (1-2 ops)")
    print("  2. Increase complexity penalty dramatically")
    print("  3. Test generalization after every change")

if __name__ == "__main__":
    main()
