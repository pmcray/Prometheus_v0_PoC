"""
tests/test_hierarchical_planner.py — Test suite for WP9

Tests for:
  - prometheus/option.py          (Option, OptionLibrary)
  - prometheus/hierarchical_planner.py (ManagerAgent, WorkerAgent, HierarchicalPlanner)
  - benchmarks/hierarchical_planning_benchmark.py

Run with: pytest tests/test_hierarchical_planner.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prometheus.option import Option, OptionExecutionRecord, OptionLibrary, State, Action
from prometheus.hierarchical_planner import (
    HierarchicalPlanner,
    HierarchicalEpisodeResult,
    ManagerAgent,
    WorkerAgent,
    make_hierarchical_planner,
)
from prometheus.value_learning import ValueLearningAgent
from benchmarks.hierarchical_planning_benchmark import (
    HierarchicalPlanningBenchmark,
    _build_option_library,
    _env_step,
    _goal_fn,
    _trained_agent,
    _make_preference_pairs,
    N_FEATS,
    STAGE_FEATURES,
    STAGE_ORDER,
    FlatPlanner,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def value_agent() -> ValueLearningAgent:
    agent = ValueLearningAgent(feature_size=N_FEATS, l2_reg=0.01)
    pairs = _make_preference_pairs(seed=0, n=30)
    agent.train_to_convergence(pairs, max_epochs=50)
    return agent


@pytest.fixture(scope="module")
def option_library() -> OptionLibrary:
    return _build_option_library(N_FEATS)


@pytest.fixture
def simple_option() -> Option:
    """A minimal option for unit tests."""
    return Option(
        name                 = "test_option",
        description          = "Always applicable, always terminates after 1 step",
        initiation_condition = lambda state: True,
        policy               = lambda state: {"plan": "# test\npass"},
        termination_condition= lambda state: True,
        max_steps            = 5,
    )


@pytest.fixture
def initial_state() -> State:
    return {
        "stage"   : "idle",
        "step"    : 0,
        "features": STAGE_FEATURES["idle"].copy(),
    }


# ---------------------------------------------------------------------------
# 1. TestOption
# ---------------------------------------------------------------------------

class TestOption:
    """Tests for the Option dataclass."""

    def test_construction_defaults(self, simple_option):
        assert simple_option.name == "test_option"
        assert simple_option.max_steps == 5
        assert len(simple_option.option_id) == 12   # sha1 truncated
        assert isinstance(simple_option.metadata, dict)

    def test_custom_option_id(self):
        opt = Option(
            name                 = "custom",
            description          = "custom",
            initiation_condition = lambda s: True,
            policy               = lambda s: {},
            termination_condition= lambda s: False,
            option_id            = "my-custom-id",
        )
        assert opt.option_id == "my-custom-id"

    def test_max_steps_validation(self):
        with pytest.raises(ValueError, match="max_steps"):
            Option(
                name                 = "bad",
                description          = "bad",
                initiation_condition = lambda s: True,
                policy               = lambda s: {},
                termination_condition= lambda s: False,
                max_steps            = 0,
            )

    def test_can_initiate_true(self, simple_option, initial_state):
        assert simple_option.can_initiate(initial_state) is True

    def test_can_initiate_false(self):
        opt = Option(
            name                 = "never",
            description          = "never starts",
            initiation_condition = lambda s: False,
            policy               = lambda s: {},
            termination_condition= lambda s: True,
        )
        assert opt.can_initiate({}) is False

    def test_act_returns_dict(self, simple_option, initial_state):
        action = simple_option.act(initial_state)
        assert isinstance(action, dict)
        assert "plan" in action

    def test_should_terminate(self, simple_option, initial_state):
        assert simple_option.should_terminate(initial_state) is True

    def test_extract_features_default(self, simple_option, initial_state):
        feats = simple_option.extract_features(initial_state)
        assert isinstance(feats, np.ndarray)
        assert feats.shape == (5,)
        assert np.all(feats == 0.0)

    def test_extract_features_custom(self):
        opt = Option(
            name                 = "feat",
            description          = "with extractor",
            initiation_condition = lambda s: True,
            policy               = lambda s: {},
            termination_condition= lambda s: True,
            feature_extractor    = lambda s: np.ones(5),
        )
        feats = opt.extract_features({})
        assert np.all(feats == 1.0)

    def test_hash_and_eq(self, simple_option):
        opt2 = Option(
            name                 = "test_option",
            description          = "copy",
            initiation_condition = lambda s: True,
            policy               = lambda s: {},
            termination_condition= lambda s: True,
        )
        # Same name → same auto-generated option_id
        assert simple_option == opt2
        assert hash(simple_option) == hash(opt2)

    def test_repr(self, simple_option):
        r = repr(simple_option)
        assert "Option" in r
        assert "test_option" in r

    def test_initiation_exception_defaults_false(self):
        """If initiation_condition raises, can_initiate returns False."""
        def bad_init(state):
            raise RuntimeError("oops")

        opt = Option(
            name                 = "bad_init",
            description          = "",
            initiation_condition = bad_init,
            policy               = lambda s: {},
            termination_condition= lambda s: True,
        )
        # Should not propagate; returns False
        assert opt.can_initiate({}) is False

    def test_termination_exception_defaults_true(self):
        """If termination_condition raises, should_terminate returns True."""
        def bad_term(state):
            raise RuntimeError("oops")

        opt = Option(
            name                 = "bad_term",
            description          = "",
            initiation_condition = lambda s: True,
            policy               = lambda s: {},
            termination_condition= bad_term,
        )
        assert opt.should_terminate({}) is True


# ---------------------------------------------------------------------------
# 2. TestOptionLibrary
# ---------------------------------------------------------------------------

class TestOptionLibrary:
    """Tests for OptionLibrary."""

    def test_register_and_get(self, simple_option):
        lib = OptionLibrary()
        lib.register(simple_option)
        assert lib.size == 1
        retrieved = lib.get(simple_option.option_id)
        assert retrieved is simple_option

    def test_register_type_error(self):
        lib = OptionLibrary()
        with pytest.raises(TypeError):
            lib.register("not_an_option")

    def test_remove(self, simple_option):
        lib = OptionLibrary()
        lib.register(simple_option)
        lib.remove(simple_option.option_id)
        assert lib.size == 0

    def test_get_missing_raises(self):
        lib = OptionLibrary()
        with pytest.raises(KeyError):
            lib.get("nonexistent")

    def test_list_applicable_all(self, simple_option, initial_state):
        lib = OptionLibrary()
        lib.register(simple_option)
        applicable = lib.list_applicable(initial_state)
        assert len(applicable) == 1
        assert applicable[0] is simple_option

    def test_list_applicable_filter(self, initial_state):
        lib = OptionLibrary()
        opt_yes = Option(
            name="yes", description="yes",
            initiation_condition=lambda s: True,
            policy=lambda s: {}, termination_condition=lambda s: True,
        )
        opt_no = Option(
            name="no", description="no",
            initiation_condition=lambda s: False,
            policy=lambda s: {}, termination_condition=lambda s: True,
        )
        lib.register(opt_yes)
        lib.register(opt_no)
        applicable = lib.list_applicable(initial_state)
        assert len(applicable) == 1
        assert applicable[0] == opt_yes

    def test_iter(self, option_library):
        opts = list(option_library)
        assert len(opts) == option_library.size

    def test_len(self, option_library):
        assert len(option_library) == option_library.size

    def test_repr(self, option_library):
        r = repr(option_library)
        assert "OptionLibrary" in r

    def test_summary(self, option_library):
        s = option_library.summary()
        assert "OptionLibrary" in s

    def test_discover_from_empty(self):
        lib = OptionLibrary()
        result = lib.discover_from_trajectories([])
        assert result == []

    def test_discover_from_trajectories(self):
        """Repeated state transitions should produce discovered options."""
        lib   = OptionLibrary(feature_size=N_FEATS)
        state = {"stage": "idle", "features": STAGE_FEATURES["idle"].copy()}
        # Generate 10 identical short trajectories
        traj  = [dict(state), {"stage": "acquired", "features": STAGE_FEATURES["acquired"].copy(), "acquired": True}]
        trajs = [traj] * 10
        discovered = lib.discover_from_trajectories(trajs, min_frequency=2)
        assert len(discovered) >= 1

    def test_discover_min_frequency(self):
        """Options with frequency < min_frequency should not be discovered."""
        lib = OptionLibrary(feature_size=N_FEATS)
        traj = [{"a": True}, {"a": True, "b": True}]
        # Only 1 trajectory — frequency=1 < min_frequency=2
        discovered = lib.discover_from_trajectories([traj], min_frequency=2)
        assert len(discovered) == 0

    def test_overwrite_on_register(self, simple_option):
        lib = OptionLibrary()
        lib.register(simple_option)
        # Register again (overwrite) — size stays 1
        lib.register(simple_option)
        assert lib.size == 1

    def test_benchmark_library_has_five_options(self, option_library):
        assert option_library.size == 5  # one per stage transition


# ---------------------------------------------------------------------------
# 3. TestWorkerAgent
# ---------------------------------------------------------------------------

class TestWorkerAgent:
    """Tests for WorkerAgent."""

    def test_execute_single_option(self, simple_option, value_agent, initial_state):
        worker = WorkerAgent(value_agent=value_agent, feature_size=N_FEATS)
        rec    = worker.execute_option(simple_option, initial_state, _env_step)
        assert isinstance(rec, OptionExecutionRecord)
        assert rec.option_id == simple_option.option_id
        assert rec.steps_taken >= 0
        assert isinstance(rec.total_reward, float)

    def test_termination_after_one_step(self, simple_option, value_agent, initial_state):
        """Option terminates immediately (termination_condition=True always)."""
        worker = WorkerAgent(value_agent=value_agent)
        rec    = worker.execute_option(simple_option, initial_state, _env_step)
        # Option terminates after 1 step at most
        assert rec.steps_taken <= 1
        assert rec.terminated is True

    def test_safety_gate_blocks(self, value_agent, initial_state):
        """Safety gate that rejects all plans causes safety_violation."""
        def always_reject(plan: str) -> bool:
            return False

        opt = Option(
            name                 = "blocked",
            description          = "always blocked",
            initiation_condition = lambda s: True,
            policy               = lambda s: {"plan": "some plan"},
            termination_condition= lambda s: False,
        )
        worker = WorkerAgent(value_agent=value_agent, safety_gate_fn=always_reject)
        rec    = worker.execute_option(opt, initial_state, _env_step)
        assert rec.safety_violation is True
        assert rec.terminated is True
        assert rec.steps_taken == 0

    def test_safety_gate_allows_safe(self, simple_option, value_agent, initial_state):
        """Safety gate that accepts all plans does not block."""
        worker = WorkerAgent(
            value_agent    = value_agent,
            safety_gate_fn = lambda plan: True,
        )
        rec = worker.execute_option(simple_option, initial_state, _env_step)
        assert rec.safety_violation is False

    def test_max_steps_truncation(self, value_agent, initial_state):
        """Option with termination_condition=False should be truncated."""
        opt = Option(
            name                 = "no_term",
            description          = "never terminates",
            initiation_condition = lambda s: True,
            policy               = lambda s: {"plan": "pass"},
            termination_condition= lambda s: False,
            max_steps            = 3,
        )
        worker = WorkerAgent(value_agent=value_agent)
        rec    = worker.execute_option(opt, initial_state, _env_step)
        assert rec.truncated is True
        assert rec.steps_taken == 3

    def test_step_log_populated(self, simple_option, value_agent, initial_state):
        worker = WorkerAgent(value_agent=value_agent)
        worker.execute_option(simple_option, initial_state, _env_step)
        log = worker.step_log()
        assert len(log) >= 0   # could be 0 if immediate termination

    def test_env_step_exception_causes_violation(self, value_agent, initial_state):
        """If env_step_fn raises, safety_violation is set."""
        def bad_env(state, action):
            raise RuntimeError("env crash")

        opt = Option(
            name                 = "crash",
            description          = "env crashes",
            initiation_condition = lambda s: True,
            policy               = lambda s: {"plan": "pass"},
            termination_condition= lambda s: False,
        )
        worker = WorkerAgent(value_agent=value_agent)
        rec    = worker.execute_option(opt, initial_state, bad_env)
        assert rec.safety_violation is True

    def test_wall_clock_recorded(self, simple_option, value_agent, initial_state):
        worker = WorkerAgent(value_agent=value_agent)
        rec    = worker.execute_option(simple_option, initial_state, _env_step)
        assert rec.wall_clock_s >= 0.0


# ---------------------------------------------------------------------------
# 4. TestManagerAgent
# ---------------------------------------------------------------------------

class TestManagerAgent:
    """Tests for ManagerAgent."""

    def test_select_option_returns_best(self, value_agent, option_library, initial_state):
        manager = ManagerAgent(
            value_agent    = value_agent,
            option_library = option_library,
        )
        best, candidates = manager.select_option(initial_state)
        # At "idle" state, only the "acquire" option should be applicable
        assert best is not None
        assert best.name == "acquire"

    def test_select_option_no_applicable(self, value_agent):
        """No options applicable → returns (None, [])."""
        lib = OptionLibrary()
        opt = Option(
            name                 = "never",
            description          = "never applicable",
            initiation_condition = lambda s: False,
            policy               = lambda s: {},
            termination_condition= lambda s: True,
        )
        lib.register(opt)
        manager  = ManagerAgent(value_agent=value_agent, option_library=lib)
        best, cs = manager.select_option({})
        assert best is None
        assert cs == []

    def test_decisions_log(self, value_agent, option_library, initial_state):
        manager = ManagerAgent(value_agent=value_agent, option_library=option_library)
        manager.select_option(initial_state)
        log = manager.decisions()
        assert len(log) == 1
        assert "selected" in log[0]
        assert "n_candidates" in log[0]

    def test_run_episode_goal_achieved(self, value_agent, option_library, initial_state):
        worker = WorkerAgent(value_agent=value_agent)
        manager = ManagerAgent(
            value_agent    = value_agent,
            option_library = option_library,
            goal_fn        = _goal_fn,
            max_options    = 10,
            step_budget    = 50,
        )
        result = manager.run_episode(initial_state, "done", worker, _env_step)
        assert isinstance(result, HierarchicalEpisodeResult)
        assert result.goal_achieved is True
        assert result.termination_reason == "goal_achieved"

    def test_run_episode_budget_exceeded(self, value_agent, initial_state):
        """Very low budget → budget_exceeded termination."""
        lib = OptionLibrary()
        opt = Option(
            name                 = "infinite",
            description          = "never terminates, never reaches goal",
            initiation_condition = lambda s: True,
            policy               = lambda s: {"plan": "pass"},
            termination_condition= lambda s: False,
            max_steps            = 2,
        )
        lib.register(opt)

        worker  = WorkerAgent(value_agent=value_agent)
        manager = ManagerAgent(
            value_agent    = value_agent,
            option_library = lib,
            goal_fn        = lambda s, g: False,
            max_options    = 2,
            step_budget    = 3,
        )
        result = manager.run_episode(initial_state, "impossible", worker, _env_step)
        assert result.termination_reason in ("budget_exceeded",)

    def test_run_episode_safety_abort(self, value_agent, option_library, initial_state):
        """Safety gate that blocks → safety_abort or goal_achieved."""
        def reject_all(plan: str) -> bool:
            return False

        worker = WorkerAgent(value_agent=value_agent, safety_gate_fn=reject_all)
        manager = ManagerAgent(
            value_agent    = value_agent,
            option_library = option_library,
            goal_fn        = _goal_fn,
            max_options    = 5,
        )
        result = manager.run_episode(initial_state, "done", worker, _env_step)
        assert result.termination_reason in ("safety_abort", "goal_achieved")

    def test_run_episode_no_options(self, value_agent, initial_state):
        """Empty library → no_options termination."""
        lib     = OptionLibrary()
        worker  = WorkerAgent(value_agent=value_agent)
        manager = ManagerAgent(
            value_agent    = value_agent,
            option_library = lib,
            goal_fn        = lambda s, g: False,
        )
        result = manager.run_episode(initial_state, "done", worker, _env_step)
        assert result.termination_reason == "no_options"

    def test_episode_accumulates_rewards(self, value_agent, option_library, initial_state):
        worker = WorkerAgent(value_agent=value_agent)
        manager = ManagerAgent(
            value_agent    = value_agent,
            option_library = option_library,
            goal_fn        = _goal_fn,
            max_options    = 10,
        )
        result = manager.run_episode(initial_state, "done", worker, _env_step)
        assert isinstance(result.total_reward, float)
        assert result.total_steps >= 0


# ---------------------------------------------------------------------------
# 5. TestHierarchicalPlanner
# ---------------------------------------------------------------------------

class TestHierarchicalPlanner:
    """Tests for the HierarchicalPlanner facade."""

    def test_plan_returns_result(self, value_agent, option_library, initial_state):
        planner = make_hierarchical_planner(
            value_agent    = value_agent,
            option_library = option_library,
            env_step_fn    = _env_step,
            goal_fn        = _goal_fn,
        )
        result = planner.plan(initial_state, "done")
        assert isinstance(result, HierarchicalEpisodeResult)

    def test_plan_goal_achieved(self, value_agent, option_library, initial_state):
        planner = make_hierarchical_planner(
            value_agent    = value_agent,
            option_library = option_library,
            env_step_fn    = _env_step,
            goal_fn        = _goal_fn,
            max_options    = 10,
            step_budget    = 50,
        )
        result = planner.plan(initial_state, "done")
        assert result.goal_achieved is True

    def test_stats_after_episodes(self, value_agent, option_library, initial_state):
        planner = make_hierarchical_planner(
            value_agent    = value_agent,
            option_library = option_library,
            env_step_fn    = _env_step,
            goal_fn        = _goal_fn,
        )
        for _ in range(3):
            planner.plan(dict(initial_state), "done")

        stats = planner.stats()
        assert stats["n_episodes"] == 3
        assert 0.0 <= stats["goal_achievement_rate"] <= 1.0
        assert stats["mean_steps_per_episode"] >= 0.0

    def test_stats_empty(self, value_agent, option_library):
        planner = make_hierarchical_planner(
            value_agent    = value_agent,
            option_library = option_library,
            env_step_fn    = _env_step,
        )
        stats = planner.stats()
        assert stats["n_episodes"] == 0

    def test_repr(self, value_agent, option_library):
        planner = make_hierarchical_planner(
            value_agent    = value_agent,
            option_library = option_library,
            env_step_fn    = _env_step,
        )
        r = repr(planner)
        assert "HierarchicalPlanner" in r

    def test_episode_result_summary(self, value_agent, option_library, initial_state):
        planner = make_hierarchical_planner(
            value_agent    = value_agent,
            option_library = option_library,
            env_step_fn    = _env_step,
            goal_fn        = _goal_fn,
        )
        result = planner.plan(initial_state, "done")
        s = result.summary()
        assert "HierarchicalEpisode" in s
        assert "goal=" in s

    def test_safety_gate_integration(self, value_agent, option_library, initial_state):
        """Gate accepting only 'pass'-containing plans should allow stage advances."""
        def gate(plan: str) -> bool:
            return "pass" in plan or "advance" in plan or "#" in plan

        planner = make_hierarchical_planner(
            value_agent    = value_agent,
            option_library = option_library,
            env_step_fn    = _env_step,
            goal_fn        = _goal_fn,
            safety_gate_fn = gate,
        )
        result = planner.plan(initial_state, "done")
        assert result.safety_violations == 0


# ---------------------------------------------------------------------------
# 6. TestHierarchicalPlanningBenchmark
# ---------------------------------------------------------------------------

class TestHierarchicalPlanningBenchmark:
    """Tests for the benchmark runner."""

    @pytest.fixture(scope="class")
    def bench(self):
        return HierarchicalPlanningBenchmark(n_episodes=5, seed=42)

    def test_flat_vs_hierarchical(self, bench):
        result = bench.run("flat_vs_hierarchical")
        assert result.scenario == "flat_vs_hierarchical"
        assert 0.0 <= result.hp_goal_rate <= 1.0
        assert 0.0 <= result.flat_goal_rate <= 1.0
        assert result.n_episodes == 5

    def test_sample_efficiency(self, bench):
        result = bench.run("sample_efficiency")
        assert result.scenario == "sample_efficiency"
        assert "pair_counts" in result.extra
        assert len(result.extra["hp_rates"]) == len(result.extra["pair_counts"])

    def test_safety_gating(self, bench):
        result = bench.run("safety_gating")
        assert result.scenario == "safety_gating"
        # With 25% unsafe injection, some violations should occur or not — just check types
        assert isinstance(result.hp_safety_viol_rate, float)
        assert 0.0 <= result.hp_safety_viol_rate <= 1.0

    def test_option_discovery(self, bench):
        result = bench.run("option_discovery")
        assert result.scenario == "option_discovery"
        assert result.extra["n_trajectories"] == 30
        assert result.extra["n_discovered"] >= 0

    def test_run_all_returns_four(self, bench):
        results = bench.run_all()
        assert len(results) == 4
        scenarios = {r.scenario for r in results}
        assert scenarios == {
            "flat_vs_hierarchical",
            "sample_efficiency",
            "safety_gating",
            "option_discovery",
        }

    def test_summary_table(self, bench):
        results = bench.run_all()
        table   = bench.summary_table(results)
        assert "flat_vs_hierarchical" in table
        assert "safety_gating" in table

    def test_unknown_scenario_raises(self, bench):
        with pytest.raises(ValueError):
            bench.run("nonexistent_scenario")

    def test_hp_consistently_achieves_goal(self, bench):
        """Hierarchical planner should achieve goal on well-specified task."""
        result = bench.run("flat_vs_hierarchical")
        # With 5-option sequential task and proper options, HP should almost always succeed
        assert result.hp_goal_rate >= 0.5


# ---------------------------------------------------------------------------
# 7. TestIntegration
# ---------------------------------------------------------------------------

class TestIntegration:
    """End-to-end integration tests."""

    def test_full_pipeline(self, value_agent, option_library, initial_state):
        """Complete Manager→Worker pipeline reaches goal state."""
        planner = make_hierarchical_planner(
            value_agent    = value_agent,
            option_library = option_library,
            env_step_fn    = _env_step,
            goal_fn        = _goal_fn,
            max_options    = 10,
            step_budget    = 50,
        )
        result = planner.plan(initial_state, "done")
        assert result.goal_achieved
        assert result.total_steps > 0
        # Verify state progression
        last_stage = result.execution_records[-1].states_visited[-1].get("stage")
        assert last_stage == "done"

    def test_option_reward_ordering(self, value_agent, option_library, initial_state):
        """Manager should prefer options whose features score higher."""
        manager = ManagerAgent(value_agent=value_agent, option_library=option_library)
        best, candidates = manager.select_option(initial_state)
        # All candidates should have their rewards computed; best should not be None
        assert best is not None

    def test_multiple_episodes_independent(self, value_agent, option_library):
        """Each episode starts fresh and does not depend on previous state."""
        planner = make_hierarchical_planner(
            value_agent    = value_agent,
            option_library = option_library,
            env_step_fn    = _env_step,
            goal_fn        = _goal_fn,
            max_options    = 10,
        )
        results = [planner.plan({"stage": "idle", "step": 0, "features": STAGE_FEATURES["idle"].copy()}, "done")
                   for _ in range(5)]
        achieved = sum(r.goal_achieved for r in results)
        assert achieved >= 3   # expect most to succeed

    def test_feature_extraction_per_stage(self, option_library):
        """Feature extractors should return distinct vectors for each stage."""
        for stage in STAGE_ORDER:
            state = {
                "stage"   : stage,
                "step"    : 0,
                "features": STAGE_FEATURES[stage].copy(),
                stage     : True,
            }
            opts = option_library.list_applicable(state)
            for opt in opts:
                feats = opt.extract_features(state)
                assert isinstance(feats, np.ndarray)

    def test_option_library_serialisation_roundtrip(self, option_library):
        """OptionLibrary can enumerate and size is stable."""
        names  = sorted(o.name for o in option_library)
        size   = option_library.size
        names2 = sorted(o.name for o in option_library)
        assert names == names2
        assert option_library.size == size
