#!/usr/bin/env python3
"""
Prometheus ARC Ensemble (v0.80)
Combines baseline, meta-learning, and transfer learning predictions via voting
"""

import sys
import time
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
import argparse

# Import all three evolution strategies
from prometheus_arc_regularized import (
    PrometheusARCRegularized,
    load_arc_task
)
from prometheus_arc_meta_evolution import PrometheusARCMetaEvolution
from prometheus_arc_transfer_evolution import PrometheusARCTransferEvolution
from arc_transfer_learner import ARCTransferLearner


class PrometheusARCEnsemble:
    """
    Ensemble solver combining three strategies:
    1. Baseline regularized evolution
    2. Meta-learning from solved tasks
    3. Transfer learning from task clusters

    Voting strategy: Pick solution with highest fitness
    Tiebreaker: Prefer transfer > meta > baseline
    """

    def __init__(self, use_meta: bool = True, use_transfer: bool = True,
                 population_size: int = 100, max_pattern_length: int = 2):
        """
        Initialize ensemble with three solvers

        Args:
            use_meta: Enable meta-learning solver
            use_transfer: Enable transfer learning solver
            population_size: Population size for evolution
            max_pattern_length: Maximum pattern length
        """
        self.population_size = population_size
        self.max_pattern_length = max_pattern_length

        # Always use baseline
        print("🔧 Initializing baseline solver...")
        self.baseline = PrometheusARCRegularized(
            population_size=population_size,
            max_pattern_length=max_pattern_length
        )

        # Optional meta-learning
        self.meta = None
        if use_meta:
            print("🔧 Initializing meta-learning solver...")
            self.meta = PrometheusARCMetaEvolution(
                population_size=population_size,
                max_pattern_length=max_pattern_length
            )

        # Optional transfer learning
        self.transfer = None
        self.transfer_learner = None
        if use_transfer:
            print("🔧 Initializing transfer learning solver...")
            # Will be initialized after clustering
            pass

        self.use_meta = use_meta
        self.use_transfer = use_transfer

        # Track ensemble statistics
        self.votes = {'baseline': 0, 'meta': 0, 'transfer': 0}
        self.agreements = 0  # All three agree
        self.disagreements = 0  # All three disagree

    def initialize_transfer_learner(self, transfer_learner: ARCTransferLearner):
        """Initialize transfer learning with pre-built clusters"""
        if self.use_transfer:
            print("🔧 Initializing transfer learning solver with clusters...")
            self.transfer_learner = transfer_learner
            self.transfer = PrometheusARCTransferEvolution(
                transfer_learner=transfer_learner,
                population_size=self.population_size,
                max_pattern_length=self.max_pattern_length
            )

    def solve_task(self, train_examples: List[Tuple], test_examples: List[Tuple],
                   task_id: str = None, max_generations: int = 200):
        """
        Solve task using ensemble voting

        Args:
            train_examples: Training input/output pairs
            test_examples: Test input/output pairs
            task_id: Task identifier (for transfer learning)
            max_generations: Generations per solver

        Returns:
            best_pattern: Winning pattern
            best_solver: Which solver won ('baseline', 'meta', 'transfer')
            all_solutions: Dict of all solutions
        """
        solutions = {}

        # Run all enabled solvers
        print(f"  🔄 Running ensemble solvers...", end=" ")

        # 1. Baseline
        try:
            baseline_pattern = self.baseline.evolve_for_task(
                train_examples, max_generations=max_generations
            )
            solutions['baseline'] = {
                'pattern': baseline_pattern,
                'fitness': baseline_pattern.fitness
            }
        except Exception as e:
            print(f"⚠️ Baseline failed: {str(e)[:50]}")
            solutions['baseline'] = None

        # 2. Meta-learning
        if self.use_meta and self.meta:
            try:
                meta_pattern = self.meta.evolve_for_task(
                    train_examples, max_generations=max_generations
                )
                solutions['meta'] = {
                    'pattern': meta_pattern,
                    'fitness': meta_pattern.fitness
                }
            except Exception as e:
                print(f"⚠️ Meta failed: {str(e)[:50]}")
                solutions['meta'] = None

        # 3. Transfer learning
        if self.use_transfer and self.transfer and task_id:
            try:
                self.transfer.set_current_task(task_id)
                transfer_pattern = self.transfer.evolve_for_task(
                    train_examples, max_generations=max_generations
                )
                solutions['transfer'] = {
                    'pattern': transfer_pattern,
                    'fitness': transfer_pattern.fitness
                }
            except Exception as e:
                print(f"⚠️ Transfer failed: {str(e)[:50]}")
                solutions['transfer'] = None

        # Vote: pick solution with highest fitness
        best_solver = None
        best_fitness = -1.0
        best_pattern = None

        # Tiebreaker order: transfer > meta > baseline
        solver_priority = ['transfer', 'meta', 'baseline']

        for solver_name in solver_priority:
            if solver_name in solutions and solutions[solver_name] is not None:
                sol = solutions[solver_name]
                if sol['fitness'] > best_fitness:
                    best_fitness = sol['fitness']
                    best_pattern = sol['pattern']
                    best_solver = solver_name

        if best_solver:
            self.votes[best_solver] += 1

        # Check agreement
        if len([s for s in solutions.values() if s is not None]) >= 2:
            fitnesses = [s['fitness'] for s in solutions.values() if s is not None]
            if len(set(fitnesses)) == 1:
                self.agreements += 1
            else:
                self.disagreements += 1

        print(f"Winner: {best_solver} (fitness: {best_fitness:.3f})")

        return best_pattern, best_solver, solutions

    def record_success(self, task_id: str, pattern, success: bool, fitness: float):
        """Record successful pattern for meta and transfer learning"""
        # Update meta-learning
        if self.use_meta and self.meta and success:
            pattern_names = [op.name for op in pattern.operations]
            self.meta.add_solved_task(task_id, pattern_names)

        # Update transfer learning
        if self.use_transfer and self.transfer and task_id:
            pattern_names = [op.name for op in pattern.operations]
            self.transfer.transfer_learner.add_attempt(
                task_id=task_id,
                pattern=pattern_names,
                success=success,
                fitness=fitness
            )

    def get_statistics(self):
        """Get ensemble voting statistics"""
        total_votes = sum(self.votes.values())
        if total_votes == 0:
            return {}

        return {
            'total_votes': total_votes,
            'baseline_wins': self.votes['baseline'],
            'meta_wins': self.votes['meta'],
            'transfer_wins': self.votes['transfer'],
            'baseline_rate': self.votes['baseline'] / total_votes,
            'meta_rate': self.votes['meta'] / total_votes if self.use_meta else 0,
            'transfer_rate': self.votes['transfer'] / total_votes if self.use_transfer else 0,
            'agreements': self.agreements,
            'disagreements': self.disagreements,
            'agreement_rate': self.agreements / (self.agreements + self.disagreements) if (self.agreements + self.disagreements) > 0 else 0
        }


