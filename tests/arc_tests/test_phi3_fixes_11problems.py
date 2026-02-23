#!/usr/bin/env python3
"""
Test Phi-3 prompt fixes on 11 previously failed problems
Expected: 8-9/11 should now pass (vs 0/11 before)
"""

import os
import sys
from ioi_synthesizer_local import IOICodeSynthesizer, ProblemClassifier
from ioi_tester import IOITester

# 11 failed problems from original benchmark
FAILED_PROBLEMS = [
    {
        'name': 'Sum of Array',
        'difficulty': 'Easy',
        'text': 'Calculate the sum of all elements in an array.',
        'examples': [
            {'input': '5\n1 2 3 4 5', 'output': '15'},
            {'input': '3\n10 20 30', 'output': '60'},
            {'input': '1\n42', 'output': '42'}
        ],
        'test_cases': [
            ({'input': '5\n1 2 3 4 5'}, '15'),
            ({'input': '3\n10 20 30'}, '60'),
            ({'input': '1\n42'}, '42')
        ],
        'algorithms': ['use_array', 'cumulative_sum']
    },
    {
        'name': 'Two Sum Exists',
        'difficulty': 'Medium-Hard',
        'text': 'Check if there exist two numbers in the array that sum to a target value.',
        'examples': [
            {'input': '5 10\n2 4 6 8 10', 'output': 'YES'},
            {'input': '3 100\n1 2 3', 'output': 'NO'},
            {'input': '4 7\n3 4 5 6', 'output': 'YES'}
        ],
        'test_cases': [
            ({'input': '5 10\n2 4 6 8 10'}, 'YES'),
            ({'input': '3 100\n1 2 3'}, 'NO'),
            ({'input': '4 7\n3 4 5 6'}, 'YES')
        ],
        'algorithms': ['use_array', 'use_set', 'two_pointers_pair_sum']
    },
    {
        'name': 'Range Sum',
        'difficulty': 'Easy',
        'text': 'Calculate the sum of elements in a given range [L, R] of an array.',
        'examples': [
            {'input': '5\n1 2 3 4 5\n1 3', 'output': '9'},
            {'input': '4\n10 20 30 40\n0 1', 'output': '30'},
            {'input': '3\n5 5 5\n0 2', 'output': '15'}
        ],
        'test_cases': [
            ({'input': '5\n1 2 3 4 5\n1 3'}, '9'),
            ({'input': '4\n10 20 30 40\n0 1'}, '30'),
            ({'input': '3\n5 5 5\n0 2'}, '15')
        ],
        'algorithms': ['use_array', 'use_prefix_sum']
    },
    {
        'name': 'Prime Number Check',
        'difficulty': 'Medium',
        'text': 'Check if a number is prime. Output YES or NO.',
        'examples': [
            {'input': '7', 'output': 'YES'},
            {'input': '12', 'output': 'NO'},
            {'input': '2', 'output': 'YES'}
        ],
        'test_cases': [
            ({'input': '7'}, 'YES'),
            ({'input': '12'}, 'NO'),
            ({'input': '2'}, 'YES')
        ],
        'algorithms': ['math_is_prime']
    },
    {
        'name': 'Nth Fibonacci Number',
        'difficulty': 'Medium',
        'text': 'Calculate the Nth Fibonacci number (0-indexed).',
        'examples': [
            {'input': '5', 'output': '5'},
            {'input': '10', 'output': '55'},
            {'input': '0', 'output': '0'}
        ],
        'test_cases': [
            ({'input': '5'}, '5'),
            ({'input': '10'}, '55'),
            ({'input': '0'}, '0')
        ],
        'algorithms': ['dp_fibonacci']
    },
    {
        'name': 'Coin Change',
        'difficulty': 'Hard',
        'text': 'Find minimum number of coins needed to make amount N using coins [1, 5, 10, 25].',
        'examples': [
            {'input': '30', 'output': '2'},
            {'input': '17', 'output': '4'},
            {'input': '0', 'output': '0'}
        ],
        'test_cases': [
            ({'input': '30'}, '2'),
            ({'input': '17'}, '4'),
            ({'input': '0'}, '0')
        ],
        'algorithms': ['dp_coin_change', 'greedy_minimum_coins']
    },
    {
        'name': 'Reverse String',
        'difficulty': 'Easy',
        'text': 'Reverse a string.',
        'examples': [
            {'input': 'hello', 'output': 'olleh'},
            {'input': 'world', 'output': 'dlrow'},
            {'input': 'a', 'output': 'a'}
        ],
        'test_cases': [
            ({'input': 'hello'}, 'olleh'),
            ({'input': 'world'}, 'dlrow'),
            ({'input': 'a'}, 'a')
        ],
        'algorithms': ['string_reverse']
    },
    {
        'name': 'Count Vowels',
        'difficulty': 'Easy',
        'text': 'Count the number of vowels (a, e, i, o, u) in a string (case-insensitive).',
        'examples': [
            {'input': 'hello', 'output': '2'},
            {'input': 'AEIOU', 'output': '5'},
            {'input': 'bcdfg', 'output': '0'}
        ],
        'test_cases': [
            ({'input': 'hello'}, '2'),
            ({'input': 'AEIOU'}, '5'),
            ({'input': 'bcdfg'}, '0')
        ],
        'algorithms': ['string_count', 'count_if']
    },
    {
        'name': 'Cumulative Sum',
        'difficulty': 'Easy',
        'text': 'Calculate cumulative sum array. Output space-separated integers.',
        'examples': [
            {'input': '4\n1 2 3 4', 'output': '1 3 6 10'},
            {'input': '3\n5 5 5', 'output': '5 10 15'},
            {'input': '1\n7', 'output': '7'}
        ],
        'test_cases': [
            ({'input': '4\n1 2 3 4'}, '1 3 6 10'),
            ({'input': '3\n5 5 5'}, '5 10 15'),
            ({'input': '1\n7'}, '7')
        ],
        'algorithms': ['use_array', 'cumulative_sum']
    },
    {
        'name': 'Filter Positive Numbers',
        'difficulty': 'Easy',
        'text': 'Filter and output only positive numbers from array. Output space-separated.',
        'examples': [
            {'input': '5\n-2 3 -1 5 0', 'output': '3 5'},
            {'input': '3\n-1 -2 -3', 'output': ''},
            {'input': '4\n1 2 3 4', 'output': '1 2 3 4'}
        ],
        'test_cases': [
            ({'input': '5\n-2 3 -1 5 0'}, '3 5'),
            ({'input': '3\n-1 -2 -3'}, ''),
            ({'input': '4\n1 2 3 4'}, '1 2 3 4')
        ],
        'algorithms': ['use_array', 'filter_by']
    },
    {
        'name': 'Partition Even and Odd',
        'difficulty': 'Medium',
        'text': 'Partition array into even numbers first, then odd numbers. Output space-separated.',
        'examples': [
            {'input': '5\n1 2 3 4 5', 'output': '2 4 1 3 5'},
            {'input': '4\n10 15 20 25', 'output': '10 20 15 25'},
            {'input': '3\n1 3 5', 'output': '1 3 5'}
        ],
        'test_cases': [
            ({'input': '5\n1 2 3 4 5'}, '2 4 1 3 5'),
            ({'input': '4\n10 15 20 25'}, '10 20 15 25'),
            ({'input': '3\n1 3 5'}, '1 3 5')
        ],
        'algorithms': ['use_array', 'filter_by', 'sort_by_key']
    }
]


