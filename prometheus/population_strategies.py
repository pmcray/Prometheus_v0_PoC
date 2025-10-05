"""
Population-Based Improvement Strategies v0.1 (v0.57)
Advanced population management and evolution strategies

Implements sophisticated population-based optimization techniques:
- Multi-objective optimization with Pareto fronts
- Speciation and niching strategies
- Island model evolution
- Adaptive population sizing
- Diversity maintenance mechanisms
"""

import random
import statistics
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import logging

from .genetic_programming import CodeGenome, GeneticProgrammingEngine, EvolutionResult

class OptimizationObjective(Enum):
    """Different optimization objectives"""
    PERFORMANCE = "performance"
    MEMORY_EFFICIENCY = "memory_efficiency"
    CODE_QUALITY = "code_quality"
    MAINTAINABILITY = "maintainability"
    SECURITY = "security"
    EXECUTION_TIME = "execution_time"

@dataclass
class MultiObjectiveFitness:
    """Multi-objective fitness scores"""
    objectives: Dict[OptimizationObjective, float]
    weighted_score: float = 0.0
    pareto_rank: int = 0
    crowding_distance: float = 0.0

    def __post_init__(self):
        if not self.weighted_score:
            # Default equal weighting
            self.weighted_score = sum(self.objectives.values()) / len(self.objectives)

@dataclass
class Species:
    """Represents a species in speciation-based evolution"""
    species_id: str
    representative: CodeGenome
    members: List[CodeGenome] = field(default_factory=list)
    fitness_sharing_sigma: float = 2.0
    stagnation_count: int = 0
    best_fitness_history: List[float] = field(default_factory=list)
    creation_generation: int = 0

@dataclass
class Island:
    """Represents an island in island model evolution"""
    island_id: str
    population: List[CodeGenome]
    evolution_strategy: str  # "aggressive", "conservative", "explorative"
    migration_rate: float = 0.05
    isolation_generations: int = 10
    local_best: Optional[CodeGenome] = None
    specialization: Optional[OptimizationObjective] = None

