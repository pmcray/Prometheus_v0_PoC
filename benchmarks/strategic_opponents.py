"""
Strategic Opponents for Evolution
Provides opponents of varying skill levels to create learning gradients
"""

import random
from typing import Optional
from prometheus.game_suite import Connect4


class RandomOpponent:
    """Baseline random opponent (weakest)"""
    def __init__(self, name: str = "RandomBot"):
        self.name = name
        self.skill_level = 0

    def select_move(self, game_state) -> Optional[int]:
        if hasattr(game_state, 'board'):
            board = game_state.board
        else:
            board = game_state['board']

        valid_moves = [col for col in range(7) if board[0][col] == 0]
        return random.choice(valid_moves) if valid_moves else None


class HeuristicOpponent:
    """
    Heuristic-based opponent (medium skill)

    Strategy:
    1. Win if possible (check for 3-in-a-row with empty 4th)
    2. Block opponent's winning move
    3. Prefer center columns
    4. Avoid edges unless necessary
    """
    def __init__(self, name: str = "HeuristicBot"):
        self.name = name
        self.skill_level = 5

    def select_move(self, game_state) -> Optional[int]:
        if hasattr(game_state, 'board'):
            board = game_state.board
            player = game_state.current_player
        else:
            board = game_state['board']
            player = game_state.get('current_player', 1)

        valid_moves = [col for col in range(7) if board[0][col] == 0]
        if not valid_moves:
            return None

        # 1. Check for winning move
        for col in valid_moves:
            if self._is_winning_move(board, col, player):
                return col

        # 2. Block opponent's winning move
        opponent = -player
        for col in valid_moves:
            if self._is_winning_move(board, col, opponent):
                return col

        # 3. Prefer center (column 3), then nearby columns
        center_preference = [3, 2, 4, 1, 5, 0, 6]
        for col in center_preference:
            if col in valid_moves:
                return col

        return random.choice(valid_moves)

    def _is_winning_move(self, board, col: int, player: int) -> bool:
        """Check if placing piece in col wins for player"""
        # Find row where piece would land
        row = None
        for r in range(5, -1, -1):
            if board[r][col] == 0:
                row = r
                break

        if row is None:
            return False

        # Temporarily place piece
        board[row][col] = player

        # Check win conditions
        win = self._check_win(board, row, col, player)

        # Remove piece
        board[row][col] = 0

        return win

    def _check_win(self, board, row: int, col: int, player: int) -> bool:
        """Check if position (row, col) creates 4-in-a-row for player"""
        # Horizontal
        count = 1
        for dc in [-1, 1]:
            c = col + dc
            while 0 <= c < 7 and board[row][c] == player:
                count += 1
                c += dc
        if count >= 4:
            return True

        # Vertical
        count = 1
        for dr in [-1, 1]:
            r = row + dr
            while 0 <= r < 6 and board[r][col] == player:
                count += 1
                r += dr
        if count >= 4:
            return True

        # Diagonal /
        count = 1
        for d in [-1, 1]:
            r, c = row + d, col + d
            while 0 <= r < 6 and 0 <= c < 7 and board[r][c] == player:
                count += 1
                r += d
                c += d
        if count >= 4:
            return True

        # Diagonal \
        count = 1
        for d in [-1, 1]:
            r, c = row + d, col - d
            while 0 <= r < 6 and 0 <= c < 7 and board[r][c] == player:
                count += 1
                r += d
                c -= d
        if count >= 4:
            return True

        return False


