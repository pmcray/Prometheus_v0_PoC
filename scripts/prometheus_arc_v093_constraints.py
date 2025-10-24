#!/usr/bin/env python3
"""
Prometheus ARC v0.93: Constraint-Based Search

Based on v0.92 baseline, this version adds constraint extraction to dramatically
reduce the search space from ~79M to ~100K patterns.

Key Innovation:
- Extract task constraints (size, color, symmetry, object)
- Filter primitives based on constraints
- Reduce search space by 99%+ while maintaining accuracy

Expected Performance: 10-15% solve rate (vs 5-10% in v0.92)
"""

import json
import numpy as np
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from collections import Counter, defaultdict
import time
from scipy.ndimage import label

# Import v0.92 baseline
from prometheus_arc_v092_baseline import (
    PrometheusARC_v092_Baseline,
    hybrid_fitness,
    get_generation_budget,
    BASELINE_PRIMITIVES,
    CORRECTION_PRIMITIVES
)


# ============================================================================
# CONSTRAINT EXTRACTION
# ============================================================================

class ConstraintExtractor:
    """
    Extract constraints from ARC task training examples.

    Constraints identify what transformations are POSSIBLE given the
    task structure, reducing search space by eliminating incompatible primitives.
    """

    def __init__(self):
        self.extracted_constraints = {}
        self.confidence_scores = {}

    def extract_all_constraints(self, task: Dict) -> Dict[str, str]:
        """
        Extract all constraint types from task.

        Args:
            task: Dict with 'train' key containing training examples

        Returns:
            {
                'size': 'size_preserved' | 'scaled_2x' | ...,
                'color': 'colors_preserved' | 'colors_mapped' | ...,
                'symmetry': 'horizontal_symmetry' | 'no_symmetry' | ...,
                'object': 'object_count_preserved' | ...
            }
        """
        train_examples = task.get('train', [])

        if not train_examples:
            return self._default_constraints()

        constraints = {
            'size': self._extract_size_constraint(train_examples),
            'color': self._extract_color_constraint(train_examples),
            'symmetry': self._extract_symmetry_constraint(train_examples),
            'object': self._extract_object_constraint(train_examples)
        }

        self.extracted_constraints = constraints
        return constraints

    def _default_constraints(self) -> Dict[str, str]:
        """Return default constraints when no training data available."""
        return {
            'size': 'size_variable',
            'color': 'colors_variable',
            'symmetry': 'no_symmetry',
            'object': 'object_count_variable'
        }

    def _extract_size_constraint(self, train_examples: List[Dict]) -> str:
        """
        Extract size transformation constraint.

        Detects patterns like:
        - size_preserved: Input size == output size
        - scaled_2x: Output = 2× input
        - dimensions_swapped: Height ↔ width
        - cropped: Output smaller than input
        """
        patterns = []

        for ex in train_examples:
            # Convert to arrays to get shape
            if not isinstance(ex['input'], np.ndarray):
                in_grid = np.array(ex['input'])
            else:
                in_grid = ex['input']

            if not isinstance(ex['output'], np.ndarray):
                out_grid = np.array(ex['output'])
            else:
                out_grid = ex['output']

            in_h, in_w = in_grid.shape
            out_h, out_w = out_grid.shape

            # Check size relationship
            if (in_h, in_w) == (out_h, out_w):
                patterns.append('size_preserved')
            elif (in_w, in_h) == (out_h, out_w):
                patterns.append('dimensions_swapped')
            elif out_h == in_h * 2 and out_w == in_w * 2:
                patterns.append('scaled_2x')
            elif out_h == in_h * 3 and out_w == in_w * 3:
                patterns.append('scaled_3x')
            elif out_h < in_h and out_w < in_w:
                patterns.append('cropped')
            elif out_h > in_h and out_w > in_w:
                patterns.append('expanded')
            else:
                patterns.append('size_variable')

        # Require unanimity for constraint (all examples must agree)
        if len(set(patterns)) == 1:
            return patterns[0]
        else:
            return 'size_variable'

    def _extract_color_constraint(self, train_examples: List[Dict]) -> str:
        """
        Extract color transformation constraint.

        Detects patterns like:
        - colors_preserved: Input colors == output colors
        - colors_reduced: Output has fewer colors
        - colors_mapped: 1-to-1 color mapping
        - background_removed: Color 0 removed
        """
        patterns = []

        for ex in train_examples:
            if not isinstance(ex['input'], np.ndarray):
                in_grid = np.array(ex['input'])
            else:
                in_grid = ex['input']

            if not isinstance(ex['output'], np.ndarray):
                out_grid = np.array(ex['output'])
            else:
                out_grid = ex['output']

            # Get unique colors
            in_colors = set(in_grid.flatten())
            out_colors = set(out_grid.flatten())

            # Check color relationship
            if in_colors == out_colors:
                patterns.append('colors_preserved')
            elif out_colors < in_colors and 0 not in out_colors and 0 in in_colors:
                patterns.append('background_removed')
            elif out_colors < in_colors:
                patterns.append('colors_reduced')
            elif out_colors > in_colors:
                patterns.append('colors_added')
            elif len(in_colors) == len(out_colors):
                patterns.append('colors_mapped')
            else:
                patterns.append('colors_variable')

        # Require unanimity
        if len(set(patterns)) == 1:
            return patterns[0]
        else:
            return 'colors_variable'

    def _extract_symmetry_constraint(self, train_examples: List[Dict]) -> str:
        """
        Extract symmetry constraint from OUTPUT grids.

        Detects if output has:
        - horizontal_symmetry: Mirror across vertical axis
        - vertical_symmetry: Mirror across horizontal axis
        - rotational_symmetry: 180° rotational symmetry
        - no_symmetry: No obvious symmetry
        """
        symmetries = []

        for ex in train_examples:
            if not isinstance(ex['output'], np.ndarray):
                output = np.array(ex['output'])
            else:
                output = ex['output']

            has_symmetry = False

            # Check horizontal symmetry (left-right mirror)
            if np.array_equal(output, np.fliplr(output)):
                symmetries.append('horizontal_symmetry')
                has_symmetry = True

            # Check vertical symmetry (top-bottom mirror)
            if np.array_equal(output, np.flipud(output)):
                symmetries.append('vertical_symmetry')
                has_symmetry = True

            # Check 180° rotational symmetry
            if np.array_equal(output, np.rot90(output, 2)):
                symmetries.append('rotational_symmetry')
                has_symmetry = True

            if not has_symmetry:
                symmetries.append('no_symmetry')

        # Return most common symmetry
        if not symmetries:
            return 'no_symmetry'

        counter = Counter(symmetries)
        most_common = counter.most_common(1)[0]

        # Require at least 50% of examples to have this symmetry
        if most_common[1] >= len(train_examples) * 0.5:
            return most_common[0]
        else:
            return 'no_symmetry'

    def _extract_object_constraint(self, train_examples: List[Dict]) -> str:
        """
        Extract object-level constraint using connected components.

        Detects patterns like:
        - object_count_preserved: Same number of objects
        - object_count_increased: Objects replicated
        - object_count_decreased: Objects merged/removed
        """
        patterns = []

        for ex in train_examples:
            if not isinstance(ex['input'], np.ndarray):
                in_grid = np.array(ex['input'])
            else:
                in_grid = ex['input']

            if not isinstance(ex['output'], np.ndarray):
                out_grid = np.array(ex['output'])
            else:
                out_grid = ex['output']

            try:
                # Count connected components (objects)
                in_labeled, in_count = label(in_grid > 0)  # Binary: non-zero = object
                out_labeled, out_count = label(out_grid > 0)

                if in_count == out_count:
                    patterns.append('object_count_preserved')
                elif out_count > in_count:
                    patterns.append('object_count_increased')
                elif out_count < in_count:
                    patterns.append('object_count_decreased')
                else:
                    patterns.append('object_count_variable')

            except Exception:
                # If object detection fails, mark as variable
                patterns.append('object_count_variable')

        # Require unanimity
        if len(set(patterns)) == 1:
            return patterns[0]
        else:
            return 'object_count_variable'


