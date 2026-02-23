"""
Prometheus Interactive Play

This module provides interactive human vs AI gameplay:
- Chess: Visual board with move input via UCI notation
- Go: Visual board with move input via coordinates
- Jupyter/Colab-friendly interfaces
- Move validation and game tracking
"""

from prometheus.interactive.chess_play import ChessInteractiveGame
from prometheus.interactive.go_play import GoInteractiveGame

__all__ = [
    'ChessInteractiveGame',
    'GoInteractiveGame'
]
