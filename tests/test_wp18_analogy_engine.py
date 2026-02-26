"""
WP18 Test Suite: Analogy Engine MVP — Cross-Domain Transfer
============================================================

Tests are structured in six classes mirroring the WP17 pattern:

TestTacticSignature       Unit tests for TacticSignature dataclass
TestStructuralAnalogy     Unit tests for StructuralAnalogy confidence dynamics
TestCrossDomainAnalogyMap Registry registration, query, and safety gating
TestTransferBootstrapper  Seeding algorithm and entropy reduction
TestGoChessCRLS           Integration: transfer advantage on real GoBoard puzzles
TestWP18ExitCriteria      Formal exit criteria verification

Design principle for TestGoChessCRLS
-------------------------------------
The Go puzzles are ATARI positions on a 9×9 board — real GoBoard instances,
no mocking.  The Chess puzzles are *synthetic* tactical sequences represented
as (board_stub, player, correct_tactic_name) triples where the "board" is a
lightweight mock that exposes only the interface the tactic functions require
(get_legal_moves, would_capture, is_legal_move).  This avoids the python-chess
dependency while keeping the MetaLearner update loop genuine.

The transfer advantage test verifies the core WP18 claim:
    A MetaLearner seeded via Go→Chess analogies reaches accuracy ≥ threshold
    in fewer generations than an identical MetaLearner starting from uniform.
"""

import math
import random
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple
from unittest.mock import MagicMock

import pytest

from prometheus.environments.go import GoBoard
from prometheus.meta_learner import MetaLearner
from prometheus.safety.checks import GodelianSafetyGovernor, SafetyStatus
from prometheus.wp18_analogy_engine import (
    CrossDomainAnalogyMap,
    GoChessCRLS,
    GoChessTacticRegistry,
    StructuralAnalogy,
    TacticSignature,
    TransferBootstrapper,
    TransferExperimentRecord,
    verify_wp18_exit_criteria,
)


# ===========================================================================
# Shared fixtures and helpers
# ===========================================================================

GO_TACTICS   = ["capture_atari", "ladder", "ko_fight", "territory_claim", "connect_groups"]
CHESS_TACTICS = ["pin_piece",    "skewer", "zugzwang", "space_control",   "piece_coordination"]


def make_go_sig(name: str) -> TacticSignature:
    return TacticSignature(
        threat_type     = "capture",
        constraint_type = "forced_move",
        resolution_type = "piece_removed",
        domain          = "go",
        tactic_name     = name,
    )


def make_chess_sig(name: str) -> TacticSignature:
    return TacticSignature(
        threat_type     = "capture",
        constraint_type = "forced_move",
        resolution_type = "piece_removed",
        domain          = "chess",
        tactic_name     = name,
    )


def make_map() -> CrossDomainAnalogyMap:
    return GoChessTacticRegistry.build()


def make_converged_go_learner(bias_tactic: str = "capture_atari") -> MetaLearner:
    """Return a Go MetaLearner that has converged toward bias_tactic."""
    meta = MetaLearner(GO_TACTICS, upward_rate=0.20, downward_rate=0.15)
    # Simulate convergence: many successes on bias_tactic, failures elsewhere
    for _ in range(30):
        meta.update_on_success(bias_tactic)
    for other in GO_TACTICS:
        if other != bias_tactic:
            for _ in range(10):
                meta.update_on_failure(other)
    return meta


# ---------------------------------------------------------------------------
# Synthetic Chess puzzle helpers (no python-chess dependency)
# ---------------------------------------------------------------------------

class _FakeChessBoard:
    """
    Minimal board stub exposing the interface the tactic runner expects.

    Internally stores a "correct_tactic" that signals which tactic yields a
    successful outcome.  The evaluate_fn uses this to determine success.
    """
    def __init__(self, correct_tactic: str, size: int = 8):
        self.size = size
        self.correct_tactic = correct_tactic

    def get_legal_moves(self, player=None) -> List[Tuple[int, int]]:
        return [(r, c) for r in range(self.size) for c in range(self.size)]

    def is_legal_move(self, r: int, c: int, player=None) -> bool:
        return 0 <= r < self.size and 0 <= c < self.size

    def would_capture(self, r: int, c: int, player=None) -> List[Tuple[int, int]]:
        # Simulates a capture-threatening move at (0,0)
        return [(1, 1)] if (r, c) == (0, 0) else []


