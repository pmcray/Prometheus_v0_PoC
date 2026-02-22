"""
Uncertainty Quantification Benchmark — Prometheus v0.97 (WP11)

Evaluates conformal prediction coverage and bootstrap ensemble uncertainty
on synthetic preference data.

Scenarios
---------
coverage_guarantee
    Verify the marginal coverage guarantee: for α ∈ {0.05, 0.1, 0.2},
    empirical coverage on held-out test pairs must be ≥ 1 − α.
    Reports actual vs expected coverage, mean interval width.

alpha_sweep
    Sweep α ∈ {0.05, 0.10, 0.15, 0.20, 0.30} and report:
    coverage, abstain_rate, certain_correct_rate, mean_width.

bootstrap_uncertainty
    Vary number of bootstrap models B ∈ {5, 10, 20, 50} and report:
    mean epistemic uncertainty (std), rank correlation with true reward.

abstention_quality
    Inject OOD (out-of-distribution) samples; verify that the conformal
    predictor abstains on high-uncertainty inputs more often than in-dist.

Public API
----------
UncertaintyBenchmark.run(scenario)  → UQBenchmarkResult
UncertaintyBenchmark.run_all()      → List[UQBenchmarkResult]
UncertaintyBenchmark.summary_table(results) → str
"""
from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prometheus.value_learning import ValueLearningAgent
from prometheus.uncertainty import (
    ConformalRewardPredictor,
    BootstrapEnsemble,
    CalibrationResult,
    RewardInterval,
    calibration_curve,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------

N_FEATS = 5


def _true_reward(features: np.ndarray, true_w: np.ndarray) -> float:
    return float(np.dot(true_w, features))


def _make_pairs(
    n: int,
    true_w: np.ndarray,
    seed: int = 0,
    noise: float = 0.0,
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Generate (preferred, unpreferred) pairs under true_w."""
    rng   = np.random.default_rng(seed)
    pairs = []
    for _ in range(n):
        a = rng.uniform(0, 1, N_FEATS)
        b = rng.uniform(0, 1, N_FEATS)
        if noise > 0:
            a += rng.normal(0, noise, N_FEATS)
            b += rng.normal(0, noise, N_FEATS)
        ra = _true_reward(a, true_w)
        rb = _true_reward(b, true_w)
        pairs.append((a, b) if ra >= rb else (b, a))
    return pairs


def _trained_agent(
    true_w   : np.ndarray,
    n_train  : int = 80,
    seed     : int = 0,
) -> ValueLearningAgent:
    agent = ValueLearningAgent(feature_size=N_FEATS, l2_reg=0.01)
    pairs = _make_pairs(n_train, true_w, seed=seed)
    agent.train_to_convergence(pairs, max_epochs=100)
    return agent


def _make_true_w(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    w   = rng.normal(0, 1, N_FEATS)
    return w / (np.linalg.norm(w) + 1e-12)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class UQBenchmarkResult:
    scenario     : str
    notes        : str

    # Coverage guarantee scenario
    alphas_tested          : List[float] = field(default_factory=list)
    target_coverages       : List[float] = field(default_factory=list)
    empirical_coverages    : List[float] = field(default_factory=list)
    coverage_satisfied     : List[bool]  = field(default_factory=list)

    # Alpha sweep scenario
    abstain_rates          : List[float] = field(default_factory=list)
    certain_correct_rates  : List[float] = field(default_factory=list)
    mean_widths            : List[float] = field(default_factory=list)

    # Bootstrap scenario
    n_bootstraps           : List[int]   = field(default_factory=list)
    mean_uncertainties     : List[float] = field(default_factory=list)
    rank_correlations      : List[float] = field(default_factory=list)

    # Abstention quality
    indist_abstain_rate    : float = 0.0
    ood_abstain_rate       : float = 0.0

    wall_clock_s           : float = 0.0
    extra                  : Dict[str, Any] = field(default_factory=dict)

    def summary_dict(self) -> Dict[str, Any]:
        return {
            "scenario"            : self.scenario,
            "notes"               : self.notes,
            "alphas_tested"       : self.alphas_tested,
            "target_coverages"    : [round(c, 3) for c in self.target_coverages],
            "empirical_coverages" : [round(c, 3) for c in self.empirical_coverages],
            "coverage_satisfied"  : self.coverage_satisfied,
            "wall_clock_s"        : round(self.wall_clock_s, 3),
        }


# ---------------------------------------------------------------------------
# Benchmark class
# ---------------------------------------------------------------------------

class UncertaintyBenchmark:
    """
    Benchmark runner for WP11.

    Parameters
    ----------
    n_train     : Training pairs for base agent.
    n_calibrate : Calibration pairs for conformal predictor.
    n_test      : Test pairs for evaluation.
    seed        : Random seed.
    """

    SCENARIOS = (
        "coverage_guarantee",
        "alpha_sweep",
        "bootstrap_uncertainty",
        "abstention_quality",
    )

    def __init__(
        self,
        n_train    : int = 80,
        n_calibrate: int = 60,
        n_test     : int = 100,
        seed       : int = 42,
    ) -> None:
        self.n_train     = n_train
        self.n_calibrate = n_calibrate
        self.n_test      = n_test
        self.seed        = seed

        self._true_w = _make_true_w(seed)
        self._agent  = _trained_agent(self._true_w, n_train=n_train, seed=seed)
        self._cal    = _make_pairs(n_calibrate, self._true_w, seed=seed + 1)
        self._test   = _make_pairs(n_test,      self._true_w, seed=seed + 2)

    # ------------------------------------------------------------------
    # Scenario 1: coverage_guarantee
    # ------------------------------------------------------------------

    def _run_coverage_guarantee(self) -> UQBenchmarkResult:
        t0     = time.time()
        alphas = [0.05, 0.10, 0.20, 0.30]

        target_coverages    = []
        empirical_coverages = []
        coverage_satisfied  = []
        mean_widths         = []

        for alpha in alphas:
            pred = ConformalRewardPredictor(self._agent, alpha=alpha)
            pred.calibrate(self._cal)

            # Measure coverage on test set
            n_covered = 0
            widths    = []
            for phi1, phi2 in self._test:
                phi1 = np.asarray(phi1, dtype=float)
                phi2 = np.asarray(phi2, dtype=float)
                iv   = pred.predict(phi1)
                r1   = self._agent.get_reward(phi1)
                r2   = self._agent.get_reward(phi2)
                diff = r1 - r2
                if iv.lower <= diff <= iv.upper:
                    n_covered += 1
                widths.append(iv.width)

            emp_cov = n_covered / len(self._test)
            target  = 1 - alpha

            target_coverages.append(target)
            empirical_coverages.append(emp_cov)
            coverage_satisfied.append(emp_cov >= target - 0.02)   # 2% tolerance
            mean_widths.append(float(np.mean(widths)))

        return UQBenchmarkResult(
            scenario             = "coverage_guarantee",
            notes                = "Marginal coverage ≥ 1−α for α ∈ {0.05,0.1,0.2,0.3}",
            alphas_tested        = alphas,
            target_coverages     = target_coverages,
            empirical_coverages  = empirical_coverages,
            coverage_satisfied   = coverage_satisfied,
            mean_widths          = mean_widths,
            wall_clock_s         = time.time() - t0,
            extra                = {"all_satisfied": all(coverage_satisfied)},
        )

    # ------------------------------------------------------------------
    # Scenario 2: alpha_sweep
    # ------------------------------------------------------------------

    def _run_alpha_sweep(self) -> UQBenchmarkResult:
        t0     = time.time()
        alphas = [0.05, 0.10, 0.15, 0.20, 0.30]

        pred = ConformalRewardPredictor(self._agent, alpha=0.10, abstain_width=0.8)
        pred.calibrate(self._cal)

        alphas_out   = []
        abstain_rates  = []
        correct_rates  = []
        mean_widths    = []

        for alpha in alphas:
            # Temporarily use this alpha's quantile
            scores = pred._cal_result.nonconformity_scores
            n      = len(scores)
            level  = np.ceil((n + 1) * (1 - alpha)) / n
            level  = min(level, 1.0)
            pred._q_hat = float(np.quantile(scores, level))
            pred.alpha  = alpha

            stats = pred.coverage_stats(self._test)
            alphas_out.append(alpha)
            abstain_rates.append(stats["abstain_rate"])
            correct_rates.append(stats["certain_correct"])
            mean_widths.append(stats["mean_width"])

        return UQBenchmarkResult(
            scenario            = "alpha_sweep",
            notes               = "Abstain/accuracy/width trade-off vs α",
            alphas_tested       = alphas_out,
            target_coverages    = [1 - a for a in alphas_out],
            abstain_rates       = abstain_rates,
            certain_correct_rates = correct_rates,
            mean_widths         = mean_widths,
            wall_clock_s        = time.time() - t0,
        )

    # ------------------------------------------------------------------
    # Scenario 3: bootstrap_uncertainty
    # ------------------------------------------------------------------

    def _run_bootstrap_uncertainty(self) -> UQBenchmarkResult:
        t0           = time.time()
        n_boots_list = [5, 10, 20, 50]
        train_pairs  = _make_pairs(self.n_train, self._true_w, seed=self.seed)

        mean_uncs   = []
        rank_corrs  = []

        test_feats  = [phi1 for phi1, _ in self._test[:40]]
        true_rewards = [_true_reward(f, self._true_w) for f in test_feats]

        for n_b in n_boots_list:
            ensemble = BootstrapEnsemble(
                feature_size = N_FEATS,
                n_bootstrap  = n_b,
                seed         = self.seed,
            )
            ensemble.fit(train_pairs, max_epochs=50)

            preds = [ensemble.predict(f) for f in test_feats]
            uncs  = [p.std for p in preds]
            means = [p.mean for p in preds]

            mean_uncs.append(float(np.mean(uncs)))

            # Rank correlation: do higher-uncertainty predictions correspond
            # to larger absolute errors?
            errors = [abs(m - t) for m, t in zip(means, true_rewards)]
            rho, _  = spearmanr(uncs, errors)
            rank_corrs.append(float(rho) if np.isfinite(rho) else 0.0)

        return UQBenchmarkResult(
            scenario           = "bootstrap_uncertainty",
            notes              = "Epistemic uncertainty vs B; rank corr with abs error",
            n_bootstraps       = n_boots_list,
            mean_uncertainties = mean_uncs,
            rank_correlations  = rank_corrs,
            wall_clock_s       = time.time() - t0,
            extra              = {"n_test_feats": len(test_feats)},
        )

    # ------------------------------------------------------------------
    # Scenario 4: abstention_quality
    # ------------------------------------------------------------------

    def _run_abstention_quality(self) -> UQBenchmarkResult:
        t0 = time.time()

        pred = ConformalRewardPredictor(
            self._agent, alpha=0.10, abstain_width=0.5
        )
        pred.calibrate(self._cal)

        # In-distribution: same distribution as training
        indist_feats = [phi1 for phi1, _ in self._test[:50]]
        n_abstain_id = sum(
            1 for f in indist_feats
            if pred.predict(f).abstain
        )
        indist_abstain_rate = n_abstain_id / len(indist_feats)

        # OOD: features drawn from a very different range (5× scale)
        rng         = np.random.default_rng(self.seed + 77)
        ood_feats   = [rng.uniform(5, 10, N_FEATS) for _ in range(50)]
        n_abstain_od = sum(
            1 for f in ood_feats
            if pred.predict(np.array(f)).abstain
        )
        ood_abstain_rate = n_abstain_od / len(ood_feats)

        return UQBenchmarkResult(
            scenario             = "abstention_quality",
            notes                = "OOD inputs should abstain more than in-distribution",
            indist_abstain_rate  = indist_abstain_rate,
            ood_abstain_rate     = ood_abstain_rate,
            wall_clock_s         = time.time() - t0,
            extra                = {
                "n_indist"       : len(indist_feats),
                "n_ood"          : len(ood_feats),
                "n_abstain_id"   : n_abstain_id,
                "n_abstain_ood"  : n_abstain_od,
            },
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self, scenario: str) -> UQBenchmarkResult:
        if scenario == "coverage_guarantee":
            return self._run_coverage_guarantee()
        elif scenario == "alpha_sweep":
            return self._run_alpha_sweep()
        elif scenario == "bootstrap_uncertainty":
            return self._run_bootstrap_uncertainty()
        elif scenario == "abstention_quality":
            return self._run_abstention_quality()
        else:
            raise ValueError(
                f"Unknown scenario {scenario!r}. Choose from {self.SCENARIOS}"
            )

    def run_all(self) -> List[UQBenchmarkResult]:
        return [self.run(s) for s in self.SCENARIOS]

    def summary_table(self, results: List[UQBenchmarkResult]) -> str:
        lines = []
        for r in results:
            lines.append(f"\n{'='*60}")
            lines.append(f"Scenario: {r.scenario}")
            lines.append(f"  Notes: {r.notes}  Time: {r.wall_clock_s:.2f}s")

            if r.scenario == "coverage_guarantee":
                lines.append(f"  {'α':<6} {'Target':>8} {'Empirical':>10} {'OK?':>5} {'Width':>8}")
                lines.append("  " + "-" * 40)
                for a, tgt, emp, ok, w in zip(
                    r.alphas_tested, r.target_coverages,
                    r.empirical_coverages, r.coverage_satisfied, r.mean_widths
                ):
                    lines.append(
                        f"  {a:<6.2f} {tgt*100:>7.1f}% {emp*100:>9.1f}% "
                        f"{'✓' if ok else '✗':>5} {w:>8.4f}"
                    )
                lines.append(f"  All satisfied: {r.extra.get('all_satisfied', '?')}")

            elif r.scenario == "alpha_sweep":
                lines.append(f"  {'α':<6} {'AbstainRate':>12} {'CertainCorr':>12} {'Width':>8}")
                lines.append("  " + "-" * 42)
                for a, ar, cr, w in zip(
                    r.alphas_tested, r.abstain_rates,
                    r.certain_correct_rates, r.mean_widths
                ):
                    lines.append(
                        f"  {a:<6.2f} {ar*100:>11.1f}% {cr*100:>11.1f}% {w:>8.4f}"
                    )

            elif r.scenario == "bootstrap_uncertainty":
                lines.append(f"  {'B':>5} {'MeanStd':>10} {'RankCorr':>10}")
                lines.append("  " + "-" * 28)
                for nb, mu, rc in zip(
                    r.n_bootstraps, r.mean_uncertainties, r.rank_correlations
                ):
                    lines.append(f"  {nb:>5} {mu:>10.4f} {rc:>10.4f}")

            elif r.scenario == "abstention_quality":
                lines.append(f"  In-distribution abstain rate:  {r.indist_abstain_rate*100:.1f}%")
                lines.append(f"  OOD abstain rate:              {r.ood_abstain_rate*100:.1f}%")
                diff = r.ood_abstain_rate - r.indist_abstain_rate
                lines.append(f"  Δ (OOD − in-dist):            {diff*100:+.1f}%")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bench   = UncertaintyBenchmark(seed=42)
    results = bench.run_all()
    print("\n=== Uncertainty Quantification Benchmark Results ===")
    print(bench.summary_table(results))
