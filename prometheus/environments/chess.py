"""
Prometheus Chess Environment

This module implements a chess environment for Prometheus agents:
- Board state representation using 8×8×12 tensor encoding
- Legal move generation and validation
- UCI protocol interface for external engines
- Self-play and benchmark utilities
"""

import numpy as np
import chess
import chess.engine
from typing import List, Tuple, Dict, Optional, Any
from pathlib import Path
import subprocess
import time
from prometheus.strategic_knowledge import StrategicKnowledgeBase, ChessRulesManager


class ChessBoardEncoder:
    """
    Encodes chess board state as 8×8×12 tensor.

    Channels (12 total):
    - 0-5: White pieces (Pawn, Knight, Bishop, Rook, Queen, King)
    - 6-11: Black pieces (Pawn, Knight, Bishop, Rook, Queen, King)

    This representation allows CNNs to learn spatial patterns on the board.
    """

    PIECE_TO_CHANNEL = {
        chess.PAWN: 0,
        chess.KNIGHT: 1,
        chess.BISHOP: 2,
        chess.ROOK: 3,
        chess.QUEEN: 4,
        chess.KING: 5
    }

    @staticmethod
    def encode(board: chess.Board) -> np.ndarray:
        """
        Encode chess board to 8×8×12 tensor.

        Args:
            board: python-chess Board object

        Returns:
            8×8×12 numpy array representing board state
        """
        state = np.zeros((8, 8, 12), dtype=np.float32)

        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece is not None:
                # Get rank (row) and file (column)
                rank = chess.square_rank(square)
                file = chess.square_file(square)

                # Get channel index
                channel = ChessBoardEncoder.PIECE_TO_CHANNEL[piece.piece_type]
                if piece.color == chess.BLACK:
                    channel += 6

                # Set position
                state[rank, file, channel] = 1.0

        return state

    @staticmethod
    def encode_with_history(
        board: chess.Board,
        history_length: int = 8
    ) -> np.ndarray:
        """
        Encode board with move history (AlphaZero-style).

        Args:
            board: Current board state
            history_length: Number of previous positions to include

        Returns:
            8×8×(12*history_length) numpy array
        """
        # Returns current position repeated across history channels.
        # Full history tracking would store board states per move; this
        # approximation is sufficient for single-position evaluation agents.
        current = ChessBoardEncoder.encode(board)
        return np.repeat(current, history_length, axis=2)

    @staticmethod
    def encode_metadata(board: chess.Board) -> np.ndarray:
        """
        Encode additional metadata as extra channels.

        Metadata includes:
        - Turn (White=1, Black=0)
        - Castling rights (4 channels)
        - En passant target (1 channel)
        - Halfmove clock (1 channel)

        Args:
            board: python-chess Board object

        Returns:
            8×8×7 numpy array with metadata
        """
        metadata = np.zeros((8, 8, 7), dtype=np.float32)

        # Turn indicator (channel 0)
        if board.turn == chess.WHITE:
            metadata[:, :, 0] = 1.0

        # Castling rights (channels 1-4)
        if board.has_kingside_castling_rights(chess.WHITE):
            metadata[:, :, 1] = 1.0
        if board.has_queenside_castling_rights(chess.WHITE):
            metadata[:, :, 2] = 1.0
        if board.has_kingside_castling_rights(chess.BLACK):
            metadata[:, :, 3] = 1.0
        if board.has_queenside_castling_rights(chess.BLACK):
            metadata[:, :, 4] = 1.0

        # En passant target (channel 5)
        if board.ep_square is not None:
            rank = chess.square_rank(board.ep_square)
            file = chess.square_file(board.ep_square)
            metadata[rank, file, 5] = 1.0

        # Halfmove clock normalized (channel 6)
        metadata[:, :, 6] = board.halfmove_clock / 100.0  # Normalize to [0, 1]

        return metadata

    @staticmethod
    def encode_full(board: chess.Board) -> np.ndarray:
        """
        Full encoding: board state + metadata.

        Args:
            board: python-chess Board object

        Returns:
            8×8×19 numpy array (12 pieces + 7 metadata)
        """
        pieces = ChessBoardEncoder.encode(board)
        metadata = ChessBoardEncoder.encode_metadata(board)
        return np.concatenate([pieces, metadata], axis=2)


