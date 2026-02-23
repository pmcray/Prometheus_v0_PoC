"""
OpenRA Benchmark for PrometheusStar — Prometheus v0.97

Implements the curriculum-learning evaluation framework for OpenRA agents.
Mirrors the structure of `benchmarks/microrts_benchmark.py` so the
PrometheusStar curriculum runner can treat both interchangeably.

Curriculum
----------
Four difficulty tiers with progressive target win-rates:

  Stage 1  Easy AI    — target 70% win rate
  Stage 2  Medium AI  — target 55%
  Stage 3  Hard AI    — target 40%
  Stage 4  Expert AI  — target 25%

Each stage runs `num_games` games against the simulated OpenRA backend
(no external dependency required).

Public API
----------
OpenRABenchmark.evaluate_agent(agent, num_games) → Dict
get_openra_opponent(stage)                        → OpenRAOpponentConfig
estimate_openra_training_time(...)                → Dict
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from prometheus.openra_environment import (
    FEATURE_SIZE,
    GameResult,
    NUM_ACTIONS,
    OpenRAEnvironment,
    OpenRAGameState,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Opponent configurations
# ---------------------------------------------------------------------------

@dataclass
class OpenRAOpponentConfig:
    """Configuration for one curriculum stage."""
    name:             str
    difficulty:       str          # "easy" | "medium" | "hard" | "expert"
    skill_level:      int          # 1–10 scale
    description:      str
    target_win_rate:  float        # success threshold to advance


# Four-stage curriculum
OPENRA_CURRICULUM: List[OpenRAOpponentConfig] = [
    OpenRAOpponentConfig(
        name="Easy AI",
        difficulty="easy",
        skill_level=2,
        description="Slow economy, minimal aggression — good for learning basic controls",
        target_win_rate=0.70,
    ),
    OpenRAOpponentConfig(
        name="Medium AI",
        difficulty="medium",
        skill_level=5,
        description="Balanced production and attack — requires solid economy",
        target_win_rate=0.55,
    ),
    OpenRAOpponentConfig(
        name="Hard AI",
        difficulty="hard",
        skill_level=7,
        description="Fast unit production and coordinated pushes — tactical response required",
        target_win_rate=0.40,
    ),
    OpenRAOpponentConfig(
        name="Expert AI",
        difficulty="expert",
        skill_level=9,
        description="High-tempo aggression with air superiority — strategic depth required",
        target_win_rate=0.25,
    ),
]


def get_openra_opponent(stage: int) -> OpenRAOpponentConfig:
    """
    Return the opponent config for the given 0-indexed curriculum stage.

    Args:
        stage: Integer in [0, len(OPENRA_CURRICULUM)).

    Raises:
        ValueError: if stage is out of range.
    """
    if not (0 <= stage < len(OPENRA_CURRICULUM)):
        raise ValueError(
            f"Invalid stage {stage}. Valid range: 0–{len(OPENRA_CURRICULUM) - 1}"
        )
    return OPENRA_CURRICULUM[stage]


# ---------------------------------------------------------------------------
# Benchmark class
# ---------------------------------------------------------------------------

class OpenRABenchmark:
    """
    Evaluates OpenRA agents through curriculum-based game episodes.

    Uses the `OpenRAEnvironment` simulator so no real OpenRA installation
    is needed.  The same code works with a live OpenRA backend if the
    `openra-python` package is available.

    Args:
        difficulty: Opponent difficulty tier (overrides stage-based selection
                    if provided directly).
        num_games:  Default number of games per evaluation.
        max_steps:  Hard cap on steps per game (guard against infinite loops).
        seed:       RNG seed for reproducibility.
    """

    def __init__(
        self,
        difficulty: str = "easy",
        num_games: int = 5,
        max_steps: int = 2000,
        seed: Optional[int] = None,
    ):
        self.difficulty = difficulty
        self.num_games  = num_games
        self.max_steps  = max_steps
        self.seed       = seed

        self._env = OpenRAEnvironment(difficulty=difficulty, seed=seed)

    # ------------------------------------------------------------------
    # Core evaluation
    # ------------------------------------------------------------------

    def evaluate_agent(
        self,
        agent: Any,
        num_games: Optional[int] = None,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """
        Evaluate `agent` over `num_games` episodes.

        Args:
            agent:     Any object with `.select_action(state)` and `.reset()`.
            num_games: Override the benchmark's default game count.
            verbose:   Print per-game results.

        Returns:
            Dict with keys:
              win_rate         float
              avg_reward       float
              avg_game_length  float
              games_played     int
              wins / losses / draws  int
              difficulty       str
              game_summaries   List[Dict]  — per-game detail
        """
        n = num_games if num_games is not None else self.num_games
        wins = losses = draws = 0
        total_reward = 0.0
        game_lengths: List[int] = []
        game_summaries: List[Dict] = []

        for game_num in range(n):
            state = self._env.reset()
            if hasattr(agent, "reset"):
                agent.reset()

            episode_reward = 0.0
            steps = 0

            while steps < self.max_steps:
                try:
                    action = agent.select_action(state)
                except Exception as e:
                    logger.warning("Agent.select_action raised %s — using no-op", e)
                    action = 0

                # Clamp to valid range
                action = int(np.clip(action, 0, NUM_ACTIONS - 1))
                state, reward, done, info = self._env.step(action)
                episode_reward += reward
                steps += 1

                if done:
                    break

            result = state.game_result
            if result == GameResult.VICTORY:
                wins += 1
            elif result == GameResult.DEFEAT:
                losses += 1
            else:
                draws += 1

            total_reward += episode_reward
            game_lengths.append(steps)

            summary = {
                "game":   game_num + 1,
                "result": result.value,
                "steps":  steps,
                "reward": round(episode_reward, 2),
                "own_units_lost":    state.own_units_lost,
                "enemy_units_lost":  state.enemy_units_lost,
                "own_bld_lost":      state.own_buildings_lost,
                "enemy_bld_lost":    state.enemy_buildings_lost,
            }
            game_summaries.append(summary)

            if verbose:
                icon = "W" if result == GameResult.VICTORY else (
                       "D" if result == GameResult.DRAW else "L")
                print(f"  Game {game_num + 1:2d}/{n} [{icon}] "
                      f"steps={steps:4d} reward={episode_reward:+7.1f}  "
                      f"kills={state.enemy_units_lost} "
                      f"losses={state.own_units_lost}")

        win_rate = wins / n if n > 0 else 0.0
        avg_reward = total_reward / n if n > 0 else 0.0
        avg_length = sum(game_lengths) / len(game_lengths) if game_lengths else 0.0

        return {
            "win_rate":        win_rate,
            "avg_reward":      avg_reward,
            "avg_game_length": avg_length,
            "games_played":    n,
            "wins":            wins,
            "losses":          losses,
            "draws":           draws,
            "difficulty":      self.difficulty,
            "game_summaries":  game_summaries,
        }

    # ------------------------------------------------------------------
    # Curriculum helpers
    # ------------------------------------------------------------------

    def advance_difficulty(self) -> bool:
        """
        Move to the next curriculum stage.

        Returns:
            True if advanced, False if already at maximum difficulty.
        """
        stages = [c.difficulty for c in OPENRA_CURRICULUM]
        if self.difficulty not in stages:
            return False
        idx = stages.index(self.difficulty)
        if idx >= len(stages) - 1:
            return False
        self.difficulty = stages[idx + 1]
        self._env = OpenRAEnvironment(difficulty=self.difficulty, seed=self.seed)
        logger.info("Curriculum advanced to difficulty: %s", self.difficulty)
        return True

    def meets_target(self, result: Dict[str, Any]) -> bool:
        """Return True if the evaluation result meets the current stage target."""
        cfg = next(
            (c for c in OPENRA_CURRICULUM if c.difficulty == self.difficulty),
            None,
        )
        if cfg is None:
            return False
        return result["win_rate"] >= cfg.target_win_rate

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def print_curriculum_overview(self) -> None:
        """Print the full curriculum to stdout."""
        print("=" * 65)
        print("OpenRA Curriculum Overview")
        print("=" * 65)
        for i, cfg in enumerate(OPENRA_CURRICULUM):
            marker = " <-- current" if cfg.difficulty == self.difficulty else ""
            print(f"\nStage {i + 1}: {cfg.name}{marker}")
            print(f"  Difficulty:   {cfg.difficulty}")
            print(f"  Skill level:  {cfg.skill_level}/10")
            print(f"  Target:       {cfg.target_win_rate:.0%} win rate")
            print(f"  Description:  {cfg.description}")
        print()


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def estimate_openra_training_time(
    population_size: int,
    generations: int,
    games_per_eval: int = 5,
    seconds_per_game: int = 15,
) -> Dict[str, float]:
    """
    Estimate total training time for one curriculum stage.

    Args:
        population_size: Agents per generation.
        generations:     Number of evolutionary generations.
        games_per_eval:  Games per agent evaluation.
        seconds_per_game: Simulated-clock seconds per game (fast sim ≈ 15s).

    Returns:
        Dict with total_games, total_seconds, total_minutes, total_hours,
        and per_generation_minutes.
    """
    total_games   = population_size * generations * games_per_eval
    total_seconds = total_games * seconds_per_game

    return {
        "total_games":            total_games,
        "total_seconds":          total_seconds,
        "total_minutes":          total_seconds / 60,
        "total_hours":            total_seconds / 3600,
        "per_generation_minutes": (population_size * games_per_eval * seconds_per_game) / 60,
    }


def run_quick_evaluation(
    agent: Any,
    difficulty: str = "easy",
    num_games: int = 3,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Convenience wrapper for a quick single-stage evaluation.

    Args:
        agent:      Agent with .select_action() and .reset().
        difficulty: Opponent difficulty.
        num_games:  Games to play.
        verbose:    Print per-game results.

    Returns:
        Evaluation result dict from OpenRABenchmark.evaluate_agent().
    """
    bench = OpenRABenchmark(difficulty=difficulty)
    if verbose:
        print(f"\nEvaluating against {difficulty.upper()} AI "
              f"({num_games} games)...")
    result = bench.evaluate_agent(agent, num_games=num_games, verbose=verbose)
    if verbose:
        cfg = next(c for c in OPENRA_CURRICULUM if c.difficulty == difficulty)
        status = "PASS" if result["win_rate"] >= cfg.target_win_rate else "FAIL"
        print(f"\n  Win rate: {result['win_rate']:.1%}  "
              f"(target {cfg.target_win_rate:.0%})  [{status}]")
        print(f"  Avg reward: {result['avg_reward']:+.1f}  "
              f"Avg length: {result['avg_game_length']:.0f} steps")
    return result


