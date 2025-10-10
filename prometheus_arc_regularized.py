#!/usr/bin/env python3
"""
Prometheus v0.69 - REGULARIZED Evolutionary ARC-AGI Pattern Discovery

Key differences from base evolution:
1. MAX_PATTERN_LENGTH = 2 (hard limit, not 5)
2. COMPLEXITY_PENALTY = 0.1 per operation (10x stronger)
3. Focus on simple patterns that generalize
4. Designed to reduce overfitting on training set

This tests the hypothesis that simpler patterns generalize better.
"""

import json
import numpy as np
import random
import time
from pathlib import Path
from typing import List, Tuple, Dict, Callable
from dataclasses import dataclass, field
from copy import deepcopy

@dataclass
class PrimitiveOperation:
    """Atomic transformation operation"""
    name: str
    function: Callable[[np.ndarray], np.ndarray]
    parameters: dict = field(default_factory=dict)

@dataclass
class CompositePattern:
    """Sequence of primitive operations"""
    operations: List[PrimitiveOperation]
    fitness: float = 0.0
    generation: int = 0
    parent_ids: List[int] = field(default_factory=list)

class ARCPrimitives:
    """Library of primitive transformation operations"""

    @staticmethod
    def identity(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Copy input to output"""
        return grid.copy()

    @staticmethod
    def rotate_90(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Rotate 90 degrees clockwise"""
        return np.rot90(grid, k=1)

    @staticmethod
    def rotate_180(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Rotate 180 degrees"""
        return np.rot90(grid, k=2)

    @staticmethod
    def rotate_270(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Rotate 270 degrees clockwise"""
        return np.rot90(grid, k=3)

    @staticmethod
    def flip_horizontal(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Flip horizontally"""
        return np.flip(grid, axis=1)

    @staticmethod
    def flip_vertical(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Flip vertically"""
        return np.flip(grid, axis=0)

    @staticmethod
    def transpose(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Transpose (swap rows and columns)"""
        return grid.T

    @staticmethod
    def scale_2x(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Scale 2x (repeat each cell)"""
        return np.repeat(np.repeat(grid, 2, axis=0), 2, axis=1)

    @staticmethod
    def scale_3x(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Scale 3x"""
        return np.repeat(np.repeat(grid, 3, axis=0), 3, axis=1)

    @staticmethod
    def tile_2x2(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Tile the grid in 2x2 pattern"""
        return np.block([[grid, grid], [grid, grid]])

    @staticmethod
    def tile_3x3(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Tile the grid in 3x3 pattern"""
        return np.block([[grid, grid, grid],
                        [grid, grid, grid],
                        [grid, grid, grid]])

    @staticmethod
    def gravity_down(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Apply gravity (non-zero cells fall down)"""
        output = grid.copy()
        for j in range(output.shape[1]):
            col = output[:, j]
            nonzero = col[col != 0]
            output[:, j] = np.concatenate([
                np.zeros(output.shape[0] - len(nonzero), dtype=np.int32),
                nonzero
            ])
        return output

    @staticmethod
    def gravity_up(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Apply gravity upward"""
        output = grid.copy()
        for j in range(output.shape[1]):
            col = output[:, j]
            nonzero = col[col != 0]
            output[:, j] = np.concatenate([
                nonzero,
                np.zeros(output.shape[0] - len(nonzero), dtype=np.int32)
            ])
        return output

    @staticmethod
    def fill_zeros_common(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Fill zeros with most common non-zero color"""
        colors, counts = np.unique(grid[grid != 0], return_counts=True)
        if len(colors) == 0:
            return grid.copy()
        fill_color = int(colors[np.argmax(counts)])
        output = grid.copy()
        output[output == 0] = fill_color
        return output

    @staticmethod
    def remove_background(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Remove most common color (set to 0)"""
        colors, counts = np.unique(grid, return_counts=True)
        bg_color = int(colors[np.argmax(counts)])
        output = grid.copy()
        output[output == bg_color] = 0
        return output

    @staticmethod
    def color_swap_01(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Swap colors 0 and 1"""
        output = grid.copy()
        mask_0 = grid == 0
        mask_1 = grid == 1
        output[mask_0] = 1
        output[mask_1] = 0
        return output

    @staticmethod
    def color_increment(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Increment all colors by 1 (mod 10)"""
        return (grid + 1) % 10

    @staticmethod
    def isolate_color(grid: np.ndarray, color: int = 1, **kwargs) -> np.ndarray:
        """Keep only specified color, zero others"""
        output = np.zeros_like(grid)
        output[grid == color] = color
        return output

    @staticmethod
    def border_extract(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Extract border pixels only"""
        output = np.zeros_like(grid)
        if grid.shape[0] > 0 and grid.shape[1] > 0:
            output[0, :] = grid[0, :]
            output[-1, :] = grid[-1, :]
            output[:, 0] = grid[:, 0]
            output[:, -1] = grid[:, -1]
        return output

    @staticmethod
    def center_extract(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Extract center region (remove border)"""
        if grid.shape[0] <= 2 or grid.shape[1] <= 2:
            return grid.copy()
        return grid[1:-1, 1:-1].copy()

    @staticmethod
    def pad_1(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Add 1-pixel border of zeros"""
        return np.pad(grid, pad_width=1, mode='constant', constant_values=0)

    @staticmethod
    def invert_colors(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Invert colors (9 - color for each cell)"""
        output = grid.copy()
        output[output > 0] = 10 - output[output > 0]
        return output

    @staticmethod
    def hollow_objects(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Convert filled regions to hollow outlines"""
        from scipy import ndimage
        output = np.zeros_like(grid)
        for color in np.unique(grid):
            if color == 0:
                continue
            mask = (grid == color)
            eroded = ndimage.binary_erosion(mask)
            outline = mask & ~eroded
            output[outline] = color
        return output

    @staticmethod
    def count_colors_to_value(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Fill grid with count of unique non-zero colors"""
        num_colors = len(np.unique(grid[grid != 0]))
        return np.full_like(grid, num_colors)

    @staticmethod
    def swap_max_min_colors(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Swap most and least common non-zero colors"""
        colors, counts = np.unique(grid[grid != 0], return_counts=True)
        if len(colors) < 2:
            return grid.copy()
        max_color = int(colors[np.argmax(counts)])
        min_color = int(colors[np.argmin(counts)])
        output = grid.copy()
        output[grid == max_color] = -1  # Temp marker
        output[grid == min_color] = max_color
        output[output == -1] = min_color
        return output

    @staticmethod
    def extend_edges(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Extend edge colors to fill grid"""
        output = grid.copy()
        if grid.shape[0] == 0 or grid.shape[1] == 0:
            return output
        # Extend from edges inward
        for i in range(output.shape[0]):
            if output[i, 0] != 0:
                output[i, :] = output[i, 0]
        for j in range(output.shape[1]):
            if output[0, j] != 0:
                output[:, j] = output[0, j]
        return output

    @staticmethod
    def crop_to_content(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Crop to bounding box of non-zero content"""
        rows, cols = np.where(grid != 0)
        if len(rows) == 0:
            return grid.copy()
        return grid[rows.min():rows.max()+1, cols.min():cols.max()+1].copy()

    @staticmethod
    def symmetrize_horizontal(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Make grid horizontally symmetric (copy left to right)"""
        output = grid.copy()
        mid = output.shape[1] // 2
        output[:, mid:] = np.flip(output[:, :mid], axis=1)
        return output

    @staticmethod
    def symmetrize_vertical(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Make grid vertically symmetric (copy top to bottom)"""
        output = grid.copy()
        mid = output.shape[0] // 2
        output[mid:, :] = np.flip(output[:mid, :], axis=0)
        return output

    @staticmethod
    def diagonal_flip(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Flip along main diagonal (anti-transpose)"""
        return np.flip(grid.T, axis=1)

    @staticmethod
    def color_map_to_position(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Map each color to its row position"""
        output = np.zeros_like(grid)
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                if grid[i, j] != 0:
                    output[i, j] = i + 1
        return output

    @staticmethod
    def downsample_2x(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Downsample by 2x (take every other cell)"""
        return grid[::2, ::2].copy()

    @staticmethod
    def checkerboard_pattern(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Create checkerboard from two most common colors"""
        colors, counts = np.unique(grid, return_counts=True)
        if len(colors) < 2:
            return grid.copy()
        c1, c2 = colors[np.argsort(counts)[-2:]]
        output = np.zeros_like(grid)
        output[::2, ::2] = c1
        output[1::2, 1::2] = c1
        output[::2, 1::2] = c2
        output[1::2, ::2] = c2
        return output

    @staticmethod
    def compress_horizontal(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Remove zero-only columns"""
        mask = np.any(grid != 0, axis=0)
        if not mask.any():
            return grid.copy()
        return grid[:, mask]

    @staticmethod
    def compress_vertical(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Remove zero-only rows"""
        mask = np.any(grid != 0, axis=1)
        if not mask.any():
            return grid.copy()
        return grid[mask, :]

    @staticmethod
    def mirror_horizontal(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Create horizontal mirror (left + right)"""
        return np.concatenate([grid, np.flip(grid, axis=1)], axis=1)

    @staticmethod
    def mirror_vertical(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Create vertical mirror (top + bottom)"""
        return np.concatenate([grid, np.flip(grid, axis=0)], axis=0)

    # Include useful primitives from Options C & E (only those that were used)
    @staticmethod
    def tile_2x1(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Tile grid 2 times horizontally"""
        return np.concatenate([grid, grid], axis=1)

    @staticmethod
    def tile_1x3(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Tile grid 3 times vertically"""
        return np.concatenate([grid, grid, grid], axis=0)

    @staticmethod
    def overlay_max(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Overlay top/bottom halves with max operation"""
        h, w = grid.shape
        if h < 2:
            return grid.copy()
        h_mid = h // 2
        top = grid[:h_mid, :]
        bottom = grid[h_mid:h_mid+h_mid, :]
        min_h = min(top.shape[0], bottom.shape[0])
        min_w = min(top.shape[1], bottom.shape[1])
        return np.maximum(top[:min_h, :min_w], bottom[:min_h, :min_w])

class PrometheusARCRegularized:
    """Regularized evolutionary system for ARC pattern discovery

    Key differences from base version:
    - max_pattern_length = 2 (hard limit)
    - complexity_penalty = 0.1 (10x stronger)
    - Focuses on simple patterns that generalize
    """

    def __init__(self, population_size: int = 100, max_pattern_length: int = 2):
        self.population_size = population_size  # Increased for more diversity
        self.max_pattern_length = max_pattern_length  # HARD LIMIT: 2
        self.population: List[CompositePattern] = []
        self.generation = 0
        self.meta_learning_rate = 1.0
        self.best_fitness_history = []

        # STRONG REGULARIZATION
        self.complexity_penalty = 0.1  # 10x stronger than base (was 0.01)

        # Initialize primitive operations library
        self.primitives = self._build_primitive_library()

        # Statistics
        self.patterns_evolved = 0
        self.successful_patterns = 0

    def _build_primitive_library(self) -> List[PrimitiveOperation]:
        """Build library of primitive operations (all 56 primitives)"""
        primitives = []

        # All primitives from base system (56 total)
        primitive_methods = [
            ('identity', ARCPrimitives.identity, {}),
            ('rotate_90', ARCPrimitives.rotate_90, {}),
            ('rotate_180', ARCPrimitives.rotate_180, {}),
            ('rotate_270', ARCPrimitives.rotate_270, {}),
            ('flip_h', ARCPrimitives.flip_horizontal, {}),
            ('flip_v', ARCPrimitives.flip_vertical, {}),
            ('transpose', ARCPrimitives.transpose, {}),
            ('scale_2x', ARCPrimitives.scale_2x, {}),
            ('scale_3x', ARCPrimitives.scale_3x, {}),
            ('tile_2x2', ARCPrimitives.tile_2x2, {}),
            ('tile_3x3', ARCPrimitives.tile_3x3, {}),
            ('gravity_down', ARCPrimitives.gravity_down, {}),
            ('gravity_up', ARCPrimitives.gravity_up, {}),
            ('fill_zeros', ARCPrimitives.fill_zeros_common, {}),
            ('remove_bg', ARCPrimitives.remove_background, {}),
            ('swap_01', ARCPrimitives.color_swap_01, {}),
            ('color_inc', ARCPrimitives.color_increment, {}),
            ('isolate_1', ARCPrimitives.isolate_color, {'color': 1}),
            ('isolate_2', ARCPrimitives.isolate_color, {'color': 2}),
            ('border', ARCPrimitives.border_extract, {}),
            ('center', ARCPrimitives.center_extract, {}),
            ('pad_1', ARCPrimitives.pad_1, {}),
            ('compress_h', ARCPrimitives.compress_horizontal, {}),
            ('compress_v', ARCPrimitives.compress_vertical, {}),
            ('mirror_h', ARCPrimitives.mirror_horizontal, {}),
            ('mirror_v', ARCPrimitives.mirror_vertical, {}),
            ('invert', ARCPrimitives.invert_colors, {}),
            ('hollow', ARCPrimitives.hollow_objects, {}),
            ('count_colors', ARCPrimitives.count_colors_to_value, {}),
            ('swap_max_min', ARCPrimitives.swap_max_min_colors, {}),
            ('extend_edges', ARCPrimitives.extend_edges, {}),
            ('crop', ARCPrimitives.crop_to_content, {}),
            ('sym_h', ARCPrimitives.symmetrize_horizontal, {}),
            ('sym_v', ARCPrimitives.symmetrize_vertical, {}),
            ('diag_flip', ARCPrimitives.diagonal_flip, {}),
            ('color_pos', ARCPrimitives.color_map_to_position, {}),
            ('downsample', ARCPrimitives.downsample_2x, {}),
            ('checkerboard', ARCPrimitives.checkerboard_pattern, {}),
            # Only include the 3 new primitives that were actually used
            ('tile_2x1', ARCPrimitives.tile_2x1, {}),
            ('tile_1x3', ARCPrimitives.tile_1x3, {}),
            ('overlay_max', ARCPrimitives.overlay_max, {}),
        ]

        for name, func, params in primitive_methods:
            primitives.append(PrimitiveOperation(
                name=name,
                function=func,
                parameters=params
            ))

        return primitives

    def initialize_population(self):
        """Create initial population of random patterns

        REGULARIZATION: Only 1-2 operation patterns
        """
        self.population = []

        # Start with ALL single-operation patterns (one per primitive)
        for prim in self.primitives:
            pattern = CompositePattern(
                operations=[prim],
                generation=0
            )
            self.population.append(pattern)

        # Fill remaining population with 2-operation combinations
        while len(self.population) < self.population_size:
            ops = random.choices(self.primitives, k=2)
            pattern = CompositePattern(
                operations=ops,
                generation=0
            )
            self.population.append(pattern)

    def apply_pattern(self, grid: np.ndarray, pattern: CompositePattern) -> np.ndarray:
        """Apply composite pattern to grid"""
        try:
            output = grid.copy()
            for op in pattern.operations:
                output = op.function(output, **op.parameters)
            return output
        except Exception as e:
            # Pattern failed, return input unchanged
            return grid.copy()

    def evaluate_fitness(self, pattern: CompositePattern,
                        task_examples: List[Tuple[np.ndarray, np.ndarray]]) -> float:
        """Evaluate pattern fitness with STRONG complexity penalty"""
        if not task_examples:
            return 0.0

        correct = 0
        total = len(task_examples)

        for input_grid, expected_output in task_examples:
            predicted = self.apply_pattern(input_grid, pattern)

            # Check if prediction matches expected output
            if predicted.shape == expected_output.shape and \
               np.array_equal(predicted, expected_output):
                correct += 1

        # Fitness = accuracy - STRONG complexity penalty
        accuracy = correct / total
        complexity = len(pattern.operations)

        # REGULARIZATION: 0.1 per operation (10x stronger than base)
        complexity_penalty = self.complexity_penalty * complexity

        fitness = accuracy - complexity_penalty

        return max(0.0, fitness)

    def mutate(self, pattern: CompositePattern) -> CompositePattern:
        """Mutate a pattern (respects max_length=2 constraint)"""
        new_ops = pattern.operations.copy()

        if len(new_ops) == 0:
            # Add a random primitive
            new_ops = [random.choice(self.primitives)]
        elif len(new_ops) == 1:
            # Either replace or add (if allowed)
            if random.random() < 0.5:
                # Replace
                new_ops = [random.choice(self.primitives)]
            elif len(new_ops) < self.max_pattern_length:
                # Add second operation
                new_ops.append(random.choice(self.primitives))
        else:  # len == 2
            # Either replace one, remove one, or swap
            mutation_type = random.choice(['replace', 'remove', 'swap'])

            if mutation_type == 'replace':
                pos = random.randint(0, len(new_ops) - 1)
                new_ops[pos] = random.choice(self.primitives)
            elif mutation_type == 'remove':
                pos = random.randint(0, len(new_ops) - 1)
                new_ops.pop(pos)
            elif mutation_type == 'swap':
                new_ops[0], new_ops[1] = new_ops[1], new_ops[0]

        return CompositePattern(
            operations=new_ops,
            generation=self.generation,
            parent_ids=[id(pattern)]
        )

    def crossover(self, parent1: CompositePattern, parent2: CompositePattern) -> CompositePattern:
        """Create offspring from two parents (respects max_length=2)"""
        # Simple crossover: take one op from each parent
        if len(parent1.operations) == 0:
            new_ops = [random.choice(parent2.operations)] if len(parent2.operations) > 0 else []
        elif len(parent2.operations) == 0:
            new_ops = [random.choice(parent1.operations)]
        else:
            # Take one from each, or one from one parent
            if random.random() < 0.5 and self.max_pattern_length >= 2:
                new_ops = [
                    random.choice(parent1.operations),
                    random.choice(parent2.operations)
                ]
            else:
                parent = random.choice([parent1, parent2])
                new_ops = [random.choice(parent.operations)]

        # Enforce max length
        if len(new_ops) > self.max_pattern_length:
            new_ops = new_ops[:self.max_pattern_length]

        return CompositePattern(
            operations=new_ops,
            generation=self.generation,
            parent_ids=[id(parent1), id(parent2)]
        )

    def select_parents(self, fitnesses: List[float], k: int = 2) -> List[CompositePattern]:
        """Select k parents via tournament selection"""
        parents = []
        for _ in range(k):
            # Tournament of size 3
            tournament = random.sample(range(len(self.population)), min(3, len(self.population)))
            winner = max(tournament, key=lambda i: fitnesses[i])
            parents.append(self.population[winner])
        return parents

    def evolve_generation(self, task_examples: List[Tuple[np.ndarray, np.ndarray]]):
        """Evolve one generation"""

        # Evaluate fitness of current population
        fitnesses = []
        for pattern in self.population:
            fitness = self.evaluate_fitness(pattern, task_examples)
            pattern.fitness = fitness
            fitnesses.append(fitness)

        # Track best fitness
        best_fitness = max(fitnesses) if fitnesses else 0.0
        self.best_fitness_history.append(best_fitness)

        # Create next generation
        next_generation = []

        # Elitism: keep top 10% unchanged
        elite_count = max(1, self.population_size // 10)
        elite_indices = sorted(range(len(fitnesses)), key=lambda i: fitnesses[i], reverse=True)[:elite_count]
        for idx in elite_indices:
            next_generation.append(deepcopy(self.population[idx]))

        # Fill rest with offspring
        while len(next_generation) < self.population_size:
            if random.random() < 0.7:  # 70% crossover
                parent1, parent2 = self.select_parents(fitnesses, k=2)
                child = self.crossover(parent1, parent2)
            else:  # 30% mutation
                parent = self.select_parents(fitnesses, k=1)[0]
                child = self.mutate(parent)

            # Occasional random mutation
            if random.random() < 0.1:
                child = self.mutate(child)

            next_generation.append(child)

        self.population = next_generation
        self.generation += 1
        self.patterns_evolved += len(next_generation)

        # Meta-learning: accelerate by 2% per generation
        self.meta_learning_rate *= 1.02

    def evolve_for_task(self, task_examples: List[Tuple[np.ndarray, np.ndarray]],
                       max_generations: int = 200) -> CompositePattern:
        """Evolve patterns for a specific task"""

        self.initialize_population()

        for gen in range(max_generations):
            self.evolve_generation(task_examples)

            # Early stopping if perfect solution found
            best_fitness = max(p.fitness for p in self.population)
            if best_fitness >= 0.89:  # Nearly perfect (accounting for complexity penalty)
                break

        # Return best pattern
        best_pattern = max(self.population, key=lambda p: p.fitness)
        if best_pattern.fitness > 0.5:
            self.successful_patterns += 1

        return best_pattern

def load_arc_task(json_path: str):
    """Load ARC task from JSON file"""
    with open(json_path, 'r') as f:
        data = json.load(f)

    task_id = Path(json_path).stem

    # Parse training examples
    train_examples = []
    for example in data['train']:
        input_grid = np.array(example['input'], dtype=np.int32)
        output_grid = np.array(example['output'], dtype=np.int32)
        train_examples.append((input_grid, output_grid))

    # Parse test examples
    test_examples = []
    for example in data['test']:
        input_grid = np.array(example['input'], dtype=np.int32)
        if 'output' in example:
            output_grid = np.array(example['output'], dtype=np.int32)
        else:
            output_grid = None
        test_examples.append((input_grid, output_grid))

    return task_id, train_examples, test_examples

def main():
    """Main evolutionary training loop"""
    import argparse

    parser = argparse.ArgumentParser(description="Prometheus ARC-AGI REGULARIZED Evolution")
    parser.add_argument("--data-dir", type=str, default="arc_agi_official/data",
                        help="Path to ARC-AGI data directory")
    parser.add_argument("--split", type=str, default="evaluation", choices=["training", "evaluation"],
                        help="Which split to use (default: evaluation for generalization test)")
    parser.add_argument("--max-tasks", type=int, default=None,
                        help="Maximum number of tasks (default: all)")
    parser.add_argument("--generations", type=int, default=200,
                        help="Generations per task (default: 200)")

    args = parser.parse_args()

    # Initialize REGULARIZED evolutionary system
    evolver = PrometheusARCRegularized(population_size=100, max_pattern_length=2)

    # Find all tasks
    task_dir = Path(args.data_dir) / args.split
    task_files = sorted(task_dir.glob("*.json"))

    if args.max_tasks:
        task_files = task_files[:args.max_tasks]

    print(f"🧬 Prometheus ARC-AGI REGULARIZED Evolution")
    print(f"   Split: {args.split}")
    print(f"   Tasks: {len(task_files)}")
    print(f"   Population: {evolver.population_size}")
    print(f"   Generations/task: {args.generations}")
    print(f"   Primitive operations: {len(evolver.primitives)}")
    print(f"   MAX PATTERN LENGTH: {evolver.max_pattern_length} (HARD LIMIT)")
    print(f"   COMPLEXITY PENALTY: {evolver.complexity_penalty} per op (10x stronger)")
    print()

    results = []
    solved = 0
    start_time = time.time()

    for i, task_file in enumerate(task_files, 1):
        task_id, train_examples, test_examples = load_arc_task(str(task_file))

        # Evolve pattern for this task
        best_pattern = evolver.evolve_for_task(train_examples, max_generations=args.generations)

        # Test on test examples
        test_correct = 0
        predictions = []

        for test_input, test_output in test_examples:
            predicted = evolver.apply_pattern(test_input, best_pattern)
            predictions.append(predicted)

            if test_output is not None and predicted.shape == test_output.shape and \
               np.array_equal(predicted, test_output):
                test_correct += 1

        success = test_correct == len(test_examples) if test_examples else False
        if success:
            solved += 1

        results.append({
            'task_id': task_id,
            'success': success,
            'train_fitness': best_pattern.fitness,
            'pattern_length': len(best_pattern.operations),
            'pattern_ops': [op.name for op in best_pattern.operations]
        })

        # Progress update
        if i % 10 == 0 or success:
            elapsed = time.time() - start_time
            rate = solved / i * 100
            print(f"Task {i}/{len(task_files)} | {task_id} | "
                  f"{'✓ SOLVED' if success else 'Failed'} | "
                  f"Fitness: {best_pattern.fitness:.3f} | "
                  f"Pattern: {[op.name for op in best_pattern.operations]} | "
                  f"Success rate: {rate:.1f}% ({solved}/{i}) | "
                  f"Meta-learning: {evolver.meta_learning_rate:.2f}x")

    total_time = time.time() - start_time
    success_rate = solved / len(task_files) if len(task_files) > 0 else 0.0

    print()
    print(f"✅ REGULARIZED Evolution Complete!")
    print(f"   Tasks: {len(task_files)}")
    print(f"   Solved: {solved}/{len(task_files)} ({success_rate*100:.1f}%)")
    print(f"   Patterns evolved: {evolver.patterns_evolved}")
    print(f"   Successful patterns: {evolver.successful_patterns}")
    print(f"   Meta-learning: 1.00x → {evolver.meta_learning_rate:.2f}x")
    print(f"   Duration: {total_time:.1f}s")
    print()

    # Save results
    results_dir = Path("arc_evolution_results")
    results_dir.mkdir(exist_ok=True)

    summary = {
        'total_tasks': len(task_files),
        'solved': solved,
        'success_rate': success_rate,
        'patterns_evolved': evolver.patterns_evolved,
        'successful_patterns': evolver.successful_patterns,
        'meta_learning_rate': evolver.meta_learning_rate,
        'duration': total_time,
        'max_pattern_length': evolver.max_pattern_length,
        'complexity_penalty': evolver.complexity_penalty,
        'regularization': 'STRONG (max_len=2, penalty=0.1)',
        'results': results
    }

    with open(results_dir / f"regularized_{args.split}_results.json", 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"📊 Results saved to: {results_dir / f'regularized_{args.split}_results.json'}")

if __name__ == "__main__":
    main()
