#!/usr/bin/env python3
"""
Prometheus v0.69 - Meta-Evolution: Evolving the Primitive Library

Phase 2 breakthrough strategy: Instead of evolving patterns from fixed primitives,
evolve NEW primitives themselves from numpy/scipy operations.

Expected impact: +5-10 tasks by discovering novel transformations we didn't hand-code.

Approach:
1. Define meta-primitive language (numpy, scipy operations with parameters)
2. Evolve useful primitive operations on subset of tasks
3. Add successful primitives to library
4. Re-run standard evolution with expanded library
"""

import json
import numpy as np
from scipy import ndimage
import random
import time
from pathlib import Path
from typing import List, Tuple, Callable, Dict
from dataclasses import dataclass
from copy import deepcopy

# Import base evolution
import sys
sys.path.insert(0, str(Path(__file__).parent))
from prometheus_arc_evolution import ARCPrimitives


@dataclass
class MetaPrimitive:
    """Evolved primitive operation"""
    name: str
    operations: List[str]  # Sequence of numpy/scipy ops
    parameters: Dict  # Parameters for operations
    fitness: float = 0.0
    tasks_solved: List[str] = None

    def __post_init__(self):
        if self.tasks_solved is None:
            self.tasks_solved = []

    def apply(self, grid: np.ndarray) -> np.ndarray:
        """Apply meta-primitive to grid"""
        result = grid.copy()

        for op in self.operations:
            try:
                # Parse operation and apply
                if op == 'flip_both':
                    result = np.flip(np.flip(result, axis=0), axis=1)
                elif op == 'rot90_twice':
                    result = np.rot90(np.rot90(result))
                elif op == 'dilate':
                    # Binary dilation for each color
                    output = np.zeros_like(result)
                    for color in np.unique(result):
                        if color == 0:
                            continue
                        mask = (result == color)
                        dilated = ndimage.binary_dilation(mask)
                        output[dilated] = color
                    result = output
                elif op == 'erode':
                    # Binary erosion for each color
                    output = np.zeros_like(result)
                    for color in np.unique(result):
                        if color == 0:
                            continue
                        mask = (result == color)
                        eroded = ndimage.binary_erosion(mask)
                        output[eroded] = color
                    result = output
                elif op == 'gaussian_smooth':
                    # Smooth then round
                    result = ndimage.gaussian_filter(result.astype(float), sigma=1.0)
                    result = np.round(result).astype(int)
                elif op == 'median_filter':
                    result = ndimage.median_filter(result, size=3)
                elif op == 'edge_detect':
                    # Sobel edge detection
                    edges = ndimage.sobel(result.astype(float))
                    result = (edges > 0).astype(int) * np.max(result)
                elif op == 'fill_holes':
                    # Fill holes in each color
                    output = result.copy()
                    for color in np.unique(result):
                        if color == 0:
                            continue
                        mask = (result == color)
                        filled = ndimage.binary_fill_holes(mask)
                        output[filled] = color
                    result = output
                elif op == 'extract_boundary':
                    # Extract object boundaries
                    output = np.zeros_like(result)
                    for color in np.unique(result):
                        if color == 0:
                            continue
                        mask = (result == color)
                        eroded = ndimage.binary_erosion(mask)
                        boundary = mask & ~eroded
                        output[boundary] = color
                    result = output
                elif op == 'centroid_shift':
                    # Shift to center of mass
                    output = np.zeros_like(result)
                    for color in np.unique(result):
                        if color == 0:
                            continue
                        mask = (result == color)
                        com = ndimage.center_of_mass(mask)
                        if not np.isnan(com[0]):
                            # Shift to grid center
                            shift_y = result.shape[0]//2 - int(com[0])
                            shift_x = result.shape[1]//2 - int(com[1])
                            shifted = ndimage.shift(mask.astype(float), (shift_y, shift_x), order=0) > 0.5
                            output[shifted] = color
                    result = output
                elif op == 'zoom_2x':
                    result = ndimage.zoom(result, 2, order=0)
                elif op == 'zoom_half':
                    result = ndimage.zoom(result, 0.5, order=0)
                elif op == 'rotate_45':
                    result = ndimage.rotate(result, 45, reshape=False, order=0)
                elif op == 'majority_filter':
                    # Replace each cell with most common neighbor
                    output = result.copy()
                    for i in range(1, result.shape[0]-1):
                        for j in range(1, result.shape[1]-1):
                            neighbors = result[i-1:i+2, j-1:j+2].flatten()
                            values, counts = np.unique(neighbors, return_counts=True)
                            output[i,j] = values[np.argmax(counts)]
                    result = output

            except Exception:
                # Operation failed, return current state
                pass

        return result


