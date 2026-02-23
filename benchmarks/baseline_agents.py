"""
Baseline agents for testing Prometheus-Bench-v0.2
Provides reference implementations for each benchmark domain
"""

import random
from typing import Dict, List, Any, Optional, Tuple


class RandomDraughtsAgent:
    """
    Random move player for Draughts
    Used as baseline for comparison
    """

    def __init__(self):
        self.name = "RandomDraughtsAgent"

    def select_move(self, game_state: Dict[str, Any]) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Select a random valid move from game state

        Args:
            game_state: Dictionary containing game state with valid moves

        Returns:
            Random move tuple ((from_row, from_col), (to_row, to_col))
        """
        try:
            # Parse board to find valid moves
            board = game_state["board"]
            current_player = game_state["current_player"]

            # Find all pieces belonging to current player
            valid_moves = []

            for from_row in range(8):
                for from_col in range(8):
                    piece = board[from_row][from_col]

                    # Check if piece belongs to current player
                    if (current_player == 1 and piece > 0) or (current_player == -1 and piece < 0):
                        # Check possible moves for this piece
                        moves = self._get_moves_for_piece(board, from_row, from_col, piece)
                        valid_moves.extend(moves)

            # Return random valid move
            return random.choice(valid_moves) if valid_moves else None

        except Exception as e:
            print(f"Error in RandomDraughtsAgent: {e}")
            return None

    def _get_moves_for_piece(self, board: List[List[int]], row: int, col: int, piece: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Get valid moves for a specific piece"""
        moves = []
        is_king = abs(piece) == 2

        # Determine valid directions
        if piece > 0:
            directions = [(-1, -1), (-1, 1)]
            if is_king:
                directions.extend([(1, -1), (1, 1)])
        else:
            directions = [(1, -1), (1, 1)]
            if is_king:
                directions.extend([(-1, -1), (-1, 1)])

        # Check simple moves
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                if board[new_row][new_col] == 0:
                    moves.append(((row, col), (new_row, new_col)))

        # Check capture moves
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            capture_row, capture_col = row + dr, col + dc
            land_row, land_col = row + 2*dr, col + 2*dc

            if 0 <= land_row < 8 and 0 <= land_col < 8:
                if 0 <= capture_row < 8 and 0 <= capture_col < 8:
                    if board[land_row][land_col] == 0:
                        capture_piece = board[capture_row][capture_col]
                        if (piece > 0 and capture_piece < 0) or (piece < 0 and capture_piece > 0):
                            moves.append(((row, col), (land_row, land_col)))

        return moves


class SimpleChatbotAgent:
    """
    Simple conversational agent for testing
    Uses basic response patterns
    """

    def __init__(self):
        self.name = "SimpleChatbotAgent"
        self.response_templates = [
            "That's an interesting question. Let me help you with that.",
            "I understand. Here's what I can tell you about that topic.",
            "Good question! Let me provide some information.",
            "I'm happy to help with that.",
            "Let me explain that in more detail."
        ]

    def generate_response(self, conversation_history: List[Dict[str, str]]) -> str:
        """
        Generate response based on conversation history

        Args:
            conversation_history: List of {"role": "user/assistant", "content": "..."}

        Returns:
            Response string
        """
        try:
            # Get last user message
            user_messages = [msg for msg in conversation_history if msg["role"] == "user"]

            if not user_messages:
                return "Hello! How can I help you today?"

            last_user_msg = user_messages[-1]["content"].lower()

            # Simple pattern matching
            if "hello" in last_user_msg or "hi" in last_user_msg:
                return "Hello! I'm here to assist you. What would you like to know?"

            elif "thank" in last_user_msg:
                return "You're welcome! Feel free to ask if you need anything else."

            elif "example" in last_user_msg:
                return "Here's an example: Let's say you want to learn about a topic. You can ask me specific questions and I'll provide detailed answers to help you understand better."

            elif "key points" in last_user_msg or "remember" in last_user_msg:
                return "The key points to remember are: 1) Ask specific questions for better answers, 2) I'm here to help with a wide range of topics, and 3) Feel free to ask for clarification anytime."

            elif "more" in last_user_msg:
                return "Certainly! I can provide more detailed information. The topic we're discussing has several important aspects worth exploring. Each aspect contributes to a fuller understanding of the subject matter."

            else:
                # Default response with topic echo
                response = random.choice(self.response_templates)

                # Try to extract topic from message
                words = last_user_msg.split()
                if len(words) > 3:
                    topic_words = [w for w in words if len(w) > 4]
                    if topic_words:
                        topic = topic_words[0]
                        response += f" Regarding {topic}, it's important to understand the fundamentals first."

                return response

        except Exception as e:
            return "I apologize, but I'm having trouble processing that request. Could you please rephrase?"


class ImprovedDraughtsAgent:
    """
    Slightly improved Draughts agent with basic strategy
    Prioritizes captures and king pieces
    """

    def __init__(self):
        self.name = "ImprovedDraughtsAgent"

    def select_move(self, game_state: Dict[str, Any]) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Select move with basic strategic priorities"""
        try:
            board = game_state["board"]
            current_player = game_state["current_player"]

            # Find all valid moves
            all_moves = []
            capture_moves = []
            king_moves = []

            for from_row in range(8):
                for from_col in range(8):
                    piece = board[from_row][from_col]

                    if (current_player == 1 and piece > 0) or (current_player == -1 and piece < 0):
                        moves = self._get_moves_for_piece(board, from_row, from_col, piece)

                        for move in moves:
                            all_moves.append(move)

                            # Categorize moves
                            if self._is_capture(move):
                                capture_moves.append(move)

                            if abs(piece) == 2:  # King piece
                                king_moves.append(move)

            # Priority: captures > king moves > random
            if capture_moves:
                return random.choice(capture_moves)
            elif king_moves:
                return random.choice(king_moves)
            elif all_moves:
                return random.choice(all_moves)
            else:
                return None

        except Exception as e:
            print(f"Error in ImprovedDraughtsAgent: {e}")
            return None

    def _get_moves_for_piece(self, board: List[List[int]], row: int, col: int, piece: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Get valid moves for a piece"""
        moves = []
        is_king = abs(piece) == 2

        if piece > 0:
            directions = [(-1, -1), (-1, 1)]
            if is_king:
                directions.extend([(1, -1), (1, 1)])
        else:
            directions = [(1, -1), (1, 1)]
            if is_king:
                directions.extend([(-1, -1), (-1, 1)])

        # Simple moves
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                if board[new_row][new_col] == 0:
                    moves.append(((row, col), (new_row, new_col)))

        # Capture moves
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            capture_row, capture_col = row + dr, col + dc
            land_row, land_col = row + 2*dr, col + 2*dc

            if 0 <= land_row < 8 and 0 <= land_col < 8:
                if 0 <= capture_row < 8 and 0 <= capture_col < 8:
                    if board[land_row][land_col] == 0:
                        capture_piece = board[capture_row][capture_col]
                        if (piece > 0 and capture_piece < 0) or (piece < 0 and capture_piece > 0):
                            moves.append(((row, col), (land_row, land_col)))

        return moves

    def _is_capture(self, move: Tuple[Tuple[int, int], Tuple[int, int]]) -> bool:
        """Check if move is a capture"""
        (from_row, from_col), (to_row, to_col) = move
        return abs(to_row - from_row) == 2