class MinimaxOpponent:
    """
    Minimax-based opponent (strong)

    Uses alpha-beta pruning with configurable depth
    """
    def __init__(self, depth: int = 3, name: str = "MinimaxBot"):
        self.name = name
        self.depth = depth
        self.skill_level = 8

    def select_move(self, game_state) -> Optional[int]:
        if hasattr(game_state, 'board'):
            board = [row[:] for row in game_state.board]  # Copy
            player = game_state.current_player
        else:
            board = [row[:] for row in game_state['board']]
            player = game_state.get('current_player', 1)

        valid_moves = [col for col in range(7) if board[0][col] == 0]
        if not valid_moves:
            return None

        best_score = float('-inf')
        best_moves = []

        for col in valid_moves:
            # Make move
            row = self._drop_piece(board, col, player)
            if row is None:
                continue

            # Evaluate
            score = self._minimax(board, self.depth - 1, float('-inf'), float('inf'), False, player, -player)

            # Undo move
            board[row][col] = 0

            if score > best_score:
                best_score = score
                best_moves = [col]
            elif score == best_score:
                best_moves.append(col)

        return random.choice(best_moves) if best_moves else random.choice(valid_moves)

    def _minimax(self, board, depth: int, alpha: float, beta: float, maximizing: bool, max_player: int, current_player: int) -> float:
        """Minimax with alpha-beta pruning"""
        # Check terminal states
        if self._check_winner(board, max_player):
            return 1000 + depth  # Prefer faster wins
        if self._check_winner(board, -max_player):
            return -1000 - depth  # Prefer slower losses

        valid_moves = [col for col in range(7) if board[0][col] == 0]
        if not valid_moves or depth == 0:
            return self._evaluate_position(board, max_player)

        if maximizing:
            max_eval = float('-inf')
            for col in valid_moves:
                row = self._drop_piece(board, col, current_player)
                if row is not None:
                    eval_score = self._minimax(board, depth - 1, alpha, beta, False, max_player, -current_player)
                    board[row][col] = 0  # Undo
                    max_eval = max(max_eval, eval_score)
                    alpha = max(alpha, eval_score)
                    if beta <= alpha:
                        break
            return max_eval
        else:
            min_eval = float('inf')
            for col in valid_moves:
                row = self._drop_piece(board, col, current_player)
                if row is not None:
                    eval_score = self._minimax(board, depth - 1, alpha, beta, True, max_player, -current_player)
                    board[row][col] = 0  # Undo
                    min_eval = min(min_eval, eval_score)
                    beta = min(beta, eval_score)
                    if beta <= alpha:
                        break
            return min_eval

    def _drop_piece(self, board, col: int, player: int) -> Optional[int]:
        """Drop piece in column, return row (or None if full)"""
        for row in range(5, -1, -1):
            if board[row][col] == 0:
                board[row][col] = player
                return row
        return None

    def _check_winner(self, board, player: int) -> bool:
        """Check if player has won"""
        # Horizontal
        for r in range(6):
            for c in range(4):
                if all(board[r][c+i] == player for i in range(4)):
                    return True

        # Vertical
        for r in range(3):
            for c in range(7):
                if all(board[r+i][c] == player for i in range(4)):
                    return True

        # Diagonal /
        for r in range(3, 6):
            for c in range(4):
                if all(board[r-i][c+i] == player for i in range(4)):
                    return True

        # Diagonal \
        for r in range(3):
            for c in range(4):
                if all(board[r+i][c+i] == player for i in range(4)):
                    return True

        return False

    def _evaluate_position(self, board, player: int) -> float:
        """Heuristic evaluation of board position"""
        score = 0

        # Center column control
        center_count = sum(1 for r in range(6) if board[r][3] == player)
        score += center_count * 3

        # Count potential 4-in-a-rows
        score += self._count_windows(board, player, 4) * 100
        score += self._count_windows(board, player, 3) * 10
        score += self._count_windows(board, player, 2) * 1

        # Penalize opponent's potential
        score -= self._count_windows(board, -player, 4) * 100
        score -= self._count_windows(board, -player, 3) * 10
        score -= self._count_windows(board, -player, 2) * 1

        return score

    def _count_windows(self, board, player: int, length: int) -> int:
        """Count windows with 'length' pieces of player and rest empty"""
        count = 0

        # Horizontal
        for r in range(6):
            for c in range(4):
                window = [board[r][c+i] for i in range(4)]
                if window.count(player) == length and window.count(0) == 4 - length:
                    count += 1

        # Vertical
        for r in range(3):
            for c in range(7):
                window = [board[r+i][c] for i in range(4)]
                if window.count(player) == length and window.count(0) == 4 - length:
                    count += 1

        # Diagonals
        for r in range(3, 6):
            for c in range(4):
                window = [board[r-i][c+i] for i in range(4)]
                if window.count(player) == length and window.count(0) == 4 - length:
                    count += 1

        for r in range(3):
            for c in range(4):
                window = [board[r+i][c+i] for i in range(4)]
                if window.count(player) == length and window.count(0) == 4 - length:
                    count += 1

        return count


class AdaptiveOpponent:
    """
    Adaptive opponent that adjusts difficulty based on agent performance

    Starts weak and gets stronger as agent improves
    """
    def __init__(self, initial_level: int = 1):
        self.level = initial_level
        self.opponents = {
            0: RandomOpponent("Adaptive-Random"),
            1: HeuristicOpponent("Adaptive-Heuristic"),
            2: MinimaxOpponent(depth=2, name="Adaptive-Minimax-Easy"),
            3: MinimaxOpponent(depth=3, name="Adaptive-Minimax-Medium"),
            4: MinimaxOpponent(depth=4, name="Adaptive-Minimax-Hard"),
        }
        self.current_opponent = self.opponents[min(initial_level, 4)]
        self.name = f"AdaptiveBot-L{initial_level}"
        self.skill_level = initial_level

    def select_move(self, game_state) -> Optional[int]:
        return self.current_opponent.select_move(game_state)

    def adjust_difficulty(self, agent_win_rate: float):
        """Adjust difficulty based on agent performance"""
        if agent_win_rate > 0.7 and self.level < 4:
            self.level += 1
            self.current_opponent = self.opponents[self.level]
            print(f"  📈 Opponent difficulty increased to level {self.level}")
        elif agent_win_rate < 0.3 and self.level > 0:
            self.level -= 1
            self.current_opponent = self.opponents[self.level]
            print(f"  📉 Opponent difficulty decreased to level {self.level}")


# Opponent ladder for curriculum training
OPPONENT_LADDER = [
    ("Random", RandomOpponent()),
    ("Heuristic", HeuristicOpponent()),
    ("Minimax-Depth1", MinimaxOpponent(depth=1)),
    ("Minimax-Depth2", MinimaxOpponent(depth=2)),
    ("Minimax-Depth3", MinimaxOpponent(depth=3)),
]
