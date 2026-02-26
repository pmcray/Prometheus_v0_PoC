"""
WP19 Test Suite: Causal Action Evaluator
=========================================

Six test classes mirroring WP17/WP18 structure:

TestActionOutcomeTable      Unit tests for the potential-outcomes data table
TestATEEstimation           ATE computation, CI coverage, confidence scaling
TestCausalRecommendation    Heuristic override logic and fallback behaviour
TestCausalAnalogyAuditor    WP18 integration: causally-attributed confirm/refute
TestCausalCRLS              Integration on real GoBoard puzzles
TestWP19ExitCriteria        Formal six-criterion verifier

Design principle
----------------
Tests are structured to avoid GoBoard wherever only the evaluator logic is
being tested (TestActionOutcomeTable, TestATEEstimation, TestCausalRecommendation,
TestCausalAnalogyAuditor).  Only TestCausalCRLS and TestWP19ExitCriteria use real
GoBoard puzzles — the same infrastructure as WP17's TestCausalIsolation.
"""

import math
import random
import time
from typing import Callable, Dict, List, Optional, Tuple

import pytest

from prometheus.environments.go import GoBoard
from prometheus.meta_learner import MetaLearner
from prometheus.wp17_crls_synthesis import SynthesisAction, SynthesisRecord
from prometheus.wp18_analogy_engine import (
    GoChessTacticRegistry,
    StructuralAnalogy,
    TacticSignature,
)
from prometheus.wp19_causal_evaluator import (
    ATEEstimate,
    ActionOutcomeTable,
    CausalActionEvaluator,
    CausalAnalogyAuditor,
    CausalCRLS,
    CausalRecommendation,
    verify_wp19_exit_criteria,
)


# ===========================================================================
# Shared helpers
# ===========================================================================

TACTICS = ["capture_atari", "ladder", "ko_fight", "territory_claim",
           "connect_groups", "random_legal"]


def _make_record(
    action: SynthesisAction,
    acc_before: float,
    improvement: float,
    generation: int = 0,
) -> SynthesisRecord:
    """Build a synthetic SynthesisRecord with known improvement."""
    acc_after = acc_before + improvement
    r = SynthesisRecord(
        generation    = generation,
        action        = action,
        trigger       = "test",
        before_probs  = {"a": 0.5, "b": 0.5},
        after_probs   = {"a": 0.5, "b": 0.5},
        before_upward = 0.20,
        after_upward  = 0.20,
        safety_status = "provably_safe",
        safety_reason = "rule_add",
        acc_before    = acc_before,
        acc_after     = acc_after,
        improvement   = improvement,
    )
    return r


def _make_meta() -> MetaLearner:
    return MetaLearner(TACTICS, upward_rate=0.0, downward_rate=0.0)


# ---------------------------------------------------------------------------
# Go puzzle helpers (reused from WP17 test pattern)
# ---------------------------------------------------------------------------

def _make_atari_board() -> Tuple[GoBoard, int, Tuple[int, int]]:
    board = GoBoard(size=9)
    board.board[4][4] = GoBoard.WHITE
    board.board[4][3] = GoBoard.BLACK
    board.board[4][5] = GoBoard.BLACK
    board.board[5][4] = GoBoard.BLACK
    board.current_player = GoBoard.BLACK
    return board, GoBoard.BLACK, (3, 4)


def _go_puzzles(n: int) -> List[Tuple]:
    return [_make_atari_board() for _ in range(n)]


def _go_evaluate(board, move, correct_move, player) -> bool:
    if move == correct_move:
        return True
    if move[0] >= 0 and board.is_legal_move(move[0], move[1], player):
        if len(board.would_capture(move[0], move[1], player)) > 0:
            return True
    return False


