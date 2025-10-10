#!/usr/bin/env python3
"""
Prometheus v0.70 - Phase 3: Hybrid Neural-Symbolic ARC Solver

Ensemble approach combining:
1. Evolutionary pattern search (38 primitives)
2. DSL program synthesis (compositional programs)
3. Domain-specific ARC primitives (hand-crafted for common patterns)
4. Neural guidance (lightweight feature-based heuristics)

Target: 10-15% by leveraging complementary solving strategies
"""

import json
import numpy as np
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# Import existing systems
import sys
sys.path.insert(0, str(Path(__file__).parent))
from prometheus_arc_evolution import PrometheusARCEvolution
from prometheus_arc_dsl import DSLProgramSynthesis


@dataclass
class TaskFeatures:
    """Neural-guided features for task classification"""
    grid_size_ratio: float  # output/input size ratio
    color_count: int
    has_objects: bool
    has_symmetry: bool
    is_sparse: bool
    pattern_type: str  # 'geometric', 'color', 'object', 'composition'

    def predict_best_solver(self) -> str:
        """Heuristic to select best solving strategy"""
        # Geometric transformations → Evolution
        if abs(self.grid_size_ratio - 1.0) < 0.1 and not self.has_objects:
            return 'evolution'

        # Object-based tasks → DSL
        if self.has_objects and self.color_count <= 5:
            return 'dsl'

        # Complex compositions → Domain-specific
        if self.grid_size_ratio > 2.0 or self.grid_size_ratio < 0.5:
            return 'domain'

        # Default: try evolution first
        return 'evolution'


class DomainSpecificPrimitives:
    """Hand-crafted primitives for common ARC patterns"""

    @staticmethod
    def extract_and_tile_objects(grid: np.ndarray) -> np.ndarray:
        """Extract objects and tile them in grid"""
        from scipy import ndimage

        objects = []
        for color in np.unique(grid):
            if color == 0:
                continue
            mask = (grid == color)
            labeled, num = ndimage.label(mask)
            for i in range(1, num + 1):
                obj_mask = (labeled == i)
                objects.append((obj_mask, color))

        if not objects:
            return grid

        # Get largest object
        largest = max(objects, key=lambda x: np.sum(x[0]))
        obj_mask, color = largest

        # Extract to bounding box
        rows = np.any(obj_mask, axis=1)
        cols = np.any(obj_mask, axis=0)
        if not rows.any() or not cols.any():
            return grid

        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        obj = grid[rmin:rmax+1, cmin:cmax+1] * obj_mask[rmin:rmax+1, cmin:cmax+1]

        # Tile it
        return np.tile(obj, (2, 2))

    @staticmethod
    def color_by_position(grid: np.ndarray) -> np.ndarray:
        """Color cells based on position (common ARC pattern)"""
        result = np.zeros_like(grid)
        for r in range(grid.shape[0]):
            for c in range(grid.shape[1]):
                if grid[r, c] != 0:
                    # Color based on position (row + col) mod N
                    result[r, c] = ((r + c) % 9) + 1
        return result

    @staticmethod
    def extend_pattern(grid: np.ndarray) -> np.ndarray:
        """Extend pattern to fill grid (continuation)"""
        if grid.shape[0] < 2 or grid.shape[1] < 2:
            return grid

        result = grid.copy()

        # Horizontal extension
        if grid.shape[1] >= 2:
            pattern_col = grid[:, -1]
            for c in range(grid.shape[1]):
                if np.all(grid[:, c] == 0):
                    result[:, c] = pattern_col

        # Vertical extension
        if grid.shape[0] >= 2:
            pattern_row = grid[-1, :]
            for r in range(grid.shape[0]):
                if np.all(grid[r, :] == 0):
                    result[r, :] = pattern_row

        return result

    @staticmethod
    def fill_shape_with_pattern(grid: np.ndarray) -> np.ndarray:
        """Fill shapes with internal patterns"""
        from scipy import ndimage

        result = grid.copy()

        for color in np.unique(grid):
            if color == 0:
                continue

            mask = (grid == color)
            labeled, num = ndimage.label(mask)

            for i in range(1, num + 1):
                obj_mask = (labeled == i)

                # Fill with checkerboard pattern
                for r in range(grid.shape[0]):
                    for c in range(grid.shape[1]):
                        if obj_mask[r, c]:
                            if (r + c) % 2 == 0:
                                result[r, c] = color
                            else:
                                result[r, c] = (color % 9) + 1

        return result

    @staticmethod
    def replicate_pattern_by_count(grid: np.ndarray) -> np.ndarray:
        """Replicate pattern N times where N = object count"""
        from scipy import ndimage

        # Count objects
        count = 0
        for color in np.unique(grid):
            if color == 0:
                continue
            mask = (grid == color)
            labeled, num = ndimage.label(mask)
            count += num

        if count == 0:
            return grid

        # Replicate grid count times
        return np.tile(grid, (min(count, 3), min(count, 3)))


