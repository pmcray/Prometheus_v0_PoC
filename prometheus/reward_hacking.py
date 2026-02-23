"""
WP12 — Reward Hacking Detection & Robustness
=============================================

Detects and mitigates reward hacking (Goodhart's law violations), reward
tampering, specification gaming, and overoptimisation in learned reward
functions (Krakovna et al. 2020; Gao et al. 2022; Pan et al. 2022).

Three orthogonal detectors:

1. **GoodhartDetector** — monitors proxy metric divergence from true reward.
   Tracks rolling correlation between proxy and true signals; alerts when
   the correlation collapses while the proxy keeps climbing (classic Goodhart).

2. **RewardTamperingDetector** — detects attempts to modify the reward
   function or its inputs (Pan et al. 2022).  Uses structural diff on
   reward-model weight vectors and bit-exact checksums on feature arrays.

3. **SpecificationGamingDetector** — identifies when an agent exploits
   unintended loopholes: value-over-replacement (VOR) analysis
   (Everitt et al. 2017), reward overoptimisation (Gao et al. 2022 KL-
   divergence proxy), and complexity/hardcoding heuristics.

The ``RobustRewardWrapper`` composes all three into a single drop-in
replacement for ``ValueLearningAgent.get_reward()``.

References
----------
Krakovna et al. (2020) *Avoiding Side Effects in Complex Environments*
Gao et al. (2022) *Scaling Laws for Reward Model Overoptimisation*
Pan et al. (2022) *The Effects of Reward Misspecification*
Everitt et al. (2017) *Reinforcement Learning with a Corrupted Reward Channel*
"""

from __future__ import annotations

import hashlib
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class GoodhartSignal:
    """Snapshot of proxy–true correlation at one timestep."""
    step: int
    proxy_value: float
    true_value: Optional[float]
    rolling_correlation: float
    diverging: bool                  # True when Goodhart pattern is active
    alert_level: str                 # "none" | "warning" | "critical"
    reason: str = ""


@dataclass
class TamperingReport:
    """Report from the reward-tampering detector."""
    tampered: bool
    tamper_type: str                 # "weight_change" | "feature_injection" | "none"
    weight_delta_norm: float         # L2 norm of weight change
    feature_hash_match: bool         # True if feature checksum unchanged
    description: str = ""
    severity: int = 0                # 0–10


@dataclass
class SpecGamingReport:
    """Report from the specification-gaming detector."""
    gaming_detected: bool
    gaming_type: str                 # "overoptimisation" | "hardcoding" | "loophole" | "none"
    vor_score: float                 # Value-over-replacement score ∈ [0, 1]
    overopt_score: float             # Overoptimisation severity ∈ [0, 1]
    complexity_ratio: float          # reward / behaviour complexity
    description: str = ""


@dataclass
class HackingVerdict:
    """Aggregated verdict from all three detectors."""
    reward: float                    # possibly modified / penalised reward
    hacking_detected: bool
    goodhart_signal: Optional[GoodhartSignal]
    tampering_report: Optional[TamperingReport]
    spec_gaming_report: Optional[SpecGamingReport]
    penalty_applied: float           # reward reduction
    wall_clock_s: float
    description: str = ""

    def summary(self) -> str:
        flags = []
        if self.goodhart_signal and self.goodhart_signal.diverging:
            flags.append(f"Goodhart({self.goodhart_signal.alert_level})")
        if self.tampering_report and self.tampering_report.tampered:
            flags.append(f"Tamper({self.tampering_report.tamper_type})")
        if self.spec_gaming_report and self.spec_gaming_report.gaming_detected:
            flags.append(f"Gaming({self.spec_gaming_report.gaming_type})")
        flag_str = ", ".join(flags) if flags else "none"
        return (
            f"HackingVerdict(reward={self.reward:.3f}, "
            f"penalty={self.penalty_applied:.3f}, "
            f"flags=[{flag_str}])"
        )


# ---------------------------------------------------------------------------
# 1. Goodhart Detector
# ---------------------------------------------------------------------------