def _go_tactic_fns() -> Dict[str, Callable]:
    def capture_atari(board, player):
        for r in range(board.size):
            for c in range(board.size):
                if board.is_legal_move(r, c, player):
                    if board.would_capture(r, c, player):
                        return (r, c)
        legal = board.get_legal_moves(player)
        return legal[0] if legal else None

    def ladder(board, player):
        legal = board.get_legal_moves(player)
        for m in legal:
            if board.would_capture(m[0], m[1], player):
                return m
        return legal[0] if legal else None

    def ko_fight(board, player):
        legal = board.get_legal_moves(player)
        return legal[0] if legal else None

    def territory_claim(board, player):
        legal = board.get_legal_moves(player)
        return legal[-1] if legal else None

    def connect_groups(board, player):
        legal = board.get_legal_moves(player)
        mid = len(legal) // 2
        return legal[mid] if legal else None

    def random_legal(board, player):
        legal = board.get_legal_moves(player)
        return random.choice(legal) if legal else None

    return {
        "capture_atari":   capture_atari,
        "ladder":          ladder,
        "ko_fight":        ko_fight,
        "territory_claim": territory_claim,
        "connect_groups":  connect_groups,
        "random_legal":    random_legal,
    }


# ===========================================================================
# TestActionOutcomeTable
# ===========================================================================

class TestActionOutcomeTable:

    def test_ingest_adds_to_table(self):
        t = ActionOutcomeTable()
        r = _make_record(SynthesisAction.DEMOTE_WORST, 0.50, +0.10)
        t.ingest(r)
        assert t.n_trials(SynthesisAction.DEMOTE_WORST) == 1

    def test_ingest_ignores_record_with_none_improvement(self):
        t = ActionOutcomeTable()
        r = SynthesisRecord(
            generation=0, action=SynthesisAction.DEMOTE_WORST, trigger="x",
            before_probs={}, after_probs={},
            before_upward=0.2, after_upward=0.2,
            safety_status="provably_safe", safety_reason="ok",
            acc_before=0.5, acc_after=None, improvement=None,
        )
        t.ingest(r)
        assert t.n_trials(SynthesisAction.DEMOTE_WORST) == 0

    def test_mean_improvement_correct(self):
        t = ActionOutcomeTable()
        t.ingest(_make_record(SynthesisAction.PROMOTE_BEST, 0.5, +0.10))
        t.ingest(_make_record(SynthesisAction.PROMOTE_BEST, 0.5, +0.20))
        mean = t.mean_improvement(SynthesisAction.PROMOTE_BEST)
        assert abs(mean - 0.15) < 1e-9

    def test_baseline_drift_zero_when_no_no_action(self):
        t = ActionOutcomeTable()
        t.ingest(_make_record(SynthesisAction.DEMOTE_WORST, 0.5, +0.10))
        assert t.baseline_drift() == 0.0

    def test_baseline_drift_uses_no_action_rows(self):
        t = ActionOutcomeTable()
        t.ingest(_make_record(SynthesisAction.NO_ACTION, 0.5, +0.03))
        t.ingest(_make_record(SynthesisAction.NO_ACTION, 0.5, +0.05))
        assert abs(t.baseline_drift() - 0.04) < 1e-9

    def test_seed_from_records(self):
        records = [
            _make_record(SynthesisAction.BOOST_UPWARD, 0.5, +0.12, gen)
            for gen in range(5)
        ]
        t = ActionOutcomeTable(records)
        assert t.n_trials(SynthesisAction.BOOST_UPWARD) == 5

    def test_all_actions_seen(self):
        t = ActionOutcomeTable()
        t.ingest(_make_record(SynthesisAction.DEMOTE_WORST, 0.5, 0.10))
        t.ingest(_make_record(SynthesisAction.PROMOTE_BEST, 0.5, 0.05))
        seen = set(t.all_actions_seen())
        assert SynthesisAction.DEMOTE_WORST in seen
        assert SynthesisAction.PROMOTE_BEST in seen
        assert SynthesisAction.NO_ACTION    not in seen


# ===========================================================================
# TestATEEstimation
# ===========================================================================

