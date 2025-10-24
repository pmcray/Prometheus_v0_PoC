#!/usr/bin/env python3
"""
Prometheus TRM Chess Tactics Adapter (Proof of Concept)

Adapts the TRM (Tiny Recursive Models) framework from ARC-AGI to chess tactical puzzles.

Goal: Validate TRM's pattern discovery on a game domain before applying to RTS/4X games.

Input: Chess board position (FEN notation)
Output: Winning move sequence (tactical combination)

Primitives: Chess tactical patterns (fork, pin, skewer, discovered attack, etc.)
"""

import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import chess
import chess.engine

# ============================================================================
# CHESS TACTICAL PRIMITIVES
# ============================================================================

class ChessTacticalPrimitives:
    """
    Tactical patterns as primitives for TRM learning.

    Each primitive represents a tactical motif that can be composed
    into complex combinations (just like ARC primitives compose into patterns).
    """

    @staticmethod
    def is_fork(board: chess.Board, move: chess.Move) -> bool:
        """
        Detect if move creates a fork (attacks 2+ valuable pieces).

        Similar to ARC's 'detect_pattern' - recognizes tactical structure.
        """
        board_copy = board.copy()
        board_copy.push(move)

        from_square = move.to_square
        piece = board_copy.piece_at(from_square)

        if piece is None:
            return False

        # Get all attacked squares
        attacks = board_copy.attacks(from_square)

        # Count valuable pieces attacked (queen, rook, bishop, knight)
        valuable_attacked = 0
        for square in attacks:
            attacked_piece = board_copy.piece_at(square)
            if attacked_piece and attacked_piece.color != piece.color:
                # Value check: queen=9, rook=5, bishop/knight=3
                if attacked_piece.piece_type in [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]:
                    valuable_attacked += 1

        return valuable_attacked >= 2

    @staticmethod
    def is_pin(board: chess.Board, move: chess.Move) -> bool:
        """
        Detect if move creates a pin (piece can't move without exposing king/queen).
        """
        board_copy = board.copy()
        board_copy.push(move)

        # Check if any opponent piece is pinned
        opponent_pieces = board_copy.piece_map()
        for square, piece in opponent_pieces.items():
            if piece.color == board_copy.turn:  # Opponent's turn now
                continue

            # Try moving the piece - if it exposes king, it's pinned
            legal_moves = list(board_copy.legal_moves)
            piece_moves = [m for m in legal_moves if m.from_square == square]

            if not piece_moves:
                continue

            # Check if moving exposes king
            for test_move in piece_moves[:1]:  # Test one move
                test_board = board_copy.copy()
                test_board.push(test_move)
                if test_board.is_check():
                    return True  # Piece is pinned

        return False

    @staticmethod
    def is_skewer(board: chess.Board, move: chess.Move) -> bool:
        """
        Detect skewer (attack valuable piece, revealing attack on less valuable piece behind).
        """
        # Simplified: Check if move attacks queen/rook with sliding piece
        board_copy = board.copy()
        piece = board.piece_at(move.from_square)

        if piece is None or piece.piece_type not in [chess.BISHOP, chess.ROOK, chess.QUEEN]:
            return False

        board_copy.push(move)

        # Check if attacked piece has another piece behind it on the same ray
        to_square = move.to_square
        attacked_piece = board_copy.piece_at(to_square)

        if attacked_piece and attacked_piece.piece_type in [chess.QUEEN, chess.ROOK]:
            # Simplified skewer detection
            return True

        return False

    @staticmethod
    def is_discovered_attack(board: chess.Board, move: chess.Move) -> bool:
        """
        Detect discovered attack (moving piece reveals attack from piece behind).
        """
        # Check if moving piece uncovers an attack
        from_square = move.from_square
        to_square = move.to_square

        board_copy = board.copy()
        board_copy.push(move)

        # Check if opponent king is now attacked by a piece that wasn't attacking before
        opponent_king_square = board_copy.king(not board_copy.turn)

        if opponent_king_square is None:
            return False

        # Get attackers of opponent king after move
        attackers_after = board_copy.attackers(board.turn, opponent_king_square)

        # Check if any attacker is NOT the piece that moved
        for attacker_square in attackers_after:
            if attacker_square != to_square:
                # Check if this was an attack before the move
                board_before = board.copy()
                if attacker_square in board_before.attackers(board_before.turn, opponent_king_square):
                    continue  # Was already attacking
                else:
                    return True  # Discovered attack!

        return False

    @staticmethod
    def is_check(board: chess.Board, move: chess.Move) -> bool:
        """Simple: Does move give check?"""
        board_copy = board.copy()
        board_copy.push(move)
        return board_copy.is_check()

    @staticmethod
    def is_capture(board: chess.Board, move: chess.Move) -> bool:
        """Simple: Does move capture a piece?"""
        return board.is_capture(move)

    @staticmethod
    def threatens_checkmate(board: chess.Board, move: chess.Move) -> bool:
        """Does move threaten checkmate on next turn?"""
        board_copy = board.copy()
        board_copy.push(move)

        # Check if any next move is checkmate
        for next_move in board_copy.legal_moves:
            test_board = board_copy.copy()
            test_board.push(next_move)
            if test_board.is_checkmate():
                return True

        return False