class MultiObjectiveEvolution:
    """Multi-objective evolutionary algorithm (NSGA-II inspired)"""

    def __init__(self, objectives: List[OptimizationObjective],
                 objective_weights: Optional[Dict[OptimizationObjective, float]] = None):
        self.objectives = objectives
        self.objective_weights = objective_weights or {obj: 1.0 for obj in objectives}

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def evaluate_multiobjective_fitness(self, genome: CodeGenome,
                                      evaluators: Dict[OptimizationObjective, Callable]) -> MultiObjectiveFitness:
        """Evaluate genome against multiple objectives"""
        objective_scores = {}

        for objective in self.objectives:
            if objective in evaluators:
                try:
                    score = evaluators[objective](genome.source_code)
                    objective_scores[objective] = score
                except Exception:
                    objective_scores[objective] = 0.0
            else:
                # Default scoring for missing evaluators
                objective_scores[objective] = self._default_objective_score(genome, objective)

        # Calculate weighted score
        weighted_score = sum(
            score * self.objective_weights.get(objective, 1.0)
            for objective, score in objective_scores.items()
        )

        return MultiObjectiveFitness(
            objectives=objective_scores,
            weighted_score=weighted_score
        )

    def _default_objective_score(self, genome: CodeGenome, objective: OptimizationObjective) -> float:
        """Default scoring for objectives without specific evaluators"""
        code = genome.source_code

        if objective == OptimizationObjective.PERFORMANCE:
            # Favor shorter, more efficient code
            return max(0, 1.0 - len(code) / 1000.0)

        elif objective == OptimizationObjective.MEMORY_EFFICIENCY:
            # Count memory-efficient patterns
            efficient_patterns = ['generator', 'yield', 'del ', '__slots__']
            score = sum(0.1 for pattern in efficient_patterns if pattern in code)
            return min(1.0, score)

        elif objective == OptimizationObjective.CODE_QUALITY:
            # Basic code quality metrics
            lines = code.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            if not non_empty_lines:
                return 0.0

            avg_line_length = sum(len(line) for line in non_empty_lines) / len(non_empty_lines)
            quality_score = 1.0 - min(0.5, abs(avg_line_length - 40) / 80)  # Prefer ~40 char lines
            return quality_score

        elif objective == OptimizationObjective.MAINTAINABILITY:
            # Count maintainable patterns
            maintainable_patterns = ['def ', 'class ', '"""', "'''", 'return']
            score = sum(0.1 for pattern in maintainable_patterns if pattern in code)
            return min(1.0, score)

        elif objective == OptimizationObjective.SECURITY:
            # Penalize potentially unsafe patterns
            unsafe_patterns = ['eval(', 'exec(', '__import__', 'open(']
            penalty = sum(0.2 for pattern in unsafe_patterns if pattern in code)
            return max(0.0, 1.0 - penalty)

        elif objective == OptimizationObjective.EXECUTION_TIME:
            # Estimate execution efficiency
            efficient_constructs = ['list comprehension', 'set(', 'dict(', 'tuple(']
            score = sum(0.1 for construct in efficient_constructs
                       if any(pattern in code for pattern in [construct, construct.replace(' ', '_')]))
            return min(1.0, score)

        return 0.5  # Default neutral score

    def calculate_pareto_fronts(self, population: List[Tuple[CodeGenome, MultiObjectiveFitness]]) -> List[List[int]]:
        """Calculate Pareto fronts using non-dominated sorting"""
        n = len(population)
        fronts = []
        dominated_count = [0] * n
        dominated_solutions = [[] for _ in range(n)]

        # Find domination relationships
        for i in range(n):
            for j in range(n):
                if i != j:
                    if self._dominates(population[i][1], population[j][1]):
                        dominated_solutions[i].append(j)
                    elif self._dominates(population[j][1], population[i][1]):
                        dominated_count[i] += 1

        # Build first front
        current_front = []
        for i in range(n):
            if dominated_count[i] == 0:
                population[i][1].pareto_rank = 0
                current_front.append(i)

        fronts.append(current_front[:])

        # Build subsequent fronts
        while current_front:
            next_front = []
            for i in current_front:
                for j in dominated_solutions[i]:
                    dominated_count[j] -= 1
                    if dominated_count[j] == 0:
                        population[j][1].pareto_rank = len(fronts)
                        next_front.append(j)

            if next_front:
                fronts.append(next_front)
                current_front = next_front
            else:
                break

        return fronts

    def _dominates(self, fitness1: MultiObjectiveFitness, fitness2: MultiObjectiveFitness) -> bool:
        """Check if fitness1 dominates fitness2"""
        better_in_one = False
        for objective in self.objectives:
            score1 = fitness1.objectives.get(objective, 0.0)
            score2 = fitness2.objectives.get(objective, 0.0)

            if score1 < score2:
                return False
            elif score1 > score2:
                better_in_one = True

        return better_in_one

    def calculate_crowding_distance(self, front: List[int],
                                  population: List[Tuple[CodeGenome, MultiObjectiveFitness]]) -> None:
        """Calculate crowding distance for diversity maintenance"""
        if len(front) <= 2:
            for i in front:
                population[i][1].crowding_distance = float('inf')
            return

        # Initialize distances
        for i in front:
            population[i][1].crowding_distance = 0.0

        # Calculate distance for each objective
        for objective in self.objectives:
            # Sort front by this objective
            front.sort(key=lambda i: population[i][1].objectives.get(objective, 0.0))

            # Set boundary points to infinite distance
            population[front[0]][1].crowding_distance = float('inf')
            population[front[-1]][1].crowding_distance = float('inf')

            # Calculate distance for intermediate points
            obj_values = [population[i][1].objectives.get(objective, 0.0) for i in front]
            obj_range = max(obj_values) - min(obj_values)

            if obj_range > 0:
                for i in range(1, len(front) - 1):
                    distance = (obj_values[i + 1] - obj_values[i - 1]) / obj_range
                    population[front[i]][1].crowding_distance += distance