class TestATEEstimation:

    def _eval_with_data(
        self,
        action_improvements:    List[float],
        no_action_improvements: List[float],
    ) -> CausalActionEvaluator:
        ev = CausalActionEvaluator(min_trials_to_override=2, n_bootstrap=100)
        for imp in action_improvements:
            ev.update(_make_record(SynthesisAction.DEMOTE_WORST, 0.5, imp))
        for imp in no_action_improvements:
            ev.update(_make_record(SynthesisAction.NO_ACTION, 0.5, imp))
        return ev

    def test_ate_subtracts_baseline(self):
        """ATE(DEMOTE_WORST) = mean_improvement - baseline_drift."""
        ev = self._eval_with_data(
            action_improvements    = [0.10, 0.12, 0.11],
            no_action_improvements = [0.03, 0.03],
        )
        ate_est = ev.estimate_ate(SynthesisAction.DEMOTE_WORST)
        expected_ate = 0.11 - 0.03   # mean action − mean baseline
        assert abs(ate_est.ate - expected_ate) < 0.01

    def test_ate_zero_when_no_observations(self):
        ev = CausalActionEvaluator()
        est = ev.estimate_ate(SynthesisAction.RESET_UNIFORM)
        assert est.ate == 0.0
        assert est.confidence == 0.0
        assert est.n_trials == 0

    def test_confidence_increases_with_n(self):
        ev = CausalActionEvaluator(n_bootstrap=50)
        for n in range(1, 6):
            ev.update(_make_record(SynthesisAction.BOOST_UPWARD, 0.5, 0.05))
        est = ev.estimate_ate(SynthesisAction.BOOST_UPWARD)
        # confidence = 1 - 1/(1+5) ≈ 0.833
        assert est.confidence > 0.5
        assert est.confidence <= 1.0

    def test_ci_contains_ate(self):
        """Bootstrap CI must contain the point estimate."""
        ev = self._eval_with_data(
            action_improvements    = [0.08, 0.10, 0.09, 0.11, 0.07],
            no_action_improvements = [0.02],
        )
        est = ev.estimate_ate(SynthesisAction.DEMOTE_WORST)
        assert est.ci_low <= est.ate <= est.ci_high, (
            f"ATE={est.ate:.4f} not in CI [{est.ci_low:.4f}, {est.ci_high:.4f}]"
        )

    def test_negative_ate_for_harmful_action(self):
        """If an action consistently degrades performance, ATE should be negative."""
        ev = self._eval_with_data(
            action_improvements    = [-0.10, -0.08, -0.12],
            no_action_improvements = [0.02],
        )
        est = ev.estimate_ate(SynthesisAction.DEMOTE_WORST)
        assert est.ate < 0.0, "Harmful action must have negative ATE"

    def test_best_causal_action_returns_highest_ate(self):
        ev = CausalActionEvaluator(min_trials_to_override=2, n_bootstrap=50)
        # DEMOTE_WORST: moderate improvement
        for imp in [0.08, 0.09, 0.07]:
            ev.update(_make_record(SynthesisAction.DEMOTE_WORST, 0.5, imp))
        # PROMOTE_BEST: larger improvement
        for imp in [0.15, 0.16, 0.14]:
            ev.update(_make_record(SynthesisAction.PROMOTE_BEST, 0.5, imp))
        # Baseline
        ev.update(_make_record(SynthesisAction.NO_ACTION, 0.5, 0.02))

        best = ev.best_causal_action()
        assert best is not None
        assert best.action == SynthesisAction.PROMOTE_BEST

    def test_best_causal_action_none_below_min_trials(self):
        """With fewer trials than min_trials_to_override, best returns None."""
        ev = CausalActionEvaluator(min_trials_to_override=5, n_bootstrap=50)
        for imp in [0.10, 0.10]:   # only 2 trials, need 5
            ev.update(_make_record(SynthesisAction.DEMOTE_WORST, 0.5, imp))
        assert ev.best_causal_action() is None


# ===========================================================================
# TestCausalRecommendation
# ===========================================================================

