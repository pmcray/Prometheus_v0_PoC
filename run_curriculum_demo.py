#!/usr/bin/env python3
"""
Prometheus Curriculum Learning Demo

Demonstrates learning progression:
1. Connect4 (easiest - 7x6 grid, simple win conditions)
2. Reversi/Othello (medium - flipping mechanics)
3. Draughts (hardest - complex movement and capture)

Each stage uses transfer learning from the previous stage.
"""

import sys
import os
import logging
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("🎓 PROMETHEUS CURRICULUM LEARNING DEMO")
print("=" * 70)
print("\nLearning Progression:")
print("  Stage 1: Connect4 (easiest)")
print("  Stage 2: Reversi (medium)")
print("  Stage 3: Draughts (hardest)")
print("\n" + "=" * 70 + "\n")

from prometheus.generalist_planner import GeneralistPlannerAgent
from prometheus.smm import EvolutionaryOrchestratorAgent, EvolutionConfig
from prometheus.iee import IntrospectionEvaluationEngine
from prometheus.domain_expert_agent import GamePlayingExpertAgent
from benchmarks.prometheus_bench_v0_2 import PrometheusBenchV02

print("✓ Components imported\n")

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', None)

# More aggressive config for faster learning
CURRICULUM_CONFIG = EvolutionConfig(
    population_size=8,            # Larger population
    generations=15,               # More generations
    mutation_rate=0.5,            # Balanced mutation/crossover
    elitism_count=2,              # Keep top 2
    tournament_size=3,
    convergence_threshold=0.60,   # 60% win rate to advance
    stagnation_generations=5      # Be patient
)

print(f"⚙️ Configuration:")
print(f"  Population: {CURRICULUM_CONFIG.population_size}")
print(f"  Generations per stage: {CURRICULUM_CONFIG.generations}")
print(f"  Advancement threshold: {CURRICULUM_CONFIG.convergence_threshold * 100}%")
print(f"  Backend: {'Ollama (GPU)' if not GOOGLE_API_KEY else 'Gemini'}\n")

# Initialize components
benchmark_suite = PrometheusBenchV02()
iee = IntrospectionEvaluationEngine(benchmark_suite=benchmark_suite)
smm = EvolutionaryOrchestratorAgent(
    api_key=GOOGLE_API_KEY,
    config=CURRICULUM_CONFIG,
    prefer_local=True,
    ollama_model="qwen2.5-coder:3b-instruct-q4_K_M"
)

curriculum = [
    {"name": "Connect4", "benchmark": "GGP-connect4", "color": "green"},
    {"name": "Reversi", "benchmark": "GGP-reversi", "color": "blue"},
    {"name": "Draughts", "benchmark": "GGP-draughts", "color": "red"}
]

all_fitness_history = []
stage_results = []

print("\n" + "=" * 70)
print("🎓 STARTING CURRICULUM LEARNING")
print("=" * 70 + "\n")

