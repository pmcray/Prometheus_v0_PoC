"""
Game Analysis module for Prometheus

Provides post-game analysis tools:
- Position evaluation
- Critical moments identification
- Mistake detection
- Aggregate statistics
"""

from prometheus.analysis.game_analyzer import (
    PositionEvaluator,
    GoGameAnalyzer,
    ChessGameAnalyzer,
    BatchAnalyzer
)

__all__ = [
    'PositionEvaluator',
    'GoGameAnalyzer',
    'ChessGameAnalyzer',
    'BatchAnalyzer'
]
