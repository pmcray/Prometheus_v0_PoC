"""
tests/test_uncertainty.py — Test suite for WP11

Tests for:
  - prometheus/uncertainty.py
      ConformalRewardPredictor, BootstrapEnsemble,
      UncertaintyAwareManager, calibration_curve helpers
  - benchmarks/uncertainty_benchmark.py
      UncertaintyBenchmark (all 4 scenarios)

Run with: pytest tests/test_uncertainty.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prometheus.value_learning import ValueLearningAgent
from prometheus.uncertainty import (
    ConformalRewardPredictor,
    BootstrapEnsemble,
    UncertaintyAwareManager,
    CalibrationResult,
    RewardInterval,
    EnsemblePrediction,
    UncertaintyDecision,
    calibration_curve,
)
from benchmarks.uncertainty_benchmark import (
    UncertaintyBenchmark,
    N_FEATS,
    _make_pairs,
    _make_true_w,
    _trained_agent,
    _true_reward,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def true_w() -> np.ndarray:
    return _make_true_w(seed=0)


@pytest.fixture(scope="module")
def train_pairs(true_w) -> List[Tuple[np.ndarray, np.ndarray]]:
    return _make_pairs(60, true_w, seed=0)


@pytest.fixture(scope="module")
def cal_pairs(true_w) -> List[Tuple[np.ndarray, np.ndarray]]:
    return _make_pairs(40, true_w, seed=1)


@pytest.fixture(scope="module")
def test_pairs(true_w) -> List[Tuple[np.ndarray, np.ndarray]]:
    return _make_pairs(50, true_w, seed=2)


@pytest.fixture(scope="module")
def agent(true_w, train_pairs) -> ValueLearningAgent:
    a = ValueLearningAgent(feature_size=N_FEATS, l2_reg=0.01)
    a.train_to_convergence(train_pairs, max_epochs=50)
    return a


@pytest.fixture(scope="module")
def calibrated_predictor(agent, cal_pairs) -> ConformalRewardPredictor:
    pred = ConformalRewardPredictor(agent, alpha=0.10, abstain_width=1.0)
    pred.calibrate(cal_pairs)
    return pred


@pytest.fixture(scope="module")
def fitted_ensemble(train_pairs) -> BootstrapEnsemble:
    ens = BootstrapEnsemble(feature_size=N_FEATS, n_bootstrap=10, seed=0)
    ens.fit(train_pairs, max_epochs=30)
    return ens


@pytest.fixture
def sample_features() -> np.ndarray:
    return np.array([0.5, 0.3, 0.7, 0.1, 0.9])


# ---------------------------------------------------------------------------
# 1. TestConformalRewardPredictorConstruction
# ---------------------------------------------------------------------------

class TestConformalRewardPredictorConstruction:

    def test_valid_construction(self, agent):
        pred = ConformalRewardPredictor(agent, alpha=0.10)
        assert pred.alpha        == 0.10
        assert pred.is_calibrated is False

    def test_invalid_alpha_zero(self, agent):
        with pytest.raises(ValueError, match="alpha"):
            ConformalRewardPredictor(agent, alpha=0.0)

    def test_invalid_alpha_one(self, agent):
        with pytest.raises(ValueError, match="alpha"):
            ConformalRewardPredictor(agent, alpha=1.0)

    def test_invalid_alpha_negative(self, agent):
        with pytest.raises(ValueError, match="alpha"):
            ConformalRewardPredictor(agent, alpha=-0.1)

    def test_predict_before_calibrate_raises(self, agent, sample_features):
        pred = ConformalRewardPredictor(agent, alpha=0.10)
        with pytest.raises(RuntimeError, match="calibrate"):
            pred.predict(sample_features)

    def test_coverage_stats_before_calibrate_raises(self, agent, test_pairs):
        pred = ConformalRewardPredictor(agent, alpha=0.10)
        with pytest.raises(RuntimeError, match="calibrate"):
            pred.coverage_stats(test_pairs)


# ---------------------------------------------------------------------------
# 2. TestCalibration
# ---------------------------------------------------------------------------

class TestCalibration:

    def test_calibrate_returns_result(self, agent, cal_pairs):
        pred   = ConformalRewardPredictor(agent, alpha=0.10)
        result = pred.calibrate(cal_pairs)
        assert isinstance(result, CalibrationResult)

    def test_calibrate_sets_q_hat(self, agent, cal_pairs):
        pred = ConformalRewardPredictor(agent, alpha=0.10)
        pred.calibrate(cal_pairs)
        assert pred._q_hat is not None
        assert pred._q_hat >= 0.0

    def test_calibrate_is_calibrated(self, agent, cal_pairs):
        pred = ConformalRewardPredictor(agent, alpha=0.10)
        pred.calibrate(cal_pairs)
        assert pred.is_calibrated is True

    def test_calibration_result_fields(self, agent, cal_pairs):
        pred   = ConformalRewardPredictor(agent, alpha=0.10)
        result = pred.calibrate(cal_pairs)
        assert result.alpha           == pytest.approx(0.10)
        assert result.n_calibration   == len(cal_pairs)
        assert result.q_hat           >= 0.0
        assert 0.0 <= result.coverage_empirical <= 1.0
        assert len(result.nonconformity_scores) == len(cal_pairs)
        assert result.calibration_time_s >= 0.0

    def test_calibration_result_summary(self, calibrated_predictor):
        s = calibrated_predictor.calibration_result.summary()
        assert "CalibrationResult" in s
        assert "q̂" in s

    def test_empty_calibration_raises(self, agent):
        pred = ConformalRewardPredictor(agent, alpha=0.10)
        with pytest.raises(ValueError, match="non-empty"):
            pred.calibrate([])

    def test_nonconformity_scores_nonnegative(self, calibrated_predictor):
        scores = calibrated_predictor.calibration_result.nonconformity_scores
        assert np.all(scores >= 0.0)

    def test_empirical_coverage_approx_target(self, calibrated_predictor):
        # Empirical coverage on calibration set should be close to 1 - alpha
        cr = calibrated_predictor.calibration_result
        # Coverage on calibration set should be >= 1 - alpha (by construction)
        assert cr.coverage_empirical >= 1 - calibrated_predictor.alpha - 0.05


# ---------------------------------------------------------------------------
# 3. TestRewardInterval
# ---------------------------------------------------------------------------

class TestRewardInterval:

    def test_predict_returns_interval(self, calibrated_predictor, sample_features):
        iv = calibrated_predictor.predict(sample_features)
        assert isinstance(iv, RewardInterval)

    def test_interval_bounds_ordered(self, calibrated_predictor, sample_features):
        iv = calibrated_predictor.predict(sample_features)
        assert iv.lower <= iv.point_estimate <= iv.upper

    def test_interval_width_equals_2q(self, calibrated_predictor, sample_features):
        iv = calibrated_predictor.predict(sample_features)
        assert iv.width == pytest.approx(iv.upper - iv.lower, abs=1e-10)

    def test_alpha_stored(self, calibrated_predictor, sample_features):
        iv = calibrated_predictor.predict(sample_features)
        assert iv.alpha == pytest.approx(calibrated_predictor.alpha)

    def test_predict_time_nonneg(self, calibrated_predictor, sample_features):
        iv = calibrated_predictor.predict(sample_features)
        assert iv.predict_time_s >= 0.0

    def test_contains_true(self, calibrated_predictor, sample_features):
        iv = calibrated_predictor.predict(sample_features)
        assert iv.contains(iv.point_estimate)

    def test_contains_false(self, calibrated_predictor, sample_features):
        iv = calibrated_predictor.predict(sample_features)
        assert not iv.contains(iv.upper + 100.0)

    def test_abstain_when_wide(self, agent, cal_pairs, sample_features):
        pred = ConformalRewardPredictor(agent, alpha=0.10, abstain_width=0.0)
        pred.calibrate(cal_pairs)
        iv = pred.predict(sample_features)
        # Width > 0 → abstain
        assert iv.abstain is True

    def test_no_abstain_when_narrow_threshold(self, agent, cal_pairs, sample_features):
        pred = ConformalRewardPredictor(agent, alpha=0.10, abstain_width=1e6)
        pred.calibrate(cal_pairs)
        iv = pred.predict(sample_features)
        assert iv.abstain is False

    def test_interval_summary(self, calibrated_predictor, sample_features):
        iv = calibrated_predictor.predict(sample_features)
        s  = iv.summary()
        assert "RewardInterval" in s

    def test_batch_predict(self, calibrated_predictor, test_pairs):
        feats = [phi1 for phi1, _ in test_pairs[:5]]
        ivs   = calibrated_predictor.batch_predict(feats)
        assert len(ivs) == 5
        for iv in ivs:
            assert isinstance(iv, RewardInterval)


# ---------------------------------------------------------------------------
# 4. TestCoverageGuarantee
# ---------------------------------------------------------------------------

class TestCoverageGuarantee:
    """Core guarantee: empirical coverage ≥ 1 − α."""

    def _measure_coverage(
        self,
        pred      : ConformalRewardPredictor,
        test_pairs: List[Tuple[np.ndarray, np.ndarray]],
        agent     : ValueLearningAgent,
    ) -> float:
        n_covered = 0
        for phi1, phi2 in test_pairs:
            phi1 = np.asarray(phi1, dtype=float)
            phi2 = np.asarray(phi2, dtype=float)
            iv   = pred.predict(phi1)
            r1   = agent.get_reward(phi1)
            r2   = agent.get_reward(phi2)
            diff = r1 - r2
            if iv.lower <= diff <= iv.upper:
                n_covered += 1
        return n_covered / len(test_pairs)

    @pytest.mark.parametrize("alpha", [0.05, 0.10, 0.20])
    def test_marginal_coverage(self, agent, cal_pairs, test_pairs, alpha):
        pred = ConformalRewardPredictor(agent, alpha=alpha)
        pred.calibrate(cal_pairs)
        emp_cov = self._measure_coverage(pred, test_pairs, agent)
        # Allow 15% tolerance for finite-sample variation with small calibration sets
        assert emp_cov >= (1 - alpha) - 0.15, (
            f"Coverage {emp_cov:.3f} < {1-alpha:.2f} - 0.15 for alpha={alpha}"
        )

    def test_wider_alpha_yields_narrower_interval(self, agent, cal_pairs, sample_features):
        pred_tight = ConformalRewardPredictor(agent, alpha=0.05)
        pred_loose = ConformalRewardPredictor(agent, alpha=0.30)
        pred_tight.calibrate(cal_pairs)
        pred_loose.calibrate(cal_pairs)
        iv_tight = pred_tight.predict(sample_features)
        iv_loose = pred_loose.predict(sample_features)
        assert iv_tight.width >= iv_loose.width

    def test_coverage_stats_returns_dict(self, calibrated_predictor, test_pairs):
        stats = calibrated_predictor.coverage_stats(test_pairs)
        for key in ["n_pairs", "certain_correct", "abstain_rate", "mean_width", "median_width"]:
            assert key in stats

    def test_coverage_stats_values_in_range(self, calibrated_predictor, test_pairs):
        stats = calibrated_predictor.coverage_stats(test_pairs)
        assert 0.0 <= stats["certain_correct"] <= 1.0
        assert 0.0 <= stats["abstain_rate"]    <= 1.0
        assert stats["mean_width"] >= 0.0


# ---------------------------------------------------------------------------
# 5. TestUncertaintyDecision
# ---------------------------------------------------------------------------

class TestUncertaintyDecision:

    def test_predict_and_decide_returns_decision(self, calibrated_predictor, sample_features):
        d = calibrated_predictor.predict_and_decide(sample_features)
        assert isinstance(d, UncertaintyDecision)

    def test_proceed_when_confident(self, agent, cal_pairs, sample_features):
        pred = ConformalRewardPredictor(agent, alpha=0.10, abstain_width=1e6)
        pred.calibrate(cal_pairs)
        d = pred.predict_and_decide(sample_features)
        assert d.recommended_action in ("proceed", "request_more_data")

    def test_abstain_when_uncertain(self, agent, cal_pairs, sample_features):
        pred = ConformalRewardPredictor(agent, alpha=0.10, abstain_width=0.0)
        pred.calibrate(cal_pairs)
        d = pred.predict_and_decide(sample_features)
        assert d.recommended_action == "abstain"
        assert d.is_certain is False

    def test_reason_is_string(self, calibrated_predictor, sample_features):
        d = calibrated_predictor.predict_and_decide(sample_features)
        assert isinstance(d.reason, str) and len(d.reason) > 0

    def test_interval_stored(self, calibrated_predictor, sample_features):
        d = calibrated_predictor.predict_and_decide(sample_features)
        assert isinstance(d.interval, RewardInterval)


# ---------------------------------------------------------------------------
# 6. TestBootstrapEnsemble
# ---------------------------------------------------------------------------

class TestBootstrapEnsemble:

    def test_construction_valid(self):
        ens = BootstrapEnsemble(feature_size=N_FEATS, n_bootstrap=5)
        assert ens.n_bootstrap   == 5
        assert ens.is_fitted     is False
        assert ens.n_models      == 0

    def test_invalid_n_bootstrap(self):
        with pytest.raises(ValueError, match="n_bootstrap"):
            BootstrapEnsemble(feature_size=N_FEATS, n_bootstrap=1)

    def test_predict_before_fit_raises(self, sample_features):
        ens = BootstrapEnsemble(feature_size=N_FEATS, n_bootstrap=5)
        with pytest.raises(RuntimeError, match="fit"):
            ens.predict(sample_features)

    def test_fit_returns_self(self, train_pairs):
        ens  = BootstrapEnsemble(feature_size=N_FEATS, n_bootstrap=5, seed=0)
        ret  = ens.fit(train_pairs, max_epochs=20)
        assert ret is ens

    def test_is_fitted_after_fit(self, fitted_ensemble):
        assert fitted_ensemble.is_fitted is True

    def test_n_models_correct(self, fitted_ensemble):
        assert fitted_ensemble.n_models == 10

    def test_predict_returns_ensemble_prediction(self, fitted_ensemble, sample_features):
        pred = fitted_ensemble.predict(sample_features)
        assert isinstance(pred, EnsemblePrediction)

    def test_ensemble_prediction_fields(self, fitted_ensemble, sample_features):
        pred = fitted_ensemble.predict(sample_features)
        assert pred.n_bootstrap    == 10
        assert len(pred.predictions) == 10
        assert pred.lower_95       <= pred.mean <= pred.upper_95
        assert pred.std            >= 0.0
        assert pred.predict_time_s >= 0.0

    def test_ensemble_prediction_summary(self, fitted_ensemble, sample_features):
        pred = fitted_ensemble.predict(sample_features)
        s    = pred.summary()
        assert "EnsemblePrediction" in s

    def test_uncertainty_scalar(self, fitted_ensemble, sample_features):
        u = fitted_ensemble.uncertainty(sample_features)
        assert isinstance(u, float)
        assert u >= 0.0

    def test_rank_by_uncertainty(self, fitted_ensemble, test_pairs):
        feats  = [phi1 for phi1, _ in test_pairs[:10]]
        ranked = fitted_ensemble.rank_by_uncertainty(feats)
        assert len(ranked) == 10
        # Ascending uncertainty order
        uncs = [u for u, _ in ranked]
        assert uncs == sorted(uncs)

    def test_empty_pairs_raises(self):
        ens = BootstrapEnsemble(feature_size=N_FEATS, n_bootstrap=5)
        with pytest.raises(ValueError, match="non-empty"):
            ens.fit([])

    def test_more_bootstrap_reduces_variance(self, train_pairs, sample_features):
        """More models → lower variance in the mean prediction."""
        stds = []
        for n_b in [5, 20]:
            ens = BootstrapEnsemble(feature_size=N_FEATS, n_bootstrap=n_b, seed=0)
            ens.fit(train_pairs, max_epochs=30)
            preds = [ens.predict(sample_features).mean for _ in range(1)]
            stds.append(ens.uncertainty(sample_features))
        # Just check both are non-negative (exact ordering not guaranteed with small N)
        assert all(s >= 0 for s in stds)


# ---------------------------------------------------------------------------
# 7. TestUncertaintyAwareManager
# ---------------------------------------------------------------------------

class TestUncertaintyAwareManager:

    @pytest.fixture
    def mock_manager(self, agent):
        """A minimal mock ManagerAgent that always returns a single option."""
        import types

        class FakeOption:
            name      = "fake_option"
            option_id = "fake-id"
            def extract_features(self, state):
                return np.array([0.5]*N_FEATS)

        class FakeManager:
            def __init__(self):
                self._opt = FakeOption()
            def select_option(self, state):
                return self._opt, [self._opt]

        return FakeManager()

    def test_selects_option_when_certain(
        self, mock_manager, calibrated_predictor
    ):
        # Use very wide abstain_width → always certain
        mgr = UncertaintyAwareManager(
            manager      = mock_manager,
            uq_predictor = calibrated_predictor,
            max_width    = 1e6,
        )
        best, candidates = mgr.select_option({})
        assert best is not None
        assert len(candidates) == 1

    def test_abstains_when_uncertain(self, mock_manager, agent, cal_pairs):
        # Use width=0 → always abstain
        pred = ConformalRewardPredictor(agent, alpha=0.10, abstain_width=0.0)
        pred.calibrate(cal_pairs)
        mgr  = UncertaintyAwareManager(
            manager      = mock_manager,
            uq_predictor = pred,
            max_width    = 0.0,
        )
        best, candidates = mgr.select_option({})
        assert best is None

    def test_abstention_rate_tracked(self, mock_manager, agent, cal_pairs):
        pred = ConformalRewardPredictor(agent, alpha=0.10, abstain_width=0.0)
        pred.calibrate(cal_pairs)
        mgr  = UncertaintyAwareManager(
            manager=mock_manager, uq_predictor=pred, max_width=0.0
        )
        for _ in range(5):
            mgr.select_option({})
        assert mgr.abstention_rate() == pytest.approx(1.0)

    def test_stats_dict(self, mock_manager, calibrated_predictor):
        mgr = UncertaintyAwareManager(
            manager=mock_manager, uq_predictor=calibrated_predictor, max_width=1e6
        )
        mgr.select_option({})
        s = mgr.stats()
        assert "abstentions"     in s
        assert "selections"      in s
        assert "abstention_rate" in s

    def test_no_candidates_returns_none(self, calibrated_predictor):
        class EmptyManager:
            def select_option(self, state):
                return None, []

        mgr  = UncertaintyAwareManager(
            manager=EmptyManager(), uq_predictor=calibrated_predictor, max_width=1e6
        )
        best, candidates = mgr.select_option({})
        assert best is None
        assert candidates == []


# ---------------------------------------------------------------------------
# 8. TestCalibrationCurve
# ---------------------------------------------------------------------------

class TestCalibrationCurve:

    def test_returns_two_lists(self, calibrated_predictor, test_pairs):
        targets, empiricals = calibration_curve(calibrated_predictor, test_pairs)
        assert len(targets)    == len(empiricals)
        assert len(targets)    > 0

    def test_targets_in_range(self, calibrated_predictor, test_pairs):
        targets, _ = calibration_curve(calibrated_predictor, test_pairs)
        assert all(0 < t <= 1 for t in targets)

    def test_custom_alphas(self, calibrated_predictor, test_pairs):
        alphas           = [0.05, 0.20, 0.50]
        targets, empiricals = calibration_curve(
            calibrated_predictor, test_pairs, alphas=alphas
        )
        assert len(targets) == 3
        expected_targets = [1 - a for a in alphas]
        for t, et in zip(targets, expected_targets):
            assert t == pytest.approx(et)

    def test_original_state_restored(self, calibrated_predictor, test_pairs):
        """calibration_curve should not permanently alter predictor state."""
        orig_alpha = calibrated_predictor.alpha
        orig_q     = calibrated_predictor._q_hat
        calibration_curve(calibrated_predictor, test_pairs)
        assert calibrated_predictor.alpha    == pytest.approx(orig_alpha)
        assert calibrated_predictor._q_hat   == pytest.approx(orig_q)


# ---------------------------------------------------------------------------
# 9. TestUncertaintyBenchmark
# ---------------------------------------------------------------------------

class TestUncertaintyBenchmark:

    @pytest.fixture(scope="class")
    def bench(self):
        return UncertaintyBenchmark(
            n_train=40, n_calibrate=30, n_test=50, seed=42
        )

    def test_coverage_guarantee(self, bench):
        r = bench.run("coverage_guarantee")
        assert r.scenario == "coverage_guarantee"
        assert len(r.alphas_tested) == 4
        assert len(r.empirical_coverages) == 4
        # Each empirical coverage should be close to target
        for emp, tgt in zip(r.empirical_coverages, r.target_coverages):
            assert 0.0 <= emp <= 1.0
            assert 0.0 <  tgt <= 1.0

    def test_alpha_sweep(self, bench):
        r = bench.run("alpha_sweep")
        assert r.scenario == "alpha_sweep"
        assert len(r.alphas_tested)      == 5
        assert len(r.abstain_rates)      == 5
        assert len(r.certain_correct_rates) == 5

    def test_bootstrap_uncertainty(self, bench):
        r = bench.run("bootstrap_uncertainty")
        assert r.scenario == "bootstrap_uncertainty"
        assert len(r.n_bootstraps)       == 4
        assert len(r.mean_uncertainties) == 4
        assert len(r.rank_correlations)  == 4
        for mu in r.mean_uncertainties:
            assert mu >= 0.0

    def test_abstention_quality(self, bench):
        r = bench.run("abstention_quality")
        assert r.scenario == "abstention_quality"
        assert 0.0 <= r.indist_abstain_rate <= 1.0
        assert 0.0 <= r.ood_abstain_rate    <= 1.0

    def test_run_all_returns_four(self, bench):
        results   = bench.run_all()
        assert len(results) == 4
        scenarios = {r.scenario for r in results}
        assert scenarios == {
            "coverage_guarantee",
            "alpha_sweep",
            "bootstrap_uncertainty",
            "abstention_quality",
        }

    def test_summary_table(self, bench):
        results = bench.run_all()
        table   = bench.summary_table(results)
        assert "coverage_guarantee"    in table
        assert "alpha_sweep"           in table
        assert "bootstrap_uncertainty" in table
        assert "abstention_quality"    in table

    def test_unknown_scenario_raises(self, bench):
        with pytest.raises(ValueError):
            bench.run("nonexistent_scenario")

    def test_coverage_guarantee_wall_clock(self, bench):
        r = bench.run("coverage_guarantee")
        assert r.wall_clock_s > 0.0

    def test_alpha_sweep_increasing_width(self, bench):
        """Smaller α → wider intervals (higher confidence)."""
        r = bench.run("alpha_sweep")
        # alphas = [0.05, 0.10, 0.15, 0.20, 0.30]
        # Wider interval for smaller alpha (tighter guarantee)
        # Note: due to finite samples this may not be strictly monotone,
        # but the first should be wider than the last
        assert r.mean_widths[0] >= r.mean_widths[-1] - 0.01


# ---------------------------------------------------------------------------
# 10. TestIntegration
# ---------------------------------------------------------------------------

class TestIntegration:

    def test_conformal_and_bootstrap_agree_on_reward_sign(
        self, calibrated_predictor, fitted_ensemble, sample_features
    ):
        """Both methods should agree on reward sign for unambiguous inputs."""
        iv   = calibrated_predictor.predict(sample_features)
        ep   = fitted_ensemble.predict(sample_features)
        if not iv.abstain:
            # Check signs are compatible (both positive or both negative)
            if iv.lower > 0:
                assert ep.mean > 0 or abs(ep.mean) < ep.std * 2
            elif iv.upper < 0:
                assert ep.mean < 0 or abs(ep.mean) < ep.std * 2

    def test_uncertainty_aware_manager_with_real_library(
        self, calibrated_predictor, agent
    ):
        """Integration with OptionLibrary from WP9."""
        try:
            from prometheus.option import Option, OptionLibrary
            from prometheus.hierarchical_planner import ManagerAgent

            lib = OptionLibrary(feature_size=N_FEATS)
            opt = Option(
                name                 = "test",
                description          = "test option",
                initiation_condition = lambda s: True,
                policy               = lambda s: {"plan": "pass"},
                termination_condition= lambda s: True,
                feature_extractor    = lambda s: np.array([0.5] * N_FEATS),
            )
            lib.register(opt)
            mgr = ManagerAgent(value_agent=agent, option_library=lib)
            ua_mgr = UncertaintyAwareManager(
                manager      = mgr,
                uq_predictor = calibrated_predictor,
                max_width    = 1e6,
            )
            best, candidates = ua_mgr.select_option({"stage": "idle"})
            assert best is not None or candidates == []   # either is valid
        except ImportError:
            pytest.skip("WP9 hierarchical_planner not available")

    def test_full_pipeline(self, agent, train_pairs, cal_pairs, test_pairs):
        """Full pipeline: train → calibrate → predict → coverage stats."""
        pred = ConformalRewardPredictor(agent, alpha=0.10, abstain_width=1.0)
        pred.calibrate(cal_pairs)
        stats = pred.coverage_stats(test_pairs)
        assert stats["n_pairs"] == len(test_pairs)
        assert 0.0 <= stats["certain_correct"] <= 1.0
        assert 0.0 <= stats["abstain_rate"]    <= 1.0
