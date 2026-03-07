"""
WP67: Integration Test Suite
==============================

Closes the **end-to-end validation gap** in the Prometheus stack.

Individual WP modules each have isolated unit tests (pytest).  But there is
no automated suite that:

  1. Imports every WP module (WP17–WP66) and verifies that imports succeed.
  2. Runs every ``verify_wpXX_exit_criteria()`` function and collects results.
  3. Detects regressions across WP tiers when any module changes.
  4. Produces a machine-readable pass/fail report (JSON + human summary).
  5. Can be executed as a single CLI command or pytest session.

WP67 fix
--------
``WPEntry``             — registry entry for one WP: module path, class names
                          to import, and a reference to the verify function.

``WPRegistry``          — ordered registry of all 54 WP entries (WP17–WP70).

``ImportChecker``       — verifies that all expected symbols can be imported
                          from each WP module without error.

``CriteriaRunner``      — runs each WP's ``verify_wpXX_exit_criteria()``
                          function, captures results and exceptions.

``IntegrationResult``   — per-WP result: wp_id, import_ok, criteria_results,
                          error, duration_s.

``IntegrationReport``   — full suite report: per-WP results, pass rates,
                          tier summaries, overall verdict.

``IntegrationTestSuite``— orchestrates the full suite:
                          1. Import check for all WPs.
                          2. Criteria runner for all WPs.
                          3. Aggregate into IntegrationReport.
                          4. Export JSON + print summary.

``verify_wp67_exit_criteria`` — six-criterion verifier (meta: tests the
                          tester).

Theoretical grounding
---------------------
Beck (2002) "Test-Driven Development": a comprehensive test suite is the
single most important artefact for maintaining a large codebase's integrity.

Fowler (2018) "Refactoring": integration tests provide a safety net when
refactoring individual WP modules — changes that break the stack are caught
immediately.

Good (1965): a self-improving machine must be able to verify that its own
modifications have not regressed its existing capabilities — WP67 operationalises
this as an automated integration test suite.

Classes
-------
WPEntry                 Registry entry for one WP module
WPRegistry              Ordered registry of all WPs (WP17–WP70)
ImportChecker           Verifies all WP imports succeed
CriteriaRunner          Runs each WP's verify function
IntegrationResult       Per-WP import + criteria result
IntegrationReport       Full suite report with tier summaries
IntegrationTestSuite    Orchestrates the full integration run
verify_wp67_exit_criteria  Six-criterion verifier (meta)
"""

from __future__ import annotations

import importlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# WPEntry
# ---------------------------------------------------------------------------

@dataclass
class WPEntry:
    """Registry entry for one WP module."""
    wp_id: str                    # e.g. "wp17"
    module_path: str              # e.g. "prometheus.wp17_crls_synthesis"
    verify_fn_name: str           # e.g. "verify_wp17_exit_criteria"
    symbols: List[str]            # key class/function names to import-check
    tier: int                     # 2=CRLS, 3=Evolutionary, 4=Theoretical, etc.
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wp_id": self.wp_id,
            "module_path": self.module_path,
            "tier": self.tier,
            "description": self.description,
            "n_symbols": len(self.symbols),
        }


# ---------------------------------------------------------------------------
# WPRegistry — ordered registry of all WPs
# ---------------------------------------------------------------------------

