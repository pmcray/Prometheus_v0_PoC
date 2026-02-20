"""
OpenRA Environment Interface — Prometheus v0.97

Provides a Python game-loop interface to OpenRA (the open-source
Command & Conquer engine).  Two modes are available, selected at
construction time:

  SimulatedMode  (default, no external dependency)
    A self-contained discrete-event simulator that reproduces the
    economy, production, and combat mechanics of an OpenRA Red Alert
    skirmish game.  Sufficient for curriculum training and unit tests
    without a running OpenRA server.

  LiveMode  (optional, requires openra-python bridge)
    Wraps the openra-python WebSocket API so the same agent code drives
    a real OpenRA process.  Falls back to SimulatedMode if the bridge
    package is absent.

The interface follows the standard Gym step/reset contract so that
agents and benchmarks are agnostic about which backend is active.

Game State
----------
The environment exposes a flat feature vector (OpenRAGameState.to_vector())
together with a structured dataclass for agents that need human-readable
access to individual fields.

Reward function
---------------
  +5.0   per enemy unit destroyed
  -3.0   per own unit lost
  +10.0  per enemy building destroyed
  -7.0   per own building lost
  +0.1   per resource credit harvested (normalised)
  -0.01  per timestep (efficiency incentive)
  +100.0 victory bonus
  -50.0  defeat penalty
"""

import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FEATURE_SIZE = 20          # dimensionality of get_state().to_vector()
MAX_STEPS_PER_GAME = 3000  # hard ceiling for one episode

