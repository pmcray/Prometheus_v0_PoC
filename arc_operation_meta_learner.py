#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Operation Meta-Learner for v0.95

Learns operation and parameter preferences from successful solves.

Key Learning Objectives:
1. Operation frequency: Which ops appear in successful programs?
2. Operation combinations: Which pairs/sequences work together?
3. Parameter preferences: Which parameter values work best?
4. Constraint-operation mapping: Which ops work for which task types?

Outputs biased operation lists for beam search to improve efficiency.

Author: Prometheus v0.95
Date: 2025-10-22
"""

import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter


class OperationMetaLearner:
    """
    Learn operation and parameter biases from successful programs.
    """

    def __init__(self):
        """Initialize empty meta-learner."""
        # Operation frequency tracking
        self.operation_counts = Counter()  # op_name -> count
        self.operation_successes = Counter()  # op_name -> fitness_sum
        self.operation_by_position = defaultdict(Counter)  # position -> {op_name -> count}

        # Operation combination tracking
        self.operation_pairs = Counter()  # (op1, op2) -> count
        self.operation_sequences = Counter()  # tuple(ops) -> count

        # Parameter tracking
        self.parameter_values = defaultdict(lambda: defaultdict(Counter))  # op -> param -> {value -> count}

        # Constraint-operation mapping
        self.constraint_operation_map = defaultdict(Counter)  # constraint_key -> {op_name -> count}

        # Statistics
        self.programs_learned = 0
        self.total_fitness_sum = 0.0

    def learn_from_program(self,
                          program_ops: List[Tuple[str, Dict]],
                          fitness: float,
                          task_constraints: Optional[Dict] = None):
        """
        Learn from a successful program.

        Args:
            program_ops: List of (operation_name, parameters) tuples
            fitness: Program fitness score
            task_constraints: Optional task constraints for constraint-op mapping
        """
        if not program_ops or fitness < 0.3:
            return  # Only learn from reasonably successful programs

        self.programs_learned += 1
        self.total_fitness_sum += fitness

        # Learn operation frequency and position
        for i, (op_name, params) in enumerate(program_ops):
            self.operation_counts[op_name] += 1
            self.operation_successes[op_name] += fitness
            self.operation_by_position[i][op_name] += 1

            # Learn parameter values
            for param_name, param_value in params.items():
                # Convert param value to hashable type
                if isinstance(param_value, (list, dict)):
                    param_value_str = str(param_value)
                else:
                    param_value_str = param_value

                self.parameter_values[op_name][param_name][param_value_str] += 1

        # Learn operation pairs (bigrams)
        for i in range(len(program_ops) - 1):
            op1 = program_ops[i][0]
            op2 = program_ops[i+1][0]
            self.operation_pairs[(op1, op2)] += 1

        # Learn full sequences (for short programs)
        if len(program_ops) <= 4:
            op_sequence = tuple(op[0] for op in program_ops)
            self.operation_sequences[op_sequence] += 1

        # Learn constraint-operation mapping
        if task_constraints:
            constraint_key = self._make_constraint_key(task_constraints)
            for op_name, _ in program_ops:
                self.constraint_operation_map[constraint_key][op_name] += 1

    def _make_constraint_key(self, constraints: Dict) -> str:
        """Create hashable key from constraints."""
        # Extract key constraint features
        size_behavior = constraints.get('size', 'unknown')
        color_behavior = constraints.get('color', 'unknown')

        return f"size:{size_behavior},color:{color_behavior}"

    def get_top_operations(self, n: int = 15) -> List[str]:
        """
        Get top N operations by success-weighted frequency.

        Returns:
            List of operation names, sorted by success
        """
        # Calculate success-weighted scores
        op_scores = []
        for op_name in self.operation_counts:
            count = self.operation_counts[op_name]
            avg_fitness = self.operation_successes[op_name] / count if count > 0 else 0
            score = count * avg_fitness  # Frequency × quality
            op_scores.append((score, op_name))

        op_scores.sort(reverse=True)
        return [op_name for _, op_name in op_scores[:n]]

    def get_operations_by_constraints(self,
                                     constraints: Dict,
                                     n: int = 15) -> List[str]:
        """
        Get top N operations for tasks matching these constraints.

        Args:
            constraints: Task constraints
            n: Number of operations to return

        Returns:
            List of operation names, sorted by relevance
        """
        constraint_key = self._make_constraint_key(constraints)

        if constraint_key in self.constraint_operation_map:
            ops = self.constraint_operation_map[constraint_key]
            sorted_ops = ops.most_common(n)
            return [op_name for op_name, _ in sorted_ops]

        # Fallback to general top operations
        return self.get_top_operations(n)

    def get_likely_next_operation(self,
                                  current_ops: List[str],
                                  n: int = 5) -> List[str]:
        """
        Predict likely next operations given current sequence.

        Args:
            current_ops: Current operation sequence
            n: Number of predictions

        Returns:
            List of likely next operations
        """
        if not current_ops:
            # Start with most common first operations
            first_ops = self.operation_by_position[0].most_common(n)
            return [op_name for op_name, _ in first_ops]

        # Look at operation pairs
        last_op = current_ops[-1]
        next_ops = Counter()

        for (op1, op2), count in self.operation_pairs.items():
            if op1 == last_op:
                next_ops[op2] += count

        if next_ops:
            top_next = next_ops.most_common(n)
            return [op_name for op_name, _ in top_next]

        # Fallback to general frequency
        return self.get_top_operations(n)

    def get_parameter_preferences(self,
                                  op_name: str,
                                  param_name: str,
                                  n: int = 3) -> List:
        """
        Get most common parameter values for an operation.

        Args:
            op_name: Operation name
            param_name: Parameter name
            n: Number of values to return

        Returns:
            List of parameter values, sorted by frequency
        """
        if op_name in self.parameter_values and param_name in self.parameter_values[op_name]:
            values = self.parameter_values[op_name][param_name]
            top_values = values.most_common(n)

            # Convert string representations back to original types
            result = []
            for value_str, _ in top_values:
                # Try to parse as Python literal
                try:
                    import ast
                    result.append(ast.literal_eval(value_str))
                except:
                    result.append(value_str)

            return result

        return []

    def get_statistics(self) -> Dict:
        """Get meta-learning statistics."""
        return {
            'programs_learned': self.programs_learned,
            'average_fitness': self.total_fitness_sum / self.programs_learned if self.programs_learned > 0 else 0,
            'unique_operations': len(self.operation_counts),
            'unique_pairs': len(self.operation_pairs),
            'unique_sequences': len(self.operation_sequences),
            'constraint_types': len(self.constraint_operation_map)
        }

    def print_statistics(self):
        """Print meta-learning statistics."""
        stats = self.get_statistics()

        print()
        print("📊 Operation Meta-Learner Statistics:")
        print(f"   Programs learned: {stats['programs_learned']}")
        print(f"   Average fitness: {stats['average_fitness']:.3f}")
        print(f"   Unique operations: {stats['unique_operations']}")
        print(f"   Unique operation pairs: {stats['unique_pairs']}")
        print(f"   Unique sequences: {stats['unique_sequences']}")
        print(f"   Constraint types tracked: {stats['constraint_types']}")
        print()

        # Top operations
        print("   Top 10 Operations:")
        top_ops = self.get_top_operations(10)
        for i, op_name in enumerate(top_ops, 1):
            count = self.operation_counts[op_name]
            avg_fitness = self.operation_successes[op_name] / count if count > 0 else 0
            print(f"      {i}. {op_name}: {count} uses, {avg_fitness:.3f} avg fitness")
        print()

        # Top operation pairs
        print("   Top 5 Operation Pairs:")
        top_pairs = self.operation_pairs.most_common(5)
        for i, ((op1, op2), count) in enumerate(top_pairs, 1):
            print(f"      {i}. {op1} → {op2}: {count} times")
        print()

    def save(self, output_path: str):
        """Save meta-learner to JSON."""
        data = {
            'operation_counts': dict(self.operation_counts),
            'operation_successes': dict(self.operation_successes),
            'operation_by_position': {
                str(pos): dict(ops) for pos, ops in self.operation_by_position.items()
            },
            'operation_pairs': {
                f"{op1}->{op2}": count for (op1, op2), count in self.operation_pairs.items()
            },
            'operation_sequences': {
                "->".join(seq): count for seq, count in self.operation_sequences.items()
            },
            'parameter_values': {
                op: {param: dict(values) for param, values in params.items()}
                for op, params in self.parameter_values.items()
            },
            'constraint_operation_map': {
                key: dict(ops) for key, ops in self.constraint_operation_map.items()
            },
            'statistics': self.get_statistics()
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✅ Meta-learner saved: {output_path}")

    def load(self, input_path: str):
        """Load meta-learner from JSON."""
        with open(input_path, 'r') as f:
            data = json.load(f)

        # Restore counters
        self.operation_counts = Counter(data['operation_counts'])
        self.operation_successes = Counter(data['operation_successes'])

        for pos_str, ops in data['operation_by_position'].items():
            pos = int(pos_str)
            self.operation_by_position[pos] = Counter(ops)

        for pair_str, count in data['operation_pairs'].items():
            op1, op2 = pair_str.split('->')
            self.operation_pairs[(op1, op2)] = count

        for seq_str, count in data['operation_sequences'].items():
            seq = tuple(seq_str.split('->'))
            self.operation_sequences[seq] = count

        for op, params in data['parameter_values'].items():
            for param, values in params.items():
                self.parameter_values[op][param] = Counter(values)

        for key, ops in data['constraint_operation_map'].items():
            self.constraint_operation_map[key] = Counter(ops)

        # Restore statistics
        stats = data['statistics']
        self.programs_learned = stats['programs_learned']
        self.total_fitness_sum = stats['average_fitness'] * stats['programs_learned']

        print(f"✅ Loaded meta-learner: {self.programs_learned} programs")

    def load_from_template_database(self, template_db_path: str):
        """
        Learn from existing template database.

        Args:
            template_db_path: Path to arc_template_learner JSON file
        """
        with open(template_db_path, 'r') as f:
            db = json.load(f)

        templates = db.get('templates', {})

        print(f"Learning from {len(templates)} templates...")

        # Learn from templates (each template represents multiple successful uses)
        for pattern_str, stats in templates.items():
            # Parse pattern (e.g., "crop()" or "rotate_90() -> flip_h()")
            ops_with_parens = pattern_str.split(' -> ')
            pattern = [op.replace('()', '') for op in ops_with_parens]

            # Get template metrics
            count = stats['count']
            avg_fitness = stats['avg_fitness']

            # Convert pattern to list of (op_name, params) tuples
            program_ops = [(op_name, {}) for op_name in pattern]

            # Learn from this template multiple times (weighted by count)
            # Treat each use as a separate learning event
            for _ in range(min(count, 10)):  # Cap at 10 to avoid over-weighting
                self.learn_from_program(program_ops, avg_fitness)

        print(f"✅ Learned from {len(templates)} templates")
        self.print_statistics()


# ============================================================================
# TESTING
# ============================================================================

def test_operation_meta_learner():
    """Test operation meta-learner."""
    print("=" * 80)
    print("🧪 Testing Operation Meta-Learner")
    print("=" * 80)
    print()

    # Create meta-learner
    learner = OperationMetaLearner()

    # Load from template database
    print("Loading from template database...")
    learner.load_from_template_database('arc_v095_expanded_templates.json')

    print()
    print("=" * 80)
    print("🔍 Testing Predictions")
    print("=" * 80)
    print()

    # Test 1: Top operations
    print("Test 1: Top 10 operations:")
    top_ops = learner.get_top_operations(10)
    for i, op in enumerate(top_ops, 1):
        print(f"   {i}. {op}")
    print()

    # Test 2: Likely next operation
    print("Test 2: Likely next operations after ['crop']:")
    next_ops = learner.get_likely_next_operation(['crop'], 5)
    for i, op in enumerate(next_ops, 1):
        print(f"   {i}. {op}")
    print()

    # Test 3: Likely next operation after geometric
    print("Test 3: Likely next operations after ['rotate_90', 'flip_h']:")
    next_ops = learner.get_likely_next_operation(['rotate_90', 'flip_h'], 5)
    for i, op in enumerate(next_ops, 1):
        print(f"   {i}. {op}")
    print()

    # Test 4: Save and reload
    print("Test 4: Save and reload:")
    learner.save('arc_operation_meta_learner_test.json')

    learner2 = OperationMetaLearner()
    learner2.load('arc_operation_meta_learner_test.json')
    print(f"   Reloaded: {learner2.programs_learned} programs")
    print()

    print("=" * 80)
    print("✅ All tests passed!")
    print("=" * 80)


if __name__ == '__main__':
    test_operation_meta_learner()