# ============================================================================
# TRM CHESS TACTICS SOLVER
# ============================================================================

@dataclass
class TacticalPattern:
    """A sequence of tactical primitives (like ARC patterns)"""
    primitives: List[str]  # e.g., ['fork', 'capture', 'check']
    moves: List[str]  # Corresponding chess moves in UCI notation
    fitness: float  # How well this pattern solves the puzzle

class TRMChessTactics:
    """
    TRM adapted for chess tactical puzzles.

    Architecture parallels ARC-AGI TRM:
    - Primitives: Tactical motifs (fork, pin, discovered attack)
    - Patterns: Sequences of tactical moves
    - Fitness: Material gain + positional advantage
    - Meta-learning: Which tactical patterns work in which positions
    """

    def __init__(self):
        """Initialize TRM chess solver"""
        self.primitives_map = {
            'fork': ChessTacticalPrimitives.is_fork,
            'pin': ChessTacticalPrimitives.is_pin,
            'skewer': ChessTacticalPrimitives.is_skewer,
            'discovered_attack': ChessTacticalPrimitives.is_discovered_attack,
            'check': ChessTacticalPrimitives.is_check,
            'capture': ChessTacticalPrimitives.is_capture,
            'threaten_mate': ChessTacticalPrimitives.threatens_checkmate
        }

        # TRM components (simplified - no full Phases 8-10 yet)
        self.discovered_patterns: List[TacticalPattern] = []

    def solve_puzzle(self,
                    fen: str,
                    target_moves: Optional[List[str]] = None,
                    max_depth: int = 3) -> Dict:
        """
        Solve a chess tactical puzzle.

        Args:
            fen: Board position in FEN notation
            target_moves: Ground truth solution (for training)
            max_depth: Maximum move sequence depth

        Returns:
            {
                'solution': List of moves,
                'pattern': Tactical pattern discovered,
                'fitness': Quality score
            }
        """
        board = chess.Board(fen)

        # Phase 1: Generate candidate moves using tactical heuristics
        candidates = self._generate_tactical_candidates(board, max_depth)

        # Phase 2: Evaluate each candidate
        best_candidate = None
        best_fitness = -float('inf')

        for candidate in candidates:
            fitness = self._evaluate_candidate(board, candidate, target_moves)

            if fitness > best_fitness:
                best_fitness = fitness
                best_candidate = candidate

        # Phase 3: Return best solution
        if best_candidate:
            return {
                'solution': best_candidate['moves'],
                'pattern': best_candidate['primitives'],
                'fitness': best_fitness,
                'success': best_fitness > 0.8  # Threshold for "solved"
            }
        else:
            return {
                'solution': [],
                'pattern': [],
                'fitness': 0.0,
                'success': False
            }

    def _generate_tactical_candidates(self,
                                     board: chess.Board,
                                     max_depth: int) -> List[Dict]:
        """
        Generate candidate move sequences using tactical primitives.

        Similar to ARC's pattern evolution, but guided by chess tactics.
        """
        candidates = []

        # Get all legal moves
        legal_moves = list(board.legal_moves)

        # Filter to tactical moves (checks, captures, threats)
        tactical_moves = []
        for move in legal_moves:
            primitives = []

            # Tag move with tactical primitives
            for prim_name, prim_func in self.primitives_map.items():
                if prim_func(board, move):
                    primitives.append(prim_name)

            if primitives or board.is_capture(move):
                tactical_moves.append({
                    'move': move,
                    'primitives': primitives
                })

        # Generate 1-move candidates
        for tmove in tactical_moves:
            candidates.append({
                'moves': [tmove['move'].uci()],
                'primitives': tmove['primitives']
            })

        # Generate 2-move combinations (depth 2)
        if max_depth >= 2:
            for tmove1 in tactical_moves[:10]:  # Limit to top 10
                board_copy = board.copy()
                board_copy.push(tmove1['move'])

                # Opponent's response (simplified: any move)
                opponent_moves = list(board_copy.legal_moves)
                if opponent_moves:
                    # Try first opponent move
                    board_copy.push(opponent_moves[0])

                    # Our second move
                    second_legal = list(board_copy.legal_moves)
                    for move2 in second_legal[:5]:  # Top 5
                        primitives2 = []
                        for prim_name, prim_func in self.primitives_map.items():
                            if prim_func(board_copy, move2):
                                primitives2.append(prim_name)

                        if primitives2:
                            candidates.append({
                                'moves': [tmove1['move'].uci(), opponent_moves[0].uci(), move2.uci()],
                                'primitives': tmove1['primitives'] + primitives2
                            })

        return candidates

    def _evaluate_candidate(self,
                          board: chess.Board,
                          candidate: Dict,
                          target_moves: Optional[List[str]]) -> float:
        """
        Evaluate candidate solution.

        Fitness = material_gain + positional_advantage + match_to_target
        """
        # Material count before
        material_before = self._count_material(board)

        # Apply moves
        board_copy = board.copy()
        for move_uci in candidate['moves']:
            try:
                move = chess.Move.from_uci(move_uci)
                board_copy.push(move)
            except:
                return 0.0  # Invalid move sequence

        # Material count after
        material_after = self._count_material(board_copy)
        material_gain = material_after - material_before

        # Normalize material gain (-10 to +10 → 0.0 to 1.0)
        material_score = (material_gain + 10) / 20.0

        # Match to target (if provided)
        target_score = 0.0
        if target_moves:
            # Check if our moves match target
            matches = sum(1 for m1, m2 in zip(candidate['moves'], target_moves) if m1 == m2)
            target_score = matches / len(target_moves) if target_moves else 0.0

        # Combined fitness
        fitness = 0.5 * material_score + 0.5 * target_score

        return fitness

    def _count_material(self, board: chess.Board) -> float:
        """
        Count material value for current side to move.

        Values: Pawn=1, Knight=3, Bishop=3, Rook=5, Queen=9
        """
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 0  # King doesn't count for material
        }

        our_material = 0
        opponent_material = 0
        our_color = board.turn

        for square, piece in board.piece_map().items():
            value = piece_values[piece.piece_type]
            if piece.color == our_color:
                our_material += value
            else:
                opponent_material += value

        return our_material - opponent_material