# ---------------------------------------------------------------------------
# Simple baseline agents (no external dependencies)
# ---------------------------------------------------------------------------

class RandomOpenRAAgent:
    """Uniform random baseline."""

    def select_action(self, obs: Any) -> int:
        return int(np.random.randint(0, NUM_ACTIONS))

    def reset(self) -> None:
        pass


class RushOpenRAAgent:
    """Always rushes — useful as an aggressive baseline."""

    _BUILD_INFANTRY = 1
    _RUSH           = 11

    def __init__(self):
        self._step = 0

    def select_action(self, obs: Any) -> int:
        self._step += 1
        # Build up for first 50 steps, then rush
        if self._step < 50:
            return self._BUILD_INFANTRY
        return self._RUSH

    def reset(self) -> None:
        self._step = 0


class EconomyOpenRAAgent:
    """Focuses entirely on economy — useful for testing defensive AI."""

    _BUILD_HARVESTER = 4
    _EXPAND          = 5
    _HARVEST         = 12
    _DEFEND          = 10

    def __init__(self):
        self._step = 0

    def select_action(self, obs: Any) -> int:
        self._step += 1
        cycle = self._step % 4
        if cycle == 0:
            return self._BUILD_HARVESTER
        elif cycle == 1:
            return self._EXPAND
        elif cycle == 2:
            return self._HARVEST
        else:
            return self._DEFEND

    def reset(self) -> None:
        self._step = 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    from prometheus.openra_agent import OpenRAStrategyAgent

    agent = OpenRAStrategyAgent()

    print("=" * 65)
    print("OpenRA Benchmark — Quick Curriculum Test")
    print("=" * 65)
    agent.get_strategy_description()

    for stage_cfg in OPENRA_CURRICULUM:
        result = run_quick_evaluation(
            agent,
            difficulty=stage_cfg.difficulty,
            num_games=3,
            verbose=True,
        )
        if result["win_rate"] < stage_cfg.target_win_rate:
            print(f"  => Did not meet target — stopping at {stage_cfg.name}")
            break
    else:
        print("\n✓ Agent completed the full curriculum!")

    print("\n=== Training Time Estimates ===")
    configs = [
        (4,  5,  "Quick test"),
        (8,  15, "Standard run"),
        (12, 25, "Extended run"),
    ]
    for pop, gens, desc in configs:
        est = estimate_openra_training_time(pop, gens)
        print(f"\n{desc} ({pop} agents × {gens} gens):")
        print(f"  Total games:  {est['total_games']}")
        print(f"  Total time:   {est['total_hours']:.1f}h  ({est['total_minutes']:.0f} min)")
        print(f"  Per gen:      {est['per_generation_minutes']:.1f} min")
