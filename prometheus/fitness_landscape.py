"""
Fitness Landscape Exploration System v0.1 (v0.59)
Advanced fitness landscape analysis and exploration

Implements sophisticated techniques for understanding and navigating
the fitness landscape in code evolution:
- Fitness landscape mapping and visualization
- Local optima detection and escape strategies
- Gradient-based search and hill climbing
- Novelty search and exploration rewards
- Adaptive search strategies based on landscape topology
"""

import random
import statistics
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import json

from .genetic_programming import CodeGenome, GeneticProgrammingEngine
from .advanced_operators import AdaptiveOperatorSelector, OperatorType

class LandscapeTopology(Enum):
    """Types of fitness landscape topologies"""
    SMOOTH = "smooth"
    RUGGED = "rugged"
    NEUTRAL = "neutral"
    MULTI_MODAL = "multi_modal"
    DECEPTIVE = "deceptive"

@dataclass
class FitnessPoint:
    """A point in the fitness landscape"""
    genome: CodeGenome
    fitness: float
    coordinates: List[float]  # Simplified coordinate representation
    neighbors: List[str] = field(default_factory=list)  # Genome IDs of neighbors
    local_gradient: Optional[List[float]] = None
    visited: bool = False

@dataclass
class LocalOptimum:
    """Represents a local optimum in the fitness landscape"""
    peak_genome: CodeGenome
    peak_fitness: float
    basin_size: int
    escape_difficulty: float
    discovery_generation: int
    exploration_count: int = 0

@dataclass
class SearchTrajectory:
    """Tracks a search trajectory through the landscape"""
    trajectory_id: str
    points: List[FitnessPoint]
    start_fitness: float
    end_fitness: float
    improvement: float
    stuck_generations: int
    exploration_novelty: float

