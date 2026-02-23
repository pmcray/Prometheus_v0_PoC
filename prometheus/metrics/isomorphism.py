"""
Prometheus Isomorphism Tracking

Tracks the convergence between the agent's internal world model (isomorphism)
and the environment's ground truth during recursive self-improvement.
"""

import numpy as np
from typing import Dict, List, Any


def compute_isomorphism_score(
    internal_predictions: np.ndarray,
    external_reality: np.ndarray
) -> float:
    """
    Measure how closely the internal model matches reality.
    
    Higher score (0.0 to 1.0) means higher isomorphism.
    """
    if internal_predictions.shape != external_reality.shape:
        return 0.0
        
    # MSE-based isomorphism
    mse = np.mean(np.square(internal_predictions - external_reality))
    
    # Map MSE to 0-1 score (exponential decay)
    return float(np.exp(-mse))


class IsomorphismTracker:
    """
    Tracks isomorphism growth over multiple generations.
    """

    def __init__(self):
        self.history = []
        self.reality_alignment = []

    def record_observation(
        self,
        generation: int,
        predicted_state: np.ndarray,
        actual_state: np.ndarray
    ):
        score = compute_isomorphism_score(predicted_state, actual_state)
        self.reality_alignment.append(score)
        self.history.append({
            'generation': generation,
            'isomorphism_score': score
        })

    def get_growth_rate(self) -> float:
        """Calculate the rate of isomorphism expansion."""
        if len(self.reality_alignment) < 2:
            return 0.0
        
        return float(self.reality_alignment[-1] - self.reality_alignment[0])

    def get_statistics(self) -> Dict[str, Any]:
        if not self.reality_alignment:
            return {'avg_isomorphism': 0.0}
            
        return {
            'current_isomorphism': self.reality_alignment[-1],
            'avg_isomorphism': np.mean(self.reality_alignment),
            'max_isomorphism': np.max(self.reality_alignment),
            'growth_rate': self.get_growth_rate()
        }