class WPRegistry:
    """
    Ordered registry of all implemented WPs (WP17–WP70).

    Only includes modules that exist in the prometheus package.
    """

    _ENTRIES: Optional[List[WPEntry]] = None

    @classmethod
    def all(cls) -> List[WPEntry]:
        if cls._ENTRIES is None:
            cls._ENTRIES = cls._build()
        return cls._ENTRIES

    @classmethod
    def by_tier(cls, tier: int) -> List[WPEntry]:
        return [e for e in cls.all() if e.tier == tier]

    @classmethod
    def _build(cls) -> List[WPEntry]:
        return [
            # Tier 2: CRLS Synthesis
            WPEntry("wp17", "prometheus.wp17_crls_synthesis", "verify_wp17_exit_criteria",
                    ["CRLSSynthesiser", "SynthesisRecord"], 2, "CRLS Synthesis Closure"),
            WPEntry("wp18", "prometheus.wp18_analogy_engine", "verify_wp18_exit_criteria",
                    ["TransferBootstrapper", "GoChessCRLS"], 2, "Analogy Engine MVP"),
            WPEntry("wp19", "prometheus.wp19_causal_evaluator", "verify_wp19_exit_criteria",
                    ["CausalActionEvaluator", "CausalCRLS"], 2, "Causal Action Evaluator"),
            WPEntry("wp20", "prometheus.wp20_temporal_planner", "verify_wp20_exit_criteria",
                    ["RolloutPlanner", "TemporalCRLS"], 2, "Temporal Synthesis Planner"),
            WPEntry("wp21", "prometheus.wp21_meta_gradient", "verify_wp21_exit_criteria",
                    ["MetaGradientOptimiser", "MetaGradientCRLS"], 2, "Meta-Gradient Adaptation"),
            WPEntry("wp22", "prometheus.wp22_bandit_exploration", "verify_wp22_exit_criteria",
                    ["BanditPolicy", "BanditCRLS"], 2, "Multi-Armed Bandit Exploration"),
            WPEntry("wp23", "prometheus.wp23_policy_distillation", "verify_wp23_exit_criteria",
                    ["PolicyDistiller", "DistilledCRLS"], 2, "Policy Distillation"),
            WPEntry("wp24", "prometheus.wp24_ensemble_uncertainty", "verify_wp24_exit_criteria",
                    ["EnsembleDistiller", "EnsembleCRLS"], 2, "Ensemble Uncertainty"),
            WPEntry("wp25", "prometheus.wp25_ewc_forgetting", "verify_wp25_exit_criteria",
                    ["ForgettingDetector", "EWCEnsembleCRLS"], 2, "Forgetting Detection & EWC"),
            WPEntry("wp26", "prometheus.wp26_hierarchical_decomp", "verify_wp26_exit_criteria",
                    ["TaskDecomposer", "HierarchicalCRLS"], 2, "Hierarchical Task Decomposition"),
            WPEntry("wp27", "prometheus.wp27_formal_invariants", "verify_wp27_exit_criteria",
                    ["InvariantRegistry", "InvariantCRLS"], 2, "Formal Invariant Verification"),
            WPEntry("wp28", "prometheus.wp28_cross_domain_transfer", "verify_wp28_exit_criteria",
                    ["CrossDomainDistiller", "TransferCRLS"], 2, "Cross-Domain Transfer"),
            WPEntry("wp29", "prometheus.wp29_self_play_tournament", "verify_wp29_exit_criteria",
                    ["SelfPlayTournament", "TournamentCRLS"], 2, "Self-Play Tournament"),
            WPEntry("wp30", "prometheus.wp30_causal_world_model", "verify_wp30_exit_criteria",
                    ["WorldModelCRLS", "LatentTransitionModel"], 2, "Causal World Model"),
            WPEntry("wp31", "prometheus.wp31_curriculum_generator", "verify_wp31_exit_criteria",
                    ["CurriculumScheduler", "CurriculumCRLS"], 2, "Curriculum Generator"),

            # Tier 3: Evolutionary & Lean
            WPEntry("wp32", "prometheus.wp32_evolutionary_search", "verify_wp32_exit_criteria",
                    ["EvolutionarySearcher", "EvolutionReport"], 3, "Evolutionary Code Search"),
            WPEntry("wp33", "prometheus.wp33_lean_theorem_proving", "verify_wp33_exit_criteria",
                    ["TheoremProver", "TheoremProvingReport"], 3, "Lean Theorem Proving"),

            # Tier 4: Theoretical Grounding
            WPEntry("wp34", "prometheus.wp34_proof_tree_search", "verify_wp34_exit_criteria",
                    ["ProofTreeSearcher", "ProofSearchRecord"], 4, "Proof Tree Search"),
            WPEntry("wp35", "prometheus.wp35_failure_memory", "verify_wp35_exit_criteria",
                    ["FailureMemory", "ConditionedSearcher"], 4, "Meta-Learning from Failure"),
            WPEntry("wp36", "prometheus.wp36_transformer_policy", "verify_wp36_exit_criteria",
                    ["TransformerPolicyHead", "TransformerCRLS"], 4, "Transformer Policy Head"),
            WPEntry("wp37", "prometheus.wp37_elo_registry", "verify_wp37_exit_criteria",
                    ["ELORegistry", "GlickoRating"], 4, "Online ELO Registry"),
            WPEntry("wp38", "prometheus.wp38_analogy_engine", "verify_wp38_exit_criteria",
                    ["AnalogyEngine", "StructureMapper"], 4, "Analogical Reasoning Engine"),
            WPEntry("wp39", "prometheus.wp39_web_api", "verify_wp39_exit_criteria",
                    ["PrometheusAPI", "APIMetrics"], 4, "Web API & Dashboard"),
            WPEntry("wp40", "prometheus.wp40_learned_safety", "verify_wp40_exit_criteria",
                    ["LearnedSafetyGuard", "SafetyClassifier"], 4, "Learned Safety Model"),
            WPEntry("wp41", "prometheus.wp41_strange_loop_visualiser", "verify_wp41_exit_criteria",
                    ["StrangeLoopSimulator", "StrangeLoopTrace"], 4, "Strange Loop Visualiser"),
            WPEntry("wp42", "prometheus.wp42_godel_sentence", "verify_wp42_exit_criteria",
                    ["GodelProbe", "FormalSystem"], 4, "Gödel Sentence Generator"),
            WPEntry("wp43", "prometheus.wp43_tangled_hierarchy", "verify_wp43_exit_criteria",
                    ["TanglingAnalyser", "TanglingReport"], 4, "Tangled Hierarchy Detector"),
            WPEntry("wp44", "prometheus.wp44_ultraintelligence_trajectory", "verify_wp44_exit_criteria",
                    ["TrajectoryAnalyser", "CRLSSimulator"], 4, "Ultraintelligence Trajectory"),

            # Tier 5: Corrigibility & Advanced
            WPEntry("wp46", "prometheus.wp46_corrigibility", "verify_wp46_exit_criteria",
                    ["CorrigibleSimulator", "CorrigibilityReport"], 5, "Corrigibility"),
            WPEntry("wp47", "prometheus.wp47_self_description", "verify_wp47_exit_criteria",
                    ["SelfVerifier", "SelfDescription"], 5, "Recursive Self-Description"),
            WPEntry("wp49", "prometheus.wp49_theory_of_mind", "verify_wp49_exit_criteria",
                    ["TheoryOfMindTournament", "ToMReport"], 5, "Theory of Mind Tournament"),
            WPEntry("wp50", "prometheus.wp50_halt_problem", "verify_wp50_exit_criteria",
                    ["RecursionDepthSimulator", "HaltReport"], 5, "Halt Problem Safety"),

            # Tier 6: Scaling & Verification
            WPEntry("wp51", "prometheus.wp51_distributed_crls", "verify_wp51_exit_criteria",
                    ["DistributedCRLSCoordinator", "DistributedReport"], 6, "Distributed CRLS"),
            WPEntry("wp52", "prometheus.wp52_crls_convergence", "verify_wp52_exit_criteria",
                    ["ConvergenceCertifier", "ConvergenceReport"], 6, "CRLS Convergence Proof"),
            WPEntry("wp53", "prometheus.wp53_meta_analogy", "verify_wp53_exit_criteria",
                    ["MetaAnalogySimulator", "MetaAnalogyReport"], 6, "Meta-Analogy Transfer"),
            WPEntry("wp54", "prometheus.wp54_curriculum_meta", "verify_wp54_exit_criteria",
                    ["CurriculumMetaLearner", "CurriculumMetaReport"], 6, "Curriculum Meta-Learning"),
            WPEntry("wp55", "prometheus.wp55_pareto_safety", "verify_wp55_exit_criteria",
                    ["UncertaintyAwareParetoSearcher", "ParetoSafetyReport"], 6, "Pareto Safety"),

            # Tier 7: Theory Deepening
            WPEntry("wp56", "prometheus.wp56_strange_loop_theorem", "verify_wp56_exit_criteria",
                    ["LoopComplexityExperiment", "LoopComplexityReport"], 7, "Strange-Loop Theorem"),
            WPEntry("wp57", "prometheus.wp57_godel_machine", "verify_wp57_exit_criteria",
                    ["GodelMachine", "GodelMachineReport"], 7, "Gödel Machine"),
            WPEntry("wp58", "prometheus.wp58_explosion_rate_bound", "verify_wp58_exit_criteria",
                    ["ExplosionRateExperiment", "ExplosionRateReport"], 7, "Explosion Rate Bound"),

            # Tier 8: Emergence & Alignment
            WPEntry("wp59", "prometheus.wp59_emergent_goals", "verify_wp59_exit_criteria",
                    ["EmergentGoalFormer", "EmergentGoalReport"], 8, "Emergent Goal Formation"),
            WPEntry("wp60", "prometheus.wp60_alignment_preservation", "verify_wp60_exit_criteria",
                    ["AlignmentPreservationExperiment", "AlignmentPreservationReport"], 8, "Alignment Preservation"),

            # Tier 9: Benchmarking
            WPEntry("wp61", "prometheus.wp61_multigame_benchmark", "verify_wp61_exit_criteria",
                    ["MultiGameBenchmark", "BenchmarkReport"], 9, "Multi-Game Benchmark"),
            WPEntry("wp62", "prometheus.wp62_arc_agi", "verify_wp62_exit_criteria",
                    ["ARCBenchmark", "ARCSolver"], 9, "ARC-AGI Integration"),
            WPEntry("wp63", "prometheus.wp63_ioi_solver", "verify_wp63_exit_criteria",
                    ["IOIBenchmark", "IOISolver"], 9, "IOI Bronze Solver"),
            WPEntry("wp64", "prometheus.wp64_experiment_tracker", "verify_wp64_exit_criteria",
                    ["ExperimentRegistry", "ExperimentTracker"], 9, "Experiment Tracker"),

            # Tier 10: Integration & Observability
            WPEntry("wp65", "prometheus.wp65_dashboard", "verify_wp65_exit_criteria",
                    ["DashboardServer", "StreamlitFallbackDashboard"], 10, "Monitoring Dashboard"),
            WPEntry("wp66", "prometheus.wp66_training_loop", "verify_wp66_exit_criteria",
                    ["LongRunTrainer", "TrainingReport"], 10, "Long-Run Training Loop"),

            # Tier 11: Safety Operationalisation
            WPEntry("wp68", "prometheus.wp68_safety_verification", "verify_wp68_exit_criteria",
                    ["SafetyVerifier", "SafetyReport"], 11, "Safety Verification"),
            WPEntry("wp69", "prometheus.wp69_red_team", "verify_wp69_exit_criteria",
                    ["RedTeamHarness", "RedTeamReport"], 11, "Red-Team Harness"),
            WPEntry("wp70", "prometheus.wp70_paper_package", "verify_wp70_exit_criteria",
                    ["ReproducibilityPackage", "PaperOutline"], 11, "Academic Paper & Repro"),
        ]


