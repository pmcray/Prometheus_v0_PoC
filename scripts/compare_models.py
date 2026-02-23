#!/usr/bin/env python3
"""
Model Comparison Tool

Compare two Prometheus models head-to-head across multiple games.
Calculates win rates, ELO differences, and performance metrics.

Usage:
    # Compare two models
    python scripts/compare_models.py \
        --model1 models/pretrained/go_9x9.h5 \
        --model2 models/pretrained/go_9x9_v2.h5 \
        --num-games 50

    # Compare with MCTS
    python scripts/compare_models.py \
        --model1 models/pretrained/go_9x9.h5 \
        --model2 models/pretrained/go_9x9.h5 \
        --mcts1 400 \
        --mcts2 100 \
        --num-games 20

    # Quick comparison
    python scripts/compare_models.py \
        --model1 models/pretrained/chess.h5 \
        --model2 random \
        --num-games 10 \
        --game chess
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np


def calculate_elo_difference(win_rate: float) -> float:
    """
    Calculate ELO difference from win rate.

    Uses standard ELO formula: ELO_diff = -400 * log10((1/win_rate) - 1)

    Args:
        win_rate: Win rate as fraction (0.0 to 1.0)

    Returns:
        ELO difference (positive means model1 is stronger)
    """
    if win_rate >= 0.99:
        return 600  # Cap very high win rates
    elif win_rate <= 0.01:
        return -600  # Cap very low win rates

    # Standard ELO formula
    elo_diff = -400 * np.log10((1 / win_rate) - 1)
    return elo_diff


def calculate_confidence_interval(wins: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """
    Calculate Wilson score confidence interval for win rate.

    Args:
        wins: Number of wins
        total: Total games
        confidence: Confidence level (default 0.95)

    Returns:
        (lower_bound, upper_bound) as fractions
    """
    if total == 0:
        return (0.0, 1.0)

    p = wins / total

    # Wilson score interval
    z = 1.96 if confidence == 0.95 else 2.576  # 95% or 99%

    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    margin = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator

    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)

    return (lower, upper)


def play_game(env, agent1, agent2, verbose: bool = False) -> int:
    """
    Play one game between two agents.

    Args:
        env: Game environment
        agent1: First agent
        agent2: Second agent
        verbose: Print game progress

    Returns:
        1 if agent1 wins, 0 if draw, -1 if agent2 wins
    """
    state = env.reset()
    current_player = 0  # 0 = agent1, 1 = agent2
    agents = [agent1, agent2]

    move_count = 0
    max_moves = 500  # Prevent infinite games

    while move_count < max_moves:
        # Get current agent
        agent = agents[current_player]

        # Select move
        try:
            move = agent.select_move(state)
        except Exception as e:
            if verbose:
                print(f"Agent {current_player} error: {e}")
            # Agent error = loss
            return -1 if current_player == 0 else 1

        # Make move
        try:
            next_state, reward, done, info = env.step(move)
        except Exception as e:
            if verbose:
                print(f"Invalid move by agent {current_player}: {e}")
            # Invalid move = loss
            return -1 if current_player == 0 else 1

        if verbose:
            print(f"Move {move_count + 1}: Player {current_player} plays {move}")

        if done:
            # Determine winner from reward
            if reward > 0:
                # Current player won
                return 1 if current_player == 0 else -1
            elif reward < 0:
                # Current player lost
                return -1 if current_player == 0 else 1
            else:
                # Draw
                return 0

        state = next_state
        current_player = 1 - current_player
        move_count += 1

    # Max moves reached - draw
    if verbose:
        print(f"Game reached max moves ({max_moves}) - draw")
    return 0


def compare_models(
    model1_path: str,
    model2_path: str,
    game: str = "go",
    board_size: int = 9,
    num_games: int = 50,
    mcts1_sims: int = 0,
    mcts2_sims: int = 0,
    verbose: bool = False,
    output_path: str = None
) -> Dict:
    """
    Compare two models head-to-head.

    Args:
        model1_path: Path to first model (or 'random')
        model2_path: Path to second model (or 'random')
        game: Game type ('go' or 'chess')
        board_size: Board size for Go
        num_games: Number of games to play
        mcts1_sims: MCTS simulations for model1 (0 = no MCTS)
        mcts2_sims: MCTS simulations for model2 (0 = no MCTS)
        verbose: Print progress
        output_path: Path to save results JSON

    Returns:
        Dictionary with comparison results
    """
    print("=" * 80)
    print("MODEL COMPARISON")
    print("=" * 80)

    # Import here to avoid import errors in CLI help
    if game == "go":
        from prometheus.environments.go import GoEnvironment
        from prometheus.models.go_models import create_go_agent, RandomGoAgent
        import tensorflow as tf

        env = GoEnvironment(board_size=board_size)

        # Load agent 1
        if model1_path == "random":
            agent1 = RandomGoAgent()
            agent1_name = "Random"
        else:
            model1 = tf.keras.models.load_model(model1_path, compile=False)
            # Wrap in agent interface
            from prometheus.models.go_models import PrometheusGoAgent
            agent1 = PrometheusGoAgent(model1, board_size=board_size)
            agent1_name = Path(model1_path).stem

        # Load agent 2
        if model2_path == "random":
            agent2 = RandomGoAgent()
            agent2_name = "Random"
        else:
            model2 = tf.keras.models.load_model(model2_path, compile=False)
            from prometheus.models.go_models import PrometheusGoAgent
            agent2 = PrometheusGoAgent(model2, board_size=board_size)
            agent2_name = Path(model2_path).stem

    elif game == "chess":
        from prometheus.environments.chess_env import ChessEnvironment
        from prometheus.models.chess_models import create_chess_agent, RandomChessAgent
        import tensorflow as tf

        env = ChessEnvironment()

        # Load agent 1
        if model1_path == "random":
            agent1 = RandomChessAgent()
            agent1_name = "Random"
        else:
            model1 = tf.keras.models.load_model(model1_path, compile=False)
            from prometheus.models.chess_models import PrometheusChessAgent
            agent1 = PrometheusChessAgent(model1)
            agent1_name = Path(model1_path).stem

        # Load agent 2
        if model2_path == "random":
            agent2 = RandomChessAgent()
            agent2_name = "Random"
        else:
            model2 = tf.keras.models.load_model(model2_path, compile=False)
            from prometheus.models.chess_models import PrometheusChessAgent
            agent2 = PrometheusChessAgent(model2)
            agent2_name = Path(model2_path).stem

    else:
        raise ValueError(f"Unknown game: {game}")

    # Add MCTS if requested
    if mcts1_sims > 0:
        from prometheus.mcts import add_mcts
        agent1 = add_mcts(agent1, num_simulations=mcts1_sims)
        agent1_name += f" (MCTS {mcts1_sims})"

    if mcts2_sims > 0:
        from prometheus.mcts import add_mcts
        agent2 = add_mcts(agent2, num_simulations=mcts2_sims)
        agent2_name += f" (MCTS {mcts2_sims})"

    print(f"\nAgent 1: {agent1_name}")
    print(f"Agent 2: {agent2_name}")
    print(f"Game: {game.upper()}" + (f" {board_size}×{board_size}" if game == "go" else ""))
    print(f"Number of games: {num_games}")
    print()

    # Play games
    results = []
    agent1_wins = 0
    agent2_wins = 0
    draws = 0
    game_times = []

    for i in range(num_games):
        start_time = time.time()

        # Alternate who plays first
        if i % 2 == 0:
            result = play_game(env, agent1, agent2, verbose=verbose)
        else:
            result = -play_game(env, agent2, agent1, verbose=verbose)

        game_time = time.time() - start_time
        game_times.append(game_time)

        results.append(result)

        if result == 1:
            agent1_wins += 1
        elif result == -1:
            agent2_wins += 1
        else:
            draws += 1

        # Progress
        if (i + 1) % 10 == 0 or i == num_games - 1:
            win_rate = agent1_wins / (i + 1)
            print(f"Games {i + 1}/{num_games}: "
                  f"W:{agent1_wins} L:{agent2_wins} D:{draws} "
                  f"(Win rate: {win_rate:.1%}, "
                  f"Avg time: {np.mean(game_times):.1f}s)")

    # Calculate statistics
    total_decisive = agent1_wins + agent2_wins
    win_rate = agent1_wins / num_games if num_games > 0 else 0
    win_rate_decisive = agent1_wins / total_decisive if total_decisive > 0 else 0.5

    elo_diff = calculate_elo_difference(win_rate_decisive)
    ci_lower, ci_upper = calculate_confidence_interval(agent1_wins, num_games)

    # Summary
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"\n{agent1_name} vs {agent2_name}:")
    print(f"  Wins:   {agent1_wins}/{num_games} ({agent1_wins/num_games*100:.1f}%)")
    print(f"  Losses: {agent2_wins}/{num_games} ({agent2_wins/num_games*100:.1f}%)")
    print(f"  Draws:  {draws}/{num_games} ({draws/num_games*100:.1f}%)")
    print(f"\nWin Rate: {win_rate:.1%}")
    print(f"95% Confidence Interval: [{ci_lower:.1%}, {ci_upper:.1%}]")
    print(f"\nELO Difference: {elo_diff:+.0f}")
    print(f"  ({agent1_name} is {abs(elo_diff):.0f} ELO {'stronger' if elo_diff > 0 else 'weaker'})")
    print(f"\nAverage game time: {np.mean(game_times):.2f}s")
    print(f"Total time: {sum(game_times):.1f}s ({sum(game_times)/60:.1f} min)")

    # Build results dict
    comparison_results = {
        "agent1": {
            "name": agent1_name,
            "path": model1_path,
            "mcts_sims": mcts1_sims,
        },
        "agent2": {
            "name": agent2_name,
            "path": model2_path,
            "mcts_sims": mcts2_sims,
        },
        "game": game,
        "board_size": board_size if game == "go" else None,
        "num_games": num_games,
        "results": {
            "agent1_wins": agent1_wins,
            "agent2_wins": agent2_wins,
            "draws": draws,
            "win_rate": win_rate,
            "win_rate_decisive": win_rate_decisive,
            "confidence_interval": {
                "lower": ci_lower,
                "upper": ci_upper,
            },
            "elo_difference": elo_diff,
        },
        "timing": {
            "avg_game_time_s": float(np.mean(game_times)),
            "total_time_s": float(sum(game_times)),
            "game_times": [float(t) for t in game_times],
        },
    }

    # Save results
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(comparison_results, f, indent=2)
        print(f"\n✓ Results saved to: {output_path}")

    return comparison_results


def main():
    parser = argparse.ArgumentParser(
        description="Compare two Prometheus models head-to-head",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two Go models
  python scripts/compare_models.py \\
    --model1 models/pretrained/go_9x9.h5 \\
    --model2 models/pretrained/go_9x9_v2.h5 \\
    --num-games 50

  # Compare with different MCTS settings
  python scripts/compare_models.py \\
    --model1 models/pretrained/go_9x9.h5 \\
    --model2 models/pretrained/go_9x9.h5 \\
    --mcts1 400 \\
    --mcts2 100 \\
    --num-games 20

  # Compare chess models vs random
  python scripts/compare_models.py \\
    --model1 models/pretrained/chess.h5 \\
    --model2 random \\
    --game chess \\
    --num-games 30
        """
    )

    parser.add_argument('--model1', required=True,
                        help='Path to first model (or "random")')
    parser.add_argument('--model2', required=True,
                        help='Path to second model (or "random")')
    parser.add_argument('--game', default='go', choices=['go', 'chess'],
                        help='Game type (default: go)')
    parser.add_argument('--board-size', type=int, default=9,
                        help='Board size for Go (default: 9)')
    parser.add_argument('--num-games', type=int, default=50,
                        help='Number of games to play (default: 50)')
    parser.add_argument('--mcts1', type=int, default=0,
                        help='MCTS simulations for model1 (0 = no MCTS)')
    parser.add_argument('--mcts2', type=int, default=0,
                        help='MCTS simulations for model2 (0 = no MCTS)')
    parser.add_argument('--output', type=str,
                        help='Output path for results JSON')
    parser.add_argument('--verbose', action='store_true',
                        help='Print detailed game progress')

    args = parser.parse_args()

    # Run comparison
    results = compare_models(
        model1_path=args.model1,
        model2_path=args.model2,
        game=args.game,
        board_size=args.board_size,
        num_games=args.num_games,
        mcts1_sims=args.mcts1,
        mcts2_sims=args.mcts2,
        verbose=args.verbose,
        output_path=args.output,
    )

    # Exit with success
    return 0


if __name__ == '__main__':
    sys.exit(main())
