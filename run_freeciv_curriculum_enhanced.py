#!/usr/bin/env python3
"""
PrometheusStar FreeCiv Curriculum - Enhanced Version
- 1000+ generations per stage
- Earth map with 7 civilizations
- Rich strategy genomes
- Progress updates every generation
"""

import time
import random
from typing import List, Dict
from freeciv_simulator_enhanced import FreeCivGameEnhanced, StrategyGenome

# Enhanced curriculum - much larger scale
CURRICULUM = [
    {
        "stage": 1,
        "name": "City Building Basics",
        "ai_level": "novice",
        "ai_skill": 1,
        "population": 50,  # Increased from 4
        "generations": 1000,  # Increased from 10
        "target_fitness": 0.30,  # 30% win rate vs Novice
        "mutation_rate": 0.7,
        "elitism": 2,
    },
    {
        "stage": 2,
        "name": "Economic Development",
        "ai_level": "easy",
        "ai_skill": 3,
        "population": 75,  # Increased from 6
        "generations": 2000,  # Increased from 15
        "target_fitness": 0.20,  # 20% win rate vs Easy
        "mutation_rate": 0.6,
        "elitism": 3,
    },
    {
        "stage": 3,
        "name": "Strategic Mastery",
        "ai_level": "normal",
        "ai_skill": 5,
        "population": 100,  # Increased from 8
        "generations": 3000,  # Increased from 20
        "target_fitness": 0.15,  # 15% win rate vs Normal
        "mutation_rate": 0.5,
        "elitism": 5,
    },
    {
        "stage": 4,
        "name": "Expert Competition",
        "ai_level": "hard",
        "ai_skill": 8,
        "population": 150,  # Increased from 10
        "generations": 5000,  # Increased from 25
        "target_fitness": 0.10,  # 10% win rate vs Hard
        "mutation_rate": 0.4,
        "elitism": 5,
    },
]


class FreeCivEvolver:
    """Evolutionary algorithm for FreeCiv strategies"""

    def __init__(self, population_size: int, mutation_rate: float, elitism: int):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.elitism = elitism
        self.population: List[StrategyGenome] = []
        self.fitness_scores: List[float] = []

    def initialize_population(self):
        """Create initial random population"""
        self.population = [StrategyGenome.random() for _ in range(self.population_size)]

    def evaluate_fitness(self, ai_difficulty: int, games_per_eval: int = 3) -> List[float]:
        """Evaluate fitness of each genome by playing games"""
        fitness_scores = []

        for i, genome in enumerate(self.population):
            wins = 0
            total_score = 0

            for _ in range(games_per_eval):
                game = FreeCivGameEnhanced(
                    ai_difficulty=ai_difficulty,
                    player_strategy=genome,
                    num_opponents=6,  # 7 total civs
                    use_earth_map=True
                )
                result = game.play_game(verbose=False)

                if result['player_won']:
                    wins += 1

                # Score based on performance
                score = 0
                if result['player_won']:
                    score += 1000
                score += result['player_population'] * 2
                score += result['player_tech_level'] * 20
                score += result['player_culture'] * 0.5
                total_score += score

            avg_score = total_score / games_per_eval
            win_rate = wins / games_per_eval
            fitness = avg_score * (1.0 + win_rate)  # Bonus for winning
            fitness_scores.append(fitness)

        return fitness_scores

    def select_parents(self) -> List[StrategyGenome]:
        """Tournament selection"""
        parents = []
        tournament_size = 3

        for _ in range(self.population_size):
            tournament = random.sample(list(zip(self.population, self.fitness_scores)), tournament_size)
            winner = max(tournament, key=lambda x: x[1])[0]
            parents.append(winner)

        return parents

    def crossover(self, parent1: StrategyGenome, parent2: StrategyGenome) -> StrategyGenome:
        """Create offspring from two parents"""
        child = StrategyGenome()

        # Average numeric values
        child.expansion_weight = (parent1.expansion_weight + parent2.expansion_weight) / 2
        child.military_weight = (parent1.military_weight + parent2.military_weight) / 2
        child.economy_weight = (parent1.economy_weight + parent2.economy_weight) / 2
        child.science_weight = (parent1.science_weight + parent2.science_weight) / 2
        child.culture_weight = (parent1.culture_weight + parent2.culture_weight) / 2
        child.defense_weight = (parent1.defense_weight + parent2.defense_weight) / 2
        child.aggression_level = (parent1.aggression_level + parent2.aggression_level) / 2
        child.tax_rate = (parent1.tax_rate + parent2.tax_rate) / 2
        child.alliance_tendency = (parent1.alliance_tendency + parent2.alliance_tendency) / 2
        child.defense_ratio = (parent1.defense_ratio + parent2.defense_ratio) / 2

        # Randomly pick categorical values
        child.tech_path = random.choice([parent1.tech_path, parent2.tech_path])
        child.diplomacy_stance = random.choice([parent1.diplomacy_stance, parent2.diplomacy_stance])
        child.city_spacing = random.choice([parent1.city_spacing, parent2.city_spacing])
        child.max_cities = random.choice([parent1.max_cities, parent2.max_cities])

        return child

    def evolve_generation(self, ai_difficulty: int) -> Dict:
        """Run one generation of evolution"""
        # Evaluate fitness
        self.fitness_scores = self.evaluate_fitness(ai_difficulty)

        # Statistics
        best_fitness = max(self.fitness_scores)
        avg_fitness = sum(self.fitness_scores) / len(self.fitness_scores)
        best_genome = self.population[self.fitness_scores.index(best_fitness)]

        # Elitism - keep best genomes
        elite_indices = sorted(range(len(self.fitness_scores)),
                             key=lambda i: self.fitness_scores[i],
                             reverse=True)[:self.elitism]
        elite = [self.population[i] for i in elite_indices]

        # Selection and reproduction
        parents = self.select_parents()
        new_population = elite.copy()

        while len(new_population) < self.population_size:
            parent1, parent2 = random.sample(parents, 2)
            child = self.crossover(parent1, parent2)
            child.mutate(self.mutation_rate)
            new_population.append(child)

        self.population = new_population[:self.population_size]

        return {
            'best_fitness': best_fitness,
            'avg_fitness': avg_fitness,
            'best_genome': best_genome
        }


