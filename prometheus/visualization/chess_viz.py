"""
Prometheus Chess Visualization

Interactive visualization tools for chess games and agent analysis:
- Board rendering with python-chess SVG
- Game replay with move-by-move animation
- Side-by-side agent comparisons
- Position evaluation heatmaps
- Move probability overlays
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation
from IPython.display import display, SVG, HTML, clear_output
import chess
import chess.svg
from typing import List, Dict, Optional, Tuple, Any
import time


class ChessBoardVisualizer:
    """
    Visualizes chess boards and games using python-chess SVG rendering.

    Provides interactive visualization for Jupyter/Colab notebooks.
    """

    @staticmethod
    def render_board(
        board: chess.Board,
        size: int = 400,
        orientation: chess.Color = chess.WHITE,
        arrows: Optional[List[chess.svg.Arrow]] = None,
        squares: Optional[List[int]] = None
    ) -> SVG:
        """
        Render chess board as SVG.

        Args:
            board: python-chess Board object
            size: Board size in pixels
            orientation: Board orientation (WHITE or BLACK)
            arrows: List of arrows to draw
            squares: List of squares to highlight

        Returns:
            IPython SVG display object
        """
        svg_str = chess.svg.board(
            board,
            size=size,
            orientation=orientation,
            arrows=arrows or [],
            squares=squares or [],
        )
        return SVG(svg_str)

    @staticmethod
    def render_position(
        fen: str,
        size: int = 400,
        title: str = ""
    ) -> SVG:
        """
        Render position from FEN string.

        Args:
            fen: FEN string
            size: Board size
            title: Optional title

        Returns:
            SVG object
        """
        board = chess.Board(fen)
        if title:
            print(f"\n{title}")
        return ChessBoardVisualizer.render_board(board, size=size)

    @staticmethod
    def show_move(
        board: chess.Board,
        move: chess.Move,
        size: int = 400
    ) -> SVG:
        """
        Show board with move highlighted.

        Args:
            board: Board state
            move: Move to highlight
            size: Board size

        Returns:
            SVG object
        """
        arrow = chess.svg.Arrow(move.from_square, move.to_square, color="#0000ccaa")
        return ChessBoardVisualizer.render_board(
            board,
            size=size,
            arrows=[arrow]
        )


class GameReplayer:
    """
    Replay chess games with move-by-move visualization.
    """

    def __init__(self, board: Optional[chess.Board] = None):
        """
        Initialize game replayer.

        Args:
            board: Starting board position (default: standard position)
        """
        self.board = board if board else chess.Board()
        self.move_history = []

    def replay_game(
        self,
        moves: List[chess.Move],
        delay: float = 1.0,
        size: int = 400,
        show_evaluation: bool = False,
        evaluator: Optional[Any] = None
    ):
        """
        Replay game move by move.

        Args:
            moves: List of moves to replay
            delay: Delay between moves in seconds
            size: Board size
            show_evaluation: Show position evaluation
            evaluator: Agent to evaluate positions
        """
        self.board.reset()

        for i, move in enumerate(moves):
            clear_output(wait=True)

            # Show current position
            move_num = (i // 2) + 1
            player = "White" if i % 2 == 0 else "Black"

            print(f"Move {move_num} - {player}: {move.uci()}")

            # Show evaluation if requested
            if show_evaluation and evaluator:
                eval_score = evaluator.evaluate_position(self.board)
                print(f"Position evaluation: {eval_score:+.3f}")

            # Render board with move arrow
            arrow = chess.svg.Arrow(move.from_square, move.to_square, color="#0000ccaa")
            svg = chess.svg.board(self.board, size=size, arrows=[arrow])
            display(SVG(svg))

            # Execute move
            self.board.push(move)

            # Delay
            if i < len(moves) - 1:
                time.sleep(delay)

        # Show final position
        clear_output(wait=True)
        print(f"\n🏁 Game Over: {self.board.result()}")
        svg = chess.svg.board(self.board, size=size)
        display(SVG(svg))

    def show_game_summary(
        self,
        moves: List[chess.Move],
        result: str,
        white_name: str = "White",
        black_name: str = "Black"
    ):
        """
        Show game summary with key positions.

        Args:
            moves: Move list
            result: Game result
            white_name: White player name
            black_name: Black player name
        """
        print(f"\n♟️  {white_name} vs {black_name}")
        print(f"Result: {result}")
        print(f"Moves: {len(moves)}")

        # Show opening, middlegame, endgame
        positions = [0, len(moves) // 3, 2 * len(moves) // 3, len(moves) - 1]
        labels = ["Opening", "Middlegame", "Late Middlegame", "Final Position"]

        board = chess.Board()
        for i, (pos, label) in enumerate(zip(positions, labels)):
            for move in moves[:pos+1]:
                if board.is_legal(move):
                    board.push(move)

            print(f"\n{label} (Move {pos+1}):")
            svg = chess.svg.board(board, size=300)
            display(SVG(svg))


class SideBySideComparison:
    """
    Compare two agents playing side-by-side.
    """

    @staticmethod
    def compare_games(
        game1: Dict[str, Any],
        game2: Dict[str, Any],
        agent1_name: str = "Agent 1",
        agent2_name: str = "Agent 2",
        size: int = 350
    ):
        """
        Show two games side-by-side.

        Args:
            game1: First game dict with 'moves' and 'result'
            game2: Second game dict with 'moves' and 'result'
            agent1_name: Name of first agent
            agent2_name: Name of second agent
            size: Board size
        """
        moves1 = game1['moves']
        moves2 = game2['moves']

        max_moves = max(len(moves1), len(moves2))

        board1 = chess.Board()
        board2 = chess.Board()

        print(f"🔵 {agent1_name} vs 🟢 {agent2_name}\n")

        for i in range(max_moves):
            clear_output(wait=True)

            print(f"Move {i+1}")
            print("="*70)

            # Create HTML for side-by-side display
            html_parts = ['<div style="display: flex; justify-content: space-around;">']

            # Game 1
            if i < len(moves1):
                board1.push(moves1[i])
            svg1 = chess.svg.board(board1, size=size)
            html_parts.append(f'<div><h3>{agent1_name}</h3>{svg1}</div>')

            # Game 2
            if i < len(moves2):
                board2.push(moves2[i])
            svg2 = chess.svg.board(board2, size=size)
            html_parts.append(f'<div><h3>{agent2_name}</h3>{svg2}</div>')

            html_parts.append('</div>')

            display(HTML(''.join(html_parts)))

            time.sleep(1.0)

        # Final results
        clear_output(wait=True)
        print(f"\n🏁 Final Results:")
        print(f"   {agent1_name}: {game1['result']}")
        print(f"   {agent2_name}: {game2['result']}")


class PositionHeatmap:
    """
    Visualize position evaluations as heatmaps.
    """

    @staticmethod
    def create_evaluation_heatmap(
        board: chess.Board,
        agent: Any,
        size: int = 8
    ) -> np.ndarray:
        """
        Create heatmap of piece-square values.

        Args:
            board: Current board state
            agent: Agent to evaluate positions
            size: Board size (8x8)

        Returns:
            8x8 numpy array of evaluations
        """
        heatmap = np.zeros((8, 8))

        # Evaluate importance of each square
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                # Simple heuristic: piece value
                values = {
                    chess.PAWN: 1,
                    chess.KNIGHT: 3,
                    chess.BISHOP: 3,
                    chess.ROOK: 5,
                    chess.QUEEN: 9,
                    chess.KING: 100
                }
                rank = chess.square_rank(square)
                file = chess.square_file(square)
                value = values[piece.piece_type]
                heatmap[rank, file] = value if piece.color == chess.WHITE else -value

        return heatmap

    @staticmethod
    def plot_heatmap(
        heatmap: np.ndarray,
        title: str = "Position Evaluation",
        cmap: str = "RdYlGn"
    ):
        """
        Plot evaluation heatmap.

        Args:
            heatmap: 8x8 evaluation array
            title: Plot title
            cmap: Colormap
        """
        fig, ax = plt.subplots(figsize=(8, 8))

        im = ax.imshow(heatmap, cmap=cmap, aspect='equal', vmin=-10, vmax=10)

        # Add gridlines
        ax.set_xticks(np.arange(8))
        ax.set_yticks(np.arange(8))
        ax.set_xticklabels(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'])
        ax.set_yticklabels(['1', '2', '3', '4', '5', '6', '7', '8'])

        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.grid(which='both', color='black', linewidth=2)

        # Colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Evaluation (White positive)', fontsize=12)

        plt.tight_layout()
        plt.show()


class MoveProbabilityOverlay:
    """
    Overlay move probabilities on chess board.
    """

    @staticmethod
    def visualize_policy(
        board: chess.Board,
        policy: np.ndarray,
        top_k: int = 5,
        size: int = 400
    ):
        """
        Visualize top-k moves from policy.

        Args:
            board: Current board state
            policy: 4096-dim policy array
            top_k: Number of top moves to show
            size: Board size
        """
        from prometheus.environments.chess import ChessMoveEncoder

        encoder = ChessMoveEncoder()

        # Get legal moves and their probabilities
        legal_moves = list(board.legal_moves)
        move_probs = []

        for move in legal_moves:
            idx = encoder.move_to_index(move)
            prob = policy[idx]
            move_probs.append((move, prob))

        # Sort by probability
        move_probs.sort(key=lambda x: x[1], reverse=True)

        # Show top-k
        print(f"\n🎯 Top {top_k} Moves:")
        arrows = []

        for i, (move, prob) in enumerate(move_probs[:top_k]):
            print(f"   {i+1}. {move.uci()}: {prob*100:.2f}%")

            # Color by rank
            if i == 0:
                color = "#00cc00aa"  # Green for best
            elif i == 1:
                color = "#0000ccaa"  # Blue for second
            else:
                color = "#ccccccaa"  # Gray for others

            arrows.append(chess.svg.Arrow(move.from_square, move.to_square, color=color))

        # Render board with arrows
        svg = chess.svg.board(board, size=size, arrows=arrows)
        display(SVG(svg))


def create_learning_animation(
    static_games: List[Dict],
    prometheus_games: List[Dict],
    iterations: List[int],
    filename: str = "learning_progress.gif"
):
    """
    Create animated GIF showing learning progress.

    Args:
        static_games: List of Static agent games
        prometheus_games: List of Prometheus agent games
        iterations: Iteration numbers
        filename: Output filename
    """
    # This would create an animated comparison
    # Placeholder for now - full implementation would use matplotlib.animation
    print(f"Creating learning animation: {filename}")
    print("(Full implementation requires matplotlib.animation.FuncAnimation)")


def visualize_game_comparison(
    game_data: Dict[str, Any],
    agent1_name: str = "Static",
    agent2_name: str = "Prometheus"
):
    """
    Create comprehensive game comparison visualization.

    Args:
        game_data: Dictionary with game information
        agent1_name: First agent name
        agent2_name: Second agent name
    """
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    # Game length comparison
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.bar([agent1_name, agent2_name],
            [game_data.get('static_moves', 0), game_data.get('prometheus_moves', 0)],
            color=['blue', 'green'], alpha=0.7)
    ax1.set_ylabel('Number of Moves', fontsize=12, fontweight='bold')
    ax1.set_title('Game Length', fontsize=14, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)

    # Win rate
    ax2 = fig.add_subplot(gs[0, 1])
    win_rates = [game_data.get('static_winrate', 0), game_data.get('prometheus_winrate', 0)]
    ax2.bar([agent1_name, agent2_name], win_rates, color=['blue', 'green'], alpha=0.7)
    ax2.set_ylabel('Win Rate (%)', fontsize=12, fontweight='bold')
    ax2.set_title('Performance vs Random', fontsize=14, fontweight='bold')
    ax2.set_ylim([0, 100])
    ax2.grid(axis='y', alpha=0.3)

    # Add more subplots as needed...

    plt.tight_layout()
    plt.show()
