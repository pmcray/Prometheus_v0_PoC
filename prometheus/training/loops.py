"""
Prometheus Training Utilities

This module contains training loop utilities and helper functions:
- Pretrain loop with validation
- Online learning loop
- Metric tracking and logging
- Learning rate scheduling
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
from typing import Dict, List, Optional, Callable
import time


class TrainingMetrics:
    """
    Tracks training metrics across epochs and generations/rounds/cycles.

    Attributes:
        history: Dictionary of metric lists
    """

    def __init__(self):
        self.history = {
            'loss': [],
            'accuracy': [],
            'val_loss': [],
            'val_accuracy': [],
            'epoch_times': []
        }

    def update(self, metrics: Dict[str, float]):
        """Update metrics with new values."""
        for key, value in metrics.items():
            if key in self.history:
                self.history[key].append(value)

    def get_recent_average(self, metric: str, n: int = 3) -> float:
        """Get average of last n values for a metric."""
        if metric not in self.history or not self.history[metric]:
            return 0.0
        recent = self.history[metric][-n:]
        return np.mean(recent)

    def get_trend(self, metric: str, window: int = 5) -> str:
        """
        Determine trend direction for a metric.

        Returns:
            'improving', 'degrading', or 'stable'
        """
        if metric not in self.history or len(self.history[metric]) < window:
            return 'stable'

        recent = self.history[metric][-window:]
        slope = np.polyfit(range(len(recent)), recent, 1)[0]

        # For loss, negative slope is improving
        # For accuracy, positive slope is improving
        if 'loss' in metric.lower():
            if slope < -0.01:
                return 'improving'
            elif slope > 0.01:
                return 'degrading'
        else:  # accuracy
            if slope > 0.01:
                return 'improving'
            elif slope < -0.01:
                return 'degrading'

        return 'stable'


def pretrain_model(
    model: keras.Model,
    X_train: np.ndarray,
    y_train: np.ndarray,
    epochs: int = 20,
    batch_size: int = 64,
    validation_split: float = 0.15,
    verbose: int = 1,
    callbacks: Optional[List[keras.callbacks.Callback]] = None
) -> keras.callbacks.History:
    """
    Pre-train a model on initial training data.

    Args:
        model: Keras model to train
        X_train: Training data
        y_train: Training labels
        epochs: Number of training epochs
        batch_size: Batch size
        validation_split: Fraction of data for validation
        verbose: Verbosity level (0=silent, 1=progress bar, 2=one line per epoch)
        callbacks: Optional list of Keras callbacks

    Returns:
        Training history

    Example:
        >>> from prometheus.models.architectures import build_resnet
        >>> model = build_resnet((64, 64, 1), num_classes=8)
        >>> history = pretrain_model(model, X_train, y_train, epochs=20)
    """
    if callbacks is None:
        callbacks = []

    print(f"  🔧 Pre-training model ({epochs} epochs, {len(X_train)} samples)...")
    start_time = time.time()

    history = model.fit(
        X_train, y_train,
        epochs=epochs,
        batch_size=batch_size,
        validation_split=validation_split,
        verbose=verbose,
        callbacks=callbacks
    )

    elapsed = time.time() - start_time
    print(f"  ✅ Pre-training complete ({elapsed/60:.1f} minutes)")

    # Print final metrics
    final_acc = history.history['accuracy'][-1]
    final_val_acc = history.history.get('val_accuracy', [0])[-1]
    print(f"     Final train accuracy: {final_acc*100:.1f}%")
    print(f"     Final val accuracy:   {final_val_acc*100:.1f}%")

    return history


def online_train_model(
    model: keras.Model,
    X_train: np.ndarray,
    y_train: np.ndarray,
    epochs: int = 5,
    batch_size: int = 64,
    validation_split: float = 0.15,
    verbose: int = 0,
    callbacks: Optional[List[keras.callbacks.Callback]] = None
) -> keras.callbacks.History:
    """
    Online training: Continue training on new data.

    This is used during recursive self-improvement to adapt to:
    - Distribution shifts
    - New task types
    - Evolving patterns

    Args:
        model: Keras model to train
        X_train: New training data
        y_train: New training labels
        epochs: Number of online epochs
        batch_size: Batch size
        validation_split: Fraction of data for validation
        verbose: Verbosity level
        callbacks: Optional list of Keras callbacks

    Returns:
        Training history

    Example:
        >>> # After pre-training, adapt to new distribution
        >>> X_new, y_new = generator.generate_batch(300, new_distribution)
        >>> history = online_train_model(model, X_new, y_new, epochs=5)
    """
    history = model.fit(
        X_train, y_train,
        epochs=epochs,
        batch_size=batch_size,
        validation_split=validation_split,
        verbose=verbose,
        callbacks=callbacks
    )

    return history


def evaluate_model(
    model: keras.Model,
    X_test: np.ndarray,
    y_test: np.ndarray,
    batch_size: int = 64,
    verbose: int = 0
) -> Dict[str, float]:
    """
    Evaluate model on test data.

    Args:
        model: Keras model
        X_test: Test data
        y_test: Test labels
        batch_size: Batch size
        verbose: Verbosity level

    Returns:
        Dictionary with 'loss' and 'accuracy' keys
    """
    loss, accuracy = model.evaluate(X_test, y_test, batch_size=batch_size, verbose=verbose)

    return {
        'loss': float(loss),
        'accuracy': float(accuracy)
    }


def freeze_model(model: keras.Model, verbose: bool = True) -> keras.Model:
    """
    Freeze all model weights (for Static Agent).

    Args:
        model: Keras model
        verbose: Print confirmation message

    Returns:
        Model with frozen weights
    """
    model.trainable = False

    if verbose:
        print(f"  ❄️  ALL {model.count_params():,} weights FROZEN")

    return model


def unfreeze_model(model: keras.Model, verbose: bool = True) -> keras.Model:
    """
    Unfreeze all model weights (for Prometheus Agent).

    Args:
        model: Keras model
        verbose: Print confirmation message

    Returns:
        Model with trainable weights
    """
    model.trainable = True

    if verbose:
        print(f"  🔓 {model.count_params():,} weights ready for online learning")

    return model


class LearningRateScheduler:
    """
    Simple learning rate scheduler for online learning.

    Supports:
    - Constant learning rate
    - Exponential decay
    - Step decay
    - Performance-based adaptation
    """

    def __init__(
        self,
        initial_lr: float = 0.001,
        schedule_type: str = 'constant',
        decay_rate: float = 0.96,
        decay_steps: int = 10
    ):
        """
        Initialize learning rate scheduler.

        Args:
            initial_lr: Initial learning rate
            schedule_type: 'constant', 'exponential', 'step', or 'adaptive'
            decay_rate: Decay rate (for exponential/step)
            decay_steps: Steps between decay (for step)
        """
        self.initial_lr = initial_lr
        self.schedule_type = schedule_type
        self.decay_rate = decay_rate
        self.decay_steps = decay_steps
        self.current_step = 0

    def get_lr(self, performance: Optional[float] = None) -> float:
        """
        Get learning rate for current step.

        Args:
            performance: Current performance (for adaptive schedule)

        Returns:
            Learning rate
        """
        if self.schedule_type == 'constant':
            return self.initial_lr

        elif self.schedule_type == 'exponential':
            return self.initial_lr * (self.decay_rate ** self.current_step)

        elif self.schedule_type == 'step':
            decay_factor = self.current_step // self.decay_steps
            return self.initial_lr * (self.decay_rate ** decay_factor)

        elif self.schedule_type == 'adaptive':
            if performance is None:
                return self.initial_lr

            # Increase LR if performance is poor, decrease if good
            if performance < 0.6:
                return min(self.initial_lr * 2.0, 0.01)
            elif performance > 0.85:
                return self.initial_lr * 0.8
            else:
                return self.initial_lr

        return self.initial_lr

    def step(self):
        """Increment step counter."""
        self.current_step += 1

    def reset(self):
        """Reset step counter."""
        self.current_step = 0


class EarlyStopping:
    """
    Early stopping with patience for training.

    Stops training if validation metric doesn't improve for patience epochs.
    """

    def __init__(
        self,
        patience: int = 10,
        min_delta: float = 0.001,
        mode: str = 'max',
        verbose: bool = True
    ):
        """
        Initialize early stopping.

        Args:
            patience: Number of epochs to wait for improvement
            min_delta: Minimum change to qualify as improvement
            mode: 'max' for metrics to maximize (accuracy), 'min' for minimize (loss)
            verbose: Print messages
        """
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.verbose = verbose

        self.best_value = float('-inf') if mode == 'max' else float('inf')
        self.wait = 0
        self.stopped_epoch = 0

    def should_stop(self, current_value: float, epoch: int) -> bool:
        """
        Check if training should stop.

        Args:
            current_value: Current metric value
            epoch: Current epoch

        Returns:
            True if should stop, False otherwise
        """
        if self.mode == 'max':
            improved = current_value > self.best_value + self.min_delta
        else:  # min
            improved = current_value < self.best_value - self.min_delta

        if improved:
            self.best_value = current_value
            self.wait = 0
        else:
            self.wait += 1

        if self.wait >= self.patience:
            self.stopped_epoch = epoch
            if self.verbose:
                print(f"\n  ⏹️  Early stopping triggered at epoch {epoch}")
                print(f"     Best value: {self.best_value:.4f}")
            return True

        return False

    def reset(self):
        """Reset early stopping state."""
        self.best_value = float('-inf') if self.mode == 'max' else float('inf')
        self.wait = 0
        self.stopped_epoch = 0


def compute_performance_gap(
    static_results: List[float],
    prometheus_results: List[float]
) -> Dict[str, float]:
    """
    Compute performance gap between Static and Prometheus agents.

    Args:
        static_results: List of static agent accuracies (%)
        prometheus_results: List of Prometheus agent accuracies (%)

    Returns:
        Dictionary with gap statistics
    """
    static_results = np.array(static_results)
    prometheus_results = np.array(prometheus_results)

    gap = prometheus_results - static_results

    return {
        'initial_gap': float(gap[0]),
        'final_gap': float(gap[-1]),
        'average_gap': float(np.mean(gap)),
        'max_gap': float(np.max(gap)),
        'min_gap': float(np.min(gap)),
        'gap_trend': 'widening' if gap[-1] > gap[0] else 'narrowing',
        'prometheus_advantage': float(np.mean(gap) > 5.0)  # >5% advantage
    }


def print_performance_summary(
    static_results: List[float],
    prometheus_results: List[float],
    experiment_name: str = "Experiment"
):
    """
    Print formatted performance summary.

    Args:
        static_results: List of static agent accuracies (%)
        prometheus_results: List of Prometheus agent accuracies (%)
        experiment_name: Name of experiment for title
    """
    print("\n" + "="*70)
    print(f"📊 {experiment_name.upper()} RESULTS")
    print("="*70)

    print(f"\n🔵 Static (Frozen Weights):")
    print(f"  Initial:  {static_results[0]:.1f}%")
    print(f"  Final:    {static_results[-1]:.1f}%")
    print(f"  Change:   {static_results[-1] - static_results[0]:+.1f}%")
    print(f"  Average:  {np.mean(static_results):.1f}%")

    print(f"\n🟢 Prometheus (Online Learning):")
    print(f"  Initial:  {prometheus_results[0]:.1f}%")
    print(f"  Final:    {prometheus_results[-1]:.1f}%")
    print(f"  Change:   {prometheus_results[-1] - prometheus_results[0]:+.1f}%")
    print(f"  Average:  {np.mean(prometheus_results):.1f}%")

    gap = compute_performance_gap(static_results, prometheus_results)

    print(f"\n🎯 Prometheus Advantage:")
    print(f"  Initial Gap:  {gap['initial_gap']:+.1f}%")
    print(f"  Final Gap:    {gap['final_gap']:+.1f}%")
    print(f"  Average Gap:  {gap['average_gap']:+.1f}%")
    print(f"  Trend:        {gap['gap_trend'].capitalize()}")

    print(f"\n✅ Conclusion:")
    if gap['average_gap'] > 10:
        print(f"  🚀 Prometheus shows STRONG advantage ({gap['average_gap']:+.1f}%)")
    elif gap['average_gap'] > 5:
        print(f"  📈 Prometheus shows CLEAR advantage ({gap['average_gap']:+.1f}%)")
    elif gap['average_gap'] > 0:
        print(f"  ✓ Prometheus shows modest advantage ({gap['average_gap']:+.1f}%)")
    else:
        print(f"  ⚠️  No clear advantage detected")

    print("="*70)
