#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus ARC v0.94: Meta-Learning on Constraints

Based on v0.93 constraint-based search, this version adds meta-learning
to adaptively refine primitive filtering based on historical performance.

Key Innovation:
- Learn from constraint->primitive->success mappings across tasks
- Adaptive filtering based on historical data
- 80% exploitation, 20% exploration strategy
- Gets better over time as it sees more tasks

Expected Performance: 15-20% solve rate (vs 10-15% in v0.93)
"""

import json
import time
from typing import List, Dict
from collections import defaultdict

# Import v0.93 constraint-based search
from prometheus_arc_v093_constraints import (
    PrometheusARC_v093_Constraints,
    ConstraintExtractor,
    PrimitiveFilter
)

# Import meta-learner
from arc_meta_learner_v094 import ConstraintMetaLearner


class PrometheusARC_v094_MetaLearning(PrometheusARC_v093_Constraints):
    """
    v0.94: Add meta-learning on constraints to v0.93 baseline.

    Key improvement: Learn which primitives work best for each constraint
    pattern, using historical success data to adaptively refine filtering.
    """

    def __init__(self,
                 database_path: str = 'arc_learned_patterns_v094.json',
                 use_llm: bool = False,  # FORCE disable LLM (performance fix)
                 use_adaptive: bool = True,
                 use_metarefine: bool = True,
                 max_refinement_cycles: int = 1):  # Reduce from 3 to 1 for speed
        # PERFORMANCE FIX: Explicitly pass use_llm=False to avoid 17s LLM subprocess
        super().__init__(
            use_llm=use_llm,
            use_adaptive=use_adaptive,
            use_metarefine=use_metarefine,
            max_refinement_cycles=max_refinement_cycles
        )

        # v0.94 components
        self.meta_learner = ConstraintMetaLearner()
        self.database_path = database_path

        # Try to load existing database
        if self.meta_learner.load_database(database_path):
            stats = self.meta_learner.get_statistics()
            print(f"  [v0.94] Loaded meta-learner database:")
            print(f"    - {stats['tasks_seen']} tasks seen")
            print(f"    - {stats['unique_constraint_patterns']} constraint patterns")
            print(f"    - {stats['primitives_learned']} primitives learned")
            print(f"    - {stats['success_rate']*100:.1f}% success rate")
        else:
            print(f"  [v0.94] Starting with empty meta-learner database")

        # Statistics
        self.meta_learning_usage = defaultdict(int)
        self.learning_improvements = 0
        self.tasks_processed = 0

    def solve_task(self,
                   train_examples: List[Dict],
                   test_examples: List[Dict],
                   task_id: str) -> Dict:
        """
        Solve task using meta-learning enhanced constraint-based search.

        Flow:
        1. Extract constraints from training examples (v0.93)
        2. Query meta-learner for refined filter based on constraints (NEW!)
        3. If meta-learner has data: Use learned filter (adaptive mode)
        4. If no data: Fall back to v0.93 constraint filtering
        5. Record attempt for future learning (NEW!)
        6. Save database periodically (NEW!)
        """
        print(f"  [v0.94] Solving task {task_id}...")

        # Step 1: Extract constraints (same as v0.93)
        task_data = {'train': train_examples}
        constraints = self.constraint_extractor.extract_all_constraints(task_data)

        print(f"  [Constraints] {constraints}")

        # Step 2: Query meta-learner for refined filter
        v093_strict = self.primitive_filter.filter_by_constraints(
            constraints, mode='strict'
        )
        v093_soft = self.primitive_filter.filter_by_constraints(
            constraints, mode='soft'
        )

        # Try to get learned filter
        learned_filter = self.meta_learner.get_refined_filter(
            constraints,
            mode='adaptive',
            top_k=15,
            v093_fallback=v093_strict
        )

        # Decide which filter to use
        if learned_filter is not None:
            # Meta-learner has historical data - use it!
            filter_to_use = learned_filter
            filter_mode = 'meta_learned'
            print(f"  [v0.94 Meta] Using learned filter: {len(learned_filter)} primitives")
            self.meta_learning_usage['meta_learned'] += 1

            # Check if learned filter is different from v0.93
            if set(learned_filter) != set(v093_strict):
                self.learning_improvements += 1
                print(f"  [v0.94 Meta] Learned filter differs from v0.93 (potential improvement!)")
        else:
            # No historical data - fall back to v0.93
            filter_to_use = v093_strict if len(v093_strict) >= 3 else v093_soft
            filter_mode = 'v093_fallback'
            print(f"  [v0.94 Meta] No historical data, falling back to v0.93")
            self.meta_learning_usage['v093_fallback'] += 1

        # Calculate search space reduction
        original_space = len(self.primitive_methods) ** 5
        filtered_space = len(filter_to_use) ** 5 if filter_to_use else original_space
        reduction = 1 - (filtered_space / original_space) if filter_to_use else 0

        print(f"  [Filter] {len(filter_to_use)} prims ({reduction*100:.1f}% reduction, mode: {filter_mode})")

        # Step 3: Run evolution with filtered primitives
        original_methods = self.primitive_methods.copy()
        self.primitive_methods = {k: v for k, v in self.primitive_methods.items()
                                 if k in filter_to_use}

        try:
            # Call v0.92 solve_task (skipping v0.93's filtering since we already did it)
            from prometheus_arc_v092_baseline import PrometheusARC_v092_Baseline
            result = PrometheusARC_v092_Baseline.solve_task(
                self, train_examples, test_examples, task_id
            )

            # Add v0.94 metadata
            result['constraints'] = constraints
            result['filtered_primitives'] = len(filter_to_use)
            result['search_space_reduction'] = reduction
            result['filter_mode'] = filter_mode

            # Step 4: Record attempt for future learning
            self.meta_learner.record_attempt(
                constraints,
                result['pattern'],
                result['fitness'],
                task_id
            )

            print(f"  [v0.94 Meta] Recorded attempt: fitness={result['fitness']:.3f}")

        finally:
            # Restore original primitive methods
            self.primitive_methods = original_methods

        # Step 5: Save database periodically (every 5 tasks)
        self.tasks_processed += 1
        if self.tasks_processed % 5 == 0:
            self.meta_learner.save_database(self.database_path)
            stats = self.meta_learner.get_statistics()
            print(f"  [v0.94 Meta] Saved database ({stats['total_attempts']} attempts, "
                  f"{stats['success_rate']*100:.1f}% success rate)")

        return result

    def get_statistics(self) -> Dict:
        """Get v0.94 statistics."""
        stats = super().get_statistics()

        # Add meta-learning statistics
        meta_stats = self.meta_learner.get_statistics()

        stats.update({
            'meta_learning_usage': dict(self.meta_learning_usage),
            'learning_improvements': self.learning_improvements,
            'meta_learner_stats': meta_stats
        })

        return stats

    def save_database(self):
        """Explicitly save meta-learner database."""
        self.meta_learner.save_database(self.database_path)
        print(f"  [v0.94] Saved meta-learner database to {self.database_path}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Test v0.94 meta-learning on ARC evaluation set"""
    import argparse

    parser = argparse.ArgumentParser(description='ARC v0.94 Meta-Learning Solver')
    parser.add_argument('--split', type=str, default='evaluation',
                       choices=['training', 'evaluation'],
                       help='Dataset split to use')
    parser.add_argument('--num-tasks', type=int, default=None,
                       help='Number of tasks to test (default: all)')
    parser.add_argument('--no-llm', action='store_true',
                       help='Disable Phase 6 (LLM guidance)')
    parser.add_argument('--no-adaptive', action='store_true',
                       help='Disable Phase 5 (adaptive primitives)')
    parser.add_argument('--no-meta', action='store_true',
                       help='Disable Phase 7 (meta-refinement)')
    parser.add_argument('--cycles', type=int, default=3,
                       help='Maximum refinement cycles')
    parser.add_argument('--database', type=str, default='arc_learned_patterns_v094.json',
                       help='Path to meta-learner database')

    args = parser.parse_args()

    # Load ARC data
    from pathlib import Path

    task_dir = Path(f"arc_agi_2/data/{args.split}")
    if not task_dir.exists():
        print(f"Error: {task_dir} not found")
        return

    task_files = sorted(task_dir.glob("*.json"))
    if not task_files:
        print(f"Error: No task files found in {task_dir}")
        return

    # Load tasks
    arc_data = {}
    for task_file in task_files:
        with open(task_file, 'r') as f:
            arc_data[task_file.stem] = json.load(f)

    # Select tasks
    task_ids = list(arc_data.keys())
    if args.num_tasks:
        task_ids = task_ids[:args.num_tasks]

    print("="*80)
    print("🧠 Prometheus ARC v0.94: Meta-Learning on Constraints")
    print("="*80)
    print(f"Split: {args.split}")
    print(f"Tasks: {len(task_ids)}")
    print(f"Database: {args.database}")
    print(f"Phase 5 (Adaptive): {'Disabled' if args.no_adaptive else 'Enabled'}")
    print(f"Phase 6 (LLM): {'Disabled' if args.no_llm else 'Enabled'}")
    print(f"Phase 7 (Meta): {'Disabled' if args.no_meta else 'Enabled'}")
    print(f"Max refinement cycles: {args.cycles}")
    print()
    print("Key Improvements over v0.93:")
    print("  1. Meta-learning on constraint->primitive->success mappings")
    print("  2. Adaptive filtering based on historical performance")
    print("  3. 80% exploitation, 20% exploration strategy")
    print("  4. Learning curve: Improves with more tasks")
    print("="*80)
    print()

    # Initialize solver
    solver = PrometheusARC_v094_MetaLearning(
        database_path=args.database,
        use_llm=not args.no_llm,
        use_adaptive=not args.no_adaptive,
        use_metarefine=not args.no_meta,
        max_refinement_cycles=args.cycles
    )

    # Solve tasks
    results = []
    solved_count = 0
    start_time = time.time()

    for i, task_id in enumerate(task_ids, 1):
        task = arc_data[task_id]
        train_examples = task['train']
        test_examples = task['test']

        print(f"[{i}/{len(task_ids)}] Task {task_id}")

        try:
            result = solver.solve_task(train_examples, test_examples, task_id)

            success = result['fitness'] >= 0.95
            if success:
                solved_count += 1

            result_summary = {
                'task_id': task_id,
                'success': success,
                'fitness': result['fitness'],
                'pattern': result['pattern'],
                'method': result['method'],
                'generation_budget': result.get('generation_budget', 100),
                'constraints': result.get('constraints', {}),
                'search_space_reduction': result.get('search_space_reduction', 0),
                'filter_mode': result.get('filter_mode', 'none')
            }
            results.append(result_summary)

            status = "✓ SOLVED" if success else f"✗ Failed (fitness: {result['fitness']:.3f})"
            print(f"  {status} via {result['method']}")
            print(f"  Reduction: {result.get('search_space_reduction', 0)*100:.1f}%")
            print(f"  Filter: {result.get('filter_mode', 'unknown')}")
            print()

        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'task_id': task_id,
                'success': False,
                'error': str(e)
            })
            print()

    # Save final database
    solver.save_database()

    # Summary
    elapsed = time.time() - start_time
    print("="*80)
    print("📊 RESULTS")
    print("="*80)
    print(f"Solved: {solved_count}/{len(task_ids)} ({solved_count/len(task_ids)*100:.2f}%)")
    print(f"Time: {elapsed:.1f}s ({elapsed/len(task_ids):.1f}s per task)")
    print()

    # Statistics
    stats = solver.get_statistics()
    print("📈 v0.94 Statistics:")
    print(f"  Meta-learning usage: {stats.get('meta_learning_usage', {})}")
    print(f"  Learning improvements: {stats.get('learning_improvements', 0)}")
    print()
    print(f"  Meta-learner stats:")
    meta_stats = stats.get('meta_learner_stats', {})
    print(f"    - Total attempts: {meta_stats.get('total_attempts', 0)}")
    print(f"    - Success rate: {meta_stats.get('success_rate', 0)*100:.1f}%")
    print(f"    - Unique patterns: {meta_stats.get('unique_constraint_patterns', 0)}")
    print(f"    - Primitives learned: {meta_stats.get('primitives_learned', 0)}")
    print()

    # Save results
    output_file = f'arc_v094_metalearning_{args.split}_{len(task_ids)}tasks.json'

    # Convert numpy types
    import numpy as np
    def convert_types(obj):
        if isinstance(obj, dict):
            return {k: convert_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_types(item) for item in obj]
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

    output_data = convert_types({
        'version': 'v0.94',
        'improvements': [
            'meta_learning_on_constraints',
            'adaptive_filtering',
            '80_20_exploitation_exploration',
            'historical_success_tracking'
        ],
        'config': {
            'split': args.split,
            'num_tasks': len(task_ids),
            'max_cycles': args.cycles,
            'database': args.database
        },
        'summary': {
            'solved': solved_count,
            'total': len(task_ids),
            'accuracy': solved_count / len(task_ids) if task_ids else 0,
            'time': elapsed
        },
        'statistics': stats,
        'results': results
    })

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"✅ Results saved to {output_file}")


if __name__ == "__main__":
    main()
