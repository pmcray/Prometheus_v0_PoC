#!/usr/bin/env python3
"""
Connect4 Evolution with Strategic Opponents
Demonstrates learning against progressively harder opponents
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from prometheus.smm import EvolutionaryOrchestratorAgent, EvolutionConfig
from prometheus.iee import IntrospectionEvaluationEngine
from prometheus.domain_expert_agent import GamePlayingExpertAgent
from benchmarks.prometheus_bench_v0_2 import PrometheusBenchV02
from benchmarks.strategic_opponents import HeuristicOpponent, MinimaxOpponent

print("=" * 70)
print("🧬 CONNECT4 EVOLUTION - STRATEGIC OPPONENT VERSION")
print("=" * 70)
print("\nThis demo uses a HEURISTIC opponent instead of random.")
print("Expected progression:")
print("  Gen 1: ~10-20% (random agents vs smart opponent)")
print("  Gen 5: ~30-50% (learning basic tactics)")
print("  Gen 10: ~50-70% (strong tactical play)")
print("\n" + "=" * 70 + "\n")

# Configuration
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', None)

CONFIG = EvolutionConfig(
    population_size=10,           # Larger population for diversity
    generations=15,               # More generations
    mutation_rate=0.6,
    elitism_count=2,
    tournament_size=3,
    convergence_threshold=0.70,   # 70% win rate against heuristic opponent
    stagnation_generations=5      # More patience
)

print("⚙️ Configuration:")
print(f"  Population: {CONFIG.population_size}")
print(f"  Generations: {CONFIG.generations}")
print(f"  Target: {CONFIG.convergence_threshold:.0%} win rate vs HeuristicBot")
print(f"  Backend: {'Ollama (GPU)' if not GOOGLE_API_KEY else 'Gemini'}\n")

# Initialize components
print("✓ Initializing components...")
benchmark_suite = PrometheusBenchV02()

# Patch benchmark to use HeuristicOpponent
from benchmarks import connect4_benchmark
original_opponent = connect4_benchmark.RandomOpponent

# Replace with HeuristicOpponent
connect4_benchmark.RandomOpponent = HeuristicOpponent
print("✓ Using HeuristicOpponent (strategic play)\n")

iee = IntrospectionEvaluationEngine(benchmark_suite=benchmark_suite)

smm = EvolutionaryOrchestratorAgent(
    api_key=GOOGLE_API_KEY,
    config=CONFIG,
    prefer_local=True,
    ollama_model="qwen2.5-coder:3b-instruct-q4_K_M"
)

print("=" * 70)
print("🧬 STARTING EVOLUTION")
print("=" * 70)
print("\nNote: Initial agents will struggle (~10-20% win rate)")
print("Watch for steady improvement as they learn tactics!\n")

try:
    best_agent, fitness_history = smm.run_evolution(
        iee_evaluator=iee,
        benchmark_name="GGP-connect4",
        template_class=GamePlayingExpertAgent
    )

    print("\n" + "=" * 70)
    print("🎉 EVOLUTION COMPLETE!")
    print("=" * 70)

    if fitness_history:
        initial_best = fitness_history[0]['best']
        final_best = fitness_history[-1]['best']
        improvement = final_best - initial_best

        print(f"\nInitial Best: {initial_best:.1%}")
        print(f"Final Best:   {final_best:.1%}")
        print(f"Improvement:  +{improvement:.1%}")
        print(f"Generations:  {len(fitness_history)}")

        print("\nGeneration-by-Generation Progress:")
        print("─" * 70)
        print(f"{'Gen':<6} {'Best':<10} {'Mean':<10} {'Worst':<10}")
        print("─" * 70)
        for h in fitness_history:
            print(f"{h['generation']:<6} {h['best']:<10.1%} {h['mean']:<10.1%} {h['worst']:<10.1%}")
        print("─" * 70)

        if final_best >= CONFIG.convergence_threshold:
            print(f"\n🎉 SUCCESS! Reached {final_best:.1%} (target was {CONFIG.convergence_threshold:.0%})")
        else:
            print(f"\n📈 GOOD PROGRESS! Reached {final_best:.1%} (target was {CONFIG.convergence_threshold:.0%})")
            print("   Run longer or increase population for better results.")

    print("\n" + "=" * 70)
    print("💡 KEY INSIGHTS")
    print("=" * 70)
    print("\n✓ Strategic opponent creates learning pressure")
    print("✓ Agents must discover tactics to improve")
    print("✓ Larger population + more generations = better results")
    print("\nNext steps:")
    print("  1. Try MinimaxOpponent for even harder challenge")
    print("  2. Use AdaptiveOpponent to auto-adjust difficulty")
    print("  3. Implement opponent curriculum: Random → Heuristic → Minimax")
    print()

except KeyboardInterrupt:
    print("\n\n⚠️ Evolution interrupted by user")
    sys.exit(1)
except Exception as e:
    print(f"\n\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    # Restore original opponent
    connect4_benchmark.RandomOpponent = original_opponent
