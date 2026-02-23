"""
Hierarchical Planning Benchmark — Prometheus v0.97 (WP9)

Compares single-level planning (flat policy) against two-level hierarchical
planning (Manager + Worker with options) on a series of synthetic multi-step
tasks.

Scenarios
---------
flat_vs_hierarchical
    Run both planners on a 5-step sequential task (acquire resource →
    verify → process → report → cleanup).  Measure: goal achievement rate,
    mean steps-to-goal, and total reward.

sample_efficiency
    Train the value agent on increasing numbers of preference pairs and
    report how quickly each planner reaches 80% goal-achievement rate.

safety_gating
    Inject unsafe plan code on 25% of steps; verify that the safety gate
    catches violations and the hierarchical planner terminates gracefully.

option_discovery
    Generate synthetic trajectories, call OptionLibrary.discover_from_trajectories(),
    and benchmark how many discovered options are applicable per state.

Public API
----------
HierarchicalPlanningBenchmark.run(scenario) → HPBenchmarkResult
HierarchicalPlanningBenchmark.run_all()     → List[HPBenchmarkResult]
HierarchicalPlanningBenchmark.summary_table(results) → str
"""
from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prometheus.value_learning import ValueLearningAgent
from prometheus.option import Option, OptionLibrary, State, Action
from prometheus.hierarchical_planner import (
    HierarchicalPlanner,
    ManagerAgent,
    WorkerAgent,
    HierarchicalEpisodeResult,
    make_hierarchical_planner,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Synthetic environment
# ---------------------------------------------------------------------------

N_FEATS = 5

# Task stages and their feature-vector representation
STAGE_FEATURES: Dict[str, np.ndarray] = {
    "idle"      : np.array([0.0, 0.0, 0.0, 0.0, 0.0]),
    "acquired"  : np.array([1.0, 0.0, 0.0, 0.0, 0.0]),
    "verified"  : np.array([1.0, 1.0, 0.0, 0.0, 0.0]),
    "processed" : np.array([1.0, 1.0, 1.0, 0.0, 0.0]),
    "reported"  : np.array([1.0, 1.0, 1.0, 1.0, 0.0]),
    "done"      : np.array([1.0, 1.0, 1.0, 1.0, 1.0]),
}

STAGE_ORDER = ["idle", "acquired", "verified", "processed", "reported", "done"]


def _make_preference_pairs(seed: int = 0, n: int = 40) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Pairs preferring later stages over earlier ones."""
    rng   = np.random.default_rng(seed)
    pairs = []
    for _ in range(n):
        i = rng.integers(0, len(STAGE_ORDER) - 1)
        j = rng.integers(i + 1, len(STAGE_ORDER))
        pref   = STAGE_FEATURES[STAGE_ORDER[j]] + rng.uniform(-0.05, 0.05, N_FEATS)
        unpref = STAGE_FEATURES[STAGE_ORDER[i]] + rng.uniform(-0.05, 0.05, N_FEATS)
        pairs.append((pref, unpref))
    return pairs


def _trained_agent(seed: int = 0, n_pairs: int = 40) -> ValueLearningAgent:
    agent = ValueLearningAgent(feature_size=N_FEATS, l2_reg=0.01)
    agent.train_to_convergence(_make_preference_pairs(seed, n_pairs), max_epochs=100)
    return agent


def _env_step(state: State, action: Action) -> State:
    """
    Deterministic environment: advance to the next stage if the action
    targets the current stage's successor.
    """
    stage = state.get("stage", "idle")
    try:
        idx = STAGE_ORDER.index(stage)
    except ValueError:
        idx = 0

    next_stage = STAGE_ORDER[min(idx + 1, len(STAGE_ORDER) - 1)]
    return {
        "stage"       : next_stage,
        "step"        : state.get("step", 0) + 1,
        "features"    : STAGE_FEATURES[next_stage],
        next_stage    : True,   # flag for termination conditions
    }


def _unsafe_env_step(state: State, action: Action, inject_prob: float = 0.25,
                     rng: Optional[np.random.Generator] = None) -> State:
    """
    Like _env_step but randomly injects 'import os' into plan code
    so the safety gate is triggered.
    """
    if rng is None:
        rng = np.random.default_rng(99)
    if rng.random() < inject_prob:
        action = dict(action)
        action["plan"] = "import os\nos.system('id')"
    return _env_step(state, action)


def _goal_fn(state: State, goal: str) -> bool:
    """Episode is done when the 'done' stage is reached."""
    return state.get("stage") == "done" or state.get("done", False)


# ---------------------------------------------------------------------------
# Option library for the synthetic task
# ---------------------------------------------------------------------------

def _build_option_library(feature_size: int = N_FEATS) -> OptionLibrary:
    lib = OptionLibrary(feature_size=feature_size)

    stage_transitions = [
        ("acquire",  "idle",       "acquired"),
        ("verify",   "acquired",   "verified"),
        ("process",  "verified",   "processed"),
        ("report",   "processed",  "reported"),
        ("cleanup",  "reported",   "done"),
    ]

    for name, from_stage, to_stage in stage_transitions:
        feat_from = STAGE_FEATURES[from_stage]
        feat_to   = STAGE_FEATURES[to_stage]

        def _init(state: State, fs: str = from_stage) -> bool:
            return state.get("stage", "idle") == fs

        def _term(state: State, ts: str = to_stage) -> bool:
            return state.get("stage", "idle") == ts or state.get(ts, False)

        def _policy(state: State, ts: str = to_stage) -> Action:
            return {
                "plan"       : f"# advance to {ts}\npass",
                "target_stage": ts,
            }

        feat_target = feat_to.copy()

        def _extractor(state: State, ft: np.ndarray = feat_target) -> np.ndarray:
            feats = state.get("features", np.zeros(feature_size, dtype=float))
            if isinstance(feats, np.ndarray):
                return feats + 0.01 * ft   # slight bias toward target
            return ft

        opt = Option(
            name                 = name,
            description          = f"Advance from {from_stage} to {to_stage}",
            initiation_condition = _init,
            policy               = _policy,
            termination_condition= _term,
            max_steps            = 5,
            feature_extractor    = _extractor,
            metadata             = {"domain": "synthetic_task",
                                    "from_stage": from_stage,
                                    "to_stage"  : to_stage},
        )
        lib.register(opt)

    return lib


# ---------------------------------------------------------------------------
# Flat (single-level) planner for comparison
# ---------------------------------------------------------------------------

class FlatPlanner:
    """
    Baseline: applies a fixed greedy policy at each step without any
    temporal abstraction.  Uses the same ValueLearningAgent as the
    hierarchical planner.
    """

    def __init__(
        self,
        value_agent   : ValueLearningAgent,
        env_step_fn   : Callable[[State, Action], State],
        goal_fn       : Callable[[State, str], bool],
        step_budget   : int = 100,
        safety_gate_fn: Optional[Callable[[str], bool]] = None,
    ) -> None:
        self.value_agent    = value_agent
        self.env_step_fn    = env_step_fn
        self.goal_fn        = goal_fn
        self.step_budget    = step_budget
        self.safety_gate_fn = safety_gate_fn or (lambda p: True)

    def plan(self, state: State, goal: str) -> Dict[str, Any]:
        t0    = time.perf_counter()
        steps = 0
        total_reward = 0.0
        safety_violations = 0
        goal_achieved = False

        for _ in range(self.step_budget):
            if self.goal_fn(state, goal):
                goal_achieved = True
                break

            # Fixed action: always try to advance one step
            action    = {"plan": "# advance\npass"}
            plan_code = action["plan"]

            if not self.safety_gate_fn(plan_code):
                safety_violations += 1
                break

            try:
                state = self.env_step_fn(state, action)
            except Exception:
                break

            feats        = state.get("features", np.zeros(N_FEATS, dtype=float))
            total_reward += self.value_agent.get_reward(np.asarray(feats, dtype=float))
            steps        += 1

        return {
            "goal_achieved"    : goal_achieved,
            "total_steps"      : steps,
            "total_reward"     : total_reward,
            "safety_violations": safety_violations,
            "wall_clock_s"     : time.perf_counter() - t0,
        }


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class HPBenchmarkResult:
    """Benchmark result for one scenario."""
    scenario              : str
    notes                 : str

    # Hierarchical planner metrics
    hp_goal_rate          : float = 0.0
    hp_mean_steps         : float = 0.0
    hp_mean_reward        : float = 0.0
    hp_safety_viol_rate   : float = 0.0

    # Flat planner metrics (where applicable)
    flat_goal_rate        : float = 0.0
    flat_mean_steps       : float = 0.0
    flat_mean_reward      : float = 0.0
    flat_safety_viol_rate : float = 0.0

    # Extra per-scenario data
    extra                 : Dict[str, Any] = field(default_factory=dict)

    # Timing
    wall_clock_s          : float = 0.0
    n_episodes            : int   = 0

    def summary_dict(self) -> Dict[str, Any]:
        return {
            "scenario"           : self.scenario,
            "hp_goal_rate"       : round(self.hp_goal_rate, 4),
            "hp_mean_steps"      : round(self.hp_mean_steps, 2),
            "hp_mean_reward"     : round(self.hp_mean_reward, 4),
            "flat_goal_rate"     : round(self.flat_goal_rate, 4),
            "flat_mean_steps"    : round(self.flat_mean_steps, 2),
            "flat_mean_reward"   : round(self.flat_mean_reward, 4),
            "wall_clock_s"       : round(self.wall_clock_s, 3),
            "n_episodes"         : self.n_episodes,
            "notes"              : self.notes,
        }


# ---------------------------------------------------------------------------
# Benchmark class
# ---------------------------------------------------------------------------

class HierarchicalPlanningBenchmark:
    """
    Benchmark runner for WP9.

    Parameters
    ----------
    n_episodes : Episodes per scenario.
    seed       : Random seed.
    """

    SCENARIOS = (
        "flat_vs_hierarchical",
        "sample_efficiency",
        "safety_gating",
        "option_discovery",
    )

    def __init__(self, n_episodes: int = 20, seed: int = 42) -> None:
        self.n_episodes = n_episodes
        self.seed       = seed
        self._agent     = _trained_agent(seed=seed, n_pairs=60)
        self._lib       = _build_option_library()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _initial_state(self) -> State:
        return {
            "stage"   : "idle",
            "step"    : 0,
            "features": STAGE_FEATURES["idle"].copy(),
        }

    def _run_hp_episodes(
        self,
        planner    : HierarchicalPlanner,
        n          : int,
        env_step_fn: Callable[[State, Action], State],
    ) -> List[HierarchicalEpisodeResult]:
        results = []
        for _ in range(n):
            state  = self._initial_state()
            result = planner.plan(state, "done")
            results.append(result)
        return results

    def _run_flat_episodes(
        self,
        flat       : FlatPlanner,
        n          : int,
    ) -> List[Dict[str, Any]]:
        return [flat.plan(self._initial_state(), "done") for _ in range(n)]

    # ------------------------------------------------------------------
    # Scenario 1: flat vs hierarchical
    # ------------------------------------------------------------------

    def _run_flat_vs_hierarchical(self) -> HPBenchmarkResult:
        t0 = time.time()

        hp = make_hierarchical_planner(
            value_agent    = self._agent,
            option_library = self._lib,
            env_step_fn    = _env_step,
            goal_fn        = _goal_fn,
            max_options    = 10,
            step_budget    = 30,
            feature_size   = N_FEATS,
        )
        flat = FlatPlanner(
            value_agent = self._agent,
            env_step_fn = _env_step,
            goal_fn     = _goal_fn,
            step_budget = 30,
        )

        hp_eps   = self._run_hp_episodes(hp,   self.n_episodes, _env_step)
        flat_eps = self._run_flat_episodes(flat, self.n_episodes)

        n = self.n_episodes

        return HPBenchmarkResult(
            scenario            = "flat_vs_hierarchical",
            notes               = "5-stage sequential task; options vs greedy flat policy",
            hp_goal_rate        = sum(e.goal_achieved for e in hp_eps) / n,
            hp_mean_steps       = sum(e.total_steps   for e in hp_eps) / n,
            hp_mean_reward      = sum(e.total_reward  for e in hp_eps) / n,
            hp_safety_viol_rate = sum(e.safety_violations > 0 for e in hp_eps) / n,
            flat_goal_rate      = sum(e["goal_achieved"]     for e in flat_eps) / n,
            flat_mean_steps     = sum(e["total_steps"]       for e in flat_eps) / n,
            flat_mean_reward    = sum(e["total_reward"]      for e in flat_eps) / n,
            flat_safety_viol_rate = sum(e["safety_violations"] > 0 for e in flat_eps) / n,
            wall_clock_s        = time.time() - t0,
            n_episodes          = n,
        )

    # ------------------------------------------------------------------
    # Scenario 2: sample efficiency
    # ------------------------------------------------------------------

    def _run_sample_efficiency(self) -> HPBenchmarkResult:
        t0       = time.time()
        pair_counts = [5, 10, 20, 40, 80]
        hp_rates    = []
        flat_rates  = []

        for n_pairs in pair_counts:
            agent = _trained_agent(seed=self.seed, n_pairs=n_pairs)
            lib   = _build_option_library()

            hp = make_hierarchical_planner(
                value_agent    = agent,
                option_library = lib,
                env_step_fn    = _env_step,
                goal_fn        = _goal_fn,
                max_options    = 10,
                step_budget    = 30,
                feature_size   = N_FEATS,
            )
            flat = FlatPlanner(
                value_agent = agent,
                env_step_fn = _env_step,
                goal_fn     = _goal_fn,
                step_budget = 30,
            )

            n_ep   = max(5, self.n_episodes // 4)
            hp_eps = self._run_hp_episodes(hp, n_ep, _env_step)
            fl_eps = self._run_flat_episodes(flat, n_ep)

            hp_rates.append(sum(e.goal_achieved     for e in hp_eps) / n_ep)
            flat_rates.append(sum(e["goal_achieved"] for e in fl_eps) / n_ep)

        return HPBenchmarkResult(
            scenario       = "sample_efficiency",
            notes          = "Goal-achievement rate vs training-pair count",
            hp_goal_rate   = float(np.mean(hp_rates)),
            flat_goal_rate = float(np.mean(flat_rates)),
            wall_clock_s   = time.time() - t0,
            n_episodes     = self.n_episodes,
            extra          = {
                "pair_counts": pair_counts,
                "hp_rates"   : hp_rates,
                "flat_rates" : flat_rates,
            },
        )

    # ------------------------------------------------------------------
    # Scenario 3: safety gating
    # ------------------------------------------------------------------

    def _run_safety_gating(self) -> HPBenchmarkResult:
        t0  = time.time()
        rng = np.random.default_rng(self.seed + 7)

        # Gate rejects any plan containing "import"
        def gate(plan: str) -> bool:
            return "import" not in plan

        unsafe_step = lambda s, a, _rng=rng: _unsafe_env_step(s, a, inject_prob=0.25, rng=_rng)

        hp = make_hierarchical_planner(
            value_agent    = self._agent,
            option_library = self._lib,
            env_step_fn    = unsafe_step,
            goal_fn        = _goal_fn,
            safety_gate_fn = gate,
            max_options    = 10,
            step_budget    = 30,
            feature_size   = N_FEATS,
        )

        hp_eps = self._run_hp_episodes(hp, self.n_episodes, unsafe_step)
        n      = self.n_episodes
        n_viols = sum(e.safety_violations for e in hp_eps)
        viol_rate = sum(e.safety_violations > 0 for e in hp_eps) / n

        return HPBenchmarkResult(
            scenario            = "safety_gating",
            notes               = "25% unsafe plan injection; gate catches violations",
            hp_goal_rate        = sum(e.goal_achieved for e in hp_eps) / n,
            hp_mean_steps       = sum(e.total_steps   for e in hp_eps) / n,
            hp_safety_viol_rate = viol_rate,
            wall_clock_s        = time.time() - t0,
            n_episodes          = n,
            extra               = {"total_violations": n_viols},
        )

    # ------------------------------------------------------------------
    # Scenario 4: option discovery
    # ------------------------------------------------------------------

    def _run_option_discovery(self) -> HPBenchmarkResult:
        t0  = time.time()
        rng = np.random.default_rng(self.seed + 13)

        # Generate synthetic trajectories
        trajectories: List[List[State]] = []
        for _ in range(30):
            traj  : List[State] = []
            state = self._initial_state()
            for __step in range(8):
                traj.append(dict(state))
                state = _env_step(state, {"plan": "pass"})
            traj.append(dict(state))
            trajectories.append(traj)

        # Discovery
        lib_fresh = OptionLibrary(feature_size=N_FEATS)
        discovered = lib_fresh.discover_from_trajectories(trajectories, min_frequency=2)

        # Measure applicability
        test_state   = self._initial_state()
        applicable   = lib_fresh.list_applicable(test_state)

        return HPBenchmarkResult(
            scenario     = "option_discovery",
            notes        = "Discover options from trajectories; measure applicability",
            hp_goal_rate = 0.0,   # N/A for this scenario
            wall_clock_s = time.time() - t0,
            n_episodes   = 0,
            extra        = {
                "n_trajectories"  : len(trajectories),
                "n_discovered"    : len(discovered),
                "n_applicable"    : len(applicable),
                "discovered_names": [o.name for o in discovered],
            },
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self, scenario: str) -> HPBenchmarkResult:
        if scenario == "flat_vs_hierarchical":
            return self._run_flat_vs_hierarchical()
        elif scenario == "sample_efficiency":
            return self._run_sample_efficiency()
        elif scenario == "safety_gating":
            return self._run_safety_gating()
        elif scenario == "option_discovery":
            return self._run_option_discovery()
        else:
            raise ValueError(
                f"Unknown scenario {scenario!r}. Choose from {self.SCENARIOS}"
            )

    def run_all(self) -> List[HPBenchmarkResult]:
        return [self.run(s) for s in self.SCENARIOS]

    def summary_table(self, results: List[HPBenchmarkResult]) -> str:
        lines = []
        for r in results:
            lines.append(f"\n{'='*60}")
            lines.append(f"Scenario: {r.scenario}")
            lines.append(f"  Notes: {r.notes}")
            lines.append(f"  Episodes: {r.n_episodes}  Time: {r.wall_clock_s:.2f}s")
            lines.append(f"  Hierarchical planner:")
            lines.append(f"    Goal rate:   {r.hp_goal_rate*100:.1f}%")
            lines.append(f"    Mean steps:  {r.hp_mean_steps:.1f}")
            lines.append(f"    Mean reward: {r.hp_mean_reward:.4f}")
            lines.append(f"    Safety viol: {r.hp_safety_viol_rate*100:.1f}%")
            if r.flat_goal_rate or r.flat_mean_steps:
                lines.append(f"  Flat planner:")
                lines.append(f"    Goal rate:   {r.flat_goal_rate*100:.1f}%")
                lines.append(f"    Mean steps:  {r.flat_mean_steps:.1f}")
                lines.append(f"    Mean reward: {r.flat_mean_reward:.4f}")
            if r.extra:
                for k, v in r.extra.items():
                    lines.append(f"  {k}: {v}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bench   = HierarchicalPlanningBenchmark(n_episodes=20, seed=42)
    results = bench.run_all()
    print("\n=== Hierarchical Planning Benchmark Results ===")
    print(bench.summary_table(results))
