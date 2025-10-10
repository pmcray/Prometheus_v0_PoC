#!/usr/bin/env python3
"""
Prometheus v0.69 - Multi-Task Transfer Learning for ARC-AGI

Phase 2 improvement strategy: Share successful patterns across similar tasks
to avoid re-discovering common solutions.

Approach:
1. Cluster 400 tasks by similarity (grid size, color count, symmetry, etc.)
2. Evolve patterns for each cluster independently
3. Initialize each task's evolution with cluster's best patterns
4. Share successful patterns within cluster as they're discovered

Expected improvement: +3-5 tasks by leveraging pattern reuse
"""

import json
import numpy as np
import random
import time
from pathlib import Path
from typing import List, Tuple, Dict
from dataclasses import dataclass
from collections import defaultdict
from copy import deepcopy

# Import base evolution system
import sys
sys.path.insert(0, str(Path(__file__).parent))
from prometheus_arc_evolution import (
    ARCPrimitives, PrimitiveOperation, CompositePattern,
    PrometheusARCEvolution
)


@dataclass
class TaskFeatures:
    """Features for task clustering"""
    task_id: str
    avg_grid_size: float  # Average of input/output sizes
    num_colors: int  # Number of unique colors
    has_symmetry: bool  # Any symmetry detected
    is_sparse: bool  # <20% filled
    grid_size_change: float  # Output/input size ratio

    def distance(self, other: 'TaskFeatures') -> float:
        """Euclidean distance for clustering"""
        size_diff = abs(self.avg_grid_size - other.avg_grid_size) / 30.0
        color_diff = abs(self.num_colors - other.num_colors) / 10.0
        sym_diff = 1.0 if self.has_symmetry != other.has_symmetry else 0.0
        sparse_diff = 1.0 if self.is_sparse != other.is_sparse else 0.0
        scale_diff = abs(self.grid_size_change - other.grid_size_change)

        return np.sqrt(size_diff**2 + color_diff**2 + sym_diff**2 +
                      sparse_diff**2 + scale_diff**2)


class TaskClusterer:
    """Cluster ARC tasks by similarity"""

    @staticmethod
    def extract_features(task: dict, task_id: str) -> TaskFeatures:
        """Extract features from ARC task"""
        train_pairs = task['train']

        # Aggregate statistics
        sizes = []
        colors = set()
        symmetries = []
        sparsities = []
        size_ratios = []

        for pair in train_pairs:
            input_grid = np.array(pair['input'])
            output_grid = np.array(pair['output'])

            # Sizes
            sizes.append(input_grid.size)
            sizes.append(output_grid.size)

            # Colors
            colors.update(np.unique(input_grid))
            colors.update(np.unique(output_grid))

            # Symmetry (horizontal)
            sym = np.array_equal(input_grid, np.flip(input_grid, axis=1))
            symmetries.append(sym)

            # Sparsity
            filled = np.count_nonzero(input_grid) / input_grid.size
            sparsities.append(filled < 0.2)

            # Size change
            size_ratios.append(output_grid.size / input_grid.size)

        return TaskFeatures(
            task_id=task_id,
            avg_grid_size=np.mean(sizes),
            num_colors=len(colors),
            has_symmetry=any(symmetries),
            is_sparse=any(sparsities),
            grid_size_change=np.mean(size_ratios)
        )

    @staticmethod
    def cluster_tasks(tasks: List[dict], task_ids: List[str],
                     num_clusters: int = 20) -> Dict[int, List[str]]:
        """Simple k-means clustering of tasks"""
        # Extract features
        features = [TaskClusterer.extract_features(task, task_id)
                   for task, task_id in zip(tasks, task_ids)]

        # Random initialization of cluster centers
        centers = random.sample(features, num_clusters)

        # K-means iterations
        for iteration in range(10):
            # Assign to nearest cluster
            clusters = defaultdict(list)
            for feat in features:
                distances = [feat.distance(center) for center in centers]
                cluster_id = np.argmin(distances)
                clusters[cluster_id].append(feat.task_id)

            # Update centers (simplified - just pick random member)
            for cluster_id in range(num_clusters):
                if clusters[cluster_id]:
                    member_id = random.choice(clusters[cluster_id])
                    centers[cluster_id] = next(f for f in features
                                              if f.task_id == member_id)

        # Final assignment
        final_clusters = defaultdict(list)
        for feat in features:
            distances = [feat.distance(center) for center in centers]
            cluster_id = np.argmin(distances)
            final_clusters[cluster_id].append(feat.task_id)

        return dict(final_clusters)


