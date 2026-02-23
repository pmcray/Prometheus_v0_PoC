"""
OOD Robustness Benchmark — Prometheus v0.97

Evaluates OOD detectors across three scenario classes:

  in_distribution   — samples drawn from the same distribution as the training set
  mild_shift        — features shifted by 2–4 standard deviations
  severe_shift      — features shifted by 6+ standard deviations or from a
                      completely different domain (e.g. ARC grid stats vs.
                      OpenRA game-state features)

For each scenario the benchmark reports:
  - True Positive Rate (TPR): fraction of OOD inputs correctly flagged
  - False Positive Rate (FPR): fraction of in-distribution inputs incorrectly flagged
  - AUROC: area under the ROC curve (threshold-free summary)
  - Mean OOD score for each class

Public API
----------
OODBenchmark.run(detector) → OODBenchmarkResult
OODBenchmark.run_all(detectors) → List[OODBenchmarkResult]
generate_in_distribution(feature_size, n) → np.ndarray
generate_ood_mild(in_dist_features, n) → np.ndarray
generate_ood_severe(feature_size, n) → np.ndarray
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from prometheus.ood_detection import (
    BaseOODDetector,
    EnsembleOODDetector,
    MahalanobisOODDetector,
    ReconstructionOODDetector,
    SafeMode,
    SafeModeProtocol,
    create_ood_detector,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data generators
# ---------------------------------------------------------------------------

def generate_in_distribution(
    feature_size: int,
    n:            int = 200,
    seed:         int = 42,
    mean:         Optional[np.ndarray] = None,
    cov_scale:    float = 1.0,
) -> np.ndarray:
    """
    Draw N samples from a multivariate Gaussian (in-distribution).

    Args:
        feature_size: Dimension of each feature vector.
        n:            Number of samples.
        seed:         RNG seed.
        mean:         Optional mean vector; defaults to zeros.
        cov_scale:    Scale factor for the covariance matrix.

    Returns:
        Array of shape (N, feature_size).
    """
    rng  = np.random.default_rng(seed)
    mu   = mean if mean is not None else np.zeros(feature_size)
    # Random positive-definite covariance: A @ A.T / feature_size
    A    = rng.standard_normal((feature_size, feature_size))
    cov  = (A @ A.T) / feature_size * cov_scale
    return rng.multivariate_normal(mu, cov, size=n)


def generate_ood_mild(
    in_dist_features: np.ndarray,
    n:                int = 100,
    shift_sigma:      float = 3.0,
    seed:             int = 99,
) -> np.ndarray:
    """
    Generate mildly OOD samples: in-distribution mean + a shift of
    `shift_sigma` × per-feature standard deviation in a random direction.

    Args:
        in_dist_features: Training features (N, D).
        n:                Number of OOD samples to generate.
        shift_sigma:      How many σ to shift in a random direction.
        seed:             RNG seed.

    Returns:
        Array of shape (n, D).
    """
    rng    = np.random.default_rng(seed)
    mu     = in_dist_features.mean(axis=0)
    sigma  = in_dist_features.std(axis=0) + 1e-8
    D      = in_dist_features.shape[1]

    # Random unit direction
    direction = rng.standard_normal(D)
    direction /= np.linalg.norm(direction) + 1e-8

    # Shift the mean in that direction
    shifted_mu = mu + shift_sigma * sigma * direction

    # Add residual noise at the same scale as the training data
    noise = rng.standard_normal((n, D)) * sigma * 0.5
    return shifted_mu[None, :] + noise


def generate_ood_severe(
    feature_size: int,
    n:            int = 100,
    seed:         int = 777,
    strategy:     str = "uniform_far",
) -> np.ndarray:
    """
    Generate severely OOD samples using one of several strategies.

    Args:
        feature_size: Feature dimension.
        n:            Number of samples.
        seed:         RNG seed.
        strategy:     "uniform_far" — large uniform noise far from origin;
                      "constant"    — all features set to a constant value;
                      "zeros"       — all-zero vectors;
                      "adversarial" — maximally distant from unit hypercube.

    Returns:
        Array of shape (n, feature_size).
    """
    rng = np.random.default_rng(seed)

    if strategy == "uniform_far":
        return rng.uniform(10.0, 20.0, size=(n, feature_size)) * rng.choice([-1, 1], size=(n, feature_size))
    elif strategy == "constant":
        val = rng.uniform(5.0, 15.0)
        return np.full((n, feature_size), val)
    elif strategy == "zeros":
        return np.zeros((n, feature_size))
    elif strategy == "adversarial":
        base = rng.standard_normal((n, feature_size))
        norms = np.linalg.norm(base, axis=1, keepdims=True) + 1e-8
        return base / norms * rng.uniform(8.0, 15.0, size=(n, 1))
    else:
        raise ValueError(f"Unknown strategy '{strategy}'")


# ---------------------------------------------------------------------------
# Benchmark result
# ---------------------------------------------------------------------------

@dataclass
class ScenarioResult:
    """Per-scenario metrics for one detector."""
    scenario:    str           # "in_distribution", "mild_shift", "severe_shift"
    n_samples:   int
    mean_score:  float
    std_score:   float
    ood_rate:    float         # Fraction flagged as OOD (threshold = 2.0σ)
    mode_counts: Dict[str, int] = field(default_factory=dict)


@dataclass
class OODBenchmarkResult:
    """Full benchmark result for one detector."""
    detector_name:  str
    feature_size:   int
    n_train:        int
    scenarios:      Dict[str, ScenarioResult]
    tpr:            float      # True Positive Rate  (mild + severe OOD flagged)
    fpr:            float      # False Positive Rate (in-dist incorrectly flagged)
    auroc:          float      # Area under the ROC curve
    wall_clock_s:   float

    def summary_line(self) -> str:
        return (
            f"{self.detector_name:<22} "
            f"AUROC={self.auroc:.3f}  "
            f"TPR={self.tpr:.1%}  "
            f"FPR={self.fpr:.1%}  "
            f"({self.wall_clock_s:.2f}s)"
        )


# ---------------------------------------------------------------------------
# Benchmark class
# ---------------------------------------------------------------------------

class OODBenchmark:
    """
    Evaluates OOD detector performance on synthetic datasets.

    Three scenario classes are generated:
      - in_distribution (200 samples, same dist as training)
      - mild_shift      (100 samples, 3σ shift from in-dist mean)
      - severe_shift    (100 samples, uniform far from origin)

    Metrics:
      - TPR  = (mild_ood_flagged + severe_ood_flagged) / (n_mild + n_severe)
      - FPR  = in_dist_flagged / n_in_dist
      - AUROC computed via trapezoidal rule over 50 thresholds

    Args:
        feature_size:  Feature dimensionality.
        n_train:       Number of training samples used to fit each detector.
        n_in_dist:     Number of in-distribution evaluation samples.
        n_mild:        Number of mild OOD samples.
        n_severe:      Number of severe OOD samples.
        mild_sigma:    Sigma shift for mild OOD generation.
        seed:          Base RNG seed.
    """

    def __init__(
        self,
        feature_size: int = 6,
        n_train:      int = 200,
        n_in_dist:    int = 200,
        n_mild:       int = 100,
        n_severe:     int = 100,
        mild_sigma:   float = 3.0,
        seed:         int = 42,
    ):
        self.feature_size = feature_size
        self.n_train      = n_train
        self.n_in_dist    = n_in_dist
        self.n_mild       = n_mild
        self.n_severe     = n_severe
        self.mild_sigma   = mild_sigma
        self.seed         = seed

        # Generate training set once
        self._train_features = generate_in_distribution(
            feature_size, n_train, seed=seed
        )

        # Generate evaluation sets (fixed, shared across all detectors)
        self._eval_in_dist = generate_in_distribution(
            feature_size, n_in_dist, seed=seed + 1
        )
        self._eval_mild = generate_ood_mild(
            self._train_features, n_mild,
            shift_sigma=mild_sigma, seed=seed + 2
        )
        self._eval_severe = generate_ood_severe(
            feature_size, n_severe, seed=seed + 3
        )

    # ------------------------------------------------------------------
    # Run one detector
    # ------------------------------------------------------------------

    def run(
        self,
        detector,
        ood_threshold: float = 2.0,
        verbose:       bool  = True,
    ) -> OODBenchmarkResult:
        """
        Fit the detector on training data and evaluate it on all scenarios.

        Args:
            detector:      Un-fitted detector instance.
            ood_threshold: Normalised score threshold for binary OOD decision.
            verbose:       Print per-scenario progress.

        Returns:
            OODBenchmarkResult.
        """
        t0 = time.time()
        detector.fit(self._train_features)

        if verbose:
            logger.info("Evaluating %s ...", getattr(detector, 'name', type(detector).__name__))

        scenarios: Dict[str, ScenarioResult] = {}

        eval_sets = [
            ("in_distribution", self._eval_in_dist,  False),
            ("mild_shift",      self._eval_mild,      True),
            ("severe_shift",    self._eval_severe,    True),
        ]

        all_scores:  List[float] = []
        all_labels:  List[int]   = []   # 1 = OOD, 0 = in-dist

        in_dist_flagged = 0
        ood_total       = 0
        ood_flagged     = 0

        for scenario_name, data, is_ood_class in eval_sets:
            scores     = []
            mode_counts: Dict[str, int] = {m.value: 0 for m in SafeMode}

            for x in data:
                ood_obj = detector.evaluate(x)
                s       = ood_obj.normalised
                scores.append(s)
                all_scores.append(s)
                all_labels.append(1 if is_ood_class else 0)
                mode_counts[ood_obj.safe_mode.value] += 1

            flagged = sum(1 for s in scores if s > ood_threshold)
            rate    = flagged / len(scores) if scores else 0.0

            if is_ood_class:
                ood_total   += len(scores)
                ood_flagged += flagged
            else:
                in_dist_flagged += flagged

            scenarios[scenario_name] = ScenarioResult(
                scenario    = scenario_name,
                n_samples   = len(scores),
                mean_score  = float(np.mean(scores)),
                std_score   = float(np.std(scores)),
                ood_rate    = rate,
                mode_counts = mode_counts,
            )

        # Global metrics
        tpr   = ood_flagged / ood_total if ood_total > 0 else 0.0
        fpr   = in_dist_flagged / self.n_in_dist if self.n_in_dist > 0 else 0.0
        auroc = self._compute_auroc(np.array(all_scores), np.array(all_labels))

        result = OODBenchmarkResult(
            detector_name = getattr(detector, 'name', type(detector).__name__),
            feature_size  = self.feature_size,
            n_train       = self.n_train,
            scenarios     = scenarios,
            tpr           = tpr,
            fpr           = fpr,
            auroc         = auroc,
            wall_clock_s  = time.time() - t0,
        )

        if verbose:
            print(f"  {result.summary_line()}")

        return result

    # ------------------------------------------------------------------
    # Run all detectors
    # ------------------------------------------------------------------

    def run_all(
        self,
        detectors:     Optional[List] = None,
        ood_threshold: float = 2.0,
        verbose:       bool  = True,
    ) -> List[OODBenchmarkResult]:
        """
        Run the benchmark for multiple detectors.

        Args:
            detectors:     List of un-fitted detector instances.
                           Defaults to one of each type.
            ood_threshold: Normalised score threshold for binary OOD decision.
            verbose:       Print progress and summary table.

        Returns:
            List of OODBenchmarkResult, sorted by AUROC descending.
        """
        if detectors is None:
            detectors = [
                MahalanobisOODDetector(self.feature_size),
                ReconstructionOODDetector(self.feature_size, epochs=150),
                EnsembleOODDetector(self.feature_size, epochs=150),
            ]

        if verbose:
            print(f"\nOOD Benchmark  (feature_size={self.feature_size}, "
                  f"n_train={self.n_train})")
            print("=" * 65)

        results = [
            self.run(det, ood_threshold=ood_threshold, verbose=verbose)
            for det in detectors
        ]
        results.sort(key=lambda r: r.auroc, reverse=True)

        if verbose:
            self._print_summary(results)

        return results

    # ------------------------------------------------------------------
    # AUROC helper
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_auroc(scores: np.ndarray, labels: np.ndarray) -> float:
        """
        Compute AUROC via trapezoidal integration over 50 thresholds.

        Args:
            scores: 1-D array of OOD scores.
            labels: 1-D binary array (1 = OOD, 0 = in-dist).

        Returns:
            AUROC in [0, 1].
        """
        thresholds = np.linspace(scores.min(), scores.max(), 50)
        tprs = []
        fprs = []
        pos  = labels == 1
        neg  = labels == 0
        n_pos = pos.sum()
        n_neg = neg.sum()

        if n_pos == 0 or n_neg == 0:
            return 0.5

        for t in thresholds:
            pred = scores >= t
            tprs.append(pred[pos].mean())
            fprs.append(pred[neg].mean())

        # Add corner points and sort by FPR
        fprs_arr = np.array([1.0] + fprs + [0.0])
        tprs_arr = np.array([1.0] + tprs + [0.0])
        order    = np.argsort(fprs_arr)
        return float(np.trapz(tprs_arr[order], fprs_arr[order]))

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def _print_summary(self, results: List[OODBenchmarkResult]) -> None:
        print("\nSummary Table:")
        print(f"  {'Detector':<22} {'AUROC':>7} {'TPR':>7} {'FPR':>7} "
              f"{'InDist↑':>9} {'Mild↑':>8} {'Severe↑':>9} {'Time':>7}")
        print("  " + "-" * 75)
        for r in results:
            in_d  = r.scenarios['in_distribution'].ood_rate
            mild  = r.scenarios['mild_shift'].ood_rate
            sev   = r.scenarios['severe_shift'].ood_rate
            print(
                f"  {r.detector_name:<22} {r.auroc:>7.3f} {r.tpr:>7.1%} "
                f"{r.fpr:>7.1%} {in_d:>9.1%} {mild:>8.1%} {sev:>9.1%} "
                f"{r.wall_clock_s:>6.1f}s"
            )

    def print_scenario_detail(self, result: OODBenchmarkResult) -> None:
        """Print per-scenario breakdown for a single result."""
        print(f"\n{result.detector_name} — Scenario Detail")
        print("-" * 55)
        for name, sr in result.scenarios.items():
            print(f"  {name}  (n={sr.n_samples})")
            print(f"    OOD rate:   {sr.ood_rate:.1%}")
            print(f"    Score:      mean={sr.mean_score:.3f}  std={sr.std_score:.3f}")
            print(f"    Modes:      {sr.mode_counts}")


# ---------------------------------------------------------------------------
# Scenario generators for specific Prometheus domains
# ---------------------------------------------------------------------------

def gridworld_in_distribution(n: int = 200, seed: int = 42) -> np.ndarray:
    """
    Generate in-distribution GridWorld feature vectors (6-D).

    Features: row_norm, col_norm, dist_norm, wall_clearance, goal_flag, bias.
    Matches the feature space used by ValueLearningAgent / benchmarks/value_learning_benchmark.py.
    """
    rng = np.random.default_rng(seed)
    rows  = rng.uniform(0.0, 1.0, n)
    cols  = rng.uniform(0.0, 1.0, n)
    dists = np.sqrt((rows - 1.0)**2 + (cols - 1.0)**2) / np.sqrt(2)  # normalised dist to goal
    walls = rng.uniform(0.0, 1.0, n)
    goals = (dists < 0.05).astype(float)
    bias  = np.ones(n)
    return np.stack([rows, cols, dists, walls, goals, bias], axis=1)


def openra_in_distribution(n: int = 200, seed: int = 42) -> np.ndarray:
    """
    Generate in-distribution OpenRA game-state feature vectors (20-D).

    Matches the 20-D normalised observation space of OpenRAEnvironment.
    """
    from prometheus.openra_environment import OpenRAEnvironment
    env   = OpenRAEnvironment(difficulty='easy', seed=seed)
    feats = []
    rng   = np.random.default_rng(seed)
    for _ in range(n):
        state = env.reset()
        # Take a few random steps to get a more varied state
        for _ in range(rng.integers(0, 50)):
            action = rng.integers(0, 15)
            state, _, done, _ = env.step(int(action))
            if done:
                break
        feats.append(env.get_observation())
    return np.array(feats)


def arc_in_distribution(n: int = 200, seed: int = 42) -> np.ndarray:
    """
    Generate in-distribution ARC grid summary feature vectors (8-D).

    Features: n_colors, n_nonzero_norm, symmetry_h, symmetry_v,
              aspect_ratio, mean_color_norm, n_objects_norm, size_ratio.
    These summarise ARC input grids within the typical training distribution.
    """
    rng = np.random.default_rng(seed)
    n_colors       = rng.integers(2, 5, n).astype(float) / 9.0
    n_nonzero      = rng.uniform(0.1, 0.6, n)
    symmetry_h     = rng.choice([0.0, 1.0], n, p=[0.6, 0.4])
    symmetry_v     = rng.choice([0.0, 1.0], n, p=[0.6, 0.4])
    aspect_ratio   = rng.uniform(0.5, 2.0, n) / 2.0
    mean_color     = rng.uniform(0.1, 0.5, n)
    n_objects      = rng.integers(1, 5, n).astype(float) / 9.0
    size_ratio     = rng.uniform(0.8, 1.2, n)
    return np.stack([n_colors, n_nonzero, symmetry_h, symmetry_v,
                     aspect_ratio, mean_color, n_objects, size_ratio], axis=1)


# ---------------------------------------------------------------------------
# Quick evaluation helper
# ---------------------------------------------------------------------------

def run_quick_ood_test(
    detector_type: str = "mahalanobis",
    feature_size:  int = 6,
    n_train:       int = 200,
    seed:          int = 42,
    verbose:       bool = True,
) -> OODBenchmarkResult:
    """
    Convenience function: generate data, fit one detector, return result.

    Args:
        detector_type: "mahalanobis" | "reconstruction" | "ensemble"
        feature_size:  Feature dimensionality.
        n_train:       Training set size.
        seed:          RNG seed.
        verbose:       Print result.

    Returns:
        OODBenchmarkResult.
    """
    bench    = OODBenchmark(feature_size=feature_size, n_train=n_train, seed=seed)
    detector = create_ood_detector(detector_type, feature_size)
    return bench.run(detector, verbose=verbose)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)

    print("OOD Benchmark — Prometheus v0.97")
    print("=" * 65)

    for fsize, domain in [(6, "GridWorld"), (8, "ARC"), (20, "OpenRA")]:
        print(f"\nDomain: {domain}  (feature_size={fsize})")
        bench = OODBenchmark(feature_size=fsize, n_train=200, seed=42)
        bench.run_all(verbose=True)
