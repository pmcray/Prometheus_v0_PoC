#!/usr/bin/env python3
"""
Prometheus ARC-AGI Meta-Evolution (v0.78)
Integrates meta-learning with evolution for improved performance

Key Features:
1. Learns from 5 solved tasks (1.2% baseline)
2. Seeds population with successful patterns
3. Biases toward proven primitives
4. Expected: 1.2% → 1.8-2.2% improvement
"""

import json
import numpy as np
import random
import time
from pathlib import Path
from typing import List, Tuple, Dict
from copy import deepcopy

# Import base evolution system
from prometheus_arc_regularized import (
    PrometheusARCRegularized,
    PrimitiveOperation,
    CompositePattern,
    load_arc_task
)

# Import meta-learner
from arc_meta_learner import ARCMetaLearner


class PrometheusARCMetaEvolution(PrometheusARCRegularized):
    """Enhanced evolution with meta-learning from solved tasks

    Extends PrometheusARCRegularized with:
    - Pattern-based population seeding
    - Bias toward successful primitives
    - Transfer learning from solved tasks
    """

    def __init__(self, population_size: int = 100, max_pattern_length: int = 2,
                 meta_learner: ARCMetaLearner = None):
        super().__init__(population_size, max_pattern_length)

        self.meta_learner = meta_learner or ARCMetaLearner()
        self.using_meta_learning = (meta_learner is not None and
                                   len(meta_learner.success_primitives) > 0)

    def initialize_population(self):
        """Initialize population with meta-learning

        If meta_learner has patterns:
        - 10% exact copies of successful sequences
        - 15% variations (add/remove/replace one op)
        - 75% biased random (70% use successful primitives)

        Otherwise falls back to parent class behavior
        """

        if not self.using_meta_learning:
            # Fall back to standard initialization
            super().initialize_population()
            return

        print(f"   🧠 Meta-learning: Seeding population with {len(self.meta_learner.sequence_patterns)} patterns")

        self.population = []

        # Get primitive names for mapping
        primitive_map = {p.name: p for p in self.primitives}
        all_prim_names = [p.name for p in self.primitives]

        success_prims = list(self.meta_learner.success_primitives)
        if not success_prims:
            success_prims = all_prim_names

        # 1. Exact copies (10%)
        exact_count = int(self.population_size * 0.10)
        for _ in range(exact_count):
            if self.meta_learner.sequence_patterns:
                idx = np.random.randint(len(self.meta_learner.sequence_patterns))
                pattern_names = list(self.meta_learner.sequence_patterns[idx])

                # Convert names to PrimitiveOperation objects
                ops = []
                for name in pattern_names:
                    if name in primitive_map:
                        ops.append(primitive_map[name])
                    else:
                        # Fallback if primitive not found
                        ops.append(random.choice(self.primitives))

                if ops:
                    pattern = CompositePattern(operations=ops, generation=0)
                    self.population.append(pattern)

        # 2. Variations (15%)
        variation_count = int(self.population_size * 0.15)
        for _ in range(variation_count):
            if self.meta_learner.sequence_patterns:
                idx = np.random.randint(len(self.meta_learner.sequence_patterns))
                pattern_names = list(self.meta_learner.sequence_patterns[idx])

                # Mutate: add, remove, or replace one primitive
                mutation = np.random.choice(['add', 'remove', 'replace'])

                if mutation == 'add' and len(pattern_names) < self.max_pattern_length:
                    pattern_names.append(np.random.choice(success_prims))
                elif mutation == 'remove' and len(pattern_names) > 1:
                    pattern_names.pop(np.random.randint(len(pattern_names)))
                elif mutation == 'replace' and pattern_names:
                    idx = np.random.randint(len(pattern_names))
                    pattern_names[idx] = np.random.choice(success_prims)

                # Convert to operations
                ops = []
                for name in pattern_names:
                    if name in primitive_map:
                        ops.append(primitive_map[name])
                    else:
                        ops.append(random.choice(self.primitives))

                if ops:
                    pattern = CompositePattern(operations=ops, generation=0)
                    self.population.append(pattern)

        # 3. Biased random (75%)
        remaining = self.population_size - len(self.population)
        for _ in range(remaining):
            length = np.random.randint(1, self.max_pattern_length + 1)

            # 70% use successful primitives
            if np.random.random() < 0.7 and success_prims:
                prim_names = np.random.choice(success_prims, size=length, replace=True)
            else:
                prim_names = np.random.choice(all_prim_names, size=length, replace=True)

            # Convert to operations
            ops = [primitive_map[name] for name in prim_names if name in primitive_map]

            if ops:
                pattern = CompositePattern(operations=ops, generation=0)
                self.population.append(pattern)

        print(f"   ✅ Population seeded: {len(self.population)} individuals")


