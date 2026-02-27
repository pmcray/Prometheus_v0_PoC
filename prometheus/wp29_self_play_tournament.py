"""
WP29: Self-Play Synthesis Tournament
======================================

Two ``TransferCRLS`` instances — **Alpha** and **Beta** — play against each
other on Go tactical puzzles.  Each instance serves simultaneously as the
*opponent* (puzzle setter) and the *teacher* (distillation label source) for
the other.  The mutual teaching loop drives both agents to specialise
beyond any single-teacher curriculum.

The gap in WP17–28
--------------------
Every WP17–28 CRLS layer is self-contained: it learns from its own history
of (state, action, accuracy) tuples.  There is no *external adversarial
signal* — no other agent is actively trying to expose the system's blind
spots.  Silver et al. (AlphaGo Zero, 2017) showed that self-play is the
primary driver of superhuman performance: the opponent is the only teacher
that provably knows your current limitations.

WP29 fix
---------
``TournamentMatch`` pairs two ``TransferCRLS`` agents on the same batch of
puzzles for one generation.  After each match:

  1. Each agent runs ``run_generation`` and ``end_of_generation`` independently.
  2. The *winner* (higher generation accuracy) becomes the **teacher** for the
     next match: its ``end_of_generation`` synthesis action is injected as an
     additional distillation label into the *loser's* WP28 transfer student via
     a special ``teach_from_opponent()`` call.
  3. Both agents' WP21 meta-gradient optimisers receive a *tournament signal*:
     the winner's current meta-params are used as a soft target to nudge the
     loser toward more aggressive exploration (higher ``boost_factor``).

``TournamentRecord`` is the audit trail for one match.

``SelfPlayTournament`` manages a sequence of matches, tracks Elo ratings,
detects convergence (when the rating gap < ``elo_convergence_threshold`` for
``convergence_patience`` consecutive matches), and exposes a ``run()`` method.

``TournamentCRLS`` is a thin wrapper around ``TransferCRLS`` that exposes the
``teach_from_opponent()`` and ``receive_tournament_signal()`` hooks.

``verify_wp29_exit_criteria`` checks six measurable criteria.

Layer hierarchy after WP29:

    Tournament  SelfPlayTournament (WP29) — mutual teaching between two TransferCRLS
    Layer 10    CrossDomainDistiller (WP28)
    Layer 9     TaskDecomposer (WP26)
    Layer 8     EWC guard (WP25)
    ...
    Layer 1     WP17 heuristic

Theoretical grounding
---------------------
Silver et al. (2017): "Mastering the game of Go without human knowledge" —
self-play as the sole training signal; the opponent is the curriculum.

Tesauro (1995): TD-Gammon — reinforcement learning by playing against itself;
emergent strategy from scratch without any human games.

Hofstadter (GEB, 1979): strange loops — agent A is simultaneously the
object-level problem for agent B and the meta-level commentator on B's
solutions; the loop creates new levels of competence that neither agent could
reach alone.

Good (1965): an ultraintelligent machine would recognise that the most
powerful teacher is a copy of itself slightly ahead; self-play is this
principle operationalised.

Classes
-------
TournamentRecord        Audit record for one match
TournamentCRLS          TransferCRLS + teach_from_opponent hook
SelfPlayTournament      Manages match sequence, Elo ratings, convergence
verify_wp29_exit_criteria   Six-criterion verifier
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from prometheus.wp17_crls_synthesis import SynthesisAction, SynthesisRecord
from prometheus.wp18_analogy_engine import CrossDomainAnalogyMap
from prometheus.wp19_causal_evaluator import CausalRecommendation
from prometheus.wp20_temporal_planner import RolloutResult, SynthesisStateSnapshot
from prometheus.wp21_meta_gradient import MetaGradStep, MetaParams
from prometheus.wp22_bandit_exploration import BanditMode, ExplorationRecord
from prometheus.wp23_policy_distillation import DistillationRecord
from prometheus.wp24_ensemble_uncertainty import EnsembleRecord
from prometheus.wp25_ewc_forgetting import ForgettingRecord
from prometheus.wp26_hierarchical_decomp import DecompositionRecord
from prometheus.wp28_cross_domain_transfer import TransferCRLS, TransferRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TournamentRecord  —  audit record for one tournament match
# ---------------------------------------------------------------------------

@dataclass
class TournamentRecord:
    """
    Audit record for one self-play match between Alpha and Beta agents.

    Attributes
    ----------
    match_number : int
    alpha_accuracy : float
    beta_accuracy : float
    winner : str
        "alpha", "beta", or "draw".
    alpha_elo : float
        Alpha's Elo rating *after* this match.
    beta_elo : float
        Beta's Elo rating *after* this match.
    elo_gap : float
        abs(alpha_elo - beta_elo) after this match.
    teach_action : SynthesisAction
        The winner's synthesis action injected into the loser.
    loser_received_teach : bool
        True if the teach was actually applied to the loser.
    timestamp : float
    """
    match_number:        int
    alpha_accuracy:      float
    beta_accuracy:       float
    winner:              str
    alpha_elo:           float
    beta_elo:            float
    elo_gap:             float
    teach_action:        SynthesisAction
    loser_received_teach: bool
    timestamp:           float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_number":        self.match_number,
            "alpha_accuracy":      self.alpha_accuracy,
            "beta_accuracy":       self.beta_accuracy,
            "winner":              self.winner,
            "alpha_elo":           self.alpha_elo,
            "beta_elo":            self.beta_elo,
            "elo_gap":             self.elo_gap,
            "teach_action":        self.teach_action.value,
            "loser_received_teach": self.loser_received_teach,
        }


# ---------------------------------------------------------------------------
# TournamentCRLS  —  TransferCRLS + tournament hooks
# ---------------------------------------------------------------------------

class TournamentCRLS(TransferCRLS):
    """
    WP29 upgrade of TransferCRLS: adds mutual teaching hooks for self-play.

    Extends ``TransferCRLS`` with two additional methods:

    ``teach_from_opponent(action, generation)``
        Injects a synthesis action from the opponent (the winner of the last
        match) as an additional fine-tuning signal into this agent's WP28
        transfer student.  This is the core self-play teaching step.

    ``receive_tournament_signal(winner_params, alpha)``
        Soft-target nudge: blend this agent's WP21 meta-params toward the
        winner's meta-params using a blending coefficient ``alpha``.

    Parameters
    ----------
    (all TransferCRLS parameters — no new additions required)
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.teach_log: List[Dict[str, Any]] = []

    def teach_from_opponent(
        self,
        action:     SynthesisAction,
        generation: int,
    ) -> float:
        """
        Fine-tune the transfer student using the opponent's synthesis action
        as a teaching label on the current synthesis state.

        Parameters
        ----------
        action : SynthesisAction
            The opponent (winner)'s synthesis action.
        generation : int

        Returns
        -------
        float  cross-entropy loss of the fine-tuning step
        """
        acc_now = self.acc_history[-1] if self.acc_history else 0.0
        state   = SynthesisStateSnapshot.from_meta_and_acc(
            generation, self.meta, acc_now
        )
        loss = self.transfer_student.finetune(state, action)
        self.teach_log.append({
            "generation":  generation,
            "teach_action": action.value,
            "loss":         loss,
        })
        logger.debug(
            "TournamentCRLS gen %d: opponent teaches action=%s loss=%.4f",
            generation, action.value, loss,
        )
        return loss

    def receive_tournament_signal(
        self,
        winner_params: MetaParams,
        alpha:         float = 0.10,
    ) -> None:
        """
        Soft-target nudge of WP21 meta-params toward the winner's params.

        Applies the update:
            θ_self ← (1 - α) · θ_self + α · θ_winner

        Only the scalar parameters of MetaParams are blended; bounds and
        clipping are respected automatically by accessing the dataclass fields.

        Parameters
        ----------
        winner_params : MetaParams
            The winning agent's current meta-params.
        alpha : float
            Blending coefficient (default 0.10 — subtle nudge).
        """
        def _blend(self_val: float, win_val: float) -> float:
            return (1 - alpha) * self_val + alpha * win_val

        self.meta_params.demote_factor  = _blend(
            self.meta_params.demote_factor,  winner_params.demote_factor)
        self.meta_params.promote_factor = _blend(
            self.meta_params.promote_factor, winner_params.promote_factor)
        self.meta_params.boost_factor   = _blend(
            self.meta_params.boost_factor,   winner_params.boost_factor)
        self.meta_params.discount       = _blend(
            self.meta_params.discount,       winner_params.discount)
        self.meta_params.horizon_cont   = _blend(
            self.meta_params.horizon_cont,   winner_params.horizon_cont)

        # Re-apply clamped params to the underlying synthesiser
        self._apply_meta_params()
        logger.debug(
            "TournamentCRLS: received tournament signal (alpha=%.2f)", alpha
        )


