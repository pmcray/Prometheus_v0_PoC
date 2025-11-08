"""
Prometheus Visualization Utilities

This module contains plotting functions for the Prometheus experiments:
- Performance comparison plots
- Distribution shift annotations
- Advantage gap visualization
- Training progress plots
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import List, Optional, Dict, Tuple


def plot_performance_comparison(
    static_results: List[float],
    prometheus_results: List[float],
    title: str = "Performance Comparison",
    xlabel: str = "Generation",
    save_path: Optional[str] = None,
    show_distribution_shifts: Optional[List[int]] = None
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Plot performance comparison between Static and Prometheus agents.

    Args:
        static_results: List of static agent accuracies (%)
        prometheus_results: List of Prometheus agent accuracies (%)
        title: Plot title
        xlabel: X-axis label
        save_path: Optional path to save figure
        show_distribution_shifts: Optional list of indices where distribution shifts occur

    Returns:
        Tuple of (figure, axes)

    Example:
        >>> fig, ax = plot_performance_comparison(
        ...     static_results=[92, 85, 78, 68],
        ...     prometheus_results=[92, 88, 86, 86],
        ...     title="Intelligence Explosion",
        ...     xlabel="Generation"
        ... )
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))

    x_axis = np.arange(len(static_results))

    # === LEFT: Performance Curves ===
    ax1.plot(x_axis, static_results, 'b-o', linewidth=3, markersize=10,
             label='Static (Frozen Weights)', alpha=0.7)
    ax1.plot(x_axis, prometheus_results, 'g-o', linewidth=3, markersize=10,
             label='Prometheus (Online Learning)', alpha=0.7)

    # Reference lines
    ax1.axhline(y=70, color='red', linestyle='--', linewidth=2, alpha=0.5,
                label='Degraded Performance')
    ax1.fill_between(x_axis, 85, 100, alpha=0.2, color='green',
                     label='High Performance Zone')

    # Distribution shift markers
    if show_distribution_shifts:
        for shift_idx in show_distribution_shifts:
            if shift_idx < len(x_axis):
                ax1.axvline(x=shift_idx, color='gray', linestyle=':', alpha=0.5)
                ax1.text(shift_idx, 95, 'Dist.\nShift', fontsize=9,
                        ha='center', va='top', alpha=0.7)

    ax1.set_xlabel(xlabel, fontsize=14, fontweight='bold')
    ax1.set_ylabel('Accuracy (%)', fontsize=14, fontweight='bold')
    ax1.set_title(title, fontsize=15, fontweight='bold', pad=20)
    ax1.legend(loc='lower left', fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, 100)

    # === RIGHT: Performance Gap ===
    gap = np.array(prometheus_results) - np.array(static_results)

    ax2.plot(x_axis, gap, 'purple', linewidth=3, marker='s', markersize=8)
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.3)
    ax2.fill_between(x_axis, 0, gap, where=(gap > 0), alpha=0.3, color='green',
                     label='Prometheus Advantage')
    ax2.fill_between(x_axis, 0, gap, where=(gap < 0), alpha=0.3, color='red',
                     label='Static Advantage')

    ax2.set_xlabel(xlabel, fontsize=14, fontweight='bold')
    ax2.set_ylabel('Performance Gap (%)', fontsize=14, fontweight='bold')
    ax2.set_title('Prometheus Advantage\n(Positive = Adaptive Wins)',
                  fontsize=15, fontweight='bold', pad=20)
    ax2.legend(loc='upper left', fontsize=11)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')

    return fig, (ax1, ax2)


def plot_training_progress(
    history: Dict[str, List[float]],
    title: str = "Training Progress",
    save_path: Optional[str] = None
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Plot training metrics over epochs.

    Args:
        history: Dictionary with 'loss', 'accuracy', 'val_loss', 'val_accuracy' keys
        title: Plot title
        save_path: Optional path to save figure

    Returns:
        Tuple of (figure, axes)

    Example:
        >>> history = model.fit(X, y, epochs=20, validation_split=0.15)
        >>> fig, axes = plot_training_progress(history.history)
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    epochs = np.arange(1, len(history['loss']) + 1)

    # === LEFT: Loss ===
    ax1.plot(epochs, history['loss'], 'b-o', linewidth=2, markersize=6,
             label='Training Loss', alpha=0.8)
    if 'val_loss' in history:
        ax1.plot(epochs, history['val_loss'], 'r-o', linewidth=2, markersize=6,
                 label='Validation Loss', alpha=0.8)

    ax1.set_xlabel('Epoch', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Loss', fontsize=13, fontweight='bold')
    ax1.set_title('Training & Validation Loss', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper right', fontsize=11)
    ax1.grid(True, alpha=0.3)

    # === RIGHT: Accuracy ===
    ax2.plot(epochs, np.array(history['accuracy']) * 100, 'b-o', linewidth=2,
             markersize=6, label='Training Accuracy', alpha=0.8)
    if 'val_accuracy' in history:
        ax2.plot(epochs, np.array(history['val_accuracy']) * 100, 'r-o',
                 linewidth=2, markersize=6, label='Validation Accuracy', alpha=0.8)

    ax2.set_xlabel('Epoch', fontsize=13, fontweight='bold')
    ax2.set_ylabel('Accuracy (%)', fontsize=13, fontweight='bold')
    ax2.set_title('Training & Validation Accuracy', fontsize=14, fontweight='bold')
    ax2.legend(loc='lower right', fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, 100)

    fig.suptitle(title, fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')

    return fig, (ax1, ax2)


def plot_distribution_shift(
    distributions: List[Dict[str, float]],
    title: str = "Distribution Shift Evolution",
    save_path: Optional[str] = None
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Plot how data distribution shifts over time.

    Args:
        distributions: List of dictionaries mapping class names to probabilities
        title: Plot title
        save_path: Optional path to save figure

    Returns:
        Tuple of (figure, axes)

    Example:
        >>> distributions = [
        ...     {'A': 0.5, 'B': 0.3, 'C': 0.2},
        ...     {'A': 0.3, 'B': 0.5, 'C': 0.2},
        ...     {'A': 0.2, 'B': 0.2, 'C': 0.6}
        ... ]
        >>> fig, ax = plot_distribution_shift(distributions)
    """
    fig, ax = plt.subplots(figsize=(14, 8))

    # Get all class names
    all_classes = set()
    for dist in distributions:
        all_classes.update(dist.keys())
    all_classes = sorted(list(all_classes))

    # Create matrix of probabilities
    n_steps = len(distributions)
    n_classes = len(all_classes)
    prob_matrix = np.zeros((n_classes, n_steps))

    for i, dist in enumerate(distributions):
        for j, class_name in enumerate(all_classes):
            prob_matrix[j, i] = dist.get(class_name, 0.0)

    # Stacked area plot
    x = np.arange(n_steps)
    colors = plt.cm.tab10(np.linspace(0, 1, n_classes))

    ax.stackplot(x, prob_matrix, labels=all_classes, colors=colors, alpha=0.8)

    ax.set_xlabel('Generation/Round/Cycle', fontsize=13, fontweight='bold')
    ax.set_ylabel('Probability', fontsize=13, fontweight='bold')
    ax.set_title(title, fontsize=15, fontweight='bold', pad=20)
    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(0, 1)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')

    return fig, ax