class TestCausalRecommendation:

    def _make_evaluator_with_data(self) -> CausalActionEvaluator:
        ev = CausalActionEvaluator(
            min_trials_to_override = 3,
            override_tolerance     = 0.02,
            n_bootstrap            = 100,
        )
        # DEMOTE_WORST is the heuristic choice (mediocre)
        for imp in [0.05, 0.06, 0.05]:
            ev.update(_make_record(SynthesisAction.DEMOTE_WORST, 0.5, imp))
        # PROMOTE_BEST is causally better (clearly)
        for imp in [0.15, 0.16, 0.14]:
            ev.update(_make_record(SynthesisAction.PROMOTE_BEST, 0.5, imp))
        # Baseline drift
        for imp in [0.02, 0.02]:
            ev.update(_make_record(SynthesisAction.NO_ACTION, 0.5, imp))
        return ev

    def test_override_when_causal_better(self):
        """Evaluator must override when PROMOTE_BEST has much higher ATE."""
        ev  = self._make_evaluator_with_data()
        rec = ev.recommend(SynthesisAction.DEMOTE_WORST, "heuristic: large drop")
        assert rec.override, (
            f"Expected override; ATE table: "
            f"{ev.get_summary()['ate_table']}"
        )
        assert rec.action == SynthesisAction.PROMOTE_BEST

    def test_no_override_when_data_insufficient(self):
        """With zero observations, evaluator must defer to heuristic."""
        ev  = CausalActionEvaluator(min_trials_to_override=3)
        rec = ev.recommend(SynthesisAction.DEMOTE_WORST, "heuristic")
        assert not rec.override
        assert rec.action == SynthesisAction.DEMOTE_WORST

    def test_no_override_within_tolerance(self):
        """If causal advantage < tolerance, no override."""
        ev = CausalActionEvaluator(
            min_trials_to_override = 3,
            override_tolerance     = 0.20,   # very high tolerance
            n_bootstrap            = 50,
        )
        for imp in [0.10, 0.11, 0.09]:
            ev.update(_make_record(SynthesisAction.DEMOTE_WORST, 0.5, imp))
        for imp in [0.11, 0.12, 0.10]:   # barely better
            ev.update(_make_record(SynthesisAction.PROMOTE_BEST, 0.5, imp))
        ev.update(_make_record(SynthesisAction.NO_ACTION, 0.5, 0.02))

        rec = ev.recommend(SynthesisAction.DEMOTE_WORST, "heuristic")
        assert not rec.override

    def test_recommendation_logged(self):
        ev  = CausalActionEvaluator()
        ev.recommend(SynthesisAction.NO_ACTION, "test")
        assert len(ev.recommendations) == 1

    def test_to_dict_structure(self):
        ev  = CausalActionEvaluator()
        rec = ev.recommend(SynthesisAction.DEMOTE_WORST, "test")
        d   = rec.to_dict()
        for key in ("action", "heuristic_action", "override", "trigger", "ate_estimate"):
            assert key in d, f"Missing key: {key}"

    def test_heuristic_action_preserved_in_recommendation(self):
        ev  = CausalActionEvaluator()
        rec = ev.recommend(SynthesisAction.RESET_UNIFORM, "some trigger")
        assert rec.heuristic_action == SynthesisAction.RESET_UNIFORM

    def test_override_count_increments(self):
        ev = self._make_evaluator_with_data()
        ev.recommend(SynthesisAction.DEMOTE_WORST, "heuristic 1")
        ev.recommend(SynthesisAction.DEMOTE_WORST, "heuristic 2")
        summary = ev.get_summary()
        assert summary["total_overrides"] >= 1


# ===========================================================================
# TestCausalAnalogyAuditor
# ===========================================================================