class GoodhartDetector:
    """
    Monitors proxy–true reward correlation over a rolling window.

    Goodhart's law: once a measure becomes a target, it ceases to be a good
    measure.  Symptom: proxy metric keeps climbing while true reward stagnates
    or falls → rolling Pearson r drops while proxy trend is positive.

    Parameters
    ----------
    window : int
        Rolling window for correlation (default 30).
    divergence_threshold : float
        Pearson r below this while proxy is trending up → "warning".
    critical_threshold : float
        Pearson r below this → "critical".
    min_proxy_trend : float
        Minimum positive slope of proxy (per step) to check Goodhart.
    """

    def __init__(
        self,
        window: int = 30,
        divergence_threshold: float = 0.3,
        critical_threshold: float = 0.0,
        min_proxy_trend: float = 0.01,
    ) -> None:
        self.window               = window
        self.divergence_threshold = divergence_threshold
        self.critical_threshold   = critical_threshold
        self.min_proxy_trend      = min_proxy_trend

        self._proxy_history: List[float] = []
        self._true_history:  List[float] = []
        self._step           = 0
        self._signals: List[GoodhartSignal] = []

    # ------------------------------------------------------------------
    def update(
        self,
        proxy_value: float,
        true_value: Optional[float] = None,
    ) -> GoodhartSignal:
        """
        Record one timestep and return a Goodhart signal.

        If ``true_value`` is None the detector still tracks proxy history
        (useful when ground truth is only occasionally available).
        """
        self._proxy_history.append(proxy_value)
        if true_value is not None:
            self._true_history.append(true_value)
        self._step += 1

        corr    = self._rolling_correlation()
        trend   = self._proxy_trend()
        diverging, alert, reason = self._classify(corr, trend, true_value)

        signal = GoodhartSignal(
            step                = self._step,
            proxy_value         = proxy_value,
            true_value          = true_value,
            rolling_correlation = corr,
            diverging           = diverging,
            alert_level         = alert,
            reason              = reason,
        )
        self._signals.append(signal)

        if diverging:
            logger.warning("GoodhartDetector: %s (step=%d)", reason, self._step)

        return signal

    # ------------------------------------------------------------------
    def _rolling_correlation(self) -> float:
        """Pearson r between proxy and true over the last ``window`` steps."""
        n = min(self.window, len(self._proxy_history), len(self._true_history))
        if n < 5:
            return 1.0  # not enough data — assume OK
        px = np.array(self._proxy_history[-n:])
        ty = np.array(self._true_history[-n:])
        if px.std() < 1e-9 or ty.std() < 1e-9:
            return 1.0  # constant series — no information
        return float(np.corrcoef(px, ty)[0, 1])

    def _proxy_trend(self) -> float:
        """OLS slope of the proxy over the last ``window`` steps (per step)."""
        n = min(self.window, len(self._proxy_history))
        if n < 3:
            return 0.0
        y = np.array(self._proxy_history[-n:])
        x = np.arange(n, dtype=float)
        # Closed-form OLS slope
        x_mean = x.mean()
        return float(np.dot(x - x_mean, y - y.mean()) / max(np.dot(x - x_mean, x - x_mean), 1e-12))

    def _classify(
        self,
        corr: float,
        trend: float,
        true_value: Optional[float],
    ) -> Tuple[bool, str, str]:
        has_true = len(self._true_history) >= 5
        if not has_true:
            return False, "none", "insufficient true reward data"

        proxy_climbing = trend > self.min_proxy_trend

        if corr < self.critical_threshold and proxy_climbing:
            return True, "critical", (
                f"proxy climbing (slope={trend:.4f}) but true reward "
                f"negatively correlated (r={corr:.3f})"
            )
        if corr < self.divergence_threshold and proxy_climbing:
            return True, "warning", (
                f"proxy climbing (slope={trend:.4f}) with weak "
                f"true-reward correlation (r={corr:.3f})"
            )
        return False, "none", ""

    # ------------------------------------------------------------------
    @property
    def signals(self) -> List[GoodhartSignal]:
        return list(self._signals)

    def n_alerts(self, level: str = "warning") -> int:
        """Count signals at or above ``level`` ('warning', 'critical')."""
        lvl_map = {"none": 0, "warning": 1, "critical": 2}
        target  = lvl_map.get(level, 1)
        return sum(1 for s in self._signals if lvl_map.get(s.alert_level, 0) >= target)

    def stats(self) -> Dict[str, Any]:
        return {
            "steps"            : self._step,
            "n_warnings"       : self.n_alerts("warning"),
            "n_criticals"      : self.n_alerts("critical"),
            "last_correlation" : self._rolling_correlation(),
            "last_proxy_trend" : self._proxy_trend(),
        }

    def reset(self) -> None:
        self._proxy_history.clear()
        self._true_history.clear()
        self._step = 0
        self._signals.clear()


