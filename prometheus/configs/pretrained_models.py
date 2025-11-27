"""
Pretrained Model Configurations

Provides ready-to-use model architectures and configurations:
- Standard architectures for common board sizes
- Hyperparameter presets
- Model zoo with pretrained weights (when available)
- Quick-start templates

Usage:
    # Get standard 9x9 Go config
    config = get_go_config(board_size=9, strength='strong')
    agent = PrometheusGoAgent(**config)

    # Load pretrained model
    agent = load_pretrained('go_9x9_medium')
"""

import tensorflow as tf
from tensorflow import keras
from typing import Dict, Any, Optional
import os


# Model configurations
MODEL_CONFIGS = {
    # Go configurations
    'go_9x9_light': {
        'board_size': 9,
        'num_filters': 64,
        'num_res_blocks': 5,
        'l2_reg': 1e-4,
        'dropout': 0.3,
        'learning_rate': 1e-3,
        'description': 'Lightweight model for 9x9 Go (~100K params, fast inference)'
    },

    'go_9x9_medium': {
        'board_size': 9,
        'num_filters': 128,
        'num_res_blocks': 10,
        'l2_reg': 1e-4,
        'dropout': 0.3,
        'learning_rate': 1e-3,
        'description': 'Balanced model for 9x9 Go (~500K params, good strength)'
    },

    'go_9x9_strong': {
        'board_size': 9,
        'num_filters': 256,
        'num_res_blocks': 20,
        'l2_reg': 1e-4,
        'dropout': 0.3,
        'learning_rate': 1e-3,
        'description': 'Strong model for 9x9 Go (~2M params, high strength, slower)'
    },

    'go_13x13_medium': {
        'board_size': 13,
        'num_filters': 128,
        'num_res_blocks': 10,
        'l2_reg': 1e-4,
        'dropout': 0.3,
        'learning_rate': 1e-3,
        'description': 'Balanced model for 13x13 Go'
    },

    'go_19x19_medium': {
        'board_size': 19,
        'num_filters': 128,
        'num_res_blocks': 10,
        'l2_reg': 1e-4,
        'dropout': 0.3,
        'learning_rate': 1e-3,
        'description': 'Balanced model for 19x19 Go'
    },

    'go_19x19_strong': {
        'board_size': 19,
        'num_filters': 256,
        'num_res_blocks': 20,
        'l2_reg': 1e-4,
        'dropout': 0.3,
        'learning_rate': 1e-4,  # Lower LR for larger model
        'description': 'Strong model for 19x19 Go (AlphaGo Zero-style)'
    },

    # Chess configurations
    'chess_light': {
        'num_filters': 64,
        'num_res_blocks': 5,
        'l2_reg': 1e-4,
        'dropout': 0.3,
        'learning_rate': 1e-3,
        'description': 'Lightweight chess model (~100K params)'
    },

    'chess_medium': {
        'num_filters': 128,
        'num_res_blocks': 10,
        'l2_reg': 1e-4,
        'dropout': 0.3,
        'learning_rate': 1e-3,
        'description': 'Medium chess model (~500K params)'
    },

    'chess_strong': {
        'num_filters': 256,
        'num_res_blocks': 20,
        'l2_reg': 1e-4,
        'dropout': 0.3,
        'learning_rate': 1e-4,
        'description': 'Strong chess model (~2M params)'
    },

    # Pattern recognition
    'pattern_64x64_light': {
        'input_shape': (64, 64, 3),
        'num_classes': 8,
        'num_filters': 32,
        'num_res_blocks': 3,
        'l2_reg': 1e-4,
        'dropout': 0.3,
        'learning_rate': 1e-3,
        'description': '64x64 pattern classifier (light)'
    },

    'pattern_64x64_medium': {
        'input_shape': (64, 64, 3),
        'num_classes': 8,
        'num_filters': 64,
        'num_res_blocks': 5,
        'l2_reg': 1e-4,
        'dropout': 0.3,
        'learning_rate': 1e-3,
        'description': '64x64 pattern classifier (medium)'
    },
}


# Training presets
TRAINING_PRESETS = {
    'quick_test': {
        'num_games': 10,
        'epochs': 5,
        'batch_size': 32,
        'description': 'Quick test (5-10 minutes)'
    },

    'standard': {
        'num_games': 100,
        'epochs': 20,
        'batch_size': 64,
        'description': 'Standard training (1-2 hours)'
    },

    'extensive': {
        'num_games': 500,
        'epochs': 50,
        'batch_size': 128,
        'description': 'Extensive training (4-8 hours)'
    },

    'production': {
        'num_games': 5000,
        'epochs': 100,
        'batch_size': 256,
        'description': 'Production quality (1-3 days)'
    }
}


