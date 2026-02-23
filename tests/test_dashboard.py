"""
tests/test_dashboard.py — Unit tests for WP6 Strategy Visualisation (Prometheus v0.97)

Tests cover the prometheus.strategy_data data layer.  Streamlit page functions
are not exercised here (they require a running Streamlit server); instead we
verify the data transformation helpers that underpin every dashboard page.

Run with:
    pytest tests/test_dashboard.py -v
"""
from __future__ import annotations

import numpy as np
import pytest

from prometheus.strategy_data import (
    generate_synthetic_openra_run,
    generate_synthetic_microrts_run,
    flatten_generation_log,
    agent_params_over_generations,
    stage_summary_df,
    ood_summary_df,
    value_weight_df,
    save_run,
    load_run,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def openra_run():
    return generate_synthetic_openra_run(seed=42, n_stages=4)


@pytest.fixture(scope="module")
def microrts_run():
    return generate_synthetic_microrts_run(seed=7, n_stages=3)


# ---------------------------------------------------------------------------
# generate_synthetic_openra_run
# ---------------------------------------------------------------------------

class TestGenerateSyntheticOpenraRun:
    def test_returns_list(self, openra_run):
        assert isinstance(openra_run, list)

    def test_n_stages(self, openra_run):
        assert len(openra_run) == 4

    def test_stage_keys(self, openra_run):
        required = {
            "stage", "name", "difficulty", "generations_run",
            "best_win_rate", "target", "target_met",
            "agent_params", "generation_log", "wall_clock_s", "game_type",
        }
        for r in openra_run:
            assert required.issubset(r.keys()), f"Missing keys in stage {r['stage']}"

    def test_game_type(self, openra_run):
        for r in openra_run:
            assert r["game_type"] == "openra"

    def test_win_rate_in_range(self, openra_run):
        for r in openra_run:
            assert 0.0 <= r["best_win_rate"] <= 1.0

    def test_target_met_bool(self, openra_run):
        for r in openra_run:
            assert isinstance(r["target_met"], bool)
            assert r["target_met"] == (r["best_win_rate"] >= r["target"])

    def test_generation_log_length(self, openra_run):
        for r in openra_run:
            assert len(r["generation_log"]) == r["generations_run"]

    def test_generation_log_keys(self, openra_run):
        for r in openra_run:
            for g in r["generation_log"]:
                assert "generation" in g
                assert "best_win_rate" in g
                assert "mean_win_rate" in g

    def test_agent_params_keys(self, openra_run):
        expected_params = {
            "aggression", "economy_focus", "expansion_rate",
            "tech_priority", "defense_bias",
        }
        for r in openra_run:
            assert expected_params == set(r["agent_params"].keys())

    def test_reproducible_with_seed(self):
        run_a = generate_synthetic_openra_run(seed=99)
        run_b = generate_synthetic_openra_run(seed=99)
        for a, b in zip(run_a, run_b):
            assert abs(a["best_win_rate"] - b["best_win_rate"]) < 1e-9

    def test_different_seeds_differ(self):
        run_a = generate_synthetic_openra_run(seed=1)
        run_b = generate_synthetic_openra_run(seed=2)
        assert run_a[0]["best_win_rate"] != run_b[0]["best_win_rate"]

    def test_n_stages_param(self):
        run = generate_synthetic_openra_run(seed=0, n_stages=2)
        assert len(run) == 2

    def test_wall_clock_positive(self, openra_run):
        for r in openra_run:
            assert r["wall_clock_s"] > 0


# ---------------------------------------------------------------------------
# generate_synthetic_microrts_run
# ---------------------------------------------------------------------------

class TestGenerateSyntheticMicroRTSRun:
    def test_returns_list(self, microrts_run):
        assert isinstance(microrts_run, list)

    def test_n_stages(self, microrts_run):
        assert len(microrts_run) == 3

    def test_game_type(self, microrts_run):
        for r in microrts_run:
            assert r["game_type"] == "microrts"

    def test_stage_keys(self, microrts_run):
        required = {
            "stage", "name", "difficulty", "opponent",
            "generations_run", "best_win_rate", "target", "target_met",
            "agent_params", "generation_log", "wall_clock_s", "game_type",
        }
        for r in microrts_run:
            assert required.issubset(r.keys())

    def test_win_rates_in_range(self, microrts_run):
        for r in microrts_run:
            assert 0.0 <= r["best_win_rate"] <= 1.0
            for g in r["generation_log"]:
                assert 0.0 <= g["best_win_rate"] <= 1.0
                assert 0.0 <= g["mean_win_rate"] <= 1.0

    def test_n_stages_one(self):
        run = generate_synthetic_microrts_run(seed=0, n_stages=1)
        assert len(run) == 1


# ---------------------------------------------------------------------------
# flatten_generation_log
# ---------------------------------------------------------------------------

class TestFlattenGenerationLog:
    def test_returns_dataframe(self, openra_run):
        pd = pytest.importorskip("pandas")
        df = flatten_generation_log(openra_run)
        assert hasattr(df, "columns")

    def test_columns(self, openra_run):
        df = flatten_generation_log(openra_run)
        expected = {
            "stage", "stage_name", "difficulty", "generation",
            "cumulative_generation", "best_win_rate", "mean_win_rate",
            "target", "game_type",
        }
        assert expected.issubset(set(df.columns))

    def test_row_count(self, openra_run):
        df = flatten_generation_log(openra_run)
        total_gens = sum(r["generations_run"] for r in openra_run)
        assert len(df) == total_gens

    def test_cumulative_generation_monotonic(self, openra_run):
        df = flatten_generation_log(openra_run)
        cg = df["cumulative_generation"].tolist()
        assert cg == sorted(cg)

    def test_win_rate_range(self, openra_run):
        df = flatten_generation_log(openra_run)
        assert df["best_win_rate"].between(0.0, 1.0).all()
        assert df["mean_win_rate"].between(0.0, 1.0).all()

    def test_microrts_run(self, microrts_run):
        df = flatten_generation_log(microrts_run)
        total_gens = sum(r["generations_run"] for r in microrts_run)
        assert len(df) == total_gens

    def test_empty_input(self):
        df = flatten_generation_log([])
        assert len(df) == 0


# ---------------------------------------------------------------------------
# agent_params_over_generations
# ---------------------------------------------------------------------------

class TestAgentParamsOverGenerations:
    def test_returns_dataframe(self, openra_run):
        df = agent_params_over_generations(openra_run)
        assert hasattr(df, "columns")

    def test_columns(self, openra_run):
        df = agent_params_over_generations(openra_run)
        expected = {
            "stage", "stage_name", "generation",
            "cumulative_generation", "param_name", "param_value",
        }
        assert expected.issubset(set(df.columns))

    def test_param_values_in_range(self, openra_run):
        df = agent_params_over_generations(openra_run)
        assert df["param_value"].between(0.0, 1.0).all()

    def test_param_names_present(self, openra_run):
        df = agent_params_over_generations(openra_run)
        expected_params = {
            "aggression", "economy_focus", "expansion_rate",
            "tech_priority", "defense_bias",
        }
        assert expected_params == set(df["param_name"].unique())

    def test_row_count(self, openra_run):
        df = agent_params_over_generations(openra_run)
        n_params = 5
        total_gens = sum(r["generations_run"] for r in openra_run)
        assert len(df) == total_gens * n_params

    def test_empty_input(self):
        df = agent_params_over_generations([])
        assert len(df) == 0


# ---------------------------------------------------------------------------
# stage_summary_df
# ---------------------------------------------------------------------------

class TestStageSummaryDf:
    def test_returns_dataframe(self, openra_run):
        df = stage_summary_df(openra_run)
        assert hasattr(df, "columns")

    def test_one_row_per_stage(self, openra_run):
        df = stage_summary_df(openra_run)
        assert len(df) == len(openra_run)

    def test_required_columns(self, openra_run):
        df = stage_summary_df(openra_run)
        required = {
            "stage", "name", "difficulty", "target",
            "best_win_rate", "target_met", "generations_run", "game_type",
        }
        assert required.issubset(set(df.columns))

    def test_param_columns_added(self, openra_run):
        df = stage_summary_df(openra_run)
        param_cols = [c for c in df.columns if c.startswith("param_")]
        assert len(param_cols) == 5

    def test_win_rates_match_source(self, openra_run):
        df = stage_summary_df(openra_run)
        for i, r in enumerate(openra_run):
            assert abs(df.iloc[i]["best_win_rate"] - r["best_win_rate"]) < 1e-9

    def test_microrts_run(self, microrts_run):
        df = stage_summary_df(microrts_run)
        assert len(df) == len(microrts_run)


# ---------------------------------------------------------------------------
# ood_summary_df
# ---------------------------------------------------------------------------

class TestOodSummaryDf:
    def test_empty_input(self):
        df = ood_summary_df([])
        assert len(df) == 0

    def test_dict_input(self):
        fake = [
            {"detector": "iso", "auroc": 0.9, "tpr": 0.8, "fpr": 0.1},
            {"detector": "kde", "auroc": 0.85, "tpr": 0.75, "fpr": 0.15},
        ]
        df = ood_summary_df(fake)
        assert len(df) == 2
        assert "detector" in df.columns
        assert "auroc" in df.columns


# ---------------------------------------------------------------------------
# value_weight_df
# ---------------------------------------------------------------------------

class TestValueWeightDf:
    def test_shape(self):
        history = [np.random.randn(4) for _ in range(10)]
        df = value_weight_df(history)
        assert len(df) == 10 * 4

    def test_columns(self):
        history = [np.random.randn(3) for _ in range(5)]
        df = value_weight_df(history)
        assert {"epoch", "feature_name", "weight_value"} == set(df.columns)

    def test_custom_feature_names(self):
        history = [np.array([0.1, 0.2]) for _ in range(3)]
        df = value_weight_df(history, feature_names=["alpha", "beta"])
        assert set(df["feature_name"].unique()) == {"alpha", "beta"}

    def test_default_feature_names(self):
        history = [np.array([0.5, 0.6, 0.7]) for _ in range(2)]
        df = value_weight_df(history)
        names = set(df["feature_name"].unique())
        assert "φ[0]" in names
        assert "φ[2]" in names

    def test_epoch_range(self):
        n_ep = 8
        history = [np.ones(2) for _ in range(n_ep)]
        df = value_weight_df(history)
        assert df["epoch"].min() == 0
        assert df["epoch"].max() == n_ep - 1

    def test_weight_values_preserved(self):
        history = [np.array([0.123, 0.456])]
        df = value_weight_df(history)
        vals = sorted(df["weight_value"].tolist())
        assert abs(vals[0] - 0.123) < 1e-6
        assert abs(vals[1] - 0.456) < 1e-6


# ---------------------------------------------------------------------------
# save_run / load_run (JSON round-trip)
# ---------------------------------------------------------------------------

class TestSaveLoadRun:
    def test_round_trip(self, openra_run, tmp_path):
        out = str(tmp_path / "run.json")
        save_run(openra_run, out)
        loaded = load_run(out)
        assert len(loaded) == len(openra_run)

    def test_stage_fields_preserved(self, openra_run, tmp_path):
        out = str(tmp_path / "run2.json")
        save_run(openra_run, out)
        loaded = load_run(out)
        for orig, saved in zip(openra_run, loaded):
            assert orig["stage"] == saved["stage"]
            assert orig["name"]  == saved["name"]
            assert abs(orig["best_win_rate"] - saved["best_win_rate"]) < 1e-9

    def test_best_agent_stripped(self, tmp_path):
        """save_run must strip non-serialisable best_agent objects."""
        fake_run = [{
            "stage": 1, "name": "test", "difficulty": "easy",
            "generations_run": 1, "best_win_rate": 0.5, "target": 0.4,
            "target_met": True, "agent_params": {"a": 0.5},
            "generation_log": [], "wall_clock_s": 1.0, "game_type": "openra",
            "best_agent": object(),   # non-serialisable
        }]
        out = str(tmp_path / "run3.json")
        save_run(fake_run, out)   # should not raise
        loaded = load_run(out)
        assert "best_agent" not in loaded[0]

    def test_microrts_round_trip(self, microrts_run, tmp_path):
        out = str(tmp_path / "mrts.json")
        save_run(microrts_run, out)
        loaded = load_run(out)
        assert len(loaded) == len(microrts_run)
