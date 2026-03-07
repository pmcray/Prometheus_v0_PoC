"""
WP65 Test Suite: Streamlit Monitoring Dashboard
================================================

TestDashboardConfig       Config dataclass, defaults
TestDashboardSection      Section structure
TestDataContainers        EloChartData, ARCProgressData, SafetyStatusData
TestStreamlitFallback     HTML rendering, port finding
TestDashboardServer       Instantiation, server selection
TestWP65ExitCriteria      Six-criterion verifier
TestIntegration           End-to-end: server → report
"""

import pytest

from prometheus.wp65_dashboard import (
    ARCProgressData,
    DashboardConfig,
    DashboardSection,
    DashboardServer,
    EloChartData,
    PrometheusStreamlitApp,
    SafetyStatusData,
    StreamlitFallbackDashboard,
    verify_wp65_exit_criteria,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _config() -> DashboardConfig:
    return DashboardConfig(title="Test Dashboard", port=0, refresh_interval_s=5)


def _server() -> DashboardServer:
    return DashboardServer(config=_config(), force_fallback=True)


# ===========================================================================
# TestDashboardConfig
# ===========================================================================

class TestDashboardConfig:
    def test_fields(self):
        c = _config()
        assert c.title == "Test Dashboard"
        assert c.refresh_interval_s == 5

    def test_to_dict(self):
        d = _config().to_dict()
        for k in ("title", "port", "refresh_interval_s"):
            assert k in d, f"Missing key: {k}"

    def test_default_config(self):
        c = DashboardConfig()
        assert isinstance(c.title, str)
        assert c.refresh_interval_s > 0


# ===========================================================================
# TestDashboardSection
# ===========================================================================

class TestDashboardSection:
    def test_fields(self):
        sec = DashboardSection(
            title="ELO Tracker",
            content_fn=lambda: {"elo": 1500},
            page_id="elo",
        )
        assert sec.title == "ELO Tracker"
        assert sec.page_id == "elo"

    def test_content_fn_callable(self):
        sec = DashboardSection(
            title="Test",
            content_fn=lambda: {"key": "value"},
            page_id="test",
        )
        result = sec.content_fn()
        assert result == {"key": "value"}

    def test_to_dict(self):
        sec = DashboardSection(
            title="Test",
            content_fn=lambda: {},
            page_id="test",
        )
        d = sec.to_dict()
        assert "title" in d
        assert "page_id" in d


# ===========================================================================
# TestDataContainers
# ===========================================================================

class TestDataContainers:
    def test_elo_chart_data(self):
        d = EloChartData(
            agents=["A", "B"],
            elo_scores=[1500.0, 1400.0],
            timestamps=["2025-01-01"],
        )
        assert len(d.agents) == 2

    def test_elo_chart_to_dict(self):
        d = EloChartData(agents=["A"], elo_scores=[1500.0], timestamps=["t"])
        rd = d.to_dict()
        assert "agents" in rd
        assert "elo_scores" in rd

    def test_arc_progress_data(self):
        d = ARCProgressData(
            n_tasks=100,
            solved=10,
            solve_rate=0.10,
            history=[0.05, 0.08, 0.10],
        )
        assert d.solve_rate == 0.10

    def test_arc_progress_to_dict(self):
        d = ARCProgressData(n_tasks=10, solved=1, solve_rate=0.1, history=[])
        rd = d.to_dict()
        assert "solve_rate" in rd

    def test_safety_status_data(self):
        d = SafetyStatusData(
            properties_checked=8,
            properties_passed=8,
            last_audit_ts="2025-01-01T00:00:00",
            certificate_valid=True,
        )
        assert d.certificate_valid is True

    def test_safety_status_to_dict(self):
        d = SafetyStatusData(
            properties_checked=8,
            properties_passed=6,
            last_audit_ts="ts",
            certificate_valid=False,
        )
        rd = d.to_dict()
        assert "properties_checked" in rd
        assert "certificate_valid" in rd


# ===========================================================================
# TestStreamlitFallbackDashboard
# ===========================================================================

class TestStreamlitFallbackDashboard:
    def test_instantiate(self):
        dash = StreamlitFallbackDashboard(config=_config())
        assert dash is not None

    def test_render_html_returns_string(self):
        dash = StreamlitFallbackDashboard(config=_config())
        html = dash.render_html(page_id="overview")
        assert isinstance(html, str)
        assert len(html) > 0

    def test_render_html_contains_title(self):
        dash = StreamlitFallbackDashboard(config=_config())
        html = dash.render_html(page_id="overview")
        assert "Test Dashboard" in html or "Prometheus" in html

    def test_render_html_is_valid_html(self):
        dash = StreamlitFallbackDashboard(config=_config())
        html = dash.render_html(page_id="overview")
        assert "<html" in html.lower() or "<!doctype" in html.lower() or "<div" in html.lower()


# ===========================================================================
# TestDashboardServer
# ===========================================================================

class TestDashboardServer:
    def test_instantiate_fallback(self):
        server = _server()
        assert server is not None

    def test_uses_fallback_when_forced(self):
        server = _server()
        assert server.using_fallback is True

    def test_get_status(self):
        server = _server()
        status = server.get_status()
        assert isinstance(status, dict)
        assert "running" in status or "mode" in status

    def test_to_dict(self):
        server = _server()
        d = server.to_dict()
        assert isinstance(d, dict)


# ===========================================================================
# TestWP65ExitCriteria
# ===========================================================================

class TestWP65ExitCriteria:
    def test_returns_dict(self):
        assert isinstance(verify_wp65_exit_criteria(), dict)

    def test_six_criteria(self):
        assert len(verify_wp65_exit_criteria()) == 6

    def test_all_pass_with_server(self):
        server = _server()
        result = verify_wp65_exit_criteria(server)
        for k, v in result.items():
            assert v, f"Criterion failed: '{k}'"

    def test_no_server_returns_dict(self):
        result = verify_wp65_exit_criteria(None)
        assert isinstance(result, dict)
        assert len(result) == 6


# ===========================================================================
# TestIntegration
# ===========================================================================

class TestIntegration:
    def test_server_status_after_init(self):
        server = DashboardServer(force_fallback=True)
        status = server.get_status()
        assert isinstance(status, dict)

    def test_criteria_pass(self):
        server = _server()
        result = verify_wp65_exit_criteria(server)
        assert all(result.values()), f"Some criteria failed: {result}"
