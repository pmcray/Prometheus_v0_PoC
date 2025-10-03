"""
MicroRTS Agent Adapter for Prometheus
Bridges between Prometheus's GamePlayingExpertAgent and MicroRTS gym environment
"""

import logging
import numpy as np
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class MicroRTSAgentAdapter:
    """
    Adapter that wraps a Prometheus GamePlayingExpertAgent for MicroRTS

    Handles conversion between:
    - MicroRTS observation space → agent decision format
    - Agent decisions → MicroRTS action space
    """

    def __init__(self, prometheus_agent):
        """
        Initialize adapter

        Args:
            prometheus_agent: A Prometheus GamePlayingExpertAgent instance
        """
        self.agent = prometheus_agent
        self.game_history = []

    def select_action(self, observation):
        """
        Select action for MicroRTS environment

        Args:
            observation: MicroRTS observation (varies by environment)

        Returns:
            Action compatible with MicroRTS action space
        """
        try:
            # MicroRTS observations can be complex multi-dimensional arrays
            # For now, use a simple heuristic-based approach
            # TODO: Evolve this strategy using Prometheus's evolutionary system

            # Check if observation is dict (some environments return dicts)
            if isinstance(observation, dict):
                return self._handle_dict_observation(observation)

            # Handle array observations
            elif isinstance(observation, np.ndarray):
                return self._handle_array_observation(observation)

            else:
                logger.warning(f"Unknown observation type: {type(observation)}")
                return 0  # Default action

        except Exception as e:
            logger.error(f"Error selecting action: {e}")
            return 0  # Safe fallback

    def _handle_dict_observation(self, obs_dict: Dict) -> int:
        """Handle dictionary-based observations"""
        # Check for action mask (valid actions)
        if 'action_mask' in obs_dict:
            action_mask = obs_dict['action_mask']
            valid_actions = np.where(action_mask)[0]

            if len(valid_actions) > 0:
                # Use agent's strategy to pick from valid actions
                # For now, prefer middle actions (balanced strategy)
                return int(valid_actions[len(valid_actions) // 2])
            else:
                return 0

        # Check for state/board representation
        if 'state' in obs_dict:
            state = obs_dict['state']
            return self._analyze_state(state)

        # Fallback
        return 0

    def _handle_array_observation(self, obs_array: np.ndarray) -> int:
        """Handle array-based observations"""
        # Flatten if multi-dimensional
        if obs_array.ndim > 1:
            obs_flat = obs_array.flatten()
        else:
            obs_flat = obs_array

        # Simple heuristic: sum of observation features
        obs_sum = np.sum(obs_flat)

        # Map to action (this is placeholder logic)
        # TODO: Replace with evolved strategy
        action = int(obs_sum % 10)  # Simple modulo mapping

        return action

    def _analyze_state(self, state: np.ndarray) -> int:
        """
        Analyze game state to select action

        This is where we'd integrate Prometheus's evolved strategies.
        For now, using simple heuristics.
        """
        # Count friendly vs enemy units
        friendly_units = np.sum(state > 0)
        enemy_units = np.sum(state < 0)

        # Simple strategy logic
        if friendly_units > enemy_units * 1.5:
            # Strong position: aggressive action
            return 7  # Attack action (placeholder)
        elif friendly_units < enemy_units * 0.7:
            # Weak position: defensive action
            return 3  # Defend action (placeholder)
        else:
            # Balanced: economic action
            return 5  # Build/gather action (placeholder)

    def reset(self):
        """Reset agent state for new episode"""
        self.game_history = []
        if hasattr(self.agent, 'reset'):
            self.agent.reset()


class MicroRTSStrategyAgent:
    """
    Strategy-based MicroRTS agent that can be evolved by Prometheus

    This agent uses parameterized strategies that can be mutated and evolved.
    """

    def __init__(self, strategy_params: Optional[Dict[str, float]] = None):
        """
        Initialize with strategy parameters

        Args:
            strategy_params: Dictionary of strategy weights
        """
        # Default strategy parameters (can be evolved)
        self.params = strategy_params or {
            'aggression': 0.5,      # 0=defensive, 1=aggressive
            'economy_focus': 0.5,   # 0=military, 1=economy
            'expansion_rate': 0.5,  # 0=consolidate, 1=expand
            'tech_priority': 0.5,   # 0=quantity, 1=quality
        }

        self.game_step = 0

    def select_action(self, observation) -> int:
        """
        Select action based on evolved strategy parameters

        Args:
            observation: MicroRTS observation

        Returns:
            Action ID
        """
        self.game_step += 1

        # Early game: focus on economy
        if self.game_step < 100:
            if self.params['economy_focus'] > 0.5:
                return self._economic_action(observation)
            else:
                return self._military_action(observation)

        # Mid game: balance based on aggression parameter
        elif self.game_step < 500:
            if np.random.random() < self.params['aggression']:
                return self._aggressive_action(observation)
            else:
                return self._defensive_action(observation)

        # Late game: decisive action
        else:
            return self._endgame_action(observation)

    def _economic_action(self, obs) -> int:
        """Action focused on resource gathering"""
        # Placeholder: actual implementation would analyze observation
        return 1  # Gather resources

    def _military_action(self, obs) -> int:
        """Action focused on military units"""
        return 2  # Build military

    def _aggressive_action(self, obs) -> int:
        """Aggressive action"""
        return 3  # Attack

    def _defensive_action(self, obs) -> int:
        """Defensive action"""
        return 4  # Defend

    def _endgame_action(self, obs) -> int:
        """Late game decisive action"""
        if self.params['aggression'] > 0.6:
            return 5  # All-in attack
        else:
            return 6  # Fortify position

    def reset(self):
        """Reset for new episode"""
        self.game_step = 0

    def mutate(self, mutation_rate: float = 0.1) -> 'MicroRTSStrategyAgent':
        """
        Create mutated copy of this agent

        Args:
            mutation_rate: Probability and magnitude of mutations

        Returns:
            New mutated agent
        """
        new_params = {}
        for key, value in self.params.items():
            if np.random.random() < mutation_rate:
                # Mutate: add random noise
                delta = np.random.normal(0, 0.2)
                new_value = np.clip(value + delta, 0.0, 1.0)
                new_params[key] = new_value
            else:
                new_params[key] = value

        return MicroRTSStrategyAgent(strategy_params=new_params)

    def crossover(self, other: 'MicroRTSStrategyAgent') -> 'MicroRTSStrategyAgent':
        """
        Create offspring by crossover with another agent

        Args:
            other: Another MicroRTSStrategyAgent

        Returns:
            New agent with mixed parameters
        """
        new_params = {}
        for key in self.params.keys():
            if np.random.random() < 0.5:
                new_params[key] = self.params[key]
            else:
                new_params[key] = other.params[key]

        return MicroRTSStrategyAgent(strategy_params=new_params)

    def get_strategy_description(self) -> str:
        """Get human-readable strategy description"""
        desc = "MicroRTS Strategy:\n"
        for param, value in self.params.items():
            desc += f"  {param}: {value:.2f}\n"
        return desc


def create_microrts_agent(agent_type: str = 'strategy') -> Any:
    """
    Factory function to create MicroRTS agents

    Args:
        agent_type: 'strategy' or 'adapter'

    Returns:
        MicroRTS agent instance
    """
    if agent_type == 'strategy':
        return MicroRTSStrategyAgent()
    elif agent_type == 'adapter':
        # Would wrap a Prometheus GamePlayingExpertAgent
        from prometheus.domain_expert_agent import GamePlayingExpertAgent
        prometheus_agent = GamePlayingExpertAgent()
        return MicroRTSAgentAdapter(prometheus_agent)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


if __name__ == "__main__":
    # Test agent creation
    print("Testing MicroRTS Agent Adapter")
    print("=" * 50)

    # Test strategy agent
    agent = MicroRTSStrategyAgent()
    print("\nInitial Strategy:")
    print(agent.get_strategy_description())

    # Test mutation
    mutated = agent.mutate(mutation_rate=0.3)
    print("\nMutated Strategy:")
    print(mutated.get_strategy_description())

    # Test crossover
    other_agent = MicroRTSStrategyAgent({
        'aggression': 0.8,
        'economy_focus': 0.2,
        'expansion_rate': 0.7,
        'tech_priority': 0.3
    })
    offspring = agent.crossover(other_agent)
    print("\nOffspring Strategy:")
    print(offspring.get_strategy_description())
