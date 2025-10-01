"""
Game Suite for Project Prometheus v0.69+

Provides multiple games with visualization:
- Connect 4 (simple, 7x6 grid)
- Othello/Reversi (intermediate, 8x8 grid)
- Draughts/Checkers (complex, 8x8 grid)

All games include:
- ASCII visualization
- Move validation
- Win detection
- Game state tracking
"""

import random
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class GameResult(Enum):
    """Game outcome"""
    ONGOING = "ongoing"
    PLAYER1_WIN = "player1_win"
    PLAYER2_WIN = "player2_win"
    DRAW = "draw"


@dataclass
class GameState:
    """Universal game state representation"""
    board: List[List[int]]
    current_player: int
    move_count: int
    result: GameResult
    winner: Optional[int]
    last_move: Optional[Any]


class Connect4:
    """
    Connect 4 Game

    Simple drop-token game. First to connect 4 wins.
    Board: 7 columns x 6 rows
    """

    def __init__(self):
        self.rows = 6
        self.cols = 7
        self.reset()

    def reset(self):
        """Reset to starting position"""
        self.board = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.current_player = 1
        self.move_count = 0
        self.result = GameResult.ONGOING
        self.winner = None
        self.last_move = None

    def get_valid_moves(self) -> List[int]:
        """Get valid column numbers where a piece can be dropped"""
        return [col for col in range(self.cols) if self.board[0][col] == 0]

    def make_move(self, column: int) -> bool:
        """Drop a piece in the specified column"""
        if column not in self.get_valid_moves():
            return False

        # Drop piece to lowest available row
        for row in range(self.rows - 1, -1, -1):
            if self.board[row][column] == 0:
                self.board[row][column] = self.current_player
                self.last_move = (row, column)
                self.move_count += 1

                # Check win
                if self._check_win(row, column):
                    self.result = GameResult.PLAYER1_WIN if self.current_player == 1 else GameResult.PLAYER2_WIN
                    self.winner = self.current_player
                elif not self.get_valid_moves():
                    self.result = GameResult.DRAW
                    self.winner = 0
                else:
                    # Switch player
                    self.current_player = -self.current_player

                return True

        return False

    def _check_win(self, row: int, col: int) -> bool:
        """Check if last move won the game"""
        player = self.board[row][col]

        # Check horizontal
        if self._count_direction(row, col, 0, 1, player) + self._count_direction(row, col, 0, -1, player) + 1 >= 4:
            return True

        # Check vertical
        if self._count_direction(row, col, 1, 0, player) + self._count_direction(row, col, -1, 0, player) + 1 >= 4:
            return True

        # Check diagonal /
        if self._count_direction(row, col, -1, 1, player) + self._count_direction(row, col, 1, -1, player) + 1 >= 4:
            return True

        # Check diagonal \
        if self._count_direction(row, col, 1, 1, player) + self._count_direction(row, col, -1, -1, player) + 1 >= 4:
            return True

        return False

    def _count_direction(self, row: int, col: int, dr: int, dc: int, player: int) -> int:
        """Count consecutive pieces in a direction"""
        count = 0
        r, c = row + dr, col + dc

        while 0 <= r < self.rows and 0 <= c < self.cols and self.board[r][c] == player:
            count += 1
            r += dr
            c += dc

        return count

    def visualize(self) -> str:
        """Return ASCII visualization of board"""
        lines = []
        lines.append("\n╔═" + "══╤═" * (self.cols - 1) + "══╗")

        for row in range(self.rows):
            line = "║ "
            for col in range(self.cols):
                piece = self.board[row][col]
                if piece == 1:
                    symbol = "●"  # Player 1 (Red)
                elif piece == -1:
                    symbol = "○"  # Player 2 (Yellow)
                else:
                    symbol = " "

                line += symbol + " "
                if col < self.cols - 1:
                    line += "│ "

            lines.append(line + "║")

            if row < self.rows - 1:
                lines.append("╟─" + "──┼─" * (self.cols - 1) + "──╢")

        lines.append("╚═" + "══╧═" * (self.cols - 1) + "══╝")
        lines.append("  " + "  ".join(str(i) for i in range(self.cols)))

        return "\n".join(lines)

    def get_state(self) -> GameState:
        """Get current game state"""
        return GameState(
            board=[row[:] for row in self.board],
            current_player=self.current_player,
            move_count=self.move_count,
            result=self.result,
            winner=self.winner,
            last_move=self.last_move
        )

    def copy(self):
        """Create copy of game"""
        new_game = Connect4()
        new_game.board = [row[:] for row in self.board]
        new_game.current_player = self.current_player
        new_game.move_count = self.move_count
        new_game.result = self.result
        new_game.winner = self.winner
        new_game.last_move = self.last_move
        return new_game


