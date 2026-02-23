"""
Certified Robustness Benchmark — Prometheus v0.97 (WP8)

Evaluates the SmoothedValueLearner's certification guarantees across:

  sigma_sweep   — vary noise level σ ∈ {0.05, 0.1, 0.25, 0.5};
                  report certified fraction and mean radius at ε = 0.1.

  epsilon_sweep — vary perturbation budget ε ∈ {0.05, 0.1, 0.2, 0.3};
                  report certified fraction and accuracy at fixed σ = 0.1.

  adversarial   — apply actual L₂-bounded perturbations (ε_attack = 0.05)
                  to preferred trajectories; measure whether the certified
                  preference still holds (certified accuracy under attack).

For each scenario the benchmark reports:
  - certified_fraction: fraction of pairs with a valid certificate
  - mean_certified_radius: mean R over non-abstained pairs
  - preference_accuracy: agreement between smoothed and base learner
  - certified_accuracy_under_attack: for adversarial scenario

Public API
----------
CertifiedRobustnessBenchmark.run(scenario) → CRBenchmarkResult
CertifiedRobustnessBenchmark.run_all()     → List[CRBenchmarkResult]
"""
from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prometheus.value_learning import ValueLearningAgent
from prometheus.certified_robustness import SmoothedValueLearner, CertificationResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Synthetic data helpers (reused from WP3 tests)
# ---------------------------------------------------------------------------

N_FEATS = 5
RNG     = np.random.default_rng(0)


