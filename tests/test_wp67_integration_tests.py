"""
WP67 Test Suite: Integration Test Suite (meta)
===============================================

TestWPEntry               Entry fields, to_dict()
TestWPRegistry            all(), by_tier(), lookup
TestImportChecker         Import success/failure detection
TestCriteriaRunner        Run criteria, error handling
TestIntegrationTestSuite  Import-only mode, report structure
TestWP67ExitCriteria      Six-criterion verifier
TestIntegration           End-to-end: suite run → report
"""

import pytest

from prometheus.wp67_integration_tests import (
    CriteriaRunner,
    ImportChecker,
    IntegrationReport,
    IntegrationResult,
    IntegrationTestSuite,
    WPEntry,
    WPRegistry,
    verify_wp67_exit_criteria,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry(wp_id: str = "WP61", module: str = "prometheus.wp61_multigame_benchmark",
           criteria_fn: str = "verify_wp61_exit_criteria", tier: int = 9) -> WPEntry:
    return WPEntry(
        wp_id=wp_id,
        module=module,
        criteria_fn=criteria_fn,
        tier=tier,
        description="Multi-Game Benchmark",
    )


def _small_suite(run_criteria: bool = False) -> IntegrationTestSuite:
    entries = [
        _entry("WP61", "prometheus.wp61_multigame_benchmark", "verify_wp61_exit_criteria"),
        _entry("WP62", "prometheus.wp62_arc_agi", "verify_wp62_exit_criteria", tier=9),
    ]
    return IntegrationTestSuite(entries=entries, run_criteria=run_criteria, timeout_per_wp_s=30.0)


# ===========================================================================
# TestWPEntry
# ===========================================================================

class TestWPEntry:
    def test_fields(self):
        e = _entry()
        assert e.wp_id == "WP61"
        assert e.tier == 9

    def test_to_dict(self):
        d = _entry().to_dict()
        for k in ("wp_id", "module", "criteria_fn", "tier", "description"):
            assert k in d, f"Missing key: {k}"

    def test_custom_entry(self):
        e = WPEntry(
            wp_id="WP99",
            module="prometheus.wp99_test",
            criteria_fn="verify_wp99_exit_criteria",
            tier=99,
            description="Test entry",
        )
        assert e.wp_id == "WP99"
        assert e.tier == 99


# ===========================================================================
# TestWPRegistry
# ===========================================================================

class TestWPRegistry:
    def test_all_returns_list(self):
        entries = WPRegistry.all()
        assert isinstance(entries, list)
        assert len(entries) >= 10

    def test_all_has_wp17(self):
        entries = WPRegistry.all()
        ids = {e.wp_id for e in entries}
        assert "WP17" in ids

    def test_all_has_wp70(self):
        entries = WPRegistry.all()
        ids = {e.wp_id for e in entries}
        assert "WP70" in ids

    def test_by_tier_returns_subset(self):
        tier9 = WPRegistry.by_tier(9)
        assert isinstance(tier9, list)
        for e in tier9:
            assert e.tier == 9

    def test_by_tier_coverage(self):
        # Multiple tiers should be populated
        for tier in [2, 3, 9, 10, 11]:
            entries = WPRegistry.by_tier(tier)
            assert len(entries) >= 1, f"Tier {tier} has no entries"

    def test_count_54_or_more_entries(self):
        entries = WPRegistry.all()
        assert len(entries) >= 54  # WP17-WP70 (minus intentionally skipped ones)


# ===========================================================================
# TestImportChecker
# ===========================================================================

class TestImportChecker:
    def test_import_existing_module(self):
        entry = _entry("WP61", "prometheus.wp61_multigame_benchmark", "verify_wp61_exit_criteria")
        ok, err = ImportChecker.check(entry)
        assert ok is True
        assert err is None

    def test_import_nonexistent_module(self):
        entry = WPEntry(
            wp_id="WP99",
            module="prometheus.nonexistent_xyz",
            criteria_fn="verify_wp99_exit_criteria",
            tier=99,
            description="Fake",
        )
        ok, err = ImportChecker.check(entry)
        assert ok is False
        assert err is not None

    def test_import_error_message_is_string(self):
        entry = WPEntry(
            wp_id="WP99",
            module="prometheus.nonexistent_xyz",
            criteria_fn="verify_wp99_exit_criteria",
            tier=99,
            description="Fake",
        )
        _, err = ImportChecker.check(entry)
        assert isinstance(err, str)


# ===========================================================================
# TestCriteriaRunner
# ===========================================================================

class TestCriteriaRunner:
    def test_run_known_module(self):
        entry = _entry("WP61", "prometheus.wp61_multigame_benchmark", "verify_wp61_exit_criteria")
        criteria, err = CriteriaRunner.run(entry)
        assert isinstance(criteria, dict)

    def test_run_returns_6_criteria(self):
        entry = _entry("WP61", "prometheus.wp61_multigame_benchmark", "verify_wp61_exit_criteria")
        criteria, _ = CriteriaRunner.run(entry)
        assert len(criteria) == 6

    def test_run_nonexistent_raises_gracefully(self):
        entry = WPEntry(
            wp_id="WP99",
            module="prometheus.nonexistent_xyz",
            criteria_fn="verify_wp99_exit_criteria",
            tier=99,
            description="Fake",
        )
        criteria, err = CriteriaRunner.run(entry)
        assert err is not None


# ===========================================================================
# TestIntegrationTestSuite
# ===========================================================================

class TestIntegrationTestSuite:
    def test_import_only_mode(self):
        suite = _small_suite(run_criteria=False)
        report = suite.run()
        assert isinstance(report, IntegrationReport)

    def test_report_has_results(self):
        suite = _small_suite(run_criteria=False)
        report = suite.run()
        assert len(report.results) >= 2

    def test_all_imports_pass(self):
        suite = _small_suite(run_criteria=False)
        report = suite.run()
        for result in report.results:
            assert result.import_ok, f"Import failed for {result.wp_id}: {result.import_error}"

    def test_report_to_dict(self):
        suite = _small_suite(run_criteria=False)
        report = suite.run()
        d = report.to_dict()
        assert "results" in d
        assert "n_checked" in d or "total" in d or len(d) > 0

    def test_result_to_dict_keys(self):
        suite = _small_suite(run_criteria=False)
        report = suite.run()
        for result in report.results:
            d = result.to_dict()
            assert "wp_id" in d
            assert "import_ok" in d

    def test_full_registry_import_only(self):
        # All registered WPs should import cleanly
        suite = IntegrationTestSuite(run_criteria=False, timeout_per_wp_s=30.0)
        report = suite.run()
        failed = [r.wp_id for r in report.results if not r.import_ok]
        assert len(failed) == 0, f"Failed imports: {failed}"


# ===========================================================================
# TestWP67ExitCriteria
# ===========================================================================

class TestWP67ExitCriteria:
    def _report(self) -> IntegrationReport:
        suite = _small_suite(run_criteria=False)
        return suite.run()

    def test_returns_dict(self):
        assert isinstance(verify_wp67_exit_criteria(), dict)

    def test_six_criteria(self):
        assert len(verify_wp67_exit_criteria()) == 6

    def test_all_pass_with_report(self):
        report = self._report()
        result = verify_wp67_exit_criteria(report)
        for k, v in result.items():
            assert v, f"Criterion failed: '{k}'"

    def test_no_report_returns_dict(self):
        result = verify_wp67_exit_criteria(None)
        assert isinstance(result, dict)
        assert len(result) == 6


# ===========================================================================
# TestIntegration
# ===========================================================================

class TestIntegration:
    def test_full_suite_import_only(self):
        suite = IntegrationTestSuite(run_criteria=False, timeout_per_wp_s=30.0)
        report = suite.run()
        failed = [r for r in report.results if not r.import_ok]
        assert len(failed) == 0

    def test_criteria_pass_after_run(self):
        suite = _small_suite(run_criteria=False)
        report = suite.run()
        result = verify_wp67_exit_criteria(report)
        assert all(result.values()), f"Some criteria failed: {result}"