class TestCausalAnalogyAuditor:

    def _make_analogy(self) -> StructuralAnalogy:
        amap = GoChessTacticRegistry.build()
        return amap.get_target_analogues("capture_atari", "chess")[0]

    def _make_auditor(self, baseline_drift: float) -> CausalAnalogyAuditor:
        ev = CausalActionEvaluator(n_bootstrap=50)
        # Seed NO_ACTION rows to set baseline
        for _ in range(4):
            ev.update(_make_record(SynthesisAction.NO_ACTION, 0.5, baseline_drift))
        return CausalAnalogyAuditor(ev, attribution_tolerance=0.02)

    def test_confirm_when_excess_above_tolerance(self):
        analogy  = self._make_analogy()
        auditor  = self._make_auditor(baseline_drift=0.02)
        # ΔY=0.08, baseline=0.02, excess=0.06 > tolerance=0.02 → confirm
        result = auditor.audit(analogy, acc_before=0.50, acc_after=0.58)
        assert result is True
        assert analogy.confirmations == 1
        assert analogy.refutations   == 0

    def test_refute_when_excess_below_tolerance(self):
        analogy  = self._make_analogy()
        auditor  = self._make_auditor(baseline_drift=0.05)
        # ΔY=0.05, baseline=0.05, excess=0.00 < tolerance=0.02 → refute
        result = auditor.audit(analogy, acc_before=0.50, acc_after=0.55)
        assert result is False
        assert analogy.refutations   == 1
        assert analogy.confirmations == 0

    def test_audit_log_populated(self):
        analogy  = self._make_analogy()
        auditor  = self._make_auditor(baseline_drift=0.01)
        auditor.audit(analogy, 0.5, 0.6)
        auditor.audit(analogy, 0.6, 0.65)
        assert len(auditor.audit_log) == 2

    def test_audit_summary_counts(self):
        analogy = self._make_analogy()
        auditor = self._make_auditor(baseline_drift=0.02)
        # 3 confirms (excess=0.10), 2 refutes (excess=0.00)
        for _ in range(3):
            auditor.audit(analogy, 0.5, 0.62)   # excess=0.10
        for _ in range(2):
            auditor.audit(analogy, 0.5, 0.52)   # excess=0.00
        s = auditor.get_audit_summary()
        assert s["confirmed"] == 3
        assert s["refuted"]   == 2
        assert abs(s["attribution_rate"] - 0.6) < 0.01

    def test_negative_delta_always_refuted(self):
        analogy = self._make_analogy()
        auditor = self._make_auditor(baseline_drift=0.0)
        result  = auditor.audit(analogy, acc_before=0.6, acc_after=0.5)
        assert result is False


# ===========================================================================
# TestCausalCRLS — integration on real GoBoard puzzles
# ===========================================================================