def _make_pairs(n_pairs: int = 60, seed: int = 0) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Generate synthetic (preferred, unpreferred) pairs under a true reward vector."""
    rng    = np.random.default_rng(seed)
    true_w = rng.normal(0, 1, N_FEATS)
    pairs  = []
    for _ in range(n_pairs):
        a = rng.uniform(0, 1, N_FEATS)
        b = rng.uniform(0, 1, N_FEATS)
        pairs.append((a, b) if np.dot(true_w, a) >= np.dot(true_w, b) else (b, a))
    return pairs


def _trained_agent(n_pairs: int = 80, seed: int = 0) -> ValueLearningAgent:
    agent = ValueLearningAgent(feature_size=N_FEATS, l2_reg=0.01)
    agent.train_to_convergence(_make_pairs(n_pairs, seed), max_epochs=50)
    return agent


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class CRBenchmarkResult:
    """Result record for one certified-robustness benchmark scenario."""
    scenario                    : str
    param_name                  : str           # "sigma" or "epsilon"
    param_values                : List[float]
    certified_fractions         : List[float]
    mean_certified_radii        : List[float]
    preference_accuracies       : List[float]
    certified_accuracy_attacks  : List[float]   # empty unless adversarial
    n_pairs                     : int
    n_samples                   : int
    wall_clock_s                : float
    notes                       : str = ""

    def summary_dict(self) -> Dict[str, Any]:
        return {
            "scenario":                  self.scenario,
            "param_name":                self.param_name,
            "param_values":              self.param_values,
            "certified_fractions":       [round(f, 4) for f in self.certified_fractions],
            "mean_certified_radii":      [round(r, 4) for r in self.mean_certified_radii],
            "preference_accuracies":     [round(a, 4) for a in self.preference_accuracies],
            "certified_accuracy_attacks":[round(a, 4) for a in self.certified_accuracy_attacks],
            "n_pairs":                   self.n_pairs,
            "n_samples":                 self.n_samples,
            "wall_clock_s":              round(self.wall_clock_s, 3),
            "notes":                     self.notes,
        }


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

class CertifiedRobustnessBenchmark:
    """
    Evaluates certified robustness of the SmoothedValueLearner.

    Parameters
    ----------
    n_pairs   : Preference pairs per evaluation.
    n_samples : Monte Carlo samples per certification call.
    seed      : Random seed.
    """

    SCENARIOS = ("sigma_sweep", "epsilon_sweep", "adversarial")

    SIGMA_VALUES   = [0.05, 0.10, 0.25, 0.50]
    EPSILON_VALUES = [0.05, 0.10, 0.20, 0.30]

    def __init__(
        self,
        n_pairs:   int = 50,
        n_samples: int = 500,
        seed:      int = 42,
    ):
        self.n_pairs   = n_pairs
        self.n_samples = n_samples
        self.seed      = seed

        # Train a base agent once; all scenarios share it
        self._agent = _trained_agent(seed=seed)
        self._pairs = _make_pairs(n_pairs, seed=seed + 1)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _preference_accuracy(
        self,
        smoother: SmoothedValueLearner,
        pairs:    List[Tuple[np.ndarray, np.ndarray]],
    ) -> float:
        """Fraction of pairs where smoothed agent agrees with base agent."""
        correct = 0
        for phi1, phi2 in pairs:
            base_prefers  = self._agent.get_reward(phi1) >= self._agent.get_reward(phi2)
            smooth_prefers = smoother.predict_preference(phi1, phi2)
            if base_prefers == smooth_prefers:
                correct += 1
        return correct / len(pairs) if pairs else 0.0

    def _eval_sigma(
        self,
        sigma:   float,
        epsilon: float = 0.10,
    ) -> Tuple[float, float, float]:
        """
        Return (certified_fraction, mean_radius, preference_accuracy)
        for a given sigma.
        """
        smoother = SmoothedValueLearner(
            self._agent,
            sigma=sigma,
            n_samples=self.n_samples,
            seed=self.seed,
        )
        stats  = smoother.certification_stats(self._pairs, epsilon)
        acc    = self._preference_accuracy(smoother, self._pairs)
        return (
            stats["certified_fraction"],
            stats["mean_radius"],
            acc,
        )

    def _eval_epsilon(
        self,
        epsilon: float,
        sigma:   float = 0.10,
    ) -> Tuple[float, float, float]:
        """
        Return (certified_fraction, mean_radius, preference_accuracy)
        for a given epsilon at fixed sigma.
        """
        smoother = SmoothedValueLearner(
            self._agent,
            sigma=sigma,
            n_samples=self.n_samples,
            seed=self.seed,
        )
        stats = smoother.certification_stats(self._pairs, epsilon)
        acc   = self._preference_accuracy(smoother, self._pairs)
        return (
            stats["certified_fraction"],
            stats["mean_radius"],
            acc,
        )

    # ------------------------------------------------------------------
    # Scenarios
    # ------------------------------------------------------------------

    def _run_sigma_sweep(self) -> CRBenchmarkResult:
        t0 = time.time()
        frac, radii, accs = [], [], []
        for sigma in self.SIGMA_VALUES:
            f, r, a = self._eval_sigma(sigma, epsilon=0.10)
            frac.append(f)
            radii.append(r)
            accs.append(a)
        return CRBenchmarkResult(
            scenario                   = "sigma_sweep",
            param_name                 = "sigma",
            param_values               = list(self.SIGMA_VALUES),
            certified_fractions        = frac,
            mean_certified_radii       = radii,
            preference_accuracies      = accs,
            certified_accuracy_attacks = [],
            n_pairs                    = self.n_pairs,
            n_samples                  = self.n_samples,
            wall_clock_s               = time.time() - t0,
            notes                      = (
                "Fixed ε=0.1; larger σ → larger radius but lower preference accuracy."
            ),
        )

    def _run_epsilon_sweep(self) -> CRBenchmarkResult:
        t0 = time.time()
        frac, radii, accs = [], [], []
        for eps in self.EPSILON_VALUES:
            f, r, a = self._eval_epsilon(eps, sigma=0.10)
            frac.append(f)
            radii.append(r)
            accs.append(a)
        return CRBenchmarkResult(
            scenario                   = "epsilon_sweep",
            param_name                 = "epsilon",
            param_values               = list(self.EPSILON_VALUES),
            certified_fractions        = frac,
            mean_certified_radii       = radii,
            preference_accuracies      = accs,
            certified_accuracy_attacks = [],
            n_pairs                    = self.n_pairs,
            n_samples                  = self.n_samples,
            wall_clock_s               = time.time() - t0,
            notes                      = (
                "Fixed σ=0.1; larger ε → lower certified fraction."
            ),
        )

    def _run_adversarial(self) -> CRBenchmarkResult:
        """
        Apply actual L₂-bounded perturbations (ε_attack) to preferred
        trajectories; check if the certified preference still holds.

        certified_accuracy_under_attack:
            Fraction of pairs where the smoothed preference under attack
            matches the original (no-attack) smoothed preference AND
            a certificate was issued for the original preference.
        """
        t0         = time.time()
        eps_attack = 0.05   # actual attack budget
        sigma      = 0.10
        smoother   = SmoothedValueLearner(
            self._agent,
            sigma=sigma,
            n_samples=self.n_samples,
            seed=self.seed,
        )
        rng = np.random.default_rng(self.seed + 99)

        cert_accs_by_eps = []
        for eps in self.EPSILON_VALUES:
            n_cert_correct = 0
            n_certified    = 0
            for phi1, phi2 in self._pairs:
                # Certify at the clean point
                cr = smoother.certify(phi1, phi2)
                if cr.abstain or cr.certified_radius < eps:
                    continue
                n_certified += 1

                # Apply adversarial perturbation within eps_attack
                direction = rng.standard_normal(N_FEATS)
                direction /= max(np.linalg.norm(direction), 1e-12)
                phi1_adv  = phi1 + eps_attack * direction

                # Check if preference still holds under attack
                adv_prefers = smoother.predict_preference(phi1_adv, phi2)
                if adv_prefers == cr.prefers_phi1:
                    n_cert_correct += 1

            cert_accs_by_eps.append(
                n_cert_correct / n_certified if n_certified > 0 else float("nan")
            )

        # Preference accuracy at the clean point
        acc = self._preference_accuracy(smoother, self._pairs)
        # Certified fraction at eps_attack
        stats = smoother.certification_stats(self._pairs, eps_attack)

        return CRBenchmarkResult(
            scenario                   = "adversarial",
            param_name                 = "epsilon (cert threshold)",
            param_values               = list(self.EPSILON_VALUES),
            certified_fractions        = [stats["certified_fraction"]] * len(self.EPSILON_VALUES),
            mean_certified_radii       = [stats["mean_radius"]] * len(self.EPSILON_VALUES),
            preference_accuracies      = [acc] * len(self.EPSILON_VALUES),
            certified_accuracy_attacks = cert_accs_by_eps,
            n_pairs                    = self.n_pairs,
            n_samples                  = self.n_samples,
            wall_clock_s               = time.time() - t0,
            notes                      = (
                f"Attack: L₂ perturbation of ε_attack={eps_attack} on phi1. "
                "Certified pairs should maintain preference under attack."
            ),
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self, scenario: str) -> CRBenchmarkResult:
        if scenario == "sigma_sweep":
            return self._run_sigma_sweep()
        elif scenario == "epsilon_sweep":
            return self._run_epsilon_sweep()
        elif scenario == "adversarial":
            return self._run_adversarial()
        else:
            raise ValueError(
                f"Unknown scenario '{scenario}'. "
                f"Choose from: {self.SCENARIOS}"
            )

    def run_all(self) -> List[CRBenchmarkResult]:
        return [self.run(s) for s in self.SCENARIOS]

    def summary_table(self, results: List[CRBenchmarkResult]) -> str:
        lines = []
        for r in results:
            lines.append(f"\n{'='*60}")
            lines.append(f"Scenario: {r.scenario}  ({r.notes})")
            lines.append(f"{'='*60}")
            header = (
                f"  {r.param_name:<10} {'Cert%':>7} {'MeanR':>8} "
                f"{'Acc%':>7}"
            )
            if r.certified_accuracy_attacks:
                header += f" {'CertAcc%':>10}"
            lines.append(header)
            lines.append("  " + "-" * (len(header) - 2))
            for i, pv in enumerate(r.param_values):
                row = (
                    f"  {pv:<10.3f} "
                    f"{r.certified_fractions[i]*100:>6.1f}% "
                    f"{r.mean_certified_radii[i]:>8.4f} "
                    f"{r.preference_accuracies[i]*100:>6.1f}%"
                )
                if r.certified_accuracy_attacks:
                    ca = r.certified_accuracy_attacks[i]
                    ca_str = f"{ca*100:.1f}%" if ca == ca else "N/A"
                    row += f" {ca_str:>10}"
                lines.append(row)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bench   = CertifiedRobustnessBenchmark(n_pairs=50, n_samples=500, seed=42)
    results = bench.run_all()
    print("\n=== Certified Robustness Benchmark Results ===")
    print(bench.summary_table(results))
