"""
Introspection and Evaluation Engine (IEE) v1.0 (Task P1.T5)

This module implements the fitness function for the evolutionary loop,
using the static Prometheus-Bench-v1 suite to ensure fitness monotonicity.
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional
from benchmarks.prometheus_bench_v1 import PrometheusBenchV1

class IEEV1:
    """
    Introspection and Evaluation Engine v1.0.
    The objective arbiter of intelligence for Project Prometheus.
    """
    
    def __init__(self, benchmark_path: str = "benchmarks/prometheus_bench_v1.json"):
        self.bench = PrometheusBenchV1()
        self.logger = logging.getLogger("IEE_v1")
        self.performance_history = {}

    def evaluate_agent_on_problem(self, problem_id: str, agent_code: str) -> Dict[str, Any]:
        """
        Evaluate a specific agent code on a specific problem.
        """
        problem = next((p for p in self.bench.problems if p.id == problem_id), None)
        if not problem:
            return {"success": False, "error": "Problem not found"}

        start_time = time.time()
        
        # We temporarily swap the problem's 'naive_code' with agent_code for testing
        original_naive = problem.naive_code
        problem.naive_code = agent_code
        
        success = self.bench.run_tests(problem_id, use_optimized=False)
        execution_time = time.time() - start_time
        
        # Restore original
        problem.naive_code = original_naive
        
        return {
            "success": success,
            "execution_time_ms": execution_time * 1000,
            "problem_id": problem_id,
            "complexity_target": problem.complexity_optimized
        }

    def calculate_fitness(self, agent_id: str, results: List[Dict[str, Any]]) -> float:
        """
        Calculate an overall fitness score based on benchmark results.
        Fitness = (Success Rate * 100) - (Avg Execution Time Adjustment)
        """
        if not results:
            return 0.0
            
        successes = sum(1 for r in results if r['success'])
        success_rate = successes / len(results)
        
        # Fitness is primarily success rate
        fitness = success_rate * 100.0
        
        # Store in history for monotonicity tracking
        if agent_id not in self.performance_history:
            self.performance_history[agent_id] = []
        self.performance_history[agent_id].append(fitness)
        
        return fitness

    def check_monotonicity(self, agent_id: str) -> bool:
        """
        Verify that the agent's fitness is not decreasing over time.
        """
        history = self.performance_history.get(agent_id, [])
        if len(history) < 2:
            return True
            
        return history[-1] >= history[-2]
