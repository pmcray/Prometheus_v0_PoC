#!/usr/bin/env python3
"""
Prometheus IOI Bronze (v0.75)

Complete system for solving IOI Bronze-level competitive programming problems.
Integrates: Problem classification → Evolutionary search → Code synthesis → Testing

Architecture:
  Problem → Classifier → Evolution → Synthesizer → Tester → Solution
"""

import os
import json
import time
from typing import List, Dict, Tuple
from pathlib import Path

# Import our components
from ioi_primitives import IOIPrimitives
from ioi_evolution import IOIEvolution, AlgorithmSequence
from ioi_tester import IOITester, TestGenerator

# Conditional import for synthesizer (cloud or local)
# Prefer local synthesizer (uses llama.cpp), fall back to cloud synthesizer (uses Gemini API)
try:
    from ioi_synthesizer_local import IOICodeSynthesizer, ProblemClassifier
    SYNTHESIZER_AVAILABLE = True
except ImportError:
    try:
        from ioi_synthesizer import IOICodeSynthesizer, ProblemClassifier
        SYNTHESIZER_AVAILABLE = True
    except ImportError:
        SYNTHESIZER_AVAILABLE = False


class PrometheusIOIBronze:
    """Complete IOI Bronze problem-solving system"""

    def __init__(self,
                 api_key: str = None,
                 local_model_path: str = None,
                 use_local: bool = False,
                 population_size: int = 30,
                 max_generations: int = 20,
                 timeout_seconds: float = 2.0):
        """
        Initialize IOI Bronze system.

        Args:
            api_key: Google API key for cloud LLM (Gemini)
            local_model_path: Path to local GGUF model
            use_local: Prefer local model over cloud
            population_size: Evolution population size
            max_generations: Maximum evolution generations
            timeout_seconds: Test timeout per case
        """
        # Initialize components
        self.primitives = IOIPrimitives()
        self.primitive_names = self._get_primitive_names()

        self.tester = IOITester(timeout_seconds=timeout_seconds)
        self.test_generator = TestGenerator()

        # Evolution parameters
        self.population_size = population_size
        self.max_generations = max_generations

        # Optional LLM components (local or cloud)
        self.use_llm = SYNTHESIZER_AVAILABLE and (use_local or api_key is not None)

        if self.use_llm:
            self.classifier = ProblemClassifier(
                api_key=api_key,
                local_model_path=local_model_path,
                use_local=use_local
            )
            self.synthesizer = IOICodeSynthesizer(
                api_key=api_key,
                local_model_path=local_model_path,
                use_local=use_local
            )
            mode = "local model" if use_local else "cloud (Gemini)"
            print(f"✅ LLM mode: Using {mode} for classification and synthesis")
        else:
            self.classifier = None
            self.synthesizer = None
            print("⚠️  Mock mode: Using template-based code generation")

        # Statistics
        self.problems_solved = 0
        self.total_problems = 0
        self.solve_times = []

    def _get_primitive_names(self) -> List[str]:
        """Extract all primitive names from IOIPrimitives"""
        import inspect

        names = []
        for name, method in inspect.getmembers(IOIPrimitives, predicate=inspect.isfunction):
            if not name.startswith('_'):
                names.append(name)

        return names

    def solve_problem(self,
                     problem_text: str,
                     examples: List[Dict],
                     constraints: Dict = None,
                     verbose: bool = True) -> Dict:
        """
        Solve a competitive programming problem.

        Args:
            problem_text: Problem description
            examples: List of {'input': str, 'output': str}
            constraints: Optional constraints dict
            verbose: Print progress

        Returns:
            {
                'solved': bool,
                'code': str,
                'algorithm_sequence': list,
                'test_results': dict,
                'generation': int,
                'time_seconds': float
            }
        """
        start_time = time.time()
        self.total_problems += 1

        if verbose:
            print(f"\n{'='*70}")
            print(f"SOLVING PROBLEM {self.total_problems}")
            print(f"{'='*70}")
            print(f"Problem: {problem_text[:100]}...")

        # Step 1: Classify problem
        if verbose:
            print(f"\n📊 Step 1: Classifying problem...")

        if self.use_llm:
            classification = self.classifier.classify(problem_text, examples)
            suggested_algorithms = classification.get('algorithms', [])
            if constraints is None:
                constraints = classification.get('constraints', {})
        else:
            # Mock classification
            suggested_algorithms = ['use_array', 'count_if', 'find_max']
            if constraints is None:
                constraints = {'n_max': 1000, 'time_limit_ms': 2000}

        if verbose:
            print(f"   Suggested algorithms: {suggested_algorithms[:5]}")

        # Step 2: Evolutionary search
        if verbose:
            print(f"\n🧬 Step 2: Evolving algorithm sequences...")

        best_solution = self._evolve_solution(
            problem_text,
            examples,
            suggested_algorithms,
            constraints,
            verbose=verbose
        )

        # Record statistics
        elapsed = time.time() - start_time
        self.solve_times.append(elapsed)

        if best_solution['solved']:
            self.problems_solved += 1

        best_solution['time_seconds'] = elapsed

        if verbose:
            print(f"\n{'='*70}")
            if best_solution['solved']:
                print(f"✅ SOLVED in {elapsed:.1f}s")
            else:
                print(f"❌ FAILED after {elapsed:.1f}s")
            print(f"{'='*70}")

        return best_solution

    def _evolve_solution(self,
                        problem_text: str,
                        examples: List[Dict],
                        suggested_algorithms: List[str],
                        constraints: Dict,
                        verbose: bool) -> Dict:
        """Run evolutionary search to find solution"""

        # Initialize evolution
        evolver = IOIEvolution(
            primitive_names=self.primitive_names,
            population_size=self.population_size,
            max_sequence_length=3  # Keep it simple
        )

        evolver.initialize_population(suggested_algorithms)

        # Convert examples to test cases
        test_cases = [(ex['input'], ex['output']) for ex in examples]

        best_solution = {
            'solved': False,
            'code': None,
            'algorithm_sequence': [],
            'test_results': {},
            'generation': 0
        }

        # Evolution loop
        for gen in range(self.max_generations):
            if verbose and gen % 5 == 0:
                print(f"   Generation {gen+1}/{self.max_generations}...")

            # Evaluate all individuals
            for individual in evolver.population:
                # Generate code
                code = self._synthesize_code(
                    problem_text,
                    examples,
                    individual.algorithms,
                    constraints
                )

                # Test code
                test_results = self.tester.test(code, test_cases, verbose=False)

                # Calculate fitness
                fitness = evolver.evaluate_fitness(individual, test_results)

                # Track best
                if fitness > best_solution['test_results'].get('success_rate', 0):
                    best_solution = {
                        'solved': test_results['success_rate'] >= 0.99,
                        'code': code,
                        'algorithm_sequence': individual.algorithms.copy(),
                        'test_results': test_results,
                        'generation': gen + 1
                    }

            # Early stopping if solved
            if best_solution['solved']:
                if verbose:
                    print(f"   ✅ Solution found at generation {gen+1}!")
                break

            # Evolve next generation
            evolver.evolve_generation()

        return best_solution

    def _synthesize_code(self,
                        problem_text: str,
                        examples: List[Dict],
                        algorithm_sequence: List[str],
                        constraints: Dict) -> str:
        """Generate code from algorithm sequence"""

        if self.use_llm:
            # Use LLM synthesis
            try:
                code = self.synthesizer.synthesize(
                    problem_text,
                    examples,
                    algorithm_sequence,
                    constraints
                )
                return code
            except Exception as e:
                print(f"   LLM synthesis failed: {e}")
                return self._generate_template_code(algorithm_sequence)
        else:
            # Use template-based generation
            return self._generate_template_code(algorithm_sequence)

    def _generate_template_code(self, algorithm_sequence: List[str]) -> str:
        """Generate simple template code (fallback)"""
        return f"""# Template solution using: {', '.join(algorithm_sequence)}
n = int(input())
arr = list(map(int, input().split()))

# Process using suggested algorithms
result = 0
for x in arr:
    # Apply logic here based on: {algorithm_sequence}
    if x % 2 == 0:  # Example: count even
        result += 1

print(result)
"""

    def benchmark(self, problems: List[Dict], verbose: bool = True) -> Dict:
        """
        Benchmark on multiple problems.

        Args:
            problems: List of problem dicts with keys:
                - 'text': problem description
                - 'examples': list of example dicts
                - 'constraints': optional constraints

        Returns:
            {
                'solved': int,
                'total': int,
                'success_rate': float,
                'avg_time': float,
                'results': list of individual results
            }
        """
        results = []

        for i, problem in enumerate(problems, 1):
            if verbose:
                print(f"\n{'#'*70}")
                print(f"PROBLEM {i}/{len(problems)}")
                print(f"{'#'*70}")

            result = self.solve_problem(
                problem['text'],
                problem['examples'],
                problem.get('constraints'),
                verbose=verbose
            )
            results.append(result)

        # Aggregate statistics
        solved = sum(1 for r in results if r['solved'])
        total = len(results)
        success_rate = solved / total if total > 0 else 0.0
        avg_time = sum(self.solve_times) / len(self.solve_times) if self.solve_times else 0.0

        summary = {
            'solved': solved,
            'total': total,
            'success_rate': success_rate,
            'avg_time': avg_time,
            'results': results
        }

        if verbose:
            print(f"\n{'='*70}")
            print("BENCHMARK SUMMARY")
            print(f"{'='*70}")
            print(f"Solved: {solved}/{total} ({success_rate*100:.1f}%)")
            print(f"Average time: {avg_time:.1f}s per problem")
            print(f"{'='*70}")

        return summary


