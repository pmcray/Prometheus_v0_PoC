"""
Value Learning Module — Prometheus v0.97

Implements preference-based Inverse Reinforcement Learning (IRL) following
the Bradley-Terry model, as specified in WORKPLAN_1_Value_Learning.md.

The core idea (I.J. Good / Stuart Russell alignment):
  Rather than hard-coding a reward function, the system infers human values
  from pairwise trajectory preferences.  The learned weights are then used
  to guide the MCSSupervisor's planning decisions.

Key classes
-----------
ValueLearningAgent
    Learns a linear reward  R(s) = w^T φ(s)  via online gradient updates
    from human (or synthetic) pairwise trajectory preferences.

    Improvements over the original stub:
    - Bradley-Terry gradient (proper log-likelihood, not raw perceptron)
    - Learning-rate schedule and L2 regularisation
    - Convergence tracking (weight delta history)
    - Serialise / deserialise weights to JSON
    - `rank_trajectories()` — rank a list of trajectories by learned reward

PreferenceBuffer
    Stores (preferred, unpreferred) feature-sum pairs for batch or
    replay-based training, with optional random shuffling.

References
----------
- Christiano et al. (2017) "Deep Reinforcement Learning from Human Preferences"
- Bradley & Terry (1952) "Rank Analysis of Incomplete Block Designs"
- Russell (2019) "Human Compatible"
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

import numpy as np

from prometheus.adversarial_robustness import DataValidator
from prometheus.lineage import ModelRegistry

logger = logging.getLogger(__name__)


class PreferenceBuffer:
    """
    Stores pairwise preference data: (phi_preferred, phi_unpreferred).

    Each entry is a pair of cumulative feature vectors (one per trajectory).
    The buffer supports random sampling for mini-batch training.
    """

    def __init__(self, max_size: int = 1000, feature_size: Optional[int] = None):
        self.max_size = max_size
        self.feature_size = feature_size
        self._preferred: List[np.ndarray] = []
        self._unpreferred: List[np.ndarray] = []
        self.validator = DataValidator(feature_size) if feature_size is not None else None

    def add(self, preferred_features: np.ndarray,
            unpreferred_features: np.ndarray) -> None:
        """Add a preference pair to the buffer."""
        pref = np.array(preferred_features, dtype=float)
        unpref = np.array(unpreferred_features, dtype=float)

        # Validate features if validator is available
        if self.validator:
            self.validator.validate_pair(pref, unpref)
        elif self.feature_size is None:
            # Lazy initialization of feature_size and validator
            self.feature_size = pref.shape[0]
            self.validator = DataValidator(self.feature_size)
            self.validator.validate_pair(pref, unpref)

        self._preferred.append(pref)
        self._unpreferred.append(unpref)
        # Trim if over capacity (FIFO)
        if len(self._preferred) > self.max_size:
            self._preferred.pop(0)
            self._unpreferred.pop(0)

    def sample(self, n: int) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Return up to n random (preferred, unpreferred) pairs."""
        size = len(self._preferred)
        if size == 0:
            return []
        indices = np.random.choice(size, min(n, size), replace=False)
        return [(self._preferred[i], self._unpreferred[i]) for i in indices]

    def __len__(self) -> int:
        return len(self._preferred)

    def all_pairs(self) -> List[Tuple[np.ndarray, np.ndarray]]:
        return list(zip(self._preferred, self._unpreferred))


