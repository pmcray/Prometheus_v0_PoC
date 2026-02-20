#!/usr/bin/env python3
"""
IOI Automated Tester (v0.75)

Runs generated code against test cases with timeout and correctness checking.
"""

import subprocess
import tempfile
import os
import time
from typing import List, Dict, Tuple
from pathlib import Path

class IOITester:
    """Test generated code on problems"""

    def __init__(self, timeout_seconds: float = 2.0):
        """
        Args:
            timeout_seconds: Maximum time for each test case
        """
        self.timeout = timeout_seconds
        self.test_results = []

    def test(self,
             code: str,
             test_cases: List[Tuple[str, str]],
             verbose: bool = False) -> Dict:
        """
        Run code on all test cases.

        Args:
            code: Python code to test
            test_cases: List of (input, expected_output) tuples
            verbose: Print detailed results

        Returns:
            {
                'passed': int,
                'total': int,
                'success_rate': float,
                'failures': list of failure details,
                'time_avg': average execution time
            }
        """
        results = {
            'passed': 0,
            'total': len(test_cases),
            'success_rate': 0.0,
            'failures': [],
            'time_avg': 0.0
        }

        if not test_cases:
            return results

        times = []

        for i, (test_input, expected_output) in enumerate(test_cases):
            try:
                start = time.time()
                actual_output, error = self._run_code(code, test_input)
                elapsed = time.time() - start
                times.append(elapsed)

                if error:
                    results['failures'].append({
                        'test': i + 1,
                        'type': 'runtime_error',
                        'error': error,
                        'input': test_input[:100]
                    })
                    if verbose:
                        print(f"❌ Test {i+1}: Runtime Error - {error[:100]}")
                    continue

                # Compare outputs
                if self._compare_outputs(actual_output, expected_output):
                    results['passed'] += 1
                    if verbose:
                        print(f"✅ Test {i+1}: PASSED ({elapsed:.3f}s)")
                else:
                    results['failures'].append({
                        'test': i + 1,
                        'type': 'wrong_answer',
                        'expected': expected_output[:100],
                        'actual': actual_output[:100],
                        'input': test_input[:100]
                    })
                    if verbose:
                        print(f"❌ Test {i+1}: Wrong Answer")
                        print(f"   Expected: {expected_output[:50]}")
                        print(f"   Got:      {actual_output[:50]}")

            except subprocess.TimeoutExpired:
                results['failures'].append({
                    'test': i + 1,
                    'type': 'timeout',
                    'timeout': self.timeout
                })
                if verbose:
                    print(f"❌ Test {i+1}: TIMEOUT (>{self.timeout}s)")

            except Exception as e:
                results['failures'].append({
                    'test': i + 1,
                    'type': 'error',
                    'error': str(e)
                })
                if verbose:
                    print(f"❌ Test {i+1}: Error - {e}")

        results['success_rate'] = results['passed'] / results['total']
        results['time_avg'] = sum(times) / len(times) if times else 0.0

        return results

    def _run_code(self, code: str, input_data: str) -> Tuple[str, str]:
        """
        Execute code in subprocess with input.

        Returns:
            (stdout, stderr)
        """
        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            code_file = f.name

        try:
            # Run with timeout
            proc = subprocess.run(
                ['python3', code_file],
                input=input_data,
                capture_output=True,
                timeout=self.timeout,
                text=True
            )

            return proc.stdout, proc.stderr

        finally:
            # Clean up temp file
            try:
                os.unlink(code_file)
            except OSError:
                pass

    def _compare_outputs(self, actual: str, expected: str) -> bool:
        """
        Compare outputs with flexible whitespace handling.
        """
        # Strip and normalize whitespace
        actual_lines = [line.strip() for line in actual.strip().split('\n')]
        expected_lines = [line.strip() for line in expected.strip().split('\n')]

        # Remove empty lines
        actual_lines = [l for l in actual_lines if l]
        expected_lines = [l for l in expected_lines if l]

        return actual_lines == expected_lines

    def test_file(self,
                  code_file: Path,
                  test_cases: List[Tuple[str, str]],
                  verbose: bool = False) -> Dict:
        """Test a code file directly"""
        with open(code_file, 'r') as f:
            code = f.read()
        return self.test(code, test_cases, verbose)


