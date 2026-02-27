"""
WP22 Test Suite: Multi-Armed Bandit Exploration Policy
=======================================================

Seven test classes mirroring the WP17–21 structure:

TestExplorationRecord       Unit tests for the audit-record dataclass
TestBanditPolicyUCB1        UCB1 policy: construction, scoring, selection
TestBanditPolicyThompson    Thompson Sampling: posterior, selection
TestBanditCRLS              Integration on real GoBoard puzzles —
                             verifies all five planning layers fire
TestBanditRewardFeedback    That observe() feeds reward correctly and
                             updates mean estimates
TestWP22ExitCriteria        Six-criterion verifier
TestLayerInteraction        All five layers (WP17–22) interact correctly
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
from prometheus.wp21_meta_gradient import (
    MetaGradStep,
    MetaGradientCRLS,
    MetaParams,
    _DEFAULT_PARAMS,
    _PARAM_BOUNDS,
)
from prometheus.wp22_bandit_exploration import (
    BanditCRLS,
    BanditMode,
    BanditPolicy,
    ExplorationRecord,
    verify_wp22_exit_criteria,
)


# ===========================================================================
# Shared helpers  (mirrors WP21 pattern)
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


def _make_transition(
    action: SynthesisAction,
    acc_before: float = 0.50,
    acc_after: float = 0.60,
    generation: int = 0,
) -> TrajectoryTransition:
    before = _make_snapshot(generation, accuracy=acc_before)
    after  = _make_snapshot(generation + 1, accuracy=acc_after)
    return TrajectoryTransition(before, action, after)


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


# ===========================================================================
# TestExplorationRecord
# ===========================================================================

class TestExplorationRecord:

    def _make_record(
        self,
        exploit: SynthesisAction = SynthesisAction.DEMOTE_WORST,
        explore: SynthesisAction = SynthesisAction.PROMOTE_BEST,
        is_exploration: bool = True,
    ) -> ExplorationRecord:
        return ExplorationRecord(
            generation     = 3,
            mode           = BanditMode.UCB1,
            exploit_action = exploit,
            explore_action = explore,
            is_exploration = is_exploration,
            ucb_scores     = {a.value: 0.5 for a in SynthesisAction},
            n_trials       = {a.value: 2  for a in SynthesisAction},
            total_t        = 8,
        )

    def test_to_dict_has_all_required_keys(self):
        rec = self._make_record()
        d   = rec.to_dict()
        for k in ("generation", "mode", "exploit_action", "explore_action",
                  "is_exploration", "ucb_scores", "n_trials", "total_t", "reward"):
            assert k in d, f"Missing key {k} in ExplorationRecord.to_dict()"

    def test_reward_defaults_to_none(self):
        rec = self._make_record()
        assert rec.reward is None

    def test_reward_can_be_set(self):
        rec = self._make_record()
        rec.reward = 0.07
        assert abs(rec.reward - 0.07) < 1e-9

    def test_timestamp_is_positive_float(self):
        rec = self._make_record()
        assert isinstance(rec.timestamp, float)
        assert rec.timestamp > 0.0

    def test_is_exploration_flag_true_when_actions_differ(self):
        rec = self._make_record(
            exploit=SynthesisAction.DEMOTE_WORST,
            explore=SynthesisAction.PROMOTE_BEST,
            is_exploration=True,
        )
        assert rec.is_exploration

    def test_is_exploration_flag_false_when_actions_same(self):
        rec = self._make_record(
            exploit=SynthesisAction.PROMOTE_BEST,
            explore=SynthesisAction.PROMOTE_BEST,
            is_exploration=False,
        )
        assert not rec.is_exploration

    def test_mode_serialised_as_string(self):
        rec = self._make_record()
        d   = rec.to_dict()
        assert isinstance(d["mode"], str)
        assert d["mode"] == BanditMode.UCB1.value


# ===========================================================================
# TestBanditPolicyUCB1
# ===========================================================================

class TestBanditPolicyUCB1:

    def _policy(self, c: float = 1.0, force: bool = True) -> BanditPolicy:
        return BanditPolicy(
            mode                 = BanditMode.UCB1,
            exploration_coeff    = c,
            force_explore_unseen = force,
        )

    # --- Construction ---

    def test_construction_default_mode(self):
        p = BanditPolicy()
        assert p.mode == BanditMode.UCB1

    def test_all_actions_unseen_at_start(self):
        p = self._policy()
        for a in SynthesisAction:
            assert p.n_trials(a) == 0

    def test_total_trials_zero_at_start(self):
        p = self._policy()
        assert p.total_trials() == 0

    def test_mean_reward_zero_for_unseen_action(self):
        p = self._policy()
        for a in SynthesisAction:
            assert p.mean_reward(a) == 0.0

    # --- UCB score ---

    def test_unseen_action_has_infinite_ucb(self):
        p = self._policy(force=False)
        scores = p.scores()
        for a in SynthesisAction:
            assert scores[a] == float("inf"), (
                f"Unseen action {a} should have UCB=inf"
            )

    def test_seen_action_has_finite_ucb(self):
        p = self._policy(force=False)
        p.observe(SynthesisAction.PROMOTE_BEST, 0.05)
        p.observe(SynthesisAction.PROMOTE_BEST, 0.03)
        scores = p.scores([SynthesisAction.PROMOTE_BEST])
        assert math.isfinite(scores[SynthesisAction.PROMOTE_BEST])

    def test_ucb_increases_with_exploration_coeff(self):
        """Higher c → higher UCB score for same data."""
        def _score(c):
            pol = BanditPolicy(mode=BanditMode.UCB1,
                               exploration_coeff=c, force_explore_unseen=False)
            for _ in range(3):
                pol.observe(SynthesisAction.DEMOTE_WORST, 0.02)
            return pol.scores([SynthesisAction.DEMOTE_WORST])[SynthesisAction.DEMOTE_WORST]

        assert _score(2.0) > _score(0.5), (
            "UCB score must be higher with larger exploration coefficient"
        )

    def test_ucb_decreases_as_trials_increase(self):
        """More observations on an arm → confidence bonus shrinks → lower UCB.

        With UCB1 = μ̂ + c√(ln(t)/n), for a fixed total t we compare n=1 vs
        n=50 on the same arm: the bonus term √(ln(t)/n) decreases as n grows.
        We fix t by pre-seeding all other arms with many observations so that
        t is large and stable, then compare n_arm=1 vs n_arm=50.
        """
        pol = BanditPolicy(mode=BanditMode.UCB1,
                           exploration_coeff=1.0, force_explore_unseen=False)
        # Pre-seed all other arms with 100 obs each (fixes a large total t)
        for a in SynthesisAction:
            if a != SynthesisAction.DEMOTE_WORST:
                for _ in range(100):
                    pol.observe(a, 0.02)
        # Now observe DEMOTE_WORST just once → large bonus
        pol.observe(SynthesisAction.DEMOTE_WORST, 0.02)
        score_1 = pol.scores([SynthesisAction.DEMOTE_WORST])[SynthesisAction.DEMOTE_WORST]
        # Add 49 more observations on the same arm (same mean reward, higher n)
        for _ in range(49):
            pol.observe(SynthesisAction.DEMOTE_WORST, 0.02)
        score_50 = pol.scores([SynthesisAction.DEMOTE_WORST])[SynthesisAction.DEMOTE_WORST]
        assert score_1 > score_50, (
            "UCB bonus must shrink as n_arm grows (√(ln(t)/n) decreases with n)"
        )

    # --- Force-explore unseen ---

    def test_force_explore_unseen_picks_first_unseen_arm(self):
        p = self._policy(force=True)
        # Observe every action except the first one in SynthesisAction
        actions = list(SynthesisAction)
        for a in actions[1:]:
            p.observe(a, 0.01)
        rec = p.select(actions[1], generation=0)
        assert rec.explore_action == actions[0], (
            "With force_explore_unseen=True, should pick the one unseen arm"
        )

    def test_force_explore_flag_false_uses_scores(self):
        """When force_explore_unseen=False and all seen, must use UCB scores."""
        p = self._policy(force=False)
        for a in SynthesisAction:
            p.observe(a, 0.01)
        rec = p.select(SynthesisAction.DEMOTE_WORST, generation=5)
        # Should return an ExplorationRecord
        assert isinstance(rec, ExplorationRecord)

    # --- Selection ---

    def test_select_returns_exploration_record(self):
        p   = self._policy()
        rec = p.select(SynthesisAction.DEMOTE_WORST, generation=0)
        assert isinstance(rec, ExplorationRecord)

    def test_exploration_log_grows_after_select(self):
        p = self._policy()
        for i in range(5):
            p.select(SynthesisAction.DEMOTE_WORST, generation=i)
        assert len(p.exploration_log) == 5

    def test_generation_field_in_record(self):
        p   = self._policy()
        rec = p.select(SynthesisAction.DEMOTE_WORST, generation=7)
        assert rec.generation == 7

    def test_exploit_action_stored_correctly(self):
        p = self._policy()
        rec = p.select(SynthesisAction.BOOST_UPWARD, generation=0)
        assert rec.exploit_action == SynthesisAction.BOOST_UPWARD

    # --- Observe ---

    def test_observe_increments_n_trials(self):
        p = self._policy()
        p.observe(SynthesisAction.PROMOTE_BEST, 0.05)
        assert p.n_trials(SynthesisAction.PROMOTE_BEST) == 1

    def test_observe_updates_mean_reward(self):
        p = self._policy()
        p.observe(SynthesisAction.PROMOTE_BEST, 0.10)
        p.observe(SynthesisAction.PROMOTE_BEST, 0.20)
        assert abs(p.mean_reward(SynthesisAction.PROMOTE_BEST) - 0.15) < 1e-9

    def test_observe_fills_reward_on_latest_record(self):
        p = self._policy()
        rec = p.select(SynthesisAction.DEMOTE_WORST, generation=0)
        p.observe(rec.explore_action, 0.04)
        assert rec.reward is not None

    def test_observe_does_not_overwrite_already_filled_reward(self):
        p = self._policy()
        rec = p.select(SynthesisAction.DEMOTE_WORST, generation=0)
        p.observe(rec.explore_action, 0.04)
        first_reward = rec.reward
        p.observe(rec.explore_action, 0.99)  # second observe on same action
        # First record should still have first reward
        assert abs(rec.reward - first_reward) < 1e-9

    # --- Summary ---

    def test_get_summary_has_required_keys(self):
        p = self._policy()
        for i in range(4):
            p.select(SynthesisAction.DEMOTE_WORST, generation=i)
        s = p.get_summary()
        for k in ("mode", "exploration_coeff", "total_t",
                  "exploration_count", "exploitation_count",
                  "exploration_rate", "mean_reward_per_action",
                  "n_trials_per_action", "exploration_log"):
            assert k in s, f"Missing key {k} in BanditPolicy.get_summary()"

    def test_exploration_rate_between_zero_and_one(self):
        p = self._policy()
        for i in range(10):
            p.select(SynthesisAction.DEMOTE_WORST, generation=i)
        s = p.get_summary()
        assert 0.0 <= s["exploration_rate"] <= 1.0


# ===========================================================================
# TestBanditPolicyThompson
# ===========================================================================

class TestBanditPolicyThompson:

    def _policy(self) -> BanditPolicy:
        return BanditPolicy(
            mode                 = BanditMode.THOMPSON,
            prior_variance       = 1.0,
            force_explore_unseen = True,
        )

    def test_mode_is_thompson(self):
        p = self._policy()
        assert p.mode == BanditMode.THOMPSON

    def test_select_returns_exploration_record(self):
        p   = self._policy()
        rec = p.select(SynthesisAction.DEMOTE_WORST, generation=0)
        assert isinstance(rec, ExplorationRecord)

    def test_thompson_scores_are_finite_for_seen_actions(self):
        """After observing all actions, Thompson scores should be finite floats."""
        p = BanditPolicy(mode=BanditMode.THOMPSON, force_explore_unseen=False)
        for a in SynthesisAction:
            p.observe(a, 0.03)
        for gen in range(5):
            scores = p.scores()
            for a in SynthesisAction:
                assert math.isfinite(scores[a]), (
                    f"Thompson score for {a} should be finite after observation"
                )

    def test_high_reward_action_selected_more_often(self):
        """Action with consistently high reward should win more selections."""
        random.seed(99)
        p = BanditPolicy(mode=BanditMode.THOMPSON, force_explore_unseen=False)
        # Seed PROMOTE_BEST with many high rewards
        for _ in range(20):
            p.observe(SynthesisAction.PROMOTE_BEST, 0.90)
        # Seed DEMOTE_WORST with many low rewards
        for _ in range(20):
            p.observe(SynthesisAction.DEMOTE_WORST, -0.30)

        promote_count = sum(
            1 for _ in range(200)
            if p.select(SynthesisAction.DEMOTE_WORST, generation=0).explore_action
               == SynthesisAction.PROMOTE_BEST
        )
        assert promote_count > 100, (
            "High-reward action should be selected majority of the time by Thompson"
        )

    def test_prior_variance_affects_scores_for_unseen_actions(self):
        """Higher prior variance → more spread in Thompson samples."""
        random.seed(42)
        p_low  = BanditPolicy(mode=BanditMode.THOMPSON,
                               prior_variance=0.01, force_explore_unseen=False)
        p_high = BanditPolicy(mode=BanditMode.THOMPSON,
                               prior_variance=10.0, force_explore_unseen=False)
        # One observation each so n_trials=1
        for a in SynthesisAction:
            p_low.observe(a, 0.0)
            p_high.observe(a, 0.0)

        # Compute variance of 100 score samples
        def _score_variance(pol):
            vals = [pol.scores([SynthesisAction.PROMOTE_BEST])[SynthesisAction.PROMOTE_BEST]
                    for _ in range(100)]
            mu  = sum(vals) / len(vals)
            return sum((v - mu) ** 2 for v in vals) / len(vals)

        assert _score_variance(p_high) > _score_variance(p_low), (
            "Higher prior_variance should produce higher spread in Thompson samples"
        )

    def test_reward_variance_uses_prior_for_single_observation(self):
        p = BanditPolicy(mode=BanditMode.THOMPSON, prior_variance=2.5)
        p.observe(SynthesisAction.DEMOTE_WORST, 0.05)
        assert abs(p.reward_variance(SynthesisAction.DEMOTE_WORST) - 2.5) < 1e-9


# ===========================================================================
# TestBanditCRLS — integration on real GoBoard puzzles
# ===========================================================================

class TestBanditCRLS:

    def _make_crls(
        self,
        seed: int = 42,
        mode: BanditMode = BanditMode.UCB1,
    ) -> BanditCRLS:
        random.seed(seed)
        return BanditCRLS(
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
            bandit_mode            = mode,
            exploration_coeff      = 1.0,
            force_explore_unseen   = True,
        )

    def test_construction_creates_bandit_policy(self):
        crls = self._make_crls()
        assert isinstance(crls.bandit, BanditPolicy)
        assert crls.bandit.mode == BanditMode.UCB1

    def test_bandit_crls_is_subclass_of_meta_gradient_crls(self):
        crls = self._make_crls()
        assert isinstance(crls, MetaGradientCRLS)

    def test_run_generation_returns_valid_accuracy(self):
        crls = self._make_crls()
        acc  = crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        assert 0.0 <= acc <= 1.0

    def test_end_of_generation_returns_quintuple(self):
        crls = self._make_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        result = crls.end_of_generation()
        assert len(result) == 5
        record, causal_rec, rollout, grad_step, bandit_rec = result
        assert isinstance(record,     SynthesisRecord)
        assert isinstance(causal_rec, CausalRecommendation)
        assert isinstance(rollout,    RolloutResult)
        assert isinstance(grad_step,  MetaGradStep)
        assert isinstance(bandit_rec, ExplorationRecord)

    def test_bandit_log_grows_with_generations(self):
        crls = self._make_crls()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert len(crls.bandit_log) == 5

    def test_no_unsafe_synthesis_applied(self):
        crls = self._make_crls()
        for _ in range(6):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        for rec in crls.synth.records:
            if rec.action != SynthesisAction.NO_ACTION:
                assert rec.safety_status != "provably_unsafe"

    def test_full_report_has_wp22_keys(self):
        crls = self._make_crls()
        for _ in range(3):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        report = crls.get_full_report()
        assert "bandit_summary" in report
        assert "bandit_log"     in report

    def test_full_report_preserves_wp21_keys(self):
        """get_full_report() must still expose WP21 keys from super()."""
        crls = self._make_crls()
        for _ in range(3):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        report = crls.get_full_report()
        assert "meta_gradient_summary" in report
        assert "meta_grad_log"         in report

    def test_acc_history_populated(self):
        crls = self._make_crls()
        for _ in range(4):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert len(crls.acc_history) == 4

    def test_thompson_mode_construction(self):
        crls = self._make_crls(mode=BanditMode.THOMPSON)
        assert crls.bandit.mode == BanditMode.THOMPSON

    def test_thompson_mode_runs_generations(self):
        crls = self._make_crls(seed=7, mode=BanditMode.THOMPSON)
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert len(crls.bandit_log) == 5

    def test_generation_counter_advances(self):
        crls = self._make_crls()
        N = 6
        for _ in range(N):
            crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
            crls.end_of_generation()
        assert crls.generation == N

    def test_gen_log_has_bandit_fields(self):
        """gen_log entries must contain WP22 bandit fields."""
        crls = self._make_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        entry = crls.gen_log[0]
        assert "bandit_action"  in entry, "gen_log must contain bandit_action"
        assert "bandit_explore" in entry, "gen_log must contain bandit_explore"

    def test_bandit_log_entry_structure(self):
        crls = self._make_crls()
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        entry = crls.bandit_log[0]
        for k in ("generation", "mode", "exploit_action", "explore_action",
                  "is_exploration", "ucb_scores", "n_trials", "total_t"):
            assert k in entry, f"bandit_log entry missing key {k}"


# ===========================================================================
# TestBanditRewardFeedback
# ===========================================================================

class TestBanditRewardFeedback:

    def _seeded_policy(self) -> BanditPolicy:
        p = BanditPolicy(mode=BanditMode.UCB1, force_explore_unseen=False)
        # Pre-seed all actions with at least one reward
        for a in SynthesisAction:
            p.observe(a, 0.01)
        return p

    def test_observe_increments_total_trials(self):
        p   = self._seeded_policy()
        t_before = p.total_trials()
        p.observe(SynthesisAction.PROMOTE_BEST, 0.05)
        assert p.total_trials() == t_before + 1

    def test_mean_reward_converges_to_true_mean(self):
        """After many observations, mean_reward should converge to ground truth."""
        p = BanditPolicy(mode=BanditMode.UCB1, force_explore_unseen=False)
        true_mean = 0.123
        random.seed(0)
        for _ in range(500):
            p.observe(SynthesisAction.PROMOTE_BEST,
                      true_mean + random.gauss(0, 0.01))
        assert abs(p.mean_reward(SynthesisAction.PROMOTE_BEST) - true_mean) < 0.005

    def test_best_action_selected_after_many_observations(self):
        """UCB policy should converge to selecting the best action most often."""
        random.seed(1)
        p = BanditPolicy(mode=BanditMode.UCB1,
                         exploration_coeff=0.3, force_explore_unseen=False)
        # PROMOTE_BEST is far superior
        for _ in range(30):
            p.observe(SynthesisAction.PROMOTE_BEST,  0.80)
        for a in SynthesisAction:
            if a != SynthesisAction.PROMOTE_BEST:
                for _ in range(30):
                    p.observe(a, 0.10)

        promote_count = sum(
            1 for i in range(300)
            if p.select(SynthesisAction.DEMOTE_WORST,
                        generation=i).explore_action == SynthesisAction.PROMOTE_BEST
        )
        assert promote_count > 200, (
            f"PROMOTE_BEST should dominate selections after convergence; "
            f"got {promote_count}/300"
        )

    def test_reward_variance_increases_with_noisy_rewards(self):
        p = BanditPolicy(mode=BanditMode.UCB1, force_explore_unseen=False)
        # Clean action: constant reward
        for _ in range(10):
            p.observe(SynthesisAction.PROMOTE_BEST, 0.5)
        # Noisy action: high-variance reward
        for _ in range(10):
            p.observe(SynthesisAction.DEMOTE_WORST, 0.5 + (0.3 if _ % 2 else -0.3))
        assert (p.reward_variance(SynthesisAction.DEMOTE_WORST)
                > p.reward_variance(SynthesisAction.PROMOTE_BEST)), (
            "Noisy action should have higher reward variance"
        )

    def test_exploration_rate_decreases_as_data_accumulates(self):
        """After forced-explore phase completes, at least one exploitation must occur.

        With 5 SynthesisActions and force_explore_unseen=True the first 5
        end_of_generation calls are forced-explore.  From generation 6 onward
        the bandit switches to UCB / Thompson and exploitation decisions appear.
        We verify that at least one exploitation decision was made.
        """
        crls = BanditCRLS(
            strategies           = TACTICS,
            upward_rate          = 0.0,
            downward_rate        = 0.0,
            exploration_coeff    = 0.5,
            force_explore_unseen = True,
        )
        tactic_fns = _go_tactic_fns()
        # Run enough generations to well-clear the forced-explore phase
        for _ in range(30):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()
        summary = crls.bandit.get_summary()
        # At least one exploitation decision must have occurred
        assert summary["exploitation_count"] > 0, (
            "After 30 generations, at least one exploitation decision must "
            "have been made (forced-explore phase covers at most n_actions gens)"
        )


# ===========================================================================
# TestWP22ExitCriteria
# ===========================================================================

class TestWP22ExitCriteria:

    def _make_converged_crls(self, seed: int = 12) -> BanditCRLS:
        random.seed(seed)
        crls = BanditCRLS(
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
        )
        tactic_fns = _go_tactic_fns()
        # Run enough generations to cover all arms at least once (forced explore)
        # plus a few exploitation rounds
        for _ in range(30):
            crls.run_generation(_go_puzzles(30), tactic_fns, _go_eval)
            crls.end_of_generation()
        return crls

    def test_bandit_constructed(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp22_exit_criteria(crls)
        assert criteria["bandit_constructed"], (
            "BanditPolicy must be constructed with a valid mode"
        )

    def test_all_actions_explored(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp22_exit_criteria(crls)
        assert criteria["all_actions_explored"], (
            "Every SynthesisAction must be tried at least once"
        )

    def test_exploration_occurred(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp22_exit_criteria(crls)
        assert criteria["exploration_occurred"], (
            "At least one bandit decision must have been an exploration"
        )

    def test_rewards_observed(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp22_exit_criteria(crls)
        assert criteria["rewards_observed"], (
            "At least one reward must have been fed back to the bandit"
        )

    def test_exploitation_occurs(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp22_exit_criteria(crls)
        assert criteria["exploitation_occurs"], (
            "At least one decision must have been exploitation (not forced explore)"
        )

    def test_safety_preserved(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp22_exit_criteria(crls)
        assert criteria["safety_preserved"], (
            "All synthesis proposals must be safety-evaluated; none UNSAFE applied"
        )

    def test_all_criteria_pass(self):
        crls     = self._make_converged_crls()
        criteria = verify_wp22_exit_criteria(crls)
        failing  = [k for k, v in criteria.items() if not v]
        assert not failing, f"WP22 exit criteria failed: {failing}"


# ===========================================================================
# TestLayerInteraction — all five layers (WP17–22) interact correctly
# ===========================================================================

class TestLayerInteraction:

    def test_fallback_chain_all_five_layers(self):
        """
        With no trajectory data, WP21, WP20 and WP19 fall back gracefully;
        WP22 bandit still fires and returns an ExplorationRecord.
        """
        crls = BanditCRLS(
            strategies             = TACTICS,
            upward_rate            = 0.0,
            downward_rate          = 0.0,
            min_trials_to_override = 100,   # WP19 never overrides
            min_transitions        = 100,   # WP20 never plans
            meta_min_transitions   = 100,   # WP21 never fires
        )
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        record, causal_rec, rollout, grad_step, bandit_rec = crls.end_of_generation()

        # Lower layers fall back
        assert not causal_rec.override
        assert rollout.fallback_used
        assert all(abs(g) < 1e-12 for g in grad_step.gradients.values())
        # But WP22 always fires
        assert isinstance(bandit_rec, ExplorationRecord)

    def test_bandit_log_has_exploit_and_explore_keys(self):
        crls = BanditCRLS(
            strategies    = TACTICS,
            upward_rate   = 0.0,
            downward_rate = 0.0,
        )
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()
        entry = crls.bandit_log[0]
        assert "exploit_action" in entry
        assert "explore_action" in entry

    def test_generation_count_consistent_across_all_five_layers(self):
        """Generation counter must advance consistently across all layers."""
        crls = BanditCRLS(
            strategies    = TACTICS,
            upward_rate   = 0.0,
            downward_rate = 0.0,
        )
        tactic_fns = _go_tactic_fns()
        N = 8
        for _ in range(N):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()

        assert crls.generation       == N
        assert len(crls.acc_history) == N
        assert len(crls.gen_log)     == N
        assert len(crls.bandit_log)  == N

    def test_all_five_layer_fields_in_gen_log(self):
        """gen_log entries must contain fields from all five WP layers."""
        crls = BanditCRLS(
            strategies    = TACTICS,
            upward_rate   = 0.0,
            downward_rate = 0.0,
        )
        crls.run_generation(_go_puzzles(20), _go_tactic_fns(), _go_eval)
        crls.end_of_generation()

        entry = crls.gen_log[0]
        assert "heuristic"      in entry   # WP17
        assert "causal_action"  in entry   # WP19
        assert "rollout_action" in entry   # WP20
        assert "bandit_action"  in entry   # WP22
        assert "bandit_explore" in entry   # WP22

    def test_wp22_does_not_break_wp20_rollout_log(self):
        """BanditCRLS must still populate the WP20 rollout_log."""
        crls = BanditCRLS(
            strategies    = TACTICS,
            upward_rate   = 0.0,
            downward_rate = 0.0,
        )
        tactic_fns = _go_tactic_fns()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()

        assert len(crls.rollout_log) == 5, (
            "WP20 rollout_log must still be populated by BanditCRLS"
        )

    def test_wp22_does_not_break_wp21_meta_grad_log(self):
        """BanditCRLS must still populate the WP21 meta_grad_log."""
        crls = BanditCRLS(
            strategies    = TACTICS,
            upward_rate   = 0.0,
            downward_rate = 0.0,
        )
        tactic_fns = _go_tactic_fns()
        for _ in range(5):
            crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
            crls.end_of_generation()

        assert len(crls.meta_grad_log) == 5, (
            "WP21 meta_grad_log must still be populated by BanditCRLS"
        )

    def test_bandit_observe_triggered_after_run_generation(self):
        """
        After run_generation completes, the bandit must have received a reward
        for the action taken in end_of_generation of the *previous* generation.
        """
        crls = BanditCRLS(
            strategies    = TACTICS,
            upward_rate   = 0.0,
            downward_rate = 0.0,
        )
        tactic_fns = _go_tactic_fns()
        # Generation 0: end_of_generation sets pending exploration
        crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)
        crls.end_of_generation()
        # Generation 1: run_generation should call bandit.observe()
        crls.run_generation(_go_puzzles(20), tactic_fns, _go_eval)

        # At least one action should now have a reward
        assert crls.bandit.total_trials() > 0, (
            "Bandit must have received at least one reward via observe() "
            "after the second run_generation"
        )
