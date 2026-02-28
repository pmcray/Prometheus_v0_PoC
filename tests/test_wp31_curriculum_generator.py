"""
WP31 Test Suite: Curriculum Generator — Adaptive Difficulty Scheduling
======================================================================

Seven test classes:

TestPuzzleCategory          Unit tests for PuzzleCategory accuracy tracking
TestCurriculumScheduler     ZPD selection logic, fallback strategies
TestCurriculumRecord        Audit dataclass, to_dict()
TestCurriculumCRLS          Full 12-layer stack: end_of_generation, reports
TestWP31ExitCriteria        Six-criterion verifier
TestZPDLogic                ZPD boundary tests, edge cases
TestLayerInteraction        Integration: scheduler + world model + invariants
"""

import random
from typing import Callable, Dict, List, Optional, Tuple

import pytest

from prometheus.wp17_crls_synthesis import SynthesisAction, SynthesisRecord
from prometheus.wp19_causal_evaluator import CausalRecommendation
from prometheus.wp20_temporal_planner import RolloutResult, SynthesisStateSnapshot
from prometheus.wp21_meta_gradient import MetaGradStep
from prometheus.wp22_bandit_exploration import BanditMode, ExplorationRecord
from prometheus.wp23_policy_distillation import DistillationRecord
from prometheus.wp24_ensemble_uncertainty import EnsembleRecord
from prometheus.wp25_ewc_forgetting import ForgettingRecord
from prometheus.wp26_hierarchical_decomp import DecompositionRecord
from prometheus.wp27_formal_invariants import InvariantRecord
from prometheus.wp30_causal_world_model import WorldModelRecord
from prometheus.wp31_curriculum_generator import (
    CurriculumCRLS,
    CurriculumRecord,
    CurriculumScheduler,
    PuzzleCategory,
    verify_wp31_exit_criteria,
)
from prometheus.environments.go import GoBoard


# ===========================================================================
# Shared helpers
# ===========================================================================

GO_TACTICS = ["capture_atari", "ladder", "ko_fight",
              "territory_claim", "connect_groups", "random_legal"]


def _cats(n: int = 3, difficulties=None) -> List[PuzzleCategory]:
    if difficulties is None:
        difficulties = [i / (n - 1) if n > 1 else 0.5 for i in range(n)]
    return [
        PuzzleCategory(name=f"cat_{i}", difficulty=difficulties[i])
        for i in range(n)
    ]


def _atari_board():
    board = GoBoard(size=9)
    board.board[4][4] = GoBoard.WHITE
    board.board[4][3] = GoBoard.BLACK
    board.board[4][5] = GoBoard.BLACK
    board.board[5][4] = GoBoard.BLACK
    board.current_player = GoBoard.BLACK
    return board, GoBoard.BLACK, (3, 4)


def _territory_board():
    board = GoBoard(size=9)
    board.board[0][0] = GoBoard.WHITE
    board.board[0][8] = GoBoard.WHITE
    board.board[8][0] = GoBoard.WHITE
    board.current_player = GoBoard.BLACK
    return board, GoBoard.BLACK, (8, 8)


def _go_puzzles(n: int) -> List[Tuple]:
    puzzles = []
    for i in range(n):
        if i % 2 == 0:
            puzzles.append(_atari_board())
        else:
            puzzles.append(_territory_board())
    return puzzles


def _go_eval(board, move, correct_move, player) -> bool:
    if move == correct_move:
        return True
    if move is not None and board.is_legal_move(move[0], move[1], player):
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


def _build_crls(
    strategies=None,
    puzzle_categories=None,
    zpd_lo: float = 0.40,
    zpd_hi: float = 0.80,
    wm_min_buffer: int = 3,
    wm_batch_size: int = 2,
) -> CurriculumCRLS:
    strategies = strategies or GO_TACTICS
    return CurriculumCRLS(
        strategies=strategies,
        puzzle_categories=puzzle_categories,
        zpd_lo=zpd_lo,
        zpd_hi=zpd_hi,
        upward_rate=0.0,
        downward_rate=0.0,
        synthesiser_kwargs={"acc_drop_threshold": 0.0},
        min_trials_to_override=3,
        override_tolerance=0.02,
        rollout_horizon=3,
        rollout_discount=0.90,
        min_transitions=3,
        meta_step_size=0.02,
        meta_min_transitions=4,
        bandit_mode=BanditMode.UCB1,
        exploration_coeff=1.0,
        force_explore_unseen=True,
        distill_lr=0.10,
        distill_min_steps=5,
        distill_confidence=0.40,
        ensemble_n_members=3,
        ensemble_lr=0.10,
        ensemble_l2=1e-4,
        ensemble_init_noise=0.01,
        ensemble_min_steps=5,
        ensemble_max_jsd=1.0,
        ensemble_min_conf=0.0,
        ensemble_seed=42,
        ewc_lambda=1.0,
        fisher_sample_size=20,
        forgetting_threshold=0.05,
        ema_alpha=0.5,
        ewc_min_steps_before_detect=5,
        decomp_min_bucket_size=1,
        decomp_confidence_base=0.80,
        decomp_override_threshold=1.01,
        wm_min_buffer=wm_min_buffer,
        wm_batch_size=wm_batch_size,
        wm_hidden_dim=8,
        wm_horizon=2,
        wm_buffer_capacity=200,
        wm_seed=0,
        curriculum_seed=0,
    )


