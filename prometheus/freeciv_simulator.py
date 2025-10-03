"""
FreeCiv Simulator for Testing

Provides simulated FreeCiv gameplay for testing Prometheus learning loop
without requiring FreeCiv server installation.

Simulates:
- AI opponents at various difficulty levels
- City building and expansion
- Technology research
- Military conflicts
- Victory/defeat conditions
"""

from typing import Dict, Any, List, Optional, Tuple
import random
from dataclasses import dataclass, field

from prometheus.freeciv_environment import (
    GameState, FreeCivAction, DifficultyLevel
)


class FreeCivSimulator:
    """
    Simulates FreeCiv gameplay for testing

    Uses simplified game mechanics but realistic enough to test
    Prometheus's CRLS learning loop and strategy evolution.
    """

    def __init__(self, difficulty: DifficultyLevel = DifficultyLevel.NORMAL):
        self.difficulty = difficulty
        self.turn = 0
        self.state = None
        self.current_state = None  # Alias for compatibility
        self.ai_strength = self._get_ai_strength(difficulty)

        # Simulation parameters
        self.map_size = 80  # 80x50 tiles
        self.max_cities = 20
        self.max_units = 50
        self.tech_tree_size = 50

    def _get_ai_strength(self, difficulty: DifficultyLevel) -> float:
        """Get AI strength multiplier based on difficulty"""
        strength_map = {
            DifficultyLevel.NOVICE: 0.5,
            DifficultyLevel.EASY: 0.7,
            DifficultyLevel.NORMAL: 1.0,
            DifficultyLevel.HARD: 1.3,
            DifficultyLevel.CHEATING: 1.6,
            DifficultyLevel.EXPERIMENTAL: 2.0
        }
        return strength_map.get(difficulty, 1.0)

    def reset(self) -> GameState:
        """Reset simulator and start new game"""
        self.turn = 0

        # Initial state
        self.state = self.current_state = GameState(
            turn=0,
            year=-4000,  # 4000 BC
            score=0,
            population=1,
            cities=1,  # Start with capital
            units=1,   # Start with settler
            techs_researched=0,
            gold=50,
            science_rate=50,
            tax_rate=0,
            luxury_rate=50,
            total_production=0,
            total_science=0,
            military_strength=0
        )

        # AI state
        self.ai_cities = 1
        self.ai_units = 1
        self.ai_techs = 0
        self.ai_military = 0

        return self.state

    def step(self, action: FreeCivAction) -> Tuple[GameState, float, bool, Dict[str, Any]]:
        """
        Execute action and simulate one turn

        Args:
            action: Action to execute

        Returns:
            (new_state, reward, done, info)
        """
        old_state = self.state

        # Apply player action
        self._apply_action(action)

        # Simulate AI turn
        self._simulate_ai_turn()

        # Advance turn
        self.turn += 1
        self.state.turn = self.turn
        self.state.year = self._calculate_year(self.turn)
        self.current_state = self.state  # Keep alias in sync

        # Natural growth
        self._simulate_growth()

        # Random events
        self._simulate_random_events()

        # Calculate reward
        reward = self._calculate_reward(old_state, self.state)

        # Check game end
        done = self._check_game_end()

        # Info
        info = {
            'turn': self.turn,
            'year': self.state.year,
            'score_delta': self.state.score - old_state.score,
            'ai_cities': self.ai_cities,
            'ai_strength': self.ai_military
        }

        return self.state, reward, done, info

    def _apply_action(self, action: FreeCivAction):
        """Apply player action to state"""
        if action.action_type == "set_rates":
            # Update economic rates
            self.state.science_rate = action.parameters.get('science', 50)
            self.state.tax_rate = action.parameters.get('tax', 0)
            self.state.luxury_rate = 100 - self.state.science_rate - self.state.tax_rate

        elif action.action_type == "build_city":
            # Found new city
            if self.state.units > 0 and self.state.cities < self.max_cities:
                self.state.cities += 1
                self.state.units -= 1  # Settler used
                self.state.population += 1

        elif action.action_type == "build_unit":
            # Build military unit
            if self.state.gold >= 10:
                self.state.units += 1
                self.state.military_strength += 10
                self.state.gold -= 10

        elif action.action_type == "research_tech":
            # Research technology (happens gradually)
            pass

    def _simulate_ai_turn(self):
        """Simulate AI opponent actions"""
        # AI expands based on difficulty
        if random.random() < 0.05 * self.ai_strength:
            if self.ai_cities < self.max_cities:
                self.ai_cities += 1

        # AI builds military
        if random.random() < 0.1 * self.ai_strength:
            self.ai_units += 1
            self.ai_military += int(10 * self.ai_strength)

        # AI researches tech
        if random.random() < 0.08 * self.ai_strength:
            self.ai_techs += 1

        # AI attacks if strong enough
        if self.ai_military > self.state.military_strength * 1.5:
            if random.random() < 0.15 * self.ai_strength:
                self._simulate_combat()

    def _simulate_growth(self):
        """Simulate natural city growth and production"""
        # Population growth
        if self.state.cities > 0:
            growth_rate = 0.02 * self.state.cities
            if random.random() < growth_rate:
                self.state.population += 1

        # Gold income
        self.state.gold += self.state.cities * 2

        # Production
        production = self.state.cities * 3
        self.state.total_production += production
        self.state.score += production // 10

        # Science progress
        science = int(self.state.science_rate / 100.0 * self.state.cities * 2)
        self.state.total_science += science

        # Tech discovery
        if self.state.total_science >= (self.state.techs_researched + 1) * 50:
            self.state.techs_researched += 1
            self.state.score += 20

    def _simulate_random_events(self):
        """Simulate random events"""
        # Barbarian raids (lose units)
        if random.random() < 0.02:
            if self.state.units > 1:
                self.state.units -= 1
                self.state.military_strength = max(0, self.state.military_strength - 5)

        # Discovery bonus
        if random.random() < 0.01:
            self.state.gold += 25

    def _simulate_combat(self):
        """Simulate combat between player and AI"""
        # Simple combat: stronger side wins
        player_strength = self.state.military_strength + self.state.cities * 5
        ai_strength = self.ai_military + self.ai_cities * 5

        if player_strength > ai_strength:
            # Player wins - capture AI city
            if self.ai_cities > 1:
                self.ai_cities -= 1
                self.state.cities += 1
                self.state.score += 50
        else:
            # AI wins - lose player city
            if self.state.cities > 1:
                self.state.cities -= 1
                self.ai_cities += 1

        # Both sides lose military strength
        self.state.military_strength = max(0, self.state.military_strength - 20)
        self.ai_military = max(0, self.ai_military - 20)

    def _calculate_reward(self, old_state: GameState, new_state: GameState) -> float:
        """Calculate reward for state transition"""
        reward = 0.0

        # Reward for score increase
        score_delta = new_state.score - old_state.score
        reward += score_delta * 0.1

        # Reward for new cities
        cities_delta = new_state.cities - old_state.cities
        reward += cities_delta * 10.0

        # Reward for population growth
        pop_delta = new_state.population - old_state.population
        reward += pop_delta * 0.5

        # Reward for technological progress
        tech_delta = new_state.techs_researched - old_state.techs_researched
        reward += tech_delta * 5.0

        # Small negative reward per turn (encourages efficiency)
        reward -= 0.01

        return reward

    def _check_game_end(self) -> bool:
        """Check if game has ended"""
        # Defeat: no cities
        if self.state.cities == 0:
            return True

        # Victory: AI eliminated
        if self.ai_cities == 0:
            self.state.score += 1000  # Victory bonus
            return True

        # Max turns
        if self.turn >= 200:
            return True

        return False

    def _calculate_year(self, turn: int) -> int:
        """Calculate calendar year from turn number"""
        # Simplified: ~20 years per turn in ancient era
        year = -4000 + (turn * 20)
        return year

    def get_current_state(self) -> GameState:
        """Get current game state"""
        return self.state


def test_simulator():
    """Test the simulator"""
    print("Testing FreeCiv Simulator...")
    print("=" * 60)

    # Create simulator
    sim = FreeCivSimulator(difficulty=DifficultyLevel.NORMAL)

    # Reset
    state = sim.reset()
    print(f"Initial state: Turn {state.turn}, Cities: {state.cities}")

    # Play some turns
    for turn in range(10):
        # Simple strategy: build cities when possible
        if state.cities < 5 and state.units > 0:
            action = FreeCivAction(
                action_type="build_city",
                parameters={}
            )
        else:
            action = FreeCivAction(
                action_type="set_rates",
                parameters={'science': 60, 'tax': 0}
            )

        state, reward, done, info = sim.step(action)

        print(f"Turn {turn+1}: Cities={state.cities}, "
              f"Pop={state.population}, Score={state.score}, "
              f"Reward={reward:.2f}")

        if done:
            print("Game ended!")
            break

    print("=" * 60)
    print("✓ Simulator test complete")


if __name__ == "__main__":
    test_simulator()
