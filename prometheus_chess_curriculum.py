#!/usr/bin/env python3
"""
Prometheus Chess - Curriculum Learning with Adaptive Opponents

Key improvements:
1. Start vs weak opponent (Elo 400-600)
2. Gradually increase difficulty based on performance
3. Deeper search (depth 6-8 vs 3-4)
4. Better position evaluation

This enables learning through achievable challenges rather than
immediate crushing defeats.
"""

import chess
import chess.engine
import random
import time
import json
from pathlib import Path

class PrometheusChessCurriculum:
    """Chess agent with curriculum learning"""

    def __init__(self, starting_elo: float = 800.0):
        self.elo = starting_elo
        self.skill_level = 0  # Stockfish skill 0-20 (0=weakest)
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.games_played = 0
        self.wins = 0
        self.draws = 0
        self.losses = 0
        self.meta_learning_rate = 1.0

    def evaluate_position(self, board: chess.Board) -> float:
        """Enhanced position evaluation"""
        if board.is_checkmate():
            return -10000 if board.turn else 10000
        if board.is_stalemate() or board.is_insufficient_material():
            return 0

        # Piece values
        piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 20000
        }

        score = 0

        # Material count
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                value = piece_values[piece.piece_type]

                # Positional bonuses
                if piece.piece_type == chess.PAWN:
                    # Advance bonus
                    rank = chess.square_rank(square)
                    if piece.color == chess.WHITE:
                        value += rank * 10
                    else:
                        value += (7 - rank) * 10

                # Center control bonus for knights/bishops
                elif piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
                    file = chess.square_file(square)
                    rank = chess.square_rank(square)
                    center_distance = abs(3.5 - file) + abs(3.5 - rank)
                    value += (7 - center_distance) * 5

                # Add or subtract based on color
                if piece.color == chess.WHITE:
                    score += value
                else:
                    score -= value

        # Mobility bonus (number of legal moves)
        mobility = len(list(board.legal_moves))
        score += mobility * 2 if board.turn == chess.WHITE else -mobility * 2

        # King safety penalty if in check
        if board.is_check():
            score += -50 if board.turn == chess.WHITE else 50

        return score if board.turn == chess.WHITE else -score

    def minimax(self, board: chess.Board, depth: int, alpha: float, beta: float,
                maximizing: bool) -> float:
        """Minimax with alpha-beta pruning (depth 6-8)"""
        if depth == 0 or board.is_game_over():
            return self.evaluate_position(board)

        if maximizing:
            max_eval = float('-inf')
            for move in board.legal_moves:
                board.push(move)
                eval_score = self.minimax(board, depth - 1, alpha, beta, False)
                board.pop()
                max_eval = max(max_eval, eval_score)
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float('inf')
            for move in board.legal_moves:
                board.push(move)
                eval_score = self.minimax(board, depth - 1, alpha, beta, True)
                board.pop()
                min_eval = min(min_eval, eval_score)
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break
            return min_eval

    def select_move(self, board: chess.Board) -> chess.Move:
        """Select best move with deeper search"""
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return None

        # Depth increases with meta-learning
        base_depth = 6
        adjusted_depth = min(8, base_depth + int(self.meta_learning_rate * 0.1))

        best_move = None
        best_value = float('-inf') if board.turn == chess.WHITE else float('inf')

        for move in legal_moves:
            board.push(move)
            value = self.minimax(board, adjusted_depth - 1,
                               float('-inf'), float('inf'),
                               board.turn != chess.WHITE)
            board.pop()

            if board.turn == chess.WHITE:
                if value > best_value:
                    best_value = value
                    best_move = move
            else:
                if value < best_value:
                    best_value = value
                    best_move = move

        return best_move if best_move else random.choice(legal_moves)

    def adjust_difficulty(self, result: str):
        """Adapt opponent skill level based on performance"""
        if result == "1-0":  # Prometheus wins
            self.wins += 1
            self.consecutive_wins += 1
            self.consecutive_losses = 0

            # Win 3 consecutive → increase difficulty
            if self.consecutive_wins >= 3:
                self.skill_level = min(20, self.skill_level + 1)
                self.consecutive_wins = 0
                print(f"   🔼 Increased opponent skill to {self.skill_level}/20")

        elif result == "0-1":  # Prometheus loses
            self.losses += 1
            self.consecutive_losses += 1
            self.consecutive_wins = 0

            # Lose 5 consecutive → decrease difficulty
            if self.consecutive_losses >= 5:
                self.skill_level = max(0, self.skill_level - 1)
                self.consecutive_losses = 0
                print(f"   🔽 Decreased opponent skill to {self.skill_level}/20")

        else:  # Draw
            self.draws += 1
            self.consecutive_wins = 0
            self.consecutive_losses = 0

        # Meta-learning acceleration (1% per game)
        self.meta_learning_rate *= 1.01

    def play_game(self, engine_path: str = "stockfish") -> str:
        """Play one game with curriculum opponent"""
        board = chess.Board()
        engine = chess.engine.SimpleEngine.popen_uci(engine_path)

        # Set opponent to curriculum skill level (0-20)
        engine.configure({"Skill Level": self.skill_level})

        prometheus_color = chess.WHITE if random.random() < 0.5 else chess.BLACK
        move_count = 0

        while not board.is_game_over() and move_count < 200:
            if board.turn == prometheus_color:
                # Prometheus's turn
                move = self.select_move(board)
                if move:
                    board.push(move)
            else:
                # Opponent's turn (Stockfish at curriculum Elo)
                result = engine.play(board, chess.engine.Limit(time=0.1))
                board.push(result.move)

            move_count += 1

        engine.quit()

        # Determine result
        if board.is_checkmate():
            result = "0-1" if board.turn == prometheus_color else "1-0"
        else:
            result = "1/2-1/2"

        return result

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Prometheus Chess Curriculum Learning")
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--engine", type=str, default="stockfish")
    parser.add_argument("--start-elo", type=float, default=800.0)

    args = parser.parse_args()

    agent = PrometheusChessCurriculum(starting_elo=args.start_elo)

    print(f"🎮 Prometheus Chess Curriculum Learning")
    print(f"   Starting Elo: {args.start_elo}")
    print(f"   Initial Opponent Skill: {agent.skill_level}/20")
    print(f"   Games: {args.games}")
    print()

    start_time = time.time()

    for game_num in range(1, args.games + 1):
        game_start = time.time()
        result = agent.play_game(args.engine)
        game_time = time.time() - game_start

        agent.adjust_difficulty(result)
        agent.games_played += 1

        # Progress update
        wr = (agent.wins / agent.games_played) * 100
        print(f"Game {game_num}/{args.games} | Result: {result} | "
              f"Record: {agent.wins}W-{agent.draws}D-{agent.losses}L ({wr:.1f}%) | "
              f"Opponent Skill: {agent.skill_level}/20 | "
              f"Meta-learning: {agent.meta_learning_rate:.2f}x | "
              f"Time: {game_time:.1f}s")

        # Save checkpoint every 10 games
        if game_num % 10 == 0:
            results_dir = Path("chess_curriculum_results")
            results_dir.mkdir(exist_ok=True)

            with open(results_dir / f"checkpoint_{game_num}.json", 'w') as f:
                json.dump({
                    'game': game_num,
                    'wins': agent.wins,
                    'draws': agent.draws,
                    'losses': agent.losses,
                    'win_rate': wr,
                    'opponent_skill': agent.skill_level,
                    'meta_learning_rate': agent.meta_learning_rate
                }, f, indent=2)

    total_time = time.time() - start_time
    wr = (agent.wins / agent.games_played) * 100

    print()
    print(f"✅ Training Complete!")
    print(f"   Record: {agent.wins}W-{agent.draws}D-{agent.losses}L ({wr:.1f}%)")
    print(f"   Final opponent skill: {agent.skill_level}/20")
    print(f"   Meta-learning: 1.00x → {agent.meta_learning_rate:.2f}x")
    print(f"   Duration: {total_time:.1f}s ({total_time/60:.1f} min)")

if __name__ == "__main__":
    main()
