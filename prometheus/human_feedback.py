"""
Human Feedback Interface — Prometheus v0.97

Provides two modes for collecting pairwise trajectory preferences:

  Interactive mode  — CLI prompt shown to a human operator.
  Synthetic mode    — Programmatic oracle based on a known true reward,
                      used for automated experiments and unit tests.

Both return the same PreferenceResult type so callers are agnostic
about the collection mechanism.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PreferenceResult:
    """Outcome of one preference query."""
    preferred_index: int        # 0 = trajectory1 preferred, 1 = trajectory2
    preferred_features: np.ndarray
    unpreferred_features: np.ndarray
    confidence: float = 1.0     # 1.0 for hard labels; <1 for soft/noisy
    source: str = "human"       # "human" | "oracle" | "noisy_oracle"


# ---------------------------------------------------------------------------
# Interactive (CLI) mode
# ---------------------------------------------------------------------------

def get_human_preference(
    trajectory1: Any,
    trajectory2: Any,
    features1: Optional[np.ndarray] = None,
    features2: Optional[np.ndarray] = None,
) -> PreferenceResult:
    """
    Ask the human operator for their preference between two trajectories.

    Args:
        trajectory1: First trajectory (printed for the human to inspect).
        trajectory2: Second trajectory.
        features1:   Cumulative feature vector of trajectory1 (optional display).
        features2:   Cumulative feature vector of trajectory2 (optional display).

    Returns:
        PreferenceResult with preferred_index 0 (traj1) or 1 (traj2).
    """
    print("\n" + "=" * 50)
    print("PREFERENCE QUERY")
    print("=" * 50)
    print(f"\nTrajectory A:\n  {trajectory1}")
    if features1 is not None:
        print(f"  Features: {np.round(features1, 3)}")
    print(f"\nTrajectory B:\n  {trajectory2}")
    if features2 is not None:
        print(f"  Features: {np.round(features2, 3)}")
    print()

    while True:
        try:
            raw = input("Which trajectory is better? Enter A or B: ").strip().upper()
            if raw in ("A", "1"):
                preferred_index = 0
                break
            elif raw in ("B", "2"):
                preferred_index = 1
                break
            else:
                print("Please enter A or B.")
        except (ValueError, EOFError):
            print("No input received — defaulting to A.")
            preferred_index = 0
            break

    f1 = features1 if features1 is not None else np.zeros(1)
    f2 = features2 if features2 is not None else np.zeros(1)

    if preferred_index == 0:
        return PreferenceResult(0, f1, f2, source="human")
    else:
        return PreferenceResult(1, f2, f1, source="human")


# ---------------------------------------------------------------------------
# Synthetic oracle mode (for automated experiments / tests)
# ---------------------------------------------------------------------------

class SyntheticOracle:
    """
    Programmatic preference oracle based on a true reward function.

    Used for:
    - Unit tests (no human needed)
    - Benchmark experiments with known ground truth
    - Noisy-label ablation studies

    The oracle computes true rewards using `true_reward_fn` and returns
    the trajectory with higher reward as preferred.  An optional noise
    level σ draws the preference from the Bradley-Terry model instead of
    the hard argmax (simulating a human who sometimes makes mistakes).
    """

    def __init__(self,
                 true_reward_fn: Callable[[np.ndarray], float],
                 noise_level: float = 0.0):
        """
        Args:
            true_reward_fn: Function (feature_vector) → scalar reward.
                            Called on the cumulative feature sum of each trajectory.
            noise_level:    Standard deviation of Gaussian noise added to true rewards
                            before comparison.  0.0 = deterministic optimal oracle.
        """
        self.true_reward_fn = true_reward_fn
        self.noise_level = noise_level
        self._query_count = 0

    def query(self,
              features1: np.ndarray,
              features2: np.ndarray,
              trajectory1: Any = None,
              trajectory2: Any = None) -> PreferenceResult:
        """
        Return a synthetic preference based on true rewards.

        Args:
            features1: Cumulative feature vector of trajectory 1.
            features2: Cumulative feature vector of trajectory 2.
            trajectory1: Optional trajectory data (ignored by oracle).
            trajectory2: Optional trajectory data (ignored by oracle).

        Returns:
            PreferenceResult.
        """
        r1 = self.true_reward_fn(features1)
        r2 = self.true_reward_fn(features2)

        if self.noise_level > 0:
            r1 += np.random.normal(0, self.noise_level)
            r2 += np.random.normal(0, self.noise_level)

        self._query_count += 1
        source = "oracle" if self.noise_level == 0 else "noisy_oracle"

        if r1 >= r2:
            confidence = _bradley_terry_prob(r1 - r2)
            return PreferenceResult(0, features1, features2,
                                    confidence=confidence, source=source)
        else:
            confidence = _bradley_terry_prob(r2 - r1)
            return PreferenceResult(1, features2, features1,
                                    confidence=confidence, source=source)

    @property
    def query_count(self) -> int:
        return self._query_count


# ---------------------------------------------------------------------------
# Batch preference collection helpers
# ---------------------------------------------------------------------------

def collect_preferences_batch(
    trajectory_feature_pairs: List[Tuple[np.ndarray, np.ndarray]],
    oracle: Optional[SyntheticOracle] = None,
    verbose: bool = False,
) -> List[PreferenceResult]:
    """
    Collect preferences for a batch of trajectory pairs.

    If `oracle` is provided, uses it automatically.
    Otherwise, prompts the human for each pair.

    Args:
        trajectory_feature_pairs: List of (features_a, features_b) pairs.
        oracle:   SyntheticOracle to use instead of human input.
        verbose:  Print progress.

    Returns:
        List of PreferenceResult objects.
    """
    results = []
    n = len(trajectory_feature_pairs)
    for i, (f1, f2) in enumerate(trajectory_feature_pairs):
        if verbose:
            print(f"  Query {i + 1}/{n}...", end=" ", flush=True)
        if oracle is not None:
            result = oracle.query(f1, f2)
        else:
            result = get_human_preference(
                trajectory1=f"Trajectory {i * 2 + 1}",
                trajectory2=f"Trajectory {i * 2 + 2}",
                features1=f1,
                features2=f2,
            )
        results.append(result)
        if verbose:
            src = result.source
            idx = "A" if result.preferred_index == 0 else "B"
            print(f"preferred={idx} ({src})")
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bradley_terry_prob(delta_r: float) -> float:
    """P(τ₁ ≻ τ₂) under the Bradley-Terry model given reward difference."""
    if delta_r >= 0:
        return 1.0 / (1.0 + np.exp(-delta_r))
    e = np.exp(delta_r)
    return e / (1.0 + e)