class TestGenerator:
    """Generate additional test cases for problems"""

    def generate_edge_cases(self, constraints: Dict) -> List[str]:
        """
        Generate edge case inputs based on constraints.

        Args:
            constraints: {'n_min': 1, 'n_max': 1000, 'value_min': 1, 'value_max': 10^9}

        Returns:
            List of test input strings
        """
        edge_cases = []

        n_min = constraints.get('n_min', 1)
        n_max = constraints.get('n_max', 1000)
        v_min = constraints.get('value_min', 1)
        v_max = constraints.get('value_max', 10**9)

        # Minimum size
        edge_cases.append(self._generate_array_input(n_min, v_min, v_max))

        # Maximum size (if reasonable)
        if n_max <= 1000:
            edge_cases.append(self._generate_array_input(n_max, v_min, v_max))

        # Small size
        if n_min < 10:
            edge_cases.append(self._generate_array_input(min(10, n_max), v_min, v_max))

        # Medium size
        mid_n = (n_min + n_max) // 2
        edge_cases.append(self._generate_array_input(mid_n, v_min, v_max))

        # All same value
        edge_cases.append(self._generate_array_input(min(100, n_max), v_min, v_min))

        # Alternating values
        edge_cases.append(self._generate_alternating_input(min(100, n_max), v_min, v_max))

        return edge_cases

    def generate_random_cases(self,
                             constraints: Dict,
                             num_cases: int = 10) -> List[str]:
        """Generate random test cases"""
        import random

        cases = []
        n_min = constraints.get('n_min', 1)
        n_max = constraints.get('n_max', 1000)
        v_min = constraints.get('value_min', 1)
        v_max = constraints.get('value_max', 10**9)

        for _ in range(num_cases):
            n = random.randint(n_min, min(n_max, 1000))
            cases.append(self._generate_array_input(n, v_min, v_max))

        return cases

    def _generate_array_input(self, n: int, v_min: int, v_max: int) -> str:
        """Generate input with n random values"""
        import random

        values = [random.randint(v_min, min(v_max, 10**6)) for _ in range(n)]
        return f"{n}\n{' '.join(map(str, values))}"

    def _generate_alternating_input(self, n: int, v_min: int, v_max: int) -> str:
        """Generate alternating min/max values"""
        values = [v_min if i % 2 == 0 else min(v_max, 10**6) for i in range(n)]
        return f"{n}\n{' '.join(map(str, values))}"


# ============================================================================
# EXAMPLE USAGE & TESTS
# ============================================================================

if __name__ == "__main__":
    print("Testing IOI Tester...")

    # Test code (simple solution to count even numbers)
    test_code = """
n = int(input())
arr = list(map(int, input().split()))
count = sum(1 for x in arr if x % 2 == 0)
print(count)
"""

    # Test cases
    test_cases = [
        ("5\n2 4 6 8 10", "5"),
        ("3\n1 3 5", "0"),
        ("4\n1 2 3 4", "2"),
        ("1\n2", "1"),
        ("2\n1 1", "0"),
    ]

    # Initialize tester
    tester = IOITester(timeout_seconds=2.0)

    # Run tests
    print("\n" + "="*70)
    print("TESTING CODE")
    print("="*70)
    results = tester.test(test_code, test_cases, verbose=True)

    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"Passed: {results['passed']}/{results['total']}")
    print(f"Success Rate: {results['success_rate']*100:.1f}%")
    print(f"Average Time: {results['time_avg']:.3f}s")

    if results['failures']:
        print(f"\nFailures: {len(results['failures'])}")
        for failure in results['failures']:
            print(f"  Test {failure['test']}: {failure['type']}")

    # Test generator
    print("\n" + "="*70)
    print("TEST GENERATOR")
    print("="*70)

    generator = TestGenerator()
    constraints = {
        'n_min': 1,
        'n_max': 1000,
        'value_min': 1,
        'value_max': 10**9
    }

    edge_cases = generator.generate_edge_cases(constraints)
    print(f"\nGenerated {len(edge_cases)} edge cases:")
    for i, case in enumerate(edge_cases[:3], 1):
        print(f"\nEdge case {i}:")
        print(case[:100] + ("..." if len(case) > 100 else ""))

    random_cases = generator.generate_random_cases(constraints, num_cases=3)
    print(f"\nGenerated {len(random_cases)} random cases:")
    for i, case in enumerate(random_cases[:2], 1):
        print(f"\nRandom case {i}:")
        print(case[:100] + ("..." if len(case) > 100 else ""))

    print("\n✅ Tester and Generator working!")
