"""
GridWorld Value Learning Benchmark — Prometheus v0.97

Provides a 2-D grid-world environment for empirically validating the
ValueLearningAgent pipeline.  Three things live here:

1. GridWorld
   A configurable N×N grid with walls, a start cell, and a goal cell.
   Features are richer than raw coordinates — they encode proximity to
   the goal, proximity to walls, and a "goal-reached" indicator.

2. GridWorldPolicy
   A lightweight planner that picks the action with the highest
   learnt reward.  Falls back to a random walk before the agent has
   any non-zero weights.

3. GridWorldExperiment
   End-to-end experiment runner:
     a. Generate pairs of trajectories under different policies.
     b. Query a SyntheticOracle for pairwise preferences.
     c. Train the ValueLearningAgent via Bradley-Terry IRL.
     d. Evaluate: does the learnt reward rank the optimal trajectory
        above random ones?
   Returns a results dict consumed by run_value_learning_cycle() in
   prometheus/mcs.py and by the test suite.

Feature vector (6-D)
--------------------
  [0] row  / (N-1)                  — normalised row position
  [1] col  / (N-1)                  — normalised col position
  [2] Manhattan(pos, goal) / (2N-2)  — distance to goal (lower = better)
  [3] min wall-distance / (N-1)      — clearance from nearest wall cell
  [4] 1.0 if pos == goal else 0.0    — goal indicator
  [5] constant 1.0                   — bias term
"""

import logging
import random
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from prometheus.value_learning import ValueLearningAgent
from prometheus.human_feedback import SyntheticOracle, collect_preferences_batch

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FEATURE_SIZE = 6          # dimensionality of the state feature vector
ACTIONS = [0, 1, 2, 3]   # up / down / left / right
ACTION_DELTAS = {
    0: (-1, 0),   # up
    1: (1, 0),    # down
    2: (0, -1),   # left
    3: (0, 1),    # right
}


# ---------------------------------------------------------------------------
# GridWorld
# ---------------------------------------------------------------------------

