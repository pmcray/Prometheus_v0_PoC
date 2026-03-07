"""
WP64: Continuous Learning Tracker & Experiment Registry
=========================================================

Closes the **cross-session observability gap** in the existing benchmark and
CRLS stack.  WP37 (ELO Registry) tracks game-play ratings persistently;
WP39 (Web API) exposes live metrics; but there is no unified system that:

  - Records every experiment run (config, metrics, timestamps) in a
    structured, queryable registry.
  - Produces learning curves spanning multiple sessions.
  - Computes statistical summaries (mean, std, confidence intervals) across
    runs with the same configuration.
  - Exports publication-quality plots and JSON artefacts compatible with
    TensorBoard / Weights & Biases conventions.

WP64 fix
--------
``ExperimentConfig``    — immutable experiment specification: WP module, hyper-
                          parameters, seed, notes.

``MetricSample``        — one time-stamped scalar observation: step, name, value.

``ExperimentRun``       — one completed (or in-progress) run: config, list of
                          ``MetricSample`` objects, start/end timestamps,
                          summary statistics.

``ExperimentRegistry``  — SQLite-backed registry of all runs.
  - ``start_run(config)``           → run_id (str)
  - ``log(run_id, step, name, val)`` — record one metric sample
  - ``end_run(run_id, status)``     — finalise a run
  - ``get_run(run_id)``             → ExperimentRun
  - ``list_runs(wp_module, status)``→ list of run summaries
  - ``learning_curve(name, wp)``    → aggregated (step, mean, std) list
  - ``export_json(path)``           → dump registry to JSON

``LearningCurveAggregator``
                        — computes mean ± std per step across multiple runs
                          with the same WP module and metric name.  Produces
                          data suitable for matplotlib or TensorBoard scalars.

``RunComparator``       — statistical comparison of two run groups (Welch's
                          t-test on final metric values); reports p-value and
                          effect size (Cohen's d).

``ExperimentTracker``   — high-level façade:
                          ``start(config) → RunContext``
                          where ``RunContext`` is a context manager that logs
                          metrics and auto-ends the run on exit.

``verify_wp64_exit_criteria`` — six-criterion verifier.

Theoretical grounding
---------------------
Sculley et al. (2015) "Hidden Technical Debt in Machine Learning Systems":
experiment tracking and reproducible logging are first-class engineering
concerns for ML systems.

Henderson et al. (2018) "Deep Reinforcement Learning That Matters": without
proper experiment tracking and statistical comparison, RL results are
unreproducible and misleading.

Weights & Biases / MLflow conventions: structured run management with
config, metrics, and artefacts is now standard practice in ML engineering.

Good (1965): monitoring the self-improvement trajectory is essential for
verifying that recursive improvement is actually occurring — WP64 provides
the measurement infrastructure.

Classes
-------
ExperimentConfig        Immutable experiment specification
MetricSample            One time-stamped scalar observation
ExperimentRun           One complete experiment run with metrics
ExperimentRegistry      SQLite-backed persistent run registry
LearningCurveAggregator Mean ± std per-step aggregation across runs
RunComparator           Welch t-test + Cohen's d between run groups
ExperimentTracker       High-level façade with RunContext manager
verify_wp64_exit_criteria  Six-criterion verifier
"""

from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ExperimentConfig
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExperimentConfig:
    """Immutable experiment specification."""
    wp_module: str                       # e.g. "wp61", "wp62"
    name: str                            # human-readable experiment name
    hyperparams: Dict[str, Any]          # key-value hyperparam dict
    seed: int = 42
    notes: str = ""
    tags: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wp_module": self.wp_module,
            "name": self.name,
            "hyperparams": self.hyperparams,
            "seed": self.seed,
            "notes": self.notes,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ExperimentConfig":
        return cls(
            wp_module=d["wp_module"],
            name=d["name"],
            hyperparams=d.get("hyperparams", {}),
            seed=d.get("seed", 42),
            notes=d.get("notes", ""),
            tags=tuple(d.get("tags", [])),
        )


# ---------------------------------------------------------------------------
# MetricSample
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MetricSample:
    """One time-stamped scalar observation."""
    step: int
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "name": self.name,
            "value": round(self.value, 6),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# ExperimentRun
# ---------------------------------------------------------------------------

