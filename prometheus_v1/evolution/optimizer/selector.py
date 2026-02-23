
import random
from typing import List, Tuple, Dict, Any
import uuid

class Selector:
    """
    Tournament Selection Logic for Evolutionary Self-Improvement.
    Selects the fittest agent variants from a population for the next generation.
    """
    def __init__(self, tournament_size: int = 3):
        self.tournament_size = tournament_size

    def select(self, population: List[Tuple[uuid.UUID, float]]) -> List[uuid.UUID]:
        """
        Select the top 2 fittest candidates from the population for mutation/crossover.
        
        Args:
            population: A list of (variant_id, fitness_score) tuples.
        
        Returns:
            A list of selected variant_ids.
        """
        if not population:
            return []
            
        # Perform tournament selection to choose parents
        selected_parents = []
        for _ in range(2):
            # Sample tournament_size unique individuals
            tournament = random.sample(population, min(len(population), self.tournament_size))
            # Choose the one with the highest fitness score
            winner = max(tournament, key=lambda x: x[1])
            selected_parents.append(winner[0])
            
        print(f"Selector: Selected fittest parents {selected_parents[0]} and {selected_parents[1]} for evolution.")
        return selected_parents

    def get_population_stats(self, population: List[Tuple[uuid.UUID, float]]) -> Dict[str, Any]:
        """Calculate basic statistics for the current population."""
        if not population:
            return {"avg_fitness": 0.0, "max_fitness": 0.0, "count": 0}
            
        fitness_scores = [p[1] for p in population]
        avg_fitness = sum(fitness_scores) / len(fitness_scores)
        max_fitness = max(fitness_scores)
        
        return {
            "avg_fitness": avg_fitness,
            "max_fitness": max_fitness,
            "count": len(population)
        }