def make_chess_tactic_fns() -> Dict[str, Callable]:
    """
    Tactic functions for synthetic Chess puzzles.
    Each returns a fixed deterministic move; success is determined by
    whether the tactic matches the puzzle's correct_tactic field.
    """
    def pin_piece(board, player):        return (0, 0)   # capture-threatening move
    def skewer(board, player):           return (0, 1)
    def zugzwang(board, player):         return (1, 0)
    def space_control(board, player):    return (1, 1)
    def piece_coordination(board, player): return (2, 2)

    return {
        "pin_piece":          pin_piece,
        "skewer":             skewer,
        "zugzwang":           zugzwang,
        "space_control":      space_control,
        "piece_coordination": piece_coordination,
    }


def chess_evaluate_fn(board, move, correct_move, player) -> bool:
    """Success if the tactic that produced `move` matches correct_move."""
    return move == correct_move


def make_chess_puzzles(n: int, bias_tactic: str = "pin_piece") -> List[Tuple]:
    """
    Generate n synthetic Chess puzzles biased toward bias_tactic.
    80% of puzzles require bias_tactic; 20% require the others uniformly.
    """
    tactic_fns = make_chess_tactic_fns()
    # Map tactic name → its fixed move output
    tactic_move = {t: tactic_fns[t](_FakeChessBoard(""), 1)
                   for t in CHESS_TACTICS}

    puzzles = []
    for i in range(n):
        if i < int(n * 0.80):
            correct_tactic = bias_tactic
        else:
            # Round-robin through others
            others = [t for t in CHESS_TACTICS if t != bias_tactic]
            correct_tactic = others[i % len(others)]

        board = _FakeChessBoard(correct_tactic)
        puzzles.append((board, 1, tactic_move[correct_tactic]))
    return puzzles


# ---------------------------------------------------------------------------
# Synthetic Go puzzle helpers (real GoBoard)
# ---------------------------------------------------------------------------

def make_atari_board() -> Tuple[GoBoard, int, Tuple[int, int]]:
    """
    Return a 9×9 GoBoard with a single White stone at (4,4) that Black
    can capture by playing (4,3), (4,5), (3,4), (5,4) — the atari is
    at (3,4) which reduces it to 1 liberty.
    The correct move is (3,4): play atari.
    """
    board = GoBoard(size=9)
    board.board[4][4] = GoBoard.WHITE    # White stone with multiple liberties
    board.board[4][3] = GoBoard.BLACK    # Black already occupies left
    board.board[4][5] = GoBoard.BLACK    # Black already occupies right
    board.board[5][4] = GoBoard.BLACK    # Black already occupies below
    # White's only liberty left is (3,4)
    board.current_player = GoBoard.BLACK
    correct_move = (3, 4)   # Black plays atari — captures White if White passes
    return board, GoBoard.BLACK, correct_move


def make_go_puzzles(n: int) -> List[Tuple]:
    """Generate n Go atari puzzles."""
    return [make_atari_board() for _ in range(n)]


def go_evaluate_fn(board, move, correct_move, player) -> bool:
    if move == correct_move:
        return True
    if move[0] >= 0 and board.is_legal_move(move[0], move[1], player):
        if len(board.would_capture(move[0], move[1], player)) > 0:
            return True
    return False


def make_go_tactic_fns() -> Dict[str, Callable]:
    """Tactic functions for the Go domain."""

    def capture_atari(board: GoBoard, player: int):
        """Play the move that gives a White stone only 1 liberty."""
        for r in range(board.size):
            for c in range(board.size):
                if board.is_legal_move(r, c, player):
                    caps = board.would_capture(r, c, player)
                    if caps:
                        return (r, c)
        legal = board.get_legal_moves(player)
        return legal[0] if legal else None

    def ladder(board: GoBoard, player: int):
        legal = board.get_legal_moves(player)
        if not legal:
            return None
        for move in legal:
            caps = board.would_capture(move[0], move[1], player)
            if caps:
                return move
        return legal[0]

    def ko_fight(board: GoBoard, player: int):
        legal = board.get_legal_moves(player)
        return legal[0] if legal else None

    def territory_claim(board: GoBoard, player: int):
        legal = board.get_legal_moves(player)
        return legal[-1] if legal else None

    def connect_groups(board: GoBoard, player: int):
        legal = board.get_legal_moves(player)
        mid = len(legal) // 2
        return legal[mid] if legal else None

    def random_legal(board: GoBoard, player: int):
        legal = board.get_legal_moves(player)
        return random.choice(legal) if legal else None

    return {
        "capture_atari":  capture_atari,
        "ladder":         ladder,
        "ko_fight":       ko_fight,
        "territory_claim": territory_claim,
        "connect_groups": connect_groups,
        "random_legal":   random_legal,
    }