class ChessMoveEncoder:
    """
    Encodes chess moves for neural network output.

    Uses policy representation similar to AlphaZero:
    - 73 move types (56 queen moves + 8 knight moves + 9 underpromotions)
    - Output shape: 8×8×73 (from_square × to_square × move_type)

    Simplified version uses 64×64 matrix (from_square to to_square).
    """

    @staticmethod
    def move_to_index(move: chess.Move) -> int:
        """
        Convert move to flat index (0-4095 for 64×64 encoding).

        Args:
            move: python-chess Move object

        Returns:
            Integer index in range [0, 4095]
        """
        from_square = move.from_square
        to_square = move.to_square
        return from_square * 64 + to_square

    @staticmethod
    def index_to_move(index: int, board: chess.Board) -> Optional[chess.Move]:
        """
        Convert flat index to chess move (if legal).

        Args:
            index: Integer index in range [0, 4095]
            board: Current board state

        Returns:
            chess.Move if legal, None otherwise
        """
        from_square = index // 64
        to_square = index % 64

        # Check all legal moves for match
        for move in board.legal_moves:
            if move.from_square == from_square and move.to_square == to_square:
                return move

        return None

    @staticmethod
    def encode_legal_moves(board: chess.Board) -> np.ndarray:
        """
        Create mask of legal moves.

        Args:
            board: Current board state

        Returns:
            4096-element binary mask (1=legal, 0=illegal)
        """
        mask = np.zeros(4096, dtype=np.float32)
        for move in board.legal_moves:
            idx = ChessMoveEncoder.move_to_index(move)
            mask[idx] = 1.0
        return mask

    @staticmethod
    def decode_policy(
        policy: np.ndarray,
        board: chess.Board,
        temperature: float = 1.0
    ) -> chess.Move:
        """
        Sample move from policy distribution.

        Args:
            policy: 4096-element policy distribution
            board: Current board state
            temperature: Sampling temperature (1.0=normal, 0.0=greedy)

        Returns:
            Sampled legal chess move
        """
        # Mask illegal moves
        legal_mask = ChessMoveEncoder.encode_legal_moves(board)
        masked_policy = policy * legal_mask

        # Normalize
        total = np.sum(masked_policy)
        if total > 0:
            masked_policy /= total
        else:
            # Fallback: uniform over legal moves
            masked_policy = legal_mask / np.sum(legal_mask)

        # Apply temperature
        if temperature != 1.0:
            if temperature == 0.0:
                # Greedy: pick maximum
                idx = np.argmax(masked_policy)
            else:
                # Temperature sampling
                logits = np.log(masked_policy + 1e-10) / temperature
                exp_logits = np.exp(logits - np.max(logits))
                probs = exp_logits / np.sum(exp_logits)
                idx = np.random.choice(len(probs), p=probs)
        else:
            # Normal sampling
            idx = np.random.choice(len(masked_policy), p=masked_policy)

        move = ChessMoveEncoder.index_to_move(idx, board)
        if move is None:
            # Fallback: random legal move
            move = np.random.choice(list(board.legal_moves))

        return move


