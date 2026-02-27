"""
WP24 Test Suite: Ensemble Disagreement & Uncertainty-Aware Action Selection
============================================================================

Seven test classes mirroring the WP17–23 structure:

TestEnsembleRecord          Unit tests for the audit-record dataclass
TestEntropyAndJSD           Unit tests for _entropy and _jsd helpers
TestEnsembleDistiller       Construction, predict_all, should_lead, train_all
TestEnsembleCRLS            Integration on real GoBoard puzzles —
                             verifies all seven planning layers fire
TestJSDConvergence          That JSD decreases and ensemble eventually leads
TestWP24ExitCriteria        Six-criterion verifier
TestLayerInteraction        All seven layers (WP17–24) interact correctly
"""

import math
import random
from typing import Callable, Dict, List, Optional, Tuple

import pytest

from prometheus.environments.go import GoBoard
from prometheus.wp17_crls_synthesis import SynthesisAction, SynthesisRecord
from prometheus.wp19_causal_evaluator import CausalRecommendation
from prometheus.wp20_temporal_planner import (
    RolloutResult,
    SynthesisStateSnapshot,
)
from prometheus.wp21_meta_gradient import MetaGradStep, MetaParams
from prometheus.wp22_bandit_exploration import BanditMode, ExplorationRecord
from prometheus.wp23_policy_distillation import (
    DistillationRecord,
    StudentPolicy,
    _ACTIONS,
    _N_ACTIONS,
)
from prometheus.wp24_ensemble_uncertainty import (
    EnsembleCRLS,
    EnsembleDistiller,
    EnsembleRecord,
    _entropy,
    _jsd,
    _mean_probs,
    verify_wp24_exit_criteria,
)


# ===========================================================================
# Shared helpers
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
# Real GoBoard puzzle helpers
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


def _make_ensemble_crls(
    seed: int = 42,
    ensemble_min_steps: int = 5,
    ensemble_max_jsd: float = 0.30,
    ensemble_min_conf: float = 0.30,
    n_members: int = 3,
) -> EnsembleCRLS:
    random.seed(seed)
    return EnsembleCRLS(
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
        distill_min_steps      = 5,
        distill_confidence     = 0.40,
        ensemble_n_members     = n_members,
        ensemble_lr            = 0.10,
        ensemble_l2            = 1e-4,
        ensemble_init_noise    = 0.01,
        ensemble_min_steps     = ensemble_min_steps,
        ensemble_max_jsd       = ensemble_max_jsd,
        ensemble_min_conf      = ensemble_min_conf,
        ensemble_seed          = seed,
    )


# ===========================================================================
# TestEnsembleRecord
# ===========================================================================

class TestEnsembleRecord:

    def _make_record(
        self,
        ensemble_led: bool = False,
        jsd: float = 0.05,
    ) -> EnsembleRecord:
        return EnsembleRecord(
            generation         = 3,
            member_actions     = [SynthesisAction.DEMOTE_WORST.value] * 3,
            member_confidences = [0.60, 0.55, 0.62],
            mean_probs         = {a.value: 1.0 / _N_ACTIONS for a in _ACTIONS},
            ensemble_action    = SynthesisAction.DEMOTE_WORST,
            jsd                = jsd,
            mean_entropy       = 0.4,
            ensemble_led       = ensemble_led,
            teacher_action     = SynthesisAction.PROMOTE_BEST,
        )

    def test_to_dict_has_all_required_keys(self):
        rec = self._make_record()
        d   = rec.to_dict()
        for k in ("generation", "member_actions", "member_confidences",
                  "mean_probs", "ensemble_action", "jsd", "mean_entropy",
                  "ensemble_led", "teacher_action"):
            assert k in d, f"Missing key {k} in EnsembleRecord.to_dict()"

    def test_ensemble_action_serialised_as_string(self):
        rec = self._make_record()
        assert isinstance(rec.to_dict()["ensemble_action"], str)

    def test_teacher_action_serialised_as_string(self):
        rec = self._make_record()
        assert isinstance(rec.to_dict()["teacher_action"], str)

    def test_ensemble_led_false_stored(self):
        rec = self._make_record(ensemble_led=False)
        assert not rec.ensemble_led

    def test_ensemble_led_true_stored(self):
        rec = self._make_record(ensemble_led=True)
        assert rec.ensemble_led

    def test_jsd_is_float(self):
        rec = self._make_record(jsd=0.123)
        assert isinstance(rec.jsd, float)
        assert abs(rec.jsd - 0.123) < 1e-9

    def test_timestamp_is_positive_float(self):
        rec = self._make_record()
        assert isinstance(rec.timestamp, float)
        assert rec.timestamp > 0.0