# ============================================================================
# CONSTRAINT FILTERS
# ============================================================================

# Size constraint filters
SIZE_CONSTRAINT_FILTERS = {
    'size_preserved': {
        'allow': ['rotate_90', 'rotate_180', 'rotate_270', 'flip_h', 'flip_v',
                  'transpose', 'invert', 'swap_01', 'color_inc', 'sym_h', 'sym_v',
                  'fill_zeros', 'remove_bg', 'hollow', 'border', 'gravity_down',
                  'gravity_up'],
        'block': ['scale_2x', 'scale_3x', 'crop', 'downsample', 'tile_2x2', 'tile_3x3',
                  'pad_1', 'extend_edges']
    },
    'scaled_2x': {
        'allow': ['scale_2x', 'tile_2x2'],
        'block': ['crop', 'downsample', 'scale_3x']
    },
    'scaled_3x': {
        'allow': ['scale_3x', 'tile_3x3'],
        'block': ['crop', 'downsample', 'scale_2x']
    },
    'dimensions_swapped': {
        'allow': ['rotate_90', 'rotate_270', 'transpose'],
        'block': ['flip_h', 'flip_v', 'rotate_180', 'scale_2x', 'crop']
    },
    'cropped': {
        'allow': ['crop', 'downsample', 'extract_largest', 'extract_smallest'],
        'block': ['scale_2x', 'scale_3x', 'tile_2x2', 'pad_1']
    },
    'expanded': {
        'allow': ['scale_2x', 'scale_3x', 'tile_2x2', 'tile_3x3', 'pad_1', 'extend_edges'],
        'block': ['crop', 'downsample']
    }
}