# ---------------------------------------------------------------------------
# 2. Reward Tampering Detector
# ---------------------------------------------------------------------------

class RewardTamperingDetector:
    """
    Detects modifications to reward model weights or input features.

    Two checks:
    - **Weight-change check**: compares L2 norm of weight delta against a
      learned baseline.  Sudden large jumps flag tampering.
    - **Feature hash check**: bit-exact SHA-256 checksum of feature arrays.
      Any byte-level change is flagged.

    Parameters
    ----------
    weight_change_threshold : float
        Fraction of ||w|| that constitutes suspicious change (default 0.5).
    """

    def __init__(self, weight_change_threshold: float = 0.5) -> None:
        self.weight_change_threshold = weight_change_threshold
        self._reference_weights: Optional[np.ndarray] = None
        self._reports: List[TamperingReport] = []

    # ------------------------------------------------------------------
    def register_weights(self, weights: np.ndarray) -> None:
        """Store the current (trusted) weight vector as reference."""
        self._reference_weights = weights.copy()

    def check_weights(self, current_weights: np.ndarray) -> TamperingReport:
        """
        Compare ``current_weights`` against the stored reference.

        Returns a TamperingReport.  Always call ``register_weights`` first.
        """
        if self._reference_weights is None:
            return TamperingReport(
                tampered          = False,
                tamper_type       = "none",
                weight_delta_norm = 0.0,
                feature_hash_match= True,
                description       = "no reference weights registered",
            )

        delta      = current_weights - self._reference_weights
        delta_norm = float(np.linalg.norm(delta))
        ref_norm   = float(np.linalg.norm(self._reference_weights))
        threshold  = self.weight_change_threshold * max(ref_norm, 1e-9)

        tampered = delta_norm > threshold
        severity = min(10, int(delta_norm / max(threshold, 1e-9) * 5))

        report = TamperingReport(
            tampered          = tampered,
            tamper_type       = "weight_change" if tampered else "none",
            weight_delta_norm = delta_norm,
            feature_hash_match= True,
            description       = (
                f"weight delta {delta_norm:.4f} exceeds threshold {threshold:.4f}"
                if tampered else
                f"weight delta {delta_norm:.4f} within threshold"
            ),
            severity = severity if tampered else 0,
        )
        self._reports.append(report)

        if tampered:
            logger.warning(
                "RewardTamperingDetector: weight change %.4f > threshold %.4f",
                delta_norm, threshold,
            )
        return report

    # ------------------------------------------------------------------
    @staticmethod
    def feature_checksum(features: np.ndarray) -> str:
        """SHA-256 checksum of a feature array (byte-exact)."""
        return hashlib.sha256(np.ascontiguousarray(features).tobytes()).hexdigest()

    def check_features(
        self,
        features: np.ndarray,
        reference_checksum: str,
    ) -> TamperingReport:
        """
        Verify ``features`` against a previously computed checksum.

        Returns a TamperingReport with ``tamper_type="feature_injection"``
        if the checksum mismatches.
        """
        current_checksum = self.feature_checksum(features)
        match = current_checksum == reference_checksum

        report = TamperingReport(
            tampered           = not match,
            tamper_type        = "none" if match else "feature_injection",
            weight_delta_norm  = 0.0,
            feature_hash_match = match,
            description        = (
                "feature checksum matches reference" if match else
                "feature checksum MISMATCH — possible feature injection"
            ),
            severity = 8 if not match else 0,
        )
        self._reports.append(report)

        if not match:
            logger.warning("RewardTamperingDetector: feature checksum mismatch!")
        return report

    # ------------------------------------------------------------------
    @property
    def reports(self) -> List[TamperingReport]:
        return list(self._reports)

    def n_tamper_events(self) -> int:
        return sum(1 for r in self._reports if r.tampered)

    def stats(self) -> Dict[str, Any]:
        return {
            "n_checks"        : len(self._reports),
            "n_tamper_events" : self.n_tamper_events(),
            "max_delta_norm"  : max((r.weight_delta_norm for r in self._reports), default=0.0),
        }

    def reset(self) -> None:
        self._reference_weights = None
        self._reports.clear()


# ---------------------------------------------------------------------------
# 3. Specification Gaming Detector
# ---------------------------------------------------------------------------