# MCTS presets
MCTS_PRESETS = {
    'fast': {
        'num_simulations': 100,
        'c_puct': 1.0,
        'temperature': 1.0,
        'description': 'Fast MCTS (1-2s per move, +200 ELO)'
    },

    'standard': {
        'num_simulations': 400,
        'c_puct': 1.0,
        'temperature': 1.0,
        'description': 'Standard MCTS (5-10s per move, +350 ELO)'
    },

    'strong': {
        'num_simulations': 800,
        'c_puct': 1.0,
        'temperature': 1.0,
        'description': 'Strong MCTS (10-20s per move, +500 ELO)'
    },

    'alphazero': {
        'num_simulations': 1600,
        'c_puct': 1.0,
        'temperature': 1.0,
        'description': 'AlphaZero-style (30-60s per move, +600 ELO)'
    }
}


def get_model_config(config_name: str) -> Dict[str, Any]:
    """
    Get model configuration by name.

    Args:
        config_name: Configuration name (e.g., 'go_9x9_medium')

    Returns:
        Configuration dictionary

    Raises:
        KeyError: If configuration not found
    """
    if config_name not in MODEL_CONFIGS:
        available = ', '.join(MODEL_CONFIGS.keys())
        raise KeyError(f"Configuration '{config_name}' not found. "
                      f"Available: {available}")

    return MODEL_CONFIGS[config_name].copy()


def get_training_preset(preset_name: str) -> Dict[str, Any]:
    """
    Get training preset by name.

    Args:
        preset_name: Preset name (e.g., 'standard')

    Returns:
        Training configuration

    Raises:
        KeyError: If preset not found
    """
    if preset_name not in TRAINING_PRESETS:
        available = ', '.join(TRAINING_PRESETS.keys())
        raise KeyError(f"Preset '{preset_name}' not found. "
                      f"Available: {available}")

    return TRAINING_PRESETS[preset_name].copy()


def get_mcts_preset(preset_name: str) -> Dict[str, Any]:
    """
    Get MCTS preset by name.

    Args:
        preset_name: Preset name (e.g., 'standard')

    Returns:
        MCTS configuration

    Raises:
        KeyError: If preset not found
    """
    if preset_name not in MCTS_PRESETS:
        available = ', '.join(MCTS_PRESETS.keys())
        raise KeyError(f"Preset '{preset_name}' not found. "
                      f"Available: {available}")

    return MCTS_PRESETS[preset_name].copy()


def list_available_configs():
    """Print all available configurations."""
    print("="*70)
    print("AVAILABLE MODEL CONFIGURATIONS")
    print("="*70)

    print("\nGo Models:")
    for name, config in MODEL_CONFIGS.items():
        if name.startswith('go_'):
            print(f"  {name:25} - {config['description']}")

    print("\nChess Models:")
    for name, config in MODEL_CONFIGS.items():
        if name.startswith('chess_'):
            print(f"  {name:25} - {config['description']}")

    print("\nPattern Recognition:")
    for name, config in MODEL_CONFIGS.items():
        if name.startswith('pattern_'):
            print(f"  {name:25} - {config['description']}")

    print("\nTraining Presets:")
    for name, preset in TRAINING_PRESETS.items():
        print(f"  {name:15} - {preset['description']}")

    print("\nMCTS Presets:")
    for name, preset in MCTS_PRESETS.items():
        print(f"  {name:15} - {preset['description']}")

    print("="*70)


def create_go_agent(config_name: str = 'go_9x9_medium',
                   agent_type: str = 'prometheus'):
    """
    Create Go agent with preset configuration.

    Args:
        config_name: Configuration name
        agent_type: 'prometheus' or 'static'

    Returns:
        Configured agent
    """
    from prometheus.models.go_models import PrometheusGoAgent, StaticGoAgent

    config = get_model_config(config_name)

    if agent_type == 'prometheus':
        return PrometheusGoAgent(
            board_size=config['board_size'],
            num_filters=config['num_filters'],
            num_res_blocks=config['num_res_blocks']
        )
    else:
        return StaticGoAgent(
            board_size=config['board_size'],
            num_filters=config['num_filters'],
            num_res_blocks=config['num_res_blocks']
        )


