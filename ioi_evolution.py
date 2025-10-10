#!/usr/bin/env python3
"""
IOI Evolutionary Search (v0.75)

Genetic algorithm to search over algorithm sequences for solving IOI problems.
Combines with LLM code synthesis and automated testing.
"""

import random
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from copy import deepcopy
import time

@dataclass
class AlgorithmSequence:
    """Sequence of algorithm primitives"""
    algorithms: List[str]
    fitness: float = 0.0
    generation: int = 0
    test_results: Dict = field(default_factory=dict)

class IOIEvolution:
    """Evolve algorithm sequences to solve IOI problems"""

    def __init__(self,
                 primitive_names: List[str],
                 population_size: int = 30,
                 max_sequence_length: int = 3,
                 mutation_rate: float = 0.3):
        """
        Args:
            primitive_names: List of all available primitive names
            population_size: Number of individuals in population
            max_sequence_length: Maximum algorithms in a sequence
            mutation_rate: Probability of mutation
        """
        self.primitive_names = primitive_names
        self.population_size = population_size
        self.max_sequence_length = max_sequence_length
        self.mutation_rate = mutation_rate

        self.population: List[AlgorithmSequence] = []
        self.generation = 0
        self.best_fitness_history = []
        self.best_individual = None

    def initialize_population(self, suggested_algorithms: List[str] = None):
        """
        Create initial population.

        Args:
            suggested_algorithms: Algorithms suggested by classifier (prioritized)
        """
        self.population = []

        # Add suggested algorithms first (single operations)
        if suggested_algorithms:
            for alg in suggested_algorithms[:self.population_size // 3]:
                seq = AlgorithmSequence(
                    algorithms=[alg],
                    generation=0
                )
                self.population.append(seq)

        # Add random combinations
        while len(self.population) < self.population_size:
            # Random length (biased toward shorter sequences)
            length = random.choices(
                range(1, self.max_sequence_length + 1),
                weights=[3, 2, 1][:self.max_sequence_length]  # Favor shorter
            )[0]

            # Choose algorithms (with bias toward suggested if available)
            if suggested_algorithms and random.random() < 0.7:
                # 70% chance to use suggested algorithms
                algs = random.choices(suggested_algorithms, k=length)
            else:
                # 30% chance to use any primitive
                algs = random.choices(self.primitive_names, k=length)

            seq = AlgorithmSequence(
                algorithms=algs,
                generation=0
            )
            self.population.append(seq)

    def evaluate_fitness(self,
                        sequence: AlgorithmSequence,
                        test_results: Dict) -> float:
        """
        Calculate fitness from test results.

        Args:
            sequence: Algorithm sequence
            test_results: Results from IOITester

        Returns:
            Fitness score (0-1, higher is better)
        """
        # Base fitness: success rate on tests
        success_rate = test_results.get('success_rate', 0.0)

        # Complexity penalty (favor simpler solutions)
        complexity = len(sequence.algorithms)
        complexity_penalty = 0.05 * complexity  # 5% penalty per algorithm

        # Time penalty (favor faster solutions)
        avg_time = test_results.get('time_avg', 0.0)
        time_penalty = min(0.1, avg_time / 2.0)  # Max 10% penalty

        fitness = success_rate - complexity_penalty - time_penalty
        fitness = max(0.0, min(1.0, fitness))

        # Store results
        sequence.test_results = test_results
        sequence.fitness = fitness

        return fitness

    def mutate(self, sequence: AlgorithmSequence) -> AlgorithmSequence:
        """
        Mutate a sequence.

        Mutations:
        - Add algorithm
        - Remove algorithm
        - Replace algorithm
        - Swap two algorithms
        """
        new_algs = sequence.algorithms.copy()

        mutation_type = random.choice(['add', 'remove', 'replace', 'swap'])

        if mutation_type == 'add' and len(new_algs) < self.max_sequence_length:
            # Add random algorithm
            pos = random.randint(0, len(new_algs))
            new_algs.insert(pos, random.choice(self.primitive_names))

        elif mutation_type == 'remove' and len(new_algs) > 1:
            # Remove random algorithm
            pos = random.randint(0, len(new_algs) - 1)
            new_algs.pop(pos)

        elif mutation_type == 'replace' and len(new_algs) > 0:
            # Replace random algorithm
            pos = random.randint(0, len(new_algs) - 1)
            new_algs[pos] = random.choice(self.primitive_names)

        elif mutation_type == 'swap' and len(new_algs) > 1:
            # Swap two algorithms
            i, j = random.sample(range(len(new_algs)), 2)
            new_algs[i], new_algs[j] = new_algs[j], new_algs[i]

        return AlgorithmSequence(
            algorithms=new_algs,
            generation=self.generation
        )

    def crossover(self,
                  parent1: AlgorithmSequence,
                  parent2: AlgorithmSequence) -> AlgorithmSequence:
        """
        Create offspring from two parents via crossover.
        """
        if len(parent1.algorithms) == 0:
            return AlgorithmSequence(
                algorithms=parent2.algorithms.copy(),
                generation=self.generation
            )

        if len(parent2.algorithms) == 0:
            return AlgorithmSequence(
                algorithms=parent1.algorithms.copy(),
                generation=self.generation
            )

        # Take prefix from parent1, suffix from parent2
        split1 = random.randint(0, len(parent1.algorithms))
        split2 = random.randint(0, len(parent2.algorithms))

        new_algs = parent1.algorithms[:split1] + parent2.algorithms[split2:]

        # Trim if too long
        if len(new_algs) > self.max_sequence_length:
            new_algs = new_algs[:self.max_sequence_length]

        # Ensure at least one algorithm
        if len(new_algs) == 0:
            new_algs = [random.choice([parent1.algorithms[0], parent2.algorithms[0]])]

        return AlgorithmSequence(
            algorithms=new_algs,
            generation=self.generation
        )

    def select_parents(self, k: int = 2) -> List[AlgorithmSequence]:
        """
        Select k parents via tournament selection.
        """
        parents = []
        fitnesses = [ind.fitness for ind in self.population]

        for _ in range(k):
            # Tournament of size 3
            tournament_indices = random.sample(
                range(len(self.population)),
                min(3, len(self.population))
            )
            winner_idx = max(tournament_indices, key=lambda i: fitnesses[i])
            parents.append(self.population[winner_idx])

        return parents

    def evolve_generation(self):
        """Evolve one generation (assumes fitness already evaluated)"""

        # Track best fitness
        best_fitness = max(ind.fitness for ind in self.population)
        self.best_fitness_history.append(best_fitness)

        # Find best individual
        best_idx = max(range(len(self.population)),
                      key=lambda i: self.population[i].fitness)
        self.best_individual = deepcopy(self.population[best_idx])

        # Create next generation
        next_generation = []

        # Elitism: keep top 20%
        elite_count = max(1, self.population_size // 5)
        elite_indices = sorted(
            range(len(self.population)),
            key=lambda i: self.population[i].fitness,
            reverse=True
        )[:elite_count]

        for idx in elite_indices:
            next_generation.append(deepcopy(self.population[idx]))

        # Fill rest with offspring
        while len(next_generation) < self.population_size:
            if random.random() < 0.7:
                # 70% crossover
                parent1, parent2 = self.select_parents(k=2)
                child = self.crossover(parent1, parent2)
            else:
                # 30% mutation only
                parent = self.select_parents(k=1)[0]
                child = self.mutate(parent)

            # Additional mutation with probability
            if random.random() < self.mutation_rate:
                child = self.mutate(child)

            next_generation.append(child)

        self.population = next_generation
        self.generation += 1

    def get_best_sequences(self, n: int = 5) -> List[AlgorithmSequence]:
        """Get top n sequences sorted by fitness"""
        sorted_pop = sorted(
            self.population,
            key=lambda x: x.fitness,
            reverse=True
        )
        return sorted_pop[:n]

    def get_unique_sequences(self) -> List[AlgorithmSequence]:
        """Get unique algorithm sequences (remove duplicates)"""
        seen = set()
        unique = []

        for ind in self.population:
            key = tuple(ind.algorithms)
            if key not in seen:
                seen.add(key)
                unique.append(ind)

        return unique


# ============================================================================
# EXAMPLE USAGE & TESTS
# ============================================================================

if __name__ == "__main__":
    print("Testing IOI Evolution...")

    # All 50 primitive names (from ioi_primitives.py)
    primitive_names = [
        # Data structures
        'use_array', 'use_2d_array', 'use_dict', 'use_set', 'use_heap',
        'use_queue', 'use_stack', 'use_frequency_map', 'use_prefix_sum',
        # Search/Sort
        'linear_search', 'binary_search', 'sort_ascending', 'sort_descending',
        # Array ops
        'find_max', 'find_min', 'count_if', 'filter_by', 'cumulative_sum',
        # Strings
        'string_reverse', 'string_is_palindrome',
        # Graph
        'graph_bfs', 'graph_dfs', 'graph_shortest_path_unweighted',
        # DP
        'dp_fibonacci', 'dp_max_subarray_sum', 'dp_coin_change',
        # Greedy
        'greedy_activity_selection',
        # Math
        'math_gcd', 'math_is_prime'
    ]

    # Initialize evolution
    evolver = IOIEvolution(
        primitive_names=primitive_names,
        population_size=20,
        max_sequence_length=3
    )

    # Suggested algorithms from classifier
    suggested = ['use_array', 'count_if', 'find_max']

    print(f"\nInitializing population with suggestions: {suggested}")
    evolver.initialize_population(suggested)

    print(f"Population size: {len(evolver.population)}")
    print(f"\nSample individuals:")
    for i, ind in enumerate(evolver.population[:5]):
        print(f"  {i+1}. {ind.algorithms}")

    # Simulate fitness evaluation
    print(f"\n{'='*70}")
    print("SIMULATING EVOLUTION")
    print(f"{'='*70}")

    for gen in range(5):
        # Simulate fitness (in real use, would call tester)
        for ind in evolver.population:
            # Fake fitness based on sequence quality
            # Favor sequences with 'count_if'
            if 'count_if' in ind.algorithms:
                base_fitness = 0.8
            else:
                base_fitness = 0.3

            # Add randomness
            fitness = base_fitness + random.random() * 0.2

            # Apply complexity penalty
            fitness -= 0.05 * len(ind.algorithms)
            ind.fitness = max(0.0, min(1.0, fitness))

        # Evolve
        evolver.evolve_generation()

        # Report
        best = evolver.best_individual
        avg_fitness = np.mean([ind.fitness for ind in evolver.population])

        print(f"\nGen {gen+1}:")
        print(f"  Best: {best.algorithms} (fitness: {best.fitness:.3f})")
        print(f"  Avg fitness: {avg_fitness:.3f}")

    # Show final top sequences
    print(f"\n{'='*70}")
    print("TOP 5 SEQUENCES")
    print(f"{'='*70}")

    top_seqs = evolver.get_best_sequences(n=5)
    for i, seq in enumerate(top_seqs, 1):
        print(f"{i}. {seq.algorithms}")
        print(f"   Fitness: {seq.fitness:.3f}")
        print()

    # Test unique sequences
    unique = evolver.get_unique_sequences()
    print(f"Unique sequences: {len(unique)}/{len(evolver.population)}")

    print("\n✅ Evolution working!")
