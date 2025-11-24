"""
Prometheus Visualization

Visualization tools for Prometheus experiments:
- Performance plots and comparisons
- Chess game visualization and replay
- Position heatmaps and move overlays
"""

# Import from plots.py (existing)
from prometheus.visualization.plots import (
    plot_performance_comparison,
    plot_learning_curves,
    plot_capability_growth
)

# Import from chess_viz.py (new)
from prometheus.visualization.chess_viz import (
    ChessBoardVisualizer,
    GameReplayer,
    SideBySideComparison,
    PositionHeatmap,
    MoveProbabilityOverlay,
    visualize_game_comparison
)

__all__ = [
    # Performance visualization
    'plot_performance_comparison',
    'plot_learning_curves',
    'plot_capability_growth',
    # Chess visualization
    'ChessBoardVisualizer',
    'GameReplayer',
    'SideBySideComparison',
    'PositionHeatmap',
    'MoveProbabilityOverlay',
    'visualize_game_comparison'
]
