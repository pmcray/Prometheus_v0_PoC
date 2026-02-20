"""
PrometheusStar OpenRA Curriculum Runner — Prometheus v0.97

Applies the PrometheusStar evolutionary self-improvement loop to the OpenRA
Real-Time Strategy benchmark.  The runner:

  1. Prints the four-stage curriculum overview.
  2. For each stage:
       a. Evolves a population of OpenRAStrategyAgents over N generations.
       b. Evaluates the best agent against the stage's AI difficulty.
       c. Advances to the next stage if the target win rate is met.
  3. Plots learning curves (win rate vs. generation) using matplotlib.
  4. Prints a final summary table.

The runner is intentionally self-contained: it does NOT require the full
Prometheus LLM stack, a real OpenRA installation, or GPU hardware.

Usage
-----
    python run_prometheusstar_openra.py [--stages N] [--population P]
                                        [--generations G] [--games-per-eval E]
                                        [--seed S] [--no-plot]
"""

import argparse
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from prometheus.openra_agent import OpenRAStrategyAgent
from benchmarks.openra_benchmark import (
    OPENRA_CURRICULUM,
    OpenRABenchmark,
    OpenRAOpponentConfig,
    estimate_openra_training_time,
    get_openra_opponent,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Curriculum stages
# ---------------------------------------------------------------------------

CURRICULUM: List[Dict] = [
    {
        "stage":       1,
        "name":        "Basic Controls",
        "difficulty":  "easy",
        "population":  6,
        "generations": 10,
        "games_per_eval": 4,
        "mutation_rate":  0.25,
        "target":      0.70,
    },
    {
        "stage":       2,
        "name":        "Resource Management",
        "difficulty":  "medium",
        "population":  8,
        "generations": 15,
        "games_per_eval": 4,
        "mutation_rate":  0.20,
        "target":      0.55,
    },
    {
        "stage":       3,
        "name":        "Tactical Response",
        "difficulty":  "hard",
        "population":  10,
        "generations": 20,
        "games_per_eval": 4,
        "mutation_rate":  0.15,
        "target":      0.40,
    },
    {
        "stage":       4,
        "name":        "Strategic Depth",
        "difficulty":  "expert",
        "population":  12,
        "generations": 25,
        "games_per_eval": 5,
        "mutation_rate":  0.12,
        "target":      0.25,
    },
]


# ---------------------------------------------------------------------------
# Evolutionary helpers
# ---------------------------------------------------------------------------

def _evaluate_population(
    population: List[OpenRAStrategyAgent],
    benchmark: OpenRABenchmark,
    games_per_eval: int,
) -> List[Tuple[float, OpenRAStrategyAgent]]:
    """
    Evaluate all agents and return (win_rate, agent) pairs sorted descending.
    """
    scored: List[Tuple[float, OpenRAStrategyAgent]] = []
    for agent in population:
        result = benchmark.evaluate_agent(agent, num_games=games_per_eval)
        win_rate = result["win_rate"]
        agent.record_result_batch(result)
        scored.append((win_rate, agent))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def _evolve_generation(
    scored: List[Tuple[float, OpenRAStrategyAgent]],
    population_size: int,
    mutation_rate: float,
    elite_frac: float = 0.3,
) -> List[OpenRAStrategyAgent]:
    """
    Create the next generation via elitism + crossover + mutation.

    Args:
        scored:          Sorted list of (win_rate, agent).
        population_size: Target size for the new generation.
        mutation_rate:   Per-parameter mutation probability.
        elite_frac:      Fraction of top agents carried over unchanged.

    Returns:
        New population of OpenRAStrategyAgent objects.
    """
    n_elite = max(1, int(population_size * elite_frac))
    elites = [agent for _, agent in scored[:n_elite]]

    new_pop: List[OpenRAStrategyAgent] = list(elites)

    while len(new_pop) < population_size:
        # Tournament selection: pick two parents from the top half
        top = scored[: max(2, len(scored) // 2)]
        p1 = np.random.choice([a for _, a in top])
        p2 = np.random.choice([a for _, a in top])
        child = p1.crossover(p2).mutate(mutation_rate=mutation_rate)
        new_pop.append(child)

    return new_pop[:population_size]


# ---------------------------------------------------------------------------
# Monkey-patch: add record_result_batch to OpenRAStrategyAgent
# ---------------------------------------------------------------------------

def _record_result_batch(self, result: Dict):
    """Record wins/losses/draws from a benchmark evaluation result."""
    self._wins   += result.get("wins",   0)
    self._losses += result.get("losses", 0)
    self._draws  += result.get("draws",  0)


OpenRAStrategyAgent.record_result_batch = _record_result_batch  # type: ignore


# ---------------------------------------------------------------------------
# Stage runner
# ---------------------------------------------------------------------------

def run_stage(
    stage_cfg: Dict,
    seed: Optional[int] = None,
    verbose: bool = True,
) -> Dict:
    """
    Run one curriculum stage: evolve agents and return results.

    Returns:
        Dict with:
          stage, name, difficulty, generations_run, best_win_rate,
          target_met, best_agent, generation_log, wall_clock_s
    """
    stage    = stage_cfg["stage"]
    name     = stage_cfg["name"]
    diff     = stage_cfg["difficulty"]
    pop_size = stage_cfg["population"]
    max_gen  = stage_cfg["generations"]
    gpe      = stage_cfg["games_per_eval"]
    mut_rate = stage_cfg["mutation_rate"]
    target   = stage_cfg["target"]

    if verbose:
        print(f"\n{'=' * 65}")
        print(f"Stage {stage}: {name}  [{diff.upper()}]")
        print(f"  Population={pop_size}  Generations={max_gen}  "
              f"Games/eval={gpe}  Target={target:.0%}")
        print("=" * 65)

    benchmark = OpenRABenchmark(difficulty=diff, seed=seed)

    # Initialise population
    rng_seed = seed if seed is not None else 42
    np.random.seed(rng_seed)

    population: List[OpenRAStrategyAgent] = [
        OpenRAStrategyAgent() for _ in range(pop_size)
    ]

    generation_log: List[Dict] = []
    best_win_rate  = 0.0
    best_agent     = population[0]
    t0             = time.time()

    for gen in range(max_gen):
        scored = _evaluate_population(population, benchmark, gpe)

        top_win   = scored[0][0]
        mean_win  = float(np.mean([s for s, _ in scored]))
        best_current = scored[0][1]

        if top_win > best_win_rate:
            best_win_rate = top_win
            best_agent    = best_current

        generation_log.append({
            "generation": gen + 1,
            "best_win_rate": top_win,
            "mean_win_rate": mean_win,
            "best_agent": repr(best_current),
        })

        if verbose:
            bar = "█" * int(top_win * 30)
            status = "✓" if top_win >= target else " "
            print(f"  Gen {gen + 1:3d}/{max_gen} [{status}]  "
                  f"best={top_win:.1%}  mean={mean_win:.1%}  {bar}")

        # Early stopping
        if top_win >= target:
            if verbose:
                print(f"\n  ✓ Target {target:.0%} met at generation {gen + 1}!")
            break

        population = _evolve_generation(scored, pop_size, mut_rate)

    wall_clock = time.time() - t0
    target_met = best_win_rate >= target

    if verbose:
        status = "PASSED" if target_met else "FAILED (did not meet target)"
        print(f"\n  Stage result: {status}")
        print(f"  Best win rate: {best_win_rate:.1%}  (target {target:.0%})")
        print(f"  Wall clock: {wall_clock:.1f}s")
        print(f"  Best agent: {best_agent}")

    return {
        "stage":           stage,
        "name":            name,
        "difficulty":      diff,
        "generations_run": len(generation_log),
        "best_win_rate":   best_win_rate,
        "target":          target,
        "target_met":      target_met,
        "best_agent":      best_agent,
        "generation_log":  generation_log,
        "wall_clock_s":    wall_clock,
    }


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------

def plot_learning_curves(stage_results: List[Dict]) -> None:
    """Plot win-rate learning curves for all completed stages."""
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except ImportError:
        logger.warning("matplotlib not installed — skipping plot. "
                       "Install with: pip install matplotlib")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    colours = ["royalblue", "darkorange", "green", "red"]
    gen_offset = 0

    for i, result in enumerate(stage_results):
        log = result["generation_log"]
        gens = [gen_offset + l["generation"] for l in log]
        best = [l["best_win_rate"] for l in log]
        mean = [l["mean_win_rate"] for l in log]
        target = result["target"]
        colour = colours[i % len(colours)]

        ax.plot(gens, best, color=colour, linewidth=2,
                label=f"Stage {result['stage']}: {result['name']} (best)")
        ax.plot(gens, mean, color=colour, linewidth=1,
                linestyle="--", alpha=0.6)
        ax.axhline(target, color=colour, linewidth=0.8,
                   linestyle=":", alpha=0.8,
                   label=f"Target {target:.0%}")

        gen_offset += len(log)

    ax.set_xlabel("Generation (cumulative)")
    ax.set_ylabel("Win Rate")
    ax.set_title("PrometheusStar OpenRA — Curriculum Learning Curves")
    ax.legend(loc="lower right", fontsize=8)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    out_path = "openra_learning_curves.png"
    plt.savefig(out_path, dpi=120)
    print(f"\nLearning curve saved to: {out_path}")
    plt.close()


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------

def print_summary(stage_results: List[Dict]) -> None:
    """Print a formatted summary table of all stage outcomes."""
    print("\n" + "=" * 65)
    print("PrometheusStar OpenRA — Final Summary")
    print("=" * 65)
    print(f"  {'Stage':<6} {'Name':<22} {'Best WR':>8} {'Target':>8} "
          f"{'Gens':>5} {'Status'}")
    print("  " + "-" * 60)
    stages_passed = 0
    for r in stage_results:
        status = "PASS" if r["target_met"] else "FAIL"
        if r["target_met"]:
            stages_passed += 1
        print(f"  {r['stage']:<6} {r['name']:<22} "
              f"{r['best_win_rate']:>7.1%}  "
              f"{r['target']:>7.0%}  "
              f"{r['generations_run']:>5}  {status}")

    total_time = sum(r["wall_clock_s"] for r in stage_results)
    print(f"\n  Stages passed: {stages_passed}/{len(stage_results)}")
    print(f"  Total wall clock: {total_time:.1f}s")

    if stage_results:
        best = max(stage_results, key=lambda r: r["best_win_rate"])
        print(f"\n  Overall best agent (Stage {best['stage']}):")
        print(f"    {best['best_agent']}")
    print("=" * 65)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(
    max_stages: int = len(CURRICULUM),
    population: Optional[int] = None,
    generations: Optional[int] = None,
    games_per_eval: Optional[int] = None,
    seed: Optional[int] = None,
    plot: bool = True,
    verbose: bool = True,
) -> List[Dict]:
    """
    Run the full PrometheusStar OpenRA curriculum.

    Args:
        max_stages:     Number of curriculum stages to attempt (1–4).
        population:     Override population size for all stages.
        generations:    Override generation count for all stages.
        games_per_eval: Override games-per-evaluation for all stages.
        seed:           Global RNG seed.
        plot:           Generate matplotlib learning curve.
        verbose:        Print per-generation progress.

    Returns:
        List of per-stage result dicts.
    """
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s:%(name)s: %(message)s",
    )

    if verbose:
        print("\n" + "=" * 65)
        print("PrometheusStar OpenRA — Curriculum Learning")
        print("=" * 65)
        print("\nCurriculum overview:")
        for i, cfg in enumerate(OPENRA_CURRICULUM[:max_stages]):
            print(f"  Stage {i + 1}: {cfg.name} [{cfg.difficulty}] "
                  f"— target {cfg.target_win_rate:.0%}")

        print("\nTraining time estimates:")
        for stage in CURRICULUM[:max_stages]:
            pop  = population or stage["population"]
            gens = generations or stage["generations"]
            gpe  = games_per_eval or stage["games_per_eval"]
            est  = estimate_openra_training_time(pop, gens, gpe)
            print(f"  Stage {stage['stage']}: ~{est['total_minutes']:.0f} min "
                  f"({est['total_games']} games)")

    stage_results: List[Dict] = []

    for stage_cfg in CURRICULUM[:max_stages]:
        # Apply overrides
        cfg = dict(stage_cfg)
        if population    is not None: cfg["population"]    = population
        if generations   is not None: cfg["generations"]   = generations
        if games_per_eval is not None: cfg["games_per_eval"] = games_per_eval

        result = run_stage(cfg, seed=seed, verbose=verbose)
        stage_results.append(result)

        if not result["target_met"] and verbose:
            print(f"\n  Stopping: Stage {cfg['stage']} target not met.")
            break

    if verbose:
        print_summary(stage_results)

    if plot:
        plot_learning_curves(stage_results)

    return stage_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PrometheusStar OpenRA Curriculum Runner"
    )
    parser.add_argument(
        "--stages", type=int, default=len(CURRICULUM),
        help="Number of curriculum stages to run (default: all 4)"
    )
    parser.add_argument(
        "--population", type=int, default=None,
        help="Override population size"
    )
    parser.add_argument(
        "--generations", type=int, default=None,
        help="Override generation count per stage"
    )
    parser.add_argument(
        "--games-per-eval", dest="games_per_eval", type=int, default=None,
        help="Override games per evaluation"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="RNG seed (default: 42)"
    )
    parser.add_argument(
        "--no-plot", dest="plot", action="store_false",
        help="Skip matplotlib learning curve generation"
    )
    args = parser.parse_args()

    main(
        max_stages=args.stages,
        population=args.population,
        generations=args.generations,
        games_per_eval=args.games_per_eval,
        seed=args.seed,
        plot=args.plot,
    )