class Othello:
    """
    Othello/Reversi Game

    Intermediate complexity. Capture opponent pieces by flanking.
    Board: 8x8 grid
    """

    def __init__(self):
        self.size = 8
        self.reset()

    def reset(self):
        """Reset to starting position"""
        self.board = [[0 for _ in range(self.size)] for _ in range(self.size)]

        # Starting position (center 2x2)
        mid = self.size // 2
        self.board[mid-1][mid-1] = -1  # Player 2
        self.board[mid-1][mid] = 1     # Player 1
        self.board[mid][mid-1] = 1     # Player 1
        self.board[mid][mid] = -1      # Player 2

        self.current_player = 1
        self.move_count = 0
        self.result = GameResult.ONGOING
        self.winner = None
        self.last_move = None
        self.consecutive_passes = 0

    def get_valid_moves(self) -> List[Tuple[int, int]]:
        """Get valid moves for current player"""
        valid = []

        for row in range(self.size):
            for col in range(self.size):
                if self.board[row][col] == 0 and self._would_flip(row, col, self.current_player):
                    valid.append((row, col))

        return valid

    def _would_flip(self, row: int, col: int, player: int) -> bool:
        """Check if placing piece would flip any opponent pieces"""
        if self.board[row][col] != 0:
            return False

        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

        for dr, dc in directions:
            if self._check_direction(row, col, dr, dc, player):
                return True

        return False

    def _check_direction(self, row: int, col: int, dr: int, dc: int, player: int) -> bool:
        """Check if placing piece would flip in this direction"""
        r, c = row + dr, col + dc
        found_opponent = False

        while 0 <= r < self.size and 0 <= c < self.size:
            if self.board[r][c] == 0:
                return False
            elif self.board[r][c] == -player:
                found_opponent = True
            elif self.board[r][c] == player:
                return found_opponent

            r += dr
            c += dc

        return False

    def make_move(self, move: Optional[Tuple[int, int]]) -> bool:
        """Place piece and flip opponent pieces"""
        # Handle pass
        if move is None:
            self.consecutive_passes += 1
            if self.consecutive_passes >= 2:
                self._end_game()
            else:
                self.current_player = -self.current_player
            return True

        row, col = move

        if move not in self.get_valid_moves():
            return False

        self.consecutive_passes = 0
        self.board[row][col] = self.current_player
        self.last_move = move

        # Flip pieces in all directions
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

        for dr, dc in directions:
            if self._check_direction(row, col, dr, dc, self.current_player):
                self._flip_direction(row, col, dr, dc, self.current_player)

        self.move_count += 1
        self.current_player = -self.current_player

        # Check if game over
        if not self.get_valid_moves():
            # Try passing to other player
            self.current_player = -self.current_player
            if not self.get_valid_moves():
                self._end_game()
            else:
                self.current_player = -self.current_player

        return True

    def _flip_direction(self, row: int, col: int, dr: int, dc: int, player: int):
        """Flip opponent pieces in direction"""
        r, c = row + dr, col + dc

        while 0 <= r < self.size and 0 <= c < self.size:
            if self.board[r][c] == -player:
                self.board[r][c] = player
            elif self.board[r][c] == player:
                break

            r += dr
            c += dc

    def _end_game(self):
        """Calculate final score and determine winner"""
        p1_count = sum(row.count(1) for row in self.board)
        p2_count = sum(row.count(-1) for row in self.board)

        if p1_count > p2_count:
            self.result = GameResult.PLAYER1_WIN
            self.winner = 1
        elif p2_count > p1_count:
            self.result = GameResult.PLAYER2_WIN
            self.winner = -1
        else:
            self.result = GameResult.DRAW
            self.winner = 0

    def visualize(self) -> str:
        """Return ASCII visualization"""
        lines = []
        lines.append("\n  " + " ".join(str(i) for i in range(self.size)))
        lines.append("┌─" + "─┬─" * (self.size - 1) + "─┐")

        for row in range(self.size):
            line = str(row) + "│"
            for col in range(self.size):
                piece = self.board[row][col]
                if piece == 1:
                    symbol = "●"  # Player 1 (Black)
                elif piece == -1:
                    symbol = "○"  # Player 2 (White)
                else:
                    symbol = " "

                line += symbol + "│"

            lines.append(line)

            if row < self.size - 1:
                lines.append(" ├─" + "─┼─" * (self.size - 1) + "─┤")

        lines.append(" └─" + "─┴─" * (self.size - 1) + "─┘")

        # Score
        p1_count = sum(row.count(1) for row in self.board)
        p2_count = sum(row.count(-1) for row in self.board)
        lines.append(f"\nScore: ● {p1_count}  ○ {p2_count}")

        return "\n".join(lines)

    def get_state(self) -> GameState:
        """Get current game state"""
        return GameState(
            board=[row[:] for row in self.board],
            current_player=self.current_player,
            move_count=self.move_count,
            result=self.result,
            winner=self.winner,
            last_move=self.last_move
        )

    def copy(self):
        """Create copy of game"""
        new_game = Othello()
        new_game.board = [row[:] for row in self.board]
        new_game.current_player = self.current_player
        new_game.move_count = self.move_count
        new_game.result = self.result
        new_game.winner = self.winner
        new_game.last_move = self.last_move
        new_game.consecutive_passes = self.consecutive_passes
        return new_game


