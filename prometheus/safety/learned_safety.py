"""
Prometheus Learned Gödelian Safety

Transition from rule-based safety to learned safety models.
Uses a neural network to predict the risk of proposed self-modifications
based on historical outcomes and causal attribution.
"""

import numpy as np
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False

from typing import Dict, List, Tuple, Optional, Any
from prometheus.safety.checks import SafetyStatus, GodelianSafetyGovernor


class LearnedSafetyModel:
    """
    Neural model that predicts the safety of a proposed modification.
    """

    def __init__(self, input_dim: int = 16):
        self.input_dim = input_dim
        if TENSORFLOW_AVAILABLE:
            self.model = self._build_model(input_dim)
        else:
            # Simple NumPy-based logistic regression fallback
            self.weights = np.random.randn(input_dim) * 0.01
            self.bias = 0.0

    def _build_model(self, input_dim: int) -> Any:
        model = keras.Sequential([
            layers.Input(shape=(input_dim,)),
            layers.Dense(32, activation='relu'),
            layers.Dropout(0.2),
            layers.Dense(16, activation='relu'),
            layers.Dense(1, activation='sigmoid', name='risk_probability')
        ])
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        return model

    def predict_risk(self, features: np.ndarray) -> float:
        """Predict the risk of a modification (0.0 to 1.0)."""
        if TENSORFLOW_AVAILABLE:
            risk = self.model.predict(features, verbose=0)
            return float(risk[0, 0])
        else:
            # Logistic sigmoid
            z = np.dot(features, self.weights) + self.bias
            return 1.0 / (1.0 + np.exp(-z))

    def train_on_batch(self, X: np.ndarray, y: np.ndarray):
        """Train the risk predictor on experience."""
        if TENSORFLOW_AVAILABLE:
            return self.model.train_on_batch(X, y)
        else:
            # Simple SGD for logistic regression
            lr = 0.01
            for xi, yi in zip(X, y):
                pred = self.predict_risk(xi)
                error = yi - pred
                self.weights += lr * error * xi
                self.bias += lr * error
            return 0.0


class AdvancedSafetyGovernor(GodelianSafetyGovernor):
    """
    Enhanced Safety Governor that combines rule-based checks with learned risk prediction.
    """

    def __init__(
        self,
        bounds: Optional[Any] = None,
        learned_model: Optional[LearnedSafetyModel] = None,
        risk_threshold: float = 0.3
    ):
        super().__init__(bounds=bounds)
        self.learned_model = learned_model or LearnedSafetyModel()
        self.risk_threshold = risk_threshold
        self.experience_buffer = []

    def evaluate_modification(
        self,
        modification: Dict[str, Any],
        context_features: Optional[np.ndarray] = None,
        verbose: bool = True
    ) -> Tuple[SafetyStatus, str]:
        """
        Evaluate modification using both hard rules and learned risk assessment.
        """
        # 1. Hard rule-based check (Gödelian Base)
        status, reason = super().evaluate_modification(modification, verbose=False)
        
        if status == SafetyStatus.PROVABLY_UNSAFE:
            if verbose:
                print(f"   🛡️  [SAFETY] ❌ PROVABLY_UNSAFE: {reason}")
            return status, reason

        # 2. Learned risk prediction
        if context_features is not None:
            risk = self.learned_model.predict_risk(context_features)
            
            if risk > self.risk_threshold:
                if verbose:
                    print(f"   🛡️  [SAFETY] ⚠️  LEARNED_RISK ({risk:.2%}): Denied by predictive model")
                return SafetyStatus.PROVABLY_UNSAFE, f"Predicted high risk: {risk:.2%}"
            
            if verbose:
                print(f"   🛡️  [SAFETY] ✅ LEARNED_SAFE (Risk: {risk:.2%})")

        if verbose and status == SafetyStatus.PROVABLY_SAFE:
            print(f"   🛡️  [SAFETY] ✅ PROVABLY_SAFE: {reason}")
        elif verbose and status == SafetyStatus.UNDECIDABLE:
            print(f"   🛡️  [SAFETY] ⚠️  UNDECIDABLE: {reason}")

        return status, reason

    def record_outcome(self, features: np.ndarray, violation_occurred: bool):
        """Record experience for training the learned safety model."""
        self.experience_buffer.append((features, float(violation_occurred)))
        
        # Periodically train
        if len(self.experience_buffer) >= 10:
            X = np.array([item[0] for item in self.experience_buffer])
            y = np.array([item[1] for item in self.experience_buffer])
            self.learned_model.train_on_batch(X, y)
            self.experience_buffer = []