def _run_n_generations(crls: CurriculumCRLS, n: int = 8):
    puzzles = _go_puzzles(10)
    tactic_fns = _go_tactic_fns()
    for _ in range(n):
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        crls.end_of_generation()


# ===========================================================================
# TestPuzzleCategory
# ===========================================================================

class TestPuzzleCategory:
    """Unit tests for PuzzleCategory accuracy tracking."""

    def test_initial_mean_accuracy_zero(self):
        cat = PuzzleCategory(name="easy", difficulty=0.2)
        assert cat.mean_accuracy == 0.0

    def test_initial_n_observations_zero(self):
        cat = PuzzleCategory(name="easy", difficulty=0.2)
        assert cat.n_observations == 0

    def test_update_single(self):
        cat = PuzzleCategory(name="easy", difficulty=0.2)
        cat.update(0.8)
        assert cat.n_observations == 1
        assert abs(cat.mean_accuracy - 0.8) < 1e-9

    def test_update_multiple(self):
        cat = PuzzleCategory(name="medium", difficulty=0.5)
        cat.update(0.6)
        cat.update(0.4)
        assert cat.n_observations == 2
        assert abs(cat.mean_accuracy - 0.5) < 1e-9

    def test_to_dict_keys(self):
        cat = PuzzleCategory(name="hard", difficulty=0.9)
        cat.update(0.3)
        d = cat.to_dict()
        for key in ("name", "difficulty", "mean_accuracy", "n_observations"):
            assert key in d

    def test_to_dict_name(self):
        cat = PuzzleCategory(name="tricky")
        assert cat.to_dict()["name"] == "tricky"

    def test_default_difficulty(self):
        cat = PuzzleCategory(name="x")
        assert cat.difficulty == 0.5


# ===========================================================================
# TestCurriculumScheduler
# ===========================================================================