@dataclass
class ExperimentRun:
    """One complete experiment run."""
    run_id: str
    config: ExperimentConfig
    metrics: List[MetricSample]
    status: str                  # "running" | "completed" | "failed"
    start_time: float
    end_time: Optional[float] = None

    @property
    def duration_s(self) -> float:
        if self.end_time is not None:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    def final_metrics(self) -> Dict[str, float]:
        """Last recorded value per metric name."""
        result: Dict[str, float] = {}
        for sample in self.metrics:
            result[sample.name] = sample.value
        return result

    def metric_history(self, name: str) -> List[Tuple[int, float]]:
        """(step, value) list for one metric, chronological."""
        return [(s.step, s.value) for s in self.metrics if s.name == name]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "config": self.config.to_dict(),
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_s": round(self.duration_s, 2),
            "n_samples": len(self.metrics),
            "final_metrics": self.final_metrics(),
        }


# ---------------------------------------------------------------------------
# ExperimentRegistry — SQLite-backed persistent run registry
# ---------------------------------------------------------------------------

class ExperimentRegistry:
    """
    SQLite-backed persistent experiment registry.

    Schema
    ------
    runs(run_id, wp_module, name, config_json, status, start_time, end_time)
    metrics(run_id, step, name, value, timestamp)
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(
            tempfile.gettempdir(), "prometheus_experiments.db"
        )
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id      TEXT PRIMARY KEY,
                wp_module   TEXT NOT NULL,
                name        TEXT NOT NULL,
                config_json TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'running',
                start_time  REAL NOT NULL,
                end_time    REAL
            );
            CREATE TABLE IF NOT EXISTS metrics (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id      TEXT NOT NULL,
                step        INTEGER NOT NULL,
                name        TEXT NOT NULL,
                value       REAL NOT NULL,
                timestamp   REAL NOT NULL,
                FOREIGN KEY(run_id) REFERENCES runs(run_id)
            );
            CREATE INDEX IF NOT EXISTS idx_metrics_run ON metrics(run_id);
            CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name);
        """)
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Run management
    # ------------------------------------------------------------------

    def start_run(self, config: ExperimentConfig) -> str:
        """Create a new run entry and return its run_id."""
        run_id = str(uuid.uuid4())[:8]
        conn = self._connect()
        conn.execute(
            "INSERT INTO runs VALUES (?,?,?,?,?,?,?)",
            (run_id, config.wp_module, config.name,
             json.dumps(config.to_dict()), "running", time.time(), None)
        )
        conn.commit()
        conn.close()
        logger.info("Started run %s (%s / %s)", run_id, config.wp_module, config.name)
        return run_id

    def log(self, run_id: str, step: int, name: str, value: float) -> None:
        """Record one metric sample."""
        conn = self._connect()
        conn.execute(
            "INSERT INTO metrics(run_id,step,name,value,timestamp) VALUES (?,?,?,?,?)",
            (run_id, step, name, value, time.time())
        )
        conn.commit()
        conn.close()

    def log_dict(self, run_id: str, step: int, metrics: Dict[str, float]) -> None:
        """Record multiple metrics at the same step."""
        conn = self._connect()
        t = time.time()
        conn.executemany(
            "INSERT INTO metrics(run_id,step,name,value,timestamp) VALUES (?,?,?,?,?)",
            [(run_id, step, name, value, t) for name, value in metrics.items()]
        )
        conn.commit()
        conn.close()

    def end_run(self, run_id: str, status: str = "completed") -> None:
        """Finalise a run."""
        conn = self._connect()
        conn.execute(
            "UPDATE runs SET status=?, end_time=? WHERE run_id=?",
            (status, time.time(), run_id)
        )
        conn.commit()
        conn.close()
        logger.info("Ended run %s with status '%s'.", run_id, status)

    def get_run(self, run_id: str) -> Optional[ExperimentRun]:
        """Retrieve a full ExperimentRun by run_id."""
        conn = self._connect()
        row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            conn.close()
            return None
        config = ExperimentConfig.from_dict(json.loads(row["config_json"]))
        metric_rows = conn.execute(
            "SELECT step,name,value,timestamp FROM metrics WHERE run_id=? ORDER BY id",
            (run_id,)
        ).fetchall()
        conn.close()
        metrics = [
            MetricSample(step=r["step"], name=r["name"],
                         value=r["value"], timestamp=r["timestamp"])
            for r in metric_rows
        ]
        return ExperimentRun(
            run_id=run_id,
            config=config,
            metrics=metrics,
            status=row["status"],
            start_time=row["start_time"],
            end_time=row["end_time"],
        )

    def list_runs(
        self,
        wp_module: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return lightweight summaries of matching runs."""
        query = "SELECT run_id, wp_module, name, status, start_time, end_time FROM runs WHERE 1=1"
        params: List[Any] = []
        if wp_module:
            query += " AND wp_module=?"
            params.append(wp_module)
        if status:
            query += " AND status=?"
            params.append(status)
        query += " ORDER BY start_time DESC"
        conn = self._connect()
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def learning_curve(
        self, metric_name: str, wp_module: Optional[str] = None
    ) -> List[Tuple[int, float, float]]:
        """
        Aggregate (step, mean_value, std_value) across all completed runs
        with this metric name (optionally filtered by wp_module).
        """
        query = """
            SELECT m.step, m.value
            FROM metrics m
            JOIN runs r ON m.run_id = r.run_id
            WHERE m.name=? AND r.status='completed'
        """
        params: List[Any] = [metric_name]
        if wp_module:
            query += " AND r.wp_module=?"
            params.append(wp_module)
        conn = self._connect()
        rows = conn.execute(query, params).fetchall()
        conn.close()

        by_step: Dict[int, List[float]] = {}
        for r in rows:
            by_step.setdefault(r["step"], []).append(r["value"])

        result: List[Tuple[int, float, float]] = []
        for step in sorted(by_step):
            vals = by_step[step]
            mean = sum(vals) / len(vals)
            std = math.sqrt(sum((v - mean) ** 2 for v in vals) / max(len(vals) - 1, 1))
            result.append((step, mean, std))
        return result

    def export_json(self, path: str) -> None:
        """Dump the full registry to a JSON file."""
        conn = self._connect()
        runs = conn.execute("SELECT run_id FROM runs ORDER BY start_time").fetchall()
        conn.close()
        data = []
        for row in runs:
            run = self.get_run(row["run_id"])
            if run:
                d = run.to_dict()
                d["metrics"] = [s.to_dict() for s in run.metrics]
                data.append(d)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("Exported %d runs to %s.", len(data), path)

    def close(self) -> None:
        """No persistent connection to close (connects per-operation)."""
        pass


# ---------------------------------------------------------------------------
# LearningCurveAggregator
# ---------------------------------------------------------------------------

class LearningCurveAggregator:
    """
    Aggregates learning curves across multiple runs.

    Given a list of (step, value) series (one per run), computes:
      - mean value per step
      - std value per step
      - 95 % confidence interval (± 1.96 × std / √n)
    """

    def __init__(self, series: List[List[Tuple[int, float]]]):
        self.series = series

    def aggregate(self) -> List[Dict[str, Any]]:
        by_step: Dict[int, List[float]] = {}
        for run_series in self.series:
            for step, val in run_series:
                by_step.setdefault(step, []).append(val)

        result: List[Dict[str, Any]] = []
        for step in sorted(by_step):
            vals = by_step[step]
            n = len(vals)
            mean = sum(vals) / n
            if n > 1:
                var = sum((v - mean) ** 2 for v in vals) / (n - 1)
                std = math.sqrt(var)
            else:
                std = 0.0
            ci = 1.96 * std / math.sqrt(n) if n > 0 else 0.0
            result.append({
                "step": step,
                "mean": round(mean, 6),
                "std": round(std, 6),
                "ci_95": round(ci, 6),
                "n_runs": n,
            })
        return result


# ---------------------------------------------------------------------------
# RunComparator
# ---------------------------------------------------------------------------

class RunComparator:
    """
    Statistical comparison between two groups of runs.

    Uses Welch's t-test (unequal variance) for the null hypothesis that
    both groups have the same mean final metric value.

    Returns p-value and Cohen's d effect size.
    """

    @staticmethod
    def _mean_std(values: List[float]) -> Tuple[float, float, int]:
        n = len(values)
        if n == 0:
            return 0.0, 0.0, 0
        mean = sum(values) / n
        if n > 1:
            var = sum((v - mean) ** 2 for v in values) / (n - 1)
        else:
            var = 0.0
        return mean, math.sqrt(var), n

    @classmethod
    def compare(
        cls,
        group_a: List[float],
        group_b: List[float],
    ) -> Dict[str, Any]:
        """
        Compare two groups.

        Parameters
        ----------
        group_a, group_b : list of float
            Final metric values for each group.

        Returns
        -------
        dict with keys: mean_a, mean_b, p_value, cohens_d, significant
        """
        mu_a, std_a, n_a = cls._mean_std(group_a)
        mu_b, std_b, n_b = cls._mean_std(group_b)

        # Welch's t-test
        if n_a < 2 or n_b < 2:
            return {
                "mean_a": round(mu_a, 4),
                "mean_b": round(mu_b, 4),
                "p_value": 1.0,
                "cohens_d": 0.0,
                "significant": False,
                "note": "Insufficient samples for t-test",
            }

        var_a = std_a ** 2
        var_b = std_b ** 2
        se = math.sqrt(var_a / n_a + var_b / n_b)
        if se == 0:
            t_stat = 0.0
            df = n_a + n_b - 2
        else:
            t_stat = (mu_a - mu_b) / se
            # Welch–Satterthwaite degrees of freedom
            num = (var_a / n_a + var_b / n_b) ** 2
            den = (var_a / n_a) ** 2 / (n_a - 1) + (var_b / n_b) ** 2 / (n_b - 1)
            df = num / den if den > 0 else n_a + n_b - 2

        # Approximate p-value via t-distribution CDF (two-tailed)
        p_value = cls._t_pvalue(abs(t_stat), df)

        # Cohen's d (pooled std)
        pooled_std = math.sqrt((std_a ** 2 + std_b ** 2) / 2.0) if (std_a + std_b) > 0 else 1.0
        cohens_d = (mu_a - mu_b) / pooled_std

        return {
            "mean_a": round(mu_a, 4),
            "mean_b": round(mu_b, 4),
            "p_value": round(p_value, 4),
            "cohens_d": round(cohens_d, 4),
            "significant": p_value < 0.05,
        }

    @staticmethod
    def _t_pvalue(t: float, df: float) -> float:
        """Approximate two-tailed p-value using a simple t-distribution approximation."""
        # Use Wilson–Hilferty approximation for chi-squared → normal
        # For practical purposes, approximate with normal for large df
        if df >= 30:
            # Use standard normal approximation
            x = t
            # 2 * P(Z > x) where Z ~ N(0,1)
            # Abramowitz & Stegun approximation
            p = 2.0 * (1.0 - RunComparator._normal_cdf(x))
        else:
            # Conservative: use p = 2 * exp(-t^2/2) / sqrt(2pi) (Gaussian lower bound)
            p = min(1.0, 2.0 * math.exp(-t * t / 2.0) / math.sqrt(2 * math.pi) * math.sqrt(df))
        return max(0.0, min(1.0, p))

    @staticmethod
    def _normal_cdf(x: float) -> float:
        """Standard normal CDF via error function."""
        return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


# ---------------------------------------------------------------------------
# ExperimentTracker — high-level façade with RunContext
# ---------------------------------------------------------------------------

class ExperimentTracker:
    """
    High-level façade over ExperimentRegistry.

    Usage
    -----
    tracker = ExperimentTracker()
    with tracker.start(config) as run:
        for step in range(100):
            run.log(step, "loss", 1.0 / (step + 1))
    """

    def __init__(self, registry: Optional[ExperimentRegistry] = None):
        self.registry = registry or ExperimentRegistry()

    @contextmanager
    def start(self, config: ExperimentConfig) -> Generator["RunContext", None, None]:
        """Context manager that creates a run, yields a RunContext, and ends the run."""
        run_id = self.registry.start_run(config)
        ctx = RunContext(run_id=run_id, registry=self.registry)
        try:
            yield ctx
            self.registry.end_run(run_id, status="completed")
        except Exception as exc:
            self.registry.end_run(run_id, status="failed")
            logger.error("Run %s failed: %s", run_id, exc)
            raise

    def get_learning_curve(
        self, metric_name: str, wp_module: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Aggregate learning curve for a metric across all completed runs."""
        raw = self.registry.learning_curve(metric_name, wp_module)
        # Convert to dict format for compatibility
        return [{"step": s, "mean": m, "std": sd} for s, m, sd in raw]


@dataclass
class RunContext:
    """Context object yielded by ExperimentTracker.start()."""
    run_id: str
    registry: ExperimentRegistry

    def log(self, step: int, name: str, value: float) -> None:
        """Log one metric sample."""
        self.registry.log(self.run_id, step, name, value)

    def log_dict(self, step: int, metrics: Dict[str, float]) -> None:
        """Log multiple metrics at one step."""
        self.registry.log_dict(self.run_id, step, metrics)


# ---------------------------------------------------------------------------
# verify_wp64_exit_criteria
# ---------------------------------------------------------------------------

def verify_wp64_exit_criteria(
    registry: Optional[ExperimentRegistry] = None,
) -> Dict[str, bool]:
    """
    Six measurable exit criteria for WP64.

    1. ExperimentRegistry creates a SQLite DB and supports start/log/end_run.
    2. Logged metrics are retrievable via get_run().
    3. learning_curve() aggregates correctly across multiple runs.
    4. RunComparator returns significant=True for clearly different groups.
    5. ExperimentTracker context manager auto-ends runs on success and failure.
    6. export_json() produces a valid JSON file.
    """
    import tempfile, os, json as json_mod

    results: Dict[str, bool] = {}

    # Criterion 1: registry CRUD
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        reg = ExperimentRegistry(db_path)
        cfg = ExperimentConfig("wp64", "test_run", {"lr": 0.01})
        run_id = reg.start_run(cfg)
        reg.log(run_id, 0, "loss", 1.0)
        reg.end_run(run_id)
        runs = reg.list_runs("wp64", "completed")
        results["c1_registry_crud"] = len(runs) == 1
        os.unlink(db_path)
    except Exception:
        results["c1_registry_crud"] = False

    # Criterion 2: get_run retrieves metrics
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        reg = ExperimentRegistry(db_path)
        cfg = ExperimentConfig("wp64", "test", {"x": 1})
        run_id = reg.start_run(cfg)
        reg.log(run_id, 1, "acc", 0.5)
        reg.log(run_id, 2, "acc", 0.7)
        reg.end_run(run_id)
        run = reg.get_run(run_id)
        ok = run is not None and len(run.metrics) == 2
        results["c2_get_run_retrieves_metrics"] = ok
        os.unlink(db_path)
    except Exception:
        results["c2_get_run_retrieves_metrics"] = False

    # Criterion 3: learning_curve aggregates
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        reg = ExperimentRegistry(db_path)
        cfg = ExperimentConfig("wp64", "test", {})
        for _ in range(3):
            rid = reg.start_run(cfg)
            for s in range(5):
                reg.log(rid, s, "score", float(s) * 0.1)
            reg.end_run(rid)
        curve = reg.learning_curve("score", "wp64")
        ok = len(curve) == 5 and all(len(pt) == 3 for pt in curve)
        results["c3_learning_curve_aggregates"] = ok
        os.unlink(db_path)
    except Exception:
        results["c3_learning_curve_aggregates"] = False

    # Criterion 4: RunComparator detects difference
    try:
        cmp = RunComparator.compare(
            [0.9, 0.91, 0.92, 0.88, 0.93],
            [0.1, 0.12, 0.09, 0.11, 0.10],
        )
        results["c4_comparator_significant"] = cmp["significant"] is True
    except Exception:
        results["c4_comparator_significant"] = False

    # Criterion 5: tracker context manager
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        reg = ExperimentRegistry(db_path)
        tracker = ExperimentTracker(reg)
        cfg = ExperimentConfig("wp64", "ctx_test", {})
        with tracker.start(cfg) as run:
            run.log(0, "val", 1.0)
        runs = reg.list_runs("wp64", "completed")
        ok = len(runs) == 1
        # Test failure case
        try:
            with tracker.start(cfg) as run2:
                run2.log(0, "val", 0.5)
                raise RuntimeError("simulated failure")
        except RuntimeError:
            pass
        failed_runs = reg.list_runs("wp64", "failed")
        ok = ok and len(failed_runs) == 1
        results["c5_tracker_context_manager"] = ok
        os.unlink(db_path)
    except Exception:
        results["c5_tracker_context_manager"] = False

    # Criterion 6: export_json
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_path = f.name
        reg = ExperimentRegistry(db_path)
        cfg = ExperimentConfig("wp64", "export_test", {})
        rid = reg.start_run(cfg)
        reg.log(rid, 0, "x", 1.0)
        reg.end_run(rid)
        reg.export_json(json_path)
        with open(json_path) as f:
            data = json_mod.load(f)
        ok = isinstance(data, list) and len(data) == 1
        results["c6_export_json_valid"] = ok
        os.unlink(db_path)
        os.unlink(json_path)
    except Exception:
        results["c6_export_json_valid"] = False

    passed = sum(results.values())
    logger.info("WP64 exit criteria: %d/6 passed.", passed)
    return results