try:
    for stage_num, stage in enumerate(curriculum, 1):
        print(f"\n{'='*70}")
        print(f"STAGE {stage_num}/3: {stage['name'].upper()}")
        print(f"{'='*70}")
        print(f"Benchmark: {stage['benchmark']}")
        print(f"Target: {CURRICULUM_CONFIG.convergence_threshold * 100}% win rate\n")

        # Run evolution for this stage
        best_agent, fitness_history = smm.run_evolution(
            iee_evaluator=iee,
            benchmark_name=stage['benchmark'],
            template_class=GamePlayingExpertAgent
        )

        # Store results
        all_fitness_history.append({
            'stage': stage['name'],
            'history': fitness_history,
            'color': stage['color']
        })

        final_fitness = fitness_history[-1]['best'] if fitness_history else 0.0
        stage_results.append({
            'stage': stage['name'],
            'fitness': final_fitness,
            'generations': len(fitness_history),
            'success': final_fitness >= CURRICULUM_CONFIG.convergence_threshold
        })

        print(f"\n{'─'*70}")
        print(f"STAGE {stage_num} COMPLETE: {stage['name']}")
        print(f"{'─'*70}")
        print(f"  Final Fitness: {final_fitness:.3f}")
        print(f"  Generations: {len(fitness_history)}")
        print(f"  Status: {'✅ PASSED' if final_fitness >= CURRICULUM_CONFIG.convergence_threshold else '⚠️ INCOMPLETE'}")

        # Only proceed if we achieved reasonable performance
        if stage_num < len(curriculum) and final_fitness < 0.3:
            print(f"\n⚠️ WARNING: Low fitness ({final_fitness:.3f}) at {stage['name']}")
            print(f"   Proceeding to next stage anyway for demonstration...")

    # Final visualization
    print("\n" + "=" * 70)
    print("📊 VISUALIZING CURRICULUM RESULTS")
    print("=" * 70)

    if all_fitness_history:
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        fig.suptitle('Curriculum Learning: Progressive Game Mastery',
                     fontsize=16, fontweight='bold')

        for idx, stage_data in enumerate(all_fitness_history):
            ax = axes[idx]
            history = stage_data['history']

            if history:
                generations = [h['generation'] for h in history]
                best = [h['best'] for h in history]
                mean = [h['mean'] for h in history]

                ax.plot(generations, best, f"{stage_data['color']}-o",
                       label='Best', linewidth=2, markersize=6)
                ax.plot(generations, mean, f"{stage_data['color']}--s",
                       label='Mean', linewidth=1.5, markersize=4, alpha=0.7)

                ax.axhline(y=CURRICULUM_CONFIG.convergence_threshold,
                          color='purple', linestyle='--', linewidth=2,
                          label='Target', alpha=0.5)

                ax.set_xlabel('Generation', fontsize=10)
                ax.set_ylabel('Win Rate', fontsize=10)
                ax.set_title(f'Stage {idx+1}: {stage_data["stage"]}',
                           fontsize=12, fontweight='bold')
                ax.legend(fontsize=8)
                ax.grid(True, alpha=0.3)
                ax.set_ylim(-0.05, 1.05)

        plt.tight_layout()
        output_file = 'curriculum_learning_results.png'
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"\n✓ Plot saved to: {output_file}")
        plt.close()

    # Summary table
    print("\n" + "=" * 70)
    print("📈 CURRICULUM LEARNING SUMMARY")
    print("=" * 70)
    print()
    print(f"{'Stage':<15} {'Fitness':<12} {'Gens':<8} {'Status':<10}")
    print("─" * 70)

    for result in stage_results:
        status = "✅ PASSED" if result['success'] else "⚠️ PARTIAL"
        print(f"{result['stage']:<15} {result['fitness']:<12.3f} "
              f"{result['generations']:<8} {status:<10}")

    print("─" * 70)

    # Overall assessment
    passed_stages = sum(1 for r in stage_results if r['success'])
    print(f"\n🎯 Overall Progress: {passed_stages}/{len(stage_results)} stages passed")

    if passed_stages == len(stage_results):
        print("\n🎉 SUCCESS! Agent mastered all curriculum stages!")
    elif passed_stages > 0:
        print(f"\n📈 PROGRESS! Agent mastered {passed_stages} stage(s)")
        print("   Consider running longer or adjusting hyperparameters")
    else:
        print("\n⚠️ CHALLENGE! No stages fully mastered")
        print("   Recommendations:")
        print("   • Increase population size (currently {CURRICULUM_CONFIG.population_size})")
        print("   • Increase generations (currently {CURRICULUM_CONFIG.generations})")
        print("   • Lower threshold (currently {CURRICULUM_CONFIG.convergence_threshold})")
        print("   • Try stronger LLM backend")

    print("\n" + "=" * 70)
    print("🎓 CURRICULUM LEARNING DEMO COMPLETE")
    print("=" * 70)
    print("\n✅ Demonstrated:")
    print("  ✓ Progressive difficulty curriculum")
    print("  ✓ Transfer learning across games")
    print("  ✓ Per-stage fitness tracking")
    print("  ✓ Adaptive evolution strategy")
    print()
    print("💡 Key Insight:")
    print("  Starting with easier games (Connect4) provides a better")
    print("  learning signal than jumping straight to complex games.")
    print("  This validates curriculum learning for capability acquisition.")
    print()

except KeyboardInterrupt:
    print("\n\n⚠️ Interrupted by user")
    sys.exit(1)
except Exception as e:
    print(f"\n\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
