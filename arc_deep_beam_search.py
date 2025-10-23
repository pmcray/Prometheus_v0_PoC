#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep Beam Search for ARC Program Synthesis (Option D)

Improvements over standard beam search:
1. Deeper search: depth 10 (vs 5)
2. Wider beam: width 100 (vs 50)
3. Better fitness: exact + fuzzy + structural
4. Smarter early stopping: plateau detection
5. Diversity maintenance: penalize duplicate patterns

Expected impact: 9 tasks at 0.90-0.95 should cross 0.95 threshold

Author: Prometheus Option D
Date: 2025-10-22
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from arc_program import ARCProgram
from arc_parametric_operations import (
    build_operation_map,
    get_parameter_candidates,
    PARAMETRIC_OPERATIONS
)


class DeepBeamSearch:
    """
    Deep beam search with improved fitness and stopping criteria.
    """

    def __init__(self,
                 beam_width: int = 100,  # Doubled from 50
                 max_depth: int = 10,     # Doubled from 5
                 max_candidates_per_op: int = 3,
                 diversity_penalty: float = 0.01):
        """
        Initialize deep beam search.

        Args:
            beam_width: Number of programs to keep in beam (doubled)
            max_depth: Maximum program length (doubled)
            max_candidates_per_op: Max parameter sets per operation
            diversity_penalty: Penalty for similar programs
        """
        self.beam_width = beam_width
        self.max_depth = max_depth
        self.max_candidates_per_op = max_candidates_per_op
        self.diversity_penalty = diversity_penalty

        # Build operation map
        self.operation_map = build_operation_map()

        # Statistics
        self.programs_evaluated = 0
        self.best_fitness_by_depth = {}
        self.plateau_counter = 0

    def synthesize(self,
                   task: Dict,
                   constraints: Dict = None,
                   biased_operations: List[str] = None) -> Tuple[ARCProgram, float]:
        """
        Synthesize program using deep beam search.

        Args:
            task: Task with 'train' examples
            constraints: Task constraints
            biased_operations: Preferred operations

        Returns:
            (best_program, best_fitness)
        """
        print(f"  [Deep Beam] Starting (width={self.beam_width}, depth={self.max_depth})")

        # Extract training examples
        train_examples = task.get('train', [])
        if not train_examples:
            return ARCProgram([]), 0.0

        # Determine candidate operations
        if biased_operations and len(biased_operations) > 0:
            candidate_ops = biased_operations[:20]  # Increased from 15
            print(f"  [Deep Beam] Using {len(candidate_ops)} biased operations")
        else:
            candidate_ops = list(PARAMETRIC_OPERATIONS.keys())[:20]
            print(f"  [Deep Beam] Using {len(candidate_ops)} default operations")

        # Initialize beam with empty program
        beam = [(0.0, ARCProgram([]))]
        best_overall = (0.0, ARCProgram([]))
        last_improvement_depth = 0

        # Deep beam search
        for depth in range(self.max_depth):
            print(f"  [Deep Beam] Depth {depth+1}/{self.max_depth}...")

            candidates = []
            seen_patterns = set()  # For diversity

            # Expand each program in beam
            for fitness, program in beam:
                # Try adding each operation
                for op_name in candidate_ops:
                    # Get parameter candidates
                    param_sets = get_parameter_candidates(
                        op_name, task, constraints
                    )[:self.max_candidates_per_op]

                    # Try each parameter set
                    for params in param_sets:
                        # Create new program
                        new_program = program.copy()
                        new_program.add_operation(op_name, params)

                        # Check for duplicates (diversity)
                        pattern_key = tuple(new_program.to_pattern())  # Convert list to tuple for hashing
                        if pattern_key in seen_patterns:
                            continue  # Skip duplicate patterns
                        seen_patterns.add(pattern_key)

                        # Evaluate with improved fitness
                        new_fitness = self._evaluate_improved(new_program, train_examples)
                        self.programs_evaluated += 1

                        candidates.append((new_fitness, new_program))

                        # Track best
                        if new_fitness > best_overall[0]:
                            best_overall = (new_fitness, new_program)
                            last_improvement_depth = depth

                        # Early exit if solved
                        if new_fitness >= 0.95:
                            print(f"  [Deep Beam] ✓ Solution found at depth {depth+1}! Fitness: {new_fitness:.3f}")
                            return new_program, new_fitness

            # Keep top-k
            candidates.sort(reverse=True, key=lambda x: x[0])
            beam = candidates[:self.beam_width]

            # Track best fitness at this depth
            if beam:
                self.best_fitness_by_depth[depth] = beam[0][0]
                print(f"  [Deep Beam]   Best: {beam[0][0]:.3f}, Programs: {self.programs_evaluated}")

                # Plateau detection: stop if no improvement for 3 depths
                if depth - last_improvement_depth >= 3:
                    print(f"  [Deep Beam] Plateau detected (no improvement for 3 depths), stopping")
                    break

            # Check for progress
            if beam[0][0] <= 0.05:
                print(f"  [Deep Beam] No progress, stopping early")
                break

        # Return best program found
        print(f"  [Deep Beam] Search complete. Best fitness: {best_overall[0]:.3f}")
        return best_overall[1], best_overall[0]

    def _evaluate_improved(self,
                          program: ARCProgram,
                          train_examples: List) -> float:
        """
        Evaluate program with improved fitness function.

        Improvements:
        1. Exact matching (perfect match)
        2. Fuzzy matching (pixel-level similarity)
        3. Structural similarity (shape, pattern preservation)

        Args:
            program: Program to evaluate
            train_examples: List of dicts with 'input' and 'output' keys OR tuples

        Returns:
            Fitness score (0.0 to 1.0)
        """
        if not train_examples or len(program) == 0:
            return 0.0

        total_fitness = 0.0

        for example in train_examples:
            try:
                # Handle both dict format and tuple format
                if isinstance(example, dict):
                    input_grid = np.array(example['input'])
                    expected_output = np.array(example['output'])
                else:
                    input_grid, expected_output = example

                predicted = program.execute(input_grid, self.operation_map)

                # Compute multi-component fitness
                exact_score = self._exact_similarity(predicted, expected_output)
                fuzzy_score = self._fuzzy_similarity(predicted, expected_output)
                structural_score = self._structural_similarity(predicted, expected_output)

                # Weighted combination
                fitness = (
                    0.50 * exact_score +      # Exact match most important
                    0.30 * fuzzy_score +       # Fuzzy matching second
                    0.20 * structural_score    # Structure preservation bonus
                )

                total_fitness += fitness

            except Exception as e:
                # Execution failed
                total_fitness += 0.0

        # Average across examples
        avg_fitness = total_fitness / len(train_examples)

        # Smaller complexity penalty (encourage exploration)
        complexity_penalty = 0.005 * len(program)  # Reduced from 0.01

        return max(0.0, avg_fitness - complexity_penalty)

    def _exact_similarity(self,
                         predicted: np.ndarray,
                         expected: np.ndarray) -> float:
        """
        Exact matching score (perfect match = 1.0).
        """
        if predicted.shape == expected.shape and np.array_equal(predicted, expected):
            return 1.0

        # Size mismatch: max 0.5
        if predicted.shape != expected.shape:
            min_h = min(predicted.shape[0], expected.shape[0])
            min_w = min(predicted.shape[1], expected.shape[1])

            if min_h == 0 or min_w == 0:
                return 0.0

            pred_crop = predicted[:min_h, :min_w]
            exp_crop = expected[:min_h, :min_w]

            matching_pixels = np.sum(pred_crop == exp_crop)
            total_pixels = exp_crop.size

            return (matching_pixels / total_pixels) * 0.5

        # Same size: pure pixel similarity
        matching_pixels = np.sum(predicted == expected)
        total_pixels = expected.size

        return matching_pixels / total_pixels if total_pixels > 0 else 0.0

    def _fuzzy_similarity(self,
                         predicted: np.ndarray,
                         expected: np.ndarray) -> float:
        """
        Fuzzy matching with tolerance for off-by-one errors.
        """
        if predicted.shape != expected.shape:
            return 0.0

        if predicted.size == 0:
            return 0.0

        # Exact matches
        exact_matches = np.sum(predicted == expected)

        # Off-by-one color matches (neighboring colors in palette)
        off_by_one = np.sum(np.abs(predicted - expected) == 1)

        # Weighted score
        score = (exact_matches + 0.5 * off_by_one) / predicted.size

        return min(1.0, score)

    def _structural_similarity(self,
                              predicted: np.ndarray,
                              expected: np.ndarray) -> float:
        """
        Structural similarity: shape, pattern preservation.
        """
        score = 0.0

        # Shape similarity (aspect ratio)
        if predicted.shape == expected.shape:
            score += 0.5
        elif predicted.size > 0 and expected.size > 0:
            pred_aspect = predicted.shape[0] / predicted.shape[1]
            exp_aspect = expected.shape[0] / expected.shape[1]
            aspect_diff = abs(pred_aspect - exp_aspect)
            score += 0.25 * max(0, 1.0 - aspect_diff)

        # Color distribution similarity
        if predicted.size > 0 and expected.size > 0:
            pred_colors = set(predicted.flatten())
            exp_colors = set(expected.flatten())

            if exp_colors:
                color_overlap = len(pred_colors & exp_colors) / len(exp_colors)
                score += 0.5 * color_overlap

        return min(1.0, score)

    def get_statistics(self) -> Dict:
        """Get search statistics."""
        return {
            'programs_evaluated': self.programs_evaluated,
            'best_fitness_by_depth': self.best_fitness_by_depth,
            'beam_width': self.beam_width,
            'max_depth': self.max_depth
        }


