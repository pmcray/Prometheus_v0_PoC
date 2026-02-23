"""
MicroRTS Benchmark for PrometheusStar
Provides RTS game integration with curriculum learning opponents
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MicroRTSOpponentConfig:
    """Configuration for MicroRTS opponents"""
    name: str
    ai_type: str  # 'passive', 'rush', 'mixed', 'random'
    skill_level: int
    description: str
    target_win_rate: float


class MicroRTSBenchmark:
    """
    MicroRTS benchmark integration for Prometheus

    Provides curriculum learning through progressive AI opponents:
    - PassiveAI: Resource gathering focus
    - RushAI: Early aggression
    - MixedAI: Balanced strategy
    """

    def __init__(self, opponent: str = 'passive', map_size: str = '8x8'):
        """
        Initialize MicroRTS benchmark

        Args:
            opponent: AI opponent type ('passive', 'rush', 'mixed', 'random')
            map_size: Map dimensions ('4x4', '8x8', '16x16', '64x64')
        """
        self.opponent = opponent
        self.map_size = map_size
        self.env_name = f"Microrts{self._format_map_size()}-{opponent}-v0"

        # Check if gym_microrts is available
        try:
            import gym
            from gym_microrts import microrts_ai
            self.gym = gym
            self.microrts_ai = microrts_ai
            self.available = True
        except ImportError:
            logger.warning("gym-microrts not installed. Run: pip install gym-microrts")
            self.available = False

    def _format_map_size(self) -> str:
        """Format map size for environment name"""
        # Convert '8x8' -> 'Mining8x8'
        return f"Mining{self.map_size}"

    def evaluate_agent(self, agent, num_games: int = 5) -> Dict[str, Any]:
        """
        Evaluate agent performance

        Args:
            agent: Prometheus agent with select_action() method
            num_games: Number of games to play

        Returns:
            Dictionary with win rate, avg reward, and game stats
        """
        if not self.available:
            logger.error("MicroRTS not available - cannot evaluate")
            return {
                'win_rate': 0.0,
                'avg_reward': 0.0,
                'games_played': 0,
                'error': 'MicroRTS not installed'
            }

        wins = 0
        total_reward = 0.0
        game_lengths = []

        try:
            env = self.gym.make(self.env_name)
        except Exception as e:
            logger.error(f"Failed to create environment {self.env_name}: {e}")
            return {
                'win_rate': 0.0,
                'avg_reward': 0.0,
                'games_played': 0,
                'error': str(e)
            }

        for game_num in range(num_games):
            obs = env.reset()
            done = False
            episode_reward = 0.0
            steps = 0

            while not done:
                # Get action from agent
                try:
                    action = agent.select_action(obs)
                except AttributeError:
                    # Fallback if agent doesn't have select_action
                    logger.warning("Agent missing select_action() - using random actions")
                    action = env.action_space.sample()

                # Step environment
                obs, reward, done, info = env.step(action)
                episode_reward += reward
                steps += 1

                # Timeout safeguard
                if steps > 10000:
                    logger.warning(f"Game {game_num} timeout after {steps} steps")
                    break

            # Record results
            if reward > 0:
                wins += 1
            total_reward += episode_reward
            game_lengths.append(steps)

            logger.info(f"Game {game_num + 1}/{num_games}: Reward={reward:.2f}, Steps={steps}")

        env.close()

        return {
            'win_rate': wins / num_games,
            'avg_reward': total_reward / num_games,
            'games_played': num_games,
            'avg_game_length': sum(game_lengths) / len(game_lengths),
            'opponent': self.opponent,
            'map_size': self.map_size
        }


# Curriculum opponents for MicroRTS
MICRORTS_CURRICULUM = [
    MicroRTSOpponentConfig(
        name="Random AI",
        ai_type="random",
        skill_level=1,
        description="Random action baseline",
        target_win_rate=0.80
    ),
    MicroRTSOpponentConfig(
        name="Passive AI",
        ai_type="passive",
        skill_level=3,
        description="Resource gathering focus",
        target_win_rate=0.65
    ),
    MicroRTSOpponentConfig(
        name="Rush AI",
        ai_type="rush",
        skill_level=6,
        description="Early aggressive strategy",
        target_win_rate=0.50
    ),
    MicroRTSOpponentConfig(
        name="Mixed AI",
        ai_type="mixed",
        skill_level=8,
        description="Balanced strategy combining economy and aggression",
        target_win_rate=0.40
    ),
]


def get_microrts_opponent(stage: int) -> MicroRTSOpponentConfig:
    """Get opponent configuration for curriculum stage"""
    if 0 <= stage < len(MICRORTS_CURRICULUM):
        return MICRORTS_CURRICULUM[stage]
    else:
        raise ValueError(f"Invalid stage {stage}. Valid range: 0-{len(MICRORTS_CURRICULUM)-1}")


def estimate_microrts_training_time(
    population_size: int,
    generations: int,
    games_per_eval: int = 5,
    seconds_per_game: int = 30
) -> Dict[str, float]:
    """
    Estimate training time for MicroRTS curriculum

    Args:
        population_size: Number of agents per generation
        generations: Number of evolutionary generations
        games_per_eval: Games played per agent evaluation
        seconds_per_game: Average game duration

    Returns:
        Dictionary with time estimates in various units
    """
    total_games = population_size * generations * games_per_eval
    total_seconds = total_games * seconds_per_game

    return {
        'total_games': total_games,
        'total_seconds': total_seconds,
        'total_minutes': total_seconds / 60,
        'total_hours': total_seconds / 3600,
        'per_generation_minutes': (population_size * games_per_eval * seconds_per_game) / 60
    }


# Example: Simple random agent for testing
class RandomMicroRTSAgent:
    """Simple random agent for MicroRTS testing"""

    def select_action(self, obs):
        """Select random action from observation space"""
        # MicroRTS uses multi-discrete action space
        # This is just for testing - real agents would be smarter
        import numpy as np

        # Get action space dimensions from observation
        if isinstance(obs, dict):
            # Some environments return dict observations
            action_mask = obs.get('action_mask', None)
            if action_mask is not None:
                # Use valid actions only
                valid_actions = np.where(action_mask)[0]
                return np.random.choice(valid_actions) if len(valid_actions) > 0 else 0

        # Fallback: return simple action
        # (Real implementation would need proper action space handling)
        return 0


# Quick test function
def test_microrts_installation():
    """Test if MicroRTS is properly installed"""
    try:
        import gym
        from gym_microrts import microrts_ai

        print("✓ gym-microrts installed")

        # Try to create environment
        env = gym.make("MicrortsMining4x4-v0")
        print("✓ MicroRTS environment created successfully")

        # Quick test
        obs = env.reset()
        action = env.action_space.sample()
        obs, reward, done, info = env.step(action)
        print("✓ MicroRTS environment step successful")

        env.close()
        print("\n✅ MicroRTS is ready to use!")
        return True

    except ImportError as e:
        print(f"❌ gym-microrts not installed: {e}")
        print("\nInstall with: pip install gym-microrts")
        return False
    except Exception as e:
        print(f"❌ Error testing MicroRTS: {e}")
        return False


if __name__ == "__main__":
    # Test MicroRTS installation
    print("=" * 70)
    print("Testing MicroRTS Installation")
    print("=" * 70)

    if test_microrts_installation():
        print("\n" + "=" * 70)
        print("MicroRTS Curriculum Overview")
        print("=" * 70)

        for i, opponent in enumerate(MICRORTS_CURRICULUM):
            print(f"\nStage {i + 1}: {opponent.name}")
            print(f"  Type: {opponent.ai_type}")
            print(f"  Skill: {opponent.skill_level}/10")
            print(f"  Target: {opponent.target_win_rate:.0%} win rate")
            print(f"  Description: {opponent.description}")

        # Show time estimates
        print("\n" + "=" * 70)
        print("Training Time Estimates (per stage)")
        print("=" * 70)

        configs = [
            (6, 10, "Quick test"),
            (10, 20, "Full training"),
            (15, 30, "Extended training")
        ]

        for pop, gens, desc in configs:
            est = estimate_microrts_training_time(pop, gens)
            print(f"\n{desc} ({pop} agents × {gens} gens):")
            print(f"  Total games: {est['total_games']}")
            print(f"  Total time: {est['total_hours']:.1f} hours ({est['total_minutes']:.0f} min)")
            print(f"  Per generation: {est['per_generation_minutes']:.1f} min")
