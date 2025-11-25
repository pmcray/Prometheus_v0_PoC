"""
Prometheus Go Training

This module implements training utilities for Go agents:
- Self-play game generation
- Training data preparation
- ELO rating estimation
- Game outcome tracking
- MCTS integration for improved policy targets
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Any
import time
from collections import deque

from prometheus.environments.go import (
    GoEnvironment,
    GoBoard,
    GoBoardEncoder,
    GoMoveEncoder
)


def generate_selfplay_game(
    agent: Any,
    board_size: int = 19,
    komi: float = 7.5,
    temperature_schedule: Optional[List[Tuple[int, float]]] = None,
    max_moves: int = 400,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Generate single self-play Go game for training.

    Args:
        agent: Go agent with get_move() method
        board_size: Size of Go board (9, 13, or 19)
        komi: Komi compensation for white
        temperature_schedule: List of (move_num, temperature) tuples
        max_moves: Maximum moves before game ends
        verbose: Print game progress

    Returns:
        Dictionary with game data for training:
        - states: Board states (N, board_size, board_size, 3)
        - policy_targets: Move targets (N, board_size^2 + 1)
        - value_targets: Game outcome from each player's perspective (N,)
        - moves_played: List of moves
        - result: Final score
    """
    if temperature_schedule is None:
        # More exploration in Go since board is larger
        temperature_schedule = [(0, 1.2), (50, 0.8), (100, 0.5)]

    env = GoEnvironment(board_size=board_size, komi=komi)
    encoder = GoBoardEncoder(board_size=board_size)
    move_encoder = GoMoveEncoder(board_size=board_size)

    # Game history
    states = []
    policy_targets = []
    moves_played = []
    pass_count = 0

    move_count = 0

    if verbose:
        print(f"🎮 Starting Go self-play game ({board_size}×{board_size})...")

    while move_count < max_moves:
        # Get current temperature
        temperature = 1.0
        for threshold, temp in temperature_schedule:
            if move_count >= threshold:
                temperature = temp

        # Get current state
        state = env.get_state()
        states.append(state)

        # Get legal moves
        legal_moves = env.get_legal_moves()

        # Get move from agent
        move = agent.get_move(state, legal_moves, temperature=temperature)

        # Create policy target (one-hot for supervised learning)
        num_moves = board_size * board_size + 1
        policy_target = np.zeros(num_moves)
        move_idx = move_encoder.move_to_index(move)
        policy_target[move_idx] = 1.0
        policy_targets.append(policy_target)

        # Execute move
        if move == ('pass',):
            pass_count += 1
            if pass_count >= 2:
                # Two consecutive passes = game over
                break
        else:
            pass_count = 0

        _, _, done, _ = env.step(move)
        moves_played.append(move)
        move_count += 1

        if verbose and move_count % 20 == 0:
            print(f"  Move {move_count}: {move}")

        if done:
            break

    # Get game outcome (scoring)
    score_dict = env.board.score()
    black_score = score_dict['black']
    white_score = score_dict['white']
    score_diff = black_score - white_score

    if verbose:
        print(f"  Game ended after {move_count} moves")
        print(f"  Black: {black_score:.1f}, White: {white_score:.1f}")
        print(f"  Winner: {'Black' if score_diff > 0 else 'White' if score_diff < 0 else 'Draw'}")

    # Assign value targets based on outcome
    # Value from -1 (black loses) to +1 (black wins)
    value_targets = []
    for i in range(len(states)):
        # Current player alternates: 0=black, 1=white, 2=black, ...
        is_black_turn = (i % 2 == 0)

        if score_diff > 0:  # Black wins
            value = 1.0 if is_black_turn else -1.0
        elif score_diff < 0:  # White wins
            value = -1.0 if is_black_turn else 1.0
        else:  # Draw
            value = 0.0

        value_targets.append(value)

    return {
        'states': np.array(states),
        'policy_targets': np.array(policy_targets),
        'value_targets': np.array(value_targets),
        'moves_played': moves_played,
        'result': score_diff,
        'black_score': black_score,
        'white_score': white_score,
        'num_moves': move_count
    }


