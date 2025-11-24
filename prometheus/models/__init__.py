"""
Prometheus Models

Neural network architectures and agents:
- architectures.py: ResNet and CNN builders
- chess_models.py: Chess-specific agents (Static, Prometheus, Random)
- mcts.py: Monte Carlo Tree Search for improved play
"""

# Import from architectures.py (existing)
from prometheus.models.architectures import (
    residual_block,
    build_resnet_model,
    StaticAgent,
    PrometheusAgent
)

# Import from chess_models.py
from prometheus.models.chess_models import (
    build_chess_cnn,
    build_chess_resnet,
    chess_residual_block,
    BaseChessAgent,
    StaticChessAgent,
    PrometheusChessAgent,
    RandomChessAgent
)

# Import from mcts.py
from prometheus.models.mcts import (
    MCTSNode,
    MCTS,
    MCTSAgent,
    compare_mcts_strength
)

__all__ = [
    # Architectures
    'residual_block',
    'build_resnet_model',
    'StaticAgent',
    'PrometheusAgent',
    # Chess models
    'build_chess_cnn',
    'build_chess_resnet',
    'chess_residual_block',
    'BaseChessAgent',
    'StaticChessAgent',
    'PrometheusChessAgent',
    'RandomChessAgent',
    # MCTS
    'MCTSNode',
    'MCTS',
    'MCTSAgent',
    'compare_mcts_strength'
]
