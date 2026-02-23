"""
Strategy Data Layer — Prometheus v0.97 (WP6)

Provides a unified data-loading interface for the PrometheusStar dashboard.
Loads, normalises, and caches evolution data from:

  - OpenRA curriculum runs  (run_prometheusstar_openra.py stage_results format)
  - MicroRTS curriculum runs (run_prometheusstar_microrts.py stage_results format)
  - OOD benchmark results   (benchmarks/ood_benchmark.py OODBenchmarkResult)
  - Value-learning weight history

All functions return plain Python dicts / lists so the dashboard has no
dependency on internal Prometheus classes at render time.

Public API
----------
generate_synthetic_openra_run(seed)   → List[stage_result_dict]
generate_synthetic_microrts_run(seed) → List[stage_result_dict]
flatten_generation_log(stage_results) → pd.DataFrame
agent_params_over_generations(stage_results) → pd.DataFrame
stage_summary_df(stage_results)       → pd.DataFrame
ood_summary_df(benchmark_results)     → pd.DataFrame
value_weight_df(weight_history, names) → pd.DataFrame
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Synthetic data generators (used when no real run data is available)
# ---------------------------------------------------------------------------

def generate_synthetic_openra_run(
    seed:         int = 42,
    n_stages:     int = 4,
    noise:        float = 0.06,
) -> List[Dict[str, Any]]:
    """
    Generate realistic synthetic OpenRA curriculum run data.

    Returns a list of stage_result dicts matching the format produced by
    run_prometheusstar_openra.run_stage().
    """
    rng = np.random.default_rng(seed)

    curriculum = [
        {"stage": 1, "name": "Basic Controls",       "difficulty": "easy",   "target": 0.70,
         "generations": 10, "population": 6},
        {"stage": 2, "name": "Resource Management",  "difficulty": "medium",  "target": 0.55,
         "generations": 15, "population": 8},
        {"stage": 3, "name": "Tactical Response",    "difficulty": "hard",    "target": 0.40,
         "generations": 20, "population": 10},
        {"stage": 4, "name": "Strategic Depth",      "difficulty": "expert",  "target": 0.25,
         "generations": 25, "population": 12},
    ]

    # Initial agent strategy params (random starting point)
    param_names = ["aggression", "economy_focus", "expansion_rate",
                   "tech_priority", "defense_bias"]
    agent_params = {k: float(rng.uniform(0.3, 0.7)) for k in param_names}

    results = []
    for cfg in curriculum[:n_stages]:
        target  = cfg["target"]
        n_gen   = cfg["generations"]
        pop     = cfg["population"]

        # Simulate a sigmoid learning curve with noise
        t       = np.linspace(0, 5, n_gen)
        base    = target * (1 / (1 + np.exp(-t + 2.5)))
        noise_v = rng.normal(0, noise, n_gen)
        best_rates = np.clip(base + noise_v, 0.0, 1.0)
        # Ensure non-decreasing best rate
        for i in range(1, n_gen):
            if best_rates[i] < best_rates[i-1]:
                best_rates[i] = best_rates[i-1] * rng.uniform(0.98, 1.01)
        best_rates = np.clip(best_rates, 0.0, 1.0)

        mean_rates = np.clip(best_rates - rng.uniform(0.05, 0.15, n_gen), 0.0, 1.0)

        # Evolve agent params slightly each stage
        for k in param_names:
            agent_params[k] = float(
                np.clip(agent_params[k] + rng.normal(0, 0.07), 0.0, 1.0)
            )

        gen_log = []
        for g in range(n_gen):
            gen_log.append({
                "generation":     g + 1,
                "best_win_rate":  float(best_rates[g]),
                "mean_win_rate":  float(mean_rates[g]),
                "agent_params":   dict(agent_params),   # snapshot of params at this gen
                "population_size": pop,
            })

        best_wr   = float(best_rates[-1])
        target_met = best_wr >= target

        results.append({
            "stage":           cfg["stage"],
            "name":            cfg["name"],
            "difficulty":      cfg["difficulty"],
            "generations_run": n_gen,
            "best_win_rate":   best_wr,
            "target":          target,
            "target_met":      target_met,
            "agent_params":    dict(agent_params),
            "generation_log":  gen_log,
            "wall_clock_s":    float(rng.uniform(30, 120)),
            "game_type":       "openra",
        })

    return results


def generate_synthetic_microrts_run(
    seed:     int = 7,
    n_stages: int = 3,
    noise:    float = 0.05,
) -> List[Dict[str, Any]]:
    """
    Generate realistic synthetic MicroRTS curriculum run data.

    Returns a list of stage_result dicts matching the format produced by
    run_prometheusstar_microrts.run_curriculum_stage().
    """
    rng = np.random.default_rng(seed)

    curriculum = [
        {"stage": 1, "name": "RandomBiasedAI",  "opponent": "RandomBiasedAI",
         "target": 0.60, "generations": 8},
        {"stage": 2, "name": "WorkerRush",       "opponent": "WorkerRushAI",
         "target": 0.50, "generations": 12},
        {"stage": 3, "name": "LightRush",        "opponent": "LightRushAI",
         "target": 0.40, "generations": 16},
    ]

    param_names = ["aggression", "economy_focus", "expansion_rate",
                   "tech_priority", "defense_bias"]
    agent_params = {k: float(rng.uniform(0.3, 0.7)) for k in param_names}

    results = []
    for cfg in curriculum[:n_stages]:
        target = cfg["target"]
        n_gen  = cfg["generations"]

        t          = np.linspace(0, 4, n_gen)
        base       = target * (1 / (1 + np.exp(-t + 2.0)))
        best_rates = np.clip(base + rng.normal(0, noise, n_gen), 0.0, 1.0)
        for i in range(1, n_gen):
            if best_rates[i] < best_rates[i-1]:
                best_rates[i] = best_rates[i-1] * rng.uniform(0.97, 1.01)
        best_rates = np.clip(best_rates, 0.0, 1.0)
        mean_rates = np.clip(best_rates - rng.uniform(0.05, 0.12, n_gen), 0.0, 1.0)

        for k in param_names:
            agent_params[k] = float(
                np.clip(agent_params[k] + rng.normal(0, 0.06), 0.0, 1.0)
            )

        gen_log = []
        for g in range(n_gen):
            gen_log.append({
                "generation":    g + 1,
                "best_win_rate": float(best_rates[g]),
                "mean_win_rate": float(mean_rates[g]),
                "agent_params":  dict(agent_params),
            })

        results.append({
            "stage":           cfg["stage"],
            "name":            cfg["name"],
            "difficulty":      cfg["opponent"],
            "opponent":        cfg["opponent"],
            "generations_run": n_gen,
            "best_win_rate":   float(best_rates[-1]),
            "target":          target,
            "target_met":      float(best_rates[-1]) >= target,
            "agent_params":    dict(agent_params),
            "generation_log":  gen_log,
            "wall_clock_s":    float(rng.uniform(20, 80)),
            "game_type":       "microrts",
        })

    return results


# ---------------------------------------------------------------------------
# Data transformation helpers (produce DataFrames — imported lazily)
# ---------------------------------------------------------------------------

def flatten_generation_log(stage_results: List[Dict]) -> "pd.DataFrame":
    """
    Flatten stage_results into a long-form DataFrame with one row per generation.

    Columns:
        stage, stage_name, difficulty, generation, cumulative_generation,
        best_win_rate, mean_win_rate, target, game_type
    """
    import pandas as pd

    rows = []
    cumulative = 0
    for r in stage_results:
        for g in r["generation_log"]:
            rows.append({
                "stage":                r["stage"],
                "stage_name":           r["name"],
                "difficulty":           r.get("difficulty", ""),
                "generation":           g["generation"],
                "cumulative_generation": cumulative + g["generation"],
                "best_win_rate":        g["best_win_rate"],
                "mean_win_rate":        g["mean_win_rate"],
                "target":               r["target"],
                "game_type":            r.get("game_type", "unknown"),
            })
        cumulative += r["generations_run"]
    return pd.DataFrame(rows)


def agent_params_over_generations(stage_results: List[Dict]) -> "pd.DataFrame":
    """
    Extract agent strategy parameter evolution into a long-form DataFrame.

    Columns:
        stage, stage_name, generation, cumulative_generation,
        param_name, param_value
    """
    import pandas as pd

    rows = []
    cumulative = 0
    for r in stage_results:
        for g in r["generation_log"]:
            params = g.get("agent_params", r.get("agent_params", {}))
            for param_name, param_value in params.items():
                rows.append({
                    "stage":                r["stage"],
                    "stage_name":           r["name"],
                    "generation":           g["generation"],
                    "cumulative_generation": cumulative + g["generation"],
                    "param_name":           param_name,
                    "param_value":          float(param_value),
                })
        cumulative += r["generations_run"]
    return pd.DataFrame(rows)


def stage_summary_df(stage_results: List[Dict]) -> "pd.DataFrame":
    """
    One row per stage: stage, name, difficulty, target, best_win_rate,
    target_met, generations_run, wall_clock_s, game_type.
    """
    import pandas as pd

    rows = []
    for r in stage_results:
        params = r.get("agent_params", {})
        row = {
            "stage":           r["stage"],
            "name":            r["name"],
            "difficulty":      r.get("difficulty", ""),
            "target":          r["target"],
            "best_win_rate":   r["best_win_rate"],
            "target_met":      r["target_met"],
            "generations_run": r["generations_run"],
            "wall_clock_s":    r.get("wall_clock_s", 0.0),
            "game_type":       r.get("game_type", "unknown"),
        }
        row.update({f"param_{k}": v for k, v in params.items()})
        rows.append(row)
    return pd.DataFrame(rows)


def ood_summary_df(benchmark_results: List[Any]) -> "pd.DataFrame":
    """
    Convert a list of OODBenchmarkResult objects to a display DataFrame.
    Works with both real OODBenchmarkResult and plain dicts.
    """
    import pandas as pd

    rows = []
    for r in benchmark_results:
        if hasattr(r, "scenarios"):
            # Real OODBenchmarkResult
            row = {
                "detector":  r.detector_name,
                "auroc":     r.auroc,
                "tpr":       r.tpr,
                "fpr":       r.fpr,
                "in_dist_flagged":   r.scenarios["in_distribution"].ood_rate,
                "mild_flagged":      r.scenarios["mild_shift"].ood_rate,
                "severe_flagged":    r.scenarios["severe_shift"].ood_rate,
                "wall_clock_s":      r.wall_clock_s,
            }
        else:
            row = dict(r)
        rows.append(row)
    return pd.DataFrame(rows)


def value_weight_df(
    weight_history: List["np.ndarray"],
    feature_names:  Optional[List[str]] = None,
) -> "pd.DataFrame":
    """
    Convert a weight history list (one array per epoch) into a long-form
    DataFrame for plotting convergence.

    Columns: epoch, feature_name, weight_value
    """
    import pandas as pd

    arr = np.array(weight_history)    # (epochs, feature_size)
    n_epochs, n_features = arr.shape
    names = feature_names or [f"φ[{i}]" for i in range(n_features)]

    rows = []
    for ep in range(n_epochs):
        for j, name in enumerate(names):
            rows.append({
                "epoch":         ep,
                "feature_name":  name,
                "weight_value":  float(arr[ep, j]),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# JSON persistence helpers
# ---------------------------------------------------------------------------

def save_run(stage_results: List[Dict], filepath: str) -> None:
    """Persist stage_results to JSON (stripping non-serialisable objects)."""
    clean = []
    for r in stage_results:
        row = {k: v for k, v in r.items() if k != "best_agent"}
        clean.append(row)
    Path(filepath).write_text(json.dumps(clean, indent=2))
    logger.info("Saved %d stages to %s", len(stage_results), filepath)


def load_run(filepath: str) -> List[Dict]:
    """Load stage_results from JSON."""
    return json.loads(Path(filepath).read_text())
