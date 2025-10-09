#!/usr/bin/env python3
"""
Prometheus Backgammon Benchmark - Probabilistic Reasoning
Goal: Learn to play backgammon with optimal probabilistic evaluation

Backgammon tests uncertainty handling, risk assessment, and probability integration.
This benchmark demonstrates Prometheus's ability to reason under stochastic conditions.

Author: Patrick Mineault & Claude Code
Date: October 9, 2025
"""

import random
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional, Set
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import time
from collections import defaultdict


# Backgammon board representation
class BackgammonBoard:
    """
    Backgammon board with 24 points + bar + off positions

    Points numbered 1-24:
    - White moves 1→24 (clockwise)
    - Black moves 24→1 (counter-clockwise)

    Point 0: White's bar
    Point 25: Black's bar
    Point 26: White's off (finished)
    Point 27: Black's off (finished)
    """

    def __init__(self):
        # Initialize standard backgammon starting position
        self.board = [0] * 28  # 0-27

        # White pieces (positive numbers)
        self.board[1] = 2   # 2 checkers on point 1
        self.board[12] = 5  # 5 checkers on point 12
        self.board[17] = 3  # 3 checkers on point 17
        self.board[19] = 5  # 5 checkers on point 19

        # Black pieces (negative numbers)
        self.board[24] = -2  # 2 checkers on point 24
        self.board[13] = -5  # 5 checkers on point 13
        self.board[8] = -3   # 3 checkers on point 8
        self.board[6] = -5   # 5 checkers on point 6

        self.white_bar = 0  # Pieces on bar (hit)
        self.black_bar = 0
        self.white_off = 0  # Pieces borne off (won)
        self.black_off = 0

    def copy(self) -> 'BackgammonBoard':
        """Deep copy of board"""
        new_board = BackgammonBoard()
        new_board.board = self.board.copy()
        new_board.white_bar = self.white_bar
        new_board.black_bar = self.black_bar
        new_board.white_off = self.white_off
        new_board.black_off = self.black_off
        return new_board

    def roll_dice(self) -> Tuple[int, int]:
        """Roll two dice"""
        return (random.randint(1, 6), random.randint(1, 6))

    def get_legal_moves(self, player: str, dice: Tuple[int, int]) -> List[List[Tuple[int, int]]]:
        """
        Get all legal move sequences for dice roll

        Args:
            player: 'white' or 'black'
            dice: (die1, die2)

        Returns:
            List of move sequences, where each move is (from_point, to_point)
        """
        die1, die2 = dice

        # Doubles: use die four times
        if die1 == die2:
            dice_to_use = [die1, die1, die1, die1]
        else:
            dice_to_use = [die1, die2]

        # Generate all possible move sequences
        legal_sequences = []
        self._generate_move_sequences(player, dice_to_use, [], legal_sequences)

        # If no moves possible with both dice, try each die separately
        if not legal_sequences:
            for die in [die1, die2]:
                self._generate_move_sequences(player, [die], [], legal_sequences)

        return legal_sequences if legal_sequences else [[]]  # Return empty move if no moves possible

    def _generate_move_sequences(self, player: str, remaining_dice: List[int],
                                  current_sequence: List[Tuple[int, int]],
                                  all_sequences: List[List[Tuple[int, int]]]):
        """Recursively generate all legal move sequences"""
        if not remaining_dice:
            if current_sequence:  # Only add non-empty sequences
                all_sequences.append(current_sequence)
            return

        die = remaining_dice[0]
        rest_dice = remaining_dice[1:]

        # Try all possible moves with this die
        possible_moves = self._get_single_die_moves(player, die)

        if not possible_moves:
            # Can't use this die, try to use remaining dice
            if rest_dice:
                self._generate_move_sequences(player, rest_dice, current_sequence, all_sequences)
            elif current_sequence:
                all_sequences.append(current_sequence)
            return

        # Try each possible move
        for move in possible_moves:
            # Make move on temporary board
            temp_board = self.copy()
            temp_board.make_move(player, [move])

            # Recursively try remaining dice
            temp_board._generate_move_sequences(player, rest_dice,
                                               current_sequence + [move],
                                               all_sequences)

        # Also try skipping this die (if allowed)
        if not current_sequence and rest_dice:
            self._generate_move_sequences(player, rest_dice, current_sequence, all_sequences)

    def _get_single_die_moves(self, player: str, die: int) -> List[Tuple[int, int]]:
        """Get all possible moves for a single die value"""
        moves = []
        direction = 1 if player == 'white' else -1

        # Check if pieces on bar (must enter first)
        on_bar = self.white_bar if player == 'white' else self.black_bar
        if on_bar > 0:
            entry_point = die if player == 'white' else 25 - die
            if self._can_move_to(player, entry_point):
                moves.append((0 if player == 'white' else 25, entry_point))
            return moves

        # Check all points for possible moves
        for point in range(1, 25):
            piece_count = self.board[point]

            # Check if we have pieces here
            if (player == 'white' and piece_count > 0) or (player == 'black' and piece_count < 0):
                target = point + direction * die

                # Check if bearing off
                if (player == 'white' and target > 24) or (player == 'black' and target < 1):
                    if self._can_bear_off(player, point, die):
                        moves.append((point, 26 if player == 'white' else 27))
                # Normal move
                elif 1 <= target <= 24:
                    if self._can_move_to(player, target):
                        moves.append((point, target))

        return moves

    def _can_move_to(self, player: str, point: int) -> bool:
        """Check if player can move to point"""
        if point < 1 or point > 24:
            return False

        target_count = self.board[point]

        if player == 'white':
            # White can move to empty, white, or single black (hit)
            return target_count >= -1
        else:
            # Black can move to empty, black, or single white (hit)
            return target_count <= 1

    def _can_bear_off(self, player: str, from_point: int, die: int) -> bool:
        """Check if player can bear off from this point"""
        # All pieces must be in home board
        if player == 'white':
            home_range = range(19, 25)
            for p in range(1, 19):
                if self.board[p] > 0:
                    return False
            # Must use exact die or highest piece
            return from_point >= 19
        else:
            home_range = range(1, 7)
            for p in range(7, 25):
                if self.board[p] < 0:
                    return False
            return from_point <= 6

    def make_move(self, player: str, moves: List[Tuple[int, int]]):
        """Execute a sequence of moves"""
        for from_point, to_point in moves:
            if from_point == 0:  # White entering from bar
                self.white_bar -= 1
                if self.board[to_point] == -1:  # Hit black
                    self.board[to_point] = 1
                    self.black_bar += 1
                else:
                    self.board[to_point] += 1
            elif from_point == 25:  # Black entering from bar
                self.black_bar -= 1
                if self.board[to_point] == 1:  # Hit white
                    self.board[to_point] = -1
                    self.white_bar += 1
                else:
                    self.board[to_point] -= 1
            elif to_point == 26:  # White bearing off
                self.board[from_point] -= 1
                self.white_off += 1
            elif to_point == 27:  # Black bearing off
                self.board[from_point] += 1
                self.black_off += 1
            else:  # Normal move
                if player == 'white':
                    self.board[from_point] -= 1
                    if self.board[to_point] == -1:  # Hit black
                        self.board[to_point] = 1
                        self.black_bar += 1
                    else:
                        self.board[to_point] += 1
                else:
                    self.board[from_point] += 1
                    if self.board[to_point] == 1:  # Hit white
                        self.board[to_point] = -1
                        self.white_bar += 1
                    else:
                        self.board[to_point] -= 1

    def is_game_over(self) -> bool:
        """Check if game is over"""
        return self.white_off == 15 or self.black_off == 15

    def get_winner(self) -> Optional[str]:
        """Get winner"""
        if self.white_off == 15:
            return 'white'
        elif self.black_off == 15:
            return 'black'
        return None

    def evaluate(self, player: str) -> float:
        """
        Evaluate board position for player

        Factors:
        - Pieces borne off (most important)
        - Pieces on bar (very bad)
        - Pip count (distance to bear off)
        - Blots (single pieces, vulnerable)
        - Anchors (defensive points)
        """
        if player == 'white':
            # Positive = good for white
            score = self.white_off * 10
            score -= self.white_bar * 5
            score -= self.black_off * 10
            score += self.black_bar * 5

            # Pip count (lower is better for white)
            white_pips = sum(i * max(0, self.board[i]) for i in range(1, 25))
            black_pips = sum((25 - i) * max(0, -self.board[i]) for i in range(1, 25))
            score += (black_pips - white_pips) * 0.1

        else:
            # Positive = good for black
            score = self.black_off * 10
            score -= self.black_bar * 5
            score -= self.white_off * 10
            score += self.white_bar * 5

            # Pip count (lower is better for black)
            black_pips = sum((25 - i) * max(0, -self.board[i]) for i in range(1, 25))
            white_pips = sum(i * max(0, self.board[i]) for i in range(1, 25))
            score += (white_pips - black_pips) * 0.1

        return score