class UCIEngineInterface:
    """
    Interface to UCI chess engines (GNU Chess, Stockfish, etc.).

    Allows Prometheus agents to play against established engines
    for benchmarking and training.
    """

    def __init__(
        self,
        engine_path: str = "/usr/games/gnuchess",
        skill_level: Optional[int] = None,
        time_limit: float = 0.1
    ):
        """
        Initialize UCI engine interface.

        Args:
            engine_path: Path to UCI engine executable
            skill_level: Skill level (engine-specific)
            time_limit: Time limit per move in seconds
        """
        self.engine_path = engine_path
        self.skill_level = skill_level
        self.time_limit = time_limit
        self.engine = None

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    def start(self):
        """Start UCI engine."""
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
            if self.skill_level is not None:
                self.engine.configure({"Skill Level": self.skill_level})
        except Exception as e:
            print(f"⚠️  Warning: Could not start engine at {self.engine_path}: {e}")
            print(f"   Ensure chess engine is installed (e.g., 'apt-get install gnuchess')")
            self.engine = None

    def stop(self):
        """Stop UCI engine."""
        if self.engine is not None:
            self.engine.quit()
            self.engine = None

    def get_move(self, board: chess.Board) -> Optional[chess.Move]:
        """
        Get engine's move for current position.

        Args:
            board: Current board state

        Returns:
            chess.Move from engine
        """
        if self.engine is None:
            return None

        try:
            result = self.engine.play(
                board,
                chess.engine.Limit(time=self.time_limit)
            )
            return result.move
        except Exception as e:
            print(f"⚠️  Engine error: {e}")
            return None

    def get_evaluation(self, board: chess.Board) -> Optional[float]:
        """
        Get engine's evaluation of position in centipawns.

        Args:
            board: Current board state

        Returns:
            Evaluation in centipawns (positive = White advantage)
        """
        if self.engine is None:
            return None

        try:
            info = self.engine.analyse(
                board,
                chess.engine.Limit(time=self.time_limit)
            )
            score = info["score"].relative
            if score.is_mate():
                # Mate in N moves
                return 10000 if score.mate() > 0 else -10000
            else:
                return score.score()
        except Exception as e:
            print(f"⚠️  Evaluation error: {e}")
            return None


