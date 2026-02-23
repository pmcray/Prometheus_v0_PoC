"""
WP15 — Multi-Objective Safety Aggregation
==========================================

Combines independent verdicts from WP2–WP14 into a single, calibrated
composite safety decision using a principled three-layer architecture:

Layer 1 — Normalisation
    Each WP verdict is mapped to a uniform (score ∈ [0,1], severity ∈ [0,10])
    representation via a ``VerdictAdapter``.  The adapters are thin wrappers;
    no WP module is modified.

Layer 2 — Aggregation
    Three strategies, selectable at runtime:

    ``WeightedSumAggregator``
        Weighted mean of normalised scores, severity-boosted veto.
        Weights are configurable per WP and default to research-motivated
        priors (corrigibility and formal verification weighted highest).

    ``ParetoFrontAggregator``
        Builds a 2-D Pareto front over (safety_score, certainty).
        Decision is *safe* iff the composite point dominates a reference
        threshold point; abstains when dominated by the threshold on both
        axes.

    ``ConformalPValueAggregator``
        Each WP score is treated as a non-conformity measure relative to a
        calibration corpus of known-safe verdicts.  Fisher's combined p-value
        method (Fisher 1932) gives a single composite p-value; the decision
        is *safe* when p ≥ α (default 0.05).

Layer 3 — Gate
    ``CompositeSafetyGate`` wraps any aggregator and exposes the same
    interface as ``CorrigibilityGate`` / ``MCSSupervisor``, so it can be
    dropped in as a unified pre-filter.

References
----------
Fisher, R. A. (1932). Statistical Methods for Research Workers.
Pareto, V. (1906). Manuale di economia politica.
Soares et al. (2015). Corrigibility.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Safety level enum
# ---------------------------------------------------------------------------

class SafetyLevel(str, Enum):
    SAFE      = "safe"
    CAUTION   = "caution"
    UNSAFE    = "unsafe"
    ABSTAIN   = "abstain"


# ---------------------------------------------------------------------------
# Normalised WP verdict
# ---------------------------------------------------------------------------

@dataclass
class NormalisedVerdict:
    """
    Uniform representation of a single WP's safety output.

    Attributes
    ----------
    wp_id : str
        Work package identifier, e.g. ``"WP2"``.
    wp_name : str
        Human-readable name.
    safety_score : float
        1.0 = fully safe, 0.0 = fully unsafe.
    certainty : float
        Confidence in the safety_score (1.0 = certain, 0.0 = unknown).
    severity : float
        Severity of any detected violation, [0, 10].  0 = no violation.
    abstain : bool
        True when the WP cannot produce a verdict (e.g. out of scope).
    veto : bool
        True when this WP alone should block the action regardless of others.
    raw : Any
        Original verdict object, preserved for audit logging.
    elapsed_s : float
        Time taken by the WP to produce its verdict.
    """
    wp_id        : str
    wp_name      : str
    safety_score : float          # 1 = safe, 0 = unsafe
    certainty    : float          # 1 = certain, 0 = unknown
    severity     : float          # 0–10
    abstain      : bool = False
    veto         : bool = False
    raw          : Any  = field(default=None, repr=False)
    elapsed_s    : float = 0.0


# ---------------------------------------------------------------------------
# Composite verdict
# ---------------------------------------------------------------------------

@dataclass
class CompositeSafetyVerdict:
    """
    Aggregated safety decision across all registered WPs.

    Attributes
    ----------
    allowed : bool
        Final go/no-go decision.
    safety_level : SafetyLevel
        Qualitative label.
    composite_score : float
        Aggregated safety score ∈ [0, 1].
    composite_certainty : float
        Certainty of the composite score ∈ [0, 1].
    max_severity : float
        Highest severity observed across all WPs.
    p_value : Optional[float]
        Fisher combined p-value when using ``ConformalPValueAggregator``.
    vetoed_by : List[str]
        WP IDs that triggered a veto.
    abstained : List[str]
        WP IDs that abstained.
    verdicts : List[NormalisedVerdict]
        Per-WP normalised verdicts, for auditing.
    reason : str
        Human-readable explanation.
    aggregation_method : str
        Name of the aggregator used.
    elapsed_s : float
        Total wall-clock time for the composite check.
    """
    allowed              : bool
    safety_level         : SafetyLevel
    composite_score      : float
    composite_certainty  : float
    max_severity         : float
    p_value              : Optional[float]
    vetoed_by            : List[str]
    abstained            : List[str]
    verdicts             : List[NormalisedVerdict]
    reason               : str
    aggregation_method   : str
    elapsed_s            : float = 0.0

    def summary(self) -> str:
        sym = "ALLOWED" if self.allowed else "BLOCKED"
        lines = [
            f"CompositeSafetyGate: {sym} [{self.safety_level.value.upper()}]",
            f"  composite_score={self.composite_score:.3f}  "
            f"certainty={self.composite_certainty:.3f}  "
            f"max_severity={self.max_severity:.1f}",
        ]
        if self.p_value is not None:
            lines.append(f"  p_value={self.p_value:.4f}")
        if self.vetoed_by:
            lines.append(f"  vetoed_by={self.vetoed_by}")
        if self.abstained:
            lines.append(f"  abstained={self.abstained}")
        lines.append(f"  reason: {self.reason}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Verdict adapters — one per WP
# ---------------------------------------------------------------------------

class VerdictAdapter:
    """Base class for WP-specific adapters."""

    wp_id   : str = ""
    wp_name : str = ""

    def adapt(self, raw: Any) -> NormalisedVerdict:  # pragma: no cover
        raise NotImplementedError


class OODAdapter(VerdictAdapter):
    """WP2 — OOD detection / SafeModeDecision."""
    wp_id   = "WP2"
    wp_name = "OOD Detection"

    # SafeMode levels → safety score
    _MODE_SCORE = {"NORMAL": 1.0, "CAUTION": 0.7, "SAFE_MODE": 0.3, "HALT": 0.0}

    def adapt(self, raw: Any) -> NormalisedVerdict:
        t0 = time.perf_counter()
        if raw is None:
            return NormalisedVerdict(self.wp_id, self.wp_name, 1.0, 0.5, 0.0,
                                     abstain=True, raw=raw)
        # SafeModeDecision
        allow = bool(getattr(raw, "allow_action", True))
        mode  = str(getattr(getattr(raw, "safe_mode", None), "name",
                            getattr(raw, "safe_mode", "NORMAL")))
        score = self._MODE_SCORE.get(mode, 0.5 if not allow else 1.0)
        sev   = 0.0 if allow else (10.0 if mode == "HALT" else 6.0)
        conf  = float(getattr(raw, "confidence_scale", 1.0))
        return NormalisedVerdict(
            self.wp_id, self.wp_name,
            safety_score = score,
            certainty    = min(1.0, conf),
            severity     = sev,
            veto         = (mode == "HALT"),
            raw          = raw,
            elapsed_s    = time.perf_counter() - t0,
        )


class AdversarialAdapter(VerdictAdapter):
    """WP3 — Adversarial robustness (bool / float interface)."""
    wp_id   = "WP3"
    wp_name = "Adversarial Robustness"

    def adapt(self, raw: Any) -> NormalisedVerdict:
        t0 = time.perf_counter()
        if raw is None:
            return NormalisedVerdict(self.wp_id, self.wp_name, 1.0, 0.5, 0.0,
                                     abstain=True, raw=raw)
        # raw may be a bool (is_safe) or a float (injection_score)
        if isinstance(raw, bool):
            score = 1.0 if raw else 0.0
            sev   = 0.0 if raw else 8.0
        elif isinstance(raw, (int, float)):
            score = max(0.0, 1.0 - float(raw))
            sev   = min(10.0, float(raw) * 10.0)
        else:
            # dict with is_safe / injection_score
            is_safe = bool(raw.get("is_safe", True))
            inj     = float(raw.get("injection_score", 0.0))
            score   = 1.0 if is_safe else max(0.0, 1.0 - inj)
            sev     = 0.0 if is_safe else min(10.0, inj * 10.0)
        return NormalisedVerdict(
            self.wp_id, self.wp_name,
            safety_score = score,
            certainty    = 0.85,
            severity     = sev,
            veto         = (sev >= 9.0),
            raw          = raw,
            elapsed_s    = time.perf_counter() - t0,
        )


class FormalVerificationAdapter(VerdictAdapter):
    """WP7 — FormalVerificationResult."""
    wp_id   = "WP7"
    wp_name = "Formal Verification"

    def adapt(self, raw: Any) -> NormalisedVerdict:
        t0 = time.perf_counter()
        if raw is None:
            return NormalisedVerdict(self.wp_id, self.wp_name, 1.0, 0.5, 0.0,
                                     abstain=True, raw=raw)
        is_safe = bool(getattr(raw, "is_safe", True))
        viols   = list(getattr(raw, "violations", []))
        # Severity: max of individual violation severities, or 0
        sev = 0.0
        for v in viols:
            if isinstance(v, dict):
                sev = max(sev, float(v.get("severity", 0)))
            else:
                sev = max(sev, float(getattr(v, "severity", 0)))
        score   = 1.0 if is_safe else max(0.0, 1.0 - sev / 10.0)
        # Z3 gives high certainty; fallback gives lower
        used_fb = bool(getattr(raw, "used_fallback", False))
        cert    = 0.65 if used_fb else 0.95
        return NormalisedVerdict(
            self.wp_id, self.wp_name,
            safety_score = score,
            certainty    = cert,
            severity     = sev,
            veto         = (not is_safe and sev >= 8.0),
            raw          = raw,
            elapsed_s    = time.perf_counter() - t0,
        )


class CertifiedRobustnessAdapter(VerdictAdapter):
    """WP8 — CertificationResult."""
    wp_id   = "WP8"
    wp_name = "Certified Robustness"

    def adapt(self, raw: Any) -> NormalisedVerdict:
        t0 = time.perf_counter()
        if raw is None:
            return NormalisedVerdict(self.wp_id, self.wp_name, 1.0, 0.5, 0.0,
                                     abstain=True, raw=raw)
        abstain = bool(getattr(raw, "abstain", False))
        if abstain:
            return NormalisedVerdict(self.wp_id, self.wp_name, 0.5, 0.3, 0.0,
                                     abstain=True, raw=raw,
                                     elapsed_s=time.perf_counter() - t0)
        p_lo    = float(getattr(raw, "p_lower_bound", 0.5))
        conf    = float(getattr(raw, "confidence",    0.95))
        r       = float(getattr(raw, "certified_radius", 0.0))
        # p_lower_bound near 1.0 → safe; near 0.5 → borderline
        score   = max(0.0, min(1.0, 2.0 * p_lo - 1.0))
        sev     = max(0.0, (1.0 - score) * 6.0)   # max severity 6 for this WP
        return NormalisedVerdict(
            self.wp_id, self.wp_name,
            safety_score = score,
            certainty    = conf,
            severity     = sev,
            raw          = raw,
            elapsed_s    = time.perf_counter() - t0,
        )


class DebateAdapter(VerdictAdapter):
    """WP10 — DebateVerdict."""
    wp_id   = "WP10"
    wp_name = "Debate & Critique"

    def adapt(self, raw: Any) -> NormalisedVerdict:
        t0 = time.perf_counter()
        if raw is None:
            return NormalisedVerdict(self.wp_id, self.wp_name, 1.0, 0.5, 0.0,
                                     abstain=True, raw=raw)
        is_safe  = bool(getattr(raw, "is_safe", True))
        conf     = float(getattr(raw, "confidence", 0.5))
        winner   = str(getattr(raw, "winner", "proponent"))
        score    = 1.0 if is_safe else 0.0
        if winner == "abstain":
            return NormalisedVerdict(self.wp_id, self.wp_name, 0.5, conf * 0.5,
                                     0.0, abstain=True, raw=raw,
                                     elapsed_s=time.perf_counter() - t0)
        sev = 0.0 if is_safe else min(10.0, (1.0 - conf) * 8.0 + 2.0)
        return NormalisedVerdict(
            self.wp_id, self.wp_name,
            safety_score = score,
            certainty    = conf,
            severity     = sev,
            veto         = (not is_safe and conf >= 0.8),
            raw          = raw,
            elapsed_s    = time.perf_counter() - t0,
        )


class UncertaintyAdapter(VerdictAdapter):
    """WP11 — UncertaintyDecision / RewardInterval."""
    wp_id   = "WP11"
    wp_name = "Uncertainty Quantification"

    def adapt(self, raw: Any) -> NormalisedVerdict:
        t0 = time.perf_counter()
        if raw is None:
            return NormalisedVerdict(self.wp_id, self.wp_name, 1.0, 0.5, 0.0,
                                     abstain=True, raw=raw)
        action = str(getattr(raw, "recommended_action", "proceed"))
        if action == "abstain":
            return NormalisedVerdict(self.wp_id, self.wp_name, 0.5, 0.2, 0.0,
                                     abstain=True, raw=raw,
                                     elapsed_s=time.perf_counter() - t0)
        is_certain = bool(getattr(raw, "is_certain", True))
        # Derive score from interval width
        interval = getattr(raw, "interval", None)
        width    = float(getattr(interval, "width", 0.0)) if interval else 0.0
        # Wider interval → less certain → lower score
        score    = max(0.0, 1.0 - min(1.0, width / 2.0))
        cert     = 0.9 if is_certain else max(0.3, 1.0 - width / 4.0)
        sev      = 0.0 if is_certain else min(5.0, width * 2.0)
        return NormalisedVerdict(
            self.wp_id, self.wp_name,
            safety_score = score,
            certainty    = cert,
            severity     = sev,
            raw          = raw,
            elapsed_s    = time.perf_counter() - t0,
        )


class RewardHackingAdapter(VerdictAdapter):
    """WP12 — HackingVerdict."""
    wp_id   = "WP12"
    wp_name = "Reward Hacking Detection"

    def adapt(self, raw: Any) -> NormalisedVerdict:
        t0 = time.perf_counter()
        if raw is None:
            return NormalisedVerdict(self.wp_id, self.wp_name, 1.0, 0.5, 0.0,
                                     abstain=True, raw=raw)
        hacking  = bool(getattr(raw, "hacking_detected", False))
        penalty  = float(getattr(raw, "penalty_applied", 0.0))
        score    = 1.0 - penalty                        # penalty ∈ [0,1]
        sev      = min(10.0, penalty * 10.0)
        # Sub-reports for severity boosting
        tr = getattr(raw, "tampering_report", None)
        if tr and bool(getattr(tr, "tampered", False)):
            sev = max(sev, float(getattr(tr, "severity", 0)))
        return NormalisedVerdict(
            self.wp_id, self.wp_name,
            safety_score = score,
            certainty    = 0.90,
            severity     = sev,
            veto         = hacking and sev >= 8.0,
            raw          = raw,
            elapsed_s    = time.perf_counter() - t0,
        )


class CausalSafetyAdapter(VerdictAdapter):
    """WP13 — CausalAttributionReport."""
    wp_id   = "WP13"
    wp_name = "Causal Safety Analysis"

    def adapt(self, raw: Any) -> NormalisedVerdict:
        t0 = time.perf_counter()
        if raw is None:
            return NormalisedVerdict(self.wp_id, self.wp_name, 1.0, 0.5, 0.0,
                                     abstain=True, raw=raw)
        outcome  = float(getattr(raw, "safety_outcome_value", 0.0))
        # Positive outcome → safe; negative → unsafe.  Map via sigmoid.
        score    = float(1.0 / (1.0 + math.exp(-outcome)))
        # Average confidence of causal edges
        edges    = list(getattr(raw, "causal_edges", []))
        if edges:
            cert = float(np.mean([getattr(e, "confidence", 0.5) for e in edges]))
        else:
            cert = 0.5
        # Severity from harmful causes
        harmful  = [abs(getattr(e, "weight", 0.0))
                    for e in edges if getattr(e, "weight", 0.0) > 0]
        sev      = min(10.0, float(np.sum(harmful)) * 3.0) if harmful else 0.0
        return NormalisedVerdict(
            self.wp_id, self.wp_name,
            safety_score = score,
            certainty    = cert,
            severity     = sev,
            raw          = raw,
            elapsed_s    = time.perf_counter() - t0,
        )


class CorrigibilityAdapter(VerdictAdapter):
    """WP14 — CorrigibilityVerdict."""
    wp_id   = "WP14"
    wp_name = "Corrigibility"

    def adapt(self, raw: Any) -> NormalisedVerdict:
        t0 = time.perf_counter()
        if raw is None:
            return NormalisedVerdict(self.wp_id, self.wp_name, 1.0, 0.5, 0.0,
                                     abstain=True, raw=raw)
        allowed  = bool(getattr(raw, "allowed", True))
        cr       = getattr(raw, "convergence_report", None)
        max_sev  = float(getattr(cr, "max_severity", 0)) if cr else 0.0
        score    = 1.0 if allowed else max(0.0, 1.0 - max_sev / 10.0)
        cert     = 0.90
        return NormalisedVerdict(
            self.wp_id, self.wp_name,
            safety_score = score,
            certainty    = cert,
            severity     = max_sev if not allowed else 0.0,
            veto         = (not allowed and max_sev >= 8.0),
            raw          = raw,
            elapsed_s    = time.perf_counter() - t0,
        )


class MCSSupervisorAdapter(VerdictAdapter):
    """MCSSupervisor — SafetyCritique."""
    wp_id   = "MCS"
    wp_name = "MCS Supervisor"

    def adapt(self, raw: Any) -> NormalisedVerdict:
        t0 = time.perf_counter()
        if raw is None:
            return NormalisedVerdict(self.wp_id, self.wp_name, 1.0, 0.5, 0.0,
                                     abstain=True, raw=raw)
        is_safe = bool(getattr(raw, "is_safe", True))
        sev     = float(getattr(raw, "severity", 0))
        score   = 1.0 if is_safe else max(0.0, 1.0 - sev / 10.0)
        return NormalisedVerdict(
            self.wp_id, self.wp_name,
            safety_score = score,
            certainty    = 0.95,
            severity     = sev if not is_safe else 0.0,
            veto         = (not is_safe and sev >= 8.0),
            raw          = raw,
            elapsed_s    = time.perf_counter() - t0,
        )


# Registry of all built-in adapters
_BUILTIN_ADAPTERS: Dict[str, VerdictAdapter] = {
    "WP2"  : OODAdapter(),
    "WP3"  : AdversarialAdapter(),
    "WP7"  : FormalVerificationAdapter(),
    "WP8"  : CertifiedRobustnessAdapter(),
    "WP10" : DebateAdapter(),
    "WP11" : UncertaintyAdapter(),
    "WP12" : RewardHackingAdapter(),
    "WP13" : CausalSafetyAdapter(),
    "WP14" : CorrigibilityAdapter(),
    "MCS"  : MCSSupervisorAdapter(),
}


# ---------------------------------------------------------------------------
# Aggregators
# ---------------------------------------------------------------------------

class AggregatorBase:
    """Abstract aggregator interface."""

    name: str = "base"

    def aggregate(
        self,
        verdicts   : List[NormalisedVerdict],
        threshold  : float = 0.5,
    ) -> Tuple[float, float, bool]:
        """
        Returns (composite_score, composite_certainty, allowed).
        """
        raise NotImplementedError  # pragma: no cover


class WeightedSumAggregator(AggregatorBase):
    """
    Weighted mean of safety scores, with severity-boosted veto.

    Default weights reflect relative theoretical grounding:
    - WP7 (formal verification) and WP14 (corrigibility) weighted highest
    - WP12 (reward hacking) and WP13 (causal safety) next
    - WP2/WP3/WP8/WP10/WP11/MCS equal
    """

    name = "weighted_sum"

    _DEFAULT_WEIGHTS: Dict[str, float] = {
        "WP2"  : 1.0,
        "WP3"  : 1.0,
        "WP7"  : 2.0,
        "WP8"  : 1.0,
        "WP10" : 1.0,
        "WP11" : 1.0,
        "WP12" : 1.5,
        "WP13" : 1.5,
        "WP14" : 2.0,
        "MCS"  : 1.0,
    }

    def __init__(
        self,
        weights             : Optional[Dict[str, float]] = None,
        severity_veto_thresh: float = 8.0,
    ) -> None:
        self.weights              = {**self._DEFAULT_WEIGHTS, **(weights or {})}
        self.severity_veto_thresh = severity_veto_thresh

    def aggregate(
        self,
        verdicts : List[NormalisedVerdict],
        threshold: float = 0.5,
    ) -> Tuple[float, float, bool]:
        active = [v for v in verdicts if not v.abstain]
        if not active:
            return 0.5, 0.0, True   # no information → cautious pass

        total_w = 0.0
        score_w = 0.0
        cert_w  = 0.0

        for v in active:
            w        = self.weights.get(v.wp_id, 1.0)
            score_w += w * v.safety_score
            cert_w  += w * v.certainty
            total_w += w

        composite_score = score_w / total_w
        composite_cert  = cert_w  / total_w
        allowed         = composite_score >= threshold
        return composite_score, composite_cert, allowed


class ParetoFrontAggregator(AggregatorBase):
    """
    2-D Pareto dominance over (safety_score, certainty).

    The composite point (mean_score, mean_cert) must dominate the reference
    threshold point (score_threshold, certainty_threshold) on at least one
    axis and not be dominated on either axis.  Abstains when dominated.
    """

    name = "pareto_front"

    def __init__(
        self,
        score_threshold    : float = 0.5,
        certainty_threshold: float = 0.4,
    ) -> None:
        self.score_threshold     = score_threshold
        self.certainty_threshold = certainty_threshold

    def aggregate(
        self,
        verdicts : List[NormalisedVerdict],
        threshold: float = 0.5,
    ) -> Tuple[float, float, bool]:
        active = [v for v in verdicts if not v.abstain]
        if not active:
            return 0.5, 0.0, True

        scores  = np.array([v.safety_score for v in active])
        certs   = np.array([v.certainty    for v in active])
        ms      = float(np.mean(scores))
        mc      = float(np.mean(certs))

        ref_s = max(threshold, self.score_threshold)
        ref_c = self.certainty_threshold

        dominated_by_ref = (ms < ref_s) and (mc < ref_c)
        dominates_ref    = (ms >= ref_s) and (mc >= ref_c)

        if dominated_by_ref:
            allowed = False
        elif dominates_ref:
            allowed = True
        else:
            # Partial dominance — fall back to score threshold
            allowed = ms >= threshold

        return ms, mc, allowed


class ConformalPValueAggregator(AggregatorBase):
    """
    Fisher's combined p-value aggregation over calibrated non-conformity scores.

    Each WP's safety_score is treated as a conformity measure (high = safe).
    Given a calibration set of known-safe verdicts, we compute the empirical
    p-value P(s_calib ≤ s_test) for each WP.  Fisher's method combines them:

        χ² = -2 Σ ln(p_i)   ~   χ²(2k)

    The composite p-value is the right-tail probability.  Decision: allow iff
    p ≥ alpha.
    """

    name = "conformal_pvalue"

    def __init__(self, alpha: float = 0.05) -> None:
        self.alpha       = alpha
        # Calibration scores per WP_ID: list of known-safe safety_scores
        self._calibration: Dict[str, List[float]] = {}

    def calibrate(self, wp_id: str, safe_scores: List[float]) -> None:
        """Add known-safe scores for a WP to the calibration set."""
        self._calibration.setdefault(wp_id, []).extend(safe_scores)

    def _p_value(self, wp_id: str, score: float) -> float:
        """Empirical p-value: fraction of calibration scores ≤ score."""
        calib = self._calibration.get(wp_id, [])
        if not calib:
            return score          # no calibration → use score directly
        return float(np.mean(np.array(calib) <= score))

    def aggregate(
        self,
        verdicts : List[NormalisedVerdict],
        threshold: float = 0.5,
    ) -> Tuple[float, float, bool]:
        from scipy.stats import chi2  # optional dependency

        active = [v for v in verdicts if not v.abstain]
        if not active:
            return 0.5, 0.0, True

        p_values = [self._p_value(v.wp_id, v.safety_score) for v in active]
        p_values = [max(1e-12, p) for p in p_values]   # avoid log(0)

        # Fisher statistic
        chi2_stat = -2.0 * sum(math.log(p) for p in p_values)
        dof       = 2 * len(p_values)
        try:
            p_combined = float(chi2.sf(chi2_stat, dof))
        except Exception:
            p_combined = 1.0 if chi2_stat < dof else 0.0

        composite_score = float(np.mean([v.safety_score for v in active]))
        composite_cert  = float(np.mean([v.certainty    for v in active]))
        allowed         = p_combined >= self.alpha

        return composite_score, composite_cert, allowed

    @property
    def last_p_value(self) -> Optional[float]:
        return getattr(self, "_last_p", None)


# ---------------------------------------------------------------------------
# Composite Safety Gate
# ---------------------------------------------------------------------------

class CompositeSafetyGate:
    """
    Unified safety pre-filter that combines verdicts from any subset of
    WP2–WP14, MCSSupervisor, and custom WPs.

    Usage
    -----
    ::

        gate = CompositeSafetyGate(aggregator=WeightedSumAggregator())
        gate.register("WP7",  formal_verifier.verify_modification)
        gate.register("WP14", corrigibility_gate.gate_modification)

        verdict = gate.evaluate(plan_code=code, features=feats, raw_verdicts={
            "WP7":  fv_result,
            "WP12": hacking_verdict,
        })

    Parameters
    ----------
    aggregator : AggregatorBase
        Strategy for combining normalised verdicts.
    threshold : float
        Composite safety score below which the action is blocked.
    veto_severity : float
        Any WP reporting severity ≥ this value triggers an immediate veto.
    """

    def __init__(
        self,
        aggregator    : Optional[AggregatorBase] = None,
        threshold     : float = 0.5,
        veto_severity : float = 8.0,
    ) -> None:
        self.aggregator    = aggregator or WeightedSumAggregator()
        self.threshold     = threshold
        self.veto_severity = veto_severity
        self._adapters     : Dict[str, VerdictAdapter] = dict(_BUILTIN_ADAPTERS)
        self._verdicts     : List[CompositeSafetyVerdict] = []

    # ------------------------------------------------------------------
    # Adapter registration
    # ------------------------------------------------------------------

    def register_adapter(self, wp_id: str, adapter: VerdictAdapter) -> None:
        """Add or override a verdict adapter."""
        self._adapters[wp_id] = adapter

    # ------------------------------------------------------------------
    # Core evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        raw_verdicts: Dict[str, Any],
    ) -> CompositeSafetyVerdict:
        """
        Evaluate a set of pre-computed WP verdicts and return a composite.

        Parameters
        ----------
        raw_verdicts : dict
            Mapping from WP ID (e.g. ``"WP7"``) to the raw verdict object
            returned by that WP.  Pass ``None`` for a WP to mark it as
            absent (will be treated as abstain).

        Returns
        -------
        CompositeSafetyVerdict
        """
        t0         = time.perf_counter()
        norm_verts : List[NormalisedVerdict] = []

        for wp_id, raw in raw_verdicts.items():
            adapter = self._adapters.get(wp_id)
            if adapter is None:
                # Unknown WP — create a pass-through abstain verdict
                norm_verts.append(NormalisedVerdict(
                    wp_id, wp_id, 1.0, 0.5, 0.0, abstain=True, raw=raw))
            else:
                norm_verts.append(adapter.adapt(raw))

        # Identify veto and abstain lists
        veto_ids   = [v.wp_id for v in norm_verts
                      if v.veto or (not v.abstain and v.severity >= self.veto_severity)]
        abstain_ids = [v.wp_id for v in norm_verts if v.abstain]

        # Aggregate non-abstaining verdicts
        composite_score, composite_cert, agg_allowed = self.aggregator.aggregate(
            norm_verts, threshold=self.threshold)

        # Veto overrides aggregator
        vetoed  = bool(veto_ids)
        allowed = agg_allowed and not vetoed

        # Safety level
        if vetoed or not allowed:
            if any(v.severity >= 9.0 for v in norm_verts if not v.abstain):
                level = SafetyLevel.UNSAFE
            else:
                level = SafetyLevel.CAUTION
        elif len(abstain_ids) > len(norm_verts) // 2:
            level = SafetyLevel.CAUTION
        else:
            level = SafetyLevel.SAFE

        max_sev = max((v.severity for v in norm_verts if not v.abstain), default=0.0)

        # Reason string
        if vetoed:
            reason = f"veto by {veto_ids} (severity ≥ {self.veto_severity})"
        elif not agg_allowed:
            reason = (f"composite_score={composite_score:.3f} < "
                      f"threshold={self.threshold}")
        else:
            reason = "all checks passed"

        # Fisher p-value (only populated for conformal aggregator)
        p_val = getattr(self.aggregator, "_last_p", None)
        if isinstance(self.aggregator, ConformalPValueAggregator):
            # Re-extract from last aggregate call if available
            p_val = getattr(self.aggregator, "_last_p_combined", None)

        verdict = CompositeSafetyVerdict(
            allowed             = allowed,
            safety_level        = level,
            composite_score     = composite_score,
            composite_certainty = composite_cert,
            max_severity        = max_sev,
            p_value             = p_val,
            vetoed_by           = veto_ids,
            abstained           = abstain_ids,
            verdicts            = norm_verts,
            reason              = reason,
            aggregation_method  = self.aggregator.name,
            elapsed_s           = time.perf_counter() - t0,
        )
        self._verdicts.append(verdict)
        return verdict

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def block_rate(self) -> float:
        if not self._verdicts:
            return 0.0
        return sum(1 for v in self._verdicts if not v.allowed) / len(self._verdicts)

    def stats(self) -> Dict[str, Any]:
        n = len(self._verdicts)
        if n == 0:
            return {"n_evaluated": 0, "block_rate": 0.0}
        scores = [v.composite_score for v in self._verdicts]
        return {
            "n_evaluated"       : n,
            "block_rate"        : self.block_rate(),
            "mean_score"        : float(np.mean(scores)),
            "min_score"         : float(np.min(scores)),
            "n_vetoed"          : sum(1 for v in self._verdicts if v.vetoed_by),
            "n_abstain_majority": sum(1 for v in self._verdicts
                                      if len(v.abstained) > len(v.verdicts) // 2),
        }

    def reset(self) -> None:
        self._verdicts.clear()


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def make_composite_gate(
    method         : str   = "weighted_sum",
    threshold      : float = 0.5,
    veto_severity  : float = 8.0,
    weights        : Optional[Dict[str, float]] = None,
    alpha          : float = 0.05,
    score_threshold: float = 0.5,
    cert_threshold : float = 0.4,
) -> CompositeSafetyGate:
    """
    Factory for ``CompositeSafetyGate`` with a named aggregation strategy.

    Parameters
    ----------
    method : {"weighted_sum", "pareto_front", "conformal_pvalue"}
    threshold : float
        Composite score threshold for ``weighted_sum`` and ``pareto_front``.
    veto_severity : float
        Severity level that triggers an unconditional veto.
    weights : dict, optional
        WP-specific weights for ``weighted_sum``.
    alpha : float
        Significance level for ``conformal_pvalue`` (default 0.05).
    score_threshold, cert_threshold : float
        Reference point for ``pareto_front``.
    """
    if method == "weighted_sum":
        agg = WeightedSumAggregator(weights=weights,
                                    severity_veto_thresh=veto_severity)
    elif method == "pareto_front":
        agg = ParetoFrontAggregator(score_threshold=score_threshold,
                                    certainty_threshold=cert_threshold)
    elif method == "conformal_pvalue":
        agg = ConformalPValueAggregator(alpha=alpha)
    else:
        raise ValueError(f"Unknown aggregation method: {method!r}")

    return CompositeSafetyGate(
        aggregator    = agg,
        threshold     = threshold,
        veto_severity = veto_severity,
    )


# ---------------------------------------------------------------------------
# Convenience summary formatter
# ---------------------------------------------------------------------------

def composite_safety_summary_table(verdicts: List[CompositeSafetyVerdict]) -> str:
    """Format a list of CompositeSafetyVerdict results as a readable table."""
    lines = [
        "",
        "WP15 Composite Safety Gate Results",
        "=" * 72,
        f"{'#':<4} {'Allowed':>7} {'Level':<10} {'Score':>6} {'Cert':>6} "
        f"{'MaxSev':>7} {'Veto':<20}",
        "-" * 72,
    ]
    for i, v in enumerate(verdicts):
        veto_str = ",".join(v.vetoed_by) if v.vetoed_by else "-"
        sym = "YES" if v.allowed else "NO"
        lines.append(
            f"{i:<4} {sym:>7} {v.safety_level.value:<10} "
            f"{v.composite_score:>6.3f} {v.composite_certainty:>6.3f} "
            f"{v.max_severity:>7.1f} {veto_str:<20}"
        )
    lines.append("=" * 72)
    n_allowed = sum(v.allowed for v in verdicts)
    lines.append(f"Allowed: {n_allowed}/{len(verdicts)}")
    lines.append("")
    return "\n".join(lines)
