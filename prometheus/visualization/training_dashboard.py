"""
Training Dashboard for Go Agents

Provides real-time visualization of:
- Training metrics (loss, accuracy, ELO)
- Game statistics (win rate, move distribution)
- Evolution progress (generations, improvements)
- Performance comparisons

Usage:
    dashboard = TrainingDashboard()
    dashboard.update(metrics)
    dashboard.plot()
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque


class TrainingDashboard:
    """
    Real-time training visualization dashboard.

    Tracks and displays:
    - Training loss curves
    - Win rates over time
    - ELO ratings
    - Move distribution heatmaps
    - Generation evolution
    """

    def __init__(self, window_size: int = 100, figsize: Tuple[int, int] = (16, 10)):
        """
        Initialize training dashboard.

        Args:
            window_size: Number of recent data points to display
            figsize: Figure size (width, height)
        """
        self.window_size = window_size
        self.figsize = figsize

        # Metrics storage
        self.metrics = defaultdict(lambda: deque(maxlen=window_size))

        # Game statistics
        self.game_outcomes = defaultdict(int)  # wins, losses, draws
        self.move_heatmap = None

        # Figure and axes
        self.fig = None
        self.axes = {}

    def update(self, metrics: Dict):
        """
        Update dashboard with new metrics.

        Args:
            metrics: Dictionary of metric_name -> value
                Common keys:
                - 'policy_loss': Policy network loss
                - 'value_loss': Value network loss
                - 'total_loss': Combined loss
                - 'win_rate': Win rate (0-1)
                - 'elo': ELO rating
                - 'generation': Current generation
                - 'games_played': Total games
                - 'move_entropy': Move diversity
        """
        for key, value in metrics.items():
            self.metrics[key].append(value)

    def update_game_outcome(self, outcome: str):
        """
        Update game outcome statistics.

        Args:
            outcome: 'win', 'loss', or 'draw'
        """
        self.game_outcomes[outcome] += 1

    def update_move_heatmap(self, move: Tuple[int, int], board_size: int = 9):
        """
        Update move distribution heatmap.

        Args:
            move: (row, col) position
            board_size: Board size
        """
        if self.move_heatmap is None:
            self.move_heatmap = np.zeros((board_size, board_size))

        if isinstance(move, tuple) and len(move) == 2:
            row, col = move
            if 0 <= row < board_size and 0 <= col < board_size:
                self.move_heatmap[row, col] += 1

    def plot(self, save_path: Optional[str] = None):
        """
        Create comprehensive training dashboard.

        Args:
            save_path: Optional path to save figure
        """
        # Create figure with subplots
        self.fig = plt.figure(figsize=self.figsize)
        gs = GridSpec(3, 3, figure=self.fig, hspace=0.3, wspace=0.3)

        # 1. Loss curves (top left, spans 2 columns)
        ax_loss = self.fig.add_subplot(gs[0, :2])
        self._plot_loss_curves(ax_loss)

        # 2. Win rate (top right)
        ax_winrate = self.fig.add_subplot(gs[0, 2])
        self._plot_win_rate(ax_winrate)

        # 3. ELO rating (middle left)
        ax_elo = self.fig.add_subplot(gs[1, 0])
        self._plot_elo(ax_elo)

        # 4. Game outcomes pie chart (middle center)
        ax_outcomes = self.fig.add_subplot(gs[1, 1])
        self._plot_game_outcomes(ax_outcomes)

        # 5. Move heatmap (middle right)
        ax_heatmap = self.fig.add_subplot(gs[1, 2])
        self._plot_move_heatmap(ax_heatmap)

        # 6. Generation progress (bottom left)
        ax_generation = self.fig.add_subplot(gs[2, 0])
        self._plot_generation(ax_generation)

        # 7. Move entropy (bottom center)
        ax_entropy = self.fig.add_subplot(gs[2, 1])
        self._plot_move_entropy(ax_entropy)

        # 8. Summary statistics (bottom right)
        ax_summary = self.fig.add_subplot(gs[2, 2])
        self._plot_summary(ax_summary)

        # Overall title
        total_games = sum(self.game_outcomes.values())
        self.fig.suptitle(f'Go Agent Training Dashboard (Games: {total_games})',
                         fontsize=16, fontweight='bold')

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')

        plt.show()

    def _plot_loss_curves(self, ax):
        """Plot training loss curves."""
        ax.set_title('Training Loss', fontweight='bold')

        if 'policy_loss' in self.metrics and len(self.metrics['policy_loss']) > 0:
            steps = range(len(self.metrics['policy_loss']))
            ax.plot(steps, list(self.metrics['policy_loss']),
                   label='Policy Loss', linewidth=2, alpha=0.8)

        if 'value_loss' in self.metrics and len(self.metrics['value_loss']) > 0:
            steps = range(len(self.metrics['value_loss']))
            ax.plot(steps, list(self.metrics['value_loss']),
                   label='Value Loss', linewidth=2, alpha=0.8)

        if 'total_loss' in self.metrics and len(self.metrics['total_loss']) > 0:
            steps = range(len(self.metrics['total_loss']))
            ax.plot(steps, list(self.metrics['total_loss']),
                   label='Total Loss', linewidth=2, alpha=0.8, linestyle='--')

        ax.set_xlabel('Training Steps')
        ax.set_ylabel('Loss')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)

    def _plot_win_rate(self, ax):
        """Plot win rate over time."""
        ax.set_title('Win Rate', fontweight='bold')

        if 'win_rate' in self.metrics and len(self.metrics['win_rate']) > 0:
            win_rates = list(self.metrics['win_rate'])
            steps = range(len(win_rates))

            ax.plot(steps, win_rates, linewidth=2, color='green', alpha=0.8)
            ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, label='Random')

            # Fill area
            ax.fill_between(steps, win_rates, 0.5, alpha=0.3, color='green')

            ax.set_ylim(0, 1)
            ax.set_xlabel('Evaluation')
            ax.set_ylabel('Win Rate')
            ax.legend(loc='lower right')
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'No win rate data',
                   ha='center', va='center', transform=ax.transAxes)

    def _plot_elo(self, ax):
        """Plot ELO rating evolution."""
        ax.set_title('ELO Rating', fontweight='bold')

        if 'elo' in self.metrics and len(self.metrics['elo']) > 0:
            elo_ratings = list(self.metrics['elo'])
            steps = range(len(elo_ratings))

            ax.plot(steps, elo_ratings, linewidth=2, color='blue', alpha=0.8)
            ax.axhline(y=1200, color='gray', linestyle='--', alpha=0.5,
                      label='Intermediate')

            ax.set_xlabel('Evaluation')
            ax.set_ylabel('ELO Rating')
            ax.legend(loc='lower right')
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'No ELO data',
                   ha='center', va='center', transform=ax.transAxes)

    def _plot_game_outcomes(self, ax):
        """Plot game outcomes as pie chart."""
        ax.set_title('Game Outcomes', fontweight='bold')

        if sum(self.game_outcomes.values()) > 0:
            labels = []
            sizes = []
            colors = []

            if self.game_outcomes['win'] > 0:
                labels.append(f"Wins ({self.game_outcomes['win']})")
                sizes.append(self.game_outcomes['win'])
                colors.append('green')

            if self.game_outcomes['loss'] > 0:
                labels.append(f"Losses ({self.game_outcomes['loss']})")
                sizes.append(self.game_outcomes['loss'])
                colors.append('red')

            if self.game_outcomes['draw'] > 0:
                labels.append(f"Draws ({self.game_outcomes['draw']})")
                sizes.append(self.game_outcomes['draw'])
                colors.append('gray')

            ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                  startangle=90)
            ax.axis('equal')
        else:
            ax.text(0.5, 0.5, 'No game data',
                   ha='center', va='center', transform=ax.transAxes)

    def _plot_move_heatmap(self, ax):
        """Plot move distribution heatmap."""
        ax.set_title('Move Distribution', fontweight='bold')

        if self.move_heatmap is not None and np.sum(self.move_heatmap) > 0:
            # Normalize
            heatmap_normalized = self.move_heatmap / np.max(self.move_heatmap)

            im = ax.imshow(heatmap_normalized, cmap='hot', interpolation='nearest')
            ax.set_xlabel('Column')
            ax.set_ylabel('Row')

            # Add colorbar
            plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        else:
            ax.text(0.5, 0.5, 'No move data',
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])

    def _plot_generation(self, ax):
        """Plot generation progress."""
        ax.set_title('Generation Evolution', fontweight='bold')

        if 'generation' in self.metrics and len(self.metrics['generation']) > 0:
            generations = list(self.metrics['generation'])
            steps = range(len(generations))

            ax.plot(steps, generations, linewidth=2, marker='o',
                   markersize=4, color='purple', alpha=0.8)

            ax.set_xlabel('Training Iteration')
            ax.set_ylabel('Generation')
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'No generation data',
                   ha='center', va='center', transform=ax.transAxes)

    def _plot_move_entropy(self, ax):
        """Plot move entropy (diversity)."""
        ax.set_title('Move Diversity', fontweight='bold')

        if 'move_entropy' in self.metrics and len(self.metrics['move_entropy']) > 0:
            entropy = list(self.metrics['move_entropy'])
            steps = range(len(entropy))

            ax.plot(steps, entropy, linewidth=2, color='orange', alpha=0.8)

            ax.set_xlabel('Game')
            ax.set_ylabel('Entropy')
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'No entropy data',
                   ha='center', va='center', transform=ax.transAxes)

    def _plot_summary(self, ax):
        """Plot summary statistics."""
        ax.set_title('Summary Statistics', fontweight='bold')
        ax.axis('off')

        # Compile statistics
        stats = []

        total_games = sum(self.game_outcomes.values())
        stats.append(f"Total Games: {total_games}")

        if 'win_rate' in self.metrics and len(self.metrics['win_rate']) > 0:
            current_wr = self.metrics['win_rate'][-1]
            stats.append(f"Current Win Rate: {current_wr:.1%}")

        if 'elo' in self.metrics and len(self.metrics['elo']) > 0:
            current_elo = self.metrics['elo'][-1]
            stats.append(f"Current ELO: {current_elo:.0f}")

        if 'generation' in self.metrics and len(self.metrics['generation']) > 0:
            current_gen = self.metrics['generation'][-1]
            stats.append(f"Generation: {int(current_gen)}")

        if 'total_loss' in self.metrics and len(self.metrics['total_loss']) > 0:
            current_loss = self.metrics['total_loss'][-1]
            stats.append(f"Current Loss: {current_loss:.4f}")

        # Display statistics
        y_pos = 0.9
        for stat in stats:
            ax.text(0.1, y_pos, stat, fontsize=11,
                   transform=ax.transAxes, verticalalignment='top')
            y_pos -= 0.15

    def save_metrics(self, filepath: str):
        """
        Save metrics to file.

        Args:
            filepath: Path to save metrics (CSV format)
        """
        import csv

        # Get all metric names
        metric_names = list(self.metrics.keys())

        # Find maximum length
        max_len = max(len(self.metrics[name]) for name in metric_names)

        # Write to CSV
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(['step'] + metric_names)

            # Data
            for i in range(max_len):
                row = [i]
                for name in metric_names:
                    if i < len(self.metrics[name]):
                        row.append(self.metrics[name][i])
                    else:
                        row.append('')
                writer.writerow(row)

    def load_metrics(self, filepath: str):
        """
        Load metrics from file.

        Args:
            filepath: Path to load metrics from (CSV format)
        """
        import csv

        with open(filepath, 'r') as f:
            reader = csv.reader(f)

            # Read header
            header = next(reader)
            metric_names = header[1:]  # Skip 'step' column

            # Read data
            for row in reader:
                for i, name in enumerate(metric_names):
                    if row[i+1]:  # Skip empty cells
                        try:
                            value = float(row[i+1])
                            self.metrics[name].append(value)
                        except ValueError:
                            pass

    def clear(self):
        """Clear all metrics and reset dashboard."""
        self.metrics.clear()
        self.game_outcomes.clear()
        self.move_heatmap = None


class ComparisonDashboard:
    """
    Dashboard for comparing multiple agents.

    Visualizes:
    - Comparative performance metrics
    - Head-to-head win rates
    - ELO progression
    - Training efficiency
    """

    def __init__(self, agent_names: List[str], figsize: Tuple[int, int] = (14, 10)):
        """
        Initialize comparison dashboard.

        Args:
            agent_names: List of agent names to compare
            figsize: Figure size (width, height)
        """
        self.agent_names = agent_names
        self.figsize = figsize

        # Metrics for each agent
        self.agent_metrics = {name: defaultdict(list) for name in agent_names}

        # Head-to-head results
        self.matchups = defaultdict(lambda: {'wins': 0, 'losses': 0, 'draws': 0})

    def update(self, agent_name: str, metrics: Dict):
        """
        Update metrics for specific agent.

        Args:
            agent_name: Name of agent
            metrics: Dictionary of metrics
        """
        for key, value in metrics.items():
            self.agent_metrics[agent_name][key].append(value)

    def update_matchup(self, agent1: str, agent2: str, result: str):
        """
        Update head-to-head matchup result.

        Args:
            agent1: First agent name
            agent2: Second agent name
            result: 'win' (agent1 wins), 'loss' (agent2 wins), or 'draw'
        """
        key = f"{agent1}_vs_{agent2}"
        self.matchups[key][result] += 1

    def plot(self, save_path: Optional[str] = None):
        """
        Create comparison dashboard.

        Args:
            save_path: Optional path to save figure
        """
        fig = plt.figure(figsize=self.figsize)
        gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)

        # 1. ELO comparison
        ax_elo = fig.add_subplot(gs[0, 0])
        self._plot_elo_comparison(ax_elo)

        # 2. Win rate comparison
        ax_winrate = fig.add_subplot(gs[0, 1])
        self._plot_winrate_comparison(ax_winrate)

        # 3. Loss comparison
        ax_loss = fig.add_subplot(gs[0, 2])
        self._plot_loss_comparison(ax_loss)

        # 4. Head-to-head matrix
        ax_h2h = fig.add_subplot(gs[1, :2])
        self._plot_head_to_head(ax_h2h)

        # 5. Training efficiency
        ax_efficiency = fig.add_subplot(gs[1, 2])
        self._plot_training_efficiency(ax_efficiency)

        fig.suptitle('Agent Comparison Dashboard', fontsize=16, fontweight='bold')

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')

        plt.show()

    def _plot_elo_comparison(self, ax):
        """Plot ELO rating comparison."""
        ax.set_title('ELO Rating Progression', fontweight='bold')

        for name in self.agent_names:
            if 'elo' in self.agent_metrics[name]:
                elo = self.agent_metrics[name]['elo']
                if len(elo) > 0:
                    ax.plot(elo, label=name, linewidth=2, alpha=0.8)

        ax.set_xlabel('Evaluation')
        ax.set_ylabel('ELO Rating')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_winrate_comparison(self, ax):
        """Plot win rate comparison."""
        ax.set_title('Win Rate Comparison', fontweight='bold')

        for name in self.agent_names:
            if 'win_rate' in self.agent_metrics[name]:
                wr = self.agent_metrics[name]['win_rate']
                if len(wr) > 0:
                    ax.plot(wr, label=name, linewidth=2, alpha=0.8)

        ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5)
        ax.set_ylim(0, 1)
        ax.set_xlabel('Evaluation')
        ax.set_ylabel('Win Rate')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_loss_comparison(self, ax):
        """Plot training loss comparison."""
        ax.set_title('Training Loss Comparison', fontweight='bold')

        for name in self.agent_names:
            if 'total_loss' in self.agent_metrics[name]:
                loss = self.agent_metrics[name]['total_loss']
                if len(loss) > 0:
                    ax.plot(loss, label=name, linewidth=2, alpha=0.8)

        ax.set_xlabel('Training Step')
        ax.set_ylabel('Loss')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_head_to_head(self, ax):
        """Plot head-to-head matchup results."""
        ax.set_title('Head-to-Head Results', fontweight='bold')

        if len(self.matchups) == 0:
            ax.text(0.5, 0.5, 'No matchup data',
                   ha='center', va='center', transform=ax.transAxes)
            ax.axis('off')
            return

        # Create bar chart
        matchup_names = list(self.matchups.keys())
        x = np.arange(len(matchup_names))
        width = 0.25

        wins = [self.matchups[m]['wins'] for m in matchup_names]
        losses = [self.matchups[m]['losses'] for m in matchup_names]
        draws = [self.matchups[m]['draws'] for m in matchup_names]

        ax.bar(x - width, wins, width, label='Wins', color='green', alpha=0.8)
        ax.bar(x, draws, width, label='Draws', color='gray', alpha=0.8)
        ax.bar(x + width, losses, width, label='Losses', color='red', alpha=0.8)

        ax.set_xticks(x)
        ax.set_xticklabels(matchup_names, rotation=45, ha='right')
        ax.set_ylabel('Games')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

    def _plot_training_efficiency(self, ax):
        """Plot training efficiency metrics."""
        ax.set_title('Training Efficiency', fontweight='bold')

        # Calculate games needed to reach ELO 1200
        efficiencies = {}

        for name in self.agent_names:
            if 'elo' in self.agent_metrics[name] and 'games_played' in self.agent_metrics[name]:
                elo = self.agent_metrics[name]['elo']
                games = self.agent_metrics[name]['games_played']

                # Find first time ELO >= 1200
                for i, e in enumerate(elo):
                    if e >= 1200 and i < len(games):
                        efficiencies[name] = games[i]
                        break

        if efficiencies:
            names = list(efficiencies.keys())
            values = list(efficiencies.values())

            ax.barh(names, values, color='skyblue', alpha=0.8)
            ax.set_xlabel('Games to Reach ELO 1200')
            ax.grid(True, alpha=0.3, axis='x')
        else:
            ax.text(0.5, 0.5, 'Insufficient data',
                   ha='center', va='center', transform=ax.transAxes)
            ax.axis('off')
