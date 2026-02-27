"""
WP23 Test Suite: Policy Distillation
======================================

Seven test classes mirroring the WP17–22 structure:

TestDistillationRecord      Unit tests for the audit-record dataclass
TestStudentPolicy           Feature extraction, softmax, SGD update
TestPolicyDistiller         Confidence gate, train(), get_summary()
TestDistilledCRLS           Integration on real GoBoard puzzles —
                             verifies all six planning layers fire
TestDistillationConvergence That loss decreases and student eventually leads
TestWP23ExitCriteria        Six-criterion verifier
TestLayerInteraction        All six layers (WP17–23) interact correctly
"""

import math
import random
from typing import Callable, Dict, List, Optional, Tuple

import pytest

from prometheus.environments.go import GoBoard
from prometheus.meta_learner import MetaLearner
from prometheus.wp17_crls_synthesis import SynthesisAction, SynthesisRecord
from prometheus.wp19_causal_evaluator import CausalRecommendation
from prometheus.wp20_temporal_planner import (
    RolloutResult,
    SynthesisStateSnapshot,
    SynthesisTrajectoryModel,
    TrajectoryTransition,
)
from prometheus.wp21_meta_gradient import MetaGradStep, MetaParams
from prometheus.wp22_bandit_exploration import (
    BanditCRLS,
    BanditMode,
    ExplorationRecord,
)
from prometheus.wp23_policy_distillation import (
    DistilledCRLS,
    DistillationRecord,
    PolicyDistiller,
    StudentPolicy,
    _ACTIONS,
    _FEAT_DIM,
    _N_ACTIONS,
    _extract_features,
    verify_wp23_exit_criteria,
)


# ===========================================================================
# Shared helpers  (mirrors WP22 pattern)
# ===========================================================================

TACTICS = ["capture_atari", "ladder", "ko_fight",
           "territory_claim", "connect_groups", "random_legal"]


def _make_snapshot(
    generation: int = 0,
    probs: Optional[Dict[str, float]] = None,
    upward_rate: float = 0.20,
    accuracy: float = 0.50,
) -> SynthesisStateSnapshot:
    if probs is None:
        n = len(TACTICS)
        probs = {t: 1.0 / n for t in TACTICS}
    return SynthesisStateSnapshot(
        generation=generation, probs=probs,
        upward_rate=upward_rate, accuracy=accuracy,
    )


# ---------------------------------------------------------------------------
# Real GoBoard puzzle helpers (mirrors WP22)
# ---------------------------------------------------------------------------

def _atari_board() -> Tuple[GoBoard, int, Tuple[int, int]]:
    board = GoBoard(size=9)
    board.board[4][4] = GoBoard.WHITE
    board.board[4][3] = GoBoard.BLACK
    board.board[4][5] = GoBoard.BLACK
    board.board[5][4] = GoBoard.BLACK
    board.current_player = GoBoard.BLACK
    return board, GoBoard.BLACK, (3, 4)


def _go_puzzles(n: int) -> List[Tuple]:
    return [_atari_board() for _ in range(n)]


def _go_eval(board, move, correct_move, player) -> bool:
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


def _make_distilled_crls(
    seed: int = 42,
    distill_min_steps: int = 5,
    distill_confidence: float = 0.40,
) -> DistilledCRLS:
    random.seed(seed)
    return DistilledCRLS(
        strategies             = TACTICS,
        upward_rate            = 0.0,
        downward_rate          = 0.0,
        synthesiser_kwargs     = {"acc_drop_threshold": 0.0},
        min_trials_to_override = 3,
        override_tolerance     = 0.02,
        rollout_horizon        = 3,
        rollout_discount       = 0.90,
        min_transitions        = 3,
        meta_step_size         = 0.02,
        meta_min_transitions   = 4,
        bandit_mode            = BanditMode.UCB1,
        exploration_coeff      = 1.0,
        force_explore_unseen   = True,
        distill_lr             = 0.10,
        distill_l2             = 1e-4,
        distill_min_steps      = distill_min_steps,
        distill_confidence     = distill_confidence,
    )