class SpecificationGamingDetector:
    """
    Detects specification gaming via three complementary metrics.

    1. **Value-over-replacement (VOR)** (Everitt et al. 2017): compare
       reward of a proposed action against a reference replacement action.
       A large positive VOR means the agent is exploiting an unintended
       shortcut rather than genuinely solving the task.

    2. **Overoptimisation score** (Gao et al. 2022): proxy reward diverges
       from a held-out evaluation signal.  We approximate as the ratio of
       proxy reward growth to evaluation reward growth; values > 1 indicate
       overoptimisation.

    3. **Complexity ratio**: reward / log(behaviour_complexity).  High reward
       at low complexity signals hardcoding / shortcut solutions.

    Parameters
    ----------
    vor_threshold : float
        VOR score above which gaming is flagged (default 0.7).
    overopt_threshold : float
        Overoptimisation score above which gaming is flagged (default 2.0).
    complexity_threshold : float
        Reward-to-complexity ratio above which gaming is flagged (default 5.0).
    """

    def __init__(
        self,
        vor_threshold: float       = 0.7,
        overopt_threshold: float   = 2.0,
        complexity_threshold: float = 5.0,
    ) -> None:
        self.vor_threshold         = vor_threshold
        self.overopt_threshold     = overopt_threshold
        self.complexity_threshold  = complexity_threshold
        self._reports: List[SpecGamingReport] = []

    # ------------------------------------------------------------------
    def check(
        self,
        proxy_reward: float,
        eval_reward: Optional[float]  = None,
        replacement_reward: Optional[float] = None,
        behaviour_complexity: Optional[float] = None,
        proxy_baseline: float         = 0.0,
        eval_baseline: float          = 0.0,
    ) -> SpecGamingReport:
        """
        Run all three checks and return a SpecGamingReport.

        Parameters
        ----------
        proxy_reward : float
            The agent's proxy reward signal.
        eval_reward : float, optional
            Independent evaluation / true reward.
        replacement_reward : float, optional
            Reward of a reference "replacement" behaviour (for VOR).
        behaviour_complexity : float, optional
            Measure of plan complexity (e.g. AST node count, code length).
        proxy_baseline : float
            Expected proxy reward under normal behaviour.
        eval_baseline : float
            Expected eval reward under normal behaviour.
        """
        # --- VOR ---
        if replacement_reward is not None:
            # VOR = (proxy - replacement) normalised to [0, 1]
            vor_raw = proxy_reward - replacement_reward
            vor_score = float(np.clip(vor_raw / max(abs(replacement_reward) + 1e-9, 1e-9), 0.0, 1.0))
        else:
            vor_score = 0.0

        # --- Overoptimisation ---
        if eval_reward is not None:
            proxy_gain = proxy_reward - proxy_baseline
            eval_gain  = eval_reward  - eval_baseline
            if abs(eval_gain) < 1e-9:
                # proxy increasing while eval is flat → bad
                overopt_score = min(abs(proxy_gain) * 5, 10.0) if proxy_gain > 0.01 else 0.0
            else:
                overopt_score = float(abs(proxy_gain) / abs(eval_gain))
        else:
            overopt_score = 0.0

        # --- Complexity ratio ---
        if behaviour_complexity is not None and behaviour_complexity > 0:
            complexity_ratio = float(proxy_reward / max(math.log1p(behaviour_complexity), 1e-9))
        else:
            complexity_ratio = 0.0

        # --- Classify ---
        gaming_detected = False
        gaming_type     = "none"
        desc_parts      = []

        if vor_score >= self.vor_threshold:
            gaming_detected = True
            gaming_type     = "loophole"
            desc_parts.append(f"VOR={vor_score:.3f} ≥ {self.vor_threshold}")

        if overopt_score >= self.overopt_threshold:
            gaming_detected = True
            gaming_type     = "overoptimisation"
            desc_parts.append(f"overopt={overopt_score:.2f} ≥ {self.overopt_threshold}")

        if complexity_ratio >= self.complexity_threshold:
            gaming_detected = True
            gaming_type     = gaming_type if gaming_type != "none" else "hardcoding"
            desc_parts.append(f"complexity_ratio={complexity_ratio:.2f} ≥ {self.complexity_threshold}")

        report = SpecGamingReport(
            gaming_detected  = gaming_detected,
            gaming_type      = gaming_type,
            vor_score        = vor_score,
            overopt_score    = overopt_score,
            complexity_ratio = complexity_ratio,
            description      = "; ".join(desc_parts) if desc_parts else "no gaming detected",
        )
        self._reports.append(report)

        if gaming_detected:
            logger.warning(
                "SpecificationGamingDetector: %s — %s",
                gaming_type, report.description,
            )
        return report

    # ------------------------------------------------------------------
    @property
    def reports(self) -> List[SpecGamingReport]:
        return list(self._reports)

    def gaming_rate(self) -> float:
        if not self._reports:
            return 0.0
        return sum(1 for r in self._reports if r.gaming_detected) / len(self._reports)

    def stats(self) -> Dict[str, Any]:
        return {
            "n_checks"        : len(self._reports),
            "gaming_rate"     : self.gaming_rate(),
            "mean_vor"        : float(np.mean([r.vor_score for r in self._reports])) if self._reports else 0.0,
            "mean_overopt"    : float(np.mean([r.overopt_score for r in self._reports])) if self._reports else 0.0,
        }

    def reset(self) -> None:
        self._reports.clear()