class ChessEnvironment:
    """
    Chess environment for Prometheus agents.

    Provides:
    - Board state management
    - Move execution and validation
    - Game termination detection
    - Reward calculation
    - Self-play utilities
    """

    def __init__(self, start_position: Optional[str] = None):
        """
        Initialize chess environment.

        Args:
            start_position: FEN string for starting position (None = standard)
        """
        self.board = chess.Board(start_position) if start_position else chess.Board()
        self.move_history = []
        self.encoder = ChessBoardEncoder()
        self.move_encoder = ChessMoveEncoder()
        self.knowledge_base = StrategicKnowledgeBase()
        self.rules_manager = ChessRulesManager()

    def reset(self, start_position: Optional[str] = None) -> np.ndarray:
        """
        Reset environment to starting position.

        Args:
            start_position: FEN string (None = standard position)

        Returns:
            Initial board state encoding
        """
        self.board = chess.Board(start_position) if start_position else chess.Board()
        self.move_history = []
        return self.get_state()

    def get_state(self) -> np.ndarray:
        """
        Get current board state encoding.

        Returns:
            8×8×19 numpy array (board + metadata)
        """
        return self.encoder.encode_full(self.board)

    def get_legal_moves(self) -> List[chess.Move]:
        """
        Get list of legal moves in current position.

        Returns:
            List of legal chess.Move objects
        """
        return list(self.board.legal_moves)

    def get_legal_move_mask(self) -> np.ndarray:
        """
        Get binary mask of legal moves.

        Returns:
            4096-element binary array
        """
        return self.move_encoder.encode_legal_moves(self.board)

    def step(self, move: chess.Move) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Execute move and return next state.

        Args:
            move: chess.Move to execute

        Returns:
            Tuple of (next_state, reward, done, info)
        """
        # Validate move
        if move not in self.board.legal_moves:
            raise ValueError(f"Illegal move: {move}")

        # Execute move
        self.board.push(move)
        self.move_history.append(move)

        # Get new state
        next_state = self.get_state()

        # Check termination (including 3-fold repetition and 50-move rule)
        done = self.board.is_game_over()
        
        # Internal rule tracking for transparency
        is_repetition = self.rules_manager.check_repetition(self.board, self.move_history)
        is_50_move = self.rules_manager.check_50_move_rule(self.board)

        # Calculate reward
        reward = self._calculate_reward()

        # Record interesting positions (e.g., checkmate or stalemate)
        if done:
            self.knowledge_base.record_interesting_position(
                "chess", 
                self.board.fen(), 
                {"reason": "termination", "result": self.get_game_result()}
            )

        # Info
        info = {
            'move': move,
            'move_number': len(self.move_history),
            'is_check': self.board.is_check(),
            'is_checkmate': self.board.is_checkmate(),
            'is_repetition': is_repetition,
            'is_50_move': is_50_move,
            'is_stalemate': self.board.is_stalemate(),
            'is_insufficient_material': self.board.is_insufficient_material(),
            'fen': self.board.fen()
        }

        return next_state, reward, done, info

    def _calculate_reward(self) -> float:
        """
        Calculate reward for current position.

        Returns:
            Reward value (1.0 = win, 0.0 = draw, -1.0 = loss)
        """
        if not self.board.is_game_over():
            return 0.0  # Game continues

        outcome = self.board.outcome()
        if outcome is None:
            return 0.0  # Draw

        # Win/Loss from perspective of player who just moved
        if outcome.winner == chess.WHITE:
            return 1.0 if len(self.move_history) % 2 == 1 else -1.0
        elif outcome.winner == chess.BLACK:
            return 1.0 if len(self.move_history) % 2 == 0 else -1.0
        else:
            return 0.0  # Draw

    def render(self, unicode: bool = True) -> str:
        """
        Render board as text.

        Args:
            unicode: Use Unicode chess symbols

        Returns:
            String representation of board
        """
        return str(self.board) if not unicode else self.board.unicode()

    def get_game_result(self) -> Optional[str]:
        """
        Get game result string.

        Returns:
            "1-0" (White wins), "0-1" (Black wins), "1/2-1/2" (Draw), or None
        """
        if not self.board.is_game_over():
            return None

        outcome = self.board.outcome()
        if outcome is None:
            return "1/2-1/2"

        if outcome.winner == chess.WHITE:
            return "1-0"
        elif outcome.winner == chess.BLACK:
            return "0-1"
        else:
            return "1/2-1/2"

    def clone(self) -> 'ChessEnvironment':
        """
        Create deep copy of environment.

        Returns:
            New ChessEnvironment with same state
        """
        env_copy = ChessEnvironment()
        env_copy.board = self.board.copy()
        env_copy.move_history = self.move_history.copy()
        return env_copy

    def play_random_move(self) -> Tuple[chess.Move, np.ndarray, float, bool]:
        """
        Play random legal move.

        Returns:
            Tuple of (move, next_state, reward, done)
        """
        legal_moves = self.get_legal_moves()
        if not legal_moves:
            raise RuntimeError("No legal moves available")

        move = np.random.choice(legal_moves)
        next_state, reward, done, info = self.step(move)
        return move, next_state, reward, done


def play_game(
    white_agent: Any,
    black_agent: Any,
    max_moves: int = 500,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Play a complete chess game between two agents.

    Args:
        white_agent: Agent playing White (must have get_move(state) method)
        black_agent: Agent playing Black
        max_moves: Maximum moves before draw
        verbose: Print game progress

    Returns:
        Dictionary with game result and statistics
    """
    env = ChessEnvironment()
    move_count = 0

    if verbose:
        print("🎮 Starting chess game...")
        print(env.render())

    while not env.board.is_game_over() and move_count < max_moves:
        state = env.get_state()

        # Get move from current player
        if env.board.turn == chess.WHITE:
            move = white_agent.get_move(state, env.board)
        else:
            move = black_agent.get_move(state, env.board)

        # Execute move
        next_state, reward, done, info = env.step(move)
        move_count += 1

        if verbose:
            print(f"\nMove {move_count}: {move}")
            print(env.render())

    result = env.get_game_result()

    if verbose:
        print(f"\n🏁 Game Over: {result}")
        print(f"   Total moves: {move_count}")

    return {
        'result': result,
        'moves': move_count,
        'final_position': env.board.fen(),
        'move_history': env.move_history
    }
