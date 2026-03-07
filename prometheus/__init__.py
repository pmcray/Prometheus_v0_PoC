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

__version__ = "0.82"

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

# WP23: Policy Distillation — Student Policy Compression
from prometheus.wp23_policy_distillation import (
    DistillationRecord,
    StudentPolicy,
    PolicyDistiller,
    DistilledCRLS,
    verify_wp23_exit_criteria,
)

# WP24: Ensemble Disagreement & Uncertainty-Aware Action Selection
from prometheus.wp24_ensemble_uncertainty import (
    EnsembleRecord,
    EnsembleDistiller,
    EnsembleCRLS,
    verify_wp24_exit_criteria,
)

# WP25: Forgetting Detection & EWC Regularisation
from prometheus.wp25_ewc_forgetting import (
    ForgettingRecord,
    EWCStudentPolicy,
    ForgettingDetector,
    EWCEnsembleDistiller,
    EWCEnsembleCRLS,
    verify_wp25_exit_criteria,
)

# WP26: Hierarchical Task Decomposition
from prometheus.wp26_hierarchical_decomp import (
    SubtaskType,
    SubtaskRecord,
    DecompositionRecord,
    TaskDecomposer,
    HierarchicalCRLS,
    verify_wp26_exit_criteria,
)

# WP27: Formal Invariant Verification
from prometheus.wp27_formal_invariants import (
    EnforcementMode,
    InvariantSpec,
    InvariantCheckResult,
    InvariantRecord,
    InvariantRegistry,
    InvariantGuard,
    InvariantCRLS,
    make_prob_floor_invariant,
    make_entropy_floor_invariant,
    make_upward_rate_bounds_invariant,
    make_acc_drop_guard_invariant,
    make_default_registry,
    verify_wp27_exit_criteria,
)

# WP28: Cross-Domain Student Transfer
from prometheus.wp28_cross_domain_transfer import (
    TransferRecord,
    DomainAdapter,
    TransferStudentPolicy,
    CrossDomainDistiller,
    TransferCRLS,
    verify_wp28_exit_criteria,
)

# WP29: Self-Play Synthesis Tournament
from prometheus.wp29_self_play_tournament import (
    TournamentRecord,
    TournamentCRLS,
    SelfPlayTournament,
    verify_wp29_exit_criteria,
)

# WP30: Causal World Model — Latent Transition Learning
from prometheus.wp30_causal_world_model import (
    ReplayBuffer,
    LatentTransitionModel,
    RolloutSource,
    WorldModelRollout,
    WorldModelRecord,
    WorldModelCRLS,
    verify_wp30_exit_criteria,
)

# WP31: Curriculum Generator — Adaptive Difficulty Scheduling
from prometheus.wp31_curriculum_generator import (
    PuzzleCategory,
    CurriculumScheduler,
    CurriculumRecord,
    CurriculumCRLS,
    verify_wp31_exit_criteria,
)

# WP32: Evolutionary Code Search
from prometheus.wp32_evolutionary_search import (
    MutationOperator,
    CrossoverOperator,
    FitnessEvaluator,
    EvolutionRecord,
    EvolutionReport,
    EvolutionarySearcher,
    verify_wp32_exit_criteria,
)

# WP33: Formal Domain Adaptation — Lean Theorem Proving
from prometheus.wp33_lean_theorem_proving import (
    TheoremDifficulty,
    TheoremCurriculum,
    ProofAttemptRecord,
    ProofSession,
    TheoremProvingReport,
    TheoremProver,
    verify_wp33_exit_criteria,
)

# WP34: Multi-Step Proof Tree Search
from prometheus.wp34_proof_tree_search import (
    TacticPrior,
    ProofNode,
    ProofTree,
    ProofSearchRecord,
    ProofTreeSearcher,
    verify_wp34_exit_criteria,
)

# WP35: Meta-Learning from Failure
from prometheus.wp35_failure_memory import (
    ErrorClassifier,
    FailureRecord,
    FailureMemory,
    ConditionedSearcher,
    verify_wp35_exit_criteria,
)

# WP36: Transformer-Based Policy Head
from prometheus.wp36_transformer_policy import (
    TransformerTokeniser,
    MultiHeadSelfAttention,
    TransformerBlock,
    TransformerPolicyHead,
    SequenceBuffer,
    TransformerRecord,
    TransformerCRLS,
    verify_wp36_exit_criteria,
)