def main():
    print("="*70)
    print("🧪 Testing Phi-3 Prompt Fixes on 11 Failed Problems")
    print("="*70)

    # Check if model is available
    model_path = os.environ.get('IOI_LOCAL_MODEL')
    if not model_path:
        print("\n❌ IOI_LOCAL_MODEL not set")
        print("   Set it to your Phi-3 model path:")
        print("   export IOI_LOCAL_MODEL=\"/home/pmc/ioi_models/Phi-3-mini-4k-instruct-q4.gguf\"")
        sys.exit(1)

    print(f"\n✅ Using model: {model_path}")
    print(f"🎯 Target: 8-9/11 passing (vs 0/11 before fixes)")
    print(f"🔧 Fixes applied:")
    print(f"   - max_tokens: 2048 → 4096")
    print(f"   - Code-only output enforcement")
    print(f"   - Explicit format specifications")
    print(f"   - Edge case handling prompts")
    print()

    # Initialize synthesizer with improved prompts
    synthesizer = IOICodeSynthesizer(
        local_model_path=model_path,
        use_local=True
    )

    tester = IOITester()

    results = []
    passed = 0
    failed = 0

    print("="*70)
    print("Running tests...")
    print("="*70)
    print()

    for i, problem in enumerate(FAILED_PROBLEMS, 1):
        print(f"[{i}/11] {problem['name']} ({problem['difficulty']})")
        print(f"  📝 Generating code...", end=" ", flush=True)

        try:
            # Generate code with improved prompts
            code = synthesizer.synthesize(
                problem['text'],
                problem['examples'],
                problem['algorithms']
            )

            print(f"✓ ({len(code)} chars)")

            # Convert test_cases from dict format to tuple format for IOITester
            # IOITester expects: List[Tuple[input_str, output_str]]
            # We have: List[Tuple[Dict[str, str], output_str]]
            test_cases_formatted = [
                (tc[0]['input'], tc[1]) if isinstance(tc[0], dict) else tc
                for tc in problem['test_cases']
            ]

            # Test the code
            result = tester.test(code, test_cases_formatted, verbose=False)

            # Check if result has expected keys
            if 'passed' in result and 'total' in result:
                all_passed = (result['passed'] == result['total'])
            else:
                all_passed = False
                print(f"  ⚠️  Unexpected result format: {result}")

            if all_passed:
                print(f"  ✅ PASSED: {result['passed']}/{result['total']} tests")
                passed += 1
                results.append({
                    'name': problem['name'],
                    'difficulty': problem['difficulty'],
                    'status': 'PASS',
                    'tests': f"{result['passed']}/{result['total']}",
                    'code_length': len(code)
                })
            else:
                print(f"  ❌ FAILED: {result['passed']}/{result['total']} tests")
                # Show first failure detail
                if result.get('failures'):
                    first_failure = result['failures'][0]
                    failure_type = first_failure.get('type', 'unknown')
                    if failure_type == 'runtime_error':
                        error_msg = first_failure.get('error', '')[:80]
                        print(f"  ❌ Runtime Error: {error_msg}")
                    elif failure_type == 'wrong_answer':
                        expected = first_failure.get('expected', '')[:40]
                        actual = first_failure.get('actual', '')[:40]
                        print(f"  ❌ Expected: {expected}")
                        print(f"     Got: {actual}")
                    elif failure_type == 'timeout':
                        print(f"  ❌ Timeout: >{first_failure.get('timeout', 2.0)}s")
                failed += 1

                # Get error summary for results
                error_summary = 'Output mismatch'
                if result.get('failures'):
                    first_failure = result['failures'][0]
                    if first_failure.get('type') == 'runtime_error':
                        error_summary = first_failure.get('error', 'Runtime error')[:100]
                    elif first_failure.get('type') == 'wrong_answer':
                        error_summary = f"Expected: {first_failure.get('expected', '')[:50]}"
                    elif first_failure.get('type') == 'timeout':
                        error_summary = 'Timeout'

                results.append({
                    'name': problem['name'],
                    'difficulty': problem['difficulty'],
                    'status': 'FAIL',
                    'tests': f"{result['passed']}/{result['total']}",
                    'error': error_summary,
                    'code_length': len(code)
                })

        except Exception as e:
            print(f"  ❌ ERROR: {str(e)[:80]}")
            failed += 1
            results.append({
                'name': problem['name'],
                'difficulty': problem['difficulty'],
                'status': 'ERROR',
                'error': str(e)[:100],
                'code_length': 0
            })

        print()

    # Summary
    print("="*70)
    print("📊 RESULTS SUMMARY")
    print("="*70)
    print()
    print(f"✅ Passed: {passed}/11 ({passed/11*100:.1f}%)")
    print(f"❌ Failed: {failed}/11 ({failed/11*100:.1f}%)")
    print()

    # Comparison
    print("📈 Comparison:")
    print(f"  Before fixes: 0/11 (0%)")
    print(f"  After fixes:  {passed}/11 ({passed/11*100:.1f}%)")
    print(f"  Improvement:  +{passed} problems fixed")
    print()

    # Expected vs Actual
    print("🎯 Expected: 8-9/11 (73-82%)")
    if passed >= 8:
        print(f"✅ SUCCESS: Met or exceeded target!")
    elif passed >= 6:
        print(f"⚠️  PARTIAL: Better than before, but below target")
    else:
        print(f"❌ BELOW TARGET: Fixes didn't work as expected")
    print()

    # Breakdown by difficulty
    print("📊 By Difficulty:")
    for diff in ['Easy', 'Medium', 'Medium-Hard', 'Hard']:
        diff_results = [r for r in results if r['difficulty'] == diff]
        if diff_results:
            diff_passed = len([r for r in diff_results if r['status'] == 'PASS'])
            diff_total = len(diff_results)
            print(f"  {diff:12s}: {diff_passed}/{diff_total} ({diff_passed/diff_total*100:.0f}%)")

    # Failed problems
    if failed > 0:
        print()
        print("="*70)
        print(f"❌ FAILED PROBLEMS ({failed}/11):")
        print("="*70)
        print()
        for i, r in enumerate([r for r in results if r['status'] in ['FAIL', 'ERROR']], 1):
            print(f"{i}. {r['name']} ({r['difficulty']})")
            if 'tests' in r:
                print(f"   Tests: {r['tests']}")
            if 'error' in r:
                print(f"   Error: {r['error']}")
            print()

    print("="*70)
    print("✅ Test complete!")
    print("="*70)

    # Return exit code based on success
    if passed >= 8:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Below target


if __name__ == "__main__":
    main()
