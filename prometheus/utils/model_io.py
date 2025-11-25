"""
Prometheus Model Persistence

Save and load trained models for:
- Resuming training after interruption
- Comparing model versions
- Deploying to production
- Sharing pretrained models
"""

import os
import json
import tensorflow as tf
from tensorflow import keras
import numpy as np
from typing import Dict, Any, Optional
from pathlib import Path
import pickle


class ModelCheckpoint:
    """
    Manage model checkpoints for chess and Go agents.

    Saves:
    - Model weights
    - Training statistics
    - Hyperparameters
    - Metadata (version, date, performance)
    """

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory for saving checkpoints
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save_agent(
        self,
        agent: Any,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        overwrite: bool = False
    ) -> str:
        """
        Save agent to checkpoint.

        Args:
            agent: Chess or Go agent
            name: Checkpoint name
            metadata: Additional metadata to save
            overwrite: Overwrite existing checkpoint

        Returns:
            Path to saved checkpoint
        """
        checkpoint_path = self.checkpoint_dir / name

        if checkpoint_path.exists() and not overwrite:
            raise FileExistsError(
                f"Checkpoint {name} already exists. Use overwrite=True to replace."
            )

        checkpoint_path.mkdir(parents=True, exist_ok=True)

        # Save model weights
        model_path = checkpoint_path / "model.h5"
        agent.model.save(model_path)

        # Save agent statistics
        stats_path = checkpoint_path / "statistics.json"
        stats = {
            'games_played': agent.games_played,
            'wins': agent.wins,
            'losses': agent.losses,
            'draws': agent.draws,
            'name': agent.name
        }

        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)

        # Save metadata
        meta_path = checkpoint_path / "metadata.json"
        meta = {
            'agent_type': type(agent).__name__,
            'model_params': agent.model.count_params(),
            'architecture': getattr(agent, 'architecture', 'unknown'),
            **(metadata or {})
        }

        with open(meta_path, 'w') as f:
            json.dump(meta, f, indent=2)

        print(f"✅ Saved checkpoint: {checkpoint_path}")
        return str(checkpoint_path)

    def load_agent(
        self,
        name: str,
        agent_class: Any,
        **agent_kwargs
    ) -> Any:
        """
        Load agent from checkpoint.

        Args:
            name: Checkpoint name
            agent_class: Agent class to instantiate
            **agent_kwargs: Additional arguments for agent

        Returns:
            Loaded agent
        """
        checkpoint_path = self.checkpoint_dir / name

        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint {name} not found")

        # Load metadata
        meta_path = checkpoint_path / "metadata.json"
        with open(meta_path, 'r') as f:
            metadata = json.load(f)

        # Create agent
        agent = agent_class(**agent_kwargs)

        # Load model weights
        model_path = checkpoint_path / "model.h5"
        agent.model = keras.models.load_model(model_path)

        # Load statistics
        stats_path = checkpoint_path / "statistics.json"
        if stats_path.exists():
            with open(stats_path, 'r') as f:
                stats = json.load(f)
                agent.games_played = stats.get('games_played', 0)
                agent.wins = stats.get('wins', 0)
                agent.losses = stats.get('losses', 0)
                agent.draws = stats.get('draws', 0)

        print(f"✅ Loaded checkpoint: {checkpoint_path}")
        print(f"   Games played: {agent.games_played}")
        print(f"   W/L/D: {agent.wins}/{agent.losses}/{agent.draws}")

        return agent

    def list_checkpoints(self) -> list:
        """List all available checkpoints."""
        checkpoints = []

        for path in self.checkpoint_dir.iterdir():
            if path.is_dir():
                meta_path = path / "metadata.json"
                if meta_path.exists():
                    with open(meta_path, 'r') as f:
                        metadata = json.load(f)
                    checkpoints.append({
                        'name': path.name,
                        'path': str(path),
                        'metadata': metadata
                    })

        return checkpoints

    def delete_checkpoint(self, name: str):
        """Delete a checkpoint."""
        checkpoint_path = self.checkpoint_dir / name

        if checkpoint_path.exists():
            import shutil
            shutil.rmtree(checkpoint_path)
            print(f"🗑️  Deleted checkpoint: {name}")
        else:
            print(f"⚠️  Checkpoint {name} not found")


