"""
WP25 Test Suite: Forgetting Detection & Elastic Weight Consolidation
=====================================================================

Seven test classes mirroring the WP17–24 structure:

TestForgettingRecord        Unit tests for the audit-record dataclass
TestEWCStudentPolicy        Fisher estimation, EWC penalty, consolidation
TestForgettingDetector      EMA smoothing, threshold logic, warm-up
TestEWCEnsembleDistiller    EWC members, train_all forgetting flags, consolidate_all
TestEWCEnsembleCRLS         Integration on real GoBoard puzzles —
                             verifies all eight planning layers fire
TestWP25ExitCriteria        Six-criterion verifier
TestLayerInteraction        All eight layers (WP17–25) interact correctly
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
    _ACTIONS,
    _N_ACTIONS,
)
from prometheus.wp24_ensemble_uncertainty import EnsembleRecord
from prometheus.wp25_ewc_forgetting import (
    EWCEnsembleCRLS,
    EWCEnsembleDistiller,
    EWCStudentPolicy,
    ForgettingDetector,
    ForgettingRecord,
    verify_wp25_exit_criteria,
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


def _make_ewc_crls(
    seed: int = 42,
    ewc_lambda: float = 1.0,
    forgetting_threshold: float = 0.05,   # low → events fire easily in tests
    ewc_min_steps: int = 5,
    n_members: int = 3,
) -> EWCEnsembleCRLS:
    random.seed(seed)
    return EWCEnsembleCRLS(
        strategies                  = TACTICS,
        upward_rate                 = 0.0,
        downward_rate               = 0.0,
        synthesiser_kwargs          = {"acc_drop_threshold": 0.0},
        min_trials_to_override      = 3,
        override_tolerance          = 0.02,
        rollout_horizon             = 3,
        rollout_discount            = 0.90,
        min_transitions             = 3,
        meta_step_size              = 0.02,
        meta_min_transitions        = 4,
        bandit_mode                 = BanditMode.UCB1,
        exploration_coeff           = 1.0,
        force_explore_unseen        = True,
        distill_lr                  = 0.10,
        distill_min_steps           = 5,
        distill_confidence          = 0.40,
        ensemble_n_members          = n_members,
        ensemble_lr                 = 0.10,
        ensemble_l2                 = 1e-4,
        ensemble_init_noise         = 0.01,
        ensemble_min_steps          = 5,
        ensemble_max_jsd            = 1.0,
        ensemble_min_conf           = 0.0,
        ensemble_seed               = seed,
        ewc_lambda                  = ewc_lambda,
        fisher_sample_size          = 20,
        forgetting_threshold        = forgetting_threshold,
        ema_alpha                   = 0.5,   # fast EMA for test speed
        ewc_min_steps_before_detect = ewc_min_steps,
    )


# ===========================================================================
# TestForgettingRecord
# ===========================================================================

class TestForgettingRecord:

    def _make_record(self) -> ForgettingRecord:
        return ForgettingRecord(
            generation              = 7,
            smoothed_loss           = 1.80,
            historical_min_loss     = 1.50,
            forgetting_delta        = 0.30,
            consolidation_triggered = True,
            ewc_lambda              = 1.0,
            n_fisher_samples        = 20,
            fisher_norm             = 0.42,
        )

    def test_to_dict_has_all_required_keys(self):
        rec = self._make_record()
        d   = rec.to_dict()
        for k in ("generation", "smoothed_loss", "historical_min_loss",
                  "forgetting_delta", "consolidation_triggered",
                  "ewc_lambda", "n_fisher_samples", "fisher_norm"):
            assert k in d, f"Missing key {k}"

    def test_consolidation_triggered_stored(self):
        rec = self._make_record()
        assert rec.consolidation_triggered

    def test_forgetting_delta_is_positive(self):
        rec = self._make_record()
        assert rec.forgetting_delta > 0

    def test_timestamp_is_positive_float(self):
        rec = self._make_record()
        assert isinstance(rec.timestamp, float)
        assert rec.timestamp > 0.0


# ===========================================================================
# TestEWCStudentPolicy
# ===========================================================================

class TestEWCStudentPolicy:

    def test_construction_no_consolidation(self):
        m = EWCStudentPolicy()
        assert not m.is_consolidated()

    def test_update_returns_positive_loss(self):
        m    = EWCStudentPolicy()
        snap = _make_snapshot()
        loss = m.update(snap, SynthesisAction.PROMOTE_BEST)
        assert loss > 0.0

    def test_update_increments_training_steps(self):
        m    = EWCStudentPolicy()
        snap = _make_snapshot()
        m.update(snap, SynthesisAction.DEMOTE_WORST)
        assert m.training_steps == 1

    def test_buffer_grows_up_to_max(self):
        m    = EWCStudentPolicy(fisher_sample_size=5)
        snap = _make_snapshot()
        for _ in range(10):
            m.update(snap, SynthesisAction.DEMOTE_WORST)
        assert len(m._buffer) == 5

    def test_fisher_norm_zero_before_consolidation(self):
        m = EWCStudentPolicy()
        assert m.fisher_norm() == 0.0

    def test_consolidate_sets_consolidated_flag(self):
        m    = EWCStudentPolicy()
        snap = _make_snapshot()
        for _ in range(5):
            m.update(snap, SynthesisAction.PROMOTE_BEST)
        m.consolidate()
        assert m.is_consolidated()

    def test_consolidate_makes_fisher_positive(self):
        m    = EWCStudentPolicy()
        snap = _make_snapshot()
        for _ in range(10):
            m.update(snap, SynthesisAction.PROMOTE_BEST)
        m.consolidate()
        assert m.fisher_norm() > 0.0

    def test_consolidate_snapshots_theta_star(self):
        m    = EWCStudentPolicy()
        snap = _make_snapshot()
        for _ in range(5):
            m.update(snap, SynthesisAction.DEMOTE_WORST)
        w_before = [list(row) for row in m._W]
        m.consolidate()
        # theta_star should equal W at consolidation time
        for i in range(_N_ACTIONS):
            for j in range(len(m._theta_star[i])):
                assert abs(m._theta_star[i][j] - w_before[i][j]) < 1e-9

    def test_ewc_penalty_reduces_weight_drift_from_theta_star(self):
        """
        After consolidation, a student with high ewc_lambda should
        move weights *less* than one with ewc_lambda=0 when given a
        different training signal.
        """
        snap_a = _make_snapshot(accuracy=0.8)
        snap_b = _make_snapshot(accuracy=0.2)

        # Consolidate on snap_a / PROMOTE_BEST
        def _train_and_consolidate(lam):
            m = EWCStudentPolicy(learning_rate=0.1, ewc_lambda=lam, fisher_sample_size=20)
            for _ in range(20):
                m.update(snap_a, SynthesisAction.PROMOTE_BEST)
            m.consolidate()
            # Now train on a conflicting signal (DEMOTE_WORST)
            for _ in range(20):
                m.update(snap_b, SynthesisAction.DEMOTE_WORST)
            # Return weight drift from theta_star
            drift = math.sqrt(sum(
                (m._W[i][j] - m._theta_star[i][j]) ** 2
                for i in range(_N_ACTIONS)
                for j in range(len(m._W[i]))
            ))
            return drift

        drift_no_ewc   = _train_and_consolidate(0.0)
        drift_with_ewc = _train_and_consolidate(5.0)
        assert drift_with_ewc < drift_no_ewc, (
            f"EWC must reduce weight drift; no_ewc={drift_no_ewc:.4f} "
            f"with_ewc={drift_with_ewc:.4f}"
        )

    def test_estimate_fisher_with_empty_buffer(self):
        """estimate_fisher on empty buffer should not raise."""
        m = EWCStudentPolicy()
        m.estimate_fisher()   # Should be a no-op
        assert m.fisher_norm() == 0.0

    def test_ewc_lambda_zero_equals_base_student(self):
        """With ewc_lambda=0 and consolidation, update must equal base student."""
        snap   = _make_snapshot()
        target = SynthesisAction.RESET_UNIFORM

        import copy
        m_base = EWCStudentPolicy(learning_rate=0.05, ewc_lambda=0.0)
        m_ewc  = EWCStudentPolicy(learning_rate=0.05, ewc_lambda=0.0)
        # Give both the same initial weights
        m_ewc._W = [list(row) for row in m_base._W]

        for _ in range(5):
            m_base.update(snap, target)
            m_ewc.update(snap, target)
        m_ewc.consolidate()

        # Now train on a different target — with lambda=0, EWC adds nothing
        for _ in range(5):
            m_base.update(snap, SynthesisAction.DEMOTE_WORST)
            m_ewc.update(snap,  SynthesisAction.DEMOTE_WORST)

        for i in range(_N_ACTIONS):
            for j in range(len(m_base._W[i])):
                assert abs(m_base._W[i][j] - m_ewc._W[i][j]) < 1e-9, (
                    "ewc_lambda=0 must give identical weights to base student"
                )


# ===========================================================================
# TestForgettingDetector
# ===========================================================================

class TestForgettingDetector:

    def test_no_event_during_warmup(self):
        det = ForgettingDetector(forgetting_threshold=0.01, ema_alpha=1.0,
                                 min_steps_before_detect=10)
        # Feed a high loss immediately — should not trigger during warmup
        for _ in range(9):
            event = det.update(2.0)
            assert not event

    def test_no_event_when_loss_at_minimum(self):
        det = ForgettingDetector(forgetting_threshold=0.10, ema_alpha=1.0,
                                 min_steps_before_detect=3)
        for _ in range(5):
            assert not det.update(1.0)   # flat loss, at its min

    def test_event_fires_when_loss_spikes(self):
        det = ForgettingDetector(forgetting_threshold=0.10, ema_alpha=1.0,
                                 min_steps_before_detect=3)
        # Drive min down
        for _ in range(5):
            det.update(1.0)
        # Now spike — with alpha=1.0, smoothed = current; delta = 0.20 > 0.10
        event = det.update(1.20)
        assert event

    def test_historical_min_tracks_minimum(self):
        det = ForgettingDetector(forgetting_threshold=1.0, ema_alpha=1.0,
                                 min_steps_before_detect=1)
        losses = [2.0, 1.5, 1.0, 1.8]
        for l in losses:
            det.update(l)
        assert abs(det.historical_min - 1.0) < 1e-9

    def test_smoothed_loss_is_ema(self):
        """With alpha=0.5, smoothed should be EMA of the series."""
        det = ForgettingDetector(forgetting_threshold=999, ema_alpha=0.5,
                                 min_steps_before_detect=1)
        det.update(1.0)   # smoothed = 1.0
        det.update(2.0)   # smoothed = 0.5*2.0 + 0.5*1.0 = 1.5
        assert abs(det.smoothed_loss - 1.5) < 1e-9

    def test_get_summary_has_required_keys(self):
        det = ForgettingDetector()
        for _ in range(5):
            det.update(1.0)
        s = det.get_summary()
        for k in ("steps", "smoothed_loss", "historical_min", "forgetting_delta"):
            assert k in s, f"Missing key {k} in ForgettingDetector.get_summary()"

    def test_step_counter_increments(self):
        det = ForgettingDetector(min_steps_before_detect=1)
        for i in range(7):
            det.update(1.0)
        assert det.get_summary()["steps"] == 7


# ===========================================================================
# TestEWCEnsembleDistiller
# ===========================================================================

class TestEWCEnsembleDistiller:

    def _distiller(
        self,
        n: int = 3,
        ewc_lambda: float = 1.0,
        forgetting_threshold: float = 0.05,
        seed: int = 0,
    ) -> EWCEnsembleDistiller:
        return EWCEnsembleDistiller(
            n_members               = n,
            learning_rate           = 0.10,
            l2_reg                  = 1e-4,
            init_noise              = 0.01,
            min_training_steps      = 5,
            max_jsd_threshold       = 1.0,
            min_mean_confidence     = 0.0,
            seed                    = seed,
            ewc_lambda              = ewc_lambda,
            fisher_sample_size      = 20,
            forgetting_threshold    = forgetting_threshold,
            ema_alpha               = 0.5,
            min_steps_before_detect = 3,
        )

    def test_members_are_ewc_student_policies(self):
        d = self._distiller(n=3)
        for m in d.members:
            assert isinstance(m, EWCStudentPolicy)

    def test_detectors_count_equals_n_members(self):
        n = 4
        d = self._distiller(n=n)
        assert len(d.detectors) == n

    def test_train_all_returns_losses_and_flags(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        losses, flags = d.train_all(snap, SynthesisAction.PROMOTE_BEST)
        assert len(losses) == 3
        assert len(flags) == 3

    def test_train_all_losses_are_positive(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        losses, _ = d.train_all(snap, SynthesisAction.DEMOTE_WORST)
        assert all(l > 0.0 for l in losses)

    def test_consolidate_all_returns_fisher_norms(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        for _ in range(10):
            d.train_all(snap, SynthesisAction.PROMOTE_BEST)
        norms = d.consolidate_all()
        assert len(norms) == 3
        assert all(isinstance(n, float) for n in norms)

    def test_n_consolidated_after_consolidate_all(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        for _ in range(10):
            d.train_all(snap, SynthesisAction.PROMOTE_BEST)
        d.consolidate_all()
        assert d.n_consolidated() == 3

    def test_mean_fisher_norm_positive_after_consolidation(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        for _ in range(10):
            d.train_all(snap, SynthesisAction.PROMOTE_BEST)
        d.consolidate_all()
        assert d.mean_fisher_norm() > 0.0

    def test_forgetting_flag_fires_on_loss_spike(self):
        """Feed a sustained low loss then spike — at least one flag should fire."""
        d    = self._distiller(n=1, forgetting_threshold=0.10)
        snap = _make_snapshot()
        # Warm up with low loss (target = action with high prob after training)
        for _ in range(10):
            d.train_all(snap, SynthesisAction.PROMOTE_BEST)
        # Now give a very different signal to spike loss
        # Feed many rounds to overcome EMA
        any_flag = False
        for _ in range(20):
            _, flags = d.train_all(snap, SynthesisAction.RESET_UNIFORM)
            if any(flags):
                any_flag = True
                break
        assert any_flag, (
            "Forgetting flag must fire after a sustained loss spike "
            "with threshold=0.10"
        )

    def test_forgetting_summary_has_required_keys(self):
        d    = self._distiller(n=3)
        snap = _make_snapshot()
        for _ in range(5):
            d.train_all(snap, SynthesisAction.DEMOTE_WORST)
        s = d.forgetting_summary()
        for k in ("n_members", "n_consolidated", "ewc_lambda",
                  "mean_fisher_norm", "member_steps", "detectors"):
            assert k in s, f"Missing key {k} in forgetting_summary()"


# ===========================================================================
# TestEWCEnsembleCRLS  —  integration on real GoBoard puzzles
# ===========================================================================

class TestEWCEnsembleCRLS:

    def test_construction_creates_ewc_ensemble(self):
        crls = _make_ewc_crls()
        assert isinstance(crls.ensemble, EWCEnsembleDistiller)

    def test_ewc_crls_is_subclass_of_ensemble_crls(self):
        from prometheus.wp24_ensemble_uncertainty import EnsembleCRLS
        crls = _make_ewc_crls()
        assert isinstance(crls, EnsembleCRLS)

    def test_run_generation_returns_valid_accuracy(self):
        crls = _make_ewc_crls()
        acc  = crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        assert 0.0 <= acc <= 1.0

    def test_end_of_generation_returns_octuple(self):
        crls = _make_ewc_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        result = crls.end_of_generation()
        assert len(result) == 8
        (record, causal_rec, rollout, grad_step,
         bandit_rec, distill_rec, ens_rec, forget_rec) = result
        assert isinstance(record,      SynthesisRecord)
        assert isinstance(causal_rec,  CausalRecommendation)
        assert isinstance(rollout,     RolloutResult)
        assert isinstance(grad_step,   MetaGradStep)
        assert isinstance(bandit_rec,  ExplorationRecord)
        assert isinstance(distill_rec, DistillationRecord)
        assert isinstance(ens_rec,     EnsembleRecord)
        # forget_rec is None when no event; ForgettingRecord otherwise
        assert forget_rec is None or isinstance(forget_rec, ForgettingRecord)

    def test_gen_log_has_ewc_fields(self):
        crls = _make_ewc_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        entry = crls.gen_log[0]
        for key in ("ewc_forgetting", "ewc_fisher_norm", "ewc_consolidated"):
            assert key in entry, f"gen_log missing key {key}"

    def test_full_report_has_wp25_keys(self):
        crls = _make_ewc_crls()
        for _ in range(3):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        report = crls.get_full_report()
        assert "ewc_summary"    in report
        assert "forgetting_log" in report

    def test_full_report_preserves_wp24_keys(self):
        crls = _make_ewc_crls()
        for _ in range(3):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        report = crls.get_full_report()
        assert "ensemble_summary" in report

    def test_no_unsafe_synthesis_applied(self):
        crls = _make_ewc_crls()
        for _ in range(6):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        for rec in crls.synth.records:
            if rec.action != SynthesisAction.NO_ACTION:
                assert rec.safety_status != "provably_unsafe"

    def test_generation_counter_advances(self):
        crls = _make_ewc_crls()
        N = 6
        for _ in range(N):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert crls.generation == N

    def test_all_members_are_ewc_student_policies(self):
        crls = _make_ewc_crls()
        for m in crls.ensemble.members:
            assert isinstance(m, EWCStudentPolicy)

    def test_forgetting_log_is_list(self):
        crls = _make_ewc_crls()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert isinstance(crls.forgetting_log, list)

    def test_ewc_fisher_norm_positive_in_gen_log_after_consolidation(self):
        """After a forgetting event fires (low threshold), fisher norm > 0."""
        crls = _make_ewc_crls(forgetting_threshold=0.001)  # very low → always fires
        tactic_fns = _go_tactic_fns()
        for _ in range(20):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        # At least some gen_log entries should have positive fisher norm
        positive = [e for e in crls.gen_log if e["ewc_fisher_norm"] > 0.0]
        assert len(positive) > 0

    def test_generation_count_consistent(self):
        crls = _make_ewc_crls()
        N = 8
        tactic_fns = _go_tactic_fns()
        for _ in range(N):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        assert crls.generation            == N
        assert len(crls.acc_history)      == N
        assert len(crls.gen_log)          == N
        assert len(crls.bandit_log)       == N
        assert len(crls.distillation_log) == N
        assert len(crls.ensemble_log)     == N


# ===========================================================================
# TestWP25ExitCriteria
# ===========================================================================

class TestWP25ExitCriteria:

    def _make_converged_crls(self, seed: int = 25) -> EWCEnsembleCRLS:
        random.seed(seed)
        crls = EWCEnsembleCRLS(
            strategies                  = TACTICS,
            upward_rate                 = 0.0,
            downward_rate               = 0.0,
            synthesiser_kwargs          = {"acc_drop_threshold": 0.0},
            min_trials_to_override      = 3,
            override_tolerance          = 0.02,
            rollout_horizon             = 3,
            rollout_discount            = 0.90,
            min_transitions             = 3,
            meta_step_size              = 0.03,
            meta_min_transitions        = 4,
            exploration_coeff           = 1.0,
            force_explore_unseen        = True,
            distill_lr                  = 0.15,
            distill_min_steps           = 10,
            distill_confidence          = 0.20,
            ensemble_n_members          = 3,
            ensemble_lr                 = 0.15,
            ensemble_init_noise         = 0.001,
            ensemble_min_steps          = 10,
            ensemble_max_jsd            = 1.0,
            ensemble_min_conf           = 0.0,
            ensemble_seed               = seed,
            ewc_lambda                  = 2.0,
            fisher_sample_size          = 20,
            forgetting_threshold        = 0.01,   # very low → events fire easily
            ema_alpha                   = 0.5,
            ewc_min_steps_before_detect = 5,
        )
        tactic_fns = _go_tactic_fns()
        for _ in range(50):
            crls.run_generation(_go_puzzles(30), tactic_fns, _go_eval)
            crls.end_of_generation()
        return crls

    def test_ewc_members_constructed(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp25_exit_criteria(crls)
        assert criteria["ewc_members_constructed"]

    def test_ewc_penalty_active(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp25_exit_criteria(crls)
        assert criteria["ewc_penalty_active"]

    def test_forgetting_detected(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp25_exit_criteria(crls)
        assert criteria["forgetting_detected"]

    def test_consolidation_triggered(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp25_exit_criteria(crls)
        assert criteria["consolidation_triggered"]

    def test_fisher_norm_positive(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp25_exit_criteria(crls)
        assert criteria["fisher_norm_positive"]

    def test_safety_preserved(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp25_exit_criteria(crls)
        assert criteria["safety_preserved"]

    def test_all_criteria_pass(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp25_exit_criteria(crls)
        failing  = [k for k, v in criteria.items() if not v]
        assert not failing, f"WP25 exit criteria failed: {failing}"


# ===========================================================================
# TestLayerInteraction — all eight layers (WP17–25) interact correctly
# ===========================================================================

class TestLayerInteraction:

    def test_fallback_chain_all_eight_layers(self):
        """Lower layers fall back; EWC guard fires; ForgettingRecord can be None."""
        crls = EWCEnsembleCRLS(
            strategies                  = TACTICS,
            upward_rate                 = 0.0,
            downward_rate               = 0.0,
            min_trials_to_override      = 100,
            min_transitions             = 100,
            meta_min_transitions        = 100,
            distill_min_steps           = 100,
            ensemble_min_steps          = 100,
            ewc_min_steps_before_detect = 100,
        )
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        result = crls.end_of_generation()
        assert len(result) == 8
        (record, causal_rec, rollout, grad_step,
         bandit_rec, distill_rec, ens_rec, forget_rec) = result
        assert not causal_rec.override
        assert rollout.fallback_used
        assert isinstance(ens_rec, EnsembleRecord)
        # No forgetting yet (warm-up not done)
        assert forget_rec is None

    def test_all_eight_layer_fields_in_gen_log(self):
        crls = _make_ewc_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        entry = crls.gen_log[0]
        assert "heuristic"       in entry   # WP17
        assert "causal_action"   in entry   # WP19
        assert "rollout_action"  in entry   # WP20
        assert "bandit_action"   in entry   # WP22
        assert "student_led"     in entry   # WP23
        assert "ensemble_led"    in entry   # WP24
        assert "ewc_forgetting"  in entry   # WP25
        assert "ewc_fisher_norm" in entry   # WP25

    def test_wp25_does_not_break_wp24_ensemble_log(self):
        crls = _make_ewc_crls()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert len(crls.ensemble_log) == 5

    def test_wp25_does_not_break_wp23_distillation_log(self):
        crls = _make_ewc_crls()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert len(crls.distillation_log) == 5

    def test_wp25_does_not_break_wp22_bandit_log(self):
        crls = _make_ewc_crls()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert len(crls.bandit_log) == 5

    def test_ewc_weight_drift_less_than_no_ewc(self):
        """
        EWC should limit weight drift from theta_star after a regime shift.
        We measure the mean Frobenius distance of member weights from theta_star.
        """
        snap_a = _make_snapshot(accuracy=0.9)
        snap_b = _make_snapshot(accuracy=0.1)

        def _run(ewc_lam):
            d = EWCEnsembleDistiller(
                n_members               = 1,
                learning_rate           = 0.15,
                ewc_lambda              = ewc_lam,
                fisher_sample_size      = 20,
                forgetting_threshold    = 999,   # no auto-trigger
                ema_alpha               = 0.5,
                min_steps_before_detect = 1,
                seed                    = 0,
            )
            # Phase 1: train on A / PROMOTE_BEST, then consolidate
            for _ in range(30):
                d.train_all(snap_a, SynthesisAction.PROMOTE_BEST)
            d.consolidate_all()
            star = [list(row) for row in d.members[0]._theta_star]
            # Phase 2: train on B / DEMOTE_WORST
            for _ in range(30):
                d.train_all(snap_b, SynthesisAction.DEMOTE_WORST)
            w_now = d.members[0]._W
            drift = math.sqrt(sum(
                (w_now[i][j] - star[i][j]) ** 2
                for i in range(_N_ACTIONS)
                for j in range(len(w_now[i]))
            ))
            return drift

        drift_no_ewc   = _run(0.0)
        drift_with_ewc = _run(5.0)
        assert drift_with_ewc < drift_no_ewc, (
            f"EWC must reduce weight drift; no_ewc={drift_no_ewc:.4f} "
            f"with_ewc={drift_with_ewc:.4f}"
        )

    def test_generation_count_consistent_across_all_eight_layers(self):
        crls = _make_ewc_crls()
        N = 8
        for _ in range(N):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert crls.generation            == N
        assert len(crls.acc_history)      == N
        assert len(crls.gen_log)          == N
        assert len(crls.bandit_log)       == N
        assert len(crls.distillation_log) == N
        assert len(crls.ensemble_log)     == N
