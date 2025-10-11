#!/usr/bin/env python3
"""
Test simplified synthesizer on 3 easy problems
"""

import os
import sys
import time

# Set environment
os.environ['PATH'] = f"/home/pmc/llama.cpp/build/bin:{os.environ.get('PATH', '')}"
os.environ['IOI_LOCAL_MODEL'] = "/home/pmc/ioi_models/deepseek-coder-1.3b-instruct.Q4_K_M.gguf"

from ioi_synthesizer_simple import SimpleIOICodeSynthesizer, SimpleProblemClassifier
from usaco_bronze_problems import PROBLEM_1, PROBLEM_2, PROBLEM_3
from ioi_tester import IOITester

def test_three_problems():
    """Test on 3 easy problems with simplified synthesizer"""
    print("="*70)
    print("🧪 SIMPLE SYNTHESIZER TEST: 3 Easy Problems")
    print("="*70)

    model_path = os.environ.get('IOI_LOCAL_MODEL')
    print(f"Model: {model_path}\n")

    # Initialize
    synthesizer = SimpleIOICodeSynthesizer(model_path)
    classifier = SimpleProblemClassifier()
    tester = IOITester()

    problems = [PROBLEM_1, PROBLEM_2, PROBLEM_3]
    solved = 0
    total_time = 0

    for i, problem in enumerate(problems, 1):
        print(f"\n[{i}/3] {problem['name']}")
        print(f"Problem: {problem['text'][:60]}...")

        try:
            start_time = time.time()

            # Classify (fast heuristic)
            classification = classifier.classify(problem['text'])
            print(f"  Algorithms: {', '.join(classification['algorithms'][:2])}")

            # Synthesize
            code = synthesizer.synthesize(
                problem['text'],
                problem['examples'],
                classification['algorithms']
            )

            synth_time = time.time() - start_time
            total_time += synth_time

            print(f"  Generated in {synth_time:.1f}s")
            print(f"  Code preview: {code.split(chr(10))[0][:50]}...")

            # Test
            test_cases = [(ex['input'], ex['output']) for ex in problem['examples']]
            result = tester.test(code, test_cases, verbose=False)

            status = "✅" if result['success_rate'] == 1.0 else "❌"
            print(f"  {status} Tests: {result['passed']}/{result['total']} ({result['success_rate']*100:.0f}%)")

            if result['success_rate'] == 1.0:
                solved += 1
            elif result.get('failures'):
                print(f"  First failure: {result['failures'][0].get('error', 'Output mismatch')[:60]}")

        except Exception as e:
            print(f"  ❌ ERROR: {str(e)[:60]}")

    print(f"\n{'='*70}")
    print(f"📊 RESULTS")
    print(f"{'='*70}")
    print(f"\n✅ Problems Solved: {solved}/3 ({solved/3*100:.0f}%)")
    print(f"⏱️  Total Time: {total_time:.1f}s ({total_time/3:.1f}s/problem)")

    print(f"\n📈 Comparison:")
    print(f"  Mock mode: 1/3 (33%)")
    print(f"  Simple synthesizer: {solved}/3 ({solved/3*100:.0f}%)")

    if solved >= 2:
        print(f"\n✅ SUCCESS: {solved}/3 ≥ 2/3 target")
        return True
    else:
        print(f"\n⚠️  Need improvement: {solved}/3 < 2/3 target")
        return False

if __name__ == "__main__":
    success = test_three_problems()
    sys.exit(0 if success else 1)