def generate_selfplay_batch(
    agent: Any,
    num_games: int = 10,
    board_size: int = 19,
    komi: float = 7.5,
    verbose: bool = False
) -> Dict[str, np.ndarray]:
    """
    Generate batch of self-play games for training.

    Args:
        agent: Go agent
        num_games: Number of games to generate
        board_size: Size of Go board
        komi: Komi compensation
        verbose: Print progress

    Returns:
        Dictionary with concatenated training data:
        - X: Board states
        - policy_y: Policy targets
        - value_y: Value targets
        - game_results: List of game outcomes
    """
    all_states = []
    all_policies = []
    all_values = []
    game_results = []

    if verbose:
        print(f"🎲 Generating {num_games} self-play games...")

    for game_idx in range(num_games):
        if verbose:
            print(f"\n  Game {game_idx + 1}/{num_games}")

        game_data = generate_selfplay_game(
            agent=agent,
            board_size=board_size,
            komi=komi,
            verbose=verbose
        )

        all_states.append(game_data['states'])
        all_policies.append(game_data['policy_targets'])
        all_values.append(game_data['value_targets'])
        game_results.append({
            'result': game_data['result'],
            'black_score': game_data['black_score'],
            'white_score': game_data['white_score'],
            'num_moves': game_data['num_moves']
        })

    # Concatenate all games
    X = np.concatenate(all_states, axis=0)
    policy_y = np.concatenate(all_policies, axis=0)
    value_y = np.concatenate(all_values, axis=0)

    if verbose:
        print(f"\n✅ Generated {len(X)} training positions from {num_games} games")

    return {
        'X': X,
        'policy_y': policy_y,
        'value_y': value_y,
        'game_results': game_results
    }


