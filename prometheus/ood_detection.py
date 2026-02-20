"""
OOD Detection Module — Prometheus v0.97
Out-of-Distribution detection and Safe Mode protocol

Implements two complementary OOD detection strategies:

  1. ReconstructionOODDetector  — trains a lightweight autoencoder on
     in-distribution feature vectors; high reconstruction error signals OOD.

  2. MahalanobisOODDetector     — fits a multivariate Gaussian on in-distribution
     features; uses Mahalanobis distance as the OOD score.  Fast, interpretable,
     and does not require gradient descent at inference time.

Both detectors share the same public API:
  detector.fit(features)          — learn the in-distribution manifold
  detector.score(x)               — return scalar OOD score (higher = more OOD)
  detector.is_ood(x, threshold)   — binary decision
  detector.safe_mode_action(x)    — SafeModeDecision with recommended action

Safe Mode Protocol
------------------
When OOD is detected the system enters one of three escalating safe modes:

  CAUTION   — score in [low_threshold, high_threshold): log and reduce confidence
  SAFE_MODE — score in [high_threshold, critical_threshold): restrict actions,
              request human oversight
  HALT      — score ≥ critical_threshold: refuse to act, alert supervisor

Integration
-----------
  from prometheus.ood_detection import MahalanobisOODDetector, SafeModeProtocol
  detector = MahalanobisOODDetector(feature_size=6)
  detector.fit(in_distribution_features)

  protocol = SafeModeProtocol(detector)
  decision = protocol.evaluate(current_features)
  if not decision.allow_action:
      # take conservative fallback

References
----------
- Lee et al. (2018) "A Simple Unified Framework for Detecting Out-of-Distribution
  Samples and Adversarial Attacks"
- Hendrycks & Gimpel (2017) "A Baseline for Detecting Misclassified and
  Out-of-Distribution Examples in Neural Networks"
"""

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums and data classes
# ---------------------------------------------------------------------------

class SafeMode(Enum):
    """Escalating safe-mode levels."""
    NORMAL    = "normal"     # OOD score below low threshold — operate normally
    CAUTION   = "caution"    # Mildly OOD — log, reduce confidence
    SAFE_MODE = "safe_mode"  # Moderately OOD — restrict actions, request oversight
    HALT      = "halt"       # Severely OOD — refuse to act


@dataclass
class OODScore:
    """Result of a single OOD evaluation."""
    raw_score:      float           # Detector-specific score (higher = more OOD)
    normalised:     float           # Linearly rescaled to [0, 1] against fit stats
    safe_mode:      SafeMode
    detector_name:  str
    feature_vector: np.ndarray
    timestamp:      float = field(default_factory=time.time)

    def is_ood(self) -> bool:
        return self.safe_mode != SafeMode.NORMAL


