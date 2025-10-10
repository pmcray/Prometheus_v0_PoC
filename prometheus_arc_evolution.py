#!/usr/bin/env python3
"""
Prometheus v0.69 - Evolutionary ARC-AGI Pattern Discovery

Implements recursive self-improvement for ARC-AGI through:
1. Primitive operations (building blocks)
2. Pattern composition (chaining operations)
3. Genetic evolution (mutation, crossover, selection)
4. Meta-learning acceleration

This demonstrates Good's (1965) vision of ultraintelligence:
a system that improves its own pattern recognition capabilities.
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

    # ========================================================================
    # NEW PRIMITIVES FROM OPTIONS C & E (Strategic Expansion)
    # ========================================================================

    @staticmethod
    def color_add(grid: np.ndarray, offset: int = 1, **kwargs) -> np.ndarray:
        """Add offset to all non-zero colors (mod 10)"""
        output = grid.copy()
        mask = output > 0
        output[mask] = ((output[mask] + offset - 1) % 9) + 1
        return output

    @staticmethod
    def color_multiply(grid: np.ndarray, factor: int = 2, **kwargs) -> np.ndarray:
        """Multiply non-zero colors by factor (mod 10)"""
        output = grid.copy()
        mask = output > 0
        output[mask] = ((output[mask] * factor - 1) % 9) + 1
        return output

    @staticmethod
    def color_by_row_col(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Set color based on (row + col) mod 9"""
        output = np.zeros_like(grid)
        for r in range(grid.shape[0]):
            for c in range(grid.shape[1]):
                if grid[r, c] != 0:
                    output[r, c] = ((r + c) % 9) + 1
        return output

    @staticmethod
    def diagonal_shift(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Shift each row by its row index (diagonal shearing)"""
        output = np.zeros_like(grid)
        for r in range(grid.shape[0]):
            output[r] = np.roll(grid[r], r)
        return output

    @staticmethod
    def antidiagonal_mirror(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Mirror along anti-diagonal (bottom-left to top-right)"""
        return np.flip(grid.T, axis=1)

    @staticmethod
    def fold_quadrants(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Fold grid into quarters, overlay with max"""
        h, w = grid.shape
        if h < 2 or w < 2:
            return grid.copy()

        h_mid = h // 2
        w_mid = w // 2

        # Extract quadrants (adjust if odd dimensions)
        q1 = grid[:h_mid, :w_mid]
        q2 = grid[:h_mid, w_mid:w_mid+w_mid] if w >= w_mid*2 else np.zeros((h_mid, w_mid), dtype=grid.dtype)
        q3 = grid[h_mid:h_mid+h_mid, :w_mid] if h >= h_mid*2 else np.zeros((h_mid, w_mid), dtype=grid.dtype)
        q4_h = min(h - h_mid, h_mid)
        q4_w = min(w - w_mid, w_mid)
        q4 = grid[h_mid:h_mid+q4_h, w_mid:w_mid+q4_w]

        # Resize to common size
        min_h = min(q1.shape[0], q2.shape[0], q3.shape[0], q4.shape[0])
        min_w = min(q1.shape[1], q2.shape[1], q3.shape[1], q4.shape[1])

        q1 = q1[:min_h, :min_w]
        q2 = q2[:min_h, :min_w]
        q3 = q3[:min_h, :min_w]
        q4 = q4[:min_h, :min_w]

        # Overlay with max
        return np.maximum(np.maximum(q1, q2), np.maximum(q3, q4))

    @staticmethod
    def tile_2x1(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Tile grid 2 times horizontally"""
        return np.concatenate([grid, grid], axis=1)

    @staticmethod
    def tile_1x2(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Tile grid 2 times vertically"""
        return np.concatenate([grid, grid], axis=0)

    @staticmethod
    def tile_3x1(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Tile grid 3 times horizontally"""
        return np.concatenate([grid, grid, grid], axis=1)

    @staticmethod
    def tile_1x3(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Tile grid 3 times vertically"""
        return np.concatenate([grid, grid, grid], axis=0)

    @staticmethod
    def mask_by_color(grid: np.ndarray, keep_color: int = 1, **kwargs) -> np.ndarray:
        """Keep only cells matching specific color"""
        output = np.zeros_like(grid)
        output[grid == keep_color] = keep_color
        return output

    @staticmethod
    def invert_foreground_background(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Swap foreground/background (0 ↔ 1, others unchanged)"""
        output = grid.copy()
        mask_0 = (grid == 0)
        mask_nonzero = (grid > 0)
        output[mask_0] = 1
        output[mask_nonzero] = 0
        return output

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

    @staticmethod
    def extend_edges_outward(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Extend edge pixels outward by 1"""
        if grid.shape[0] == 0 or grid.shape[1] == 0:
            return grid.copy()
        output = np.pad(grid, pad_width=1, mode='edge')
        return output

    @staticmethod
    def extract_corners(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Extract 4 corner pixels only"""
        output = np.zeros_like(grid)
        if grid.shape[0] > 0 and grid.shape[1] > 0:
            output[0, 0] = grid[0, 0]
            output[0, -1] = grid[0, -1]
            output[-1, 0] = grid[-1, 0]
            output[-1, -1] = grid[-1, -1]
        return output

    @staticmethod
    def replicate_smallest_object(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Find smallest object and tile it across grid"""
        from scipy import ndimage
        output = np.zeros_like(grid)

        objects = []
        for color in np.unique(grid):
            if color == 0:
                continue
            mask = (grid == color)
            labeled, num = ndimage.label(mask)
            for i in range(1, num + 1):
                obj_mask = (labeled == i)
                objects.append((np.sum(obj_mask), obj_mask, color))

        if len(objects) == 0:
            return output

        # Get smallest object
        smallest = min(objects, key=lambda x: x[0])
        obj_mask, color = smallest[1], smallest[2]

        # Extract bounding box
        rows = np.any(obj_mask, axis=1)
        cols = np.any(obj_mask, axis=0)
        if not rows.any() or not cols.any():
            return output

        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        obj_pattern = grid[rmin:rmax+1, cmin:cmax+1] * obj_mask[rmin:rmax+1, cmin:cmax+1]

        # Tile across output
        ph, pw = obj_pattern.shape
        if ph == 0 or pw == 0:
            return output

        for r in range(0, output.shape[0], ph):
            for c in range(0, output.shape[1], pw):
                h_end = min(r + ph, output.shape[0])
                w_end = min(c + pw, output.shape[1])
                output[r:h_end, c:w_end] = np.maximum(
                    output[r:h_end, c:w_end],
                    obj_pattern[:h_end-r, :w_end-c]
                )

        return output

class PrometheusARCEvolution:
    """Evolutionary system for ARC pattern discovery"""

    def __init__(self, population_size: int = 50, max_pattern_length: int = 5):
        self.population_size = population_size
        self.max_pattern_length = max_pattern_length
        self.population: List[CompositePattern] = []
        self.generation = 0
        self.meta_learning_rate = 1.0
        self.best_fitness_history = []

        # Initialize primitive operations library
        self.primitives = self._build_primitive_library()

        # Statistics
        self.patterns_evolved = 0
        self.successful_patterns = 0

    def _build_primitive_library(self) -> List[PrimitiveOperation]:
        """Build library of primitive operations"""
        primitives = []

        # Add all primitive methods from ARCPrimitives
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
            # NEW: 12 additional primitives for better coverage
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
            # NEW: 17 primitives from Options C & E
            ('color_add', ARCPrimitives.color_add, {'offset': 1}),
            ('color_add2', ARCPrimitives.color_add, {'offset': 2}),
            ('color_mul', ARCPrimitives.color_multiply, {'factor': 2}),
            ('color_row_col', ARCPrimitives.color_by_row_col, {}),
            ('diag_shift', ARCPrimitives.diagonal_shift, {}),
            ('antidiag_mirror', ARCPrimitives.antidiagonal_mirror, {}),
            ('fold_quads', ARCPrimitives.fold_quadrants, {}),
            ('tile_2x1', ARCPrimitives.tile_2x1, {}),
            ('tile_1x2', ARCPrimitives.tile_1x2, {}),
            ('tile_3x1', ARCPrimitives.tile_3x1, {}),
            ('tile_1x3', ARCPrimitives.tile_1x3, {}),
            ('mask_color1', ARCPrimitives.mask_by_color, {'keep_color': 1}),
            ('mask_color2', ARCPrimitives.mask_by_color, {'keep_color': 2}),
            ('invert_fg_bg', ARCPrimitives.invert_foreground_background, {}),
            ('overlay_max', ARCPrimitives.overlay_max, {}),
            ('extend_out', ARCPrimitives.extend_edges_outward, {}),
            ('corners', ARCPrimitives.extract_corners, {}),
            ('replicate_small', ARCPrimitives.replicate_smallest_object, {}),
        ]

        for name, func, params in primitive_methods:
            primitives.append(PrimitiveOperation(
                name=name,
                function=func,
                parameters=params
            ))

        return primitives

    def initialize_population(self):
        """Create initial population of random patterns"""
        self.population = []

        # Start with single-operation patterns (all primitives)
        for prim in self.primitives:
            pattern = CompositePattern(
                operations=[prim],
                generation=0
            )
            self.population.append(pattern)

        # Add some random 2-3 operation combinations
        while len(self.population) < self.population_size:
            length = random.randint(2, min(3, self.max_pattern_length))
            ops = random.choices(self.primitives, k=length)
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
        """Evaluate pattern fitness on task examples"""
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

        # Fitness = accuracy - complexity penalty
        accuracy = correct / total
        complexity = len(pattern.operations)
        complexity_penalty = 0.01 * complexity  # Prefer simpler patterns

        fitness = accuracy - complexity_penalty

        return max(0.0, fitness)

    def mutate(self, pattern: CompositePattern) -> CompositePattern:
        """Mutate a pattern"""
        new_ops = pattern.operations.copy()

        mutation_type = random.choice(['add', 'remove', 'replace', 'swap'])

        if mutation_type == 'add' and len(new_ops) < self.max_pattern_length:
            # Add random operation
            pos = random.randint(0, len(new_ops))
            new_ops.insert(pos, random.choice(self.primitives))

        elif mutation_type == 'remove' and len(new_ops) > 1:
            # Remove random operation
            pos = random.randint(0, len(new_ops) - 1)
            new_ops.pop(pos)

        elif mutation_type == 'replace' and len(new_ops) > 0:
            # Replace random operation
            pos = random.randint(0, len(new_ops) - 1)
            new_ops[pos] = random.choice(self.primitives)

        elif mutation_type == 'swap' and len(new_ops) > 1:
            # Swap two operations
            i, j = random.sample(range(len(new_ops)), 2)
            new_ops[i], new_ops[j] = new_ops[j], new_ops[i]

        return CompositePattern(
            operations=new_ops,
            generation=self.generation,
            parent_ids=[id(pattern)]
        )

    def crossover(self, parent1: CompositePattern, parent2: CompositePattern) -> CompositePattern:
        """Create offspring from two parents"""
        # Take prefix from parent1, suffix from parent2
        if len(parent1.operations) == 0:
            new_ops = parent2.operations.copy()
        elif len(parent2.operations) == 0:
            new_ops = parent1.operations.copy()
        else:
            split1 = random.randint(0, len(parent1.operations))
            split2 = random.randint(0, len(parent2.operations))

            new_ops = parent1.operations[:split1] + parent2.operations[split2:]

        # Trim if too long
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
                       max_generations: int = 50) -> CompositePattern:
        """Evolve patterns for a specific task"""

        self.initialize_population()

        for gen in range(max_generations):
            self.evolve_generation(task_examples)

            # Early stopping if perfect solution found
            best_fitness = max(p.fitness for p in self.population)
            if best_fitness >= 0.99:  # Nearly perfect
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

    parser = argparse.ArgumentParser(description="Prometheus ARC-AGI Evolutionary Pattern Discovery")
    parser.add_argument("--data-dir", type=str, default="arc_agi_official/data",
                        help="Path to ARC-AGI data directory")
    parser.add_argument("--split", type=str, default="training", choices=["training", "evaluation"],
                        help="Which split to use for evolution")
    parser.add_argument("--max-tasks", type=int, default=None,
                        help="Maximum number of tasks (default: all)")
    parser.add_argument("--generations", type=int, default=50,
                        help="Generations per task")

    args = parser.parse_args()

    # Initialize evolutionary system
    evolver = PrometheusARCEvolution(population_size=50, max_pattern_length=5)

    # Find all tasks
    task_dir = Path(args.data_dir) / args.split
    task_files = sorted(task_dir.glob("*.json"))

    if args.max_tasks:
        task_files = task_files[:args.max_tasks]

    print(f"🧬 Prometheus ARC-AGI Evolutionary Pattern Discovery")
    print(f"   Split: {args.split}")
    print(f"   Tasks: {len(task_files)}")
    print(f"   Population: {evolver.population_size}")
    print(f"   Generations/task: {args.generations}")
    print(f"   Primitive operations: {len(evolver.primitives)}")
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
    success_rate = solved / len(task_files) * 100

    print()
    print(f"✅ Evolution Complete!")
    print(f"   Tasks: {len(task_files)}")
    print(f"   Solved: {solved}/{len(task_files)} ({success_rate:.1f}%)")
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
        'results': results
    }

    with open(results_dir / f"evolution_{args.split}_results.json", 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"📊 Results saved to: {results_dir / f'evolution_{args.split}_results.json'}")

if __name__ == "__main__":
    main()
