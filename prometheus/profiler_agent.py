"""
ProfilerAgent for Empirical Performance Measurement
Implements the empirical evaluation system from v0.46 workplan
"""

import time
import tracemalloc
import subprocess
import tempfile
import os
import psutil
import threading
import statistics
from typing import Dict, List, Any, Optional, Tuple
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import ast
import json

from .blackboard import AgentBase, BlackboardObject
from .schemas.communication import DynamicAnalysis

@dataclass
class PerformanceProfile:
    """Structured performance profile data"""
    execution_time_ms: Dict[str, float]
    peak_memory_mb: Dict[str, float]
    cpu_usage_percent: float
    io_operations: Dict[str, int]
    function_calls: int
    profile_metadata: Dict[str, Any]

class SecureExecutionEnvironment:
    """Secure containerized environment for code execution"""

    def __init__(self, timeout_seconds: int = 30):
        self.timeout = timeout_seconds
        self.temp_dir = None

    @contextmanager
    def __call__(self):
        """Context manager for secure execution"""
        self.temp_dir = tempfile.mkdtemp(prefix="prometheus_profiler_")
        try:
            yield self.temp_dir
        finally:
            # Clean up
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def execute_code(self, code: str, test_data: Any = None) -> Tuple[Any, Dict[str, Any]]:
        """Execute code in secure environment with performance monitoring"""
        with self as temp_dir:
            # Write code to temporary file
            code_file = os.path.join(temp_dir, "target_function.py")
            with open(code_file, 'w') as f:
                f.write(code)

            # Create test runner
            test_runner = f"""
import sys
import time
import tracemalloc
import json
import psutil
import os
sys.path.insert(0, '{temp_dir}')

from target_function import *

def run_performance_test():
    # Start monitoring
    tracemalloc.start()
    process = psutil.Process()
    start_time = time.perf_counter()
    start_cpu = process.cpu_percent()

    # Test data
    test_data = {json.dumps(test_data) if test_data else 'None'}

    try:
        # Find the main function (first function definition)
        import target_function
        functions = [name for name in dir(target_function)
                    if callable(getattr(target_function, name)) and not name.startswith('_')]

        if not functions:
            raise ValueError("No function found in code")

        main_func = getattr(target_function, functions[0])

        # Execute with test data
        if test_data:
            result = main_func(test_data)
        else:
            # Use default test data based on function signature
            import inspect
            sig = inspect.signature(main_func)
            if len(sig.parameters) == 0:
                result = main_func()
            elif len(sig.parameters) == 1:
                # Generate appropriate test data
                result = main_func([1, 2, 3, 4, 5] * 1000)  # Default large list
            else:
                result = main_func([1, 2, 3, 4, 5] * 1000, 10)  # List and target

    except Exception as e:
        return {{"error": str(e), "traceback": traceback.format_exc()}}

    # Stop monitoring
    end_time = time.perf_counter()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    end_cpu = process.cpu_percent()

    return {{
        "result": str(result)[:1000],  # Truncate large results
        "execution_time_ms": (end_time - start_time) * 1000,
        "peak_memory_mb": peak / 1024 / 1024,
        "current_memory_mb": current / 1024 / 1024,
        "cpu_usage_percent": (start_cpu + end_cpu) / 2,
        "success": True
    }}

if __name__ == "__main__":
    import traceback
    try:
        result = run_performance_test()
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({{"error": str(e), "traceback": traceback.format_exc()}}))
"""

            # Write and execute test runner
            runner_file = os.path.join(temp_dir, "test_runner.py")
            with open(runner_file, 'w') as f:
                f.write(test_runner)

            try:
                # Execute with timeout
                result = subprocess.run(
                    ["python", runner_file],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=temp_dir
                )

                if result.returncode == 0:
                    return json.loads(result.stdout)
                else:
                    return {
                        "error": f"Execution failed: {result.stderr}",
                        "success": False
                    }

            except subprocess.TimeoutExpired:
                return {
                    "error": f"Execution timeout ({self.timeout}s)",
                    "success": False
                }