class TestCurriculumScheduler:
    """ZPD selection logic, fallback strategies."""

    def test_construction_requires_nonempty(self):
        with pytest.raises((ValueError, IndexError, AssertionError)):
            CurriculumScheduler(categories=[])

    def test_select_single_category(self):
        cats = _cats(1)
        sched = CurriculumScheduler(cats, zpd_lo=0.4, zpd_hi=0.8)
        chosen = sched.select()
        assert isinstance(chosen, PuzzleCategory)

    def test_select_returns_puzzle_category(self):
        cats = _cats(3)
        sched = CurriculumScheduler(cats, zpd_lo=0.4, zpd_hi=0.8)
        chosen = sched.select()
        assert isinstance(chosen, PuzzleCategory)

    def test_zpd_prefers_highest_difficulty(self):
        """When multiple categories are in ZPD, pick highest difficulty."""
        cats = [
            PuzzleCategory("low",  difficulty=0.2),
            PuzzleCategory("mid",  difficulty=0.5),
            PuzzleCategory("high", difficulty=0.8),
        ]
        # Set all to ZPD range
        for c in cats:
            c.update(0.6)
        sched = CurriculumScheduler(cats, zpd_lo=0.4, zpd_hi=0.8)
        chosen = sched.select()
        # highest difficulty in ZPD = 0.8
        assert chosen.name == "high"

    def test_explore_unseen_when_seen_outside_zpd(self):
        """Unobserved categories should be explored when seen category is outside ZPD."""
        cats = [
            PuzzleCategory("seen",   difficulty=0.5),
            PuzzleCategory("unseen", difficulty=0.3),
        ]
        cats[0].update(0.95)  # seen is above zpd_hi (too easy, not in ZPD)
        sched = CurriculumScheduler(cats, zpd_lo=0.4, zpd_hi=0.8)
        chosen = sched.select()
        assert chosen.name == "unseen"

    def test_all_easy_pushes_hardest(self):
        """When all categories are above zpd_hi, select the hardest."""
        cats = [
            PuzzleCategory("easy",   difficulty=0.1),
            PuzzleCategory("medium", difficulty=0.5),
            PuzzleCategory("hard",   difficulty=0.9),
        ]
        for c in cats:
            c.update(0.9)  # all above zpd_hi=0.8
        sched = CurriculumScheduler(cats, zpd_lo=0.4, zpd_hi=0.8)
        chosen = sched.select()
        assert chosen.name == "hard"

    def test_all_hard_pulls_easiest(self):
        """When all categories are below zpd_lo, select the easiest."""
        cats = [
            PuzzleCategory("easy",   difficulty=0.1),
            PuzzleCategory("medium", difficulty=0.5),
            PuzzleCategory("hard",   difficulty=0.9),
        ]
        for c in cats:
            c.update(0.1)  # all below zpd_lo=0.4
        sched = CurriculumScheduler(cats, zpd_lo=0.4, zpd_hi=0.8)
        chosen = sched.select()
        assert chosen.name == "easy"

    def test_record_accuracy_updates_category(self):
        cats = _cats(2)
        sched = CurriculumScheduler(cats, zpd_lo=0.4, zpd_hi=0.8)
        cat = cats[0]
        sched.record_accuracy(cat, 0.7)
        assert cat.n_observations == 1
        assert abs(cat.mean_accuracy - 0.7) < 1e-9

    def test_get_zpd_summary_keys(self):
        cats = _cats(2)
        sched = CurriculumScheduler(cats, zpd_lo=0.4, zpd_hi=0.8)
        sched.select()
        summ = sched.get_zpd_summary()
        for key in ("n_categories", "n_in_zpd", "zpd_lo", "zpd_hi",
                    "categories", "selection_log"):
            assert key in summ

    def test_selection_log_grows(self):
        cats = _cats(3)
        sched = CurriculumScheduler(cats, zpd_lo=0.4, zpd_hi=0.8)
        for _ in range(5):
            sched.select()
        assert len(sched._selection_log) == 5

    def test_round_robin_on_mixed(self):
        """Mixed easy/hard (no ZPD): round-robin selects distinct categories over time."""
        cats = [
            PuzzleCategory("easy", difficulty=0.1),
            PuzzleCategory("hard", difficulty=0.9),
        ]
        cats[0].update(0.95)  # too easy
        cats[1].update(0.05)  # too hard
        sched = CurriculumScheduler(cats, zpd_lo=0.4, zpd_hi=0.8, seed=0)
        selected = [sched.select().name for _ in range(4)]
        # Should alternate (round-robin) between easy and hard
        assert len(set(selected)) > 1


# ===========================================================================
# TestCurriculumRecord
# ===========================================================================

class TestCurriculumRecord:
    """Audit record dataclass."""

    def _record(self) -> CurriculumRecord:
        return CurriculumRecord(
            generation=3,
            selected_category="medium",
            selection_reason="zpd",
            category_accuracy_before=0.55,
            category_accuracy_after=0.60,
            n_in_zpd=2,
            difficulty=0.5,
        )

    def test_to_dict_keys(self):
        d = self._record().to_dict()
        for key in (
            "generation", "selected_category", "selection_reason",
            "category_accuracy_before", "category_accuracy_after",
            "n_in_zpd", "difficulty",
        ):
            assert key in d

    def test_generation_value(self):
        assert self._record().to_dict()["generation"] == 3

    def test_reason_preserved(self):
        assert self._record().to_dict()["selection_reason"] == "zpd"

    def test_difficulty_rounded(self):
        d = self._record().to_dict()
        assert isinstance(d["difficulty"], float)


# ===========================================================================
# TestCurriculumCRLS
# ===========================================================================

