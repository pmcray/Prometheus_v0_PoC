#!/usr/bin/env python3
"""
Prometheus ARC Transfer Evolution (v0.79)
Integrates transfer learning with regularized evolution using task clustering
"""

import sys
import time
import json
import numpy as np
import random
from pathlib import Path
from typing import List, Dict, Tuple
import argparse
from collections import defaultdict, Counter

# Import base evolution system
from prometheus_arc_regularized import (
    PrometheusARCRegularized,
    PrimitiveOperation,
    CompositePattern,
    load_arc_task
)
from arc_transfer_learner import ARCTransferLearner


class PrometheusARCTransferEvolution(PrometheusARCRegularized):
    """
    ARC solver with transfer learning across task clusters

    Extends regularized evolution to use knowledge from similar tasks
    """

    def __init__(self, transfer_learner: ARCTransferLearner = None,
                 population_size: int = 100, max_pattern_length: int = 2):
        super().__init__(population_size=population_size, max_pattern_length=max_pattern_length)

        self.transfer_learner = transfer_learner
        self.using_transfer = (transfer_learner is not None and
                              len(transfer_learner.clusters) > 0)
        self.current_task_id = None

        if self.using_transfer:
            print(f"  🔄 Transfer learning: ENABLED")
            stats = transfer_learner.get_statistics()
            print(f"  📊 Clusters: {stats['num_clusters']}")
            print(f"  📊 Tasks: {stats['total_tasks']}")
        else:
            print(f"  🔄 Transfer learning: DISABLED (baseline mode)")

    def set_current_task(self, task_id: str):
        """Set the task ID for transfer learning"""
        self.current_task_id = task_id

    def initialize_population(self):
        """
        Initialize population using transfer learning

        Uses cluster knowledge if available, falls back to baseline
        """
        if not self.using_transfer or self.current_task_id is None:
            # Baseline: random initialization
            super().initialize_population()
            return

        # Get transfer knowledge for this task's cluster
        knowledge = self.transfer_learner.get_cluster_knowledge(self.current_task_id)

        # Build primitive map
        primitive_map = {p.name: p for p in self.primitives}
        all_prim_names = [p.name for p in self.primitives]

        successful_patterns = knowledge['successful_patterns']
        success_prims = list(knowledge['success_primitives']) if knowledge['success_primitives'] else all_prim_names

        self.population = []

        # 1. Exact copies of successful patterns (15%)
        exact_count = int(self.population_size * 0.15)
        for _ in range(exact_count):
            if successful_patterns:
                # Weight by fitness
                weights = [p['fitness'] for p in successful_patterns]
                if sum(weights) > 0:
                    weights = np.array(weights) / sum(weights)
                    idx = np.random.choice(len(successful_patterns), p=weights)
                else:
                    idx = np.random.randint(len(successful_patterns))

                pattern_names = successful_patterns[idx]['pattern']
                ops = [primitive_map[name] for name in pattern_names if name in primitive_map]

                if ops:
                    pattern = CompositePattern(operations=ops, generation=0)
                    self.population.append(pattern)

        # 2. Variations of successful patterns (15%)
        variation_count = int(self.population_size * 0.15)
        for _ in range(variation_count):
            if successful_patterns:
                idx = np.random.randint(len(successful_patterns))
                pattern_names = list(successful_patterns[idx]['pattern'])

                # Mutate
                mutation = np.random.choice(['add', 'remove', 'replace', 'swap'])

                if mutation == 'add' and len(pattern_names) < self.max_pattern_length:
                    pattern_names.append(np.random.choice(success_prims if success_prims else all_prim_names))
                elif mutation == 'remove' and len(pattern_names) > 1:
                    pattern_names.pop(np.random.randint(len(pattern_names)))
                elif mutation == 'replace' and pattern_names:
                    idx = np.random.randint(len(pattern_names))
                    pattern_names[idx] = np.random.choice(success_prims if success_prims else all_prim_names)
                elif mutation == 'swap' and len(pattern_names) >= 2:
                    i, j = np.random.choice(len(pattern_names), 2, replace=False)
                    pattern_names[i], pattern_names[j] = pattern_names[j], pattern_names[i]

                ops = [primitive_map[name] for name in pattern_names if name in primitive_map]
                if ops:
                    pattern = CompositePattern(operations=ops, generation=0)
                    self.population.append(pattern)

        # 3. Biased random using cluster primitives (40%)
        biased_count = int(self.population_size * 0.40)
        for _ in range(biased_count):
            length = np.random.randint(1, self.max_pattern_length + 1)

            # Use successful primitives with weighted sampling
            if success_prims and knowledge['primitive_frequencies']:
                prims = [p for p in knowledge['primitive_frequencies'].keys() if p in primitive_map]
                if prims:
                    weights = [knowledge['primitive_frequencies'][p] for p in prims]
                    weights = np.array(weights) / sum(weights)
                    prim_names = np.random.choice(prims, size=length, replace=True, p=weights)
                else:
                    prim_names = np.random.choice(all_prim_names, size=length, replace=True)
            elif success_prims:
                prim_names = np.random.choice([p for p in success_prims if p in primitive_map] or all_prim_names,
                                            size=length, replace=True)
            else:
                prim_names = np.random.choice(all_prim_names, size=length, replace=True)

            ops = [primitive_map[name] for name in prim_names if name in primitive_map]
            if ops:
                pattern = CompositePattern(operations=ops, generation=0)
                self.population.append(pattern)

        # 4. Standard random exploration (30%)
        remaining = self.population_size - len(self.population)
        for _ in range(remaining):
            length = np.random.randint(1, self.max_pattern_length + 1)
            ops = random.choices(self.primitives, k=length)
            pattern = CompositePattern(operations=ops, generation=0)
            self.population.append(pattern)

        print(f"    ✅ Population seeded: {len(self.population)} individuals from transfer knowledge")