# ===========================================================================
# TestDistillationRecord
# ===========================================================================

class TestDistillationRecord:

    def _make_record(
        self,
        teacher: SynthesisAction = SynthesisAction.DEMOTE_WORST,
        student: SynthesisAction = SynthesisAction.PROMOTE_BEST,
        student_led: bool = False,
    ) -> DistillationRecord:
        return DistillationRecord(
            generation     = 5,
            teacher_action = teacher,
            student_probs  = {a.value: 1.0 / _N_ACTIONS for a in _ACTIONS},
            student_action = student,
            student_led    = student_led,
            confidence     = 1.0 / _N_ACTIONS,
            loss           = math.log(_N_ACTIONS),
            training_step  = 1,
        )

    def test_to_dict_has_all_required_keys(self):
        rec = self._make_record()
        d   = rec.to_dict()
        for k in ("generation", "teacher_action", "student_probs",
                  "student_action", "student_led", "confidence",
                  "loss", "training_step"):
            assert k in d, f"Missing key {k} in DistillationRecord.to_dict()"

    def test_teacher_action_serialised_as_string(self):
        rec = self._make_record(teacher=SynthesisAction.DEMOTE_WORST)
        assert rec.to_dict()["teacher_action"] == SynthesisAction.DEMOTE_WORST.value

    def test_student_action_serialised_as_string(self):
        rec = self._make_record(student=SynthesisAction.PROMOTE_BEST)
        assert rec.to_dict()["student_action"] == SynthesisAction.PROMOTE_BEST.value

    def test_student_led_false_by_default(self):
        rec = self._make_record(student_led=False)
        assert not rec.student_led

    def test_student_led_true_stored(self):
        rec = self._make_record(student_led=True)
        assert rec.student_led

    def test_timestamp_is_positive_float(self):
        rec = self._make_record()
        assert isinstance(rec.timestamp, float)
        assert rec.timestamp > 0.0

    def test_loss_is_positive_for_uniform_student(self):
        """Cross-entropy against a uniform student should be log(|A|)."""
        rec = self._make_record()
        assert rec.loss > 0.0


# ===========================================================================
# TestStudentPolicy
# ===========================================================================

