"""
Prometheus-Bench-v0.3: Advanced Generative & Formal Reasoning Benchmarks (v0.73)

Extends v0.2 with:
- Multimodal generative tasks (image/audio/video generation quality)
- Mathematical reasoning (symbolic problem solving)
- Creative synthesis benchmarks
- Hybrid intelligence evaluation (neural + symbolic)
"""

import os
import logging
import json
import random
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from abc import ABC, abstractmethod
from enum import Enum


class BenchmarkDomain(Enum):
    """Extended benchmark domains for v0.73"""
    GENERAL_GAME_PLAYING = "general_game_playing"
    CONVERSATIONAL_AI = "conversational_ai"
    CODE_OPTIMIZATION = "code_optimization"
    GENERATIVE_IMAGE = "generative_image"  # NEW in v0.73
    GENERATIVE_AUDIO = "generative_audio"  # NEW in v0.73
    GENERATIVE_VIDEO = "generative_video"  # NEW in v0.73
    MATHEMATICAL_REASONING = "mathematical_reasoning"  # NEW in v0.73


@dataclass
class BenchmarkResult:
    """Result of a single benchmark evaluation"""
    benchmark_name: str
    domain: str
    fitness_score: float
    execution_time_ms: float
    success: bool
    details: Dict[str, Any]
    timestamp: str
    agent_identifier: str