# Difficulty presets (multiplier applied to AI production speed)
DIFFICULTY_SPEED = {
    "easy":   0.5,
    "medium": 1.0,
    "hard":   1.5,
    "expert": 2.5,
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class GameResult(Enum):
    ONGOING  = "ongoing"
    VICTORY  = "victory"
    DEFEAT   = "defeat"
    DRAW     = "draw"


@dataclass
class OpenRAGameState:
    """
    Snapshot of one OpenRA skirmish game from the agent's perspective.

    All numeric fields are normalised to [0, 1] (or small non-negative
    integers) so that to_vector() produces a bounded feature vector.
    """
    # --- Economy ---
    credits: float = 0.0           # 0–5000  (normalised: /5000)
    income_rate: float = 0.0       # harvesters * efficiency (normalised)

    # --- Own forces ---
    own_infantry:   int = 0
    own_vehicles:   int = 0
    own_aircraft:   int = 0
    own_buildings:  int = 0
    own_harvesters: int = 0

    # --- Enemy forces (estimated) ---
    enemy_infantry:  int = 0
    enemy_vehicles:  int = 0
    enemy_aircraft:  int = 0
    enemy_buildings: int = 0

    # --- Map control ---
    map_control_pct: float = 0.5   # fraction of the map controlled [0,1]
    resource_pct:    float = 1.0   # remaining resource nodes [0,1]

    # --- Attrition tracking ---
    own_units_lost:    int = 0
    enemy_units_lost:  int = 0
    own_buildings_lost:    int = 0
    enemy_buildings_lost:  int = 0

    # --- Meta ---
    game_step: int = 0
    game_result: GameResult = GameResult.ONGOING

    def to_vector(self) -> np.ndarray:
        """Return normalised 20-D feature vector."""
        return np.array([
            self.credits / 5000.0,
            self.income_rate,
            self.own_infantry   / 20.0,
            self.own_vehicles   / 10.0,
            self.own_aircraft   /  5.0,
            self.own_buildings  /  8.0,
            self.own_harvesters /  4.0,
            self.enemy_infantry  / 20.0,
            self.enemy_vehicles  / 10.0,
            self.enemy_aircraft  /  5.0,
            self.enemy_buildings /  8.0,
            self.map_control_pct,
            self.resource_pct,
            self.own_units_lost    / 30.0,
            self.enemy_units_lost  / 30.0,
            self.own_buildings_lost   / 8.0,
            self.enemy_buildings_lost / 8.0,
            self.game_step / MAX_STEPS_PER_GAME,
            1.0 if self.game_result == GameResult.VICTORY else 0.0,
            1.0 if self.game_result == GameResult.DEFEAT  else 0.0,
        ], dtype=float)

    def total_own_strength(self) -> float:
        return (self.own_infantry * 1.0 +
                self.own_vehicles * 2.0 +
                self.own_aircraft * 3.0 +
                self.own_buildings * 5.0)

    def total_enemy_strength(self) -> float:
        return (self.enemy_infantry * 1.0 +
                self.enemy_vehicles * 2.0 +
                self.enemy_aircraft * 3.0 +
                self.enemy_buildings * 5.0)


# Action space:  discrete integer → (action_type, sub_arg)
# 0  No-op
# 1  Build infantry
# 2  Build vehicle
# 3  Build aircraft
# 4  Build harvester
# 5  Expand (build construction yard)
# 6  Attack enemy infantry cluster
# 7  Attack enemy vehicle cluster
# 8  Attack enemy aircraft
# 9  Attack enemy buildings
# 10 Defend base
# 11 Rush all-in attack
# 12 Harvest resources (redirect harvesters)
# 13 Repair buildings
# 14 Recon (map scouting)

NUM_ACTIONS = 15

ACTION_NAMES = [
    "no_op", "build_infantry", "build_vehicle", "build_aircraft",
    "build_harvester", "expand", "attack_infantry", "attack_vehicle",
    "attack_aircraft", "attack_buildings", "defend", "rush",
    "harvest", "repair", "recon",
]


# ---------------------------------------------------------------------------
# Simulated backend
# ---------------------------------------------------------------------------

class _SimulatedOpenRA:
    """
    Discrete-event simulator for an OpenRA Red Alert 1v1 skirmish.

    Internally advances the game by one "tick" per step() call.
    Each tick ≈ 0.5 real seconds of OpenRA game time at normal speed.

    The simulator is intentionally lightweight: it models unit counts,
    resource flow, and stochastic combat resolution rather than full
    spatial simulation.  This is enough for curriculum training and
    offline evaluation without requiring an OpenRA installation.
    """

    def __init__(self, difficulty: str = "medium", seed: Optional[int] = None):
        self.difficulty = difficulty
        self._ai_speed = DIFFICULTY_SPEED.get(difficulty, 1.0)
        self._rng = np.random.RandomState(seed)
        self.state: OpenRAGameState = OpenRAGameState()
        self._step_count = 0
        self._reset_state()

    # ------------------------------------------------------------------
    # Environment API
    # ------------------------------------------------------------------

    def reset(self) -> OpenRAGameState:
        self._step_count = 0
        self._reset_state()
        return self._copy_state()

    def step(self, action: int) -> Tuple[OpenRAGameState, float, bool, Dict]:
        """
        Advance the simulation by one tick and apply agent action.

        Returns (new_state, reward, done, info).
        """
        assert 0 <= action < NUM_ACTIONS, f"Invalid action {action}"

        prev_state = self._copy_state()
        self._step_count += 1
        self.state.game_step = self._step_count

        # --- Economy tick ---
        self._economy_tick()

        # --- Apply agent action ---
        self._apply_action(action)

        # --- AI opponent turn ---
        self._ai_turn()

        # --- Stochastic combat ---
        self._combat_tick()

        # --- Map control update ---
        self._update_map_control()

        # --- Check termination ---
        done = self._check_termination()

        # --- Reward ---
        reward = self._compute_reward(prev_state, done)

        info = {
            "step": self._step_count,
            "result": self.state.game_result.value,
            "own_strength": self.state.total_own_strength(),
            "enemy_strength": self.state.total_enemy_strength(),
        }

        return self._copy_state(), reward, done, info

    # ------------------------------------------------------------------
    # Internal simulation
    # ------------------------------------------------------------------

    def _reset_state(self):
        """Place both sides at starting conditions."""
        self.state = OpenRAGameState(
            credits=1500.0,
            income_rate=0.1,
            own_infantry=4,
            own_vehicles=1,
            own_aircraft=0,
            own_buildings=3,
            own_harvesters=1,
            enemy_infantry=4,
            enemy_vehicles=1,
            enemy_aircraft=0,
            enemy_buildings=3,
            map_control_pct=0.5,
            resource_pct=1.0,
        )

    def _economy_tick(self):
        """Harvest resources; income ~ harvesters × resource availability."""
        if self.state.resource_pct <= 0:
            return
        harvested = self.state.own_harvesters * 8.0 * self.state.resource_pct
        self.state.credits = min(5000.0, self.state.credits + harvested)
        self.state.income_rate = (self.state.own_harvesters *
                                   self.state.resource_pct / 4.0)
        # Slow depletion
        self.state.resource_pct = max(0.0, self.state.resource_pct - 0.0003)

    def _apply_action(self, action: int):
        """Apply agent's chosen action to the simulation state."""
        if action == 0:    # no_op
            pass

        elif action == 1:  # build_infantry
            cost = 100
            if self.state.credits >= cost and self.state.own_buildings >= 1:
                self.state.credits -= cost
                self.state.own_infantry += self._rng.randint(1, 3)

        elif action == 2:  # build_vehicle
            cost = 400
            if self.state.credits >= cost and self.state.own_buildings >= 2:
                self.state.credits -= cost
                self.state.own_vehicles += 1

        elif action == 3:  # build_aircraft
            cost = 800
            if self.state.credits >= cost and self.state.own_buildings >= 3:
                self.state.credits -= cost
                self.state.own_aircraft += 1

        elif action == 4:  # build_harvester
            cost = 1400
            if self.state.credits >= cost and self.state.own_harvesters < 3:
                self.state.credits -= cost
                self.state.own_harvesters += 1

        elif action == 5:  # expand (build a building)
            cost = 500
            if self.state.credits >= cost and self.state.own_buildings < 8:
                self.state.credits -= cost
                self.state.own_buildings += 1

        elif action == 6:  # attack infantry
            casualties = self._combat_roll(
                attacker_str=self.state.own_vehicles + self.state.own_infantry * 0.5,
                defender_str=self.state.enemy_infantry * 0.5,
            )
            self.state.enemy_infantry = max(0, self.state.enemy_infantry - casualties)
            self.state.enemy_units_lost += casualties
            own_loss = self._rng.binomial(n=max(1, self.state.own_infantry), p=0.08)
            self.state.own_infantry = max(0, self.state.own_infantry - own_loss)
            self.state.own_units_lost += own_loss

        elif action == 7:  # attack vehicles
            casualties = self._combat_roll(
                attacker_str=self.state.own_aircraft * 2 + self.state.own_vehicles,
                defender_str=self.state.enemy_vehicles,
            )
            self.state.enemy_vehicles = max(0, self.state.enemy_vehicles - casualties)
            self.state.enemy_units_lost += casualties

        elif action == 8:  # attack aircraft
            if self.state.enemy_aircraft > 0:
                shot_down = self._combat_roll(
                    attacker_str=self.state.own_infantry * 0.3,
                    defender_str=self.state.enemy_aircraft,
                )
                self.state.enemy_aircraft = max(0, self.state.enemy_aircraft - shot_down)
                self.state.enemy_units_lost += shot_down

        elif action == 9:  # attack buildings
            casualties = self._combat_roll(
                attacker_str=(self.state.own_vehicles * 2 +
                              self.state.own_aircraft * 3),
                defender_str=self.state.enemy_buildings * 2,
            )
            self.state.enemy_buildings = max(0, self.state.enemy_buildings - casualties)
            self.state.enemy_buildings_lost += casualties

        elif action == 10:  # defend base
            # Fortification: reduces incoming combat losses this tick
            self._fortified = True

        elif action == 11:  # rush all-in attack
            # Commit all units; higher casualties but bigger impact
            total_str = (self.state.own_infantry +
                         self.state.own_vehicles * 2 +
                         self.state.own_aircraft * 3)
            enemy_total = (self.state.enemy_infantry +
                           self.state.enemy_vehicles +
                           self.state.enemy_buildings)
            destroyed = self._combat_roll(total_str, enemy_total, amplified=True)
            enemy_units_hit = min(destroyed, self.state.enemy_infantry + self.state.enemy_vehicles)
            buildings_hit = max(0, destroyed - enemy_units_hit)
            self.state.enemy_infantry = max(0, self.state.enemy_infantry - enemy_units_hit // 2)
            self.state.enemy_vehicles  = max(0, self.state.enemy_vehicles  - enemy_units_hit // 3)
            self.state.enemy_buildings = max(0, self.state.enemy_buildings - buildings_hit)
            self.state.enemy_units_lost += enemy_units_hit
            self.state.enemy_buildings_lost += buildings_hit
            # Own casualties during rush
            own_loss = self._rng.binomial(n=max(1, self.state.own_infantry), p=0.25)
            self.state.own_infantry = max(0, self.state.own_infantry - own_loss)
            self.state.own_units_lost += own_loss

        elif action == 12:  # harvest (send idle infantry as makeshift harvesters)
            if self.state.own_harvesters < 3:
                extra_harvest = self.state.own_infantry * 2.0 * self.state.resource_pct
                self.state.credits = min(5000.0, self.state.credits + extra_harvest)

        elif action == 13:  # repair buildings
            cost = 200 * self.state.own_buildings_lost
            if cost > 0 and self.state.credits >= cost:
                self.state.credits -= cost
                repaired = min(self.state.own_buildings_lost, 2)
                self.state.own_buildings += repaired
                self.state.own_buildings_lost -= repaired

        elif action == 14:  # recon
            # Improve intelligence (small random scout bonuses)
            self.state.map_control_pct = min(
                1.0, self.state.map_control_pct + self._rng.uniform(0, 0.05)
            )

    def _ai_turn(self):
        """Simplified rule-based AI opponent."""
        ai_credits = getattr(self, '_ai_credits', 1500.0)
        ai_credits += self.state.enemy_buildings * 6.0 * self._ai_speed

        # AI production decisions based on difficulty-scaled speed
        if self._step_count % max(1, int(10 / self._ai_speed)) == 0:
            if ai_credits >= 100:
                self.state.enemy_infantry += self._rng.randint(0, 2)
                ai_credits -= 100
            if ai_credits >= 400 and self._rng.random() < 0.3:
                self.state.enemy_vehicles += 1
                ai_credits -= 400
            if (ai_credits >= 800 and self._rng.random() < 0.15 and
                    self._step_count > 300):
                self.state.enemy_aircraft += 1
                ai_credits -= 800

        # AI attacks periodically
        if self._step_count % max(1, int(20 / self._ai_speed)) == 0:
            self._ai_attack()

        self._ai_credits = min(5000.0, ai_credits)

    def _ai_attack(self):
        """AI launches an attack on the agent's units/buildings."""
        fortified = getattr(self, '_fortified', False)
        defense_mult = 0.5 if fortified else 1.0
        self._fortified = False

        if self.state.enemy_infantry > 2:
            loss = self._combat_roll(
                self.state.enemy_infantry * 0.5,
                self.state.own_infantry * defense_mult,
            )
            self.state.own_infantry = max(0, self.state.own_infantry - loss)
            self.state.own_units_lost += loss

        if self.state.enemy_vehicles > 0 and self._rng.random() < 0.4:
            loss = self._combat_roll(
                self.state.enemy_vehicles,
                self.state.own_vehicles * defense_mult + self.state.own_buildings,
            )
            self.state.own_vehicles = max(0, self.state.own_vehicles - loss)
            self.state.own_units_lost += loss

        # Occasional building strike
        if (self.state.enemy_aircraft > 0 or self.state.enemy_vehicles > 2):
            if self._rng.random() < 0.15:
                self.state.own_buildings = max(0, self.state.own_buildings - 1)
                self.state.own_buildings_lost += 1

    def _combat_tick(self):
        """Passive attrition between forces each tick."""
        if self.state.own_infantry > 0 and self.state.enemy_infantry > 0:
            own_loss = self._rng.binomial(
                n=self.state.own_infantry,
                p=min(0.9, 0.005 * self.state.enemy_infantry)
            )
            enemy_loss = self._rng.binomial(
                n=self.state.enemy_infantry,
                p=min(0.9, 0.005 * self.state.own_infantry)
            )
            self.state.own_infantry = max(0, self.state.own_infantry - own_loss)
            self.state.enemy_infantry = max(0, self.state.enemy_infantry - enemy_loss)
            self.state.own_units_lost   += own_loss
            self.state.enemy_units_lost += enemy_loss

    def _update_map_control(self):
        """Map control shifts toward the side with more field presence."""
        own_field = (self.state.own_infantry + self.state.own_vehicles * 2 +
                     self.state.own_aircraft * 3)
        enemy_field = (self.state.enemy_infantry + self.state.enemy_vehicles * 2 +
                       self.state.enemy_aircraft * 3)
        total = max(1, own_field + enemy_field)
        target = own_field / total
        # Smooth exponential moving average
        self.state.map_control_pct = (0.95 * self.state.map_control_pct +
                                       0.05 * target)

    def _check_termination(self) -> bool:
        """Determine if the game has ended."""
        # Victory: enemy has no buildings left
        if self.state.enemy_buildings <= 0:
            self.state.game_result = GameResult.VICTORY
            return True

        # Defeat: agent has no buildings left
        if self.state.own_buildings <= 0:
            self.state.game_result = GameResult.DEFEAT
            return True

        # Timeout
        if self._step_count >= MAX_STEPS_PER_GAME:
            # Whoever has more strength wins
            if self.state.total_own_strength() > self.state.total_enemy_strength() * 1.2:
                self.state.game_result = GameResult.VICTORY
            elif self.state.total_enemy_strength() > self.state.total_own_strength() * 1.2:
                self.state.game_result = GameResult.DEFEAT
            else:
                self.state.game_result = GameResult.DRAW
            return True

        return False

    def _compute_reward(self, prev: OpenRAGameState, done: bool) -> float:
        """Shaped reward incentivising efficient offense and defence."""
        r = 0.0
        # Combat rewards
        enemy_killed = self.state.enemy_units_lost - prev.enemy_units_lost
        own_lost     = self.state.own_units_lost   - prev.own_units_lost
        bld_destroyed = self.state.enemy_buildings_lost - prev.enemy_buildings_lost
        bld_lost      = self.state.own_buildings_lost   - prev.own_buildings_lost

        r += enemy_killed * 5.0
        r -= own_lost     * 3.0
        r += bld_destroyed * 10.0
        r -= bld_lost      *  7.0

        # Economy
        income_delta = self.state.credits - prev.credits
        if income_delta > 0:
            r += income_delta * 0.01

        # Time penalty (efficiency)
        r -= 0.01

        # Terminal bonuses
        if done:
            if self.state.game_result == GameResult.VICTORY:
                r += 100.0
            elif self.state.game_result == GameResult.DEFEAT:
                r -= 50.0

        return float(r)

    def _combat_roll(
        self,
        attacker_str: float,
        defender_str: float,
        amplified: bool = False,
    ) -> int:
        """
        Stochastic combat resolution.

        Returns number of defender casualties (units or buildings).
        """
        attacker_str = max(0.1, attacker_str)
        defender_str = max(0.1, defender_str)

        p_hit = attacker_str / (attacker_str + defender_str)
        if amplified:
            p_hit = min(0.95, p_hit * 1.5)

        n_trials = max(1, int(attacker_str * (2 if amplified else 1)))
        hits = self._rng.binomial(n=n_trials, p=min(0.95, p_hit))
        return int(hits // 2)

    def _copy_state(self) -> OpenRAGameState:
        import copy
        return copy.copy(self.state)


# ---------------------------------------------------------------------------
# Public environment wrapper
# ---------------------------------------------------------------------------

class OpenRAEnvironment:
    """
    Python environment interface to OpenRA.

    Automatically uses the simulated backend unless openra-python is
    installed and `mode='live'` is passed.

    Args:
        difficulty: "easy" | "medium" | "hard" | "expert"
        mode:       "simulated" | "live"
        seed:       RNG seed for the simulated backend.
        verbose:    Log step-level debug information.
    """

    def __init__(
        self,
        difficulty: str = "medium",
        mode: str = "simulated",
        seed: Optional[int] = None,
        verbose: bool = False,
    ):
        self.difficulty = difficulty
        self.mode = mode
        self.verbose = verbose

        # Try live backend; fall back gracefully
        self._backend: _SimulatedOpenRA
        if mode == "live":
            try:
                from openra_python import OpenRAClient  # type: ignore
                logger.info("Using live OpenRA backend")
                # Wrap the live client in the same interface
                self._backend = _LiveOpenRAWrapper(OpenRAClient(), difficulty)
            except ImportError:
                logger.warning(
                    "openra-python not installed; falling back to SimulatedMode. "
                    "Install with: pip install openra-python"
                )
                self._backend = _SimulatedOpenRA(difficulty=difficulty, seed=seed)
        else:
            self._backend = _SimulatedOpenRA(difficulty=difficulty, seed=seed)

        self._current_state: Optional[OpenRAGameState] = None
        self._episode_rewards: List[float] = []
        self._total_episodes: int = 0

    # ------------------------------------------------------------------
    # Gym-compatible API
    # ------------------------------------------------------------------

    def reset(self) -> OpenRAGameState:
        """Reset to a new game. Returns the initial GameState."""
        self._current_state = self._backend.reset()
        self._episode_rewards = []
        return self._current_state

    def step(
        self, action: int
    ) -> Tuple[OpenRAGameState, float, bool, Dict[str, Any]]:
        """
        Apply `action` and advance the game by one tick.

        Args:
            action: Integer in [0, NUM_ACTIONS).

        Returns:
            (new_state, reward, done, info)
        """
        if self._current_state is None:
            raise RuntimeError("Call reset() before step()")

        new_state, reward, done, info = self._backend.step(action)
        self._current_state = new_state
        self._episode_rewards.append(reward)

        if done:
            self._total_episodes += 1
            info["episode_return"] = sum(self._episode_rewards)

        if self.verbose:
            logger.debug(
                "step=%d action=%s(%d) reward=%.2f done=%s",
                new_state.game_step,
                ACTION_NAMES[action], action,
                reward, done,
            )

        return new_state, reward, done, info

    def get_state(self) -> Optional[OpenRAGameState]:
        """Return the current game state without advancing."""
        return self._current_state

    def get_observation(self) -> np.ndarray:
        """Return the current state as a flat feature vector."""
        if self._current_state is None:
            return np.zeros(FEATURE_SIZE, dtype=float)
        return self._current_state.to_vector()

    def render(self, mode: str = "text") -> Optional[str]:
        """ASCII snapshot of the current game state."""
        if self._current_state is None:
            return "No active game."
        s = self._current_state
        lines = [
            f"=== OpenRA [{self.difficulty.upper()}] Step {s.game_step} ===",
            f"  Credits: {s.credits:.0f}  |  Income: {s.income_rate:.2f}/tick",
            f"  OWN:    inf={s.own_infantry:2d}  veh={s.own_vehicles:2d}  "
            f"air={s.own_aircraft:2d}  bld={s.own_buildings:2d}  harv={s.own_harvesters}",
            f"  ENEMY:  inf={s.enemy_infantry:2d}  veh={s.enemy_vehicles:2d}  "
            f"air={s.enemy_aircraft:2d}  bld={s.enemy_buildings:2d}",
            f"  Map control: {s.map_control_pct:.1%}  "
            f"Resources: {s.resource_pct:.1%}",
            f"  Losses — own: {s.own_units_lost} units, {s.own_buildings_lost} bld  |  "
            f"enemy: {s.enemy_units_lost} units, {s.enemy_buildings_lost} bld",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def num_actions(self) -> int:
        return NUM_ACTIONS

    @property
    def observation_size(self) -> int:
        return FEATURE_SIZE

    @property
    def total_episodes(self) -> int:
        return self._total_episodes


# ---------------------------------------------------------------------------
# Stub for live backend (filled when openra-python is installed)
# ---------------------------------------------------------------------------

class _LiveOpenRAWrapper:
    """Thin wrapper around openra-python to match _SimulatedOpenRA API."""

    def __init__(self, client, difficulty: str):
        self._client = client
        self.difficulty = difficulty

    def reset(self) -> OpenRAGameState:
        raw = self._client.reset()
        return _parse_live_state(raw)

    def step(self, action: int) -> Tuple[OpenRAGameState, float, bool, Dict]:
        raw_obs, reward, done, info = self._client.step(action)
        return _parse_live_state(raw_obs), float(reward), bool(done), info


def _parse_live_state(raw: Any) -> OpenRAGameState:
    """Convert openra-python raw observation dict to OpenRAGameState."""
    if isinstance(raw, dict):
        return OpenRAGameState(
            credits      = float(raw.get("credits", 0)),
            own_infantry = int(raw.get("own_infantry", 0)),
            own_vehicles = int(raw.get("own_vehicles", 0)),
            own_aircraft = int(raw.get("own_aircraft", 0)),
            own_buildings= int(raw.get("own_buildings", 0)),
            own_harvesters=int(raw.get("own_harvesters", 0)),
            enemy_infantry = int(raw.get("enemy_infantry", 0)),
            enemy_vehicles = int(raw.get("enemy_vehicles", 0)),
            enemy_aircraft = int(raw.get("enemy_aircraft", 0)),
            enemy_buildings= int(raw.get("enemy_buildings", 0)),
        )
    # Unknown format: return empty state
    return OpenRAGameState()
