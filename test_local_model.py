#!/usr/bin/env python3
"""
Quick test of local model integration for IOI Bronze
Tests the improved synthesizer with DeepSeek-Coder-1.3B
"""

import os
import sys

# Set environment variables
os.environ['PATH'] = f"{os.environ['HOME']}/llama.cpp/build/bin:{os.environ.get('PATH', '')}"
os.environ['IOI_LOCAL_MODEL'] = f"{os.environ['HOME']}/ioi_models/deepseek-coder-1.3b-instruct.Q4_K_M.gguf"

from ioi_synthesizer_local import IOICodeSynthesizer, ProblemClassifier
from usaco_bronze_problems import PROBLEM_1, PROBLEM_2, PROBLEM_3
import ioi_tester

def test_local_synthesizer():
    """Test local model with improved prompts"""

    print("="*70)
    print("🧪 Testing Local Model Integration (v0.76)")
    print("="*70)

    # Check configuration
    model_path = os.environ.get('IOI_LOCAL_MODEL')
    print(f"\n📦 Model: {model_path}")
    print(f"✅ Model exists: {os.path.exists(model_path)}")

    # Initialize with local model
    print("\n🔧 Initializing local model synthesizer...")
    try:
        synthesizer = IOICodeSynthesizer(
            local_model_path=model_path,
            use_local=True
        )
        print(f"✅ Mode: {synthesizer.mode}")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return

    # Test classifier
    print("\n🔍 Testing problem classifier...")
    classifier = ProblemClassifier(
        local_model_path=model_path,
        use_local=True
    )

    # Test on Problem 1: Count Even Numbers
    problem = PROBLEM_1
    print(f"\n{'='*70}")
    print(f"Problem: {problem['name']} ({problem['difficulty']})")
    print(f"{'='*70}")

    try:
        # Classify
        print("\n📊 Classifying problem...")
        classification = classifier.classify(problem['text'], problem['examples'])
        print(f"Categories: {classification.get('categories', [])}")
        print(f"Algorithms: {classification.get('algorithms', [])[:5]}")
        print(f"Complexity: {classification.get('complexity', 'unknown')}")

        # Synthesize
        print("\n💻 Synthesizing code with local model...")
        code = synthesizer.synthesize(
            problem['text'],
            problem['examples'],
            classification.get('algorithms', ['use_array', 'count_if'])[:3],
            classification.get('constraints')
        )

        print("\nGenerated code:")
        print("-"*70)
        print(code)
        print("-"*70)

        # Test the code
        print("\n🧪 Testing generated code...")
        tester = ioi_tester.IOITester()
        test_cases = [(ex['input'], ex['output']) for ex in problem['examples']]

        results = tester.test(code, test_cases, verbose=False)

        print(f"\n📊 Results:")
        print(f"  Passed: {results['passed']}/{results['total']}")
        print(f"  Success Rate: {results['success_rate']*100:.1f}%")

        if results['success_rate'] == 1.0:
            print(f"\n✅ SUCCESS: Problem solved correctly!")
            return True
        else:
            print(f"\n⚠️  PARTIAL: {results['passed']}/{results['total']} tests passed")
            if results.get('failures'):
                print(f"\nFailures:")
                for failure in results['failures'][:2]:
                    print(f"  - {failure.get('error', 'Output mismatch')}")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting local model integration test...\n")

    success = test_local_synthesizer()

    print("\n" + "="*70)
    if success:
        print("✅ LOCAL MODEL TEST PASSED")
        print("Ready for full benchmark on 30 problems!")
    else:
        print("⚠️  LOCAL MODEL TEST INCOMPLETE")
        print("Need to debug or adjust prompts")
    print("="*70)

    sys.exit(0 if success else 1)
