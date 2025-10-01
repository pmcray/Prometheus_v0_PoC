#!/usr/bin/env python3
"""
Game Visualization Demo for Project Prometheus

This demonstrates:
1. Three games with increasing complexity (Connect4, Othello, Draughts)
2. Visual game boards showing each move
3. Agent "thinking" visualization using heuristics
4. Evolution-ready agent templates

Usage:
    python demo_game_visualization.py [game] [show_thinking]

    game: connect4, othello, draughts (default: connect4)
    show_thinking: true/false (default: true)
"""

import sys
import random
from prometheus.game_suite import Connect4, Othello, play_game_with_visualization, GameResult
from benchmarks.prometheus_bench_v0_2 import DraughtsGame


class HeuristicAgent:
    """
    Simple heuristic-based agent template

    This is a better starting point than random play. It uses basic
    heuristics that the evolutionary process can then refine.
    """

    def __init__(self, name: str = "Agent", game_type: str = "connect4"):
        self.name = name
        self.game_type = game_type
        self.move_history = []
        self.thinking = []

    def select_move(self, game_state):
        """
        Select move using simple heuristics

        This method tracks "thinking" so we can visualize the agent's
        decision-making process.
        """
        self.thinking = []

        if self.game_type == "connect4":
            return self._select_connect4_move(game_state)
        elif self.game_type == "othello":
            return self._select_othello_move(game_state)
        elif self.game_type == "draughts":
            return self._select_draughts_move(game_state)
        else:
            # Fallback to random
            if hasattr(game_state, 'board'):
                valid_moves = self._get_valid_moves(game_state)
                return random.choice(valid_moves) if valid_moves else None
            return None

    def _select_connect4_move(self, game_state):
        """
        Connect 4 heuristic:
        1. Win if possible
        2. Block opponent win
        3. Prefer center columns
        4. Random from remaining
        """
        if hasattr(game_state, 'board'):
            board = game_state.board
            current_player = game_state.current_player
        else:
            board = game_state['board']
            current_player = game_state['current_player']

        valid_moves = [col for col in range(7) if board[0][col] == 0]

        if not valid_moves:
            return None

        self.thinking.append(f"Valid moves: {valid_moves}")

        # Try to win
        for move in valid_moves:
            if self._would_win_connect4(board, move, current_player):
                self.thinking.append(f"WINNING MOVE: {move}")
                return move

        # Block opponent
        for move in valid_moves:
            if self._would_win_connect4(board, move, -current_player):
                self.thinking.append(f"BLOCKING MOVE: {move}")
                return move

        # Prefer center
        center_moves = [m for m in valid_moves if 2 <= m <= 4]
        if center_moves:
            move = random.choice(center_moves)
            self.thinking.append(f"Center column: {move}")
            return move

        move = random.choice(valid_moves)
        self.thinking.append(f"Random move: {move}")
        return move

    def _would_win_connect4(self, board, col, player):
        """Check if move would create 4-in-a-row"""
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

        # Check for 4-in-a-row
        win = self._check_connect4_win(board, row, col, player)

        # Remove piece
        board[row][col] = 0

        return win

    def _check_connect4_win(self, board, row, col, player):
        """Check if position has 4-in-a-row"""
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

        # Diagonals
        for dr, dc in [(1, 1), (1, -1)]:
            count = 1
            for direction in [-1, 1]:
                r, c = row + dr * direction, col + dc * direction
                while 0 <= r < 6 and 0 <= c < 7 and board[r][c] == player:
                    count += 1
                    r += dr * direction
                    c += dc * direction
            if count >= 4:
                return True

        return False

    def _select_othello_move(self, game_state):
        """
        Othello heuristic:
        1. Prefer corners (very strong positions)
        2. Avoid squares next to corners
        3. Maximize pieces flipped
        4. Random from remaining
        """
        if hasattr(game_state, 'board'):
            board = game_state.board
            valid_moves = self._get_othello_valid_moves(game_state)
        else:
            return None

        if not valid_moves:
            return None

        self.thinking.append(f"Valid moves: {len(valid_moves)}")

        # Corners are best
        corners = [(0, 0), (0, 7), (7, 0), (7, 7)]
        corner_moves = [m for m in valid_moves if m in corners]
        if corner_moves:
            move = random.choice(corner_moves)
            self.thinking.append(f"CORNER: {move}")
            return move

        # Avoid squares next to corners (danger zones)
        danger = [(0, 1), (1, 0), (1, 1),  # Near (0,0)
                  (0, 6), (1, 6), (1, 7),  # Near (0,7)
                  (6, 0), (6, 1), (7, 1),  # Near (7,0)
                  (6, 6), (6, 7), (7, 6)]  # Near (7,7)
        safe_moves = [m for m in valid_moves if m not in danger]

        if safe_moves:
            move = random.choice(safe_moves)
            self.thinking.append(f"Safe move: {move}")
        else:
            move = random.choice(valid_moves)
            self.thinking.append(f"Forced danger: {move}")

        return move

    def _get_othello_valid_moves(self, game_state):
        """Get valid Othello moves"""
        if hasattr(game_state, 'get_valid_moves'):
            return game_state.get_valid_moves()
        return []

    def _select_draughts_move(self, game_state):
        """
        Draughts heuristic:
        1. Prefer captures
        2. Advance pieces toward opponent
        3. Protect pieces
        4. Random from remaining
        """
        if hasattr(game_state, 'board'):
            board = game_state.board
            current_player = game_state.current_player
        else:
            board = game_state['board']
            current_player = game_state['current_player']

        valid_moves = self._get_draughts_valid_moves(board, current_player)

        if not valid_moves:
            return None

        self.thinking.append(f"Valid moves: {len(valid_moves)}")

        # Prefer captures (moves of length 2 diagonally)
        captures = [m for m in valid_moves if abs(m[0][0] - m[1][0]) == 2]
        if captures:
            move = random.choice(captures)
            self.thinking.append(f"CAPTURE: {move}")
            return move

        # Prefer forward moves (advancing)
        forward_moves = []
        for move in valid_moves:
            from_row, to_row = move[0][0], move[1][0]
            if current_player == 1 and to_row < from_row:  # Moving up
                forward_moves.append(move)
            elif current_player == -1 and to_row > from_row:  # Moving down
                forward_moves.append(move)

        if forward_moves:
            move = random.choice(forward_moves)
            self.thinking.append(f"Forward: {move}")
        else:
            move = random.choice(valid_moves)
            self.thinking.append(f"Random: {move}")

        return move

    def _get_draughts_valid_moves(self, board, player):
        """Get valid Draughts moves"""
        moves = []

        for row in range(8):
            for col in range(8):
                piece = board[row][col]

                if (player == 1 and piece > 0) or (player == -1 and piece < 0):
                    is_king = abs(piece) == 2

                    # Determine directions
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

                    # Captures
                    for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                        capture_row, capture_col = row + dr, col + dc
                        land_row, land_col = row + 2*dr, col + 2*dc

                        if 0 <= land_row < 8 and 0 <= land_col < 8:
                            if board[land_row][land_col] == 0:
                                capture_piece = board[capture_row][capture_col]
                                if (piece > 0 and capture_piece < 0) or (piece < 0 and capture_piece > 0):
                                    moves.append(((row, col), (land_row, land_col)))

        # Prioritize captures
        captures = [m for m in moves if abs(m[0][0] - m[1][0]) == 2]
        return captures if captures else moves

    def _get_valid_moves(self, game_state):
        """Generic valid move getter"""
        if hasattr(game_state, 'get_valid_moves'):
            return game_state.get_valid_moves()
        return []

    def show_thinking(self):
        """Display agent's thinking process"""
        if self.thinking:
            print(f"\n🧠 {self.name} thinking:")
            for thought in self.thinking:
                print(f"   {thought}")


