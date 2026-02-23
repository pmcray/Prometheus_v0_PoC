"""
Multi-Game Performance Logger (v0.81)

Tracks performance across multiple game types and identifies
cross-game learning patterns.
"""

import csv
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np


class MultiGameLogger:
    """
    Logs performance across multiple game types

    Extends PerformanceLogger to track cross-game patterns and
    transfer learning effectiveness.
    """

    def __init__(self, log_file: str = "multi_game_performance.csv",
                 window_size: int = 20):
        self.log_file = log_file
        self.window_size = window_size
        self.games_by_type = {
            'connect4': [],
            'othello': [],
            'draughts': []
        }
        self.total_games = 0

        # Initialize CSV
        self._initialize_csv()

    def _initialize_csv(self):
        """Create CSV with headers if doesn't exist"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'game_number',
                    'timestamp',
                    'game_type',
                    'result',
                    'winner',
                    'agent_player',
                    'moves_count',
                    'win_rate_rolling',
                    'game_type_win_rate',
                    'generation'
                ])

    def log_game(self, game_history: Dict[str, Any], agent_player: int,
                 game_type: str, generation: int = 0):
        """
        Log game result with game type

        Args:
            game_history: Game history dict
            agent_player: Which player agent was
            game_type: Type of game
            generation: Generation number
        """
        result = game_history['result']
        winner = game_history['winner']
        moves = game_history.get('moves', [])

        # Determine if agent won
        agent_won = (winner == agent_player)

        # Update game-specific history
        if game_type in self.games_by_type:
            self.games_by_type[game_type].append(agent_won)

        # Calculate rolling win rates
        all_results = []
        for game_results in self.games_by_type.values():
            all_results.extend(game_results)

        # Overall rolling win rate
        recent_results = all_results[-self.window_size:]
        overall_win_rate = sum(recent_results) / len(recent_results) if recent_results else 0.0

        # Game-specific win rate
        game_results = self.games_by_type.get(game_type, [])
        recent_game_results = game_results[-self.window_size:]
        game_win_rate = sum(recent_game_results) / len(recent_game_results) if recent_game_results else 0.0

        # Log to CSV
        self.total_games += 1
        timestamp = datetime.now().isoformat()

        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                self.total_games,
                timestamp,
                game_type,
                result,
                winner,
                agent_player,
                len(moves),
                f"{overall_win_rate:.3f}",
                f"{game_win_rate:.3f}",
                generation
            ])

    def read_log(self) -> List[Dict[str, Any]]:
        """Read all logged games"""
        games = []

        if not os.path.exists(self.log_file):
            return games

        with open(self.log_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                games.append({
                    'game_number': int(row['game_number']),
                    'timestamp': row['timestamp'],
                    'game_type': row['game_type'],
                    'result': row['result'],
                    'winner': int(row['winner']) if row['winner'] != 'None' else None,
                    'agent_player': int(row['agent_player']),
                    'moves_count': int(row['moves_count']),
                    'win_rate_rolling': float(row['win_rate_rolling']),
                    'game_type_win_rate': float(row['game_type_win_rate']),
                    'generation': int(row['generation'])
                })

        return games

    def get_stats_by_game(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics broken down by game type"""
        stats = {}
        games = self.read_log()

        for game_type in ['connect4', 'othello', 'draughts']:
            type_games = [g for g in games if g['game_type'] == game_type]

            if type_games:
                wins = sum(1 for g in type_games if g['winner'] == g['agent_player'])
                total = len(type_games)

                stats[game_type] = {
                    'total_games': total,
                    'wins': wins,
                    'losses': total - wins,
                    'win_rate': wins / total if total > 0 else 0.0,
                    'latest_rolling_win_rate': type_games[-1]['game_type_win_rate'] if type_games else 0.0
                }
            else:
                stats[game_type] = {
                    'total_games': 0,
                    'wins': 0,
                    'losses': 0,
                    'win_rate': 0.0,
                    'latest_rolling_win_rate': 0.0
                }

        return stats

    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall statistics across all games"""
        games = self.read_log()

        if not games:
            return {
                'total_games': 0,
                'overall_win_rate': 0.0,
                'games_by_type': {}
            }

        wins = sum(1 for g in games if g['winner'] == g['agent_player'])

        return {
            'total_games': len(games),
            'overall_win_rate': wins / len(games) if games else 0.0,
            'latest_rolling_win_rate': games[-1]['win_rate_rolling'] if games else 0.0,
            'games_by_type': self.get_stats_by_game()
        }

    def calculate_transfer_learning_metric(self) -> float:
        """
        Calculate transfer learning effectiveness

        Measures if learning in one game improves performance in others.

        Returns:
            Score from 0.0 to 1.0
        """
        stats = self.get_stats_by_game()

        # Count games with sufficient data
        games_with_data = [
            game_type for game_type, st in stats.items()
            if st['total_games'] >= 10
        ]

        if len(games_with_data) < 2:
            return 0.0  # Need multiple games for transfer learning

        # Check if all games have above-baseline performance
        win_rates = [stats[gt]['win_rate'] for gt in games_with_data]
        avg_win_rate = np.mean(win_rates)
        min_win_rate = min(win_rates)
        std_win_rate = np.std(win_rates)

        # Transfer learning score:
        # High if: average win rate is high, minimum is above baseline,
        # and variance is low (consistent across games)
        score = (
            0.5 * min(1.0, avg_win_rate / 0.7) +  # Average performance
            0.3 * min(1.0, min_win_rate / 0.5) +   # Minimum performance
            0.2 * max(0.0, 1.0 - std_win_rate * 3)  # Consistency
        )

        return score


def create_multi_game_plot(log_file: str = "multi_game_performance.csv",
                           save_path: Optional[str] = None) -> plt.Figure:
    """
    Create visualization of multi-game performance

    Args:
        log_file: Path to CSV log
        save_path: Optional save path

    Returns:
        matplotlib Figure
    """
    logger = MultiGameLogger(log_file)
    games = logger.read_log()

    if not games:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, 'No games logged yet', ha='center', va='center', fontsize=16)
        return fig

    # Create figure with 3 subplots
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10))
    fig.suptitle('Multi-Game CRLS Learning Performance', fontsize=16)

    # Plot 1: Overall rolling win rate
    game_numbers = [g['game_number'] for g in games]
    overall_win_rates = [g['win_rate_rolling'] for g in games]

    ax1.plot(game_numbers, overall_win_rates, 'b-', linewidth=2, label='Overall Win Rate')
    ax1.axhline(y=0.5, color='r', linestyle='--', alpha=0.5, label='50% Baseline')
    ax1.set_xlabel('Game Number')
    ax1.set_ylabel('Win Rate')
    ax1.set_title('Overall Rolling Win Rate (All Games)')
    ax1.set_ylim(-0.05, 1.05)
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Plot 2: Win rate by game type
    stats_by_game = logger.get_stats_by_game()
    game_types = [gt for gt, st in stats_by_game.items() if st['total_games'] > 0]
    win_rates_by_type = [stats_by_game[gt]['win_rate'] for gt in game_types]
    colors = ['#3498db', '#e74c3c', '#2ecc71'][:len(game_types)]

    bars = ax2.bar(game_types, win_rates_by_type, color=colors, alpha=0.7)
    ax2.axhline(y=0.5, color='r', linestyle='--', alpha=0.5, label='50% Baseline')
    ax2.set_xlabel('Game Type')
    ax2.set_ylabel('Win Rate')
    ax2.set_title('Win Rate by Game Type')
    ax2.set_ylim(0, 1.05)
    ax2.grid(True, alpha=0.3, axis='y')

    # Add value labels on bars
    for bar, game_type in zip(bars, game_types):
        height = bar.get_height()
        games_count = stats_by_game[game_type]['total_games']
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{height:.1%}\n({games_count} games)',
                ha='center', va='bottom', fontsize=10)

    # Plot 3: Game type timeline
    game_types_played = [g['game_type'] for g in games]
    game_type_to_num = {'connect4': 0, 'othello': 1, 'draughts': 2}
    game_type_nums = [game_type_to_num.get(gt, 0) for gt in game_types_played]
    colors_timeline = ['#3498db' if g['winner'] == g['agent_player'] else '#e74c3c'
                      for g in games]

    ax3.scatter(game_numbers, game_type_nums, c=colors_timeline, alpha=0.6, s=40)
    ax3.set_xlabel('Game Number')
    ax3.set_ylabel('Game Type')
    ax3.set_yticks([0, 1, 2])
    ax3.set_yticklabels(['Connect4', 'Othello', 'Draughts'])
    ax3.set_title('Game Type Timeline (Blue=Win, Red=Loss)')
    ax3.grid(True, alpha=0.3, axis='x')

    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')

    return fig
