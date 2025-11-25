"""
Prometheus Neural Network Architectures

This module contains reusable model architectures for the Prometheus experiments:
- ResNet blocks with skip connections
- Static agents (frozen weights)
- Prometheus agents (online learning)
- Model builders for different input sizes
"""

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from typing import Tuple, Optional


def residual_block(x: tf.Tensor, filters: int, kernel_size: int = 3, downsample: bool = False) -> tf.Tensor:
    """
    Residual block with skip connection (He et al., 2016).

    Args:
        x: Input tensor
        filters: Number of convolutional filters
        kernel_size: Size of convolutional kernels
        downsample: Whether to downsample with stride=2

    Returns:
        Output tensor with residual connection
    """
    shortcut = x
    stride = 2 if downsample else 1

    # Main path
    y = layers.Conv2D(filters, kernel_size, strides=stride, padding='same')(x)
    y = layers.BatchNormalization()(y)
    y = layers.Activation('relu')(y)

    y = layers.Conv2D(filters, kernel_size, padding='same')(y)
    y = layers.BatchNormalization()(y)

    # Shortcut path - match dimensions if needed
    if downsample or shortcut.shape[-1] != filters:
        shortcut = layers.Conv2D(filters, 1, strides=stride, padding='same')(shortcut)
        shortcut = layers.BatchNormalization()(shortcut)

    # Add skip connection
    y = layers.Add()([y, shortcut])
    y = layers.Activation('relu')(y)

    return y


def build_resnet(
    input_shape: Tuple[int, int, int],
    num_classes: int,
    filters: Tuple[int, ...] = (64, 128, 256, 512),
    blocks_per_stage: Tuple[int, ...] = (2, 2, 2, 2),
    dropout_rate: float = 0.5,
    name: str = "ResNet"
) -> keras.Model:
    """
    Build a ResNet-style CNN for classification.

    Args:
        input_shape: Input tensor shape (height, width, channels)
        num_classes: Number of output classes
        filters: Number of filters per stage
        blocks_per_stage: Number of residual blocks per stage
        dropout_rate: Dropout rate before final layer
        name: Model name

    Returns:
        Compiled Keras model

    Example:
        >>> model = build_resnet((64, 64, 1), num_classes=8)
        >>> print(model.summary())
    """
    inputs = layers.Input(shape=input_shape, name=f"{name}_input")

    # Stem: Initial convolution
    x = layers.Conv2D(64, 7, strides=2, padding='same', name=f"{name}_stem_conv")(inputs)
    x = layers.BatchNormalization(name=f"{name}_stem_bn")(x)
    x = layers.Activation('relu', name=f"{name}_stem_relu")(x)
    x = layers.MaxPooling2D(3, strides=2, padding='same', name=f"{name}_stem_pool")(x)

    # Residual stages
    for stage_idx, (num_filters, num_blocks) in enumerate(zip(filters, blocks_per_stage)):
        for block_idx in range(num_blocks):
            downsample = (block_idx == 0 and stage_idx > 0)
            x = residual_block(x, num_filters, downsample=downsample)

    # Head: Global pooling and classification
    x = layers.GlobalAveragePooling2D(name=f"{name}_global_pool")(x)
    x = layers.Dense(512, activation='relu', name=f"{name}_fc1")(x)
    x = layers.Dropout(dropout_rate, name=f"{name}_dropout1")(x)
    x = layers.Dense(256, activation='relu', name=f"{name}_fc2")(x)
    x = layers.Dropout(dropout_rate / 2, name=f"{name}_dropout2")(x)
    outputs = layers.Dense(num_classes, activation='softmax', name=f"{name}_output")(x)

    model = keras.Model(inputs=inputs, outputs=outputs, name=name)
    return model


def build_simple_cnn(
    input_shape: Tuple[int, int, int],
    num_classes: int,
    filters: Tuple[int, ...] = (32, 64, 128),
    dropout_rate: float = 0.4,
    name: str = "SimpleCNN"
) -> keras.Model:
    """
    Build a simple CNN for classification (lighter than ResNet).

    Args:
        input_shape: Input tensor shape (height, width, channels)
        num_classes: Number of output classes
        filters: Number of filters per conv layer
        dropout_rate: Dropout rate
        name: Model name

    Returns:
        Compiled Keras model
    """
    model = keras.Sequential(name=name)

    # Convolutional layers
    for i, num_filters in enumerate(filters):
        model.add(layers.Conv2D(
            num_filters, 3, activation='relu', padding='same',
            input_shape=input_shape if i == 0 else None,
            name=f"{name}_conv{i+1}"
        ))
        model.add(layers.BatchNormalization(name=f"{name}_bn{i+1}"))
        model.add(layers.MaxPooling2D(2, name=f"{name}_pool{i+1}"))

    # Dense layers
    model.add(layers.Flatten(name=f"{name}_flatten"))
    model.add(layers.Dense(256, activation='relu', name=f"{name}_fc1"))
    model.add(layers.Dropout(dropout_rate, name=f"{name}_dropout1"))
    model.add(layers.Dense(128, activation='relu', name=f"{name}_fc2"))
    model.add(layers.Dropout(dropout_rate * 0.75, name=f"{name}_dropout2"))
    model.add(layers.Dense(num_classes, activation='softmax', name=f"{name}_output"))

    return model


