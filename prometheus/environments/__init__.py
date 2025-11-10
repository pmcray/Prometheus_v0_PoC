"""
Prometheus Environments

This module provides game environments for Prometheus agents:
- Chess environment with UCI protocol support
- Board state representation
- Move generation and validation
- Integration with external chess engines
"""

from prometheus.environments.chess import (
    ChessEnvironment,
    ChessBoardEncoder,
    ChessMoveEncoder,
    UCIEngineInterface
)

__all__ = [
    'ChessEnvironment',
    'ChessBoardEncoder',
    'ChessMoveEncoder',
    'UCIEngineInterface'
]