class ValueLearningAgent:
    """
    Learns a linear reward function  R(s) = w^T φ(s)  from pairwise
    trajectory preferences using the Bradley-Terry gradient.

    Bradley-Terry model
    -------------------
    P(τ₁ ≻ τ₂) = σ( R(τ₁) − R(τ₂) )   where  R(τ) = w^T Σ_t φ(s_t)

    Gradient of the log-likelihood for one pair:
        ∇w L  =  (1 − σ(Δ)) · (φ_pref − φ_unpref)  −  λ w

    The agent also maintains a `PreferenceBuffer` so that past preferences
    can be replayed during training.
    """

    def __init__(self,
                 feature_size: int,
                 learning_rate: float = 0.05,
                 l2_reg: float = 1e-3,
                 history_window: int = 20):
        """
        Args:
            feature_size:    Dimensionality of state feature vectors.
            learning_rate:   Initial gradient-ascent step size.
            l2_reg:          L2 regularisation coefficient (prevents weight blow-up).
            history_window:  How many recent weight-delta norms to track for
                             convergence detection.
        """
        self.feature_size = feature_size
        self.learning_rate = learning_rate
        self.l2_reg = l2_reg
        self.history_window = history_window

        self.weights = np.zeros(feature_size, dtype=float)
        self.buffer = PreferenceBuffer(feature_size=feature_size)
        self.registry = ModelRegistry()

        # Convergence tracking
        self._update_count: int = 0
        self._delta_history: List[float] = []

    # ------------------------------------------------------------------
    # Core reward interface
    # ------------------------------------------------------------------

    def get_reward(self, features: np.ndarray) -> float:
        """Return scalar reward for a feature vector (or trajectory sum)."""
        return float(np.dot(self.weights, features))

    def score_trajectory(self, trajectory_features: np.ndarray) -> float:
        """
        Score a trajectory given its cumulative feature sum.

        Args:
            trajectory_features: Sum of φ(s_t) over all t in the trajectory.

        Returns:
            Scalar reward estimate.
        """
        return self.get_reward(trajectory_features)

    def rank_trajectories(
            self,
            feature_sums: List[np.ndarray]
    ) -> List[Tuple[float, int]]:
        """
        Rank trajectories by learned reward (highest first).

        Args:
            feature_sums: List of cumulative feature vectors, one per trajectory.

        Returns:
            List of (score, original_index) sorted descending by score.
        """
        scored = [(self.score_trajectory(f), i) for i, f in enumerate(feature_sums)]
        return sorted(scored, reverse=True)

    # ------------------------------------------------------------------
    # Learning
    # ------------------------------------------------------------------

    def update_weights(self,
                       preferred_features: np.ndarray,
                       unpreferred_features: np.ndarray) -> float:
        """
        Update weights using the Bradley-Terry gradient for one preference pair.

        Args:
            preferred_features:   Cumulative φ of the preferred trajectory.
            unpreferred_features: Cumulative φ of the unpreferred trajectory.

        Returns:
            Weight-delta norm (useful for convergence monitoring).
        """
        pref = np.array(preferred_features, dtype=float)
        unpref = np.array(unpreferred_features, dtype=float)

        # Reward difference
        delta_r = self.get_reward(pref) - self.get_reward(unpref)

        # Bradley-Terry probability P(pref ≻ unpref)
        prob = _sigmoid(delta_r)

        # Gradient of log P: (1 − P) · (φ_pref − φ_unpref) − λ·w
        grad = (1.0 - prob) * (pref - unpref) - self.l2_reg * self.weights

        # Gradient ascent step
        old_weights = self.weights.copy()
        self.weights += self.learning_rate * grad

        # Track convergence
        delta_norm = float(np.linalg.norm(self.weights - old_weights))
        self._delta_history.append(delta_norm)
        if len(self._delta_history) > self.history_window:
            self._delta_history.pop(0)

        self._update_count += 1

        # Store in buffer for replay
        self.buffer.add(pref, unpref)

        # Automated Checkpointing & Lineage Tracking (WP-04)
        if self._update_count % 100 == 0:
            weight_file = "value_weights_checkpoint.json"
            self.save(weight_file)
            
            version_id = self.registry.checkpoint_system(
                code_files=[], # Weights only for this tracker
                weight_files=[weight_file]
            )
            
            # Use probability as a proxy for "improvement" 
            # (higher prob means the model already correctly predicted the preference)
            LineageTracker(self.registry).track_modification(
                "ValueLearningAgent", "weights",
                f"Batch update {self._update_count}",
                0.0, float(prob)
            )

        logger.debug(
            f"Update {self._update_count}: P(pref)={prob:.3f}, "
            f"delta_norm={delta_norm:.5f}"
        )
        return delta_norm

    def train_from_buffer(self, n_pairs: int = 16) -> float:
        """
        Sample n_pairs from the preference buffer and do gradient updates.

        Useful for experience-replay training between live preference rounds.

        Returns:
            Mean weight-delta norm across sampled pairs.
        """
        pairs = self.buffer.sample(n_pairs)
        if not pairs:
            return 0.0
        deltas = [self.update_weights(p, u) for p, u in pairs]
        return float(np.mean(deltas))

    def train_to_convergence(self,
                              preference_pairs: List[Tuple[np.ndarray, np.ndarray]],
                              max_epochs: int = 200,
                              tol: float = 1e-4) -> Dict[str, Any]:
        """
        Train on a fixed dataset of preference pairs until convergence.

        Args:
            preference_pairs: List of (preferred_features, unpreferred_features).
            max_epochs:       Maximum number of full passes through the dataset.
            tol:              Convergence threshold on mean weight-delta norm.

        Returns:
            Dict with keys: epochs_run, final_delta, converged, weight_history.
        """
        weight_history = [self.weights.copy()]
        converged = False

        for epoch in range(max_epochs):
            # Shuffle for stochastic-style updates
            indices = np.random.permutation(len(preference_pairs))
            epoch_deltas = []

            for idx in indices:
                pref, unpref = preference_pairs[idx]
                delta = self.update_weights(pref, unpref)
                epoch_deltas.append(delta)

            mean_delta = float(np.mean(epoch_deltas))
            weight_history.append(self.weights.copy())

            if mean_delta < tol:
                converged = True
                logger.info(
                    f"Converged at epoch {epoch + 1} "
                    f"(mean_delta={mean_delta:.6f} < tol={tol})"
                )
                break

        return {
            "epochs_run": epoch + 1,
            "final_delta": mean_delta,
            "converged": converged,
            "weight_history": weight_history,
        }

    # ------------------------------------------------------------------
    # Convergence diagnostics
    # ------------------------------------------------------------------

    def is_converged(self, tol: float = 1e-3) -> bool:
        """
        Return True if the recent weight-delta norms are all below tol.
        Requires at least history_window updates to make a determination.
        """
        if len(self._delta_history) < self.history_window:
            return False
        return max(self._delta_history) < tol

    def convergence_stats(self) -> Dict[str, float]:
        """Return mean / max / last weight-delta norms from recent history."""
        if not self._delta_history:
            return {"mean": 0.0, "max": 0.0, "last": 0.0, "updates": 0}
        return {
            "mean": float(np.mean(self._delta_history)),
            "max": float(np.max(self._delta_history)),
            "last": float(self._delta_history[-1]),
            "updates": self._update_count,
        }

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def get_weights(self) -> np.ndarray:
        """Return the current weight vector."""
        return self.weights.copy()

    def set_weights(self, weights: np.ndarray) -> None:
        """Overwrite weights (e.g. after loading from disk)."""
        self.weights = np.array(weights, dtype=float)

    def save(self, filepath: str) -> None:
        """Persist weights and metadata to a JSON file."""
        data = {
            "feature_size": self.feature_size,
            "learning_rate": self.learning_rate,
            "l2_reg": self.l2_reg,
            "update_count": self._update_count,
            "weights": self.weights.tolist(),
        }
        Path(filepath).write_text(json.dumps(data, indent=2))
        logger.info(f"ValueLearningAgent saved to {filepath}")

    @classmethod
    def load(cls, filepath: str) -> "ValueLearningAgent":
        """Load a previously saved agent from a JSON file."""
        data = json.loads(Path(filepath).read_text())
        agent = cls(
            feature_size=data["feature_size"],
            learning_rate=data["learning_rate"],
            l2_reg=data.get("l2_reg", 1e-3),
        )
        agent.weights = np.array(data["weights"], dtype=float)
        agent._update_count = data.get("update_count", 0)
        logger.info(f"ValueLearningAgent loaded from {filepath}")
        return agent

    def __repr__(self) -> str:
        stats = self.convergence_stats()
        return (
            f"ValueLearningAgent(feature_size={self.feature_size}, "
            f"updates={stats['updates']}, "
            f"converged={self.is_converged()}, "
            f"weights={np.round(self.weights, 3)})"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    if x >= 0:
        return 1.0 / (1.0 + np.exp(-x))
    e = np.exp(x)
    return e / (1.0 + e)