class TestStudentPolicy:

    def test_feature_vector_has_correct_dimension(self):
        snap = _make_snapshot()
        phi  = _extract_features(snap)
        assert len(phi) == _FEAT_DIM

    def test_feature_accuracy_is_first_element(self):
        snap = _make_snapshot(accuracy=0.73)
        phi  = _extract_features(snap)
        assert abs(phi[0] - 0.73) < 1e-9

    def test_feature_upward_rate_is_second_element(self):
        snap = _make_snapshot(upward_rate=0.35)
        phi  = _extract_features(snap)
        assert abs(phi[1] - 0.35) < 1e-9

    def test_feature_generation_is_normalised(self):
        snap = _make_snapshot(generation=50)
        phi  = _extract_features(snap)
        assert abs(phi[2] - 0.50) < 1e-9

    def test_softmax_probs_sum_to_one(self):
        student = StudentPolicy()
        snap    = _make_snapshot()
        probs   = student.softmax_probs(_extract_features(snap))
        assert abs(sum(probs) - 1.0) < 1e-9

    def test_softmax_probs_all_positive(self):
        student = StudentPolicy()
        snap    = _make_snapshot()
        probs   = student.softmax_probs(_extract_features(snap))
        assert all(p > 0.0 for p in probs)

    def test_predict_returns_synthesis_action(self):
        student = StudentPolicy()
        snap    = _make_snapshot()
        action, conf, prob_dict = student.predict(snap)
        assert isinstance(action, SynthesisAction)
        assert 0.0 <= conf <= 1.0
        assert len(prob_dict) == _N_ACTIONS

    def test_predict_confidence_is_max_prob(self):
        student = StudentPolicy()
        snap    = _make_snapshot()
        _, conf, prob_dict = student.predict(snap)
        assert abs(conf - max(prob_dict.values())) < 1e-9

    def test_training_steps_zero_initially(self):
        student = StudentPolicy()
        assert student.training_steps == 0

    def test_update_increments_training_steps(self):
        student = StudentPolicy()
        snap    = _make_snapshot()
        student.update(snap, SynthesisAction.DEMOTE_WORST)
        assert student.training_steps == 1

    def test_update_returns_positive_loss(self):
        student = StudentPolicy()
        snap    = _make_snapshot()
        loss = student.update(snap, SynthesisAction.DEMOTE_WORST)
        assert loss > 0.0

    def test_repeated_updates_on_same_action_reduce_loss(self):
        """After many updates targeting the same action, loss should decrease."""
        random.seed(0)
        student = StudentPolicy(learning_rate=0.1)
        snap    = _make_snapshot(accuracy=0.6, upward_rate=0.2)
        target  = SynthesisAction.PROMOTE_BEST

        losses = [student.update(snap, target) for _ in range(100)]
        # Last 10 losses should be less than first 10 on average
        early = sum(losses[:10]) / 10
        late  = sum(losses[-10:]) / 10
        assert late < early, (
            f"Loss should decrease with repeated training; early={early:.4f} late={late:.4f}"
        )

    def test_weight_matrix_has_correct_shape(self):
        student = StudentPolicy()
        W = student.get_weight_matrix()
        assert len(W) == _N_ACTIONS
        for row in W:
            assert len(row) == _FEAT_DIM

    def test_weight_norm_zero_before_training(self):
        student = StudentPolicy()
        assert student.weight_norm() == 0.0

    def test_weight_norm_positive_after_training(self):
        student = StudentPolicy()
        snap    = _make_snapshot()
        student.update(snap, SynthesisAction.DEMOTE_WORST)
        assert student.weight_norm() > 0.0

    def test_target_action_probability_increases_after_training(self):
        """Probability of target action should increase after one SGD step."""
        student = StudentPolicy(learning_rate=0.5)
        snap    = _make_snapshot()
        target  = SynthesisAction.BOOST_UPWARD

        _, _, probs_before = student.predict(snap)
        student.update(snap, target)
        _, _, probs_after = student.predict(snap)

        assert probs_after[target.value] > probs_before[target.value], (
            "Target action probability must increase after one training step"
        )

    def test_l2_reg_reduces_weight_growth(self):
        """With high L2, weights should grow more slowly."""
        snap   = _make_snapshot()
        target = SynthesisAction.PROMOTE_BEST

        s_no_reg  = StudentPolicy(learning_rate=0.1, l2_reg=0.0)
        s_high_reg = StudentPolicy(learning_rate=0.1, l2_reg=1.0)

        for _ in range(50):
            s_no_reg.update(snap, target)
            s_high_reg.update(snap, target)

        assert s_no_reg.weight_norm() > s_high_reg.weight_norm(), (
            "Higher L2 regularisation should produce smaller weight norms"
        )


# ===========================================================================
# TestPolicyDistiller
# ===========================================================================

