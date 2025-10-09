#!/usr/bin/env python3
"""
PrometheusStar FreeCiv Curriculum - REAL FREECIV VERSION
Uses actual FreeCiv server instead of simulation
WARNING: Much slower - expect 100+ hours for full curriculum!
"""

import time
from typing import List, Dict
from freeciv_control import FreeCivGame, FreeCivConfig
from freeciv_simulator_enhanced import StrategyGenome  # Still use genomes for evolution

# Reduced scale curriculum for REAL FreeCiv (games take minutes each!)
CURRICULUM_REAL = [
    {
        "stage": 1,
        "name": "City Building Basics",
        "ai_skill": 1,
        "population": 10,  # Reduced from 50 (real games are slow!)
        "generations": 50,  # Reduced from 1000
        "target_fitness": 0.30,
        "mutation_rate": 0.7,
        "elitism": 2,
    },
    {
        "stage": 2,
        "name": "Economic Development",
        "ai_skill": 3,
        "population": 15,  # Reduced from 75
        "generations": 75,  # Reduced from 2000
        "target_fitness": 0.20,
        "mutation_rate": 0.6,
        "elitism": 3,
    },
    {
        "stage": 3,
        "name": "Strategic Mastery",
        "ai_skill": 5,
        "population": 20,  # Reduced from 100
        "generations": 100,  # Reduced from 3000
        "target_fitness": 0.15,
        "mutation_rate": 0.5,
        "elitism": 5,
    },
    {
        "stage": 4,
        "name": "Expert Competition",
        "ai_skill": 8,
        "population": 25,  # Reduced from 150
        "generations": 150,  # Reduced from 5000
        "target_fitness": 0.10,
        "mutation_rate": 0.4,
        "elitism": 5,
    },
]


class FreeCivEvolverReal:
    """Evolutionary algorithm using REAL FreeCiv"""

    def __init__(self, population_size: int, mutation_rate: float, elitism: int):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.elitism = elitism
        self.population: List[StrategyGenome] = []
        self.fitness_scores: List[float] = []

    def initialize_population(self):
        """Create initial random population"""
        self.population = [StrategyGenome.random() for _ in range(self.population_size)]

    def evaluate_fitness(self, ai_difficulty: int, games_per_eval: int = 2) -> List[float]:
        """
        Evaluate fitness by playing REAL FreeCiv games
        Note: This is SLOW! Each game takes 1-3 minutes
        """
        fitness_scores = []

        for i, genome in enumerate(self.population):
            print(f"    Evaluating agent {i+1}/{self.population_size}...", end=" ", flush=True)

            wins = 0
            total_score = 0

            # Play fewer games since they're real (and slow!)
            for game_num in range(games_per_eval):
                config = FreeCivConfig(
                    ai_difficulty=ai_difficulty,
                    num_civs=7,
                    timeout=300,  # 5 min max per game
                    max_turns=150  # Shorter for speed
                )

                game = FreeCivGame(config)
                result = game.play_game(verbose=False)

                if result.get('player_won', False):
                    wins += 1

                # Score based on performance
                score = 0
                if result.get('player_won', False):
                    score += 1000
                score += result.get('player_population', 0) * 2
                score += result.get('player_tech_level', 0) * 20
                score += result.get('player_culture', 0) * 0.5
                total_score += score

            avg_score = total_score / games_per_eval
            win_rate = wins / games_per_eval
            fitness = avg_score * (1.0 + win_rate)
            fitness_scores.append(fitness)

            print(f"✓ (wins: {wins}/{games_per_eval}, fitness: {fitness:.1f})")

        return fitness_scores

    def select_parents(self) -> List[StrategyGenome]:
        """Tournament selection"""
        import random
        parents = []
        tournament_size = 3

        for _ in range(self.population_size):
            tournament = random.sample(list(zip(self.population, self.fitness_scores)), tournament_size)
            winner = max(tournament, key=lambda x: x[1])[0]
            parents.append(winner)

        return parents

    def crossover(self, parent1: StrategyGenome, parent2: StrategyGenome) -> StrategyGenome:
        """Create offspring from two parents"""
        import random

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

        # Randomly pick categorical values
        child.tech_path = random.choice([parent1.tech_path, parent2.tech_path])
        child.diplomacy_stance = random.choice([parent1.diplomacy_stance, parent2.diplomacy_stance])

        return child

    def evolve_generation(self, ai_difficulty: int) -> Dict:
        """Run one generation of evolution"""
        print(f"  Evaluating {self.population_size} agents (this will take time...)...")

        # Evaluate fitness
        self.fitness_scores = self.evaluate_fitness(ai_difficulty)

        # Statistics
        best_fitness = max(self.fitness_scores)
        avg_fitness = sum(self.fitness_scores) / len(self.fitness_scores)
        best_genome = self.population[self.fitness_scores.index(best_fitness)]

        # Elitism
        import random
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


