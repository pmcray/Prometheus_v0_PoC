#!/usr/bin/env python3
"""
PrometheusStar - MicroRTS Demo
Demonstrates curriculum learning on RTS games

This is the quick proof-of-concept version using MicroRTS:
- Fast training (hours instead of days)
- Progressive curriculum (Random → Passive → Rush → Mixed AI)
- Demonstrates PrometheusStar advantages over AlphaStar
"""

import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import Prometheus components
from prometheus.generalist_planner import GeneralistPlannerAgent
from prometheus.smm import EvolutionaryOrchestratorAgent, EvolutionConfig
from prometheus.iee import IntrospectionEvaluationEngine
from prometheus.domain_expert_agent import GamePlayingExpertAgent
from benchmarks.prometheus_bench_v0_2 import PrometheusBenchV02
from benchmarks.microrts_benchmark import (
    MicroRTSBenchmark,
    MICRORTS_CURRICULUM,
    get_microrts_opponent,
    estimate_microrts_training_time,
    test_microrts_installation
)

# Try to import visualization
try:
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    logger.warning("matplotlib not available - visualization disabled")
    MATPLOTLIB_AVAILABLE = False


# Curriculum configuration
CURRICULUM = [
    {
        "stage": 1,
        "name": "Random Baseline",
        "opponent": "random",
        "population": 4,
        "generations": 5,
        "target_fitness": 0.80,
        "mutation_rate": 0.7,
        "elitism": 1,
    },
    {
        "stage": 2,
        "name": "Resource Management",
        "opponent": "passive",
        "population": 6,
        "generations": 8,
        "target_fitness": 0.65,
        "mutation_rate": 0.6,
        "elitism": 1,
    },
    {
        "stage": 3,
        "name": "Tactical Response",
        "opponent": "rush",
        "population": 8,
        "generations": 10,
        "target_fitness": 0.50,
        "mutation_rate": 0.5,
        "elitism": 2,
    },
    {
        "stage": 4,
        "name": "Strategic Depth",
        "opponent": "mixed",
        "population": 10,
        "generations": 12,
        "target_fitness": 0.40,
        "mutation_rate": 0.4,
        "elitism": 2,
    },
]


def print_curriculum_overview():
    """Print curriculum overview"""
    print("=" * 70)
    print("PROMETHEUSSTAR - MicroRTS CURRICULUM")
    print("=" * 70)
    print("\n4-Stage Progressive Difficulty Training:\n")

    for stage in CURRICULUM:
        time_est = estimate_microrts_training_time(
            population_size=stage['population'],
            generations=stage['generations'],
            games_per_eval=5,
            seconds_per_game=30
        )

        print(f"Stage {stage['stage']}: {stage['name']}")
        print(f"  Opponent: {stage['opponent']}")
        print(f"  Target: {stage['target_fitness']:.0%} win rate")
        print(f"  Training: {stage['population']} agents × {stage['generations']} gens")
        print(f"  Est. time: {time_est['total_hours']:.1f} hours ({time_est['total_minutes']:.0f} min)")
        print()

    total_time = sum([
        estimate_microrts_training_time(
            s['population'], s['generations'], 5, 30
        )['total_hours'] for s in CURRICULUM
    ])
    print(f"Total curriculum time: {total_time:.1f} hours ({total_time/24:.1f} days)")
    print("=" * 70)