class StaticAgent:
    """
    Static Agent: Pre-trained model with frozen weights (Foundation Model analogue).

    Attributes:
        model: The neural network
        generation: Current generation/cycle counter

    Example:
        >>> agent = StaticAgent((64, 64, 1), num_classes=8)
        >>> agent.pretrain(X_train, y_train, epochs=20)
        >>> loss, acc = agent.evaluate(X_test, y_test)
    """

    def __init__(
        self,
        input_shape: Tuple[int, int, int],
        num_classes: int,
        architecture: str = "resnet",
        **kwargs
    ):
        """
        Initialize Static Agent.

        Args:
            input_shape: Input tensor shape
            num_classes: Number of output classes
            architecture: "resnet" or "simple"
            **kwargs: Additional arguments for model builder
        """
        self.input_shape = input_shape
        self.num_classes = num_classes
        self.generation = 0

        # Build model
        if architecture == "resnet":
            self.model = build_resnet(input_shape, num_classes, **kwargs)
        elif architecture == "simple":
            self.model = build_simple_cnn(input_shape, num_classes, **kwargs)
        else:
            raise ValueError(f"Unknown architecture: {architecture}")

        # Compile
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )

        print(f"  📊 Static Model: {self.model.count_params():,} parameters")

    def pretrain(self, X_train, y_train, epochs: int = 20, batch_size: int = 64, verbose: int = 0):
        """
        Pre-train the model and freeze weights.

        Args:
            X_train: Training data
            y_train: Training labels
            epochs: Number of training epochs
            batch_size: Batch size
            verbose: Verbosity level

        Returns:
            Training history
        """
        print(f"  🔧 Pre-training Static Agent ({epochs} epochs)...")

        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            verbose=verbose,
            validation_split=0.15
        )

        # FREEZE ALL WEIGHTS
        self.model.trainable = False
        print(f"  ❄️  ALL {self.model.count_params():,} weights FROZEN")

        return history

    def evaluate(self, X_test, y_test, batch_size: int = 64):
        """Evaluate the model."""
        loss, accuracy = self.model.evaluate(X_test, y_test, verbose=0, batch_size=batch_size)
        return loss, accuracy

    def evolve(self, performance: float):
        """Static agents don't evolve - weights remain frozen."""
        self.generation += 1


class PrometheusAgent:
    """
    Prometheus Agent: Model with online learning (Recursive Self-Improvement).

    Attributes:
        model: The neural network
        generation: Current generation/cycle counter
        performance_history: Track of performance over time

    Example:
        >>> agent = PrometheusAgent((64, 64, 1), num_classes=8)
        >>> agent.pretrain(X_train, y_train, epochs=20)
        >>> loss, acc = agent.evaluate(X_test, y_test)
        >>> agent.evolve(acc, X_new, y_new, online_epochs=5)
    """

    def __init__(
        self,
        input_shape: Tuple[int, int, int],
        num_classes: int,
        architecture: str = "resnet",
        online_lr: float = 0.0003,
        **kwargs
    ):
        """
        Initialize Prometheus Agent.

        Args:
            input_shape: Input tensor shape
            num_classes: Number of output classes
            architecture: "resnet" or "simple"
            online_lr: Learning rate for online learning
            **kwargs: Additional arguments for model builder
        """
        self.input_shape = input_shape
        self.num_classes = num_classes
        self.generation = 0
        self.performance_history = []

        # Build model (same architecture as Static)
        if architecture == "resnet":
            self.model = build_resnet(input_shape, num_classes, **kwargs)
        elif architecture == "simple":
            self.model = build_simple_cnn(input_shape, num_classes, **kwargs)
        else:
            raise ValueError(f"Unknown architecture: {architecture}")

        # Compile with lower learning rate for online learning
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=online_lr),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )

        print(f"  📊 Prometheus Model: {self.model.count_params():,} parameters")

    def pretrain(self, X_train, y_train, epochs: int = 20, batch_size: int = 64, verbose: int = 0):
        """
        Pre-train the model (weights remain trainable).

        Args:
            X_train: Training data
            y_train: Training labels
            epochs: Number of training epochs
            batch_size: Batch size
            verbose: Verbosity level

        Returns:
            Training history
        """
        print(f"  🔧 Pre-training Prometheus Agent ({epochs} epochs)...")

        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            verbose=verbose,
            validation_split=0.15
        )

        print(f"  🔓 {self.model.count_params():,} weights ready for online learning")

        return history

    def evaluate(self, X_test, y_test, batch_size: int = 64):
        """Evaluate the model."""
        loss, accuracy = self.model.evaluate(X_test, y_test, verbose=0, batch_size=batch_size)
        self.performance_history.append(accuracy)
        return loss, accuracy

    def online_train(self, X_train, y_train, epochs: int = 5, batch_size: int = 64, verbose: int = 0):
        """
        Online learning: Continue training on new data.

        Args:
            X_train: New training data
            y_train: New training labels
            epochs: Number of online epochs
            batch_size: Batch size
            verbose: Verbosity level

        Returns:
            Training history
        """
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            verbose=verbose,
            validation_split=0.15
        )
        return history

    def evolve(self, performance: float, X_new, y_new, online_epochs: int = 5):
        """
        Prometheus evolves: Adapt to new data via online learning.

        Args:
            performance: Current performance (for tracking)
            X_new: New training data
            y_new: New training labels
            online_epochs: Number of epochs for adaptation
        """
        self.generation += 1
        self.online_train(X_new, y_new, epochs=online_epochs, verbose=0)
