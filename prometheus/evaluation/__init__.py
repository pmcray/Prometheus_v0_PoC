"""
Evaluation module for Prometheus

Provides comprehensive evaluation and benchmarking tools:
- ELO rating calculation
- Tournament management
- Statistical significance testing
- Performance analysis
"""

from prometheus.evaluation.benchmark import (
    ELOCalculator,
    GoEvaluator,
    PerformanceAnalyzer
)

__all__ = [
    'ELOCalculator',
    'GoEvaluator',
    'PerformanceAnalyzer'
]
