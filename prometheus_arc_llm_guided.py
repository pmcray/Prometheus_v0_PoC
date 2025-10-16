#!/usr/bin/env python3
"""
Prometheus v0.82-local - LLM-Guided ARC Solver (Local Phi-3)

Combines local LLM semantic understanding with symbolic verification.

Key Innovation: Use Phi-3 locally to suggest primitive sequences, then verify symbolically.
This combines the semantic reasoning of LLMs with the precision of symbolic execution.

No cloud API dependency - runs entirely on Jetson Orin via llama.cpp.

Expected Performance: 4-6% on ARC-AGI-1 (vs 1.25% baseline)
"""

import json
import numpy as np
import time
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass

# Import our components
from local_arc_task_analyzer import LocalARCAnalyzer
from prometheus_arc_regularized import ARCPrimitives


@dataclass
class TaskAnalysis:
    """LLM's analysis of an ARC task (compatible with GeminiTaskAnalyzer)"""
    task_type: str = 'unknown'
    key_transformations: List[str] = None
    suggested_primitives: List[str] = None
    confidence: float = 0.5
    reasoning: str = ''

    def __post_init__(self):
        if self.key_transformations is None:
            self.key_transformations = []
        if self.suggested_primitives is None:
            self.suggested_primitives = ['identity']