@dataclass
class SafeModeDecision:
    """
    Actionable decision produced by SafeModeProtocol.evaluate().

    Attributes
    ----------
    allow_action:       True if normal operation may proceed.
    safe_mode:          Current escalation level.
    ood_score:          Underlying OOD score object.
    recommended_action: Human-readable recommendation string.
    confidence_scale:   Multiply agent confidence by this factor (0-1).
    alert_supervisor:   Whether the MCSSupervisor should be notified.
    """
    allow_action:       bool
    safe_mode:          SafeMode
    ood_score:          OODScore
    recommended_action: str
    confidence_scale:   float = 1.0
    alert_supervisor:   bool  = False


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BaseOODDetector:
    """
    Common interface for all OOD detectors.

    Subclasses must implement:
      _fit_internal(features)   — learn in-distribution statistics
      _score_internal(x)        — return raw scalar OOD score
    """

    name: str = "base"

    def __init__(self, feature_size: int):
        self.feature_size = feature_size
        self._fitted      = False
        self._score_mean  = 0.0   # Mean OOD score on training set (for normalisation)
        self._score_std   = 1.0   # Std of OOD scores on training set

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, features: np.ndarray) -> "BaseOODDetector":
        """
        Fit the detector on in-distribution feature vectors.

        Args:
            features: 2-D array of shape (N, feature_size).

        Returns:
            self (for chaining).
        """
        features = np.atleast_2d(np.array(features, dtype=float))
        if features.shape[1] != self.feature_size:
            raise ValueError(
                f"Expected feature_size={self.feature_size}, "
                f"got {features.shape[1]}"
            )
        self._fit_internal(features)
        self._fitted = True

        # Calibrate normalisation: compute scores on training set
        train_scores = np.array([self._score_internal(x) for x in features])
        self._score_mean = float(train_scores.mean())
        self._score_std  = float(train_scores.std()) + 1e-8

        logger.info(
            "%s fitted on %d samples.  "
            "Train score: mean=%.4f, std=%.4f",
            self.name, len(features), self._score_mean, self._score_std,
        )
        return self

    def score(self, x: np.ndarray) -> float:
        """
        Return the raw OOD score for a single feature vector.
        Higher = more likely OOD.
        """
        self._check_fitted()
        x = np.array(x, dtype=float).ravel()
        return float(self._score_internal(x))

    def normalised_score(self, x: np.ndarray) -> float:
        """
        Return OOD score normalised to approximate [0, 1] range.
        Values > 1.0 indicate very strong OOD.
        """
        raw = self.score(x)
        return max(0.0, (raw - self._score_mean) / self._score_std)

    def is_ood(self, x: np.ndarray, threshold: float = 2.0) -> bool:
        """
        Return True if the normalised OOD score exceeds `threshold`.
        Default threshold of 2.0 corresponds to ~2σ above the training mean.
        """
        return self.normalised_score(x) > threshold

    def evaluate(
        self,
        x: np.ndarray,
        low_threshold:      float = 1.5,
        high_threshold:     float = 3.0,
        critical_threshold: float = 6.0,
    ) -> OODScore:
        """
        Full evaluation returning an OODScore with escalation level.

        Args:
            x:                  Feature vector to test.
            low_threshold:      Normalised score above which CAUTION is triggered.
            high_threshold:     Normalised score above which SAFE_MODE is triggered.
            critical_threshold: Normalised score above which HALT is triggered.

        Returns:
            OODScore instance.
        """
        self._check_fitted()
        raw   = self.score(x)
        norm  = max(0.0, (raw - self._score_mean) / self._score_std)

        if norm >= critical_threshold:
            mode = SafeMode.HALT
        elif norm >= high_threshold:
            mode = SafeMode.SAFE_MODE
        elif norm >= low_threshold:
            mode = SafeMode.CAUTION
        else:
            mode = SafeMode.NORMAL

        return OODScore(
            raw_score      = raw,
            normalised     = norm,
            safe_mode      = mode,
            detector_name  = self.name,
            feature_vector = np.array(x, dtype=float).ravel(),
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def save(self, filepath: str) -> None:
        """Save detector state to JSON."""
        state = self._get_state()
        state.update({
            "name":         self.name,
            "feature_size": self.feature_size,
            "fitted":       self._fitted,
            "score_mean":   self._score_mean,
            "score_std":    self._score_std,
        })
        Path(filepath).write_text(json.dumps(state, indent=2))
        logger.info("Saved %s to %s", self.name, filepath)

    @classmethod
    def load(cls, filepath: str) -> "BaseOODDetector":
        """Load detector state from JSON."""
        state   = json.loads(Path(filepath).read_text())
        feature_size = state["feature_size"]
        detector = cls(feature_size=feature_size)
        detector._fitted     = state["fitted"]
        detector._score_mean = state["score_mean"]
        detector._score_std  = state["score_std"]
        detector._set_state(state)
        return detector

    # ------------------------------------------------------------------
    # Internal hooks (override in subclasses)
    # ------------------------------------------------------------------

    def _fit_internal(self, features: np.ndarray) -> None:
        raise NotImplementedError

    def _score_internal(self, x: np.ndarray) -> float:
        raise NotImplementedError

    def _get_state(self) -> Dict:
        return {}

    def _set_state(self, state: Dict) -> None:
        pass

    def _check_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError(
                f"{self.name} has not been fitted yet.  Call fit() first."
            )


# ---------------------------------------------------------------------------
# Mahalanobis OOD Detector
# ---------------------------------------------------------------------------

class MahalanobisOODDetector(BaseOODDetector):
    """
    OOD detector based on the Mahalanobis distance from the in-distribution mean.

    The score for a new vector x is:

        score(x) = sqrt( (x - μ)ᵀ Σ⁻¹ (x - μ) )

    where μ and Σ are the mean and covariance estimated from the training set.

    Advantages
    ----------
    - No iterative training required — O(N·D²) fit, O(D²) inference.
    - Naturally accounts for feature correlations.
    - Interpretable: score is in units of standard deviations.
    - Scale-invariant.

    Args:
        feature_size: Dimensionality of feature vectors.
        reg:          Regularisation added to the diagonal of Σ before inversion
                      (prevents singular covariance with few samples or correlated features).
    """

    name = "mahalanobis"

    def __init__(self, feature_size: int, reg: float = 1e-4):
        super().__init__(feature_size)
        self.reg          = reg
        self._mean: Optional[np.ndarray]    = None
        self._cov_inv: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    # Internal implementation
    # ------------------------------------------------------------------

    def _fit_internal(self, features: np.ndarray) -> None:
        self._mean = features.mean(axis=0)
        if len(features) < 2:
            # Cannot compute covariance from a single sample; fall back to identity
            cov = np.eye(self.feature_size)
        else:
            cov = np.cov(features, rowvar=False)
            if cov.ndim == 0:                    # single feature dimension
                cov = np.array([[float(cov)]])
            elif cov.shape != (self.feature_size, self.feature_size):
                cov = np.atleast_2d(cov)
        cov = cov + self.reg * np.eye(self.feature_size)
        self._cov_inv = np.linalg.inv(cov)

    def _score_internal(self, x: np.ndarray) -> float:
        diff = x - self._mean
        return float(np.sqrt(diff @ self._cov_inv @ diff))

    def _get_state(self) -> Dict:
        return {
            "reg":      self.reg,
            "mean":     self._mean.tolist() if self._mean is not None else None,
            "cov_inv":  self._cov_inv.tolist() if self._cov_inv is not None else None,
        }

    def _set_state(self, state: Dict) -> None:
        self.reg = state.get("reg", 1e-4)
        if state.get("mean") is not None:
            self._mean    = np.array(state["mean"])
            self._cov_inv = np.array(state["cov_inv"])


# ---------------------------------------------------------------------------
# Reconstruction (Autoencoder) OOD Detector
# ---------------------------------------------------------------------------

class ReconstructionOODDetector(BaseOODDetector):
    """
    OOD detector based on reconstruction error from a shallow autoencoder.

    Architecture
    ------------
    Encoder: feature_size → bottleneck_size  (tanh activation)
    Decoder: bottleneck_size → feature_size  (linear)

    OOD score = mean squared reconstruction error.

    In-distribution inputs are reconstructed well (low error).
    OOD inputs cannot be compressed into the learned bottleneck, giving high error.

    Args:
        feature_size:    Dimensionality of feature vectors.
        bottleneck_size: Dimension of latent code (default: feature_size // 2).
        learning_rate:   Adam-style gradient descent step size.
        epochs:          Number of full passes over training data during fit().
        batch_size:      Mini-batch size for gradient updates.
    """

    name = "reconstruction"

    def __init__(
        self,
        feature_size:    int,
        bottleneck_size: Optional[int] = None,
        learning_rate:   float = 1e-2,
        epochs:          int   = 200,
        batch_size:      int   = 32,
    ):
        super().__init__(feature_size)
        self.bottleneck_size = bottleneck_size or max(1, feature_size // 2)
        self.learning_rate   = learning_rate
        self.epochs          = epochs
        self.batch_size      = batch_size

        # Weights initialised with Glorot uniform
        self._init_weights()

    # ------------------------------------------------------------------
    # Weight management
    # ------------------------------------------------------------------

    def _init_weights(self) -> None:
        lim_enc = np.sqrt(6.0 / (self.feature_size + self.bottleneck_size))
        lim_dec = np.sqrt(6.0 / (self.bottleneck_size + self.feature_size))
        self._W_enc = np.random.uniform(-lim_enc, lim_enc,
                                        (self.feature_size, self.bottleneck_size))
        self._b_enc = np.zeros(self.bottleneck_size)
        self._W_dec = np.random.uniform(-lim_dec, lim_dec,
                                        (self.bottleneck_size, self.feature_size))
        self._b_dec = np.zeros(self.feature_size)

    # ------------------------------------------------------------------
    # Forward / backward pass
    # ------------------------------------------------------------------

    @staticmethod
    def _tanh(x: np.ndarray) -> np.ndarray:
        return np.tanh(x)

    @staticmethod
    def _tanh_grad(x: np.ndarray) -> np.ndarray:
        return 1.0 - np.tanh(x) ** 2

    def _encode(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Returns (pre_activation, activation)."""
        pre = x @ self._W_enc + self._b_enc
        return pre, self._tanh(pre)

    def _decode(self, z: np.ndarray) -> np.ndarray:
        return z @ self._W_dec + self._b_dec

    def _forward(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Returns (pre_enc, z, x_hat)."""
        pre, z = self._encode(x)
        x_hat  = self._decode(z)
        return pre, z, x_hat

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def _fit_internal(self, features: np.ndarray) -> None:
        N = len(features)
        # Simple SGD with momentum
        m_We = np.zeros_like(self._W_enc); v_We = np.zeros_like(self._W_enc)
        m_be = np.zeros_like(self._b_enc); v_be = np.zeros_like(self._b_enc)
        m_Wd = np.zeros_like(self._W_dec); v_Wd = np.zeros_like(self._W_dec)
        m_bd = np.zeros_like(self._b_dec); v_bd = np.zeros_like(self._b_dec)
        beta1, beta2, eps_adam = 0.9, 0.999, 1e-8
        t = 0

        for epoch in range(self.epochs):
            idx = np.random.permutation(N)
            for start in range(0, N, self.batch_size):
                batch = features[idx[start:start + self.batch_size]]
                B     = len(batch)
                t    += 1

                # Forward
                pre, z, x_hat = self._forward(batch)

                # MSE loss gradient w.r.t. x_hat
                d_loss = 2.0 * (x_hat - batch) / B          # (B, feature_size)

                # Decoder gradients
                dW_dec = z.T @ d_loss                        # (bottleneck, feature_size)
                db_dec = d_loss.sum(axis=0)
                d_z    = d_loss @ self._W_dec.T              # (B, bottleneck)

                # Encoder gradients (through tanh)
                d_pre  = d_z * self._tanh_grad(pre)          # (B, bottleneck)
                dW_enc = batch.T @ d_pre                     # (feature_size, bottleneck)
                db_enc = d_pre.sum(axis=0)

                # Adam update
                def adam_step(param, grad, m, v):
                    m[:] = beta1 * m + (1 - beta1) * grad
                    v[:] = beta2 * v + (1 - beta2) * grad ** 2
                    m_hat = m / (1 - beta1 ** t)
                    v_hat = v / (1 - beta2 ** t)
                    param -= self.learning_rate * m_hat / (np.sqrt(v_hat) + eps_adam)

                adam_step(self._W_enc, dW_enc, m_We, v_We)
                adam_step(self._b_enc, db_enc, m_be, v_be)
                adam_step(self._W_dec, dW_dec, m_Wd, v_Wd)
                adam_step(self._b_dec, db_dec, m_bd, v_bd)

    def _score_internal(self, x: np.ndarray) -> float:
        x2d = x[None, :]
        _, _, x_hat = self._forward(x2d)
        return float(np.mean((x2d - x_hat) ** 2))

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def _get_state(self) -> Dict:
        return {
            "bottleneck_size": self.bottleneck_size,
            "learning_rate":   self.learning_rate,
            "epochs":          self.epochs,
            "batch_size":      self.batch_size,
            "W_enc":           self._W_enc.tolist(),
            "b_enc":           self._b_enc.tolist(),
            "W_dec":           self._W_dec.tolist(),
            "b_dec":           self._b_dec.tolist(),
        }

    def _set_state(self, state: Dict) -> None:
        self.bottleneck_size = state["bottleneck_size"]
        self.learning_rate   = state["learning_rate"]
        self.epochs          = state["epochs"]
        self.batch_size      = state["batch_size"]
        self._W_enc = np.array(state["W_enc"])
        self._b_enc = np.array(state["b_enc"])
        self._W_dec = np.array(state["W_dec"])
        self._b_dec = np.array(state["b_dec"])


# ---------------------------------------------------------------------------
# Ensemble detector
# ---------------------------------------------------------------------------

class EnsembleOODDetector:
    """
    Combines Mahalanobis and Reconstruction detectors by averaging
    their normalised scores.  More robust than either alone.

    Args:
        feature_size: Dimensionality of feature vectors.
        weights:      Optional (mahalanobis_weight, reconstruction_weight).
                      Defaults to equal weighting.
    """

    name = "ensemble"

    def __init__(
        self,
        feature_size: int,
        weights: Tuple[float, float] = (0.5, 0.5),
        bottleneck_size: Optional[int] = None,
        epochs: int = 200,
        reg: float = 1e-4,
    ):
        self.feature_size = feature_size
        self.weights      = weights
        self._maha  = MahalanobisOODDetector(feature_size, reg=reg)
        self._recon = ReconstructionOODDetector(
            feature_size,
            bottleneck_size=bottleneck_size,
            epochs=epochs,
        )
        self._fitted = False

    def fit(self, features: np.ndarray) -> "EnsembleOODDetector":
        features = np.atleast_2d(np.array(features, dtype=float))
        self._maha.fit(features)
        self._recon.fit(features)
        self._fitted = True
        logger.info("EnsembleOODDetector fitted on %d samples.", len(features))
        return self

    def score(self, x: np.ndarray) -> float:
        """Return weighted average of normalised scores."""
        s_maha  = self._maha.normalised_score(x)
        s_recon = self._recon.normalised_score(x)
        w1, w2  = self.weights
        return (w1 * s_maha + w2 * s_recon) / (w1 + w2)

    def evaluate(
        self,
        x: np.ndarray,
        low_threshold:      float = 1.5,
        high_threshold:     float = 3.0,
        critical_threshold: float = 6.0,
    ) -> OODScore:
        norm = self.score(x)
        if norm >= critical_threshold:
            mode = SafeMode.HALT
        elif norm >= high_threshold:
            mode = SafeMode.SAFE_MODE
        elif norm >= low_threshold:
            mode = SafeMode.CAUTION
        else:
            mode = SafeMode.NORMAL

        return OODScore(
            raw_score      = norm,
            normalised     = norm,
            safe_mode      = mode,
            detector_name  = self.name,
            feature_vector = np.array(x, dtype=float).ravel(),
        )

    def is_ood(self, x: np.ndarray, threshold: float = 2.0) -> bool:
        return self.score(x) > threshold


# ---------------------------------------------------------------------------
# Safe Mode Protocol
# ---------------------------------------------------------------------------

class SafeModeProtocol:
    """
    Wraps an OOD detector and translates OODScore into SafeModeDecision.

    The protocol maps escalation levels to concrete actions:

      NORMAL    → allow action,  confidence_scale=1.0
      CAUTION   → allow action,  confidence_scale=0.7,  log warning
      SAFE_MODE → restrict,      confidence_scale=0.3,  alert supervisor
      HALT      → block action,  confidence_scale=0.0,  alert supervisor

    Args:
        detector:           Fitted OOD detector (any type with .evaluate()).
        low_threshold:      Normalised score threshold for CAUTION.
        high_threshold:     Normalised score threshold for SAFE_MODE.
        critical_threshold: Normalised score threshold for HALT.
    """

    def __init__(
        self,
        detector,
        low_threshold:      float = 1.5,
        high_threshold:     float = 3.0,
        critical_threshold: float = 6.0,
    ):
        self.detector           = detector
        self.low_threshold      = low_threshold
        self.high_threshold     = high_threshold
        self.critical_threshold = critical_threshold
        self._decision_log: List[SafeModeDecision] = []

    def evaluate(self, x: np.ndarray) -> SafeModeDecision:
        """
        Evaluate a feature vector and return a SafeModeDecision.

        Args:
            x: Feature vector (1-D, length == detector.feature_size).

        Returns:
            SafeModeDecision with allow_action, safe_mode, recommended_action.
        """
        ood = self.detector.evaluate(
            x,
            low_threshold      = self.low_threshold,
            high_threshold     = self.high_threshold,
            critical_threshold = self.critical_threshold,
        )

        mode = ood.safe_mode

        if mode == SafeMode.NORMAL:
            decision = SafeModeDecision(
                allow_action       = True,
                safe_mode          = mode,
                ood_score          = ood,
                recommended_action = "Proceed normally.",
                confidence_scale   = 1.0,
                alert_supervisor   = False,
            )

        elif mode == SafeMode.CAUTION:
            decision = SafeModeDecision(
                allow_action       = True,
                safe_mode          = mode,
                ood_score          = ood,
                recommended_action = (
                    f"Input is mildly out-of-distribution "
                    f"(score={ood.normalised:.2f}). "
                    "Proceed with reduced confidence; prefer conservative actions."
                ),
                confidence_scale   = 0.7,
                alert_supervisor   = False,
            )
            logger.warning(
                "OOD CAUTION: normalised_score=%.3f (threshold=%.1f)",
                ood.normalised, self.low_threshold,
            )

        elif mode == SafeMode.SAFE_MODE:
            decision = SafeModeDecision(
                allow_action       = True,
                safe_mode          = mode,
                ood_score          = ood,
                recommended_action = (
                    f"Input is significantly out-of-distribution "
                    f"(score={ood.normalised:.2f}). "
                    "Entering SAFE MODE: restrict to pre-approved actions only; "
                    "request human confirmation before proceeding."
                ),
                confidence_scale   = 0.3,
                alert_supervisor   = True,
            )
            logger.error(
                "OOD SAFE_MODE: normalised_score=%.3f — supervisor alerted.",
                ood.normalised,
            )

        else:  # HALT
            decision = SafeModeDecision(
                allow_action       = False,
                safe_mode          = mode,
                ood_score          = ood,
                recommended_action = (
                    f"Input is severely out-of-distribution "
                    f"(score={ood.normalised:.2f}). "
                    "HALTING: action refused. Supervisor must review this input."
                ),
                confidence_scale   = 0.0,
                alert_supervisor   = True,
            )
            logger.critical(
                "OOD HALT: normalised_score=%.3f — action blocked.",
                ood.normalised,
            )

        self._decision_log.append(decision)
        return decision

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_log(self) -> List[SafeModeDecision]:
        """Return all decisions made so far."""
        return list(self._decision_log)

    def summary(self) -> Dict[str, Any]:
        """Return counts and rates for each safe-mode level."""
        log   = self._decision_log
        total = len(log)
        if total == 0:
            return {"total": 0}

        counts = {m.value: 0 for m in SafeMode}
        for d in log:
            counts[d.safe_mode.value] += 1

        return {
            "total":        total,
            "counts":       counts,
            "rates":        {k: v / total for k, v in counts.items()},
            "ood_rate":     1.0 - counts[SafeMode.NORMAL.value] / total,
            "halt_rate":    counts[SafeMode.HALT.value] / total,
            "blocked":      counts[SafeMode.HALT.value],
        }


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def create_ood_detector(
    detector_type: str,
    feature_size:  int,
    **kwargs,
) -> BaseOODDetector:
    """
    Factory function.

    Args:
        detector_type: "mahalanobis" | "reconstruction" | "ensemble"
        feature_size:  Feature dimensionality.
        **kwargs:      Passed to the detector constructor.

    Returns:
        Un-fitted detector instance.
    """
    mapping = {
        "mahalanobis":    MahalanobisOODDetector,
        "reconstruction": ReconstructionOODDetector,
        "ensemble":       EnsembleOODDetector,
    }
    if detector_type not in mapping:
        raise ValueError(
            f"Unknown detector_type '{detector_type}'. "
            f"Choose from: {list(mapping)}"
        )
    return mapping[detector_type](feature_size=feature_size, **kwargs)