def main():
    parser = argparse.ArgumentParser(description="ARC Transfer Evolution v0.79")
    parser.add_argument('--split', type=str, default='evaluation',
                       help='Dataset split to evaluate (training/evaluation)')
    parser.add_argument('--num-tasks', type=int, default=None,
                       help='Number of tasks to evaluate (default: all)')
    parser.add_argument('--no-transfer', action='store_true',
                       help='Disable transfer learning (baseline mode)')
    parser.add_argument('--clusters', type=int, default=20,
                       help='Number of clusters for transfer learning')
    parser.add_argument('--load-state', type=str, default=None,
                       help='Load transfer learner state from file')
    parser.add_argument('--generations', type=int, default=200,
                       help='Generations per task (default: 200)')

    args = parser.parse_args()

    print("="*70)
    print("🔄 Prometheus ARC Transfer Evolution v0.79")
    print("="*70)
    print(f"\nSplit: {args.split}")
    print(f"Clusters: {args.clusters}")
    print(f"Transfer: {'DISABLED' if args.no_transfer else 'ENABLED'}")

    # Initialize transfer learner
    transfer_learner = None

    if not args.no_transfer:
        print(f"\n{'='*70}")
        print("🔬 Initializing Transfer Learner")
        print(f"{'='*70}")

        transfer_learner = ARCTransferLearner()

        # Try to load existing state
        if args.load_state and transfer_learner.load_state(args.load_state):
            print(f"✅ Loaded transfer state from: {args.load_state}")
            stats = transfer_learner.get_statistics()
            print(f"  Clusters: {stats['num_clusters']}")
            print(f"  Tasks: {stats['total_tasks']}")
        else:
            # Build clusters from training data
            print(f"📂 Loading training data for clustering...")

            dataset_path = None
            for path in [Path("arc_data/ARC-AGI/data/training"),
                         Path("arc-agi/data/training"),
                         Path("ARC-AGI/data/training")]:
                if path.exists():
                    dataset_path = path
                    break

            if not dataset_path:
                print(f"❌ Training data not found")
                sys.exit(1)

            task_data = {}
            for task_file in dataset_path.glob("*.json"):
                with open(task_file) as f:
                    task_data[task_file.stem] = json.load(f)

            print(f"✅ Loaded {len(task_data)} training tasks")

            print(f"\n🔬 Clustering tasks into {args.clusters} clusters...")
            clusters = transfer_learner.cluster_tasks(task_data, num_clusters=args.clusters)

            print(f"✅ Created {len(clusters)} clusters")
            for cid in sorted(clusters.keys())[:5]:
                print(f"  Cluster {cid}: {len(clusters[cid])} tasks")
            if len(clusters) > 5:
                print(f"  ... and {len(clusters) - 5} more clusters")

    # Initialize evolution system
    print(f"\n{'='*70}")
    print("🧬 Initializing Evolution System")
    print(f"{'='*70}")

    solver = PrometheusARCTransferEvolution(
        transfer_learner=transfer_learner,
        population_size=100,
        max_pattern_length=2
    )

    # Find evaluation tasks
    data_dir = None
    for path in [Path(f"arc_data/ARC-AGI/data/{args.split}"),
                 Path(f"arc-agi/data/{args.split}"),
                 Path(f"ARC-AGI/data/{args.split}")]:
        if path.exists():
            data_dir = path
            break

    if not data_dir:
        print(f"❌ Data directory not found for {args.split}")
        sys.exit(1)

    task_files = sorted(data_dir.glob("*.json"))
    if args.num_tasks:
        task_files = task_files[:args.num_tasks]

    print(f"\n{'='*70}")
    print(f"🚀 Starting Evaluation")
    print(f"{'='*70}")
    print(f"\n📊 Evaluating {len(task_files)} tasks from '{args.split}' split\n")

    results = []
    solved = 0
    start_time = time.time()

    for i, task_file in enumerate(task_files, 1):
        task_id, train_examples, test_examples = load_arc_task(str(task_file))

        print(f"Task {i}/{len(task_files)} | {task_id}", end=" | ")

        try:
            # Set task ID for transfer learning
            if solver.using_transfer:
                solver.set_current_task(task_id)

            # Evolve pattern for this task
            best_pattern = solver.evolve_for_task(train_examples, max_generations=args.generations)

            # Test on test examples
            test_correct = 0
            for test_input, test_output in test_examples:
                predicted = solver.apply_pattern(test_input, best_pattern)

                if test_output is not None and predicted.shape == test_output.shape and \
                   np.array_equal(predicted, test_output):
                    test_correct += 1

            success = test_correct == len(test_examples) if test_examples else False
            if success:
                solved += 1

            # Record attempt for transfer learning
            if solver.using_transfer:
                pattern_names = [op.name for op in best_pattern.operations]
                solver.transfer_learner.add_attempt(
                    task_id=task_id,
                    pattern=pattern_names,
                    success=success,
                    fitness=best_pattern.fitness
                )

            status = "✓ SOLVED" if success else "✗ FAILED"
            print(f"{status} | Fitness: {best_pattern.fitness:.3f} | Pattern: {[op.name for op in best_pattern.operations]}")

            results.append({
                'task_id': task_id,
                'success': success,
                'fitness': float(best_pattern.fitness),
                'solution': [op.name for op in best_pattern.operations]
            })

        except Exception as e:
            print(f"✗ ERROR | {str(e)[:50]}")
            results.append({
                'task_id': task_id,
                'success': False,
                'fitness': 0.0,
                'solution': None,
                'error': str(e)
            })

    # Summary
    elapsed_time = time.time() - start_time

    print(f"\n{'='*70}")
    print(f"📊 RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"\nSplit: {args.split}")
    print(f"Tasks: {len(task_files)}")
    print(f"Solved: {solved}/{len(task_files)} ({solved/len(task_files)*100:.2f}%)")
    print(f"Duration: {elapsed_time:.1f}s ({elapsed_time/len(task_files):.1f}s/task)")

    # Comparison
    print(f"\n📈 Comparison:")
    print(f"  Baseline (v0.69):  5/400 (1.25%)")
    print(f"  Meta (v0.78):      5/400 (1.25%)")
    print(f"  Transfer (v0.79):  {solved}/{len(task_files)} ({solved/len(task_files)*100:.2f}%)")

    # Save results
    output_data = {
        'split': args.split,
        'total_tasks': len(task_files),
        'solved': solved,
        'success_rate': solved / len(task_files),
        'elapsed_seconds': elapsed_time,
        'avg_time_per_task': elapsed_time / len(task_files),
        'results': results
    }

    output_file = f"arc_evolution_results/transfer_evolution_{args.split}_results.json"
    Path("arc_evolution_results").mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")

    # Save updated transfer learner state
    if solver.using_transfer:
        transfer_state_file = f"arc_transfer_learner_updated.json"

        # Convert numpy types to Python types
        def convert_numpy(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            return obj

        # Save with conversion
        cluster_patterns_converted = {}
        for cluster_id, tasks in solver.transfer_learner.cluster_patterns.items():
            cluster_patterns_converted[int(cluster_id)] = {}
            for task_id, patterns in tasks.items():
                cluster_patterns_converted[int(cluster_id)][task_id] = convert_numpy(patterns)

        data = {
            'clusters': {int(k): v for k, v in solver.transfer_learner.clusters.items()},
            'task_features': convert_numpy(solver.transfer_learner.task_features),
            'cluster_patterns': cluster_patterns_converted,
            'cluster_primitives': {
                int(cid): dict(counter)
                for cid, counter in solver.transfer_learner.cluster_primitives.items()
            },
            'cluster_success_primitives': {
                int(cid): list(prims)
                for cid, prims in solver.transfer_learner.cluster_success_primitives.items()
            }
        }

        with open(transfer_state_file, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"💾 Transfer state saved to: {transfer_state_file}")

    print(f"\n✅ Evaluation complete!")


if __name__ == "__main__":
    main()
