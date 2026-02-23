"""
Prometheus Chess Models

This module implements chess-specific neural network architectures:
- Policy-value networks (AlphaZero-style)
- Chess CNN and ResNet architectures
- StaticChessAgent and PrometheusChessAgent
- Self-play training utilities
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
from typing import Tuple, Dict, List, Optional, Any
import chess

from prometheus.environments.chess import (
    ChessEnvironment,
    ChessBoardEncoder,
    ChessMoveEncoder
)


def build_chess_cnn(
    input_shape: Tuple[int, int, int] = (8, 8, 19),
    num_filters: int = 256,
    num_blocks: int = 10,
    policy_output_size: int = 4096,
    dropout_rate: float = 0.3
) -> keras.Model:
    """
    Build chess CNN with policy and value heads.

    Architecture:
    - Input: 8×8×19 board encoding
    - Convolutional blocks with batch normalization
    - Policy head: 4096-dim move probabilities
    - Value head: scalar position evaluation

    Args:
        input_shape: Input tensor shape (8, 8, 19)
        num_filters: Filters per conv layer
        num_blocks: Number of conv blocks
        policy_output_size: Policy output dimension (4096)
        dropout_rate: Dropout rate

    Returns:
        Keras Model with policy and value outputs
    """
    # Input
    board_input = layers.Input(shape=input_shape, name='board_state')

    # Initial conv block
    x = layers.Conv2D(num_filters, 3, padding='same')(board_input)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)

    # Convolutional blocks
    for i in range(num_blocks):
        x = layers.Conv2D(num_filters, 3, padding='same')(x)
        x = layers.BatchNormalization()(x)
        x = layers.Activation('relu')(x)
        x = layers.Dropout(dropout_rate)(x)

    # Policy head (move probabilities)
    policy = layers.Conv2D(32, 1, padding='same')(x)
    policy = layers.BatchNormalization()(policy)
    policy = layers.Activation('relu')(policy)
    policy = layers.Flatten()(policy)
    policy = layers.Dense(policy_output_size, activation='softmax', name='policy')(policy)

    # Value head (position evaluation)
    value = layers.Conv2D(8, 1, padding='same')(x)
    value = layers.BatchNormalization()(value)
    value = layers.Activation('relu')(value)
    value = layers.Flatten()(value)
    value = layers.Dense(256, activation='relu')(value)
    value = layers.Dropout(dropout_rate)(value)
    value = layers.Dense(1, activation='tanh', name='value')(value)

    # Combined model
    model = keras.Model(
        inputs=board_input,
        outputs=[policy, value],
        name='ChessCNN'
    )

    return model


def chess_residual_block(
    x: tf.Tensor,
    filters: int,
    kernel_size: int = 3
) -> tf.Tensor:
    """
    Residual block for chess ResNet.

    Args:
        x: Input tensor
        filters: Number of filters
        kernel_size: Convolution kernel size

    Returns:
        Output tensor with skip connection
    """
    shortcut = x

    # First conv
    y = layers.Conv2D(filters, kernel_size, padding='same')(x)
    y = layers.BatchNormalization()(y)
    y = layers.Activation('relu')(y)

    # Second conv
    y = layers.Conv2D(filters, kernel_size, padding='same')(y)
    y = layers.BatchNormalization()(y)

    # Skip connection
    y = layers.Add()([y, shortcut])
    y = layers.Activation('relu')(y)

    return y


def build_chess_resnet(
    input_shape: Tuple[int, int, int] = (8, 8, 19),
    num_filters: int = 256,
    num_residual_blocks: int = 19,
    policy_output_size: int = 4096,
    dropout_rate: float = 0.3
) -> keras.Model:
    """
    Build chess ResNet with policy and value heads (AlphaZero-style).

    Architecture:
    - Input: 8×8×19 board encoding
    - Initial conv layer
    - N residual blocks
    - Policy head: 4096-dim softmax
    - Value head: tanh scalar

    Args:
        input_shape: Input tensor shape
        num_filters: Filters per residual block
        num_residual_blocks: Number of residual blocks
        policy_output_size: Policy output dimension
        dropout_rate: Dropout rate

    Returns:
        Keras Model with policy and value outputs
    """
    # Input
    board_input = layers.Input(shape=input_shape, name='board_state')

    # Initial conv block
    x = layers.Conv2D(num_filters, 3, padding='same')(board_input)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)

    # Residual tower
    for i in range(num_residual_blocks):
        x = chess_residual_block(x, num_filters)

    # Policy head
    policy = layers.Conv2D(32, 1, padding='same')(x)
    policy = layers.BatchNormalization()(policy)
    policy = layers.Activation('relu')(policy)
    policy = layers.Flatten()(policy)
    policy = layers.Dense(policy_output_size, activation='softmax', name='policy')(policy)

    # Value head
    value = layers.Conv2D(8, 1, padding='same')(x)
    value = layers.BatchNormalization()(value)
    value = layers.Activation('relu')(value)
    value = layers.Flatten()(value)
    value = layers.Dense(256, activation='relu')(value)
    value = layers.Dropout(dropout_rate)(value)
    value = layers.Dense(1, activation='tanh', name='value')(value)

    # Combined model
    model = keras.Model(
        inputs=board_input,
        outputs=[policy, value],
        name='ChessResNet'
    )

    return model


class BaseChessAgent:
    """
    Base class for chess agents.

    Provides common functionality:
    - Board state encoding
    - Move selection
    - Model inference
    - Training utilities
    """

    def __init__(
        self,
        model: keras.Model,
        name: str = "ChessAgent"
    ):
        """
        Initialize chess agent.

        Args:
            model: Keras model with policy and value outputs
            name: Agent name
        """
        self.model = model
        self.name = name
        self.encoder = ChessBoardEncoder()
        self.move_encoder = ChessMoveEncoder()
        self.games_played = 0
        self.wins = 0
        self.losses = 0
        self.draws = 0

    def get_move(
        self,
        board_state: np.ndarray,
        board: chess.Board,
        temperature: float = 1.0
    ) -> chess.Move:
        """
        Get move for current position.

        Args:
            board_state: Encoded board state
            board: python-chess Board object
            temperature: Sampling temperature

        Returns:
            Selected chess.Move
        """
        # Get policy and value from model
        policy, value = self.predict(board_state)

        # Decode move from policy
        move = self.move_encoder.decode_policy(policy, board, temperature)

        return move

    def predict(self, board_state: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Get policy and value predictions.

        Args:
            board_state: Encoded board state (8×8×19)

        Returns:
            Tuple of (policy, value)
        """
        # Add batch dimension
        state_batch = np.expand_dims(board_state, axis=0)

        # Predict
        policy, value = self.model.predict(state_batch, verbose=0)

        return policy[0], value[0, 0]

    def evaluate_position(self, board: chess.Board) -> float:
        """
        Evaluate position using value head.

        Args:
            board: python-chess Board object

        Returns:
            Position evaluation in range [-1, 1]
        """
        state = self.encoder.encode_full(board)
        _, value = self.predict(state)
        return value

    def update_statistics(self, result: str):
        """
        Update win/loss/draw statistics.

        Args:
            result: Game result ("1-0", "0-1", "1/2-1/2")
        """
        self.games_played += 1
        if result == "1-0":
            self.wins += 1
        elif result == "0-1":
            self.losses += 1
        else:
            self.draws += 1

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get agent statistics.

        Returns:
            Dictionary with games played, wins, losses, draws
        """
        win_rate = (self.wins / self.games_played * 100) if self.games_played > 0 else 0
        return {
            'name': self.name,
            'games_played': self.games_played,
            'wins': self.wins,
            'losses': self.losses,
            'draws': self.draws,
            'win_rate': win_rate
        }


class StaticChessAgent(BaseChessAgent):
    """
    Static Chess Agent: Pre-trained model with frozen weights.

    After initial training, weights are frozen and cannot adapt
    to new opponents or strategies.
    """

    def __init__(
        self,
        architecture: str = 'cnn',
        num_filters: int = 128,
        num_blocks: int = 10,
        name: str = "StaticChess"
    ):
        """
        Initialize static chess agent.

        Args:
            architecture: 'cnn' or 'resnet'
            num_filters: Filters per layer
            num_blocks: Number of conv/residual blocks
            name: Agent name
        """
        # Build model
        if architecture == 'resnet':
            model = build_chess_resnet(
                num_filters=num_filters,
                num_residual_blocks=num_blocks
            )
        else:
            model = build_chess_cnn(
                num_filters=num_filters,
                num_blocks=num_blocks
            )

        super().__init__(model, name)
        self.is_frozen = False

    def pretrain(
        self,
        games: List[Dict],
        epochs: int = 20,
        batch_size: int = 64,
        learning_rate: float = 0.001
    ):
        """
        Pre-train on game data, then freeze weights.

        Args:
            games: List of game dictionaries with states, moves, outcomes
            epochs: Training epochs
            batch_size: Batch size
            learning_rate: Learning rate
        """
        # Compile model
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate),
            loss={
                'policy': 'categorical_crossentropy',
                'value': 'mse'
            },
            loss_weights={'policy': 1.0, 'value': 0.5},
            metrics={'policy': 'accuracy', 'value': 'mae'}
        )

        # Prepare training data
        X_train, y_policy, y_value = self._prepare_training_data(games)

        # Train
        history = self.model.fit(
            X_train,
            {'policy': y_policy, 'value': y_value},
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.15,
            verbose=1
        )

        # FREEZE weights
        self.model.trainable = False
        self.is_frozen = True

        print(f"✅ {self.name} pre-trained and weights FROZEN")

        return history

    def _prepare_training_data(
        self,
        games: List[Dict]
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare training data from games.

        Args:
            games: List of game dictionaries

        Returns:
            Tuple of (states, policy_targets, value_targets)
        """
        # Extract data from games
        states = []
        policy_targets = []
        value_targets = []

        for game in games:
            states.extend(game['states'])
            policy_targets.extend(game['policy_targets'])
            value_targets.extend(game['value_targets'])

        return (
            np.array(states),
            np.array(policy_targets),
            np.array(value_targets)
        )