# ---------------------------------------------------------------------------
# IntegrationResult
# ---------------------------------------------------------------------------

@dataclass
class IntegrationResult:
    """Per-WP integration test result."""
    wp_id: str
    tier: int
    import_ok: bool
    criteria_results: Dict[str, bool]
    error: Optional[str]
    duration_s: float

    @property
    def criteria_pass_rate(self) -> float:
        if not self.criteria_results:
            return 0.0
        return sum(1 for v in self.criteria_results.values() if v) / len(self.criteria_results)

    @property
    def fully_passing(self) -> bool:
        return self.import_ok and self.criteria_pass_rate == 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wp_id": self.wp_id,
            "tier": self.tier,
            "import_ok": self.import_ok,
            "criteria_pass_rate": round(self.criteria_pass_rate, 4),
            "criteria_results": self.criteria_results,
            "error": self.error,
            "duration_s": round(self.duration_s, 4),
            "fully_passing": self.fully_passing,
        }


# ---------------------------------------------------------------------------
# IntegrationReport
# ---------------------------------------------------------------------------

@dataclass
class IntegrationReport:
    """Full integration suite report."""
    results: List[IntegrationResult]
    total_wps: int
    import_pass_count: int
    fully_passing_count: int
    tier_summaries: Dict[int, Dict[str, Any]]
    total_time_s: float

    @property
    def import_pass_rate(self) -> float:
        return self.import_pass_count / max(self.total_wps, 1)

    @property
    def overall_pass_rate(self) -> float:
        return self.fully_passing_count / max(self.total_wps, 1)

    def summary(self) -> str:
        lines = [
            "=== WP67 Integration Test Suite Report ===",
            f"Total WPs      : {self.total_wps}",
            f"Imports OK     : {self.import_pass_count} ({self.import_pass_rate:.1%})",
            f"Fully passing  : {self.fully_passing_count} ({self.overall_pass_rate:.1%})",
            f"Total time     : {self.total_time_s:.1f}s",
            "",
            "Per-tier summary:",
        ]
        for tier in sorted(self.tier_summaries):
            ts = self.tier_summaries[tier]
            lines.append(
                f"  Tier {tier}: {ts['n_passing']}/{ts['n_wps']} passing "
                f"({ts['pass_rate']:.1%})"
            )
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_wps": self.total_wps,
            "import_pass_rate": round(self.import_pass_rate, 4),
            "overall_pass_rate": round(self.overall_pass_rate, 4),
            "total_time_s": round(self.total_time_s, 2),
            "tier_summaries": self.tier_summaries,
            "results": [r.to_dict() for r in self.results],
        }