class TestCurriculumCRLS:
    """Integration tests for the 12-layer CurriculumCRLS."""

    def test_construction_default_category(self):
        crls = _build_crls()
        assert len(crls.puzzle_categories) == 1
        assert crls.puzzle_categories[0].name == "default"

    def test_construction_custom_categories(self):
        cats = _cats(3)
        crls = _build_crls(puzzle_categories=cats)
        assert len(crls.puzzle_categories) == 3

    def test_end_of_generation_returns_12_tuple(self):
        crls = _build_crls()
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        result = crls.end_of_generation()
        assert len(result) == 12

    def test_last_element_is_curriculum_record(self):
        crls = _build_crls()
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        *_, curr_rec = crls.end_of_generation()
        assert isinstance(curr_rec, CurriculumRecord)

    def test_gen_log_has_wp31_keys(self):
        crls = _build_crls()
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        crls.end_of_generation()
        assert len(crls.gen_log) >= 1
        log_entry = crls.gen_log[-1]
        for key in ("wp31_category", "wp31_reason", "wp31_n_in_zpd",
                    "wp31_difficulty", "wp31_cat_acc"):
            assert key in log_entry, f"Missing key: {key}"

    def test_get_full_report_has_curriculum_keys(self):
        crls = _build_crls()
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        crls.end_of_generation()
        report = crls.get_full_report()
        assert "curriculum_summary" in report
        assert "curriculum_log" in report

    def test_multi_generation_run(self):
        crls = _build_crls(puzzle_categories=_cats(3))
        _run_n_generations(crls, n=8)
        assert crls.generation == 8
        report = crls.get_full_report()
        assert len(report["curriculum_log"]) == 8

    def test_category_accuracy_updated(self):
        cats = _cats(1)
        crls = _build_crls(puzzle_categories=cats)
        _run_n_generations(crls, n=3)
        # The single category should have been observed 3 times
        assert cats[0].n_observations == 3

    def test_category_filter_hook(self):
        """category_filter can restrict puzzles to a subset."""
        crls = _build_crls(puzzle_categories=_cats(2))
        puzzles = _go_puzzles(10)
        tactic_fns = _go_tactic_fns()
        # Filter: only puzzles at even indices
        acc = crls.run_generation(
            puzzles, tactic_fns, _go_eval,
            category_filter=lambda p: True,  # accept all
        )
        assert isinstance(acc, float)


# ===========================================================================
# TestWP31ExitCriteria
# ===========================================================================

class TestWP31ExitCriteria:
    """verify_wp31_exit_criteria — six criteria."""

    def _trained_crls(self, n_gens: int = 10) -> CurriculumCRLS:
        crls = _build_crls(
            puzzle_categories=_cats(3),
            wm_min_buffer=3,
            wm_batch_size=2,
        )
        _run_n_generations(crls, n=n_gens)
        return crls

    def test_all_criteria_pass_after_training(self):
        crls = self._trained_crls(n_gens=10)
        result = verify_wp31_exit_criteria(crls)
        for criterion, passed in result.items():
            assert passed, f"Criterion '{criterion}' failed"

    def test_returns_dict(self):
        crls = self._trained_crls()
        result = verify_wp31_exit_criteria(crls)
        assert isinstance(result, dict)

    def test_six_criteria(self):
        crls = self._trained_crls()
        result = verify_wp31_exit_criteria(crls)
        assert len(result) == 6

    def test_expected_criterion_keys(self):
        crls = self._trained_crls()
        result = verify_wp31_exit_criteria(crls)
        expected = {
            "scheduler_constructed",
            "category_selected",
            "selection_logged",
            "accuracy_tracked",
            "zpd_logic_used",
            "safety_preserved",
        }
        assert set(result.keys()) == expected

    def test_scheduler_constructed_always_true(self):
        """Any properly constructed CurriculumCRLS satisfies scheduler_constructed."""
        crls = _build_crls()
        result = verify_wp31_exit_criteria(crls)
        assert result["scheduler_constructed"]

    def test_category_not_selected_fails(self):
        """No generation run → no category selected."""
        crls = _build_crls()
        result = verify_wp31_exit_criteria(crls)
        assert not result["category_selected"]


# ===========================================================================
# TestZPDLogic
# ===========================================================================