# ============================================================================
# PROOF OF CONCEPT TEST
# ============================================================================

def test_simple_fork():
    """Test on a simple knight fork puzzle"""
    # Position: White knight can fork king and rook
    fen = "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1"

    solver = TRMChessTactics()
    result = solver.solve_puzzle(fen, max_depth=2)

    print("=" * 60)
    print("Test: Simple Knight Fork")
    print("=" * 60)
    print(f"FEN: {fen}")
    print(f"Solution: {result['solution']}")
    print(f"Pattern: {result['pattern']}")
    print(f"Fitness: {result['fitness']:.3f}")
    print(f"Success: {result['success']}")
    print()

    return result

def test_pin_puzzle():
    """Test on a pin tactic"""
    # Position with potential pin
    fen = "rnbqkb1r/ppp2ppp/4pn2/3p4/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq - 0 1"

    solver = TRMChessTactics()
    result = solver.solve_puzzle(fen, max_depth=1)

    print("=" * 60)
    print("Test: Pin Tactic")
    print("=" * 60)
    print(f"FEN: {fen}")
    print(f"Solution: {result['solution']}")
    print(f"Pattern: {result['pattern']}")
    print(f"Fitness: {result['fitness']:.3f}")
    print(f"Success: {result['success']}")
    print()

    return result

def main():
    """Run proof-of-concept tests"""
    print("🔬 Prometheus TRM Chess Tactics - Proof of Concept")
    print("=" * 60)
    print()

    # Test 1: Fork
    result1 = test_simple_fork()

    # Test 2: Pin
    result2 = test_pin_puzzle()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Fork puzzle: {'✓ SOLVED' if result1['success'] else '✗ FAILED'}")
    print(f"Pin puzzle: {'✓ SOLVED' if result2['success'] else '✗ FAILED'}")
    print()
    print("Next steps:")
    print("1. Add more tactical primitives (sacrifice, zugzwang, etc.)")
    print("2. Integrate Phases 8-10 (subroutines, multi-hypothesis, meta-meta)")
    print("3. Test on Lichess puzzle database")
    print("4. Compare to Stockfish tactical analysis")


if __name__ == "__main__":
    main()
