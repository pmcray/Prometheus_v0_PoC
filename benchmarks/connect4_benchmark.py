"""
Connect4 Benchmark for Evolution Demo

This benchmark:
1. Uses the new Connect4 game from prometheus.game_suite
2. Plays against a RANDOM opponent (not Minimax) so agents can actually win
3. Provides game visualization support
4. Returns win rate as fitness score
"""

import random
from typing import Dict, Any, Tuple, List
from prometheus.game_suite import Connect4, GameResult


class RandomOpponent:
    """
    Random move opponent for Connect4

    This is intentionally weak so evolved agents can learn to beat it.
    """

    def __init__(self, name: str = "RandomBot"):
        self.name = name

    def select_move(self, game_state) -> int:
        """Select a random valid move"""
        # Handle both dict and GameState object
        if hasattr(game_state, 'board'):
            board = game_state.board
        else:
            board = game_state['board']

        valid_moves = [col for col in range(7) if board[0][col] == 0]

        if not valid_moves:
            return None

        return random.choice(valid_moves)


def evaluate_connect4_agent(agent, num_games: int = 5, show_games: bool = False, opponent_type: str = "random") -> Tuple[float, Dict[str, Any]]:
    """
    Evaluate an agent playing Connect4

    Args:
        agent: Agent to evaluate (must have select_move method)
        num_games: Number of games to play
        show_games: Whether to print game boards (for debugging)
        opponent_type: Type of opponent ("random", "heuristic", "minimax-1", "minimax-2", "minimax-3")

    Returns:
        (fitness_score, details_dict)
        fitness_score is win_rate (0.0 to 1.0)
    """
    # Select opponent based on type
    if opponent_type == "random":
        from benchmarks.strategic_opponents import RandomOpponent
        opponent = RandomOpponent()
    elif opponent_type == "heuristic":
        from benchmarks.strategic_opponents import HeuristicOpponent
        opponent = HeuristicOpponent()
    elif opponent_type.startswith("minimax"):
        from benchmarks.strategic_opponents import MinimaxOpponent
        depth = int(opponent_type.split("-")[1]) if "-" in opponent_type else 2
        opponent = MinimaxOpponent(depth=depth)
    else:
        from benchmarks.strategic_opponents import RandomOpponent
        opponent = RandomOpponent()

    wins = 0
    losses = 0
    draws = 0
    game_histories = []

    for game_num in range(num_games):
        game = Connect4()
        moves_made = []

        # Alternate who goes first
        agent_player = 1 if game_num % 2 == 0 else -1

        while game.result.value == 'ongoing':
            current_player = game.current_player

            # Get move from appropriate player
            if current_player == agent_player:
                # Agent's turn
                try:
                    move = agent.select_move(game.get_state())
                except Exception as e:
                    # Agent error = loss
                    losses += 1
                    break
            else:
                # Opponent's turn
                move = opponent.select_move(game.get_state())

            # Make move
            if move is not None:
                success = game.make_move(move)
                if not success:
                    # Invalid move = loss
                    if current_player == agent_player:
                        losses += 1
                    else:
                        wins += 1
                    break

                moves_made.append((current_player, move))
            else:
                # No move available
                break

        # Check result
        if game.result.value == 'ongoing':
            # Game was aborted due to error
            continue
        elif game.winner == agent_player:
            wins += 1
        elif game.winner == -agent_player:
            losses += 1
        else:
            draws += 1

        # Save game history
        game_histories.append({
            'moves': moves_made,
            'result': game.result.value,
            'winner': game.winner,
            'agent_player': agent_player
        })

        if show_games:
            print(f"\nGame {game_num + 1}:")
            print(game.visualize())
            print(f"Result: {game.result.value}")

    # Calculate fitness
    total_games = wins + losses + draws
    if total_games == 0:
        fitness = 0.0
    else:
        # Win rate as fitness
        fitness = wins / total_games

    details = {
        'wins': wins,
        'losses': losses,
        'draws': draws,
        'total_games': total_games,
        'win_rate': fitness,
        'opponent': opponent.name if hasattr(opponent, 'name') else opponent_type,
        'opponent_skill': opponent.skill_level if hasattr(opponent, 'skill_level') else 0,
        'game_histories': game_histories
    }

    return fitness, details


# Benchmark registration
BENCHMARK_NAME = "GGP-connect4"
BENCHMARK_DOMAIN = "general_game_playing"
BENCHMARK_DIFFICULTY = "easy"
BENCHMARK_DESCRIPTION = "Connect4 game against random opponent"

def run_benchmark(agent, **kwargs) -> Dict[str, Any]:
    """
    Run Connect4 benchmark

    Returns benchmark result dict compatible with IEE
    """
    num_games = kwargs.get('num_games', 10)
    show_games = kwargs.get('show_games', False)
    opponent_type = kwargs.get('opponent_type', 'random')

    fitness, details = evaluate_connect4_agent(agent, num_games, show_games, opponent_type)

    return {
        'benchmark_name': BENCHMARK_NAME,
        'domain': BENCHMARK_DOMAIN,
        'fitness_score': fitness,
        'success': True,
        'details': details
    }