class FitnessLandscapeMapper:
    """Maps and analyzes the fitness landscape"""

    def __init__(self, dimensionality: int = 10):
        self.dimensionality = dimensionality
        self.fitness_points: Dict[str, FitnessPoint] = {}
        self.local_optima: List[LocalOptimum] = []
        self.explored_regions: Set[Tuple[float, ...]] = set()

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def map_genome_to_coordinates(self, genome: CodeGenome) -> List[float]:
        """Map a genome to coordinates in the fitness landscape"""
        # Simplified coordinate mapping based on code features
        code = genome.source_code

        coordinates = []

        # Feature 1: Code length (normalized)
        coordinates.append(min(1.0, len(code) / 1000.0))

        # Feature 2: Number of functions
        func_count = code.count('def ') + code.count('lambda')
        coordinates.append(min(1.0, func_count / 10.0))

        # Feature 3: Cyclomatic complexity estimate
        complexity = code.count('if ') + code.count('for ') + code.count('while ') + code.count('except ')
        coordinates.append(min(1.0, complexity / 20.0))

        # Feature 4: Variable diversity
        import re
        variables = set(re.findall(r'\b[a-zA-Z_]\w*\b', code))
        coordinates.append(min(1.0, len(variables) / 50.0))

        # Feature 5: String/numeric literal ratio
        strings = code.count('"') + code.count("'")
        numbers = len(re.findall(r'\b\d+\b', code))
        coordinates.append(min(1.0, (strings + numbers) / 20.0))

        # Additional features to reach desired dimensionality
        remaining = self.dimensionality - len(coordinates)
        for i in range(remaining):
            # Hash-based features for additional dimensions
            feature_hash = hash(code + str(i)) % 1000
            coordinates.append(feature_hash / 1000.0)

        return coordinates[:self.dimensionality]

    def add_fitness_point(self, genome: CodeGenome, fitness: float) -> FitnessPoint:
        """Add a new point to the fitness landscape"""
        coordinates = self.map_genome_to_coordinates(genome)

        point = FitnessPoint(
            genome=genome,
            fitness=fitness,
            coordinates=coordinates
        )

        self.fitness_points[genome.genome_id] = point

        # Update explored regions (discretized coordinates)
        discretized = tuple(round(c, 1) for c in coordinates)
        self.explored_regions.add(discretized)

        return point

    def calculate_local_gradient(self, point: FitnessPoint) -> List[float]:
        """Calculate local gradient at a fitness point"""
        if not point.neighbors:
            return [0.0] * self.dimensionality

        gradient = [0.0] * self.dimensionality

        for neighbor_id in point.neighbors:
            if neighbor_id in self.fitness_points:
                neighbor = self.fitness_points[neighbor_id]
                fitness_diff = neighbor.fitness - point.fitness

                for i in range(self.dimensionality):
                    coord_diff = neighbor.coordinates[i] - point.coordinates[i]
                    if abs(coord_diff) > 1e-6:  # Avoid division by zero
                        gradient[i] += fitness_diff / coord_diff

        # Normalize gradient
        if point.neighbors:
            gradient = [g / len(point.neighbors) for g in gradient]

        point.local_gradient = gradient
        return gradient

    def find_neighbors(self, point: FitnessPoint, radius: float = 0.1) -> List[str]:
        """Find neighboring points in the landscape"""
        neighbors = []

        for genome_id, other_point in self.fitness_points.items():
            if genome_id == point.genome.genome_id:
                continue

            # Calculate Euclidean distance
            distance = self._euclidean_distance(point.coordinates, other_point.coordinates)

            if distance <= radius:
                neighbors.append(genome_id)

        point.neighbors = neighbors
        return neighbors

    def identify_local_optima(self, fitness_threshold: float = 0.01) -> List[LocalOptimum]:
        """Identify local optima in the fitness landscape"""
        potential_optima = []

        for point in self.fitness_points.values():
            if not point.neighbors:
                self.find_neighbors(point)

            # Check if this point is a local maximum
            is_local_max = True
            for neighbor_id in point.neighbors:
                neighbor = self.fitness_points[neighbor_id]
                if neighbor.fitness > point.fitness + fitness_threshold:
                    is_local_max = False
                    break

            if is_local_max and point.fitness > 0.1:  # Minimum fitness threshold
                # Calculate basin size and escape difficulty
                basin_size = len(point.neighbors) + 1
                escape_difficulty = self._calculate_escape_difficulty(point)

                optimum = LocalOptimum(
                    peak_genome=point.genome,
                    peak_fitness=point.fitness,
                    basin_size=basin_size,
                    escape_difficulty=escape_difficulty,
                    discovery_generation=point.genome.generation
                )

                potential_optima.append(optimum)

        # Remove duplicates and update local optima list
        unique_optima = self._deduplicate_optima(potential_optima)
        self.local_optima = unique_optima

        self.logger.info(f"🏔️ Identified {len(unique_optima)} local optima")
        return unique_optima

    def analyze_landscape_topology(self) -> LandscapeTopology:
        """Analyze the overall topology of the fitness landscape"""
        if len(self.fitness_points) < 10:
            return LandscapeTopology.SMOOTH

        fitness_values = [p.fitness for p in self.fitness_points.values()]

        # Calculate landscape statistics
        fitness_variance = statistics.variance(fitness_values)
        fitness_range = max(fitness_values) - min(fitness_values)
        num_optima = len(self.local_optima)

        # Analyze gradients
        gradients = []
        for point in self.fitness_points.values():
            if point.local_gradient:
                gradient_magnitude = sum(abs(g) for g in point.local_gradient)
                gradients.append(gradient_magnitude)

        avg_gradient = statistics.mean(gradients) if gradients else 0.0

        # Topology classification
        if num_optima > 5 and fitness_variance > 0.1:
            return LandscapeTopology.MULTI_MODAL
        elif avg_gradient < 0.01 and fitness_variance < 0.05:
            return LandscapeTopology.NEUTRAL
        elif fitness_variance > 0.2 and avg_gradient > 0.1:
            return LandscapeTopology.RUGGED
        elif self._detect_deceptive_pattern():
            return LandscapeTopology.DECEPTIVE
        else:
            return LandscapeTopology.SMOOTH

    def _euclidean_distance(self, coords1: List[float], coords2: List[float]) -> float:
        """Calculate Euclidean distance between coordinate points"""
        return sum((a - b) ** 2 for a, b in zip(coords1, coords2)) ** 0.5

    def _calculate_escape_difficulty(self, point: FitnessPoint) -> float:
        """Calculate difficulty of escaping from a local optimum"""
        if not point.neighbors:
            return 1.0

        max_neighbor_fitness = max(
            self.fitness_points[nid].fitness for nid in point.neighbors
        )

        escape_barrier = point.fitness - max_neighbor_fitness
        return max(0.0, escape_barrier)

    def _deduplicate_optima(self, optima: List[LocalOptimum]) -> List[LocalOptimum]:
        """Remove duplicate local optima"""
        unique_optima = []

        for optimum in optima:
            is_duplicate = False
            for existing in unique_optima:
                # Check if optima are too close in fitness and position
                fitness_diff = abs(optimum.peak_fitness - existing.peak_fitness)
                if fitness_diff < 0.01:  # Too similar in fitness
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_optima.append(optimum)

        return unique_optima

    def _detect_deceptive_pattern(self) -> bool:
        """Detect deceptive landscape patterns"""
        # Simple deception detection: high fitness areas that don't lead to global optimum
        if not self.fitness_points:
            return False

        fitness_values = [p.fitness for p in self.fitness_points.values()]
        max_fitness = max(fitness_values)

        # Look for isolated high-fitness regions
        high_fitness_points = [
            p for p in self.fitness_points.values()
            if p.fitness > max_fitness * 0.8
        ]

        if len(high_fitness_points) > 1:
            # Check if high-fitness points are far apart
            for i, p1 in enumerate(high_fitness_points):
                for p2 in high_fitness_points[i+1:]:
                    distance = self._euclidean_distance(p1.coordinates, p2.coordinates)
                    if distance > 0.5:  # Far apart in coordinate space
                        return True

        return False

