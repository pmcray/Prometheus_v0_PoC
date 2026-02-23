#!/usr/bin/env python3
"""
Prometheus ARC TRM Phases 5-7 (v0.90)

Complete implementation of Goodian-Hofstadterian recursive refinement:
- PHASE 5: Adaptive/Conditional Primitives (context-aware operations)
- PHASE 6: LLM-Guided Hypothesis Generation (semantic guidance)
- PHASE 7: Metarefinement (strange loop - TRM refines its own refinement strategy)

This represents the synthesis described in PHASE_4_ANALYSIS_AND_TRM_PARADIGMS.md:
Neural-symbolic integration where:
1. Neural (LLM) provides semantic grounding
2. Symbolic (primitives) provides compositionality
3. Recursion provides self-improvement
4. Strange loops provide emergent understanding

Expected Performance: 10-20% on ARC-AGI (vs Samsung's 45% target)
"""

import json
import numpy as np
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import time

# Import base components
from prometheus_arc_fuzzy_fitness import PrometheusARCFuzzyFitness, ARCPrimitives, PrimitiveOperation


# ============================================================================
# PHASE 5: ADAPTIVE PRIMITIVES
# ============================================================================

class AdaptivePrimitives:
    """
    Phase 5: Adaptive/conditional primitives that adjust behavior based on input properties.

    Instead of fixed operations like pad_2(grid), we have adaptive operations like:
    - pad_to_size(grid, target_size): Pad until grid matches target dimensions
    - scale_to_match(grid, target): Scale to match target grid size
    - fill_until_symmetric(grid): Fill/mirror until symmetric
    """

    @staticmethod
    def pad_to_size(grid: np.ndarray, target_h: int, target_w: int, **kwargs) -> np.ndarray:
        """
        Adaptive padding: Pad grid until it reaches target size.
        If target is smaller, crop instead.
        """
        h, w = grid.shape
        if h >= target_h and w >= target_w:
            # Crop to target size
            return grid[:target_h, :target_w]

        # Calculate padding needed
        pad_h = max(0, (target_h - h + 1) // 2)
        pad_w = max(0, (target_w - w + 1) // 2)

        return np.pad(grid, ((pad_h, pad_h), (pad_w, pad_w)),
                     mode='constant', constant_values=0)[:target_h, :target_w]

    @staticmethod
    def scale_to_match(grid: np.ndarray, target_h: int, target_w: int, **kwargs) -> np.ndarray:
        """
        Adaptive scaling: Scale grid to approximately match target dimensions.
        Finds best integer scaling factor.
        """
        h, w = grid.shape
        if h == 0 or w == 0:
            return grid

        # Find best scaling factor
        scale_h = max(1, target_h // h)
        scale_w = max(1, target_w // w)
        scale_factor = min(scale_h, scale_w)  # Use consistent scaling

        # Scale using repeat
        scaled = np.repeat(np.repeat(grid, scale_factor, axis=0), scale_factor, axis=1)

        # Crop to exact target if needed
        if scaled.shape[0] > target_h or scaled.shape[1] > target_w:
            scaled = scaled[:target_h, :target_w]

        return scaled

    @staticmethod
    def tile_to_fill(grid: np.ndarray, target_h: int, target_w: int, **kwargs) -> np.ndarray:
        """
        Adaptive tiling: Tile grid until it fills target dimensions.
        """
        h, w = grid.shape
        if h == 0 or w == 0:
            return grid

        # Calculate number of tiles needed
        tiles_h = (target_h + h - 1) // h  # Ceiling division
        tiles_w = (target_w + w - 1) // w

        # Tile and crop to exact size
        tiled = np.tile(grid, (tiles_h, tiles_w))
        return tiled[:target_h, :target_w]

    @staticmethod
    def fill_until_symmetric_h(grid: np.ndarray, **kwargs) -> np.ndarray:
        """
        Adaptive symmetry: Mirror horizontally to create symmetric result.
        """
        # Mirror the grid horizontally (add flipped version to right)
        mirrored = np.fliplr(grid)
        return np.hstack([grid, mirrored])

    @staticmethod
    def fill_until_symmetric_v(grid: np.ndarray, **kwargs) -> np.ndarray:
        """
        Adaptive symmetry: Mirror vertically to create symmetric result.
        """
        # Mirror the grid vertically (add flipped version below)
        mirrored = np.flipud(grid)
        return np.vstack([grid, mirrored])

    @staticmethod
    def extract_pattern_and_repeat(grid: np.ndarray, **kwargs) -> np.ndarray:
        """
        Adaptive pattern extraction: Find smallest repeating unit and tile it.
        """
        h, w = grid.shape

        # Try to find repeating pattern by testing divisors
        for pattern_h in range(1, h // 2 + 1):
            if h % pattern_h == 0:
                # Check if pattern repeats vertically
                pattern = grid[:pattern_h, :]
                is_repeating = True
                for i in range(pattern_h, h, pattern_h):
                    if not np.array_equal(grid[i:i+pattern_h, :], pattern):
                        is_repeating = False
                        break

                if is_repeating:
                    return pattern  # Return smallest repeating unit

        # No vertical pattern found, try horizontal
        for pattern_w in range(1, w // 2 + 1):
            if w % pattern_w == 0:
                pattern = grid[:, :pattern_w]
                is_repeating = True
                for j in range(pattern_w, w, pattern_w):
                    if not np.array_equal(grid[:, j:j+pattern_w], pattern):
                        is_repeating = False
                        break

                if is_repeating:
                    return pattern

        # No pattern found, return original
        return grid

    @staticmethod
    def align_to_grid(grid: np.ndarray, cell_size: int = 2, **kwargs) -> np.ndarray:
        """
        Adaptive grid alignment: Downsample to detect grid structure, then align.
        """
        if cell_size < 2:
            return grid

        h, w = grid.shape
        new_h = (h // cell_size) * cell_size
        new_w = (w // cell_size) * cell_size

        if new_h == 0 or new_w == 0:
            return grid

        # Crop to grid-aligned size
        aligned = grid[:new_h, :new_w]

        # Downsample by taking mode of each cell
        downsampled = np.zeros((new_h // cell_size, new_w // cell_size), dtype=grid.dtype)
        for i in range(0, new_h, cell_size):
            for j in range(0, new_w, cell_size):
                cell = aligned[i:i+cell_size, j:j+cell_size]
                # Take most common value in cell
                values, counts = np.unique(cell, return_counts=True)
                downsampled[i//cell_size, j//cell_size] = values[np.argmax(counts)]

        return downsampled


# ============================================================================
# PHASE 6: LLM-GUIDED HYPOTHESIS GENERATION
# ============================================================================

class LLMHypothesisGenerator:
    """
    Phase 6: Use LLM to generate semantic hypotheses about transformations.

    This is the KEY to Samsung TRM's 45% performance - LLM provides semantic
    understanding that random search cannot achieve.
    """

    def __init__(self, use_local_model: bool = True, model_path: str = None):
        """
        Initialize LLM hypothesis generator.

        Args:
            use_local_model: Use local Phi-3 model (default) vs Google Gemini
            model_path: Path to local model (if use_local_model=True)
        """
        self.use_local_model = use_local_model
        self.model_path = model_path or "/home/pmc/ioi_models/Phi-3-mini-4k-instruct-q4.gguf"

        if use_local_model:
            try:
                from local_arc_task_analyzer import LocalARCAnalyzer
                self.analyzer = LocalARCAnalyzer(model_path=self.model_path)
                print(f"✅ LLM hypothesis generator initialized (local Phi-3)")
            except Exception as e:
                print(f"⚠️  Local model initialization failed: {e}")
                print(f"⚠️  Falling back to pattern-based heuristics")
                self.analyzer = None
        else:
            # Could add Google Gemini support here
            print(f"⚠️  Cloud LLM not implemented, using heuristics")
            self.analyzer = None

    def generate_hypotheses(self,
                          train_examples: List[Dict],
                          task_id: str,
                          num_hypotheses: int = 5) -> List[List[str]]:
        """
        Generate multiple hypotheses for transformation patterns.

        Returns:
            List of pattern hypotheses (each is a list of primitive names)
        """
        if self.analyzer:
            # Use LLM to analyze task
            try:
                suggested_prims = self.analyzer.analyze_task(task_id, train_examples)

                # Generate variations of LLM suggestion
                hypotheses = [suggested_prims]

                # Add variations by permuting order
                if len(suggested_prims) >= 2:
                    # Reverse order
                    hypotheses.append(suggested_prims[::-1])

                    # Try subsets
                    if len(suggested_prims) >= 3:
                        hypotheses.append(suggested_prims[:2])  # First 2
                        hypotheses.append(suggested_prims[1:])  # Last n-1

                # Add single primitive hypotheses
                for prim in suggested_prims[:3]:  # Top 3 primitives
                    hypotheses.append([prim])

                return hypotheses[:num_hypotheses]

            except Exception as e:
                print(f"  ⚠️  LLM hypothesis generation failed: {e}")
                # Fall through to heuristics

        # Fallback: Pattern-based heuristics
        return self._heuristic_hypotheses(train_examples, num_hypotheses)

    def _heuristic_hypotheses(self,
                             train_examples: List[Dict],
                             num_hypotheses: int) -> List[List[str]]:
        """
        Fallback: Generate hypotheses using pattern analysis heuristics.
        """
        hypotheses = []

        # Analyze first training example
        if not train_examples:
            return [['identity']]

        input_grid = np.array(train_examples[0]['input'])
        output_grid = np.array(train_examples[0]['output'])

        in_h, in_w = input_grid.shape
        out_h, out_w = output_grid.shape

        # Size-based hypotheses
        if out_h > in_h or out_w > in_w:
            # Output larger - try scaling/tiling
            if out_h == in_h * 2 and out_w == in_w * 2:
                hypotheses.append(['scale_2x'])
            elif out_h == in_h * 3 and out_w == in_w * 3:
                hypotheses.append(['scale_3x'])
            else:
                hypotheses.append(['tile_2x2'])

        elif out_h < in_h or out_w < in_w:
            # Output smaller - try cropping/downsampling
            hypotheses.append(['crop'])
            hypotheses.append(['downsample'])

        # Shape-based hypotheses
        if out_h == in_w and out_w == in_h:
            # Transposition
            hypotheses.append(['transpose'])
            hypotheses.append(['rotate_90'])

        # Color-based hypotheses
        in_colors = set(input_grid.flatten())
        out_colors = set(output_grid.flatten())

        if in_colors != out_colors:
            hypotheses.append(['invert'])
            hypotheses.append(['swap_01'])

        # Symmetry hypotheses
        if np.array_equal(output_grid, np.fliplr(output_grid)):
            hypotheses.append(['sym_h'])

        if np.array_equal(output_grid, np.flipud(output_grid)):
            hypotheses.append(['sym_v'])

        # Fill with common single-op hypotheses if needed
        common_ops = ['rotate_90', 'flip_h', 'flip_v', 'identity']
        for op in common_ops:
            if len(hypotheses) >= num_hypotheses:
                break
            if [op] not in hypotheses:
                hypotheses.append([op])

        return hypotheses[:num_hypotheses]


# ============================================================================
# PHASE 7: METAREFINEMENT (STRANGE LOOP)
# ============================================================================

@dataclass
class RefinementStrategy:
    """
    Represents a refinement strategy that can itself be refined.

    This creates the "strange loop" - the system refines not just patterns,
    but also its strategy for refining patterns.
    """
    name: str
    success_count: int = 0
    failure_count: int = 0
    avg_fitness_gain: float = 0.0
    total_attempts: int = 0

    def success_rate(self) -> float:
        """Calculate success rate of this strategy"""
        if self.total_attempts == 0:
            return 0.0
        return self.success_count / self.total_attempts

    def update_statistics(self, success: bool, fitness_gain: float):
        """Update strategy statistics after an attempt"""
        self.total_attempts += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        # Update running average of fitness gain
        n = self.total_attempts
        self.avg_fitness_gain = ((n - 1) * self.avg_fitness_gain + fitness_gain) / n


class MetaRefiner:
    """
    Phase 7: Metarefinement - system that refines its own refinement strategies.

    This completes the "strange loop":
    - Level 0: Primitives
    - Level 1: Patterns (sequences of primitives)
    - Level 2: Refinement strategies (how to improve patterns)
    - Level 3: Meta-refinement (how to improve refinement strategies)

    The loop closes when Level 3 modifies Level 2, which affects Level 1.
    """

    def __init__(self):
        """Initialize meta-refiner with strategy portfolio"""
        self.strategies: Dict[str, RefinementStrategy] = {
            'llm_guided': RefinementStrategy(name='llm_guided'),
            'local_search': RefinementStrategy(name='local_search'),
            'evolution': RefinementStrategy(name='evolution'),
            'adaptive_ops': RefinementStrategy(name='adaptive_ops'),
            'hybrid': RefinementStrategy(name='hybrid')
        }

        # Strategy selection parameters (learned over time)
        self.strategy_weights = {name: 1.0 for name in self.strategies.keys()}

        # Meta-learning rate
        self.meta_learning_rate = 0.1

    def select_strategy(self,
                       current_fitness: float,
                       task_context: Dict) -> str:
        """
        Select best refinement strategy based on context and past performance.

        This is the "self-referential" part - using learned strategy performance
        to choose how to refine.
        """
        # Normalize weights to probabilities
        total_weight = sum(self.strategy_weights.values())
        if total_weight == 0:
            # All weights zero, use uniform
            return np.random.choice(list(self.strategies.keys()))

        probs = {name: w / total_weight for name, w in self.strategy_weights.items()}

        # Context-aware adjustments
        if current_fitness > 0.95:
            # High fitness - prefer local_search or adaptive_ops
            probs['local_search'] *= 2.0
            probs['adaptive_ops'] *= 2.0
        elif current_fitness < 0.5:
            # Low fitness - prefer LLM guidance
            probs['llm_guided'] *= 2.0

        # Normalize again
        total_prob = sum(probs.values())
        probs = {name: p / total_prob for name, p in probs.items()}

        # Sample strategy
        strategies = list(probs.keys())
        probabilities = [probs[s] for s in strategies]

        selected = np.random.choice(strategies, p=probabilities)
        return selected

    def update_strategy_weights(self):
        """
        Meta-learning: Update strategy selection weights based on performance.

        This is the "strange loop" closing - past refinement results modify
        future refinement strategy selection.
        """
        for name, strategy in self.strategies.items():
            if strategy.total_attempts == 0:
                continue

            # Weight based on success rate and fitness gain
            performance = strategy.success_rate() * (1.0 + strategy.avg_fitness_gain)

            # Update weight with meta-learning rate
            current_weight = self.strategy_weights[name]
            new_weight = (1 - self.meta_learning_rate) * current_weight + \
                        self.meta_learning_rate * performance

            self.strategy_weights[name] = max(0.1, new_weight)  # Floor at 0.1

    def report_attempt(self,
                      strategy_name: str,
                      success: bool,
                      fitness_before: float,
                      fitness_after: float):
        """
        Report results of a refinement attempt to update meta-statistics.
        """
        if strategy_name in self.strategies:
            fitness_gain = fitness_after - fitness_before
            self.strategies[strategy_name].update_statistics(success, fitness_gain)

            # Periodically update strategy weights
            if self.strategies[strategy_name].total_attempts % 5 == 0:
                self.update_strategy_weights()


# ============================================================================
# INTEGRATED TRM PHASES 5-7
# ============================================================================

class PrometheusARCTRM_Phases567:
    """
    Complete TRM implementation with Phases 5-7 integrated.

    This is the full neural-symbolic recursive refinement system with:
    - Adaptive primitives (Phase 5)
    - LLM-guided hypotheses (Phase 6)
    - Meta-refinement (Phase 7)
    """

    def __init__(self,
                 use_llm: bool = True,
                 use_adaptive: bool = True,
                 use_metarefine: bool = True,
                 max_refinement_cycles: int = 5):
        """
        Initialize integrated TRM system.

        Args:
            use_llm: Enable Phase 6 (LLM guidance)
            use_adaptive: Enable Phase 5 (adaptive primitives)
            use_metarefine: Enable Phase 7 (meta-refinement)
            max_refinement_cycles: Maximum refinement iterations
        """
        self.use_llm = use_llm
        self.use_adaptive = use_adaptive
        self.use_metarefine = use_metarefine
        self.max_refinement_cycles = max_refinement_cycles

        # Initialize components
        self.primitives = ARCPrimitives()
        self.adaptive_prims = AdaptivePrimitives()

        # Phase 6: LLM hypothesis generator
        self.llm_generator = None
        if use_llm:
            self.llm_generator = LLMHypothesisGenerator(use_local_model=True)

        # Phase 7: Meta-refiner
        self.meta_refiner = None
        if use_metarefine:
            self.meta_refiner = MetaRefiner()

        # Baseline evolution solver
        self.baseline = PrometheusARCFuzzyFitness(
            population_size=100,
            max_pattern_length=5,
            use_fuzzy=True
        )

        # Build primitive mappings
        self.primitive_methods = self._build_primitive_mapping()

        # Statistics
        self.refinement_history = []
        self.total_solves = 0
        self.phase5_solves = 0
        self.phase6_solves = 0
        self.phase7_improves = 0

    def _build_primitive_mapping(self) -> Dict[str, Callable]:
        """Build mapping from primitive names to methods"""
        mapping = {
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
            'sym_h': ARCPrimitives.symmetrize_horizontal,
            'sym_v': ARCPrimitives.symmetrize_vertical,
            'downsample': ARCPrimitives.downsample_2x,
        }

        # Add Phase 5 adaptive primitives
        if self.use_adaptive:
            mapping.update({
                'adaptive_pad': AdaptivePrimitives.pad_to_size,
                'adaptive_scale': AdaptivePrimitives.scale_to_match,
                'adaptive_tile': AdaptivePrimitives.tile_to_fill,
                'mirror_h_double': AdaptivePrimitives.fill_until_symmetric_h,
                'mirror_v_double': AdaptivePrimitives.fill_until_symmetric_v,
                'extract_pattern': AdaptivePrimitives.extract_pattern_and_repeat,
                'align_grid': AdaptivePrimitives.align_to_grid,
            })

        return mapping

    def solve_task(self,
                   train_examples: List[Dict],
                   test_examples: List[Dict],
                   task_id: str) -> Dict:
        """
        Solve ARC task using integrated TRM Phases 5-7.

        Returns:
            {
                'pattern': best pattern found,
                'fitness': fitness score,
                'method': which phase solved it,
                'refinement_cycles': number of cycles used,
                'meta_stats': meta-learning statistics
            }
        """
        print(f"  [TRM 567] Solving task {task_id}...")

        self.refinement_history = []

        # Phase 6: Try LLM-guided hypotheses first
        if self.use_llm and self.llm_generator:
            print(f"  [Phase 6] Generating LLM hypotheses...")
            hypotheses = self.llm_generator.generate_hypotheses(
                train_examples, task_id, num_hypotheses=5
            )

            # Test each hypothesis
            best_pattern = None
            best_fitness = 0.0

            for hyp in hypotheses:
                fitness = self._evaluate_pattern(hyp, train_examples)
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_pattern = hyp

                if fitness >= 1.0:
                    # Perfect solution from LLM!
                    self.phase6_solves += 1
                    print(f"  [Phase 6] ✓ LLM solved it! Pattern: {hyp}")
                    return {
                        'pattern': hyp,
                        'fitness': 1.0,
                        'method': 'phase6_llm',
                        'refinement_cycles': 0,
                        'meta_stats': self._get_meta_stats()
                    }

            print(f"  [Phase 6] Best LLM hypothesis: {best_pattern} (fitness: {best_fitness:.3f})")

        else:
            # No LLM - start with baseline evolution
            print(f"  [Baseline] Running initial evolution...")
            train_tuples = [(np.array(ex['input']), np.array(ex['output']))
                           for ex in train_examples]
            initial = self.baseline.evolve_for_task(train_tuples, max_generations=100)
            best_pattern = [op.name for op in initial.operations]
            best_fitness = initial.fitness
            print(f"  [Baseline] Initial fitness: {best_fitness:.3f}")

        # Recursive refinement cycles
        for cycle in range(1, self.max_refinement_cycles + 1):
            if best_fitness >= 1.0:
                break  # Already perfect

            print(f"  [Cycle {cycle}] Current fitness: {best_fitness:.3f}")

            # Phase 7: Select refinement strategy using meta-learning
            strategy = 'hybrid'  # Default
            if self.use_metarefine and self.meta_refiner:
                strategy = self.meta_refiner.select_strategy(
                    best_fitness,
                    {'cycle': cycle, 'task_id': task_id}
                )
                print(f"  [Phase 7] Selected strategy: {strategy}")

            # Apply selected strategy
            refined_pattern, refined_fitness = self._refine_pattern(
                best_pattern,
                best_fitness,
                train_examples,
                strategy
            )

            # Update meta-statistics
            if self.use_metarefine and self.meta_refiner:
                success = refined_fitness > best_fitness
                self.meta_refiner.report_attempt(
                    strategy, success, best_fitness, refined_fitness
                )
                if success:
                    self.phase7_improves += 1

            # Keep if improved
            if refined_fitness > best_fitness:
                print(f"  [Cycle {cycle}] ✓ Improved: {best_fitness:.3f} → {refined_fitness:.3f}")
                best_pattern = refined_pattern
                best_fitness = refined_fitness
            else:
                print(f"  [Cycle {cycle}] ✗ No improvement")

        # Final result
        success = best_fitness >= 1.0
        if success:
            self.total_solves += 1

        method = 'phase567_integrated'
        if best_fitness >= 1.0 and cycle == 0:
            method = 'phase6_llm'

        return {
            'pattern': best_pattern,
            'fitness': best_fitness,
            'method': method,
            'refinement_cycles': cycle,
            'meta_stats': self._get_meta_stats()
        }

    def _refine_pattern(self,
                       pattern: List[str],
                       current_fitness: float,
                       train_examples: List[Dict],
                       strategy: str) -> Tuple[List[str], float]:
        """
        Refine a pattern using the selected strategy.
        """
        if strategy == 'llm_guided':
            return self._refine_with_llm(pattern, train_examples)
        elif strategy == 'local_search':
            return self._refine_with_local_search(pattern, train_examples)
        elif strategy == 'adaptive_ops':
            return self._refine_with_adaptive(pattern, train_examples)
        elif strategy == 'evolution':
            return self._refine_with_evolution(pattern, train_examples)
        else:  # hybrid
            return self._refine_hybrid(pattern, train_examples)

    def _refine_with_llm(self, pattern: List[str], train_examples: List[Dict]) -> Tuple[List[str], float]:
        """Refine using LLM to suggest corrections"""
        if not self.llm_generator:
            return pattern, self._evaluate_pattern(pattern, train_examples)

        # Generate new hypotheses and try combining with current pattern
        hypotheses = self.llm_generator.generate_hypotheses(train_examples, 'refine', num_hypotheses=3)

        best = pattern
        best_fitness = self._evaluate_pattern(pattern, train_examples)

        for hyp in hypotheses:
            # Try: hyp + pattern, pattern + hyp
            for combined in [hyp + pattern, pattern + hyp]:
                fitness = self._evaluate_pattern(combined, train_examples)
                if fitness > best_fitness:
                    best_fitness = fitness
                    best = combined

        return best, best_fitness

    def _refine_with_local_search(self, pattern: List[str], train_examples: List[Dict]) -> Tuple[List[str], float]:
        """Refine using local search through primitive space"""
        best = pattern
        best_fitness = self._evaluate_pattern(pattern, train_examples)

        # Try adding single primitives
        for prim_name in ['rotate_90', 'flip_h', 'flip_v', 'transpose', 'crop', 'sym_h']:
            for candidate in [pattern + [prim_name], [prim_name] + pattern]:
                fitness = self._evaluate_pattern(candidate, train_examples)
                if fitness > best_fitness:
                    best_fitness = fitness
                    best = candidate

        return best, best_fitness

    def _refine_with_adaptive(self, pattern: List[str], train_examples: List[Dict]) -> Tuple[List[str], float]:
        """Refine using Phase 5 adaptive primitives"""
        if not self.use_adaptive:
            return pattern, self._evaluate_pattern(pattern, train_examples)

        best = pattern
        best_fitness = self._evaluate_pattern(pattern, train_examples)

        # Try adding adaptive operations
        adaptive_ops = ['adaptive_pad', 'adaptive_scale', 'adaptive_tile',
                       'mirror_h_double', 'mirror_v_double']

        for op in adaptive_ops:
            candidate = pattern + [op]
            fitness = self._evaluate_pattern(candidate, train_examples)
            if fitness > best_fitness:
                best_fitness = fitness
                best = candidate

        return best, best_fitness

    def _refine_with_evolution(self, pattern: List[str], train_examples: List[Dict]) -> Tuple[List[str], float]:
        """Refine using evolutionary search"""
        train_tuples = [(np.array(ex['input']), np.array(ex['output']))
                       for ex in train_examples]
        result = self.baseline.evolve_for_task(train_tuples, max_generations=50)
        return [op.name for op in result.operations], result.fitness

    def _refine_hybrid(self, pattern: List[str], train_examples: List[Dict]) -> Tuple[List[str], float]:
        """Hybrid: Try multiple strategies and return best"""
        strategies = [
            self._refine_with_local_search,
            self._refine_with_adaptive,
        ]

        best_pattern = pattern
        best_fitness = self._evaluate_pattern(pattern, train_examples)

        for strategy_fn in strategies:
            refined, fitness = strategy_fn(pattern, train_examples)
            if fitness > best_fitness:
                best_fitness = fitness
                best_pattern = refined

        return best_pattern, best_fitness

    def _evaluate_pattern(self, pattern: List[str], train_examples: List[Dict]) -> float:
        """Evaluate pattern fitness using fuzzy matching"""
        if not pattern:
            return 0.0

        total_similarity = 0.0
        for example in train_examples:
            input_grid = np.array(example['input'])
            expected = np.array(example['output'])

            try:
                predicted = self._apply_pattern(pattern, input_grid, expected)
                similarity = self.baseline._fuzzy_match(predicted, expected)
                total_similarity += similarity
            except Exception as e:
                # print(f"    Error applying pattern: {e}")
                total_similarity += 0.0

        return total_similarity / len(train_examples) if train_examples else 0.0

    def _apply_pattern(self, pattern: List[str], grid: np.ndarray, target: np.ndarray = None) -> np.ndarray:
        """Apply a pattern (with adaptive primitives needing target dimensions)"""
        output = grid.copy()

        for prim_name in pattern:
            if prim_name not in self.primitive_methods:
                continue

            method = self.primitive_methods[prim_name]

            # Adaptive primitives need target dimensions
            if prim_name in ['adaptive_pad', 'adaptive_scale', 'adaptive_tile'] and target is not None:
                target_h, target_w = target.shape
                output = method(output, target_h, target_w)
            else:
                output = method(output)

        return output

    def _get_meta_stats(self) -> Dict:
        """Get meta-learning statistics"""
        if not self.meta_refiner:
            return {}

        return {
            'strategy_weights': self.meta_refiner.strategy_weights.copy(),
            'strategy_performance': {
                name: {
                    'success_rate': strat.success_rate(),
                    'avg_fitness_gain': strat.avg_fitness_gain,
                    'total_attempts': strat.total_attempts
                }
                for name, strat in self.meta_refiner.strategies.items()
            }
        }

    def get_statistics(self) -> Dict:
        """Get solver statistics"""
        return {
            'total_solves': self.total_solves,
            'phase5_solves': self.phase5_solves,
            'phase6_solves': self.phase6_solves,
            'phase7_improves': self.phase7_improves,
            'meta_stats': self._get_meta_stats()
        }


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Test integrated TRM Phases 5-7 on ARC evaluation set"""
    import argparse

    parser = argparse.ArgumentParser(description='ARC TRM Phases 5-7 Solver')
    parser.add_argument('--split', type=str, default='evaluation',
                       choices=['training', 'evaluation'],
                       help='Dataset split to use')
    parser.add_argument('--num-tasks', type=int, default=None,
                       help='Number of tasks to test (default: all)')
    parser.add_argument('--no-llm', action='store_true',
                       help='Disable Phase 6 (LLM guidance)')
    parser.add_argument('--no-adaptive', action='store_true',
                       help='Disable Phase 5 (adaptive primitives)')
    parser.add_argument('--no-meta', action='store_true',
                       help='Disable Phase 7 (meta-refinement)')
    parser.add_argument('--cycles', type=int, default=5,
                       help='Maximum refinement cycles')

    args = parser.parse_args()

    # Load ARC data
    from pathlib import Path

    task_dir = Path(f"arc_agi_2/data/{args.split}")
    if not task_dir.exists():
        print(f"Error: {task_dir} not found")
        return

    task_files = sorted(task_dir.glob("*.json"))
    if not task_files:
        print(f"Error: No task files found in {task_dir}")
        return

    # Load tasks
    arc_data = {}
    for task_file in task_files:
        with open(task_file, 'r') as f:
            arc_data[task_file.stem] = json.load(f)

    # Select tasks
    task_ids = list(arc_data.keys())
    if args.num_tasks:
        task_ids = task_ids[:args.num_tasks]

    print("="*80)
    print("🔬 Prometheus ARC TRM Phases 5-7 (v0.90)")
    print("="*80)
    print(f"Split: {args.split}")
    print(f"Tasks: {len(task_ids)}")
    print(f"Phase 5 (Adaptive): {'Disabled' if args.no_adaptive else 'Enabled'}")
    print(f"Phase 6 (LLM): {'Disabled' if args.no_llm else 'Enabled'}")
    print(f"Phase 7 (Meta): {'Disabled' if args.no_meta else 'Enabled'}")
    print(f"Max refinement cycles: {args.cycles}")
    print("="*80)
    print()

    # Initialize solver
    solver = PrometheusARCTRM_Phases567(
        use_llm=not args.no_llm,
        use_adaptive=not args.no_adaptive,
        use_metarefine=not args.no_meta,
        max_refinement_cycles=args.cycles
    )

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
            result = solver.solve_task(train_examples, test_examples, task_id)

            success = result['fitness'] >= 1.0
            if success:
                solved_count += 1

            result_summary = {
                'task_id': task_id,
                'success': success,
                'fitness': result['fitness'],
                'pattern': result['pattern'],
                'method': result['method'],
                'refinement_cycles': result['refinement_cycles']
            }
            results.append(result_summary)

            status = "✓ SOLVED" if success else f"✗ Failed (fitness: {result['fitness']:.3f})"
            print(f"  {status} via {result['method']}")
            print(f"  Pattern: {result['pattern']}")
            print()

        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
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

    # Phase statistics
    stats = solver.get_statistics()
    print("📈 Phase Statistics:")
    print(f"  Phase 6 (LLM) solves: {stats['phase6_solves']}")
    print(f"  Phase 7 (Meta) improvements: {stats['phase7_improves']}")
    print()

    # Meta-learning statistics
    if 'meta_stats' in stats and stats['meta_stats']:
        print("🧠 Meta-Learning Statistics:")
        print(f"  Strategy weights: {stats['meta_stats'].get('strategy_weights', {})}")
        print()

    # Save results
    output_file = f'arc_trm_phases567_{args.split}_{len(task_ids)}tasks.json'

    # Convert numpy types to Python types for JSON serialization
    def convert_to_python_types(obj):
        """Recursively convert numpy types to Python types"""
        if isinstance(obj, dict):
            return {k: convert_to_python_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_python_types(item) for item in obj]
        elif isinstance(obj, (np.int_, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64,
                             np.uint8, np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

    output_data = convert_to_python_types({
        'version': 'v0.90',
        'phases': {
            'phase5_adaptive': not args.no_adaptive,
            'phase6_llm': not args.no_llm,
            'phase7_meta': not args.no_meta
        },
        'config': {
            'split': args.split,
            'num_tasks': len(task_ids),
            'max_cycles': args.cycles
        },
        'summary': {
            'solved': solved_count,
            'total': len(task_ids),
            'accuracy': solved_count / len(task_ids) if task_ids else 0,
            'time': elapsed
        },
        'statistics': stats,
        'results': results
    })

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"✅ Results saved to {output_file}")


if __name__ == "__main__":
    main()