class TrainingCheckpointer:
    """
    Automatic checkpointing during training.

    Saves best models based on performance metrics.
    """

    def __init__(
        self,
        checkpoint_manager: ModelCheckpoint,
        save_best_only: bool = True,
        monitor: str = 'win_rate',
        mode: str = 'max'
    ):
        """
        Initialize training checkpointer.

        Args:
            checkpoint_manager: ModelCheckpoint instance
            save_best_only: Only save when metric improves
            monitor: Metric to monitor
            mode: 'max' or 'min'
        """
        self.checkpoint_manager = checkpoint_manager
        self.save_best_only = save_best_only
        self.monitor = monitor
        self.mode = mode

        self.best_value = -float('inf') if mode == 'max' else float('inf')
        self.checkpoint_count = 0

    def on_iteration_end(
        self,
        agent: Any,
        iteration: int,
        metrics: Dict[str, float]
    ):
        """
        Called at end of training iteration.

        Args:
            agent: Agent to checkpoint
            iteration: Current iteration
            metrics: Performance metrics
        """
        current_value = metrics.get(self.monitor)

        if current_value is None:
            print(f"⚠️  Metric {self.monitor} not found in metrics")
            return

        should_save = False

        if self.save_best_only:
            if self.mode == 'max':
                if current_value > self.best_value:
                    self.best_value = current_value
                    should_save = True
            else:
                if current_value < self.best_value:
                    self.best_value = current_value
                    should_save = True
        else:
            should_save = True

        if should_save:
            checkpoint_name = f"{agent.name}_iter{iteration:03d}"
            metadata = {
                'iteration': iteration,
                'metrics': metrics,
                f'best_{self.monitor}': float(self.best_value)
            }

            self.checkpoint_manager.save_agent(
                agent,
                checkpoint_name,
                metadata=metadata,
                overwrite=True
            )

            self.checkpoint_count += 1
            print(f"💾 Checkpoint saved: {checkpoint_name}")
            print(f"   {self.monitor}: {current_value:.4f} (best: {self.best_value:.4f})")


def save_pretrained_model(
    agent: Any,
    name: str,
    description: str,
    performance: Dict[str, Any],
    output_dir: str = "pretrained_models"
):
    """
    Save a pretrained model for distribution.

    Args:
        agent: Trained agent
        name: Model name
        description: Model description
        performance: Performance metrics
        output_dir: Output directory
    """
    output_path = Path(output_dir) / name
    output_path.mkdir(parents=True, exist_ok=True)

    # Save model
    model_path = output_path / "model.h5"
    agent.model.save(model_path)

    # Save README
    readme_path = output_path / "README.md"
    readme_content = f"""# {name}

{description}

## Performance

{json.dumps(performance, indent=2)}

## Usage

```python
from prometheus.models.chess_models import PrometheusChessAgent
from prometheus.utils.model_io import load_pretrained_model

# Load model
agent = load_pretrained_model('{name}', PrometheusChessAgent)

# Use for inference
move = agent.get_move(board_state, board)
```

## Training Details

- Agent Type: {type(agent).__name__}
- Parameters: {agent.model.count_params():,}
- Games Played: {agent.games_played}
- Win Rate: {(agent.wins / agent.games_played * 100) if agent.games_played > 0 else 0:.1f}%
"""

    with open(readme_path, 'w') as f:
        f.write(readme_content)

    # Save config
    config_path = output_path / "config.json"
    config = {
        'name': name,
        'agent_type': type(agent).__name__,
        'description': description,
        'performance': performance,
        'parameters': agent.model.count_params(),
        'statistics': {
            'games_played': agent.games_played,
            'wins': agent.wins,
            'losses': agent.losses,
            'draws': agent.draws
        }
    }

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"✅ Pretrained model saved: {output_path}")
    return str(output_path)


def load_pretrained_model(
    name: str,
    agent_class: Any,
    pretrained_dir: str = "pretrained_models",
    **agent_kwargs
) -> Any:
    """
    Load a pretrained model.

    Args:
        name: Model name
        agent_class: Agent class
        pretrained_dir: Pretrained models directory
        **agent_kwargs: Agent constructor arguments

    Returns:
        Loaded agent
    """
    model_path = Path(pretrained_dir) / name / "model.h5"

    if not model_path.exists():
        raise FileNotFoundError(f"Pretrained model {name} not found at {model_path}")

    # Load config
    config_path = Path(pretrained_dir) / name / "config.json"
    with open(config_path, 'r') as f:
        config = json.load(f)

    # Create agent
    agent = agent_class(**agent_kwargs)

    # Load weights
    agent.model = keras.models.load_model(model_path)

    # Restore statistics
    stats = config.get('statistics', {})
    agent.games_played = stats.get('games_played', 0)
    agent.wins = stats.get('wins', 0)
    agent.losses = stats.get('losses', 0)
    agent.draws = stats.get('draws', 0)

    print(f"✅ Loaded pretrained model: {name}")
    print(f"   {config.get('description', 'No description')}")

    return agent