class NoveltySearch:
    """Implements novelty search to encourage exploration"""

    def __init__(self, k_nearest: int = 5, novelty_threshold: float = 0.1):
        self.k_nearest = k_nearest
        self.novelty_threshold = novelty_threshold
        self.behavior_archive: List[Tuple[str, List[float]]] = []

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def calculate_novelty(self, genome: CodeGenome, landscape_mapper: FitnessLandscapeMapper) -> float:
        """Calculate novelty score for a genome"""
        # Extract behavior characteristics
        behavior = self._extract_behavior_characteristics(genome)

        if len(self.behavior_archive) < self.k_nearest:
            # Not enough archive members, assume high novelty
            self.behavior_archive.append((genome.genome_id, behavior))
            return 1.0

        # Calculate distances to k-nearest neighbors in behavior space
        distances = []
        for archive_id, archive_behavior in self.behavior_archive:
            distance = self._behavior_distance(behavior, archive_behavior)
            distances.append(distance)

        # Get k-nearest distances
        distances.sort()
        k_nearest_distances = distances[:self.k_nearest]

        # Novelty is average distance to k-nearest neighbors
        novelty_score = statistics.mean(k_nearest_distances)

        # Add to archive if novel enough
        if novelty_score > self.novelty_threshold:
            self.behavior_archive.append((genome.genome_id, behavior))

        return novelty_score

    def _extract_behavior_characteristics(self, genome: CodeGenome) -> List[float]:
        """Extract behavioral characteristics from genome"""
        code = genome.source_code

        characteristics = []

        # Execution pattern characteristics
        characteristics.append(float(code.count('return')))  # Number of returns
        characteristics.append(float(code.count('if')))      # Branching behavior
        characteristics.append(float(code.count('for') + code.count('while')))  # Loop behavior
        characteristics.append(float(len(code.split('\n'))))  # Code structure

        # Semantic characteristics
        characteristics.append(float(code.count('+')))       # Addition operations
        characteristics.append(float(code.count('-')))       # Subtraction operations
        characteristics.append(float(code.count('*')))       # Multiplication operations
        characteristics.append(float(code.count('=')))       # Assignment operations

        # Normalize characteristics
        max_val = max(characteristics) if characteristics else 1.0
        if max_val > 0:
            characteristics = [c / max_val for c in characteristics]

        return characteristics

    def _behavior_distance(self, behavior1: List[float], behavior2: List[float]) -> float:
        """Calculate distance between behavioral characteristics"""
        min_len = min(len(behavior1), len(behavior2))
        return sum(abs(behavior1[i] - behavior2[i]) for i in range(min_len)) / min_len