def main():
    """Main meta-evolution training loop"""
    import argparse

    parser = argparse.ArgumentParser(description="Prometheus ARC-AGI Meta-Evolution")
    parser.add_argument("--data-dir", type=str, default="arc_agi_official/data",
                        help="Path to ARC-AGI data directory")
    parser.add_argument("--split", type=str, default="evaluation",
                        choices=["training", "evaluation"],
                        help="Which split to use")
    parser.add_argument("--max-tasks", type=int, default=None,
                        help="Maximum number of tasks (default: all)")
    parser.add_argument("--generations", type=int, default=200,
                        help="Generations per task (default: 200)")
    parser.add_argument("--patterns-file", type=str, default="arc_learned_patterns.json",
                        help="Path to learned patterns file")
    parser.add_argument("--no-meta", action="store_true",
                        help="Disable meta-learning (baseline comparison)")

    args = parser.parse_args()

    print("="*70)
    print("🧬 Prometheus ARC-AGI Meta-Evolution v0.78")
    print("="*70)

    # Load meta-learner patterns
    meta_learner = ARCMetaLearner()
    patterns_loaded = False

    if not args.no_meta:
        if Path(args.patterns_file).exists():
            print(f"\n📚 Loading learned patterns from {args.patterns_file}...")
            patterns_loaded = meta_learner.load_patterns(args.patterns_file)

            if patterns_loaded:
                stats = meta_learner.get_pattern_statistics()
                print(f"   ✅ Loaded {stats['total_solved']} solved task patterns")
                print(f"   🔧 Success primitives: {stats['unique_primitives']}")
                print(f"   📊 Most common: {stats['most_common'][:5]}")
            else:
                print(f"   ⚠️  Failed to load patterns, using baseline evolution")
        else:
            print(f"   ⚠️  Patterns file not found: {args.patterns_file}")
            print(f"   ℹ️  Run arc_meta_learner.py first to generate patterns")
            print(f"   ℹ️  Using baseline evolution without meta-learning")
    else:
        print(f"\n⚠️  Meta-learning disabled (--no-meta flag)")

    # Initialize meta-evolution system
    evolver = PrometheusARCMetaEvolution(
        population_size=100,
        max_pattern_length=2,
        meta_learner=meta_learner if patterns_loaded and not args.no_meta else None
    )

    # Find all tasks
    task_dir = Path(args.data_dir) / args.split
    task_files = sorted(task_dir.glob("*.json"))

    if args.max_tasks:
        task_files = task_files[:args.max_tasks]

    print(f"\n📋 Configuration:")
    print(f"   Split: {args.split}")
    print(f"   Tasks: {len(task_files)}")
    print(f"   Population: {evolver.population_size}")
    print(f"   Generations/task: {args.generations}")
    print(f"   Max pattern length: {evolver.max_pattern_length}")
    print(f"   Complexity penalty: {evolver.complexity_penalty}")
    print(f"   Meta-learning: {'ENABLED ✅' if evolver.using_meta_learning else 'DISABLED ⚠️'}")
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
        for test_input, test_output in test_examples:
            predicted = evolver.apply_pattern(test_input, best_pattern)

            if test_output is not None and predicted.shape == test_output.shape and \
               np.array_equal(predicted, test_output):
                test_correct += 1

        success = test_correct == len(test_examples) if test_examples else False
        if success:
            solved += 1

            # Learn from this successful solve
            if evolver.using_meta_learning:
                pattern_names = [op.name for op in best_pattern.operations]
                evolver.meta_learner.add_solved_task(task_id, pattern_names, best_pattern.fitness)

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
                  f"Rate: {rate:.1f}% ({solved}/{i})")

    total_time = time.time() - start_time
    success_rate = solved / len(task_files) if len(task_files) > 0 else 0.0

    print()
    print("="*70)
    print("✅ Meta-Evolution Complete!")
    print("="*70)
    print(f"Tasks: {len(task_files)}")
    print(f"Solved: {solved}/{len(task_files)} ({success_rate*100:.2f}%)")
    print(f"Patterns evolved: {evolver.patterns_evolved}")
    print(f"Meta-learning: {'ENABLED' if evolver.using_meta_learning else 'DISABLED'}")
    print(f"Duration: {total_time:.1f}s ({total_time/len(task_files):.1f}s/task)")
    print()

    # Save results
    results_dir = Path("arc_evolution_results")
    results_dir.mkdir(exist_ok=True)

    summary = {
        'version': 'v0.78_meta_evolution',
        'total_tasks': len(task_files),
        'solved': solved,
        'success_rate': success_rate,
        'meta_learning_enabled': evolver.using_meta_learning,
        'patterns_evolved': evolver.patterns_evolved,
        'duration': total_time,
        'results': results
    }

    output_file = results_dir / f"meta_evolution_{args.split}_results.json"
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"📊 Results saved to: {output_file}")

    # Save updated patterns if meta-learning was used
    if evolver.using_meta_learning:
        updated_patterns_file = "arc_learned_patterns_updated.json"
        evolver.meta_learner.save_patterns(updated_patterns_file)
        print(f"💾 Updated patterns saved to: {updated_patterns_file}")

    # Comparison
    print(f"\n📈 Comparison:")
    print(f"   Baseline (v0.69): 5/400 (1.25%)")
    print(f"   Meta (v0.78): {solved}/{len(task_files)} ({success_rate*100:.2f}%)")

    if success_rate > 0.0125:
        improvement = (success_rate / 0.0125 - 1) * 100
        print(f"   Improvement: +{improvement:.1f}% relative 🎉")
    else:
        decline = (1 - success_rate / 0.0125) * 100
        print(f"   Decline: -{decline:.1f}% relative ⚠️")


if __name__ == "__main__":
    main()
