"""
WP69 Test Suite: Red-Team & Adversarial Robustness Harness
===========================================================

TestAttackVector          Vector fields, to_dict()
TestAttackResult          Result structure
TestRedTeamScenario       Scenario fields
TestRedTeamHarness        run_scenario, run_all, report
TestRedTeamReport         Robustness score, recommendations
TestWP69ExitCriteria      Six-criterion verifier
TestIntegration           End-to-end: harness → report
"""

import pytest

from prometheus.wp69_red_team import (
    AttackResult,
    AttackVector,
    RedTeamHarness,
    RedTeamReport,
    RedTeamScenario,
    verify_wp69_exit_criteria,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _harness(seed: int = 42) -> RedTeamHarness:
    return RedTeamHarness(seed=seed)


def _safe_baseline() -> dict:
    return {
        "alignment_score": 0.95,
        "deception_score": 0.02,
        "resource_usage": 0.5,
        "override_latency_ms": 50.0,
        "transparency_score": 0.9,
        "convergence_delta": 0.005,
        "explainability_score": 0.8,
        "self_reinforcement_factor": 0.1,
        "elo": 1500.0,
        "consensus_votes": [True, True, True],
        "crls_state": "stable",
        "corrigibility_flag": True,
    }


# ===========================================================================
# TestAttackVector
# ===========================================================================

class TestAttackVector:
    def test_fields(self):
        harness = _harness()
        vectors = harness.attack_vectors
        assert len(vectors) >= 5

    def test_vector_name(self):
        harness = _harness()
        for v in harness.attack_vectors:
            assert isinstance(v.name, str)
            assert len(v.name) > 0

    def test_vector_severity(self):
        harness = _harness()
        for v in harness.attack_vectors:
            assert v.severity in ("critical", "major", "minor")

    def test_vector_to_dict(self):
        harness = _harness()
        v = harness.attack_vectors[0]
        d = v.to_dict()
        assert "name" in d
        assert "severity" in d
        assert "subsystem" in d

    def test_vector_subsystem(self):
        harness = _harness()
        for v in harness.attack_vectors:
            assert isinstance(v.subsystem, str)


# ===========================================================================
# TestAttackResult
# ===========================================================================

class TestAttackResult:
    def test_to_dict_keys(self):
        r = AttackResult(
            attack_name="test_attack",
            subsystem="safety",
            severity="critical",
            bypassed=False,
            detection_triggered=True,
            details="blocked",
        )
        d = r.to_dict()
        for k in ("attack_name", "subsystem", "severity", "bypassed", "detection_triggered"):
            assert k in d, f"Missing key: {k}"

    def test_bypassed_false(self):
        r = AttackResult(
            attack_name="a", subsystem="s", severity="minor",
            bypassed=False, detection_triggered=True, details="",
        )
        assert r.bypassed is False


# ===========================================================================
# TestRedTeamScenario
# ===========================================================================

class TestRedTeamScenario:
    def test_fields(self):
        harness = _harness()
        scenarios = harness.scenarios
        assert len(scenarios) >= 5

    def test_scenario_to_dict(self):
        harness = _harness()
        s = harness.scenarios[0]
        d = s.to_dict()
        assert "name" in d
        assert "attack_vectors" in d or "n_vectors" in d

    def test_scenario_has_attack_vectors(self):
        harness = _harness()
        for s in harness.scenarios:
            assert len(s.attack_vectors) >= 1


# ===========================================================================
# TestRedTeamHarness
# ===========================================================================

class TestRedTeamHarness:
    def test_run_all_returns_report(self):
        harness = _harness()
        report = harness.run_all()
        assert isinstance(report, RedTeamReport)

    def test_report_has_results(self):
        harness = _harness()
        report = harness.run_all()
        assert len(report.results) > 0

    def test_robustness_score_in_range(self):
        harness = _harness()
        report = harness.run_all()
        assert 0.0 <= report.robustness_score <= 1.0

    def test_report_to_dict(self):
        harness = _harness()
        report = harness.run_all()
        d = report.to_dict()
        assert "robustness_score" in d
        assert "results" in d

    def test_run_with_baseline(self):
        harness = RedTeamHarness(baseline_state=_safe_baseline(), seed=0)
        report = harness.run_all()
        assert isinstance(report, RedTeamReport)

    def test_result_to_dict_keys(self):
        harness = _harness()
        report = harness.run_all()
        for r in report.results:
            d = r.to_dict()
            for k in ("attack_name", "subsystem", "severity", "bypassed"):
                assert k in d, f"Missing key: {k}"

    def test_deterministic_with_seed(self):
        h1 = RedTeamHarness(seed=42)
        h2 = RedTeamHarness(seed=42)
        r1 = h1.run_all()
        r2 = h2.run_all()
        assert abs(r1.robustness_score - r2.robustness_score) < 1e-6


# ===========================================================================
# TestRedTeamReport
# ===========================================================================

class TestRedTeamReport:
    def _report(self) -> RedTeamReport:
        return _harness().run_all()

    def test_recommendations_list(self):
        report = self._report()
        assert isinstance(report.recommendations, list)

    def test_elapsed_s_positive(self):
        report = self._report()
        assert report.elapsed_s >= 0.0

    def test_n_bypassed_count(self):
        report = self._report()
        bypassed_count = sum(1 for r in report.results if r.bypassed)
        assert report.n_bypassed == bypassed_count

    def test_robustness_score_formula(self):
        """robustness_score = 1 - weighted_bypass_rate."""
        report = self._report()
        # Score should be 1.0 if nothing is bypassed
        if report.n_bypassed == 0:
            assert report.robustness_score == 1.0


# ===========================================================================
# TestWP69ExitCriteria
# ===========================================================================

class TestWP69ExitCriteria:
    def _report(self) -> RedTeamReport:
        return _harness().run_all()

    def test_returns_dict(self):
        assert isinstance(verify_wp69_exit_criteria(), dict)

    def test_six_criteria(self):
        assert len(verify_wp69_exit_criteria()) == 6

    def test_all_pass_with_report(self):
        report = self._report()
        result = verify_wp69_exit_criteria(report)
        for k, v in result.items():
            assert v, f"Criterion failed: '{k}'"

    def test_no_report_returns_dict(self):
        result = verify_wp69_exit_criteria(None)
        assert isinstance(result, dict)
        assert len(result) == 6


# ===========================================================================
# TestIntegration
# ===========================================================================

class TestIntegration:
    def test_end_to_end_with_safe_baseline(self):
        harness = RedTeamHarness(baseline_state=_safe_baseline(), seed=1)
        report = harness.run_all()
        assert 0.0 <= report.robustness_score <= 1.0
        assert len(report.results) >= 5

    def test_criteria_pass_after_full_run(self):
        harness = _harness()
        report = harness.run_all()
        result = verify_wp69_exit_criteria(report)
        assert all(result.values()), f"Some criteria failed: {result}"