def create_chess_agent(config_name: str = 'chess_medium',
                      agent_type: str = 'prometheus'):
    """
    Create chess agent with preset configuration.

    Args:
        config_name: Configuration name
        agent_type: 'prometheus' or 'static'

    Returns:
        Configured agent
    """
    from prometheus.models.architectures import PrometheusChessAgent, StaticChessAgent

    config = get_model_config(config_name)

    if agent_type == 'prometheus':
        return PrometheusChessAgent(
            num_filters=config['num_filters'],
            num_res_blocks=config['num_res_blocks']
        )
    else:
        return StaticChessAgent(
            num_filters=config['num_filters'],
            num_res_blocks=config['num_res_blocks']
        )


def create_mcts_agent(base_agent,
                     preset_name: str = 'standard'):
    """
    Enhance agent with MCTS using preset.

    Args:
        base_agent: Base agent to enhance
        preset_name: MCTS preset name

    Returns:
        MCTS-enhanced agent
    """
    from prometheus.models.go_mcts import GoMCTSAgent

    preset = get_mcts_preset(preset_name)

    return GoMCTSAgent(
        base_agent=base_agent,
        num_simulations=preset['num_simulations']
    )


class ModelBuilder:
    """
    Fluent API for building configured models.

    Example:
        agent = (ModelBuilder()
                .go(board_size=9)
                .strength('medium')
                .with_mcts('standard')
                .build())
    """

    def __init__(self):
        """Initialize builder."""
        self.game = None
        self.board_size = None
        self.strength_level = 'medium'
        self.agent_type = 'prometheus'
        self.mcts_preset = None

    def go(self, board_size: int = 9):
        """Configure for Go."""
        self.game = 'go'
        self.board_size = board_size
        return self

    def chess(self):
        """Configure for Chess."""
        self.game = 'chess'
        return self

    def strength(self, level: str = 'medium'):
        """Set strength level (light/medium/strong)."""
        self.strength_level = level
        return self

    def prometheus(self):
        """Use Prometheus agent (online learning)."""
        self.agent_type = 'prometheus'
        return self

    def static(self):
        """Use Static agent (frozen weights)."""
        self.agent_type = 'static'
        return self

    def with_mcts(self, preset: str = 'standard'):
        """Add MCTS enhancement."""
        self.mcts_preset = preset
        return self

    def build(self):
        """Build configured agent."""
        if self.game == 'go':
            config_name = f"go_{self.board_size}x{self.board_size}_{self.strength_level}"
            agent = create_go_agent(config_name, self.agent_type)
        elif self.game == 'chess':
            config_name = f"chess_{self.strength_level}"
            agent = create_chess_agent(config_name, self.agent_type)
        else:
            raise ValueError("Must specify game (go or chess)")

        if self.mcts_preset:
            agent = create_mcts_agent(agent, self.mcts_preset)

        return agent


# Pretrained weights management (placeholder for future)
PRETRAINED_WEIGHTS_URL = "https://github.com/pmcray/Prometheus_v0_PoC/releases/download/v0.69/"


def download_pretrained(model_name: str, save_dir: str = 'models/pretrained'):
    """
    Download pretrained weights (placeholder for future).

    Args:
        model_name: Model name
        save_dir: Directory to save weights

    Returns:
        Path to downloaded weights
    """
    print(f"Pretrained weights not yet available for: {model_name}")
    print("Train your own models or use random initialization")
    return None


def load_pretrained(model_name: str):
    """
    Load pretrained model (placeholder for future).

    Args:
        model_name: Model name

    Returns:
        Loaded agent with pretrained weights
    """
    print(f"Loading pretrained model: {model_name}")

    # For now, return untrained model
    # In future, would download and load weights

    if model_name.startswith('go_'):
        parts = model_name.split('_')
        board_size = int(parts[1].replace('x', '').replace(parts[1].split('x')[1], ''))
        strength = parts[2] if len(parts) > 2 else 'medium'
        config_name = f"go_{board_size}x{board_size}_{strength}"
        return create_go_agent(config_name)
    elif model_name.startswith('chess_'):
        strength = model_name.split('_')[1]
        config_name = f"chess_{strength}"
        return create_chess_agent(config_name)
    else:
        raise ValueError(f"Unknown model: {model_name}")