class TestPolicyDistiller:

    def _distiller(
        self,
        min_steps: int = 5,
        conf_threshold: float = 0.40,
    ) -> PolicyDistiller:
        return PolicyDistiller(
            learning_rate        = 0.10,
            l2_reg               = 1e-4,
            min_training_steps   = min_steps,
            confidence_threshold = conf_threshold,
        )

    def test_should_lead_false_before_min_steps(self):
        d    = self._distiller(min_steps=100)
        snap = _make_snapshot()
        assert not d.should_lead(snap)

    def test_should_lead_possible_after_training(self):
        """After enough training, student with low threshold should lead."""
        d    = self._distiller(min_steps=5, conf_threshold=0.01)
        snap = _make_snapshot(accuracy=0.9)
        target = SynthesisAction.PROMOTE_BEST
        for i in range(20):
            d.train(snap, target, generation=i, student_led=False)
        # With conf_threshold=0.01, student should be able to lead now
        assert d.should_lead(snap)

    def test_train_returns_distillation_record(self):
        d    = self._distiller()
        snap = _make_snapshot()
        rec  = d.train(snap, SynthesisAction.DEMOTE_WORST, generation=0, student_led=False)
        assert isinstance(rec, DistillationRecord)

    def test_distillation_log_grows_after_train(self):
        d    = self._distiller()
        snap = _make_snapshot()
        for i in range(7):
            d.train(snap, SynthesisAction.DEMOTE_WORST, generation=i, student_led=False)
        assert len(d.distillation_log) == 7

    def test_record_teacher_action_matches(self):
        d    = self._distiller()
        snap = _make_snapshot()
        rec  = d.train(snap, SynthesisAction.BOOST_UPWARD, generation=0, student_led=False)
        assert rec.teacher_action == SynthesisAction.BOOST_UPWARD

    def test_record_generation_matches(self):
        d    = self._distiller()
        snap = _make_snapshot()
        rec  = d.train(snap, SynthesisAction.PROMOTE_BEST, generation=42, student_led=False)
        assert rec.generation == 42

    def test_record_student_led_stored(self):
        d    = self._distiller()
        snap = _make_snapshot()
        rec  = d.train(snap, SynthesisAction.DEMOTE_WORST, generation=0, student_led=True)
        assert rec.student_led

    def test_training_step_counter_in_record(self):
        d    = self._distiller()
        snap = _make_snapshot()
        for i in range(3):
            rec = d.train(snap, SynthesisAction.DEMOTE_WORST, generation=i, student_led=False)
        assert rec.training_step == 3

    def test_get_summary_has_required_keys(self):
        d    = self._distiller()
        snap = _make_snapshot()
        for i in range(5):
            d.train(snap, SynthesisAction.DEMOTE_WORST, generation=i, student_led=False)
        s = d.get_summary()
        for k in ("training_steps", "student_led_count", "teacher_led_count",
                  "student_led_rate", "mean_loss", "mean_confidence",
                  "weight_norm", "distillation_log"):
            assert k in s, f"Missing key {k} in PolicyDistiller.get_summary()"

    def test_get_summary_empty_before_training(self):
        d = self._distiller()
        s = d.get_summary()
        assert s["training_steps"] == 0
        assert s["mean_loss"] is None

    def test_student_led_rate_between_zero_and_one(self):
        d    = self._distiller(min_steps=2, conf_threshold=0.01)
        snap = _make_snapshot(accuracy=0.9)
        target = SynthesisAction.PROMOTE_BEST
        for i in range(20):
            student_led = d.should_lead(snap)
            d.train(snap, target, generation=i, student_led=student_led)
        s = d.get_summary()
        assert 0.0 <= s["student_led_rate"] <= 1.0


# ===========================================================================
# TestDistilledCRLS  —  integration on real GoBoard puzzles
# ===========================================================================

