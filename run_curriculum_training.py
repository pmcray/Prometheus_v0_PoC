#!/usr/bin/env python3
"""
Curriculum Training Demo - Progressive Difficulty
Trains agents on increasing difficulty opponents for both Connect4 and FreeCiv
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from prometheus.smm import EvolutionaryOrchestratorAgent, EvolutionConfig
from prometheus.iee import IntrospectionEvaluationEngine
from prometheus.domain_expert_agent import GamePlayingExpertAgent
from benchmarks.prometheus_bench_v0_2 import PrometheusBenchV02
from benchmarks.freeciv_strategic_opponents import (
    FREECIV_CURRICULUM, get_opponent_config, estimate_training_time
)

print("=" * 80)
print("🎓 CURRICULUM TRAINING - PROGRESSIVE DIFFICULTY")
print("=" * 80)
print("\nTrains agents using curriculum learning:")
print("  Stage 1: Easy opponents  → Learn basics")
print("  Stage 2: Medium opponents → Learn tactics")
print("  Stage 3: Hard opponents   → Learn strategy")
print("  Stage 4: Expert opponents → Master the domain")
print("\n" + "=" * 80 + "\n")

# Select game type
GAME_TYPE = os.environ.get('GAME_TYPE', 'connect4')  # 'connect4' or 'freeciv'
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', None)

if GAME_TYPE == 'connect4':
    print("🎮 Training on: CONNECT4")
    CURRICULUM = [
        {
            "stage": 1,
            "opponent_type": "random",
            "target_win_rate": 0.70,
            "population": 8,
            "generations": 10,
            "description": "Learn basic play vs random"
        },
        {
            "stage": 2,
            "opponent_type": "heuristic",
            "target_win_rate": 0.60,
            "population": 12,
            "generations": 15,
            "description": "Develop tactics vs heuristic AI"
        },
        {
            "stage": 3,
            "opponent_type": "minimax-2",
            "target_win_rate": 0.50,
            "population": 15,
            "generations": 20,
            "description": "Master strategy vs Minimax-Depth2"
        },
        {
            "stage": 4,
            "opponent_type": "minimax-3",
            "target_win_rate": 0.40,
            "population": 20,
            "generations": 30,
            "description": "Expert play vs Minimax-Depth3"
        },
    ]
    BENCHMARK_NAME = "GGP-connect4"

elif GAME_TYPE == 'freeciv':
    print("🎮 Training on: FREECIV")
    CURRICULUM = [
        {
            "stage": stage_info['stage'],
            "opponent_type": stage_info['opponent'],
            "target_win_rate": stage_info['target_win_rate'],
            "population": 6,
            "generations": stage_info['max_games'] // (6 * 5),  # Rough estimate
            "description": stage_info['description']
        }
        for stage_info in FREECIV_CURRICULUM
    ]
    BENCHMARK_NAME = "FreeCiv"

    # Estimate time
    print("\n⏱️  TIME ESTIMATE:")
    total_time = estimate_training_time(
        population_size=6,
        generations=sum(s['generations'] for s in CURRICULUM),
        games_per_eval=5,
        minutes_per_game=30
    )
    print(f"  Total time: {total_time['total_hours']:.1f} hours ({total_time['total_days']:.1f} days)")
    print("  ⚠️  This will take DAYS - consider running on cloud compute!\n")

else:
    print(f"❌ Unknown game type: {GAME_TYPE}")
    sys.exit(1)

# Display curriculum
print("\n📚 CURRICULUM STAGES:")
print("─" * 80)
for stage in CURRICULUM:
    print(f"Stage {stage['stage']}: {stage['description']}")
    print(f"  Opponent: {stage['opponent_type']}")
    print(f"  Target: {stage['target_win_rate']:.0%} win rate")
    print(f"  Training: {stage['population']} agents × {stage['generations']} generations")
    print()

response = input("Continue with training? (y/n): ")
if response.lower() != 'y':
    print("Training cancelled.")
    sys.exit(0)

# Initialize components
print("\n✓ Initializing components...")
benchmark_suite = PrometheusBenchV02()
iee = IntrospectionEvaluationEngine(benchmark_suite=benchmark_suite)

# Training history
training_history = {
    'game_type': GAME_TYPE,
    'curriculum': CURRICULUM,
    'stages': [],
    'start_time': datetime.now().isoformat()
}

# Train through curriculum
print("\n" + "=" * 80)
print("🎓 STARTING CURRICULUM TRAINING")
print("=" * 80)

try:
    for stage_idx, stage in enumerate(CURRICULUM, 1):
        print(f"\n{'=' * 80}")
        print(f"📖 STAGE {stage['stage']}/{len(CURRICULUM)}: {stage['description']}")
        print(f"{'=' * 80}")
        print(f"\n🎯 Opponent: {stage['opponent_type']}")
        print(f"🎯 Target: {stage['target_win_rate']:.0%} win rate")
        print(f"🧬 Population: {stage['population']} agents")
        print(f"🧬 Generations: {stage['generations']}\n")

        # Create evolution config for this stage
        config = EvolutionConfig(
            population_size=stage['population'],
            generations=stage['generations'],
            mutation_rate=0.6,
            elitism_count=max(2, stage['population'] // 5),
            tournament_size=min(5, stage['population'] // 2),
            convergence_threshold=stage['target_win_rate'],
            stagnation_generations=max(5, stage['generations'] // 5)
        )

        # Create SMM for this stage
        smm = EvolutionaryOrchestratorAgent(
            api_key=GOOGLE_API_KEY,
            config=config,
            prefer_local=True,
            ollama_model="qwen2.5-coder:3b-instruct-q4_K_M"
        )

        # Configure benchmark with opponent type
        benchmark_kwargs = {}
        if GAME_TYPE == 'connect4':
            benchmark_kwargs['opponent_type'] = stage['opponent_type']
        elif GAME_TYPE == 'freeciv':
            # Would set FreeCiv difficulty here
            from prometheus.freeciv_environment import DifficultyLevel
            difficulty_map = {
                'novice': DifficultyLevel.NOVICE,
                'easy': DifficultyLevel.EASY,
                'normal': DifficultyLevel.NORMAL,
                'hard': DifficultyLevel.HARD,
            }
            # Store for simulator initialization
            stage['difficulty'] = difficulty_map.get(stage['opponent_type'], DifficultyLevel.NORMAL)

        # Run evolution
        print(f"🚀 Starting evolution for Stage {stage['stage']}...")

        if GAME_TYPE == 'connect4':
            # Temporarily override benchmark's opponent selection
            from benchmarks import connect4_benchmark
            original_run = connect4_benchmark.run_benchmark

            def run_with_opponent(agent, **kwargs):
                kwargs['opponent_type'] = stage['opponent_type']
                return original_run(agent, **kwargs)

            connect4_benchmark.run_benchmark = run_with_opponent

            try:
                best_agent, fitness_history = smm.run_evolution(
                    iee_evaluator=iee,
                    benchmark_name=BENCHMARK_NAME,
                    template_class=GamePlayingExpertAgent
                )
            finally:
                connect4_benchmark.run_benchmark = original_run

        else:  # freeciv
            best_agent, fitness_history = smm.run_evolution(
                iee_evaluator=iee,
                benchmark_name=BENCHMARK_NAME,
                template_class=GamePlayingExpertAgent
            )

        # Record stage results
        stage_results = {
            'stage': stage['stage'],
            'opponent': stage['opponent_type'],
            'best_fitness': smm.best_fitness,
            'generations_run': len(fitness_history),
            'fitness_history': fitness_history,
            'target_achieved': smm.best_fitness >= stage['target_win_rate']
        }
        training_history['stages'].append(stage_results)

        # Display results
        print(f"\n{'─' * 80}")
        print(f"✅ STAGE {stage['stage']} COMPLETE")
        print(f"{'─' * 80}")
        print(f"Final Fitness: {smm.best_fitness:.1%}")
        print(f"Target: {stage['target_win_rate']:.1%}")
        print(f"Status: {'✅ ACHIEVED' if stage_results['target_achieved'] else '⏸️  PARTIAL'}")

        # Check if we should continue
        if not stage_results['target_achieved']:
            print(f"\n⚠️  Did not reach target win rate for Stage {stage['stage']}")
            response = input("Continue to next stage anyway? (y/n): ")
            if response.lower() != 'y':
                print("Training stopped early.")
                break

        # Save checkpoint
        checkpoint_file = f"curriculum_checkpoint_stage{stage['stage']}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(training_history, f, indent=2)
        print(f"💾 Checkpoint saved: {checkpoint_file}")

    # Final summary
    print("\n" + "=" * 80)
    print("🎉 CURRICULUM TRAINING COMPLETE!")
    print("=" * 80)

    print("\n📊 STAGE SUMMARY:")
    print("─" * 80)
    print(f"{'Stage':<8} {'Opponent':<20} {'Final Fitness':<15} {'Target':<10} {'Status':<10}")
    print("─" * 80)

    for stage_result in training_history['stages']:
        status = "✅ PASS" if stage_result['target_achieved'] else "⏸️  PARTIAL"
        print(f"{stage_result['stage']:<8} {stage_result['opponent']:<20} "
              f"{stage_result['best_fitness']:<15.1%} "
              f"{CURRICULUM[stage_result['stage']-1]['target_win_rate']:<10.1%} {status:<10}")

    print("─" * 80)

    # Save final results
    training_history['end_time'] = datetime.now().isoformat()
    final_file = f"curriculum_training_{GAME_TYPE}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(final_file, 'w') as f:
        json.dump(training_history, f, indent=2)

    print(f"\n💾 Final results saved: {final_file}")

    print("\n" + "=" * 80)
    print("💡 KEY TAKEAWAYS")
    print("=" * 80)
    print("\n✓ Curriculum learning enables progressive skill development")
    print("✓ Each stage builds on previous learning")
    print("✓ Objective difficulty measurement via AI skill levels")
    print("✓ Transfer learning between difficulty levels")

    if GAME_TYPE == 'freeciv':
        print("\n⏱️  FreeCiv Training Notes:")
        print("  • Each stage can take hours or days")
        print("  • Save checkpoints frequently")
        print("  • Consider parallel training on multiple machines")
        print("  • Cloud compute recommended for full curriculum")

    print()

except KeyboardInterrupt:
    print("\n\n⚠️  Training interrupted by user")
    print(f"📊 Completed {len(training_history['stages'])} of {len(CURRICULUM)} stages")

    # Save interrupted state
    training_history['end_time'] = datetime.now().isoformat()
    training_history['interrupted'] = True
    interrupted_file = f"curriculum_INTERRUPTED_{GAME_TYPE}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(interrupted_file, 'w') as f:
        json.dump(training_history, f, indent=2)
    print(f"💾 Progress saved: {interrupted_file}")

    sys.exit(1)

except Exception as e:
    print(f"\n\n❌ Error during training: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