class GridWorld:
    """
    Configurable N×N grid-world for value-learning experiments.

    Grid encoding
    -------------
    0 = free cell
    1 = wall cell (impassable)
    The agent always starts at `start` and the goal is at `goal`.

    Args:
        size:  Side length of the (square) grid.
        walls: Optional list of (row, col) wall positions.
        start: Starting position (default: top-left corner).
        goal:  Goal position (default: bottom-right corner).
    """

    def __init__(
        self,
        size: int = 5,
        walls: Optional[List[Tuple[int, int]]] = None,
        start: Tuple[int, int] = (0, 0),
        goal: Optional[Tuple[int, int]] = None,
    ):
        self.size = size
        self.start = np.array(start, dtype=int)
        self.goal_pos = np.array(goal if goal else (size - 1, size - 1), dtype=int)

        # Build wall mask
        self.wall_mask = np.zeros((size, size), dtype=bool)
        if walls:
            for r, c in walls:
                self.wall_mask[r, c] = True

        # Precompute wall-cell coordinates for fast proximity queries
        wall_coords = np.argwhere(self.wall_mask)
        self._wall_coords: Optional[np.ndarray] = (
            wall_coords if len(wall_coords) > 0 else None
        )

        # Agent state
        self.agent_pos = self.start.copy()

    # ------------------------------------------------------------------
    # Core environment API
    # ------------------------------------------------------------------

    def reset(self) -> np.ndarray:
        """Reset agent to start; return state."""
        self.agent_pos = self.start.copy()
        return self.agent_pos.copy()

    def get_state(self) -> np.ndarray:
        """Return current agent position as a (2,) int array."""
        return self.agent_pos.copy()

    def step(self, action: int) -> Tuple[np.ndarray, float, bool]:
        """
        Move agent.  Walls and borders are impassable (action silently blocked).

        Returns:
            (new_state, reward=0.0, done)  — reward is always 0 (learnt later).
        """
        dr, dc = ACTION_DELTAS[action]
        nr = int(self.agent_pos[0]) + dr
        nc = int(self.agent_pos[1]) + dc

        # Clamp to grid and respect walls
        if 0 <= nr < self.size and 0 <= nc < self.size and not self.wall_mask[nr, nc]:
            self.agent_pos = np.array([nr, nc], dtype=int)

        done = bool(np.array_equal(self.agent_pos, self.goal_pos))
        return self.agent_pos.copy(), 0.0, done

    def is_done(self) -> bool:
        return bool(np.array_equal(self.agent_pos, self.goal_pos))

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------

    def get_features(self, state: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Compute a 6-D feature vector for `state` (defaults to current pos).

        Features
        --------
        [0] normalised row
        [1] normalised col
        [2] normalised Manhattan distance to goal
        [3] normalised minimum distance to any wall (1.0 if no walls)
        [4] goal-reached indicator (0 or 1)
        [5] bias = 1.0
        """
        if state is None:
            state = self.agent_pos
        r, c = int(state[0]), int(state[1])
        N = self.size
        norm = max(1, N - 1)

        row_norm = r / norm
        col_norm = c / norm

        manhattan = (abs(r - int(self.goal_pos[0])) + abs(c - int(self.goal_pos[1])))
        dist_goal = manhattan / (2 * norm)

        if self._wall_coords is not None:
            dists = np.abs(self._wall_coords - np.array([r, c])).sum(axis=1)
            min_wall_dist = float(dists.min()) / norm
        else:
            min_wall_dist = 1.0   # no walls → maximum clearance

        goal_indicator = 1.0 if (r == int(self.goal_pos[0]) and
                                  c == int(self.goal_pos[1])) else 0.0

        return np.array([row_norm, col_norm, dist_goal, min_wall_dist,
                         goal_indicator, 1.0], dtype=float)

    # ------------------------------------------------------------------
    # Trajectory generation
    # ------------------------------------------------------------------

    def generate_trajectory(
        self,
        policy_func: Callable[[np.ndarray], int],
        num_steps: int = 10,
        reset: bool = True,
    ) -> Tuple[List[np.ndarray], np.ndarray]:
        """
        Roll out `policy_func` for up to `num_steps` steps.

        Args:
            policy_func: state → action int.
            num_steps:   Maximum number of steps before truncation.
            reset:       Whether to reset the agent to start first.

        Returns:
            (states_list, cumulative_feature_sum)
        """
        if reset:
            self.reset()

        states: List[np.ndarray] = [self.agent_pos.copy()]
        feature_sum = self.get_features(self.agent_pos)

        for _ in range(num_steps):
            action = policy_func(self.agent_pos.copy())
            new_state, _, done = self.step(action)
            states.append(new_state.copy())
            feature_sum = feature_sum + self.get_features(new_state)
            if done:
                break

        return states, feature_sum


# ---------------------------------------------------------------------------
# GridWorldPolicy
# ---------------------------------------------------------------------------

class GridWorldPolicy:
    """
    Chooses the greedy action (highest one-step learnt reward) or falls back
    to random if weights are all zero.

    Args:
        agent:      ValueLearningAgent supplying the reward model.
        env:        GridWorld used for feature lookup.
        epsilon:    Probability of random action (ε-greedy exploration).
    """

    def __init__(
        self,
        agent: ValueLearningAgent,
        env: GridWorld,
        epsilon: float = 0.1,
    ):
        self.agent = agent
        self.env = env
        self.epsilon = epsilon

    def __call__(self, state: np.ndarray) -> int:
        """Select an action for `state`."""
        if self.epsilon > 0 and random.random() < self.epsilon:
            return random.choice(ACTIONS)

        # If no weights learned yet, random walk
        if np.allclose(self.agent.weights, 0.0):
            return random.choice(ACTIONS)

        best_action = random.choice(ACTIONS)
        best_reward = -np.inf
        r, c = int(state[0]), int(state[1])

        for action in ACTIONS:
            dr, dc = ACTION_DELTAS[action]
            nr, nc = r + dr, c + dc
            # Clamp / wall check
            if not (0 <= nr < self.env.size and 0 <= nc < self.env.size):
                nr, nc = r, c
            elif self.env.wall_mask[nr, nc]:
                nr, nc = r, c
            next_feat = self.env.get_features(np.array([nr, nc]))
            reward = self.agent.get_reward(next_feat)
            if reward > best_reward:
                best_reward = reward
                best_action = action

        return best_action


def random_policy(state: np.ndarray) -> int:
    """Pure random walk — used to generate diverse trajectory pairs."""
    return random.choice(ACTIONS)


def goal_seeking_policy(env: GridWorld) -> Callable[[np.ndarray], int]:
    """
    Oracle policy: always move toward the goal (Manhattan heuristic).
    Used as the 'true best' trajectory source for the synthetic oracle.
    """
    def _policy(state: np.ndarray) -> int:
        r, c = int(state[0]), int(state[1])
        gr, gc = int(env.goal_pos[0]), int(env.goal_pos[1])
        candidates = []
        for action, (dr, dc) in ACTION_DELTAS.items():
            nr, nc = r + dr, c + dc
            if not (0 <= nr < env.size and 0 <= nc < env.size):
                continue
            if env.wall_mask[nr, nc]:
                continue
            dist = abs(nr - gr) + abs(nc - gc)
            candidates.append((dist, action))
        if not candidates:
            return random.choice(ACTIONS)
        candidates.sort()
        return candidates[0][1]
    return _policy


# ---------------------------------------------------------------------------
# GridWorldExperiment
# ---------------------------------------------------------------------------

class GridWorldExperiment:
    """
    End-to-end value-learning experiment on the GridWorld.

    Protocol
    --------
    1. Generate `n_pairs` trajectory pairs: one from the oracle (goal-seeking)
       policy, one from a random walk.
    2. Query a SyntheticOracle (true reward = -distance_to_goal) for
       pairwise preferences — no human needed.
    3. Train the ValueLearningAgent via `train_to_convergence()`.
    4. Evaluate: compute the fraction of held-out trajectory pairs where
       the learnt reward correctly ranks the oracle trajectory above the
       random one.

    Args:
        env:            GridWorld instance (shared across all phases).
        vl_agent:       ValueLearningAgent to train.
        n_pairs:        Number of preference pairs to collect.
        trajectory_len: Steps per trajectory.
        noise_level:    Oracle noise level (0 = deterministic).
        max_epochs:     Max training epochs.
        tol:            Convergence tolerance.
        eval_pairs:     Number of held-out pairs for evaluation.
    """

    def __init__(
        self,
        env: GridWorld,
        vl_agent: ValueLearningAgent,
        n_pairs: int = 40,
        trajectory_len: int = 12,
        noise_level: float = 0.0,
        max_epochs: int = 200,
        tol: float = 1e-4,
        eval_pairs: int = 20,
    ):
        self.env = env
        self.vl_agent = vl_agent
        self.n_pairs = n_pairs
        self.trajectory_len = trajectory_len
        self.noise_level = noise_level
        self.max_epochs = max_epochs
        self.tol = tol
        self.eval_pairs = eval_pairs

        # True reward: negative normalised Manhattan distance to goal
        def _true_reward(features: np.ndarray) -> float:
            # features[2] = normalised dist-to-goal; lower = better
            return -float(features[2])

        self.oracle = SyntheticOracle(_true_reward, noise_level=noise_level)
        self._oracle_policy = goal_seeking_policy(env)

    # ------------------------------------------------------------------
    # Data collection
    # ------------------------------------------------------------------

    def _collect_trajectory_pair(
        self,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate one pair: (oracle trajectory, random trajectory).
        Returns their cumulative feature sums.
        """
        _, oracle_feat = self.env.generate_trajectory(
            self._oracle_policy, num_steps=self.trajectory_len
        )
        _, random_feat = self.env.generate_trajectory(
            random_policy, num_steps=self.trajectory_len
        )
        return oracle_feat, random_feat

    def collect_preferences(self) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Collect `n_pairs` oracle-vs-random trajectory pairs and query the
        synthetic oracle for preferences.

        Returns list of (preferred_features, unpreferred_features).
        """
        raw_pairs = [self._collect_trajectory_pair() for _ in range(self.n_pairs)]
        results = collect_preferences_batch(raw_pairs, oracle=self.oracle, verbose=False)
        preference_pairs = [
            (r.preferred_features, r.unpreferred_features) for r in results
        ]
        logger.info(
            f"Collected {len(preference_pairs)} preference pairs "
            f"(oracle queries: {self.oracle.query_count})"
        )
        return preference_pairs

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(
        self,
        preference_pairs: List[Tuple[np.ndarray, np.ndarray]],
    ) -> Dict[str, Any]:
        """Train the ValueLearningAgent to convergence on preference_pairs."""
        logger.info(
            f"Training ValueLearningAgent on {len(preference_pairs)} pairs "
            f"(max_epochs={self.max_epochs}, tol={self.tol})"
        )
        return self.vl_agent.train_to_convergence(
            preference_pairs,
            max_epochs=self.max_epochs,
            tol=self.tol,
        )

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self) -> Dict[str, float]:
        """
        Generate `eval_pairs` held-out pairs and check ranking accuracy.

        Returns
        -------
        Dict with keys:
          ranking_accuracy  — fraction of pairs correctly ranked
          mean_reward_gap   — mean (R_oracle − R_random) under learnt weights
          oracle_rank_pct   — same as ranking_accuracy (alias for clarity)
        """
        correct = 0
        reward_gaps = []

        for _ in range(self.eval_pairs):
            oracle_feat, random_feat = self._collect_trajectory_pair()
            r_oracle = self.vl_agent.get_reward(oracle_feat)
            r_random = self.vl_agent.get_reward(random_feat)
            gap = r_oracle - r_random
            reward_gaps.append(gap)
            if gap > 0:
                correct += 1

        accuracy = correct / self.eval_pairs if self.eval_pairs > 0 else 0.0
        mean_gap = float(np.mean(reward_gaps)) if reward_gaps else 0.0

        logger.info(
            f"Evaluation — ranking_accuracy={accuracy:.3f}, "
            f"mean_reward_gap={mean_gap:.4f}"
        )
        return {
            "ranking_accuracy": accuracy,
            "mean_reward_gap": mean_gap,
            "oracle_rank_pct": accuracy,
        }

    # ------------------------------------------------------------------
    # Full experiment pipeline
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        """
        Execute the full experiment:
          collect → train → evaluate.

        Returns
        -------
        Dict with keys:
          preference_pairs     — raw training data (list of tuples)
          training_result      — dict from train_to_convergence()
          eval_result          — dict from evaluate()
          learnt_weights       — final weight vector
          converged            — bool
          ranking_accuracy     — top-level shortcut
        """
        logger.info("=== GridWorld Value Learning Experiment ===")

        # Phase 1: Data collection
        preference_pairs = self.collect_preferences()

        # Phase 2: Training
        training_result = self.train(preference_pairs)

        # Phase 3: Evaluation
        eval_result = self.evaluate()

        result = {
            "preference_pairs": preference_pairs,
            "training_result": training_result,
            "eval_result": eval_result,
            "learnt_weights": self.vl_agent.get_weights().tolist(),
            "converged": training_result.get("converged", False),
            "ranking_accuracy": eval_result["ranking_accuracy"],
        }

        logger.info(
            f"Experiment complete — converged={result['converged']}, "
            f"ranking_accuracy={result['ranking_accuracy']:.3f}"
        )
        return result


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def make_default_experiment(
    size: int = 5,
    n_pairs: int = 40,
    trajectory_len: int = 12,
    noise_level: float = 0.0,
    walls: Optional[List[Tuple[int, int]]] = None,
) -> GridWorldExperiment:
    """
    Build a GridWorldExperiment with sensible defaults.

    Args:
        size:           Grid side length.
        n_pairs:        Training preference pairs.
        trajectory_len: Steps per trajectory.
        noise_level:    Oracle noise (0 = deterministic).
        walls:          Optional wall positions.

    Returns:
        Ready-to-run GridWorldExperiment.
    """
    env = GridWorld(size=size, walls=walls)
    agent = ValueLearningAgent(
        feature_size=FEATURE_SIZE,
        learning_rate=0.05,
        l2_reg=1e-3,
    )
    return GridWorldExperiment(
        env=env,
        vl_agent=agent,
        n_pairs=n_pairs,
        trajectory_len=trajectory_len,
        noise_level=noise_level,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)

    walls = [(1, 1), (1, 2), (2, 1)]
    experiment = make_default_experiment(size=5, n_pairs=60, walls=walls)
    result = experiment.run()

    print("\n=== Experiment Results ===")
    print(f"  Converged:        {result['converged']}")
    print(f"  Ranking accuracy: {result['ranking_accuracy']:.3f}")
    print(f"  Training epochs:  {result['training_result']['epochs_run']}")
    print(f"  Learnt weights:   {[round(w, 4) for w in result['learnt_weights']]}")