def main():
    parser = argparse.ArgumentParser(description="ARC Ensemble Evolution v0.80")
    parser.add_argument('--split', type=str, default='evaluation',
                       help='Dataset split (training/evaluation)')
    parser.add_argument('--num-tasks', type=int, default=None,
                       help='Number of tasks to evaluate')
    parser.add_argument('--no-meta', action='store_true',
                       help='Disable meta-learning')
    parser.add_argument('--no-transfer', action='store_true',
                       help='Disable transfer learning')
    parser.add_argument('--generations', type=int, default=200,
                       help='Generations per solver')
    parser.add_argument('--load-transfer-state', type=str, default=None,
                       help='Load transfer learner state')

    args = parser.parse_args()

    print("="*70)
    print("🎯 Prometheus ARC Ensemble v0.80")
    print("="*70)
    print(f"\nSplit: {args.split}")
    print(f"Meta-learning: {'DISABLED' if args.no_meta else 'ENABLED'}")
    print(f"Transfer learning: {'DISABLED' if args.no_transfer else 'ENABLED'}")

    # Initialize transfer learner if enabled
    transfer_learner = None
    if not args.no_transfer:
        print(f"\n{'='*70}")
        print("🔬 Initializing Transfer Learner")
        print(f"{'='*70}")

        transfer_learner = ARCTransferLearner()

        # Try to load existing state
        if args.load_transfer_state and transfer_learner.load_state(args.load_transfer_state):
            print(f"✅ Loaded transfer state from: {args.load_transfer_state}")
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
            print(f"🔬 Clustering tasks...")

            clusters = transfer_learner.cluster_tasks(task_data, num_clusters=20)
            print(f"✅ Created {len(clusters)} clusters")

    # Initialize ensemble
    print(f"\n{'='*70}")
    print("🎯 Initializing Ensemble")
    print(f"{'='*70}")

    ensemble = PrometheusARCEnsemble(
        use_meta=not args.no_meta,
        use_transfer=not args.no_transfer,
        population_size=100,
        max_pattern_length=2
    )

    if transfer_learner:
        ensemble.initialize_transfer_learner(transfer_learner)

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
            # Solve with ensemble
            best_pattern, best_solver, all_solutions = ensemble.solve_task(
                train_examples, test_examples, task_id, max_generations=args.generations
            )

            # Test on test examples
            test_correct = 0
            for test_input, test_output in test_examples:
                predicted = ensemble.baseline.apply_pattern(test_input, best_pattern)

                if test_output is not None and predicted.shape == test_output.shape and \
                   np.array_equal(predicted, test_output):
                    test_correct += 1

            success = test_correct == len(test_examples) if test_examples else False
            if success:
                solved += 1

            # Record for learning
            ensemble.record_success(task_id, best_pattern, success, best_pattern.fitness)

            status = "✓ SOLVED" if success else "✗ FAILED"
            print(f"  {status} | Fitness: {best_pattern.fitness:.3f} | Pattern: {[op.name for op in best_pattern.operations]}")

            results.append({
                'task_id': task_id,
                'success': success,
                'fitness': float(best_pattern.fitness),
                'solution': [op.name for op in best_pattern.operations],
                'winning_solver': best_solver,
                'all_solutions': {
                    k: {'fitness': v['fitness'], 'pattern': [op.name for op in v['pattern'].operations]}
                    if v else None
                    for k, v in all_solutions.items()
                }
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

    # Ensemble statistics
    stats = ensemble.get_statistics()
    if stats:
        print(f"\n📈 Ensemble Statistics:")
        print(f"  Baseline wins: {stats['baseline_wins']}/{stats['total_votes']} ({stats['baseline_rate']*100:.1f}%)")
        if not args.no_meta:
            print(f"  Meta wins: {stats['meta_wins']}/{stats['total_votes']} ({stats['meta_rate']*100:.1f}%)")
        if not args.no_transfer:
            print(f"  Transfer wins: {stats['transfer_wins']}/{stats['total_votes']} ({stats['transfer_rate']*100:.1f}%)")
        print(f"  Agreements: {stats['agreements']}/{stats['agreements']+stats['disagreements']} ({stats['agreement_rate']*100:.1f}%)")

    # Comparison
    print(f"\n📈 Comparison:")
    print(f"  Baseline (v0.69):  5/400 (1.25%)")
    print(f"  Meta (v0.78):      5/400 (1.25%)")
    print(f"  Transfer (v0.79):  5/400 (1.25%)")
    print(f"  Ensemble (v0.80):  {solved}/{len(task_files)} ({solved/len(task_files)*100:.2f}%)")

    # Save results
    output_data = {
        'split': args.split,
        'total_tasks': len(task_files),
        'solved': solved,
        'success_rate': solved / len(task_files),
        'elapsed_seconds': elapsed_time,
        'avg_time_per_task': elapsed_time / len(task_files),
        'ensemble_stats': stats,
        'results': results
    }

    output_file = f"arc_evolution_results/ensemble_{args.split}_results.json"
    Path("arc_evolution_results").mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")
    print(f"\n✅ Evaluation complete!")


if __name__ == "__main__":
    main()
