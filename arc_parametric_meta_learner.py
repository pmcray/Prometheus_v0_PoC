#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARC-AGI v0.95: Parametric Meta-Learning

Extends v0.94 meta-learning to track (operation, parameters) -> success mappings.
Learns parameter distributions for each operation in different constraint contexts.

Key Features:
- Track operation+parameter combinations
- Learn parameter value distributions
- Suggest best parameters for operations given constraints
- Support for template-based transfer learning

Author: Prometheus v0.95
Date: 2025-10-22
"""

import json
import hashlib
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
import numpy as np
from arc_program import ARCProgram
from arc_meta_learner_v094 import ConstraintMetaLearner


class ParametricMetaLearner(ConstraintMetaLearner):
    """
    Enhanced meta-learner that tracks parametric operations.

    Extends v0.94 ConstraintMetaLearner to support:
    - (operation, parameters) -> success tracking
    - Parameter distribution learning
    - Best parameter suggestions for operations
    """

    def __init__(self):
        """Initialize parametric meta-learner."""
        super().__init__()

        # {constraint_hash: {(op_name, param_tuple): {'successes': int, 'total': int, 'best_fitness': float}}}
        self.param_success_db = {}

        # {constraint_hash: {op_name: {param_name: {value: count}}}}
        # Tracks parameter value distributions
        self.param_distributions = {}

    def record_program_attempt(self,
                               constraints: Dict[str, str],
                               program: ARCProgram,
                               fitness: float,
                               task_id: str) -> None:
        """
        Record a program attempt with parametric operations.

        Args:
            constraints: Extracted constraints
            program: ARCProgram instance
            fitness: Fitness score (0.0 to 1.0)
            task_id: Task identifier
        """
        constraint_hash = self._hash_constraints(constraints)

        # Initialize databases if needed
        if constraint_hash not in self.param_success_db:
            self.param_success_db[constraint_hash] = {}
        if constraint_hash not in self.param_distributions:
            self.param_distributions[constraint_hash] = {}

        # Record each (operation, parameters) pair
        for op_name, params in program.operations:
            # Create hashable parameter tuple
            param_tuple = tuple(sorted(params.items())) if params else ()
            key = (op_name, param_tuple)

            # Initialize if needed
            if key not in self.param_success_db[constraint_hash]:
                self.param_success_db[constraint_hash][key] = {
                    'successes': 0,
                    'total': 0,
                    'best_fitness': 0.0
                }

            # Update statistics
            self.param_success_db[constraint_hash][key]['total'] += 1
            if fitness >= 0.95:
                self.param_success_db[constraint_hash][key]['successes'] += 1
            if fitness > self.param_success_db[constraint_hash][key]['best_fitness']:
                self.param_success_db[constraint_hash][key]['best_fitness'] = fitness

            # Update parameter distributions
            if op_name not in self.param_distributions[constraint_hash]:
                self.param_distributions[constraint_hash][op_name] = {}

            for param_name, param_value in params.items():
                if param_name not in self.param_distributions[constraint_hash][op_name]:
                    self.param_distributions[constraint_hash][op_name][param_name] = defaultdict(int)

                # Convert value to hashable type
                hashable_value = param_value if isinstance(param_value, (int, str, float, bool)) else str(param_value)
                self.param_distributions[constraint_hash][op_name][param_name][hashable_value] += 1

        # Also call parent to track primitive-level stats (for backward compatibility)
        # Convert program to pattern format
        pattern = program.to_pattern()
        super().record_attempt(constraints, pattern, fitness, task_id)

        # Update global stats
        self.total_attempts += 1
        if fitness >= 0.95:
            self.total_successes += 1
        self.tasks_seen.add(task_id)

    def get_best_params(self,
                       op_name: str,
                       constraints: Dict[str, str],
                       top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Get best-performing parameter sets for an operation given constraints.

        Args:
            op_name: Operation name
            constraints: Current constraint pattern
            top_k: Number of parameter sets to return

        Returns:
            List of parameter dicts, sorted by success rate
        """
        constraint_hash = self._hash_constraints(constraints)

        if constraint_hash not in self.param_success_db:
            return []

        # Find all parameter sets for this operation
        relevant = []
        for (op, params), stats in self.param_success_db[constraint_hash].items():
            if op == op_name:
                success_rate = stats['successes'] / max(stats['total'], 1)
                relevant.append((dict(params), success_rate, stats))

        # Sort by success rate (with best_fitness as tiebreaker)
        relevant.sort(key=lambda x: (x[1], x[2]['best_fitness']), reverse=True)

        # Return top-k parameter dicts
        return [params for params, _, _ in relevant[:top_k]]

    def get_param_distribution(self,
                              op_name: str,
                              param_name: str,
                              constraints: Dict[str, str]) -> Dict[Any, float]:
        """
        Get probability distribution for a parameter value.

        Args:
            op_name: Operation name
            param_name: Parameter name
            constraints: Current constraint pattern

        Returns:
            Dict mapping parameter values to probabilities
        """
        constraint_hash = self._hash_constraints(constraints)

        if (constraint_hash not in self.param_distributions or
            op_name not in self.param_distributions[constraint_hash] or
            param_name not in self.param_distributions[constraint_hash][op_name]):
            return {}

        # Get counts
        counts = self.param_distributions[constraint_hash][op_name][param_name]
        total = sum(counts.values())

        if total == 0:
            return {}

        # Convert to probabilities
        return {value: count / total for value, count in counts.items()}

    def suggest_parameters(self,
                          op_name: str,
                          constraints: Dict[str, str],
                          top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Suggest parameter values for an operation based on learned distributions.

        Uses both direct parameter success tracking and value distributions.

        Args:
            op_name: Operation name
            constraints: Current constraint pattern
            top_k: Number of suggestions

        Returns:
            List of parameter dicts
        """
        # First try: Get directly successful parameter sets
        best_params = self.get_best_params(op_name, constraints, top_k)

        if best_params:
            return best_params

        # Second try: Use similar constraints
        similar_params = []
        constraint_hash = self._hash_constraints(constraints)

        # Find similar constraint patterns
        for other_hash in self.param_success_db.keys():
            similarity = self._constraint_similarity(constraints, other_hash)
            if similarity > 0.5:  # At least 50% similarity
                # Get successful params from similar constraint
                for (op, params), stats in self.param_success_db[other_hash].items():
                    if op == op_name and stats['successes'] > 0:
                        similar_params.append((dict(params), stats['best_fitness']))

        # Sort by fitness
        similar_params.sort(key=lambda x: x[1], reverse=True)
        return [params for params, _ in similar_params[:top_k]]

    def save_database(self, filepath: str) -> None:
        """
        Save parametric meta-learning database to JSON.

        Args:
            filepath: Path to save database
        """
        data = {
            'success_db': self.success_db,
            'pattern_db': self.pattern_db,
            'constraint_cache': self.constraint_cache,
            'param_success_db': {
                hash_val: {
                    f"{op}@{param_tuple}": stats
                    for (op, param_tuple), stats in params.items()
                }
                for hash_val, params in self.param_success_db.items()
            },
            'param_distributions': {
                hash_val: {
                    op: {
                        param: dict(values)
                        for param, values in params.items()
                    }
                    for op, params in ops.items()
                }
                for hash_val, ops in self.param_distributions.items()
            },
            'stats': {
                'total_attempts': self.total_attempts,
                'total_successes': self.total_successes,
                'tasks_seen': list(self.tasks_seen)
            }
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def load_database(self, filepath: str) -> bool:
        """
        Load parametric meta-learning database from JSON.

        Args:
            filepath: Path to load database from

        Returns:
            True if successful, False if file not found
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            self.success_db = data.get('success_db', {})
            self.pattern_db = data.get('pattern_db', {})
            self.constraint_cache = data.get('constraint_cache', {})

            # Reconstruct param_success_db
            self.param_success_db = {}
            for hash_val, params in data.get('param_success_db', {}).items():
                self.param_success_db[hash_val] = {}
                for key_str, stats in params.items():
                    # Parse "op@param_tuple" format
                    op, param_tuple_str = key_str.split('@', 1)
                    param_tuple = eval(param_tuple_str)  # Safe because we control the format
                    self.param_success_db[hash_val][(op, param_tuple)] = stats

            # Reconstruct param_distributions
            self.param_distributions = {}
            for hash_val, ops in data.get('param_distributions', {}).items():
                self.param_distributions[hash_val] = {}
                for op, params in ops.items():
                    self.param_distributions[hash_val][op] = {}
                    for param_name, values in params.items():
                        self.param_distributions[hash_val][op][param_name] = defaultdict(int, values)

            # Restore stats
            stats = data.get('stats', {})
            self.total_attempts = stats.get('total_attempts', 0)
            self.total_successes = stats.get('total_successes', 0)
            self.tasks_seen = set(stats.get('tasks_seen', []))

            return True

        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"Warning: Error loading database: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about learned data."""
        stats = super().get_statistics()

        # Add parametric stats
        total_param_combos = sum(len(params) for params in self.param_success_db.values())
        stats['parametric_combinations_learned'] = total_param_combos
        stats['operations_with_params'] = len(set(
            op for params in self.param_success_db.values()
            for op, _ in params.keys()
        ))

        return stats
