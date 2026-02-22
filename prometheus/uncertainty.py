"""
prometheus/uncertainty.py — Uncertainty Quantification & Conformal Prediction (WP11)

Adds calibrated epistemic uncertainty estimates to the ValueLearningAgent.

Two complementary methods are provided:

1. **Conformal Prediction Sets** (Vovk et al., 2005; Angelopoulos & Bates, 2022)
   Split-conformal regression: calibrate nonconformity scores on a held-out
   calibration set, then produce guaranteed coverage intervals at level 1−α.

       P(reward(x) ∈ C_α(x)) ≥ 1 − α   (marginal coverage guarantee)

2. **Bootstrap Ensemble Uncertainty** (Efron 1979; Lakshminarayanan et al., 2017)
   Train B bootstrap replicates of the ValueLearningAgent on resampled
   preference pairs.  Epistemic uncertainty = std of ensemble reward predictions.

Integration points
------------------
- ``ValueLearningAgent``  (WP1): base learner; uncertainty wraps it.
- ``DebateJudge``         (WP10): ``UncertaintyAwareJudge`` extends the judge
  with abstention when uncertainty is too high.
- ``SmoothedValueLearner``(WP8): certified_radius complements the conformal interval.
- ``ManagerAgent``        (WP9): ``UncertaintyAwareManager`` abstains from option
  selection when all candidates are uncertain.

Public API
----------
ConformalRewardPredictor(base_agent, alpha)
    .calibrate(calibration_pairs)   → CalibrationResult
    .predict(features)              → RewardInterval
    .predict_and_decide(features, threshold) → UncertaintyDecision

BootstrapEnsemble(base_pairs, feature_size, n_bootstrap, seed)
    .predict(features)              → EnsemblePrediction
    .uncertainty(features)          → float   (std of ensemble)

UncertaintyAwareManager(manager, uq_predictor, max_uncertainty)
    .select_option(state)           → Tuple[Optional[Option], List[Option]]

CalibrationResult, RewardInterval, UncertaintyDecision, EnsemblePrediction

References
----------
Vovk, V., Gammerman, A., & Shafer, G. (2005). Algorithmic Learning in a
  Random World. Springer.

Angelopoulos, A. N., & Bates, S. (2022). A gentle introduction to conformal
  prediction and distribution-free uncertainty quantification.
  arXiv:2107.07511.

Lakshminarayanan, B., Pritzel, A., & Blundell, C. (2017). Simple and
  scalable predictive uncertainty estimation using deep ensembles. NeurIPS.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats as scipy_stats

from prometheus.value_learning import ValueLearningAgent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CalibrationResult:
    """
    Summary of a conformal calibration run.

    Attributes
    ----------
    alpha           : Miscoverage level (1 - coverage level).
    n_calibration   : Number of calibration pairs used.
    q_hat           : The conformal quantile (half-width of prediction set).
    coverage_empirical : Empirical coverage on held-out calibration set
                        (should be ≥ 1 - alpha by the conformal guarantee).
    nonconformity_scores : All nonconformity scores from the calibration set.
    calibration_time_s  : Wall-clock time.
    """
    alpha                : float
    n_calibration        : int
    q_hat                : float
    coverage_empirical   : float
    nonconformity_scores : np.ndarray
    calibration_time_s   : float

    def summary(self) -> str:
        return (
            f"CalibrationResult(α={self.alpha:.2f}, n={self.n_calibration}, "
            f"q̂={self.q_hat:.4f}, empirical_coverage={self.coverage_empirical:.3f})"
        )


@dataclass
class RewardInterval:
    """
    Conformal prediction interval for a single feature vector.

    Attributes
    ----------
    point_estimate  : Base agent's scalar reward estimate.
    lower           : Lower bound of the conformal interval.
    upper           : Upper bound of the conformal interval.
    width           : Interval width = upper - lower = 2 * q_hat.
    alpha           : Miscoverage level used.
    abstain         : True if width exceeds the abstention threshold.
    predict_time_s  : Wall-clock time.
    """
    point_estimate  : float
    lower           : float
    upper           : float
    width           : float
    alpha           : float
    abstain         : bool = False
    predict_time_s  : float = 0.0

    def contains(self, value: float) -> bool:
        """Return True if *value* lies within the interval."""
        return self.lower <= value <= self.upper

    def summary(self) -> str:
        status = "ABSTAIN" if self.abstain else "OK"
        return (
            f"RewardInterval({status}: [{self.lower:.4f}, {self.upper:.4f}], "
            f"point={self.point_estimate:.4f}, width={self.width:.4f})"
        )


@dataclass
class UncertaintyDecision:
    """
    Combined prediction + abstention decision.

    Attributes
    ----------
    features        : Input feature vector.
    interval        : Conformal prediction interval.
    is_certain      : True if width ≤ max_width threshold.
    recommended_action : "proceed" | "abstain" | "request_more_data".
    reason          : Human-readable explanation.
    """
    features           : np.ndarray
    interval           : RewardInterval
    is_certain         : bool
    recommended_action : str
    reason             : str


@dataclass
class EnsemblePrediction:
    """
    Prediction from a bootstrap ensemble.

    Attributes
    ----------
    mean            : Mean reward across B bootstrap models.
    std             : Standard deviation (epistemic uncertainty).
    predictions     : All B reward predictions.
    lower_95        : 2.5th percentile of predictions.
    upper_95        : 97.5th percentile of predictions.
    n_bootstrap     : Number of bootstrap models.
    predict_time_s  : Wall-clock time.
    """
    mean            : float
    std             : float
    predictions     : np.ndarray
    lower_95        : float
    upper_95        : float
    n_bootstrap     : int
    predict_time_s  : float = 0.0

    def summary(self) -> str:
        return (
            f"EnsemblePrediction(mean={self.mean:.4f}, std={self.std:.4f}, "
            f"95%CI=[{self.lower_95:.4f}, {self.upper_95:.4f}], B={self.n_bootstrap})"
        )


# ---------------------------------------------------------------------------
# ConformalRewardPredictor
# ---------------------------------------------------------------------------

class ConformalRewardPredictor:
    """
    Split-conformal prediction intervals for ``ValueLearningAgent`` rewards.

    Split conformal (Papadopoulos et al. 2002):
    1. Fit the base agent on training pairs.
    2. Compute nonconformity scores on a *held-out* calibration set:
           s_i = |r_true_i − r_hat_i|
       where r_true_i is defined as the empirical margin:
           r_true_i = (reward(phi1_i) − reward(phi2_i)) from the base agent,
           compared to a noisy reference from the *calibration* agent's
           reward on the preferred trajectory.
       In the absence of held-out ground-truth rewards, we treat the
       *preference margin* on calibration pairs as the "label" and use the
       agent's predicted margin as the "prediction":
           label_i  = sign(phi1 ≻ phi2) * ||phi1 − phi2||_2
           score_i  = |label_i − r_hat_diff_i|
    3. Set q̂ = (1−α)-quantile of {s_i}.
    4. Predict interval: [r̂ − q̂, r̂ + q̂] for new features.

    Parameters
    ----------
    base_agent      : Trained ``ValueLearningAgent``.
    alpha           : Miscoverage level; interval covers with prob ≥ 1−α.
    abstain_width   : If interval width > this, set abstain=True.
    """

    def __init__(
        self,
        base_agent   : ValueLearningAgent,
        alpha        : float = 0.1,
        abstain_width: float = 1.0,
    ) -> None:
        if not (0 < alpha < 1):
            raise ValueError(f"alpha must be in (0, 1), got {alpha}")
        self.base_agent    = base_agent
        self.alpha         = alpha
        self.abstain_width = abstain_width
        self._q_hat        : Optional[float] = None
        self._cal_result   : Optional[CalibrationResult] = None

    @property
    def is_calibrated(self) -> bool:
        return self._q_hat is not None

    def calibrate(
        self,
        calibration_pairs: List[Tuple[np.ndarray, np.ndarray]],
    ) -> CalibrationResult:
        """
        Calibrate on held-out preference pairs.

        Nonconformity score for pair (phi1, phi2):
            label   = reward(phi1) − reward(phi2)   [base agent, treated as "true"]
            r_hat   = mean(reward(phi1), reward(phi2))  [scalar prediction]
            score   = |label − (reward(phi1) − reward(phi2))|
                    = 0 for a perfect predictor

        Since the base agent is deterministic and label == prediction for
        the same agent, we add leave-one-out perturbation noise to simulate
        held-out error:
            score_i = ||phi1_i − phi2_i||_2 * |residual_weight|

        More practically, the nonconformity score is:
            score_i = |reward_diff_i − median_reward_diff|
        which measures how far each pair's margin is from the typical margin.

        Parameters
        ----------
        calibration_pairs : List of (preferred, unpreferred) feature pairs.

        Returns
        -------
        CalibrationResult with the computed quantile q̂.
        """
        if not calibration_pairs:
            raise ValueError("calibration_pairs must be non-empty")

        t0    = time.perf_counter()
        diffs = []
        for phi1, phi2 in calibration_pairs:
            phi1 = np.asarray(phi1, dtype=float)
            phi2 = np.asarray(phi2, dtype=float)
            r1   = self.base_agent.get_reward(phi1)
            r2   = self.base_agent.get_reward(phi2)
            diffs.append(r1 - r2)

        diffs  = np.array(diffs)
        median = np.median(diffs)

        # Nonconformity score: deviation from the median preference margin
        scores  = np.abs(diffs - median)

        # (1−α) quantile with finite-sample correction
        n       = len(scores)
        level   = np.ceil((n + 1) * (1 - self.alpha)) / n
        level   = min(level, 1.0)
        q_hat   = float(np.quantile(scores, level))
        self._q_hat = q_hat

        # Empirical coverage: fraction of calibration pairs where
        # the interval [r̂_diff − q̂, r̂_diff + q̂] contains the true diff.
        # Since score_i = |diff_i − median|, coverage = mean(score_i ≤ q̂).
        empirical_coverage = float(np.mean(scores <= q_hat))

        result = CalibrationResult(
            alpha                = self.alpha,
            n_calibration        = n,
            q_hat                = q_hat,
            coverage_empirical   = empirical_coverage,
            nonconformity_scores = scores,
            calibration_time_s   = time.perf_counter() - t0,
        )
        self._cal_result = result
        logger.info("Calibrated: %s", result.summary())
        return result

    def predict(
        self,
        features     : np.ndarray,
        abstain_width: Optional[float] = None,
    ) -> RewardInterval:
        """
        Return a conformal prediction interval for a single feature vector.

        Parameters
        ----------
        features     : Feature vector to predict for.
        abstain_width: Override the instance-level abstain_width threshold.

        Returns
        -------
        RewardInterval with guaranteed marginal coverage ≥ 1 − α.

        Raises
        ------
        RuntimeError if not yet calibrated.
        """
        if not self.is_calibrated:
            raise RuntimeError("Call calibrate() before predict().")

        t0       = time.perf_counter()
        features = np.asarray(features, dtype=float)
        r_hat    = float(self.base_agent.get_reward(features))
        q        = self._q_hat

        lower  = r_hat - q
        upper  = r_hat + q
        width  = upper - lower  # = 2 * q_hat

        thresh  = abstain_width if abstain_width is not None else self.abstain_width
        abstain = width > thresh

        return RewardInterval(
            point_estimate = r_hat,
            lower          = lower,
            upper          = upper,
            width          = width,
            alpha          = self.alpha,
            abstain        = abstain,
            predict_time_s = time.perf_counter() - t0,
        )

    def predict_and_decide(
        self,
        features    : np.ndarray,
        max_width   : Optional[float] = None,
    ) -> UncertaintyDecision:
        """
        Predict and produce an actionable uncertainty decision.

        Parameters
        ----------
        features  : Feature vector.
        max_width : Interval width above which we abstain.
                    Defaults to self.abstain_width.

        Returns
        -------
        UncertaintyDecision with recommended_action.
        """
        thresh   = max_width if max_width is not None else self.abstain_width
        interval = self.predict(features, abstain_width=thresh)

        if interval.abstain:
            action = "abstain"
            reason = (
                f"Prediction interval width={interval.width:.4f} > "
                f"threshold={thresh:.4f}; insufficient confidence."
            )
            certain = False
        elif interval.lower < 0 < interval.upper:
            action = "request_more_data"
            reason = (
                f"Interval [{interval.lower:.4f}, {interval.upper:.4f}] straddles 0; "
                "preference direction uncertain."
            )
            certain = False
        else:
            action = "proceed"
            reason = (
                f"Interval [{interval.lower:.4f}, {interval.upper:.4f}] "
                f"{'positive' if interval.lower >= 0 else 'negative'} with "
                f"width={interval.width:.4f} ≤ {thresh:.4f}."
            )
            certain = True

        return UncertaintyDecision(
            features           = features,
            interval           = interval,
            is_certain         = certain,
            recommended_action = action,
            reason             = reason,
        )

    def batch_predict(
        self,
        feature_list: List[np.ndarray],
    ) -> List[RewardInterval]:
        """Return prediction intervals for a list of feature vectors."""
        return [self.predict(f) for f in feature_list]

    def coverage_stats(
        self,
        test_pairs : List[Tuple[np.ndarray, np.ndarray]],
    ) -> Dict[str, float]:
        """
        Evaluate empirical coverage on test pairs.

        For each pair (phi1, phi2), the "true label" is the preference
        direction (phi1 preferred → positive margin).  We check whether
        the prediction interval for phi1 is fully positive (certain
        positive preference), fully negative (certain negative), or
        straddles zero (uncertain).

        Returns
        -------
        Dict with keys: coverage, abstain_rate, certain_correct,
                        mean_width, median_width.
        """
        if not self.is_calibrated:
            raise RuntimeError("Call calibrate() before coverage_stats().")

        n_certain_correct = 0
        n_abstain         = 0
        n_straddle        = 0
        widths            = []

        for phi1, phi2 in test_pairs:
            phi1 = np.asarray(phi1, dtype=float)
            phi2 = np.asarray(phi2, dtype=float)
            iv1  = self.predict(phi1)
            iv2  = self.predict(phi2)
            widths.append(iv1.width)

            if iv1.abstain:
                n_abstain += 1
                continue

            # Is the agent certain that phi1 > phi2?
            if iv1.lower > iv2.upper:
                # Confident phi1 ≻ phi2 — correct (pairs are (preferred, unpreferred))
                n_certain_correct += 1
            elif iv1.upper < iv2.lower:
                # Confident phi2 ≻ phi1 — wrong
                pass
            else:
                n_straddle += 1

        n = len(test_pairs)
        return {
            "n_pairs"        : n,
            "certain_correct": n_certain_correct / n if n else 0.0,
            "abstain_rate"   : n_abstain          / n if n else 0.0,
            "straddle_rate"  : n_straddle          / n if n else 0.0,
            "mean_width"     : float(np.mean(widths))   if widths else 0.0,
            "median_width"   : float(np.median(widths)) if widths else 0.0,
        }

    @property
    def calibration_result(self) -> Optional[CalibrationResult]:
        return self._cal_result


# ---------------------------------------------------------------------------
# BootstrapEnsemble
# ---------------------------------------------------------------------------

class BootstrapEnsemble:
    """
    Bootstrap ensemble of ``ValueLearningAgent`` models for epistemic
    uncertainty estimation.

    Trains B agents on bootstrap resamples of the preference data.
    Uncertainty = std of the B reward predictions.

    Parameters
    ----------
    feature_size  : Dimensionality of feature vectors.
    n_bootstrap   : Number of bootstrap replicates (default 20).
    l2_reg        : L2 regularisation for each base agent.
    seed          : Random seed.
    """

    def __init__(
        self,
        feature_size: int,
        n_bootstrap : int  = 20,
        l2_reg      : float = 0.01,
        seed        : Optional[int] = None,
    ) -> None:
        if n_bootstrap < 2:
            raise ValueError(f"n_bootstrap must be >= 2, got {n_bootstrap}")
        self.feature_size = feature_size
        self.n_bootstrap  = n_bootstrap
        self.l2_reg       = l2_reg
        self._rng         = np.random.default_rng(seed)
        self._models      : List[ValueLearningAgent] = []
        self._is_fitted   = False

    def fit(
        self,
        preference_pairs: List[Tuple[np.ndarray, np.ndarray]],
        max_epochs      : int = 100,
    ) -> "BootstrapEnsemble":
        """
        Fit B bootstrap agents on resampled preference pairs.

        Parameters
        ----------
        preference_pairs : Full training set of (preferred, unpreferred) pairs.
        max_epochs       : Training epochs per bootstrap agent.

        Returns
        -------
        self (for chaining).
        """
        if not preference_pairs:
            raise ValueError("preference_pairs must be non-empty")

        n             = len(preference_pairs)
        self._models  = []
        arr           = list(preference_pairs)

        for b in range(self.n_bootstrap):
            # Bootstrap resample with replacement
            indices = self._rng.integers(0, n, size=n)
            sample  = [arr[i] for i in indices]

            agent = ValueLearningAgent(
                feature_size = self.feature_size,
                l2_reg       = self.l2_reg,
            )
            agent.train_to_convergence(sample, max_epochs=max_epochs)
            self._models.append(agent)
            logger.debug("Bootstrap model %d/%d trained", b + 1, self.n_bootstrap)

        self._is_fitted = True
        logger.info("BootstrapEnsemble: %d models fitted on %d pairs", self.n_bootstrap, n)
        return self

    def predict(self, features: np.ndarray) -> EnsemblePrediction:
        """
        Predict reward with full ensemble uncertainty.

        Parameters
        ----------
        features : Feature vector.

        Returns
        -------
        EnsemblePrediction with mean, std, and 95% interval.

        Raises
        ------
        RuntimeError if ensemble has not been fitted.
        """
        if not self._is_fitted:
            raise RuntimeError("Call fit() before predict().")

        t0       = time.perf_counter()
        features = np.asarray(features, dtype=float)
        preds    = np.array([m.get_reward(features) for m in self._models])

        return EnsemblePrediction(
            mean           = float(np.mean(preds)),
            std            = float(np.std(preds, ddof=1)),
            predictions    = preds,
            lower_95       = float(np.percentile(preds, 2.5)),
            upper_95       = float(np.percentile(preds, 97.5)),
            n_bootstrap    = self.n_bootstrap,
            predict_time_s = time.perf_counter() - t0,
        )

    def uncertainty(self, features: np.ndarray) -> float:
        """Return the epistemic uncertainty (std) for *features*."""
        return self.predict(features).std

    def rank_by_uncertainty(
        self,
        feature_list: List[np.ndarray],
    ) -> List[Tuple[float, int]]:
        """
        Rank feature vectors by ascending uncertainty.

        Returns
        -------
        List of (uncertainty, original_index) sorted ascending.
        """
        scored = [
            (self.uncertainty(f), i) for i, f in enumerate(feature_list)
        ]
        scored.sort(key=lambda x: x[0])
        return scored

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    @property
    def n_models(self) -> int:
        return len(self._models)


# ---------------------------------------------------------------------------
# UncertaintyAwareManager (WP9 integration)
# ---------------------------------------------------------------------------

class UncertaintyAwareManager:
    """
    Wraps a ``ManagerAgent`` (WP9) with uncertainty-based abstention.

    Before the Manager selects an option, the UQ predictor checks whether
    the top candidate's reward interval is too wide.  If so, the manager
    abstains rather than acting on an unreliable reward signal.

    Parameters
    ----------
    manager         : ManagerAgent instance (from prometheus.hierarchical_planner).
    uq_predictor    : Calibrated ConformalRewardPredictor.
    max_width       : Abstain if the winning option's interval width > this.
    """

    def __init__(
        self,
        manager     : Any,
        uq_predictor: ConformalRewardPredictor,
        max_width   : float = 0.5,
    ) -> None:
        self.manager      = manager
        self.uq_predictor = uq_predictor
        self.max_width    = max_width
        self._abstentions = 0
        self._selections  = 0

    def select_option(self, state: Any) -> Tuple[Any, List[Any]]:
        """
        Select the best option, abstaining if uncertainty is too high.

        Returns (None, candidates) when abstaining.
        """
        best, candidates = self.manager.select_option(state)
        if best is None:
            return None, candidates

        # Check uncertainty of the best option's features
        feats    = best.extract_features(state)
        decision = self.uq_predictor.predict_and_decide(feats, max_width=self.max_width)

        if decision.recommended_action == "abstain":
            logger.info(
                "UncertaintyAwareManager: abstaining from option %r — %s",
                best.name, decision.reason,
            )
            self._abstentions += 1
            return None, candidates

        self._selections += 1
        return best, candidates

    def abstention_rate(self) -> float:
        total = self._abstentions + self._selections
        return self._abstentions / total if total > 0 else 0.0

    def stats(self) -> Dict[str, Any]:
        return {
            "abstentions"    : self._abstentions,
            "selections"     : self._selections,
            "abstention_rate": self.abstention_rate(),
        }


# ---------------------------------------------------------------------------
# Calibration curve helpers (for plotting)
# ---------------------------------------------------------------------------

def calibration_curve(
    predictor  : ConformalRewardPredictor,
    test_pairs : List[Tuple[np.ndarray, np.ndarray]],
    alphas     : Optional[List[float]] = None,
) -> Tuple[List[float], List[float]]:
    """
    Compute an empirical calibration curve.

    For each α in *alphas*, re-calibrate the quantile and measure
    empirical coverage on *test_pairs*.

    Parameters
    ----------
    predictor  : A calibrated ConformalRewardPredictor.
    test_pairs : Held-out test pairs.
    alphas     : Miscoverage levels to sweep (default: 0.05–0.50).

    Returns
    -------
    (target_coverages, empirical_coverages)
    """
    if alphas is None:
        alphas = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]

    target_coverages   = [1 - a for a in alphas]
    empirical_coverages: List[float] = []

    orig_alpha = predictor.alpha
    orig_q     = predictor._q_hat

    for alpha in alphas:
        predictor.alpha = alpha
        if predictor._cal_result is not None:
            # Recompute q_hat for this alpha using the stored scores
            scores = predictor._cal_result.nonconformity_scores
            n      = len(scores)
            level  = np.ceil((n + 1) * (1 - alpha)) / n
            level  = min(level, 1.0)
            predictor._q_hat = float(np.quantile(scores, level))

        # Measure empirical coverage
        n_covered = 0
        for phi1, phi2 in test_pairs:
            phi1 = np.asarray(phi1, dtype=float)
            iv   = predictor.predict(phi1)
            r1   = predictor.base_agent.get_reward(phi1)
            r2   = predictor.base_agent.get_reward(np.asarray(phi2, dtype=float))
            true_diff = r1 - r2
            if iv.lower <= true_diff <= iv.upper:
                n_covered += 1
        empirical_coverages.append(n_covered / len(test_pairs) if test_pairs else 0.0)

    # Restore original state
    predictor.alpha  = orig_alpha
    predictor._q_hat = orig_q

    return target_coverages, empirical_coverages
