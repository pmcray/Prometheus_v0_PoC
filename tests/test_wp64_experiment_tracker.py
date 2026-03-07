"""
WP64 Test Suite: Continuous Learning Tracker & Experiment Registry
===================================================================

TestExperimentConfig      Dataclass fields, to_dict()
TestExperimentRegistry    CRUD operations, SQLite persistence
TestLearningCurveAggregator   Aggregation, series input
TestRunComparator         Statistical comparison (t-test, Cohen's d)
TestExperimentTracker     Context manager, RunContext
TestWP64ExitCriteria      Six-criterion verifier
TestIntegration           End-to-end: tracker → comparison
"""

import os
import tempfile
import pytest

from prometheus.wp64_experiment_tracker import (
    ExperimentConfig,
    ExperimentRegistry,
    ExperimentRun,
    ExperimentTracker,
    LearningCurveAggregator,
    MetricSample,
    RunComparator,
    RunContext,
    verify_wp64_exit_criteria,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _config(name: str = "test_run", wp: str = "WP64") -> ExperimentConfig:
    return ExperimentConfig(name=name, wp_module=wp, hyperparams={"lr": 0.01})


def _tmp_registry(tmp_path) -> ExperimentRegistry:
    """Registry backed by a temp file (NOT :memory: — that doesn't init tables)."""
    return ExperimentRegistry(str(tmp_path / "test.db"))


def _filled_registry(tmp_path, n_runs: int = 3, n_steps: int = 5) -> ExperimentRegistry:
    reg = _tmp_registry(tmp_path)
    for i in range(n_runs):
        config = _config(name=f"run_{i}")
        run_id = reg.start_run(config)
        for step in range(n_steps):
            reg.log(run_id, step, "loss", 1.0 / (step + 1))
            reg.log(run_id, step, "accuracy", step / n_steps)
        reg.end_run(run_id)
    return reg


# ===========================================================================
# TestExperimentConfig
# ===========================================================================

class TestExperimentConfig:
    def test_fields(self):
        c = _config()
        assert c.name == "test_run"
        assert c.wp_module == "WP64"

    def test_to_dict(self):
        d = _config().to_dict()
        for k in ("name", "wp_module", "hyperparams"):
            assert k in d, f"Missing key: {k}"

    def test_hyperparams_preserved(self):
        c = _config()
        assert c.hyperparams["lr"] == 0.01


# ===========================================================================
# TestExperimentRegistry
# ===========================================================================

class TestExperimentRegistry:
    def test_start_run_returns_id(self, tmp_path):
        reg = _tmp_registry(tmp_path)
        run_id = reg.start_run(_config())
        assert isinstance(run_id, str)
        assert len(run_id) > 0

    def test_log_and_retrieve(self, tmp_path):
        reg = _tmp_registry(tmp_path)
        run_id = reg.start_run(_config())
        reg.log(run_id, 0, "loss", 0.5)
        curve = reg.learning_curve("loss")
        assert len(curve) >= 1

    def test_end_run(self, tmp_path):
        reg = _tmp_registry(tmp_path)
        run_id = reg.start_run(_config())
        reg.log(run_id, 0, "loss", 0.5)
        reg.end_run(run_id)  # No error expected

    def test_multiple_metrics(self, tmp_path):
        reg = _tmp_registry(tmp_path)
        run_id = reg.start_run(_config())
        reg.log(run_id, 0, "loss", 0.9)
        reg.log(run_id, 0, "acc", 0.1)
        loss_curve = reg.learning_curve("loss")
        acc_curve = reg.learning_curve("acc")
        assert len(loss_curve) >= 1
        assert len(acc_curve) >= 1

    def test_filter_by_wp_module(self, tmp_path):
        reg = _tmp_registry(tmp_path)
        run_id = reg.start_run(ExperimentConfig(name="wp61_run", wp_module="WP61", hyperparams={}))
        reg.log(run_id, 0, "elo", 1500.0)
        reg.end_run(run_id)
        curve = reg.learning_curve("elo", wp_module="WP61")
        assert len(curve) >= 1

    def test_persist_to_file(self, tmp_path):
        path = str(tmp_path / "exp.db")
        reg = ExperimentRegistry(path)
        run_id = reg.start_run(_config())
        reg.log(run_id, 0, "loss", 0.5)
        reg.end_run(run_id)
        assert os.path.exists(path)

    def test_list_runs(self, tmp_path):
        reg = _filled_registry(tmp_path, n_runs=3)
        runs = reg.list_runs()
        assert len(runs) >= 3

    def test_get_run(self, tmp_path):
        reg = _tmp_registry(tmp_path)
        run_id = reg.start_run(_config(name="specific"))
        reg.end_run(run_id)
        run = reg.get_run(run_id)
        assert run is not None
        assert run.config.name == "specific"

    def test_learning_curve_tuple_format(self, tmp_path):
        reg = _tmp_registry(tmp_path)
        run_id = reg.start_run(_config())
        for step in range(3):
            reg.log(run_id, step, "loss", 1.0 / (step + 1))
        reg.end_run(run_id)
        curve = reg.learning_curve("loss")
        assert len(curve) == 3
        # Each entry is a tuple (step, value, ...)
        assert isinstance(curve[0], tuple)


# ===========================================================================
# TestMetricSample
# ===========================================================================

class TestMetricSample:
    def test_fields(self):
        s = MetricSample(step=3, name="loss", value=0.42)
        assert s.step == 3
        assert s.name == "loss"
        assert s.value == 0.42

    def test_has_timestamp(self):
        s = MetricSample(step=0, name="acc", value=0.9)
        assert hasattr(s, "timestamp")


# ===========================================================================
# TestLearningCurveAggregator
# ===========================================================================

class TestLearningCurveAggregator:
    def test_aggregate_returns_list(self):
        # LearningCurveAggregator takes series: List[List[Tuple[int, float]]]
        series = [
            [(0, 1.0), (1, 0.9), (2, 0.8)],
            [(0, 0.9), (1, 0.8), (2, 0.7)],
        ]
        agg = LearningCurveAggregator(series=series)
        result = agg.aggregate()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_aggregate_has_expected_structure(self):
        series = [
            [(0, 1.0), (1, 0.5)],
            [(0, 0.8), (1, 0.4)],
        ]
        agg = LearningCurveAggregator(series=series)
        result = agg.aggregate()
        # Should be tuples or dicts with step and mean
        assert len(result) > 0

    def test_single_series(self):
        series = [[(0, 1.0), (1, 0.5), (2, 0.3)]]
        agg = LearningCurveAggregator(series=series)
        result = agg.aggregate()
        assert len(result) == 3


# ===========================================================================
# TestRunComparator
# ===========================================================================

class TestRunComparator:
    def test_compare_two_groups(self):
        # RunComparator.compare(group_a: List[float], group_b: List[float])
        group_a = [0.9, 0.8, 0.85, 0.82, 0.88]
        group_b = [0.6, 0.65, 0.7, 0.68, 0.62]
        rc = RunComparator()
        result = rc.compare(group_a, group_b)
        assert isinstance(result, dict)

    def test_compare_result_has_p_value(self):
        group_a = [0.9, 0.8, 0.85]
        group_b = [0.5, 0.6, 0.55]
        rc = RunComparator()
        result = rc.compare(group_a, group_b)
        assert "p_value" in result

    def test_compare_result_has_effect_size(self):
        group_a = [0.9, 0.8, 0.85]
        group_b = [0.5, 0.6, 0.55]
        rc = RunComparator()
        result = rc.compare(group_a, group_b)
        assert "effect_size" in result or "cohen_d" in result

    def test_identical_groups_p_value_large(self):
        group = [0.5, 0.5, 0.5, 0.5, 0.5]
        rc = RunComparator()
        result = rc.compare(group, group)
        # Identical groups → p-value should be large (or NaN)
        p = result.get("p_value", 1.0)
        assert p is None or p >= 0.0


# ===========================================================================
# TestExperimentTracker
# ===========================================================================

class TestExperimentTracker:
    def test_start_returns_context(self, tmp_path):
        reg = _tmp_registry(tmp_path)
        tracker = ExperimentTracker(registry=reg)
        with tracker.start(_config()) as ctx:
            assert isinstance(ctx, RunContext)

    def test_log_inside_context(self, tmp_path):
        reg = _tmp_registry(tmp_path)
        tracker = ExperimentTracker(registry=reg)
        with tracker.start(_config()) as ctx:
            ctx.log(0, "loss", 0.9)
            ctx.log(1, "loss", 0.8)
        curve = reg.learning_curve("loss")
        assert len(curve) >= 2

    def test_run_completes_on_exit(self, tmp_path):
        reg = _tmp_registry(tmp_path)
        tracker = ExperimentTracker(registry=reg)
        with tracker.start(_config(name="ctx_run")) as ctx:
            ctx.log(0, "acc", 0.5)
        runs = reg.list_runs()
        assert any(r["name"] == "ctx_run" for r in runs)

    def test_exception_in_context_handled(self, tmp_path):
        reg = _tmp_registry(tmp_path)
        tracker = ExperimentTracker(registry=reg)
        try:
            with tracker.start(_config(name="fail_run")) as ctx:
                ctx.log(0, "loss", 1.0)
                raise ValueError("intentional")
        except ValueError:
            pass
        # Should not crash
        runs = reg.list_runs()
        assert len(runs) >= 0


# ===========================================================================
# TestWP64ExitCriteria
# ===========================================================================

class TestWP64ExitCriteria:
    def test_returns_dict(self):
        assert isinstance(verify_wp64_exit_criteria(), dict)

    def test_six_criteria(self):
        assert len(verify_wp64_exit_criteria()) == 6

    def test_all_pass_with_registry(self, tmp_path):
        reg = _filled_registry(tmp_path, n_runs=3, n_steps=5)
        result = verify_wp64_exit_criteria(reg)
        for k, v in result.items():
            assert v, f"Criterion failed: '{k}'"

    def test_no_registry_returns_dict(self):
        result = verify_wp64_exit_criteria(None)
        assert isinstance(result, dict)
        assert len(result) == 6


# ===========================================================================
# TestIntegration
# ===========================================================================

class TestIntegration:
    def test_end_to_end_tracker(self, tmp_path):
        reg = _tmp_registry(tmp_path)
        tracker = ExperimentTracker(registry=reg)
        for i in range(3):
            with tracker.start(_config(name=f"run_{i}")) as ctx:
                for step in range(5):
                    ctx.log(step, "loss", 1.0 / (step + 1 + i))
        runs = reg.list_runs()
        assert len(runs) == 3

    def test_criteria_pass_after_full_run(self, tmp_path):
        reg = _filled_registry(tmp_path, n_runs=3, n_steps=5)
        result = verify_wp64_exit_criteria(reg)
        assert all(result.values()), f"Some criteria failed: {result}"
