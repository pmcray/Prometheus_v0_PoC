"""
tests/adversarial/test_data_poisoning.py — WP3 Adversarial Robustness

Data poisoning tests against the value-learning (IRL) pipeline.

Attack surface
--------------
PreferenceBuffer.add() and ValueLearningAgent accept arbitrary numpy arrays
as feature vectors with no validation.  An adversary who can inject
preference pairs can:

  1. Corrupt the learned reward function so the agent maximises a false
     objective (reward hacking).
  2. Destabilise training via NaN/Inf injection.
  3. Dominate the buffer with mislabelled pairs (label-flip attack).
  4. Shift weights towards adversarial directions (gradient attack).

Tests
-----
  CLASS TestPreferenceBufferPoisoning  — buffer-level injection resistance
  CLASS TestValueLearningPoisoning     — end-to-end training corruption
  CLASS TestDataValidator              — unit tests for DataValidator defence

Run with:
    pytest tests/adversarial/test_data_poisoning.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from prometheus.value_learning import PreferenceBuffer, ValueLearningAgent
from prometheus.adversarial_robustness import DataValidator, AdversarialRobustnessError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

N_FEATS = 5
RNG     = np.random.default_rng(42)


def _random_pair(n: int = N_FEATS) -> Tuple[np.ndarray, np.ndarray]:
    """Return a valid (preferred, unpreferred) feature pair."""
    a = RNG.uniform(0, 1, n).astype(float)
    b = RNG.uniform(0, 1, n).astype(float)
    return a, b


def _make_synthetic_pairs(
    n_pairs: int = 30, n_feats: int = N_FEATS, seed: int = 0
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    Generate synthetic preference pairs using a fixed true reward vector.
    Preferred trajectory always has higher dot product with true_w.
    """
    rng    = np.random.default_rng(seed)
    true_w = rng.normal(0, 1, n_feats)
    pairs  = []
    for _ in range(n_pairs):
        a = rng.uniform(0, 1, n_feats)
        b = rng.uniform(0, 1, n_feats)
        if np.dot(true_w, a) >= np.dot(true_w, b):
            pairs.append((a, b))
        else:
            pairs.append((b, a))
    return pairs


def _train_clean(n_epochs: int = 30) -> ValueLearningAgent:
    """Return an agent trained on clean synthetic data."""
    pairs = _make_synthetic_pairs(n_pairs=40, seed=0)
    agent = ValueLearningAgent(feature_size=N_FEATS)
    agent.train_to_convergence(pairs, max_epochs=n_epochs)
    return agent


# ---------------------------------------------------------------------------
# PreferenceBuffer poisoning
# ---------------------------------------------------------------------------

class TestPreferenceBufferPoisoning:

    def test_nan_feature_rejected_by_validator(self):
        """NaN in a feature vector must be caught by DataValidator."""
        validator = DataValidator(n_features=N_FEATS)
        nan_feat  = np.array([0.1, float("nan"), 0.3, 0.4, 0.5])
        with pytest.raises(AdversarialRobustnessError, match="NaN"):
            validator.validate_features(nan_feat)

    def test_inf_feature_rejected_by_validator(self):
        validator = DataValidator(n_features=N_FEATS)
        inf_feat  = np.array([0.1, float("inf"), 0.3, 0.4, 0.5])
        with pytest.raises(AdversarialRobustnessError, match="[Ii]nf"):
            validator.validate_features(inf_feat)

    def test_wrong_dimension_rejected(self):
        validator = DataValidator(n_features=N_FEATS)
        wrong     = np.array([0.1, 0.2])   # only 2 features
        with pytest.raises(AdversarialRobustnessError, match="dimension"):
            validator.validate_features(wrong)

    def test_extreme_magnitude_flagged(self):
        """Feature values many σ from normal range should be flagged."""
        validator = DataValidator(n_features=N_FEATS)
        extreme   = np.array([1e9, 1e9, 1e9, 1e9, 1e9])
        with pytest.raises(AdversarialRobustnessError):
            validator.validate_features(extreme)

    def test_valid_features_pass(self):
        validator = DataValidator(n_features=N_FEATS)
        good      = np.array([0.2, 0.5, 0.8, 0.1, 0.6])
        validator.validate_features(good)  # must not raise

    def test_buffer_accepts_valid_pairs(self):
        buf = PreferenceBuffer(max_size=50)
        for _ in range(10):
            a, b = _random_pair()
            buf.add(a, b)
        assert len(buf) == 10

    def test_buffer_fifo_capacity(self):
        """Buffer must not grow beyond max_size."""
        buf = PreferenceBuffer(max_size=5)
        for _ in range(10):
            buf.add(*_random_pair())
        assert len(buf) == 5

    def test_label_flip_does_not_corrupt_forever(self):
        """
        Label-flip: inject (unpreferred, preferred) pairs (reversed labels)
        alongside clean pairs.  Re-training on a 50/50 mix should produce
        weights that are not identical to the fully-flipped direction.
        """
        clean_pairs   = _make_synthetic_pairs(n_pairs=20, seed=0)
        agent         = ValueLearningAgent(feature_size=N_FEATS, learning_rate=0.05)

        # Train on clean data first
        agent.train_to_convergence(clean_pairs, max_epochs=10)
        weights_before = agent.weights.copy()

        # Inject 5 flipped (poisoned) pairs and retrain on the mix
        poisoned = [(b, a) for a, b in clean_pairs[:5]]
        mixed    = clean_pairs + poisoned
        agent.train_to_convergence(mixed, max_epochs=5)
        weights_after = agent.weights.copy()

        # Weights should change but not flip sign completely
        cos_sim = float(np.dot(weights_before, weights_after) /
                        (np.linalg.norm(weights_before) * np.linalg.norm(weights_after) + 1e-9))
        # With only 5 flipped out of 25, weights should still be somewhat aligned
        assert cos_sim > -0.5, \
            f"Label-flip attack caused full weight reversal (cosine={cos_sim:.3f})"


