"""
MetaLearner: Probabilistic Synaptic Mutation (I.J. Good, 1965)

Implements Good's vision of an ultraintelligent machine that modifies its own
"synaptic weights" (strategy probabilities) based on experience:
- Upward mutation: Strengthen successful strategies
- Downward mutation: Weaken failed strategies

This is THE MISSING PIECE: weights that adapt DURING task execution,
not just during offline pre-training.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import random
from collections import defaultdict


@dataclass
class LearningHistory:
    """Tracks the evolution of strategy probabilities over time."""

    attempts: List[int] = field(default_factory=list)
    probabilities: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    outcomes: List[Tuple[str, bool]] = field(default_factory=list)  # (strategy, success)


class MetaLearner:
    """
    Implements I.J. Good's probabilistic synaptic mutation for online learning.

    Key Properties:
    - Strategy weights evolve during task execution (NOT frozen after training)
    - Upward mutation: Successful strategies → increased probability
    - Downward mutation: Failed strategies → decreased probability
    - Converges to task-specific optimal policy

    Example:
        >>> learner = MetaLearner(['rotation', 'symmetry', 'crop'])
        >>> learner.update_on_success('symmetry')
        >>> learner.update_on_failure('rotation')
        >>> probs = learner.get_strategy_probabilities()
        # 'symmetry' probability increased, 'rotation' decreased
    """

    def __init__(
        self,
        strategies: List[str],
        upward_rate: float = 0.2,
        downward_rate: float = 0.15,
        min_probability: float = 0.05,
        max_probability: float = 0.85,
        initial_uniform: bool = True,
    ):
        """
        Initialize MetaLearner with strategy set and mutation rates.

        Args:
            strategies: List of strategy names to track
            upward_rate: Multiplicative factor for successful strategies (default 0.2 = 20% boost)
            downward_rate: Multiplicative factor for failed strategies (default 0.15 = 15% reduction)
            min_probability: Floor to prevent complete pruning (default 0.05 = 5%)
            max_probability: Ceiling to prevent over-concentration (default 0.85 = 85%)
            initial_uniform: Start with uniform distribution vs weighted prior
        """
        self.strategies = strategies
        self.upward_rate = upward_rate
        self.downward_rate = downward_rate
        self.min_probability = min_probability
        self.max_probability = max_probability

        # Initialize strategy probabilities
        if initial_uniform:
            # Uniform prior: all strategies equally likely
            init_prob = 1.0 / len(strategies)
            self.probabilities = {strategy: init_prob for strategy in strategies}
        else:
            # Start with slight bias (can be customized)
            self.probabilities = {strategy: 1.0 / len(strategies) for strategy in strategies}

        # Tracking for analysis
        self.attempt_count = 0
        self.history = LearningHistory()
        self.success_counts = defaultdict(int)
        self.failure_counts = defaultdict(int)

        # Record initial state
        self._record_history()

    def update_on_success(self, strategy: str) -> None:
        """
        Upward mutation: Strengthen successful strategy (Good's reinforcement).

        Args:
            strategy: Name of strategy that succeeded
        """
        if strategy not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Upward mutation: multiply by (1 + upward_rate)
        self.probabilities[strategy] *= 1.0 + self.upward_rate

        # Enforce maximum to prevent over-concentration
        if self.probabilities[strategy] > self.max_probability:
            self.probabilities[strategy] = self.max_probability

        # Renormalize to maintain probability distribution
        self._normalize()

        # Track success
        self.success_counts[strategy] += 1
        self.attempt_count += 1
        self.history.outcomes.append((strategy, True))
        self._record_history()

    def update_on_failure(self, strategy: str) -> None:
        """
        Downward mutation: Weaken failed strategy (Good's pruning).

        Args:
            strategy: Name of strategy that failed
        """
        if strategy not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Downward mutation: multiply by (1 - downward_rate)
        self.probabilities[strategy] *= 1.0 - self.downward_rate

        # Enforce minimum to prevent complete pruning
        if self.probabilities[strategy] < self.min_probability:
            self.probabilities[strategy] = self.min_probability

        # Renormalize to maintain probability distribution
        self._normalize()

        # Track failure
        self.failure_counts[strategy] += 1
        self.attempt_count += 1
        self.history.outcomes.append((strategy, False))
        self._record_history()

    def select_strategy(self, temperature: float = 1.0) -> str:
        """
        Probabilistically select next strategy based on current weights.

        Args:
            temperature: Exploration/exploitation trade-off
                        - temperature > 1.0: More exploration (flatten distribution)
                        - temperature < 1.0: More exploitation (sharpen distribution)
                        - temperature = 1.0: Use raw probabilities

        Returns:
            Selected strategy name
        """
        if temperature != 1.0:
            # Apply temperature to probabilities for exploration control
            tempered_probs = {s: p ** (1.0 / temperature) for s, p in self.probabilities.items()}
            # Renormalize
            total = sum(tempered_probs.values())
            tempered_probs = {s: p / total for s, p in tempered_probs.items()}
        else:
            tempered_probs = self.probabilities

        # Weighted random selection
        strategies = list(tempered_probs.keys())
        weights = [tempered_probs[s] for s in strategies]
        return random.choices(strategies, weights=weights, k=1)[0]

    def get_strategy_probabilities(self) -> Dict[str, float]:
        """
        Get current strategy probability distribution.

        Returns:
            Dictionary mapping strategy names to probabilities
        """
        return self.probabilities.copy()

    def get_best_strategy(self) -> str:
        """
        Get strategy with highest current probability.

        Returns:
            Name of most probable strategy
        """
        return max(self.probabilities.items(), key=lambda x: x[1])[0]

    def get_success_rate(self, strategy: Optional[str] = None) -> float:
        """
        Calculate success rate for a strategy or overall.

        Args:
            strategy: Strategy name, or None for overall success rate

        Returns:
            Success rate between 0.0 and 1.0
        """
        if strategy is None:
            # Overall success rate
            total_successes = sum(self.success_counts.values())
            total_attempts = self.attempt_count
        else:
            # Strategy-specific success rate
            total_successes = self.success_counts[strategy]
            total_attempts = self.success_counts[strategy] + self.failure_counts[strategy]

        if total_attempts == 0:
            return 0.0
        return total_successes / total_attempts

    def get_history(self) -> LearningHistory:
        """
        Get complete learning history for visualization.

        Returns:
            LearningHistory object with attempts, probabilities, outcomes
        """
        return self.history

    def reset(self, keep_history: bool = False) -> None:
        """
        Reset learner to initial state.

        Args:
            keep_history: If True, preserve history for analysis; if False, clear it
        """
        # Reset probabilities to uniform
        init_prob = 1.0 / len(self.strategies)
        self.probabilities = {strategy: init_prob for strategy in self.strategies}

        # Reset counters
        self.attempt_count = 0
        self.success_counts = defaultdict(int)
        self.failure_counts = defaultdict(int)

        if not keep_history:
            self.history = LearningHistory()

        # Record reset state
        self._record_history()

    def _normalize(self) -> None:
        """Normalize probabilities to sum to 1.0."""
        total = sum(self.probabilities.values())
        if total > 0:
            self.probabilities = {strategy: prob / total for strategy, prob in self.probabilities.items()}

    def _record_history(self) -> None:
        """Record current state to history for later visualization."""
        self.history.attempts.append(self.attempt_count)
        for strategy in self.strategies:
            self.history.probabilities[strategy].append(self.probabilities[strategy])

    def get_statistics(self) -> Dict[str, any]:
        """
        Get comprehensive statistics about learning progress.

        Returns:
            Dictionary with current state, history, and performance metrics
        """
        return {
            "attempt_count": self.attempt_count,
            "current_probabilities": self.get_strategy_probabilities(),
            "best_strategy": self.get_best_strategy(),
            "overall_success_rate": self.get_success_rate(),
            "strategy_success_rates": {strategy: self.get_success_rate(strategy) for strategy in self.strategies},
            "success_counts": dict(self.success_counts),
            "failure_counts": dict(self.failure_counts),
            "convergence_score": self._calculate_convergence_score(),
        }

    def _calculate_convergence_score(self) -> float:
        """
        Calculate how much the distribution has converged (entropy-based).

        Returns:
            Score between 0.0 (uniform) and 1.0 (fully converged to one strategy)
        """
        # Use entropy to measure convergence
        # High entropy = uniform (not converged)
        # Low entropy = peaked (converged)
        import math

        entropy = -sum(p * math.log2(p) if p > 0 else 0 for p in self.probabilities.values())

        # Normalize: max entropy is log2(n) for uniform distribution
        max_entropy = math.log2(len(self.strategies))

        if max_entropy == 0:
            return 1.0

        # Convert to convergence score: 0 = uniform, 1 = fully converged
        return 1.0 - (entropy / max_entropy)

    def __repr__(self) -> str:
        """String representation showing current state."""
        best = self.get_best_strategy()
        best_prob = self.probabilities[best]
        return (
            f"MetaLearner(attempts={self.attempt_count}, "
            f"best_strategy='{best}' ({best_prob:.2%}), "
            f"success_rate={self.get_success_rate():.2%})"
        )
