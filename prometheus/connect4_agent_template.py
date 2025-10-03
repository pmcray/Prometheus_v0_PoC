"""
Connect4 Agent Template for Evolution

This provides a heuristic-based starting point for Connect4 agents,
which is much better than random play. The evolutionary process will
refine and improve these heuristics.
"""

import random
from typing import Dict, Any, List
from prometheus.domain_expert_agent import RandomDomainExpertAgent, AgentDomain


class Connect4AgentTemplate(RandomDomainExpertAgent):
    """
    Heuristic-based Connect4 agent template

    Starting heuristics:
    1. Win if possible
    2. Block opponent wins
    3. Prefer center columns
    4. Random from remaining moves

    Evolution will refine these priorities and add new heuristics.
    """

    def __init__(self, agent_id: str = "connect4_agent_000"):
        super().__init__(agent_id, AgentDomain.GENERAL_GAME_PLAYING)
        self.game_type = "connect4"

    def select_move(self, game_state) -> int:
        """
        Select move using heuristic strategy

        Args:
            game_state: GameState object or dict with 'board' and 'current_player'

        Returns:
            Column number (0-6) or None if no valid moves
        """
        # Handle both GameState object and dict
        if hasattr(game_state, 'board'):
            board = game_state.board
            current_player = game_state.current_player
        elif isinstance(game_state, dict):
            if 'board' not in game_state or 'current_player' not in game_state:
                # Invalid state - pick random column
                return random.randint(0, 6)
            board = game_state['board']
            current_player = game_state['current_player']
        else:
            # Unknown format - pick random
            return random.randint(0, 6)

        # Get valid moves (columns that aren't full)
        valid_moves = [col for col in range(7) if board[0][col] == 0]

        if not valid_moves:
            return None

        # 1. Check for winning moves
        for move in valid_moves:
            if self._would_win(board, move, current_player):
                return move

        # 2. Block opponent wins
        opponent = -current_player
        for move in valid_moves:
            if self._would_win(board, move, opponent):
                return move

        # 3. Prefer center columns (columns 2-4)
        center_moves = [m for m in valid_moves if 2 <= m <= 4]
        if center_moves:
            return random.choice(center_moves)

        # 4. Random from remaining
        return random.choice(valid_moves)

    def _would_win(self, board: List[List[int]], col: int, player: int) -> bool:
        """
        Check if placing a piece in this column would create 4-in-a-row

        Args:
            board: Current board state
            col: Column to check
            player: Player number (1 or -1)

        Returns:
            True if this move wins the game
        """
        # Find where piece would land
        row = None
        for r in range(5, -1, -1):
            if board[r][col] == 0:
                row = r
                break

        if row is None:
            return False

        # Temporarily place piece
        board[row][col] = player

        # Check for win
        win = self._check_win(board, row, col, player)

        # Remove piece
        board[row][col] = 0

        return win

    def _check_win(self, board: List[List[int]], row: int, col: int, player: int) -> bool:
        """
        Check if there's a 4-in-a-row including position (row, col)

        Checks horizontal, vertical, and both diagonals.
        """
        # Horizontal
        count = 1
        # Check left
        c = col - 1
        while c >= 0 and board[row][c] == player:
            count += 1
            c -= 1
        # Check right
        c = col + 1
        while c < 7 and board[row][c] == player:
            count += 1
            c += 1
        if count >= 4:
            return True

        # Vertical
        count = 1
        # Check down
        r = row + 1
        while r < 6 and board[r][col] == player:
            count += 1
            r += 1
        # Check up
        r = row - 1
        while r >= 0 and board[r][col] == player:
            count += 1
            r -= 1
        if count >= 4:
            return True

        # Diagonal (down-right)
        count = 1
        r, c = row + 1, col + 1
        while r < 6 and c < 7 and board[r][c] == player:
            count += 1
            r += 1
            c += 1
        r, c = row - 1, col - 1
        while r >= 0 and c >= 0 and board[r][c] == player:
            count += 1
            r -= 1
            c -= 1
        if count >= 4:
            return True

        # Diagonal (down-left)
        count = 1
        r, c = row + 1, col - 1
        while r < 6 and c >= 0 and board[r][c] == player:
            count += 1
            r += 1
            c -= 1
        r, c = row - 1, col + 1
        while r >= 0 and c < 7 and board[r][c] == player:
            count += 1
            r -= 1
            c += 1
        if count >= 4:
            return True

        return False


# For IEE compatibility
def create_agent(agent_id: str = "connect4_agent"):
    """Factory function to create Connect4 agents"""
    return Connect4AgentTemplate(agent_id)
