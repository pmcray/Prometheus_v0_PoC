"""
OpenRA Strategy Agent — Prometheus v0.97

Provides two complementary agent classes for playing OpenRA skirmish games:

OpenRAStrategyAgent
    A parameterised strategy agent whose five continuous parameters can be
    evolved via `mutate()` and `crossover()`.  This mirrors the design of
    `MicroRTSStrategyAgent` so it plugs directly into the PrometheusStar
    curriculum runner.

    Parameters
    ----------
    aggression       float [0,1]  — 0 = turtles and builds; 1 = rushes early
    economy_focus    float [0,1]  — 0 = military spam; 1 = harvester/credit economy
    expansion_rate   float [0,1]  — 0 = holds base; 1 = expands buildings aggressively
    tech_priority    float [0,1]  — 0 = quantities (infantry); 1 = quality (aircraft)
    defense_bias     float [0,1]  — 0 = ignores defense; 1 = fortifies often

OpenRAAgentAdapter
    Wraps any Prometheus GamePlayingExpertAgent so it can play OpenRA.
    Converts the flat OpenRAGameState feature vector into an action integer
    using the wrapped agent's weight vector.

Factory functions
-----------------
create_openra_agent(agent_type)  → OpenRAStrategyAgent | OpenRAAgentAdapter
"""

import logging
from typing import Any, Dict, Optional

import numpy as np

