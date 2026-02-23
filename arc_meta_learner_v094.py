# -*- coding: utf-8 -*-
"""
ARC-AGI v0.94: Meta-Learning on Constraints

Learns which primitives work best for each constraint pattern.
Tracks constraint->primitive->success mappings and uses this knowledge
to adaptively refine filtering on new tasks.

Author: Prometheus v0.94
Date: 2025-10-18
"""

import json
import hashlib
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
import numpy as np


class ConstraintMetaLearner:
    """
    Learns from constraint extraction patterns across tasks to adaptively refine filtering.

    Tracks:
    - constraint_pattern -> primitive -> success_rate
    - constraint_pattern -> primitive_sequence -> fitness
    - task_similarity -> constraint_mapping

    The system learns from every attempt (success or failure) and improves over time.
    """

    def __init__(self):
        """Initialize the meta-learner with empty databases."""
        # {constraint_hash: {primitive: {'successes': int, 'total': int, 'best_fitness': float}}}
        self.success_db = {}

        # {constraint_hash: [(pattern, fitness, task_id), ...]}
        self.pattern_db = {}

        # {constraint_hash: {'size': str, 'color': str, 'symmetry': str, 'object': str}}
        self.constraint_cache = {}

        # Statistics
        self.total_attempts = 0
        self.total_successes = 0
        self.tasks_seen = set()

    def _hash_constraints(self, constraints: Dict[str, str]) -> str:
        """
        Create a canonical hash of constraint combination.

        Args:
            constraints: Dict with keys 'size', 'color', 'symmetry', 'object'

        Returns:
            Hash string representing this constraint pattern
        """
        # Sort keys for canonical ordering
        sorted_items = sorted(constraints.items())
        constraint_str = '|'.join([f"{k}:{v}" for k, v in sorted_items])
        return hashlib.md5(constraint_str.encode()).hexdigest()[:16]

    def _constraint_similarity(self, constraints1: Dict[str, str],
                              constraints2_hash: str) -> float:
        """
        Calculate similarity between two constraint patterns.

        Args:
            constraints1: First constraint dict
            constraints2_hash: Hash of second constraint pattern

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if constraints2_hash not in self.constraint_cache:
            return 0.0

        constraints2 = self.constraint_cache[constraints2_hash]

        # Count matching constraint values
        matches = 0
        total = 0

        for key in ['size', 'color', 'symmetry', 'object']:
            if key in constraints1 and key in constraints2:
                total += 1
                if constraints1[key] == constraints2[key]:
                    matches += 1

        if total == 0:
            return 0.0

        return matches / total

    def record_attempt(self, constraints: Dict[str, str], pattern: List[str],
                      fitness: float, task_id: str) -> None:
        """
        Record a pattern attempt with its fitness for given constraints.

        Args:
            constraints: Extracted constraints (size, color, symmetry, object)
            pattern: Sequence of primitives used
            fitness: Fitness score achieved (0.0 to 1.0)
            task_id: Task identifier
        """
        constraint_hash = self._hash_constraints(constraints)

        # Cache constraints for similarity calculations
        self.constraint_cache[constraint_hash] = constraints.copy()

        # Initialize success_db entry if needed
        if constraint_hash not in self.success_db:
            self.success_db[constraint_hash] = {}

        # Initialize pattern_db entry if needed
        if constraint_hash not in self.pattern_db:
            self.pattern_db[constraint_hash] = []

        # Record success for each primitive in pattern
        for prim in pattern:
            if prim not in self.success_db[constraint_hash]:
                self.success_db[constraint_hash][prim] = {
                    'successes': 0,
                    'total': 0,
                    'best_fitness': 0.0
                }

            self.success_db[constraint_hash][prim]['total'] += 1

            # Consider success if fitness >= 0.95
            if fitness >= 0.95:
                self.success_db[constraint_hash][prim]['successes'] += 1

            # Track best fitness achieved with this primitive
            if fitness > self.success_db[constraint_hash][prim]['best_fitness']:
                self.success_db[constraint_hash][prim]['best_fitness'] = fitness

        # Store pattern with fitness
        self.pattern_db[constraint_hash].append({
            'pattern': pattern,
            'fitness': fitness,
            'task_id': task_id
        })

        # Keep only top 20 patterns per constraint to limit memory
        if len(self.pattern_db[constraint_hash]) > 20:
            # Sort by fitness descending
            self.pattern_db[constraint_hash].sort(key=lambda x: x['fitness'], reverse=True)
            self.pattern_db[constraint_hash] = self.pattern_db[constraint_hash][:20]

        # Update statistics
        self.total_attempts += 1
        if fitness >= 0.95:
            self.total_successes += 1
        self.tasks_seen.add(task_id)

    def get_refined_filter(self, constraints: Dict[str, str],
                          mode: str = 'adaptive',
                          top_k: int = 15,
                          v093_fallback: Optional[List[str]] = None) -> Optional[List[str]]:
        """
        Get refined primitive filter based on historical success.

        Args:
            constraints: Current task constraints
            mode: 'strict' (high success rate only), 'adaptive' (80/20 exploit/explore), 'soft' (broader)
            top_k: Maximum number of primitives to return
            v093_fallback: v0.93 filtered primitives to use as fallback

        Returns:
            List of primitive names, or None if no historical data
        """
        constraint_hash = self._hash_constraints(constraints)

        # Check if we have exact match
        if constraint_hash in self.success_db:
            return self._get_filter_from_exact_match(constraint_hash, mode, top_k, v093_fallback)

        # Check for similar constraint patterns
        similar = self.get_similar_tasks(constraints, top_k=5)

        if len(similar) >= 2:  # Need at least 2 similar tasks for confidence
            return self._get_filter_from_similar_tasks(similar, mode, top_k, v093_fallback)

        # No historical data available
        return None

    def _get_filter_from_exact_match(self, constraint_hash: str, mode: str,
                                     top_k: int, v093_fallback: Optional[List[str]]) -> List[str]:
        """Get filter from exact constraint match."""
        success_rates = {}

        for prim, stats in self.success_db[constraint_hash].items():
            # Require at least 3 attempts for confidence
            if stats['total'] >= 3:
                success_rates[prim] = {
                    'rate': stats['successes'] / stats['total'],
                    'best_fitness': stats['best_fitness'],
                    'total': stats['total']
                }

        if not success_rates:
            return v093_fallback if v093_fallback else None

        if mode == 'strict':
            # Only primitives with >50% success rate
            prioritized = [p for p, data in success_rates.items() if data['rate'] >= 0.5]
        elif mode == 'adaptive':
            # 80% exploitation (proven performers), 20% exploration (mid-tier)
            exploit_count = int(top_k * 0.8)
            explore_count = top_k - exploit_count

            # Sort by success rate * best_fitness (weighted by confidence)
            sorted_prims = sorted(
                success_rates.items(),
                key=lambda x: x[1]['rate'] * x[1]['best_fitness'] * np.log(x[1]['total'] + 1),
                reverse=True
            )

            # Top performers (exploitation)
            prioritized = [p for p, _ in sorted_prims[:exploit_count]]

            # Mid-tier performers (exploration)
            mid_tier = [p for p, data in sorted_prims[exploit_count:] if data['rate'] >= 0.2]
            if mid_tier:
                np.random.shuffle(mid_tier)
                prioritized.extend(mid_tier[:explore_count])
        else:  # soft
            # All primitives with >20% success rate
            prioritized = [p for p, data in success_rates.items() if data['rate'] >= 0.2]

        # Include v0.93 filter as fallback
        if v093_fallback:
            for prim in v093_fallback:
                if prim not in prioritized:
                    prioritized.append(prim)

        return prioritized[:top_k]

    def _get_filter_from_similar_tasks(self, similar_tasks: List[Tuple], mode: str,
                                      top_k: int, v093_fallback: Optional[List[str]]) -> List[str]:
        """Get filter by aggregating similar tasks."""
        # Aggregate success rates from similar tasks (weighted by similarity)
        weighted_success = defaultdict(lambda: {'weighted_successes': 0.0, 'weighted_total': 0.0})

        for constraint_hash, similarity, _ in similar_tasks:
            if constraint_hash not in self.success_db:
                continue

            for prim, stats in self.success_db[constraint_hash].items():
                if stats['total'] >= 2:  # Lower threshold for similar tasks
                    weighted_success[prim]['weighted_successes'] += stats['successes'] * similarity
                    weighted_success[prim]['weighted_total'] += stats['total'] * similarity

        # Calculate weighted success rates
        success_rates = {}
        for prim, data in weighted_success.items():
            if data['weighted_total'] >= 3.0:  # Require meaningful weight
                success_rates[prim] = data['weighted_successes'] / data['weighted_total']

        if not success_rates:
            return v093_fallback if v093_fallback else None

        # Apply mode filtering
        if mode == 'strict':
            threshold = 0.4  # Lower threshold for similar tasks
        elif mode == 'adaptive':
            threshold = 0.2
        else:  # soft
            threshold = 0.1

        prioritized = [p for p, rate in success_rates.items() if rate >= threshold]

        # Sort by success rate
        prioritized.sort(key=lambda p: success_rates[p], reverse=True)

        # Include v0.93 fallback
        if v093_fallback:
            for prim in v093_fallback:
                if prim not in prioritized:
                    prioritized.append(prim)

        return prioritized[:top_k]

    def get_similar_tasks(self, constraints: Dict[str, str],
                         top_k: int = 5) -> List[Tuple[str, float, Dict]]:
        """
        Find k most similar previously-seen tasks.

        Args:
            constraints: Current task constraints
            top_k: Number of similar tasks to return

        Returns:
            List of (constraint_hash, similarity_score, constraint_dict) tuples
        """
        similarities = []

        for constraint_hash in self.success_db.keys():
            similarity = self._constraint_similarity(constraints, constraint_hash)
            if similarity > 0.0:
                similarities.append((
                    constraint_hash,
                    similarity,
                    self.constraint_cache[constraint_hash]
                ))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def get_statistics(self) -> Dict[str, Any]:
        """Get meta-learner statistics."""
        return {
            'total_attempts': self.total_attempts,
            'total_successes': self.total_successes,
            'success_rate': self.total_successes / self.total_attempts if self.total_attempts > 0 else 0.0,
            'unique_constraint_patterns': len(self.success_db),
            'tasks_seen': len(self.tasks_seen),
            'total_patterns_stored': sum(len(patterns) for patterns in self.pattern_db.values()),
            'primitives_learned': len(set(
                prim for prims in self.success_db.values() for prim in prims.keys()
            ))
        }

    def save_database(self, filepath: str) -> None:
        """
        Save learned patterns to JSON file.

        Args:
            filepath: Path to JSON file
        """
        data = {
            'success_db': self.success_db,
            'pattern_db': self.pattern_db,
            'constraint_cache': self.constraint_cache,
            'statistics': self.get_statistics()
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def load_database(self, filepath: str) -> bool:
        """
        Load learned patterns from JSON file.

        Args:
            filepath: Path to JSON file

        Returns:
            True if loaded successfully, False if file doesn't exist
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            self.success_db = data.get('success_db', {})
            self.pattern_db = data.get('pattern_db', {})
            self.constraint_cache = data.get('constraint_cache', {})

            # Rebuild statistics
            self.total_attempts = 0
            self.total_successes = 0
            self.tasks_seen = set()

            for constraint_hash, patterns in self.pattern_db.items():
                for entry in patterns:
                    self.total_attempts += 1
                    if entry['fitness'] >= 0.95:
                        self.total_successes += 1
                    self.tasks_seen.add(entry['task_id'])

            return True

        except FileNotFoundError:
            return False
        except json.JSONDecodeError:
            print(f"Warning: Could not parse {filepath}")
            return False

    def get_best_patterns_for_constraints(self, constraints: Dict[str, str],
                                         top_k: int = 5) -> List[Dict]:
        """
        Get best patterns previously seen for these constraints.

        Args:
            constraints: Task constraints
            top_k: Number of patterns to return

        Returns:
            List of pattern dictionaries sorted by fitness
        """
        constraint_hash = self._hash_constraints(constraints)

        if constraint_hash not in self.pattern_db:
            # Check similar tasks
            similar = self.get_similar_tasks(constraints, top_k=3)
            patterns = []
            for sim_hash, similarity, _ in similar:
                if sim_hash in self.pattern_db:
                    # Weight patterns by similarity
                    for entry in self.pattern_db[sim_hash]:
                        patterns.append({
                            **entry,
                            'weighted_fitness': entry['fitness'] * similarity
                        })
            patterns.sort(key=lambda x: x['weighted_fitness'], reverse=True)
            return patterns[:top_k]

        # Sort by fitness
        patterns = sorted(self.pattern_db[constraint_hash],
                         key=lambda x: x['fitness'],
                         reverse=True)
        return patterns[:top_k]


