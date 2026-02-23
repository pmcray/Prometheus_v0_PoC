#!/usr/bin/env python3
"""
Quick test of enhanced curriculum (just first 3 generations)
"""

from run_freeciv_curriculum_enhanced import FreeCivEvolver, CURRICULUM
from freeciv_simulator_enhanced import StrategyGenome

# Use minimal test config
test_config = {
    "stage": 1,
    "name": "City Building Basics (TEST)",
    "ai_level": "novice",
    "ai_skill": 1,
    "population": 10,  # Small for testing
    "generations": 3,  # Just 3 generations
    "target_fitness": 0.30,
    "mutation_rate": 0.7,
    "elitism": 2,
}

print("="*80)
print("🌟 TESTING ENHANCED FREECIV CURRICULUM")
print("="*80)
print()
print("Quick test with:")
print(f"  Population: {test_config['population']} agents")
print(f"  Generations: {test_config['generations']}")
print(f"  AI Difficulty: {test_config['ai_skill']}/10")
print()

# Initialize evolver
evolver = FreeCivEvolver(
    population_size=test_config['population'],
    mutation_rate=test_config['mutation_rate'],
    elitism=test_config['elitism']
)

# Initialize population
evolver.initialize_population()

# Run a few generations
for gen in range(test_config['generations']):
    print(f"Generation {gen}...")

    stats = evolver.evolve_generation(test_config['ai_skill'])

    # Show example game
    from freeciv_simulator_enhanced import FreeCivGameEnhanced

    test_game = FreeCivGameEnhanced(
        ai_difficulty=test_config['ai_skill'],
        player_strategy=stats['best_genome'],
        num_opponents=6,
        use_earth_map=True
    )
    result = test_game.play_game(verbose=False)

    win_icon = "🏆" if result['player_won'] else "💀"

    print(f"  Gen {gen} | Best: {stats['best_fitness']:.1f} | Avg: {stats['avg_fitness']:.1f}")
    print(f"  {win_icon} {result['player_civ']} vs {result['winner']}")
    print(f"  Year: {result['final_year']} | Pop: {result['player_population']} | Tech: {result['player_tech_level']}")
    print()

print("="*80)
print("✅ Enhanced curriculum is working!")
print()
print("For the full curriculum with 11,000 generations, run:")
print("  python run_freeciv_curriculum_enhanced.py")
print()
print("Or use the Jupyter notebook:")
print("  jupyter notebook PrometheusStar_FreeCiv_ENHANCED.ipynb")
print("="*80)
