#!/usr/bin/env python3
"""
Prometheus Connect4 Evolution - Pure Symbolic Meta-Learning Test

Tests whether evolutionary meta-learning works on a simpler game than chess.
Uses minimax search with evolving evaluation function weights.

This is a CLEAN TEST of meta-learning without neural networks or LLMs.
"""

import numpy as np
import json
import time
from typing import List, Tuple, Optional
from dataclasses import dataclass
import random

# ===========================
# Connect4 Game Logic
# ===========================

class Connect4:
    """Connect4 game state and rules"""

    def __init__(self):
        self.board = np.zeros((6, 7), dtype=int)  # 6 rows, 7 columns
        self.current_player = 1  # 1 or 2

    def copy(self):
        """Deep copy of game state"""
        new_game = Connect4()
        new_game.board = self.board.copy()
        new_game.current_player = self.current_player
        return new_game

    def get_valid_moves(self) -> List[int]:
        """Return list of valid column indices"""
        return [col for col in range(7) if self.board[0, col] == 0]

    def make_move(self, col: int) -> bool:
        """Drop piece in column, return True if successful"""
        if col < 0 or col >= 7 or self.board[0, col] != 0:
            return False

        # Find lowest empty row
        for row in range(5, -1, -1):
            if self.board[row, col] == 0:
                self.board[row, col] = self.current_player
                self.current_player = 3 - self.current_player  # Switch player
                return True
        return False

    def check_winner(self) -> Optional[int]:
        """Check if there's a winner. Returns 1, 2, or None"""
        # Check horizontal
        for row in range(6):
            for col in range(4):
                if self.board[row, col] != 0 and \
                   all(self.board[row, col + i] == self.board[row, col] for i in range(4)):
                    return self.board[row, col]

        # Check vertical
        for row in range(3):
            for col in range(7):
                if self.board[row, col] != 0 and \
                   all(self.board[row + i, col] == self.board[row, col] for i in range(4)):
                    return self.board[row, col]

        # Check diagonal (down-right)
        for row in range(3):
            for col in range(4):
                if self.board[row, col] != 0 and \
                   all(self.board[row + i, col + i] == self.board[row, col] for i in range(4)):
                    return self.board[row, col]

        # Check diagonal (down-left)
        for row in range(3):
            for col in range(3, 7):
                if self.board[row, col] != 0 and \
                   all(self.board[row + i, col - i] == self.board[row, col] for i in range(4)):
                    return self.board[row, col]

        return None

    def is_full(self) -> bool:
        """Check if board is full (draw)"""
        return np.all(self.board[0, :] != 0)

    def display(self):
        """Pretty print board"""
        symbols = {0: '·', 1: 'X', 2: 'O'}
        for row in self.board:
            print(' '.join(symbols[cell] for cell in row))
        print('0 1 2 3 4 5 6')


# ===========================
# Evaluation Function
# ===========================

@dataclass
class EvalWeights:
    """Weights for position evaluation"""
    win_score: float = 1000.0
    three_in_row: float = 10.0
    two_in_row: float = 3.0
    center_control: float = 5.0
    block_opponent: float = 15.0

    def mutate(self, mutation_rate: float = 0.2):
        """Create mutated copy"""
        new_weights = EvalWeights()
        for field in ['three_in_row', 'two_in_row', 'center_control', 'block_opponent']:
            current = getattr(self, field)
            if random.random() < mutation_rate:
                # Mutate by ±30%
                multiplier = random.uniform(0.7, 1.3)
                setattr(new_weights, field, current * multiplier)
            else:
                setattr(new_weights, field, current)
        return new_weights

    def to_dict(self):
        return {
            'three_in_row': self.three_in_row,
            'two_in_row': self.two_in_row,
            'center_control': self.center_control,
            'block_opponent': self.block_opponent
        }


def evaluate_position(game: Connect4, player: int, weights: EvalWeights) -> float:
    """Evaluate position for given player using weights"""
    # Check for immediate win/loss
    winner = game.check_winner()
    if winner == player:
        return weights.win_score
    elif winner is not None:
        return -weights.win_score

    score = 0.0

    # Count patterns for both players
    for p in [player, 3 - player]:
        multiplier = 1.0 if p == player else -weights.block_opponent / 15.0

        # Horizontal patterns
        for row in range(6):
            for col in range(4):
                window = game.board[row, col:col+4]
                score += score_window(window, p, weights) * multiplier

        # Vertical patterns
        for row in range(3):
            for col in range(7):
                window = game.board[row:row+4, col]
                score += score_window(window, p, weights) * multiplier

        # Diagonal patterns
        for row in range(3):
            for col in range(4):
                window = np.array([game.board[row+i, col+i] for i in range(4)])
                score += score_window(window, p, weights) * multiplier

        # Anti-diagonal patterns
        for row in range(3):
            for col in range(3, 7):
                window = np.array([game.board[row+i, col-i] for i in range(4)])
                score += score_window(window, p, weights) * multiplier

    # Center control bonus
    center_col = game.board[:, 3]
    score += np.sum(center_col == player) * weights.center_control

    return score