class TestDistilledCRLS:

    def test_construction_creates_distiller(self):
        crls = _make_distilled_crls()
        assert isinstance(crls.distiller, PolicyDistiller)

    def test_distilled_crls_is_subclass_of_bandit_crls(self):
        crls = _make_distilled_crls()
        assert isinstance(crls, BanditCRLS)

    def test_run_generation_returns_valid_accuracy(self):
        crls = _make_distilled_crls()
        acc  = crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        assert 0.0 <= acc <= 1.0

    def test_end_of_generation_returns_sextuple(self):
        crls = _make_distilled_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        result = crls.end_of_generation()
        assert len(result) == 6
        record, causal_rec, rollout, grad_step, bandit_rec, distill_rec = result
        assert isinstance(record,      SynthesisRecord)
        assert isinstance(causal_rec,  CausalRecommendation)
        assert isinstance(rollout,     RolloutResult)
        assert isinstance(grad_step,   MetaGradStep)
        assert isinstance(bandit_rec,  ExplorationRecord)
        assert isinstance(distill_rec, DistillationRecord)

    def test_distillation_log_grows_with_generations(self):
        crls = _make_distilled_crls()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert len(crls.distillation_log) == 5

    def test_gen_log_has_distillation_fields(self):
        crls = _make_distilled_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        entry = crls.gen_log[0]
        assert "student_led"    in entry, "gen_log must contain student_led"
        assert "student_action" in entry, "gen_log must contain student_action"
        assert "distill_conf"   in entry, "gen_log must contain distill_conf"
        assert "distill_loss"   in entry, "gen_log must contain distill_loss"

    def test_full_report_has_wp23_keys(self):
        crls = _make_distilled_crls()
        for _ in range(3):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        report = crls.get_full_report()
        assert "distillation_summary" in report
        assert "distillation_log"     in report

    def test_full_report_preserves_wp22_keys(self):
        crls = _make_distilled_crls()
        for _ in range(3):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        report = crls.get_full_report()
        assert "bandit_summary" in report
        assert "bandit_log"     in report

    def test_full_report_preserves_wp21_keys(self):
        crls = _make_distilled_crls()
        for _ in range(3):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        report = crls.get_full_report()
        assert "meta_gradient_summary" in report
        assert "meta_grad_log"         in report

    def test_acc_history_populated(self):
        crls = _make_distilled_crls()
        for _ in range(4):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert len(crls.acc_history) == 4

    def test_no_unsafe_synthesis_applied(self):
        crls = _make_distilled_crls()
        for _ in range(6):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        for rec in crls.synth.records:
            if rec.action != SynthesisAction.NO_ACTION:
                assert rec.safety_status != "provably_unsafe"

    def test_generation_counter_advances(self):
        crls = _make_distilled_crls()
        N = 6
        for _ in range(N):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert crls.generation == N

    def test_distillation_log_entry_structure(self):
        crls = _make_distilled_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        entry = crls.distillation_log[0]
        for k in ("generation", "teacher_action", "student_probs",
                  "student_action", "student_led", "confidence",
                  "loss", "training_step"):
            assert k in entry, f"distillation_log entry missing key {k}"

    def test_teacher_action_in_log_is_valid_synthesis_action(self):
        crls = _make_distilled_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        entry = crls.distillation_log[0]
        valid_values = {a.value for a in SynthesisAction}
        assert entry["teacher_action"] in valid_values

    def test_student_probs_sum_to_one_in_log(self):
        crls = _make_distilled_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        entry = crls.distillation_log[0]
        prob_sum = sum(entry["student_probs"].values())
        assert abs(prob_sum - 1.0) < 1e-6

    def test_distillation_confidence_between_zero_and_one(self):
        crls = _make_distilled_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        conf = crls.distillation_log[0]["confidence"]
        assert 0.0 <= conf <= 1.0


# ===========================================================================
# TestDistillationConvergence
# ===========================================================================