class PrometheusChessAgent(BaseChessAgent):
    """
    Prometheus Chess Agent: Adaptive model with online learning.

    Can continue learning during play, adapting to opponents
    and improving strategies through self-play.
    """

    def __init__(
        self,
        architecture: str = 'cnn',
        num_filters: int = 128,
        num_blocks: int = 10,
        learning_rate: float = 0.0003,
        name: str = "PrometheusChess"
    ):
        """
        Initialize Prometheus chess agent.

        Args:
            architecture: 'cnn' or 'resnet'
            num_filters: Filters per layer
            num_blocks: Number of conv/residual blocks
            learning_rate: Learning rate
            name: Agent name
        """
        # Build model
        if architecture == 'resnet':
            model = build_chess_resnet(
                num_filters=num_filters,
                num_residual_blocks=num_blocks
            )
        else:
            model = build_chess_cnn(
                num_filters=num_filters,
                num_blocks=num_blocks
            )

        super().__init__(model, name)
        self.learning_rate = learning_rate

        # Compile model (stays trainable)
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate),
            loss={
                'policy': 'categorical_crossentropy',
                'value': 'mse'
            },
            loss_weights={'policy': 1.0, 'value': 0.5},
            metrics={'policy': 'accuracy', 'value': 'mae'}
        )

    def pretrain(
        self,
        games: List[Dict],
        epochs: int = 20,
        batch_size: int = 64
    ):
        """
        Pre-train on game data (weights remain trainable).

        Args:
            games: List of game dictionaries
            epochs: Training epochs
            batch_size: Batch size
        """
        # Prepare training data
        X_train, y_policy, y_value = self._prepare_training_data(games)

        # Train
        history = self.model.fit(
            X_train,
            {'policy': y_policy, 'value': y_value},
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.15,
            verbose=1
        )

        print(f"✅ {self.name} pre-trained (weights remain TRAINABLE)")

        return history

    def online_learn(
        self,
        games: List[Dict],
        epochs: int = 5,
        batch_size: int = 32
    ):
        """
        Online learning from recent games.

        This is the key difference from Static: Prometheus can
        continue learning and adapting.

        Args:
            games: Recent game data
            epochs: Training epochs
            batch_size: Batch size
        """
        # Prepare data
        X_train, y_policy, y_value = self._prepare_training_data(games)

        # Continue training
        self.model.fit(
            X_train,
            {'policy': y_policy, 'value': y_value},
            epochs=epochs,
            batch_size=batch_size,
            verbose=0
        )

        print(f"📈 {self.name} learned from {len(games)} games")

    def _prepare_training_data(
        self,
        games: List[Dict]
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare training data from games."""
        states = []
        policy_targets = []
        value_targets = []

        for game in games:
            states.extend(game['states'])
            policy_targets.extend(game['policy_targets'])
            value_targets.extend(game['value_targets'])

        return (
            np.array(states),
            np.array(policy_targets),
            np.array(value_targets)
        )


class RandomChessAgent:
    """
    Random chess agent for baseline comparison.

    Plays random legal moves.
    """

    def __init__(self, name: str = "Random"):
        """Initialize random agent."""
        self.name = name
        self.games_played = 0
        self.wins = 0
        self.losses = 0
        self.draws = 0

    def get_move(
        self,
        board_state: np.ndarray,
        board: chess.Board,
        temperature: float = 1.0
    ) -> chess.Move:
        """Get random legal move."""
        legal_moves = list(board.legal_moves)
        return np.random.choice(legal_moves)

    def update_statistics(self, result: str):
        """Update statistics."""
        self.games_played += 1
        if result == "1-0":
            self.wins += 1
        elif result == "0-1":
            self.losses += 1
        else:
            self.draws += 1

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics."""
        win_rate = (self.wins / self.games_played * 100) if self.games_played > 0 else 0
        return {
            'name': self.name,
            'games_played': self.games_played,
            'wins': self.wins,
            'losses': self.losses,
            'draws': self.draws,
            'win_rate': win_rate
        }
