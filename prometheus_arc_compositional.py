#!/usr/bin/env python3
"""
Prometheus v0.69 - Compositional ARC-AGI Evolution

Adds object-aware reasoning to pattern evolution:
1. Object detection (connected components)
2. Per-object transformations
3. Spatial relationships
4. Hierarchical pattern composition

This addresses the core limitation of grid-level transformations
by enabling object-level reasoning as humans do.
"""

import json
import numpy as np
import random
import time
from pathlib import Path
from typing import List, Tuple, Dict, Callable, Optional
from dataclasses import dataclass, field
from copy import deepcopy
from scipy import ndimage

@dataclass
class GameObject:
    """Detected object in grid"""
    mask: np.ndarray  # Boolean mask of object pixels
    bounding_box: Tuple[int, int, int, int]  # (row_min, row_max, col_min, col_max)
    color: int
    size: int
    centroid: Tuple[float, float]

@dataclass
class PrimitiveOperation:
    """Atomic transformation operation"""
    name: str
    function: Callable
    operates_on: str  # 'grid' or 'object'
    parameters: dict = field(default_factory=dict)

@dataclass
class CompositePattern:
    """Hierarchical pattern with conditionals"""
    operations: List[PrimitiveOperation]
    conditionals: List[dict] = field(default_factory=list)  # [{condition, true_ops, false_ops}]
    fitness: float = 0.0
    generation: int = 0