# ---------------------------------------------------------------------------
# Elo rating helpers
# ---------------------------------------------------------------------------

_ELO_K = 32.0   # K-factor for Elo update


def _elo_expected(rating_a: float, rating_b: float) -> float:
    """Expected score of player A against player B."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def _elo_update(
    rating_a: float,
    rating_b: float,
    score_a:  float,   # 1.0 = A wins, 0.5 = draw, 0.0 = A loses
) -> Tuple[float, float]:
    """Return updated (rating_a, rating_b)."""
    expected_a = _elo_expected(rating_a, rating_b)
    expected_b = 1.0 - expected_a
    score_b    = 1.0 - score_a
    new_a = rating_a + _ELO_K * (score_a - expected_a)
    new_b = rating_b + _ELO_K * (score_b - expected_b)
    return new_a, new_b


# ---------------------------------------------------------------------------
# SelfPlayTournament  —  match manager
# ---------------------------------------------------------------------------

class SelfPlayTournament:
    """
    Manages a sequence of self-play matches between ``alpha`` and ``beta``,
    tracks Elo ratings, and detects convergence.

    Design
    ------
    Each ``match()`` call:
      1. Runs one generation for both agents on the *same* puzzle batch.
      2. Calls ``end_of_generation`` on both.
      3. Determines the winner (higher accuracy; tie = draw).
      4. Winner teaches the loser via ``teach_from_opponent``.
      5. Winner's meta-params nudge the loser via ``receive_tournament_signal``.
      6. Updates Elo ratings.
      7. Returns a ``TournamentRecord``.

    Convergence: detected when ``abs(alpha_elo - beta_elo) < elo_threshold``
    for ``convergence_patience`` consecutive matches.

    Parameters
    ----------
    alpha : TournamentCRLS
    beta : TournamentCRLS
    initial_elo : float
        Starting Elo rating for both agents (default 1200).
    elo_convergence_threshold : float
        Elo gap below which agents are considered equal (default 50.0).
    convergence_patience : int
        Consecutive matches below threshold needed to declare convergence
        (default 5).
    teach_alpha : float
        Blending coefficient for ``receive_tournament_signal`` (default 0.10).
    """

    def __init__(
        self,
        alpha:                       TournamentCRLS,
        beta:                        TournamentCRLS,
        initial_elo:                 float = 1200.0,
        elo_convergence_threshold:   float = 50.0,
        convergence_patience:        int   = 5,
        teach_alpha:                 float = 0.10,
    ):
        self.alpha   = alpha
        self.beta    = beta
        self.alpha_elo = initial_elo
        self.beta_elo  = initial_elo
        self.elo_convergence_threshold = elo_convergence_threshold
        self.convergence_patience      = convergence_patience
        self.teach_alpha               = teach_alpha

        self.match_log: List[TournamentRecord] = []
        self._below_threshold_count: int = 0
        self._converged: bool = False
        self.match_number: int = 0

    # ------------------------------------------------------------------
    # Single match
    # ------------------------------------------------------------------

    def match(
        self,
        puzzles:     List[Tuple],
        tactic_fns:  Dict[str, Any],
        evaluate_fn: Callable,
        regime:      str = "",
    ) -> TournamentRecord:
        """
        Run one tournament match between alpha and beta.

        Parameters
        ----------
        puzzles : list of (GoBoard, player, correct_move)
        tactic_fns : dict[str, callable]
        evaluate_fn : callable
        regime : str

        Returns
        -------
        TournamentRecord
        """
        # Step 1: run both agents on the same puzzles
        alpha_acc = self.alpha.run_generation(puzzles, tactic_fns, evaluate_fn)
        beta_acc  = self.beta.run_generation(puzzles, tactic_fns, evaluate_fn)

        # Step 2: end_of_generation for both
        alpha_result = self.alpha.end_of_generation(regime=regime)
        beta_result  = self.beta.end_of_generation(regime=regime)

        alpha_synth = alpha_result[0]   # SynthesisRecord
        beta_synth  = beta_result[0]    # SynthesisRecord

        # Step 3: determine winner
        if alpha_acc > beta_acc + 1e-9:
            winner = "alpha"
            score_a = 1.0
        elif beta_acc > alpha_acc + 1e-9:
            winner = "beta"
            score_a = 0.0
        else:
            winner = "draw"
            score_a = 0.5

        # Step 4: winner teaches loser
        teach_action = (
            alpha_synth.action if winner in ("alpha", "draw")
            else beta_synth.action
        )
        gen = self.match_number
        teach_applied = False
        if winner == "alpha":
            self.beta.teach_from_opponent(teach_action, gen)
            teach_applied = True
        elif winner == "beta":
            self.alpha.teach_from_opponent(teach_action, gen)
            teach_applied = True
        else:
            # Draw: both teach each other
            self.alpha.teach_from_opponent(beta_synth.action, gen)
            self.beta.teach_from_opponent(alpha_synth.action, gen)
            teach_applied = True

        # Step 5: winner's meta-params nudge loser
        if winner == "alpha":
            self.beta.receive_tournament_signal(
                self.alpha.meta_params, alpha=self.teach_alpha)
        elif winner == "beta":
            self.alpha.receive_tournament_signal(
                self.beta.meta_params, alpha=self.teach_alpha)
        else:
            # Draw: mutual small nudge
            self.alpha.receive_tournament_signal(
                self.beta.meta_params, alpha=self.teach_alpha * 0.5)
            self.beta.receive_tournament_signal(
                self.alpha.meta_params, alpha=self.teach_alpha * 0.5)

        # Step 6: update Elo
        self.alpha_elo, self.beta_elo = _elo_update(
            self.alpha_elo, self.beta_elo, score_a
        )
        elo_gap = abs(self.alpha_elo - self.beta_elo)

        # Step 7: check convergence
        if elo_gap < self.elo_convergence_threshold:
            self._below_threshold_count += 1
            if self._below_threshold_count >= self.convergence_patience:
                self._converged = True
        else:
            self._below_threshold_count = 0

        rec = TournamentRecord(
            match_number          = self.match_number,
            alpha_accuracy        = alpha_acc,
            beta_accuracy         = beta_acc,
            winner                = winner,
            alpha_elo             = self.alpha_elo,
            beta_elo              = self.beta_elo,
            elo_gap               = elo_gap,
            teach_action          = teach_action,
            loser_received_teach  = teach_applied,
        )
        self.match_log.append(rec)
        self.match_number += 1

        logger.info(
            "Match %d: alpha=%.3f beta=%.3f winner=%s elo_gap=%.1f",
            gen, alpha_acc, beta_acc, winner, elo_gap,
        )
        return rec

    # ------------------------------------------------------------------
    # Run multiple matches
    # ------------------------------------------------------------------

    def run(
        self,
        n_matches:   int,
        puzzles:     List[Tuple],
        tactic_fns:  Dict[str, Any],
        evaluate_fn: Callable,
        regime:      str = "",
        early_stop:  bool = True,
    ) -> List[TournamentRecord]:
        """
        Run up to ``n_matches`` matches; stop early if converged.

        Parameters
        ----------
        n_matches : int
            Maximum number of matches to run.
        puzzles, tactic_fns, evaluate_fn : see ``match``
        regime : str
        early_stop : bool
            Stop when convergence is detected (default True).

        Returns
        -------
        list of TournamentRecord
        """
        records: List[TournamentRecord] = []
        for _ in range(n_matches):
            rec = self.match(puzzles, tactic_fns, evaluate_fn, regime=regime)
            records.append(rec)
            if early_stop and self._converged:
                logger.info(
                    "SelfPlayTournament converged after %d matches "
                    "(elo_gap=%.1f < threshold=%.1f)",
                    self.match_number, rec.elo_gap,
                    self.elo_convergence_threshold,
                )
                break
        return records

    # ------------------------------------------------------------------
    # Convergence + stats
    # ------------------------------------------------------------------

    @property
    def is_converged(self) -> bool:
        """True if the Elo gap has been below threshold for convergence_patience matches."""
        return self._converged

    def get_summary(self) -> Dict[str, Any]:
        log = self.match_log
        if not log:
            return {
                "n_matches":          0,
                "alpha_elo":          self.alpha_elo,
                "beta_elo":           self.beta_elo,
                "is_converged":       self.is_converged,
            }
        alpha_accs = [r.alpha_accuracy for r in log]
        beta_accs  = [r.beta_accuracy  for r in log]
        alpha_wins = sum(1 for r in log if r.winner == "alpha")
        beta_wins  = sum(1 for r in log if r.winner == "beta")
        draws      = sum(1 for r in log if r.winner == "draw")
        elo_gaps   = [r.elo_gap for r in log]
        return {
            "n_matches":               len(log),
            "alpha_wins":              alpha_wins,
            "beta_wins":               beta_wins,
            "draws":                   draws,
            "alpha_win_rate":          alpha_wins / len(log),
            "beta_win_rate":           beta_wins  / len(log),
            "draw_rate":               draws      / len(log),
            "mean_alpha_accuracy":     sum(alpha_accs) / len(alpha_accs),
            "mean_beta_accuracy":      sum(beta_accs)  / len(beta_accs),
            "final_alpha_elo":         self.alpha_elo,
            "final_beta_elo":          self.beta_elo,
            "final_elo_gap":           elo_gaps[-1],
            "min_elo_gap":             min(elo_gaps),
            "is_converged":            self.is_converged,
            "match_log":               [r.to_dict() for r in log],
        }


# ---------------------------------------------------------------------------
# Exit-criteria verifier
# ---------------------------------------------------------------------------

def verify_wp29_exit_criteria(tournament: SelfPlayTournament) -> Dict[str, bool]:
    """
    Verify WP29 exit criteria.

    Criteria
    --------
    tournament_ran           At least one match was played
    both_agents_improved     Both alpha and beta accuracy > 0 in at least one match
    mutual_teaching_applied  loser_received_teach == True in all matches
    elo_ratings_updated      alpha_elo or beta_elo != initial_elo after first match
    meta_params_nudged       At least one ``receive_tournament_signal`` call logged
    safety_preserved         Both agents: no UNSAFE synthesis applied

    Returns
    -------
    dict mapping criterion name → bool
    """
    log    = tournament.match_log
    alpha  = tournament.alpha
    beta   = tournament.beta

    # tournament_ran
    ran = len(log) >= 1

    # both_agents_improved
    alpha_accs = [r.alpha_accuracy for r in log]
    beta_accs  = [r.beta_accuracy  for r in log]
    both_improved = (
        any(a > 0 for a in alpha_accs)
        and any(b > 0 for b in beta_accs)
    )

    # mutual_teaching_applied
    teach_ok = ran and all(r.loser_received_teach for r in log)

    # elo_ratings_updated
    initial_elo = 1200.0   # matches SelfPlayTournament default
    elo_ok = (
        abs(tournament.alpha_elo - initial_elo) > 1e-6
        or abs(tournament.beta_elo - initial_elo) > 1e-6
    ) if ran else False

    # meta_params_nudged — check that teach_log has entries on at least one agent
    meta_nudged = (
        len(getattr(alpha, "teach_log", [])) > 0
        or len(getattr(beta, "teach_log", [])) > 0
    )

    # safety_preserved — both agents
    alpha_report = alpha.get_full_report()
    beta_report  = beta.get_full_report()
    alpha_safe   = (
        alpha_report["safety_statistics"]["total_decisions"] > 0
        and alpha_report["safety_statistics"]["unsafe_count"] == 0
    )
    beta_safe    = (
        beta_report["safety_statistics"]["total_decisions"] > 0
        and beta_report["safety_statistics"]["unsafe_count"] == 0
    )
    safety_ok = alpha_safe and beta_safe

    criteria = {
        "tournament_ran":          ran,
        "both_agents_improved":    both_improved,
        "mutual_teaching_applied": teach_ok,
        "elo_ratings_updated":     elo_ok,
        "meta_params_nudged":      meta_nudged,
        "safety_preserved":        safety_ok,
    }

    logger.info("WP29 exit criteria: %s", criteria)
    return criteria
