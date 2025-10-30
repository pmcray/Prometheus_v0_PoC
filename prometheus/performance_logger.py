"""
Performance Logger for CRLS Loop (v0.80)

Logs game results to CSV and provides live performance visualization
using matplotlib.animation for real-time learning feedback.
"""

import json
import os
from typing import Dict, Any, List
from datetime import datetime

class PerformanceLogger:
    def __init__(self, log_file: str = "performance_log.json"):
        self.log_file = log_file
        self.log = self._load_log()

    def _load_log(self) -> Dict[str, List[Any]]:
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                return json.load(f)
        return {'actions': [], 'tool_usage': []}

    def _save_log(self):
        with open(self.log_file, 'w') as f:
            json.dump(self.log, f, indent=2)

    def log_action(self, agent_name: str, action: str, cost: int, success: bool, details: Dict[str, Any]):
        entry = {
            'timestamp': datetime.now().isoformat(),
            'agent': agent_name,
            'action': action,
            'cost': cost,
            'success': success,
            'details': details
        }
        self.log['actions'].append(entry)
        self._save_log()

    def log_tool_usage(self, tool_name: str, execution_time: float, success: bool, task_description: str):
        entry = {
            'timestamp': datetime.now().isoformat(),
            'tool_name': tool_name,
            'execution_time': execution_time,
            'success': success,
            'task_description': task_description
        }
        self.log['tool_usage'].append(entry)
        self._save_log()

    def get_last_solved_complexity(self) -> int:
        # This is a placeholder for a more sophisticated complexity tracking.
        return 0


class LivePerformanceVisualizer:
    """
    Creates live updating performance visualization using matplotlib.animation

    Shows:
    - Rolling win rate over time
    - Individual game results
    - Performance trends
    """

    def __init__(self, logger: PerformanceLogger, update_interval: int = 1000):
        """
        Args:
            logger: PerformanceLogger to read data from
            update_interval: Update interval in milliseconds
        """
        self.logger = logger
        self.update_interval = update_interval

        # Set up the plot
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(12, 8))
        self.fig.suptitle('Connect4 Agent Learning Performance (CRLS Loop)', fontsize=16)

        self.animation = None

    def _update_plot(self, frame):
        """Update function called by FuncAnimation"""
        # Read latest data
        games = self.logger.read_log()

        if not games:
            return

        # Extract data
        game_numbers = [g['game_number'] for g in games]
        win_rates = [g['win_rate_rolling'] for g in games]
        results = [1 if g['winner'] == g['agent_player'] else 0 for g in games]

        # Clear axes
        self.ax1.clear()
        self.ax2.clear()

        # Plot 1: Rolling win rate
        self.ax1.plot(game_numbers, win_rates, 'b-', linewidth=2, label='Rolling Win Rate')
        self.ax1.axhline(y=0.5, color='r', linestyle='--', alpha=0.5, label='50% Baseline')
        self.ax1.set_xlabel('Game Number')
        self.ax1.set_ylabel('Win Rate')
        self.ax1.set_title(f'Rolling Win Rate (Window = {self.logger.window_size} games)')
        self.ax1.set_ylim(-0.05, 1.05)
        self.ax1.grid(True, alpha=0.3)
        self.ax1.legend()

        # Plot 2: Individual results (win/loss/draw)
        colors = ['green' if r == 1 else 'red' for r in results]
        self.ax2.scatter(game_numbers, results, c=colors, alpha=0.6, s=30)
        self.ax2.set_xlabel('Game Number')
        self.ax2.set_ylabel('Result')
        self.ax2.set_yticks([0, 1])
        self.ax2.set_yticklabels(['Loss', 'Win'])
        self.ax2.set_title('Individual Game Results')
        self.ax2.grid(True, alpha=0.3, axis='x')

        # Add stats text
        stats = self.logger.get_stats()
        stats_text = (f"Total Games: {stats['total_games']} | "
                     f"Overall Win Rate: {stats['overall_win_rate']:.1%} | "
                     f"Current Rolling: {stats['current_rolling_win_rate']:.1%}")
        self.fig.text(0.5, 0.02, stats_text, ha='center', fontsize=12,
                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        self.fig.tight_layout(rect=[0, 0.04, 1, 0.96])

    def start(self):
        """Start the live animation"""
        self.animation = FuncAnimation(
            self.fig,
            self._update_plot,
            interval=self.update_interval,
            cache_frame_data=False
        )
        plt.show()

    def save_frame(self, filename: str = "performance_snapshot.png"):
        """Save current frame to file"""
        self._update_plot(None)
        self.fig.savefig(filename, dpi=150, bbox_inches='tight')

    def show_static(self):
        """Show a static (non-animated) plot"""
        self._update_plot(None)
        plt.show()


def create_performance_plot(log_file: str = "performance_log.csv",
                           save_path: Optional[str] = None) -> plt.Figure:
    """
    Create a static performance plot from a log file

    Args:
        log_file: Path to CSV log file
        save_path: Optional path to save figure

    Returns:
        matplotlib Figure object
    """
    logger = PerformanceLogger(log_file)
    games = logger.read_log()

    if not games:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, 'No games logged yet', ha='center', va='center', fontsize=16)
        return fig

    # Extract data
    game_numbers = [g['game_number'] for g in games]
    win_rates = [g['win_rate_rolling'] for g in games]
    generations = [g['generation'] for g in games]

    # Create figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    fig.suptitle('Connect4 CRLS Learning Performance', fontsize=16)

    # Plot rolling win rate
    ax1.plot(game_numbers, win_rates, 'b-', linewidth=2, label='Rolling Win Rate')
    ax1.axhline(y=0.5, color='r', linestyle='--', alpha=0.5, label='50% Baseline')
    ax1.set_xlabel('Game Number')
    ax1.set_ylabel('Win Rate')
    ax1.set_title('Rolling Win Rate Over Time')
    ax1.set_ylim(-0.05, 1.05)
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Plot win rate by generation
    if len(set(generations)) > 1:
        gen_win_rates = {}
        for g in games:
            gen = g['generation']
            if gen not in gen_win_rates:
                gen_win_rates[gen] = []
            won = (g['winner'] == g['agent_player'])
            gen_win_rates[gen].append(1 if won else 0)

        gens = sorted(gen_win_rates.keys())
        avg_win_rates = [np.mean(gen_win_rates[g]) for g in gens]

        ax2.bar(gens, avg_win_rates, color='steelblue', alpha=0.7)
        ax2.axhline(y=0.5, color='r', linestyle='--', alpha=0.5, label='50% Baseline')
        ax2.set_xlabel('Generation')
        ax2.set_ylabel('Win Rate')
        ax2.set_title('Win Rate by Generation')
        ax2.set_ylim(0, 1.05)
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.legend()
    else:
        ax2.text(0.5, 0.5, 'Not enough generations to plot', ha='center', va='center')

    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')

    return fig
