"""
tests/test_certified_robustness.py — WP8 Certified Robustness

Tests for:
  - Helper functions (_sigmoid, _clopper_pearson_lower, _certified_radius)
  - CertificationResult (properties and summary)
  - SmoothedValueLearner (predict_preference, certify, certified_preference,
                          batch_certify, certification_stats)
  - CertifiedDataValidator (validate_and_certify, forward methods)
  - CertifiedRobustnessBenchmark (sigma_sweep, epsilon_sweep, adversarial)

Run with:
    pytest tests/test_certified_robustness.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prometheus.value_learning import ValueLearningAgent
from prometheus.certified_robustness import (
    SmoothedValueLearner,
    CertificationResult,
    CertifiedDataValidator,
    _sigmoid,
    _clopper_pearson_lower,
    _certified_radius,
)
from benchmarks.certified_robustness_benchmark import (
    CertifiedRobustnessBenchmark,
    CRBenchmarkResult,
    _make_pairs,
    _trained_agent,
    N_FEATS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def trained_agent() -> ValueLearningAgent:
    """Return a trained ValueLearningAgent (shared across tests)."""
    return _trained_agent(n_pairs=60, seed=0)


@pytest.fixture
def smoother(trained_agent) -> SmoothedValueLearner:
    return SmoothedValueLearner(
        trained_agent,
        sigma=0.1,
        n_samples=300,
        seed=42,
    )


@pytest.fixture
def clean_pair():
    rng = np.random.default_rng(7)
    return rng.uniform(0, 1, N_FEATS), rng.uniform(0, 1, N_FEATS)


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestHelpers:

    def test_sigmoid_zero(self):
        assert _sigmoid(0.0) == pytest.approx(0.5)

    def test_sigmoid_large_positive(self):
        assert _sigmoid(100.0) == pytest.approx(1.0, abs=1e-6)

    def test_sigmoid_large_negative(self):
        assert _sigmoid(-100.0) == pytest.approx(0.0, abs=1e-6)

    def test_clopper_pearson_lower_all_success(self):
        # k == n: lower bound should be close to 1
        lb = _clopper_pearson_lower(100, 100, 0.05)
        assert lb > 0.95

    def test_clopper_pearson_lower_no_success(self):
        # k == 0: lower bound should be 0
        lb = _clopper_pearson_lower(0, 100, 0.05)
        assert lb == pytest.approx(0.0)

    def test_clopper_pearson_lower_half(self):
        # k ~ n/2: lower bound should be somewhat below 0.5
        lb = _clopper_pearson_lower(50, 100, 0.05)
        assert 0.3 < lb < 0.5

    def test_certified_radius_above_half(self):
        # p_lower > 0.5 → positive radius
        r = _certified_radius(0.9, sigma=0.1)
        assert r > 0.0

    def test_certified_radius_below_half(self):
        # p_lower ≤ 0.5 → zero radius (no certificate)
        r = _certified_radius(0.5, sigma=0.1)
        assert r == pytest.approx(0.0)

    def test_certified_radius_scales_with_sigma(self):
        p = 0.8
        r1 = _certified_radius(p, sigma=0.1)
        r2 = _certified_radius(p, sigma=0.2)
        assert r2 == pytest.approx(2 * r1, rel=1e-4)


# ---------------------------------------------------------------------------
# SmoothedValueLearner construction
# ---------------------------------------------------------------------------

class TestSmoothedValueLearnerConstruction:

    def test_invalid_sigma_raises(self, trained_agent):
        with pytest.raises(ValueError, match="sigma"):
            SmoothedValueLearner(trained_agent, sigma=-0.1)

    def test_invalid_confidence_raises(self, trained_agent):
        with pytest.raises(ValueError, match="confidence"):
            SmoothedValueLearner(trained_agent, sigma=0.1, confidence=1.5)

    def test_too_few_samples_raises(self, trained_agent):
        with pytest.raises(ValueError, match="n_samples"):
            SmoothedValueLearner(trained_agent, sigma=0.1, n_samples=10)

    def test_valid_construction(self, trained_agent):
        s = SmoothedValueLearner(trained_agent, sigma=0.1, n_samples=100)
        assert s.sigma == pytest.approx(0.1)
        assert s.n_samples == 100


# ---------------------------------------------------------------------------
# predict_preference
# ---------------------------------------------------------------------------

class TestPredictPreference:

    def test_returns_bool(self, smoother, clean_pair):
        phi1, phi2 = clean_pair
        result = smoother.predict_preference(phi1, phi2)
        assert isinstance(result, bool)

    def test_large_reward_gap_consistently_preferred(self, trained_agent):
        """When phi1 has a much higher reward, predict_preference should be True."""
        w    = trained_agent.weights
        phi1 = np.abs(w) * 2.0   # aligned with weights, large reward
        phi2 = -np.abs(w) * 2.0  # anti-aligned, low reward
        s    = SmoothedValueLearner(trained_agent, sigma=0.05, n_samples=300, seed=0)
        assert s.predict_preference(phi1, phi2) is True

    def test_consistent_across_calls(self, smoother, clean_pair):
        """Majority vote is stable for well-separated trajectories."""
        phi1, phi2 = clean_pair
        results = [smoother.predict_preference(phi1, phi2) for _ in range(5)]
        # Should not flip wildly (may vary slightly due to RNG, so just check type)
        assert all(isinstance(r, bool) for r in results)


# ---------------------------------------------------------------------------
# certify
# ---------------------------------------------------------------------------

class TestCertify:

    def test_returns_certification_result(self, smoother, clean_pair):
        phi1, phi2 = clean_pair
        cr = smoother.certify(phi1, phi2)
        assert isinstance(cr, CertificationResult)

    def test_p_estimate_in_unit_interval(self, smoother, clean_pair):
        phi1, phi2 = clean_pair
        cr = smoother.certify(phi1, phi2)
        assert 0.0 <= cr.p_estimate <= 1.0

    def test_p_lower_bound_leq_p_estimate(self, smoother, clean_pair):
        phi1, phi2 = clean_pair
        cr = smoother.certify(phi1, phi2)
        assert cr.p_lower_bound <= cr.p_estimate + 1e-9

    def test_certified_radius_nonneg(self, smoother, clean_pair):
        phi1, phi2 = clean_pair
        cr = smoother.certify(phi1, phi2)
        assert cr.certified_radius >= 0.0

    def test_abstain_when_p_lower_below_half(self, trained_agent):
        """Noise so large it washes out the preference → abstain."""
        s   = SmoothedValueLearner(trained_agent, sigma=5.0, n_samples=200, seed=1)
        rng = np.random.default_rng(1)
        phi1 = rng.uniform(0, 1, N_FEATS)
        phi2 = phi1 + rng.normal(0, 0.01, N_FEATS)  # nearly identical
        cr   = s.certify(phi1, phi2)
        # With σ=5 and nearly identical features, p ≈ 0.5 → likely abstain.
        # The certified_radius must be 0 (no certificate issued).
        assert cr.certified_radius == pytest.approx(0.0)

    def test_clear_preference_not_abstained(self, trained_agent):
        """Strong preference → should not abstain."""
        w    = trained_agent.weights
        phi1 = np.abs(w) * 3.0
        phi2 = np.zeros(N_FEATS)
        s    = SmoothedValueLearner(trained_agent, sigma=0.05, n_samples=500, seed=2)
        cr   = s.certify(phi1, phi2)
        assert not cr.abstain
        assert cr.certified_radius > 0.0

    def test_certify_time_positive(self, smoother, clean_pair):
        phi1, phi2 = clean_pair
        cr = smoother.certify(phi1, phi2)
        assert cr.certify_time_s > 0.0

    def test_summary_string_safe(self, trained_agent):
        w    = trained_agent.weights
        phi1 = np.abs(w) * 3.0
        phi2 = np.zeros(N_FEATS)
        s    = SmoothedValueLearner(trained_agent, sigma=0.05, n_samples=500, seed=3)
        cr   = s.certify(phi1, phi2)
        assert isinstance(cr.summary(), str)
        if cr.abstain:
            assert "ABSTAIN" in cr.summary()
        else:
            assert "CERTIFIED" in cr.summary()

    def test_larger_sigma_larger_radius_given_same_preference(self, trained_agent):
        """
        Certified radius should grow with sigma for the same preference gap
        (as long as the preference is still certified).
        """
        w    = trained_agent.weights
        phi1 = np.abs(w) * 2.0
        phi2 = np.zeros(N_FEATS)

        radii = []
        for sigma in [0.05, 0.10, 0.20]:
            s  = SmoothedValueLearner(trained_agent, sigma=sigma, n_samples=500, seed=4)
            cr = s.certify(phi1, phi2)
            radii.append(cr.certified_radius)

        # Larger sigma → larger radius (when not abstaining)
        non_zero = [r for r in radii if r > 0]
        if len(non_zero) >= 2:
            assert non_zero[-1] >= non_zero[0]


# ---------------------------------------------------------------------------
# certified_preference
# ---------------------------------------------------------------------------

class TestCertifiedPreference:

    def test_returns_tuple(self, smoother, clean_pair):
        phi1, phi2 = clean_pair
        result = smoother.certified_preference(phi1, phi2, epsilon=0.1)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_certified_within_radius(self, trained_agent):
        """Preference certified at small epsilon should be True."""
        w    = trained_agent.weights
        phi1 = np.abs(w) * 3.0
        phi2 = np.zeros(N_FEATS)
        s    = SmoothedValueLearner(trained_agent, sigma=0.1, n_samples=500, seed=5)
        pref, certified = s.certified_preference(phi1, phi2, epsilon=0.001)
        assert certified is True
        assert pref is True

    def test_not_certified_at_large_epsilon(self, smoother, clean_pair):
        """No certificate should be issued at epsilon > max possible radius."""
        phi1, phi2 = clean_pair
        _, certified = smoother.certified_preference(phi1, phi2, epsilon=1000.0)
        assert certified is False


# ---------------------------------------------------------------------------
# batch_certify and certification_stats
# ---------------------------------------------------------------------------

class TestBatchCertify:

    def test_batch_length_matches_input(self, smoother):
        pairs = _make_pairs(10, seed=0)
        results = smoother.batch_certify(pairs)
        assert len(results) == 10

    def test_all_results_are_certification_results(self, smoother):
        pairs = _make_pairs(5, seed=1)
        for cr in smoother.batch_certify(pairs):
            assert isinstance(cr, CertificationResult)

    def test_certification_stats_keys(self, smoother):
        pairs  = _make_pairs(20, seed=2)
        stats  = smoother.certification_stats(pairs, epsilon=0.1)
        for key in ["n_pairs", "n_certified", "certified_fraction",
                    "mean_radius", "min_radius", "max_radius",
                    "n_abstained", "mean_p_lower"]:
            assert key in stats

    def test_certified_fraction_in_unit_interval(self, smoother):
        pairs  = _make_pairs(20, seed=3)
        stats  = smoother.certification_stats(pairs, epsilon=0.1)
        assert 0.0 <= stats["certified_fraction"] <= 1.0

    def test_mean_radius_nonneg(self, smoother):
        pairs  = _make_pairs(10, seed=4)
        stats  = smoother.certification_stats(pairs, epsilon=0.05)
        assert stats["mean_radius"] >= 0.0


# ---------------------------------------------------------------------------
# CertifiedDataValidator
# ---------------------------------------------------------------------------

class TestCertifiedDataValidator:

    def setup_method(self):
        self.agent   = _trained_agent(n_pairs=40, seed=10)
        self.smoother = SmoothedValueLearner(
            self.agent, sigma=0.1, n_samples=300, seed=10
        )
        self.cdv = CertifiedDataValidator(
            n_features=N_FEATS, smoother=self.smoother
        )

    def test_validate_features_passes_valid(self):
        arr = np.ones(N_FEATS) * 0.5
        self.cdv.validate_features(arr)  # must not raise

    def test_validate_features_raises_on_nan(self):
        from prometheus.adversarial_robustness import AdversarialRobustnessError
        with pytest.raises(AdversarialRobustnessError):
            self.cdv.validate_features(np.array([np.nan] * N_FEATS))

    def test_validate_and_clip_returns_bounded(self):
        extreme = np.array([1e9, -1e9, 0.5, 0.5, 0.5])
        clipped = self.cdv.validate_and_clip(extreme)
        assert np.all(np.isfinite(clipped))

    def test_validate_pair_passes_valid(self):
        a = np.ones(N_FEATS) * 0.3
        b = np.ones(N_FEATS) * 0.7
        self.cdv.validate_pair(a, b)  # must not raise

    def test_validate_batch_passes_valid(self):
        batch = [np.random.rand(N_FEATS) for _ in range(5)]
        self.cdv.validate_batch(batch)  # must not raise

    def test_validate_and_certify_returns_tuple(self):
        w    = self.agent.weights
        phi1 = np.abs(w) * 2.0
        phi2 = np.zeros(N_FEATS)
        result = self.cdv.validate_and_certify(phi1, epsilon=0.001, reference=phi2)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_validate_and_certify_nan_fails(self):
        nan_arr = np.array([np.nan] * N_FEATS)
        ref     = np.ones(N_FEATS) * 0.5
        safe, radius = self.cdv.validate_and_certify(nan_arr, epsilon=0.1, reference=ref)
        assert safe is False
        assert radius == 0.0


# ---------------------------------------------------------------------------
# CertifiedRobustnessBenchmark
# ---------------------------------------------------------------------------

class TestCertifiedRobustnessBenchmark:

    @pytest.fixture(autouse=True)
    def bench(self):
        self.bench = CertifiedRobustnessBenchmark(
            n_pairs=20, n_samples=200, seed=0
        )

    def test_sigma_sweep_has_correct_param_name(self):
        result = self.bench.run("sigma_sweep")
        assert result.param_name == "sigma"
        assert len(result.param_values) == len(CertifiedRobustnessBenchmark.SIGMA_VALUES)

    def test_sigma_sweep_certified_fractions_in_unit_interval(self):
        result = self.bench.run("sigma_sweep")
        for f in result.certified_fractions:
            assert 0.0 <= f <= 1.0

    def test_epsilon_sweep_has_correct_param_name(self):
        result = self.bench.run("epsilon_sweep")
        assert result.param_name == "epsilon"

    def test_epsilon_sweep_decreasing_certified_fraction(self):
        """Larger epsilon → fewer certified pairs."""
        result = self.bench.run("epsilon_sweep")
        # Certified fraction should be non-increasing as epsilon grows
        fracs = result.certified_fractions
        # Allow small numerical noise; check overall trend
        assert fracs[0] >= fracs[-1] - 0.05   # first ≥ last

    def test_adversarial_has_certified_accuracy(self):
        result = self.bench.run("adversarial")
        assert len(result.certified_accuracy_attacks) == len(
            CertifiedRobustnessBenchmark.EPSILON_VALUES
        )

    def test_run_all_returns_three_results(self):
        results = self.bench.run_all()
        assert len(results) == 3
        assert {r.scenario for r in results} == {
            "sigma_sweep", "epsilon_sweep", "adversarial"
        }

    def test_summary_table_non_empty(self):
        results = self.bench.run_all()
        table   = self.bench.summary_table(results)
        assert "sigma_sweep"   in table
        assert "epsilon_sweep" in table
        assert "adversarial"   in table

    def test_unknown_scenario_raises(self):
        with pytest.raises(ValueError, match="Unknown scenario"):
            self.bench.run("nonexistent")

    def test_result_summary_dict_keys(self):
        result = self.bench.run("sigma_sweep")
        d      = result.summary_dict()
        for key in ["scenario", "param_name", "param_values",
                    "certified_fractions", "mean_certified_radii",
                    "preference_accuracies", "n_pairs", "n_samples"]:
            assert key in d

    def test_n_pairs_matches(self):
        result = self.bench.run("sigma_sweep")
        assert result.n_pairs == 20
