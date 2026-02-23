"""
Prometheus Chess Training

This module implements training utilities for chess agents:
- Self-play game generation
- Training data preparation
- ELO rating estimation
- Benchmarking against external engines
- Performance tracking
"""

import numpy as np
import chess
from typing import List, Dict, Tuple, Optional, Any
import time
from collections import deque

from prometheus.environments.chess import (
    ChessEnvironment,
    ChessBoardEncoder,
    ChessMoveEncoder,
    UCIEngineInterface
)


def generate_selfplay_game(
    agent: Any,
    temperature_schedule: Optional[List[Tuple[int, float]]] = None,
    max_moves: int = 500,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Generate single self-play game for training.

    Args:
        agent: Chess agent with get_move() method
        temperature_schedule: List of (move_num, temperature) tuples
        max_moves: Maximum moves before draw
        verbose: Print game progress

    Returns:
        Dictionary with game data for training
    """
    if temperature_schedule is None:
        temperature_schedule = [(0, 1.0), (30, 0.5)]  # Exploration → Exploitation

    env = ChessEnvironment()
    encoder = ChessBoardEncoder()
    move_encoder = ChessMoveEncoder()

    # Game history
    states = []
    policy_targets = []
    moves_played = []

    move_count = 0

    if verbose:
        print("🎮 Starting self-play game...")

    while not env.board.is_game_over() and move_count < max_moves:
        # Get current temperature
        temperature = 1.0
        for threshold, temp in temperature_schedule:
            if move_count >= threshold:
                temperature = temp

        # Get current state
        state = env.get_state()
        states.append(state)

        # Get move from agent
        move = agent.get_move(state, env.board, temperature=temperature)

        # Create policy target (one-hot for supervised learning)
        policy_target = np.zeros(4096)
        move_idx = move_encoder.move_to_index(move)
        policy_target[move_idx] = 1.0
        policy_targets.append(policy_target)

        # Execute move
        env.step(move)
        moves_played.append(move)
        move_count += 1

        if verbose and move_count % 10 == 0:
            print(f"  Move {move_count}: {move}")

    # Get game outcome
    result = env.get_game_result()

    # Assign value targets based on outcome
    value_targets = []
    for i, move in enumerate(moves_played):
        # From perspective of player who made the move
        if result == "1-0":
            value = 1.0 if i % 2 == 0 else -1.0  # White wins
        elif result == "0-1":
            value = -1.0 if i % 2 == 0 else 1.0  # Black wins
        else:
            value = 0.0  # Draw

        value_targets.append(value)

    if verbose:
        print(f"🏁 Game finished: {result} after {move_count} moves")

    return {
        'states': states,
        'policy_targets': policy_targets,
        'value_targets': value_targets,
        'moves': moves_played,
        'result': result,
        'move_count': move_count
    }


def generate_selfplay_batch(
    agent: Any,
    num_games: int = 10,
    temperature_schedule: Optional[List[Tuple[int, float]]] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    Generate batch of self-play games.

    Args:
        agent: Chess agent
        num_games: Number of games to generate
        temperature_schedule: Temperature schedule
        verbose: Print progress

    Returns:
        List of game dictionaries
    """
    games = []

    if verbose:
        print(f"\n🎲 Generating {num_games} self-play games...")

    start_time = time.time()

    for i in range(num_games):
        if verbose:
            print(f"\nGame {i+1}/{num_games}:")

        game = generate_selfplay_game(
            agent,
            temperature_schedule=temperature_schedule,
            verbose=verbose
        )
        games.append(game)

        if verbose:
            print(f"  Result: {game['result']}, Moves: {game['move_count']}")

    elapsed = time.time() - start_time

    if verbose:
        print(f"\n✅ Generated {num_games} games in {elapsed:.1f}s")
        print(f"   Average: {elapsed/num_games:.1f}s per game")

    return games


def play_match(
    white_agent: Any,
    black_agent: Any,
    num_games: int = 10,
    swap_colors: bool = True,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Play match between two agents.

    Args:
        white_agent: Agent playing White
        black_agent: Agent playing Black
        num_games: Number of games
        swap_colors: Swap colors halfway through
        verbose: Print progress

    Returns:
        Dictionary with match results
    """
    results = {
        'white_wins': 0,
        'black_wins': 0,
        'draws': 0,
        'games': []
    }

    if verbose:
        print(f"\n♟️  Match: {white_agent.name} vs {black_agent.name}")
        print(f"   Games: {num_games}")

    for i in range(num_games):
        # Swap colors halfway
        if swap_colors and i == num_games // 2:
            white_agent, black_agent = black_agent, white_agent
            if verbose:
                print(f"\n🔄 Swapping colors...")

        if verbose:
            print(f"\nGame {i+1}/{num_games}: {white_agent.name} (White) vs {black_agent.name} (Black)")

        # Play game
        env = ChessEnvironment()
        move_count = 0
        max_moves = 500

        while not env.board.is_game_over() and move_count < max_moves:
            state = env.get_state()

            # Get move from current player
            if env.board.turn == chess.WHITE:
                move = white_agent.get_move(state, env.board)
            else:
                move = black_agent.get_move(state, env.board)

            # Execute move
            env.step(move)
            move_count += 1

        result = env.get_game_result()

        # Update statistics
        if result == "1-0":
            results['white_wins'] += 1
        elif result == "0-1":
            results['black_wins'] += 1
        else:
            results['draws'] += 1

        results['games'].append({
            'white': white_agent.name,
            'black': black_agent.name,
            'result': result,
            'moves': move_count
        })

        if verbose:
            print(f"  Result: {result} ({move_count} moves)")

    if verbose:
        print(f"\n📊 Match Results:")
        print(f"   {white_agent.name}: {results['white_wins']} wins")
        print(f"   {black_agent.name}: {results['black_wins']} wins")
        print(f"   Draws: {results['draws']}")

    return results


def estimate_elo_rating(
    agent: Any,
    baseline_agents: List[Tuple[Any, int]],
    games_per_opponent: int = 10,
    verbose: bool = True
) -> float:
    """
    Estimate ELO rating by playing against baseline agents.

    Args:
        agent: Agent to evaluate
        baseline_agents: List of (agent, ELO) tuples
        games_per_opponent: Games per opponent
        verbose: Print progress

    Returns:
        Estimated ELO rating
    """
    if verbose:
        print(f"\n📈 Estimating ELO for {agent.name}...")

    scores = []
    elo_estimates = []

    for baseline_agent, baseline_elo in baseline_agents:
        if verbose:
            print(f"\n  vs {baseline_agent.name} (ELO {baseline_elo}):")

        # Play match
        match = play_match(
            agent,
            baseline_agent,
            num_games=games_per_opponent,
            swap_colors=True,
            verbose=False
        )

        # Calculate score (from agent's perspective)
        white_games = games_per_opponent // 2
        black_games = games_per_opponent - white_games

        score = 0.0
        for game in match['games']:
            if game['white'] == agent.name:
                if game['result'] == "1-0":
                    score += 1.0
                elif game['result'] == "1/2-1/2":
                    score += 0.5
            else:  # Agent is Black
                if game['result'] == "0-1":
                    score += 1.0
                elif game['result'] == "1/2-1/2":
                    score += 0.5

        score_percentage = score / games_per_opponent

        # ELO calculation: ELO_agent = ELO_baseline + 400 * log10(wins/losses)
        if score_percentage > 0.99:
            score_percentage = 0.99  # Avoid division by zero
        elif score_percentage < 0.01:
            score_percentage = 0.01

        expected_score = 1 / (1 + 10 ** ((baseline_elo - 1200) / 400))
        elo_diff = 400 * np.log10(score_percentage / (1 - score_percentage))
        estimated_elo = baseline_elo + elo_diff

        elo_estimates.append(estimated_elo)

        if verbose:
            print(f"    Score: {score}/{games_per_opponent} ({score_percentage*100:.1f}%)")
            print(f"    Estimated ELO: {estimated_elo:.0f}")

    # Average across all opponents
    final_elo = np.mean(elo_estimates)

    if verbose:
        print(f"\n✅ Final ELO estimate: {final_elo:.0f}")

    return final_elo


def benchmark_against_gnuchess(
    agent: Any,
    levels: List[int] = [1, 2, 3, 4, 5],
    games_per_level: int = 5,
    engine_path: str = "/usr/games/gnuchess",
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Benchmark agent against GNU Chess levels.

    Args:
        agent: Agent to benchmark
        levels: GNU Chess skill levels to test
        games_per_level: Games per level
        engine_path: Path to GNU Chess
        verbose: Print progress

    Returns:
        Dictionary with benchmark results
    """
    if verbose:
        print(f"\n♟️  Benchmarking {agent.name} against GNU Chess...")

    results = {
        'levels': [],
        'scores': [],
        'win_rates': []
    }

    for level in levels:
        if verbose:
            print(f"\n📊 Level {level}:")

        wins = 0
        draws = 0
        losses = 0

        # Create engine agent wrapper
        class EngineAgent:
            def __init__(self, engine_path, skill_level):
                self.name = f"GNUChess-L{skill_level}"
                self.engine_path = engine_path
                self.skill_level = skill_level

            def get_move(self, board_state, board, temperature=1.0):
                with UCIEngineInterface(self.engine_path, skill_level=self.skill_level) as engine:
                    return engine.get_move(board)

        engine_agent = EngineAgent(engine_path, level)

        # Play games
        for game_num in range(games_per_level):
            # Alternate colors
            if game_num % 2 == 0:
                white, black = agent, engine_agent
            else:
                white, black = engine_agent, agent

            # Play game
            env = ChessEnvironment()
            move_count = 0
            max_moves = 200

            while not env.board.is_game_over() and move_count < max_moves:
                state = env.get_state()

                if env.board.turn == chess.WHITE:
                    move = white.get_move(state, env.board)
                else:
                    move = black.get_move(state, env.board)

                env.step(move)
                move_count += 1

            result = env.get_game_result()

            # Update statistics (from agent's perspective)
            if white == agent:
                if result == "1-0":
                    wins += 1
                elif result == "1/2-1/2":
                    draws += 1
                else:
                    losses += 1
            else:
                if result == "0-1":
                    wins += 1
                elif result == "1/2-1/2":
                    draws += 1
                else:
                    losses += 1

        score = wins + 0.5 * draws
        win_rate = (score / games_per_level) * 100

        results['levels'].append(level)
        results['scores'].append(score)
        results['win_rates'].append(win_rate)

        if verbose:
            print(f"   Score: {score}/{games_per_level} ({win_rate:.1f}%)")
            print(f"   W/D/L: {wins}/{draws}/{losses}")

    if verbose:
        print(f"\n✅ Benchmark complete!")

    return results


class SelfPlayTrainer:
    """
    Self-play trainer for chess agents.

    Implements iterative self-play training loop:
    1. Generate self-play games
    2. Train on game data
    3. Evaluate performance
    4. Repeat
    """

    def __init__(
        self,
        agent: Any,
        games_per_iteration: int = 10,
        training_epochs: int = 5,
        batch_size: int = 32
    ):
        """
        Initialize self-play trainer.

        Args:
            agent: Chess agent to train
            games_per_iteration: Self-play games per iteration
            training_epochs: Training epochs per iteration
            batch_size: Training batch size
        """
        self.agent = agent
        self.games_per_iteration = games_per_iteration
        self.training_epochs = training_epochs
        self.batch_size = batch_size

        self.game_history = deque(maxlen=1000)  # Keep last 1000 games
        self.iteration = 0

    def run_iteration(self, verbose: bool = True) -> Dict[str, Any]:
        """
        Run single training iteration.

        Args:
            verbose: Print progress

        Returns:
            Dictionary with iteration statistics
        """
        if verbose:
            print(f"\n🔄 Training Iteration {self.iteration + 1}")
            print("="*70)

        # 1. Generate self-play games
        if verbose:
            print("\n1️⃣  Generating self-play games...")

        games = generate_selfplay_batch(
            self.agent,
            num_games=self.games_per_iteration,
            verbose=False
        )

        self.game_history.extend(games)

        # 2. Train on games
        if verbose:
            print(f"\n2️⃣  Training on {len(games)} games...")

        # Only train if agent has online_learn method (Prometheus)
        if hasattr(self.agent, 'online_learn'):
            self.agent.online_learn(
                games,
                epochs=self.training_epochs,
                batch_size=self.batch_size
            )
        elif hasattr(self.agent, 'pretrain'):
            self.agent.pretrain(
                games,
                epochs=self.training_epochs,
                batch_size=self.batch_size
            )

        # 3. Statistics
        results_counts = {'1-0': 0, '0-1': 0, '1/2-1/2': 0}
        for game in games:
            results_counts[game['result']] += 1

        stats = {
            'iteration': self.iteration + 1,
            'games_played': len(games),
            'white_wins': results_counts['1-0'],
            'black_wins': results_counts['0-1'],
            'draws': results_counts['1/2-1/2'],
            'total_games_history': len(self.game_history)
        }

        if verbose:
            print(f"\n📊 Iteration {self.iteration + 1} complete:")
            print(f"   White wins: {stats['white_wins']}")
            print(f"   Black wins: {stats['black_wins']}")
            print(f"   Draws: {stats['draws']}")

        self.iteration += 1

        return stats

    def train(
        self,
        num_iterations: int = 10,
        verbose: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Run multiple training iterations.

        Args:
            num_iterations: Number of iterations
            verbose: Print progress

        Returns:
            List of iteration statistics
        """
        if verbose:
            print(f"\n🚀 Starting self-play training for {num_iterations} iterations")

        all_stats = []

        for i in range(num_iterations):
            stats = self.run_iteration(verbose=verbose)
            all_stats.append(stats)

        if verbose:
            print(f"\n✅ Training complete: {num_iterations} iterations")

        return all_stats

# ============================================================================
# STOCKFISH BENCHMARKING
# ============================================================================

def benchmark_against_stockfish(
    agent: Any,
    elo_levels: List[int] = [800, 1000, 1200, 1400, 1600],
    games_per_level: int = 5,
    stockfish_path: str = "/usr/games/stockfish",
    time_limit: float = 0.1,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Benchmark agent against Stockfish at different ELO levels.

    Stockfish is the world's strongest chess engine. Benchmarking against
    it provides credible strength estimates.

    Args:
        agent: Agent to benchmark
        elo_levels: Stockfish ELO levels to test
        games_per_level: Games per ELO level
        stockfish_path: Path to Stockfish executable
        time_limit: Time limit per move in seconds
        verbose: Print progress

    Returns:
        Dictionary with benchmark results
    """
    if verbose:
        print(f"\n♟️  Benchmarking {agent.name} against Stockfish")
        print(f"   (World's strongest chess engine)")
        print("="*70)

    results = {
        'elo_levels': [],
        'scores': [],
        'win_rates': [],
        'estimated_elo': None
    }

    for elo in elo_levels:
        if verbose:
            print(f"\n📊 Stockfish ELO {elo}:")

        wins = 0
        draws = 0
        losses = 0

        # Create Stockfish agent wrapper
        class StockfishAgent:
            def __init__(self, stockfish_path, elo):
                self.name = f"Stockfish-{elo}"
                self.stockfish_path = stockfish_path
                self.elo = elo

            def get_move(self, board_state, board, temperature=1.0):
                # Use UCI interface with ELO limit
                with UCIEngineInterface(self.stockfish_path) as engine:
                    if engine.engine is not None:
                        # Set ELO limit
                        try:
                            engine.engine.configure({"UCI_LimitStrength": True})
                            engine.engine.configure({"UCI_Elo": self.elo})
                        except Exception:
                            pass  # Some Stockfish versions don't support ELO
                        return engine.get_move(board)
                # Fallback: random move
                return np.random.choice(list(board.legal_moves))

        stockfish_agent = StockfishAgent(stockfish_path, elo)

        # Play games
        for game_num in range(games_per_level):
            # Alternate colors
            if game_num % 2 == 0:
                white, black = agent, stockfish_agent
            else:
                white, black = stockfish_agent, agent

            # Play game
            env = ChessEnvironment()
            move_count = 0
            max_moves = 200

            while not env.board.is_game_over() and move_count < max_moves:
                state = env.get_state()

                if env.board.turn == chess.WHITE:
                    move = white.get_move(state, env.board)
                else:
                    move = black.get_move(state, env.board)

                env.step(move)
                move_count += 1

            result = env.get_game_result()

            # Update statistics (from agent's perspective)
            if white == agent:
                if result == "1-0":
                    wins += 1
                elif result == "1/2-1/2":
                    draws += 1
                else:
                    losses += 1
            else:
                if result == "0-1":
                    wins += 1
                elif result == "1/2-1/2":
                    draws += 1
                else:
                    losses += 1

        score = wins + 0.5 * draws
        win_rate = (score / games_per_level) * 100

        results['elo_levels'].append(elo)
        results['scores'].append(score)
        results['win_rates'].append(win_rate)

        if verbose:
            print(f"   Score: {score}/{games_per_level} ({win_rate:.1f}%)")
            print(f"   W/D/L: {wins}/{draws}/{losses}")

    # Estimate agent's ELO based on performance
    # Find ELO where agent scores ~50%
    win_rates = np.array(results['win_rates'])
    elo_levels_arr = np.array(results['elo_levels'])

    # Linear interpolation to find 50% point
    if len(win_rates) >= 2:
        if win_rates[-1] < 50 and win_rates[0] > 50:
            # Agent is between min and max
            estimated_elo = np.interp(50, win_rates[::-1], elo_levels_arr[::-1])
        elif win_rates[0] >= 50:
            # Agent is stronger than lowest level
            estimated_elo = elo_levels_arr[0] + (win_rates[0] - 50) * 10
        else:
            # Agent is weaker than highest level
            estimated_elo = elo_levels_arr[-1] - (50 - win_rates[-1]) * 10

        results['estimated_elo'] = estimated_elo

        if verbose:
            print(f"\n✅ Estimated ELO: ~{estimated_elo:.0f}")
    else:
        if verbose:
            print(f"\n⚠️  Need more data points for ELO estimate")

    if verbose:
        print("="*70)

    return results


def compare_stockfish_levels(
    agents: List[Any],
    elo_level: int = 1200,
    games_each: int = 5,
    stockfish_path: str = "/usr/games/stockfish",
    verbose: bool = True
) -> Dict[str, Dict[str, Any]]:
    """
    Compare multiple agents against same Stockfish level.

    Args:
        agents: List of agents to compare
        elo_level: Stockfish ELO level
        games_each: Games per agent
        stockfish_path: Path to Stockfish
        verbose: Print progress

    Returns:
        Dictionary mapping agent name → results
    """
    if verbose:
        print(f"\n📊 Comparing agents vs Stockfish-{elo_level}")
        print("="*70)

    results = {}

    for agent in agents:
        if verbose:
            print(f"\n🤖 {agent.name}:")

        benchmark = benchmark_against_stockfish(
            agent,
            elo_levels=[elo_level],
            games_per_level=games_each,
            stockfish_path=stockfish_path,
            verbose=False
        )

        results[agent.name] = {
            'score': benchmark['scores'][0],
            'win_rate': benchmark['win_rates'][0],
            'games': games_each
        }

        if verbose:
            print(f"   Score: {benchmark['scores'][0]}/{games_each} ({benchmark['win_rates'][0]:.1f}%)")

    if verbose:
        print("\n" + "="*70)

    return results