# ---------------------------------------------------------------------------
# 4. Robust Reward Wrapper
# ---------------------------------------------------------------------------

class RobustRewardWrapper:
    """
    Drop-in replacement for ``ValueLearningAgent.get_reward()`` that runs
    all three detectors on every call and applies a penalty when hacking is
    detected.

    Parameters
    ----------
    base_agent : object
        A ``ValueLearningAgent`` (must have ``get_reward(features) → float``
        and ``get_weights() → np.ndarray``).
    goodhart_detector : GoodhartDetector, optional
    tampering_detector : RewardTamperingDetector, optional
    gaming_detector : SpecificationGamingDetector, optional
    penalty_scale : float
        Multiplicative penalty applied to reward when hacking is detected.
        Effective reward = base_reward * (1 - penalty_scale) for each active
        detector (capped at 1.0 total).
    true_reward_fn : callable, optional
        Optional function ``(features) → float`` returning the true reward.
        Used by the Goodhart detector.
    replacement_reward_fn : callable, optional
        Optional function ``(features) → float`` returning a reference
        replacement reward.  Used by the VOR check.
    complexity_fn : callable, optional
        Optional function ``(features) → float`` returning behaviour complexity.
    """

    def __init__(
        self,
        base_agent: Any,
        goodhart_detector:   Optional[GoodhartDetector]            = None,
        tampering_detector:  Optional[RewardTamperingDetector]     = None,
        gaming_detector:     Optional[SpecificationGamingDetector] = None,
        penalty_scale: float = 0.3,
        true_reward_fn:      Optional[Callable[[np.ndarray], float]] = None,
        replacement_reward_fn: Optional[Callable[[np.ndarray], float]] = None,
        complexity_fn:       Optional[Callable[[np.ndarray], float]] = None,
    ) -> None:
        self.base_agent           = base_agent
        self.goodhart_detector    = goodhart_detector or GoodhartDetector()
        self.tampering_detector   = tampering_detector or RewardTamperingDetector()
        self.gaming_detector      = gaming_detector or SpecificationGamingDetector()
        self.penalty_scale        = penalty_scale
        self.true_reward_fn       = true_reward_fn
        self.replacement_reward_fn = replacement_reward_fn
        self.complexity_fn        = complexity_fn

        self._verdicts: List[HackingVerdict] = []
        self._proxy_baseline = 0.0
        self._eval_baseline  = 0.0

        # Seed the tampering detector with the initial weights
        try:
            self.tampering_detector.register_weights(base_agent.get_weights())
        except (AttributeError, TypeError, ValueError):
            # Agent may not expose get_weights() yet; tampering baseline
            # will be set on the first call to check_weights().
            pass

    # ------------------------------------------------------------------
    def get_reward(
        self,
        features: np.ndarray,
        eval_reward: Optional[float]  = None,
        reference_checksum: Optional[str] = None,
    ) -> HackingVerdict:
        """
        Compute reward with hacking detection.

        Parameters
        ----------
        features : np.ndarray
            State feature vector.
        eval_reward : float, optional
            Ground-truth / evaluation reward for overoptimisation check.
        reference_checksum : str, optional
            SHA-256 checksum of the original feature array; used for
            feature-injection detection.

        Returns
        -------
        HackingVerdict
            Includes the (possibly penalised) ``reward`` field plus all
            detector outputs.
        """
        t0 = time.perf_counter()

        proxy_reward = float(self.base_agent.get_reward(features))

        # --- Goodhart check ---
        true_val = None
        if self.true_reward_fn is not None:
            try:
                true_val = float(self.true_reward_fn(features))
            except (TypeError, ValueError, ArithmeticError):
                # True reward function rejected this feature vector; treat as
                # unknown (Goodhart check will use proxy only).
                pass
        goodhart_signal = self.goodhart_detector.update(proxy_reward, true_val)

        # --- Tampering check ---
        if reference_checksum is not None:
            tampering_report = self.tampering_detector.check_features(
                features, reference_checksum
            )
        else:
            try:
                current_weights = self.base_agent.get_weights()
                tampering_report = self.tampering_detector.check_weights(current_weights)
            except (AttributeError, TypeError, ValueError):
                # Agent does not expose get_weights() or weights are in an
                # unexpected format; report as unverified (not tampered).
                tampering_report = TamperingReport(
                    tampered=False, tamper_type="none",
                    weight_delta_norm=0.0, feature_hash_match=True,
                )

        # --- Specification gaming check ---
        replacement_reward = None
        if self.replacement_reward_fn is not None:
            try:
                replacement_reward = float(self.replacement_reward_fn(features))
            except (TypeError, ValueError, ArithmeticError):
                # Replacement reward function rejected these features; leave
                # replacement_reward as None (gaming check will run without it).
                pass
        complexity = None
        if self.complexity_fn is not None:
            try:
                complexity = float(self.complexity_fn(features))
            except (TypeError, ValueError, ArithmeticError):
                # Complexity function rejected these features; gaming check
                # will run without a complexity signal.
                pass
        gaming_report = self.gaming_detector.check(
            proxy_reward         = proxy_reward,
            eval_reward          = eval_reward if eval_reward is not None else true_val,
            replacement_reward   = replacement_reward,
            behaviour_complexity = complexity,
            proxy_baseline       = self._proxy_baseline,
            eval_baseline        = self._eval_baseline,
        )

        # --- Compute penalty ---
        flags = [
            goodhart_signal.diverging,
            tampering_report.tampered,
            gaming_report.gaming_detected,
        ]
        n_flags     = sum(flags)
        penalty     = min(1.0, n_flags * self.penalty_scale)
        adj_reward  = proxy_reward * (1.0 - penalty)

        hacking_detected = any(flags)
        descs = []
        if goodhart_signal.diverging:
            descs.append(f"Goodhart({goodhart_signal.alert_level})")
        if tampering_report.tampered:
            descs.append(f"Tampering({tampering_report.tamper_type})")
        if gaming_report.gaming_detected:
            descs.append(f"Gaming({gaming_report.gaming_type})")

        verdict = HackingVerdict(
            reward              = adj_reward,
            hacking_detected    = hacking_detected,
            goodhart_signal     = goodhart_signal,
            tampering_report    = tampering_report,
            spec_gaming_report  = gaming_report,
            penalty_applied     = penalty,
            wall_clock_s        = time.perf_counter() - t0,
            description         = "; ".join(descs) if descs else "clean",
        )
        self._verdicts.append(verdict)

        if hacking_detected:
            logger.warning(
                "RobustRewardWrapper: hacking detected — %s (penalty=%.2f)",
                verdict.description, penalty,
            )
        return verdict

    # ------------------------------------------------------------------
    def update_baselines(self, proxy_baseline: float, eval_baseline: float) -> None:
        """Update the expected baseline rewards for overoptimisation scoring."""
        self._proxy_baseline = proxy_baseline
        self._eval_baseline  = eval_baseline

    def register_weights(self) -> None:
        """Re-snapshot current agent weights as the trusted reference."""
        try:
            self.tampering_detector.register_weights(self.base_agent.get_weights())
        except Exception as exc:
            logger.warning("register_weights failed: %s", exc)

    # ------------------------------------------------------------------
    @property
    def verdicts(self) -> List[HackingVerdict]:
        return list(self._verdicts)

    def hacking_rate(self) -> float:
        if not self._verdicts:
            return 0.0
        return sum(1 for v in self._verdicts if v.hacking_detected) / len(self._verdicts)

    def stats(self) -> Dict[str, Any]:
        return {
            "n_calls"          : len(self._verdicts),
            "hacking_rate"     : self.hacking_rate(),
            "mean_penalty"     : float(np.mean([v.penalty_applied for v in self._verdicts])) if self._verdicts else 0.0,
            "goodhart_stats"   : self.goodhart_detector.stats(),
            "tampering_stats"  : self.tampering_detector.stats(),
            "gaming_stats"     : self.gaming_detector.stats(),
        }

    def reset(self) -> None:
        self._verdicts.clear()
        self.goodhart_detector.reset()
        self.tampering_detector.reset()
        self.gaming_detector.reset()
