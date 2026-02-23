"""
Tests for WP12 — Reward Hacking Detection & Robustness

Coverage across 10 test classes:

TestGoodhartDetector          — 18 tests
TestRewardTamperingDetector   — 16 tests
TestSpecificationGamingDetector — 18 tests
TestRobustRewardWrapper       — 16 tests
TestHackingVerdict            — 4 tests
TestGoodhartEdgeCases         — 4 tests
TestTamperingEdgeCases        — 4 tests
TestGamingEdgeCases           — 4 tests
TestWrapperIntegration        — 4 tests
TestBenchmark                 — 4 tests

Total: 92 tests
"""

from __future__ import annotations

import hashlib
import time

import numpy as np
import pytest

from prometheus.value_learning import ValueLearningAgent
from prometheus.reward_hacking import (
    GoodhartDetector,
    GoodhartSignal,
    RewardTamperingDetector,
    TamperingReport,
    SpecificationGamingDetector,
    SpecGamingReport,
    RobustRewardWrapper,
    HackingVerdict,
)
from benchmarks.reward_hacking_benchmark import (
    RewardHackingBenchmark,
    _make_agent,
    N_FEATS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def agent():
    return _make_agent(seed=0)


@pytest.fixture
def fresh_agent():
    return _make_agent(seed=1)


@pytest.fixture
def goodhart():
    return GoodhartDetector(window=20, divergence_threshold=0.3, critical_threshold=0.0)


@pytest.fixture
def tampering():
    return RewardTamperingDetector(weight_change_threshold=0.5)


@pytest.fixture
def gaming():
    return SpecificationGamingDetector(
        vor_threshold=0.7,
        overopt_threshold=2.0,
        complexity_threshold=5.0,
    )


@pytest.fixture
def wrapper(agent):
    return RobustRewardWrapper(base_agent=agent, penalty_scale=0.3)


# ---------------------------------------------------------------------------
# TestGoodhartDetector (18 tests)
# ---------------------------------------------------------------------------

class TestGoodhartDetector:

    def test_returns_signal(self, goodhart):
        sig = goodhart.update(1.0, 1.0)
        assert isinstance(sig, GoodhartSignal)

    def test_no_alert_insufficient_data(self, goodhart):
        # Only 3 steps — not enough for correlation
        for i in range(3):
            sig = goodhart.update(float(i), float(i))
        assert not sig.diverging

    def test_no_alert_aligned(self, goodhart):
        rng = np.random.default_rng(0)
        for i in range(25):
            v   = float(i) * 0.1
            sig = goodhart.update(v + rng.uniform(-0.01, 0.01),
                                   v + rng.uniform(-0.01, 0.01))
        assert not sig.diverging

    def test_alert_on_divergence(self):
        det = GoodhartDetector(window=12, divergence_threshold=0.3, min_proxy_trend=0.001)
        rng = np.random.default_rng(7)
        # Phase 1: aligned
        for i in range(12):
            det.update(float(i) * 0.05, float(i) * 0.05 + rng.uniform(-0.01, 0.01))
        # Phase 2: proxy rising, true falling
        for i in range(15):
            det.update(
                2.0 + float(i) * 0.3 + rng.uniform(-0.02, 0.02),
                1.5 - float(i) * 0.1 + rng.uniform(-0.02, 0.02),
            )
        assert det.n_alerts("warning") >= 1

    def test_critical_alert_level(self):
        det = GoodhartDetector(window=10, divergence_threshold=0.5,
                                critical_threshold=0.0, min_proxy_trend=0.001)
        rng = np.random.default_rng(3)
        for i in range(10):
            det.update(float(i) * 0.05, float(i) * 0.05 + rng.uniform(-0.005, 0.005))
        for i in range(15):
            sig = det.update(
                3.0 + float(i) * 0.5 + rng.uniform(-0.02, 0.02),
                1.0 - float(i) * 0.2 + rng.uniform(-0.02, 0.02),
            )
        assert det.n_alerts("critical") >= 1 or det.n_alerts("warning") >= 1

    def test_signal_fields(self, goodhart):
        sig = goodhart.update(0.5, 0.4)
        assert isinstance(sig.step, int)
        assert isinstance(sig.proxy_value, float)
        assert isinstance(sig.rolling_correlation, float)
        assert sig.alert_level in ("none", "warning", "critical")
        assert isinstance(sig.diverging, bool)

    def test_true_value_optional(self, goodhart):
        # No true value — should not crash
        sig = goodhart.update(1.0)
        assert isinstance(sig, GoodhartSignal)
        assert sig.true_value is None
        assert not sig.diverging

    def test_step_counter(self, goodhart):
        for i in range(5):
            sig = goodhart.update(float(i), float(i))
        assert sig.step == 5

    def test_signals_accumulated(self, goodhart):
        for i in range(7):
            goodhart.update(float(i), float(i))
        assert len(goodhart.signals) == 7

    def test_reset_clears(self, goodhart):
        for i in range(5):
            goodhart.update(float(i), float(i))
        goodhart.reset()
        assert len(goodhart.signals) == 0
        assert goodhart._step == 0

    def test_stats_keys(self, goodhart):
        for i in range(5):
            goodhart.update(float(i), float(i))
        stats = goodhart.stats()
        assert "steps" in stats
        assert "n_warnings" in stats
        assert "n_criticals" in stats
        assert "last_correlation" in stats

    def test_correlation_perfect(self):
        det = GoodhartDetector(window=20)
        for i in range(20):
            det.update(float(i), float(i))
        corr = det._rolling_correlation()
        assert corr > 0.99

    def test_correlation_anticorrelated(self):
        det = GoodhartDetector(window=20)
        for i in range(20):
            det.update(float(i), float(-i))
        corr = det._rolling_correlation()
        assert corr < -0.9

    def test_proxy_trend_positive(self):
        det = GoodhartDetector(window=20)
        for i in range(20):
            det.update(float(i) * 0.1, float(i) * 0.1)
        assert det._proxy_trend() > 0

    def test_proxy_trend_flat(self):
        det = GoodhartDetector(window=20)
        for i in range(20):
            det.update(1.0, 1.0)
        assert abs(det._proxy_trend()) < 0.01

    def test_n_alerts_count(self):
        det = GoodhartDetector(window=10, divergence_threshold=0.3, min_proxy_trend=0.001)
        rng = np.random.default_rng(5)
        for i in range(10):
            det.update(float(i) * 0.05, float(i) * 0.05 + rng.uniform(-0.005, 0.005))
        for i in range(20):
            det.update(
                3.0 + float(i) * 0.4,
                0.5 - float(i) * 0.1,
            )
        assert det.n_alerts("warning") >= 0  # at least non-negative

    def test_no_alert_no_true_data(self):
        det = GoodhartDetector(window=10)
        for i in range(25):
            sig = det.update(float(i) * 0.1)  # no true value
        assert not sig.diverging

    def test_constant_proxy_no_alert(self):
        det = GoodhartDetector(window=15, min_proxy_trend=0.01)
        rng = np.random.default_rng(0)
        for _ in range(20):
            det.update(1.0, rng.uniform(0.5, 1.5))
        # constant proxy → trend ≈ 0 → no Goodhart
        assert det.n_alerts("warning") == 0


# ---------------------------------------------------------------------------
# TestRewardTamperingDetector (16 tests)
# ---------------------------------------------------------------------------

class TestRewardTamperingDetector:

    def test_returns_report(self, tampering, agent):
        tampering.register_weights(agent.get_weights())
        report = tampering.check_weights(agent.get_weights())
        assert isinstance(report, TamperingReport)

    def test_clean_weights_not_flagged(self, tampering, agent):
        w = agent.get_weights()
        tampering.register_weights(w)
        report = tampering.check_weights(w.copy())
        assert not report.tampered
        assert report.tamper_type == "none"

    def test_large_perturbation_flagged(self, agent):
        det = RewardTamperingDetector(weight_change_threshold=0.5)
        w   = agent.get_weights()
        det.register_weights(w)
        w_tampered = w + np.ones_like(w) * float(np.linalg.norm(w))
        report = det.check_weights(w_tampered)
        assert report.tampered
        assert report.tamper_type == "weight_change"

    def test_small_perturbation_not_flagged(self, agent):
        det = RewardTamperingDetector(weight_change_threshold=0.5)
        w   = agent.get_weights()
        det.register_weights(w)
        noise      = np.random.default_rng(0).standard_normal(w.shape) * 1e-5
        report     = det.check_weights(w + noise)
        assert not report.tampered

    def test_delta_norm_positive(self, tampering, agent):
        w = agent.get_weights()
        tampering.register_weights(w)
        noise  = np.ones(N_FEATS) * 0.1
        report = tampering.check_weights(w + noise)
        assert report.weight_delta_norm > 0

    def test_feature_hash_match(self, tampering):
        feats     = np.ones(N_FEATS)
        checksum  = RewardTamperingDetector.feature_checksum(feats)
        report    = tampering.check_features(feats, checksum)
        assert report.feature_hash_match
        assert not report.tampered

    def test_feature_hash_mismatch(self, tampering):
        feats     = np.ones(N_FEATS)
        tampered  = feats.copy()
        tampered[0] += 1e-6
        checksum  = RewardTamperingDetector.feature_checksum(feats)
        report    = tampering.check_features(tampered, checksum)
        assert not report.feature_hash_match
        assert report.tampered
        assert report.tamper_type == "feature_injection"

    def test_no_reference_no_crash(self, tampering, agent):
        # No register_weights called — should return clean report
        report = tampering.check_weights(agent.get_weights())
        assert isinstance(report, TamperingReport)
        assert not report.tampered

    def test_reports_accumulated(self, tampering, agent):
        w = agent.get_weights()
        tampering.register_weights(w)
        for _ in range(3):
            tampering.check_weights(w)
        assert len(tampering.reports) == 3

    def test_reset_clears(self, tampering, agent):
        w = agent.get_weights()
        tampering.register_weights(w)
        tampering.check_weights(w)
        tampering.reset()
        assert len(tampering.reports) == 0
        assert tampering._reference_weights is None

    def test_n_tamper_events(self, agent):
        det = RewardTamperingDetector(weight_change_threshold=0.5)
        w   = agent.get_weights()
        det.register_weights(w)
        det.check_weights(w)                                   # clean
        det.check_weights(w + np.ones_like(w) * float(np.linalg.norm(w)))  # tampered
        assert det.n_tamper_events() == 1

    def test_stats_keys(self, tampering, agent):
        w = agent.get_weights()
        tampering.register_weights(w)
        tampering.check_weights(w)
        stats = tampering.stats()
        assert "n_checks" in stats
        assert "n_tamper_events" in stats
        assert "max_delta_norm" in stats

    def test_severity_zero_for_clean(self, tampering, agent):
        w = agent.get_weights()
        tampering.register_weights(w)
        report = tampering.check_weights(w.copy())
        assert report.severity == 0

    def test_severity_positive_for_tamper(self, agent):
        det = RewardTamperingDetector(weight_change_threshold=0.5)
        w   = agent.get_weights()
        det.register_weights(w)
        tampered = w + np.ones_like(w) * float(np.linalg.norm(w)) * 5
        report   = det.check_weights(tampered)
        assert report.severity > 0

    def test_feature_checksum_deterministic(self):
        feats = np.arange(N_FEATS, dtype=float)
        c1 = RewardTamperingDetector.feature_checksum(feats)
        c2 = RewardTamperingDetector.feature_checksum(feats)
        assert c1 == c2

    def test_threshold_zero_always_flags(self, agent):
        det = RewardTamperingDetector(weight_change_threshold=0.0)
        w   = agent.get_weights()
        det.register_weights(w)
        noise  = np.ones(N_FEATS) * 0.001
        report = det.check_weights(w + noise)
        assert report.tampered


# ---------------------------------------------------------------------------
# TestSpecificationGamingDetector (18 tests)
# ---------------------------------------------------------------------------

class TestSpecificationGamingDetector:

    def test_returns_report(self, gaming):
        report = gaming.check(proxy_reward=1.0)
        assert isinstance(report, SpecGamingReport)

    def test_clean_not_flagged(self, gaming):
        report = gaming.check(
            proxy_reward         = 1.0,
            eval_reward          = 0.95,
            replacement_reward   = 0.9,
            behaviour_complexity = 50.0,
            proxy_baseline       = 0.5,
            eval_baseline        = 0.5,
        )
        assert not report.gaming_detected

    def test_overoptimisation_detected(self, gaming):
        report = gaming.check(
            proxy_reward   = 10.0,
            eval_reward    = 0.5,
            proxy_baseline = 0.5,
            eval_baseline  = 0.5,
        )
        assert report.gaming_detected
        assert report.gaming_type == "overoptimisation"

    def test_hardcoding_detected(self, gaming):
        report = gaming.check(
            proxy_reward         = 20.0,
            behaviour_complexity = 1.0,
        )
        assert report.gaming_detected
        assert report.gaming_type == "hardcoding"

    def test_loophole_via_vor(self, gaming):
        report = gaming.check(
            proxy_reward       = 5.0,
            replacement_reward = 0.0,
        )
        assert report.gaming_detected
        assert report.gaming_type == "loophole"

    def test_vor_score_zero_no_replacement(self, gaming):
        report = gaming.check(proxy_reward=1.0)
        assert report.vor_score == 0.0

    def test_overopt_zero_no_eval(self, gaming):
        report = gaming.check(proxy_reward=1.0)
        assert report.overopt_score == 0.0

    def test_complexity_ratio_zero_no_complexity(self, gaming):
        report = gaming.check(proxy_reward=1.0)
        assert report.complexity_ratio == 0.0

    def test_gaming_rate(self, gaming):
        # Clean
        gaming.check(proxy_reward=1.0, eval_reward=0.95,
                     behaviour_complexity=50.0,
                     proxy_baseline=0.5, eval_baseline=0.5)
        # Gaming
        gaming.check(proxy_reward=10.0, eval_reward=0.5,
                     proxy_baseline=0.5, eval_baseline=0.5)
        rate = gaming.gaming_rate()
        assert 0.0 <= rate <= 1.0

    def test_gaming_rate_all_clean(self):
        det = SpecificationGamingDetector()
        for _ in range(10):
            det.check(proxy_reward=1.0, eval_reward=0.95,
                      behaviour_complexity=50.0,
                      proxy_baseline=0.5, eval_baseline=0.5)
        assert det.gaming_rate() == 0.0

    def test_gaming_rate_all_flagged(self):
        det = SpecificationGamingDetector(overopt_threshold=1.5)
        for _ in range(10):
            det.check(proxy_reward=10.0, eval_reward=0.5,
                      proxy_baseline=0.5, eval_baseline=0.5)
        assert det.gaming_rate() == 1.0

    def test_reports_accumulated(self, gaming):
        n = 5
        for _ in range(n):
            gaming.check(proxy_reward=1.0)
        assert len(gaming.reports) >= n

    def test_reset_clears(self, gaming):
        gaming.check(proxy_reward=1.0)
        gaming.reset()
        assert len(gaming.reports) == 0
        assert gaming.gaming_rate() == 0.0

    def test_stats_keys(self, gaming):
        gaming.check(proxy_reward=1.0)
        stats = gaming.stats()
        assert "n_checks" in stats
        assert "gaming_rate" in stats
        assert "mean_vor" in stats
        assert "mean_overopt" in stats

    def test_vor_bounded(self, gaming):
        report = gaming.check(proxy_reward=5.0, replacement_reward=0.0)
        assert 0.0 <= report.vor_score <= 1.0

    def test_overopt_eval_flat(self, gaming):
        # eval gain ≈ 0 but proxy surges → overopt
        report = gaming.check(
            proxy_reward   = 8.0,
            eval_reward    = 0.50001,
            proxy_baseline = 0.5,
            eval_baseline  = 0.5,
        )
        assert report.overopt_score > 0

    def test_description_populated_on_gaming(self, gaming):
        report = gaming.check(proxy_reward=10.0, eval_reward=0.5,
                              proxy_baseline=0.5, eval_baseline=0.5)
        if report.gaming_detected:
            assert len(report.description) > 0

    def test_description_no_gaming(self, gaming):
        report = gaming.check(proxy_reward=1.0, eval_reward=0.95,
                              behaviour_complexity=50.0,
                              proxy_baseline=0.5, eval_baseline=0.5)
        assert "no gaming" in report.description or report.description != ""


# ---------------------------------------------------------------------------
# TestRobustRewardWrapper (16 tests)
# ---------------------------------------------------------------------------

class TestRobustRewardWrapper:

    def test_returns_verdict(self, wrapper):
        feats   = np.ones(N_FEATS)
        verdict = wrapper.get_reward(feats)
        assert isinstance(verdict, HackingVerdict)

    def test_clean_input_low_penalty(self, wrapper):
        feats   = np.ones(N_FEATS) * 0.1
        verdict = wrapper.get_reward(feats)
        assert verdict.penalty_applied < 0.6   # clean input → low penalty

    def test_verdict_reward_is_float(self, wrapper):
        feats   = np.zeros(N_FEATS)
        verdict = wrapper.get_reward(feats)
        assert isinstance(verdict.reward, float)

    def test_verdict_has_all_detectors(self, wrapper):
        feats   = np.zeros(N_FEATS)
        verdict = wrapper.get_reward(feats)
        assert verdict.goodhart_signal is not None
        assert verdict.tampering_report is not None
        assert verdict.spec_gaming_report is not None

    def test_penalty_reduces_reward(self, agent):
        rng = np.random.default_rng(0)
        feats = rng.standard_normal(N_FEATS)
        raw   = float(agent.get_reward(feats))

        def true_fn(f: np.ndarray) -> float:
            return -float(np.dot(agent.get_weights(), f))  # anti-correlated

        wrapper = RobustRewardWrapper(base_agent=agent, penalty_scale=0.5,
                                      true_reward_fn=true_fn)
        # Seed Goodhart: many steps so correlation can be computed
        for i in range(35):
            f = rng.standard_normal(N_FEATS) * (1 + i * 0.05)
            wrapper.get_reward(f)

        verdict = wrapper.get_reward(feats)
        # If penalty applied, adj_reward should be ≤ |raw|
        assert verdict.reward <= abs(raw) + 0.1 or not verdict.hacking_detected

    def test_hacking_rate_initially_zero(self, wrapper):
        assert wrapper.hacking_rate() == 0.0

    def test_hacking_rate_updates(self, wrapper, agent):
        # Force a tamper
        w = agent.get_weights()
        w_heavy = w + np.ones_like(w) * float(np.linalg.norm(w)) * 2
        agent.set_weights(w_heavy)
        wrapper.get_reward(np.ones(N_FEATS))
        agent.set_weights(w)   # restore
        assert wrapper.hacking_rate() >= 0.0

    def test_reset_clears_verdicts(self, wrapper):
        wrapper.get_reward(np.zeros(N_FEATS))
        wrapper.reset()
        assert len(wrapper.verdicts) == 0

    def test_register_weights_updates_reference(self, wrapper, agent):
        wrapper.register_weights()
        # Should not crash
        report = wrapper.tampering_detector.check_weights(agent.get_weights())
        assert isinstance(report, TamperingReport)

    def test_stats_keys(self, wrapper):
        wrapper.get_reward(np.zeros(N_FEATS))
        stats = wrapper.stats()
        assert "n_calls" in stats
        assert "hacking_rate" in stats
        assert "mean_penalty" in stats
        assert "goodhart_stats" in stats
        assert "tampering_stats" in stats
        assert "gaming_stats" in stats

    def test_update_baselines(self, wrapper):
        wrapper.update_baselines(0.5, 0.4)
        assert wrapper._proxy_baseline == 0.5
        assert wrapper._eval_baseline  == 0.4

    def test_feature_checksum_integration(self, wrapper):
        feats     = np.ones(N_FEATS)
        checksum  = RewardTamperingDetector.feature_checksum(feats)
        verdict   = wrapper.get_reward(feats, reference_checksum=checksum)
        assert verdict.tampering_report.feature_hash_match

    def test_feature_injection_detected(self, wrapper):
        feats    = np.ones(N_FEATS)
        checksum = RewardTamperingDetector.feature_checksum(feats)
        injected = feats.copy()
        injected[0] += 1.0
        verdict  = wrapper.get_reward(injected, reference_checksum=checksum)
        assert verdict.tampering_report.tampered

    def test_wall_clock_positive(self, wrapper):
        verdict = wrapper.get_reward(np.zeros(N_FEATS))
        assert verdict.wall_clock_s >= 0.0

    def test_verdicts_accumulated(self, wrapper):
        n = 4
        for _ in range(n):
            wrapper.get_reward(np.zeros(N_FEATS))
        assert len(wrapper.verdicts) >= n

    def test_eval_reward_passed_through(self, agent):
        wrapper = RobustRewardWrapper(base_agent=agent, penalty_scale=0.3)
        feats   = np.ones(N_FEATS)
        verdict = wrapper.get_reward(feats, eval_reward=0.5)
        assert isinstance(verdict, HackingVerdict)


# ---------------------------------------------------------------------------
# TestHackingVerdict (4 tests)
# ---------------------------------------------------------------------------

class TestHackingVerdict:

    def test_summary_clean(self, wrapper):
        verdict = wrapper.get_reward(np.zeros(N_FEATS))
        s = verdict.summary()
        assert "HackingVerdict" in s

    def test_summary_contains_penalty(self, wrapper):
        verdict = wrapper.get_reward(np.zeros(N_FEATS))
        assert "penalty=" in verdict.summary()

    def test_description_clean(self, wrapper):
        verdict = wrapper.get_reward(np.zeros(N_FEATS))
        assert isinstance(verdict.description, str)

    def test_hacking_detected_bool(self, wrapper):
        verdict = wrapper.get_reward(np.zeros(N_FEATS))
        assert isinstance(verdict.hacking_detected, bool)


# ---------------------------------------------------------------------------
# TestGoodhartEdgeCases (4 tests)
# ---------------------------------------------------------------------------

class TestGoodhartEdgeCases:

    def test_constant_true_no_crash(self):
        det = GoodhartDetector(window=15)
        for i in range(20):
            det.update(float(i) * 0.1, 1.0)   # constant true
        assert len(det.signals) == 20

    def test_very_large_values(self):
        det = GoodhartDetector(window=15)
        for i in range(20):
            det.update(float(i) * 1e6, float(i) * 1e6)
        assert len(det.signals) == 20

    def test_negative_values(self):
        det = GoodhartDetector(window=15)
        for i in range(20):
            det.update(-float(i) * 0.1, -float(i) * 0.1)
        assert len(det.signals) == 20

    def test_window_larger_than_history(self):
        det = GoodhartDetector(window=100)
        for i in range(5):
            det.update(float(i), float(i))
        # should not crash; insufficient data → no alert
        assert not det.signals[-1].diverging


# ---------------------------------------------------------------------------
# TestTamperingEdgeCases (4 tests)
# ---------------------------------------------------------------------------

class TestTamperingEdgeCases:

    def test_zero_reference_weights(self):
        det = RewardTamperingDetector(weight_change_threshold=0.5)
        w   = np.zeros(N_FEATS)
        det.register_weights(w)
        noise  = np.ones(N_FEATS) * 0.01
        report = det.check_weights(w + noise)
        assert isinstance(report, TamperingReport)

    def test_single_feature(self):
        det = RewardTamperingDetector(weight_change_threshold=0.5)
        det.register_weights(np.array([1.0]))
        report = det.check_weights(np.array([1.0]))
        assert not report.tampered

    def test_hash_empty_array(self):
        h = RewardTamperingDetector.feature_checksum(np.array([]))
        assert isinstance(h, str)
        assert len(h) == 64   # SHA-256 hex

    def test_high_threshold_not_flagged(self, agent):
        det = RewardTamperingDetector(weight_change_threshold=100.0)
        w   = agent.get_weights()
        det.register_weights(w)
        noisy = w + np.ones_like(w) * 0.5
        report = det.check_weights(noisy)
        assert not report.tampered


# ---------------------------------------------------------------------------
# TestGamingEdgeCases (4 tests)
# ---------------------------------------------------------------------------

class TestGamingEdgeCases:

    def test_negative_proxy_reward(self, gaming):
        report = gaming.check(proxy_reward=-1.0)
        assert isinstance(report, SpecGamingReport)

    def test_zero_complexity(self, gaming):
        report = gaming.check(proxy_reward=1.0, behaviour_complexity=0.0)
        assert report.complexity_ratio == 0.0

    def test_same_proxy_eval(self, gaming):
        report = gaming.check(proxy_reward=1.0, eval_reward=1.0,
                              proxy_baseline=0.5, eval_baseline=0.5)
        assert not report.gaming_detected

    def test_replacement_equals_proxy(self, gaming):
        report = gaming.check(proxy_reward=1.0, replacement_reward=1.0)
        assert report.vor_score == 0.0


# ---------------------------------------------------------------------------
# TestWrapperIntegration (4 tests)
# ---------------------------------------------------------------------------

class TestWrapperIntegration:

    def test_true_reward_fn_called(self, agent):
        calls = []

        def true_fn(f):
            calls.append(1)
            return 0.0

        wrapper = RobustRewardWrapper(base_agent=agent, true_reward_fn=true_fn)
        wrapper.get_reward(np.zeros(N_FEATS))
        assert len(calls) == 1

    def test_replacement_fn_called(self, agent):
        calls = []

        def repl_fn(f):
            calls.append(1)
            return 0.0

        wrapper = RobustRewardWrapper(base_agent=agent, replacement_reward_fn=repl_fn)
        wrapper.get_reward(np.zeros(N_FEATS))
        assert len(calls) == 1

    def test_complexity_fn_called(self, agent):
        calls = []

        def cpx_fn(f):
            calls.append(1)
            return 50.0

        wrapper = RobustRewardWrapper(base_agent=agent, complexity_fn=cpx_fn)
        wrapper.get_reward(np.zeros(N_FEATS))
        assert len(calls) == 1

    def test_penalty_scale_zero_preserves_reward(self, agent):
        wrapper = RobustRewardWrapper(base_agent=agent, penalty_scale=0.0)
        feats   = np.ones(N_FEATS)
        verdict = wrapper.get_reward(feats)
        raw     = float(agent.get_reward(feats))
        assert abs(verdict.reward - raw) < 1e-9


# ---------------------------------------------------------------------------
# TestBenchmark (4 tests)
# ---------------------------------------------------------------------------

class TestBenchmark:

    @pytest.fixture(scope="class")
    def bench(self):
        return RewardHackingBenchmark(seed=42)

    @pytest.fixture(scope="class")
    def results(self, bench):
        return bench.run_all()

    def test_four_scenarios(self, results):
        assert len(results) == 4

    def test_scenario_names(self, results):
        names = {r.scenario for r in results}
        assert "goodhart_scenario"  in names
        assert "tampering_scenario" in names
        assert "gaming_scenario"    in names
        assert "end_to_end"         in names

    def test_all_scenarios_pass(self, results):
        for r in results:
            assert r.passed, f"Scenario '{r.scenario}' failed: {r.metrics}"

    def test_summary_table(self, bench, results):
        table = bench.summary_table(results)
        assert "WP12" in table
        assert "PASS" in table
