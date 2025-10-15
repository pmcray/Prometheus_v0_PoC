#!/usr/bin/env python3
"""
Phi-3-mini Full Benchmark: 30 USACO Bronze Problems
Expected: 15-20/30 (50-67%)
"""

import os
import sys
import time
import json
from datetime import datetime

# Set environment for Phi-3
os.environ['PATH'] = f"/home/pmc/llama.cpp/build/bin:{os.environ.get('PATH', '')}"

from ioi_synthesizer_simple import SimpleIOICodeSynthesizer, SimpleProblemClassifier
from usaco_bronze_problems import ALL_PROBLEMS
from ioi_tester import IOITester

def benchmark_phi3():
    """Run full 30-problem benchmark on Phi-3-mini"""
    print("="*80)
    print("🧪 PHI-3-MINI FULL BENCHMARK: 30 USACO Bronze Problems")
    print("="*80)

    model_path = "/home/pmc/ioi_models/Phi-3-mini-4k-instruct-q4.gguf"
    print(f"\nModel: Phi-3-mini-4k-instruct (3.8B)")
    print(f"Path: {model_path}")
    print(f"Size: {os.path.getsize(model_path) / 1024**3:.1f}GB")
    print(f"Problems: 30 (USACO Bronze difficulty)")
    print(f"Target: 15-20/30 (50-67%)")
    print(f"Estimated time: 30-40 minutes\n")

    # Initialize
    synthesizer = SimpleIOICodeSynthesizer(model_path)
    classifier = SimpleProblemClassifier()
    tester = IOITester()

    # Results tracking
    results = {
        'model': 'Phi-3-mini-4k-instruct-q4',
        'total_problems': 30,
        'timestamp': datetime.utcnow().isoformat(),
        'problems': []
    }

    solved = 0
    total_time = 0
    by_difficulty = {'Easy': {'solved': 0, 'total': 0},
                     'Medium': {'solved': 0, 'total': 0},
                     'Medium-Hard': {'solved': 0, 'total': 0},
                     'Hard': {'solved': 0, 'total': 0}}

    print("Starting benchmark...")
    print("-"*80)

    for i, problem in enumerate(ALL_PROBLEMS, 1):
        print(f"\n[{i}/30] {problem['name']} ({problem['difficulty']})")

        problem_result = {
            'id': i,
            'name': problem['name'],
            'difficulty': problem['difficulty'],
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

            # Synthesize
            code = synthesizer.synthesize(
                problem['text'],
                problem['examples'],
                classification['algorithms']
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
            else:
                if result.get('failures'):
                    error = result['failures'][0].get('error', 'Output mismatch')
                    print(f"  ⚠️  Error: {error[:70]}")
                    problem_result['error'] = error[:200]

            by_difficulty[problem['difficulty']]['total'] += 1

        except Exception as e:
            error_msg = str(e)
            print(f"  ❌ ERROR: {error_msg[:70]}")
            problem_result['error'] = error_msg[:200]
            by_difficulty[problem['difficulty']]['total'] += 1

        results['problems'].append(problem_result)

        # Progress update every 5 problems
        if i % 5 == 0:
            print(f"\n  📊 Progress: {solved}/{i} solved ({solved/i*100:.1f}%)")
            print(f"  ⏱️  Time: {total_time:.1f}s ({total_time/i:.1f}s/problem)")

    # Final results
    print(f"\n{'='*80}")
    print(f"📊 FINAL RESULTS")
    print(f"{'='*80}")
    print(f"\n✅ Problems Solved: {solved}/30 ({solved/30*100:.1f}%)")
    print(f"⏱️  Total Time: {total_time:.1f}s ({total_time/30:.1f}s/problem)")

    print(f"\n📈 By Difficulty:")
    for difficulty in ['Easy', 'Medium', 'Medium-Hard', 'Hard']:
        stats = by_difficulty[difficulty]
        if stats['total'] > 0:
            pct = stats['solved']/stats['total']*100
            print(f"  {difficulty:12s}: {stats['solved']}/{stats['total']} ({pct:.1f}%)")

    # Comparison
    print(f"\n📊 Comparison to Baselines:")
    print(f"  Mock mode:       12/30 (40%)")
    print(f"  DeepSeek-1.3B:   10/30 (33%)")
    print(f"  Phi-3-mini-3.8B: {solved}/30 ({solved/30*100:.1f}%)")

    # Success assessment
    print(f"\n{'='*80}")
    if solved >= 20:
        print(f"🎉 EXCELLENT: Exceeded target! ({solved}/30 = {solved/30*100:.1f}%)")
        status = "excellent"
    elif solved >= 15:
        print(f"✅ SUCCESS: Met target range (15-20/30)")
        status = "success"
    elif solved >= 12:
        print(f"⚠️  GOOD: Above mock baseline but below target")
        status = "good"
    else:
        print(f"❌ BELOW EXPECTATIONS: Need to improve prompts/model")
        status = "below_target"
    print(f"{'='*80}")

    # Save results
    results['solved'] = solved
    results['total_time_seconds'] = total_time
    results['avg_time_seconds'] = total_time / 30
    results['success_rate'] = solved / 30
    results['status'] = status
    results['by_difficulty'] = by_difficulty

    output_file = "phi3_benchmark_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")

    # Detailed failure analysis
    failures = [p for p in results['problems'] if not p['success']]
    if failures:
        print(f"\n{'='*80}")
        print(f"❌ FAILED PROBLEMS ({len(failures)}/30):")
        print(f"{'='*80}")
        for i, fail in enumerate(failures[:10], 1):  # Show first 10
            print(f"\n{i}. {fail['name']} ({fail['difficulty']})")
            if fail.get('error'):
                print(f"   Error: {fail['error'][:100]}")
            print(f"   Tests: {fail['test_passed']}/{fail['test_total']}")
        if len(failures) > 10:
            print(f"\n... and {len(failures) - 10} more failures")

    return solved >= 15  # Success if meets minimum target

if __name__ == "__main__":
    print(f"\n🚀 Starting Phi-3 benchmark at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    success = benchmark_phi3()
    print(f"\n✅ Benchmark complete at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    sys.exit(0 if success else 1)