def play_game_with_visualization(game, player1, player2, show_moves: bool = True):
    """
    Play a game with live visualization

    Args:
        game: Game instance (Connect4, Othello, etc.)
        player1: Agent with select_move method
        player2: Agent with select_move method
        show_moves: Print board after each move

    Returns:
        Winner (1, -1, or 0 for draw)
    """
    players = {1: player1, -1: player2}
    move_num = 0

    if show_moves:
        print("\n" + "="*50)
        print("GAME START")
        print("="*50)
        print(game.visualize())

    while game.result == GameResult.ONGOING:
        current = players[game.current_player]

        # Get valid moves
        if hasattr(game, 'get_valid_moves'):
            valid_moves = game.get_valid_moves()
        else:
            valid_moves = []

        if not valid_moves:
            # Pass or game over
            if isinstance(game, Othello):
                game.make_move(None)
                continue
            else:
                break

        # Agent selects move
        try:
            if hasattr(current, 'select_move'):
                move = current.select_move(game.get_state())
            else:
                move = random.choice(valid_moves)
        except Exception as e:
            print(f"Agent error: {e}")
            # Invalid move = loss
            game.winner = -game.current_player
            break

        # Make move
        if not game.make_move(move):
            print(f"Invalid move: {move}")
            game.winner = -game.current_player
            break

        move_num += 1

        if show_moves:
            player_name = "Player 1 (●)" if game.current_player == -1 else "Player 2 (○)"
            # Show previous player since we switched
            print(f"\nMove {move_num}: {player_name} → {move}")
            print(game.visualize())

    if show_moves:
        print("\n" + "="*50)
        print("GAME OVER")
        if game.winner == 1:
            print("Winner: Player 1 (●)")
        elif game.winner == -1:
            print("Winner: Player 2 (○)")
        else:
            print("Draw!")
        print("="*50)

    return game.winner
