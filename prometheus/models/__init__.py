"""
Prometheus Models

Neural network architectures and agents:
- architectures.py: ResNet and CNN builders
- chess_models.py: Chess-specific agents (Static, Prometheus, Random)
- go_models.py: Go-specific agents with policy-value networks
- mcts.py: Monte Carlo Tree Search for chess
- go_mcts.py: Monte Carlo Tree Search for Go
"""

# Import from architectures.py (existing)
from prometheus.models.architectures import (
    residual_block,
    build_resnet,
    build_simple_cnn,
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

# Import from go_models.py
from prometheus.models.go_models import (
    build_go_policy_value_network,
    RandomGoAgent,
    StaticGoAgent,
    PrometheusGoAgent
)

# Import from mcts.py (chess MCTS)
from prometheus.models.mcts import (
    MCTSNode,
    MCTS,
    MCTSAgent,
    compare_mcts_strength
)

# Import from go_mcts.py (Go MCTS)
from prometheus.models.go_mcts import (
    GoMCTSNode,
    GoMCTS,
    GoMCTSAgent
)

__all__ = [
    # Architectures
    'residual_block',
    'build_resnet',
    'build_simple_cnn',
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
    # Go models
    'build_go_policy_value_network',
    'RandomGoAgent',
    'StaticGoAgent',
    'PrometheusGoAgent',
    # Chess MCTS
    'MCTSNode',
    'MCTS',
    'MCTSAgent',
    'compare_mcts_strength',
    # Go MCTS
    'GoMCTSNode',
    'GoMCTS',
    'GoMCTSAgent'
]
