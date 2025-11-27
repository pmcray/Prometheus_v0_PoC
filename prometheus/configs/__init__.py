"""
Configuration module for Prometheus

Provides:
- Pretrained model configurations
- Hyperparameter presets
- Model builder API
- Training presets
- MCTS presets
"""

from prometheus.configs.pretrained_models import (
    get_model_config,
    get_training_preset,
    get_mcts_preset,
    list_available_configs,
    create_go_agent,
    create_chess_agent,
    create_mcts_agent,
    ModelBuilder,
    MODEL_CONFIGS,
    TRAINING_PRESETS,
    MCTS_PRESETS
)

__all__ = [
    'get_model_config',
    'get_training_preset',
    'get_mcts_preset',
    'list_available_configs',
    'create_go_agent',
    'create_chess_agent',
    'create_mcts_agent',
    'ModelBuilder',
    'MODEL_CONFIGS',
    'TRAINING_PRESETS',
    'MCTS_PRESETS'
]
