
import numpy as np

class GridWorld:
    """
    A simple gridworld environment for value learning.
    """

    def __init__(self, size=5):
        """
        Initializes the GridWorld environment.

        Args:
            size: The size of the grid.
        """
        self.size = size
        self.agent_pos = np.array([0, 0])
        self.goal_pos = np.array([size - 1, size - 1])  # The agent doesn't know this

    def get_state(self):
        """
        Returns the current state of the environment.
        """
        return self.agent_pos

    def get_features(self, state):
        """
        Calculates the features for a given state.
        In this simple case, the features are just the coordinates.

        Args:
            state: The state to calculate features for.

        Returns:
            The feature vector.
        """
        return state

    def step(self, action):
        """
        Takes a step in the environment.

        Args:
            action: The action to take (0: up, 1: down, 2: left, 3: right).

        Returns:
            The new state and a dummy reward (the real reward is learned).
        """
        if action == 0:
            self.agent_pos[0] = max(0, self.agent_pos[0] - 1)
        elif action == 1:
            self.agent_pos[0] = min(self.size - 1, self.agent_pos[0] + 1)
        elif action == 2:
            self.agent_pos[1] = max(0, self.agent_pos[1] - 1)
        elif action == 3:
            self.agent_pos[1] = min(self.size - 1, self.agent_pos[1] + 1)

        return self.get_state(), 0  # Dummy reward

    def generate_trajectory(self, policy_func, num_steps=5):
        """
        Generates a trajectory given a policy.

        Args:
            policy_func: A function that takes a state and returns an action.
            num_steps: The number of steps in the trajectory.

        Returns:
            The trajectory (list of states) and the sum of features.
        """
        self.agent_pos = np.array([0, 0])  # Reset agent position
        trajectory = [self.get_state()]
        sum_features = self.get_features(self.get_state())

        for _ in range(num_steps):
            action = policy_func(self.get_state())
            new_state, _ = self.step(action)
            trajectory.append(new_state)
            sum_features += self.get_features(new_state)

        return trajectory, sum_features