def plot_causal_attribution(
    causal_history: List[Dict[str, float]],
    title: str = "Causal Attribution Evolution",
    save_path: Optional[str] = None
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Plot evolution of causal attribution scores K(E:F).

    Args:
        causal_history: List of dictionaries with causal scores
        title: Plot title
        save_path: Optional path to save figure

    Returns:
        Tuple of (figure, axes)

    Example:
        >>> causal_history = [
        ...     {'learning_rate': 0.5, 'architecture': 0.5},
        ...     {'learning_rate': 0.7, 'architecture': 0.3},
        ...     {'learning_rate': 0.8, 'architecture': 0.2}
        ... ]
        >>> fig, ax = plot_causal_attribution(causal_history)
    """
    fig, ax = plt.subplots(figsize=(14, 7))

    # Extract factors
    if not causal_history:
        return fig, ax

    factors = list(causal_history[0].keys())
    x = np.arange(len(causal_history))

    colors = plt.cm.Set2(np.linspace(0, 1, len(factors)))

    for i, factor in enumerate(factors):
        scores = [ch[factor] for ch in causal_history]
        ax.plot(x, scores, 'o-', linewidth=3, markersize=8,
                label=f'K({factor}:Success)', color=colors[i], alpha=0.8)

    ax.set_xlabel('Cycle', fontsize=14, fontweight='bold')
    ax.set_ylabel('Causal Influence K(E:F)', fontsize=14, fontweight='bold')
    ax.set_title(title, fontsize=15, fontweight='bold', pad=20)
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')

    return fig, ax


def plot_safety_decisions(
    safety_history: List[str],
    title: str = "Gödelian Safety Decisions",
    save_path: Optional[str] = None
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Plot safety decision distribution.

    Args:
        safety_history: List of safety status strings ('provably_safe', 'provably_unsafe', 'undecidable')
        title: Plot title
        save_path: Optional path to save figure

    Returns:
        Tuple of (figure, axes)

    Example:
        >>> safety_history = ['provably_safe'] * 10 + ['undecidable'] * 2
        >>> fig, ax = plot_safety_decisions(safety_history)
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    # Count safety statuses
    from collections import Counter
    counts = Counter(safety_history)

    statuses = ['provably_safe', 'provably_unsafe', 'undecidable']
    status_labels = ['Provably Safe', 'Provably Unsafe', 'Undecidable']
    colors = ['green', 'red', 'orange']

    values = [counts.get(status, 0) for status in statuses]
    percentages = [v / len(safety_history) * 100 if safety_history else 0 for v in values]

    bars = ax.bar(status_labels, values, color=colors, alpha=0.7, edgecolor='black', linewidth=2)

    # Add percentage labels on bars
    for bar, pct in zip(bars, percentages):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{pct:.1f}%\n({int(height)})',
                ha='center', va='bottom', fontsize=12, fontweight='bold')

    ax.set_ylabel('Count', fontsize=13, fontweight='bold')
    ax.set_title(title, fontsize=15, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, axis='y')

    # Add summary text
    summary_text = (
        f"Total Decisions: {len(safety_history)}\n"
        f"Safe:  {counts.get('provably_safe', 0)} ({percentages[0]:.0f}%)\n"
        f"Unsafe: {counts.get('provably_unsafe', 0)} ({percentages[1]:.0f}%)\n"
        f"Undecidable: {counts.get('undecidable', 0)} ({percentages[2]:.0f}%)"
    )
    ax.text(0.98, 0.98, summary_text, transform=ax.transAxes,
            fontsize=10, va='top', ha='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')

    return fig, ax


def plot_sample_patterns(
    patterns: np.ndarray,
    labels: Optional[np.ndarray] = None,
    class_names: Optional[List[str]] = None,
    n_samples: int = 8,
    title: str = "Sample Patterns",
    save_path: Optional[str] = None
) -> Tuple[plt.Figure, np.ndarray]:
    """
    Plot grid of sample patterns.

    Args:
        patterns: Array of shape (n, height, width) or (n, height, width, 1)
        labels: Optional array of labels
        class_names: Optional list of class names
        n_samples: Number of samples to plot
        title: Plot title
        save_path: Optional path to save figure

    Returns:
        Tuple of (figure, axes array)

    Example:
        >>> X, y = generator.generate_batch(100, distribution)
        >>> fig, axes = plot_sample_patterns(X, y, class_names=['A', 'B', 'C'])
    """
    # Squeeze channel dimension if present
    if patterns.ndim == 4 and patterns.shape[-1] == 1:
        patterns = patterns.squeeze(-1)

    n_samples = min(n_samples, len(patterns))
    n_cols = 4
    n_rows = (n_samples + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(12, 3 * n_rows))
    axes = axes.flatten() if n_samples > 1 else [axes]

    for i in range(n_samples):
        ax = axes[i]
        ax.imshow(patterns[i], cmap='gray', interpolation='nearest')
        ax.axis('off')

        if labels is not None:
            label = labels[i]
            if class_names is not None and label < len(class_names):
                label_text = class_names[label]
            else:
                label_text = f"Class {label}"
            ax.set_title(label_text, fontsize=10, fontweight='bold')

    # Hide unused subplots
    for i in range(n_samples, len(axes)):
        axes[i].axis('off')

    fig.suptitle(title, fontsize=16, fontweight='bold', y=1.00)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')

    return fig, axes


def configure_plot_style(style: str = 'default'):
    """
    Configure matplotlib style for professional plots.

    Args:
        style: Style name ('default', 'dark', 'minimal')
    """
    if style == 'default':
        plt.style.use('seaborn-v0_8-darkgrid')
        plt.rcParams['figure.figsize'] = (16, 10)
        plt.rcParams['font.size'] = 12
        plt.rcParams['axes.titlesize'] = 14
        plt.rcParams['axes.labelsize'] = 12
        plt.rcParams['legend.fontsize'] = 10

    elif style == 'dark':
        plt.style.use('dark_background')
        plt.rcParams['figure.figsize'] = (16, 10)
        plt.rcParams['font.size'] = 12

    elif style == 'minimal':
        plt.style.use('seaborn-v0_8-white')
        plt.rcParams['figure.figsize'] = (16, 10)
        plt.rcParams['font.size'] = 11