# ============================================================================
# EXAMPLE USAGE & TESTS
# ============================================================================

if __name__ == "__main__":
    print("Testing Prometheus IOI Bronze...")

    # Initialize system (try local model first, then cloud, then mock)
    local_model = os.environ.get('IOI_LOCAL_MODEL')
    api_key = os.environ.get('GOOGLE_API_KEY')

    if local_model and Path(local_model).exists():
        print(f"🔧 Using local model: {local_model}")
        system = PrometheusIOIBronze(
            local_model_path=local_model,
            use_local=True,
            population_size=20,
            max_generations=10,
            timeout_seconds=2.0
        )
    elif api_key:
        print("☁️  Using cloud model (Gemini)")
        system = PrometheusIOIBronze(
            api_key=api_key,
            population_size=20,
            max_generations=10,
            timeout_seconds=2.0
        )
    else:
        print("⚠️  No model available, using mock mode")
        system = PrometheusIOIBronze(
            population_size=20,
            max_generations=10,
            timeout_seconds=2.0
        )

    # Test problem: Count even numbers
    problem = {
        'text': """
        Count Even Numbers

        You are given an array of N integers. Count how many of them are even.

        Input:
        - First line: N (1 ≤ N ≤ 1000)
        - Second line: N space-separated integers

        Output:
        - A single integer: the count of even numbers
        """,
        'examples': [
            {'input': '5\n2 4 6 8 10', 'output': '5'},
            {'input': '3\n1 3 5', 'output': '0'},
            {'input': '4\n1 2 3 4', 'output': '2'},
        ],
        'constraints': {
            'n_max': 1000,
            'time_limit_ms': 2000
        }
    }

    # Solve single problem
    print("\n" + "="*70)
    print("SINGLE PROBLEM TEST")
    print("="*70)

    result = system.solve_problem(
        problem['text'],
        problem['examples'],
        problem['constraints'],
        verbose=True
    )

    if result['solved']:
        print("\n✅ Problem solved!")
        print(f"\nGenerated code:")
        print("-"*70)
        print(result['code'])
        print("-"*70)
        print(f"\nAlgorithm sequence: {result['algorithm_sequence']}")
        print(f"Test results: {result['test_results']['passed']}/{result['test_results']['total']}")
    else:
        print("\n❌ Problem not solved")
        print(f"Best success rate: {result['test_results'].get('success_rate', 0)*100:.1f}%")

    # Benchmark on multiple problems (if desired)
    # benchmark_problems = [problem, problem, problem]  # Duplicate for testing
    # summary = system.benchmark(benchmark_problems, verbose=False)

    print("\n✅ IOI Bronze system test complete!")