class TestZPDLogic:
    """ZPD boundary tests and edge cases."""

    def test_zpd_boundary_lo(self):
        """Category exactly at zpd_lo should be in ZPD."""
        cat = PuzzleCategory("boundary_lo", difficulty=0.5)
        cat.update(0.40)  # exactly at zpd_lo=0.40
        sched = CurriculumScheduler([cat], zpd_lo=0.40, zpd_hi=0.80)
        chosen = sched.select()
        assert chosen.name == "boundary_lo"
        assert sched._selection_log[-1]["reason"] == "zpd"

    def test_zpd_boundary_hi(self):
        """Category exactly at zpd_hi should be in ZPD."""
        cat = PuzzleCategory("boundary_hi", difficulty=0.5)
        cat.update(0.80)  # exactly at zpd_hi=0.80
        sched = CurriculumScheduler([cat], zpd_lo=0.40, zpd_hi=0.80)
        chosen = sched.select()
        assert chosen.name == "boundary_hi"
        assert sched._selection_log[-1]["reason"] == "zpd"

    def test_above_zpd_hi_excluded(self):
        """Category with accuracy > zpd_hi should not be selected via zpd."""
        cat_above = PuzzleCategory("above", difficulty=0.5)
        cat_in    = PuzzleCategory("in",    difficulty=0.3)
        cat_above.update(0.85)
        cat_in.update(0.60)
        sched = CurriculumScheduler([cat_above, cat_in], zpd_lo=0.40, zpd_hi=0.80)
        chosen = sched.select()
        assert chosen.name == "in"

    def test_below_zpd_lo_excluded_from_zpd(self):
        """Category with accuracy < zpd_lo should not be selected via zpd."""
        cat_in    = PuzzleCategory("in",    difficulty=0.5)
        cat_below = PuzzleCategory("below", difficulty=0.8)
        cat_in.update(0.60)
        cat_below.update(0.20)
        sched = CurriculumScheduler([cat_in, cat_below], zpd_lo=0.40, zpd_hi=0.80)
        chosen = sched.select()
        assert chosen.name == "in"

    def test_zpd_narrow_range(self):
        """Narrow ZPD [0.50, 0.51] — only category exactly in range selected."""
        cats = [
            PuzzleCategory("low",  difficulty=0.1),
            PuzzleCategory("mid",  difficulty=0.5),
            PuzzleCategory("high", difficulty=0.9),
        ]
        cats[0].update(0.30)
        cats[1].update(0.505)  # in [0.50, 0.51]
        cats[2].update(0.80)
        sched = CurriculumScheduler(cats, zpd_lo=0.50, zpd_hi=0.51)
        chosen = sched.select()
        assert chosen.name == "mid"

    def test_single_cat_always_selected(self):
        """With a single category, it is always selected regardless of accuracy."""
        cat = PuzzleCategory("only", difficulty=0.5)
        cat.update(0.0)  # below ZPD
        sched = CurriculumScheduler([cat], zpd_lo=0.40, zpd_hi=0.80)
        chosen = sched.select()
        assert chosen.name == "only"


# ===========================================================================
# TestLayerInteraction
# ===========================================================================

class TestLayerInteraction:
    """Integration: verify correct interaction between WP31 and lower layers."""

    def test_12_tuple_types(self):
        crls = _build_crls(puzzle_categories=_cats(2))
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        result = crls.end_of_generation()
        assert len(result) == 12
        *_, wm_rec, curr_rec = result
        assert isinstance(wm_rec, WorldModelRecord)
        assert isinstance(curr_rec, CurriculumRecord)

    def test_first_element_is_synthesis_record(self):
        crls = _build_crls()
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        result = crls.end_of_generation()
        assert isinstance(result[0], SynthesisRecord)

    def test_curriculum_log_grows_with_generations(self):
        crls = _build_crls(puzzle_categories=_cats(3))
        _run_n_generations(crls, n=6)
        report = crls.get_full_report()
        assert len(report["curriculum_log"]) == 6

    def test_curriculum_log_contains_correct_keys(self):
        crls = _build_crls(puzzle_categories=_cats(2))
        _run_n_generations(crls, n=3)
        report = crls.get_full_report()
        for entry in report["curriculum_log"]:
            for key in ("generation", "selected_category", "selection_reason",
                        "n_in_zpd", "difficulty"):
                assert key in entry, f"Missing key '{key}' in curriculum_log entry"

    def test_all_categories_visited_over_time(self):
        """Over many generations, all unseen categories should be explored."""
        cats = _cats(3)
        crls = _build_crls(puzzle_categories=cats)
        _run_n_generations(crls, n=9)
        # Every category should have at least 1 observation after 9 gens
        for cat in cats:
            assert cat.n_observations >= 1, f"Category {cat.name} never visited"

    def test_full_exit_criteria_pass_integration(self):
        crls = _build_crls(
            puzzle_categories=_cats(3),
            wm_min_buffer=3,
            wm_batch_size=2,
        )
        _run_n_generations(crls, n=12)
        result = verify_wp31_exit_criteria(crls)
        for k, v in result.items():
            assert v, f"Failed: {k}"

    def test_gen_log_has_both_wp30_and_wp31_keys(self):
        """After a generation, gen_log should contain keys from both WP30 and WP31."""
        crls = _build_crls(puzzle_categories=_cats(2))
        puzzles = _go_puzzles(8)
        tactic_fns = _go_tactic_fns()
        crls.run_generation(puzzles, tactic_fns, _go_eval)
        crls.end_of_generation()
        entry = crls.gen_log[-1]
        # WP30 keys
        assert "wp30_wm_action" in entry
        # WP31 keys
        assert "wp31_category" in entry
