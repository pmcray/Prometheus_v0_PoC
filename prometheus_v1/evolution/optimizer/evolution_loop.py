import os
import uuid
from typing import List, Tuple, Dict, Any
from prometheus_v1.evolution.gene_bank.storage import GeneBank
from prometheus_v1.evolution.optimizer.mutator import MutationOperator
from prometheus_v1.evolution.optimizer.selector import Selector
from prometheus_v1.core.data_models import MutationMethod, MutationRecord
from prometheus.iee_v1 import IEEV1

class EvolutionaryOptimizer:
    """
    Main loop for Recursive Self-Improvement (RSI).
    Orchestrates the generation, evaluation, and selection of agent variants.
    """
    def __init__(self, problem_id: str = "PB-001"):
        self.gene_bank = GeneBank()
        self.mutator = MutationOperator(self.gene_bank)
        self.selector = Selector()
        self.evaluator = IEEV1()
        self.problem_id = problem_id
        self.population: List[Tuple[uuid.UUID, float]] = []

    def initialize_population(self, initial_code: str):
        """Seed the population with an initial code variant."""
        record = MutationRecord(
            mutation_method=MutationMethod.REFACTOR,
            phenotype_desc="Initial seed variant"
        )
        variant_id = self.gene_bank.store_variant(initial_code, record)
        # Evaluate initial fitness
        fitness = self.evaluate_variant(initial_code)
        self.population.append((uuid.UUID(variant_id), fitness))
        print(f"EvolutionaryOptimizer: Population initialized with variant {variant_id} (Fitness: {fitness:.2f})")

    def evaluate_variant(self, code: str) -> float:
        """Evaluate a variant using the IEE benchmark suite."""
        result = self.evaluator.evaluate_agent_on_problem(self.problem_id, code)
        # Fitness calculation logic (simplified for Phase 3)
        if result.get("success", False):
            # Success rate * 100 - (time penalty)
            fitness = 100.0 - (result.get("execution_time_ms", 0.0) / 100.0)
            return max(fitness, 1.0)
        return 1.0 # Minimal fitness for code that doesn't pass tests

    def run_generation(self, generation_id: int):
        """Execute a single evolutionary generation (Mutation, Evaluation, Selection)."""
        print(f"\n--- Generation {generation_id} ---")
        
        # 1. Selection
        parents = self.selector.select(self.population)
        if not parents:
            return

        # 2. Mutation & Crossover
        new_variants = []
        
        # Strategy A: Mutation on Parent 1
        code_a, record_a = self.mutator.mutate(parents[0], MutationMethod.OPTIMIZE)
        new_variants.append((code_a, record_a))
        
        # Strategy B: Crossover between Parent 1 and 2
        code_b, record_b = self.mutator.crossover(parents[0], parents[1])
        new_variants.append((code_b, record_b))
        
        # 3. Evaluation & Storage
        for code, record in new_variants:
            fitness = self.evaluate_variant(code)
            record.fitness_score = fitness
            variant_id = self.gene_bank.store_variant(code, record)
            self.population.append((uuid.UUID(variant_id), fitness))
            print(f"EvolutionaryOptimizer: Created new variant {variant_id} (Fitness: {fitness:.2f})")

        # 4. Pruning (Keep the best 5 individuals to prevent population explosion)
        self.population.sort(key=lambda x: x[1], reverse=True)
        self.population = self.population[:5]
        
        stats = self.selector.get_population_stats(self.population)
        print(f"Generation {generation_id} Complete. Avg Fitness: {stats['avg_fitness']:.2f}, Max Fitness: {stats['max_fitness']:.2f}")

    def run(self, num_generations: int = 3):
        """Execute multiple generations of the evolutionary loop."""
        for i in range(1, num_generations + 1):
            self.run_generation(i)
        
        best_variant_id = self.population[0][0]
        print(f"\nEvolutionary Process Complete. Best Variant: {best_variant_id} (Fitness: {self.population[0][1]:.2f})")
        return best_variant_id

if __name__ == "__main__":
    # Test script for the Evolutionary Optimizer
    initial_code = """
def sort_list(data):
    n = len(data)
    for i in range(n):
        for j in range(0, n - i - 1):
            if data[j] > data[j + 1]:
                data[j], data[j + 1] = data[j + 1], data[j]
    return data
"""
    optimizer = EvolutionaryOptimizer(problem_id="PB-001")
    optimizer.initialize_population(initial_code)
    # Perform a few generations
    # optimizer.run(num_generations=2) # This would require an actual LLM backend/API key