class PrometheusARCLLMGuided:
    """
    LLM-guided ARC solver that combines semantic understanding with symbolic verification.

    Algorithm:
    1. LLM analyzes task semantics → suggests primitive sequence
    2. Symbolic verifier tests suggestion on training examples
    3. If fails, LLM refines based on failure analysis
    4. Iterate until solution found or max refinements reached
    """

    def __init__(self,
                 use_llm: bool = True,
                 max_refinement_cycles: int = 3,
                 fallback_to_evolution: bool = True,
                 model_path: str = "/home/pmc/ioi_models/Phi-3-mini-4k-instruct-q4.gguf"):
        """
        Args:
            use_llm: Whether to use LLM guidance (local Phi-3 model)
            max_refinement_cycles: How many times to refine LLM suggestions
            fallback_to_evolution: If LLM fails, use baseline evolution
            model_path: Path to local GGUF model file
        """
        self.use_llm = use_llm
        self.max_refinement_cycles = max_refinement_cycles
        self.fallback_to_evolution = fallback_to_evolution

        # Initialize components
        self.primitives = ARCPrimitives()

        # LLM analyzer (only if enabled)
        self.llm_analyzer = None
        if self.use_llm:
            try:
                self.llm_analyzer = LocalARCAnalyzer(model_path=model_path)
                print(f"✅ LLM guidance enabled (local model: {model_path})")
                print(f"✅ {len(self.llm_analyzer.available_primitives)} primitives available")
            except Exception as e:
                print(f"⚠️  LLM initialization failed: {e}")
                if not self.fallback_to_evolution:
                    raise
                print(f"⚠️  Will use fallback evolution")
                self.use_llm = False

        # Baseline evolution solver (for fallback)
        if self.fallback_to_evolution:
            from prometheus_arc_regularized import PrometheusARCRegularized
            self.baseline_solver = PrometheusARCRegularized(
                population_size=100,
                max_pattern_length=2
            )

        # Primitive name -> method mapping
        self.primitive_methods = self._build_primitive_mapping()

        # Statistics
        self.llm_successes = 0
        self.llm_failures = 0
        self.evolution_fallbacks = 0

    def _build_primitive_mapping(self) -> Dict:
        """Build mapping from primitive names to methods"""
        return {
            'identity': ARCPrimitives.identity,
            'rotate_90': ARCPrimitives.rotate_90,
            'rotate_180': ARCPrimitives.rotate_180,
            'rotate_270': ARCPrimitives.rotate_270,
            'flip_h': ARCPrimitives.flip_horizontal,
            'flip_v': ARCPrimitives.flip_vertical,
            'transpose': ARCPrimitives.transpose,
            'diagonal_flip': ARCPrimitives.diagonal_flip,
            'scale_2x': ARCPrimitives.scale_2x,
            'scale_3x': ARCPrimitives.scale_3x,
            'tile_2x2': ARCPrimitives.tile_2x2,
            'tile_3x3': ARCPrimitives.tile_3x3,
            'tile_2x1': ARCPrimitives.tile_2x1,
            'tile_1x3': ARCPrimitives.tile_1x3,
            'gravity_down': ARCPrimitives.gravity_down,
            'gravity_up': ARCPrimitives.gravity_up,
            'fill_zeros': ARCPrimitives.fill_zeros_common,
            'remove_bg': ARCPrimitives.remove_background,
            'swap_01': ARCPrimitives.color_swap_01,
            'color_inc': ARCPrimitives.color_increment,
            'invert': ARCPrimitives.invert_colors,
            'border': ARCPrimitives.border_extract,
            'center': ARCPrimitives.center_extract,
            'pad_1': ARCPrimitives.pad_1,
            'hollow': ARCPrimitives.hollow_objects,
            'crop': ARCPrimitives.crop_to_content,
            'extend_edges': ARCPrimitives.extend_edges,
            'compress_h': ARCPrimitives.compress_horizontal,
            'compress_v': ARCPrimitives.compress_vertical,
            'mirror_h': ARCPrimitives.mirror_horizontal,
            'mirror_v': ARCPrimitives.mirror_vertical,
            'sym_h': ARCPrimitives.symmetrize_horizontal,
            'sym_v': ARCPrimitives.symmetrize_vertical,
            'color_pos': ARCPrimitives.color_map_to_position,
            'downsample': ARCPrimitives.downsample_2x,
            'checkerboard': ARCPrimitives.checkerboard_pattern,
            'overlay_max': ARCPrimitives.overlay_max,
            'count_colors': ARCPrimitives.count_colors_to_value,
            'swap_max_min': ARCPrimitives.swap_max_min_colors,
        }

    def solve_task(self,
                   train_examples: List[Dict],
                   test_examples: List[Dict],
                   task_id: str) -> Dict:
        """
        Solve an ARC task using LLM guidance + symbolic verification.

        Returns:
            {
                'pattern': list of primitive names,
                'fitness': float (0-1),
                'method': 'llm' or 'evolution',
                'llm_analysis': TaskAnalysis object (if LLM used)
            }
        """
        print(f"  Solving task {task_id}...")

        # Try LLM-guided approach
        if self.use_llm and self.llm_analyzer:
            result = self._solve_with_llm(train_examples, task_id)

            if result['fitness'] >= 1.0:
                self.llm_successes += 1
                return result
            else:
                self.llm_failures += 1
                print(f"  ⚠️  LLM guidance didn't find solution (fitness: {result['fitness']:.3f})")

        # Fallback to evolution
        if self.fallback_to_evolution:
            print(f"  → Falling back to baseline evolution...")
            self.evolution_fallbacks += 1
            result = self._solve_with_evolution(train_examples)
            result['method'] = 'evolution_fallback'
            return result
        else:
            # Return best LLM attempt
            return result

    def _solve_with_llm(self, train_examples: List[Dict], task_id: str) -> Dict:
        """Solve using LLM guidance with iterative refinement"""
        # Step 1: Get LLM analysis (local Phi-3)
        print(f"  [Phi-3] Analyzing task semantics...")
        suggested_primitives = self.llm_analyzer.analyze_task(task_id, train_examples)

        # Wrap in TaskAnalysis for compatibility
        analysis = TaskAnalysis(
            task_type='inferred',
            key_transformations=[f"Suggested: {', '.join(suggested_primitives)}"],
            suggested_primitives=suggested_primitives,
            confidence=0.7,  # Default confidence for local model
            reasoning='Local Phi-3 analysis'
        )

        print(f"  [Phi-3] Suggested primitives: {analysis.suggested_primitives}")

        best_pattern = analysis.suggested_primitives
        best_fitness = self._evaluate_pattern(best_pattern, train_examples)

        print(f"  [Phi-3] Initial fitness: {best_fitness:.3f}")

        # Step 2: Iterative refinement if needed
        for cycle in range(1, self.max_refinement_cycles + 1):
            if best_fitness >= 1.0:
                break  # Perfect solution!

            print(f"  [Phi-3] Refinement cycle {cycle}/{self.max_refinement_cycles}...")

            # Try variations of the pattern
            variations = self._generate_pattern_variations(best_pattern)

            for variation in variations:
                fitness = self._evaluate_pattern(variation, train_examples)
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_pattern = variation
                    print(f"  [Phi-3] Improved fitness: {best_fitness:.3f} with {variation}")

                if best_fitness >= 1.0:
                    break  # Perfect!

        return {
            'pattern': best_pattern,
            'fitness': best_fitness,
            'method': 'llm_guided',
            'llm_analysis': analysis
        }

    def _generate_pattern_variations(self, pattern: List[str]) -> List[List[str]]:
        """Generate variations of a pattern to try"""
        variations = []

        # Try adding one primitive
        common_additions = ['rotate_90', 'flip_h', 'flip_v', 'transpose',
                           'invert', 'crop', 'mirror_h', 'mirror_v']
        for prim in common_additions:
            if prim not in pattern:
                variations.append(pattern + [prim])
                variations.append([prim] + pattern)

        # Try removing one primitive (if length > 1)
        if len(pattern) > 1:
            for i in range(len(pattern)):
                variations.append(pattern[:i] + pattern[i+1:])

        # Try swapping order (if length == 2)
        if len(pattern) == 2:
            variations.append([pattern[1], pattern[0]])

        return variations[:20]  # Limit to 20 variations

    def _solve_with_evolution(self, train_examples: List[Dict]) -> Dict:
        """Fallback to baseline evolution"""
        # Convert to tuples for baseline
        train_tuples = [(np.array(ex['input']), np.array(ex['output']))
                       for ex in train_examples]

        result = self.baseline_solver.evolve_for_task(train_tuples, max_generations=100)

        return {
            'pattern': [op.name for op in result.operations],
            'fitness': result.fitness,
            'method': 'evolution'
        }

    def _apply_pattern(self, pattern: List[str], grid: np.ndarray) -> np.ndarray:
        """Apply a pattern (list of primitive names) to a grid"""
        output = grid.copy()
        for prim_name in pattern:
            if prim_name in self.primitive_methods:
                method = self.primitive_methods[prim_name]
                output = method(output)
        return output

    def _evaluate_pattern(self, pattern: List[str], train_examples: List[Dict]) -> float:
        """Evaluate pattern fitness on training examples"""
        if not pattern:
            return 0.0

        correct = 0
        for example in train_examples:
            input_grid = np.array(example['input'])
            expected = np.array(example['output'])

            try:
                predicted = self._apply_pattern(pattern, input_grid)
                if np.array_equal(predicted, expected):
                    correct += 1
            except:
                pass

        return correct / len(train_examples) if train_examples else 0.0

    def get_statistics(self) -> Dict:
        """Get solver statistics"""
        stats = {
            'llm_successes': self.llm_successes,
            'llm_failures': self.llm_failures,
            'evolution_fallbacks': self.evolution_fallbacks,
        }

        if self.llm_analyzer:
            stats.update(self.llm_analyzer.get_statistics())

        return stats