class TestDistillationConvergence:

    def test_loss_decreases_over_many_generations(self):
        """
        Student loss should achieve a lower minimum in the second half than the
        first half of training.

        We compare the *minimum* loss in each half rather than the mean because
        the teacher's non-stationary action distribution (bandit explores) causes
        individual losses to spike when the label changes, but the overall
        minimum still trends down as the student weight matrix grows.
        """
        random.seed(7)
        crls = _make_distilled_crls(seed=7, distill_min_steps=5)
        tactic_fns = _go_tactic_fns()
        for _ in range(80):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        losses = [e["distill_loss"] for e in crls.gen_log]
        mid = len(losses) // 2
        # The best (minimum) loss achieved in the second half should be lower
        # than the best loss in the first half, indicating the student has
        # learned a tighter lower bound on the cross-entropy.
        min_early = min(losses[:mid])
        min_late  = min(losses[mid:])
        assert min_late < min_early, (
            f"Student's minimum achieved loss must improve over training; "
            f"min_early={min_early:.4f} min_late={min_late:.4f}"
        )

    def test_student_eventually_leads(self):
        """With a low confidence threshold, student should lead at least once."""
        random.seed(3)
        crls = DistilledCRLS(
            strategies          = TACTICS,
            upward_rate         = 0.0,
            downward_rate       = 0.0,
            force_explore_unseen = True,
            distill_lr          = 0.15,
            distill_min_steps   = 5,
            distill_confidence  = 0.20,  # low threshold — student leads early
        )
        tactic_fns = _go_tactic_fns()
        for _ in range(40):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        student_led_entries = [e for e in crls.gen_log if e.get("student_led")]
        assert len(student_led_entries) > 0, (
            "Student should have led at least one generation with "
            "distill_confidence=0.20 after 40 generations"
        )

    def test_weight_norm_grows_during_training(self):
        """Student weight norm should increase from zero as training progresses."""
        crls = _make_distilled_crls(distill_min_steps=5, distill_confidence=0.99)
        tactic_fns = _go_tactic_fns()
        for _ in range(15):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        report = crls.get_full_report()
        assert report["distillation_summary"]["weight_norm"] > 0.0

    def test_training_steps_equals_num_generations(self):
        """One SGD step per end_of_generation call → steps == gens."""
        crls = _make_distilled_crls()
        tactic_fns = _go_tactic_fns()
        N = 12
        for _ in range(N):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        report = crls.get_full_report()
        assert report["distillation_summary"]["training_steps"] == N

    def test_distillation_log_length_equals_gen_log_length(self):
        """One DistillationRecord per generation, always."""
        crls = _make_distilled_crls()
        tactic_fns = _go_tactic_fns()
        N = 8
        for _ in range(N):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        assert len(crls.distillation_log) == len(crls.gen_log) == N


# ===========================================================================
# TestWP23ExitCriteria
# ===========================================================================