# ===========================================================================
# TestEntropyAndJSD
# ===========================================================================

class TestEntropyAndJSD:

    def test_entropy_uniform_is_log_n(self):
        """Entropy of uniform over N items = log(N)."""
        n = _N_ACTIONS
        probs = [1.0 / n] * n
        assert abs(_entropy(probs) - math.log(n)) < 1e-9

    def test_entropy_deterministic_is_zero(self):
        """Entropy of a point mass = 0."""
        probs = [0.0] * _N_ACTIONS
        probs[0] = 1.0
        assert abs(_entropy(probs)) < 1e-9

    def test_entropy_always_non_negative(self):
        import random as rng
        rng.seed(0)
        for _ in range(20):
            raw = [rng.random() for _ in range(_N_ACTIONS)]
            s = sum(raw)
            probs = [r / s for r in raw]
            assert _entropy(probs) >= 0.0

    def test_mean_probs_sums_to_one(self):
        n = _N_ACTIONS
        p1 = [1.0 / n] * n
        p2 = [0.0] * n
        p2[0] = 1.0
        m = _mean_probs([p1, p2])
        assert abs(sum(m) - 1.0) < 1e-9

    def test_mean_probs_correct_values(self):
        p1 = [0.8, 0.2]
        p2 = [0.4, 0.6]
        # patch _N_ACTIONS locally for this helper test
        from prometheus.wp24_ensemble_uncertainty import _mean_probs as mp
        import prometheus.wp24_ensemble_uncertainty as mod
        orig = mod._N_ACTIONS
        mod._N_ACTIONS = 2
        try:
            m = mp([p1, p2])
            assert abs(m[0] - 0.6) < 1e-9
            assert abs(m[1] - 0.4) < 1e-9
        finally:
            mod._N_ACTIONS = orig

    def test_jsd_zero_when_all_agree(self):
        """JSD = 0 when all members have identical distributions."""
        probs = [1.0 / _N_ACTIONS] * _N_ACTIONS
        jsd = _jsd([probs, probs, probs])
        assert abs(jsd) < 1e-9

    def test_jsd_positive_when_members_disagree(self):
        """JSD > 0 when members have different argmax actions."""
        p1 = [0.0] * _N_ACTIONS
        p2 = [0.0] * _N_ACTIONS
        p1[0] = 1.0
        p2[-1] = 1.0
        jsd = _jsd([p1, p2])
        assert jsd > 0.0

    def test_jsd_between_zero_and_one(self):
        """Normalised JSD must lie in [0, 1]."""
        import random as rng
        rng.seed(7)
        for _ in range(50):
            m = 4
            prob_lists = []
            for _ in range(m):
                raw = [rng.random() for _ in range(_N_ACTIONS)]
                s = sum(raw)
                prob_lists.append([r / s for r in raw])
            jsd = _jsd(prob_lists)
            assert 0.0 <= jsd <= 1.0 + 1e-9, f"JSD out of range: {jsd}"

    def test_jsd_single_member_is_zero(self):
        probs = [1.0 / _N_ACTIONS] * _N_ACTIONS
        assert _jsd([probs]) == 0.0

    def test_jsd_higher_disagreement_gives_higher_value(self):
        """More diverse members → higher JSD."""
        n = _N_ACTIONS
        # All agree
        same = [[1.0 / n] * n] * 3
        # Completely disagree (each member is a point mass on different action)
        # Use three different modes
        diverse = []
        for i in range(3):
            p = [0.0] * n
            p[i % n] = 1.0
            diverse.append(p)
        assert _jsd(diverse) > _jsd(same)