class HybridARCSolver:
    """Ensemble solver combining multiple strategies"""

    def __init__(self):
        # Initialize all solvers
        self.evolution = PrometheusARCEvolution(
            population_size=50,
            max_pattern_length=5
        )
        self.dsl = DSLProgramSynthesis(max_program_length=8)
        self.domain = DomainSpecificPrimitives()

        # Domain-specific templates
        self.domain_templates = [
            self.domain.extract_and_tile_objects,
            self.domain.color_by_position,
            self.domain.extend_pattern,
            self.domain.fill_shape_with_pattern,
            self.domain.replicate_pattern_by_count,
        ]

    def extract_features(self, task: dict) -> TaskFeatures:
        """Extract features for neural guidance"""
        train_pairs = task['train']
        pair = train_pairs[0]

        input_grid = np.array(pair['input'])
        output_grid = np.array(pair['output'])

        grid_size_ratio = output_grid.size / input_grid.size
        color_count = len(np.unique(np.concatenate([input_grid.flatten(),
                                                      output_grid.flatten()])))

        # Detect objects
        from scipy import ndimage
        has_objects = False
        for color in np.unique(input_grid):
            if color == 0:
                continue
            mask = (input_grid == color)
            labeled, num = ndimage.label(mask)
            if num > 1:
                has_objects = True
                break

        has_symmetry = np.array_equal(input_grid, np.flip(input_grid, axis=1)) or \
                       np.array_equal(input_grid, np.flip(input_grid, axis=0))

        is_sparse = (np.count_nonzero(input_grid) / input_grid.size) < 0.2

        # Classify pattern type
        if abs(grid_size_ratio - 1.0) < 0.1:
            pattern_type = 'geometric'
        elif grid_size_ratio > 2.0:
            pattern_type = 'composition'
        elif has_objects:
            pattern_type = 'object'
        else:
            pattern_type = 'color'

        return TaskFeatures(
            grid_size_ratio=grid_size_ratio,
            color_count=color_count,
            has_objects=has_objects,
            has_symmetry=has_symmetry,
            is_sparse=is_sparse,
            pattern_type=pattern_type
        )

    def solve_with_domain(self, task: dict) -> Tuple[Optional[callable], float]:
        """Try domain-specific primitives"""
        train_pairs = task['train']

        for template in self.domain_templates:
            correct = 0
            for pair in train_pairs:
                input_grid = np.array(pair['input'])
                expected = np.array(pair['output'])

                try:
                    predicted = template(input_grid)

                    if predicted.shape == expected.shape:
                        if np.array_equal(predicted, expected):
                            correct += 1
                except:
                    pass

            fitness = correct / len(train_pairs)
            if fitness >= 0.99:
                return template, fitness

        return None, 0.0

    def solve_task(self, task: dict, task_id: str) -> Tuple[str, float, str]:
        """Ensemble solving: try multiple strategies"""
        # Extract features for guidance
        features = self.extract_features(task)
        suggested_solver = features.predict_best_solver()

        solvers_to_try = []

        # Prioritize based on heuristic
        if suggested_solver == 'dsl':
            solvers_to_try = ['dsl', 'domain', 'evolution']
        elif suggested_solver == 'domain':
            solvers_to_try = ['domain', 'dsl', 'evolution']
        else:
            solvers_to_try = ['evolution', 'dsl', 'domain']

        for solver_name in solvers_to_try:
            try:
                if solver_name == 'evolution':
                    # Quick evolution (50 generations)
                    pattern, fitness = self.evolution.evolve_pattern_for_task(task, 50)
                    if fitness >= 0.99:
                        return solver_name, fitness, str([op.name for op in pattern.operations])

                elif solver_name == 'dsl':
                    program, fitness = self.dsl.synthesize_for_task(task)
                    if fitness >= 0.99:
                        return solver_name, fitness, str(program)

                elif solver_name == 'domain':
                    template, fitness = self.solve_with_domain(task)
                    if fitness >= 0.99:
                        return solver_name, fitness, template.__name__

            except Exception as e:
                # Continue to next solver
                pass

        return 'none', 0.0, ''


