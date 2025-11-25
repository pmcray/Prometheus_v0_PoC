"""
Prometheus Performance Metrics

This module contains performance metric computation utilities:
- Accuracy and loss tracking
- Performance degradation measurement
- Advantage gap computation
- Statistical analysis
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy import stats


def compute_accuracy(predictions: np.ndarray, labels: np.ndarray) -> float:
    """
    Compute classification accuracy.

    Args:
        predictions: Predicted class labels
        labels: True class labels

    Returns:
        Accuracy as percentage (0-100)
    """
    correct = np.sum(predictions == labels)
    total = len(labels)
    return (correct / total) * 100.0


def compute_performance_degradation(
    performance_history: List[float],
    window_size: int = 3
) -> Dict[str, float]:
    """
    Compute performance degradation metrics.

    Args:
        performance_history: List of performance values over time
        window_size: Window size for trend calculation

    Returns:
        Dictionary with degradation metrics
    """
    if len(performance_history) < 2:
        return {
            'total_degradation': 0.0,
            'max_degradation': 0.0,
            'trend': 'stable',
            'is_degrading': False
        }

    perf = np.array(performance_history)

    # Total change
    total_degradation = perf[0] - perf[-1]

    # Maximum single-step degradation
    diffs = np.diff(perf)
    max_degradation = np.max(-diffs) if len(diffs) > 0 else 0.0

    # Trend analysis
    if len(perf) >= window_size:
        recent = perf[-window_size:]
        slope = np.polyfit(range(len(recent)), recent, 1)[0]

        if slope < -1.0:
            trend = 'degrading'
        elif slope > 1.0:
            trend = 'improving'
        else:
            trend = 'stable'
    else:
        trend = 'stable'

    return {
        'total_degradation': float(total_degradation),
        'max_degradation': float(max_degradation),
        'trend': trend,
        'is_degrading': total_degradation > 5.0  # >5% degradation
    }


def compute_advantage_gap(
    baseline_performance: List[float],
    experimental_performance: List[float]
) -> Dict[str, float]:
    """
    Compute performance advantage gap between two methods.

    Args:
        baseline_performance: List of baseline (e.g., Static) accuracies
        experimental_performance: List of experimental (e.g., Prometheus) accuracies

    Returns:
        Dictionary with gap statistics
    """
    baseline = np.array(baseline_performance)
    experimental = np.array(experimental_performance)

    gap = experimental - baseline

    return {
        'initial_gap': float(gap[0]),
        'final_gap': float(gap[-1]),
        'average_gap': float(np.mean(gap)),
        'median_gap': float(np.median(gap)),
        'max_gap': float(np.max(gap)),
        'min_gap': float(np.min(gap)),
        'std_gap': float(np.std(gap)),
        'gap_trend': 'widening' if gap[-1] > gap[0] else 'narrowing',
        'has_advantage': float(np.mean(gap) > 0),
        'strong_advantage': float(np.mean(gap) > 10.0),  # >10% advantage
        'clear_advantage': float(np.mean(gap) > 5.0)     # >5% advantage
    }


def compute_statistical_significance(
    baseline_performance: List[float],
    experimental_performance: List[float],
    alpha: float = 0.05
) -> Dict[str, float]:
    """
    Compute statistical significance of performance difference.

    Uses paired t-test to determine if difference is statistically significant.

    Args:
        baseline_performance: List of baseline accuracies
        experimental_performance: List of experimental accuracies
        alpha: Significance level (default: 0.05)

    Returns:
        Dictionary with statistical test results
    """
    baseline = np.array(baseline_performance)
    experimental = np.array(experimental_performance)

    # Paired t-test
    t_stat, p_value = stats.ttest_rel(experimental, baseline)

    # Effect size (Cohen's d)
    diff = experimental - baseline
    mean_diff = np.mean(diff)
    std_diff = np.std(diff)
    cohens_d = mean_diff / std_diff if std_diff > 0 else 0.0

    return {
        't_statistic': float(t_stat),
        'p_value': float(p_value),
        'is_significant': bool(p_value < alpha),
        'cohens_d': float(cohens_d),
        'effect_size': 'large' if abs(cohens_d) > 0.8 else 'medium' if abs(cohens_d) > 0.5 else 'small',
        'mean_difference': float(mean_diff),
        'confidence_level': float((1 - alpha) * 100)
    }


def compute_adaptation_rate(
    performance_history: List[float],
    shift_indices: List[int]
) -> Dict[str, float]:
    """
    Compute how quickly performance recovers after distribution shifts.

    Args:
        performance_history: List of performance values
        shift_indices: Indices where distribution shifts occurred

    Returns:
        Dictionary with adaptation metrics
    """
    if not shift_indices:
        return {
            'average_recovery_time': 0.0,
            'average_drop_size': 0.0,
            'recovery_rate': 0.0
        }

    perf = np.array(performance_history)
    recovery_times = []
    drop_sizes = []

    for shift_idx in shift_indices:
        if shift_idx == 0 or shift_idx >= len(perf) - 1:
            continue

        # Performance before shift
        pre_shift = perf[shift_idx - 1]

        # Performance immediately after shift
        post_shift = perf[shift_idx]

        # Drop size
        drop = pre_shift - post_shift
        drop_sizes.append(drop)

        # Find recovery time (when performance returns to pre-shift level)
        recovery_idx = shift_idx
        for i in range(shift_idx + 1, len(perf)):
            if perf[i] >= pre_shift - 2.0:  # Within 2% of pre-shift
                recovery_idx = i
                break

        recovery_time = recovery_idx - shift_idx
        recovery_times.append(recovery_time)

    return {
        'average_recovery_time': float(np.mean(recovery_times)) if recovery_times else 0.0,
        'average_drop_size': float(np.mean(drop_sizes)) if drop_sizes else 0.0,
        'recovery_rate': float(np.mean(drop_sizes) / np.mean(recovery_times)) if recovery_times and np.mean(recovery_times) > 0 else 0.0,
        'num_shifts': len(shift_indices)
    }


def compute_learning_efficiency(
    performance_history: List[float],
    training_examples: List[int]
) -> Dict[str, float]:
    """
    Compute learning efficiency: performance gain per training example.

    Args:
        performance_history: List of performance values
        training_examples: Cumulative number of training examples at each step

    Returns:
        Dictionary with efficiency metrics
    """
    if len(performance_history) < 2 or len(training_examples) < 2:
        return {
            'performance_per_example': 0.0,
            'sample_efficiency': 0.0
        }

    perf = np.array(performance_history)
    examples = np.array(training_examples)

    # Performance gain
    perf_gain = perf[-1] - perf[0]

    # Examples used
    examples_used = examples[-1] - examples[0] if examples[-1] > examples[0] else 1

    # Efficiency = performance gain per 1000 examples
    performance_per_example = (perf_gain / examples_used) * 1000

    # Sample efficiency (higher is better)
    sample_efficiency = perf_gain / np.log1p(examples_used)

    return {
        'performance_per_example': float(performance_per_example),
        'sample_efficiency': float(sample_efficiency),
        'total_examples': int(examples_used),
        'total_gain': float(perf_gain)
    }


def compute_stability_metrics(
    performance_history: List[float]
) -> Dict[str, float]:
    """
    Compute performance stability metrics.

    Args:
        performance_history: List of performance values

    Returns:
        Dictionary with stability metrics
    """
    perf = np.array(performance_history)

    # Variance and standard deviation
    variance = float(np.var(perf))
    std_dev = float(np.std(perf))

    # Coefficient of variation (normalized stability)
    mean_perf = np.mean(perf)
    cv = (std_dev / mean_perf * 100) if mean_perf > 0 else 0.0

    # Maximum fluctuation
    max_fluctuation = float(np.max(perf) - np.min(perf))

    # Consecutive differences (volatility)
    if len(perf) > 1:
        diffs = np.abs(np.diff(perf))
        average_volatility = float(np.mean(diffs))
        max_volatility = float(np.max(diffs))
    else:
        average_volatility = 0.0
        max_volatility = 0.0

    # Stability score (0-100, higher is more stable)
    stability_score = 100.0 - min(cv, 100.0)

    return {
        'variance': variance,
        'std_dev': std_dev,
        'coefficient_of_variation': float(cv),
        'max_fluctuation': max_fluctuation,
        'average_volatility': average_volatility,
        'max_volatility': max_volatility,
        'stability_score': float(stability_score),
        'is_stable': cv < 10.0  # Stable if CV < 10%
    }


def summarize_experiment_results(
    static_results: List[float],
    prometheus_results: List[float],
    experiment_name: str = "Experiment"
) -> Dict[str, any]:
    """
    Comprehensive summary of experiment results.

    Args:
        static_results: List of static agent accuracies
        prometheus_results: List of Prometheus agent accuracies
        experiment_name: Name of experiment

    Returns:
        Dictionary with all summary statistics
    """
    # Basic statistics
    static_stats = {
        'initial': float(static_results[0]),
        'final': float(static_results[-1]),
        'change': float(static_results[-1] - static_results[0]),
        'average': float(np.mean(static_results)),
        'min': float(np.min(static_results)),
        'max': float(np.max(static_results))
    }

    prometheus_stats = {
        'initial': float(prometheus_results[0]),
        'final': float(prometheus_results[-1]),
        'change': float(prometheus_results[-1] - prometheus_results[0]),
        'average': float(np.mean(prometheus_results)),
        'min': float(np.min(prometheus_results)),
        'max': float(np.max(prometheus_results))
    }

    # Performance gap
    gap_stats = compute_advantage_gap(static_results, prometheus_results)

    # Degradation analysis
    static_degradation = compute_performance_degradation(static_results)
    prometheus_degradation = compute_performance_degradation(prometheus_results)

    # Stability
    static_stability = compute_stability_metrics(static_results)
    prometheus_stability = compute_stability_metrics(prometheus_results)

    # Statistical significance
    significance = compute_statistical_significance(static_results, prometheus_results)

    # Conclusion
    if gap_stats['average_gap'] > 10.0:
        conclusion = "STRONG Prometheus advantage demonstrated"
        conclusion_icon = "🚀"
    elif gap_stats['average_gap'] > 5.0:
        conclusion = "CLEAR Prometheus advantage demonstrated"
        conclusion_icon = "📈"
    elif gap_stats['average_gap'] > 0:
        conclusion = "Modest Prometheus advantage demonstrated"
        conclusion_icon = "✓"
    else:
        conclusion = "No clear advantage detected"
        conclusion_icon = "⚠️"

    return {
        'experiment_name': experiment_name,
        'static': static_stats,
        'prometheus': prometheus_stats,
        'advantage_gap': gap_stats,
        'static_degradation': static_degradation,
        'prometheus_degradation': prometheus_degradation,
        'static_stability': static_stability,
        'prometheus_stability': prometheus_stability,
        'statistical_significance': significance,
        'conclusion': conclusion,
        'conclusion_icon': conclusion_icon
    }
