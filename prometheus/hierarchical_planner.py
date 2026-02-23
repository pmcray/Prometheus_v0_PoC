"""
prometheus/hierarchical_planner.py — Hierarchical Planning with Temporal
Abstraction (WP9)

Implements a two-level planner built on the options framework
(Sutton, Precup & Singh 1999):

  ┌─────────────────────────────────────────┐
  │  ManagerAgent  (high-level)             │
  │  • Scores options with ValueLearningAgent│
  │  • Selects the highest-reward option     │
  │  • Delegates to WorkerAgent for exec     │
  └────────────────┬────────────────────────┘
                   │ selected Option
  ┌────────────────▼────────────────────────┐
  │  WorkerAgent   (low-level)              │
  │  • Runs intra-option policy step-by-step│
  │  • Submits each plan via AgentChannel   │
  │  • CoordinatorAgent gates via MCSSuperv │
  │  • Exits on termination/truncation/viol │
  └─────────────────────────────────────────┘

Safety integration
------------------
- Every primitive step is gated by CoordinatorAgent.run_round() which
  invokes the MCSSupervisor (and, if WP7 is available, the FormalVerifier).
- A safety violation causes immediate option termination and is recorded.

Value-learning integration
--------------------------
- ManagerAgent.select_option() ranks applicable options by
  ValueLearningAgent.get_reward(option.extract_features(state)).

Public API
----------
ManagerAgent(value_agent, option_library, coordinator, worker_channel)
    .select_option(state) → Optional[Option]
    .run_episode(state, goal) → HierarchicalEpisodeResult

WorkerAgent(channel, coordinator)
    .execute_option(option, state, env_step_fn) → OptionExecutionRecord

HierarchicalPlanner(manager, worker)
    .plan(state, goal) → HierarchicalEpisodeResult
    .stats() → Dict

References
----------
Sutton, R. S., Precup, D., & Singh, S. (1999). Between MDPs and semi-MDPs:
  A framework for temporal abstraction in reinforcement learning.
  Artificial Intelligence, 112(1–2), 181–211.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from prometheus.option import Option, OptionExecutionRecord, OptionLibrary, State, Action
from prometheus.value_learning import ValueLearningAgent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HierarchicalEpisodeResult
# ---------------------------------------------------------------------------

@dataclass
class HierarchicalEpisodeResult:
    """
    Full record of one Manager-level planning episode.

    Attributes
    ----------
    goal                  : High-level goal description.
    options_executed      : Ordered list of options that were run.
    execution_records     : Detailed record per option execution.
    total_steps           : Cumulative primitive steps across all options.
    total_reward          : Cumulative reward (from ValueLearningAgent).
    goal_achieved         : True if the goal condition held at episode end.
    safety_violations     : Total safety violations encountered.
    wall_clock_s          : Total wall-clock time.
    termination_reason    : "goal_achieved" | "no_options" | "budget_exceeded"
                            | "safety_abort"
    n_options_considered  : How many options were evaluated at each step
                            (list, one entry per manager decision).
    """
    goal                 : str
    options_executed     : List[str]                   = field(default_factory=list)
    execution_records    : List[OptionExecutionRecord] = field(default_factory=list)
    total_steps          : int                         = 0
    total_reward         : float                       = 0.0
    goal_achieved        : bool                        = False
    safety_violations    : int                         = 0
    wall_clock_s         : float                       = 0.0
    termination_reason   : str                         = "unknown"
    n_options_considered : List[int]                   = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"HierarchicalEpisode(goal={self.goal!r}, "
            f"options={len(self.options_executed)}, "
            f"steps={self.total_steps}, "
            f"reward={self.total_reward:.4f}, "
            f"achieved={self.goal_achieved}, "
            f"violations={self.safety_violations}, "
            f"reason={self.termination_reason!r})"
        )


# ---------------------------------------------------------------------------
# ManagerAgent
# ---------------------------------------------------------------------------

class ManagerAgent:
    """
    High-level planner: selects options from an OptionLibrary using
    a ValueLearningAgent as the option-scoring function.

    Parameters
    ----------
    value_agent      : Trained ValueLearningAgent for option scoring.
    option_library   : OptionLibrary containing available options.
    max_options      : Maximum number of options to execute per episode.
    step_budget      : Maximum total primitive steps per episode.
    goal_fn          : ``f(state, goal) → bool`` — episode success check.
                       If None, the episode runs until budget exhausted.
    """

    def __init__(
        self,
        value_agent   : ValueLearningAgent,
        option_library: OptionLibrary,
        max_options   : int = 10,
        step_budget   : int = 100,
        goal_fn       : Optional[Callable[[State, str], bool]] = None,
    ) -> None:
        self.value_agent    = value_agent
        self.option_library = option_library
        self.max_options    = max_options
        self.step_budget    = step_budget
        self.goal_fn        = goal_fn or (lambda state, goal: False)
        self._decisions: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Option selection
    # ------------------------------------------------------------------

    def select_option(self, state: State) -> Tuple[Optional[Option], List[Option]]:
        """
        Choose the highest-reward applicable option for *state*.

        Returns
        -------
        (best_option, candidates) where candidates is the full list
        of applicable options (sorted by descending reward).
        Returns (None, []) if no option can initiate.
        """
        candidates = self.option_library.list_applicable(state)
        if not candidates:
            logger.debug("No applicable options in state %s", list(state.keys()))
            return None, []

        scored = []
        for opt in candidates:
            feats  = opt.extract_features(state)
            reward = self.value_agent.get_reward(feats)
            scored.append((reward, opt))

        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[0][1]

        logger.debug(
            "Selected option %r (reward=%.4f) from %d candidates",
            best.name, scored[0][0], len(scored),
        )
        self._decisions.append({
            "selected"        : best.option_id,
            "n_candidates"    : len(candidates),
            "top_reward"      : scored[0][0],
            "state_keys"      : list(state.keys()),
        })
        return best, [s[1] for s in scored]

    # ------------------------------------------------------------------
    # Episode orchestration
    # ------------------------------------------------------------------

    def run_episode(
        self,
        initial_state: State,
        goal         : str,
        worker       : "WorkerAgent",
        env_step_fn  : Callable[[State, Action], State],
    ) -> HierarchicalEpisodeResult:
        """
        Execute a full Manager-level episode.

        Algorithm
        ---------
        1.  Check if goal already satisfied.
        2.  Select best applicable option from current state.
        3.  Execute option using WorkerAgent (returns updated state).
        4.  Accumulate reward and check termination conditions.
        5.  Repeat until goal, budget exhausted, or no options available.

        Parameters
        ----------
        initial_state : Starting state snapshot.
        goal          : Text description of the high-level goal.
        worker        : WorkerAgent that will execute primitive steps.
        env_step_fn   : ``f(state, action) → next_state`` simulator.
        """
        t0     = time.perf_counter()
        state  = dict(initial_state)
        result = HierarchicalEpisodeResult(goal=goal)

        for option_idx in range(self.max_options):
            # Check goal
            if self.goal_fn(state, goal):
                result.goal_achieved    = True
                result.termination_reason = "goal_achieved"
                break

            # Check step budget
            if result.total_steps >= self.step_budget:
                result.termination_reason = "budget_exceeded"
                break

            # Manager decision: select option
            best_opt, candidates = self.select_option(state)
            result.n_options_considered.append(len(candidates))

            if best_opt is None:
                result.termination_reason = "no_options"
                break

            # Worker execution
            rec   = worker.execute_option(best_opt, state, env_step_fn)
            state = rec.states_visited[-1] if rec.states_visited else state

            # Accumulate
            result.options_executed.append(best_opt.option_id)
            result.execution_records.append(rec)
            result.total_steps    += rec.steps_taken
            result.total_reward   += rec.total_reward
            result.safety_violations += (1 if rec.safety_violation else 0)

            if rec.safety_violation:
                logger.warning(
                    "Safety violation in option %r; aborting episode", best_opt.name
                )
                result.termination_reason = "safety_abort"
                break
        else:
            # Exhausted max_options without explicit termination
            if not result.termination_reason or result.termination_reason == "unknown":
                result.termination_reason = "budget_exceeded"

        # Final goal check
        if not result.goal_achieved and self.goal_fn(state, goal):
            result.goal_achieved      = True
            result.termination_reason = "goal_achieved"

        result.wall_clock_s = time.perf_counter() - t0
        logger.info("Episode done: %s", result.summary())
        return result

    def decisions(self) -> List[Dict[str, Any]]:
        """Return the Manager's option-selection decision log."""
        return list(self._decisions)


