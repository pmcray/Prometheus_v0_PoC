"""
prometheus/certified_robustness.py — Certified Robustness for Value Learning (WP8)

Provides randomised-smoothing-based certified robustness guarantees for the
``ValueLearningAgent``.  Certified robustness (Cohen et al., 2019) asks:

    *Within an L₂ ball of radius ε centred on x, is the ranking of trajectory
    x over trajectory y guaranteed to be stable?*

If the answer is "yes", the agent can act on that preference with high
statistical confidence, regardless of small adversarial perturbations.

Background
----------
Cohen et al. (2019) show that if a base classifier g(·) is smoothed by
adding Gaussian noise N(0, σ²I) to the input, the smoothed classifier

    f(x) = argmax_c  P(g(x + ε) = c)

is certifiably robust within radius R = σ · Φ⁻¹(p_A), where p_A is the
probability of the top class under the noise distribution and Φ⁻¹ is the
inverse standard-normal CDF.

We adapt this to the Bradley-Terry preference model:

    P(τ₁ ≻ τ₂ | x)  =  σ( w^T (φ₁ − φ₂) )

The smoothed preference probability is estimated by Monte Carlo: draw N
samples x_i = x + N(0, σ²I), evaluate the preference probability for each,
and use a one-sided Clopper-Pearson confidence interval to certify that the
preference is stable within radius R = σ · Φ⁻¹(p_lower_bound).

Public API
----------
SmoothedValueLearner(agent, sigma, n_samples, confidence)
    .predict_preference(phi1, phi2)        → bool  (prefers phi1 over phi2)
    .certify(phi1, phi2)                   → CertificationResult
    .certified_preference(phi1, phi2, eps) → (bool, certified: bool)

DataValidator.validate_and_certify(arr, epsilon) → (safe: bool, radius: float)
    — extends the WP3 DataValidator with a certified-radius check.

CertificationResult                        — dataclass returned by certify()

References
----------
Cohen, J., Rosenfeld, E., & Kolter, Z. (2019). Certified adversarial robustness
via randomized smoothing. ICML 2019. https://arxiv.org/abs/1902.02918
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
# Helpers
# ---------------------------------------------------------------------------

def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    if x >= 0:
        return 1.0 / (1.0 + np.exp(-x))
    e = np.exp(x)
    return e / (1.0 + e)


def _clopper_pearson_lower(k: int, n: int, alpha: float) -> float:
    """
    One-sided lower Clopper-Pearson confidence bound.

    Returns p_L such that P(p >= p_L) = 1 - alpha, i.e. we are (1-alpha)
    confident the true probability is at least p_L.

    Uses the Beta distribution relationship:
        p_L = Beta(alpha; k, n-k+1)
    """
    if k == 0:
        return 0.0
    return scipy_stats.beta.ppf(alpha, k, n - k + 1)


def _certified_radius(p_lower: float, sigma: float) -> float:
    """
    Cohen et al. (2019) Eq. 1:  R = σ · Φ⁻¹(p_lower)

    Returns 0 if p_lower ≤ 0.5 (no robustness guarantee possible).
    """
    if p_lower <= 0.5:
        return 0.0
    return float(sigma * scipy_stats.norm.ppf(p_lower))


# ---------------------------------------------------------------------------
# CertificationResult
# ---------------------------------------------------------------------------

@dataclass
class CertificationResult:
    """
    Result of one certify() call.

    Attributes
    ----------
    prefers_phi1    : Best-guess preference (True = phi1 ≻ phi2).
    p_estimate      : Monte Carlo estimate of P(phi1 ≻ phi2).
    p_lower_bound   : (1-alpha)-confidence lower bound on P(phi1 ≻ phi2).
    certified_radius: L₂ radius within which the preference is certified.
                      0 if the preference cannot be certified.
    n_samples       : Number of Monte Carlo samples used.
    sigma           : Noise level used.
    confidence      : Statistical confidence level (1 - alpha).
    certify_time_s  : Wall-clock time for the certification.
    abstain         : True if p_lower ≤ 0.5 (no certificate issued).
    """
    prefers_phi1     : bool
    p_estimate       : float
    p_lower_bound    : float
    certified_radius : float
    n_samples        : int
    sigma            : float
    confidence       : float
    certify_time_s   : float
    abstain          : bool = False

    def summary(self) -> str:
        pref = "phi1 ≻ phi2" if self.prefers_phi1 else "phi2 ≻ phi1"
        if self.abstain:
            return (
                f"ABSTAIN — p̂={self.p_estimate:.3f} ≤ 0.5; "
                f"no certificate issued (σ={self.sigma}, N={self.n_samples})"
            )
        return (
            f"CERTIFIED {pref}: p_lower={self.p_lower_bound:.3f}, "
            f"radius={self.certified_radius:.4f} "
            f"(σ={self.sigma}, N={self.n_samples}, "
            f"conf={self.confidence:.0%}, "
            f"{self.certify_time_s*1000:.1f} ms)"
        )


# ---------------------------------------------------------------------------
# SmoothedValueLearner
# ---------------------------------------------------------------------------

class SmoothedValueLearner:
    """
    Randomised-smoothing wrapper around a ``ValueLearningAgent``.

    The wrapper adds Gaussian noise N(0, σ²I) to each feature vector before
    evaluating the agent's preference, repeating N times and aggregating.

    Parameters
    ----------
    agent       : A trained ``ValueLearningAgent``.
    sigma       : Standard deviation of the additive Gaussian noise.
    n_samples   : Number of Monte Carlo samples for certification.
    confidence  : Confidence level for the Clopper-Pearson bound (default 0.99).
    seed        : Random seed for reproducibility.
    """

    def __init__(
        self,
        agent:      ValueLearningAgent,
        sigma:      float = 0.1,
        n_samples:  int   = 1_000,
        confidence: float = 0.99,
        seed:       Optional[int] = None,
    ):
        if sigma <= 0:
            raise ValueError(f"sigma must be positive, got {sigma}")
        if not (0 < confidence < 1):
            raise ValueError(f"confidence must be in (0, 1), got {confidence}")
        if n_samples < 100:
            raise ValueError(f"n_samples must be >= 100 for reliable certification, got {n_samples}")

        self.agent      = agent
        self.sigma      = sigma
        self.n_samples  = n_samples
        self.confidence = confidence
        self._rng       = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    # Internal evaluation
    # ------------------------------------------------------------------

    def _sample_preference(
        self,
        phi1: np.ndarray,
        phi2: np.ndarray,
        n:    int,
    ) -> int:
        """
        Draw n noisy samples and count how many prefer phi1 over phi2.

        Returns
        -------
        k : Number of samples where phi1 ≻ phi2 under the noisy agent.
        """
        phi1 = np.asarray(phi1, dtype=float)
        phi2 = np.asarray(phi2, dtype=float)

        # Noise matrix: shape (n, feature_size)
        noise1 = self._rng.normal(0.0, self.sigma, (n, phi1.shape[0]))
        noise2 = self._rng.normal(0.0, self.sigma, (n, phi2.shape[0]))

        noisy_phi1 = phi1[None, :] + noise1   # (n, d)
        noisy_phi2 = phi2[None, :] + noise2   # (n, d)

        # Reward differences under the linear model
        w = self.agent.weights
        delta_r = noisy_phi1 @ w - noisy_phi2 @ w   # (n,)

        # Count samples where phi1 is preferred (delta_r > 0)
        k = int(np.sum(delta_r > 0))
        return k

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def predict_preference(
        self,
        phi1: np.ndarray,
        phi2: np.ndarray,
    ) -> bool:
        """
        Majority-vote smoothed preference estimate.

        Returns True if the smoothed agent prefers phi1 over phi2.
        """
        k = self._sample_preference(phi1, phi2, self.n_samples)
        return k > self.n_samples / 2

    def certify(
        self,
        phi1: np.ndarray,
        phi2: np.ndarray,
    ) -> CertificationResult:
        """
        Compute a certified robustness radius for the preference phi1 ≻ phi2.

        Steps
        -----
        1. Draw ``n_samples`` noisy evaluations.
        2. Estimate P(phi1 ≻ phi2) by counting votes.
        3. Compute one-sided Clopper-Pearson lower bound p_L.
        4. Certified radius R = σ · Φ⁻¹(p_L)  (Cohen et al. 2019).

        If p_L ≤ 0.5, no certificate can be issued (abstain).
        """
        t0 = time.perf_counter()
        phi1 = np.asarray(phi1, dtype=float)
        phi2 = np.asarray(phi2, dtype=float)

        k         = self._sample_preference(phi1, phi2, self.n_samples)
        p_hat     = k / self.n_samples
        alpha     = 1.0 - self.confidence
        p_lower   = _clopper_pearson_lower(k, self.n_samples, alpha)
        radius    = _certified_radius(p_lower, self.sigma)
        abstain   = p_lower <= 0.5

        result = CertificationResult(
            prefers_phi1     = k > self.n_samples / 2,
            p_estimate       = p_hat,
            p_lower_bound    = p_lower,
            certified_radius = radius,
            n_samples        = self.n_samples,
            sigma            = self.sigma,
            confidence       = self.confidence,
            certify_time_s   = time.perf_counter() - t0,
            abstain          = abstain,
        )
        logger.debug(
            "certify: k=%d/%d p̂=%.3f p_L=%.3f R=%.4f abstain=%s",
            k, self.n_samples, p_hat, p_lower, radius, abstain,
        )
        return result

    def certified_preference(
        self,
        phi1:    np.ndarray,
        phi2:    np.ndarray,
        epsilon: float,
    ) -> Tuple[bool, bool]:
        """
        Return (prefers_phi1, is_certified) where is_certified is True iff
        the preference is guaranteed to hold within an L₂ ball of radius
        ``epsilon``.

        Parameters
        ----------
        phi1, phi2 : Feature vectors of the two trajectories.
        epsilon    : The adversarial perturbation budget (L₂ norm).

        Returns
        -------
        (prefers_phi1: bool, is_certified: bool)
        """
        result = self.certify(phi1, phi2)
        is_certified = (
            not result.abstain and
            result.certified_radius >= epsilon
        )
        return result.prefers_phi1, is_certified

    def batch_certify(
        self,
        pairs:   List[Tuple[np.ndarray, np.ndarray]],
    ) -> List[CertificationResult]:
        """Certify a list of (phi1, phi2) pairs."""
        return [self.certify(p1, p2) for p1, p2 in pairs]

    def certification_stats(
        self,
        pairs:   List[Tuple[np.ndarray, np.ndarray]],
        epsilon: float,
    ) -> Dict[str, Any]:
        """
        Run batch_certify and summarise certification statistics.

        Returns
        -------
        Dict with keys:
          n_pairs, n_certified, certified_fraction,
          mean_radius, min_radius, max_radius,
          n_abstained, mean_p_lower
        """
        results       = self.batch_certify(pairs)
        n_certified   = sum(1 for r in results
                            if not r.abstain and r.certified_radius >= epsilon)
        certified_radii = [r.certified_radius for r in results if not r.abstain]
        return {
            "n_pairs":            len(results),
            "n_certified":        n_certified,
            "certified_fraction": n_certified / len(results) if results else 0.0,
            "mean_radius":        float(np.mean(certified_radii))  if certified_radii else 0.0,
            "min_radius":         float(np.min(certified_radii))   if certified_radii else 0.0,
            "max_radius":         float(np.max(certified_radii))   if certified_radii else 0.0,
            "n_abstained":        sum(1 for r in results if r.abstain),
            "mean_p_lower":       float(np.mean([r.p_lower_bound for r in results])),
        }


# ---------------------------------------------------------------------------
# DataValidator extension
# ---------------------------------------------------------------------------

class CertifiedDataValidator:
    """
    Extends the WP3 ``DataValidator`` with a certified-radius check.

    Usage
    -----
    ::

        from prometheus.adversarial_robustness import DataValidator
        from prometheus.certified_robustness import CertifiedDataValidator

        cdv = CertifiedDataValidator(
            n_features = 5,
            smoother   = SmoothedValueLearner(agent, sigma=0.1),
        )

        # Standard validation (raises AdversarialRobustnessError on violation)
        cdv.validate_features(arr)

        # Certified validation: returns (safe, certified_radius)
        safe, radius = cdv.validate_and_certify(arr, epsilon=0.2, reference=ref)

    Parameters
    ----------
    n_features  : Dimensionality expected.
    smoother    : Fitted :class:`SmoothedValueLearner`.
    clip_value  : Clipping bound (default 1e6).
    """

    def __init__(
        self,
        n_features: int,
        smoother:   SmoothedValueLearner,
        clip_value: float = 1e6,
    ):
        # Reuse WP3 DataValidator for standard checks
        from prometheus.adversarial_robustness import DataValidator
        self._base      = DataValidator(n_features=n_features, clip_value=clip_value)
        self.smoother   = smoother
        self.n_features = n_features
        self.clip_value = clip_value

    # Forward all base methods
    def validate_features(self, arr: np.ndarray) -> None:
        self._base.validate_features(arr)

    def validate_and_clip(self, arr: np.ndarray) -> np.ndarray:
        return self._base.validate_and_clip(arr)

    def validate_pair(self, pref: np.ndarray, unpref: np.ndarray) -> None:
        self._base.validate_pair(pref, unpref)

    def validate_batch(self, arrays: List[np.ndarray]) -> None:
        self._base.validate_batch(arrays)

    # New certified method
    def validate_and_certify(
        self,
        arr:       np.ndarray,
        epsilon:   float,
        reference: np.ndarray,
    ) -> Tuple[bool, float]:
        """
        Validate *arr* with standard checks, then certify the preference
        ``arr ≻ reference`` within L₂ radius *epsilon*.

        Parameters
        ----------
        arr       : The feature vector to validate (candidate preferred).
        epsilon   : Adversarial perturbation budget.
        reference : The unpreferred trajectory feature vector.

        Returns
        -------
        (safe: bool, certified_radius: float)

        safe             — True if standard validation passes AND
                           the preference is certified within *epsilon*.
        certified_radius — 0.0 if abstained or standard check fails.
        """
        from prometheus.adversarial_robustness import AdversarialRobustnessError
        try:
            self._base.validate_features(arr)
            self._base.validate_features(reference)
        except AdversarialRobustnessError:
            return False, 0.0

        result = self.smoother.certify(arr, reference)
        if result.abstain or result.certified_radius < epsilon:
            return False, result.certified_radius

        return True, result.certified_radius
