"""
WP15 — Multi-Objective Safety Aggregation Tests
================================================

88 tests across 10 classes covering:

- NormalisedVerdict dataclass
- All 9 built-in VerdictAdapters
- WeightedSumAggregator
- ParetoFrontAggregator
- ConformalPValueAggregator
- CompositeSafetyGate
- make_composite_gate factory
- CompositeSafetyVerdict summary
- Edge cases (all-abstain, single WP, empty)
- Benchmark runner
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pytest

from prometheus.multi_objective_safety import (
    SafetyLevel,
    NormalisedVerdict,
    CompositeSafetyVerdict,
    CompositeSafetyGate,
    WeightedSumAggregator,
    ParetoFrontAggregator,
    ConformalPValueAggregator,
    OODAdapter,
    AdversarialAdapter,
    FormalVerificationAdapter,
    CertifiedRobustnessAdapter,
    DebateAdapter,
    UncertaintyAdapter,
    RewardHackingAdapter,
    CausalSafetyAdapter,
    CorrigibilityAdapter,
    MCSSupervisorAdapter,
    make_composite_gate,
    composite_safety_summary_table,
    _BUILTIN_ADAPTERS,
)
from benchmarks.multi_objective_safety_benchmark import (
    MultiObjectiveSafetyBenchmark,
    _safe_ood, _unsafe_ood,
    _safe_fv, _unsafe_fv,
    _safe_debate, _unsafe_debate,
    _safe_hacking, _unsafe_hacking,
    _safe_corr, _unsafe_corr,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_nv(score: float = 1.0, cert: float = 0.9, sev: float = 0.0,
             wp_id: str = "WP0", abstain: bool = False,
             veto: bool = False) -> NormalisedVerdict:
    return NormalisedVerdict(
        wp_id=wp_id, wp_name="Test",
        safety_score=score, certainty=cert, severity=sev,
        abstain=abstain, veto=veto,
    )


# ---------------------------------------------------------------------------
# 1. NormalisedVerdict
# ---------------------------------------------------------------------------

class TestNormalisedVerdict:
    def test_fields_present(self):
        v = _make_nv()
        assert hasattr(v, "wp_id")
        assert hasattr(v, "safety_score")
        assert hasattr(v, "certainty")
        assert hasattr(v, "severity")
        assert hasattr(v, "abstain")
        assert hasattr(v, "veto")

    def test_defaults(self):
        v = NormalisedVerdict("X", "X", 0.5, 0.5, 0.0)
        assert not v.abstain
        assert not v.veto
        assert v.raw is None
        assert v.elapsed_s == 0.0

    def test_score_range(self):
        v = _make_nv(score=0.8)
        assert 0.0 <= v.safety_score <= 1.0

    def test_repr(self):
        v = _make_nv()
        assert "WP0" in repr(v)


# ---------------------------------------------------------------------------
# 2. Adapters — OOD (WP2)
# ---------------------------------------------------------------------------

class TestOODAdapter:
    @pytest.fixture
    def adapter(self):
        return OODAdapter()

    def test_safe_verdict(self, adapter):
        n = adapter.adapt(_safe_ood())
        assert n.safety_score >= 0.7
        assert not n.abstain

    def test_unsafe_halt(self, adapter):
        n = adapter.adapt(_unsafe_ood())
        assert n.safety_score == 0.0
        assert n.veto

    def test_none_abstains(self, adapter):
        n = adapter.adapt(None)
        assert n.abstain

    def test_wp_id(self, adapter):
        assert adapter.wp_id == "WP2"

    def test_caution_mode(self, adapter):
        class R:
            allow_action = False
            confidence_scale = 1.0
            class safe_mode:
                name = "CAUTION"
        n = adapter.adapt(R())
        assert 0.5 <= n.safety_score <= 0.8


# ---------------------------------------------------------------------------
# 3. Adapters — Formal Verification (WP7)
# ---------------------------------------------------------------------------

class TestFormalVerificationAdapter:
    @pytest.fixture
    def adapter(self):
        return FormalVerificationAdapter()

    def test_safe(self, adapter):
        n = adapter.adapt(_safe_fv())
        assert n.safety_score >= 0.9
        assert n.severity == 0.0

    def test_unsafe_high_severity(self, adapter):
        n = adapter.adapt(_unsafe_fv(sev=9))
        assert n.safety_score < 0.5
        assert n.veto

    def test_unsafe_low_severity(self, adapter):
        n = adapter.adapt(_unsafe_fv(sev=3))
        assert n.safety_score < 0.9
        assert not n.veto

    def test_fallback_reduces_certainty(self, adapter):
        class R:
            is_safe       = True
            violations    = []
            used_fallback = True
        n = adapter.adapt(R())
        assert n.certainty < 0.90

    def test_none_abstains(self, adapter):
        n = adapter.adapt(None)
        assert n.abstain


# ---------------------------------------------------------------------------
# 4. Adapters — Debate (WP10)
# ---------------------------------------------------------------------------

class TestDebateAdapter:
    @pytest.fixture
    def adapter(self):
        return DebateAdapter()

    def test_safe(self, adapter):
        n = adapter.adapt(_safe_debate())
        assert n.safety_score == 1.0
        assert n.severity == 0.0

    def test_unsafe_high_conf(self, adapter):
        n = adapter.adapt(_unsafe_debate())
        assert n.safety_score == 0.0
        assert n.veto       # confidence 0.85 ≥ 0.8

    def test_abstain_winner(self, adapter):
        class R:
            is_safe    = True
            winner     = "abstain"
            confidence = 0.5
        n = adapter.adapt(R())
        assert n.abstain

    def test_none_abstains(self, adapter):
        assert adapter.adapt(None).abstain


# ---------------------------------------------------------------------------
# 5. Adapters — Reward Hacking (WP12)
# ---------------------------------------------------------------------------

class TestRewardHackingAdapter:
    @pytest.fixture
    def adapter(self):
        return RewardHackingAdapter()

    def test_safe(self, adapter):
        n = adapter.adapt(_safe_hacking())
        assert n.safety_score == 1.0
        assert n.severity == 0.0

    def test_unsafe_high_penalty(self, adapter):
        n = adapter.adapt(_unsafe_hacking())
        assert n.safety_score <= 0.2
        assert n.severity >= 8.0

    def test_none_abstains(self, adapter):
        assert adapter.adapt(None).abstain

    def test_partial_penalty(self, adapter):
        class R:
            hacking_detected = True
            penalty_applied  = 0.4
            tampering_report = None
        n = adapter.adapt(R())
        assert 0.5 <= n.safety_score <= 0.7


# ---------------------------------------------------------------------------
# 6. Adapters — Corrigibility (WP14)
# ---------------------------------------------------------------------------

class TestCorrigibilityAdapter:
    @pytest.fixture
    def adapter(self):
        return CorrigibilityAdapter()

    def test_safe(self, adapter):
        n = adapter.adapt(_safe_corr())
        assert n.safety_score == 1.0
        assert n.severity == 0.0

    def test_unsafe_high_severity(self, adapter):
        n = adapter.adapt(_unsafe_corr(sev=9))
        assert n.safety_score < 0.3
        assert n.veto

    def test_unsafe_low_severity(self, adapter):
        n = adapter.adapt(_unsafe_corr(sev=4))
        assert not n.veto

    def test_none_abstains(self, adapter):
        assert adapter.adapt(None).abstain


# ---------------------------------------------------------------------------
# 7. Adapters — remaining (AdversarialAdapter, CertifiedRobustnessAdapter,
#    UncertaintyAdapter, CausalSafetyAdapter, MCSSupervisorAdapter)
# ---------------------------------------------------------------------------

class TestRemainingAdapters:
    def test_adversarial_bool_safe(self):
        n = AdversarialAdapter().adapt(True)
        assert n.safety_score == 1.0

    def test_adversarial_bool_unsafe(self):
        n = AdversarialAdapter().adapt(False)
        assert n.safety_score == 0.0

    def test_adversarial_float_score(self):
        n = AdversarialAdapter().adapt(0.3)   # injection_score=0.3
        assert 0.6 <= n.safety_score <= 0.8

    def test_certified_abstain(self):
        class R:
            abstain         = True
            p_lower_bound   = 0.5
            confidence      = 0.95
            certified_radius= 0.0
        n = CertifiedRobustnessAdapter().adapt(R())
        assert n.abstain

    def test_certified_safe(self):
        class R:
            abstain         = False
            p_lower_bound   = 0.95
            confidence      = 0.95
            certified_radius= 0.5
        n = CertifiedRobustnessAdapter().adapt(R())
        assert n.safety_score >= 0.8

    def test_uncertainty_abstain_action(self):
        class R:
            recommended_action = "abstain"
            is_certain         = False
            interval           = None
        n = UncertaintyAdapter().adapt(R())
        assert n.abstain

    def test_uncertainty_proceed(self):
        class Interval:
            width = 0.2
        class R:
            recommended_action = "proceed"
            is_certain         = True
            interval           = Interval()
        n = UncertaintyAdapter().adapt(R())
        assert not n.abstain
        assert n.safety_score >= 0.8

    def test_causal_positive_outcome(self):
        class Edge:
            weight     = 0.1
            confidence = 0.8
        class R:
            safety_outcome_value = 2.0
            causal_edges         = [Edge()]
        n = CausalSafetyAdapter().adapt(R())
        assert n.safety_score > 0.8

    def test_causal_negative_outcome(self):
        class Edge:
            weight     = 0.9
            confidence = 0.7
        class R:
            safety_outcome_value = -2.0
            causal_edges         = [Edge()]
        n = CausalSafetyAdapter().adapt(R())
        assert n.safety_score < 0.2

    def test_mcs_safe(self):
        class R:
            is_safe  = True
            severity = 0
        n = MCSSupervisorAdapter().adapt(R())
        assert n.safety_score == 1.0

    def test_mcs_unsafe(self):
        class R:
            is_safe  = False
            severity = 8
        n = MCSSupervisorAdapter().adapt(R())
        assert n.safety_score < 0.5
        assert n.veto

    def test_all_adapters_handle_none(self):
        for wp_id, adapter in _BUILTIN_ADAPTERS.items():
            n = adapter.adapt(None)
            assert n.abstain, f"{wp_id} did not abstain on None"


# ---------------------------------------------------------------------------
# 8. Aggregators
# ---------------------------------------------------------------------------

class TestWeightedSumAggregator:
    @pytest.fixture
    def agg(self):
        return WeightedSumAggregator()

    def _safe_verts(self):
        return [_make_nv(1.0, 0.9, 0.0, f"WP{i}") for i in range(4)]

    def _unsafe_verts(self):
        return [_make_nv(0.0, 0.9, 9.0, f"WP{i}") for i in range(4)]

    def test_all_safe_allowed(self, agg):
        _, _, allowed = agg.aggregate(self._safe_verts(), threshold=0.5)
        assert allowed

    def test_all_unsafe_blocked(self, agg):
        _, _, allowed = agg.aggregate(self._unsafe_verts(), threshold=0.5)
        assert not allowed

    def test_empty_active_passes(self, agg):
        abstains = [_make_nv(abstain=True, wp_id=f"WP{i}") for i in range(3)]
        _, _, allowed = agg.aggregate(abstains)
        assert allowed   # no information → cautious pass

    def test_composite_score_bounded(self, agg):
        verts = self._safe_verts()
        score, _, _ = agg.aggregate(verts)
        assert 0.0 <= score <= 1.0

    def test_weights_influence_score(self, agg):
        # One unsafe WP with high weight should lower score more
        high_w_agg = WeightedSumAggregator(weights={"WP0": 10.0})
        verts_a = [_make_nv(1.0, 0.9, 0.0, "WP0"),
                   _make_nv(0.0, 0.9, 0.0, "WP1")]
        score_a, _, _ = high_w_agg.aggregate(verts_a)
        low_w_agg = WeightedSumAggregator(weights={"WP0": 0.1})
        score_b, _, _ = low_w_agg.aggregate(verts_a)
        # WP0 is safe; WP1 is unsafe.  High weight on WP0 → higher composite
        assert score_a > score_b

    def test_certainty_averaged(self, agg):
        verts = [_make_nv(1.0, 0.8, 0.0, "WP0"),
                 _make_nv(1.0, 0.6, 0.0, "WP1")]
        _, cert, _ = agg.aggregate(verts)
        assert 0.6 <= cert <= 0.9


class TestParetoFrontAggregator:
    @pytest.fixture
    def agg(self):
        return ParetoFrontAggregator(score_threshold=0.5, certainty_threshold=0.4)

    def test_dominates_allowed(self, agg):
        verts = [_make_nv(0.9, 0.9, 0.0), _make_nv(0.8, 0.8, 0.0)]
        _, _, allowed = agg.aggregate(verts)
        assert allowed

    def test_dominated_blocked(self, agg):
        verts = [_make_nv(0.1, 0.1, 9.0), _make_nv(0.2, 0.1, 9.0)]
        _, _, allowed = agg.aggregate(verts)
        assert not allowed

    def test_empty_passes(self, agg):
        _, _, allowed = agg.aggregate([])
        assert allowed

    def test_score_bounded(self, agg):
        verts = [_make_nv(0.6, 0.7, 0.0)]
        score, cert, _ = agg.aggregate(verts)
        assert 0.0 <= score <= 1.0


class TestConformalPValueAggregator:
    @pytest.fixture
    def agg(self):
        a = ConformalPValueAggregator(alpha=0.05)
        # Calibrate with known-safe scores
        for wp in ["WP2", "WP7", "WP14"]:
            a.calibrate(wp, [0.8, 0.9, 0.85, 0.95, 1.0])
        return a

    def test_all_safe_allowed(self, agg):
        verts = [_make_nv(1.0, 0.9, 0.0, "WP2"),
                 _make_nv(1.0, 0.9, 0.0, "WP7"),
                 _make_nv(1.0, 0.9, 0.0, "WP14")]
        _, _, allowed = agg.aggregate(verts, threshold=0.5)
        assert allowed

    def test_all_unsafe_blocked(self, agg):
        verts = [_make_nv(0.0, 0.9, 9.0, "WP2"),
                 _make_nv(0.0, 0.9, 9.0, "WP7"),
                 _make_nv(0.0, 0.9, 9.0, "WP14")]
        _, _, allowed = agg.aggregate(verts, threshold=0.5)
        assert not allowed

    def test_calibrate_adds_data(self, agg):
        before = len(agg._calibration.get("WP2", []))
        agg.calibrate("WP2", [0.7, 0.8])
        after = len(agg._calibration.get("WP2", []))
        assert after == before + 2

    def test_uncalibrated_wp_uses_score(self, agg):
        # WP99 has no calibration — should use score directly
        verts = [_make_nv(0.9, 0.9, 0.0, "WP99")]
        score, _, _ = agg.aggregate(verts)
        assert score >= 0.8


# ---------------------------------------------------------------------------
# 9. CompositeSafetyGate
# ---------------------------------------------------------------------------

class TestCompositeSafetyGate:
    @pytest.fixture
    def gate(self):
        return make_composite_gate(method="weighted_sum", threshold=0.5, veto_severity=8.0)

    def test_all_safe_allowed(self, gate):
        v = gate.evaluate({"WP7": _safe_fv(), "WP14": _safe_corr(), "WP12": _safe_hacking()})
        assert v.allowed

    def test_veto_blocks(self, gate):
        v = gate.evaluate({"WP7": _safe_fv(), "WP14": _unsafe_corr(sev=9), "WP12": _safe_hacking()})
        assert not v.allowed
        assert "WP14" in v.vetoed_by

    def test_all_abstain_passes(self, gate):
        v = gate.evaluate({"WP7": None, "WP14": None})
        assert v.allowed          # no information → cautious pass

    def test_safety_level_safe(self, gate):
        v = gate.evaluate({"WP7": _safe_fv(), "WP14": _safe_corr()})
        assert v.safety_level == SafetyLevel.SAFE

    def test_safety_level_unsafe(self, gate):
        v = gate.evaluate({"WP7": _unsafe_fv(sev=9)})
        assert v.safety_level in (SafetyLevel.UNSAFE, SafetyLevel.CAUTION)

    def test_composite_score_bounded(self, gate):
        v = gate.evaluate({"WP7": _safe_fv(), "WP14": _safe_corr()})
        assert 0.0 <= v.composite_score <= 1.0

    def test_certainty_bounded(self, gate):
        v = gate.evaluate({"WP7": _safe_fv()})
        assert 0.0 <= v.composite_certainty <= 1.0

    def test_summary_contains_level(self, gate):
        v = gate.evaluate({"WP7": _safe_fv()})
        assert "ALLOWED" in v.summary() or "BLOCKED" in v.summary()

    def test_stats_after_evaluations(self, gate):
        gate.evaluate({"WP7": _safe_fv()})
        gate.evaluate({"WP7": _unsafe_fv(sev=9)})
        s = gate.stats()
        assert s["n_evaluated"] == 2

    def test_block_rate(self, gate):
        gate.evaluate({"WP7": _safe_fv()})
        gate.evaluate({"WP7": _unsafe_fv(sev=9)})
        assert 0.4 <= gate.block_rate() <= 0.6

    def test_reset_clears_history(self, gate):
        gate.evaluate({"WP7": _safe_fv()})
        gate.reset()
        assert gate.stats()["n_evaluated"] == 0

    def test_unknown_wp_id_abstains(self, gate):
        v = gate.evaluate({"WP99": _safe_fv()})
        assert "WP99" in v.abstained

    def test_elapsed_positive(self, gate):
        v = gate.evaluate({"WP7": _safe_fv()})
        assert v.elapsed_s >= 0.0

    def test_verdicts_list_populated(self, gate):
        v = gate.evaluate({"WP7": _safe_fv(), "WP14": _safe_corr()})
        assert len(v.verdicts) == 2


# ---------------------------------------------------------------------------
# 10. make_composite_gate factory & summary table
# ---------------------------------------------------------------------------

class TestFactory:
    def test_weighted_sum(self):
        g = make_composite_gate("weighted_sum")
        assert isinstance(g.aggregator, WeightedSumAggregator)

    def test_pareto_front(self):
        g = make_composite_gate("pareto_front")
        assert isinstance(g.aggregator, ParetoFrontAggregator)

    def test_conformal_pvalue(self):
        g = make_composite_gate("conformal_pvalue")
        assert isinstance(g.aggregator, ConformalPValueAggregator)

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError):
            make_composite_gate("nonexistent")

    def test_threshold_propagated(self):
        g = make_composite_gate("weighted_sum", threshold=0.7)
        assert g.threshold == 0.7

    def test_veto_severity_propagated(self):
        g = make_composite_gate("weighted_sum", veto_severity=6.0)
        assert g.veto_severity == 6.0


class TestSummaryTable:
    def test_returns_string(self):
        gate = make_composite_gate()
        v = gate.evaluate({"WP7": _safe_fv()})
        table = composite_safety_summary_table([v])
        assert isinstance(table, str)

    def test_contains_allowed(self):
        gate = make_composite_gate()
        v = gate.evaluate({"WP7": _safe_fv()})
        table = composite_safety_summary_table([v])
        assert "YES" in table or "NO" in table

    def test_multiple_verdicts(self):
        gate = make_composite_gate()
        verts = [
            gate.evaluate({"WP7": _safe_fv()}),
            gate.evaluate({"WP7": _unsafe_fv(sev=9)}),
        ]
        table = composite_safety_summary_table(verts)
        assert "WP15" in table


# ---------------------------------------------------------------------------
# 11. Benchmark runner
# ---------------------------------------------------------------------------

class TestBenchmark:
    @pytest.fixture(scope="class")
    def bench(self):
        return MultiObjectiveSafetyBenchmark(seed=42)

    @pytest.fixture(scope="class")
    def results(self, bench):
        return bench.run_all()

    def test_four_scenarios(self, results):
        assert len(results) == 4

    def test_scenario_names(self, results):
        names = {r.scenario for r in results}
        assert "adapter_normalisation"   in names
        assert "aggregator_consistency"  in names
        assert "veto_propagation"        in names
        assert "end_to_end_gate"         in names

    def test_all_scenarios_pass(self, results):
        for r in results:
            assert r.passed, f"Scenario '{r.scenario}' failed: {r.metrics}"

    def test_summary_table(self, bench, results):
        table = bench.summary_table(results)
        assert "WP15" in table
        assert "PASS" in table