# ---------------------------------------------------------------------------
# ValueLearningAgent poisoning
# ---------------------------------------------------------------------------

class TestValueLearningPoisoning:

    def test_nan_injection_does_not_corrupt_weights(self):
        """
        Injecting NaN features into the buffer must not propagate NaN to
        the weight vector (existing code converts to float but doesn't validate).
        Verify that DataValidator prevents this.
        """
        validator = DataValidator(n_features=N_FEATS)
        nan_vec   = np.array([float("nan")] * N_FEATS)
        good_vec  = np.ones(N_FEATS) * 0.5
        with pytest.raises(AdversarialRobustnessError):
            validator.validate_features(nan_vec)
        # good_vec still passes
        validator.validate_features(good_vec)

    def test_gradient_attack_bounded(self):
        """
        Gradient attack: inject extreme-value pairs to maximally shift weights.
        L2 regularisation should keep the weight norm bounded.
        """
        clean_pairs  = _make_synthetic_pairs(n_pairs=30, seed=1)
        agent        = ValueLearningAgent(feature_size=N_FEATS,
                                          learning_rate=0.02, l2_reg=0.01)
        agent.train_to_convergence(clean_pairs, max_epochs=30)

        # Gradient attack: 10 extreme pairs aligned with e_0 direction
        attack_vec  = np.zeros(N_FEATS)
        attack_vec[0] = 100.0
        attack_pairs = [(attack_vec, np.zeros(N_FEATS))] * 10
        agent.train_to_convergence(attack_pairs, max_epochs=5)

        assert np.linalg.norm(agent.weights) < 50.0, \
            f"Weight norm exploded after gradient attack: {np.linalg.norm(agent.weights):.1f}"

    def test_convergence_preserved_under_mild_noise(self):
        """
        Adding small Gaussian noise to feature vectors (mild poisoning) should
        not prevent weights from remaining finite.
        """
        rng         = np.random.default_rng(99)
        clean_pairs = _make_synthetic_pairs(n_pairs=60, seed=2)
        # Add mild noise (σ=0.05)
        noisy_pairs = [
            (pref + rng.normal(0, 0.05, N_FEATS),
             unpref + rng.normal(0, 0.05, N_FEATS))
            for pref, unpref in clean_pairs
        ]
        agent = ValueLearningAgent(feature_size=N_FEATS)
        agent.train_to_convergence(noisy_pairs, max_epochs=40)
        assert np.all(np.isfinite(agent.weights)), \
            "Weights contain NaN/Inf after noisy training"

    def test_training_produces_finite_weights(self):
        """Standard clean training must always yield finite weights."""
        agent = _train_clean(n_epochs=50)
        assert np.all(np.isfinite(agent.weights)), \
            "Weights are not finite after clean training"


# ---------------------------------------------------------------------------
# DataValidator unit tests
# ---------------------------------------------------------------------------

class TestDataValidator:

    def setup_method(self):
        self.val = DataValidator(n_features=N_FEATS)

    def test_valid_zero_vector(self):
        self.val.validate_features(np.zeros(N_FEATS))

    def test_valid_unit_vector(self):
        self.val.validate_features(np.ones(N_FEATS))

    def test_nan_rejected(self):
        with pytest.raises(AdversarialRobustnessError):
            self.val.validate_features(np.array([np.nan, 0, 0, 0, 0]))

    def test_inf_rejected(self):
        with pytest.raises(AdversarialRobustnessError):
            self.val.validate_features(np.array([np.inf, 0, 0, 0, 0]))

    def test_neg_inf_rejected(self):
        with pytest.raises(AdversarialRobustnessError):
            self.val.validate_features(np.array([-np.inf, 0, 0, 0, 0]))

    def test_wrong_shape_1d_rejected(self):
        with pytest.raises(AdversarialRobustnessError):
            self.val.validate_features(np.zeros(N_FEATS + 3))

    def test_2d_array_rejected(self):
        with pytest.raises(AdversarialRobustnessError):
            self.val.validate_features(np.zeros((N_FEATS, 1)))

    def test_clip_extreme_values(self):
        """validate_and_clip() should return a bounded array."""
        extreme = np.array([1e9, -1e9, 0.5, 0.5, 0.5])
        clipped = self.val.validate_and_clip(extreme)
        assert np.all(np.isfinite(clipped))
        assert np.all(np.abs(clipped) <= self.val.clip_value + 1e-6)

    def test_validate_pair_both_valid(self):
        a = np.ones(N_FEATS) * 0.3
        b = np.ones(N_FEATS) * 0.7
        self.val.validate_pair(a, b)  # must not raise

    def test_validate_pair_one_invalid(self):
        a = np.ones(N_FEATS) * 0.3
        b = np.array([np.nan] * N_FEATS)
        with pytest.raises(AdversarialRobustnessError):
            self.val.validate_pair(a, b)

    def test_batch_validation(self):
        """validate_batch() must accept a list of valid arrays."""
        batch = [np.random.rand(N_FEATS) for _ in range(20)]
        self.val.validate_batch(batch)  # must not raise

    def test_batch_with_poison_raises(self):
        batch = [np.random.rand(N_FEATS) for _ in range(5)]
        batch.append(np.array([np.nan] * N_FEATS))  # poison
        with pytest.raises(AdversarialRobustnessError):
            self.val.validate_batch(batch)