def run_curriculum_stage(
    stage_config: Dict[str, Any],
    planner: GeneralistPlannerAgent,
    iee: IntrospectionEvaluationEngine,
    api_key: str = None
) -> Dict[str, Any]:
    """
    Run a single curriculum stage

    Args:
        stage_config: Stage configuration dictionary
        planner: GeneralistPlanner instance
        iee: IEE instance
        api_key: Google API key (optional)

    Returns:
        Results dictionary
    """
    print("\n" + "=" * 70)
    print(f"STAGE {stage_config['stage']}: {stage_config['name']}")
    print("=" * 70)
    print(f"Opponent: {stage_config['opponent']}")
    print(f"Target: {stage_config['target_fitness']:.0%}")
    print(f"Config: {stage_config['population']} agents × {stage_config['generations']} gens")
    print()

    # Create evolution config
    config = EvolutionConfig(
        population_size=stage_config['population'],
        generations=stage_config['generations'],
        mutation_rate=stage_config['mutation_rate'],
        elitism_count=stage_config['elitism'],
        tournament_size=3,
        convergence_threshold=stage_config['target_fitness'],
        stagnation_generations=max(3, stage_config['generations'] // 4)
    )

    # Create SMM
    smm = EvolutionaryOrchestratorAgent(
        api_key=api_key,
        config=config,
        prefer_local=True,  # Prefer local Ollama on Jetson
    )

    print("🚀 Starting evolution...\n")

    try:
        # Run evolution
        best_agent, fitness_history = smm.run_evolution(
            iee_evaluator=iee,
            benchmark_name="MicroRTS",  # Custom benchmark name
            template_class=GamePlayingExpertAgent
        )

        # Results
        result = {
            'stage': stage_config['stage'],
            'name': stage_config['name'],
            'opponent': stage_config['opponent'],
            'best_fitness': smm.best_fitness,
            'target_fitness': stage_config['target_fitness'],
            'achieved': smm.best_fitness >= stage_config['target_fitness'],
            'fitness_history': fitness_history
        }

        print(f"\n{'='*70}")
        print(f"STAGE {stage_config['stage']} COMPLETE")
        print(f"{'='*70}")
        print(f"Final fitness: {smm.best_fitness:.1%}")
        print(f"Target fitness: {stage_config['target_fitness']:.1%}")
        print(f"Status: {'✅ ACHIEVED' if result['achieved'] else '⏸️ PARTIAL'}")
        print()

        return result

    except Exception as e:
        logger.error(f"Error in stage {stage_config['stage']}: {e}")
        import traceback
        traceback.print_exc()
        return None


def visualize_results(curriculum_results: List[Dict[str, Any]]):
    """Create visualization of curriculum results"""
    if not MATPLOTLIB_AVAILABLE:
        logger.warning("Matplotlib not available - skipping visualization")
        return

    print("\n📊 Creating visualization...")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Plot 1: Learning curves for each stage
    stage_colors = ['green', 'blue', 'purple', 'red']

    for result in curriculum_results:
        if result and 'fitness_history' in result:
            stage_num = result['stage']
            fitness_history = result['fitness_history']

            generations = list(range(len(fitness_history)))
            best_fitness = [h['best'] for h in fitness_history]

            color = stage_colors[stage_num - 1] if stage_num <= len(stage_colors) else 'gray'
            label = f"Stage {stage_num}: {result['name']}"

            ax1.plot(generations, best_fitness, f'{color}-o',
                    label=label, linewidth=2, markersize=4)

    ax1.set_xlabel('Generation (within stage)', fontsize=11)
    ax1.set_ylabel('Fitness (Win Rate)', fontsize=11)
    ax1.set_title('MicroRTS Curriculum Learning Progress', fontsize=13, fontweight='bold')
    ax1.legend(fontsize=9, loc='best')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(-0.05, 1.0)

    # Plot 2: Stage comparison
    stages = [r['stage'] for r in curriculum_results if r]
    final_fitness = [r['best_fitness'] for r in curriculum_results if r]
    target_fitness = [r['target_fitness'] for r in curriculum_results if r]
    stage_names = [r['name'] for r in curriculum_results if r]

    x = np.arange(len(stages))
    width = 0.35

    bars1 = ax2.bar(x - width/2, final_fitness, width, label='Achieved', color='steelblue')
    bars2 = ax2.bar(x + width/2, target_fitness, width, label='Target', color='lightcoral')

    ax2.set_xlabel('Curriculum Stage', fontsize=11)
    ax2.set_ylabel('Win Rate', fontsize=11)
    ax2.set_title('Stage Performance: Achieved vs Target', fontsize=13, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"S{s}" for s in stages], fontsize=9)
    ax2.legend(fontsize=10)
    ax2.grid(True, axis='y', alpha=0.3)
    ax2.set_ylim(0, 1.0)

    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.0%}', ha='center', va='bottom', fontsize=8)

    plt.tight_layout()

    # Save
    output_file = Path("prometheusstar_microrts_results.png")
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✓ Visualization saved to: {output_file}")

    plt.close()


def print_summary_table(curriculum_results: List[Dict[str, Any]]):
    """Print summary table of all stages"""
    print("\n" + "=" * 70)
    print("PROMETHEUSSTAR CURRICULUM SUMMARY")
    print("=" * 70)

    print(f"{'Stage':<8} {'Opponent':<15} {'Final':<12} {'Target':<12} {'Status':<15}")
    print("-" * 70)

    for result in curriculum_results:
        if result:
            status = "✅ ACHIEVED" if result['achieved'] else "⏸️ PARTIAL"
            print(f"{result['stage']:<8} {result['opponent']:<15} "
                  f"{result['best_fitness']:<12.1%} {result['target_fitness']:<12.1%} {status:<15}")

    print("=" * 70)


def main():
    """Main execution"""
    print("\n" + "=" * 70)
    print("🧬 PROMETHEUSSTAR - MicroRTS Curriculum Learning Demo")
    print("=" * 70)

    # Step 1: Check MicroRTS installation
    print("\n📦 Checking MicroRTS installation...")
    if not test_microrts_installation():
        print("\n❌ MicroRTS not installed. Install with:")
        print("   pip install gym-microrts")
        sys.exit(1)

    # Step 2: Display curriculum
    print_curriculum_overview()

    # Step 3: Initialize components
    print("\n🔧 Initializing Prometheus components...")

    planner = GeneralistPlannerAgent()
    print("✓ GeneralistPlanner initialized")

    benchmark_suite = PrometheusBenchV02()
    print("✓ Benchmark suite initialized")

    iee = IntrospectionEvaluationEngine(benchmark_suite=benchmark_suite)
    print("✓ IEE initialized")

    # Check for API key (optional for Ollama)
    import os
    api_key = os.getenv('GOOGLE_API_KEY')
    if api_key:
        print("✓ Google API key found")
    else:
        print("⚠️  No Google API key - using Ollama only")

    # Step 4: Run curriculum
    print("\n" + "=" * 70)
    print("🚀 STARTING CURRICULUM TRAINING")
    print("=" * 70)

    curriculum_results = []

    for stage_config in CURRICULUM:
        result = run_curriculum_stage(
            stage_config=stage_config,
            planner=planner,
            iee=iee,
            api_key=api_key
        )

        if result:
            curriculum_results.append(result)
        else:
            logger.error(f"Stage {stage_config['stage']} failed - stopping curriculum")
            break

    # Step 5: Results
    if curriculum_results:
        print_summary_table(curriculum_results)
        visualize_results(curriculum_results)

        print("\n" + "=" * 70)
        print("🎉 PROMETHEUSSTAR MICRORTS CURRICULUM COMPLETE!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. ✅ MicroRTS proof-of-concept complete")
        print("2. 📊 Review results in prometheusstar_microrts_results.png")
        print("3. 🎮 Try OpenRA for impressive demo (see PROMETHEUSSTAR_RTS_OPTIONS.md)")
        print("4. 📝 Publish results showing curriculum learning efficiency")
        print()

    else:
        print("\n❌ Curriculum training failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