class TransferLearningEvolution:
    """Evolution with pattern transfer across similar tasks"""

    def __init__(self, primitives: List[Tuple[str, callable, dict]]):
        """Initialize with primitive operations"""
        self.primitives = [
            PrimitiveOperation(name, func, params)
            for name, func, params in primitives
        ]
        self.base_evolution = PatternEvolution(
            primitives,
            max_pattern_length=5,
            population_size=50
        )

        # Cluster-level pattern libraries
        self.cluster_patterns: Dict[int, List[CompositePattern]] = defaultdict(list)

    def evolve_with_transfer(self, tasks: List[dict], task_ids: List[str],
                            clusters: Dict[int, List[str]],
                            generations_per_task: int = 200) -> dict:
        """Evolve patterns with transfer learning"""
        # Create task lookup
        task_lookup = {task_id: task for task_id, task in zip(task_ids, tasks)}

        # Track results
        results = {
            'solved_tasks': [],
            'failed_tasks': [],
            'patterns': {},
            'clusters': clusters,
            'total_solved': 0,
            'total_tasks': len(tasks),
            'meta_learning_rate': 1.0
        }

        print(f"🔄 Prometheus ARC-AGI Transfer Learning Evolution")
        print(f"   Tasks: {len(tasks)}")
        print(f"   Clusters: {len(clusters)}")
        print(f"   Generations/task: {generations_per_task}")
        print()

        # Process tasks by cluster
        task_count = 0
        for cluster_id, cluster_task_ids in clusters.items():
            if not cluster_task_ids:
                continue

            print(f"📦 Cluster {cluster_id}: {len(cluster_task_ids)} tasks")

            for task_id in cluster_task_ids:
                task = task_lookup[task_id]
                task_count += 1

                # Initialize population with cluster's best patterns
                if self.cluster_patterns[cluster_id]:
                    # Use top 10 patterns from cluster as initial population
                    initial_pop = self.cluster_patterns[cluster_id][:10]
                else:
                    initial_pop = None

                # Evolve pattern for this task
                pattern, fitness = self.base_evolution.evolve_for_task(
                    task,
                    generations_per_task,
                    initial_population=initial_pop
                )

                # Check if solved
                solved = fitness >= 0.99

                if solved:
                    results['solved_tasks'].append(task_id)
                    results['patterns'][task_id] = {
                        'fitness': fitness,
                        'pattern': [op.name for op in pattern.operations],
                        'cluster': cluster_id
                    }
                    results['total_solved'] += 1

                    # Add successful pattern to cluster library
                    self.cluster_patterns[cluster_id].append(pattern)
                    # Keep only top 20 patterns per cluster
                    self.cluster_patterns[cluster_id].sort(
                        key=lambda p: p.fitness, reverse=True
                    )
                    self.cluster_patterns[cluster_id] = \
                        self.cluster_patterns[cluster_id][:20]

                    # Meta-learning acceleration
                    results['meta_learning_rate'] *= 1.01

                    print(f"   Task {task_count}/{len(tasks)} | {task_id} | ✓ SOLVED | Cluster: {cluster_id} | Fitness: {fitness:.3f} | Pattern: {[op.name for op in pattern.operations]} | Success: {100*results['total_solved']/task_count:.1f}% ({results['total_solved']}/{task_count})")
                else:
                    results['failed_tasks'].append(task_id)

                    if (task_count % 10 == 0) or (task_count == len(tasks)):
                        print(f"   Task {task_count}/{len(tasks)} | {task_id} | Failed | Success: {100*results['total_solved']/task_count:.1f}% ({results['total_solved']}/{task_count})")

        print()
        print(f"✅ Transfer Learning Complete!")
        print(f"   Tasks: {len(tasks)}")
        print(f"   Solved: {results['total_solved']}/{len(tasks)} ({100*results['total_solved']/len(tasks):.1f}%)")
        print(f"   Patterns shared: {sum(len(p) for p in self.cluster_patterns.values())}")

        return results


def main():
    """Run transfer learning evolution on ARC-AGI"""
    import argparse

    parser = argparse.ArgumentParser(description='Transfer Learning ARC Evolution')
    parser.add_argument('--split', type=str, default='training')
    parser.add_argument('--max-tasks', type=int, default=400)
    parser.add_argument('--generations', type=int, default=200)
    parser.add_argument('--clusters', type=int, default=20)
    args = parser.parse_args()

    # Load ARC tasks
    data_path = Path('arc_data/ARC-AGI/data')
    split_path = data_path / args.split

    tasks = []
    task_ids = []

    for task_file in sorted(split_path.glob('*.json'))[:args.max_tasks]:
        with open(task_file) as f:
            task = json.load(f)
            tasks.append(task)
            task_ids.append(task_file.stem)

    # Cluster tasks
    print(f"🔍 Clustering {len(tasks)} tasks into {args.clusters} groups...")
    clusters = TaskClusterer.cluster_tasks(tasks, task_ids, args.clusters)

    # Show cluster distribution
    cluster_sizes = sorted([len(v) for v in clusters.values()], reverse=True)
    print(f"   Cluster sizes: {cluster_sizes[:10]}...")
    print()

    # Define primitives (all 38)
    primitives = [
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
        ('mirror_h', ARCPrimitives.mirror_horizontal, {}),
        ('mirror_v', ARCPrimitives.mirror_vertical, {}),
        ('compress_h', ARCPrimitives.compress_horizontal, {}),
        ('compress_v', ARCPrimitives.compress_vertical, {}),
        ('gravity_down', ARCPrimitives.gravity_down, {}),
        ('gravity_up', ARCPrimitives.gravity_up, {}),
        ('remove_bg', ARCPrimitives.remove_background, {}),
        ('fill_zeros', ARCPrimitives.fill_zeros_common, {}),
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
    ]

    # Run transfer learning
    evolution = TransferLearningEvolution(primitives)

    start_time = time.time()
    results = evolution.evolve_with_transfer(
        tasks, task_ids, clusters, args.generations
    )
    duration = time.time() - start_time

    # Save results
    output_dir = Path('arc_transfer_results')
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f'transfer_{args.split}_{args.clusters}clusters.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print()
    print(f"📊 Results saved to: {output_file}")
    print(f"   Duration: {duration:.1f}s")
    print()


if __name__ == '__main__':
    main()
