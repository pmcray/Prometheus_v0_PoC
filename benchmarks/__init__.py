"""
Prometheus-Bench-v0.1: Internal Benchmark Suite for Self-Modification
Comprehensive evaluation suite for measuring agent capabilities
"""

from .prometheus_bench_v0_1 import PrometheusBenchV01
from .benchmark_runner import BenchmarkRunner
from .benchmark_results import BenchmarkResults

__version__ = "0.1.0"
__all__ = ["PrometheusBenchV01", "BenchmarkRunner", "BenchmarkResults"]