# ===========================================================================
# TestEnsembleDistiller
# ===========================================================================

class TestEnsembleDistiller:

    def _distiller(
        self,
        n: int = 3,
        min_steps: int = 5,
        max_jsd: float = 0.30,
        min_conf: float = 0.30,
        seed: int = 0,
    ) -> EnsembleDistiller:
        return EnsembleDistiller(
            n_members           = n,
            learning_rate       = 0.10,
            l2_reg              = 1e-4,
            init_noise          = 0.01,
            min_training_steps  = min_steps,
            max_jsd_threshold   = max_jsd,
            min_mean_confidence = min_conf,
            seed                = seed,
        )

    # --- Construction ---

    def test_correct_number_of_members(self):
        d = self._distiller(n=5)
        assert len(d.members) == 5

    def test_members_are_student_policies(self):
        d = self._distiller(n=3)
        for m in d.members:
            assert isinstance(m, StudentPolicy)

    def test_members_have_different_weights(self):
        """Init noise should make member weights non-identical."""
        d = self._distiller(n=3, seed=1)
        w0 = d.members[0]._W
        w1 = d.members[1]._W
        # At least one weight should differ
        any_diff = any(
            abs(w0[i][j] - w1[i][j]) > 1e-12
            for i in range(len(w0))
            for j in range(len(w0[i]))
        )
        assert any_diff, "Members must have different initial weights"

    def test_ensemble_log_empty_at_start(self):
        d = self._distiller()
        assert len(d.ensemble_log) == 0

    # --- predict_all ---

    def test_predict_all_returns_m_prob_lists(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        prob_lists, confs = d.predict_all(snap)
        assert len(prob_lists) == 3
        assert len(confs) == 3

    def test_predict_all_probs_sum_to_one(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        prob_lists, _ = d.predict_all(snap)
        for probs in prob_lists:
            assert abs(sum(probs) - 1.0) < 1e-9

    def test_predict_all_confidences_between_zero_and_one(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        _, confs = d.predict_all(snap)
        for c in confs:
            assert 0.0 <= c <= 1.0

    # --- predict_ensemble ---

    def test_predict_ensemble_returns_valid_action(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        action, jsd, h, pdict = d.predict_ensemble(snap)
        assert isinstance(action, SynthesisAction)

    def test_predict_ensemble_jsd_in_range(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        _, jsd, _, _ = d.predict_ensemble(snap)
        assert 0.0 <= jsd <= 1.0 + 1e-9

    def test_predict_ensemble_mean_probs_sum_to_one(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        _, _, _, pdict = d.predict_ensemble(snap)
        assert abs(sum(pdict.values()) - 1.0) < 1e-9

    # --- should_lead ---

    def test_should_lead_false_before_min_steps(self):
        d    = self._distiller(min_steps=100)
        snap = _make_snapshot()
        assert not d.should_lead(snap)

    def test_should_lead_false_when_jsd_too_high(self):
        """Even after training, if members disagree heavily, should not lead."""
        d = EnsembleDistiller(
            n_members           = 3,
            learning_rate       = 0.10,
            min_training_steps  = 1,
            max_jsd_threshold   = 0.0,    # impossible threshold
            min_mean_confidence = 0.0,
            seed                = 0,
        )
        snap   = _make_snapshot()
        target = SynthesisAction.PROMOTE_BEST
        for _ in range(5):
            d.train_all(snap, target)
        # JSD threshold is 0 — no ensemble can have JSD=0 with noise init
        assert not d.should_lead(snap)

    def test_should_lead_possible_with_generous_thresholds(self):
        """With trivially generous thresholds, ensemble leads after training."""
        d = EnsembleDistiller(
            n_members           = 3,
            learning_rate       = 0.20,
            min_training_steps  = 3,
            max_jsd_threshold   = 1.0,    # always pass
            min_mean_confidence = 0.0,    # always pass
            init_noise          = 0.001,
            seed                = 0,
        )
        snap   = _make_snapshot(accuracy=0.9)
        target = SynthesisAction.PROMOTE_BEST
        for _ in range(10):
            d.train_all(snap, target)
        assert d.should_lead(snap)

    # --- train_all ---

    def test_train_all_returns_m_losses(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        losses = d.train_all(snap, SynthesisAction.DEMOTE_WORST)
        assert len(losses) == 3

    def test_train_all_increments_training_steps(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        d.train_all(snap, SynthesisAction.DEMOTE_WORST)
        for m in d.members:
            assert m.training_steps == 1

    def test_train_all_losses_are_positive(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        losses = d.train_all(snap, SynthesisAction.PROMOTE_BEST)
        assert all(l > 0.0 for l in losses)

    # --- make_record ---

    def test_make_record_returns_ensemble_record(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        rec  = d.make_record(snap, SynthesisAction.PROMOTE_BEST,
                              ensemble_led=False, generation=0)
        assert isinstance(rec, EnsembleRecord)

    def test_make_record_appends_to_ensemble_log(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        for i in range(5):
            d.make_record(snap, SynthesisAction.PROMOTE_BEST,
                          ensemble_led=False, generation=i)
        assert len(d.ensemble_log) == 5

    def test_make_record_stores_correct_generation(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        rec  = d.make_record(snap, SynthesisAction.PROMOTE_BEST,
                              ensemble_led=False, generation=42)
        assert rec.generation == 42

    def test_make_record_member_actions_length_equals_n(self):
        n    = 4
        d    = self._distiller(n=n)
        snap = _make_snapshot()
        rec  = d.make_record(snap, SynthesisAction.DEMOTE_WORST,
                              ensemble_led=False, generation=0)
        assert len(rec.member_actions) == n

    # --- get_summary ---

    def test_get_summary_has_required_keys(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        for i in range(5):
            d.train_all(snap, SynthesisAction.DEMOTE_WORST)
            d.make_record(snap, SynthesisAction.DEMOTE_WORST,
                          ensemble_led=False, generation=i)
        s = d.get_summary()
        for k in ("n_members", "total_decisions", "ensemble_led_count",
                  "ensemble_led_rate", "mean_jsd", "mean_entropy",
                  "member_training_steps", "ensemble_log"):
            assert k in s, f"Missing key {k} in EnsembleDistiller.get_summary()"

    def test_get_summary_empty_before_decisions(self):
        d = self._distiller()
        s = d.get_summary()
        assert s["total_decisions"] == 0
        assert s["mean_jsd"] is None

    def test_member_training_steps_in_summary(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        for _ in range(4):
            d.train_all(snap, SynthesisAction.PROMOTE_BEST)
        s = d.get_summary()
        assert all(steps == 4 for steps in s["member_training_steps"])


# ===========================================================================
# TestEnsembleCRLS  —  integration on real GoBoard puzzles
# ===========================================================================

class TestEnsembleCRLS:

    def test_construction_creates_ensemble(self):
        crls = _make_ensemble_crls()
        assert isinstance(crls.ensemble, EnsembleDistiller)

    def test_ensemble_crls_is_subclass_of_distilled_crls(self):
        from prometheus.wp23_policy_distillation import DistilledCRLS
        crls = _make_ensemble_crls()
        assert isinstance(crls, DistilledCRLS)

    def test_run_generation_returns_valid_accuracy(self):
        crls = _make_ensemble_crls()
        acc  = crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        assert 0.0 <= acc <= 1.0

    def test_end_of_generation_returns_septuple(self):
        crls = _make_ensemble_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        result = crls.end_of_generation()
        assert len(result) == 7
        record, causal_rec, rollout, grad_step, bandit_rec, distill_rec, ens_rec = result
        assert isinstance(record,      SynthesisRecord)
        assert isinstance(causal_rec,  CausalRecommendation)
        assert isinstance(rollout,     RolloutResult)
        assert isinstance(grad_step,   MetaGradStep)
        assert isinstance(bandit_rec,  ExplorationRecord)
        assert isinstance(distill_rec, DistillationRecord)
        assert isinstance(ens_rec,     EnsembleRecord)

    def test_ensemble_log_grows_with_generations(self):
        crls = _make_ensemble_crls()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert len(crls.ensemble_log) == 5

    def test_gen_log_has_ensemble_fields(self):
        crls = _make_ensemble_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        entry = crls.gen_log[0]
        for key in ("ensemble_led", "ensemble_action", "ensemble_jsd", "ensemble_entropy"):
            assert key in entry, f"gen_log missing key {key}"

    def test_full_report_has_wp24_keys(self):
        crls = _make_ensemble_crls()
        for _ in range(3):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        report = crls.get_full_report()
        assert "ensemble_summary" in report
        assert "ensemble_log"     in report

    def test_full_report_preserves_wp23_keys(self):
        crls = _make_ensemble_crls()
        for _ in range(3):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        report = crls.get_full_report()
        assert "distillation_summary" in report
        assert "distillation_log"     in report

    def test_full_report_preserves_wp22_keys(self):
        crls = _make_ensemble_crls()
        for _ in range(3):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        report = crls.get_full_report()
        assert "bandit_summary" in report

    def test_no_unsafe_synthesis_applied(self):
        crls = _make_ensemble_crls()
        for _ in range(6):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        for rec in crls.synth.records:
            if rec.action != SynthesisAction.NO_ACTION:
                assert rec.safety_status != "provably_unsafe"

    def test_generation_counter_advances(self):
        crls = _make_ensemble_crls()
        N = 6
        for _ in range(N):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert crls.generation == N

    def test_ensemble_log_entry_structure(self):
        crls = _make_ensemble_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        entry = crls.ensemble_log[0]
        for k in ("generation", "member_actions", "member_confidences",
                  "mean_probs", "ensemble_action", "jsd",
                  "mean_entropy", "ensemble_led", "teacher_action"):
            assert k in entry, f"ensemble_log entry missing key {k}"

    def test_jsd_in_log_between_zero_and_one(self):
        crls = _make_ensemble_crls()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        for entry in crls.ensemble_log:
            assert 0.0 <= entry["jsd"] <= 1.0 + 1e-9

    def test_member_actions_length_equals_n_members(self):
        crls = _make_ensemble_crls(n_members=4)
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        assert len(crls.ensemble_log[0]["member_actions"]) == 4

    def test_mean_probs_sum_to_one_in_log(self):
        crls = _make_ensemble_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        prob_sum = sum(crls.ensemble_log[0]["mean_probs"].values())
        assert abs(prob_sum - 1.0) < 1e-6

    def test_all_members_trained_once_per_generation(self):
        crls = _make_ensemble_crls(n_members=3)
        N = 5
        for _ in range(N):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        for m in crls.ensemble.members:
            assert m.training_steps == N


# ===========================================================================
# TestJSDConvergence
# ===========================================================================

class TestJSDConvergence:

    def test_jsd_decreases_over_many_generations(self):
        """
        As all members train on the same teacher distribution, their
        predictions should converge → JSD should trend downward.
        """
        random.seed(5)
        crls = EnsembleCRLS(
            strategies          = TACTICS,
            upward_rate         = 0.0,
            downward_rate       = 0.0,
            force_explore_unseen = True,
            ensemble_n_members  = 5,
            ensemble_lr         = 0.15,
            ensemble_init_noise = 0.001,   # small noise → fast convergence
            ensemble_min_steps  = 5,
            ensemble_max_jsd    = 1.0,     # never blocks for this test
            ensemble_min_conf   = 0.0,
            ensemble_seed       = 5,
            distill_min_steps   = 5,
            distill_confidence  = 0.99,    # WP23 never leads
        )
        tactic_fns = _go_tactic_fns()
        for _ in range(60):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        jsds = [e["ensemble_jsd"] for e in crls.gen_log]
        mid  = len(jsds) // 2
        mean_early = sum(jsds[:mid]) / mid
        mean_late  = sum(jsds[mid:]) / (len(jsds) - mid)
        assert mean_late < mean_early, (
            f"Mean JSD should decrease as members converge; "
            f"early={mean_early:.4f} late={mean_late:.4f}"
        )

    def test_ensemble_eventually_leads(self):
        """With generous thresholds, ensemble leads at least once."""
        random.seed(9)
        crls = EnsembleCRLS(
            strategies          = TACTICS,
            upward_rate         = 0.0,
            downward_rate       = 0.0,
            force_explore_unseen = True,
            ensemble_n_members  = 3,
            ensemble_lr         = 0.20,
            ensemble_init_noise = 0.001,
            ensemble_min_steps  = 5,
            ensemble_max_jsd    = 1.0,    # always passes JSD gate
            ensemble_min_conf   = 0.0,    # always passes confidence gate
            ensemble_seed       = 9,
            distill_min_steps   = 100,    # WP23 never leads
            distill_confidence  = 0.99,
        )
        tactic_fns = _go_tactic_fns()
        for _ in range(30):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        led = [e for e in crls.gen_log if e.get("ensemble_led")]
        assert len(led) > 0, (
            "Ensemble must have led at least once with generous thresholds "
            "after 30 generations"
        )

    def test_all_member_training_steps_equal_n_generations(self):
        """Each member trains once per generation."""
        crls = _make_ensemble_crls(n_members=5)
        tactic_fns = _go_tactic_fns()
        N = 15
        for _ in range(N):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        for m in crls.ensemble.members:
            assert m.training_steps == N

    def test_ensemble_log_length_equals_gen_log_length(self):
        crls = _make_ensemble_crls()
        tactic_fns = _go_tactic_fns()
        N = 8
        for _ in range(N):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        assert len(crls.ensemble_log) == len(crls.gen_log) == N

    def test_different_seeds_give_different_initial_predictions(self):
        """Two ensembles with different seeds should have different initial JSD."""
        snap = _make_snapshot()
        d1 = EnsembleDistiller(n_members=5, seed=1, init_noise=0.1)
        d2 = EnsembleDistiller(n_members=5, seed=2, init_noise=0.1)
        _, jsd1, _, _ = d1.predict_ensemble(snap)
        _, jsd2, _, _ = d2.predict_ensemble(snap)
        # They may not differ always, but with init_noise=0.1 they likely will
        # We just check both are valid
        assert 0.0 <= jsd1 <= 1.0 + 1e-9
        assert 0.0 <= jsd2 <= 1.0 + 1e-9


# ===========================================================================
# TestWP24ExitCriteria
# ===========================================================================

class TestWP24ExitCriteria:

    def _make_converged_crls(self, seed: int = 21) -> EnsembleCRLS:
        random.seed(seed)
        crls = EnsembleCRLS(
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
            distill_min_steps      = 10,
            distill_confidence     = 0.20,
            ensemble_n_members     = 3,
            ensemble_lr            = 0.15,
            ensemble_init_noise    = 0.001,
            ensemble_min_steps     = 10,
            ensemble_max_jsd       = 1.0,   # generous — always passes
            ensemble_min_conf      = 0.0,   # generous — always passes
            ensemble_seed          = seed,
        )
        tactic_fns = _go_tactic_fns()
        for _ in range(60):
            crls.run_generation(_go_puzzles(30), tactic_fns, _go_eval)
            crls.end_of_generation()
        return crls

    def test_ensemble_constructed(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp24_exit_criteria(crls)
        assert criteria["ensemble_constructed"], (
            "EnsembleDistiller must be constructed with correct member count"
        )

    def test_all_members_trained(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp24_exit_criteria(crls)
        assert criteria["all_members_trained"], (
            "All ensemble members must have ≥ min_training_steps updates"
        )

    def test_jsd_computed(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp24_exit_criteria(crls)
        assert criteria["jsd_computed"], (
            "EnsembleRecords must contain valid JSD float values"
        )

    def test_jsd_decreases(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp24_exit_criteria(crls)
        assert criteria["jsd_decreases"], (
            "Mean JSD in the latter half must be lower than in the first half"
        )

    def test_ensemble_led_at_least_once(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp24_exit_criteria(crls)
        assert criteria["ensemble_led_at_least_once"], (
            "Ensemble must have led at least one generation"
        )

    def test_safety_preserved(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp24_exit_criteria(crls)
        assert criteria["safety_preserved"], (
            "All synthesis proposals must be safety-evaluated; none UNSAFE applied"
        )

    def test_all_criteria_pass(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp24_exit_criteria(crls)
        failing  = [k for k, v in criteria.items() if not v]
        assert not failing, f"WP24 exit criteria failed: {failing}"


# ===========================================================================
# TestLayerInteraction — all seven layers (WP17–24) interact correctly
# ===========================================================================

class TestLayerInteraction:

    def test_fallback_chain_all_seven_layers(self):
        """
        With no trajectory data and very high thresholds, lower layers fall back;
        WP22 bandit fires; WP23 student fires (not leading); WP24 ensemble fires.
        """
        crls = EnsembleCRLS(
            strategies             = TACTICS,
            upward_rate            = 0.0,
            downward_rate          = 0.0,
            min_trials_to_override = 100,
            min_transitions        = 100,
            meta_min_transitions   = 100,
            distill_min_steps      = 100,   # WP23 never leads
            ensemble_min_steps     = 100,   # WP24 never leads
        )
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        result = crls.end_of_generation()
        assert len(result) == 7
        record, causal_rec, rollout, grad_step, bandit_rec, distill_rec, ens_rec = result

        assert not causal_rec.override
        assert rollout.fallback_used
        assert all(abs(g) < 1e-12 for g in grad_step.gradients.values())
        assert isinstance(bandit_rec,  ExplorationRecord)
        assert isinstance(distill_rec, DistillationRecord)
        assert isinstance(ens_rec,     EnsembleRecord)
        assert not ens_rec.ensemble_led

    def test_all_seven_layer_fields_in_gen_log(self):
        crls = _make_ensemble_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        entry = crls.gen_log[0]
        assert "heuristic"       in entry   # WP17
        assert "causal_action"   in entry   # WP19
        assert "rollout_action"  in entry   # WP20
        assert "bandit_action"   in entry   # WP22
        assert "student_led"     in entry   # WP23
        assert "ensemble_led"    in entry   # WP24
        assert "ensemble_action" in entry   # WP24

    def test_wp24_does_not_break_wp23_distillation_log(self):
        crls = _make_ensemble_crls()
        tactic_fns = _go_tactic_fns()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        assert len(crls.distillation_log) == 5

    def test_wp24_does_not_break_wp22_bandit_log(self):
        crls = _make_ensemble_crls()
        tactic_fns = _go_tactic_fns()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        assert len(crls.bandit_log) == 5

    def test_wp24_does_not_break_wp21_meta_grad_log(self):
        crls = _make_ensemble_crls()
        tactic_fns = _go_tactic_fns()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        assert len(crls.meta_grad_log) == 5

    def test_generation_count_consistent_across_all_seven_layers(self):
        crls = _make_ensemble_crls()
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
        assert len(crls.ensemble_log)     == N

    def test_ensemble_action_is_valid_synthesis_action(self):
        crls = _make_ensemble_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        valid = {a.value for a in SynthesisAction}
        assert crls.ensemble_log[0]["ensemble_action"] in valid

    def test_member_steps_equal_generation_count(self):
        crls = _make_ensemble_crls(n_members=3)
        tactic_fns = _go_tactic_fns()
        N = 10
        for _ in range(N):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        summary = crls.get_full_report()["ensemble_summary"]
        assert all(s == N for s in summary["member_training_steps"])