class ARCObjectPrimitives:
    """Object-aware transformation operations"""

    @staticmethod
    def detect_objects(grid: np.ndarray) -> List[GameObject]:
        """Detect connected components as objects"""
        objects = []

        # Find unique colors (excluding background 0)
        colors = np.unique(grid[grid != 0])

        for color in colors:
            # Create binary mask for this color
            mask = (grid == color)

            # Label connected components
            labeled, num_features = ndimage.label(mask)

            # Extract each component as an object
            for i in range(1, num_features + 1):
                obj_mask = (labeled == i)

                # Get bounding box
                rows, cols = np.where(obj_mask)
                if len(rows) == 0:
                    continue

                bbox = (rows.min(), rows.max(), cols.min(), cols.max())

                # Calculate properties
                size = obj_mask.sum()
                centroid = (rows.mean(), cols.mean())

                objects.append(GameObject(
                    mask=obj_mask,
                    bounding_box=bbox,
                    color=int(color),
                    size=size,
                    centroid=centroid
                ))

        return objects

    @staticmethod
    def apply_to_each_object(grid: np.ndarray, operation: Callable, **kwargs) -> np.ndarray:
        """Apply transformation to each object separately"""
        objects = ARCObjectPrimitives.detect_objects(grid)
        output = np.zeros_like(grid)

        for obj in objects:
            # Extract object region
            r1, r2, c1, c2 = obj.bounding_box
            obj_region = grid[r1:r2+1, c1:c2+1].copy()
            obj_mask = obj.mask[r1:r2+1, c1:c2+1]

            # Apply transformation
            transformed = operation(obj_region, **kwargs)

            # Place back (handling size changes)
            if transformed.shape == obj_region.shape:
                output[r1:r2+1, c1:c2+1][obj_mask] = transformed[obj_mask]
            # If size changed, place at original position (may clip)
            else:
                out_r = min(r1 + transformed.shape[0], output.shape[0])
                out_c = min(r1 + transformed.shape[1], output.shape[1])
                output[r1:out_r, c1:out_c] = transformed[:out_r-r1, :out_c-c1]

        return output

    @staticmethod
    def extract_largest_object(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Keep only the largest object"""
        objects = ARCObjectPrimitives.detect_objects(grid)
        if not objects:
            return grid.copy()

        largest = max(objects, key=lambda o: o.size)
        output = np.zeros_like(grid)
        output[largest.mask] = grid[largest.mask]
        return output

    @staticmethod
    def count_objects_to_grid(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Create grid filled with object count"""
        objects = ARCObjectPrimitives.detect_objects(grid)
        count = len(objects)
        return np.full_like(grid, count)

    @staticmethod
    def sort_objects_by_size(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Rearrange objects by size (largest first)"""
        objects = ARCObjectPrimitives.detect_objects(grid)
        if not objects:
            return grid.copy()

        # Sort by size descending
        objects.sort(key=lambda o: o.size, reverse=True)

        output = np.zeros_like(grid)
        row_offset = 0

        for obj in objects:
            r1, r2, c1, c2 = obj.bounding_box
            obj_height = r2 - r1 + 1

            # Place object at new position
            if row_offset + obj_height <= output.shape[0]:
                output[row_offset:row_offset+obj_height, c1:c2+1][obj.mask[r1:r2+1, c1:c2+1]] = \
                    grid[r1:r2+1, c1:c2+1][obj.mask[r1:r2+1, c1:c2+1]]
                row_offset += obj_height

        return output

    @staticmethod
    def fill_inside_objects(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Fill holes inside objects"""
        objects = ARCObjectPrimitives.detect_objects(grid)
        output = grid.copy()

        for obj in objects:
            # Fill holes in this object's mask
            filled_mask = ndimage.binary_fill_holes(obj.mask)
            output[filled_mask] = obj.color

        return output

    @staticmethod
    def object_to_background_color(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Change all objects to background color (0)"""
        return np.where(grid != 0, 0, grid)

    @staticmethod
    def scale_each_object(grid: np.ndarray, factor: int = 2, **kwargs) -> np.ndarray:
        """Scale each object independently"""
        objects = ARCObjectPrimitives.detect_objects(grid)
        if not objects:
            return grid.copy()

        # Calculate output size
        max_r = max(obj.bounding_box[1] for obj in objects)
        max_c = max(obj.bounding_box[3] for obj in objects)
        output = np.zeros((max_r * factor + 1, max_c * factor + 1), dtype=grid.dtype)

        for obj in objects:
            r1, r2, c1, c2 = obj.bounding_box
            obj_region = grid[r1:r2+1, c1:c2+1]

            # Scale object
            scaled = np.repeat(np.repeat(obj_region, factor, axis=0), factor, axis=1)

            # Place in output
            new_r1 = r1 * factor
            new_c1 = c1 * factor
            output[new_r1:new_r1+scaled.shape[0], new_c1:new_c1+scaled.shape[1]] = scaled

        return output

    @staticmethod
    def align_objects_horizontal(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Align all objects horizontally"""
        objects = ARCObjectPrimitives.detect_objects(grid)
        if not objects:
            return grid.copy()

        output = np.zeros_like(grid)
        col_offset = 0

        for obj in objects:
            r1, r2, c1, c2 = obj.bounding_box
            obj_width = c2 - c1 + 1

            if col_offset + obj_width <= output.shape[1]:
                output[r1:r2+1, col_offset:col_offset+obj_width][obj.mask[r1:r2+1, c1:c2+1]] = \
                    grid[r1:r2+1, c1:c2+1][obj.mask[r1:r2+1, c1:c2+1]]
                col_offset += obj_width

        return output

    @staticmethod
    def replicate_smallest_object(grid: np.ndarray, **kwargs) -> np.ndarray:
        """Copy smallest object to all positions"""
        objects = ARCObjectPrimitives.detect_objects(grid)
        if not objects:
            return grid.copy()

        smallest = min(objects, key=lambda o: o.size)
        r1, r2, c1, c2 = smallest.bounding_box
        template = grid[r1:r2+1, c1:c2+1].copy()

        # Tile the template
        output = np.zeros_like(grid)
        h, w = template.shape

        for r in range(0, output.shape[0], h):
            for c in range(0, output.shape[1], w):
                end_r = min(r + h, output.shape[0])
                end_c = min(c + w, output.shape[1])
                output[r:end_r, c:end_c] = template[:end_r-r, :end_c-c]

        return output

    @staticmethod
    def rotate_each_object(grid: np.ndarray, k: int = 1, **kwargs) -> np.ndarray:
        """Rotate each object independently"""
        objects = ARCObjectPrimitives.detect_objects(grid)
        output = np.zeros_like(grid)

        for obj in objects:
            r1, r2, c1, c2 = obj.bounding_box
            obj_region = grid[r1:r2+1, c1:c2+1].copy()

            # Rotate
            rotated = np.rot90(obj_region, k=k)

            # Place back (may not fit if size changed)
            if rotated.shape[0] <= output.shape[0] - r1 and \
               rotated.shape[1] <= output.shape[1] - c1:
                output[r1:r1+rotated.shape[0], c1:c1+rotated.shape[1]] = rotated

        return output

# Import base primitives from original evolution
import sys
sys.path.append(str(Path(__file__).parent))
from prometheus_arc_evolution import ARCPrimitives, PrometheusARCEvolution

class PrometheusARCCompositional(PrometheusARCEvolution):
    """Enhanced evolution with object-aware primitives"""

    def _build_primitive_library(self) -> List[PrimitiveOperation]:
        """Build library including object-aware operations"""
        primitives = []

        # Add original grid-level primitives
        grid_primitives = [
            ('identity', ARCPrimitives.identity, 'grid', {}),
            ('rotate_90', ARCPrimitives.rotate_90, 'grid', {}),
            ('rotate_180', ARCPrimitives.rotate_180, 'grid', {}),
            ('flip_h', ARCPrimitives.flip_horizontal, 'grid', {}),
            ('flip_v', ARCPrimitives.flip_vertical, 'grid', {}),
            ('transpose', ARCPrimitives.transpose, 'grid', {}),
            ('scale_2x', ARCPrimitives.scale_2x, 'grid', {}),
            ('gravity_down', ARCPrimitives.gravity_down, 'grid', {}),
            ('mirror_h', ARCPrimitives.mirror_horizontal, 'grid', {}),
            ('mirror_v', ARCPrimitives.mirror_vertical, 'grid', {}),
        ]

        # Add NEW object-aware primitives
        object_primitives = [
            ('extract_largest', ARCObjectPrimitives.extract_largest_object, 'grid', {}),
            ('fill_inside', ARCObjectPrimitives.fill_inside_objects, 'grid', {}),
            ('sort_by_size', ARCObjectPrimitives.sort_objects_by_size, 'grid', {}),
            ('align_horizontal', ARCObjectPrimitives.align_objects_horizontal, 'grid', {}),
            ('scale_objects_2x', ARCObjectPrimitives.scale_each_object, 'grid', {'factor': 2}),
            ('rotate_objects_90', ARCObjectPrimitives.rotate_each_object, 'grid', {'k': 1}),
            ('replicate_smallest', ARCObjectPrimitives.replicate_smallest_object, 'grid', {}),
            ('objects_to_bg', ARCObjectPrimitives.object_to_background_color, 'grid', {}),
        ]

        for name, func, op_type, params in grid_primitives + object_primitives:
            primitives.append(PrimitiveOperation(
                name=name,
                function=func,
                operates_on=op_type,
                parameters=params
            ))

        return primitives

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Compositional ARC-AGI Evolution")
    parser.add_argument("--data-dir", type=str, default="arc_agi_official/data")
    parser.add_argument("--split", type=str, default="training")
    parser.add_argument("--max-tasks", type=int, default=None)
    parser.add_argument("--generations", type=int, default=50)
    parser.add_argument("--population", type=int, default=50)

    args = parser.parse_args()

    # Initialize compositional system
    evolver = PrometheusARCCompositional(
        population_size=args.population,
        max_pattern_length=5
    )

    # Find tasks
    task_dir = Path(args.data_dir) / args.split
    task_files = sorted(task_dir.glob("*.json"))

    if args.max_tasks:
        task_files = task_files[:args.max_tasks]

    print(f"🧬 Prometheus Compositional ARC-AGI Evolution")
    print(f"   Split: {args.split}")
    print(f"   Tasks: {len(task_files)}")
    print(f"   Population: {evolver.population_size}")
    print(f"   Generations/task: {args.generations}")
    print(f"   Primitive operations: {len(evolver.primitives)} (including object-aware)")
    print()

    # Load function from parent
    from prometheus_arc_evolution import load_arc_task

    results = []
    solved = 0
    start_time = time.time()

    for i, task_file in enumerate(task_files, 1):
        task_id, train_examples, test_examples = load_arc_task(str(task_file))

        # Evolve pattern
        best_pattern = evolver.evolve_for_task(train_examples, max_generations=args.generations)

        # Test
        test_correct = 0
        for test_input, test_output in test_examples:
            try:
                predicted = evolver.apply_pattern(test_input, best_pattern)
                if test_output is not None and predicted.shape == test_output.shape and \
                   np.array_equal(predicted, test_output):
                    test_correct += 1
            except Exception as e:
                pass

        success = test_correct == len(test_examples) if test_examples else False
        if success:
            solved += 1

        results.append({
            'task_id': task_id,
            'success': success,
            'train_fitness': best_pattern.fitness,
            'pattern_ops': [op.name for op in best_pattern.operations]
        })

        if i % 10 == 0 or success:
            rate = solved / i * 100
            print(f"Task {i}/{len(task_files)} | {task_id} | "
                  f"{'✓ SOLVED' if success else 'Failed'} | "
                  f"Fitness: {best_pattern.fitness:.3f} | "
                  f"Pattern: {[op.name for op in best_pattern.operations]} | "
                  f"Success rate: {rate:.1f}% ({solved}/{i})")

    total_time = time.time() - start_time
    success_rate = solved / len(task_files) * 100

    print()
    print(f"✅ Compositional Evolution Complete!")
    print(f"   Solved: {solved}/{len(task_files)} ({success_rate:.1f}%)")
    print(f"   Duration: {total_time:.1f}s")

    # Save
    results_dir = Path("arc_compositional_results")
    results_dir.mkdir(exist_ok=True)

    with open(results_dir / f"compositional_{args.split}_results.json", 'w') as f:
        json.dump({
            'total_tasks': len(task_files),
            'solved': solved,
            'success_rate': success_rate,
            'duration': total_time,
            'results': results
        }, f, indent=2)

    print(f"📊 Results saved to: {results_dir}")

if __name__ == "__main__":
    main()
