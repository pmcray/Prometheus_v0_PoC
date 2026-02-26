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

__version__ = "0.71"

# WP17: CRLS Synthesis Closure
from prometheus.wp17_crls_synthesis import (
    CRLSSynthesiser,
    GoTacticalCRLS,
    SynthesisAction,
    SynthesisRecord,
    verify_wp17_exit_criteria,
)

# WP18: Analogy Engine MVP — Cross-Domain Transfer
from prometheus.wp18_analogy_engine import (
    TacticSignature,
    StructuralAnalogy,
    CrossDomainAnalogyMap,
    TransferBootstrapper,
    GoChessTacticRegistry,
    GoChessCRLS,
    verify_wp18_exit_criteria,
)

# WP19: Causal Action Evaluator — Potential-Outcomes Action Selection
from prometheus.wp19_causal_evaluator import (
    ActionOutcomeTable,
    ATEEstimate,
    CausalRecommendation,
    CausalActionEvaluator,
    CausalAnalogyAuditor,
    CausalCRLS,
    verify_wp19_exit_criteria,
)

# WP20: Temporal Synthesis Planner — K-step Rollout Planning
from prometheus.wp20_temporal_planner import (
    SynthesisStateSnapshot,
    TrajectoryTransition,
    SynthesisTrajectoryModel,
    RolloutResult,
    RolloutPlanner,
    TemporalCRLS,
    verify_wp20_exit_criteria,
)

# WP21: Meta-Gradient Adaptation — Hyperparameter Self-Optimisation
from prometheus.wp21_meta_gradient import (
    MetaParams,
    MetaGradStep,
    MetaGradientOptimiser,
    MetaGradientCRLS,
    verify_wp21_exit_criteria,
)

# WP22: Multi-Armed Bandit Exploration Policy
from prometheus.wp22_bandit_exploration import (
    BanditMode,
    ExplorationRecord,
    BanditPolicy,
    BanditCRLS,
    verify_wp22_exit_criteria,
)

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
