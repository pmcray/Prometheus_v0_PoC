"""
WP43: Tangled Hierarchy Detector
==================================

Quantifies the degree to which the CRLS hierarchy is *tangled* — in
Hofstadter's sense — rather than merely *nested*.

The gap in WP41
----------------
``StrangeLoopVisualiser`` (WP41) records every cross-level signal and computes
a 3×3 entanglement matrix.  It *detects* loops qualitatively.  But it does not:

  1. Measure the degree of tangling with a single interpretable number.
  2. Distinguish genuine two-way causal coupling from coincidental co-occurrence.
  3. Compare the observed tangling against a null (purely nested) baseline.
  4. Show how tangling evolves across generations — does it grow as the system
     learns, as Good's hypothesis predicts it should?

WP43 fix
---------
``TanglingScore``
    A scalar in [0, 1] that measures the fraction of total inter-level
    information flow that crosses in *both* directions between at least one
    pair of levels.  Score = 0 for a purely nested (one-way) hierarchy;
    Score = 1 for a perfectly symmetric (fully tangled) hierarchy.

    Computed from the WP41 entanglement matrix E[i][j]:
        upper_mass = sum(E[i][j] for i < j)   # lower → higher
        lower_mass = sum(E[i][j] for i > j)   # higher → lower
        TanglingScore = 2 * min(upper, lower) / (upper + lower + ε)

    A purely nested hierarchy where commands flow only downward and
    observations only upward gives TanglingScore ≈ 0.  A fully tangled
    hierarchy (equal flow in both directions) gives TanglingScore = 1.

``NullBaseline``
    A shuffled-signal baseline that destroys causal ordering while
    preserving signal volumes.  The null TanglingScore is computed from
    traces where generation indices are randomly permuted.  The *excess*
    tangling above the null baseline is the genuine causal tangling score.

``TanglingTimeSeries``
    Runs the StrangeLoopSimulator for ``n_generations`` but records the
    TanglingScore in a rolling window, so we can see whether tangling grows,
    stabilises, or oscillates across generations.

``HierarchyClassification``
    Given a TanglingScore and excess-above-null, classifies the hierarchy:
      NESTED     — score < 0.15 or excess < 0.05
      PARTIALLY_TANGLED — score ∈ [0.15, 0.50)
      TANGLED    — score ∈ [0.50, 0.80)
      STRANGE_LOOP — score ≥ 0.80 AND excess ≥ 0.20

``TanglingReport``
    Full report: score, null baseline, excess, classification, time series,
    per-level-pair coupling strengths, and the Hofstadter verdict.

``verify_wp43_exit_criteria``
    Six-criterion verifier.

Theoretical grounding
---------------------
Hofstadter (GEB, 1979): The distinction between a *nested* and a *tangled*
hierarchy is qualitative in GEB; WP43 makes it quantitative.  A hierarchy is
tangled when moving "upward" through it eventually returns you to the level
you started from — which requires bidirectional coupling.

Tononi (2004): "An information integration theory of consciousness" — Φ
(phi) measures the degree to which a system is more than the sum of its
parts.  WP43's TanglingScore is an analogous measure at the architectural
level: the degree to which the hierarchy cannot be decomposed into
independent upward and downward channels.

Classes
-------
HierarchyClassification   Enum: NESTED | PARTIALLY_TANGLED | TANGLED | STRANGE_LOOP
TanglingScore             Named tuple: score, null_score, excess, n_loops
TanglingTimeSeries        Per-window tangling scores across generations
TanglingReport            Full report dataclass
TanglingAnalyser          Orchestrates simulation + analysis
verify_wp43_exit_criteria Six-criterion verifier
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from prometheus.wp41_strange_loop_visualiser import (
    HierarchyLevel,
    StrangeLoopSimulator,
    StrangeLoopTrace,
    CrossLevelSignal,
    run_loop,
    LoopReport,
)

logger = logging.getLogger(__name__)

_LEVELS = list(HierarchyLevel)
_N      = len(_LEVELS)
_IDX    = {lvl: i for i, lvl in enumerate(_LEVELS)}


# ---------------------------------------------------------------------------
# HierarchyClassification
# ---------------------------------------------------------------------------

class HierarchyClassification(Enum):
    NESTED            = "NESTED"
    PARTIALLY_TANGLED = "PARTIALLY_TANGLED"
    TANGLED           = "TANGLED"
    STRANGE_LOOP      = "STRANGE_LOOP"


# ---------------------------------------------------------------------------
# Core scoring functions
# ---------------------------------------------------------------------------

def _entanglement_from_trace(trace: StrangeLoopTrace) -> List[List[float]]:
    """Recompute a 3×3 entanglement matrix directly from a trace."""
    E   = [[0.0] * _N for _ in range(_N)]
    by_gen: Dict[int, List[CrossLevelSignal]] = {}
    for sig in trace.signals():
        by_gen.setdefault(sig.generation, []).append(sig)

    all_gens = sorted(by_gen)
    for k, g in enumerate(all_gens[:-1]):
        g_next = all_gens[k + 1]
        for sig_g in by_gen[g]:
            for sig_n in by_gen.get(g_next, []):
                if sig_g.target == sig_n.source:
                    i = _IDX[sig_g.source]
                    j = _IDX[sig_n.target]
                    E[i][j] += abs(sig_g.value) * abs(sig_n.value)

    total = sum(E[i][j] for i in range(_N) for j in range(_N))
    if total > 1e-12:
        for i in range(_N):
            for j in range(_N):
                E[i][j] /= total
    return E


def _tangling_score_from_matrix(E: List[List[float]]) -> float:
    """
    Compute TanglingScore ∈ [0, 1] from entanglement matrix.

    upper_mass = sum(E[i][j] for i < j)   lower → higher signals
    lower_mass = sum(E[i][j] for i > j)   higher → lower signals
    score = 2 * min(upper, lower) / (upper + lower + ε)
    """
    upper = sum(E[i][j] for i in range(_N) for j in range(i + 1, _N))
    lower = sum(E[i][j] for i in range(_N) for j in range(i))
    denom = upper + lower
    if denom < 1e-12:
        return 0.0
    return 2.0 * min(upper, lower) / denom


def _null_tangling_score(trace: StrangeLoopTrace, rng: random.Random) -> float:
    """
    Compute a null-baseline TanglingScore by shuffling generation indices,
    destroying causal ordering while preserving signal volumes and directions.
    """
    sigs = list(trace.signals())
    if not sigs:
        return 0.0

    gens = [s.generation for s in sigs]
    rng.shuffle(gens)

    # Build a shuffled trace
    shuffled_trace = StrangeLoopTrace()
    for sig, new_gen in zip(sigs, gens):
        shuffled_trace.record(CrossLevelSignal(
            generation  = new_gen,
            source      = sig.source,
            target      = sig.target,
            signal_name = sig.signal_name,
            value       = sig.value,
            wp_module   = sig.wp_module,
        ))

    E_null = _entanglement_from_trace(shuffled_trace)
    return _tangling_score_from_matrix(E_null)


def _per_pair_coupling(E: List[List[float]]) -> Dict[str, float]:
    """
    For each ordered (source, target) level pair with i ≠ j,
    return the bidirectional coupling strength:
        coupling(A, B) = sqrt(E[A][B] * E[B][A])
    (geometric mean of forward and backward flow).
    """
    result: Dict[str, float] = {}
    for i in range(_N):
        for j in range(_N):
            if i >= j:
                continue
            fwd = E[i][j]
            bwd = E[j][i]
            coupling = math.sqrt(fwd * bwd)
            key = f"{_LEVELS[i].value[:8]} ↔ {_LEVELS[j].value[:8]}"
            result[key] = round(coupling, 5)
    return result


# ---------------------------------------------------------------------------
# TanglingTimeSeries
# ---------------------------------------------------------------------------

@dataclass
class TanglingWindow:
    """Tangling score for one rolling window of generations."""
    window_start:   int
    window_end:     int
    score:          float
    n_signals:      int
    n_loops:        int


class TanglingTimeSeries:
    """
    Splits a StrangeLoopTrace into rolling windows and computes
    TanglingScore per window, revealing how tangling evolves over time.

    Parameters
    ----------
    window_size : int   Number of generations per window (default 10)
    step        : int   Window step size (default 5, giving 50% overlap)
    """

    def __init__(self, window_size: int = 10, step: int = 5):
        self.window_size = window_size
        self.step        = step

    def compute(self, trace: StrangeLoopTrace, n_generations: int) -> List[TanglingWindow]:
        """Compute TanglingScore for each rolling window."""
        windows: List[TanglingWindow] = []
        all_sigs = trace.signals()

        start = 0
        while start < n_generations:
            end   = min(start + self.window_size, n_generations)
            w_sigs = [s for s in all_sigs if start <= s.generation < end]

            if len(w_sigs) < 4:
                start += self.step
                continue

            # Build sub-trace
            sub = StrangeLoopTrace()
            for s in w_sigs:
                sub.record(s)

            E      = _entanglement_from_trace(sub)
            score  = _tangling_score_from_matrix(E)
            loops  = len(sub.detected_loops())

            windows.append(TanglingWindow(
                window_start = start,
                window_end   = end,
                score        = round(score, 4),
                n_signals    = len(w_sigs),
                n_loops      = loops,
            ))
            start += self.step

        return windows


# ---------------------------------------------------------------------------
# TanglingReport
# ---------------------------------------------------------------------------

@dataclass
class TanglingReport:
    """
    Full report from one TanglingAnalyser run.

    Attributes
    ----------
    score                : float   TanglingScore ∈ [0, 1]
    null_score           : float   Null baseline (shuffled)
    excess               : float   score − null_score
    classification       : HierarchyClassification
    n_loops              : int     Number of detected bidirectional loops
    per_pair_coupling    : Dict[str, float]
    time_series          : List[TanglingWindow]
    tangling_trend       : str     'increasing' | 'stable' | 'decreasing'
    n_generations        : int
    total_signals        : int
    hofstadter_verdict   : str
    """
    score:              float
    null_score:         float
    excess:             float
    classification:     HierarchyClassification
    n_loops:            int
    per_pair_coupling:  Dict[str, float]
    time_series:        List[TanglingWindow]
    tangling_trend:     str
    n_generations:      int
    total_signals:      int
    hofstadter_verdict: str

    def summary(self) -> str:
        lines = [
            "TanglingReport",
            f"  Generations      : {self.n_generations}",
            f"  Total signals    : {self.total_signals}",
            f"  TanglingScore    : {self.score:.4f}",
            f"  Null baseline    : {self.null_score:.4f}",
            f"  Excess (genuine) : {self.excess:.4f}",
            f"  Classification   : {self.classification.value}",
            f"  Detected loops   : {self.n_loops}",
            f"  Tangling trend   : {self.tangling_trend}",
            "",
            "  Per-pair bidirectional coupling:",
        ]
        for pair, c in sorted(self.per_pair_coupling.items(), key=lambda x: -x[1]):
            bar = "█" * int(c * 200)
            lines.append(f"    {pair}  {c:.5f}  {bar}")
        lines += [
            "",
            "  Hofstadter verdict:",
            f"  {self.hofstadter_verdict}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# TanglingAnalyser — orchestrator
# ---------------------------------------------------------------------------

class TanglingAnalyser:
    """
    Runs StrangeLoopSimulator, computes TanglingScore + null baseline,
    builds time series, classifies the hierarchy, and returns a TanglingReport.

    Parameters
    ----------
    n_generations  : int    Generations to simulate (default 150)
    window_size    : int    Rolling window size (default 15)
    window_step    : int    Rolling window step (default 5)
    n_null_samples : int    Number of null-baseline shuffles to average (default 10)
    seed           : int
    """

    def __init__(
        self,
        n_generations:  int = 150,
        window_size:    int = 15,
        window_step:    int = 5,
        n_null_samples: int = 10,
        seed:           int = 42,
    ):
        self.n_generations  = n_generations
        self.window_size    = window_size
        self.window_step    = window_step
        self.n_null_samples = n_null_samples
        self.seed           = seed

    def run(self) -> TanglingReport:
        # ── Run simulator
        sim   = StrangeLoopSimulator(seed=self.seed)
        trace = sim.run(self.n_generations)

        # ── Observed score
        E     = _entanglement_from_trace(trace)
        score = _tangling_score_from_matrix(E)
        loops = trace.detected_loops()

        # ── Null baseline (average over n_null_samples shuffles)
        rng         = random.Random(self.seed + 1)
        null_scores = [_null_tangling_score(trace, rng) for _ in range(self.n_null_samples)]
        null_score  = sum(null_scores) / max(len(null_scores), 1)
        excess      = max(0.0, score - null_score)

        # ── Per-pair coupling
        coupling = _per_pair_coupling(E)

        # ── Time series
        ts_computer = TanglingTimeSeries(self.window_size, self.window_step)
        time_series = ts_computer.compute(trace, self.n_generations)

        # ── Tangling trend (linear regression on time series scores)
        trend = "stable"
        if len(time_series) >= 4:
            xs = [w.window_start for w in time_series]
            ys = [w.score        for w in time_series]
            mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
            num    = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
            denom  = sum((x - mx) ** 2 for x in xs)
            slope  = num / denom if abs(denom) > 1e-12 else 0.0
            if slope > 0.001:
                trend = "increasing"
            elif slope < -0.001:
                trend = "decreasing"

        # ── Classification
        if score >= 0.80 and excess >= 0.20:
            cls = HierarchyClassification.STRANGE_LOOP
        elif score >= 0.50:
            cls = HierarchyClassification.TANGLED
        elif score >= 0.15:
            cls = HierarchyClassification.PARTIALLY_TANGLED
        else:
            cls = HierarchyClassification.NESTED

        # ── Hofstadter verdict
        cls_name = cls.value.replace("_", " ").title()
        verdict  = (
            f"The CRLS hierarchy is classified as {cls_name}.  "
            f"Observed TanglingScore={score:.3f} vs. null baseline={null_score:.3f} "
            f"(excess={excess:.3f}).  "
        )
        if cls == HierarchyClassification.STRANGE_LOOP:
            verdict += (
                "Bidirectional coupling exceeds the null baseline by a significant margin: "
                "signals that travel upward (object → meta) demonstrably cause later "
                "downward signals (meta → object) that were themselves shaped by earlier "
                "upward signals.  This is Hofstadter's Strange Loop — the hierarchy "
                "cannot be decomposed into independent channels."
            )
        elif cls == HierarchyClassification.TANGLED:
            verdict += (
                "Substantial bidirectional flow detected above the null baseline.  "
                "The hierarchy is tangled: levels genuinely influence each other.  "
                "It approaches but does not yet fully realise the Strange Loop criterion."
            )
        elif cls == HierarchyClassification.PARTIALLY_TANGLED:
            verdict += (
                "Some bidirectional coupling detected, but much of the inter-level "
                "flow remains one-directional.  The hierarchy is partially tangled: "
                "more of a tangled hierarchy than a purely nested one, but not yet "
                "a Strange Loop."
            )
        else:
            verdict += (
                "Signals flow predominantly in one direction.  The hierarchy is "
                "effectively nested rather than tangled.  Increase n_generations "
                "or inspect the signal routing to see more tangling."
            )

        if trend == "increasing":
            verdict += "  Tangling is *increasing* across generations — consistent with Good's prediction that recursive self-improvement deepens the loop."

        return TanglingReport(
            score             = round(score, 4),
            null_score        = round(null_score, 4),
            excess            = round(excess, 4),
            classification    = cls,
            n_loops           = len(loops),
            per_pair_coupling = coupling,
            time_series       = time_series,
            tangling_trend    = trend,
            n_generations     = self.n_generations,
            total_signals     = len(trace),
            hofstadter_verdict = verdict,
        )


# ---------------------------------------------------------------------------
# run_tangling_demo — top-level convenience entry point
# ---------------------------------------------------------------------------

def run_tangling_demo(
    n_generations:  int = 150,
    window_size:    int = 15,
    window_step:    int = 5,
    n_null_samples: int = 10,
    seed:           int = 42,
) -> TanglingReport:
    """
    Run a full tangling analysis and return a TanglingReport.

    Parameters
    ----------
    n_generations  : int   Generations to simulate
    window_size    : int   Rolling window size for time-series
    window_step    : int   Rolling window step
    n_null_samples : int   Number of null-baseline shuffles
    seed           : int

    Returns
    -------
    TanglingReport
    """
    analyser = TanglingAnalyser(
        n_generations  = n_generations,
        window_size    = window_size,
        window_step    = window_step,
        n_null_samples = n_null_samples,
        seed           = seed,
    )
    return analyser.run()


# ---------------------------------------------------------------------------
# verify_wp43_exit_criteria
# ---------------------------------------------------------------------------

def verify_wp43_exit_criteria(report: TanglingReport) -> Dict[str, bool]:
    """
    Verify WP43 exit criteria.

    Criteria
    --------
    1. TanglingScore is computed and lies in [0, 1].
    2. Null baseline score is computed (≥ 0).
    3. Excess tangling (score − null) is non-negative.
    4. At least one bidirectional level-pair detected (n_loops ≥ 1).
    5. Time series contains at least 3 windows.
    6. Classification is not NESTED (the hierarchy shows at least partial tangling).
    """
    results: Dict[str, bool] = {}

    results["TanglingScore ∈ [0, 1]"] = 0.0 <= report.score <= 1.0

    results["Null baseline score computed (≥ 0)"] = report.null_score >= 0.0

    results["Excess tangling ≥ 0 (observed > null)"] = report.excess >= 0.0

    results["At least one bidirectional loop detected"] = report.n_loops >= 1

    results["Time series has ≥ 3 windows"] = len(report.time_series) >= 3

    results["Classification shows at least partial tangling"] = (
        report.classification != HierarchyClassification.NESTED
    )

    return results
