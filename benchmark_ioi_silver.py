#!/usr/bin/env python3
"""
Phi-3-mini IOI Silver Benchmark: 20 USACO Silver Problems

Expected Performance: 30-50% (6-10/20)

Topics:
- Sorting & Comparators
- Prefix Sums
- Two Pointers
- Greedy Algorithms
- Binary Search
"""

import os
import sys
import time
import json
from datetime import datetime

# Set environment for Phi-3
os.environ['PATH'] = f"/home/pmc/llama.cpp/build/bin:{os.environ.get('PATH', '')}"

from ioi_synthesizer_simple import SimpleIOICodeSynthesizer, SimpleProblemClassifier
from usaco_silver_problems import SILVER_PROBLEMS
from ioi_tester import IOITester

def benchmark_silver():
    """Run 20-problem Silver benchmark on Phi-3-mini"""
    print("="*80)
    print("🥈 PHI-3-MINI SILVER BENCHMARK: 20 USACO Silver Problems")
    print("="*80)

    model_path = "/home/pmc/ioi_models/Phi-3-mini-4k-instruct-q4.gguf"
    print(f"\nModel: Phi-3-mini-4k-instruct (3.8B)")
    print(f"Path: {model_path}")
    print(f"Size: {os.path.getsize(model_path) / 1024**3:.1f}GB")
    print(f"Problems: 20 (USACO Silver difficulty)")
    print(f"Target: 6-10/20 (30-50%)")
    print(f"Bronze baseline: 19/30 (63.3%)")
    print(f"Estimated time: 40-60 minutes\n")

    # Initialize
    synthesizer = SimpleIOICodeSynthesizer(model_path)
    classifier = SimpleProblemClassifier()
    tester = IOITester()

    # Results tracking
    results = {
        'model': 'Phi-3-mini-4k-instruct-q4',
        'level': 'Silver',
        'total_problems': 20,
        'timestamp': datetime.utcnow().isoformat(),
        'problems': []
    }

    solved = 0
    total_time = 0
    by_difficulty = {
        'Easy-Silver': {'solved': 0, 'total': 0},
        'Medium-Silver': {'solved': 0, 'total': 0},
        'Hard-Silver': {'solved': 0, 'total': 0}
    }
    by_topic = {}

    print("Starting Silver benchmark...")
    print("-"*80)

    for i, problem in enumerate(SILVER_PROBLEMS, 1):
        print(f"\n[{i}/20] {problem['name']} ({problem['difficulty']}, {problem['topic']})")

        problem_result = {
            'id': problem['id'],
            'name': problem['name'],
            'difficulty': problem['difficulty'],
            'topic': problem['topic'],
            'success': False,
            'time_seconds': 0,
            'code_length': 0,
            'test_passed': 0,
            'test_total': 0,
            'error': None
        }

        try:
            start_time = time.time()

            # Classify
            classification = classifier.classify(problem['text'])

            # Synthesize with Silver-specific prompt
            code = synthesizer.synthesize(
                problem['text'],
                problem['examples'],
                classification['algorithms'],
                max_tokens=8192  # Longer for Silver complexity
            )

            synth_time = time.time() - start_time
            total_time += synth_time
            problem_result['time_seconds'] = synth_time
            problem_result['code_length'] = len(code)

            print(f"  ⏱️  Generated in {synth_time:.1f}s")
            print(f"  📝 Code length: {len(code)} chars")

            # Test
            test_cases = [(ex['input'], ex['output']) for ex in problem['examples']]
            result = tester.test(code, test_cases, verbose=False)

            problem_result['test_passed'] = result['passed']
            problem_result['test_total'] = result['total']

            success = result['success_rate'] == 1.0
            problem_result['success'] = success

            status = "✅" if success else "❌"
            print(f"  {status} Tests: {result['passed']}/{result['total']} ({result['success_rate']*100:.0f}%)")

            if success:
                solved += 1
                by_difficulty[problem['difficulty']]['solved'] += 1
                by_topic[problem['topic']] = by_topic.get(problem['topic'], {'solved': 0, 'total': 0})
                by_topic[problem['topic']]['solved'] += 1
            else:
                if result.get('failures'):
                    error = result['failures'][0].get('error', 'Output mismatch')
                    print(f"  ⚠️  Error: {error[:70]}")
                    problem_result['error'] = error[:200]

            by_difficulty[problem['difficulty']]['total'] += 1
            by_topic.setdefault(problem['topic'], {'solved': 0, 'total': 0})['total'] += 1

        except Exception as e:
            error_msg = str(e)
            print(f"  ❌ ERROR: {error_msg[:70]}")
            problem_result['error'] = error_msg[:200]
            by_difficulty[problem['difficulty']]['total'] += 1
            by_topic.setdefault(problem['topic'], {'solved': 0, 'total': 0})['total'] += 1

        results['problems'].append(problem_result)

        # Progress update every 5 problems
        if i % 5 == 0:
            print(f"\n  📊 Progress: {solved}/{i} solved ({solved/i*100:.1f}%)")
            print(f"  ⏱️  Time: {total_time:.1f}s ({total_time/i:.1f}s/problem)")

    # Final results
    print(f"\n{'='*80}")
    print(f"📊 FINAL RESULTS - IOI SILVER")
    print(f"{'='*80}")
    print(f"\n✅ Problems Solved: {solved}/20 ({solved/20*100:.1f}%)")
    print(f"⏱️  Total Time: {total_time:.1f}s ({total_time/20:.1f}s/problem)")

    print(f"\n📈 By Difficulty:")
    for difficulty in ['Easy-Silver', 'Medium-Silver', 'Hard-Silver']:
        stats = by_difficulty[difficulty]
        if stats['total'] > 0:
            pct = stats['solved']/stats['total']*100
            print(f"  {difficulty:15s}: {stats['solved']}/{stats['total']} ({pct:.1f}%)")

    print(f"\n📈 By Topic:")
    for topic in sorted(by_topic.keys()):
        stats = by_topic[topic]
        if stats['total'] > 0:
            pct = stats['solved']/stats['total']*100
            print(f"  {topic:25s}: {stats['solved']}/{stats['total']} ({pct:.1f}%)")

    # Comparison to Bronze
    print(f"\n📊 Comparison:")
    print(f"  Bronze (baseline):  19/30 (63.3%)")
    print(f"  Silver (this run):  {solved}/20 ({solved/20*100:.1f}%)")

    if solved >= 10:
        silver_ratio = solved / 20
        bronze_ratio = 19 / 30
        print(f"  Silver/Bronze ratio: {silver_ratio/bronze_ratio:.2f}x")
    else:
        print(f"  Silver is harder as expected!")

    # Success assessment
    print(f"\n{'='*80}")
    if solved >= 10:
        print(f"🎉 EXCELLENT: Exceeded target! ({solved}/20 = {solved/20*100:.1f}%)")
        status = "excellent"
    elif solved >= 8:
        print(f"✅ GOOD SUCCESS: Within target range (8-10/20)")
        status = "good_success"
    elif solved >= 6:
        print(f"✅ MINIMUM SUCCESS: Met minimum target (6-10/20)")
        status = "minimum_success"
    elif solved >= 4:
        print(f"⚠️  BELOW TARGET: Need prompt improvements")
        status = "below_target"
    else:
        print(f"❌ WELL BELOW TARGET: Silver may be too hard for 3.8B model")
        status = "too_difficult"
    print(f"{'='*80}")

    # Save results
    results['solved'] = solved
    results['total_time_seconds'] = total_time
    results['avg_time_seconds'] = total_time / 20
    results['success_rate'] = solved / 20
    results['status'] = status
    results['by_difficulty'] = by_difficulty
    results['by_topic'] = by_topic

    output_file = "ioi_silver_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")

    # Detailed failure analysis
    failures = [p for p in results['problems'] if not p['success']]
    if failures:
        print(f"\n{'='*80}")
        print(f"❌ FAILED PROBLEMS ({len(failures)}/20):")
        print(f"{'='*80}")

        # Group by difficulty
        for difficulty in ['Easy-Silver', 'Medium-Silver', 'Hard-Silver']:
            diff_failures = [f for f in failures if f['difficulty'] == difficulty]
            if diff_failures:
                print(f"\n{difficulty}:")
                for i, fail in enumerate(diff_failures[:5], 1):
                    print(f"  {i}. {fail['name']} ({fail['topic']})")
                    if fail.get('error'):
                        print(f"     Error: {fail['error'][:80]}")
                    print(f"     Tests: {fail['test_passed']}/{fail['test_total']}")

    # Insights
    print(f"\n{'='*80}")
    print(f"💡 INSIGHTS")
    print(f"{'='*80}")

    if solved >= 6:
        print(f"✅ Phi-3 (3.8B) can handle Silver-level problems")
        print(f"✅ Performance scales from Bronze to Silver")
        print(f"✅ Ready for Gold-level benchmark")
    else:
        print(f"⚠️  Silver significantly harder than Bronze")
        print(f"⚠️  May need larger model (7B+) for consistent Silver performance")
        print(f"⚠️  Consider prompt engineering improvements")

    return solved >= 6  # Success if meets minimum target

if __name__ == "__main__":
    print(f"\n🚀 Starting Silver benchmark at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    success = benchmark_silver()
    print(f"\n✅ Benchmark complete at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    sys.exit(0 if success else 1)
