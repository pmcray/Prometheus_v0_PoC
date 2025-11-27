"""
Transfer Learning Utilities

Enable knowledge transfer across:
- Board sizes (9x9 → 13x13 → 19x19 Go)
- Domains (visual patterns → games)
- Games (chess → Go via abstract features)

Usage:
    # Transfer from 9x9 to 19x19
    transfer = BoardSizeTransfer()
    large_model = transfer.transfer(small_model, source_size=9, target_size=19)

    # Transfer from chess to Go
    domain_transfer = DomainTransfer()
    go_model = domain_transfer.transfer(chess_model, target_domain='go')
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
from typing import Tuple, Optional, Dict, Any


class BoardSizeTransfer:
    """
    Transfer Go models between different board sizes.

    Strategy:
    - Copy shared convolutional layers
    - Reinitialize size-dependent layers (final policy head)
    - Fine-tune on target board size
    """

    def __init__(self):
        """Initialize board size transfer."""
        pass

    def transfer(self,
                source_model: keras.Model,
                source_size: int,
                target_size: int,
                num_filters: int = 128) -> keras.Model:
        """
        Transfer model to different board size.

        Args:
            source_model: Trained model for source size
            source_size: Source board size (e.g., 9)
            target_size: Target board size (e.g., 19)
            num_filters: Number of convolutional filters

        Returns:
            New model for target size with transferred weights
        """
        print(f"Transferring model: {source_size}x{source_size} → {target_size}x{target_size}")

        # Create target model architecture
        from prometheus.models.go_models import create_go_policy_value_network

        target_model = create_go_policy_value_network(
            board_size=target_size,
            num_filters=num_filters
        )

        # Transfer convolutional layers (size-independent)
        source_layers = {layer.name: layer for layer in source_model.layers}
        target_layers = {layer.name: layer for layer in target_model.layers}

        transferred = 0
        skipped = 0

        for layer_name, target_layer in target_layers.items():
            if layer_name in source_layers:
                source_layer = source_layers[layer_name]

                # Only transfer if shapes match
                if self._weights_compatible(source_layer, target_layer):
                    try:
                        target_layer.set_weights(source_layer.get_weights())
                        transferred += 1
                        print(f"  ✓ Transferred: {layer_name}")
                    except Exception as e:
                        print(f"  ✗ Failed to transfer {layer_name}: {e}")
                        skipped += 1
                else:
                    print(f"  ○ Skipped (incompatible): {layer_name}")
                    skipped += 1

        print(f"\nTransfer complete:")
        print(f"  Transferred: {transferred} layers")
        print(f"  Skipped: {skipped} layers")
        print(f"  Total: {len(target_layers)} layers")

        return target_model

    def _weights_compatible(self, source_layer, target_layer) -> bool:
        """
        Check if layer weights are compatible for transfer.

        Args:
            source_layer: Source layer
            target_layer: Target layer

        Returns:
            True if compatible
        """
        source_weights = source_layer.get_weights()
        target_weights = target_layer.get_weights()

        if len(source_weights) != len(target_weights):
            return False

        for sw, tw in zip(source_weights, target_weights):
            if sw.shape != tw.shape:
                return False

        return True


class DomainTransfer:
    """
    Transfer knowledge between different domains.

    Strategies:
    - Feature extraction: Use convolutional layers as feature extractor
    - Representation learning: Transfer abstract patterns
    - Meta-learning: Transfer learning strategies
    """

    def __init__(self):
        """Initialize domain transfer."""
        pass

    def transfer_conv_features(self,
                              source_model: keras.Model,
                              target_input_shape: Tuple,
                              target_output_shape: int,
                              freeze_features: bool = True) -> keras.Model:
        """
        Transfer convolutional feature extractor to new domain.

        Args:
            source_model: Source domain model
            target_input_shape: Target domain input shape
            target_output_shape: Target domain output size
            freeze_features: Freeze transferred layers initially

        Returns:
            New model with transferred features
        """
        print(f"Transferring features to new domain...")

        # Extract convolutional backbone
        conv_layers = []
        for layer in source_model.layers:
            if isinstance(layer, (keras.layers.Conv2D,
                                keras.layers.BatchNormalization,
                                keras.layers.Activation,
                                keras.layers.MaxPooling2D)):
                conv_layers.append(layer)

        # Build new model
        inputs = keras.layers.Input(shape=target_input_shape)
        x = inputs

        # Add transferred conv layers
        for layer in conv_layers:
            try:
                x = layer(x)
                if freeze_features:
                    layer.trainable = False
            except Exception as e:
                print(f"  ✗ Could not transfer layer {layer.name}: {e}")
                break

        # Add new task-specific head
        x = keras.layers.GlobalAveragePooling2D()(x)
        x = keras.layers.Dense(256, activation='relu')(x)
        x = keras.layers.Dropout(0.3)(x)
        outputs = keras.layers.Dense(target_output_shape, activation='softmax')(x)

        model = keras.Model(inputs=inputs, outputs=outputs)

        frozen = sum(1 for layer in model.layers if not layer.trainable)
        total = len(model.layers)

        print(f"  ✓ Created model with {total} layers")
        print(f"  ✓ Frozen: {frozen} layers")
        print(f"  ✓ Trainable: {total - frozen} layers")

        return model

    def progressive_unfreezing(self,
                              model: keras.Model,
                              unfreeze_schedule: Optional[Dict[int, int]] = None):
        """
        Progressively unfreeze layers during training.

        Args:
            model: Model to unfreeze
            unfreeze_schedule: Dict mapping epoch -> num_layers_to_unfreeze
        """
        if unfreeze_schedule is None:
            # Default schedule
            unfreeze_schedule = {
                0: 0,    # Start all frozen
                10: 5,   # After 10 epochs, unfreeze last 5 layers
                20: 10,  # After 20 epochs, unfreeze last 10 layers
                30: -1   # After 30 epochs, unfreeze all
            }

        return unfreeze_schedule


class CrossGameTransfer:
    """
    Transfer knowledge between different games.

    Uses abstract board representation:
    - Spatial features (conv layers)
    - Strategic patterns (mid-level features)
    - Evaluation concepts (value prediction)
    """

    def __init__(self):
        """Initialize cross-game transfer."""
        pass

    def create_universal_encoder(self,
                                input_shape: Tuple,
                                num_filters: int = 64) -> keras.Model:
        """
        Create universal board game encoder.

        Args:
            input_shape: Input shape (H, W, C)
            num_filters: Number of filters

        Returns:
            Encoder model
        """
        inputs = keras.layers.Input(shape=input_shape)

        # Convolutional backbone (game-agnostic)
        x = keras.layers.Conv2D(num_filters, 3, padding='same')(inputs)
        x = keras.layers.BatchNormalization()(x)
        x = keras.layers.Activation('relu')(x)

        for i in range(3):
            # Residual blocks
            shortcut = x

            x = keras.layers.Conv2D(num_filters, 3, padding='same')(x)
            x = keras.layers.BatchNormalization()(x)
            x = keras.layers.Activation('relu')(x)

            x = keras.layers.Conv2D(num_filters, 3, padding='same')(x)
            x = keras.layers.BatchNormalization()(x)

            x = keras.layers.Add()([shortcut, x])
            x = keras.layers.Activation('relu')(x)

        # Global features
        features = keras.layers.GlobalAveragePooling2D()(x)

        encoder = keras.Model(inputs=inputs, outputs=features,
                            name='universal_encoder')

        return encoder

    def transfer_chess_to_go(self,
                           chess_model: keras.Model,
                           board_size: int = 9) -> keras.Model:
        """
        Transfer chess model to Go.

        Args:
            chess_model: Trained chess model
            board_size: Go board size

        Returns:
            Go model with transferred features
        """
        print("Transferring Chess → Go...")

        # Extract shared convolutional features
        conv_layers = []
        for layer in chess_model.layers:
            if isinstance(layer, (keras.layers.Conv2D,
                                keras.layers.BatchNormalization,
                                keras.layers.Activation)):
                conv_layers.append(layer)
                if len(conv_layers) >= 10:  # Limit to first N layers
                    break

        # Create Go model
        from prometheus.models.go_models import create_go_policy_value_network

        go_model = create_go_policy_value_network(board_size=board_size)

        # Transfer compatible layers
        transferred = 0
        for source_layer in conv_layers:
            for target_layer in go_model.layers:
                if (source_layer.name == target_layer.name and
                    type(source_layer) == type(target_layer)):
                    try:
                        if len(source_layer.get_weights()) > 0:
                            target_layer.set_weights(source_layer.get_weights())
                            transferred += 1
                            print(f"  ✓ {source_layer.name}")
                    except:
                        pass

        print(f"Transferred {transferred} layers")

        return go_model


class FineTuner:
    """
    Fine-tuning utilities for transferred models.

    Strategies:
    - Low learning rate fine-tuning
    - Progressive layer unfreezing
    - Discriminative learning rates
    """

    def __init__(self, model: keras.Model):
        """
        Initialize fine-tuner.

        Args:
            model: Model to fine-tune
        """
        self.model = model

    def configure_fine_tuning(self,
                            base_lr: float = 1e-5,
                            unfreeze_from_layer: Optional[int] = None):
        """
        Configure model for fine-tuning.

        Args:
            base_lr: Base learning rate (should be low)
            unfreeze_from_layer: Unfreeze layers from this index
        """
        # Unfreeze specified layers
        if unfreeze_from_layer is not None:
            for i, layer in enumerate(self.model.layers):
                layer.trainable = (i >= unfreeze_from_layer)

        # Compile with low learning rate
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=base_lr),
            loss=['categorical_crossentropy', 'mse'],
            metrics=['accuracy']
        )

        trainable = sum(1 for layer in self.model.layers if layer.trainable)
        total = len(self.model.layers)

        print(f"Fine-tuning configuration:")
        print(f"  Learning rate: {base_lr}")
        print(f"  Trainable layers: {trainable}/{total}")

    def gradual_unfreezing(self,
                          X_train, y_train,
                          epochs_per_stage: int = 10,
                          num_stages: int = 3):
        """
        Train with gradual layer unfreezing.

        Args:
            X_train: Training data
            y_train: Training labels
            epochs_per_stage: Epochs per unfreezing stage
            num_stages: Number of unfreezing stages

        Returns:
            Training history
        """
        total_layers = len(self.model.layers)
        layers_per_stage = total_layers // num_stages

        histories = []

        for stage in range(num_stages):
            unfreeze_from = total_layers - (stage + 1) * layers_per_stage

            print(f"\nStage {stage + 1}/{num_stages}")
            print(f"Unfreezing from layer {unfreeze_from}")

            # Unfreeze layers
            for i, layer in enumerate(self.model.layers):
                layer.trainable = (i >= unfreeze_from)

            # Train
            history = self.model.fit(
                X_train, y_train,
                epochs=epochs_per_stage,
                validation_split=0.2,
                verbose=1
            )

            histories.append(history)

        return histories


class KnowledgeDistillation:
    """
    Transfer knowledge via distillation.

    Teacher model trains student model:
    - Soft targets (teacher predictions)
    - Dark knowledge (uncertainty information)
    - Compressed models (smaller student)
    """

    def __init__(self, teacher_model: keras.Model, temperature: float = 3.0):
        """
        Initialize knowledge distillation.

        Args:
            teacher_model: Large trained model (teacher)
            temperature: Distillation temperature (higher = softer)
        """
        self.teacher = teacher_model
        self.temperature = temperature

    def create_student(self,
                      input_shape: Tuple,
                      num_classes: int,
                      compression_factor: float = 0.5) -> keras.Model:
        """
        Create smaller student model.

        Args:
            input_shape: Input shape
            num_classes: Number of output classes
            compression_factor: Size relative to teacher (0-1)

        Returns:
            Student model
        """
        # Count teacher parameters
        teacher_params = self.teacher.count_params()
        target_params = int(teacher_params * compression_factor)

        print(f"Creating student model:")
        print(f"  Teacher parameters: {teacher_params:,}")
        print(f"  Target parameters: {target_params:,}")
        print(f"  Compression: {compression_factor:.1%}")

        # Build smaller architecture
        # (Simplified - would need domain-specific implementation)
        inputs = keras.layers.Input(shape=input_shape)
        x = keras.layers.Conv2D(64, 3, padding='same', activation='relu')(inputs)
        x = keras.layers.MaxPooling2D()(x)
        x = keras.layers.Conv2D(32, 3, padding='same', activation='relu')(x)
        x = keras.layers.GlobalAveragePooling2D()(x)
        outputs = keras.layers.Dense(num_classes, activation='softmax')(x)

        student = keras.Model(inputs=inputs, outputs=outputs)

        print(f"  Student parameters: {student.count_params():,}")

        return student

    def distill(self,
               student_model: keras.Model,
               X_train, y_train,
               epochs: int = 50,
               alpha: float = 0.7):
        """
        Train student via distillation.

        Args:
            student_model: Student model to train
            X_train: Training data
            y_train: Training labels (hard targets)
            epochs: Training epochs
            alpha: Weight for soft targets vs hard targets

        Returns:
            Trained student model
        """
        print("\nKnowledge Distillation Training:")
        print(f"  Temperature: {self.temperature}")
        print(f"  Alpha (soft weight): {alpha}")

        # Get teacher predictions (soft targets)
        teacher_predictions = self.teacher.predict(X_train, verbose=0)

        # Custom loss combining soft and hard targets
        def distillation_loss(y_true, y_pred):
            # Hard loss (regular cross-entropy)
            hard_loss = keras.losses.categorical_crossentropy(y_true, y_pred)

            # Soft loss (KL divergence with temperature scaling)
            teacher_soft = tf.nn.softmax(teacher_predictions / self.temperature)
            student_soft = tf.nn.softmax(y_pred / self.temperature)
            soft_loss = keras.losses.kullback_leibler_divergence(
                teacher_soft, student_soft
            )

            # Combined loss
            return alpha * soft_loss + (1 - alpha) * hard_loss

        # Compile and train
        student_model.compile(
            optimizer='adam',
            loss=distillation_loss,
            metrics=['accuracy']
        )

        history = student_model.fit(
            X_train, y_train,
            epochs=epochs,
            validation_split=0.2,
            verbose=1
        )

        return student_model, history