def run_curriculum_stage(stage_config: Dict, start_genome: StrategyGenome = None):
    """Run one stage of the curriculum"""
    print("="*80)
    print(f"STAGE {stage_config['stage']}: {stage_config['name']}")
    print("="*80)
    print(f"AI Level: {stage_config['ai_level'].upper()} (skill {stage_config['ai_skill']}/10)")
    print(f"Target: {stage_config['target_fitness']:.0%} win rate")
    print(f"Population: {stage_config['population']} agents")
    print(f"Generations: {stage_config['generations']}")
    print(f"Mutation Rate: {stage_config['mutation_rate']:.1%}")
    print(f"Elitism: {stage_config['elitism']}")
    print()

    # Initialize evolver
    evolver = FreeCivEvolver(
        population_size=stage_config['population'],
        mutation_rate=stage_config['mutation_rate'],
        elitism=stage_config['elitism']
    )

    # Initialize population
    if start_genome:
        # Seed with previous best
        evolver.initialize_population()
        evolver.population[0] = start_genome
    else:
        evolver.initialize_population()

    # Evolution loop
    start_time = time.time()
    best_overall_fitness = 0
    best_overall_genome = None

    for gen in range(stage_config['generations']):
        gen_start = time.time()

        # Evolve one generation
        stats = evolver.evolve_generation(stage_config['ai_skill'])

        # Track best
        if stats['best_fitness'] > best_overall_fitness:
            best_overall_fitness = stats['best_fitness']
            best_overall_genome = stats['best_genome']

        # Progress update every 10 generations
        if gen % 10 == 0 or gen == stage_config['generations'] - 1:
            elapsed = time.time() - start_time
            gen_time = time.time() - gen_start
            remaining_gens = stage_config['generations'] - gen - 1
            eta_seconds = remaining_gens * gen_time if gen > 0 else 0
            eta_hours = eta_seconds / 3600

            # Test best genome
            test_game = FreeCivGameEnhanced(
                ai_difficulty=stage_config['ai_skill'],
                player_strategy=stats['best_genome'],
                num_opponents=6,
                use_earth_map=True
            )
            test_result = test_game.play_game(verbose=False)

            win_icon = "🏆" if test_result['player_won'] else "💀"

            print(f"Gen {gen:4d}/{stage_config['generations']} | "
                  f"Best: {stats['best_fitness']:.1f} | "
                  f"Avg: {stats['avg_fitness']:.1f} | "
                  f"{win_icon} {test_result['player_civ']} vs {test_result['winner']} | "
                  f"Year: {test_result['final_year']} | "
                  f"Pop: {test_result['player_population']} | "
                  f"ETA: {eta_hours:.1f}h")

        # Check if target reached
        # Sample some games to estimate win rate
        if gen % 50 == 0 and gen > 0:
            wins = 0
            test_games = 10
            for _ in range(test_games):
                game = FreeCivGameEnhanced(
                    ai_difficulty=stage_config['ai_skill'],
                    player_strategy=best_overall_genome,
                    num_opponents=6,
                    use_earth_map=True
                )
                result = game.play_game(verbose=False)
                if result['player_won']:
                    wins += 1

            win_rate = wins / test_games
            print(f"  → Win rate check: {win_rate:.1%} (target: {stage_config['target_fitness']:.1%})")

            if win_rate >= stage_config['target_fitness']:
                print(f"\n✅ TARGET REACHED! Win rate {win_rate:.1%} >= {stage_config['target_fitness']:.1%}")
                break

    elapsed = time.time() - start_time
    print()
    print(f"Stage {stage_config['stage']} complete in {elapsed/3600:.1f} hours")
    print(f"Best fitness: {best_overall_fitness:.1f}")
    print()

    return best_overall_genome


def main():
    """Run full curriculum"""
    print("="*80)
    print("🌟 PROMETHEUSSTAR FREECIV CURRICULUM - ENHANCED")
    print("="*80)
    print()
    print("Enhanced Features:")
    print("  🌍 Earth map with historical starting positions")
    print("  🏛️  7 civilizations competing simultaneously")
    print("  🧬 Rich strategy genomes (12+ parameters)")
    print("  📈 1000-5000 generations per stage")
    print("  💪 50-150 agents per population")
    print("  📊 Progress updates every 10 generations")
    print()
    print("="*80)
    print()

    overall_start = time.time()
    best_genome = None

    for stage in CURRICULUM:
        best_genome = run_curriculum_stage(stage, best_genome)

    overall_elapsed = time.time() - overall_start

    print("="*80)
    print("🎉 CURRICULUM COMPLETE!")
    print("="*80)
    print(f"Total time: {overall_elapsed/3600:.1f} hours")
    print()
    print("Final demonstration game:")
    print()

    # Play final demo game with best genome
    final_game = FreeCivGameEnhanced(
        ai_difficulty=8,  # Hardest difficulty
        player_strategy=best_genome,
        num_opponents=6,
        use_earth_map=True
    )
    final_result = final_game.play_game(verbose=True)

    print()
    print("="*80)
    print("PrometheusStar training complete! 🌟")
    print("="*80)


if __name__ == "__main__":
    main()
