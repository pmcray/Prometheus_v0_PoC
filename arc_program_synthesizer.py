#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARC Program Synthesizer (v0.95)

Beam search-based program synthesis for ARC-AGI tasks.

Key Features:
- Beam search with configurable width
- Constraint-guided operation selection
- Parameter candidate generation
- Early stopping on solution
- Integration with meta-learner for biased search

Algorithm:
1. Start with empty program
2. Get candidate operations from meta-learner (biased by constraints)
3. For each program in beam:
   - Try adding each candidate operation with parameter variations
   - Evaluate on training examples
   - Keep top-k by fitness
4. Repeat until solved or max_depth reached
5. Return best program
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from arc_program import ARCProgram
from arc_parametric_operations import (
    build_operation_map,
    get_parameter_candidates,
    PARAMETRIC_OPERATIONS
)


class ProgramSynthesizer:
    """
    Synthesize programs using beam search with constraint guidance.
    """

    # Operation priority for tie-breaking (Option G)
    # When operations have equal fitness, prefer simpler/more fundamental operations
    OPERATION_PRIORITY = {
        # Core geometric (highest priority)
        'identity': 0,
        'crop': 1,
        'transpose': 2,
        'flip': 3,
        'rotate': 4,

        # Size operations
        'scale': 5,
        'fit_to_canvas': 6,
        'expand_to_size': 7,
        'trim': 8,

        # Color operations (prefer filtering over mapping)
        'filter_color': 9,
        'map_color': 10,
        'swap_colors': 11,
        'remove_color': 12,

        # Pattern operations
        'fill_pattern': 13,
        'detect_symmetry': 14,

        # Object operations
        'detect_objects': 15,
        'count_objects': 16,
        'sort_objects': 17,

        # Alignment
        'align_grids': 18,

        # Complex operations (lowest priority)
        'overlay_grids': 19,
        'stack_grids': 20,
    }

    def __init__(self,
                 beam_width: int = 50,
                 max_depth: int = 5,
                 max_candidates_per_op: int = 3):
        """
        Initialize synthesizer.

        Args:
            beam_width: Number of programs to keep in beam
            max_depth: Maximum program length
            max_candidates_per_op: Max parameter sets to try per operation
        """
        self.beam_width = beam_width
        self.max_depth = max_depth
        self.max_candidates_per_op = max_candidates_per_op

        # Build operation map
        self.operation_map = build_operation_map()

        # Statistics
        self.programs_evaluated = 0
        self.best_fitness_by_depth = {}
    
    def synthesize(self,
                   task: Dict,
                   constraints: Dict = None,
                   biased_operations: List[str] = None) -> ARCProgram:
        """
        Synthesize program for task using beam search.
        
        Args:
            task: Task with 'train' examples [(input, output), ...]
            constraints: Task constraints (for filtering operations)
            biased_operations: Preferred operations (from meta-learner)
        
        Returns:
            Best program found
        """
        print(f"  [Synthesizer] Starting beam search (width={self.beam_width}, max_depth={self.max_depth})")
        
        # Extract training examples
        train_examples = task.get('train', [])
        if not train_examples:
            return ARCProgram([])
        
        # Determine candidate operations
        if biased_operations and len(biased_operations) > 0:
            candidate_ops = biased_operations[:20]  # Limit to top 20
            print(f"  [Synthesizer] Using {len(candidate_ops)} biased operations")
        else:
            # Use all 19 operations (v0.96c - Option I)
            candidate_ops = list(PARAMETRIC_OPERATIONS.keys())
            print(f"  [Synthesizer] Using {len(candidate_ops)} operations (v0.96c - Option I)")
        
        # Initialize beam with empty program
        beam = [(0.0, ARCProgram([]))]
        
        best_overall = (0.0, ARCProgram([]))
        
        # Beam search
        for depth in range(self.max_depth):
            print(f"  [Synthesizer] Depth {depth+1}/{self.max_depth}...")
            
            candidates = []
            
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
                        
                        # Evaluate
                        new_fitness = self._evaluate(new_program, train_examples)
                        self.programs_evaluated += 1
                        
                        candidates.append((new_fitness, new_program))
                        
                        # Track best
                        if new_fitness > best_overall[0]:
                            best_overall = (new_fitness, new_program)
                        
                        # Early exit if solved
                        if new_fitness >= 0.99:
                            print(f"  [Synthesizer] ✓ Solution found at depth {depth+1}! Fitness: {new_fitness:.3f}")
                            return new_program
            
            # Keep top-k with diversity and tie-breaking (Options F + G)
            # Sort by: 1) fitness (descending), 2) operation priority (ascending)
            candidates.sort(reverse=True, key=lambda x: (
                x[0],  # Primary: fitness
                -self._get_operation_priority(x[1])  # Secondary: prefer simpler ops
            ))
            beam = self._diverse_beam_selection(candidates, self.beam_width)
            
            # Track best fitness at this depth
            self.best_fitness_by_depth[depth] = beam[0][0] if beam else 0.0
            
            print(f"  [Synthesizer]   Best fitness: {beam[0][0]:.3f}, Programs evaluated: {self.programs_evaluated}")
            
            # Check for progress
            if beam[0][0] <= 0.05:
                print(f"  [Synthesizer] No progress, stopping early")
                break
        
        # Return best program found
        print(f"  [Synthesizer] Search complete. Best fitness: {best_overall[0]:.3f}")
        return best_overall[1]
    
    def _evaluate(self,
                  program: ARCProgram,
                  train_examples: List) -> float:
        """
        Evaluate program on training examples.

        Args:
            program: Program to evaluate
            train_examples: List of dicts with 'input' and 'output' keys OR tuples

        Returns:
            Fitness score (0.0 to 1.0)
        """
        if not train_examples or len(program) == 0:
            return 0.0

        total_similarity = 0.0

        for example in train_examples:
            try:
                # Handle both dict format and tuple format
                if isinstance(example, dict):
                    input_grid = np.array(example['input'])
                    expected_output = np.array(example['output'])
                else:
                    input_grid, expected_output = example

                predicted = program.execute(input_grid, self.operation_map)
                similarity = self._compute_similarity(predicted, expected_output)
                total_similarity += similarity
            except Exception as e:
                # Execution failed
                total_similarity += 0.0
        
        # Average similarity across examples
        fitness = total_similarity / len(train_examples)

        # Small complexity penalty (encourage shorter programs)
        # Reduced from 0.01 to 0.005 (Option I) to avoid pushing near-threshold programs below 0.95
        complexity_penalty = 0.005 * len(program)

        return max(0.0, fitness - complexity_penalty)
    
    def _compute_similarity(self,
                           predicted: np.ndarray,
                           expected: np.ndarray) -> float:
        """
        Compute similarity between predicted and expected grids.
        
        Args:
            predicted: Predicted output grid
            expected: Expected output grid
        
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Perfect match
        if predicted.shape == expected.shape and np.array_equal(predicted, expected):
            return 1.0
        
        # Size mismatch penalty
        if predicted.shape != expected.shape:
            # Use overlap region for partial credit
            min_h = min(predicted.shape[0], expected.shape[0])
            min_w = min(predicted.shape[1], expected.shape[1])
            
            if min_h == 0 or min_w == 0:
                return 0.0
            
            pred_crop = predicted[:min_h, :min_w]
            exp_crop = expected[:min_h, :min_w]
            
            matching_pixels = np.sum(pred_crop == exp_crop)
            total_pixels = exp_crop.size
            
            # Size mismatch penalty: max 50% score
            similarity = (matching_pixels / total_pixels) * 0.5
            return similarity
        
        # Same size: pure pixel similarity
        matching_pixels = np.sum(predicted == expected)
        total_pixels = expected.size
        
        return matching_pixels / total_pixels if total_pixels > 0 else 0.0

    def _get_operation_priority(self, program: ARCProgram) -> int:
        """
        Get priority score for a program based on first operation.
        Lower score = higher priority (simpler operations preferred).

        Args:
            program: Program to score

        Returns:
            Priority score (0 = highest priority)
        """
        if not program.operations or len(program.operations) == 0:
            return 999  # Empty program lowest priority

        # Get first operation name
        first_op_name = program.operations[0][0]

        # Return priority (default to 999 for unknown operations)
        return self.OPERATION_PRIORITY.get(first_op_name, 999)

    def _diverse_beam_selection(self,
                                 candidates: List[Tuple[float, ARCProgram]],
                                 beam_width: int) -> List[Tuple[float, ARCProgram]]:
        """
        Select diverse beam to avoid greedy local optima.

        Strategy:
        - 40% best by fitness (exploitation)
        - 30% shortest programs (simplicity bias)
        - 30% random from top candidates (exploration)

        Args:
            candidates: Sorted list of (fitness, program) tuples
            beam_width: Target beam size

        Returns:
            Diverse beam of programs
        """
        if len(candidates) <= beam_width:
            return candidates

        beam = []
        used_indices = set()

        # 1. Top 40% by fitness (best performers)
        fitness_quota = int(beam_width * 0.4)
        for i in range(min(fitness_quota, len(candidates))):
            beam.append(candidates[i])
            used_indices.add(i)

        # 2. Top 30% by program length (favor shorter programs)
        length_quota = int(beam_width * 0.3)
        # Sort remaining candidates by length
        remaining = [(i, fitness, prog) for i, (fitness, prog) in enumerate(candidates)
                     if i not in used_indices]
        remaining.sort(key=lambda x: len(x[2]))  # Sort by program length

        for i, fitness, prog in remaining[:length_quota]:
            beam.append((fitness, prog))
            used_indices.add(i)

        # 3. Random 30% from top 2*beam_width (exploration)
        exploration_quota = beam_width - len(beam)
        pool_size = min(beam_width * 2, len(candidates))
        exploration_pool = [i for i in range(pool_size) if i not in used_indices]

        if exploration_pool and exploration_quota > 0:
            import random
            sampled_indices = random.sample(
                exploration_pool,
                min(exploration_quota, len(exploration_pool))
            )
            for i in sampled_indices:
                beam.append(candidates[i])

        return beam

    def get_statistics(self) -> Dict:
        """Get synthesis statistics"""
        return {
            'programs_evaluated': self.programs_evaluated,
            'best_fitness_by_depth': self.best_fitness_by_depth,
            'beam_width': self.beam_width,
            'max_depth': self.max_depth
        }


# ============================================================================
# TESTING
# ============================================================================

def test_program_synthesizer():
    """Test program synthesizer"""
    print("Testing Program Synthesizer...")
    
    # Create simple test task
    # Task: rotate 90 degrees
    test_task = {
        'train': [
            (
                np.array([[1, 2], [3, 4]]),
                np.array([[3, 1], [4, 2]])  # rotated 90 degrees
            ),
            (
                np.array([[1, 0], [0, 1]]),
                np.array([[0, 1], [1, 0]])  # rotated 90 degrees
            )
        ]
    }
    
    # Initialize synthesizer
    synthesizer = ProgramSynthesizer(
        beam_width=20,
        max_depth=3,
        max_candidates_per_op=2
    )
    
    # Synthesize program
    print("\nSynthesizing program for rotation task...")
    program = synthesizer.synthesize(test_task)
    
    print(f"\nBest program found: {program}")
    print(f"Program operations: {program.operations}")
    
    # Test on training examples
    print("\nTesting on training examples:")
    for i, (input_grid, expected) in enumerate(test_task['train']):
        predicted = program.execute(input_grid, synthesizer.operation_map)
        match = np.array_equal(predicted, expected)
        print(f"  Example {i+1}: {'✓ MATCH' if match else '✗ MISMATCH'}")
        print(f"    Input:\n{input_grid}")
        print(f"    Expected:\n{expected}")
        print(f"    Predicted:\n{predicted}")
    
    # Statistics
    stats = synthesizer.get_statistics()
    print(f"\nStatistics:")
    print(f"  Programs evaluated: {stats['programs_evaluated']}")
    print(f"  Best fitness by depth: {stats['best_fitness_by_depth']}")
    
    print("\nTest complete!")


if __name__ == "__main__":
    test_program_synthesizer()
