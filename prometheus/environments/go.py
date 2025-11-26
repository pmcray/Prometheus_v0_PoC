"""
Prometheus Go Environment

Complete Go (Weiqi/Baduk) implementation with:
- 19×19 board (standard), also supports 9×9, 13×13
- Capture rules (liberty counting)
- Ko rule (no immediate recapture)
- Superko (positional superko)
- Territory scoring with komi
- SGF file support
"""

import numpy as np
from typing import List, Tuple, Set, Optional, Dict, Any
from collections import deque
from copy import deepcopy


class GoBoard:
    """
    Go board with complete rule implementation.

    Coordinates: (row, col) where (0,0) is top-left
    Colors: BLACK = 1, WHITE = -1, EMPTY = 0
    """

    BLACK = 1
    WHITE = -1
    EMPTY = 0

    def __init__(self, size: int = 19, komi: float = 7.5):
        """
        Initialize Go board.

        Args:
            size: Board size (9, 13, or 19)
            komi: Compensation points for White (standard: 7.5)
        """
        self.size = size
        self.komi = komi

        # Board state
        self.board = np.zeros((size, size), dtype=np.int8)

        # Game state
        self.current_player = self.BLACK
        self.move_history = []
        self.captured_stones = {self.BLACK: 0, self.WHITE: 0}
        self.board_history = []  # For superko detection
        self.ko_point = None  # Ko position (if any)
        self.consecutive_passes = 0
        self.game_over = False

    def copy(self) -> 'GoBoard':
        """Create deep copy of board."""
        new_board = GoBoard(self.size, self.komi)
        new_board.board = self.board.copy()
        new_board.current_player = self.current_player
        new_board.move_history = self.move_history.copy()
        new_board.captured_stones = self.captured_stones.copy()
        new_board.board_history = [b.copy() for b in self.board_history]
        new_board.ko_point = self.ko_point
        new_board.consecutive_passes = self.consecutive_passes
        new_board.game_over = self.game_over
        return new_board

    def is_on_board(self, row: int, col: int) -> bool:
        """Check if position is on board."""
        return 0 <= row < self.size and 0 <= col < self.size

    def get_neighbors(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get neighboring positions (up, down, left, right)."""
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            if self.is_on_board(nr, nc):
                neighbors.append((nr, nc))
        return neighbors

    def get_group(self, row: int, col: int) -> Set[Tuple[int, int]]:
        """
        Get all stones in the same group (connected stones of same color).

        Uses flood-fill algorithm.

        Args:
            row, col: Starting position

        Returns:
            Set of positions in the group
        """
        color = self.board[row, col]
        if color == self.EMPTY:
            return set()

        group = set()
        queue = deque([(row, col)])
        visited = set()

        while queue:
            r, c = queue.popleft()
            if (r, c) in visited:
                continue

            visited.add((r, c))

            if self.board[r, c] == color:
                group.add((r, c))
                for nr, nc in self.get_neighbors(r, c):
                    if (nr, nc) not in visited:
                        queue.append((nr, nc))

        return group

    def count_liberties(self, group: Set[Tuple[int, int]]) -> int:
        """
        Count liberties (empty adjacent points) for a group.

        Args:
            group: Set of positions in the group

        Returns:
            Number of liberties
        """
        liberties = set()

        for row, col in group:
            for nr, nc in self.get_neighbors(row, col):
                if self.board[nr, nc] == self.EMPTY:
                    liberties.add((nr, nc))

        return len(liberties)

    def would_capture(self, row: int, col: int, color: int) -> List[Tuple[int, int]]:
        """
        Check which opponent groups would be captured by this move.

        Args:
            row, col: Move position
            color: Player color

        Returns:
            List of positions of captured stones
        """
        captured = []
        opponent = -color

        for nr, nc in self.get_neighbors(row, col):
            if self.board[nr, nc] == opponent:
                group = self.get_group(nr, nc)
                # If placing stone here removes last liberty
                liberties = self.count_liberties(group)
                if liberties == 1:
                    captured.extend(list(group))

        return captured

    def would_be_suicide(self, row: int, col: int, color: int) -> bool:
        """
        Check if move would be suicide (capturing own group with no liberties).

        Suicide is allowed if it also captures opponent stones.

        Args:
            row, col: Move position
            color: Player color

        Returns:
            True if suicide move
        """
        # Temporarily place stone
        self.board[row, col] = color

        # Check if any opponent groups would be captured
        would_capture_opponent = len(self.would_capture(row, col, color)) > 0

        # Get our group
        our_group = self.get_group(row, col)
        our_liberties = self.count_liberties(our_group)

        # Remove temporary stone
        self.board[row, col] = self.EMPTY

        # Suicide only if no liberties AND doesn't capture
        return our_liberties == 0 and not would_capture_opponent

    def is_legal_move(self, row: int, col: int, color: Optional[int] = None) -> bool:
        """
        Check if move is legal.

        Args:
            row, col: Move position
            color: Player color (None = current player)

        Returns:
            True if legal
        """
        if color is None:
            color = self.current_player

        # Must be on board
        if not self.is_on_board(row, col):
            return False

        # Must be empty
        if self.board[row, col] != self.EMPTY:
            return False

        # Can't be Ko
        if self.ko_point is not None and (row, col) == self.ko_point:
            return False

        # Can't be suicide
        if self.would_be_suicide(row, col, color):
            return False

        # Can't violate superko (no repeated board positions)
        # Simulate move
        temp_board = self.board.copy()
        temp_board[row, col] = color

        # Remove captured stones
        captured = self.would_capture(row, col, color)
        for cr, cc in captured:
            temp_board[cr, cc] = self.EMPTY

        # Check if position occurred before
        for hist_board in self.board_history:
            if np.array_equal(temp_board, hist_board):
                return False  # Superko violation

        return True

    def get_legal_moves(self, color: Optional[int] = None) -> List[Tuple[int, int]]:
        """
        Get all legal moves for current player.

        Args:
            color: Player color (None = current player)

        Returns:
            List of (row, col) positions
        """
        if color is None:
            color = self.current_player

        legal_moves = []

        for row in range(self.size):
            for col in range(self.size):
                if self.is_legal_move(row, col, color):
                    legal_moves.append((row, col))

        return legal_moves

    def play_move(self, row: int, col: int) -> bool:
        """
        Play a move.

        Args:
            row, col: Move position

        Returns:
            True if successful
        """
        if not self.is_legal_move(row, col):
            return False

        # Save current board state for superko
        self.board_history.append(self.board.copy())

        # Place stone
        self.board[row, col] = self.current_player

        # Capture opponent stones
        captured_positions = self.would_capture(row, col, self.current_player)

        for cr, cc in captured_positions:
            self.board[cr, cc] = self.EMPTY
            self.captured_stones[-self.current_player] += 1

        # Update Ko
        if len(captured_positions) == 1:
            # Might be Ko if only one stone captured
            self.ko_point = captured_positions[0]
        else:
            self.ko_point = None

        # Record move
        self.move_history.append((row, col, self.current_player))

        # Reset pass counter
        self.consecutive_passes = 0

        # Switch player
        self.current_player = -self.current_player

        return True

    def pass_turn(self):
        """Pass turn (no move)."""
        self.move_history.append(('pass', self.current_player))
        self.consecutive_passes += 1

        # Game ends after two consecutive passes
        if self.consecutive_passes >= 2:
            self.game_over = True

        self.current_player = -self.current_player

    def score(self) -> Dict[str, float]:
        """
        Calculate score using area scoring (Chinese rules).

        Score = Stones on board + Territory + Captures

        Returns:
            Dictionary with black_score, white_score, winner
        """
        # Count stones
        black_stones = np.sum(self.board == self.BLACK)
        white_stones = np.sum(self.board == self.WHITE)

        # Count territory (empty points surrounded by one color)
        black_territory, white_territory = self._count_territory()

        # Calculate scores
        black_score = black_stones + black_territory + self.captured_stones[self.BLACK]
        white_score = white_stones + white_territory + self.captured_stones[self.WHITE] + self.komi

        # Determine winner
        if black_score > white_score:
            winner = 'black'
            margin = black_score - white_score
        elif white_score > black_score:
            winner = 'white'
            margin = white_score - black_score
        else:
            winner = 'tie'
            margin = 0

        return {
            'black_score': float(black_score),
            'white_score': float(white_score),
            'black_territory': int(black_territory),
            'white_territory': int(white_territory),
            'black_captures': int(self.captured_stones[self.BLACK]),
            'white_captures': int(self.captured_stones[self.WHITE]),
            'winner': winner,
            'margin': float(margin)
        }

    def _count_territory(self) -> Tuple[int, int]:
        """
        Count territory for each player.

        Empty points are territory if they only touch one color.

        Returns:
            (black_territory, white_territory)
        """
        visited = np.zeros((self.size, self.size), dtype=bool)
        black_territory = 0
        white_territory = 0

        for row in range(self.size):
            for col in range(self.size):
                if self.board[row, col] == self.EMPTY and not visited[row, col]:
                    # Find connected empty region
                    region, touching_colors = self._get_empty_region(row, col)

                    # Mark as visited
                    for r, c in region:
                        visited[r, c] = True

                    # Assign territory
                    if touching_colors == {self.BLACK}:
                        black_territory += len(region)
                    elif touching_colors == {self.WHITE}:
                        white_territory += len(region)
                    # else: neutral (touches both colors)

        return black_territory, white_territory

    def _get_empty_region(self, row: int, col: int) -> Tuple[Set[Tuple[int, int]], Set[int]]:
        """
        Get connected empty region and which colors it touches.

        Args:
            row, col: Starting position

        Returns:
            (region_positions, touching_colors)
        """
        region = set()
        touching_colors = set()
        queue = deque([(row, col)])
        visited = set()

        while queue:
            r, c = queue.popleft()

            if (r, c) in visited:
                continue

            visited.add((r, c))

            if self.board[r, c] == self.EMPTY:
                region.add((r, c))
                for nr, nc in self.get_neighbors(r, c):
                    if (nr, nc) not in visited:
                        queue.append((nr, nc))
            else:
                # Touching a stone
                touching_colors.add(self.board[r, c])

        return region, touching_colors

    def render(self, show_coordinates: bool = True) -> str:
        """
        Render board as text.

        Args:
            show_coordinates: Show row/col labels

        Returns:
            String representation
        """
        symbols = {
            self.BLACK: '●',  # Black stone
            self.WHITE: '○',  # White stone
            self.EMPTY: '·'   # Empty
        }

        lines = []

        if show_coordinates:
            # Column labels
            col_labels = '   ' + ' '.join([chr(65 + i) if i < 8 else chr(66 + i)
                                           for i in range(self.size)])
            lines.append(col_labels)

        for row in range(self.size):
            if show_coordinates:
                row_label = f"{self.size - row:2d} "
            else:
                row_label = ""

            row_str = row_label + ' '.join([symbols[self.board[row, col]]
                                           for col in range(self.size)])
            lines.append(row_str)

        return '\n'.join(lines)

    def to_sgf(self) -> str:
        """
        Convert game to SGF (Smart Game Format).

        Returns:
            SGF string
        """
        sgf = f"(;GM[1]FF[4]SZ[{self.size}]KM[{self.komi}]\n"

        for move_data in self.move_history:
            if move_data[0] == 'pass':
                color = 'B' if move_data[1] == self.BLACK else 'W'
                sgf += f";{color}[]\n"
            else:
                row, col, player = move_data
                color = 'B' if player == self.BLACK else 'W'
                # SGF coordinates: aa = (0,0), ba = (1,0), etc.
                sgf_coord = chr(97 + col) + chr(97 + row)
                sgf += f";{color}[{sgf_coord}]\n"

        sgf += ")"
        return sgf


class GoEnvironment:
    """
    Go environment for Prometheus agents.

    Wraps GoBoard with RL-friendly interface.
    """

    def __init__(self, board_size: int = 19, komi: float = 7.5):
        """
        Initialize Go environment.

        Args:
            board_size: Board size (9, 13, or 19)
            komi: Komi value
        """
        self.board_size = board_size
        self.komi = komi
        self.board = GoBoard(board_size, komi)

    def reset(self) -> np.ndarray:
        """Reset environment."""
        self.board = GoBoard(self.board_size, self.komi)
        return self.get_state()

    def get_state(self) -> np.ndarray:
        """
        Get board state as numpy array.

        Returns:
            shape (board_size, board_size, 3):
            - Channel 0: Black stones
            - Channel 1: White stones
            - Channel 2: Current player indicator
        """
        state = np.zeros((self.board_size, self.board_size, 3), dtype=np.float32)

        # Black stones
        state[:, :, 0] = (self.board.board == GoBoard.BLACK).astype(np.float32)

        # White stones
        state[:, :, 1] = (self.board.board == GoBoard.WHITE).astype(np.float32)

        # Current player (fill entire channel)
        if self.board.current_player == GoBoard.BLACK:
            state[:, :, 2] = 1.0
        else:
            state[:, :, 2] = -1.0

        return state

    def get_legal_moves(self) -> List[Tuple[int, int]]:
        """Get legal moves plus pass."""
        moves = self.board.get_legal_moves()
        moves.append(('pass',))  # Add pass option
        return moves

    def step(self, move: Tuple) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Execute move.

        Args:
            move: (row, col) or ('pass',)

        Returns:
            (next_state, reward, done, info)
        """
        if move == ('pass',) or (len(move) == 1 and move[0] == 'pass'):
            self.board.pass_turn()
        else:
            row, col = move
            success = self.board.play_move(row, col)
            if not success:
                # Illegal move
                return self.get_state(), -1.0, True, {'illegal_move': True}

        # Check if game over
        done = self.board.game_over

        # Calculate reward
        reward = 0.0
        if done:
            scores = self.board.score()
            if scores['winner'] == 'black':
                reward = 1.0
            elif scores['winner'] == 'white':
                reward = -1.0
            else:
                reward = 0.0

        info = {
            'legal_moves': len(self.get_legal_moves()),
            'game_over': done
        }

        if done:
            info['score'] = self.board.score()

        return self.get_state(), reward, done, info

    def render(self):
        """Render board."""
        print(self.board.render())


class GoBoardEncoder:
    """Encode Go board state for neural networks."""

    @staticmethod
    def encode(board: GoBoard) -> np.ndarray:
        """
        Encode board state.

        Returns:
            shape (size, size, 3)
        """
        env = GoEnvironment(board.size, board.komi)
        env.board = board
        return env.get_state()


class GoMoveEncoder:
    """Encode Go moves for neural networks."""

    def __init__(self, board_size: int = 19):
        """Initialize encoder."""
        self.board_size = board_size
        self.num_moves = board_size * board_size + 1  # +1 for pass

    def move_to_index(self, move: Tuple) -> int:
        """Convert move to index."""
        if move == ('pass',) or (len(move) == 1 and move[0] == 'pass'):
            return self.board_size * self.board_size  # Last index is pass
        else:
            row, col = move
            return row * self.board_size + col

    def index_to_move(self, index: int) -> Tuple:
        """Convert index to move."""
        if index == self.board_size * self.board_size:
            return ('pass',)
        else:
            row = index // self.board_size
            col = index % self.board_size
            return (row, col)