class AdaptiveSearchStrategy:
    """Adapts search strategy based on landscape topology"""

    def __init__(self):
        self.strategy_performance: Dict[str, Dict[str, float]] = {
            'hill_climbing': {'attempts': 0, 'successes': 0, 'avg_improvement': 0.0},
            'random_walk': {'attempts': 0, 'successes': 0, 'avg_improvement': 0.0},
            'gradient_ascent': {'attempts': 0, 'successes': 0, 'avg_improvement': 0.0},
            'novelty_search': {'attempts': 0, 'successes': 0, 'avg_improvement': 0.0},
            'jump_escape': {'attempts': 0, 'successes': 0, 'avg_improvement': 0.0}
        }

        self.current_topology = LandscapeTopology.SMOOTH

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def select_search_strategy(self, topology: LandscapeTopology,
                             stuck_generations: int = 0) -> str:
        """Select optimal search strategy based on landscape topology"""

        self.current_topology = topology

        if topology == LandscapeTopology.SMOOTH:
            # Gradient-based methods work well on smooth landscapes
            if stuck_generations > 5:
                return 'novelty_search'  # Encourage exploration if stuck
            return 'gradient_ascent'

        elif topology == LandscapeTopology.RUGGED:
            # Random methods better for rugged landscapes
            if stuck_generations > 10:
                return 'jump_escape'  # Large jumps to escape local optima
            return 'random_walk'

        elif topology == LandscapeTopology.MULTI_MODAL:
            # Need exploration to find different modes
            return 'novelty_search'

        elif topology == LandscapeTopology.NEUTRAL:
            # Random walk effective on neutral landscapes
            return 'random_walk'

        elif topology == LandscapeTopology.DECEPTIVE:
            # Novelty search to avoid deceptive attractors
            return 'novelty_search'

        # Default to adaptive selection based on performance
        return self._select_best_performing_strategy()

    def _select_best_performing_strategy(self) -> str:
        """Select strategy with best historical performance"""
        best_strategy = 'hill_climbing'
        best_score = 0.0

        for strategy, stats in self.strategy_performance.items():
            if stats['attempts'] > 0:
                success_rate = stats['successes'] / stats['attempts']
                avg_improvement = stats['avg_improvement']
                score = success_rate * 0.7 + avg_improvement * 0.3

                if score > best_score:
                    best_score = score
                    best_strategy = strategy

        return best_strategy

    def update_strategy_performance(self, strategy: str, success: bool, improvement: float):
        """Update performance statistics for a strategy"""
        if strategy in self.strategy_performance:
            stats = self.strategy_performance[strategy]
            stats['attempts'] += 1

            if success:
                stats['successes'] += 1

            # Update average improvement (running average)
            current_avg = stats['avg_improvement']
            attempts = stats['attempts']
            stats['avg_improvement'] = (current_avg * (attempts - 1) + improvement) / attempts