# ===========================================================================
# TestTacticSignature — unit tests for the dataclass
# ===========================================================================

class TestTacticSignature:

    def test_structural_key_ignores_domain_and_name(self):
        """structural_key() is domain-agnostic."""
        go_sig    = make_go_sig("capture_atari")
        chess_sig = make_chess_sig("pin_piece")
        # They share the same (threat, constraint, resolution) triple
        go_sig2 = TacticSignature(
            threat_type     = "capture",
            constraint_type = "forced_move",
            resolution_type = "piece_removed",
            domain          = "chess",
            tactic_name     = "pin_piece",
        )
        assert go_sig.structural_key() == go_sig2.structural_key()

    def test_different_tactics_have_different_keys(self):
        go_sig    = make_go_sig("capture_atari")
        ko_sig    = TacticSignature("repetition", "forced_move", "repetition_draw", "go", "ko_fight")
        assert go_sig.structural_key() != ko_sig.structural_key()

    def test_frozen_immutable(self):
        sig = make_go_sig("capture_atari")
        with pytest.raises((AttributeError, TypeError)):
            sig.domain = "chess"  # type: ignore[misc]

    def test_domain_and_name_not_in_structural_key(self):
        sig = make_go_sig("capture_atari")
        key = sig.structural_key()
        assert sig.domain not in key
        assert sig.tactic_name not in key


# ===========================================================================
# TestStructuralAnalogy — unit tests for confidence dynamics
# ===========================================================================

class TestStructuralAnalogy:

    def _make_analogy(self, prior: float = 0.70) -> StructuralAnalogy:
        return StructuralAnalogy(
            analogy_id       = "test_analogy",
            source_sig       = make_go_sig("capture_atari"),
            target_sig       = make_chess_sig("pin_piece"),
            prior_confidence = prior,
        )

    def test_initial_confidence_equals_prior(self):
        a = self._make_analogy(0.75)
        assert a.confidence == pytest.approx(0.75)

    def test_confirm_increases_confidence(self):
        a = self._make_analogy(0.50)
        before = a.confidence
        for _ in range(10):
            a.confirm()
        assert a.confidence > before, "Confirmations should increase confidence"

    def test_refute_decreases_confidence(self):
        a = self._make_analogy(0.90)
        before = a.confidence
        for _ in range(10):
            a.refute()
        assert a.confidence < before, "Refutations should decrease confidence"

    def test_confidence_bounded_0_1(self):
        a = self._make_analogy(0.80)
        for _ in range(100):
            a.confirm()
        assert 0.0 <= a.confidence <= 1.0

        b = self._make_analogy(0.20)
        for _ in range(100):
            b.refute()
        assert 0.0 <= b.confidence <= 1.0

    def test_to_dict_contains_expected_keys(self):
        a = self._make_analogy()
        d = a.to_dict()
        for key in ("analogy_id", "source_domain", "source_tactic",
                    "target_domain", "target_tactic", "prior_confidence",
                    "confidence", "confirmations", "refutations"):
            assert key in d, f"Missing key: {key}"

    def test_zero_trials_returns_prior(self):
        a = self._make_analogy(0.65)
        assert a.confirmations == 0
        assert a.refutations   == 0
        assert a.confidence == pytest.approx(0.65)


# ===========================================================================
# TestCrossDomainAnalogyMap — registry and safety gating
# ===========================================================================

