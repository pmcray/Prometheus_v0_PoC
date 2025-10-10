#!/usr/bin/env python3
"""
Benchmark IOI Bronze System on USACO Problems

Tests the complete IOI Bronze system on a set of USACO Bronze-level problems.
"""

import os
import json
from pathlib import Path
from prometheus_ioi_bronze import PrometheusIOIBronze
from usaco_bronze_problems import ALL_PROBLEMS, get_easy_problems, get_medium_problems, get_hard_problems


def run_benchmark(problems, system, verbose=True):
    """
    Run benchmark on a set of problems.

    Args:
        problems: List of problem dicts
        system: PrometheusIOIBronze instance
        verbose: Print detailed results

    Returns:
        Dict with results
    """
    results = []

    for i, problem in enumerate(problems, 1):
        if verbose:
            print(f"\n{'='*70}")
            print(f"PROBLEM {i}/{len(problems)}: {problem['name']} ({problem['difficulty']})")
            print(f"{'='*70}")

        try:
            result = system.solve_problem(
                problem['text'],
                problem['examples'],
                problem.get('constraints'),
                verbose=verbose
            )

            result['problem_name'] = problem['name']
            result['difficulty'] = problem['difficulty']
            result['expected_algorithms'] = problem.get('solution_algorithms', [])

            results.append(result)

            if verbose:
                if result['solved']:
                    print(f"✅ {problem['name']}: SOLVED")
                else:
                    print(f"❌ {problem['name']}: FAILED")
                    print(f"   Best success rate: {result['test_results'].get('success_rate', 0)*100:.1f}%")

        except Exception as e:
            print(f"❌ {problem['name']}: ERROR - {e}")
            results.append({
                'problem_name': problem['name'],
                'difficulty': problem['difficulty'],
                'solved': False,
                'error': str(e)
            })

    # Compute statistics
    solved_count = sum(1 for r in results if r.get('solved', False))
    total_count = len(results)
    success_rate = solved_count / total_count if total_count > 0 else 0.0

    # By difficulty
    easy_solved = sum(1 for r in results if r.get('solved', False) and r.get('difficulty') == 'Easy')
    easy_total = sum(1 for r in results if r.get('difficulty') == 'Easy')

    medium_solved = sum(1 for r in results if r.get('solved', False) and 'Medium' in r.get('difficulty', ''))
    medium_total = sum(1 for r in results if 'Medium' in r.get('difficulty', ''))

    hard_solved = sum(1 for r in results if r.get('solved', False) and r.get('difficulty') == 'Hard')
    hard_total = sum(1 for r in results if r.get('difficulty') == 'Hard')

    summary = {
        'total_problems': total_count,
        'solved': solved_count,
        'success_rate': success_rate,
        'by_difficulty': {
            'easy': {'solved': easy_solved, 'total': easy_total},
            'medium': {'solved': medium_solved, 'total': medium_total},
            'hard': {'solved': hard_solved, 'total': hard_total}
        },
        'results': results
    }

    return summary


def print_summary(summary):
    """Print benchmark summary"""
    print(f"\n{'='*70}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*70}")

    print(f"\nOverall:")
    print(f"  Solved: {summary['solved']}/{summary['total_problems']} ({summary['success_rate']*100:.1f}%)")

    print(f"\nBy Difficulty:")
    for diff, stats in summary['by_difficulty'].items():
        if stats['total'] > 0:
            pct = (stats['solved'] / stats['total']) * 100
            print(f"  {diff.title()}: {stats['solved']}/{stats['total']} ({pct:.1f}%)")

    print(f"\nProblem Results:")
    for i, result in enumerate(summary['results'], 1):
        status = "✅" if result.get('solved', False) else "❌"
        name = result.get('problem_name', 'Unknown')
        diff = result.get('difficulty', 'Unknown')
        time = result.get('time_seconds', 0)
        gen = result.get('generation', 0)

        print(f"  {i}. {status} {name} ({diff}) - {time:.1f}s, gen {gen}")

    print(f"\n{'='*70}")


if __name__ == "__main__":
    print("IOI Bronze Benchmark on USACO Problems")
    print("=" * 70)

    # Setup system
    local_model = os.environ.get('IOI_LOCAL_MODEL')
    api_key = os.environ.get('GOOGLE_API_KEY')

    if local_model and Path(local_model).exists():
        print(f"🔧 Using local model: {local_model}")
        system = PrometheusIOIBronze(
            local_model_path=local_model,
            use_local=True,
            population_size=30,
            max_generations=20,
            timeout_seconds=2.0
        )
        mode = "local"
    elif api_key:
        print("☁️  Using cloud model (Gemini)")
        system = PrometheusIOIBronze(
            api_key=api_key,
            population_size=30,
            max_generations=20,
            timeout_seconds=2.0
        )
        mode = "cloud"
    else:
        print("⚠️  Using mock mode (no LLM)")
        system = PrometheusIOIBronze(
            population_size=30,
            max_generations=20,
            timeout_seconds=2.0
        )
        mode = "mock"

    # Choose problem set
    import sys
    if len(sys.argv) > 1:
        difficulty = sys.argv[1].lower()
        if difficulty == 'easy':
            problems = get_easy_problems()
            print(f"\n📝 Running EASY problems only ({len(problems)} problems)")
        elif difficulty == 'medium':
            problems = get_medium_problems()
            print(f"\n📝 Running MEDIUM problems only ({len(problems)} problems)")
        elif difficulty == 'hard':
            problems = get_hard_problems()
            print(f"\n📝 Running HARD problems only ({len(problems)} problems)")
        elif difficulty == 'all':
            problems = ALL_PROBLEMS
            print(f"\n📝 Running ALL problems ({len(problems)} problems)")
        else:
            print(f"Unknown difficulty: {difficulty}")
            print("Usage: python benchmark_ioi_bronze.py [easy|medium|hard|all]")
            sys.exit(1)
    else:
        # Default: run easy problems first
        problems = get_easy_problems()
        print(f"\n📝 Running EASY problems by default ({len(problems)} problems)")
        print("   Use: python benchmark_ioi_bronze.py [easy|medium|hard|all]")

    # Run benchmark
    summary = run_benchmark(problems, system, verbose=True)

    # Print summary
    print_summary(summary)

    # Save results
    results_file = f"ioi_bronze_benchmark_{mode}_{len(problems)}problems.json"
    with open(results_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n💾 Results saved to: {results_file}")

    # Check target
    target_rate = 0.40  # 40% target for Bronze
    if summary['success_rate'] >= target_rate:
        print(f"\n🎯 TARGET ACHIEVED! {summary['success_rate']*100:.1f}% ≥ {target_rate*100:.0f}%")
    else:
        gap = (target_rate - summary['success_rate']) * 100
        print(f"\n📈 Progress: {summary['success_rate']*100:.1f}% (need +{gap:.1f}% to reach {target_rate*100:.0f}% target)")
