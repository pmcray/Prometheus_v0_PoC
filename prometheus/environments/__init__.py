"""
Prometheus Environments

This module provides game environments for Prometheus agents:
- Chess environment with UCI protocol support
- Go environment with complete rule implementation
- Board state representation
- Move generation and validation
- Integration with external engines
"""

from prometheus.environments.chess import (
    ChessEnvironment,
    ChessBoardEncoder,
    ChessMoveEncoder,
    UCIEngineInterface
)

from prometheus.environments.go import (
    GoEnvironment,
    GoBoard,
    GoBoardEncoder,
    GoMoveEncoder
)

__all__ = [
    # Chess
    'ChessEnvironment',
    'ChessBoardEncoder',
    'ChessMoveEncoder',
    'UCIEngineInterface',
    # Go
    'GoEnvironment',
    'GoBoard',
    'GoBoardEncoder',
    'GoMoveEncoder'
]