from prometheus.openra_environment import (
    ACTION_NAMES,
    NUM_ACTIONS,
    OpenRAGameState,
    GameResult,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OpenRAStrategyAgent
# ---------------------------------------------------------------------------

class OpenRAStrategyAgent:
    """
    Parameterised RTS strategy agent for OpenRA.

    Action selection follows a three-phase game plan driven by the five
    strategy parameters.  The agent is compatible with the PrometheusStar
    evolutionary orchestrator: a population of agents is mutated and
    crossed-over across generations, with fitness measured by win rate
    against curriculum opponents.

    Args:
        strategy_params: Optional dict of parameter overrides.
    """

    # Action indices (must match openra_environment.ACTION_NAMES)
    _NO_OP          = 0
    _BUILD_INFANTRY = 1
    _BUILD_VEHICLE  = 2
    _BUILD_AIRCRAFT = 3
    _BUILD_HARVESTER= 4
    _EXPAND         = 5
    _ATTACK_INF     = 6
    _ATTACK_VEH     = 7
    _ATTACK_AIR     = 8
    _ATTACK_BLD     = 9
    _DEFEND         = 10
    _RUSH           = 11
    _HARVEST        = 12
    _REPAIR         = 13
    _RECON          = 14

    def __init__(self, strategy_params: Optional[Dict[str, float]] = None):
        self.params: Dict[str, float] = {
            "aggression":     0.5,  # 0=defensive, 1=aggressive
            "economy_focus":  0.5,  # 0=military, 1=economy
            "expansion_rate": 0.5,  # 0=hold base, 1=expand
            "tech_priority":  0.5,  # 0=infantry, 1=aircraft
            "defense_bias":   0.5,  # 0=ignore defense, 1=fortify
        }
        if strategy_params:
            for k, v in strategy_params.items():
                if k in self.params:
                    self.params[k] = float(np.clip(v, 0.0, 1.0))

        self.game_step: int = 0
        self._wins:   int = 0
        self._losses: int = 0
        self._draws:  int = 0

    # ------------------------------------------------------------------
    # Action selection
    # ------------------------------------------------------------------

    def select_action(self, observation: Any) -> int:
        """
        Choose an action given the current game state.

        Args:
            observation: OpenRAGameState or flat np.ndarray feature vector.

        Returns:
            Integer action in [0, NUM_ACTIONS).
        """
        self.game_step += 1

        # Accept both structured state and flat vector
        state = self._to_state(observation)
        if state is None:
            return self._NO_OP

        # Phase 1 — Early game: economy + base establishment  (steps 1–200)
        if self.game_step <= 200:
            return self._early_game(state)

        # Phase 2 — Mid game: unit production + tactical skirmishes (201–800)
        elif self.game_step <= 800:
            return self._mid_game(state)

        # Phase 3 — Late game: decisive engagement (800+)
        else:
            return self._late_game(state)

    def _early_game(self, state: OpenRAGameState) -> int:
        """Build economy and initial forces."""
        p = self.params

        # Always expand first if no buildings beyond HQ
        if state.own_buildings < 2 and state.credits >= 500:
            return self._EXPAND

        # Harvesters first if economy-focused and we can afford one
        if p["economy_focus"] > 0.6 and state.own_harvesters < 2 and state.credits >= 1400:
            return self._BUILD_HARVESTER

        # Light infantry to hold the base
        if state.own_infantry < 4 and state.credits >= 100:
            return self._BUILD_INFANTRY

        # Expansion opportunity
        if p["expansion_rate"] > 0.5 and state.own_buildings < 4 and state.credits >= 500:
            return self._EXPAND

        # Resource gathering if credits low
        if state.credits < 300:
            return self._HARVEST

        return self._BUILD_INFANTRY

    def _mid_game(self, state: OpenRAGameState) -> int:
        """Balance between production, map pressure, and base defence."""
        p = self.params
        rng = np.random

        # Repair damaged buildings
        if state.own_buildings_lost > 0 and state.credits >= 200 and p["defense_bias"] > 0.5:
            return self._REPAIR

        # Defend if under heavy pressure
        if (state.enemy_infantry > state.own_infantry * 1.5 or
                state.enemy_vehicles > state.own_vehicles * 1.5):
            if rng.random() < p["defense_bias"]:
                return self._DEFEND

        # Tech upgrade: aircraft if tech-priority high
        if p["tech_priority"] > 0.65 and state.own_aircraft < 2 and state.credits >= 800:
            return self._BUILD_AIRCRAFT

        # Vehicles
        if p["tech_priority"] > 0.35 and state.own_vehicles < 3 and state.credits >= 400:
            return self._BUILD_VEHICLE

        # Attack if we have numerical advantage
        own_str   = state.total_own_strength()
        enemy_str = state.total_enemy_strength()

        if own_str > enemy_str * (1.5 - p["aggression"]):
            # Choose attack target
            if state.enemy_aircraft > 0:
                return self._ATTACK_AIR
            if state.enemy_vehicles > state.enemy_infantry:
                return self._ATTACK_VEH
            if state.enemy_infantry > 0:
                return self._ATTACK_INF
            return self._ATTACK_BLD

        # Build economy if credits low
        if state.credits < 400:
            return self._HARVEST

        # Infantry filler
        if state.own_infantry < 6 and state.credits >= 100:
            return self._BUILD_INFANTRY

        return self._NO_OP

    def _late_game(self, state: OpenRAGameState) -> int:
        """Commit to decisive action."""
        p = self.params
        own_str   = state.total_own_strength()
        enemy_str = state.total_enemy_strength()

        # Aggressive: all-in rush
        if p["aggression"] > 0.6 and own_str > enemy_str * 0.8:
            return self._RUSH

        # Attack enemy buildings if no field units remain
        if state.enemy_infantry == 0 and state.enemy_vehicles == 0:
            return self._ATTACK_BLD

        # Pick most lucrative target
        if state.enemy_buildings > 0 and own_str > enemy_str:
            return self._ATTACK_BLD

        # Rebuild if badly damaged
        if state.own_buildings < 2 and state.credits >= 500:
            return self._EXPAND

        # Defensive late game
        if p["defense_bias"] > 0.6:
            return self._DEFEND

        return self._ATTACK_INF

    # ------------------------------------------------------------------
    # Observation coercion
    # ------------------------------------------------------------------

    @staticmethod
    def _to_state(obs: Any) -> Optional[OpenRAGameState]:
        """
        Convert observation to OpenRAGameState.

        Accepts: OpenRAGameState | np.ndarray | dict | None.
        """
        if obs is None:
            return None
        if isinstance(obs, OpenRAGameState):
            return obs
        if isinstance(obs, np.ndarray):
            # Reconstruct state from feature vector (best-effort)
            s = OpenRAGameState()
            if len(obs) >= 20:
                s.credits         = float(obs[0]) * 5000.0
                s.income_rate     = float(obs[1])
                s.own_infantry    = int(obs[2] * 20)
                s.own_vehicles    = int(obs[3] * 10)
                s.own_aircraft    = int(obs[4] *  5)
                s.own_buildings   = int(obs[5] *  8)
                s.own_harvesters  = int(obs[6] *  4)
                s.enemy_infantry  = int(obs[7] * 20)
                s.enemy_vehicles  = int(obs[8] * 10)
                s.enemy_aircraft  = int(obs[9] *  5)
                s.enemy_buildings = int(obs[10] * 8)
                s.map_control_pct = float(obs[11])
                s.resource_pct    = float(obs[12])
                s.own_units_lost  = int(obs[13] * 30)
                s.enemy_units_lost= int(obs[14] * 30)
                s.own_buildings_lost  = int(obs[15] * 8)
                s.enemy_buildings_lost= int(obs[16] * 8)
                s.game_step = int(obs[17] * 3000)
            return s
        if isinstance(obs, dict):
            return OpenRAGameState(
                credits       = float(obs.get("credits", 0)),
                own_infantry  = int(obs.get("own_infantry", 0)),
                own_vehicles  = int(obs.get("own_vehicles", 0)),
                own_aircraft  = int(obs.get("own_aircraft", 0)),
                own_buildings = int(obs.get("own_buildings", 0)),
                own_harvesters= int(obs.get("own_harvesters", 0)),
                enemy_infantry = int(obs.get("enemy_infantry", 0)),
                enemy_vehicles = int(obs.get("enemy_vehicles", 0)),
                enemy_aircraft = int(obs.get("enemy_aircraft", 0)),
                enemy_buildings= int(obs.get("enemy_buildings", 0)),
            )
        logger.warning("Unknown observation type: %s — returning no-op", type(obs))
        return None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self):
        """Reset per-episode counters."""
        self.game_step = 0

    def record_result(self, result: GameResult):
        """Tally win/loss/draw for fitness calculation."""
        if result == GameResult.VICTORY:
            self._wins += 1
        elif result == GameResult.DEFEAT:
            self._losses += 1
        else:
            self._draws += 1

    @property
    def win_rate(self) -> float:
        total = self._wins + self._losses + self._draws
        return self._wins / total if total > 0 else 0.0

    # ------------------------------------------------------------------
    # Evolutionary operators
    # ------------------------------------------------------------------

    def mutate(self, mutation_rate: float = 0.2) -> "OpenRAStrategyAgent":
        """
        Return a new agent with Gaussian-perturbed parameters.

        Args:
            mutation_rate: Std-dev of the Gaussian perturbation (before clipping).

        Returns:
            Mutated OpenRAStrategyAgent (independent copy).
        """
        new_params = {}
        for key, val in self.params.items():
            if np.random.random() < mutation_rate:
                delta = np.random.normal(0, 0.2)
                new_params[key] = float(np.clip(val + delta, 0.0, 1.0))
            else:
                new_params[key] = val
        return OpenRAStrategyAgent(strategy_params=new_params)

    def crossover(self, other: "OpenRAStrategyAgent") -> "OpenRAStrategyAgent":
        """
        Uniform crossover: each parameter independently drawn from self or other.

        Args:
            other: Second parent agent.

        Returns:
            New offspring OpenRAStrategyAgent.
        """
        new_params = {
            key: (self.params[key] if np.random.random() < 0.5 else other.params[key])
            for key in self.params
        }
        return OpenRAStrategyAgent(strategy_params=new_params)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_strategy_description(self) -> str:
        lines = ["OpenRA Strategy Parameters:"]
        for k, v in self.params.items():
            bar = "=" * int(v * 20)
            lines.append(f"  {k:18s}: {v:.2f}  [{bar:<20}]")
        lines.append(f"  Record: {self._wins}W / {self._losses}L / {self._draws}D  "
                     f"(win_rate={self.win_rate:.1%})")
        return "\n".join(lines)

    def to_dict(self) -> Dict:
        return {
            "params": dict(self.params),
            "wins":   self._wins,
            "losses": self._losses,
            "draws":  self._draws,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "OpenRAStrategyAgent":
        agent = cls(strategy_params=d.get("params", {}))
        agent._wins   = d.get("wins", 0)
        agent._losses = d.get("losses", 0)
        agent._draws  = d.get("draws", 0)
        return agent

    def __repr__(self) -> str:
        p = self.params
        return (
            f"OpenRAStrategyAgent("
            f"agg={p['aggression']:.2f}, "
            f"eco={p['economy_focus']:.2f}, "
            f"exp={p['expansion_rate']:.2f}, "
            f"tec={p['tech_priority']:.2f}, "
            f"def={p['defense_bias']:.2f}, "
            f"wr={self.win_rate:.1%})"
        )


# ---------------------------------------------------------------------------
# OpenRAAgentAdapter
# ---------------------------------------------------------------------------

class OpenRAAgentAdapter:
    """
    Adapter that wraps a Prometheus GamePlayingExpertAgent for OpenRA.

    Converts the flat OpenRAGameState feature vector into an action integer
    using the wrapped agent's weight vector (linear scoring over actions).

    Args:
        prometheus_agent: Any agent with a `.weights` attribute (np.ndarray)
                          or a `select_action(obs)` method.
    """

    def __init__(self, prometheus_agent: Any):
        self.agent = prometheus_agent
        self.game_step = 0
        self._episode_history = []

    def select_action(self, observation: Any) -> int:
        """
        Select an action for OpenRA.

        Tries to use the wrapped agent's `select_action()` method.
        Falls back to a linear weight scoring over action feature vectors.
        """
        self.game_step += 1

        try:
            if hasattr(self.agent, "select_action"):
                return int(self.agent.select_action(observation))
        except Exception as e:
            logger.warning("Wrapped agent select_action failed: %s", e)

        # Fallback: score each action with the agent's weight vector
        if hasattr(self.agent, "weights") and self.agent.weights is not None:
            return self._weight_based_action(observation)

        # Last resort: random
        return int(np.random.randint(0, NUM_ACTIONS))

    def _weight_based_action(self, observation: Any) -> int:
        """Score each action using w^T φ(a, s)."""
        w = np.array(self.agent.weights, dtype=float)

        state = OpenRAStrategyAgent._to_state(observation)
        if state is None:
            return 0

        obs_vec = state.to_vector()  # shape (FEATURE_SIZE,)

        # Build a simple action-conditioned feature: obs ⊗ one_hot(action)
        best_action = 0
        best_score = -np.inf
        for a in range(NUM_ACTIONS):
            one_hot = np.zeros(NUM_ACTIONS)
            one_hot[a] = 1.0
            # Use first min(len(w), FEATURE_SIZE) dimensions
            n = min(len(w), len(obs_vec))
            score = float(np.dot(w[:n], obs_vec[:n]))
            # Slight action preference bias
            score += one_hot[a] * 0.01 * (a + 1)
            if score > best_score:
                best_score = score
                best_action = a

        return best_action

    def reset(self):
        self.game_step = 0
        self._episode_history = []
        if hasattr(self.agent, "reset"):
            self.agent.reset()

    def __repr__(self) -> str:
        return f"OpenRAAgentAdapter(wrapped={type(self.agent).__name__})"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_openra_agent(
    agent_type: str = "strategy",
    strategy_params: Optional[Dict[str, float]] = None,
) -> Any:
    """
    Factory function for OpenRA agents.

    Args:
        agent_type:      "strategy" | "adapter" | "random"
        strategy_params: Optional param overrides for "strategy" type.

    Returns:
        An agent with `.select_action(obs)` and `.reset()`.
    """
    if agent_type == "strategy":
        return OpenRAStrategyAgent(strategy_params=strategy_params)

    elif agent_type == "adapter":
        try:
            from prometheus.domain_expert_agent import GamePlayingExpertAgent
            base = GamePlayingExpertAgent()
        except ImportError:
            logger.warning("GamePlayingExpertAgent not available; using stub")
            base = _StubAgent()
        return OpenRAAgentAdapter(base)

    elif agent_type == "random":
        return _RandomOpenRAAgent()

    else:
        raise ValueError(f"Unknown agent_type '{agent_type}'. "
                         f"Choose from: strategy, adapter, random")


class _RandomOpenRAAgent:
    """Uniform random baseline for benchmarking."""

    def select_action(self, observation: Any) -> int:
        return int(np.random.randint(0, NUM_ACTIONS))

    def reset(self):
        pass

    def __repr__(self) -> str:
        return "RandomOpenRAAgent()"


class _StubAgent:
    """Zero-weight stub used when GamePlayingExpertAgent is unavailable."""
    weights = np.zeros(20)

    def reset(self):
        pass


# ---------------------------------------------------------------------------
# CLI self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    print("=== OpenRA Strategy Agent Self-Test ===\n")

    agent = OpenRAStrategyAgent()
    print("Default strategy:")
    print(agent.get_strategy_description())

    mutant = agent.mutate(mutation_rate=0.4)
    print("\nMutated agent:")
    print(mutant.get_strategy_description())

    other = OpenRAStrategyAgent({
        "aggression": 0.9, "economy_focus": 0.2,
        "expansion_rate": 0.8, "tech_priority": 0.7, "defense_bias": 0.1
    })
    offspring = agent.crossover(other)
    print("\nOffspring (crossover):")
    print(offspring.get_strategy_description())

    # Quick sanity: run a few steps in simulation
    from prometheus.openra_environment import OpenRAEnvironment
    env = OpenRAEnvironment(difficulty="easy")
    state = env.reset()
    agent.reset()
    for _ in range(10):
        action = agent.select_action(state)
        state, reward, done, info = env.step(action)
        if done:
            break
    print(f"\nPost-10-step state:\n{env.render()}")
