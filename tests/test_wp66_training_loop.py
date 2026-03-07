"""
WP66 Test Suite: GPU-Optimised Long-Run Training Loop
======================================================

TestTrainingConfig        Config fields, defaults
TestCheckpointManager     Save, load, cleanup, latest pointer
TestPlateauDetector       Window detection, reset signal
TestLongRunTrainer        Step, run, budget enforcement
TestTrainingReport        Report structure, to_dict()
TestColabTrainingHelper   is_colab detection, save paths
TestWP66ExitCriteria      Six-criterion verifier
TestIntegration           End-to-end: train → report
"""

import os
import pytest
import tempfile

from prometheus.wp66_training_loop import (
    CheckpointManager,
    ColabTrainingHelper,
    LongRunTrainer,
    PlateauDetector,
    TrainingConfig,
    TrainingMetrics,
    TrainingReport,
    verify_wp66_exit_criteria,
)

# Alias for the Checkpoint imported from WP66
from prometheus.wp66_training_loop import Checkpoint as TrainingCheckpoint


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _config(
    max_generations: int = 5,
    wall_clock_budget_s: float = 30.0,
    checkpoint_every: int = 2,
) -> TrainingConfig:
    return TrainingConfig(
        max_generations=max_generations,
        wall_clock_budget_s=wall_clock_budget_s,
        checkpoint_every=checkpoint_every,
    )


def _trainer(tmp_dir: str, n_gens: int = 5) -> LongRunTrainer:
    config = _config(max_generations=n_gens)
    return LongRunTrainer(config=config)


# ===========================================================================
# TestTrainingConfig
# ===========================================================================

class TestTrainingConfig:
    def test_fields(self):
        c = _config()
        assert c.max_generations == 5
        assert c.checkpoint_every == 2

    def test_to_dict(self):
        d = _config().to_dict()
        for k in ("max_generations", "wall_clock_budget_s", "checkpoint_every"):
            assert k in d, f"Missing key: {k}"

    def test_defaults_sensible(self):
        c = TrainingConfig()
        assert c.max_generations > 0
        assert c.wall_clock_budget_s > 0


# ===========================================================================
# TestCheckpointManager
# ===========================================================================

class TestCheckpointManager:
    def test_save_creates_file(self, tmp_path):
        mgr = CheckpointManager(output_dir=str(tmp_path))
        ckpt = TrainingCheckpoint(generation=1, metrics={"loss": 0.5}, rng_state=None)
        path = mgr.save(ckpt)
        assert os.path.exists(path)

    def test_save_creates_latest_json(self, tmp_path):
        mgr = CheckpointManager(output_dir=str(tmp_path))
        ckpt = TrainingCheckpoint(generation=1, metrics={"loss": 0.5}, rng_state=None)
        mgr.save(ckpt)
        latest = os.path.join(str(tmp_path), "latest.json")
        assert os.path.exists(latest)

    def test_load_latest(self, tmp_path):
        mgr = CheckpointManager(output_dir=str(tmp_path))
        ckpt = TrainingCheckpoint(generation=3, metrics={"loss": 0.3}, rng_state=None)
        mgr.save(ckpt)
        loaded = mgr.load_latest()
        assert loaded is not None
        assert loaded.generation == 3

    def test_load_latest_none_when_empty(self, tmp_path):
        mgr = CheckpointManager(output_dir=str(tmp_path))
        assert mgr.load_latest() is None

    def test_cleanup_keeps_last_n(self, tmp_path):
        mgr = CheckpointManager(output_dir=str(tmp_path))
        for i in range(5):
            ckpt = TrainingCheckpoint(generation=i, metrics={}, rng_state=None)
            mgr.save(ckpt)
        mgr.cleanup(keep_last=2)
        ckpt_files = [f for f in os.listdir(str(tmp_path))
                      if f.startswith("ckpt_") and f.endswith(".json")]
        assert len(ckpt_files) <= 2

    def test_checkpoint_to_dict(self):
        ckpt = TrainingCheckpoint(generation=5, metrics={"loss": 0.1}, rng_state=None)
        d = ckpt.to_dict()
        assert "generation" in d
        assert "metrics" in d


# ===========================================================================
# TestPlateauDetector
# ===========================================================================

class TestPlateauDetector:
    def test_no_plateau_initially(self):
        det = PlateauDetector(window=3, min_improvement=0.01)
        for v in [1.0, 0.9, 0.8]:
            det.update(v)
        assert not det.plateau_detected()

    def test_plateau_detected_flat(self):
        det = PlateauDetector(window=3, min_improvement=0.01)
        for v in [0.5, 0.5, 0.5, 0.5]:
            det.update(v)
        assert det.plateau_detected()

    def test_plateau_not_detected_improving(self):
        det = PlateauDetector(window=4, min_improvement=0.001)
        for v in [1.0, 0.9, 0.8, 0.7, 0.6]:
            det.update(v)
        assert not det.plateau_detected()

    def test_reset_clears_history(self):
        det = PlateauDetector(window=3, min_improvement=0.01)
        for v in [0.5, 0.5, 0.5, 0.5]:
            det.update(v)
        assert det.plateau_detected()
        det.reset()
        assert not det.plateau_detected()