def main():
    """Test local Phi-3 guided solver on ARC evaluation set"""
    import argparse

    parser = argparse.ArgumentParser(description='Local Phi-3 Guided ARC Solver')
    parser.add_argument('--split', type=str, default='evaluation',
                       choices=['training', 'evaluation'],
                       help='Dataset split to use')
    parser.add_argument('--num-tasks', type=int, default=None,
                       help='Number of tasks to test (default: all)')
    parser.add_argument('--no-llm', action='store_true',
                       help='Disable LLM guidance (evolution only)')
    parser.add_argument('--no-fallback', action='store_true',
                       help='Disable evolution fallback')
    parser.add_argument('--model-path', type=str,
                       default='/home/pmc/ioi_models/Phi-3-mini-4k-instruct-q4.gguf',
                       help='Path to local GGUF model')

    args = parser.parse_args()

    # Load ARC data
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
    print("🤖 Prometheus ARC Local-Guided Solver (v0.82-local)")
    print("="*80)
    print(f"Split: {args.split}")
    print(f"Tasks: {len(task_ids)}")
    print(f"LLM guidance: {'Disabled' if args.no_llm else 'Enabled (Phi-3 local)'}")
    print(f"Evolution fallback: {'Disabled' if args.no_fallback else 'Enabled'}")
    if not args.no_llm:
        print(f"Model: {args.model_path}")
    print("="*80)
    print()

    # Initialize solver
    solver = PrometheusARCLLMGuided(
        use_llm=not args.no_llm,
        max_refinement_cycles=3,
        fallback_to_evolution=not args.no_fallback,
        model_path=args.model_path
    )

    # Solve tasks
    results = []
    solved_count = 0
    llm_solved = 0
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
                if result['method'] == 'llm_guided':
                    llm_solved += 1

            result_summary = {
                'task_id': task_id,
                'success': success,
                'fitness': result['fitness'],
                'pattern': result['pattern'],
                'method': result['method']
            }
            results.append(result_summary)

            status = "✓ SOLVED" if success else f"✗ Failed (fitness: {result['fitness']:.3f})"
            method = f"({result['method']})"
            print(f"  {status} {method}")
            print(f"  Pattern: {result['pattern']}")
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
    print(f"  LLM-guided: {llm_solved}/{solved_count} ({llm_solved/solved_count*100:.1f}% of solved)" if solved_count > 0 else "  LLM-guided: 0")
    print(f"Time: {elapsed:.1f}s ({elapsed/len(task_ids):.1f}s per task)")
    print()

    # Statistics
    stats = solver.get_statistics()
    print("🤖 Phi-3 Statistics:")
    print(f"  Successes: {stats.get('llm_successes', 0)}")
    print(f"  Failures: {stats.get('llm_failures', 0)}")
    print(f"  Evolution fallbacks: {stats.get('evolution_fallbacks', 0)}")
    if 'analyses_count' in stats:
        print(f"  Analyses performed: {stats['analyses_count']}")
        print(f"  Success rate: {stats.get('success_rate', 0):.1%}")
    print()

    # Save results
    output_file = f'arc_llm_guided_{args.split}_{len(task_ids)}tasks.json'
    with open(output_file, 'w') as f:
        json.dump({
            'config': {
                'split': args.split,
                'num_tasks': len(task_ids),
                'use_llm': not args.no_llm,
                'fallback_to_evolution': not args.no_fallback
            },
            'summary': {
                'solved': solved_count,
                'llm_solved': llm_solved,
                'total': len(task_ids),
                'accuracy': solved_count / len(task_ids) if task_ids else 0,
                'time': elapsed
            },
            'statistics': stats,
            'results': results
        }, f, indent=2)

    print(f"✅ Results saved to {output_file}")


if __name__ == "__main__":
    main()
