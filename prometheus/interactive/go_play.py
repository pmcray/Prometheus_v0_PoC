"""
Interactive Go Play

Human vs AI Go gameplay with visual board and move input.

Features:
- Visual ASCII board rendering
- Coordinate move input (e.g., "D4" or "pass")
- Legal move validation
- Territory scoring display
- Game history tracking

Usage:
    >>> from prometheus.interactive import GoInteractiveGame
    >>> game = GoInteractiveGame(agent=prometheus_go_agent, board_size=19)
    >>> game.play()  # Start interactive session
"""

import numpy as np
from typing import Optional, Any, List, Tuple
from IPython.display import display, HTML, clear_output


class GoInteractiveGame:
    """
    Interactive Go game between human and Prometheus agent.

    Features:
    - Visual board display (ASCII art)
    - Coordinate move input (e.g., "D4", "Q16")
    - Legal move validation
    - AI move display
    - Territory scoring
    - Game history

    Attributes:
        agent: Prometheus Go agent
        board_size: Board size (9, 13, or 19)
        human_color: Human player's color (BLACK=1 or WHITE=-1)
        board: Current Go board
        move_history: List of moves played
        game_active: Whether game is in progress
    """

    def __init__(
        self,
        agent: Any,
        board_size: int = 19,
        komi: float = 7.5,
        human_plays_black: bool = True,
        verbose: bool = True
    ):
        """
        Initialize interactive Go game.

        Args:
            agent: Go agent with get_move() method
            board_size: Board size (9, 13, or 19)
            komi: Komi compensation for white
            human_plays_black: If True, human plays black; else white
            verbose: Print move commentary
        """
        from prometheus.environments.go import GoBoard

        self.agent = agent
        self.board_size = board_size
        self.komi = komi
        self.human_color = 1 if human_plays_black else -1  # BLACK=1, WHITE=-1
        self.verbose = verbose

        # Game state
        self.board = GoBoard(size=board_size, komi=komi)
        self.move_history = []
        self.pass_count = 0
        self.game_active = True

        # Current player (black goes first)
        self.current_player = 1

    def play(self):
        """
        Start interactive game.

        This method provides a turn-based interface:
        - Human enters moves via coordinates
        - AI responds with its best move
        - Board is displayed after each move
        - Game continues until two consecutive passes
        """
        print("=" * 70)
        print(f"🎴 INTERACTIVE GO: HUMAN VS PROMETHEUS ({self.board_size}×{self.board_size})")
        print("=" * 70)
        print(f"You are playing {'BLACK (●)' if self.human_color == 1 else 'WHITE (○)'}")
        print(f"Komi: {self.komi}")
        print("Enter moves as coordinates (e.g., 'D4', 'Q16') or 'pass'")
        print("Special commands: 'resign', 'quit', 'score'")
        print("=" * 70)

        while self.game_active:
            # Display board
            self.display_board()

            # Check whose turn
            if self.current_player == self.human_color:
                # Human's turn
                self._human_move()
            else:
                # AI's turn
                self._ai_move()

            # Check if game ended (two consecutive passes)
            if self.pass_count >= 2:
                self.game_active = False

            # Switch player
            self.current_player *= -1

        # Game ended
        self._display_result()

    def display_board(self):
        """Display current board state."""
        print("\n" + self._board_to_string())

        if self.verbose:
            move_num = len(self.move_history)
            turn = "Black (●)" if self.current_player == 1 else "White (○)"
            print(f"\nMove {move_num + 1} - {turn} to move")

            if self.move_history:
                last_move = self.move_history[-1]
                if last_move == ('pass',):
                    print(f"Last move: PASS")
                else:
                    row, col = last_move
                    coord = self._coords_to_string(row, col)
                    print(f"Last move: {coord}")

    def _board_to_string(self) -> str:
        """Convert board to ASCII string."""
        size = self.board_size

        # Column labels
        col_labels = "   " + " ".join(self._get_column_labels()[:size])
        lines = [col_labels]
        lines.append("  ┌" + "─" * (size * 2 - 1) + "┐")

        for row in range(size):
            # Row label
            row_label = f"{row + 1:2d}│"

            # Stones
            row_str = ""
            for col in range(size):
                stone = self.board.board[row, col]

                if stone == 1:  # Black
                    row_str += "●"
                elif stone == -1:  # White
                    row_str += "○"
                else:  # Empty
                    # Determine if intersection is special
                    is_star_point = self._is_star_point(row, col)
                    row_str += "+" if is_star_point else "·"

                if col < size - 1:
                    row_str += " "

            lines.append(row_label + row_str + "│" + f"{row + 1:2d}")

        lines.append("  └" + "─" * (size * 2 - 1) + "┘")
        lines.append(col_labels)

        return "\n".join(lines)

    def _get_column_labels(self) -> List[str]:
        """Get column labels (A-Z, excluding I)."""
        labels = []
        for i in range(26):
            letter = chr(ord('A') + i)
            if letter != 'I':  # Skip I (looks like 1)
                labels.append(letter)
        return labels

    def _is_star_point(self, row: int, col: int) -> bool:
        """Check if position is a star point (hoshi)."""
        size = self.board_size

        if size == 19:
            star_points = [(3, 3), (3, 9), (3, 15),
                           (9, 3), (9, 9), (9, 15),
                           (15, 3), (15, 9), (15, 15)]
        elif size == 13:
            star_points = [(3, 3), (3, 9), (6, 6), (9, 3), (9, 9)]
        elif size == 9:
            star_points = [(2, 2), (2, 6), (4, 4), (6, 2), (6, 6)]
        else:
            return False

        return (row, col) in star_points

    def _coords_to_string(self, row: int, col: int) -> str:
        """Convert (row, col) to string like 'D4'."""
        col_labels = self._get_column_labels()
        return f"{col_labels[col]}{row + 1}"

    def _string_to_coords(self, move_str: str) -> Tuple[int, int]:
        """Convert string like 'D4' to (row, col)."""
        move_str = move_str.upper().strip()

        if move_str == "PASS":
            return ('pass',)

        # Parse column letter
        col_letter = move_str[0]
        col_labels = self._get_column_labels()

        if col_letter not in col_labels:
            raise ValueError(f"Invalid column: {col_letter}")

        col = col_labels.index(col_letter)

        # Parse row number
        row_str = move_str[1:]
        row = int(row_str) - 1  # Convert to 0-indexed

        if row < 0 or row >= self.board_size:
            raise ValueError(f"Invalid row: {row + 1}")

        return (row, col)

    def _human_move(self):
        """Get and execute human's move."""
        while True:
            try:
                # Get move input
                move_input = input("\n🎴 Your move (e.g., 'D4' or 'pass'): ").strip()

                # Handle special commands
                if move_input.lower() in ['resign', 'quit']:
                    self.game_active = False
                    print("You resigned. AI wins!")
                    return

                if move_input.lower() == 'score':
                    self._show_score()
                    continue

                # Parse move
                if move_input.lower() == 'pass':
                    move = ('pass',)
                else:
                    move = self._string_to_coords(move_input)

                # Validate move
                if move != ('pass',):
                    row, col = move
                    if not self.board.is_legal_move(row, col, self.current_player):
                        print("❌ Illegal move! Try again.")
                        continue

                # Execute move
                if move == ('pass',):
                    self.pass_count += 1
                    print("✅ Pass")
                else:
                    row, col = move
                    success = self.board.play_move(row, col, self.current_player)
                    if not success:
                        print("❌ Move failed! Try again.")
                        continue
                    self.pass_count = 0
                    print(f"✅ Move played: {self._coords_to_string(row, col)}")

                self.move_history.append(move)
                break

            except ValueError as e:
                print(f"❌ Invalid move format: {e}")
                print("Use format like 'D4', 'Q16', or 'pass'")
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
            from prometheus.environments.go import GoEnvironment
            env = GoEnvironment(board_size=self.board_size, komi=self.komi)
            env.board = self.board
            env.current_player = self.current_player
            state = env.get_state()

            # Get legal moves
            legal_moves = env.get_legal_moves()

            # Get AI move
            move = self.agent.get_move(state, legal_moves, temperature=0.1)

            # Execute move
            if move == ('pass',):
                self.pass_count += 1
                if self.verbose:
                    print("✅ AI plays: PASS")
            else:
                row, col = move
                success = self.board.play_move(row, col, self.current_player)
                if not success:
                    print("❌ AI move failed!")
                    self.game_active = False
                    return
                self.pass_count = 0
                if self.verbose:
                    print(f"✅ AI plays: {self._coords_to_string(row, col)}")

            self.move_history.append(move)

        except Exception as e:
            print(f"❌ AI error: {e}")
            import traceback
            traceback.print_exc()
            self.game_active = False

    def _show_score(self):
        """Show current territory score."""
        score_dict = self.board.score()
        black_score = score_dict['black_score']
        white_score = score_dict['white_score']

        print("\n📊 Current Score:")
        print(f"   Black (●): {black_score:.1f}")
        print(f"   White (○): {white_score:.1f} (includes {self.komi} komi)")
        print(f"   Difference: {abs(black_score - white_score):.1f} for {'Black' if black_score > white_score else 'White'}")

    def _display_result(self):
        """Display game result."""
        print("\n" + "=" * 70)
        print("🏁 GAME OVER")
        print("=" * 70)

        if not self.game_active and len(self.move_history) > 0:
            last_move = self.move_history[-1]
            if last_move != ('pass',):
                print("Game ended by user resignation")
                return

        # Calculate final score
        score_dict = self.board.score()
        black_score = score_dict['black_score']
        white_score = score_dict['white_score']
        score_diff = black_score - white_score

        print(f"Final Score:")
        print(f"   Black (●): {black_score:.1f}")
        print(f"   White (○): {white_score:.1f}")
        print(f"   Captures - Black: {score_dict['black_captures']}, White: {score_dict['white_captures']}")

        if score_diff > 0:
            winner = f"Black wins by {score_diff:.1f} points"
        elif score_diff < 0:
            winner = f"White wins by {abs(score_diff):.1f} points"
        else:
            winner = "Draw!"

        print(f"\nResult: {winner}")

        # Determine if human won
        if score_diff > 0 and self.human_color == 1:
            print("🎉 Congratulations! You won!")
        elif score_diff < 0 and self.human_color == -1:
            print("🎉 Congratulations! You won!")
        elif score_diff == 0:
            print("🤝 Draw!")
        else:
            print("💻 AI wins!")

        print(f"\nTotal moves: {len(self.move_history)}")
        print("=" * 70)

    def save_game(self, filepath: str):
        """
        Save game to SGF (Smart Game Format) file.

        Args:
            filepath: Path to save SGF file
        """
        sgf = self._generate_sgf()

        with open(filepath, 'w') as f:
            f.write(sgf)

        print(f"✅ Game saved to: {filepath}")

    def _generate_sgf(self) -> str:
        """Generate SGF representation of game."""
        # SGF header
        sgf_lines = [
            "(;",
            "FF[4]",  # File format
            f"SZ[{self.board_size}]",  # Board size
            f"KM[{self.komi}]",  # Komi
            "PB[Human]" if self.human_color == 1 else "PW[Human]",
            "PW[Prometheus]" if self.human_color == 1 else "PB[Prometheus]",
        ]

        # Add moves
        for idx, move in enumerate(self.move_history):
            color = "B" if idx % 2 == 0 else "W"

            if move == ('pass',):
                sgf_lines.append(f";{color}[]")
            else:
                row, col = move
                # SGF uses letters for coordinates
                col_letter = chr(ord('a') + col)
                row_letter = chr(ord('a') + row)
                sgf_lines.append(f";{color}[{col_letter}{row_letter}]")

        sgf_lines.append(")")

        return "\n".join(sgf_lines)


def quick_play(agent: Any, board_size: int = 19, human_plays_black: bool = True):
    """
    Quick start interactive Go game.

    Args:
        agent: Go agent
        board_size: Board size (9, 13, or 19)
        human_plays_black: Human color choice

    Example:
        >>> from prometheus.interactive.go_play import quick_play
        >>> quick_play(my_agent, board_size=9)
    """
    game = GoInteractiveGame(
        agent=agent,
        board_size=board_size,
        human_plays_black=human_plays_black
    )
    game.play()
