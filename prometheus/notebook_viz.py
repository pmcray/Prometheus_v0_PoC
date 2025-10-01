"""
Rich Jupyter Notebook Visualizations for Project Prometheus

This module provides beautiful, interactive visualizations for:
- Game boards (Connect4, Othello, Draughts) with full color
- Agent brain maps with cell assemblies
- Gene pool evolution trees
- Fitness landscapes
- Causal agentic mesh networks
- Performance metrics and statistics

Designed specifically for Jupyter notebooks with matplotlib, plotly, and networkx.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.collections import PatchCollection
import matplotlib.animation as animation
from IPython.display import HTML, display, clear_output
import networkx as nx
from typing import List, Dict, Any, Optional, Tuple
import io
import base64


# Color schemes
COLORS = {
    'player1': '#E74C3C',  # Red
    'player2': '#3498DB',  # Blue
    'empty': '#ECF0F1',    # Light gray
    'board_dark': '#34495E',  # Dark gray
    'board_light': '#95A5A6', # Medium gray
    'win': '#2ECC71',      # Green
    'active': '#F39C12',   # Orange
    'thinking': '#9B59B6', # Purple
    'gene_pool': '#1ABC9C',  # Turquoise
    'fitness': '#E67E22',  # Dark orange
}


class GameBoardViz:
    """
    Beautiful game board visualizations with full color support
    """

    @staticmethod
    def visualize_connect4(board: List[List[int]], last_move: Optional[Tuple[int, int]] = None,
                          title: str = "Connect 4", figsize=(10, 8)):
        """
        Visualize Connect 4 board with colors

        Args:
            board: 6x7 board matrix
            last_move: (row, col) of last move to highlight
            title: Plot title
            figsize: Figure size
        """
        fig, ax = plt.subplots(figsize=figsize)

        rows, cols = len(board), len(board[0])

        # Draw board background
        board_rect = patches.Rectangle((0, 0), cols, rows,
                                      linewidth=2, edgecolor='black',
                                      facecolor=COLORS['board_dark'])
        ax.add_patch(board_rect)

        # Draw pieces
        for row in range(rows):
            for col in range(cols):
                # Draw slot
                circle = patches.Circle((col + 0.5, rows - row - 0.5), 0.4,
                                       facecolor=COLORS['empty'],
                                       edgecolor='black', linewidth=2)
                ax.add_patch(circle)

                # Draw piece if present
                piece = board[row][col]
                if piece != 0:
                    color = COLORS['player1'] if piece == 1 else COLORS['player2']

                    # Highlight last move
                    if last_move and last_move == (row, col):
                        edgecolor = COLORS['win']
                        linewidth = 4
                    else:
                        edgecolor = 'black'
                        linewidth = 2

                    piece_circle = patches.Circle((col + 0.5, rows - row - 0.5), 0.35,
                                                 facecolor=color,
                                                 edgecolor=edgecolor,
                                                 linewidth=linewidth)
                    ax.add_patch(piece_circle)

        # Add column numbers
        for col in range(cols):
            ax.text(col + 0.5, -0.5, str(col),
                   ha='center', va='center', fontsize=14, fontweight='bold')

        ax.set_xlim(0, cols)
        ax.set_ylim(-0.8, rows)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(title, fontsize=18, fontweight='bold', pad=20)

        plt.tight_layout()
        return fig

    @staticmethod
    def visualize_othello(board: List[List[int]], valid_moves: List[Tuple[int, int]] = None,
                         last_move: Optional[Tuple[int, int]] = None,
                         title: str = "Othello", figsize=(10, 10)):
        """
        Visualize Othello/Reversi board with colors

        Args:
            board: 8x8 board matrix
            valid_moves: List of (row, col) valid move positions
            last_move: (row, col) of last move to highlight
            title: Plot title
            figsize: Figure size
        """
        fig, ax = plt.subplots(figsize=figsize)

        size = len(board)

        # Draw board
        for row in range(size):
            for col in range(size):
                rect = patches.Rectangle((col, row), 1, 1,
                                        facecolor=COLORS['board_light'],
                                        edgecolor='black', linewidth=1)
                ax.add_patch(rect)

                # Draw piece
                piece = board[row][col]
                if piece != 0:
                    color = COLORS['player1'] if piece == 1 else COLORS['player2']

                    # Highlight last move
                    if last_move and last_move == (row, col):
                        edgecolor = COLORS['win']
                        linewidth = 4
                    else:
                        edgecolor = 'white'
                        linewidth = 2

                    circle = patches.Circle((col + 0.5, row + 0.5), 0.4,
                                           facecolor=color,
                                           edgecolor=edgecolor,
                                           linewidth=linewidth)
                    ax.add_patch(circle)

                # Show valid moves
                elif valid_moves and (row, col) in valid_moves:
                    circle = patches.Circle((col + 0.5, row + 0.5), 0.15,
                                           facecolor=COLORS['thinking'],
                                           alpha=0.5)
                    ax.add_patch(circle)

        # Add coordinates
        for i in range(size):
            ax.text(-0.5, i + 0.5, str(i), ha='center', va='center',
                   fontsize=12, fontweight='bold')
            ax.text(i + 0.5, -0.5, str(i), ha='center', va='center',
                   fontsize=12, fontweight='bold')

        # Score
        p1_count = sum(row.count(1) for row in board)
        p2_count = sum(row.count(-1) for row in board)

        ax.text(size/2, size + 0.5,
               f"● {p1_count}  -  {p2_count} ○",
               ha='center', va='center', fontsize=16, fontweight='bold')

        ax.set_xlim(-0.8, size + 0.2)
        ax.set_ylim(-0.8, size + 0.8)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(title, fontsize=18, fontweight='bold', pad=20)

        plt.tight_layout()
        return fig

    @staticmethod
    def visualize_draughts(board: List[List[int]], valid_moves: List[Tuple] = None,
                          last_move: Optional[Tuple] = None,
                          title: str = "Draughts", figsize=(10, 10)):
        """
        Visualize Draughts/Checkers board with colors

        Args:
            board: 8x8 board matrix
            valid_moves: List of ((from_row, from_col), (to_row, to_col))
            last_move: ((from_row, from_col), (to_row, to_col)) of last move
            title: Plot title
            figsize: Figure size
        """
        fig, ax = plt.subplots(figsize=figsize)

        size = len(board)

        # Draw checkerboard
        for row in range(size):
            for col in range(size):
                color = COLORS['board_dark'] if (row + col) % 2 == 0 else COLORS['board_light']
                rect = patches.Rectangle((col, row), 1, 1,
                                        facecolor=color,
                                        edgecolor='black', linewidth=0.5)
                ax.add_patch(rect)

                # Draw piece
                piece = board[row][col]
                if piece != 0:
                    # Determine color
                    if piece == 1 or piece == 2:
                        color = COLORS['player1']
                    else:
                        color = COLORS['player2']

                    # Highlight if part of last move
                    if last_move and ((row, col) == last_move[0] or (row, col) == last_move[1]):
                        edgecolor = COLORS['win']
                        linewidth = 4
                    else:
                        edgecolor = 'white'
                        linewidth = 2

                    # Draw piece
                    circle = patches.Circle((col + 0.5, row + 0.5), 0.35,
                                           facecolor=color,
                                           edgecolor=edgecolor,
                                           linewidth=linewidth)
                    ax.add_patch(circle)

                    # Draw crown for kings
                    if abs(piece) == 2:
                        ax.text(col + 0.5, row + 0.5, '♔',
                               ha='center', va='center',
                               fontsize=20, color='gold', fontweight='bold')

        # Show valid move origins
        if valid_moves:
            origins = set(move[0] for move in valid_moves)
            for row, col in origins:
                rect = patches.Rectangle((col, row), 1, 1,
                                        facecolor='none',
                                        edgecolor=COLORS['thinking'],
                                        linewidth=3, alpha=0.6)
                ax.add_patch(rect)

        # Add coordinates
        for i in range(size):
            ax.text(-0.5, i + 0.5, str(i), ha='center', va='center',
                   fontsize=12, fontweight='bold')
            ax.text(i + 0.5, size + 0.3, str(i), ha='center', va='center',
                   fontsize=12, fontweight='bold')

        # Score
        p1_pieces = sum(1 for row in board for cell in row if cell > 0)
        p2_pieces = sum(1 for row in board for cell in row if cell < 0)

        ax.text(size/2, -0.5,
               f"● {p1_pieces}  -  {p2_pieces} ○",
               ha='center', va='center', fontsize=16, fontweight='bold')

        ax.set_xlim(-0.8, size)
        ax.set_ylim(-0.8, size + 0.5)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(title, fontsize=18, fontweight='bold', pad=20)

        plt.tight_layout()
        return fig


class AgentThinkingViz:
    """
    Visualize agent's thinking process and decision making
    """

    @staticmethod
    def show_thinking(agent_name: str, thinking_steps: List[str],
                     decision: str, figsize=(12, 6)):
        """
        Display agent's thinking process as a flowchart

        Args:
            agent_name: Name of the agent
            thinking_steps: List of thinking steps
            decision: Final decision
            figsize: Figure size
        """
        fig, ax = plt.subplots(figsize=figsize)

        y_pos = 0.9
        step_height = 0.15

        # Title
        ax.text(0.5, 0.95, f"🧠 {agent_name} Thinking Process",
               ha='center', va='top', fontsize=16, fontweight='bold',
               transform=ax.transAxes)

        # Draw thinking steps
        for i, step in enumerate(thinking_steps):
            # Step box
            rect = patches.FancyBboxPatch((0.1, y_pos - step_height/2), 0.8, step_height,
                                         boxstyle="round,pad=0.01",
                                         facecolor=COLORS['thinking'],
                                         edgecolor='black', linewidth=2,
                                         alpha=0.3, transform=ax.transAxes)
            ax.add_patch(rect)

            # Step text
            ax.text(0.5, y_pos, step,
                   ha='center', va='center', fontsize=11,
                   transform=ax.transAxes, wrap=True)

            # Arrow to next step
            if i < len(thinking_steps) - 1:
                ax.annotate('', xy=(0.5, y_pos - step_height*0.7),
                           xytext=(0.5, y_pos - step_height*0.3),
                           arrowprops=dict(arrowstyle='->', lw=2, color='black'),
                           transform=ax.transAxes)

            y_pos -= step_height + 0.05

        # Decision box
        rect = patches.FancyBboxPatch((0.1, 0.05), 0.8, 0.12,
                                     boxstyle="round,pad=0.01",
                                     facecolor=COLORS['win'],
                                     edgecolor='black', linewidth=3,
                                     alpha=0.5, transform=ax.transAxes)
        ax.add_patch(rect)

        ax.text(0.5, 0.11, f"✓ Decision: {decision}",
               ha='center', va='center', fontsize=14, fontweight='bold',
               transform=ax.transAxes)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        plt.tight_layout()
        return fig


class EvolutionViz:
    """
    Visualize gene pool evolution and fitness landscapes
    """

    @staticmethod
    def plot_fitness_evolution(generations: List[int],
                               best_fitness: List[float],
                               avg_fitness: List[float],
                               worst_fitness: List[float],
                               title: str = "Fitness Evolution",
                               figsize=(12, 6)):
        """
        Plot fitness over generations

        Args:
            generations: List of generation numbers
            best_fitness: Best fitness per generation
            avg_fitness: Average fitness per generation
            worst_fitness: Worst fitness per generation
            title: Plot title
            figsize: Figure size
        """
        fig, ax = plt.subplots(figsize=figsize)

        ax.plot(generations, best_fitness, 'o-', color=COLORS['win'],
               linewidth=3, markersize=8, label='Best', alpha=0.8)
        ax.plot(generations, avg_fitness, 's-', color=COLORS['fitness'],
               linewidth=2, markersize=6, label='Average', alpha=0.7)
        ax.plot(generations, worst_fitness, '^-', color=COLORS['player2'],
               linewidth=2, markersize=6, label='Worst', alpha=0.6)

        # Fill between
        ax.fill_between(generations, worst_fitness, best_fitness,
                       alpha=0.2, color=COLORS['gene_pool'])

        ax.set_xlabel('Generation', fontsize=14, fontweight='bold')
        ax.set_ylabel('Fitness', fontsize=14, fontweight='bold')
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.legend(fontsize=12, loc='best')
        ax.grid(True, alpha=0.3, linestyle='--')

        # Highlight improvements
        for i in range(1, len(best_fitness)):
            if best_fitness[i] > best_fitness[i-1]:
                ax.axvline(generations[i], color=COLORS['win'],
                          alpha=0.2, linestyle='--', linewidth=2)

        plt.tight_layout()
        return fig

    @staticmethod
    def plot_gene_pool_tree(population_history: List[Dict],
                           generation: int,
                           title: str = "Gene Pool Evolution Tree",
                           figsize=(14, 10)):
        """
        Visualize gene pool as evolutionary tree

        Args:
            population_history: History of populations
            generation: Current generation to display
            title: Plot title
            figsize: Figure size
        """
        fig, ax = plt.subplots(figsize=figsize)

        # Create networkx graph
        G = nx.DiGraph()

        # Add nodes and edges from history
        pos = {}
        node_colors = []
        node_sizes = []

        for gen_idx, gen_data in enumerate(population_history[:generation+1]):
            for agent_idx, agent in enumerate(gen_data.get('agents', [])):
                node_id = f"G{gen_idx}A{agent_idx}"
                G.add_node(node_id)

                # Position: x=generation, y=agent index
                pos[node_id] = (gen_idx, agent_idx * 2)

                # Color by fitness
                fitness = agent.get('fitness', 0)
                if fitness > 0.7:
                    color = COLORS['win']
                elif fitness > 0.4:
                    color = COLORS['fitness']
                else:
                    color = COLORS['player2']
                node_colors.append(color)

                # Size by fitness
                node_sizes.append(300 + fitness * 700)

                # Add edges to parents
                for parent_id in agent.get('parents', []):
                    if parent_id in G:
                        G.add_edge(parent_id, node_id)

        # Draw graph
        nx.draw_networkx_nodes(G, pos, node_color=node_colors,
                              node_size=node_sizes, alpha=0.7, ax=ax)
        nx.draw_networkx_edges(G, pos, edge_color='gray',
                              arrows=True, alpha=0.4, ax=ax)

        # Labels for best agents
        labels = {}
        for node in G.nodes():
            gen_idx = int(node[1:].split('A')[0])
            if gen_idx == generation:
                labels[node] = node
        nx.draw_networkx_labels(G, pos, labels, font_size=8, ax=ax)

        ax.set_xlabel('Generation', fontsize=14, fontweight='bold')
        ax.set_ylabel('Agent Lineage', fontsize=14, fontweight='bold')
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.axis('on')
        ax.grid(True, alpha=0.3)

        # Legend
        legend_elements = [
            patches.Patch(facecolor=COLORS['win'], label='High Fitness (>0.7)'),
            patches.Patch(facecolor=COLORS['fitness'], label='Medium Fitness (0.4-0.7)'),
            patches.Patch(facecolor=COLORS['player2'], label='Low Fitness (<0.4)')
        ]
        ax.legend(handles=legend_elements, loc='upper left', fontsize=10)

        plt.tight_layout()
        return fig


def create_animated_game(game_history: List[Dict], game_type: str = "connect4"):
    """
    Create animated visualization of a game being played

    Args:
        game_history: List of game states
        game_type: Type of game

    Returns:
        HTML animation
    """
    # This would create an animated GIF or HTML5 video
    # Placeholder for now
    print("Animated game visualization - coming soon!")
    pass