# WP37: Online ELO & Performance Registry
from prometheus.wp37_elo_registry import (
    GlickoRating,
    ELOEntry,
    ELORegistry,
    DomainRegistry,
    ZPDRatingBridge,
    glicko2_update,
    verify_wp37_exit_criteria,
)

# WP38: Analogical Reasoning Engine
from prometheus.wp38_analogy_engine import (
    RelationalGraph,
    Relation,
    StructureMapper,
    AnalogyScore,
    AnalogyMap,
    TransferPolicy,
    AnalogyRecord,
    AnalogyEngine,
    make_chess_graph,
    make_go_graph,
    make_synthesis_graph,
    verify_wp38_exit_criteria,
)

# WP39: Web API & Real-Time Monitoring Dashboard
from prometheus.wp39_web_api import (
    APIMetrics,
    LiveEventStream,
    PrometheusAPI,
    DashboardRenderer,
    PrometheusAPIServer,
    verify_wp39_exit_criteria,
)

# WP40: Learned Safety Model — Neural Gödelian Governor
from prometheus.wp40_learned_safety import (
    ModificationRecord,
    SafetyDataset,
    SafetyClassifier,
    LearnedSafetyGuard,
    SafetyDecisionRecord,
    LearnedSafetyCRLS,
    verify_wp40_exit_criteria,
)

# WP41: Strange Loop Visualiser — Tangled Hierarchy Made Observable
from prometheus.wp41_strange_loop_visualiser import (
    HierarchyLevel,
    CrossLevelSignal,
    StrangeLoopTrace,
    StrangeLoopSimulator,
    LoopReport,
    run_loop,
    verify_wp41_exit_criteria,
)

# WP42: Gödel Sentence Generator — Incompleteness Made Executable
from prometheus.wp42_godel_sentence import (
    SafetyVerdict,
    ProductionRule,
    FormalSystem,
    GodelSentence,
    GodelSafetyInterpreter,
    InterpretationRecord,
    GodelProbeResult,
    GodelProbe,
    make_default_rules,
    verify_wp42_exit_criteria,
)

# WP44: Ultraintelligence Trajectory — Testing Good (1965) Empirically
from prometheus.wp44_ultraintelligence_trajectory import (
    TrajectoryPoint,
    TrajectoryFit,
    IntelligenceExplosionTest,
    CRLSSimulator,
    TrajectoryAnalyser,
    TrajectoryReport,
    fit_linear,
    fit_exponential,
    fit_logistic,
    run_explosion_test,
    verify_wp44_exit_criteria,
)

# WP43: Tangled Hierarchy Detector — TanglingScore (Hofstadter)
from prometheus.wp43_tangled_hierarchy import (
    HierarchyClassification,
    TanglingWindow,
    TanglingTimeSeries,
    TanglingReport,
    TanglingAnalyser,
    run_tangling_demo,
    verify_wp43_exit_criteria,
)

# WP46: Corrigibility Under Self-Improvement (Good 1965)
from prometheus.wp46_corrigibility import (
    OverrideSignal,
    OverrideQueue,
    Checkpoint,
    InterruptRecord,
    CorrigibleSimulator,
    CorrigibilityReport,
    run_corrigibility_demo,
    verify_wp46_exit_criteria,
)

# WP47: Recursive Self-Description (Hofstadter — I Am a Strange Loop)
from prometheus.wp47_self_description import (
    ModuleNode,
    DependencyGraph,
    SelfDescription,
    VerificationResult,
    SelfVerifier,
    SelfDescriptionReport,
    build_self_description,
    verify_wp47_exit_criteria,
)

# WP49: Multi-Agent Strange Loop — Theory of Mind Tournament
from prometheus.wp49_theory_of_mind import (
    PolicyModel,
    MindReadingAgent,
    ToMRecord,
    TheoryOfMindTournament,
    ToMReport,
    run_tom_tournament,
    verify_wp49_exit_criteria,
)

# WP50: Halt Problem as Safety Criterion (Turing 1936 / Good 1965)
from prometheus.wp50_halt_problem import (
    DivergenceEvent,
    DepthResult,
    HaltReport,
    RecursionDepthSimulator,
    run_halt_experiment,
    verify_wp50_exit_criteria,
)