def score_window(window: np.ndarray, player: int, weights: EvalWeights) -> float:
    """Score a 4-cell window"""
    player_count = np.sum(window == player)
    empty_count = np.sum(window == 0)
    opponent_count = 4 - player_count - empty_count

    if opponent_count > 0:
        return 0.0  # Window blocked by opponent

    if player_count == 3 and empty_count == 1:
        return weights.three_in_row
    elif player_count == 2 and empty_count == 2:
        return weights.two_in_row

    return 0.0


# ===========================
# Minimax Search
# ===========================

def minimax(game: Connect4, depth: int, alpha: float, beta: float,
            maximizing: bool, player: int, weights: EvalWeights) -> Tuple[float, Optional[int]]:
    """Minimax with alpha-beta pruning"""
    # Terminal conditions
    winner = game.check_winner()
    if winner == player:
        return weights.win_score * (depth + 1), None  # Prefer faster wins
    elif winner is not None:
        return -weights.win_score * (depth + 1), None
    elif game.is_full() or depth == 0:
        return evaluate_position(game, player, weights), None

    valid_moves = game.get_valid_moves()

    if maximizing:
        max_eval = -float('inf')
        best_move = valid_moves[0] if valid_moves else None

        for move in valid_moves:
            game_copy = game.copy()
            game_copy.make_move(move)
            eval_score, _ = minimax(game_copy, depth - 1, alpha, beta, False, player, weights)

            if eval_score > max_eval:
                max_eval = eval_score
                best_move = move

            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break  # Prune

        return max_eval, best_move
    else:
        min_eval = float('inf')
        best_move = valid_moves[0] if valid_moves else None

        for move in valid_moves:
            game_copy = game.copy()
            game_copy.make_move(move)
            eval_score, _ = minimax(game_copy, depth - 1, alpha, beta, True, player, weights)

            if eval_score < min_eval:
                min_eval = eval_score
                best_move = move

            beta = min(beta, eval_score)
            if beta <= alpha:
                break  # Prune

        return min_eval, best_move


def get_best_move(game: Connect4, depth: int, weights: EvalWeights) -> int:
    """Get best move for current player"""
    _, move = minimax(game, depth, -float('inf'), float('inf'),
                     True, game.current_player, weights)
    return move if move is not None else random.choice(game.get_valid_moves())


# ===========================
# Evolution
# ===========================

def play_game(weights1: EvalWeights, weights2: EvalWeights, depth: int = 6) -> int:
    """Play a game between two weight sets. Returns 1, 2, or 0 (draw)"""
    game = Connect4()

    while True:
        if game.current_player == 1:
            move = get_best_move(game, depth, weights1)
        else:
            move = get_best_move(game, depth, weights2)

        game.make_move(move)

        winner = game.check_winner()
        if winner is not None:
            return winner
        if game.is_full():
            return 0  # Draw


def evaluate_weights(weights: EvalWeights, opponents: List[EvalWeights],
                     games_per_opponent: int = 5, depth: int = 6) -> float:
    """Evaluate weights against multiple opponents"""
    total_score = 0.0
    total_games = 0

    for opponent in opponents:
        for _ in range(games_per_opponent):
            # Play as player 1
            result = play_game(weights, opponent, depth)
            total_score += 1.0 if result == 1 else (0.5 if result == 0 else 0.0)
            total_games += 1

            # Play as player 2
            result = play_game(opponent, weights, depth)
            total_score += 1.0 if result == 2 else (0.5 if result == 0 else 0.0)
            total_games += 1

    return total_score / total_games if total_games > 0 else 0.0


