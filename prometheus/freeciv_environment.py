"""
FreeCiv Environment Wrapper for Prometheus

Provides interface to FreeCiv game engine for CRLS learning loop.
Supports both human-readable observations and structured game state access.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import socket
import json
import time


class DifficultyLevel(Enum):
    """FreeCiv AI difficulty levels"""
    NOVICE = "novice"
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    CHEATING = "cheating"
    EXPERIMENTAL = "experimental"


class UnitType(Enum):
    """Common FreeCiv unit types"""
    SETTLERS = "Settlers"
    WORKERS = "Workers"
    WARRIORS = "Warriors"
    PHALANX = "Phalanx"
    ARCHERS = "Archers"
    LEGION = "Legion"
    PIKEMEN = "Pikemen"
    MUSKETEERS = "Musketeers"
    RIFLEMEN = "Riflemen"
    CAVALRY = "Cavalry"
    ARTILLERY = "Artillery"
    ARMOR = "Armor"
    BOMBER = "Bomber"
    BATTLESHIP = "Battleship"
    CARRIER = "Carrier"


class BuildingType(Enum):
    """Common FreeCiv building types"""
    PALACE = "Palace"
    GRANARY = "Granary"
    BARRACKS = "Barracks"
    LIBRARY = "Library"
    MARKETPLACE = "Marketplace"
    TEMPLE = "Temple"
    AQUEDUCT = "Aqueduct"
    BANK = "Bank"
    UNIVERSITY = "University"
    FACTORY = "Factory"
    POWER_PLANT = "Power Plant"
    AIRPORT = "Airport"


@dataclass
class GameState:
    """Current state of FreeCiv game"""
    turn: int
    year: int
    score: int
    population: int
    cities: int
    units: int
    techs_researched: int
    gold: int
    science_rate: int
    tax_rate: int
    luxury_rate: int

    # Detailed state
    cities_data: List[Dict[str, Any]] = field(default_factory=list)
    units_data: List[Dict[str, Any]] = field(default_factory=list)
    known_tiles: Dict[Tuple[int, int], Dict[str, Any]] = field(default_factory=dict)

    # Strategic metrics
    total_production: int = 0
    total_science: int = 0
    military_strength: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'turn': self.turn,
            'year': self.year,
            'score': self.score,
            'population': self.population,
            'cities': self.cities,
            'units': self.units,
            'techs_researched': self.techs_researched,
            'gold': self.gold,
            'science_rate': self.science_rate,
            'tax_rate': self.tax_rate,
            'luxury_rate': self.luxury_rate,
            'total_production': self.total_production,
            'total_science': self.total_science,
            'military_strength': self.military_strength
        }


@dataclass
class FreeCivAction:
    """An action to take in FreeCiv"""
    action_type: str  # "move_unit", "build_city", "build_unit", "research_tech", etc.
    parameters: Dict[str, Any]

    def to_command(self) -> str:
        """Convert to FreeCiv server command"""
        # This will be implemented based on FreeCiv's command protocol
        if self.action_type == "move_unit":
            return f"/moveunit {self.parameters['unit_id']} {self.parameters['x']} {self.parameters['y']}"
        elif self.action_type == "build_city":
            return f"/buildcity {self.parameters['settler_id']}"
        elif self.action_type == "build_unit":
            return f"/build {self.parameters['city_id']} {self.parameters['unit_type']}"
        elif self.action_type == "research_tech":
            return f"/research {self.parameters['tech_name']}"
        elif self.action_type == "set_rates":
            return f"/set taxrate {self.parameters['tax']} sciencerate {self.parameters['science']}"
        return ""


class FreeCivEnvironment:
    """
    Environment wrapper for FreeCiv game

    Manages FreeCiv server process and provides interface for:
    - Starting games with specified AI difficulty
    - Executing actions
    - Observing game state
    - Detecting game end conditions
    """

    def __init__(self, server_host: str = "localhost", server_port: int = 5556):
        self.server_host = server_host
        self.server_port = server_port
        self.server_process = None
        self.socket = None
        self.game_active = False
        self.current_state = None
        self.action_history = []

    def start_server(self, difficulty: DifficultyLevel = DifficultyLevel.NORMAL,
                     ruleset: str = "classic", map_size: str = "normal"):
        """
        Start FreeCiv server process

        Args:
            difficulty: AI opponent difficulty
            ruleset: Game ruleset (classic, civ2civ3, experimental)
            map_size: Map size (tiny, small, normal, large, huge)
        """
        # Command to start FreeCiv server
        cmd = [
            "freeciv-server",
            "--port", str(self.server_port),
            "--Ruleset", ruleset,
            "--size", map_size,
            "--ai-difficulty", difficulty.value,
            "--Announce", "none"  # Don't announce to metaserver
        ]

        try:
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for server to start
            time.sleep(2)

            # Connect to server
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))

            return True

        except Exception as e:
            print(f"Failed to start FreeCiv server: {e}")
            return False

    def stop_server(self):
        """Stop FreeCiv server"""
        if self.socket:
            self.socket.close()
            self.socket = None

        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait(timeout=5)
            self.server_process = None

    def reset(self, difficulty: DifficultyLevel = DifficultyLevel.NORMAL) -> GameState:
        """
        Reset environment and start new game

        Args:
            difficulty: AI difficulty level

        Returns:
            Initial game state
        """
        # Stop existing game
        if self.game_active:
            self.stop_server()

        # Start new server
        self.start_server(difficulty=difficulty)

        # Create/join game
        self._send_command("/take Prometheus")  # Take control of player
        self._send_command("/set aifill 7")  # Add AI opponents
        self._send_command("/set timeout -1")  # No turn timeout
        self._send_command("/start")  # Start game

        self.game_active = True
        self.action_history = []

        # Get initial state
        self.current_state = self._get_game_state()

        return self.current_state

    def step(self, action: FreeCivAction) -> Tuple[GameState, float, bool, Dict[str, Any]]:
        """
        Execute action and advance game state

        Args:
            action: Action to execute

        Returns:
            (new_state, reward, done, info)
        """
        if not self.game_active:
            raise RuntimeError("Game not active. Call reset() first.")

        # Execute action
        command = action.to_command()
        response = self._send_command(command)

        # Record action
        self.action_history.append({
            'turn': self.current_state.turn if self.current_state else 0,
            'action': action.action_type,
            'parameters': action.parameters,
            'response': response
        })

        # Advance turn if needed
        self._send_command("/endturn")

        # Get new state
        new_state = self._get_game_state()
        old_state = self.current_state
        self.current_state = new_state

        # Calculate reward
        reward = self._calculate_reward(old_state, new_state)

        # Check if game ended
        done = self._check_game_end()

        # Additional info
        info = {
            'turn': new_state.turn,
            'year': new_state.year,
            'score_delta': new_state.score - (old_state.score if old_state else 0)
        }

        return new_state, reward, done, info

    def _send_command(self, command: str) -> str:
        """
        Send command to FreeCiv server

        Args:
            command: Server command

        Returns:
            Server response
        """
        if not self.socket:
            return ""

        try:
            # Send command
            self.socket.sendall((command + "\n").encode())

            # Receive response
            response = self.socket.recv(4096).decode()

            return response

        except Exception as e:
            print(f"Command failed: {e}")
            return ""

    def _get_game_state(self) -> GameState:
        """
        Query current game state from server

        Returns:
            Current game state
        """
        # This is a simplified version - real implementation would parse
        # the actual FreeCiv protocol messages

        # Send info commands
        info = self._send_command("/show")

        # Parse response (simplified)
        # In reality, would parse structured data from server

        state = GameState(
            turn=0,
            year=0,
            score=0,
            population=0,
            cities=0,
            units=0,
            techs_researched=0,
            gold=0,
            science_rate=50,
            tax_rate=0,
            luxury_rate=50
        )

        # Parse actual values from server response
        # (This would be implemented based on FreeCiv protocol)

        return state

    def _calculate_reward(self, old_state: Optional[GameState],
                         new_state: GameState) -> float:
        """
        Calculate reward for transition

        Args:
            old_state: Previous state
            new_state: New state

        Returns:
            Reward value
        """
        if not old_state:
            return 0.0

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
        """
        Check if game has ended

        Returns:
            True if game ended
        """
        # Check for victory/defeat conditions
        # (Simplified - would check actual game state)

        if not self.current_state:
            return False

        # Game ends if we have no cities (defeat)
        if self.current_state.cities == 0:
            return True

        # Game ends after certain number of turns (for testing)
        if self.current_state.turn >= 500:
            return True

        return False

    def get_legal_actions(self) -> List[FreeCivAction]:
        """
        Get list of currently legal actions

        Returns:
            List of legal actions
        """
        actions = []

        if not self.current_state:
            return actions

        # Always legal: adjust rates
        actions.append(FreeCivAction(
            action_type="set_rates",
            parameters={'tax': 0, 'science': 100}
        ))

        # Add actions based on current units and cities
        # (This would be expanded based on actual game state)

        return actions

    def render(self, mode: str = "human") -> Optional[str]:
        """
        Render current game state

        Args:
            mode: Render mode ("human", "ansi")

        Returns:
            String representation if mode="ansi"
        """
        if not self.current_state:
            return None

        lines = [
            "=" * 60,
            f"FreeCiv Game - Turn {self.current_state.turn} ({self.current_state.year} AD)",
            "=" * 60,
            f"Score: {self.current_state.score}",
            f"Cities: {self.current_state.cities} | Population: {self.current_state.population}",
            f"Units: {self.current_state.units}",
            f"Technologies: {self.current_state.techs_researched}",
            f"Gold: {self.current_state.gold}",
            f"Rates - Science: {self.current_state.science_rate}% | "
            f"Tax: {self.current_state.tax_rate}% | "
            f"Luxury: {self.current_state.luxury_rate}%",
            "=" * 60
        ]

        output = "\n".join(lines)

        if mode == "human":
            print(output)
            return None
        else:
            return output


def test_environment():
    """Test the FreeCiv environment"""
    print("Testing FreeCiv Environment...")
    print("-" * 60)

    # Note: This test requires FreeCiv to be installed
    # Install with: sudo apt-get install freeciv-server

    env = FreeCivEnvironment()

    try:
        # Try to start server
        success = env.start_server(difficulty=DifficultyLevel.EASY)

        if success:
            print("✓ Server started successfully")

            # Reset and get initial state
            state = env.reset(difficulty=DifficultyLevel.EASY)
            print(f"✓ Initial state: Turn {state.turn}")

            # Render
            env.render(mode="human")

            # Clean up
            env.stop_server()
            print("✓ Server stopped")

        else:
            print("⚠ Could not start FreeCiv server (may not be installed)")
            print("  Install with: sudo apt-get install freeciv-server")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        env.stop_server()


if __name__ == "__main__":
    test_environment()