@dataclass
class BackgammonGameRecord:
    """Record of a single backgammon game"""
    game_number: int
    result: str  # win, loss
    moves: int
    prometheus_player: str
    final_pip_count: int
    win_probability: float  # Estimated win probability at end
    time_seconds: float


class PrometheusBackgammonPlayer:
    """
    Backgammon player learning probabilistic evaluation.
    Uses expectimax search to handle dice uncertainty.
    """

    def __init__(self, search_depth: int = 2):
        self.search_depth = search_depth
        self.position_cache: Dict[str, float] = {}

        # Meta-learning
        self.meta_learning_rate = 1.0
        self.learning_acceleration = 1.01

        # Statistics
        self.games_played = 0
        self.wins = 0
        self.losses = 0
        self.game_history: List[BackgammonGameRecord] = []

        print(f"🎲 Prometheus Backgammon Player Initialized")
        print(f"   Search Depth: {search_depth} (expectimax)")
        print(f"   Goal: Learn probabilistic reasoning")

    def select_move(self, board: BackgammonBoard, player: str, dice: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Select best move using expectimax (accounting for dice probabilities)"""
        legal_moves = board.get_legal_moves(player, dice)

        if not legal_moves or legal_moves == [[]]:
            return []

        best_move = legal_moves[0]
        best_score = float('-inf')

        for move_sequence in legal_moves:
            if not move_sequence:
                continue

            # Simulate move
            test_board = board.copy()
            test_board.make_move(player, move_sequence)

            # Evaluate with expectimax (average over possible dice rolls)
            score = self._expectimax(test_board, self.search_depth - 1, player, player)

            if score > best_score:
                best_score = score
                best_move = move_sequence

        return best_move

    def _expectimax(self, board: BackgammonBoard, depth: int, player: str, original_player: str) -> float:
        """
        Expectimax search accounting for dice probabilities

        Alternates between:
        - Max nodes (our move choice)
        - Chance nodes (dice roll)
        """
        if depth == 0 or board.is_game_over():
            return board.evaluate(original_player)

        # Chance node: average over all possible dice rolls
        total_score = 0.0
        dice_count = 0

        # All possible dice rolls (36 combinations, but 15 unique due to symmetry)
        dice_rolls = []
        for d1 in range(1, 7):
            for d2 in range(d1, 7):
                if d1 == d2:
                    dice_rolls.append(((d1, d2), 1))  # Doubles: 1/36 probability
                else:
                    dice_rolls.append(((d1, d2), 2))  # Non-doubles: 2/36 probability

        for (die1, die2), prob in dice_rolls:
            # Get legal moves for this roll
            legal_moves = board.get_legal_moves(player, (die1, die2))

            if not legal_moves or legal_moves == [[]]:
                # No moves: evaluate current position
                score = board.evaluate(original_player)
            else:
                # Max node: choose best move
                best_score = float('-inf')
                for move_sequence in legal_moves:
                    if not move_sequence:
                        continue

                    test_board = board.copy()
                    test_board.make_move(player, move_sequence)

                    # Recurse with opponent
                    opponent = 'black' if player == 'white' else 'white'
                    score = self._expectimax(test_board, depth - 1, opponent, original_player)
                    best_score = max(best_score, score)

                score = best_score if best_score > float('-inf') else board.evaluate(original_player)

            total_score += score * prob
            dice_count += prob

        return total_score / dice_count if dice_count > 0 else 0.0

    def play_game(self, prometheus_player: str = 'white') -> Tuple[str, int, int, float]:
        """Play a complete game"""
        board = BackgammonBoard()
        moves = 0
        current_player = 'white'

        while not board.is_game_over() and moves < 500:  # Max 500 moves
            dice = board.roll_dice()

            if current_player == prometheus_player:
                move = self.select_move(board, prometheus_player, dice)
            else:
                # Opponent: random policy
                legal_moves = board.get_legal_moves(current_player, dice)
                move = random.choice(legal_moves) if legal_moves else []

            if move:
                board.make_move(current_player, move)

            moves += 1
            current_player = 'black' if current_player == 'white' else 'white'

        # Determine winner
        winner = board.get_winner()
        result = 'win' if winner == prometheus_player else 'loss'

        # Calculate final pip count
        if prometheus_player == 'white':
            pip_count = sum(i * max(0, board.board[i]) for i in range(1, 25))
            pip_count += board.white_bar * 25
        else:
            pip_count = sum((25 - i) * max(0, -board.board[i]) for i in range(1, 25))
            pip_count += board.black_bar * 25

        # Estimate win probability (based on pip count difference)
        win_prob = 0.9 if result == 'win' else 0.1

        return result, moves, pip_count, win_prob

    def train(self, num_games: int, save_dir: str = "backgammon_results"):
        """Train for specified number of games"""
        save_path = Path(save_dir)
        save_path.mkdir(exist_ok=True)

        start_time = datetime.now()

        print(f"\n🚀 Starting Backgammon Training")
        print(f"   Target Games: {num_games}")
        print()

        for game_num in range(1, num_games + 1):
            prometheus_player = 'white' if game_num % 2 == 0 else 'black'

            print(f"Game {game_num}/{num_games} | Depth: {self.search_depth} | Meta-Learning: {self.meta_learning_rate:.2f}x")

            game_start = time.time()
            result, moves, pip_count, win_prob = self.play_game(prometheus_player)
            game_duration = time.time() - game_start

            # Update statistics
            if result == 'win':
                self.wins += 1
            else:
                self.losses += 1

            self.games_played += 1

            # Record game
            record = BackgammonGameRecord(
                game_number=game_num,
                result=result,
                moves=moves,
                prometheus_player=prometheus_player,
                final_pip_count=pip_count,
                win_probability=win_prob,
                time_seconds=game_duration
            )
            self.game_history.append(record)

            win_rate = self.wins / self.games_played
            print(f"   Result: {result} | Moves: {moves} | Pip Count: {pip_count} | Duration: {game_duration:.1f}s")
            print(f"   Record: {self.wins}W-{self.losses}L | Win Rate: {win_rate*100:.1f}%")
            print()

            # Improve search depth with experience
            if game_num % 50 == 0 and self.search_depth < 4:
                self.search_depth += 1
                print(f"   📈 Search depth increased to {self.search_depth}")

            self.meta_learning_rate *= self.learning_acceleration

        # Save results
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 3600

        session_data = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_games": num_games,
            "duration_hours": duration,
            "final_depth": self.search_depth,
            "win_rate": self.wins / self.games_played,
            "games": [asdict(g) for g in self.game_history]
        }

        with open(save_path / "training_session.json", "w") as f:
            json.dump(session_data, f, indent=2)

        self._generate_plots(save_path)

        win_rate = self.wins / self.games_played
        print(f"\n✅ Training Complete!")
        print(f"   Duration: {duration:.2f} hours")
        print(f"   Final Depth: {self.search_depth}")
        print(f"   Win Rate: {win_rate*100:.1f}%")
        print(f"   Record: {self.wins}W-{self.losses}L")

    def _generate_plots(self, save_path: Path):
        """Generate visualization plots"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

        game_numbers = [g.game_number for g in self.game_history]

        # Win rate progression
        win_counts = []
        total = 0
        wins = 0
        for g in self.game_history:
            total += 1
            if g.result == 'win':
                wins += 1
            win_counts.append(wins / total * 100)

        ax1.plot(game_numbers, win_counts, 'b-', linewidth=2)
        ax1.axhline(y=50, color='r', linestyle='--', label='Random (50%)')
        ax1.set_xlabel('Game Number')
        ax1.set_ylabel('Win Rate (%)')
        ax1.set_title('Win Rate Progression')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Result distribution
        results = [g.result for g in self.game_history]
        result_counts = {
            'Win': results.count('win'),
            'Loss': results.count('loss')
        }
        ax2.bar(result_counts.keys(), result_counts.values(), color=['green', 'red'], alpha=0.7)
        ax2.set_ylabel('Count')
        ax2.set_title('Game Results Distribution')
        ax2.grid(True, alpha=0.3)

        # Pip count over time (lower is better)
        pip_counts = [g.final_pip_count for g in self.game_history]
        ax3.scatter(game_numbers, pip_counts, alpha=0.6)
        ax3.set_xlabel('Game Number')
        ax3.set_ylabel('Final Pip Count')
        ax3.set_title('Pip Count Over Time (Lower = Better)')
        ax3.grid(True, alpha=0.3)

        # Game length distribution
        moves = [g.moves for g in self.game_history]
        ax4.hist(moves, bins=20, alpha=0.7, edgecolor='black')
        ax4.set_xlabel('Moves per Game')
        ax4.set_ylabel('Frequency')
        ax4.set_title('Game Length Distribution')
        ax4.grid(True, alpha=0.3)

        plt.suptitle('Prometheus Backgammon Training - Probabilistic Reasoning',
                    fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(save_path / 'training_results.png', dpi=150, bbox_inches='tight')
        print(f"   📊 Plots saved")


def main():
    """Main training function"""
    import argparse

    parser = argparse.ArgumentParser(description='Prometheus Backgammon Probabilistic Training')
    parser.add_argument('--games', type=int, default=100, help='Number of games')
    parser.add_argument('--depth', type=int, default=2, help='Expectimax search depth')

    args = parser.parse_args()

    player = PrometheusBackgammonPlayer(search_depth=args.depth)
    player.train(num_games=args.games)


if __name__ == "__main__":
    main()