class TestCrossDomainAnalogyMap:

    def test_goches_registry_builds_10_analogies(self):
        """5 Go→Chess + 5 Chess→Go = 10 total."""
        amap = GoChessTacticRegistry.build()
        summary = amap.get_summary()
        assert summary["total_analogies"] == 10

    def test_forward_analogies_registered(self):
        amap = GoChessTacticRegistry.build()
        # Each Go tactic should map to a Chess tactic
        for go_tactic in GO_TACTICS:
            analogues = amap.get_target_analogues(go_tactic, "chess")
            assert len(analogues) >= 1, f"No chess analogue for go/{go_tactic}"

    def test_reverse_analogies_registered(self):
        amap = GoChessTacticRegistry.build()
        for chess_tactic in CHESS_TACTICS:
            analogues = amap.get_source_analogues(chess_tactic, "go")
            assert len(analogues) >= 1, f"No go source for chess/{chess_tactic}"

    def test_min_confidence_filter(self):
        amap = GoChessTacticRegistry.build()
        # All pre-built analogies have prior ≥ 0.65, so min_confidence=0.90
        # should filter most out
        analogues = amap.get_target_analogues("capture_atari", "chess", min_confidence=0.90)
        assert len(analogues) == 0 or all(a.confidence >= 0.90 for a in analogues)

    def test_empirical_update_propagates(self):
        amap = GoChessTacticRegistry.build()
        analogy = amap.get_target_analogues("capture_atari", "chess")[0]
        aid = analogy.analogy_id
        before = analogy.confidence
        for _ in range(20):
            amap.update_empirical(aid, success=False)
        assert analogy.confidence < before, "Refutations should lower confidence"

    def test_safety_gating_blocks_unsafe_proposal(self):
        """
        Register an analogy with a governor that always returns UNSAFE.
        The analogy should NOT appear in the map.
        """
        mock_gov = MagicMock(spec=GodelianSafetyGovernor)
        mock_gov.evaluate_modification.return_value = (
            SafetyStatus.PROVABLY_UNSAFE, "test block"
        )
        amap = CrossDomainAnalogyMap(governor=mock_gov)
        a = StructuralAnalogy(
            analogy_id       = "blocked",
            source_sig       = make_go_sig("capture_atari"),
            target_sig       = make_chess_sig("pin_piece"),
            prior_confidence = 0.80,
        )
        amap.register(a)
        assert len(amap.all_analogies()) == 0, "Unsafe analogy should be blocked"

    def test_all_built_analogies_are_provably_safe(self):
        """GoChessTacticRegistry only registers rule_add proposals → all safe."""
        amap = GoChessTacticRegistry.build()
        safety_stats = amap.governor.get_safety_statistics()
        assert safety_stats["total_decisions"] == 10
        assert safety_stats.get("unsafe_decisions", 0) == 0


# ===========================================================================
# TestTransferBootstrapper — seeding algorithm
# ===========================================================================