# ===========================================================================
# TestLongRunTrainer
# ===========================================================================

class TestLongRunTrainer:
    def test_step_returns_float(self):
        trainer = LongRunTrainer(config=_config(max_generations=3))
        val = trainer.step()
        assert isinstance(val, float)

    def test_run_returns_report(self):
        trainer = LongRunTrainer(config=_config(max_generations=5))
        report = trainer.run()
        assert isinstance(report, TrainingReport)

    def test_run_n_generations(self):
        trainer = LongRunTrainer(config=_config(max_generations=5))
        report = trainer.run()
        assert report.n_generations <= 5

    def test_report_has_metrics(self):
        trainer = LongRunTrainer(config=_config(max_generations=3))
        report = trainer.run()
        assert isinstance(report.metrics, list)
        assert len(report.metrics) > 0

    def test_wall_clock_budget_enforced(self):
        # Very short budget should terminate early
        config = TrainingConfig(max_generations=10000, wall_clock_budget_s=0.1)
        trainer = LongRunTrainer(config=config)
        report = trainer.run()
        assert report.n_generations < 10000

    def test_custom_step_fn(self):
        def my_step(gen, rng):
            return float(gen) * 0.1

        trainer = LongRunTrainer(
            config=_config(max_generations=3),
            step_fn=my_step,
        )
        report = trainer.run()
        assert report.n_generations == 3

    def test_checkpoint_with_dir(self, tmp_path):
        config = TrainingConfig(
            max_generations=4,
            checkpoint_every=2,
            checkpoint_dir=str(tmp_path),
        )
        trainer = LongRunTrainer(config=config)
        trainer.run()
        files = list(tmp_path.iterdir())
        assert len(files) >= 1  # At least one checkpoint created


# ===========================================================================
# TestTrainingReport
# ===========================================================================

class TestTrainingReport:
    def test_to_dict_keys(self):
        trainer = LongRunTrainer(config=_config(max_generations=3))
        report = trainer.run()
        d = report.to_dict()
        for k in ("n_generations", "elapsed_s", "metrics"):
            assert k in d, f"Missing key: {k}"

    def test_elapsed_s_positive(self):
        trainer = LongRunTrainer(config=_config(max_generations=3))
        report = trainer.run()
        assert report.elapsed_s >= 0.0


# ===========================================================================
# TestColabTrainingHelper
# ===========================================================================

class TestColabTrainingHelper:
    def test_is_colab_returns_bool(self):
        result = ColabTrainingHelper.is_colab()
        assert isinstance(result, bool)

    def test_is_colab_false_in_test_env(self):
        # In a standard pytest environment, should not be Colab
        assert ColabTrainingHelper.is_colab() is False

    def test_save_to_drive_noop_outside_colab(self):
        # Should return False gracefully when not in Colab
        result = ColabTrainingHelper.save_to_drive("/tmp/test.json", "/drive/test.json")
        assert result is False

    def test_notify_milestone_noop(self):
        # Should not crash
        ColabTrainingHelper.notify_milestone("Test milestone")


# ===========================================================================
# TestWP66ExitCriteria
# ===========================================================================

class TestWP66ExitCriteria:
    def _report(self) -> TrainingReport:
        trainer = LongRunTrainer(config=_config(max_generations=5))
        return trainer.run()

    def test_returns_dict(self):
        assert isinstance(verify_wp66_exit_criteria(), dict)

    def test_six_criteria(self):
        assert len(verify_wp66_exit_criteria()) == 6

    def test_all_pass_with_report(self):
        report = self._report()
        result = verify_wp66_exit_criteria(report)
        for k, v in result.items():
            assert v, f"Criterion failed: '{k}'"

    def test_no_report_returns_dict(self):
        result = verify_wp66_exit_criteria(None)
        assert isinstance(result, dict)
        assert len(result) == 6


# ===========================================================================
# TestIntegration
# ===========================================================================

class TestIntegration:
    def test_end_to_end_training(self):
        config = TrainingConfig(max_generations=10, wall_clock_budget_s=10.0)
        trainer = LongRunTrainer(config=config)
        report = trainer.run()
        assert report.n_generations <= 10
        assert isinstance(report.elapsed_s, float)

    def test_criteria_pass_after_full_run(self):
        trainer = LongRunTrainer(config=_config(max_generations=5))
        report = trainer.run()
        result = verify_wp66_exit_criteria(report)
        assert all(result.values()), f"Some criteria failed: {result}"
