"""
Prometheus: Recursive Self-Improvement AI System

This package provides modules for building adaptive AI agents
with online learning and meta-level reasoning capabilities.

Key modules:
- data: Data generators for pattern recognition tasks
- models: Neural network architectures (Static and Prometheus agents)
- training: Training loops and self-play utilities
- visualization: Plotting and visualization functions
- metrics: Performance measurement and statistical analysis
- safety: Gödelian safety checks for self-modification
- environments: Game environments (Chess, etc.)
"""

__version__ = "0.69"

# Optional imports - only load if explicitly requested
# This prevents import errors from breaking the entire package

def _lazy_import(module_name, object_name):
    """Lazy import helper to avoid loading all modules at once."""
    def _import():
        module = __import__(f'prometheus.{module_name}', fromlist=[object_name])
        return getattr(module, object_name)
    return _import

# Legacy imports (commented out to prevent automatic loading)
# Uncomment if needed for backward compatibility
# from .coder import CoderAgent
# from .corrector import CorrectorAgent
# from .evaluator import EvaluatorAgent
# from .gene_archive import GeneArchive
# from .knowledge_agent import KnowledgeAgent
# from .mcs import MCSSupervisor
# from .performance_logger import PerformanceLogger
# from .planner import PlannerAgent
# from .strategy_archive import StrategyArchive
# from .system_state import SystemState, ArchitectureState
# from .toy_chemistry_sim import ToyChemistrySim
# from .agent_templates import HypothesisGenerator, DataAnalyzer, CodeImplementer
# from .brain_map import BrainMap
# from .tool_benchmark import run_tool_benchmark