def demo_game(game_name: str = "connect4", show_thinking: bool = True):
    """
    Run a demo game with visualization

    Args:
        game_name: "connect4", "othello", or "draughts"
        show_thinking: Show agent thinking process
    """
    print("="*70)
    print(f"PROJECT PROMETHEUS - {game_name.upper()} DEMO")
    print("="*70)

    # Create game
    if game_name == "connect4":
        game = Connect4()
        game_type = "connect4"
    elif game_name == "othello":
        game = Othello()
        game_type = "othello"
    elif game_name == "draughts":
        game = DraughtsGame()
        game_type = "draughts"
    else:
        print(f"Unknown game: {game_name}")
        return

    # Create agents
    agent1 = HeuristicAgent("Agent A", game_type)
    agent2 = HeuristicAgent("Agent B", game_type)

    print(f"\nPlaying: {agent1.name} (●) vs {agent2.name} (○)")
    print(f"Game: {game_name.title()}")
    print(f"Show thinking: {show_thinking}\n")

    # Play game with visualization
    winner = play_game_with_agents(game, agent1, agent2, show_thinking)

    print("\n" + "="*70)
    if winner == 1:
        print(f"🏆 {agent1.name} WINS!")
    elif winner == -1:
        print(f"🏆 {agent2.name} WINS!")
    else:
        print("🤝 DRAW!")
    print("="*70)


def play_game_with_agents(game, agent1, agent2, show_thinking: bool = True):
    """Play game with thinking visualization"""
    agents = {1: agent1, -1: agent2}
    move_num = 0

    print(game.visualize())

    # Check if game is over (handle both DraughtsGame and new game types)
    def is_game_over():
        if hasattr(game, 'game_over'):
            return game.game_over
        elif hasattr(game, 'result'):
            if hasattr(game.result, 'value'):
                return game.result.value != 'ongoing'
            return game.result != GameResult.ONGOING
        return False

    while not is_game_over():
        current_agent = agents[game.current_player]

        # Show whose turn
        player_name = agent1.name if game.current_player == 1 else agent2.name
        symbol = "●" if game.current_player == 1 else "○"
        print(f"\n{'─'*70}")
        print(f"Move {move_num + 1}: {player_name} ({symbol}) to move")

        # Agent selects move
        try:
            move = current_agent.select_move(game)
        except Exception as e:
            print(f"❌ Agent error: {e}")
            break

        # Show thinking
        if show_thinking:
            current_agent.show_thinking()

        if move is None:
            print(f"  → Pass")
        else:
            print(f"  → Selected: {move}")

        # Make move
        success = game.make_move(move) if move is not None else False

        if not success and move is not None:
            print(f"❌ Invalid move!")
            break

        move_num += 1
        print(game.visualize())

        # Limit moves
        if move_num > 100:
            print("\n⏱️ Move limit reached (100 moves)")
            break

    # Get winner
    if hasattr(game, 'winner'):
        return game.winner
    elif hasattr(game, 'result'):
        if 'player1' in str(game.result):
            return 1
        elif 'player2' in str(game.result):
            return -1
    return 0


if __name__ == "__main__":
    game_name = sys.argv[1] if len(sys.argv) > 1 else "connect4"
    show_thinking = sys.argv[2].lower() != "false" if len(sys.argv) > 2 else True

    demo_game(game_name, show_thinking)
