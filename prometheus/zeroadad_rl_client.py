"""
0 A.D. RL Interface Client
Foundation for Prometheus v0.110-v0.119 integration with 0 A.D. RTS game

This module provides a Python wrapper for the 0 A.D. RL HTTP interface,
enabling external reinforcement learning agents to interact with the game.

Based on:
- 0 A.D. Game AI Development API.pdf
- source/rlinterface/ C++ implementation
- source/tools/rlclient/python/ reference client
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import requests
from enum import IntEnum

logger = logging.getLogger(__name__)


class CommandType(IntEnum):
    """Command types supported by 0 A.D. RL interface"""
    WALK = 0
    ATTACK_MOVE = 1
    ATTACK = 2
    GARRISON = 3
    UNGARRISON = 4
    GATHER = 5
    RETURN_RESOURCE = 6
    REPAIR = 7
    TRAIN = 8
    RESEARCH = 9
    BUILD = 10
    DELETE = 11
    STOP = 12
    GUARD = 13


@dataclass
class GameState:
    """Representation of 0 A.D. game state snapshot"""
    turn: int
    player_id: int
    resources: Dict[str, float]  # food, wood, stone, metal
    population: Dict[str, int]  # current, max
    entities: List[Dict[str, Any]]  # all visible entities
    template_list: List[str]  # available unit/building templates
    tech_list: List[str]  # available technologies
    victory: Optional[bool] = None

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'GameState':
        """Parse JSON response from RL interface into GameState"""
        return cls(
            turn=data.get('turn', 0),
            player_id=data.get('player', 0),
            resources=data.get('resources', {}),
            population=data.get('population', {'current': 0, 'max': 200}),
            entities=data.get('entities', []),
            template_list=data.get('templates', []),
            tech_list=data.get('techs', []),
            victory=data.get('victory')
        )


class ZeroADRLClient:
    """
    Client for 0 A.D. RL HTTP interface

    Usage:
        client = ZeroADRLClient(host='localhost', port=6000)
        client.connect()

        while not client.is_game_over():
            state = client.get_state()
            # ... agent decision making ...
            client.send_command(entity_id, CommandType.WALK, target_x, target_z)
            client.step()
    """

    def __init__(self, host: str = 'localhost', port: int = 6000, timeout: float = 10.0):
        """
        Initialize RL client

        Args:
            host: 0 A.D. server hostname
            port: RL interface port (default 6000)
            timeout: HTTP request timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"
        self.session = requests.Session()
        self.connected = False
        self._game_over = False

    def connect(self) -> bool:
        """
        Establish connection to 0 A.D. RL interface

        Returns:
            True if connection successful

        Raises:
            ConnectionError: If cannot connect to RL interface
        """
        try:
            response = self.session.get(
                f"{self.base_url}/status",
                timeout=self.timeout
            )
            if response.status_code == 200:
                self.connected = True
                logger.info(f"✅ Connected to 0 A.D. RL interface at {self.base_url}")
                return True
            else:
                raise ConnectionError(f"HTTP {response.status_code}: {response.text}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to connect to 0 A.D. RL interface: {e}")

    def get_state(self) -> GameState:
        """
        Query current game state

        Returns:
            GameState object with current snapshot

        Raises:
            RuntimeError: If not connected or request fails
        """
        if not self.connected:
            raise RuntimeError("Not connected to RL interface. Call connect() first.")

        try:
            response = self.session.get(
                f"{self.base_url}/state",
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            state = GameState.from_json(data)

            # Check for game over condition
            if state.victory is not None:
                self._game_over = True
                logger.info(f"🏁 Game over! Victory: {state.victory}")

            return state

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to get game state: {e}")

    def send_command(
        self,
        entity_ids: List[int],
        command_type: CommandType,
        target_id: Optional[int] = None,
        x: Optional[float] = None,
        z: Optional[float] = None,
        template: Optional[str] = None,
        tech: Optional[str] = None,
        queued: bool = False
    ) -> bool:
        """
        Send command to game entities

        Args:
            entity_ids: List of entity IDs to command
            command_type: Type of command (walk, attack, train, etc.)
            target_id: Target entity ID (for attack, garrison, etc.)
            x, z: Target coordinates (for walk, build, etc.)
            template: Unit/building template name (for train, build)
            tech: Technology name (for research)
            queued: Whether to queue command (default: replace current)

        Returns:
            True if command accepted
        """
        if not self.connected:
            raise RuntimeError("Not connected to RL interface. Call connect() first.")

        # Build command payload
        payload = {
            'entities': entity_ids,
            'type': int(command_type),
            'queued': queued
        }

        # Add optional parameters based on command type
        if target_id is not None:
            payload['target'] = target_id
        if x is not None and z is not None:
            payload['x'] = x
            payload['z'] = z
        if template is not None:
            payload['template'] = template
        if tech is not None:
            payload['tech'] = tech

        try:
            response = self.session.post(
                f"{self.base_url}/command",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send command: {e}")
            return False

    def step(self, num_turns: int = 1) -> None:
        """
        Advance game simulation by N turns

        Args:
            num_turns: Number of simulation turns to advance (default 1)
        """
        if not self.connected:
            raise RuntimeError("Not connected to RL interface. Call connect() first.")

        try:
            response = self.session.post(
                f"{self.base_url}/step",
                json={'turns': num_turns},
                timeout=self.timeout
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to step simulation: {e}")

    def reset_game(self, scenario: Optional[str] = None) -> GameState:
        """
        Reset game to initial state

        Args:
            scenario: Optional scenario/map name to load

        Returns:
            Initial game state
        """
        if not self.connected:
            raise RuntimeError("Not connected to RL interface. Call connect() first.")

        payload = {}
        if scenario:
            payload['scenario'] = scenario

        try:
            response = self.session.post(
                f"{self.base_url}/reset",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            self._game_over = False
            return self.get_state()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to reset game: {e}")

    def is_game_over(self) -> bool:
        """Check if game has ended"""
        return self._game_over

    def disconnect(self) -> None:
        """Close connection to RL interface"""
        self.session.close()
        self.connected = False
        logger.info("Disconnected from 0 A.D. RL interface")

    def get_entity_by_id(self, entity_id: int, state: GameState) -> Optional[Dict[str, Any]]:
        """
        Find entity in state by ID

        Args:
            entity_id: Entity ID to find
            state: Current game state

        Returns:
            Entity dict if found, None otherwise
        """
        for entity in state.entities:
            if entity.get('id') == entity_id:
                return entity
        return None

    def get_entities_by_type(
        self,
        entity_type: str,
        state: GameState,
        player_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Find all entities of a given type

        Args:
            entity_type: Entity template name (e.g., 'units/spart/infantry_spearman_b')
            state: Current game state
            player_id: Filter by player (None = all players)

        Returns:
            List of matching entities
        """
        matches = []
        for entity in state.entities:
            if entity.get('template') == entity_type:
                if player_id is None or entity.get('player') == player_id:
                    matches.append(entity)
        return matches

    def get_idle_units(self, state: GameState) -> List[Dict[str, Any]]:
        """
        Find all idle military units for current player

        Args:
            state: Current game state

        Returns:
            List of idle units
        """
        idle = []
        for entity in state.entities:
            if (entity.get('player') == state.player_id and
                entity.get('unitAI') and
                entity.get('idle', False)):
                idle.append(entity)
        return idle

    def get_resource_count(self, resource_type: str, state: GameState) -> float:
        """
        Get current count of a resource type

        Args:
            resource_type: 'food', 'wood', 'stone', or 'metal'
            state: Current game state

        Returns:
            Resource count
        """
        return state.resources.get(resource_type, 0.0)


# Convenience functions for common operations

def create_training_scenario_client(scenario: str = "Skirmish") -> ZeroADRLClient:
    """
    Create and connect a client for training scenarios

    Args:
        scenario: Scenario name to load

    Returns:
        Connected ZeroADRLClient
    """
    client = ZeroADRLClient()
    client.connect()
    client.reset_game(scenario)
    return client


if __name__ == '__main__':
    # Test basic connectivity
    logging.basicConfig(level=logging.INFO)

    print("0 A.D. RL Interface Client Test")
    print("=" * 50)
    print("\nEnsure 0 A.D. is running with:")
    print("  pyrogenesis -autostart=scenarios/test -rl-interface=localhost:6000")
    print()

    try:
        client = ZeroADRLClient()
        print("Connecting to RL interface...")
        client.connect()

        print("Getting initial state...")
        state = client.get_state()
        print(f"  Turn: {state.turn}")
        print(f"  Player ID: {state.player_id}")
        print(f"  Resources: {state.resources}")
        print(f"  Population: {state.population}")
        print(f"  Entity count: {len(state.entities)}")

        print("\n✅ Client test successful!")

        client.disconnect()

    except Exception as e:
        print(f"\n❌ Client test failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Is 0 A.D. installed?")
        print("  2. Is the game running with -rl-interface flag?")
        print("  3. Is port 6000 accessible?")