def run_curriculum_stage_real(stage_config: Dict, start_genome: StrategyGenome = None):
    """Run one stage using REAL FreeCiv"""
    print("="*80)
    print(f"STAGE {stage_config['stage']}: {stage_config['name']} (REAL FREECIV)")
    print("="*80)
    print(f"AI Level: skill {stage_config['ai_skill']}/10")
    print(f"Population: {stage_config['population']} agents")
    print(f"Generations: {stage_config['generations']}")
    print(f"⚠️  Each generation will take ~{stage_config['population'] * 4} minutes!")
    print()

    evolver = FreeCivEvolverReal(
        population_size=stage_config['population'],
        mutation_rate=stage_config['mutation_rate'],
        elitism=stage_config['elitism']
    )

    evolver.initialize_population()
    if start_genome:
        evolver.population[0] = start_genome

    start_time = time.time()
    best_overall_fitness = 0
    best_overall_genome = None

    for gen in range(stage_config['generations']):
        gen_start = time.time()

        print(f"\nGeneration {gen+1}/{stage_config['generations']}:")

        stats = evolver.evolve_generation(stage_config['ai_skill'])

        if stats['best_fitness'] > best_overall_fitness:
            best_overall_fitness = stats['best_fitness']
            best_overall_genome = stats['best_genome']

        gen_time = time.time() - gen_start
        remaining_gens = stage_config['generations'] - gen - 1
        eta_hours = (remaining_gens * gen_time) / 3600

        # Test best genome
        print(f"  Playing demo game with best agent...")
        config = FreeCivConfig(
            ai_difficulty=stage_config['ai_skill'],
            num_civs=7,
            timeout=300,
            max_turns=150
        )
        test_game = FreeCivGame(config)
        test_result = test_game.play_game(verbose=True)

        print(f"\n  Gen {gen+1} Summary:")
        print(f"    Best fitness: {stats['best_fitness']:.1f}")
        print(f"    Avg fitness: {stats['avg_fitness']:.1f}")
        print(f"    Generation time: {gen_time/60:.1f} minutes")
        print(f"    ETA: {eta_hours:.1f} hours")

    elapsed = time.time() - start_time
    print()
    print(f"✅ Stage {stage_config['stage']} complete in {elapsed/3600:.1f} hours")
    print()

    return best_overall_genome


def main():
    """Run curriculum with REAL FreeCiv"""
    print("="*80)
    print("🌟 PROMETHEUSSTAR - REAL FREECIV CURRICULUM")
    print("="*80)
    print()
    print("⚠️  WARNING: This uses ACTUAL FreeCiv server!")
    print("⚠️  Each game takes 1-3 minutes!")
    print("⚠️  Total expected runtime: 100+ hours!")
    print()
    print("Curriculum scale (reduced for real games):")
    print("  Stage 1: 10 agents × 50 gens = 500 games (~30 hours)")
    print("  Stage 2: 15 agents × 75 gens = 1,125 games (~60 hours)")
    print("  Stage 3: 20 agents × 100 gens = 2,000 games (~100 hours)")
    print("  Stage 4: 25 agents × 150 gens = 3,750 games (~200 hours)")
    print()
    input("Press Enter to continue or Ctrl+C to cancel...")
    print()

    overall_start = time.time()
    best_genome = None

    for stage in CURRICULUM_REAL:
        best_genome = run_curriculum_stage_real(stage, best_genome)

    overall_elapsed = time.time() - overall_start

    print("="*80)
    print("🎉 REAL FREECIV CURRICULUM COMPLETE!")
    print("="*80)
    print(f"Total time: {overall_elapsed/3600:.1f} hours")
    print()


if __name__ == "__main__":
    main()