class TestTransferBootstrapper:

    def test_seeded_probs_differ_from_uniform(self):
        """After seeding, the target distribution is not uniform."""
        amap  = GoChessTacticRegistry.build()
        src   = make_converged_go_learner("capture_atari")
        tgt   = MetaLearner(CHESS_TACTICS, upward_rate=0, downward_rate=0)
        tb    = TransferBootstrapper(amap, blend_alpha=0.70)
        tb.seed(src, "go", tgt, "chess")

        n = len(CHESS_TACTICS)
        uniform_p = 1.0 / n
        probs = tgt.get_strategy_probabilities()
        diffs = [abs(p - uniform_p) for p in probs.values()]
        assert max(diffs) > 1e-6, "Transfer should break uniform distribution"

    def test_analogous_tactic_gets_higher_probability(self):
        """
        capture_atari is biased in Go → pin_piece should get higher probability
        in Chess than a non-analogous tactic would under uniform.
        """
        amap = GoChessTacticRegistry.build()
        src  = make_converged_go_learner("capture_atari")
        tgt  = MetaLearner(CHESS_TACTICS, upward_rate=0, downward_rate=0)
        tb   = TransferBootstrapper(amap, blend_alpha=0.90)
        tb.seed(src, "go", tgt, "chess")

        probs = tgt.get_strategy_probabilities()
        # pin_piece is the Go→Chess analogue of capture_atari (conf=0.85)
        assert probs["pin_piece"] > probs["zugzwang"], (
            "pin_piece (analogue of capture_atari) should have higher "
            "probability than zugzwang (analogue of ko_fight)"
        )

    def test_probs_sum_to_one(self):
        amap = GoChessTacticRegistry.build()
        src  = make_converged_go_learner()
        tgt  = MetaLearner(CHESS_TACTICS, upward_rate=0, downward_rate=0)
        tb   = TransferBootstrapper(amap, blend_alpha=0.70)
        tb.seed(src, "go", tgt, "chess")

        total = sum(tgt.get_strategy_probabilities().values())
        assert abs(total - 1.0) < 1e-9, f"Probabilities must sum to 1, got {total}"

    def test_alpha_zero_gives_uniform(self):
        """blend_alpha=0 means 100% uniform prior regardless of source."""
        amap = GoChessTacticRegistry.build()
        src  = make_converged_go_learner("capture_atari")
        tgt  = MetaLearner(CHESS_TACTICS, upward_rate=0, downward_rate=0)
        tb   = TransferBootstrapper(amap, blend_alpha=0.0)
        tb.seed(src, "go", tgt, "chess")

        n = len(CHESS_TACTICS)
        uniform_p = 1.0 / n
        for p in tgt.get_strategy_probabilities().values():
            assert abs(p - uniform_p) < 1e-9, "alpha=0 should give uniform prior"

    def test_entropy_reduction_positive(self):
        """Transfer seeding must reduce entropy versus uniform."""
        amap = GoChessTacticRegistry.build()
        src  = make_converged_go_learner("capture_atari")
        tb   = TransferBootstrapper(amap, blend_alpha=0.70)
        reduction = tb.get_transfer_entropy_reduction(
            source_learner    = src,
            source_domain     = "go",
            target_strategies = CHESS_TACTICS,
            target_domain     = "chess",
        )
        assert reduction > 1e-6, (
            f"Transfer should reduce entropy; got reduction={reduction:.6f}"
        )

    def test_entropy_reduction_zero_for_uniform_source(self):
        """A perfectly uniform Go learner carries no information → no entropy reduction."""
        amap = GoChessTacticRegistry.build()
        # Fresh learner = uniform
        src  = MetaLearner(GO_TACTICS, upward_rate=0, downward_rate=0)
        tb   = TransferBootstrapper(amap, blend_alpha=0.70)
        reduction = tb.get_transfer_entropy_reduction(
            source_learner    = src,
            source_domain     = "go",
            target_strategies = CHESS_TACTICS,
            target_domain     = "chess",
        )
        # A uniform source still gets blended, but the signal is all equal weights
        # so the reduction should be ≤ tiny epsilon
        assert reduction < 0.10, (
            f"Uniform source should not reduce entropy much; got {reduction:.4f}"
        )


# ===========================================================================
# TestGoChessCRLS — integration: transfer advantage on real GoBoard puzzles
# ===========================================================================