class MetaEvolution:
    """Evolve new primitive operations"""

    def __init__(self):
        # Available meta-operations to compose
        self.meta_ops = [
            'flip_both', 'rot90_twice', 'dilate', 'erode',
            'gaussian_smooth', 'median_filter', 'edge_detect',
            'fill_holes', 'extract_boundary', 'centroid_shift',
            'zoom_2x', 'zoom_half', 'rotate_45', 'majority_filter'
        ]

        self.population_size = 30
        self.evolved_primitives: List[MetaPrimitive] = []

    def create_random_metaprimitive(self) -> MetaPrimitive:
        """Create random meta-primitive (1-3 operations)"""
        num_ops = random.randint(1, 3)
        ops = random.choices(self.meta_ops, k=num_ops)

        name = '_'.join(ops[:2]) if len(ops) > 1 else ops[0]

        return MetaPrimitive(
            name=name,
            operations=ops,
            parameters={}
        )

    def evaluate_metaprimitive(self, primitive: MetaPrimitive,
                               tasks: List[dict]) -> float:
        """Evaluate how useful this primitive is across tasks"""
        solved = 0
        total = len(tasks)

        for task in tasks:
            train_pairs = task['train']

            # Check if primitive solves this task
            correct = 0
            for pair in train_pairs:
                input_grid = np.array(pair['input'])
                expected = np.array(pair['output'])

                try:
                    predicted = primitive.apply(input_grid)

                    if predicted.shape == expected.shape:
                        if np.array_equal(predicted, expected):
                            correct += 1
                except Exception:
                    pass

            if correct == len(train_pairs):
                solved += 1

        return solved / total

    def evolve_primitives(self, sample_tasks: List[dict],
                         generations: int = 50) -> List[MetaPrimitive]:
        """Evolve useful primitives on sample tasks"""
        # Initialize population
        population = [self.create_random_metaprimitive()
                     for _ in range(self.population_size)]

        best_primitives = []

        print(f"🧬 Meta-Evolution: Discovering New Primitives")
        print(f"   Sample tasks: {len(sample_tasks)}")
        print(f"   Generations: {generations}")
        print(f"   Population: {self.population_size}")
        print()

        for gen in range(generations):
            # Evaluate fitness
            for prim in population:
                prim.fitness = self.evaluate_metaprimitive(prim, sample_tasks)

            # Track best
            population.sort(key=lambda p: p.fitness, reverse=True)

            if population[0].fitness > 0:
                if not any(p.name == population[0].name for p in best_primitives):
                    best_primitives.append(deepcopy(population[0]))
                    print(f"   Gen {gen}: Found useful primitive '{population[0].name}' | Solves: {population[0].fitness*100:.1f}% | Ops: {population[0].operations}")

            # Selection + crossover + mutation
            new_population = []

            # Keep top 10%
            elite = population[:self.population_size // 10]
            new_population.extend([deepcopy(p) for p in elite])

            # Generate rest
            while len(new_population) < self.population_size:
                # Tournament selection
                tournament = random.sample(population, k=3)
                parent = max(tournament, key=lambda p: p.fitness)

                # Mutation
                if random.random() < 0.5:
                    # Add/remove/replace operation
                    child = deepcopy(parent)
                    mutation_type = random.choice(['add', 'remove', 'replace'])

                    if mutation_type == 'add' and len(child.operations) < 3:
                        child.operations.append(random.choice(self.meta_ops))
                    elif mutation_type == 'remove' and len(child.operations) > 1:
                        child.operations.pop(random.randrange(len(child.operations)))
                    elif mutation_type == 'replace' and child.operations:
                        idx = random.randrange(len(child.operations))
                        child.operations[idx] = random.choice(self.meta_ops)

                    child.name = '_'.join(child.operations[:2])
                    new_population.append(child)
                else:
                    new_population.append(deepcopy(parent))

            population = new_population

        print()
        print(f"✅ Meta-Evolution Complete!")
        print(f"   Primitives discovered: {len(best_primitives)}")

        return best_primitives


def main():
    """Run meta-evolution to discover new primitives"""
    import argparse

    parser = argparse.ArgumentParser(description='Meta-Evolution of Primitives')
    parser.add_argument('--sample-size', type=int, default=50,
                       help='Number of tasks to evolve on')
    parser.add_argument('--generations', type=int, default=100)
    args = parser.parse_args()

    # Load sample of ARC tasks
    data_path = Path('arc_data/ARC-AGI/data/training')

    tasks = []
    for task_file in sorted(data_path.glob('*.json'))[:args.sample_size]:
        with open(task_file) as f:
            tasks.append(json.load(f))

    # Run meta-evolution
    meta_evo = MetaEvolution()

    start_time = time.time()
    new_primitives = meta_evo.evolve_primitives(tasks, args.generations)
    duration = time.time() - start_time

    # Save results
    output_dir = Path('arc_metaevolution_results')
    output_dir.mkdir(exist_ok=True)

    results = {
        'primitives_discovered': len(new_primitives),
        'sample_tasks': args.sample_size,
        'generations': args.generations,
        'duration': duration,
        'primitives': [
            {
                'name': p.name,
                'operations': p.operations,
                'fitness': p.fitness,
                'tasks_solved_percent': p.fitness * 100
            }
            for p in new_primitives
        ]
    }

    output_file = output_dir / 'metaevolution_primitives.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print()
    print(f"📊 Results saved to: {output_file}")
    print(f"   Duration: {duration:.1f}s")
    print(f"   New primitives: {len(new_primitives)}")
    print()

    # Show top primitives
    if new_primitives:
        print("🎯 Top Primitives Discovered:")
        for i, prim in enumerate(new_primitives[:10], 1):
            print(f"   {i}. {prim.name}: {prim.fitness*100:.1f}% | {prim.operations}")


if __name__ == '__main__':
    main()
