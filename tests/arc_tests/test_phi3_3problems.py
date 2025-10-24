#!/usr/bin/env python3
"""
Test Phi-3-mini on 3 easy problems
"""

import os
import sys
import time

# Set environment for Phi-3
os.environ['PATH'] = f"/home/pmc/llama.cpp/build/bin:{os.environ.get('PATH', '')}"

from ioi_synthesizer_simple import SimpleIOICodeSynthesizer, SimpleProblemClassifier
from usaco_bronze_problems import PROBLEM_1, PROBLEM_2, PROBLEM_3
from ioi_tester import IOITester

def test_phi3():
    """Test Phi-3-mini on 3 easy problems"""
    print("="*70)
    print("🧪 PHI-3-MINI TEST: 3 Easy Problems")
    print("="*70)

    model_path = "/home/pmc/ioi_models/Phi-3-mini-4k-instruct-q4.gguf"
    print(f"Model: {model_path}")
    print(f"Size: {os.path.getsize(model_path) / 1024**3:.1f}GB\n")

    # Initialize
    synthesizer = SimpleIOICodeSynthesizer(model_path)
    classifier = SimpleProblemClassifier()
    tester = IOITester()

    problems = [PROBLEM_1, PROBLEM_2, PROBLEM_3]
    solved = 0
    total_time = 0

    for i, problem in enumerate(problems, 1):
        print(f"\n[{i}/3] {problem['name']}")

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

            print(f"  Generated in {synth_time:.1f}s")
            print(f"  Code length: {len(code)} chars")
            print(f"  First line: {code.split(chr(10))[0][:60]}...")

            # Test
            test_cases = [(ex['input'], ex['output']) for ex in problem['examples']]
            result = tester.test(code, test_cases, verbose=False)

            status = "✅" if result['success_rate'] == 1.0 else "❌"
            print(f"  {status} Tests: {result['passed']}/{result['total']} ({result['success_rate']*100:.0f}%)")

            if result['success_rate'] == 1.0:
                solved += 1
            elif result.get('failures'):
                error = result['failures'][0].get('error', 'Output mismatch')
                print(f"  Error: {error[:70]}")

        except Exception as e:
            print(f"  ❌ ERROR: {str(e)[:70]}")

    print(f"\n{'='*70}")
    print(f"📊 RESULTS")
    print(f"{'='*70}")
    print(f"\n✅ Problems Solved: {solved}/3 ({solved/3*100:.0f}%)")
    print(f"⏱️  Total Time: {total_time:.1f}s ({total_time/3:.1f}s/problem)")

    print(f"\n📈 Comparison:")
    print(f"  Mock mode: 1/3 (33%)")
    print(f"  DeepSeek-1.3B: 1/3 (33%)")
    print(f"  Phi-3-mini: {solved}/3 ({solved/3*100:.0f}%)")

    if solved >= 2:
        print(f"\n✅ SUCCESS: Phi-3 beats baseline!")
        return True
    else:
        print(f"\n⚠️  Phi-3 = baseline, not better")
        return False

if __name__ == "__main__":
    success = test_phi3()
    sys.exit(0 if success else 1)
