"""
Prometheus Visualization

Visualization tools for Prometheus experiments:
- Performance plots and comparisons
- Chess game visualization and replay
- Position heatmaps and move overlays
- Attention/saliency for explainability
"""

# Import from plots.py (existing)
from prometheus.visualization.plots import (
    plot_performance_comparison,
    plot_learning_curves,
    plot_capability_growth
)

# Import from chess_viz.py
from prometheus.visualization.chess_viz import (
    ChessBoardVisualizer,
    GameReplayer,
    SideBySideComparison,
    PositionHeatmap,
    MoveProbabilityOverlay,
    visualize_game_comparison
)

# Import from attention.py
from prometheus.visualization.attention import (
    ChessAttentionVisualizer,
    compute_gradcam,
    compute_saliency_map,
    explain_position
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
    'visualize_game_comparison',
    # Attention/Explainability
    'ChessAttentionVisualizer',
    'compute_gradcam',
    'compute_saliency_map',
    'explain_position'
]