if __name__ == "__main__":
    # Test the meta-learner
    print("Testing ConstraintMetaLearner...")

    learner = ConstraintMetaLearner()

    # Test constraint 1: cropped + colors_reduced
    constraints1 = {
        'size': 'cropped',
        'color': 'colors_reduced',
        'symmetry': 'no_symmetry',
        'object': 'object_count_preserved'
    }

    # Record some attempts
    learner.record_attempt(constraints1, ['crop', 'downsample', 'fill_zeros'], 0.98, 'task_001')
    learner.record_attempt(constraints1, ['crop', 'extract_largest', 'fill_zeros'], 0.95, 'task_002')
    learner.record_attempt(constraints1, ['scale_2x', 'rotate_90'], 0.15, 'task_003')

    # Test constraint 2: scaled_up + horizontal_symmetry
    constraints2 = {
        'size': 'scaled_up',
        'color': 'colors_preserved',
        'symmetry': 'horizontal',
        'object': 'object_count_increased'
    }

    learner.record_attempt(constraints2, ['scale_2x', 'symmetrize_h'], 0.92, 'task_004')
    learner.record_attempt(constraints2, ['scale_3x', 'flip_h'], 0.88, 'task_005')

    # Get statistics
    stats = learner.get_statistics()
    print(f"\nStatistics: {json.dumps(stats, indent=2)}")

    # Test refined filter for constraints1
    refined = learner.get_refined_filter(constraints1, mode='adaptive', top_k=10)
    print(f"\nRefined filter for cropped+colors_reduced: {refined}")

    # Test similar tasks
    similar = learner.get_similar_tasks(constraints1, top_k=3)
    print(f"\nSimilar tasks to cropped+colors_reduced:")
    for hash_val, similarity, constraints in similar:
        print(f"  Similarity {similarity:.2f}: {constraints}")

    # Test save/load
    learner.save_database('/tmp/test_meta_learner.json')
    print(f"\nSaved database to /tmp/test_meta_learner.json")

    learner2 = ConstraintMetaLearner()
    success = learner2.load_database('/tmp/test_meta_learner.json')
    print(f"Loaded database: {success}")
    print(f"Loaded statistics: {json.dumps(learner2.get_statistics(), indent=2)}")

    print("\nConstraintMetaLearner tests passed!")