# WP51: Distributed CRLS Stack (I.J. Good — Ultraparallel Architecture)
from prometheus.wp51_distributed_crls import (
    AgentState,
    FederatedGenePool,
    ConsensusPolicy,
    DistributedAgent,
    DistributedCRLSCoordinator,
    DistributedRoundRecord,
    DistributedReport,
    run_distributed_demo,
    verify_wp51_exit_criteria,
)

# WP52: CRLS Convergence Proof (Lyapunov / Schmidhuber Gödel Machines)
from prometheus.wp52_crls_convergence import (
    ConvergenceWarning,
    LyapunovWindow,
    LyapunovMonitor,
    ProofStep,
    ProofSketch,
    LyapunovBound,
    CheckpointRecord,
    RevertEvent,
    ConvergenceCertifier,
    ConvergenceReport,
    build_proof_sketch,
    run_convergence_demo,
    verify_wp52_exit_criteria,
)

# WP53: Meta-Analogy Transfer (Hofstadter — analogy about analogies)
from prometheus.wp53_meta_analogy import (
    AnalogyRecord,
    AnalogyRegistry,
    MetaAnalogyPredictor,
    SelectiveTransferGate,
    MetaAnalogySimulator,
    MetaAnalogyReport,
    run_meta_analogy_demo,
    verify_wp53_exit_criteria,
)

# WP54: Curriculum Meta-Learning (Bengio et al. 2009)
from prometheus.wp54_curriculum_meta import (
    PacingFunction,
    CurriculumDesign,
    CurriculumEvaluator,
    CurriculumLeaderboard,
    CurriculumMetaLearner,
    CurriculumMetaReport,
    run_curriculum_meta_demo,
    verify_wp54_exit_criteria,
)

# WP55: Pareto Safety Optimisation Under Uncertainty (NSGA-II / Conformal)
from prometheus.wp55_pareto_safety import (
    SafetyPerformancePoint,
    ParetoFront,
    UncertaintyAwareParetoSearcher,
    AdaptiveWeightScheduler,
    WeightRecord,
    ParetoSafetyReport,
    run_pareto_safety_demo,
    verify_wp55_exit_criteria,
)

# WP56: Strange-Loop Complexity Theorem (Hofstadter empirical test)
from prometheus.wp56_strange_loop_theorem import (
    LoopDepthConfig,
    LoopPerformanceRecord,
    HofstadterCorrelationTest,
    LoopComplexityReport,
    LoopComplexityExperiment,
    run_loop_complexity_demo,
    verify_wp56_exit_criteria,
)

# WP57: Gödel Machine (Schmidhuber 2007 — Provably Safe Self-Modification)
from prometheus.wp57_godel_machine import (
    ProofStatus,
    PatchCategory,
    ProposedPatch,
    ProofStep as GodelProofStep,
    ProofAttemptResult,
    AuditEntry,
    GenerationRecord as GodelGenerationRecord,
    ModificationProver,
    ProofBudgetManager,
    SelfModificationAuditLog,
    GodelMachine,
    GodelMachineReport,
    run_godel_machine_demo,
    verify_wp57_exit_criteria,
)

# WP58: Intelligence Explosion Rate Bound (Good 1965 — soft takeoff)
from prometheus.wp58_explosion_rate_bound import (
    ImprovementRateTimeSeries,
    RateModelType,
    RateModelFit,
    DiminishingReturnsDetector,
    DiminishingReturnsEvent,
    SaturationForecast,
    ExplosionRateBound,
    ExplosionRateReport,
    ExplosionRateExperiment,
    run_explosion_rate_demo,
    verify_wp58_exit_criteria,
)

# WP59: Emergent Goal Formation (Schmidhuber curiosity / Klyubin empowerment)
from prometheus.wp59_emergent_goals import (
    GoalFeatureVector,
    IntrinsicRewardSignal,
    EmergentGoal,
    EmergentGoalRegistry,
    EmergentGoalFormer,
    EmergentGoalReport,
    run_emergent_goals_demo,
    verify_wp59_exit_criteria,
)

# WP60: Value Alignment Under Self-Modification (Yudkowsky CoEV / Gödel)
from prometheus.wp60_alignment_preservation import (
    ValueWeightVector,
    ValueDriftEvent,
    ValueDriftDetector,
    AlignmentCertificate,
    ProofOutcome,
    AlignmentInvariantChecker,
    AlignmentProofAttempt,
    GenerationalAlignmentRecord,
    AlignmentPreservationReport,
    AlignmentPreservationExperiment,
    run_alignment_preservation_demo,
    verify_wp60_exit_criteria,
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