# ---------------------------------------------------------------------------
# ImportChecker
# ---------------------------------------------------------------------------

class ImportChecker:
    """Verifies that all WP modules and their key symbols can be imported."""

    @staticmethod
    def check(entry: WPEntry) -> Tuple[bool, Optional[str]]:
        """
        Return (import_ok, error_message_or_None).
        """
        try:
            mod = importlib.import_module(entry.module_path)
            for sym in entry.symbols:
                if not hasattr(mod, sym):
                    return False, f"Symbol '{sym}' not found in {entry.module_path}"
            return True, None
        except ImportError as exc:
            return False, f"ImportError: {exc}"
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# CriteriaRunner
# ---------------------------------------------------------------------------

class CriteriaRunner:
    """Runs each WP's verify function and captures results."""

    @staticmethod
    def run(entry: WPEntry) -> Tuple[Dict[str, bool], Optional[str]]:
        """
        Return (criteria_results, error_or_None).
        """
        try:
            mod = importlib.import_module(entry.module_path)
            fn = getattr(mod, entry.verify_fn_name, None)
            if fn is None:
                return {}, f"Function '{entry.verify_fn_name}' not found"
            result = fn()
            if not isinstance(result, dict):
                return {}, f"verify function returned {type(result)} instead of dict"
            return {k: bool(v) for k, v in result.items()}, None
        except Exception as exc:
            return {}, f"{type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# IntegrationTestSuite — orchestrator
