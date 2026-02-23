#!/usr/bin/env python3
"""
Comprehensive Local Model Test (v0.76)
Run this script when llama.cpp arch=87 build is complete
"""

import os
import sys
import time
from datetime import datetime

# Set environment
os.environ['PATH'] = f"/home/pmc/llama.cpp/build/bin:{os.environ.get('PATH', '')}"
os.environ['IOI_LOCAL_MODEL'] = "/home/pmc/ioi_models/deepseek-coder-1.3b-instruct.Q4_K_M.gguf"

from ioi_synthesizer_local import IOICodeSynthesizer, ProblemClassifier
from usaco_bronze_problems import PROBLEM_1, PROBLEM_2, PROBLEM_3, ALL_PROBLEMS
from ioi_tester import IOITester

def test_sanity():
    """Quick sanity test on 1 easy problem"""
    print("\n" + "="*70)
    print("🧪 SANITY TEST: Count Even Numbers")
    print("="*70)

    model_path = os.environ.get('IOI_LOCAL_MODEL')
    print(f"Model: {model_path}")
    print(f"Exists: {os.path.exists(model_path)}")

    try:
        # Initialize
        print("\n🔧 Initializing local synthesizer...")
        start_time = time.time()
        synthesizer = IOICodeSynthesizer(
            local_model_path=model_path,
            use_local=True
        )
        init_time = time.time() - start_time
        print(f"✅ Initialized in {init_time:.1f}s")
        print(f"Mode: {synthesizer.mode}")

        if synthesizer.mode != "local":
            print(f"❌ Expected local mode, got {synthesizer.mode}")
            return False

        # Classify
        print("\n📊 Classifying problem...")
        classifier = ProblemClassifier(
            local_model_path=model_path,
            use_local=True
        )

        problem = PROBLEM_1
        classification = classifier.classify(problem['text'], problem['examples'])
        print(f"Categories: {classification.get('categories', [])}")
        print(f"Algorithms: {classification.get('algorithms', [])[:3]}")

        # Synthesize
        print("\n💻 Synthesizing code...")
        start_time = time.time()
        code = synthesizer.synthesize(
            problem['text'],
            problem['examples'],
            classification.get('algorithms', ['use_array', 'count_if'])[:3],
            classification.get('constraints')
        )
        synth_time = time.time() - start_time

        print(f"✅ Synthesized in {synth_time:.1f}s")
        print("\nGenerated code:")
        print("-"*70)
        print(code[:300] + "..." if len(code) > 300 else code)
        print("-"*70)

        # Test
        print("\n🧪 Testing generated code...")
        tester = IOITester()
        test_cases = [(ex['input'], ex['output']) for ex in problem['examples']]
        result = tester.test(code, test_cases, verbose=False)

        print(f"\n📊 Results:")
        print(f"  Passed: {result['passed']}/{result['total']}")
        print(f"  Success Rate: {result['success_rate']*100:.1f}%")

        if result['success_rate'] == 1.0:
            print(f"\n✅ SANITY TEST PASSED!")
            return True
        else:
            print(f"\n⚠️  SANITY TEST PARTIAL: {result['passed']}/{result['total']}")
            if result.get('failures'):
                print(f"First failure: {result['failures'][0].get('error', 'Output mismatch')[:80]}")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_three_easy():
    """Test on 3 easy problems"""
    print("\n" + "="*70)
    print("🧪 3-PROBLEM TEST: Easy Problems")
    print("="*70)

    model_path = os.environ.get('IOI_LOCAL_MODEL')
    synthesizer = IOICodeSynthesizer(local_model_path=model_path, use_local=True)
    classifier = ProblemClassifier(local_model_path=model_path, use_local=True)
    tester = IOITester()

    problems = [PROBLEM_1, PROBLEM_2, PROBLEM_3]
    solved = 0

    for i, problem in enumerate(problems, 1):
        print(f"\n[{i}/3] {problem['name']}")

        try:
            # Classify
            classification = classifier.classify(problem['text'], problem['examples'])

            # Synthesize
            code = synthesizer.synthesize(
                problem['text'],
                problem['examples'],
                classification.get('algorithms', [])[:3],
                classification.get('constraints')
            )

            # Test
            test_cases = [(ex['input'], ex['output']) for ex in problem['examples']]
            result = tester.test(code, test_cases, verbose=False)

            status = "✅" if result['success_rate'] == 1.0 else "❌"
            print(f"  {status} {result['passed']}/{result['total']} ({result['success_rate']*100:.0f}%)")

            if result['success_rate'] == 1.0:
                solved += 1

        except Exception as e:
            print(f"  ❌ ERROR: {e}")

    print(f"\n📊 Results: {solved}/3 ({solved/3*100:.0f}%)")
    print(f"Baseline (mock): 1/3 (33%)")

    if solved >= 2:
        print(f"\n✅ IMPROVEMENT: {solved}/3 > 1/3")
        return True
    else:
        print(f"\n⚠️  Need improvement: {solved}/3 vs 1/3 baseline")
        return False