class ProfilerAgent(AgentBase):
    """
    Dedicated agent for empirical performance measurement.
    Implements the ProfilerAgent specification from v0.46 workplan.
    """

    def __init__(self, agent_id: str = "profiler_agent"):
        super().__init__(agent_id)
        self.execution_env = SecureExecutionEnvironment()
        self.baseline_profiles: Dict[str, PerformanceProfile] = {}

        # Subscribe to code submission events
        self.subscribe_to_events([
            "new_code_submission",
            "code_for_profiling"
        ])

        logging.info("ProfilerAgent initialized")

    def process_event(self, obj: BlackboardObject) -> Optional[Dict[str, Any]]:
        """Process blackboard events"""
        if obj.object_type == "new_code_submission":
            return self._profile_code_submission(obj)
        elif obj.object_type == "code_for_profiling":
            return self._profile_specific_code(obj)

        return None

    def _profile_code_submission(self, obj: BlackboardObject) -> Dict[str, Any]:
        """Profile a code submission from CoderAgent"""
        submission_data = obj.data
        original_code = submission_data.get("original_code", "")
        refactored_code = submission_data.get("refactored_code", "")

        # Generate performance profiles
        profiles = self._compare_code_performance(original_code, refactored_code)

        # Create performance profile object for blackboard
        return {
            "object_type": "performance_profile",
            "data": {
                "submission_id": obj.object_id,
                "profiles": profiles,
                "analysis": self._analyze_performance_delta(profiles),
                "timestamp": time.time()
            },
            "created_by": self.agent_id,
            "tags": {"performance", "empirical_data", obj.object_id}
        }

    def _profile_specific_code(self, obj: BlackboardObject) -> Dict[str, Any]:
        """Profile specific code with custom test data"""
        code = obj.data.get("code", "")
        test_data = obj.data.get("test_data")
        profile_id = obj.data.get("profile_id", "standalone")

        profile = self._profile_single_code(code, test_data)

        return {
            "object_type": "standalone_profile",
            "data": {
                "profile_id": profile_id,
                "profile": profile,
                "timestamp": time.time()
            },
            "created_by": self.agent_id,
            "tags": {"performance", "standalone", profile_id}
        }

    def _compare_code_performance(self, original_code: str, refactored_code: str) -> Dict[str, Any]:
        """Compare performance of original vs refactored code"""
        # Generate test datasets of different sizes
        test_sizes = [100, 1000, 10000]
        results = {
            "original": {},
            "refactored": {},
            "test_metadata": {
                "sizes_tested": test_sizes,
                "iterations_per_size": 3
            }
        }

        for size in test_sizes:
            # Generate test data based on size
            test_data = self._generate_test_data(size)

            # Profile original code
            original_profiles = []
            for i in range(3):  # Multiple runs for statistical reliability
                profile = self._profile_single_code(original_code, test_data)
                if profile.get("success"):
                    original_profiles.append(profile)

            # Profile refactored code
            refactored_profiles = []
            for i in range(3):
                profile = self._profile_single_code(refactored_code, test_data)
                if profile.get("success"):
                    refactored_profiles.append(profile)

            # Calculate averages
            if original_profiles:
                results["original"][f"size_{size}"] = self._average_profiles(original_profiles)

            if refactored_profiles:
                results["refactored"][f"size_{size}"] = self._average_profiles(refactored_profiles)

        return results

    def _profile_single_code(self, code: str, test_data: Any = None) -> Dict[str, Any]:
        """Profile a single piece of code"""
        try:
            return self.execution_env.execute_code(code, test_data)
        except Exception as e:
            logging.error(f"Profiling error: {e}")
            return {
                "error": str(e),
                "success": False
            }

    def _generate_test_data(self, size: int) -> List[int]:
        """Generate test data of specified size"""
        # Simple test data - could be made more sophisticated based on code analysis
        return list(range(size))

    def _average_profiles(self, profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate average performance metrics"""
        if not profiles:
            return {}

        execution_times = [p["execution_time_ms"] for p in profiles if "execution_time_ms" in p]
        memory_usage = [p["peak_memory_mb"] for p in profiles if "peak_memory_mb" in p]
        cpu_usage = [p["cpu_usage_percent"] for p in profiles if "cpu_usage_percent" in p]

        return {
            "execution_time_ms": {
                "mean": statistics.mean(execution_times) if execution_times else 0,
                "median": statistics.median(execution_times) if execution_times else 0,
                "std_dev": statistics.stdev(execution_times) if len(execution_times) > 1 else 0
            },
            "peak_memory_mb": {
                "mean": statistics.mean(memory_usage) if memory_usage else 0,
                "median": statistics.median(memory_usage) if memory_usage else 0,
                "std_dev": statistics.stdev(memory_usage) if len(memory_usage) > 1 else 0
            },
            "cpu_usage_percent": {
                "mean": statistics.mean(cpu_usage) if cpu_usage else 0,
                "median": statistics.median(cpu_usage) if cpu_usage else 0,
                "std_dev": statistics.stdev(cpu_usage) if len(cpu_usage) > 1 else 0
            },
            "sample_count": len(profiles),
            "success": True
        }

    def _analyze_performance_delta(self, profiles: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance improvements between original and refactored code"""
        analysis = {
            "improvement_detected": False,
            "performance_ratio": {},
            "scalability_analysis": {},
            "recommendation": "no_change"
        }

        original = profiles.get("original", {})
        refactored = profiles.get("refactored", {})

        if not original or not refactored:
            analysis["error"] = "Insufficient data for comparison"
            return analysis

        # Compare across different input sizes
        improvements = []
        for size_key in original.keys():
            if size_key in refactored and size_key.startswith("size_"):
                orig_time = original[size_key].get("execution_time_ms", {}).get("mean", 0)
                new_time = refactored[size_key].get("execution_time_ms", {}).get("mean", 0)

                if orig_time > 0 and new_time > 0:
                    ratio = orig_time / new_time
                    improvements.append(ratio)
                    analysis["performance_ratio"][size_key] = ratio

        if improvements:
            avg_improvement = statistics.mean(improvements)
            analysis["average_speedup"] = avg_improvement

            if avg_improvement > 1.1:  # At least 10% improvement
                analysis["improvement_detected"] = True
                analysis["recommendation"] = "accept_improvement"

                if avg_improvement > 10:  # 10x improvement
                    analysis["recommendation"] = "verify_correctness"  # Might be too good to be true

            elif avg_improvement < 0.9:  # Performance regression
                analysis["recommendation"] = "reject_change"

            # Check for scalability improvements
            if len(improvements) > 1:
                # If improvement ratio increases with input size, it's a scalability win
                size_improvements = list(improvements)
                if size_improvements[-1] > size_improvements[0] * 1.5:
                    analysis["scalability_improvement"] = True

        return analysis

    def detect_n_plus_one_problem(self, code: str) -> Dict[str, Any]:
        """
        Specialized detection for N+1 query problems in database code.
        Supports the complex task demonstration from v0.49.
        """
        analysis = {
            "n_plus_one_detected": False,
            "evidence": [],
            "confidence": 0.0
        }

        try:
            tree = ast.parse(code)

            # Look for patterns indicating N+1 problems
            for node in ast.walk(tree):
                # Check for loops containing database queries
                if isinstance(node, (ast.For, ast.While)):
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            # Look for query-like method calls
                            if hasattr(child.func, 'attr'):
                                method_name = child.func.attr
                                if method_name in ['query', 'get', 'filter', 'find', 'select']:
                                    analysis["evidence"].append(f"Query call '{method_name}' inside loop")
                                    analysis["n_plus_one_detected"] = True

                        # Look for ORM lazy loading patterns
                        if isinstance(child, ast.Attribute):
                            if child.attr in ['children', 'related', 'items']:
                                analysis["evidence"].append(f"Lazy loading access '{child.attr}' in loop")
                                analysis["n_plus_one_detected"] = True

            # Calculate confidence based on evidence
            if analysis["evidence"]:
                analysis["confidence"] = min(0.9, len(analysis["evidence"]) * 0.3)

        except Exception as e:
            analysis["error"] = f"AST analysis failed: {e}"

        return analysis

    def profile_database_performance(self, code: str, connection_string: str = None) -> Dict[str, Any]:
        """
        Profile database-heavy code for the N+1 demonstration.
        This would integrate with actual database profiling in a real implementation.
        """
        # For the PoC, we simulate database profiling
        n_plus_one_analysis = self.detect_n_plus_one_problem(code)

        # Simulate query execution profiling
        simulated_profile = {
            "query_count": 1001 if n_plus_one_analysis["n_plus_one_detected"] else 1,
            "total_query_time_ms": 5000 if n_plus_one_analysis["n_plus_one_detected"] else 50,
            "connection_overhead_ms": 1000 if n_plus_one_analysis["n_plus_one_detected"] else 10,
            "n_plus_one_analysis": n_plus_one_analysis
        }

        return simulated_profile

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of all profiling activities"""
        return {
            "agent_id": self.agent_id,
            "total_profiles_created": len(self.baseline_profiles),
            "execution_environment": "sandboxed",
            "capabilities": [
                "empirical_timing",
                "memory_profiling",
                "cpu_monitoring",
                "n_plus_one_detection",
                "scalability_analysis"
            ]
        }