# Color constraint filters
COLOR_CONSTRAINT_FILTERS = {
    'colors_preserved': {
        'allow': ['rotate_90', 'rotate_180', 'rotate_270', 'flip_h', 'flip_v',
                  'transpose', 'crop', 'scale_2x', 'scale_3x', 'tile_2x2',
                  'gravity_down', 'gravity_up', 'sort_by_size', 'align_h', 'align_v'],
        'block': ['invert', 'swap_01', 'color_inc', 'fill_zeros', 'remove_bg']
    },
    'colors_reduced': {
        'allow': ['fill_zeros', 'remove_bg', 'extract_largest', 'extract_smallest'],
        'block': ['color_inc', 'invert']
    },
    'colors_mapped': {
        'allow': ['swap_01', 'invert', 'color_inc'],
        'block': ['remove_bg', 'fill_zeros']
    },
    'background_removed': {
        'allow': ['remove_bg', 'extract_largest'],
        'block': ['fill_zeros']
    },
    'colors_added': {
        'allow': ['border', 'color_inc', 'sym_h', 'sym_v'],
        'block': ['remove_bg', 'fill_zeros']
    }
}

# Symmetry constraint filters
SYMMETRY_CONSTRAINT_FILTERS = {
    'horizontal_symmetry': {
        'prioritize': ['sym_h'],
        'allow': ['flip_h', 'rotate_180'],
        'block': []
    },
    'vertical_symmetry': {
        'prioritize': ['sym_v'],
        'allow': ['flip_v', 'rotate_180'],
        'block': []
    },
    'rotational_symmetry': {
        'prioritize': ['rotate_180'],
        'allow': ['rotate_90', 'rotate_270'],
        'block': []
    }
}

# Object constraint filters
OBJECT_CONSTRAINT_FILTERS = {
    'object_count_preserved': {
        'allow': ['rotate_90', 'rotate_180', 'flip_h', 'flip_v', 'transpose',
                  'sort_by_size', 'align_h', 'align_v', 'gravity_objects'],
        'block': ['extract_largest', 'extract_smallest', 'tile_2x2']
    },
    'object_count_increased': {
        'prioritize': ['tile_2x2', 'tile_3x3'],
        'allow': ['scale_2x', 'scale_3x'],
        'block': ['extract_largest', 'extract_smallest', 'crop']
    },
    'object_count_decreased': {
        'prioritize': ['extract_largest', 'extract_smallest'],
        'allow': ['crop', 'remove_bg'],
        'block': ['tile_2x2', 'scale_2x']
    }
}


# ============================================================================
# PRIMITIVE FILTERING
# ============================================================================