def benchmark_all():
    """Full benchmark on all 30 problems"""
    print("\n" + "="*70)
    print("🧪 FULL BENCHMARK: 30 USACO Bronze Problems")
    print("="*70)

    model_path = os.environ.get('IOI_LOCAL_MODEL')
    synthesizer = IOICodeSynthesizer(local_model_path=model_path, use_local=True)
    classifier = ProblemClassifier(local_model_path=model_path, use_local=True)
    tester = IOITester()

    results_by_difficulty = {'Easy': [], 'Medium': [], 'Medium-Hard': [], 'Hard': []}
    total_time = 0

    for i, problem in enumerate(ALL_PROBLEMS, 1):
        print(f"\n[{i}/30] {problem['name']} ({problem['difficulty']})")

        try:
            start_time = time.time()

            # Classify
            classification = classifier.classify(problem['text'], problem['examples'])

            # Synthesize
            code = synthesizer.synthesize(
                problem['text'],
                problem['examples'],
                classification.get('algorithms', [])[:3],
                classification.get('constraints')
            )

            # Test
            test_cases = [(ex['input'], ex['output']) for ex in problem['examples']]
            result = tester.test(code, test_cases, verbose=False)

            elapsed = time.time() - start_time
            total_time += elapsed

            status = "✅" if result['success_rate'] == 1.0 else "❌"
            print(f"  {status} {result['passed']}/{result['total']} ({elapsed:.1f}s)")

            results_by_difficulty[problem['difficulty']].append({
                'name': problem['name'],
                'passed': result['passed'],
                'total': result['total'],
                'success_rate': result['success_rate'],
                'time': elapsed
            })

        except Exception as e:
            print(f"  ❌ ERROR: {str(e)[:60]}")
            results_by_difficulty[problem['difficulty']].append({
                'name': problem['name'],
                'passed': 0,
                'total': len(problem['examples']),
                'success_rate': 0.0,
                'time': 0
            })

    # Summary
    print(f"\n{'='*70}")
    print("📊 RESULTS BY DIFFICULTY")
    print(f"{'='*70}")

    overall_solved = 0
    overall_total = 0

    for difficulty in ['Easy', 'Medium', 'Medium-Hard', 'Hard']:
        results = results_by_difficulty[difficulty]
        if not results:
            continue

        solved = sum(1 for r in results if r['success_rate'] == 1.0)
        total = len(results)
        overall_solved += solved
        overall_total += total

        print(f"\n{difficulty}: {solved}/{total} ({solved/total*100:.1f}%)")

    print(f"\n{'='*70}")
    print("🎯 OVERALL RESULTS")
    print(f"{'='*70}")
    print(f"\n✅ Problems Solved: {overall_solved}/{overall_total} ({overall_solved/overall_total*100:.1f}%)")
    print(f"⏱️  Total Time: {total_time:.1f}s ({total_time/overall_total:.1f}s/problem)")

    print(f"\n📈 Comparison:")
    print(f"  Mock mode: 12/30 (40%)")
    print(f"  Local model: {overall_solved}/30 ({overall_solved/overall_total*100:.1f}%)")

    if overall_solved > 12:
        print(f"\n✅ IMPROVEMENT: Local model beats mock mode!")
    elif overall_solved == 12:
        print(f"\n⚠️  EQUAL: Local model matches mock mode")
    else:
        print(f"\n⚠️  REGRESSION: Local model underperforms mock mode")

    return overall_solved, overall_total

def main():
    """Run all tests in sequence"""
    print("="*70)
    print("🚀 LOCAL MODEL COMPREHENSIVE TEST (v0.76)")
    print("="*70)
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Check environment
    model_path = os.environ.get('IOI_LOCAL_MODEL')
    if not model_path or not os.path.exists(model_path):
        print(f"\n❌ ERROR: Model not found at {model_path}")
        print("Make sure IOI_LOCAL_MODEL is set and llama.cpp build is complete")
        return 1

    print(f"\n✅ Model: {model_path}")
    print(f"✅ Size: {os.path.getsize(model_path) / 1024**2:.0f}MB")

    # Run tests
    tests_run = []

    # 1. Sanity test
    print("\n" + "="*70)
    print("TEST 1: Sanity Check")
    print("="*70)
    sanity_pass = test_sanity()
    tests_run.append(("Sanity", sanity_pass))

    if not sanity_pass:
        print("\n⚠️  Sanity test failed - check CUDA compatibility")
        print("Try: python3 test_local_model_ready.py --sanity-only")
        return 1

    # 2. Three easy problems
    print("\n" + "="*70)
    print("TEST 2: Three Easy Problems")
    print("="*70)
    easy_pass = test_three_easy()
    tests_run.append(("3 Easy", easy_pass))

    # 3. Full benchmark
    print("\n" + "="*70)
    print("TEST 3: Full 30-Problem Benchmark")
    print("="*70)
    solved, total = benchmark_all()
    full_pass = solved >= 12
    tests_run.append(("Full (12+/30)", full_pass))

    # Final summary
    print("\n" + "="*70)
    print("📋 TEST SUMMARY")
    print("="*70)

    for test_name, passed in tests_run:
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}")

    all_passed = all(p for _, p in tests_run)

    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Local model ready for production!")
    else:
        print("⚠️  SOME TESTS FAILED - Check logs and debug")
    print("="*70)

    return 0 if all_passed else 1

if __name__ == "__main__":
    if "--sanity-only" in sys.argv:
        success = test_sanity()
        sys.exit(0 if success else 1)
    else:
        sys.exit(main())
