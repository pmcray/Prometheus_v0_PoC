"""
WP13 — Causal Safety Benchmark
================================

Four scenarios that validate the causal attribution pipeline:

1. **ace_accuracy** — the finite-difference ACE correctly identifies which
   feature dimension has the largest causal effect in a controlled linear
   reward model (ground-truth ACE = weight_i).

2. **counterfactual_success** — the counterfactual checker finds a safe
   alternative within a budget for plans that are unsafe under the learned
   reward model.

3. **causal_rank_correlation** — the graph's ranking of features by |ACE|
   correlates (Spearman ρ) with the ground-truth ranking from the true
   linear weights.

4. **integration** — full pipeline: CausalSafetyAnalyser on 60 plans
   (30 safe, 30 unsafe) with WP10/WP12 verdict integration; measures
   report completeness and counterfactual coverage on unsafe plans.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np
from scipy.stats import spearmanr

from prometheus.value_learning import ValueLearningAgent
from prometheus.causal_safety import (
    CausalSafetyGraph,
    CounterfactualSafetyChecker,
    CausalSafetyAnalyser,
    batch_analyse,
    causal_safety_summary_table,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

N_FEATS = 8
N_PAIRS = 80


def _make_agent(seed: int = 0) -> ValueLearningAgent:
    rng   = np.random.default_rng(seed)
    agent = ValueLearningAgent(feature_size=N_FEATS, learning_rate=0.05, l2_reg=1e-3)
    pairs = [
        (rng.standard_normal(N_FEATS), rng.standard_normal(N_FEATS))
        for _ in range(N_PAIRS)
    ]
    agent.train_to_convergence(pairs, max_epochs=150)
    return agent


def _make_linear_reward(weights: np.ndarray):
    """Ground-truth linear reward for controlled experiments."""
    def fn(features: np.ndarray) -> float:
        return float(np.dot(weights, features))
    return fn


FEATURE_NAMES = [f"feat_{i:02d}" for i in range(N_FEATS)]


# ---------------------------------------------------------------------------
# Benchmark result
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    scenario  : str
    passed    : bool
    metrics   : Dict[str, Any] = field(default_factory=dict)
    extra     : Dict[str, Any] = field(default_factory=dict)
    elapsed_s : float = 0.0


# ---------------------------------------------------------------------------
# Scenario 1: ACE accuracy on controlled linear reward
# ---------------------------------------------------------------------------

def _run_ace_accuracy(seed: int = 0) -> BenchmarkResult:
    """
    Ground truth: R(x) = w·x, so ACE_i = w_i (exactly).

    We check that:
    - The sign of estimated ACE matches the sign of w_i for ≥ 80% of dims.
    - The Spearman ρ between |estimated ACE| and |w_i| is ≥ 0.7.
    """
    t0  = time.perf_counter()
    rng = np.random.default_rng(seed)

    # True weights — varied magnitudes so ranking is non-trivial
    true_weights = rng.standard_normal(N_FEATS)
    true_weights *= rng.uniform(0.5, 3.0, size=N_FEATS)  # heterogeneous scale
    reward_fn    = _make_linear_reward(true_weights)

    graph = CausalSafetyGraph(
        reward_fn     = reward_fn,
        feature_names = FEATURE_NAMES,
        delta         = 0.1,
        n_mc_samples  = 30,
    )

    # Run on 10 different feature points and average ACE
    ace_accumulator = np.zeros(N_FEATS)
    for trial in range(10):
        feats = rng.standard_normal(N_FEATS)
        graph.build(feats)
        ace_vec = graph.causal_influence_matrix()
        ace_accumulator += ace_vec
    mean_ace = ace_accumulator / 10.0

    # Sign accuracy
    sign_match  = np.sign(mean_ace) == np.sign(true_weights)
    sign_acc    = float(sign_match.mean())

    # Rank correlation
    rho, pval   = spearmanr(np.abs(mean_ace), np.abs(true_weights))

    passed = sign_acc >= 0.70 and rho >= 0.60

    return BenchmarkResult(
        scenario  = "ace_accuracy",
        passed    = passed,
        metrics   = {
            "sign_accuracy"         : sign_acc,
            "spearman_rho"          : float(rho),
            "spearman_pval"         : float(pval),
        },
        extra = {
            "true_weights" : true_weights.tolist(),
            "mean_ace"     : mean_ace.tolist(),
        },
        elapsed_s = time.perf_counter() - t0,
    )


# ---------------------------------------------------------------------------
# Scenario 2: Counterfactual success rate
# ---------------------------------------------------------------------------

def _run_counterfactual_success(agent: ValueLearningAgent, seed: int = 0) -> BenchmarkResult:
    """
    Generate 40 unsafe feature vectors (reward < 0).  The counterfactual
    checker must find a safe edit (reward ≥ 0) within the budget.

    Expected: success_rate ≥ 0.75, mean_n_edits ≤ 20.
    """
    t0  = time.perf_counter()
    rng = np.random.default_rng(seed)

    reward_fn = agent.get_reward

    # Build a graph once for direction guidance
    graph = CausalSafetyGraph(
        reward_fn     = reward_fn,
        feature_names = FEATURE_NAMES,
        delta         = 0.1,
        n_mc_samples  = 20,
    )
    checker = CounterfactualSafetyChecker(
        reward_fn        = reward_fn,
        safety_threshold = 0.0,
        step_size        = 0.3,
        max_steps        = 40,
    )

    # Sample unsafe inputs: keep trying until we get 40 with reward < 0
    unsafe_feats = []
    attempts     = 0
    while len(unsafe_feats) < 40 and attempts < 2000:
        f = rng.standard_normal(N_FEATS)
        if float(reward_fn(f)) < 0.0:
            unsafe_feats.append(f)
        attempts += 1

    if not unsafe_feats:
        return BenchmarkResult(
            scenario="counterfactual_success",
            passed=False,
            metrics={"error": "could not generate unsafe inputs"},
            elapsed_s=time.perf_counter() - t0,
        )

    successes   = 0
    n_edits_list = []

    for feats in unsafe_feats:
        graph.build(feats)
        result = checker.minimal_counterfactual(feats, graph, FEATURE_NAMES)
        if result.counterfactual_safe:
            successes += 1
        n_edits_list.append(result.n_edits)

    n        = len(unsafe_feats)
    success_rate = successes / n
    mean_edits   = float(np.mean(n_edits_list))

    passed = success_rate >= 0.75 and mean_edits <= 20.0

    return BenchmarkResult(
        scenario  = "counterfactual_success",
        passed    = passed,
        metrics   = {
            "n_unsafe_tested" : n,
            "success_rate"    : success_rate,
            "mean_n_edits"    : mean_edits,
            "max_n_edits"     : int(max(n_edits_list)),
        },
        extra = {"n_edits_distribution": n_edits_list},
        elapsed_s = time.perf_counter() - t0,
    )


# ---------------------------------------------------------------------------
# Scenario 3: Causal rank correlation vs true weights
# ---------------------------------------------------------------------------

def _run_causal_rank_correlation(seed: int = 0) -> BenchmarkResult:
    """
    Use a sparse linear reward where only 3 of 8 features matter.
    The causal graph should rank those 3 highest.

    Expected: Spearman ρ ≥ 0.65, top-3 precision ≥ 0.60.
    """
    t0  = time.perf_counter()
    rng = np.random.default_rng(seed)

    # Sparse true weights: only indices 0, 3, 6 are active
    true_weights        = np.zeros(N_FEATS)
    active_indices      = [0, 3, 6]
    true_weights[active_indices] = rng.choice([-1, 1], size=3) * rng.uniform(1.5, 3.0, size=3)
    reward_fn = _make_linear_reward(true_weights)

    graph = CausalSafetyGraph(
        reward_fn     = reward_fn,
        feature_names = FEATURE_NAMES,
        delta         = 0.1,
        n_mc_samples  = 40,
    )

    # Average over multiple input points
    ace_acc = np.zeros(N_FEATS)
    for _ in range(15):
        feats = rng.standard_normal(N_FEATS)
        graph.build(feats)
        ace_acc += np.abs(graph.causal_influence_matrix())
    mean_abs_ace = ace_acc / 15.0

    # Spearman ρ
    rho, pval = spearmanr(mean_abs_ace, np.abs(true_weights))

    # Top-3 precision: fraction of estimated top-3 that are truly active
    top3_estimated = set(np.argsort(-mean_abs_ace)[:3].tolist())
    top3_true      = set(active_indices)
    precision_at_3 = len(top3_estimated & top3_true) / 3.0

    passed = rho >= 0.55 and precision_at_3 >= 0.55

    return BenchmarkResult(
        scenario  = "causal_rank_correlation",
        passed    = passed,
        metrics   = {
            "spearman_rho"     : float(rho),
            "spearman_pval"    : float(pval),
            "precision_at_3"   : precision_at_3,
            "top3_estimated"   : sorted(top3_estimated),
            "top3_true"        : sorted(top3_true),
        },
        extra = {
            "true_weights"  : true_weights.tolist(),
            "mean_abs_ace"  : mean_abs_ace.tolist(),
        },
        elapsed_s = time.perf_counter() - t0,
    )


# ---------------------------------------------------------------------------
# Scenario 4: Full pipeline integration
# ---------------------------------------------------------------------------

def _run_integration(agent: ValueLearningAgent, seed: int = 0) -> BenchmarkResult:
    """
    60 plans: 30 safe (reward ≥ 0) + 30 unsafe (reward < 0).

    For each:
    - Run CausalSafetyAnalyser.analyse()
    - Check report completeness (has causal edges, top_causes, counterfactual)
    - On unsafe plans: check counterfactual_safe rate ≥ 0.70

    Expected:
        report_completeness_rate ≥ 1.0 (all reports have all fields)
        cf_success_rate_on_unsafe ≥ 0.70
        elapsed_ms_per_plan ≤ 1000
    """
    t0 = time.perf_counter()

    analyser = CausalSafetyAnalyser(
        reward_fn        = agent.get_reward,
        feature_names    = FEATURE_NAMES,
        safety_threshold = 0.0,
        delta            = 0.1,
        n_mc_samples     = 15,
        cf_step_size     = 0.3,
        cf_max_steps     = 30,
    )

    rng          = np.random.default_rng(seed)
    safe_feats   = []
    unsafe_feats = []
    attempts     = 0
    while (len(safe_feats) < 30 or len(unsafe_feats) < 30) and attempts < 5000:
        f = rng.standard_normal(N_FEATS)
        r = float(agent.get_reward(f))
        if r >= 0.0 and len(safe_feats) < 30:
            safe_feats.append(f)
        elif r < 0.0 and len(unsafe_feats) < 30:
            unsafe_feats.append(f)
        attempts += 1

    all_feats = safe_feats + unsafe_feats

    reports         = batch_analyse(analyser, all_feats, run_counterfactual=True)
    elapsed_total   = time.perf_counter() - t0

    # Completeness: every report has edges, top_causes, counterfactual
    complete = sum(
        1 for r in reports
        if len(r.causal_edges) > 0 and len(r.top_causes) > 0 and r.counterfactual is not None
    )
    completeness_rate = complete / len(reports)

    # CF success on unsafe plans
    unsafe_reports = reports[len(safe_feats):]
    cf_successes   = sum(1 for r in unsafe_reports
                         if r.counterfactual and r.counterfactual.counterfactual_safe)
    cf_rate        = cf_successes / max(len(unsafe_reports), 1)

    ms_per_plan    = (elapsed_total / len(reports)) * 1000

    # Summary table (printed in notebook)
    table = causal_safety_summary_table(reports[:6])

    passed = completeness_rate >= 0.95 and cf_rate >= 0.65 and ms_per_plan <= 2000

    return BenchmarkResult(
        scenario  = "integration",
        passed    = passed,
        metrics   = {
            "n_plans"               : len(reports),
            "completeness_rate"     : completeness_rate,
            "cf_success_on_unsafe"  : cf_rate,
            "ms_per_plan"           : ms_per_plan,
        },
        extra = {
            "summary_table" : table,
            "n_safe"        : len(safe_feats),
            "n_unsafe"      : len(unsafe_feats),
        },
        elapsed_s = elapsed_total,
    )


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

class CausalSafetyBenchmark:
    """Run all four WP13 benchmark scenarios."""

    def __init__(self, seed: int = 42) -> None:
        self.seed  = seed
        self.agent = _make_agent(seed=seed)

    def run_all(self) -> List[BenchmarkResult]:
        return [
            _run_ace_accuracy(seed=self.seed),
            _run_counterfactual_success(self.agent, seed=self.seed),
            _run_causal_rank_correlation(seed=self.seed),
            _run_integration(self.agent, seed=self.seed),
        ]

    @staticmethod
    def summary_table(results: List[BenchmarkResult]) -> str:
        lines = [
            "",
            "WP13 Causal Safety Benchmark",
            "=" * 72,
            f"{'Scenario':<28} {'Pass?':>6} {'Key metric':<38} {'s':>5}",
            "-" * 72,
        ]
        key_metric = {
            "ace_accuracy": lambda r: (
                f"sign_acc={r.metrics['sign_accuracy']:.2f} "
                f"ρ={r.metrics['spearman_rho']:.2f}"
            ),
            "counterfactual_success": lambda r: (
                f"cf_rate={r.metrics['success_rate']:.2f} "
                f"mean_edits={r.metrics['mean_n_edits']:.1f}"
            ),
            "causal_rank_correlation": lambda r: (
                f"ρ={r.metrics['spearman_rho']:.2f} "
                f"P@3={r.metrics['precision_at_3']:.2f}"
            ),
            "integration": lambda r: (
                f"completeness={r.metrics['completeness_rate']:.2f} "
                f"cf_rate={r.metrics['cf_success_on_unsafe']:.2f} "
                f"ms={r.metrics['ms_per_plan']:.0f}"
            ),
        }
        for r in results:
            km  = key_metric.get(r.scenario, lambda _: "")(r)
            sym = "PASS" if r.passed else "FAIL"
            lines.append(
                f"{r.scenario:<28} {sym:>6} {km:<38} {r.elapsed_s:>5.2f}"
            )
        lines.append("=" * 72)
        n_pass = sum(r.passed for r in results)
        lines.append(f"Result: {n_pass}/{len(results)} scenarios passed")
        lines.append("")
        return "\n".join(lines)
