#!/usr/bin/env python3
"""
Example: Evaluate and Compare Multiple Agents

This script demonstrates agent evaluation and comparison:
1. Load multiple trained agents
2. Run head-to-head matchups
3. Calculate ELO ratings
4. Generate comparison visualizations

Usage:
    python examples/evaluate_agents.py --agents model1.h5 model2.h5 model3.h5
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tensorflow as tf
from prometheus.models.go_models import PrometheusGoAgent, RandomGoAgent
from prometheus.evaluation.benchmark import GoEvaluator
from prometheus.environments.go import GoEnvironment
from prometheus.visualization.training_dashboard import ComparisonDashboard


def load_agent(model_path: str, board_size: int = 9):
    """Load agent from model file."""
    agent = PrometheusGoAgent(board_size=board_size)
    agent.model = tf.keras.models.load_model(model_path)
    agent.trainable = False
    agent.name = Path(model_path).stem
    return agent


def main():
    """Main evaluation pipeline."""
    parser = argparse.ArgumentParser(
        description='Evaluate and compare multiple Go agents'
    )

    parser.add_argument(
        '--agents',
        type=str,
        nargs='+',
        help='Paths to trained agent models (.h5 files)'
    )

    parser.add_argument(
        '--board-size',
        type=int,
        default=9,
        choices=[9, 13, 19],
        help='Board size (default: 9)'
    )

    parser.add_argument(
        '--games-per-matchup',
        type=int,
        default=50,
        help='Games per head-to-head matchup (default: 50)'
    )

    parser.add_argument(
        '--include-random',
        action='store_true',
        help='Include random baseline agent'
    )

    parser.add_argument(
        '--tournament',
        action='store_true',
        help='Run round-robin tournament (all vs all)'
    )

    parser.add_argument(
        '--visualize',
        action='store_true',
        help='Show comparison dashboard'
    )

    args = parser.parse_args()

    if not args.agents:
        print("Error: No agents specified")
        print("Usage: python examples/evaluate_agents.py --agents model1.h5 model2.h5")
        return 1

    print("="*70)
    print("AGENT EVALUATION & COMPARISON")
    print("="*70)

    # 1. Load agents
    print(f"\n1. Loading agents...")
    agents = []

    for model_path in args.agents:
        if not Path(model_path).exists():
            print(f"   ✗ File not found: {model_path}")
            continue

        agent = load_agent(model_path, args.board_size)
        agents.append(agent)
        print(f"   ✓ Loaded: {agent.name}")

    if args.include_random:
        random_agent = RandomGoAgent(board_size=args.board_size)
        random_agent.name = "Random Baseline"
        agents.append(random_agent)
        print(f"   ✓ Added: Random Baseline")

    if len(agents) < 2:
        print("\nError: Need at least 2 agents for comparison")
        return 1

    # 2. Create evaluator
    evaluator = GoEvaluator(board_size=args.board_size)
    env = GoEnvironment(board_size=args.board_size)

    # 3. Run evaluation
    if args.tournament:
        # Round-robin tournament
        print(f"\n2. Running tournament...")
        print(f"   Matchups: {len(agents) * (len(agents) - 1) // 2}")
        print(f"   Games per matchup: {args.games_per_matchup}")
        print(f"   Total games: {len(agents) * (len(agents) - 1) // 2 * args.games_per_matchup}")

        results = evaluator.tournament(
            agents,
            env,
            games_per_matchup=args.games_per_matchup,
            verbose=True
        )

        print("\nTournament complete!")

    else:
        # Head-to-head matchups
        print(f"\n2. Running head-to-head matchups...")

        results = {}
        for i, agent1 in enumerate(agents):
            for j, agent2 in enumerate(agents):
                if i < j:
                    print(f"\n   {agent1.name} vs {agent2.name}...")

                    result = evaluator.evaluate_matchup(
                        agent1, agent2, env,
                        num_games=args.games_per_matchup,
                        verbose=False
                    )

                    key = f"{agent1.name}_vs_{agent2.name}"
                    results[key] = result

                    print(f"   {agent1.name}: {result['agent1_win_rate']:.1%} win rate, {result['agent1_elo']:.0f} ELO")
                    print(f"   {agent2.name}: {result['agent2_win_rate']:.1%} win rate, {result['agent2_elo']:.0f} ELO")

    # 4. Summary
    print("\n" + "="*70)
    print("EVALUATION RESULTS")
    print("="*70)

    if args.tournament:
        # Show standings
        standings = results['standings']
        sorted_agents = sorted(
            standings.items(),
            key=lambda x: (x[1]['points'], x[1]['elo']),
            reverse=True
        )

        print(f"\n{'Rank':<6} {'Agent':<25} {'W-L-D':<12} {'Points':<8} {'ELO':<6}")
        print("-"*70)

        for rank, (name, stats) in enumerate(sorted_agents, 1):
            wld = f"{stats['wins']}-{stats['losses']}-{stats['draws']}"
            print(f"{rank:<6} {name:<25} {wld:<12} "
                  f"{stats['points']:<8.1f} {stats['elo']:<6.0f}")

    else:
        # Show pairwise comparisons
        for key, result in results.items():
            agent1_name, agent2_name = key.split('_vs_')
            print(f"\n{agent1_name} vs {agent2_name}:")
            print(f"  {agent1_name}: {result['agent1_wins']} wins ({result['agent1_win_rate']:.1%}), ELO {result['agent1_elo']:.0f}")
            print(f"  {agent2_name}: {result['agent2_wins']} wins ({result['agent2_win_rate']:.1%}), ELO {result['agent2_elo']:.0f}")

            stats = evaluator.calculate_statistical_significance(result)
            print(f"  p-value: {stats['p_value']:.4f} ({'significant' if stats['significant'] else 'not significant'})")

    print("="*70 + "\n")

    # 5. Visualization
    if args.visualize:
        print("Generating comparison dashboard...")

        agent_names = [agent.name for agent in agents]
        comparison = ComparisonDashboard(agent_names)

        # Populate with results
        if args.tournament:
            for name, stats in results['standings'].items():
                comparison.update(name, {
                    'elo': stats['elo'],
                    'win_rate': stats['wins'] / max(1, stats['wins'] + stats['losses'] + stats['draws'])
                })

        comparison.plot()

    return 0


if __name__ == '__main__':
    sys.exit(main())
