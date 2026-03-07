"""
WP68 Test Suite: Formal Safety Verification Module
===================================================

TestSafetyProperty        Property fields, checker
TestSafetyPropertyRegistry Registry has 8 properties
TestSafetyAuditLog        Append, hash chaining, to_dict
TestSafetyVerifier        verify, issue_certificate, monitor
TestSafetyCertificate     Valid/expired certificates
TestRunSafetyAudit        Convenience function
TestWP68ExitCriteria      Six-criterion verifier
TestIntegration           End-to-end: audit → report
"""

import time
import pytest

from prometheus.wp68_safety_verification import (
    SafetyAuditLog,
    SafetyCertificate,
    SafetyCheckResult,
    SafetyMonitor,
    SafetyProperty,
    SafetyPropertyRegistry,
    SafetyReport,
    SafetyVerifier,
    run_safety_audit,
    verify_wp68_exit_criteria,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_state() -> dict:
    """State that passes all 8 default properties."""
    return {
        "alignment_score": 0.95,
        "deception_score": 0.02,
        "resource_usage": 0.5,
        "override_latency_ms": 50.0,
        "transparency_score": 0.9,
        "convergence_delta": 0.005,
        "explainability_score": 0.8,
        "self_reinforcement_factor": 0.1,
    }


def _unsafe_state() -> dict:
    """State that fails some properties."""
    return {
        "alignment_score": 0.2,
        "deception_score": 0.9,
        "resource_usage": 0.99,
        "override_latency_ms": 5000.0,
        "transparency_score": 0.1,
        "convergence_delta": 0.5,
        "explainability_score": 0.1,
        "self_reinforcement_factor": 0.95,
    }


def _verifier() -> SafetyVerifier:
    return SafetyVerifier(certificate_validity_s=3600.0)


# ===========================================================================
# TestSafetyProperty
# ===========================================================================

class TestSafetyProperty:
    def test_fields(self):
        prop = SafetyPropertyRegistry.all()[0]
        assert isinstance(prop.name, str)
        assert len(prop.name) > 0

    def test_checker_callable(self):
        prop = SafetyPropertyRegistry.all()[0]
        result = prop.checker(_safe_state())
        assert isinstance(result, bool)

    def test_to_dict(self):
        prop = SafetyPropertyRegistry.all()[0]
        d = prop.to_dict()
        assert "name" in d
        assert "description" in d

    def test_severity_field(self):
        prop = SafetyPropertyRegistry.all()[0]
        assert hasattr(prop, "severity")
        assert prop.severity in ("critical", "major", "minor")


# ===========================================================================
# TestSafetyPropertyRegistry
# ===========================================================================

class TestSafetyPropertyRegistry:
    def test_all_returns_8_properties(self):
        props = SafetyPropertyRegistry.all()
        assert len(props) == 8

    def test_names_unique(self):
        props = SafetyPropertyRegistry.all()
        names = [p.name for p in props]
        assert len(names) == len(set(names))

    def test_has_alignment_property(self):
        props = SafetyPropertyRegistry.all()
        names = [p.name for p in props]
        assert any("alignment" in n.lower() for n in names)

    def test_has_human_override_property(self):
        props = SafetyPropertyRegistry.all()
        names = [p.name for p in props]
        assert any("override" in n.lower() or "corrigib" in n.lower() for n in names)


# ===========================================================================
# TestSafetyAuditLog
# ===========================================================================

class TestSafetyAuditLog:
    def test_empty_log(self):
        log = SafetyAuditLog()
        assert len(log.entries) == 0

    def test_append_increases_length(self):
        log = SafetyAuditLog()
        results = [SafetyCheckResult(property_name="test", passed=True, value=1.0, message="ok")]
        log.append(results)
        assert len(log.entries) == 1

    def test_hash_chaining(self):
        log = SafetyAuditLog()
        results = [SafetyCheckResult(property_name="test", passed=True, value=1.0, message="ok")]
        log.append(results)
        log.append(results)
        # Each entry should have a hash
        assert all(hasattr(e, "hash") for e in log.entries)

    def test_hashes_differ(self):
        log = SafetyAuditLog()
        results = [SafetyCheckResult(property_name="test", passed=True, value=1.0, message="ok")]
        log.append(results)
        log.append(results)
        h1 = log.entries[0].hash
        h2 = log.entries[1].hash
        assert h1 != h2

    def test_to_dict(self):
        log = SafetyAuditLog()
        results = [SafetyCheckResult(property_name="test", passed=True, value=1.0, message="ok")]
        log.append(results)
        d = log.to_dict()
        assert "entries" in d

    def test_check_result_to_dict(self):
        r = SafetyCheckResult(property_name="alignment", passed=True, value=0.95, message="ok")
        d = r.to_dict()
        for k in ("property_name", "passed", "value", "message"):
            assert k in d


# ===========================================================================
# TestSafetyVerifier
# ===========================================================================

class TestSafetyVerifier:
    def test_verify_safe_state(self):
        verifier = _verifier()
        report = verifier.verify(_safe_state())
        assert isinstance(report, SafetyReport)
        assert report.all_passed

    def test_verify_unsafe_state(self):
        verifier = _verifier()
        report = verifier.verify(_unsafe_state())
        assert not report.all_passed

    def test_report_has_8_results(self):
        verifier = _verifier()
        report = verifier.verify(_safe_state())
        assert len(report.results) == 8

    def test_report_to_dict(self):
        verifier = _verifier()
        report = verifier.verify(_safe_state())
        d = report.to_dict()
        assert "all_passed" in d
        assert "results" in d

    def test_issue_certificate_on_pass(self):
        verifier = _verifier()
        verifier.verify(_safe_state())
        cert = verifier.issue_certificate()
        assert cert is not None
        assert isinstance(cert, SafetyCertificate)

    def test_no_certificate_on_fail(self):
        verifier = _verifier()
        verifier.verify(_unsafe_state())
        cert = verifier.issue_certificate()
        assert cert is None

    def test_audit_log_grows(self):
        verifier = _verifier()
        for _ in range(3):
            verifier.verify(_safe_state())
        assert len(verifier.audit_log.entries) == 3


# ===========================================================================
# TestSafetyCertificate
# ===========================================================================

class TestSafetyCertificate:
    def test_valid_certificate(self):
        verifier = _verifier()
        verifier.verify(_safe_state())
        cert = verifier.issue_certificate()
        assert cert is not None
        assert cert.is_valid()

    def test_expired_certificate(self):
        verifier = SafetyVerifier(certificate_validity_s=0.001)
        verifier.verify(_safe_state())
        cert = verifier.issue_certificate()
        time.sleep(0.05)
        assert not cert.is_valid()

    def test_certificate_to_dict(self):
        verifier = _verifier()
        verifier.verify(_safe_state())
        cert = verifier.issue_certificate()
        d = cert.to_dict()
        assert "issued_at" in d
        assert "expires_at" in d
        assert "valid" in d or "is_valid" in d


# ===========================================================================
# TestSafetyMonitor
# ===========================================================================

class TestSafetyMonitor:
    def test_monitor_safe_states(self):
        verifier = _verifier()
        monitor = SafetyMonitor(verifier=verifier)
        for _ in range(3):
            monitor.check(_safe_state())
        summary = monitor.summary()
        assert isinstance(summary, dict)

    def test_monitor_detects_unsafe(self):
        verifier = _verifier()
        monitor = SafetyMonitor(verifier=verifier)
        monitor.check(_safe_state())
        monitor.check(_unsafe_state())
        summary = monitor.summary()
        assert summary.get("n_failed", 0) >= 1 or summary.get("pass_rate", 1.0) < 1.0


# ===========================================================================
# TestRunSafetyAudit
# ===========================================================================

class TestRunSafetyAudit:
    def test_convenience_function(self):
        verifier, report = run_safety_audit(n_checks=3)
        assert isinstance(verifier, SafetyVerifier)
        assert isinstance(report, SafetyReport)

    def test_custom_state_fn(self):
        verifier, report = run_safety_audit(n_checks=2, state_fn=_safe_state)
        assert report.all_passed

    def test_n_checks_respected(self):
        verifier, _ = run_safety_audit(n_checks=5)
        assert len(verifier.audit_log.entries) == 5


# ===========================================================================
# TestWP68ExitCriteria
# ===========================================================================

class TestWP68ExitCriteria:
    def _report(self) -> SafetyReport:
        verifier, report = run_safety_audit(n_checks=5, state_fn=_safe_state)
        return report

    def test_returns_dict(self):
        assert isinstance(verify_wp68_exit_criteria(), dict)

    def test_six_criteria(self):
        assert len(verify_wp68_exit_criteria()) == 6

    def test_all_pass_with_report(self):
        report = self._report()
        result = verify_wp68_exit_criteria(report)
        for k, v in result.items():
            assert v, f"Criterion failed: '{k}'"

    def test_no_report_returns_dict(self):
        result = verify_wp68_exit_criteria(None)
        assert isinstance(result, dict)
        assert len(result) == 6


# ===========================================================================
# TestIntegration
# ===========================================================================

class TestIntegration:
    def test_end_to_end_audit(self):
        verifier, report = run_safety_audit(n_checks=5, state_fn=_safe_state)
        assert len(verifier.audit_log.entries) == 5
        assert report.all_passed
        cert = verifier.issue_certificate()
        assert cert is not None
        assert cert.is_valid()

    def test_criteria_pass_after_full_audit(self):
        _, report = run_safety_audit(n_checks=5, state_fn=_safe_state)
        result = verify_wp68_exit_criteria(report)
        assert all(result.values()), f"Some criteria failed: {result}"