class MathProblem:
    """A mathematical problem for reasoning benchmarks."""

    def __init__(
        self,
        problem_id: str,
        problem_text: str,
        expected_answer: Any,
        difficulty: str,
        category: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.problem_id = problem_id
        self.problem_text = problem_text
        self.expected_answer = expected_answer
        self.difficulty = difficulty
        self.category = category
        self.metadata = metadata or {}


class MathBenchmark:
    """
    Mathematical Reasoning Benchmark (v0.73)

    Tests agent's ability to solve formal mathematical problems.
    Fitness is binary: correct answer = 1.0, incorrect = 0.0

    Categories:
    - Algebra (equation solving)
    - Calculus (derivatives, integrals)
    - Linear algebra (matrices, vectors)
    - Number theory (primes, divisibility)
    """

    def __init__(self):
        """Initialize math benchmark with problem sets."""
        self.problems = self._create_problem_set()
        logging.info(f"MathBenchmark initialized with {len(self.problems)} problems")

    def _create_problem_set(self) -> List[MathProblem]:
        """Create a curated set of math problems."""
        problems = []

        # Algebra problems
        problems.extend([
            MathProblem(
                "algebra_001",
                "Solve for x: x**2 - 4 = 0",
                [-2, 2],  # Accept either order
                "easy",
                "algebra"
            ),
            MathProblem(
                "algebra_002",
                "Solve for x: 2*x + 5 = 13",
                [4],
                "easy",
                "algebra"
            ),
            MathProblem(
                "algebra_003",
                "Solve for x: x**2 + 5*x + 6 = 0",
                [-2, -3],
                "medium",
                "algebra"
            ),
            MathProblem(
                "algebra_004",
                "Simplify: (x + 2)*(x - 2)",
                "x**2 - 4",
                "easy",
                "algebra"
            ),
        ])

        # Calculus problems
        problems.extend([
            MathProblem(
                "calculus_001",
                "Derivative of x**2 with respect to x",
                "2*x",
                "easy",
                "calculus"
            ),
            MathProblem(
                "calculus_002",
                "Derivative of sin(x) with respect to x",
                "cos(x)",
                "easy",
                "calculus"
            ),
            MathProblem(
                "calculus_003",
                "Integral of 2*x with respect to x",
                "x**2",
                "medium",
                "calculus",
                metadata={"indefinite": True}
            ),
            MathProblem(
                "calculus_004",
                "Derivative of x**3 + 2*x**2 - 5*x + 1 with respect to x",
                "3*x**2 + 4*x - 5",
                "medium",
                "calculus"
            ),
        ])

        # Number theory
        problems.extend([
            MathProblem(
                "number_001",
                "Is 17 a prime number?",
                True,
                "easy",
                "number_theory"
            ),
            MathProblem(
                "number_002",
                "What is gcd(48, 18)?",
                6,
                "easy",
                "number_theory"
            ),
        ])

        return problems

    def evaluate(
        self,
        agent,
        num_problems: int = 10,
        difficulty: Optional[str] = None
    ) -> BenchmarkResult:
        """
        Evaluate agent on math problems.

        Args:
            agent: Agent with solve_math_problem(problem_text) method
            num_problems: Number of problems to test
            difficulty: Filter by difficulty (easy/medium/hard)

        Returns:
            BenchmarkResult with fitness score (% correct)
        """
        start_time = datetime.now()

        # Select problems
        available = self.problems
        if difficulty:
            available = [p for p in available if p.difficulty == difficulty]

        test_problems = random.sample(available, min(num_problems, len(available)))

        # Evaluate
        correct = 0
        results = []

        for problem in test_problems:
            try:
                # Agent attempts to solve
                agent_answer = agent.solve_math_problem(problem.problem_text)

                # Check correctness
                is_correct = self._check_answer(
                    agent_answer,
                    problem.expected_answer,
                    problem.category
                )

                if is_correct:
                    correct += 1

                results.append({
                    "problem_id": problem.problem_id,
                    "category": problem.category,
                    "correct": is_correct,
                    "agent_answer": str(agent_answer),
                    "expected": str(problem.expected_answer)
                })

            except Exception as e:
                logging.warning(f"Problem {problem.problem_id} failed: {e}")
                results.append({
                    "problem_id": problem.problem_id,
                    "correct": False,
                    "error": str(e)
                })

        # Calculate fitness
        fitness = correct / len(test_problems) if test_problems else 0.0

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return BenchmarkResult(
            benchmark_name="math_reasoning_v0_3",
            domain=BenchmarkDomain.MATHEMATICAL_REASONING.value,
            fitness_score=fitness,
            execution_time_ms=execution_time,
            success=True,
            details={
                "problems_tested": len(test_problems),
                "correct": correct,
                "accuracy": fitness,
                "results": results
            },
            timestamp=datetime.now().isoformat(),
            agent_identifier=getattr(agent, 'agent_id', 'unknown')
        )

    def _check_answer(
        self,
        agent_answer: Any,
        expected: Any,
        category: str
    ) -> bool:
        """
        Check if agent's answer matches expected answer.

        Handles different answer formats and symbolic equivalence.
        """
        # For lists (multiple solutions), check if they match regardless of order
        if isinstance(expected, list):
            if not isinstance(agent_answer, list):
                agent_answer = [agent_answer]
            return sorted([str(x) for x in agent_answer]) == sorted([str(x) for x in expected])

        # For booleans
        if isinstance(expected, bool):
            return bool(agent_answer) == expected

        # For numbers
        if isinstance(expected, (int, float)):
            try:
                return abs(float(agent_answer) - float(expected)) < 1e-6
            except (ValueError, TypeError):
                return False

        # For strings (symbolic expressions)
        if isinstance(expected, str):
            # Try direct match
            if str(agent_answer).strip() == expected.strip():
                return True

            # Try symbolic equivalence (would need sympy integration)
            return self._symbolic_equivalent(str(agent_answer), expected)

        return str(agent_answer) == str(expected)

    def _symbolic_equivalent(self, expr1: str, expr2: str) -> bool:
        """Check if two expressions are symbolically equivalent."""
        try:
            import sympy as sp
            from sympy.parsing.sympy_parser import parse_expr

            e1 = parse_expr(expr1)
            e2 = parse_expr(expr2)

            diff = sp.simplify(e1 - e2)
            return diff == 0

        except Exception:
            # Fallback to string comparison
            return expr1.strip() == expr2.strip()


class GenerativeImageBenchmark:
    """
    Generative Image Quality Benchmark (v0.73)

    Tests agent's ability to generate images matching text descriptions.
    Uses multimodal LLM to score alignment between prompt and generated image.
    """

    def __init__(self, multimodal_toolkit=None):
        """
        Initialize image generation benchmark.

        Args:
            multimodal_toolkit: MultimodalToolkit instance for evaluation
        """
        self.toolkit = multimodal_toolkit
        self.test_prompts = self._create_test_prompts()
        logging.info(f"GenerativeImageBenchmark initialized with {len(self.test_prompts)} prompts")

    def _create_test_prompts(self) -> List[Dict[str, Any]]:
        """Create test prompts for image generation."""
        return [
            {
                "prompt": "A serene mountain landscape at sunset",
                "criteria": ["landscape", "mountains", "sunset", "nature"],
                "difficulty": "easy"
            },
            {
                "prompt": "A cyberpunk detective in a rainy neon city",
                "criteria": ["cyberpunk", "detective", "rain", "neon", "city"],
                "difficulty": "hard"
            },
            {
                "prompt": "Abstract geometric patterns in blue and gold",
                "criteria": ["abstract", "geometric", "blue", "gold"],
                "difficulty": "medium"
            },
            {
                "prompt": "A friendly robot helping a child with homework",
                "criteria": ["robot", "child", "homework", "friendly"],
                "difficulty": "medium"
            },
        ]

    def evaluate(
        self,
        agent,
        num_prompts: int = 5
    ) -> BenchmarkResult:
        """
        Evaluate agent's image generation quality.

        Args:
            agent: Agent with generate_image(prompt) method
            num_prompts: Number of prompts to test

        Returns:
            BenchmarkResult with average quality score
        """
        start_time = datetime.now()

        test_prompts = random.sample(self.test_prompts, min(num_prompts, len(self.test_prompts)))

        scores = []
        results = []

        for prompt_data in test_prompts:
            try:
                # Agent generates image
                image_path = agent.generate_image(prompt_data["prompt"])

                # Evaluate quality
                if self.toolkit and image_path:
                    score = self.toolkit.evaluate_image_quality(
                        image_path,
                        prompt_data["prompt"]
                    )
                else:
                    # Placeholder scoring if toolkit not available
                    score = 0.5

                scores.append(score)
                results.append({
                    "prompt": prompt_data["prompt"],
                    "score": score,
                    "image_path": image_path
                })

            except Exception as e:
                logging.warning(f"Image generation failed: {e}")
                scores.append(0.0)
                results.append({
                    "prompt": prompt_data["prompt"],
                    "score": 0.0,
                    "error": str(e)
                })

        fitness = sum(scores) / len(scores) if scores else 0.0

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return BenchmarkResult(
            benchmark_name="generative_image_v0_3",
            domain=BenchmarkDomain.GENERATIVE_IMAGE.value,
            fitness_score=fitness,
            execution_time_ms=execution_time,
            success=True,
            details={
                "prompts_tested": len(test_prompts),
                "average_score": fitness,
                "results": results
            },
            timestamp=datetime.now().isoformat(),
            agent_identifier=getattr(agent, 'agent_id', 'unknown')
        )


class HybridReasoningBenchmark:
    """
    Hybrid Intelligence Benchmark (v0.73)

    Tests agent's ability to combine neural (LLM) reasoning with
    symbolic tools (SymPy) to solve complex problems.

    This measures the key capability for AGI: seamlessly integrating
    intuitive and formal reasoning.
    """

    def __init__(self, symbolic_agent=None):
        """
        Initialize hybrid reasoning benchmark.

        Args:
            symbolic_agent: SymbolicMathAgent instance
        """
        self.symbolic_agent = symbolic_agent
        self.test_problems = self._create_hybrid_problems()
        logging.info(f"HybridReasoningBenchmark initialized with {len(self.test_problems)} problems")

    def _create_hybrid_problems(self) -> List[Dict[str, Any]]:
        """Create problems requiring both neural and symbolic reasoning."""
        return [
            {
                "problem": "Find the critical points of f(x) = x**3 - 6*x**2 + 9*x + 1",
                "hint": "Critical points occur where the derivative equals zero",
                "expected_answer": [1, 3],
                "requires_strategy": True,
                "difficulty": "medium"
            },
            {
                "problem": "Solve the integral of (x**2 + 2*x) from 0 to 2",
                "hint": "First find the antiderivative, then evaluate at bounds",
                "expected_answer": 20/3,
                "requires_strategy": True,
                "difficulty": "medium"
            },
            {
                "problem": "Verify if (a + b)**2 = a**2 + 2*a*b + b**2",
                "hint": "Expand the left side and compare to right side",
                "expected_answer": True,
                "requires_strategy": False,
                "difficulty": "easy"
            },
        ]

    def evaluate(
        self,
        agent,
        num_problems: int = 5
    ) -> BenchmarkResult:
        """
        Evaluate agent's hybrid reasoning capability.

        Agent should demonstrate:
        1. High-level strategic thinking (LLM)
        2. Tool use (calling SymbolicMathAgent)
        3. Verification and error correction

        Args:
            agent: Agent with solve_hybrid_problem(problem, tools) method
            num_problems: Number of problems to test

        Returns:
            BenchmarkResult with success rate
        """
        start_time = datetime.now()

        test_problems = random.sample(
            self.test_problems,
            min(num_problems, len(self.test_problems))
        )

        correct = 0
        results = []

        for problem_data in test_problems:
            try:
                # Agent attempts to solve using hybrid approach
                agent_answer = agent.solve_hybrid_problem(
                    problem_data["problem"],
                    tools={"symbolic_math": self.symbolic_agent}
                )

                # Check correctness
                is_correct = self._check_hybrid_answer(
                    agent_answer,
                    problem_data["expected_answer"]
                )

                if is_correct:
                    correct += 1

                results.append({
                    "problem": problem_data["problem"],
                    "correct": is_correct,
                    "agent_answer": str(agent_answer),
                    "expected": str(problem_data["expected_answer"])
                })

            except Exception as e:
                logging.warning(f"Hybrid problem failed: {e}")
                results.append({
                    "problem": problem_data["problem"],
                    "correct": False,
                    "error": str(e)
                })

        fitness = correct / len(test_problems) if test_problems else 0.0

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return BenchmarkResult(
            benchmark_name="hybrid_reasoning_v0_3",
            domain=BenchmarkDomain.MATHEMATICAL_REASONING.value,
            fitness_score=fitness,
            execution_time_ms=execution_time,
            success=True,
            details={
                "problems_tested": len(test_problems),
                "correct": correct,
                "accuracy": fitness,
                "results": results
            },
            timestamp=datetime.now().isoformat(),
            agent_identifier=getattr(agent, 'agent_id', 'unknown')
        )

    def _check_hybrid_answer(self, agent_answer: Any, expected: Any) -> bool:
        """Check if hybrid reasoning produced correct answer."""
        # Similar to MathBenchmark._check_answer
        if isinstance(expected, list):
            if not isinstance(agent_answer, list):
                agent_answer = [agent_answer]
            return sorted([str(x) for x in agent_answer]) == sorted([str(x) for x in expected])

        if isinstance(expected, bool):
            return bool(agent_answer) == expected

        if isinstance(expected, (int, float)):
            try:
                return abs(float(agent_answer) - float(expected)) < 1e-5
            except (ValueError, TypeError):
                return False

        return str(agent_answer) == str(expected)


# Benchmark registry for v0.73
BENCHMARK_REGISTRY_V03 = {
    "math_reasoning": MathBenchmark,
    "generative_image": GenerativeImageBenchmark,
    "hybrid_reasoning": HybridReasoningBenchmark,
}


def get_benchmark_v03(name: str, **kwargs):
    """Factory function to create v0.73 benchmarks."""
    if name in BENCHMARK_REGISTRY_V03:
        return BENCHMARK_REGISTRY_V03[name](**kwargs)
    else:
        raise ValueError(f"Unknown benchmark: {name}")