class SpeciationStrategy:
    """Implements speciation for maintaining diversity"""

    def __init__(self, compatibility_threshold: float = 3.0):
        self.compatibility_threshold = compatibility_threshold
        self.species: List[Species] = []
        self.species_counter = 0

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def speciate_population(self, population: List[CodeGenome]) -> Dict[str, List[CodeGenome]]:
        """Divide population into species based on similarity"""
        # Reset species membership
        for species in self.species:
            species.members = []

        unassigned = population[:]

        # Assign genomes to existing species
        for genome in population[:]:
            assigned = False
            for species in self.species:
                if self._is_compatible(genome, species.representative):
                    species.members.append(genome)
                    unassigned.remove(genome)
                    assigned = True
                    break

        # Create new species for unassigned genomes
        for genome in unassigned:
            new_species = Species(
                species_id=f"species_{self.species_counter}",
                representative=genome,
                members=[genome],
                creation_generation=0  # Would be set by calling context
            )
            self.species.append(new_species)
            self.species_counter += 1

        # Remove empty species
        self.species = [s for s in self.species if s.members]

        # Update representatives
        for species in self.species:
            if species.members:
                # Choose best genome as new representative
                best_genome = max(species.members,
                                key=lambda g: g.fitness_score if g.fitness_score else 0.0)
                species.representative = best_genome

        species_dict = {s.species_id: s.members for s in self.species}
        self.logger.info(f"🧬 Created {len(self.species)} species from {len(population)} genomes")

        return species_dict

    def _is_compatible(self, genome1: CodeGenome, genome2: CodeGenome) -> bool:
        """Check if two genomes are compatible (should be in same species)"""
        # Simple compatibility based on code similarity
        # In practice, this would use more sophisticated distance metrics

        code1 = genome1.source_code
        code2 = genome2.source_code

        # Length similarity
        len_diff = abs(len(code1) - len(code2)) / max(len(code1), len(code2), 1)

        # Character similarity (simplified)
        common_chars = set(code1) & set(code2)
        total_chars = set(code1) | set(code2)
        char_similarity = len(common_chars) / len(total_chars) if total_chars else 0

        # Simple compatibility score
        compatibility_score = 1.0 - len_diff + char_similarity

        return compatibility_score > self.compatibility_threshold / 10.0  # Normalize threshold

    def fitness_sharing(self, species_dict: Dict[str, List[CodeGenome]]) -> None:
        """Apply fitness sharing within species"""
        for species_id, members in species_dict.items():
            if len(members) <= 1:
                continue

            # Apply fitness sharing
            for genome in members:
                if genome.fitness_score is not None:
                    shared_fitness = genome.fitness_score / len(members)
                    # Store original fitness in metadata
                    genome.metadata['original_fitness'] = genome.fitness_score
                    genome.fitness_score = shared_fitness

