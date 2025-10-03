"""
Othello Agent Template for Multi-Game Learning (v0.81)

Provides heuristic-based Othello agent that can learn from CRLS feedback.
Complements Connect4 agent for cross-game pattern discovery.
"""

import random
from typing import Dict, Any, List, Optional


class OthelloAgentTemplate:
    """
    Heuristic-based Othello agent with learning capabilities

    Starting heuristics:
    1. Take corners if available
    2. Avoid squares adjacent to corners (X-squares)
    3. Prefer edges
    4. Maximize piece flips
    5. Learning parameters adapt based on feedback
    """

    def __init__(self, agent_id: str = "othello_agent_001"):
        self.agent_id = agent_id
        self.games_played = 0
        self.strategy = "Play systematically in Othello"

        # Learning parameters
        self.corner_priority = 0.95  # Very high (corners are critical)
        self.edge_preference = 0.6   # Moderate (edges are good)
        self.avoid_x_squares = 0.8   # High (X-squares are bad)
        self.mobility_weight = 0.4   # Moderate

        # Othello board positions
        self.corners = [0, 7, 56, 63]  # 8x8 board corners
        self.x_squares = [1, 6, 8, 15, 48, 55, 57, 62]  # Adjacent to corners
        self.edges = list(range(8)) + list(range(56, 64)) + \
                     [i * 8 for i in range(8)] + [i * 8 + 7 for i in range(8)]

    def update_strategy(self, strategic_prompt: str):
        """Update strategy based on corrector feedback"""
        self.strategy = strategic_prompt
        prompt_lower = strategic_prompt.lower()

        # Parse feedback
        if "corner" in prompt_lower and "critical" in prompt_lower:
            self.corner_priority = min(1.0, self.corner_priority + 0.05)

        if "edge" in prompt_lower:
            self.edge_preference = min(0.9, self.edge_preference + 0.1)

        if "mobility" in prompt_lower or "flip" in prompt_lower:
            self.mobility_weight = min(0.8, self.mobility_weight + 0.1)

    def select_move(self, game_state) -> Optional[int]:
        """
        Select move using Othello heuristics

        Args:
            game_state: GameState object or dict with 'board' and 'current_player'

        Returns:
            Position (0-63) or None if no valid moves
        """
        self.games_played += 1

        # Handle both GameState object and dict
        if hasattr(game_state, 'board'):
            board = game_state.board
            current_player = game_state.current_player
        else:
            board = game_state.get('board', None)
            current_player = game_state.get('current_player', 1)

        if board is None:
            return None

        # Get valid moves (this would come from game logic)
        valid_moves = self._get_valid_moves(board, current_player)

        if not valid_moves:
            return None

        # 1. Take corners if available (highest priority)
        if random.random() < self.corner_priority:
            corner_moves = [m for m in valid_moves if m in self.corners]
            if corner_moves:
                return random.choice(corner_moves)

        # 2. Avoid X-squares (adjacent to empty corners)
        if random.random() < self.avoid_x_squares:
            safe_moves = [m for m in valid_moves if m not in self.x_squares
                         or self._is_x_square_safe(m, board)]
            if safe_moves:
                valid_moves = safe_moves

        # 3. Prefer edges
        if random.random() < self.edge_preference:
            edge_moves = [m for m in valid_moves if m in self.edges and m not in self.x_squares]
            if edge_moves:
                return random.choice(edge_moves)

        # 4. Maximize flips (mobility)
        if random.random() < self.mobility_weight and len(valid_moves) > 1:
            # Simple heuristic: prefer moves that flip more pieces
            # In real implementation, would calculate actual flips
            return random.choice(valid_moves)

        # 5. Random from remaining
        return random.choice(valid_moves)

    def _get_valid_moves(self, board: List[int], player: int) -> List[int]:
        """
        Get valid moves for current player

        This is simplified - actual Othello logic checks for valid flips
        """
        valid = []

        for pos in range(64):
            if board[pos] == 0:  # Empty square
                # Check if this move flips any pieces
                if self._would_flip_pieces(board, pos, player):
                    valid.append(pos)

        return valid

    def _would_flip_pieces(self, board: List[int], pos: int, player: int) -> bool:
        """
        Check if placing piece at pos would flip any opponent pieces

        Simplified version - checks all 8 directions
        """
        if board[pos] != 0:
            return False

        row = pos // 8
        col = pos % 8
        opponent = -player

        directions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]

        for dr, dc in directions:
            r, c = row + dr, col + dc
            found_opponent = False

            while 0 <= r < 8 and 0 <= c < 8:
                pos_check = r * 8 + c

                if board[pos_check] == 0:
                    break  # Empty square, no flip
                elif board[pos_check] == opponent:
                    found_opponent = True
                elif board[pos_check] == player:
                    if found_opponent:
                        return True  # Valid flip direction
                    break

                r += dr
                c += dc

        return False

    def _is_x_square_safe(self, pos: int, board: List[int]) -> bool:
        """Check if X-square is safe (adjacent corner is occupied)"""
        # Map X-squares to their adjacent corners
        x_to_corner = {
            1: 0, 6: 7, 8: 0, 15: 7,
            48: 56, 55: 63, 57: 56, 62: 63
        }

        if pos in x_to_corner:
            corner = x_to_corner[pos]
            return board[corner] != 0  # Safe if corner is occupied

        return True


class RandomOthelloOpponent:
    """Random Othello opponent for testing"""

    def __init__(self, name: str = "RandomOthelloBot"):
        self.name = name

    def select_move(self, game_state) -> Optional[int]:
        """Select random valid move"""
        if hasattr(game_state, 'board'):
            board = game_state.board
            current_player = game_state.current_player
        else:
            board = game_state.get('board', None)
            current_player = game_state.get('current_player', 1)

        if board is None:
            return None

        # Get valid moves
        valid_moves = []
        for pos in range(64):
            if board[pos] == 0:
                valid_moves.append(pos)

        return random.choice(valid_moves) if valid_moves else None


# Factory function for IEE compatibility
def create_agent(agent_id: str = "othello_agent"):
    """Factory function to create Othello agents"""
    return OthelloAgentTemplate(agent_id)
