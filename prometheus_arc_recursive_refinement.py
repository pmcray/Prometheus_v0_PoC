#!/usr/bin/env python3
"""
Prometheus ARC Recursive Refinement with FUZZY FITNESS (v0.88 - Phase 3 Full)

TRM-inspired recursive refinement for symbolic ARC-AGI solver.
Adapts the "Less is More" recursive reasoning approach to symbolic pattern evolution.

Key Innovations:
- PHASE 1 (v0.84-v0.85): Fuzzy fitness for pattern evaluation
- PHASE 2 (v0.86): Population seeding + smarter composition
  * Seed correction population with variations of current pattern
  * Try 4 composition strategies and keep best (base→corr, corr→base, interleave, replace)
- PHASE 3 MINIMAL (v0.87): Targeted primitive selection for >95% fitness
  * Pixel-level failure analysis (single_pixel, boundary, symmetry, scaling)
  * Restrict primitive pool from 25 → 3-5 based on failure type
- PHASE 3 FULL (v0.88): Local search for high-fitness tasks
  * Use local search instead of evolution for >95% fitness (10x faster)
  * Try single primitives and composition ordering variations
  * Micro-adjustment fallback for edge cases

Expected Performance: 3-7% on ARC-AGI-1 (vs 2% Phase 2, vs 0% Phase 1)
"""

import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import time

# Import FUZZY FITNESS baseline system
from prometheus_arc_fuzzy_fitness import PrometheusARCFuzzyFitness, ARCPrimitives


@dataclass
class FailureAnalysis:
    """Analysis of where a pattern fails"""
    example_idx: int
    input_grid: np.ndarray
    expected_output: np.ndarray
    predicted_output: np.ndarray
    pixel_diff_ratio: float  # % of pixels that are wrong
    failure_type: str  # 'wrong_colors', 'wrong_shape', 'wrong_size', 'partial_match'
    suggested_corrections: List[str]  # Primitive names that might fix this


@dataclass
class RefinementStep:
    """One recursive refinement cycle"""
    cycle: int
    base_pattern: List[str]
    correction_pattern: List[str]
    combined_pattern: List[str]
    fitness_before: float
    fitness_after: float
    failures_fixed: int


class FailureAnalyzer:
    """Analyzes why patterns fail and suggests corrections"""

    def __init__(self, primitives: ARCPrimitives):
        self.primitives = primitives

    def analyze_failure(self,
                       example_idx: int,
                       input_grid: np.ndarray,
                       expected: np.ndarray,
                       predicted: np.ndarray) -> FailureAnalysis:
        """
        Analyze a single failure case and suggest corrections.
        """
        # Calculate pixel-level difference
        if expected.shape != predicted.shape:
            pixel_diff_ratio = 1.0  # Completely wrong
            failure_type = 'wrong_size'
        else:
            diff_pixels = np.sum(expected != predicted)
            total_pixels = expected.size
            pixel_diff_ratio = diff_pixels / total_pixels if total_pixels > 0 else 1.0

            # Classify failure type
            if pixel_diff_ratio < 0.2:
                failure_type = 'partial_match'
            elif expected.shape != predicted.shape:
                failure_type = 'wrong_size'
            elif set(expected.flatten()) != set(predicted.flatten()):
                failure_type = 'wrong_colors'
            else:
                failure_type = 'wrong_shape'

        # Suggest corrections based on failure type
        corrections = self._suggest_corrections(
            failure_type, input_grid, expected, predicted
        )

        return FailureAnalysis(
            example_idx=example_idx,
            input_grid=input_grid,
            expected_output=expected,
            predicted_output=predicted,
            pixel_diff_ratio=pixel_diff_ratio,
            failure_type=failure_type,
            suggested_corrections=corrections
        )

    def _suggest_corrections(self,
                            failure_type: str,
                            input_grid: np.ndarray,
                            expected: np.ndarray,
                            predicted: np.ndarray) -> List[str]:
        """
        Suggest correction primitives based on failure type.
        """
        corrections = []

        if failure_type == 'wrong_size':
            # Size mismatch - try scaling, cropping, padding
            corrections.extend(['scale_up', 'scale_down', 'crop', 'extend_edges'])

        elif failure_type == 'wrong_colors':
            # Color mismatch - try color operations
            corrections.extend(['swap_colors', 'replace_color', 'invert_colors', 'map_color'])

        elif failure_type == 'wrong_shape':
            # Shape mismatch - try geometric operations
            corrections.extend(['rotate_90', 'rotate_180', 'flip_h', 'flip_v',
                              'transpose', 'diagonal_flip'])

        elif failure_type == 'partial_match':
            # Close but not perfect - try refinement operations
            corrections.extend(['fill_inside', 'hollow', 'extract_largest',
                              'detect_objects', 'sort_by_size'])

        return corrections

    def aggregate_failure_patterns(self,
                                   failures: List[FailureAnalysis]) -> Dict[str, any]:
        """
        Aggregate multiple failures to identify common patterns.
        """
        if not failures:
            return {}

        # Count failure types
        failure_types = defaultdict(int)
        all_corrections = []
        total_diff = 0.0

        for failure in failures:
            failure_types[failure.failure_type] += 1
            all_corrections.extend(failure.suggested_corrections)
            total_diff += failure.pixel_diff_ratio

        # Find most common failure type
        dominant_failure = max(failure_types.items(), key=lambda x: x[1])[0]

        # Find most suggested corrections (with frequency)
        correction_freq = defaultdict(int)
        for correction in all_corrections:
            correction_freq[correction] += 1

        # Sort by frequency
        top_corrections = sorted(
            correction_freq.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]  # Top 5 corrections

        return {
            'failure_types': dict(failure_types),
            'dominant_failure': dominant_failure,
            'top_corrections': [corr for corr, freq in top_corrections],
            'avg_pixel_diff': total_diff / len(failures) if failures else 0.0
        }


