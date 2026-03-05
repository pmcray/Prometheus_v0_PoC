"""
Prometheus Environments

This module provides game environments for Prometheus agents:
- Chess environment with UCI protocol support
- Go environment with complete rule implementation
- Board state representation
- Move generation and validation
- Integration with external engines
"""

try:
    from prometheus.environments.chess import (
        ChessEnvironment,
        ChessBoardEncoder,
        ChessMoveEncoder,
        UCIEngineInterface,
    )
    _CHESS_AVAILABLE = True
except ModuleNotFoundError:
    # python-chess not installed; chess symbols unavailable but Go still works
    _CHESS_AVAILABLE = False

from prometheus.environments.go import (
    GoEnvironment,
    GoBoard,
    GoBoardEncoder,
    GoMoveEncoder,
)

__all__ = [
    # Go (always available)
    'GoEnvironment',
    'GoBoard',
    'GoBoardEncoder',
    'GoMoveEncoder',
]

if _CHESS_AVAILABLE:
    __all__ += [
        'ChessEnvironment',
        'ChessBoardEncoder',
        'ChessMoveEncoder',
        'UCIEngineInterface',
    ]