class IslandModel:
    """Implements island model evolution with migration"""

    def __init__(self, num_islands: int = 4, migration_interval: int = 10):
        self.num_islands = num_islands
        self.migration_interval = migration_interval
        self.islands: List[Island] = []
        self.generation = 0

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def initialize_islands(self, population: List[CodeGenome]) -> List[Island]:
        """Initialize islands with different specializations"""
        island_size = len(population) // self.num_islands
        objectives = list(OptimizationObjective)

        for i in range(self.num_islands):
            start_idx = i * island_size
            end_idx = start_idx + island_size if i < self.num_islands - 1 else len(population)

            island_population = population[start_idx:end_idx]

            # Assign specialization and strategy
            specialization = objectives[i % len(objectives)] if objectives else None
            strategies = ["aggressive", "conservative", "explorative"]
            strategy = strategies[i % len(strategies)]

            island = Island(
                island_id=f"island_{i}",
                population=island_population,
                evolution_strategy=strategy,
                specialization=specialization,
                migration_rate=0.05 + (i * 0.01)  # Vary migration rates
            )

            self.islands.append(island)

        self.logger.info(f"🏝️ Initialized {len(self.islands)} islands")
        return self.islands

    def evolve_islands(self, generations: int) -> List[CodeGenome]:
        """Evolve islands independently with periodic migration"""
        for gen in range(generations):
            self.generation = gen

            # Evolve each island independently
            for island in self.islands:
                self._evolve_island(island)

            # Migration every N generations
            if gen % self.migration_interval == 0 and gen > 0:
                self._migrate_individuals()

        # Collect all populations
        all_individuals = []
        for island in self.islands:
            all_individuals.extend(island.population)

        return all_individuals

    def _evolve_island(self, island: Island) -> None:
        """Evolve a single island for one generation"""
        # Use different evolution strategies
        if island.evolution_strategy == "aggressive":
            # High mutation rate, aggressive selection
            mutation_rate = 0.3
            crossover_rate = 0.9
        elif island.evolution_strategy == "conservative":
            # Low mutation rate, preserve good solutions
            mutation_rate = 0.05
            crossover_rate = 0.5
        else:  # explorative
            # Balanced exploration
            mutation_rate = 0.15
            crossover_rate = 0.7

        # Create local GP engine for this island
        gp_engine = GeneticProgrammingEngine(
            population_size=len(island.population),
            mutation_rate=mutation_rate,
            crossover_rate=crossover_rate,
            elite_size=max(1, len(island.population) // 10)
        )

        # Set current population
        gp_engine.population = island.population

        # Evaluate fitness (specialized if applicable)
        gp_engine.population = gp_engine.evaluate_fitness(gp_engine.population)

        # Track island best
        if gp_engine.population:
            current_best = gp_engine.population[0]
            if not island.local_best or (current_best.fitness_score or 0) > (island.local_best.fitness_score or 0):
                island.local_best = current_best

        # Selection and reproduction
        parents = gp_engine.selection(gp_engine.population)
        island.population = gp_engine.crossover_and_mutation(parents)

    def _migrate_individuals(self) -> None:
        """Migrate best individuals between islands"""
        if len(self.islands) < 2:
            return

        migrants_per_island = max(1, int(self.islands[0].migration_rate * len(self.islands[0].population)))

        # Collect migrants from each island (best individuals)
        migrants = []
        for island in self.islands:
            # Sort by fitness and take the best
            sorted_population = sorted(
                island.population,
                key=lambda g: g.fitness_score if g.fitness_score else 0.0,
                reverse=True
            )

            island_migrants = sorted_population[:migrants_per_island]
            migrants.extend([(island.island_id, migrant) for migrant in island_migrants])

        # Redistribute migrants randomly to other islands
        for island in self.islands:
            # Remove worst individuals to make room
            island.population.sort(key=lambda g: g.fitness_score if g.fitness_score else 0.0, reverse=True)
            island.population = island.population[:-migrants_per_island]

            # Add random migrants from other islands
            available_migrants = [migrant for source_id, migrant in migrants if source_id != island.island_id]
            if available_migrants:
                new_migrants = random.sample(available_migrants,
                                           min(migrants_per_island, len(available_migrants)))
                island.population.extend(new_migrants)

        self.logger.info(f"🔄 Migration completed at generation {self.generation}")

class AdaptivePopulationManager:
    """Manages adaptive population sizing and diversity"""

    def __init__(self, min_population: int = 20, max_population: int = 200):
        self.min_population = min_population
        self.max_population = max_population
        self.diversity_history: List[float] = []
        self.fitness_history: List[float] = []

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def adapt_population_size(self, population: List[CodeGenome],
                            diversity_threshold: float = 0.1) -> int:
        """Determine optimal population size based on diversity and performance"""

        # Calculate current diversity
        diversity = self._calculate_diversity(population)
        self.diversity_history.append(diversity)

        # Calculate average fitness
        fitness_scores = [g.fitness_score for g in population if g.fitness_score is not None]
        if fitness_scores:
            avg_fitness = statistics.mean(fitness_scores)
            self.fitness_history.append(avg_fitness)

        current_size = len(population)

        # Increase population if diversity is low
        if diversity < diversity_threshold:
            new_size = min(self.max_population, int(current_size * 1.2))
            self.logger.info(f"📈 Increasing population size: {current_size} -> {new_size} (low diversity: {diversity:.3f})")
            return new_size

        # Decrease population if diversity is very high (may indicate lack of selection pressure)
        elif diversity > 0.8:
            new_size = max(self.min_population, int(current_size * 0.9))
            self.logger.info(f"📉 Decreasing population size: {current_size} -> {new_size} (high diversity: {diversity:.3f})")
            return new_size

        return current_size

    def _calculate_diversity(self, population: List[CodeGenome]) -> float:
        """Calculate genetic diversity in the population"""
        if len(population) < 2:
            return 0.0

        # Simple diversity based on code length variance
        code_lengths = [len(genome.source_code) for genome in population]

        if len(set(code_lengths)) == 1:
            return 0.0  # No diversity

        length_variance = statistics.variance(code_lengths)
        max_possible_variance = (max(code_lengths) - min(code_lengths)) ** 2 / 4

        diversity = length_variance / max_possible_variance if max_possible_variance > 0 else 0.0
        return min(1.0, diversity)

    def maintain_diversity(self, population: List[CodeGenome],
                         target_diversity: float = 0.3) -> List[CodeGenome]:
        """Actively maintain population diversity"""
        current_diversity = self._calculate_diversity(population)

        if current_diversity >= target_diversity:
            return population

        # Add diverse individuals through mutation
        diverse_population = population[:]

        # Create mutations of existing genomes to increase diversity
        from .genetic_programming import ASTMutator
        mutator = ASTMutator(mutation_rate=0.5)  # High mutation rate for diversity

        attempts = 0
        while current_diversity < target_diversity and attempts < len(population):
            # Select random genome to mutate
            base_genome = random.choice(population)

            try:
                mutated_ast, mutations = mutator.mutate(base_genome.code_ast)
                mutated_code = ast.unparse(mutated_ast)

                # Create new diverse genome
                diverse_genome = CodeGenome(
                    genome_id=f"diverse_{attempts}_{hash(mutated_code) % 10000}",
                    code_ast=mutated_ast,
                    source_code=mutated_code,
                    generation=base_genome.generation,
                    parent_ids=[base_genome.genome_id],
                    mutation_history=mutations,
                    creation_method="diversity_maintenance"
                )

                diverse_population.append(diverse_genome)
                current_diversity = self._calculate_diversity(diverse_population)

            except Exception:
                pass  # Skip failed mutations

            attempts += 1

        self.logger.info(f"🌈 Diversity maintenance: {len(population)} -> {len(diverse_population)} genomes")
        return diverse_population

class AdvancedPopulationStrategy:
    """Combines all population strategies into a unified system"""

    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}

        self.use_multiobjective = config.get('use_multiobjective', True)
        self.use_speciation = config.get('use_speciation', True)
        self.use_islands = config.get('use_islands', False)
        self.use_adaptive_sizing = config.get('use_adaptive_sizing', True)

        # Initialize components
        if self.use_multiobjective:
            objectives = config.get('objectives', [
                OptimizationObjective.PERFORMANCE,
                OptimizationObjective.CODE_QUALITY,
                OptimizationObjective.MAINTAINABILITY
            ])
            self.multiobjective = MultiObjectiveEvolution(objectives)

        if self.use_speciation:
            self.speciation = SpeciationStrategy(
                compatibility_threshold=config.get('compatibility_threshold', 3.0)
            )

        if self.use_islands:
            self.islands = IslandModel(
                num_islands=config.get('num_islands', 4),
                migration_interval=config.get('migration_interval', 10)
            )

        if self.use_adaptive_sizing:
            self.population_manager = AdaptivePopulationManager(
                min_population=config.get('min_population', 20),
                max_population=config.get('max_population', 200)
            )

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def evolve_population(self, population: List[CodeGenome],
                         generations: int = 100,
                         evaluators: Optional[Dict[OptimizationObjective, Callable]] = None) -> EvolutionResult:
        """Evolve population using all configured strategies"""

        self.logger.info(f"🚀 Starting advanced population evolution with {len(population)} genomes")

        start_time = datetime.now()
        best_fitness_history = []

        current_population = population[:]

        for gen in range(generations):
            self.logger.info(f"🧬 Generation {gen + 1}/{generations}")

            # Multi-objective evaluation
            if self.use_multiobjective and evaluators:
                multiobjective_population = []
                for genome in current_population:
                    mo_fitness = self.multiobjective.evaluate_multiobjective_fitness(genome, evaluators)
                    multiobjective_population.append((genome, mo_fitness))
                    genome.fitness_score = mo_fitness.weighted_score

                # Calculate Pareto fronts
                fronts = self.multiobjective.calculate_pareto_fronts(multiobjective_population)
                for front in fronts:
                    self.multiobjective.calculate_crowding_distance(front, multiobjective_population)

            # Speciation
            if self.use_speciation:
                species_dict = self.speciation.speciate_population(current_population)
                self.speciation.fitness_sharing(species_dict)

            # Island model evolution
            if self.use_islands:
                if gen == 0:  # Initialize islands
                    self.islands.initialize_islands(current_population)

                current_population = self.islands.evolve_islands(1)  # Evolve for 1 generation

            # Adaptive population management
            if self.use_adaptive_sizing:
                target_size = self.population_manager.adapt_population_size(current_population)

                if len(current_population) < target_size:
                    # Add diverse individuals
                    current_population = self.population_manager.maintain_diversity(current_population)
                elif len(current_population) > target_size:
                    # Remove worst individuals
                    current_population.sort(key=lambda g: g.fitness_score or 0.0, reverse=True)
                    current_population = current_population[:target_size]

            # Track best fitness
            fitness_scores = [g.fitness_score for g in current_population if g.fitness_score is not None]
            if fitness_scores:
                best_fitness = max(fitness_scores)
                best_fitness_history.append(best_fitness)

        # Final evaluation and results
        current_population.sort(key=lambda g: g.fitness_score or 0.0, reverse=True)
        best_genome = current_population[0] if current_population else None

        evolution_time = (datetime.now() - start_time).total_seconds()

        result = EvolutionResult(
            best_genome=best_genome,
            final_population=current_population,
            generation_count=generations,
            fitness_history=best_fitness_history,
            convergence_info={
                "strategies_used": {
                    "multiobjective": self.use_multiobjective,
                    "speciation": self.use_speciation,
                    "islands": self.use_islands,
                    "adaptive_sizing": self.use_adaptive_sizing
                },
                "final_population_size": len(current_population),
                "species_count": len(self.speciation.species) if self.use_speciation else 0,
                "islands_count": len(self.islands.islands) if self.use_islands else 0
            },
            evolution_time_seconds=evolution_time
        )

        self.logger.info(f"🏁 Advanced population evolution completed in {evolution_time:.1f}s")
        return result