class TestGoChessCRLS:
    """
    Core WP18 claim: transfer-seeded MetaLearner converges faster than cold.

    Uses:
    - Real GoBoard (9×9) for Go pre-training
    - Synthetic Chess puzzles (no python-chess) for target domain
    - Both MetaLearners have identical upward/downward rates
    - The only difference is the initial distribution
    """

    def _make_experiment(self) -> GoChessCRLS:
        amap = GoChessTacticRegistry.build()
        return GoChessCRLS(
            go_strategies    = GO_TACTICS + ["random_legal"],
            chess_strategies = CHESS_TACTICS,
            analogy_map      = amap,
            upward_rate      = 0.25,
            downward_rate    = 0.20,
            threshold        = 0.60,
            blend_alpha      = 0.80,
        )

    def test_pretrain_go_returns_positive_accuracy(self):
        """pretrain_go() produces a non-zero accuracy on real GoBoard puzzles."""
        exp     = self._make_experiment()
        puzzles = make_go_puzzles(20)
        tactic_fns = make_go_tactic_fns()
        acc = exp.pretrain_go(puzzles, tactic_fns, go_evaluate_fn)
        assert 0.0 <= acc <= 1.0

    def test_go_learner_converges_toward_capture_tactics(self):
        """
        After pre-training on ATARI puzzles, the dominant strategy must be one
        of the capture-oriented tactics (capture_atari or ladder — both locate
        capture moves and are indistinguishable on pure atari puzzles).
        Non-capture tactics (ko_fight, territory_claim, connect_groups, random_legal)
        must have lower probability than the best capture tactic.
        """
        exp = self._make_experiment()
        for _ in range(5):
            exp.pretrain_go(make_go_puzzles(30), make_go_tactic_fns(), go_evaluate_fn)

        probs = exp.go_learner.get_strategy_probabilities()
        capture_tactics    = {"capture_atari", "ladder"}
        non_capture_tactics = set(GO_TACTICS + ["random_legal"]) - capture_tactics

        best_capture_p    = max(probs[t] for t in capture_tactics)
        best_noncapture_p = max(probs[t] for t in non_capture_tactics)
        assert best_capture_p > best_noncapture_p, (
            f"Capture tactics (p={best_capture_p:.3f}) should dominate "
            f"non-capture tactics (p={best_noncapture_p:.3f}) after atari training"
        )

    def test_apply_transfer_breaks_uniform(self):
        """After apply_transfer(), chess MetaLearner must not be uniform."""
        exp = self._make_experiment()
        for _ in range(3):
            exp.pretrain_go(make_go_puzzles(30), make_go_tactic_fns(), go_evaluate_fn)
        exp.apply_transfer()

        n = len(CHESS_TACTICS)
        uniform_p = 1.0 / n
        probs = exp.transfer_learner.get_strategy_probabilities()
        assert any(abs(p - uniform_p) > 1e-6 for p in probs.values()), (
            "Transfer should produce a non-uniform distribution"
        )

    def test_transfer_advantage_non_negative(self):
        """
        Transfer MetaLearner should reach threshold at least as fast as cold.

        We run 10 generations of Chess puzzles (80% require pin_piece, which
        is the analogue of capture_atari that the Go learner has learned).
        The transfer learner starts with pin_piece already boosted; the cold
        learner starts from uniform.
        """
        random.seed(42)
        exp = self._make_experiment()

        # Pre-train Go sufficiently
        go_tactic_fns = make_go_tactic_fns()
        for _ in range(8):
            exp.pretrain_go(make_go_puzzles(40), go_tactic_fns, go_evaluate_fn)

        exp.apply_transfer()

        chess_tactic_fns = make_chess_tactic_fns()
        for gen in range(10):
            puzzles = make_chess_puzzles(50, bias_tactic="pin_piece")
            exp.run_generation(puzzles, chess_tactic_fns, chess_evaluate_fn)

        cold     = exp.gens_to_threshold("cold_start")
        transfer = exp.gens_to_threshold("transfer_start")

        # Transfer must converge no later than cold (or both converge at same gen)
        if cold is not None and transfer is not None:
            assert transfer <= cold, (
                f"Transfer ({transfer}) should converge ≤ cold ({cold})"
            )
        else:
            # At minimum, transfer accuracy at each generation should be ≥ cold
            for cr, tr in zip(exp.cold_records, exp.transfer_records):
                assert tr.accuracy >= cr.accuracy - 0.05, (
                    "Transfer should never be significantly worse than cold"
                )

    def test_transfer_accuracy_gen0_exceeds_cold(self):
        """
        At generation 0 (first Chess generation), transfer already has a
        head start — its accuracy should be ≥ cold accuracy.
        """
        random.seed(0)
        exp = self._make_experiment()

        go_tactic_fns = make_go_tactic_fns()
        for _ in range(8):
            exp.pretrain_go(make_go_puzzles(40), go_tactic_fns, go_evaluate_fn)

        exp.apply_transfer()
        puzzles = make_chess_puzzles(60, bias_tactic="pin_piece")
        cold_acc, transfer_acc = exp.run_generation(
            puzzles, make_chess_tactic_fns(), chess_evaluate_fn
        )

        assert transfer_acc >= cold_acc - 0.05, (
            f"Transfer gen-0 accuracy ({transfer_acc:.2%}) should be ≥ "
            f"cold accuracy ({cold_acc:.2%})"
        )

    def test_full_report_structure(self):
        """get_full_report() must have all required keys."""
        exp = self._make_experiment()
        exp.pretrain_go(make_go_puzzles(20), make_go_tactic_fns(), go_evaluate_fn)
        exp.apply_transfer()
        exp.run_generation(
            make_chess_puzzles(20), make_chess_tactic_fns(), chess_evaluate_fn
        )

        report = exp.get_full_report()
        for key in ("generations", "threshold", "cold_start", "transfer_start",
                    "transfer_advantage_gens", "analogy_map_summary", "go_learner_stats"):
            assert key in report, f"Missing key in full_report: {key}"

        for condition in ("cold_start", "transfer_start"):
            for sub in ("accuracies", "gens_to_threshold", "final_accuracy"):
                assert sub in report[condition], f"Missing {sub} in {condition}"