class FitnessLandscapeExplorer:
    """Main class for fitness landscape exploration"""

    def __init__(self,
                 fitness_evaluator: Callable[[str], float],
                 dimensionality: int = 10):

        self.fitness_evaluator = fitness_evaluator
        self.landscape_mapper = FitnessLandscapeMapper(dimensionality)
        self.novelty_search = NoveltySearch()
        self.adaptive_strategy = AdaptiveSearchStrategy()
        self.operator_selector = AdaptiveOperatorSelector()

        self.exploration_history: List[SearchTrajectory] = []
        self.current_trajectory: Optional[SearchTrajectory] = None

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def explore_landscape(self,
                         initial_population: List[CodeGenome],
                         exploration_generations: int = 100,
                         exploration_strategy: str = "adaptive") -> Dict[str, Any]:
        """Comprehensive fitness landscape exploration"""

        self.logger.info(f"🗺️ Starting fitness landscape exploration ({exploration_generations} generations)")

        start_time = datetime.now()

        # Initialize landscape with population
        for genome in initial_population:
            if genome.fitness_score is None:
                genome.fitness_score = self.fitness_evaluator(genome.source_code)

            point = self.landscape_mapper.add_fitness_point(genome, genome.fitness_score)
            self.landscape_mapper.find_neighbors(point)
            self.landscape_mapper.calculate_local_gradient(point)

        # Analyze initial topology
        current_topology = self.landscape_mapper.analyze_landscape_topology()
        self.logger.info(f"🏔️ Detected landscape topology: {current_topology.value}")

        exploration_results = {
            'initial_topology': current_topology.value,
            'trajectories': [],
            'optima_discovered': [],
            'coverage_achieved': 0.0,
            'exploration_efficiency': 0.0
        }

        # Main exploration loop
        current_population = initial_population[:]
        stuck_generations = 0
        last_best_fitness = 0.0

        for generation in range(exploration_generations):
            generation_start_fitness = max(g.fitness_score for g in current_population if g.fitness_score)

            # Select search strategy
            if exploration_strategy == "adaptive":
                strategy = self.adaptive_strategy.select_search_strategy(
                    current_topology, stuck_generations
                )
            else:
                strategy = exploration_strategy

            # Apply exploration strategy
            new_genomes = self._apply_exploration_strategy(
                strategy, current_population, generation
            )

            # Evaluate new genomes and update landscape
            for genome in new_genomes:
                if genome.fitness_score is None:
                    genome.fitness_score = self.fitness_evaluator(genome.source_code)

                point = self.landscape_mapper.add_fitness_point(genome, genome.fitness_score)
                self.landscape_mapper.find_neighbors(point)
                self.landscape_mapper.calculate_local_gradient(point)

            # Update population
            all_genomes = current_population + new_genomes
            all_genomes.sort(key=lambda g: g.fitness_score or 0.0, reverse=True)
            current_population = all_genomes[:len(initial_population)]

            # Check for improvement
            current_best_fitness = max(g.fitness_score for g in current_population if g.fitness_score)

            if current_best_fitness > last_best_fitness + 0.001:  # Improvement threshold
                stuck_generations = 0

                # Update strategy performance
                improvement = current_best_fitness - generation_start_fitness
                self.adaptive_strategy.update_strategy_performance(strategy, True, improvement)
            else:
                stuck_generations += 1
                self.adaptive_strategy.update_strategy_performance(strategy, False, 0.0)

            last_best_fitness = current_best_fitness

            # Periodic topology re-analysis
            if generation % 20 == 0:
                current_topology = self.landscape_mapper.analyze_landscape_topology()

            # Log progress
            if generation % 10 == 0:
                self.logger.info(f"Generation {generation}: Best fitness = {current_best_fitness:.4f}, "
                               f"Strategy = {strategy}, Stuck = {stuck_generations}")

        # Final analysis
        final_optima = self.landscape_mapper.identify_local_optima()
        final_topology = self.landscape_mapper.analyze_landscape_topology()

        # Calculate exploration metrics
        coverage = len(self.landscape_mapper.explored_regions) / (10 ** self.landscape_mapper.dimensionality)
        efficiency = len(final_optima) / max(1, exploration_generations)

        exploration_time = (datetime.now() - start_time).total_seconds()

        exploration_results.update({
            'final_topology': final_topology.value,
            'optima_discovered': [
                {
                    'fitness': opt.peak_fitness,
                    'basin_size': opt.basin_size,
                    'escape_difficulty': opt.escape_difficulty,
                    'generation_discovered': opt.discovery_generation
                }
                for opt in final_optima
            ],
            'coverage_achieved': coverage,
            'exploration_efficiency': efficiency,
            'total_points_explored': len(self.landscape_mapper.fitness_points),
            'final_population': current_population,
            'exploration_time_seconds': exploration_time,
            'strategy_performance': self.adaptive_strategy.strategy_performance
        })

        self.logger.info(f"🏁 Exploration completed: {len(final_optima)} optima found, "
                        f"{coverage:.1%} coverage, {exploration_time:.1f}s")

        return exploration_results

    def _apply_exploration_strategy(self,
                                  strategy: str,
                                  population: List[CodeGenome],
                                  generation: int) -> List[CodeGenome]:
        """Apply specific exploration strategy"""

        new_genomes = []

        if strategy == 'hill_climbing':
            # Local hill climbing
            for genome in population[:5]:  # Top 5 genomes
                result = self.operator_selector.select_and_apply_operator(
                    [genome], OperatorType.MUTATION
                )
                if result.success:
                    new_genomes.extend(result.offspring)

        elif strategy == 'gradient_ascent':
            # Follow local gradients
            for genome in population[:3]:
                point = self.landscape_mapper.fitness_points.get(genome.genome_id)
                if point and point.local_gradient:
                    # Create mutations biased by gradient direction
                    result = self.operator_selector.select_and_apply_operator(
                        [genome], OperatorType.MUTATION
                    )
                    if result.success:
                        new_genomes.extend(result.offspring)

        elif strategy == 'random_walk':
            # Random exploration
            for genome in random.sample(population, min(5, len(population))):
                result = self.operator_selector.select_and_apply_operator(
                    [genome], OperatorType.MUTATION
                )
                if result.success:
                    new_genomes.extend(result.offspring)

        elif strategy == 'novelty_search':
            # Prioritize novel behaviors
            population_with_novelty = []
            for genome in population:
                novelty = self.novelty_search.calculate_novelty(genome, self.landscape_mapper)
                population_with_novelty.append((genome, novelty))

            # Select most novel genomes for mutation
            population_with_novelty.sort(key=lambda x: x[1], reverse=True)
            for genome, _ in population_with_novelty[:5]:
                result = self.operator_selector.select_and_apply_operator(
                    [genome], OperatorType.MUTATION
                )
                if result.success:
                    new_genomes.extend(result.offspring)

        elif strategy == 'jump_escape':
            # Large mutations to escape local optima
            for genome in population[:3]:
                result = self.operator_selector.select_and_apply_operator(
                    [genome], OperatorType.MACRO_MUTATION
                )
                if result.success:
                    new_genomes.extend(result.offspring)

        return new_genomes

    def get_landscape_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of the fitness landscape"""
        return {
            'topology': self.landscape_mapper.analyze_landscape_topology().value,
            'points_mapped': len(self.landscape_mapper.fitness_points),
            'local_optima_count': len(self.landscape_mapper.local_optima),
            'regions_explored': len(self.landscape_mapper.explored_regions),
            'novelty_archive_size': len(self.novelty_search.behavior_archive),
            'strategy_stats': self.adaptive_strategy.strategy_performance,
            'exploration_history_count': len(self.exploration_history)
        }