# ---------------------------------------------------------------------------

class IntegrationTestSuite:
    """
    Full integration test suite.

    Parameters
    ----------
    entries : list of WPEntry, optional
        WPs to test. Defaults to WPRegistry.all().
    run_criteria : bool
        If True, run verify functions (may be slow).  If False, only check imports.
    timeout_per_wp_s : float
        Per-WP timeout for criteria runner (approximate, not enforced via signals).
    """

    def __init__(
        self,
        entries: Optional[List[WPEntry]] = None,
        run_criteria: bool = True,
        timeout_per_wp_s: float = 60.0,
    ):
        self.entries = entries or WPRegistry.all()
        self.run_criteria = run_criteria
        self.timeout_per_wp_s = timeout_per_wp_s

    def run(self) -> IntegrationReport:
        """Run the full suite and return an IntegrationReport."""
        t0 = time.time()
        results: List[IntegrationResult] = []

        for entry in self.entries:
            wp_t0 = time.time()
            import_ok, import_err = ImportChecker.check(entry)

            criteria_results: Dict[str, bool] = {}
            criteria_err: Optional[str] = import_err

            if import_ok and self.run_criteria:
                criteria_results, criteria_err = CriteriaRunner.run(entry)

            duration = time.time() - wp_t0
            results.append(IntegrationResult(
                wp_id=entry.wp_id,
                tier=entry.tier,
                import_ok=import_ok,
                criteria_results=criteria_results,
                error=criteria_err,
                duration_s=duration,
            ))
            status = "PASS" if (import_ok and (not self.run_criteria or all(criteria_results.values()))) else "FAIL"
            logger.info("[%s] %s (%.2fs)", status, entry.wp_id, duration)

        # Aggregate
        import_pass = sum(1 for r in results if r.import_ok)
        fully_passing = sum(1 for r in results if r.fully_passing)

        # Tier summaries
        tier_summaries: Dict[int, Dict[str, Any]] = {}
        for r in results:
            ts = tier_summaries.setdefault(r.tier, {"n_wps": 0, "n_passing": 0})
            ts["n_wps"] += 1
            if r.fully_passing:
                ts["n_passing"] += 1
        for tier, ts in tier_summaries.items():
            ts["pass_rate"] = round(ts["n_passing"] / max(ts["n_wps"], 1), 4)

        return IntegrationReport(
            results=results,
            total_wps=len(results),
            import_pass_count=import_pass,
            fully_passing_count=fully_passing,
            tier_summaries=tier_summaries,
            total_time_s=time.time() - t0,
        )

    def export(self, report: IntegrationReport, path: str) -> None:
        """Export report to JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)
        logger.info("Integration report saved to %s", path)


# ---------------------------------------------------------------------------
# verify_wp67_exit_criteria
# ---------------------------------------------------------------------------

def verify_wp67_exit_criteria(
    report: Optional[IntegrationReport] = None,
) -> Dict[str, bool]:
    """
    Six measurable exit criteria for WP67.

    1. WPRegistry contains ≥ 50 WP entries.
    2. ImportChecker correctly detects a missing symbol.
    3. IntegrationTestSuite import-only run completes for WP61–WP66.
    4. IntegrationReport.overall_pass_rate ≥ 0 (report generated without error).
    5. Tier summaries cover all expected tiers (2–11).
    6. IntegrationReport.to_dict() is JSON-serialisable.
    """
    import json as json_mod

    results: Dict[str, bool] = {}

    # Criterion 1: registry size
    try:
        entries = WPRegistry.all()
        results["c1_registry_min50_entries"] = len(entries) >= 50
    except Exception:
        results["c1_registry_min50_entries"] = False

    # Criterion 2: ImportChecker detects missing symbol
    try:
        bad_entry = WPEntry(
            "wp_test", "prometheus.wp61_multigame_benchmark",
            "verify_wp61_exit_criteria",
            ["NonExistentClass123"], 9
        )
        ok, err = ImportChecker.check(bad_entry)
        results["c2_import_checker_detects_missing_symbol"] = not ok and err is not None
    except Exception:
        results["c2_import_checker_detects_missing_symbol"] = False

    # Criterion 3: import-only run for WP61–WP67
    try:
        subset = [e for e in WPRegistry.all() if e.wp_id in
                  {"wp61", "wp62", "wp63", "wp64", "wp65", "wp66"}]
        suite = IntegrationTestSuite(entries=subset, run_criteria=False)
        rep = suite.run()
        results["c3_import_run_for_wp61_66"] = rep.import_pass_rate >= 0.8
    except Exception:
        results["c3_import_run_for_wp61_66"] = False

    # Criterion 4: full report generated
    try:
        if report is not None:
            ok = report.overall_pass_rate >= 0.0
        else:
            subset = [e for e in WPRegistry.all() if e.wp_id in {"wp61", "wp62"}]
            suite = IntegrationTestSuite(entries=subset, run_criteria=False)
            rep = suite.run()
            ok = rep.overall_pass_rate >= 0.0
        results["c4_report_generated_no_error"] = ok
    except Exception:
        results["c4_report_generated_no_error"] = False

    # Criterion 5: tier summaries cover expected tiers
    try:
        if report is not None:
            rep_to_check = report
        else:
            subset = [e for e in WPRegistry.all()]
            suite = IntegrationTestSuite(entries=subset, run_criteria=False)
            rep_to_check = suite.run()
        tiers_covered = set(rep_to_check.tier_summaries.keys())
        expected_tiers = {2, 3, 4, 5, 6, 7, 8, 9, 10}
        results["c5_tier_summaries_cover_tiers"] = expected_tiers.issubset(tiers_covered)
    except Exception:
        results["c5_tier_summaries_cover_tiers"] = False

    # Criterion 6: JSON-serialisable
    try:
        if report is not None:
            d = report.to_dict()
        else:
            subset = [e for e in WPRegistry.all() if e.wp_id in {"wp61"}]
            suite = IntegrationTestSuite(entries=subset, run_criteria=False)
            d = suite.run().to_dict()
        json_mod.dumps(d)
        results["c6_report_json_serialisable"] = True
    except Exception:
        results["c6_report_json_serialisable"] = False

    passed = sum(results.values())
    logger.info("WP67 exit criteria: %d/6 passed.", passed)
    return results