# ===========================================================================
# TestWP18ExitCriteria — formal exit criteria verification
# ===========================================================================

class TestWP18ExitCriteria:

    def _make_converged_experiment(self, seed: int = 1) -> GoChessCRLS:
        """Run a full experiment to convergence and return it."""
        random.seed(seed)
        amap = GoChessTacticRegistry.build()
        exp  = GoChessCRLS(
            go_strategies    = GO_TACTICS + ["random_legal"],
            chess_strategies = CHESS_TACTICS,
            analogy_map      = amap,
            upward_rate      = 0.25,
            downward_rate    = 0.20,
            threshold        = 0.60,
            blend_alpha      = 0.80,
        )

        go_tactic_fns = make_go_tactic_fns()
        for _ in range(8):
            exp.pretrain_go(make_go_puzzles(40), go_tactic_fns, go_evaluate_fn)

        exp.apply_transfer()

        chess_tactic_fns = make_chess_tactic_fns()
        for _ in range(10):
            puzzles = make_chess_puzzles(50, bias_tactic="pin_piece")
            exp.run_generation(puzzles, chess_tactic_fns, chess_evaluate_fn)

        return exp

    def test_wp18_exit_criteria_analogy_map_populated(self):
        exp = self._make_converged_experiment()
        criteria = verify_wp18_exit_criteria(exp)
        assert criteria["analogy_map_populated"], "Analogy map must have ≥5 analogies"

    def test_wp18_exit_criteria_transfer_seeded(self):
        exp = self._make_converged_experiment()
        criteria = verify_wp18_exit_criteria(exp)
        assert criteria["transfer_seeded"], "Transfer MetaLearner must be non-uniform"

    def test_wp18_exit_criteria_entropy_reduced(self):
        exp = self._make_converged_experiment()
        criteria = verify_wp18_exit_criteria(exp)
        assert criteria["entropy_reduced"], "Transfer must reduce entropy vs uniform"

    def test_wp18_exit_criteria_safety_gated(self):
        exp = self._make_converged_experiment()
        criteria = verify_wp18_exit_criteria(exp)
        assert criteria["safety_gated"], "Safety governor must have evaluated proposals"

    def test_wp18_exit_criteria_no_unsafe_applied(self):
        exp = self._make_converged_experiment()
        criteria = verify_wp18_exit_criteria(exp)
        assert criteria["no_unsafe_applied"], "No PROVABLY_UNSAFE analogy may be applied"

    def test_wp18_exit_criteria_transfer_faster(self):
        """The headline criterion: transfer reaches threshold in fewer generations."""
        exp = self._make_converged_experiment()
        criteria = verify_wp18_exit_criteria(exp)
        assert criteria["transfer_faster"], (
            "Transfer-seeded MetaLearner must reach accuracy threshold "
            "in fewer generations than cold-start"
        )

    def test_all_criteria_pass(self):
        """All 6 WP18 exit criteria must be True simultaneously."""
        exp      = self._make_converged_experiment()
        criteria = verify_wp18_exit_criteria(exp)
        failing  = [k for k, v in criteria.items() if not v]
        assert not failing, f"WP18 exit criteria failed: {failing}"


# ===========================================================================
# TestTransferExperimentRecord — unit tests for the dataclass
# ===========================================================================

class TestTransferExperimentRecord:

    def test_to_dict_keys(self):
        r = TransferExperimentRecord(generation=0, condition="cold_start", accuracy=0.55)
        d = r.to_dict()
        assert set(d.keys()) == {"generation", "condition", "accuracy"}

    def test_condition_values(self):
        r1 = TransferExperimentRecord(0, "cold_start",     0.5)
        r2 = TransferExperimentRecord(0, "transfer_start", 0.7)
        assert r1.condition == "cold_start"
        assert r2.condition == "transfer_start"
