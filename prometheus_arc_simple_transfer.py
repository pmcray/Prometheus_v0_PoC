#!/usr/bin/env python3
"""
Prometheus v0.69 - Simplified Transfer Learning

Strategy: Run base evolution on clustered task groups to find shared patterns.
Uses existing PrometheusARCEvolution - no reimplementation needed.
"""

import json
import numpy as np
import random
from pathlib import Path
from typing import List, Dict
from collections import defaultdict
from dataclasses import dataclass

# Import base system
import sys
sys.path.insert(0, str(Path(__file__).parent))
from prometheus_arc_evolution import PrometheusARCEvolution


@dataclass
class TaskFeatures:
    """Features for task clustering"""
    task_id: str
    avg_grid_size: float
    num_colors: int
    has_symmetry: bool
    is_sparse: bool
    grid_size_change: float

    def distance(self, other: 'TaskFeatures') -> float:
        """Euclidean distance"""
        size_diff = abs(self.avg_grid_size - other.avg_grid_size) / 30.0
        color_diff = abs(self.num_colors - other.num_colors) / 10.0
        sym_diff = 1.0 if self.has_symmetry != other.has_symmetry else 0.0
        sparse_diff = 1.0 if self.is_sparse != other.is_sparse else 0.0
        scale_diff = abs(self.grid_size_change - other.grid_size_change)

        return np.sqrt(size_diff**2 + color_diff**2 + sym_diff**2 +
                      sparse_diff**2 + scale_diff**2)


def extract_features(task: dict, task_id: str) -> TaskFeatures:
    """Extract features from task"""
    train_pairs = task['train']

    sizes = []
    colors = set()
    symmetries = []
    sparsities = []
    size_ratios = []

    for pair in train_pairs:
        input_grid = np.array(pair['input'])
        output_grid = np.array(pair['output'])

        sizes.append(input_grid.size)
        sizes.append(output_grid.size)

        colors.update(np.unique(input_grid))
        colors.update(np.unique(output_grid))

        sym = np.array_equal(input_grid, np.flip(input_grid, axis=1))
        symmetries.append(sym)

        filled = np.count_nonzero(input_grid) / input_grid.size
        sparsities.append(filled < 0.2)

        size_ratios.append(output_grid.size / input_grid.size)

    return TaskFeatures(
        task_id=task_id,
        avg_grid_size=np.mean(sizes),
        num_colors=len(colors),
        has_symmetry=any(symmetries),
        is_sparse=any(sparsities),
        grid_size_change=np.mean(size_ratios)
    )


def cluster_tasks(tasks: List[dict], task_ids: List[str],
                 num_clusters: int = 20) -> Dict[int, List[str]]:
    """Simple k-means clustering"""
    features = [extract_features(task, task_id)
               for task, task_id in zip(tasks, task_ids)]

    centers = random.sample(features, num_clusters)

    # K-means iterations
    for _ in range(10):
        clusters = defaultdict(list)
        for feat in features:
            distances = [feat.distance(center) for center in centers]
            cluster_id = np.argmin(distances)
            clusters[cluster_id].append(feat.task_id)

        # Update centers
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


def main():
    """Run transfer learning by clustering then evolving"""
    import argparse
    import time

    parser = argparse.ArgumentParser()
    parser.add_argument('--split', default='training')
    parser.add_argument('--max-tasks', type=int, default=400)
    parser.add_argument('--generations', type=int, default=200)
    parser.add_argument('--clusters', type=int, default=20)
    args = parser.parse_args()

    # Load tasks
    data_path = Path('arc_data/ARC-AGI/data') / args.split

    tasks = []
    task_ids = []

    for task_file in sorted(data_path.glob('*.json'))[:args.max_tasks]:
        with open(task_file) as f:
            tasks.append(json.load(f))
            task_ids.append(task_file.stem)

    # Cluster
    print(f"🔍 Clustering {len(tasks)} tasks into {args.clusters} groups...")
    clusters = cluster_tasks(tasks, task_ids, args.clusters)

    cluster_sizes = sorted([len(v) for v in clusters.values()], reverse=True)
    print(f"   Cluster sizes: {cluster_sizes[:10]}...")
    print()

    # Create task lookup
    task_lookup = {tid: task for tid, task in zip(task_ids, tasks)}

    # Results
    results = {
        'solved_tasks': [],
        'failed_tasks': [],
        'patterns': {},
        'total_solved': 0,
        'total_tasks': len(tasks),
        'clusters': {str(k): v for k, v in clusters.items()}
    }

    print(f"🔄 Prometheus Transfer Learning Evolution")
    print(f"   Tasks: {len(tasks)}")
    print(f"   Clusters: {len(clusters)}")
    print(f"   Generations/task: {args.generations}")
    print()

    # Process all tasks
    evolution = PrometheusARCEvolution(
        population_size=50,
        max_pattern_length=5
    )

    task_count = 0
    start_time = time.time()

    for cluster_id, cluster_task_ids in clusters.items():
        if not cluster_task_ids:
            continue

        print(f"📦 Cluster {cluster_id}: {len(cluster_task_ids)} tasks")

        for task_id in cluster_task_ids:
            task = task_lookup[task_id]
            task_count += 1

            # Evolve pattern
            pattern, fitness = evolution.evolve_pattern_for_task(
                task, args.generations
            )

            solved = fitness >= 0.99

            if solved:
                results['solved_tasks'].append(task_id)
                results['patterns'][task_id] = {
                    'fitness': fitness,
                    'pattern': [op.name for op in pattern.operations],
                    'cluster': cluster_id
                }
                results['total_solved'] += 1

                print(f"   ✓ {task_count}/{len(tasks)} | {task_id} | SOLVED | Fitness: {fitness:.3f} | Pattern: {[op.name for op in pattern.operations]} | Success: {100*results['total_solved']/task_count:.1f}% ({results['total_solved']}/{task_count})")
            else:
                results['failed_tasks'].append(task_id)

                if (task_count % 10 == 0) or (task_count == len(tasks)):
                    print(f"   {task_count}/{len(tasks)} | {task_id} | Failed | Success: {100*results['total_solved']/task_count:.1f}% ({results['total_solved']}/{task_count})")

    duration = time.time() - start_time

    print()
    print(f"✅ Transfer Learning Complete!")
    print(f"   Tasks: {len(tasks)}")
    print(f"   Solved: {results['total_solved']}/{len(tasks)} ({100*results['total_solved']/len(tasks):.1f}%)")
    print(f"   Duration: {duration:.1f}s")

    # Save
    output_dir = Path('arc_transfer_results')
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f'simple_transfer_{args.split}.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"📊 Results saved to: {output_file}")


if __name__ == '__main__':
    main()