class PrometheusARCRecursiveRefinement:
    """
    TRM-inspired recursive refinement for ARC-AGI.

    Algorithm:
    1. Generate initial solution using baseline evolution
    2. For k refinement cycles:
       a. Analyze failures in current solution
       b. Synthesize targeted corrections
       c. Compose corrections with current solution
       d. Evaluate and keep if better
    3. Return best solution found
    """

    def __init__(self,
                 population_size: int = 100,
                 max_pattern_length: int = 5,
                 max_refinement_cycles: int = 5,
                 correction_generations: int = 50,
                 use_fuzzy: bool = True):
        """
        Args:
            population_size: Population for baseline evolution
            max_pattern_length: Maximum pattern length (default: 5, extended from 2)
            max_refinement_cycles: Number of recursive refinement cycles
            correction_generations: Generations for evolving corrections
            use_fuzzy: Use fuzzy fitness (pixel similarity) vs binary (exact match)
        """
        self.population_size = population_size
        self.max_pattern_length = max_pattern_length
        self.max_refinement_cycles = max_refinement_cycles
        self.correction_generations = correction_generations
        self.use_fuzzy = use_fuzzy

        # Initialize FUZZY FITNESS baseline solver
        self.baseline = PrometheusARCFuzzyFitness(
            population_size=population_size,
            max_pattern_length=max_pattern_length,
            use_fuzzy=use_fuzzy
        )

        self.primitives = ARCPrimitives()
        self.analyzer = FailureAnalyzer(self.primitives)

        # Build primitive name -> method mapping
        self.primitive_methods = {
            'identity': ARCPrimitives.identity,
            'rotate_90': ARCPrimitives.rotate_90,
            'rotate_180': ARCPrimitives.rotate_180,
            'rotate_270': ARCPrimitives.rotate_270,
            'flip_h': ARCPrimitives.flip_horizontal,
            'flip_v': ARCPrimitives.flip_vertical,
            'transpose': ARCPrimitives.transpose,
            'scale_2x': ARCPrimitives.scale_2x,
            'scale_3x': ARCPrimitives.scale_3x,
            'tile_2x2': ARCPrimitives.tile_2x2,
            'tile_3x3': ARCPrimitives.tile_3x3,
            'gravity_down': ARCPrimitives.gravity_down,
            'gravity_up': ARCPrimitives.gravity_up,
            'fill_zeros': ARCPrimitives.fill_zeros_common,
            'remove_bg': ARCPrimitives.remove_background,
            'swap_01': ARCPrimitives.color_swap_01,
            'color_inc': ARCPrimitives.color_increment,
            'border': ARCPrimitives.border_extract,
            'center': ARCPrimitives.center_extract,
            'pad_1': ARCPrimitives.pad_1,
            'invert': ARCPrimitives.invert_colors,
            'hollow': ARCPrimitives.hollow_objects,
            'crop': ARCPrimitives.crop_to_content,
            'extend_edges': ARCPrimitives.extend_edges,
        }

        # Statistics
        self.refinement_history: List[RefinementStep] = []

    def solve_task(self,
                   train_examples: List[Dict],
                   test_examples: List[Dict],
                   task_id: str,
                   max_generations: int = 200) -> Dict:
        """
        Solve ARC task using recursive refinement.

        Returns:
            {
                'pattern': best pattern found,
                'fitness': fitness score,
                'refinement_cycles': number of cycles used,
                'history': refinement history
            }
        """
        self.refinement_history = []

        # Step 1: Generate initial solution (baseline evolution)
        print(f"  [Cycle 0] Baseline evolution ({max_generations} gen)...")

        # Convert train_examples to baseline format (List[Tuple])
        train_tuples = [(np.array(ex['input']), np.array(ex['output'])) for ex in train_examples]

        initial_pattern_obj = self.baseline.evolve_for_task(
            train_tuples,
            max_generations=max_generations
        )

        # Convert CompositePattern to list of strings
        current_pattern = [op.name for op in initial_pattern_obj.operations]
        current_fitness = initial_pattern_obj.fitness

        print(f"  [Cycle 0] Initial fitness: {current_fitness:.4f}")

        # If perfect solution found, return immediately
        if current_fitness >= 1.0:
            print(f"  ✓ Perfect solution in baseline!")
            return {
                'pattern': current_pattern,
                'fitness': current_fitness,
                'refinement_cycles': 0,
                'history': self.refinement_history
            }

        best_pattern = current_pattern
        best_fitness = current_fitness

        # Step 2: Recursive refinement cycles
        for cycle in range(1, self.max_refinement_cycles + 1):
            print(f"  [Cycle {cycle}] Analyzing failures...")

            # Analyze failures in current solution
            failures = self._analyze_current_failures(
                current_pattern,
                train_examples
            )

            if not failures:
                print(f"  [Cycle {cycle}] No failures found (perfect fit)")
                break

            # Aggregate failure patterns
            failure_summary = self.analyzer.aggregate_failure_patterns(failures)
            print(f"  [Cycle {cycle}] Dominant failure: {failure_summary['dominant_failure']}")
            print(f"  [Cycle {cycle}] Avg pixel diff: {failure_summary['avg_pixel_diff']:.2%}")

            # Synthesize corrections
            print(f"  [Cycle {cycle}] Synthesizing corrections...")
            correction_pattern = self._synthesize_corrections(
                failures,
                failure_summary,
                train_examples,
                current_pattern=current_pattern,  # Phase 2: Pass current pattern for seeding
                current_fitness=current_fitness   # Phase 3: Pass current fitness for targeted selection
            )

            if not correction_pattern:
                print(f"  [Cycle {cycle}] No viable corrections found")
                break

            # Compose correction with current pattern
            combined_pattern = self._compose_patterns(
                current_pattern,
                correction_pattern,
                train_examples=train_examples  # Phase 2: Pass train_examples for evaluation
            )

            # Evaluate combined pattern
            combined_fitness = self._evaluate_pattern(combined_pattern, train_examples)

            print(f"  [Cycle {cycle}] Correction pattern: {correction_pattern}")
            print(f"  [Cycle {cycle}] Fitness: {current_fitness:.4f} → {combined_fitness:.4f}")

            # Record refinement step
            failures_fixed = int((combined_fitness - current_fitness) * len(train_examples))
            step = RefinementStep(
                cycle=cycle,
                base_pattern=current_pattern,
                correction_pattern=correction_pattern,
                combined_pattern=combined_pattern,
                fitness_before=current_fitness,
                fitness_after=combined_fitness,
                failures_fixed=failures_fixed
            )
            self.refinement_history.append(step)

            # Keep if improved
            if combined_fitness > current_fitness:
                print(f"  [Cycle {cycle}] ✓ Improvement accepted!")
                current_pattern = combined_pattern
                current_fitness = combined_fitness

                if current_fitness > best_fitness:
                    best_pattern = current_pattern
                    best_fitness = current_fitness

                # Early stopping if perfect
                if current_fitness >= 1.0:
                    print(f"  [Cycle {cycle}] ✓ Perfect solution found!")
                    break
            else:
                print(f"  [Cycle {cycle}] ✗ No improvement, keeping previous")

        return {
            'pattern': best_pattern,
            'fitness': best_fitness,
            'refinement_cycles': len(self.refinement_history),
            'history': self.refinement_history
        }

    def _apply_pattern_from_names(self, pattern_names: List[str], grid: np.ndarray) -> np.ndarray:
        """Apply a pattern (list of primitive names) to a grid"""
        output = grid.copy()
        for prim_name in pattern_names:
            if prim_name in self.primitive_methods:
                method = self.primitive_methods[prim_name]
                output = method(output)
        return output

    def _analyze_current_failures(self,
                                 pattern: List[str],
                                 train_examples: List[Dict]) -> List[FailureAnalysis]:
        """
        Analyze where current pattern fails on training examples.
        """
        failures = []

        for idx, example in enumerate(train_examples):
            input_grid = np.array(example['input'])
            expected = np.array(example['output'])

            # Apply current pattern
            try:
                predicted = self._apply_pattern_from_names(pattern, input_grid)
            except Exception:
                predicted = input_grid.copy()

            # Check if it matches
            if not np.array_equal(predicted, expected):
                failure = self.analyzer.analyze_failure(
                    idx, input_grid, expected, predicted
                )
                failures.append(failure)

        return failures

    def _analyze_pixel_patterns(self, failures: List[FailureAnalysis]) -> Dict:
        """
        PHASE 3: Analyze pixel-level differences to determine specific failure type.

        For high-fitness tasks (>95%), perform fine-grained pixel analysis to identify:
        - single_pixel: < 5% pixel errors (micro-adjustments needed)
        - boundary: Errors concentrated on edges
        - symmetry: Errors show left/right or top/bottom asymmetry
        - scaling: Size mismatches or tiling issues
        """
        if not failures:
            return {'pattern_type': 'unknown', 'avg_error_rate': 0.0}

        total_error_rate = 0.0
        boundary_errors = 0
        total_errors = 0
        left_right_imbalance = 0
        size_mismatches = 0

        for failure in failures:
            predicted = failure.predicted_output
            expected = failure.expected_output

            # Size mismatch
            if predicted.shape != expected.shape:
                size_mismatches += 1
                total_error_rate += 1.0
                continue

            # Pixel-level analysis
            diff_mask = (predicted != expected)
            wrong_pixels = np.sum(diff_mask)
            total_pixels = expected.size
            error_rate = wrong_pixels / total_pixels if total_pixels > 0 else 0.0
            total_error_rate += error_rate
            total_errors += wrong_pixels

            # Boundary error detection
            h, w = expected.shape
            if h > 0 and w > 0:
                boundary_mask = np.zeros_like(diff_mask, dtype=bool)
                boundary_mask[0, :] = True
                boundary_mask[-1, :] = True
                boundary_mask[:, 0] = True
                boundary_mask[:, -1] = True
                boundary_err = np.sum(diff_mask & boundary_mask)
                boundary_errors += boundary_err

                # Left/right imbalance (symmetry issues)
                left_err = np.sum(diff_mask[:, :w//2])
                right_err = np.sum(diff_mask[:, w//2:])
                if wrong_pixels > 0:
                    imbalance = abs(left_err - right_err) / wrong_pixels
                    left_right_imbalance += imbalance

        # Aggregate statistics
        avg_error_rate = total_error_rate / len(failures)
        boundary_ratio = boundary_errors / total_errors if total_errors > 0 else 0.0
        avg_imbalance = left_right_imbalance / len(failures) if failures else 0.0
        size_mismatch_ratio = size_mismatches / len(failures)

        # Classify pattern type
        if size_mismatch_ratio > 0.5:
            pattern_type = 'scaling'
        elif avg_error_rate < 0.05:  # < 5% error
            pattern_type = 'single_pixel'
        elif boundary_ratio > 0.5:
            pattern_type = 'boundary'
        elif avg_imbalance > 0.6:
            pattern_type = 'symmetry'
        else:
            pattern_type = 'mixed'

        return {
            'pattern_type': pattern_type,
            'avg_error_rate': avg_error_rate,
            'boundary_ratio': boundary_ratio,
            'imbalance': avg_imbalance,
            'size_mismatch_ratio': size_mismatch_ratio
        }

    def _select_targeted_primitives(self, pixel_analysis: Dict) -> Optional[List[str]]:
        """
        PHASE 3: Select focused primitive pool based on pixel analysis.

        Returns 3-5 targeted primitives instead of all 25, dramatically reducing
        search space for high-fitness tasks that are close to perfect.
        """
        pattern_type = pixel_analysis.get('pattern_type', 'unknown')

        if pattern_type == 'single_pixel':
            # < 5% error - micro-adjustments
            return ['identity', 'fill_zeros', 'remove_bg']

        elif pattern_type == 'boundary':
            # Errors on edges - boundary operations
            return ['border', 'extend_edges', 'crop', 'pad_1']

        elif pattern_type == 'symmetry':
            # Left/right or top/bottom asymmetry - reflection operations
            return ['flip_h', 'flip_v', 'transpose', 'rotate_90']

        elif pattern_type == 'scaling':
            # Size mismatches - scaling/tiling operations
            return ['scale_2x', 'scale_3x', 'tile_2x2']

        else:
            # Mixed or unknown - fall back to Phase 2 (all primitives)
            return None

    def _local_search_corrections(self,
                                  failures: List[FailureAnalysis],
                                  pixel_analysis: Dict,
                                  targeted_prims: List[str],
                                  train_examples: List[Dict],
                                  current_pattern: List[str]) -> Optional[List[str]]:
        """
        PHASE 3 FULL (v0.88): Use local search instead of evolution for high-fitness tasks.

        Much faster than evolution (seconds vs minutes) and more focused.
        Try simple corrections first:
        1. Single targeted primitives
        2. Composition ordering variations
        3. Small mutations
        """
        print(f"    [Phase 3 Full] Using LOCAL SEARCH (faster than evolution)")

        best_correction = None
        best_fitness = 0.0

        # Convert train examples to tuples
        train_tuples = [(np.array(ex['input']), np.array(ex['output'])) for ex in train_examples]

        # Strategy 1: Try each targeted primitive individually
        print(f"    [Phase 3 Full] Testing {len(targeted_prims)} single primitives...")
        for prim in targeted_prims:
            candidate = [prim]
            fitness = self._evaluate_pattern(candidate, train_examples)
            if fitness > best_fitness:
                best_fitness = fitness
                best_correction = candidate

        # Strategy 2: Try each primitive BEFORE current pattern
        if current_pattern and len(current_pattern) > 0:
            print(f"    [Phase 3 Full] Testing primitives before current pattern...")
            for prim in targeted_prims:
                candidate = [prim] + current_pattern[:min(2, len(current_pattern))]
                fitness = self._evaluate_pattern(candidate, train_examples)
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_correction = candidate

        # Strategy 3: Try each primitive AFTER current pattern
        if current_pattern and len(current_pattern) > 0:
            print(f"    [Phase 3 Full] Testing primitives after current pattern...")
            for prim in targeted_prims:
                candidate = current_pattern[:min(2, len(current_pattern))] + [prim]
                fitness = self._evaluate_pattern(candidate, train_examples)
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_correction = candidate

        # Strategy 4: Try pairs of targeted primitives
        if len(targeted_prims) > 1:
            print(f"    [Phase 3 Full] Testing primitive pairs...")
            for i, prim1 in enumerate(targeted_prims):
                for prim2 in targeted_prims[i:i+2]:  # Only test adjacent pairs
                    if prim1 != prim2:
                        candidate = [prim1, prim2]
                        fitness = self._evaluate_pattern(candidate, train_examples)
                        if fitness > best_fitness:
                            best_fitness = fitness
                            best_correction = candidate

        if best_correction:
            print(f"    [Phase 3 Full] Local search found: {best_correction} (fitness: {best_fitness:.4f})")
            return best_correction
        else:
            print(f"    [Phase 3 Full] Local search failed, falling back to evolution")
            return None

    def _synthesize_corrections(self,
                               failures: List[FailureAnalysis],
                               failure_summary: Dict,
                               train_examples: List[Dict],
                               current_pattern: List[str] = None,
                               current_fitness: float = 0.0) -> Optional[List[str]]:
        """
        Synthesize correction pattern targeted at fixing failures.

        Phase 2 Improvement: Seed correction population with variations of current pattern
        Phase 3 Minimal (v0.87): Use targeted primitive selection for >95% fitness
        Phase 3 Full (v0.88): Use local search for >95% fitness (10x faster than evolution)
        """
        # Get top suggested corrections
        top_corrections = failure_summary.get('top_corrections', [])

        if not top_corrections:
            return None

        # PHASE 3: For high-fitness tasks, use targeted primitive selection + local search
        targeted_prims = None
        if current_fitness > 0.95:
            # Analyze pixel-level patterns
            pixel_analysis = self._analyze_pixel_patterns(failures)
            targeted_prims = self._select_targeted_primitives(pixel_analysis)

            if targeted_prims:
                print(f"    [Phase 3] High fitness ({current_fitness:.2%}): using targeted primitives")
                print(f"    [Phase 3] Pattern type: {pixel_analysis['pattern_type']}")
                print(f"    [Phase 3] Targeted primitives: {targeted_prims} ({len(targeted_prims)} vs 25)")

                # PHASE 3 FULL (v0.88): Try local search first (much faster)
                local_result = self._local_search_corrections(
                    failures,
                    pixel_analysis,
                    targeted_prims,
                    train_examples,
                    current_pattern if current_pattern else []
                )

                if local_result:
                    return local_result
                # If local search fails, continue to evolution below

        # Use FUZZY FITNESS solver for corrections
        correction_solver = PrometheusARCFuzzyFitness(
            population_size=self.population_size // 2,
            max_pattern_length=min(3, self.max_pattern_length),
            use_fuzzy=self.use_fuzzy
        )

        # PHASE 3: Restrict primitive pool if targeted primitives selected
        if targeted_prims:
            # Filter correction_solver's primitives to only targeted ones
            from prometheus_arc_fuzzy_fitness import PrimitiveOperation
            filtered_primitives = [
                p for p in correction_solver.primitives
                if p.name in targeted_prims
            ]
            if filtered_primitives:
                correction_solver.primitives = filtered_primitives
                print(f"    [Phase 3] Restricted primitive pool: {len(filtered_primitives)} primitives")

        # Convert to tuples for baseline
        train_tuples = [(np.array(ex['input']), np.array(ex['output'])) for ex in train_examples]

        # PHASE 2: Seed 50% of population with variations of current pattern
        if current_pattern and len(current_pattern) > 0:
            correction_solver.initialize_population()

            # Seed half the population with small mutations of current pattern
            num_seeded = len(correction_solver.population) // 2
            for i in range(num_seeded):
                # Create small variation: add, remove, or replace one operation
                mutated = self._small_mutation(current_pattern)

                # Convert string names to PrimitiveOperation objects
                from prometheus_arc_fuzzy_fitness import CompositePattern, PrimitiveOperation
                ops = []
                for op_name in mutated:
                    # Find the corresponding PrimitiveOperation from correction_solver's primitives
                    matching_prims = [p for p in correction_solver.primitives if p.name == op_name]
                    if matching_prims:
                        ops.append(matching_prims[0])

                if ops:  # Only set if we found valid operations
                    correction_solver.population[i] = CompositePattern(
                        operations=ops,
                        generation=0
                    )

        # Evolve correction
        result_pattern = correction_solver.evolve_for_task(
            train_tuples,
            max_generations=self.correction_generations
        )

        # Convert to string list
        pattern_names = [op.name for op in result_pattern.operations]

        # With fuzzy fitness, accept patterns with fitness > 0.3 (30% similarity)
        threshold = 0.3 if self.use_fuzzy else 0.0
        return pattern_names if result_pattern.fitness > threshold else None

    def _small_mutation(self, pattern: List[str]) -> List[str]:
        """Create a small mutation of a pattern (for population seeding)"""
        import random

        if not pattern:
            return ['identity']

        mutated = pattern.copy()
        mutation_type = random.choice(['add', 'remove', 'replace', 'identity'])

        if mutation_type == 'add' and len(mutated) < self.max_pattern_length:
            # Add one random primitive
            all_prims = list(self.primitive_methods.keys())
            mutated.append(random.choice(all_prims))
        elif mutation_type == 'remove' and len(mutated) > 1:
            # Remove one random operation
            mutated.pop(random.randint(0, len(mutated) - 1))
        elif mutation_type == 'replace' and len(mutated) > 0:
            # Replace one operation
            pos = random.randint(0, len(mutated) - 1)
            all_prims = list(self.primitive_methods.keys())
            mutated[pos] = random.choice(all_prims)
        # else: identity - return as is

        return mutated

    def _compose_patterns(self,
                         base_pattern: List[str],
                         correction_pattern: List[str],
                         train_examples: List[Dict] = None) -> List[str]:
        """
        Compose correction with base pattern.

        Phase 2 Improvement: Try multiple composition strategies and return best
        """
        max_total_length = self.max_pattern_length * 2

        # Strategy 1: Base then correction (base → correction)
        option1 = base_pattern + correction_pattern
        if len(option1) > max_total_length:
            option1 = option1[:max_total_length]

        # Strategy 2: Correction then base (correction → base)
        option2 = correction_pattern + base_pattern
        if len(option2) > max_total_length:
            option2 = option2[:max_total_length]

        # Strategy 3: Interleave operations
        option3 = []
        max_len = max(len(base_pattern), len(correction_pattern))
        for i in range(max_len):
            if i < len(base_pattern) and len(option3) < max_total_length:
                option3.append(base_pattern[i])
            if i < len(correction_pattern) and len(option3) < max_total_length:
                option3.append(correction_pattern[i])

        # Strategy 4: Just use correction (replace base)
        option4 = correction_pattern
        if len(option4) > max_total_length:
            option4 = option4[:max_total_length]

        # If we have training examples, evaluate all options and return best
        if train_examples:
            options = [option1, option2, option3, option4]
            fitnesses = [self._evaluate_pattern(opt, train_examples) for opt in options]

            best_idx = fitnesses.index(max(fitnesses))
            return options[best_idx]
        else:
            # Fallback to simple concatenation
            return option1

    def _evaluate_pattern(self,
                         pattern: List[str],
                         train_examples: List[Dict]) -> float:
        """
        Evaluate pattern fitness on training examples with FUZZY FITNESS.
        """
        if not pattern:
            return 0.0

        if self.use_fuzzy:
            # FUZZY FITNESS: Use pixel similarity
            total_similarity = 0.0
            for example in train_examples:
                input_grid = np.array(example['input'])
                expected = np.array(example['output'])

                try:
                    predicted = self._apply_pattern_from_names(pattern, input_grid)
                    # Use baseline's fuzzy match method
                    similarity = self.baseline._fuzzy_match(predicted, expected)
                    total_similarity += similarity
                except Exception:
                    total_similarity += 0.0

            return total_similarity / len(train_examples) if train_examples else 0.0
        else:
            # BINARY FITNESS: Exact match only (for comparison)
            correct = 0
            for example in train_examples:
                input_grid = np.array(example['input'])
                expected = np.array(example['output'])

                try:
                    predicted = self._apply_pattern_from_names(pattern, input_grid)
                    if np.array_equal(predicted, expected):
                        correct += 1
                except Exception:
                    pass

            return correct / len(train_examples) if train_examples else 0.0


def main():
    """Test recursive refinement on ARC evaluation set"""
    import argparse

    parser = argparse.ArgumentParser(description='ARC Recursive Refinement Solver')
    parser.add_argument('--split', type=str, default='evaluation',
                       choices=['training', 'evaluation'],
                       help='Dataset split to use')
    parser.add_argument('--num-tasks', type=int, default=None,
                       help='Number of tasks to test (default: all)')
    parser.add_argument('--generations', type=int, default=200,
                       help='Generations for baseline evolution')
    parser.add_argument('--cycles', type=int, default=5,
                       help='Maximum refinement cycles')
    parser.add_argument('--population', type=int, default=100,
                       help='Population size')

    args = parser.parse_args()

    # Load ARC data (use same structure as other scripts)
    from pathlib import Path

    task_dir = Path(f"arc_agi_2/data/{args.split}")
    if not task_dir.exists():
        print(f"Error: {task_dir} not found")
        print("Please ensure ARC-AGI dataset is in arc_agi_2/data/")
        return

    task_files = sorted(task_dir.glob("*.json"))
    if not task_files:
        print(f"Error: No task files found in {task_dir}")
        return

    # Load tasks into dict format
    arc_data = {}
    for task_file in task_files:
        with open(task_file, 'r') as f:
            arc_data[task_file.stem] = json.load(f)

    # Initialize solver with FUZZY FITNESS
    solver = PrometheusARCRecursiveRefinement(
        population_size=args.population,
        max_pattern_length=5,  # Extended from 2
        max_refinement_cycles=args.cycles,
        correction_generations=50,
        use_fuzzy=True  # Enable fuzzy fitness
    )

    # Select tasks
    task_ids = list(arc_data.keys())
    if args.num_tasks:
        task_ids = task_ids[:args.num_tasks]

    print("="*80)
    print("🔬 Prometheus ARC Recursive Refinement - Phase 3 Full (v0.88)")
    print("="*80)
    print(f"Split: {args.split}")
    print(f"Tasks: {len(task_ids)}")
    print(f"Baseline generations: {args.generations}")
    print(f"Max refinement cycles: {args.cycles}")
    print(f"Population: {args.population}")
    print(f"Max pattern length: {solver.max_pattern_length} (extended from 2)")
    print(f"Fitness mode: FUZZY (pixel similarity)")
    print("="*80)
    print()

    # Solve tasks
    results = []
    solved_count = 0
    start_time = time.time()

    for i, task_id in enumerate(task_ids, 1):
        task = arc_data[task_id]
        train_examples = task['train']
        test_examples = task['test']

        print(f"[{i}/{len(task_ids)}] Task {task_id}")

        try:
            result = solver.solve_task(
                train_examples,
                test_examples,
                task_id,
                max_generations=args.generations
            )

            success = result['fitness'] >= 1.0
            if success:
                solved_count += 1

            result_summary = {
                'task_id': task_id,
                'success': bool(success),  # Convert numpy.bool_ to Python bool
                'fitness': float(result['fitness']),  # Convert to Python float
                'pattern': result['pattern'],
                'refinement_cycles': int(result['refinement_cycles']),  # Convert to Python int
                'improvements': [
                    {
                        'cycle': int(step.cycle),
                        'fitness_gain': float(step.fitness_after - step.fitness_before),
                        'failures_fixed': int(step.failures_fixed)
                    }
                    for step in result['history']
                ]
            }
            results.append(result_summary)

            status = "✓ SOLVED" if success else f"✗ Failed (fitness: {result['fitness']:.4f})"
            print(f"  {status}")
            print(f"  Pattern: {result['pattern']}")
            print(f"  Refinement cycles: {result['refinement_cycles']}")
            print()

        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({
                'task_id': task_id,
                'success': False,
                'error': str(e)
            })
            print()

    # Summary
    elapsed = time.time() - start_time
    print("="*80)
    print("📊 RESULTS")
    print("="*80)
    print(f"Solved: {solved_count}/{len(task_ids)} ({solved_count/len(task_ids)*100:.2f}%)")
    print(f"Time: {elapsed:.1f}s ({elapsed/len(task_ids):.1f}s per task)")
    print()

    # Refinement statistics
    total_cycles = sum(r.get('refinement_cycles', 0) for r in results)
    total_improvements = sum(
        len(r.get('improvements', []))
        for r in results
    )
    avg_cycles = total_cycles / len(results) if results else 0

    print("🔄 Refinement Statistics:")
    print(f"  Total cycles run: {total_cycles}")
    print(f"  Successful improvements: {total_improvements}")
    print(f"  Avg cycles per task: {avg_cycles:.1f}")
    print()

    # Save results
    output_file = f'arc_recursive_refinement_{args.split}_{len(task_ids)}tasks.json'
    with open(output_file, 'w') as f:
        json.dump({
            'config': {
                'split': args.split,
                'num_tasks': len(task_ids),
                'generations': args.generations,
                'max_cycles': args.cycles,
                'population': args.population
            },
            'summary': {
                'solved': solved_count,
                'total': len(task_ids),
                'accuracy': solved_count / len(task_ids) if task_ids else 0,
                'time': elapsed,
                'avg_time_per_task': elapsed / len(task_ids) if task_ids else 0
            },
            'results': results
        }, f, indent=2)

    print(f"✅ Results saved to {output_file}")


if __name__ == "__main__":
    main()
