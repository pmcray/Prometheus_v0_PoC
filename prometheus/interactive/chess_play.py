"""
Interactive Chess Play

Human vs AI chess gameplay with visual board and move input.

Features:
- Visual SVG board rendering in Jupyter/Colab
- UCI notation move input (e.g., "e2e4")
- Legal move validation
- Move suggestions with probabilities
- Game history tracking
- ELO estimation

Usage:
    >>> from prometheus.interactive import ChessInteractiveGame
    >>> game = ChessInteractiveGame(agent=prometheus_chess_agent)
    >>> game.play()  # Start interactive session
"""

import chess
import chess.svg
import numpy as np
from typing import Optional, Any, List, Tuple
from IPython.display import display, SVG, HTML, clear_output
import ipywidgets as widgets


class ChessInteractiveGame:
    """
    Interactive chess game between human and Prometheus agent.

    Features:
    - Visual board display
    - Move input with validation
    - AI move display with evaluation
    - Game history
    - Result analysis

    Attributes:
        agent: Prometheus chess agent
        board: Current chess board state
        human_color: Human player's color (WHITE or BLACK)
        move_history: List of moves played
        game_active: Whether game is in progress
    """

    def __init__(
        self,
        agent: Any,
        human_plays_white: bool = True,
        show_suggestions: bool = True,
        verbose: bool = True
    ):
        """
        Initialize interactive chess game.

        Args:
            agent: Chess agent with get_move() method
            human_plays_white: If True, human plays white; else black
            show_suggestions: Show AI's top move suggestions
            verbose: Print move commentary
        """
        self.agent = agent
        self.human_color = chess.WHITE if human_plays_white else chess.BLACK
        self.show_suggestions = show_suggestions
        self.verbose = verbose

        # Game state
        self.board = chess.Board()
        self.move_history = []
        self.game_active = True

        # Statistics
        self.position_evaluations = []

    def play(self):
        """
        Start interactive game.

        This method provides a turn-based interface:
        - Human enters moves via text input
        - AI responds with its best move
        - Board is displayed after each move
        - Game continues until checkmate, stalemate, or resignation
        """
        print("=" * 70)
        print("♟️  INTERACTIVE CHESS: HUMAN VS PROMETHEUS")
        print("=" * 70)
        print(f"You are playing {'WHITE' if self.human_color == chess.WHITE else 'BLACK'}")
        print("Enter moves in UCI notation (e.g., 'e2e4')")
        print("Special commands: 'resign', 'draw', 'quit'")
        print("=" * 70)

        while self.game_active and not self.board.is_game_over():
            # Display board
            self.display_board()

            # Check whose turn
            if self.board.turn == self.human_color:
                # Human's turn
                self._human_move()
            else:
                # AI's turn
                self._ai_move()

        # Game ended
        self._display_result()

    def display_board(self, size: int = 400):
        """Display current board state."""
        try:
            # Try SVG display (works in Jupyter/Colab)
            svg_board = chess.svg.board(
                board=self.board,
                size=size,
                orientation=self.human_color
            )
            display(SVG(svg_board))
        except Exception:
            # Fallback to text display (e.g., not running in Jupyter)
            print("\n" + str(self.board) + "\n")

        # Show game status
        if self.verbose:
            move_num = len(self.move_history) // 2 + 1
            turn = "White" if self.board.turn == chess.WHITE else "Black"
            print(f"Move {move_num} - {turn} to move")

            if self.move_history:
                last_move = self.move_history[-1]
                print(f"Last move: {last_move}")

    def _human_move(self):
        """Get and execute human's move."""
        while True:
            try:
                # Get move input
                move_input = input("\n♟️  Your move: ").strip().lower()

                # Handle special commands
                if move_input in ['resign', 'quit']:
                    self.game_active = False
                    print("You resigned. AI wins!")
                    return

                if move_input == 'draw':
                    print("Draw offer not implemented. Continue playing or 'resign'.")
                    continue

                # Parse move
                move = chess.Move.from_uci(move_input)

                # Validate move
                if move not in self.board.legal_moves:
                    print("❌ Illegal move! Try again.")
                    print(f"Legal moves: {', '.join([m.uci() for m in list(self.board.legal_moves)[:10]])}...")
                    continue

                # Execute move
                self.board.push(move)
                self.move_history.append(move.uci())

                if self.verbose:
                    print(f"✅ Move played: {move.uci()}")

                break

            except ValueError as e:
                print(f"❌ Invalid move format: {e}")
                print("Use UCI notation (e.g., 'e2e4', 'e7e8q' for promotion)")
            except KeyboardInterrupt:
                print("\n🛑 Game interrupted")
                self.game_active = False
                return

    def _ai_move(self):
        """Get and execute AI's move."""
        if self.verbose:
            print("\n🤖 AI is thinking...")

        try:
            # Get board state
            from prometheus.environments.chess import ChessEnvironment
            env = ChessEnvironment()
            env.board = self.board.copy()
            state = env.get_state()

            # Get AI move
            move = self.agent.get_move(state, self.board, temperature=0.1)

            # Get position evaluation if agent supports it
            if hasattr(self.agent, 'evaluate'):
                eval_score = self.agent.evaluate(state)
                self.position_evaluations.append(eval_score)

                if self.verbose:
                    print(f"   Position evaluation: {eval_score:.3f}")

            # Execute move
            self.board.push(move)
            self.move_history.append(move.uci())

            if self.verbose:
                print(f"✅ AI plays: {move.uci()}")

            # Show move suggestions if enabled
            if self.show_suggestions and hasattr(self.agent, 'predict'):
                self._show_ai_thinking(state)

        except Exception as e:
            print(f"❌ AI error: {e}")
            self.game_active = False

    def _show_ai_thinking(self, state: np.ndarray, top_k: int = 3):
        """Show AI's top move candidates."""
        try:
            # Get policy prediction
            policy, value = self.agent.predict(state)

            # Get legal moves
            legal_indices = []
            legal_moves = []
            from prometheus.environments.chess import ChessMoveEncoder
            encoder = ChessMoveEncoder()

            for move in self.board.legal_moves:
                idx = encoder.move_to_index(move)
                legal_indices.append(idx)
                legal_moves.append(move)

            # Get top-k legal moves
            legal_probs = policy[legal_indices]
            top_k_indices = np.argsort(legal_probs)[-top_k:][::-1]

            print("\n   💭 AI's top considerations:")
            for rank, idx in enumerate(top_k_indices, 1):
                move = legal_moves[idx]
                prob = legal_probs[idx]
                print(f"      {rank}. {move.uci()} ({prob:.1%})")

        except Exception:
            pass  # Skip probability display if numpy ops fail (e.g., shape mismatch)

    def _display_result(self):
        """Display game result."""
        print("\n" + "=" * 70)
        print("🏁 GAME OVER")
        print("=" * 70)

        if not self.game_active:
            print("Game ended by user")
            return

        result = self.board.result()

        if result == "1-0":
            winner = "White wins"
        elif result == "0-1":
            winner = "Black wins"
        else:
            winner = "Draw"

        print(f"Result: {result} - {winner}")

        # Determine if human won
        if result == "1-0" and self.human_color == chess.WHITE:
            print("🎉 Congratulations! You won!")
        elif result == "0-1" and self.human_color == chess.BLACK:
            print("🎉 Congratulations! You won!")
        elif result == "1/2-1/2":
            print("🤝 Draw!")
        else:
            print("💻 AI wins!")

        # Game statistics
        print(f"\nTotal moves: {len(self.move_history)}")

        if self.position_evaluations:
            avg_eval = np.mean(self.position_evaluations)
            print(f"Average position evaluation: {avg_eval:.3f}")

        print("=" * 70)

    def get_game_pgn(self) -> str:
        """
        Get game in PGN format.

        Returns:
            Game in Portable Game Notation
        """
        game = chess.pgn.Game()

        # Set headers
        game.headers["Event"] = "Human vs Prometheus"
        game.headers["White"] = "Human" if self.human_color == chess.WHITE else "Prometheus"
        game.headers["Black"] = "Prometheus" if self.human_color == chess.WHITE else "Human"
        game.headers["Result"] = self.board.result() if self.board.is_game_over() else "*"

        # Add moves
        node = game
        board = chess.Board()
        for move_uci in self.move_history:
            move = chess.Move.from_uci(move_uci)
            node = node.add_variation(move)
            board.push(move)

        return str(game)

    def save_game(self, filepath: str):
        """
        Save game to PGN file.

        Args:
            filepath: Path to save PGN file
        """
        with open(filepath, 'w') as f:
            f.write(self.get_game_pgn())

        print(f"✅ Game saved to: {filepath}")


def quick_play(agent: Any, human_plays_white: bool = True):
    """
    Quick start interactive chess game.

    Args:
        agent: Chess agent
        human_plays_white: Human color choice

    Example:
        >>> from prometheus.interactive.chess_play import quick_play
        >>> quick_play(my_agent)
    """
    game = ChessInteractiveGame(
        agent=agent,
        human_plays_white=human_plays_white,
        show_suggestions=True
    )
    game.play()
