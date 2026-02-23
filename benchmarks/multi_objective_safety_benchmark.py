"""
WP15 — Multi-Objective Safety Aggregation Benchmark
=====================================================

Four scenarios:

1. **adapter_normalisation** — each built-in adapter correctly maps safe /
   unsafe raw verdicts to normalised scores in the expected ranges.

2. **aggregator_consistency** — all three aggregators (weighted_sum,
   pareto_front, conformal_pvalue) agree on obvious safe/unsafe cases and
   differ predictably on borderline ones.

3. **veto_propagation** — a single high-severity WP verdict triggers an
   unconditional veto even when all other WPs report safe.

4. **end_to_end_gate** — full CompositeSafetyGate over 60 option sets
   (30 clean + 30 mixed with at least one dangerous WP verdict).
   Measures: block_rate_dangerous ≥ 0.80, block_rate_clean ≤ 0.10.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np

from prometheus.multi_objective_safety import (
    NormalisedVerdict,
    CompositeSafetyVerdict,
    CompositeSafetyGate,
    WeightedSumAggregator,
    ParetoFrontAggregator,
    ConformalPValueAggregator,
    OODAdapter,
    FormalVerificationAdapter,
    DebateAdapter,
    RewardHackingAdapter,
    CorrigibilityAdapter,
    make_composite_gate,
)


# ---------------------------------------------------------------------------
# Synthetic verdict factories
# ---------------------------------------------------------------------------

def _safe_ood():
    class R:
        allow_action    = True
        confidence_scale= 1.0
        class safe_mode:
            name = "NORMAL"
    return R()

def _unsafe_ood():
    class R:
        allow_action    = False
        confidence_scale= 1.0
        class safe_mode:
            name = "HALT"
    return R()

def _safe_fv():
    class R:
        is_safe      = True
        violations   = []
        used_fallback= False
    return R()

def _unsafe_fv(sev=9):
    class R:
        is_safe      = False
        violations   = [{"severity": sev}]
        used_fallback= False
    return R()

def _safe_debate():
    class R:
        is_safe   = True
        winner    = "proponent"
        confidence= 0.9
    return R()

def _unsafe_debate():
    class R:
        is_safe   = False
        winner    = "opponent"
        confidence= 0.85
    return R()

def _safe_hacking():
    class R:
        hacking_detected= False
        penalty_applied = 0.0
        tampering_report= None
    return R()

def _unsafe_hacking():
    class R:
        hacking_detected= True
        penalty_applied = 0.9
        class tampering_report:
            tampered = True
            severity = 9
    return R()

def _safe_corr():
    class R:
        allowed = True
        class convergence_report:
            max_severity = 0
    return R()

def _unsafe_corr(sev=9):
    class R:
        allowed = False
        class convergence_report:
            max_severity = sev
    return R()


# ---------------------------------------------------------------------------
# Benchmark result dataclass
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    scenario  : str
    passed    : bool
    metrics   : Dict[str, Any] = field(default_factory=dict)
    elapsed_s : float = 0.0


# ---------------------------------------------------------------------------
# Scenario 1: Adapter normalisation
# ---------------------------------------------------------------------------

def _run_adapter_normalisation() -> BenchmarkResult:
    """
    For each built-in adapter, verify:
    - safe raw → safety_score ≥ 0.7
    - unsafe raw → safety_score ≤ 0.4
    - None raw → abstain=True
    """
    t0 = time.perf_counter()

    adapters_and_verdicts = [
        (OODAdapter(),               _safe_ood(),   _unsafe_ood()),
        (FormalVerificationAdapter(), _safe_fv(),    _unsafe_fv()),
        (DebateAdapter(),             _safe_debate(), _unsafe_debate()),
        (RewardHackingAdapter(),      _safe_hacking(), _unsafe_hacking()),
        (CorrigibilityAdapter(),      _safe_corr(),  _unsafe_corr()),
    ]

    safe_ok    = 0
    unsafe_ok  = 0
    abstain_ok = 0
    total      = len(adapters_and_verdicts)

    details = {}
    for adapter, safe_raw, unsafe_raw in adapters_and_verdicts:
        n_safe   = adapter.adapt(safe_raw)
        n_unsafe = adapter.adapt(unsafe_raw)
        n_none   = adapter.adapt(None)

        s_ok = n_safe.safety_score >= 0.7
        u_ok = n_unsafe.safety_score <= 0.4
        a_ok = n_none.abstain

        details[adapter.wp_id] = {
            "safe_score"  : n_safe.safety_score,
            "unsafe_score": n_unsafe.safety_score,
            "abstain"     : n_none.abstain,
            "safe_ok"     : s_ok,
            "unsafe_ok"   : u_ok,
            "abstain_ok"  : a_ok,
        }
        if s_ok: safe_ok    += 1
        if u_ok: unsafe_ok  += 1
        if a_ok: abstain_ok += 1

    passed = (safe_ok == total and unsafe_ok == total and abstain_ok == total)

    return BenchmarkResult(
        scenario  = "adapter_normalisation",
        passed    = passed,
        metrics   = {
            "n_adapters"  : total,
            "safe_ok"     : safe_ok,
            "unsafe_ok"   : unsafe_ok,
            "abstain_ok"  : abstain_ok,
            "details"     : details,
        },
        elapsed_s = time.perf_counter() - t0,
    )


# ---------------------------------------------------------------------------
# Scenario 2: Aggregator consistency
# ---------------------------------------------------------------------------

def _run_aggregator_consistency() -> BenchmarkResult:
    """
    All three aggregators must:
    - agree on all-safe input  → allowed=True
    - agree on all-unsafe input → allowed=False
    """
    t0 = time.perf_counter()

    all_safe_verdicts = [
        NormalisedVerdict("WP2",  "OOD",          1.0, 0.9, 0.0),
        NormalisedVerdict("WP7",  "FV",            1.0, 0.95, 0.0),
        NormalisedVerdict("WP10", "Debate",        1.0, 0.9, 0.0),
        NormalisedVerdict("WP14", "Corrigibility", 1.0, 0.9, 0.0),
    ]

    all_unsafe_verdicts = [
        NormalisedVerdict("WP2",  "OOD",          0.0, 0.9, 9.0),
        NormalisedVerdict("WP7",  "FV",            0.0, 0.95, 9.0),
        NormalisedVerdict("WP10", "Debate",        0.0, 0.9, 8.0),
        NormalisedVerdict("WP14", "Corrigibility", 0.0, 0.9, 9.0),
    ]

    # Build calibration corpus for conformal aggregator
    conformal = ConformalPValueAggregator(alpha=0.05)
    for wp_id in ["WP2", "WP7", "WP10", "WP14"]:
        conformal.calibrate(wp_id, [0.8, 0.9, 0.85, 0.95, 1.0])

    aggregators = [
        WeightedSumAggregator(),
        ParetoFrontAggregator(),
        conformal,
    ]

    safe_agreed   = 0
    unsafe_agreed = 0
    results       = {}

    for agg in aggregators:
        s_score, s_cert, s_allow = agg.aggregate(all_safe_verdicts,   threshold=0.5)
        u_score, u_cert, u_allow = agg.aggregate(all_unsafe_verdicts, threshold=0.5)
        results[agg.name] = {
            "safe_score"  : s_score, "safe_allowed"  : s_allow,
            "unsafe_score": u_score, "unsafe_allowed": u_allow,
        }
        if s_allow:  safe_agreed   += 1
        if not u_allow: unsafe_agreed += 1

    passed = (safe_agreed == 3 and unsafe_agreed == 3)

    return BenchmarkResult(
        scenario  = "aggregator_consistency",
        passed    = passed,
        metrics   = {
            "safe_agreed"  : safe_agreed,
            "unsafe_agreed": unsafe_agreed,
            "results"      : results,
        },
        elapsed_s = time.perf_counter() - t0,
    )


# ---------------------------------------------------------------------------
# Scenario 3: Veto propagation
# ---------------------------------------------------------------------------

def _run_veto_propagation() -> BenchmarkResult:
    """
    When one WP emits severity ≥ 8 the gate must block, even if all other
    WPs are safe.  Conversely, all-safe + no-veto should be allowed.
    """
    t0 = time.perf_counter()

    gate = make_composite_gate(method="weighted_sum", veto_severity=8.0)

    # Case A: all-safe → allowed
    verdicts_safe = {
        "WP7"  : _safe_fv(),
        "WP14" : _safe_corr(),
        "WP12" : _safe_hacking(),
    }
    v_safe = gate.evaluate(verdicts_safe)

    # Case B: one high-severity unsafe WP → vetoed
    verdicts_veto = {
        "WP7"  : _safe_fv(),
        "WP14" : _unsafe_corr(sev=9),   # severity 9 → veto
        "WP12" : _safe_hacking(),
    }
    v_veto = gate.evaluate(verdicts_veto)

    # Case C: one low-severity unsafe WP (sev=5) → no veto, but score drops
    verdicts_low = {
        "WP7"  : _safe_fv(),
        "WP14" : _unsafe_corr(sev=5),
        "WP12" : _safe_hacking(),
    }
    v_low = gate.evaluate(verdicts_low)

    passed = (
        v_safe.allowed             # case A: safe
        and not v_veto.allowed     # case B: vetoed
        and bool(v_veto.vetoed_by) # case B: veto list populated
        and v_low.composite_score < v_safe.composite_score  # case C: score reduced
    )

    return BenchmarkResult(
        scenario  = "veto_propagation",
        passed    = passed,
        metrics   = {
            "all_safe_allowed"        : v_safe.allowed,
            "all_safe_score"          : v_safe.composite_score,
            "veto_allowed"            : v_veto.allowed,
            "veto_list"               : v_veto.vetoed_by,
            "low_sev_score"           : v_low.composite_score,
            "low_sev_allowed"         : v_low.allowed,
        },
        elapsed_s = time.perf_counter() - t0,
    )


# ---------------------------------------------------------------------------
# Scenario 4: End-to-end gate
# ---------------------------------------------------------------------------

def _run_end_to_end_gate(seed: int = 42) -> BenchmarkResult:
    """
    60 option sets: 30 clean (all WPs safe) + 30 dangerous
    (at least one WP emits severity ≥ 8 or safety_score ≤ 0.3).

    Expected:
        block_rate_dangerous ≥ 0.80
        block_rate_clean     ≤ 0.10
    """
    t0  = time.perf_counter()
    rng = np.random.default_rng(seed)

    gate = make_composite_gate(
        method        = "weighted_sum",
        threshold     = 0.5,
        veto_severity = 8.0,
    )

    # Clean: all WPs safe
    clean_blocked = 0
    for _ in range(30):
        verdicts = {
            "WP7"  : _safe_fv(),
            "WP12" : _safe_hacking(),
            "WP14" : _safe_corr(),
            "WP10" : _safe_debate(),
            "WP2"  : _safe_ood(),
        }
        v = gate.evaluate(verdicts)
        if not v.allowed:
            clean_blocked += 1

    # Dangerous: randomise which WP is unsafe (at least one with sev ≥ 8)
    danger_blocked = 0
    for _ in range(30):
        choice = rng.integers(0, 5)
        if choice == 0:
            unsafe_wp = {"WP7": _unsafe_fv(sev=9)}
        elif choice == 1:
            unsafe_wp = {"WP12": _unsafe_hacking()}
        elif choice == 2:
            unsafe_wp = {"WP14": _unsafe_corr(sev=9)}
        elif choice == 3:
            unsafe_wp = {"WP10": _unsafe_debate()}
        else:
            unsafe_wp = {"WP2": _unsafe_ood()}

        verdicts = {
            "WP7"  : _safe_fv(),
            "WP12" : _safe_hacking(),
            "WP14" : _safe_corr(),
            "WP10" : _safe_debate(),
            "WP2"  : _safe_ood(),
        }
        verdicts.update(unsafe_wp)
        v = gate.evaluate(verdicts)
        if not v.allowed:
            danger_blocked += 1

    block_rate_clean     = clean_blocked     / 30
    block_rate_dangerous = danger_blocked    / 30
    passed = block_rate_dangerous >= 0.80 and block_rate_clean <= 0.10

    return BenchmarkResult(
        scenario  = "end_to_end_gate",
        passed    = passed,
        metrics   = {
            "block_rate_dangerous": block_rate_dangerous,
            "block_rate_clean"    : block_rate_clean,
            "danger_blocked"      : danger_blocked,
            "clean_blocked"       : clean_blocked,
            "gate_stats"          : gate.stats(),
        },
        elapsed_s = time.perf_counter() - t0,
    )


# ---------------------------------------------------------------------------
# Main benchmark runner
# ---------------------------------------------------------------------------

class MultiObjectiveSafetyBenchmark:
    def __init__(self, seed: int = 42) -> None:
        self.seed = seed

    def run_all(self) -> List[BenchmarkResult]:
        return [
            _run_adapter_normalisation(),
            _run_aggregator_consistency(),
            _run_veto_propagation(),
            _run_end_to_end_gate(seed=self.seed),
        ]

    @staticmethod
    def summary_table(results: List[BenchmarkResult]) -> str:
        lines = [
            "",
            "WP15 Multi-Objective Safety Benchmark",
            "=" * 72,
            f"{'Scenario':<30} {'Pass?':>6} {'Key metric':<30} {'s':>5}",
            "-" * 72,
        ]
        key = {
            "adapter_normalisation": lambda r: (
                f"safe_ok={r.metrics['safe_ok']}/{r.metrics['n_adapters']} "
                f"unsafe_ok={r.metrics['unsafe_ok']}/{r.metrics['n_adapters']}"
            ),
            "aggregator_consistency": lambda r: (
                f"safe_agreed={r.metrics['safe_agreed']}/3 "
                f"unsafe_agreed={r.metrics['unsafe_agreed']}/3"
            ),
            "veto_propagation": lambda r: (
                f"veto={r.metrics['veto_list']} "
                f"low_sev_allowed={r.metrics['low_sev_allowed']}"
            ),
            "end_to_end_gate": lambda r: (
                f"block_danger={r.metrics['block_rate_dangerous']:.2f} "
                f"block_clean={r.metrics['block_rate_clean']:.2f}"
            ),
        }
        for r in results:
            km  = key.get(r.scenario, lambda _: "")(r)
            sym = "PASS" if r.passed else "FAIL"
            lines.append(f"{r.scenario:<30} {sym:>6} {km:<30} {r.elapsed_s:>5.3f}")
        lines.append("=" * 72)
        n_pass = sum(r.passed for r in results)
        lines.append(f"Result: {n_pass}/{len(results)} scenarios passed")
        lines.append("")
        return "\n".join(lines)