class PrimitiveFilter:
    """
    Filter primitives based on extracted constraints.

    This reduces search space by removing primitives that violate
    known task constraints.
    """

    def __init__(self, all_primitives: List[str]):
        self.all_primitives = all_primitives
        self.constraint_filters = {
            'size': SIZE_CONSTRAINT_FILTERS,
            'color': COLOR_CONSTRAINT_FILTERS,
            'symmetry': SYMMETRY_CONSTRAINT_FILTERS,
            'object': OBJECT_CONSTRAINT_FILTERS
        }

    def filter_by_constraints(self,
                            constraints: Dict[str, str],
                            mode: str = 'strict') -> List[str]:
        """
        Filter primitives based on constraints.

        Args:
            constraints: Dict of constraint types and values
            mode: 'strict' (only allowed) or 'soft' (prioritize + allow)

        Returns:
            Filtered list of primitives
        """
        if mode == 'strict':
            return self._strict_filter(constraints)
        elif mode == 'soft':
            return self._soft_filter(constraints)
        else:
            raise ValueError(f"Unknown mode: {mode}")

    def _strict_filter(self, constraints: Dict[str, str]) -> List[str]:
        """
        Strict filtering: Only keep primitives that satisfy ALL constraints.

        Uses intersection of allowed primitives and removal of blocked ones.
        """
        allowed = set(self.all_primitives)

        for constraint_type, constraint_value in constraints.items():
            # Skip variable constraints (no filtering)
            if 'variable' in constraint_value:
                continue

            # Get filter specification for this constraint
            filter_spec = self.constraint_filters.get(constraint_type, {}).get(constraint_value)

            if filter_spec:
                # Intersect with allowed primitives (if specified)
                if 'allow' in filter_spec and filter_spec['allow']:
                    allowed &= set(filter_spec['allow'])

                # Remove blocked primitives
                if 'block' in filter_spec:
                    allowed -= set(filter_spec['block'])

        # Ensure we have at least 3 primitives for meaningful search
        result = list(allowed)
        if len(result) < 3:
            # Fall back to soft mode if too restrictive
            return self._soft_filter(constraints)

        return result

    def _soft_filter(self, constraints: Dict[str, str]) -> List[str]:
        """
        Soft filtering: Prioritize relevant primitives but keep others.

        Uses prioritization and partial blocking.
        """
        prioritized = []
        allowed = []
        blocked = set()

        for constraint_type, constraint_value in constraints.items():
            # Skip variable constraints
            if 'variable' in constraint_value:
                continue

            filter_spec = self.constraint_filters.get(constraint_type, {}).get(constraint_value)

            if filter_spec:
                # Add prioritized primitives (highest relevance)
                prioritized.extend(filter_spec.get('prioritize', []))

                # Add allowed primitives (medium relevance)
                allowed.extend(filter_spec.get('allow', []))

                # Accumulate blocked primitives
                blocked.update(filter_spec.get('block', []))

        # Combine prioritized + allowed (deduplicated)
        result = list(dict.fromkeys(prioritized + allowed))

        # Remove blocked primitives
        result = [p for p in result if p not in blocked]

        # Add some unfiltered primitives for exploration (10-20% of original)
        remaining = set(self.all_primitives) - set(result) - blocked
        exploration_count = max(3, len(self.all_primitives) // 10)
        result.extend(list(remaining)[:exploration_count])

        return result


# ============================================================================
# v0.93 CONSTRAINT-BASED SOLVER
# ============================================================================

class PrometheusARC_v093_Constraints(PrometheusARC_v092_Baseline):
    """
    v0.93: Add constraint-based search to v0.92 baseline.

    Key improvement: Extract constraints from task, filter primitives,
    reduce search space by 95-99%.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # v0.93 components
        self.constraint_extractor = ConstraintExtractor()
        self.primitive_filter = PrimitiveFilter(
            all_primitives=list(self.primitive_methods.keys())
        )

        # Statistics
        self.constraint_usage = defaultdict(int)
        self.search_space_reductions = []
        self.constraint_help_count = 0

    def solve_task(self,
                   train_examples: List[Dict],
                   test_examples: List[Dict],
                   task_id: str) -> Dict:
        """
        Solve task using constraint-based search.

        Flow:
        1. Extract constraints from training examples
        2. Filter primitives based on constraints (strict mode)
        3. Try evolution with filtered primitives
        4. If fails, fall back to soft filtering
        5. If still fails, fall back to v0.92 (no filtering)
        """
        print(f"  [v0.93] Solving task {task_id}...")

        # Step 1: Extract constraints
        task_data = {'train': train_examples}
        constraints = self.constraint_extractor.extract_all_constraints(task_data)

        print(f"  [Constraints] {constraints}")

        # Track constraint usage
        for c_type, c_value in constraints.items():
            self.constraint_usage[f"{c_type}:{c_value}"] += 1

        # Step 2: Filter primitives
        strict_prims = self.primitive_filter.filter_by_constraints(
            constraints, mode='strict'
        )
        soft_prims = self.primitive_filter.filter_by_constraints(
            constraints, mode='soft'
        )

        # Calculate search space reduction
        original_space = len(self.primitive_methods) ** 5
        strict_space = len(strict_prims) ** 5 if strict_prims else original_space
        soft_space = len(soft_prims) ** 5 if soft_prims else original_space

        reduction_strict = 1 - (strict_space / original_space) if strict_prims else 0
        reduction_soft = 1 - (soft_space / original_space) if soft_prims else 0

        print(f"  [Filter] Strict: {len(strict_prims)} prims ({reduction_strict*100:.1f}% reduction)")
        print(f"  [Filter] Soft: {len(soft_prims)} prims ({reduction_soft*100:.1f}% reduction)")

        self.search_space_reductions.append(reduction_strict)

        # Step 3: Try strict filtering
        if len(strict_prims) >= 3:
            print(f"  [v0.93] Trying strict mode with {len(strict_prims)} primitives...")
            # Temporarily filter primitive_methods to only include allowed primitives
            original_methods = self.primitive_methods.copy()
            self.primitive_methods = {k: v for k, v in self.primitive_methods.items()
                                     if k in strict_prims}

            try:
                result = super().solve_task(train_examples, test_examples, task_id)
                result['constraints'] = constraints
                result['filtered_primitives'] = len(strict_prims)
                result['search_space_reduction'] = reduction_strict
                result['filter_mode'] = 'strict'

                if result['fitness'] >= 0.95:
                    self.constraint_help_count += 1
                    return result
            finally:
                # Restore original primitive methods
                self.primitive_methods = original_methods

        # Step 4: Try soft filtering
        print(f"  [v0.93] Trying soft mode with {len(soft_prims)} primitives...")
        original_methods = self.primitive_methods.copy()
        self.primitive_methods = {k: v for k, v in self.primitive_methods.items()
                                 if k in soft_prims}

        try:
            result = super().solve_task(train_examples, test_examples, task_id)
            result['constraints'] = constraints
            result['filtered_primitives'] = len(soft_prims)
            result['search_space_reduction'] = reduction_soft
            result['filter_mode'] = 'soft'

            return result
        finally:
            # Restore original primitive methods
            self.primitive_methods = original_methods

    def get_statistics(self) -> Dict:
        """Get v0.93 statistics."""
        stats = super().get_statistics()

        stats.update({
            'constraint_usage': dict(self.constraint_usage),
            'avg_search_space_reduction': np.mean(self.search_space_reductions) if self.search_space_reductions else 0,
            'constraint_help_count': self.constraint_help_count
        })

        return stats


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Test v0.93 constraint-based search on ARC evaluation set"""
    import argparse

    parser = argparse.ArgumentParser(description='ARC v0.93 Constraint-Based Solver')
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
    parser.add_argument('--cycles', type=int, default=3,
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
    print("🔬 Prometheus ARC v0.93: Constraint-Based Search")
    print("="*80)
    print(f"Split: {args.split}")
    print(f"Tasks: {len(task_ids)}")
    print(f"Phase 5 (Adaptive): {'Disabled' if args.no_adaptive else 'Enabled'}")
    print(f"Phase 6 (LLM): {'Disabled' if args.no_llm else 'Enabled'}")
    print(f"Phase 7 (Meta): {'Disabled' if args.no_meta else 'Enabled'}")
    print(f"Max refinement cycles: {args.cycles}")
    print()
    print("Key Improvements over v0.92:")
    print("  1. Constraint extraction (size, color, symmetry, object)")
    print("  2. Primitive filtering (strict + soft modes)")
    print("  3. Search space reduction (95-99%)")
    print("  4. Constraint-guided evolution")
    print("="*80)
    print()

    # Initialize solver
    solver = PrometheusARC_v093_Constraints(
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

            success = result['fitness'] >= 0.95
            if success:
                solved_count += 1

            result_summary = {
                'task_id': task_id,
                'success': success,
                'fitness': result['fitness'],
                'pattern': result['pattern'],
                'method': result['method'],
                'generation_budget': result.get('generation_budget', 100),
                'constraints': result.get('constraints', {}),
                'search_space_reduction': result.get('search_space_reduction', 0),
                'filter_mode': result.get('filter_mode', 'none')
            }
            results.append(result_summary)

            status = "✓ SOLVED" if success else f"✗ Failed (fitness: {result['fitness']:.3f})"
            print(f"  {status} via {result['method']}")
            print(f"  Reduction: {result.get('search_space_reduction', 0)*100:.1f}%")
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

    # Statistics
    stats = solver.get_statistics()
    print("📈 v0.93 Statistics:")
    print(f"  Average search space reduction: {stats.get('avg_search_space_reduction', 0)*100:.1f}%")
    print(f"  Constraints helped in: {stats.get('constraint_help_count', 0)} tasks")
    print(f"  Constraint usage: {stats.get('constraint_usage', {})}")
    print()

    # Save results
    output_file = f'arc_v093_constraints_{args.split}_{len(task_ids)}tasks.json'

    # Convert numpy types
    def convert_types(obj):
        if isinstance(obj, dict):
            return {k: convert_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_types(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

    output_data = convert_types({
        'version': 'v0.93',
        'improvements': [
            'constraint_extraction',
            'primitive_filtering',
            'search_space_reduction',
            'constraint_guided_evolution'
        ],
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