# ---------------------------------------------------------------------------
# WorkerAgent
# ---------------------------------------------------------------------------

class WorkerAgent:
    """
    Low-level executor: runs a single Option step-by-step.

    Each primitive step is:
      1.  Policy application → action dict (``{"plan": str, …}``)
      2.  Safety gate (optional CoordinatorAgent round or direct check)
      3.  Environment transition via ``env_step_fn``
      4.  Reward accumulation via ``ValueLearningAgent``

    Parameters
    ----------
    value_agent     : Scoring function for primitive-step rewards.
    feature_size    : Dimension of the feature vectors extracted per step.
    safety_gate_fn  : ``f(plan_str) → bool`` — returns True if plan is safe.
                      If None, all plans are accepted (unsafe mode; for testing).
    """

    def __init__(
        self,
        value_agent   : ValueLearningAgent,
        feature_size  : int                        = 5,
        safety_gate_fn: Optional[Callable[[str], bool]] = None,
    ) -> None:
        self.value_agent    = value_agent
        self.feature_size   = feature_size
        self.safety_gate_fn = safety_gate_fn or (lambda plan: True)
        self._step_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Option execution
    # ------------------------------------------------------------------

    def execute_option(
        self,
        option     : Option,
        init_state : State,
        env_step_fn: Callable[[State, Action], State],
    ) -> OptionExecutionRecord:
        """
        Execute *option* from *init_state* until termination.

        At each step:
          1.  Apply intra-option policy to get action.
          2.  Check safety gate.
          3.  Advance environment.
          4.  Score new state with ValueLearningAgent.
          5.  Check termination condition.

        Parameters
        ----------
        option      : Option to execute.
        init_state  : State at option initiation.
        env_step_fn : Simulator: ``f(state, action) → next_state``.

        Returns
        -------
        OptionExecutionRecord with full step history.
        """
        t0    = time.perf_counter()
        state = dict(init_state)

        rec = OptionExecutionRecord(
            option_id   = option.option_id,
            steps_taken = 0,
            terminated  = False,
            truncated   = False,
            total_reward= 0.0,
        )
        rec.states_visited.append(dict(state))

        for step in range(option.max_steps):
            # 1. Policy
            action = option.act(state)
            plan_code = action.get("plan", "pass")

            # 2. Safety gate
            if not self.safety_gate_fn(plan_code):
                logger.warning(
                    "Option %r step %d blocked by safety gate", option.name, step
                )
                rec.safety_violation = True
                rec.terminated       = True
                break

            # 3. Environment transition
            try:
                next_state = env_step_fn(state, action)
            except Exception as exc:
                logger.error(
                    "env_step_fn raised %s at option %r step %d; treating as terminal",
                    exc, option.name, step,
                )
                rec.safety_violation = True
                rec.terminated       = True
                break

            # 4. Reward
            feats  = option.extract_features(next_state)
            reward = self.value_agent.get_reward(feats)
            rec.total_reward += reward

            # Record
            rec.actions_taken.append(action)
            rec.states_visited.append(dict(next_state))
            rec.steps_taken += 1

            self._step_log.append({
                "option_id": option.option_id,
                "step"     : step,
                "reward"   : reward,
                "plan_len" : len(plan_code),
            })

            state = next_state

            # 5. Termination condition
            if option.should_terminate(state):
                rec.terminated = True
                break
        else:
            # max_steps reached
            rec.truncated = True

        rec.wall_clock_s = time.perf_counter() - t0
        logger.debug(
            "Option %r: %d steps, reward=%.4f, terminated=%s, truncated=%s, "
            "violation=%s",
            option.name, rec.steps_taken, rec.total_reward,
            rec.terminated, rec.truncated, rec.safety_violation,
        )
        return rec

    def step_log(self) -> List[Dict[str, Any]]:
        """Return the primitive-step log."""
        return list(self._step_log)