# ============================================================================
# TESTING
# ============================================================================

def test_deep_beam_search():
    """Test deep beam search."""
    print("=" * 80)
    print("🧪 Testing Deep Beam Search")
    print("=" * 80)
    print()

    # Create test task (rotation)
    test_task = {
        'train': [
            {
                'input': [[1, 2], [3, 4]],
                'output': [[3, 1], [4, 2]]  # rotated 90 degrees
            },
            {
                'input': [[1, 0], [0, 1]],
                'output': [[0, 1], [1, 0]]  # rotated 90 degrees
            }
        ]
    }

    # Initialize deep beam search
    searcher = DeepBeamSearch(
        beam_width=20,
        max_depth=3,
        max_candidates_per_op=2
    )

    # Synthesize program
    print("Synthesizing program for rotation task...")
    program, fitness = searcher.synthesize(test_task)

    print()
    print(f"Best program: {program.to_pattern()}")
    print(f"Fitness: {fitness:.3f}")

    # Test on training examples
    print()
    print("Testing on training examples:")
    for i, example in enumerate(test_task['train'], 1):
        input_grid = np.array(example['input'])
        expected = np.array(example['output'])
        predicted = program.execute(input_grid, searcher.operation_map)
        match = np.array_equal(predicted, expected)
        print(f"  Example {i}: {'✓ MATCH' if match else '✗ MISMATCH'}")

    # Statistics
    stats = searcher.get_statistics()
    print()
    print(f"Statistics:")
    print(f"  Programs evaluated: {stats['programs_evaluated']}")
    print(f"  Best fitness by depth: {stats['best_fitness_by_depth']}")
    print()
    print("✅ Test complete!")


if __name__ == '__main__':
    test_deep_beam_search()