def main():
    """Run hybrid solver on ARC tasks"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', default='training')
    parser.add_argument('--max-tasks', type=int, default=400)
    args = parser.parse_args()

    # Load tasks
    data_path = Path('arc_data/ARC-AGI/data') / args.split

    tasks = []
    task_ids = []

    for task_file in sorted(data_path.glob('*.json'))[:args.max_tasks]:
        with open(task_file) as f:
            tasks.append(json.load(f))
            task_ids.append(task_file.stem)

    print(f"🔬 Prometheus Hybrid Neural-Symbolic ARC Solver")
    print(f"   Tasks: {len(tasks)}")
    print(f"   Strategies: Evolution + DSL + Domain-specific")
    print(f"   Neural guidance: Feature-based heuristics")
    print()

    # Solve tasks
    solver = HybridARCSolver()

    results = {
        'solved_tasks': [],
        'failed_tasks': [],
        'solutions': {},
        'solver_stats': {'evolution': 0, 'dsl': 0, 'domain': 0},
        'total_solved': 0,
        'total_tasks': len(tasks)
    }

    start_time = time.time()

    for i, (task_id, task) in enumerate(zip(task_ids, tasks), 1):
        solver_name, fitness, solution = solver.solve_task(task, task_id)

        solved = fitness >= 0.99

        if solved:
            results['solved_tasks'].append(task_id)
            results['solutions'][task_id] = {
                'solver': solver_name,
                'fitness': fitness,
                'solution': solution
            }
            results['solver_stats'][solver_name] += 1
            results['total_solved'] += 1

            print(f"   ✓ {i}/{len(tasks)} | {task_id} | {solver_name.upper()} | Fitness: {fitness:.3f} | Success: {100*results['total_solved']/i:.1f}% ({results['total_solved']}/{i})")
        else:
            results['failed_tasks'].append(task_id)

            if (i % 10 == 0) or (i == len(tasks)):
                print(f"   {i}/{len(tasks)} | {task_id} | Failed | Success: {100*results['total_solved']/i:.1f}% ({results['total_solved']}/{i})")

    duration = time.time() - start_time

    print()
    print(f"✅ Hybrid Solving Complete!")
    print(f"   Tasks: {len(tasks)}")
    print(f"   Solved: {results['total_solved']}/{len(tasks)} ({100*results['total_solved']/len(tasks):.1f}%)")
    print(f"   Evolution: {results['solver_stats']['evolution']} tasks")
    print(f"   DSL: {results['solver_stats']['dsl']} tasks")
    print(f"   Domain: {results['solver_stats']['domain']} tasks")
    print(f"   Duration: {duration:.1f}s")

    # Save results
    output_dir = Path('arc_hybrid_results')
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f'hybrid_{args.split}.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"📊 Results saved to: {output_file}")


if __name__ == '__main__':
    main()