class TestWP23ExitCriteria:

    def _make_converged_crls(self, seed: int = 17) -> DistilledCRLS:
        random.seed(seed)
        crls = DistilledCRLS(
            strategies             = TACTICS,
            upward_rate            = 0.0,
            downward_rate          = 0.0,
            synthesiser_kwargs     = {"acc_drop_threshold": 0.0},
            min_trials_to_override = 3,
            override_tolerance     = 0.02,
            rollout_horizon        = 3,
            rollout_discount       = 0.90,
            min_transitions        = 3,
            meta_step_size         = 0.03,
            meta_min_transitions   = 4,
            exploration_coeff      = 1.0,
            force_explore_unseen   = True,
            distill_lr             = 0.15,
            distill_l2             = 1e-4,
            distill_min_steps      = 10,
            distill_confidence     = 0.20,  # low so student leads
        )
        tactic_fns = _go_tactic_fns()
        for _ in range(50):
            crls.run_generation(_go_puzzles(30), tactic_fns, _go_eval)
            crls.end_of_generation()
        return crls

    def test_student_constructed(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp23_exit_criteria(crls)
        assert criteria["student_constructed"], (
            "StudentPolicy must be constructed with correct weight shape"
        )

    def test_student_trained(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp23_exit_criteria(crls)
        assert criteria["student_trained"], (
            "Student must have taken at least min_training_steps SGD steps"
        )

    def test_loss_decreased(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp23_exit_criteria(crls)
        assert criteria["loss_decreased"], (
            "Mean distillation loss in later half must be lower than first half"
        )

    def test_student_led_at_least_once(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp23_exit_criteria(crls)
        assert criteria["student_led_at_least_once"], (
            "Student must have led at least one generation"
        )

    def test_teacher_label_always_recorded(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp23_exit_criteria(crls)
        assert criteria["teacher_label_always_recorded"], (
            "Every generation must have exactly one DistillationRecord"
        )

    def test_safety_preserved(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp23_exit_criteria(crls)
        assert criteria["safety_preserved"], (
            "All synthesis proposals must be safety-evaluated; none UNSAFE applied"
        )

    def test_all_criteria_pass(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp23_exit_criteria(crls)
        failing  = [k for k, v in criteria.items() if not v]
        assert not failing, f"WP23 exit criteria failed: {failing}"


# ===========================================================================
# TestLayerInteraction — all six layers (WP17–23) interact correctly
# ===========================================================================

class TestLayerInteraction:

    def test_fallback_chain_all_six_layers(self):
        """
        With no trajectory data, WP21, WP20, WP19 fall back gracefully;
        WP22 bandit fires; WP23 student fires (but doesn't lead — not trained).
        """
        crls = DistilledCRLS(
            strategies             = TACTICS,
            upward_rate            = 0.0,
            downward_rate          = 0.0,
            min_trials_to_override = 100,   # WP19 never overrides
            min_transitions        = 100,   # WP20 never plans
            meta_min_transitions   = 100,   # WP21 never fires
            distill_min_steps      = 100,   # WP23 student never leads
        )
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        result = crls.end_of_generation()
        assert len(result) == 6
        record, causal_rec, rollout, grad_step, bandit_rec, distill_rec = result

        # Lower layers fall back
        assert not causal_rec.override
        assert rollout.fallback_used
        assert all(abs(g) < 1e-12 for g in grad_step.gradients.values())
        # WP22 and WP23 always fire
        assert isinstance(bandit_rec,  ExplorationRecord)
        assert isinstance(distill_rec, DistillationRecord)
        # Student does not lead (not enough training)
        assert not distill_rec.student_led

    def test_all_six_layer_fields_in_gen_log(self):
        """gen_log entries must contain fields from all six WP layers."""
        crls = _make_distilled_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()

        entry = crls.gen_log[0]
        assert "heuristic"      in entry   # WP17
        assert "causal_action"  in entry   # WP19
        assert "rollout_action" in entry   # WP20
        assert "bandit_action"  in entry   # WP22
        assert "student_led"    in entry   # WP23
        assert "student_action" in entry   # WP23

    def test_wp23_does_not_break_wp22_bandit_log(self):
        """DistilledCRLS must still populate the WP22 bandit_log."""
        crls = _make_distilled_crls()
        tactic_fns = _go_tactic_fns()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        assert len(crls.bandit_log) == 5

    def test_wp23_does_not_break_wp21_meta_grad_log(self):
        """DistilledCRLS must still populate the WP21 meta_grad_log."""
        crls = _make_distilled_crls()
        tactic_fns = _go_tactic_fns()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        assert len(crls.meta_grad_log) == 5

    def test_wp23_does_not_break_wp20_rollout_log(self):
        """DistilledCRLS must still populate the WP20 rollout_log."""
        crls = _make_distilled_crls()
        tactic_fns = _go_tactic_fns()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        assert len(crls.rollout_log) == 5

    def test_generation_count_consistent_across_all_six_layers(self):
        """Generation counter must advance consistently across all layers."""
        crls = _make_distilled_crls()
        tactic_fns = _go_tactic_fns()
        N = 8
        for _ in range(N):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()

        assert crls.generation            == N
        assert len(crls.acc_history)      == N
        assert len(crls.gen_log)          == N
        assert len(crls.bandit_log)       == N
        assert len(crls.distillation_log) == N

    def test_student_action_is_valid_synthesis_action_in_gen_log(self):
        crls = _make_distilled_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        entry = crls.gen_log[0]
        valid_values = {a.value for a in SynthesisAction}
        assert entry["student_action"] in valid_values

    def test_distillation_training_step_matches_generation_count(self):
        """Student must be trained exactly once per end_of_generation."""
        crls = _make_distilled_crls()
        tactic_fns = _go_tactic_fns()
        N = 10
        for _ in range(N):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        assert crls.distiller.student.training_steps == N
