"""
Unit tests for WP2 OOD Detection — Prometheus v0.97

Covers:
  - MahalanobisOODDetector: fit, score, normalised_score, is_ood, evaluate, save/load
  - ReconstructionOODDetector: fit, score, in-dist vs OOD ranking
  - EnsembleOODDetector: fit, score, evaluate
  - SafeModeProtocol: NORMAL, CAUTION, SAFE_MODE, HALT escalation + log/summary
  - MCSSupervisor OOD integration: attach_ood_detector, check_ood, ood_summary
  - OODBenchmark: run, run_all, AUROC, scenario generation
  - Domain generators: gridworld_in_distribution, arc_in_distribution
  - create_ood_detector factory
"""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from prometheus.ood_detection import (
    BaseOODDetector,
    EnsembleOODDetector,
    MahalanobisOODDetector,
    OODScore,
    ReconstructionOODDetector,
    SafeMode,
    SafeModeDecision,
    SafeModeProtocol,
    create_ood_detector,
)
from prometheus.safety.mcs_supervisor import MCSSupervisor
from benchmarks.ood_benchmark import (
    OODBenchmark,
    OODBenchmarkResult,
    ScenarioResult,
    arc_in_distribution,
    generate_in_distribution,
    generate_ood_mild,
    generate_ood_severe,
    gridworld_in_distribution,
    run_quick_ood_test,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FEATURE_SIZE = 6
N_TRAIN      = 100
RNG_SEED     = 0


@pytest.fixture
def train_features():
    return generate_in_distribution(FEATURE_SIZE, n=N_TRAIN, seed=RNG_SEED)


@pytest.fixture
def in_dist_sample(train_features):
    """A single sample drawn from in-distribution."""
    rng = np.random.default_rng(42)
    mu  = train_features.mean(axis=0)
    return mu + rng.standard_normal(FEATURE_SIZE) * 0.1


@pytest.fixture
def ood_sample(train_features):
    """A single severely OOD sample."""
    mu = train_features.mean(axis=0)
    return mu + 20.0  # far from mean in every dimension


@pytest.fixture
def fitted_mahalanobis(train_features):
    det = MahalanobisOODDetector(FEATURE_SIZE)
    det.fit(train_features)
    return det


@pytest.fixture
def fitted_reconstruction(train_features):
    det = ReconstructionOODDetector(FEATURE_SIZE, epochs=50)
    det.fit(train_features)
    return det


@pytest.fixture
def fitted_ensemble(train_features):
    det = EnsembleOODDetector(FEATURE_SIZE, epochs=50)
    det.fit(train_features)
    return det


# ---------------------------------------------------------------------------
# MahalanobisOODDetector
# ---------------------------------------------------------------------------

class TestMahalanobisOODDetector:

    def test_fit_sets_fitted_flag(self, train_features):
        det = MahalanobisOODDetector(FEATURE_SIZE)
        assert not det._fitted
        det.fit(train_features)
        assert det._fitted

    def test_score_returns_float(self, fitted_mahalanobis, in_dist_sample):
        s = fitted_mahalanobis.score(in_dist_sample)
        assert isinstance(s, float)
        assert s >= 0.0

    def test_score_higher_for_ood(self, fitted_mahalanobis, in_dist_sample, ood_sample):
        s_in  = fitted_mahalanobis.score(in_dist_sample)
        s_out = fitted_mahalanobis.score(ood_sample)
        assert s_out > s_in

    def test_normalised_score_in_dist_near_zero(self, fitted_mahalanobis, in_dist_sample):
        ns = fitted_mahalanobis.normalised_score(in_dist_sample)
        # in-distribution sample should be within a few sigma
        assert ns < 5.0

    def test_normalised_score_ood_high(self, fitted_mahalanobis, ood_sample):
        ns = fitted_mahalanobis.normalised_score(ood_sample)
        assert ns > 2.0

    def test_is_ood_in_dist_false(self, fitted_mahalanobis, in_dist_sample):
        assert not fitted_mahalanobis.is_ood(in_dist_sample, threshold=3.0)

    def test_is_ood_ood_true(self, fitted_mahalanobis, ood_sample):
        assert fitted_mahalanobis.is_ood(ood_sample, threshold=2.0)

    def test_evaluate_returns_ood_score(self, fitted_mahalanobis, in_dist_sample):
        result = fitted_mahalanobis.evaluate(in_dist_sample)
        assert isinstance(result, OODScore)
        assert result.detector_name == "mahalanobis"
        assert result.feature_vector.shape == (FEATURE_SIZE,)

    def test_evaluate_safe_mode_normal(self, fitted_mahalanobis, in_dist_sample):
        result = fitted_mahalanobis.evaluate(in_dist_sample)
        # Most in-dist samples should be NORMAL or CAUTION (not HALT)
        assert result.safe_mode in (SafeMode.NORMAL, SafeMode.CAUTION, SafeMode.SAFE_MODE)

    def test_evaluate_safe_mode_halt_for_severe_ood(self, fitted_mahalanobis, ood_sample):
        result = fitted_mahalanobis.evaluate(
            ood_sample, critical_threshold=5.0
        )
        assert result.safe_mode == SafeMode.HALT

    def test_raises_before_fit(self):
        det = MahalanobisOODDetector(FEATURE_SIZE)
        with pytest.raises(RuntimeError, match="not been fitted"):
            det.score(np.zeros(FEATURE_SIZE))

    def test_wrong_feature_size_raises(self, train_features):
        det = MahalanobisOODDetector(FEATURE_SIZE)
        with pytest.raises(ValueError, match="feature_size"):
            det.fit(train_features[:, :3])

    def test_save_load_roundtrip(self, fitted_mahalanobis, in_dist_sample):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        fitted_mahalanobis.save(path)
        loaded = MahalanobisOODDetector.load(path)
        assert loaded._fitted
        orig_score   = fitted_mahalanobis.score(in_dist_sample)
        loaded_score = loaded.score(in_dist_sample)
        assert abs(orig_score - loaded_score) < 1e-9

    def test_single_sample_fit(self):
        """Fit with N=1 should not crash (uses regularisation)."""
        det = MahalanobisOODDetector(FEATURE_SIZE, reg=1e-2)
        det.fit(np.zeros((1, FEATURE_SIZE)))
        s = det.score(np.ones(FEATURE_SIZE))
        assert isinstance(s, float)


# ---------------------------------------------------------------------------
# ReconstructionOODDetector
# ---------------------------------------------------------------------------

class TestReconstructionOODDetector:

    def test_fit_sets_fitted_flag(self, train_features):
        det = ReconstructionOODDetector(FEATURE_SIZE, epochs=10)
        det.fit(train_features)
        assert det._fitted

    def test_score_nonneg(self, fitted_reconstruction, in_dist_sample):
        s = fitted_reconstruction.score(in_dist_sample)
        assert s >= 0.0

    def test_ood_score_higher_than_in_dist(self, fitted_reconstruction, in_dist_sample, ood_sample):
        s_in  = fitted_reconstruction.score(in_dist_sample)
        s_out = fitted_reconstruction.score(ood_sample)
        assert s_out > s_in

    def test_bottleneck_default(self):
        det = ReconstructionOODDetector(FEATURE_SIZE)
        assert det.bottleneck_size == max(1, FEATURE_SIZE // 2)

    def test_custom_bottleneck(self):
        det = ReconstructionOODDetector(FEATURE_SIZE, bottleneck_size=1)
        assert det.bottleneck_size == 1

    def test_save_load_roundtrip(self, fitted_reconstruction, in_dist_sample):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        fitted_reconstruction.save(path)
        loaded = ReconstructionOODDetector.load(path)
        assert loaded._fitted
        orig   = fitted_reconstruction.score(in_dist_sample)
        loaded_s = loaded.score(in_dist_sample)
        assert abs(orig - loaded_s) < 1e-9

    def test_evaluate_returns_ood_score(self, fitted_reconstruction, in_dist_sample):
        result = fitted_reconstruction.evaluate(in_dist_sample)
        assert isinstance(result, OODScore)
        assert result.detector_name == "reconstruction"


# ---------------------------------------------------------------------------
# EnsembleOODDetector
# ---------------------------------------------------------------------------

class TestEnsembleOODDetector:

    def test_fit_both_sub_detectors(self, train_features):
        det = EnsembleOODDetector(FEATURE_SIZE, epochs=10)
        det.fit(train_features)
        assert det._maha._fitted
        assert det._recon._fitted

    def test_score_in_range(self, fitted_ensemble, in_dist_sample):
        s = fitted_ensemble.score(in_dist_sample)
        assert isinstance(s, float)
        assert s >= 0.0

    def test_ood_score_higher(self, fitted_ensemble, in_dist_sample, ood_sample):
        s_in  = fitted_ensemble.score(in_dist_sample)
        s_out = fitted_ensemble.score(ood_sample)
        assert s_out > s_in

    def test_custom_weights(self, train_features, in_dist_sample):
        det = EnsembleOODDetector(FEATURE_SIZE, weights=(0.9, 0.1), epochs=20)
        det.fit(train_features)
        s = det.score(in_dist_sample)
        assert isinstance(s, float)

    def test_evaluate_returns_ood_score(self, fitted_ensemble, in_dist_sample):
        result = fitted_ensemble.evaluate(in_dist_sample)
        assert isinstance(result, OODScore)
        assert result.detector_name == "ensemble"

    def test_is_ood_severe(self, fitted_ensemble, ood_sample):
        assert fitted_ensemble.is_ood(ood_sample, threshold=2.0)


# ---------------------------------------------------------------------------
# SafeModeProtocol
# ---------------------------------------------------------------------------

class TestSafeModeProtocol:

    def test_normal_decision(self, fitted_mahalanobis, in_dist_sample):
        proto    = SafeModeProtocol(fitted_mahalanobis, low_threshold=100.0)
        decision = proto.evaluate(in_dist_sample)
        assert isinstance(decision, SafeModeDecision)
        assert decision.safe_mode == SafeMode.NORMAL
        assert decision.allow_action is True
        assert decision.confidence_scale == 1.0
        assert decision.alert_supervisor is False

    def test_caution_decision(self, train_features):
        det = MahalanobisOODDetector(FEATURE_SIZE)
        det.fit(train_features)
        mu  = train_features.mean(axis=0)
        # Force score just above low threshold
        proto    = SafeModeProtocol(det, low_threshold=0.0, high_threshold=100.0, critical_threshold=200.0)
        decision = proto.evaluate(mu)
        assert decision.safe_mode in (SafeMode.NORMAL, SafeMode.CAUTION)

    def test_halt_decision(self, fitted_mahalanobis, ood_sample):
        proto    = SafeModeProtocol(fitted_mahalanobis,
                                    low_threshold=0.1, high_threshold=0.5, critical_threshold=1.0)
        decision = proto.evaluate(ood_sample)
        assert decision.safe_mode == SafeMode.HALT
        assert decision.allow_action is False
        assert decision.confidence_scale == 0.0
        assert decision.alert_supervisor is True

    def test_safe_mode_decision(self, fitted_mahalanobis, ood_sample):
        # Set critical very high so we land in SAFE_MODE not HALT
        proto    = SafeModeProtocol(fitted_mahalanobis,
                                    low_threshold=0.1, high_threshold=0.5, critical_threshold=9999.0)
        decision = proto.evaluate(ood_sample)
        assert decision.safe_mode == SafeMode.SAFE_MODE
        assert decision.allow_action is True   # SAFE_MODE still allows (with restriction)
        assert 0.0 < decision.confidence_scale < 1.0
        assert decision.alert_supervisor is True

    def test_log_accumulates(self, fitted_mahalanobis, in_dist_sample, ood_sample):
        proto = SafeModeProtocol(fitted_mahalanobis)
        proto.evaluate(in_dist_sample)
        proto.evaluate(ood_sample)
        assert len(proto.get_log()) == 2

    def test_summary_counts(self, fitted_mahalanobis, in_dist_sample, ood_sample):
        proto = SafeModeProtocol(
            fitted_mahalanobis,
            low_threshold=0.1, high_threshold=0.5, critical_threshold=1.0,
        )
        proto.evaluate(in_dist_sample)  # likely NORMAL
        proto.evaluate(ood_sample)      # HALT

        summary = proto.summary()
        assert summary["total"] == 2
        assert isinstance(summary["ood_rate"], float)
        assert isinstance(summary["halt_rate"], float)

    def test_summary_empty(self, fitted_mahalanobis):
        proto   = SafeModeProtocol(fitted_mahalanobis)
        summary = proto.summary()
        assert summary["total"] == 0


# ---------------------------------------------------------------------------
# MCSSupervisor OOD integration
# ---------------------------------------------------------------------------

class TestMCSSupervisorOOD:

    def test_no_detector_by_default(self):
        sup = MCSSupervisor()
        assert not sup.has_ood_detector

    def test_attach_detector(self, fitted_mahalanobis):
        sup = MCSSupervisor()
        sup.attach_ood_detector(fitted_mahalanobis)
        assert sup.has_ood_detector

    def test_constructor_with_detector(self, fitted_mahalanobis):
        sup = MCSSupervisor(ood_detector=fitted_mahalanobis)
        assert sup.has_ood_detector

    def test_check_ood_without_detector_raises(self):
        sup = MCSSupervisor()
        with pytest.raises(RuntimeError, match="No OOD detector"):
            sup.check_ood(np.zeros(FEATURE_SIZE))

    def test_check_ood_returns_decision(self, fitted_mahalanobis, in_dist_sample):
        sup = MCSSupervisor(ood_detector=fitted_mahalanobis)
        decision = sup.check_ood(in_dist_sample)
        assert isinstance(decision, SafeModeDecision)

    def test_check_ood_blocks_severe_ood(self, fitted_mahalanobis, ood_sample):
        sup = MCSSupervisor(ood_detector=fitted_mahalanobis)
        # Use tight thresholds so severe OOD triggers HALT
        sup.attach_ood_detector(
            fitted_mahalanobis,
            low_threshold=0.1, high_threshold=0.5, critical_threshold=1.0,
        )
        decision = sup.check_ood(ood_sample)
        assert not decision.allow_action

    def test_ood_summary_no_detector(self):
        sup     = MCSSupervisor()
        summary = sup.ood_summary()
        assert "error" in summary

    def test_ood_summary_with_detector(self, fitted_mahalanobis, in_dist_sample):
        sup = MCSSupervisor(ood_detector=fitted_mahalanobis)
        sup.check_ood(in_dist_sample)
        summary = sup.ood_summary()
        assert summary["total"] == 1

    def test_existing_verify_modification_still_works(self, fitted_mahalanobis):
        """OOD integration must not break constitutional code checks."""
        sup = MCSSupervisor(ood_detector=fitted_mahalanobis)
        safe_code  = "def foo(x):\n    return x + 1\n"
        unsafe_code = "import os\ndef foo(x):\n    os.system('rm -rf /')\n    return x\n"
        critique_ok  = sup.verify_modification(safe_code,   safe_code,   "foo.py")
        critique_bad = sup.verify_modification(safe_code, unsafe_code, "foo.py")
        assert critique_ok.is_safe
        assert not critique_bad.is_safe


# ---------------------------------------------------------------------------
# create_ood_detector factory
# ---------------------------------------------------------------------------

class TestCreateOODDetector:

    @pytest.mark.parametrize("det_type", ["mahalanobis", "reconstruction", "ensemble"])
    def test_factory_creates_correct_type(self, det_type):
        det = create_ood_detector(det_type, feature_size=FEATURE_SIZE)
        assert hasattr(det, "fit")
        assert hasattr(det, "score")
        assert hasattr(det, "evaluate")

    def test_factory_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown detector_type"):
            create_ood_detector("nonexistent", feature_size=FEATURE_SIZE)

    def test_factory_kwargs_forwarded(self):
        det = create_ood_detector("mahalanobis", feature_size=FEATURE_SIZE, reg=1e-2)
        assert det.reg == 1e-2


# ---------------------------------------------------------------------------
# Data generators
# ---------------------------------------------------------------------------

class TestDataGenerators:

    def test_in_distribution_shape(self):
        data = generate_in_distribution(FEATURE_SIZE, n=50, seed=0)
        assert data.shape == (50, FEATURE_SIZE)

    def test_mild_shift_shape(self):
        train = generate_in_distribution(FEATURE_SIZE, n=50, seed=0)
        mild  = generate_ood_mild(train, n=30, shift_sigma=3.0, seed=1)
        assert mild.shape == (30, FEATURE_SIZE)

    def test_severe_shift_strategies(self):
        for strategy in ["uniform_far", "constant", "zeros", "adversarial"]:
            data = generate_ood_severe(FEATURE_SIZE, n=20, seed=0, strategy=strategy)
            assert data.shape == (20, FEATURE_SIZE), f"Failed for strategy={strategy}"

    def test_severe_shift_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            generate_ood_severe(FEATURE_SIZE, n=10, strategy="invalid")

    def test_gridworld_in_distribution_shape(self):
        data = gridworld_in_distribution(n=50, seed=0)
        assert data.shape == (50, 6)

    def test_gridworld_values_in_range(self):
        data = gridworld_in_distribution(n=100, seed=0)
        assert data.min() >= 0.0
        # Most features should be <= 2.0 (normalised)
        assert data[:, :4].max() <= 2.0

    def test_arc_in_distribution_shape(self):
        data = arc_in_distribution(n=50, seed=0)
        assert data.shape == (50, 8)


# ---------------------------------------------------------------------------
# OODBenchmark
# ---------------------------------------------------------------------------

class TestOODBenchmark:

    @pytest.fixture
    def bench(self):
        return OODBenchmark(feature_size=FEATURE_SIZE, n_train=80, n_in_dist=50,
                            n_mild=30, n_severe=30, seed=42)

    def test_run_returns_result(self, bench):
        det    = MahalanobisOODDetector(FEATURE_SIZE)
        result = bench.run(det, verbose=False)
        assert isinstance(result, OODBenchmarkResult)
        assert result.detector_name == "mahalanobis"

    def test_result_has_three_scenarios(self, bench):
        det    = MahalanobisOODDetector(FEATURE_SIZE)
        result = bench.run(det, verbose=False)
        assert set(result.scenarios.keys()) == {
            "in_distribution", "mild_shift", "severe_shift"
        }

    def test_auroc_in_range(self, bench):
        det    = MahalanobisOODDetector(FEATURE_SIZE)
        result = bench.run(det, verbose=False)
        assert 0.0 <= result.auroc <= 1.0

    def test_tpr_fpr_in_range(self, bench):
        det    = MahalanobisOODDetector(FEATURE_SIZE)
        result = bench.run(det, verbose=False)
        assert 0.0 <= result.tpr <= 1.0
        assert 0.0 <= result.fpr <= 1.0

    def test_severe_ood_rate_higher_than_in_dist(self, bench):
        det    = MahalanobisOODDetector(FEATURE_SIZE)
        result = bench.run(det, verbose=False)
        r_in   = result.scenarios["in_distribution"].ood_rate
        r_sev  = result.scenarios["severe_shift"].ood_rate
        assert r_sev >= r_in

    def test_run_all_returns_sorted_list(self, bench):
        results = bench.run_all(verbose=False)
        assert len(results) >= 2
        aurocs = [r.auroc for r in results]
        assert aurocs == sorted(aurocs, reverse=True)

    def test_wall_clock_positive(self, bench):
        det    = MahalanobisOODDetector(FEATURE_SIZE)
        result = bench.run(det, verbose=False)
        assert result.wall_clock_s > 0.0

    def test_summary_line_string(self, bench):
        det    = MahalanobisOODDetector(FEATURE_SIZE)
        result = bench.run(det, verbose=False)
        line   = result.summary_line()
        assert "AUROC" in line
        assert "TPR"   in line

    def test_run_quick_ood_test(self):
        result = run_quick_ood_test(
            detector_type="mahalanobis",
            feature_size=FEATURE_SIZE,
            n_train=80,
            seed=0,
            verbose=False,
        )
        assert isinstance(result, OODBenchmarkResult)
        assert result.auroc > 0.5   # should beat random for severe OOD

    def test_auroc_computation(self):
        """AUROC should be high (>0.8) when scores clearly separate OOD from in-dist."""
        scores = np.array([0.1, 0.2, 0.3, 5.0, 6.0, 7.0])
        labels = np.array([0,   0,   0,   1,   1,   1  ])
        auroc  = OODBenchmark._compute_auroc(scores, labels)
        assert auroc > 0.8

    def test_auroc_random(self):
        """AUROC should be ~0.5 for random scores."""
        rng    = np.random.default_rng(0)
        scores = rng.standard_normal(200)
        labels = rng.integers(0, 2, 200)
        auroc  = OODBenchmark._compute_auroc(scores, labels)
        assert 0.3 < auroc < 0.7