def evolve_connect4(population_size: int = 10, generations: int = 20,
                    mutation_rate: float = 0.3, depth: int = 6):
    """Evolve Connect4 playing weights"""

    print("\n" + "=" * 80)
    print("🧬 Prometheus Connect4 Evolution - Pure Symbolic Meta-Learning")
    print("=" * 80)
    print(f"\n  Population: {population_size}")
    print(f"  Generations: {generations}")
    print(f"  Search depth: {depth}")
    print(f"  Mutation rate: {mutation_rate}")
    print("\n" + "=" * 80 + "\n")

    # Initialize population
    population = [EvalWeights() for _ in range(population_size)]

    # Add some diversity
    for i in range(1, population_size):
        population[i] = population[0].mutate(mutation_rate=1.0)

    best_overall = None
    best_overall_fitness = 0.0
    fitness_history = []

    start_time = time.time()

    for gen in range(generations):
        gen_start = time.time()

        # Evaluate population
        fitnesses = []
        for i, weights in enumerate(population):
            # Evaluate against random subset of population (tournament)
            opponents = random.sample(population[:i] + population[i+1:],
                                    min(5, population_size - 1))
            fitness = evaluate_weights(weights, opponents, games_per_opponent=3, depth=depth)
            fitnesses.append(fitness)

        # Track best
        best_idx = np.argmax(fitnesses)
        best_fitness = fitnesses[best_idx]
        mean_fitness = np.mean(fitnesses)
        worst_fitness = np.min(fitnesses)

        if best_fitness > best_overall_fitness:
            best_overall = population[best_idx]
            best_overall_fitness = best_fitness

        fitness_history.append({
            'generation': gen,
            'best': best_fitness,
            'mean': mean_fitness,
            'worst': worst_fitness,
            'weights': population[best_idx].to_dict()
        })

        gen_time = time.time() - gen_start

        print(f"Gen {gen:3d} | Best: {best_fitness:.3f} | "
              f"Mean: {mean_fitness:.3f} | Worst: {worst_fitness:.3f} | "
              f"Time: {gen_time:.1f}s")

        # Check convergence
        if best_fitness >= 0.90:
            print(f"\n🎉 Converged! Reached {best_fitness:.1%} win rate")
            break

        # Selection and reproduction
        new_population = []

        # Elitism: Keep top 2
        elite_indices = np.argsort(fitnesses)[-2:]
        for idx in elite_indices:
            new_population.append(population[idx])

        # Tournament selection for rest
        while len(new_population) < population_size:
            # Tournament
            contestants = random.sample(list(enumerate(population)), 3)
            winner_idx = max(contestants, key=lambda x: fitnesses[x[0]])[0]

            # Mutate winner
            new_weights = population[winner_idx].mutate(mutation_rate)
            new_population.append(new_weights)

        population = new_population

    total_time = time.time() - start_time

    print("\n" + "=" * 80)
    print("✅ Evolution Complete!")
    print("=" * 80)
    print(f"\n  Generations: {len(fitness_history)}")
    print(f"  Best fitness: {best_overall_fitness:.1%}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Time/gen: {total_time / len(fitness_history):.1f}s")

    if fitness_history:
        initial_best = fitness_history[0]['best']
        final_best = fitness_history[-1]['best']
        improvement = final_best - initial_best

        print(f"\n  Initial: {initial_best:.1%}")
        print(f"  Final: {final_best:.1%}")
        print(f"  Improvement: +{improvement:.1%}")

        print("\n  Best weights found:")
        for key, val in best_overall.to_dict().items():
            print(f"    {key}: {val:.2f}")

    # Save results
    results = {
        'generations': len(fitness_history),
        'best_fitness': best_overall_fitness,
        'best_weights': best_overall.to_dict() if best_overall else None,
        'fitness_history': fitness_history,
        'config': {
            'population_size': population_size,
            'generations': generations,
            'mutation_rate': mutation_rate,
            'depth': depth
        }
    }

    with open('connect4_evolution_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\n  Results saved to: connect4_evolution_results.json")
    print("\n" + "=" * 80)

    return best_overall, fitness_history


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Evolve Connect4 playing weights')
    parser.add_argument('--population', type=int, default=10, help='Population size')
    parser.add_argument('--generations', type=int, default=20, help='Number of generations')
    parser.add_argument('--depth', type=int, default=6, help='Minimax search depth')
    parser.add_argument('--mutation-rate', type=float, default=0.3, help='Mutation rate')

    args = parser.parse_args()

    best_weights, history = evolve_connect4(
        population_size=args.population,
        generations=args.generations,
        mutation_rate=args.mutation_rate,
        depth=args.depth
    )

    print("\n💡 Key Insights:")
    print("  ✓ Pure symbolic evolution (no neural networks)")
    print("  ✓ Meta-learning through weight evolution")
    print("  ✓ Simpler than chess, easier to measure learning")
    print("  ✓ If this works → Apply to chess with better evaluation")