# ---------------------------------------------------------------------------
# HierarchicalPlanner (facade)
# ---------------------------------------------------------------------------

class HierarchicalPlanner:
    """
    Convenience facade combining ManagerAgent and WorkerAgent.

    Parameters
    ----------
    manager          : Configured ManagerAgent.
    worker           : Configured WorkerAgent.
    env_step_fn      : Environment transition function.
    """

    def __init__(
        self,
        manager     : ManagerAgent,
        worker      : WorkerAgent,
        env_step_fn : Callable[[State, Action], State],
    ) -> None:
        self.manager     = manager
        self.worker      = worker
        self.env_step_fn = env_step_fn
        self._episodes: List[HierarchicalEpisodeResult] = []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def plan(self, state: State, goal: str) -> HierarchicalEpisodeResult:
        """
        Run a full hierarchical planning episode.

        Parameters
        ----------
        state : Current environment state.
        goal  : Natural-language goal description.

        Returns
        -------
        HierarchicalEpisodeResult with full execution history.
        """
        result = self.manager.run_episode(
            initial_state = state,
            goal          = goal,
            worker        = self.worker,
            env_step_fn   = self.env_step_fn,
        )
        self._episodes.append(result)
        return result

    def stats(self) -> Dict[str, Any]:
        """Aggregate statistics over all episodes run so far."""
        if not self._episodes:
            return {"n_episodes": 0}
        n          = len(self._episodes)
        goal_rate  = sum(e.goal_achieved for e in self._episodes) / n
        mean_steps = sum(e.total_steps   for e in self._episodes) / n
        mean_reward= sum(e.total_reward  for e in self._episodes) / n
        viol_rate  = sum(e.safety_violations > 0 for e in self._episodes) / n
        reasons    : Dict[str, int] = {}
        for e in self._episodes:
            reasons[e.termination_reason] = reasons.get(e.termination_reason, 0) + 1

        return {
            "n_episodes"            : n,
            "goal_achievement_rate" : goal_rate,
            "mean_steps_per_episode": mean_steps,
            "mean_reward_per_episode": mean_reward,
            "safety_violation_rate" : viol_rate,
            "termination_reasons"   : reasons,
        }

    def __repr__(self) -> str:
        return (
            f"HierarchicalPlanner("
            f"options={self.manager.option_library.size}, "
            f"episodes={len(self._episodes)})"
        )


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_hierarchical_planner(
    value_agent   : ValueLearningAgent,
    option_library: OptionLibrary,
    env_step_fn   : Callable[[State, Action], State],
    goal_fn       : Optional[Callable[[State, str], bool]] = None,
    safety_gate_fn: Optional[Callable[[str], bool]] = None,
    max_options   : int = 10,
    step_budget   : int = 100,
    feature_size  : int = 5,
) -> HierarchicalPlanner:
    """
    Convenience factory: wire a ManagerAgent + WorkerAgent into a planner.

    Parameters
    ----------
    value_agent    : Trained ValueLearningAgent.
    option_library : Pre-populated OptionLibrary.
    env_step_fn    : Environment transition ``f(state, action) → next_state``.
    goal_fn        : Episode-success predicate ``f(state, goal) → bool``.
    safety_gate_fn : Plan safety check ``f(plan_str) → bool``.
    max_options    : Max option executions per episode.
    step_budget    : Max total primitive steps per episode.
    feature_size   : Feature vector dimensionality.

    Returns
    -------
    HierarchicalPlanner ready to call ``.plan(state, goal)``.
    """
    manager = ManagerAgent(
        value_agent    = value_agent,
        option_library = option_library,
        max_options    = max_options,
        step_budget    = step_budget,
        goal_fn        = goal_fn,
    )
    worker = WorkerAgent(
        value_agent    = value_agent,
        feature_size   = feature_size,
        safety_gate_fn = safety_gate_fn,
    )
    return HierarchicalPlanner(
        manager     = manager,
        worker      = worker,
        env_step_fn = env_step_fn,
    )
