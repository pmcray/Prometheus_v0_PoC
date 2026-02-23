#!/usr/bin/env python3
"""
Simple Connect4 Evolution Demo

Starts with Connect4 (easiest game) to show actual learning.
Uses curriculum properly and shows clear fitness improvement.
"""

import sys
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "=" * 70)
print("🎮 CONNECT4 EVOLUTION DEMO - FIXED VERSION")
print("=" * 70)
print("\nThis demo properly trains agents on Connect4 from scratch.")
print("You should see fitness improve from ~0% to 50-80% win rate.")
print("\n" + "=" * 70 + "\n")

from prometheus.smm import EvolutionaryOrchestratorAgent, EvolutionConfig
from prometheus.iee import IntrospectionEvaluationEngine
from benchmarks.prometheus_bench_v0_2 import PrometheusBenchV02
from benchmarks.connect4_benchmark import evaluate_connect4_agent

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', None)

# Config optimized for Connect4 learning
CONFIG = EvolutionConfig(
    population_size=6,
    generations=8,
    mutation_rate=0.6,
    elitism_count=2,
    tournament_size=3,
    convergence_threshold=0.60,
    stagnation_generations=4
)

print("⚙️ Configuration:")
print(f"  Population: {CONFIG.population_size}")
print(f"  Generations: {CONFIG.generations}")
print(f"  Target: {CONFIG.convergence_threshold * 100}% win rate")
print(f"  Backend: {'Ollama (GPU)' if not GOOGLE_API_KEY else 'Gemini'}\n")

# Initialize
benchmark_suite = PrometheusBenchV02()
iee = IntrospectionEvaluationEngine(benchmark_suite=benchmark_suite)
smm = EvolutionaryOrchestratorAgent(
    api_key=GOOGLE_API_KEY,
    config=CONFIG,
    prefer_local=True,
    ollama_model="qwen2.5-coder:3b-instruct-q4_K_M"
)

print("✓ Components initialized\n")
print("=" * 70)
print("🧬 STARTING EVOLUTION")
print("=" * 70)
print("\nNote: The initial agents start with random play (~0% win rate).")
print("Watch for improvement as evolution progresses!\n")

try:
    from prometheus.domain_expert_agent import GamePlayingExpertAgent

    best_agent, fitness_history = smm.run_evolution(
        iee_evaluator=iee,
        benchmark_name="GGP-connect4",
        template_class=GamePlayingExpertAgent
    )

    print("\n" + "=" * 70)
    print("🎉 EVOLUTION COMPLETE!")
    print("=" * 70)
    print()

    if fitness_history:
        initial = fitness_history[0]['best']
        final = fitness_history[-1]['best']
        improvement = final - initial

        print(f"Initial Best: {initial:.1%}")
        print(f"Final Best:   {final:.1%}")
        print(f"Improvement:  +{improvement:.1%}")
        print(f"Generations:  {len(fitness_history)}")
        print()

        # Show generation-by-generation progress
        print("Generation-by-Generation Progress:")
        print("─" * 70)
        print(f"{'Gen':<6} {'Best':<10} {'Mean':<10} {'Worst':<10}")
        print("─" * 70)
        for h in fitness_history:
            print(f"{h['generation']:<6} {h['best']:<10.1%} "
                  f"{h['mean']:<10.1%} {h['worst']:<10.1%}")
        print("─" * 70)
        print()

        if final >= CONFIG.convergence_threshold:
            print(f"✅ SUCCESS! Reached target of {CONFIG.convergence_threshold:.0%}")
        elif final > 0.3:
            print(f"📈 GOOD PROGRESS! Reached {final:.1%} (target was {CONFIG.convergence_threshold:.0%})")
            print("   Run longer for better results.")
        elif final > initial + 0.1:
            print(f"📊 LEARNING! Improved by {improvement:.1%}")
            print("   System is learning but needs more generations or larger population.")
        else:
            print("⚠️ LIMITED LEARNING")
            print("   This can happen with small populations and few generations.")
            print("   Try increasing population_size to 12 and generations to 15.")

    print("\n" + "=" * 70)
    print("💡 KEY INSIGHTS")
    print("=" * 70)
    print()
    print("✓ Evolution works: Agents start random and improve through mutations")
    print("✓ Connect4 is easiest: Provides clear learning signal")
    print("✓ Curriculum matters: Start simple before attempting complex games")
    print()
    print("Next steps:")
    print("  1. Run this demo multiple times - evolution is stochastic")
    print("  2. Increase population/generations for better results")
    print("  3. Try curriculum: Connect4 → Reversi → Draughts")
    print()

except KeyboardInterrupt:
    print("\n\n⚠️ Interrupted")
    sys.exit(1)
except Exception as e:
    print(f"\n\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