def play_match(
    agent1: Any,
    agent2: Any,
    num_games: int = 10,
    board_size: int = 19,
    komi: float = 7.5,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Play match between two Go agents.

    Args:
        agent1: First agent (plays black in first game)
        agent2: Second agent (plays white in first game)
        num_games: Number of games (alternating colors)
        board_size: Size of Go board
        komi: Komi compensation
        verbose: Print progress

    Returns:
        Match results with win/loss/draw counts
    """
    agent1_wins = 0
    agent2_wins = 0
    draws = 0
    game_details = []

    if verbose:
        print(f"⚔️  Match: {getattr(agent1, 'name', 'Agent1')} vs {getattr(agent2, 'name', 'Agent2')}")
        print(f"   {num_games} games on {board_size}×{board_size} board")

    for game_idx in range(num_games):
        # Alternate colors
        if game_idx % 2 == 0:
            black_agent = agent1
            white_agent = agent2
            agent1_is_black = True
        else:
            black_agent = agent2
            white_agent = agent1
            agent1_is_black = False

        if verbose:
            print(f"\n  Game {game_idx + 1}: ", end="")
            if agent1_is_black:
                print(f"Black={getattr(agent1, 'name', 'Agent1')} vs White={getattr(agent2, 'name', 'Agent2')}")
            else:
                print(f"Black={getattr(agent2, 'name', 'Agent2')} vs White={getattr(agent1, 'name', 'Agent1')}")

        # Play game
        env = GoEnvironment(board_size=board_size, komi=komi)
        move_count = 0
        pass_count = 0
        max_moves = 400

        while move_count < max_moves:
            # Determine current agent
            is_black_turn = (move_count % 2 == 0)
            current_agent = black_agent if is_black_turn else white_agent

            # Get move
            state = env.get_state()
            legal_moves = env.get_legal_moves()
            move = current_agent.get_move(state, legal_moves, temperature=0.1)  # Low temp for competitive play

            # Execute move
            if move == ('pass',):
                pass_count += 1
                if pass_count >= 2:
                    break
            else:
                pass_count = 0

            _, _, done, _ = env.step(move)
            move_count += 1

            if done:
                break

        # Score game
        score_dict = env.board.score()
        black_score = score_dict['black']
        white_score = score_dict['white']
        score_diff = black_score - white_score

        # Determine winner
        if score_diff > 0:  # Black wins
            winner = agent1 if agent1_is_black else agent2
            if agent1_is_black:
                agent1_wins += 1
            else:
                agent2_wins += 1
            result = "Black wins"
        elif score_diff < 0:  # White wins
            winner = agent2 if agent1_is_black else agent1
            if agent1_is_black:
                agent2_wins += 1
            else:
                agent1_wins += 1
            result = "White wins"
        else:  # Draw
            winner = None
            draws += 1
            result = "Draw"

        game_details.append({
            'game_num': game_idx + 1,
            'agent1_color': 'black' if agent1_is_black else 'white',
            'black_score': black_score,
            'white_score': white_score,
            'result': result,
            'num_moves': move_count
        })

        if verbose:
            print(f"    Result: {result} (B: {black_score:.1f}, W: {white_score:.1f}) after {move_count} moves")

    # Calculate statistics
    total_games = agent1_wins + agent2_wins + draws
    agent1_win_rate = agent1_wins / total_games if total_games > 0 else 0.0
    agent2_win_rate = agent2_wins / total_games if total_games > 0 else 0.0

    if verbose:
        print(f"\n📊 Match Results:")
        print(f"   {getattr(agent1, 'name', 'Agent1')}: {agent1_wins} wins ({agent1_win_rate:.1%})")
        print(f"   {getattr(agent2, 'name', 'Agent2')}: {agent2_wins} wins ({agent2_win_rate:.1%})")
        print(f"   Draws: {draws}")

    return {
        'agent1_wins': agent1_wins,
        'agent2_wins': agent2_wins,
        'draws': draws,
        'agent1_win_rate': agent1_win_rate,
        'agent2_win_rate': agent2_win_rate,
        'game_details': game_details
    }


def estimate_elo_from_winrate(win_rate: float, opponent_elo: int = 1500) -> int:
    """
    Estimate ELO rating from win rate against known opponent.

    Args:
        win_rate: Win rate (0.0 to 1.0)
        opponent_elo: Known ELO of opponent

    Returns:
        Estimated ELO rating

    Note:
        Go traditionally uses different ranking systems (kyu/dan),
        but ELO is useful for cross-game comparison with chess.
    """
    if win_rate >= 0.99:
        win_rate = 0.99
    elif win_rate <= 0.01:
        win_rate = 0.01

    # ELO formula: E = 1 / (1 + 10^((R_opponent - R_player) / 400))
    # Solving for R_player: R_player = R_opponent + 400 * log10((1 - E) / E)
    elo_diff = 400 * np.log10((1 - win_rate) / win_rate)
    estimated_elo = int(opponent_elo - elo_diff)

    return estimated_elo


def train_agent_selfplay(
    agent: Any,
    num_iterations: int = 10,
    games_per_iteration: int = 10,
    epochs_per_iteration: int = 3,
    board_size: int = 19,
    komi: float = 7.5,
    verbose: bool = True
) -> Dict[str, List]:
    """
    Train Go agent via self-play (AlphaGo Zero style).

    Process:
    1. Generate self-play games
    2. Train on positions from these games
    3. Repeat (recursive self-improvement)

    Args:
        agent: PrometheusGoAgent instance
        num_iterations: Number of training iterations
        games_per_iteration: Number of self-play games per iteration
        epochs_per_iteration: Training epochs per iteration
        board_size: Size of Go board
        komi: Komi compensation
        verbose: Print progress

    Returns:
        Training history with statistics
    """
    history = {
        'iteration': [],
        'games_played': [],
        'avg_game_length': [],
        'policy_loss': [],
        'value_loss': []
    }

    total_games = 0

    if verbose:
        print("=" * 60)
        print(f"🚀 Self-Play Training ({num_iterations} iterations)")
        print(f"   {games_per_iteration} games/iteration, {epochs_per_iteration} epochs/iteration")
        print("=" * 60)

    for iteration in range(num_iterations):
        if verbose:
            print(f"\n🔄 Iteration {iteration + 1}/{num_iterations}")

        # Generate self-play games
        start_time = time.time()
        batch_data = generate_selfplay_batch(
            agent=agent,
            num_games=games_per_iteration,
            board_size=board_size,
            komi=komi,
            verbose=False
        )
        generation_time = time.time() - start_time

        X = batch_data['X']
        policy_y = batch_data['policy_y']
        value_y = batch_data['value_y']
        game_results = batch_data['game_results']

        total_games += games_per_iteration
        avg_game_length = np.mean([r['num_moves'] for r in game_results])

        if verbose:
            print(f"   Generated {len(X)} positions in {generation_time:.1f}s")
            print(f"   Avg game length: {avg_game_length:.1f} moves")

        # Train on self-play data
        if hasattr(agent, 'online_train'):
            train_history = agent.online_train(
                X, policy_y, value_y,
                epochs=epochs_per_iteration,
                verbose=0
            )

            # Extract loss values
            policy_loss = np.mean(train_history.history[f'{agent.model.name}_policy_output_loss'])
            value_loss = np.mean(train_history.history[f'{agent.model.name}_value_output_loss'])

            if verbose:
                print(f"   Policy Loss: {policy_loss:.4f}, Value Loss: {value_loss:.4f}")

            history['policy_loss'].append(policy_loss)
            history['value_loss'].append(value_loss)

        # Update agent generation
        if hasattr(agent, 'generation'):
            agent.generation += 1

        # Track statistics
        history['iteration'].append(iteration + 1)
        history['games_played'].append(total_games)
        history['avg_game_length'].append(avg_game_length)

    if verbose:
        print("\n" + "=" * 60)
        print(f"✅ Training complete! Total games: {total_games}")
        print("=" * 60)

    return history
