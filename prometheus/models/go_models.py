"""
Prometheus Go Neural Network Architectures

Go-specific models with policy-value networks for AlphaGo-style play:
- Policy head: Move probability distribution
- Value head: Position evaluation
- Support for 9×9, 13×13, and 19×19 boards
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from typing import Tuple, Optional, Dict, Any
from prometheus.models.architectures import residual_block


def build_go_policy_value_network(
    board_size: int = 19,
    num_input_planes: int = 3,
    filters: Tuple[int, ...] = (128, 128, 128, 128),
    residual_blocks: int = 10,
    dropout_rate: float = 0.3,
    name: str = "GoPolicyValue"
) -> keras.Model:
    """
    Build a policy-value network for Go (AlphaGo/AlphaZero style).

    Architecture:
        - Shared convolutional layers (ResNet blocks)
        - Policy head: Outputs move probabilities for all board positions + pass
        - Value head: Outputs position evaluation (-1 to +1)

    Args:
        board_size: Size of Go board (9, 13, or 19)
        num_input_planes: Number of input feature planes (default 3: black, white, current_player)
        filters: Number of filters in shared layers
        residual_blocks: Number of residual blocks
        dropout_rate: Dropout rate
        name: Model name

    Returns:
        Keras Model with two outputs: (policy, value)
        - policy: shape (board_size*board_size + 1,) - probabilities for all moves + pass
        - value: shape (1,) - position evaluation from -1 (black wins) to +1 (white wins)

    Example:
        >>> model = build_go_policy_value_network(board_size=19)
        >>> state = np.random.random((1, 19, 19, 3))
        >>> policy, value = model.predict(state)
        >>> policy.shape  # (1, 362)  - 19*19 + 1 for pass
        >>> value.shape   # (1, 1)
    """
    inputs = layers.Input(shape=(board_size, board_size, num_input_planes), name=f"{name}_input")

    # Initial convolution
    x = layers.Conv2D(filters[0], 3, padding='same', name=f"{name}_conv_init")(inputs)
    x = layers.BatchNormalization(name=f"{name}_bn_init")(x)
    x = layers.Activation('relu', name=f"{name}_relu_init")(x)

    # Residual tower (shared between policy and value)
    for i in range(residual_blocks):
        x = residual_block(x, filters[0], kernel_size=3, downsample=False)

    # ==== POLICY HEAD ====
    # Predicts move probabilities
    policy = layers.Conv2D(32, 1, padding='same', name=f"{name}_policy_conv")(x)
    policy = layers.BatchNormalization(name=f"{name}_policy_bn")(policy)
    policy = layers.Activation('relu', name=f"{name}_policy_relu")(policy)
    policy = layers.Flatten(name=f"{name}_policy_flatten")(policy)

    # Add one extra output for "pass" move
    num_moves = board_size * board_size + 1
    policy_output = layers.Dense(
        num_moves,
        activation='softmax',
        name=f"{name}_policy_output"
    )(policy)

    # ==== VALUE HEAD ====
    # Predicts position evaluation
    value = layers.Conv2D(16, 1, padding='same', name=f"{name}_value_conv")(x)
    value = layers.BatchNormalization(name=f"{name}_value_bn")(value)
    value = layers.Activation('relu', name=f"{name}_value_relu")(value)
    value = layers.Flatten(name=f"{name}_value_flatten")(value)
    value = layers.Dense(128, activation='relu', name=f"{name}_value_fc1")(value)
    value = layers.Dropout(dropout_rate, name=f"{name}_value_dropout")(value)
    value_output = layers.Dense(
        1,
        activation='tanh',  # Range: -1 (black wins) to +1 (white wins)
        name=f"{name}_value_output"
    )(value)

    model = keras.Model(
        inputs=inputs,
        outputs=[policy_output, value_output],
        name=name
    )

    return model


class RandomGoAgent:
    """
    Random Go agent - plays random legal moves.
    Useful as a baseline opponent.
    """

    def __init__(self, board_size: int = 19):
        """Initialize random Go agent."""
        self.board_size = board_size
        self.name = "RandomGoAgent"

    def get_move(self, state: np.ndarray, legal_moves: list, temperature: float = 1.0) -> Tuple[int, int]:
        """
        Get a random legal move.

        Args:
            state: Board state (not used for random agent)
            legal_moves: List of legal moves as (row, col) tuples or ('pass',)
            temperature: Temperature parameter (ignored for random agent, included for API compatibility)

        Returns:
            Random move from legal moves
        """
        if not legal_moves:
            return ('pass',)
        return legal_moves[np.random.randint(len(legal_moves))]

    def evaluate(self, state: np.ndarray) -> float:
        """Random agent has no position evaluation."""
        return 0.0


class StaticGoAgent:
    """
    Static Go Agent: Pre-trained policy-value network with frozen weights.

    This agent:
    - Uses a ResNet-based policy-value network
    - Predicts move probabilities (policy) and position evaluation (value)
    - Has frozen weights (cannot improve online)
    - Serves as baseline for Prometheus comparison

    Attributes:
        model: The policy-value neural network
        board_size: Size of Go board (9, 13, or 19)
        generation: Current generation counter
    """

    def __init__(
        self,
        board_size: int = 19,
        num_input_planes: int = 3,
        architecture_kwargs: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Static Go Agent.

        Args:
            board_size: Size of Go board (9, 13, or 19)
            num_input_planes: Number of input feature planes
            architecture_kwargs: Optional kwargs for network architecture
        """
        self.board_size = board_size
        self.num_input_planes = num_input_planes
        self.generation = 0
        self.name = f"StaticGoAgent_{board_size}x{board_size}"

        # Build policy-value network
        kwargs = architecture_kwargs or {}
        self.model = build_go_policy_value_network(
            board_size=board_size,
            num_input_planes=num_input_planes,
            **kwargs
        )

        # Compile with custom loss for policy-value network
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss={
                f'{self.model.name}_policy_output': 'categorical_crossentropy',
                f'{self.model.name}_value_output': 'mse'
            },
            loss_weights={
                f'{self.model.name}_policy_output': 1.0,
                f'{self.model.name}_value_output': 1.0
            },
            metrics={
                f'{self.model.name}_policy_output': 'accuracy',
                f'{self.model.name}_value_output': 'mae'
            }
        )

        print(f"  📊 Static Go Model ({board_size}×{board_size}): {self.model.count_params():,} parameters")

    def pretrain(
        self,
        X_train: np.ndarray,
        policy_train: np.ndarray,
        value_train: np.ndarray,
        epochs: int = 50,
        batch_size: int = 32,
        verbose: int = 0,
        validation_split: float = 0.15
    ):
        """
        Pre-train the model and freeze weights.

        Args:
            X_train: Training board states (N, board_size, board_size, num_planes)
            policy_train: Training move targets (N, board_size^2 + 1)
            value_train: Training position values (N, 1)
            epochs: Number of training epochs
            batch_size: Batch size
            verbose: Verbosity level
            validation_split: Fraction for validation

        Returns:
            Training history
        """
        print(f"  🔧 Pre-training Static Go Agent ({epochs} epochs)...")

        history = self.model.fit(
            X_train,
            {
                f'{self.model.name}_policy_output': policy_train,
                f'{self.model.name}_value_output': value_train
            },
            epochs=epochs,
            batch_size=batch_size,
            verbose=verbose,
            validation_split=validation_split
        )

        # FREEZE ALL WEIGHTS
        self.model.trainable = False
        print(f"  ❄️  ALL {self.model.count_params():,} weights FROZEN")

        return history

    def predict(self, state: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Predict policy and value for a board state.

        Args:
            state: Board state (board_size, board_size, num_planes) or batch

        Returns:
            (policy, value) tuple:
            - policy: Move probabilities (board_size^2 + 1,)
            - value: Position evaluation scalar
        """
        if state.ndim == 3:
            state = np.expand_dims(state, axis=0)

        policy, value = self.model.predict(state, verbose=0)
        return policy[0], float(value[0, 0])

    def get_move(self, state: np.ndarray, legal_moves: list, temperature: float = 1.0) -> Tuple[int, int]:
        """
        Get best move using policy network.

        Args:
            state: Current board state
            legal_moves: List of legal moves
            temperature: Sampling temperature (1.0 = sample from policy, 0.0 = greedy)

        Returns:
            Selected move (row, col) or ('pass',)
        """
        policy, _ = self.predict(state)

        # Mask illegal moves
        legal_mask = np.zeros(len(policy))
        for move in legal_moves:
            if move == ('pass',):
                legal_mask[-1] = 1.0  # Last index is pass
            else:
                row, col = move
                idx = row * self.board_size + col
                legal_mask[idx] = 1.0

        masked_policy = policy * legal_mask
        masked_policy /= masked_policy.sum() + 1e-8

        # Sample or greedy selection
        if temperature < 0.01:  # Greedy
            move_idx = np.argmax(masked_policy)
        else:  # Temperature sampling
            masked_policy = masked_policy ** (1.0 / temperature)
            masked_policy /= masked_policy.sum()
            move_idx = np.random.choice(len(masked_policy), p=masked_policy)

        # Convert index back to move
        if move_idx == len(policy) - 1:
            return ('pass',)
        else:
            row = move_idx // self.board_size
            col = move_idx % self.board_size
            return (row, col)

    def evaluate(self, state: np.ndarray) -> float:
        """
        Evaluate position using value network.

        Args:
            state: Board state

        Returns:
            Position value from -1 (black wins) to +1 (white wins)
        """
        _, value = self.predict(state)
        return value

    def evolve(self, performance: float):
        """Static agents don't evolve - weights remain frozen."""
        self.generation += 1


class PrometheusGoAgent:
    """
    Prometheus Go Agent: Policy-value network with online learning.

    This agent:
    - Uses same architecture as StaticGoAgent
    - Can improve via online learning from self-play
    - Implements recursive self-improvement
    - Adapts to new positions and strategies

    Attributes:
        model: The policy-value neural network
        board_size: Size of Go board
        generation: Current generation counter
        performance_history: Track performance over time
        games_played: Number of games played
        wins: Number of wins
        losses: Number of losses
        draws: Number of draws
    """

    def __init__(
        self,
        board_size: int = 19,
        num_input_planes: int = 3,
        online_lr: float = 0.0001,
        architecture_kwargs: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Prometheus Go Agent.

        Args:
            board_size: Size of Go board (9, 13, or 19)
            num_input_planes: Number of input feature planes
            online_lr: Learning rate for online learning
            architecture_kwargs: Optional kwargs for network architecture
        """
        self.board_size = board_size
        self.num_input_planes = num_input_planes
        self.generation = 0
        self.performance_history = []
        self.games_played = 0
        self.wins = 0
        self.losses = 0
        self.draws = 0
        self.name = f"PrometheusGoAgent_{board_size}x{board_size}"

        # Build policy-value network (same as Static)
        kwargs = architecture_kwargs or {}
        self.model = build_go_policy_value_network(
            board_size=board_size,
            num_input_planes=num_input_planes,
            **kwargs
        )

        # Compile with lower learning rate for online learning
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=online_lr),
            loss={
                f'{self.model.name}_policy_output': 'categorical_crossentropy',
                f'{self.model.name}_value_output': 'mse'
            },
            loss_weights={
                f'{self.model.name}_policy_output': 1.0,
                f'{self.model.name}_value_output': 1.0
            },
            metrics={
                f'{self.model.name}_policy_output': 'accuracy',
                f'{self.model.name}_value_output': 'mae'
            }
        )

        print(f"  📊 Prometheus Go Model ({board_size}×{board_size}): {self.model.count_params():,} parameters")

    def pretrain(
        self,
        X_train: np.ndarray,
        policy_train: np.ndarray,
        value_train: np.ndarray,
        epochs: int = 50,
        batch_size: int = 32,
        verbose: int = 0,
        validation_split: float = 0.15
    ):
        """
        Pre-train the model (weights remain trainable).

        Args:
            X_train: Training board states
            policy_train: Training move targets
            value_train: Training position values
            epochs: Number of training epochs
            batch_size: Batch size
            verbose: Verbosity level
            validation_split: Fraction for validation

        Returns:
            Training history
        """
        print(f"  🔧 Pre-training Prometheus Go Agent ({epochs} epochs)...")

        history = self.model.fit(
            X_train,
            {
                f'{self.model.name}_policy_output': policy_train,
                f'{self.model.name}_value_output': value_train
            },
            epochs=epochs,
            batch_size=batch_size,
            verbose=verbose,
            validation_split=validation_split
        )

        print(f"  🔓 {self.model.count_params():,} weights ready for online learning")

        return history

    def predict(self, state: np.ndarray) -> Tuple[np.ndarray, float]:
        """Predict policy and value for a board state."""
        if state.ndim == 3:
            state = np.expand_dims(state, axis=0)

        policy, value = self.model.predict(state, verbose=0)
        return policy[0], float(value[0, 0])

    def get_move(self, state: np.ndarray, legal_moves: list, temperature: float = 1.0) -> Tuple[int, int]:
        """Get best move using policy network with legal move masking."""
        policy, _ = self.predict(state)

        # Mask illegal moves
        legal_mask = np.zeros(len(policy))
        for move in legal_moves:
            if move == ('pass',):
                legal_mask[-1] = 1.0
            else:
                row, col = move
                idx = row * self.board_size + col
                legal_mask[idx] = 1.0

        masked_policy = policy * legal_mask
        masked_policy /= masked_policy.sum() + 1e-8

        # Sample or greedy selection
        if temperature < 0.01:
            move_idx = np.argmax(masked_policy)
        else:
            masked_policy = masked_policy ** (1.0 / temperature)
            masked_policy /= masked_policy.sum()
            move_idx = np.random.choice(len(masked_policy), p=masked_policy)

        # Convert index back to move
        if move_idx == len(policy) - 1:
            return ('pass',)
        else:
            row = move_idx // self.board_size
            col = move_idx % self.board_size
            return (row, col)

    def evaluate(self, state: np.ndarray) -> float:
        """Evaluate position using value network."""
        _, value = self.predict(state)
        self.performance_history.append(value)
        return value

    def online_train(
        self,
        X_train: np.ndarray,
        policy_train: np.ndarray,
        value_train: np.ndarray,
        epochs: int = 3,
        batch_size: int = 32,
        verbose: int = 0
    ):
        """
        Online learning: Continue training on new game data.

        Args:
            X_train: New board states from recent games
            policy_train: Improved policy targets
            value_train: Actual game outcomes
            epochs: Number of online epochs
            batch_size: Batch size
            verbose: Verbosity level

        Returns:
            Training history
        """
        history = self.model.fit(
            X_train,
            {
                f'{self.model.name}_policy_output': policy_train,
                f'{self.model.name}_value_output': value_train
            },
            epochs=epochs,
            batch_size=batch_size,
            verbose=verbose,
            validation_split=0.1
        )
        return history

    def evolve(
        self,
        performance: float,
        X_new: np.ndarray,
        policy_new: np.ndarray,
        value_new: np.ndarray,
        online_epochs: int = 3
    ):
        """
        Prometheus evolves: Adapt to new game data via online learning.

        This is the core of recursive self-improvement:
        1. Play games against opponents
        2. Collect (state, policy, value) tuples
        3. Train on this data to improve
        4. Repeat

        Args:
            performance: Current win rate (for tracking)
            X_new: New board states
            policy_new: Improved policy targets (e.g., from MCTS)
            value_new: Actual game outcomes
            online_epochs: Number of epochs for adaptation
        """
        self.generation += 1
        print(f"  🔄 Generation {self.generation}: Evolving on {len(X_new)} positions...")

        self.online_train(X_new, policy_new, value_new, epochs=online_epochs, verbose=0)

        # Update statistics
        self.performance_history.append(performance)

    def record_game_result(self, result: str):
        """
        Record game result for statistics tracking.

        Args:
            result: 'win', 'loss', or 'draw'
        """
        self.games_played += 1
        if result == 'win':
            self.wins += 1
        elif result == 'loss':
            self.losses += 1
        elif result == 'draw':
            self.draws += 1

    def get_statistics(self) -> Dict[str, Any]:
        """Get agent statistics."""
        win_rate = self.wins / max(self.games_played, 1)
        return {
            'generation': self.generation,
            'games_played': self.games_played,
            'wins': self.wins,
            'losses': self.losses,
            'draws': self.draws,
            'win_rate': win_rate,
            'avg_value': np.mean(self.performance_history) if self.performance_history else 0.0
        }