class TestCausalCRLS:

    def _make_crls(self, seed=42) -> CausalCRLS:
        random.seed(seed)
        return CausalCRLS(
            strategies             = TACTICS,
            upward_rate            = 0.0,
            downward_rate          = 0.0,
            min_trials_to_override = 3,
            override_tolerance     = 0.02,
            synthesiser_kwargs     = {"acc_drop_threshold": 0.0},
        )

    def test_run_generation_returns_valid_accuracy(self):
        crls = self._make_crls()
        acc  = crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_evaluate)
        assert 0.0 <= acc <= 1.0

    def test_end_of_generation_returns_both_outputs(self):
        crls = self._make_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_evaluate)
        record, causal_rec = crls.end_of_generation()
        assert isinstance(record, SynthesisRecord)
        assert isinstance(causal_rec, CausalRecommendation)

    def test_causal_rec_heuristic_action_populated(self):
        crls = self._make_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_evaluate)
        _, causal_rec = crls.end_of_generation()
        assert causal_rec.heuristic_action in list(SynthesisAction)

    def test_evaluator_ingests_records_over_time(self):
        """After 5 generations, the evaluator table must have observations."""
        crls = self._make_crls()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_evaluate)
            crls.end_of_generation()

        summary = crls.evaluator.get_summary()
        assert summary["total_recommendations"] >= 1
        # At least one action type observed
        assert len(summary["actions_observed"]) >= 1

    def test_no_unsafe_synthesis_applied(self):
        """All synthesis proposals must be safety-gated; none UNSAFE applied."""
        crls = self._make_crls()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_evaluate)
            crls.end_of_generation()

        for rec in crls.synth.records:
            if rec.action != SynthesisAction.NO_ACTION:
                assert rec.safety_status != "provably_unsafe", (
                    f"Record gen={rec.generation} applied {rec.action.value} "
                    f"with status {rec.safety_status}"
                )

    def test_full_report_structure(self):
        crls = self._make_crls()
        for _ in range(3):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_evaluate)
            crls.end_of_generation()

        report = crls.get_full_report()
        for key in ("generations", "accuracy_history", "synthesis_summary",
                    "causal_summary", "safety_statistics", "generation_log"):
            assert key in report, f"Missing key: {key}"

    def test_gen_log_records_heuristic_and_causal(self):
        crls = self._make_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_evaluate)
        crls.end_of_generation("test_regime")

        assert len(crls.gen_log) == 1
        entry = crls.gen_log[0]
        for field in ("heuristic", "causal_action", "override"):
            assert field in entry, f"Missing field: {field}"

    def test_override_triggered_after_enough_data(self):
        """
        Seed the evaluator with synthetic data showing PROMOTE_BEST is much
        better than DEMOTE_WORST, then verify override fires on next call.
        """
        crls = self._make_crls()
        # Force first generation so acc_history is populated
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_evaluate)

        # Seed evaluator with synthetic history: PROMOTE_BEST >> DEMOTE_WORST
        for imp in [0.15, 0.16, 0.14, 0.15]:
            crls.evaluator.update(
                _make_record(SynthesisAction.PROMOTE_BEST, 0.5, imp)
            )
        for imp in [0.03, 0.03, 0.02]:
            crls.evaluator.update(
                _make_record(SynthesisAction.DEMOTE_WORST, 0.5, imp)
            )
        for imp in [0.01, 0.01]:
            crls.evaluator.update(
                _make_record(SynthesisAction.NO_ACTION, 0.5, imp)
            )

        # Force a large accuracy drop so heuristic chooses DEMOTE_WORST
        crls.acc_history.append(0.30)   # second generation with big drop
        _, causal_rec = crls.end_of_generation()

        assert causal_rec.override is True, (
            "Causal evaluator should override DEMOTE_WORST with PROMOTE_BEST "
            "given the seeded history"
        )
        assert causal_rec.action == SynthesisAction.PROMOTE_BEST


# ===========================================================================
# TestWP19ExitCriteria
# ===========================================================================

class TestWP19ExitCriteria:

    def _make_converged_crls(self, seed: int = 7) -> CausalCRLS:
        random.seed(seed)
        crls = CausalCRLS(
            strategies             = TACTICS,
            upward_rate            = 0.0,
            downward_rate          = 0.0,
            min_trials_to_override = 3,
            override_tolerance     = 0.02,
            synthesiser_kwargs     = {"acc_drop_threshold": 0.0},
        )

        tactic_fns = _go_tactic_fns()
        for _ in range(8):
            crls.run_generation(_go_puzzles(30), tactic_fns, _go_evaluate)
            crls.end_of_generation()

        return crls

    def test_ate_estimated(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp19_exit_criteria(crls)
        assert criteria["ate_estimated"], "At least one ATE must be non-zero"

    def test_override_or_confirmed(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp19_exit_criteria(crls)
        assert criteria["override_or_confirmed"], (
            "Evaluator must have produced at least one recommendation"
        )

    def test_baseline_measured(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp19_exit_criteria(crls)
        assert criteria["baseline_measured"], (
            "NO_ACTION baseline drift must have been observed"
        )

    def test_causal_beats_heuristic(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp19_exit_criteria(crls)
        assert criteria["causal_beats_heuristic"], (
            "Best causal ATE must be ≥ heuristic ATE"
        )

    def test_safety_preserved(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp19_exit_criteria(crls)
        assert criteria["safety_preserved"], (
            "All synthesis proposals must be safety-evaluated; none UNSAFE applied"
        )

    def test_recommendations_logged(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp19_exit_criteria(crls)
        assert criteria["recommendations_logged"], (
            "At least one recommendation must have been logged"
        )

    def test_all_criteria_pass(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp19_exit_criteria(crls)
        failing  = [k for k, v in criteria.items() if not v]
        assert not failing, f"WP19 exit criteria failed: {failing}"
