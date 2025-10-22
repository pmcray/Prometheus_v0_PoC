
import numpy as np

class ValueLearningAgent:
    """
    An agent that learns a reward function from human preferences.
    """

    def __init__(self, feature_size):
        """
        Initializes the ValueLearningAgent.

        Args:
            feature_size: The number of features in the state representation.
        """
        self.weights = np.zeros(feature_size)

    def get_reward(self, features):
        """
        Calculates the reward for a given state.

        Args:
            features: The features of the state.

        Returns:
            The calculated reward.
        """
        return np.dot(self.weights, features)

    def update_weights(self, preferred_features, unpreferred_features):
        """
        Updates the reward model weights based on human preference.

        Args:
            preferred_features: The features of the preferred trajectory.
            unpreferred_features: The features of the unpreferred trajectory.
        """
        # Simple gradient update
        self.weights += preferred_features - unpreferred_features
        # Normalize weights to prevent them from growing too large
        self.weights /= np.linalg.norm(self.weights) or 1

    def get_weights(self):
        """
        Returns the current weights of the reward model.
        """
        return self.weights
