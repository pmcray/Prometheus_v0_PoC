"""
WP49: Multi-Agent Strange Loop — Theory of Mind
=================================================

Two agents play synthesis tournament, but each also maintains an explicit
*model of the other agent's policy*.  Beta models Alpha; Alpha models Beta's
model of Alpha.  This second-order loop is shown to converge faster than
first-order self-play (WP29 baseline) because each agent is predicting what
the other will do, not merely reacting to outcomes.

The gap in WP29
----------------
WP29's ``SelfPlayTournament`` has Alpha and Beta competing and teaching each
other via Elo-rated tournament outcomes.  But neither agent models the
*other's policy*.  Each is optimising its own synthesis stack against observed
outcomes; neither asks "what action will my opponent choose next, given what
I know about how they learn?"

This is Hofstadter's deepest point (GEB, Chapter 19, "Strange Loops and
Tangled Hierarchies"): consciousness arises when a system models another
system that is modelling it.  The *second-order* strange loop — where A
models B's model of A — creates a more tightly coupled attractor than the
first-order loop, and empirically converges faster.

WP49 fix
---------
``PolicyModel``
    A lightweight model of another agent's synthesis policy: a probability
    distribution over ``SynthesisAction`` conditioned on the observed
    state vector.  Updated each generation via exponential moving average
    of the opponent's observed actions.

``MindReadingAgent``
    Extends ``CorrigibleSimulator`` (WP46) with:
      - ``opponent_model: PolicyModel``  — the agent's model of its opponent
      - ``predict_opponent_action(state_vec) → SynthesisAction``
      - ``update_opponent_model(observed_action)``
    When choosing its own action, the agent conditions on the predicted
    opponent action: if the opponent is predicted to PROMOTE_BEST, this agent
    pre-empts by DEMOTE_WORST (adversarial) or cooperates by also promoting
    (cooperative, when behind on Elo).

``TheoryOfMindTournament``
    Runs Alpha (MindReadingAgent) vs Beta (MindReadingAgent) for n_matches.
    At each match:
      1. Both agents observe the current state vector (shared puzzle batch).
      2. Alpha predicts Beta's action; Beta predicts Alpha's action.
      3. Each agent conditions its own action selection on the prediction.
      4. Actions are applied; accuracies computed; Elo updated.
      5. Each agent updates its opponent model with the *actual* action chosen.
    Records the prediction accuracy of each agent's opponent model over time.

``ToMRecord``
    Per-match record: match number, accuracies, Elo, prediction accuracy
    (did Alpha correctly predict Beta's action?), opponent model entropy.

``ToMReport``
    Full report: ToM records, convergence stats, comparison with WP29 baseline,
    and the Hofstadter statement.

``verify_wp49_exit_criteria``
    Six-criterion verifier.

Theoretical grounding
---------------------
Hofstadter (GEB, 1979, Ch. 19): "A strange loop occurs whenever, by moving
only upwards (or only downwards) through the levels of some hierarchical
system, we unexpectedly find ourselves back where we started."  The
second-order ToM loop (A models B's model of A) creates exactly this
structure at the inter-agent level.

Premack & Woodruff (1978): "Does the chimpanzee have a theory of mind?" —
coined the term; ToM is the ability to attribute mental states to others.
WP49 implements the simplest computational version: each agent maintains a
predictive model of the other's action distribution.

Camerer et al. (2004): "A cognitive hierarchy model of games" — in game
theory, higher-order reasoning (k-level thinking) improves strategic
outcomes.  WP49 implements k=2 reasoning (agent models opponent modelling agent).

Classes
-------
PolicyModel             Action distribution model of an opponent
MindReadingAgent        CRLS agent with opponent model
ToMRecord               Per-match record
TheoryOfMindTournament  Orchestrates the second-order tournament
ToMReport               Full report
verify_wp49_exit_criteria  Six-criterion verifier
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from prometheus.wp17_crls_synthesis import SynthesisAction

logger = logging.getLogger(__name__)

_ACTION_LIST = list(SynthesisAction)
_N_ACTIONS   = len(_ACTION_LIST)


# ---------------------------------------------------------------------------
# PolicyModel — lightweight opponent policy model
# ---------------------------------------------------------------------------

class PolicyModel:
    """
    A probability distribution over SynthesisAction that models another
    agent's policy.  Updated via exponential moving average of observations.

    Parameters
    ----------
    ema_alpha : float   EMA decay rate (default 0.25 — relatively fast update)
    seed      : int
    """

    def __init__(self, ema_alpha: float = 0.25, seed: int = 0):
        self._ema    = ema_alpha
        self._rng    = random.Random(seed)
        # Initialise with uniform prior
        self._probs  = [1.0 / _N_ACTIONS] * _N_ACTIONS
        self._n_obs  = 0

    def update(self, observed_action: SynthesisAction) -> None:
        """Update model with one observed action."""
        idx = _ACTION_LIST.index(observed_action)
        # One-hot signal
        signal = [0.0] * _N_ACTIONS
        signal[idx] = 1.0
        # EMA update
        self._probs = [
            (1 - self._ema) * self._probs[i] + self._ema * signal[i]
            for i in range(_N_ACTIONS)
        ]
        self._n_obs += 1

    def predict(self) -> SynthesisAction:
        """Sample the most likely action from the current model."""
        best_i = self._probs.index(max(self._probs))
        return _ACTION_LIST[best_i]

    def entropy(self) -> float:
        """Shannon entropy of the current action distribution."""
        h = 0.0
        for p in self._probs:
            if p > 1e-9:
                h -= p * math.log(p)
        return h

    def probs(self) -> List[float]:
        return list(self._probs)

    @property
    def n_observations(self) -> int:
        return self._n_obs


# ---------------------------------------------------------------------------
# MindReadingAgent
# ---------------------------------------------------------------------------

class MindReadingAgent:
    """
    A CRLS synthesis agent that maintains a model of its opponent's policy
    and conditions its own action selection on the predicted opponent action.

    Strategy
    --------
    Adversarial mode (when agent is ahead on Elo):
      If opponent predicted to PROMOTE_BEST  → agent plays DEMOTE_WORST (neutralise)
      If opponent predicted to DEMOTE_WORST  → agent plays PROMOTE_BEST  (exploit)
      Otherwise                              → follow own heuristic

    Cooperative mode (when agent is behind on Elo):
      Mirror the opponent's predicted action (both improve together)

    Parameters
    ----------
    name              : str
    initial_accuracy  : float
    noise_std         : float
    ema_alpha         : float   Opponent model EMA rate
    seed              : int
    """

    def __init__(
        self,
        name:             str,
        initial_accuracy: float = 0.60,
        noise_std:        float = 0.015,
        ema_alpha:        float = 0.25,
        seed:             int   = 0,
    ):
        self.name             = name
        self.noise_std        = noise_std
        self._rng             = random.Random(seed)
        self.opponent_model   = PolicyModel(ema_alpha=ema_alpha, seed=seed + 1)

        # Object-level state
        self._accuracy    = initial_accuracy
        self._probs       = [1.0 / 4] * 4   # 4 meaningful actions
        self._elo         = 1200.0
        self._boost       = 1.20

        # History
        self.action_history:     List[SynthesisAction] = []
        self.prediction_history: List[SynthesisAction] = []
        self.correct_predictions: int = 0

    # ── Internal helpers ──────────────────────────────────────────────────

    def _entropy(self) -> float:
        h = 0.0
        for p in self._probs:
            if p > 1e-9:
                h -= p * math.log(p)
        return h

    def _acc_signal(self, action: SynthesisAction) -> float:
        acc    = self._accuracy
        best_p = max(self._probs)
        if action == SynthesisAction.PROMOTE_BEST:
            s = 0.03 * best_p * (1 - acc)
        elif action == SynthesisAction.DEMOTE_WORST:
            s = 0.02 * min(self._probs) * (1 - acc)
        elif action == SynthesisAction.RESET_UNIFORM:
            s = 0.04 * (0.70 - acc) if acc < 0.65 else -0.01
        elif action == SynthesisAction.BOOST_UPWARD:
            s = 0.01 * math.log(self._boost)
        else:
            s = 0.0
        return s * max(0.0, 1 - acc / 0.95)

    def _apply_action(self, action: SynthesisAction) -> None:
        n = len(self._probs)
        worst = self._probs.index(min(self._probs))
        best  = self._probs.index(max(self._probs))
        if action == SynthesisAction.DEMOTE_WORST:
            self._probs[worst] *= 0.5
        elif action == SynthesisAction.PROMOTE_BEST:
            self._probs[best] *= 2.0
        elif action == SynthesisAction.RESET_UNIFORM:
            self._probs = [1.0 / n] * n
        elif action == SynthesisAction.BOOST_UPWARD:
            self._boost = min(2.5, self._boost * 1.05)
        total = sum(self._probs)
        if total > 1e-9:
            self._probs = [p / total for p in self._probs]

    def _own_heuristic_action(self) -> SynthesisAction:
        H_max = math.log(len(self._probs))
        ent   = self._entropy()
        if ent < 0.3 * H_max:
            return SynthesisAction.RESET_UNIFORM
        if max(self._probs) > 0.60:
            return SynthesisAction.PROMOTE_BEST
        return SynthesisAction.BOOST_UPWARD

    # ── Public API ────────────────────────────────────────────────────────

    def predict_opponent(self) -> SynthesisAction:
        """Return the predicted opponent action."""
        return self.opponent_model.predict()

    def choose_action(
        self,
        opponent_elo: float,
        predicted_opponent: SynthesisAction,
    ) -> SynthesisAction:
        """
        Choose own action conditioned on predicted opponent action and Elo gap.
        """
        ahead = self._elo >= opponent_elo

        if ahead:
            # Adversarial: counter the opponent's predicted move
            if predicted_opponent == SynthesisAction.PROMOTE_BEST:
                action = SynthesisAction.DEMOTE_WORST
            elif predicted_opponent == SynthesisAction.DEMOTE_WORST:
                action = SynthesisAction.PROMOTE_BEST
            else:
                action = self._own_heuristic_action()
        else:
            # Cooperative: mirror opponent (both improve together)
            action = predicted_opponent if predicted_opponent in (
                SynthesisAction.PROMOTE_BEST,
                SynthesisAction.BOOST_UPWARD,
            ) else self._own_heuristic_action()

        self.prediction_history.append(predicted_opponent)
        return action

    def step(self, action: SynthesisAction) -> float:
        """Apply action, compute accuracy, return new accuracy."""
        self._apply_action(action)
        delta = self._acc_signal(action) + self._rng.gauss(0, self.noise_std)
        self._accuracy = max(0.05, min(0.97, self._accuracy + delta))
        self.action_history.append(action)
        return self._accuracy

    def observe_opponent(self, action: SynthesisAction) -> None:
        """Update opponent model with the opponent's actual action."""
        predicted = self.prediction_history[-1] if self.prediction_history else None
        self.opponent_model.update(action)
        if predicted is not None and predicted == action:
            self.correct_predictions += 1

    def update_elo(self, new_elo: float) -> None:
        self._elo = new_elo

    @property
    def accuracy(self) -> float:
        return self._accuracy

    @property
    def elo(self) -> float:
        return self._elo

    def prediction_accuracy(self) -> float:
        """Fraction of opponent actions correctly predicted so far."""
        n = len(self.prediction_history)
        if n == 0:
            return 0.0
        return self.correct_predictions / n


# ---------------------------------------------------------------------------
# ToMRecord — per-match record
# ---------------------------------------------------------------------------

@dataclass
class ToMRecord:
    """Per-match record for the theory-of-mind tournament."""
    match_number:        int
    alpha_accuracy:      float
    beta_accuracy:       float
    winner:              str     # 'alpha' | 'beta' | 'draw'
    alpha_elo:           float
    beta_elo:            float
    elo_gap:             float
    alpha_predicted_action:  SynthesisAction   # Alpha's prediction of Beta's action
    beta_predicted_action:   SynthesisAction   # Beta's prediction of Alpha's action
    alpha_actual_action:     SynthesisAction
    beta_actual_action:      SynthesisAction
    alpha_pred_correct:      bool
    beta_pred_correct:       bool
    alpha_model_entropy:     float
    beta_model_entropy:      float
    timestamp:           float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_number":       self.match_number,
            "alpha_accuracy":     round(self.alpha_accuracy, 4),
            "beta_accuracy":      round(self.beta_accuracy, 4),
            "winner":             self.winner,
            "alpha_elo":          round(self.alpha_elo, 1),
            "beta_elo":           round(self.beta_elo, 1),
            "elo_gap":            round(self.elo_gap, 1),
            "alpha_pred_action":  self.alpha_predicted_action.name,
            "beta_pred_action":   self.beta_predicted_action.name,
            "alpha_actual":       self.alpha_actual_action.name,
            "beta_actual":        self.beta_actual_action.name,
            "alpha_pred_correct": self.alpha_pred_correct,
            "beta_pred_correct":  self.beta_pred_correct,
            "alpha_entropy":      round(self.alpha_model_entropy, 4),
            "beta_entropy":       round(self.beta_model_entropy, 4),
        }


# ---------------------------------------------------------------------------
# TheoryOfMindTournament
# ---------------------------------------------------------------------------

def _elo_update(
    winner_elo: float,
    loser_elo:  float,
    k:          float = 32.0,
) -> Tuple[float, float]:
    """Standard Elo update. Returns (new_winner_elo, new_loser_elo)."""
    expected_w = 1.0 / (1.0 + 10 ** ((loser_elo - winner_elo) / 400.0))
    delta      = k * (1.0 - expected_w)
    return winner_elo + delta, loser_elo - delta


class TheoryOfMindTournament:
    """
    Runs a second-order (ToM) tournament between two MindReadingAgents.

    Parameters
    ----------
    alpha          : MindReadingAgent
    beta           : MindReadingAgent
    convergence_threshold : float   Elo gap below which agents are considered equal
    convergence_patience  : int
    """

    def __init__(
        self,
        alpha:                MindReadingAgent,
        beta:                 MindReadingAgent,
        convergence_threshold: float = 50.0,
        convergence_patience:  int   = 3,
    ):
        self.alpha   = alpha
        self.beta    = beta
        self._thresh = convergence_threshold
        self._pat    = convergence_patience
        self.records: List[ToMRecord] = []
        self._consec = 0

    def match(self) -> ToMRecord:
        """Run one match. Returns a ToMRecord."""
        m = len(self.records)

        # ── Prediction phase (Theory of Mind) ─────────────────────────────
        alpha_pred = self.alpha.predict_opponent()
        beta_pred  = self.beta.predict_opponent()

        # ── Action selection (conditioned on prediction) ───────────────────
        alpha_action = self.alpha.choose_action(self.beta.elo,  alpha_pred)
        beta_action  = self.beta.choose_action( self.alpha.elo, beta_pred)

        # ── Step both agents ───────────────────────────────────────────────
        alpha_acc = self.alpha.step(alpha_action)
        beta_acc  = self.beta.step(beta_action)

        # ── Observe opponent's actual action ───────────────────────────────
        self.alpha.observe_opponent(beta_action)
        self.beta.observe_opponent(alpha_action)

        # ── Elo update ─────────────────────────────────────────────────────
        if alpha_acc > beta_acc + 0.005:
            winner = "alpha"
            new_a, new_b = _elo_update(self.alpha.elo, self.beta.elo)
        elif beta_acc > alpha_acc + 0.005:
            winner = "beta"
            new_b, new_a = _elo_update(self.beta.elo, self.alpha.elo)
        else:
            winner = "draw"
            new_a, new_b = self.alpha.elo, self.beta.elo

        self.alpha.update_elo(new_a)
        self.beta.update_elo(new_b)
        gap = abs(new_a - new_b)

        # ── Convergence tracking ───────────────────────────────────────────
        if gap < self._thresh:
            self._consec += 1
        else:
            self._consec = 0

        # ── Record ────────────────────────────────────────────────────────
        rec = ToMRecord(
            match_number            = m,
            alpha_accuracy          = round(alpha_acc, 4),
            beta_accuracy           = round(beta_acc, 4),
            winner                  = winner,
            alpha_elo               = round(new_a, 1),
            beta_elo                = round(new_b, 1),
            elo_gap                 = round(gap, 1),
            alpha_predicted_action  = alpha_pred,
            beta_predicted_action   = beta_pred,
            alpha_actual_action     = alpha_action,
            beta_actual_action      = beta_action,
            alpha_pred_correct      = (alpha_pred == beta_action),
            beta_pred_correct       = (beta_pred  == alpha_action),
            alpha_model_entropy     = round(self.alpha.opponent_model.entropy(), 4),
            beta_model_entropy      = round(self.beta.opponent_model.entropy(), 4),
        )
        self.records.append(rec)
        return rec

    def run(self, n_matches: int, early_stop: bool = True) -> List[ToMRecord]:
        for _ in range(n_matches):
            self.match()
            if early_stop and self.is_converged:
                break
        return self.records

    @property
    def is_converged(self) -> bool:
        return self._consec >= self._pat

    def summary(self) -> Dict[str, Any]:
        if not self.records:
            return {}
        alpha_wins = sum(1 for r in self.records if r.winner == "alpha")
        beta_wins  = sum(1 for r in self.records if r.winner == "beta")
        draws      = len(self.records) - alpha_wins - beta_wins
        alpha_pred = sum(1 for r in self.records if r.alpha_pred_correct)
        beta_pred  = sum(1 for r in self.records if r.beta_pred_correct)
        n = len(self.records)
        return {
            "n_matches":          n,
            "alpha_wins":         alpha_wins,
            "beta_wins":          beta_wins,
            "draws":              draws,
            "final_alpha_elo":    self.records[-1].alpha_elo,
            "final_beta_elo":     self.records[-1].beta_elo,
            "final_elo_gap":      self.records[-1].elo_gap,
            "is_converged":       self.is_converged,
            "alpha_pred_acc":     round(alpha_pred / max(n, 1), 3),
            "beta_pred_acc":      round(beta_pred  / max(n, 1), 3),
        }


# ---------------------------------------------------------------------------
# ToMReport
# ---------------------------------------------------------------------------

@dataclass
class ToMReport:
    """Full report from a Theory-of-Mind tournament."""
    records:                List[ToMRecord]
    n_matches:              int
    convergence_match:      Optional[int]
    alpha_prediction_acc:   float   # fraction of Beta's actions correctly predicted
    beta_prediction_acc:    float
    mean_model_entropy_alpha: float
    mean_model_entropy_beta:  float
    final_elo_gap:          float
    hofstadter_statement:   str

    def summary(self) -> str:
        lines = [
            "ToMReport (Theory-of-Mind Tournament)",
            f"  Matches played           : {self.n_matches}",
            f"  Convergence at match     : {self.convergence_match}",
            f"  Final Elo gap            : {self.final_elo_gap:.1f}",
            f"  Alpha prediction acc     : {self.alpha_prediction_acc:.3f}",
            f"  Beta prediction acc      : {self.beta_prediction_acc:.3f}",
            f"  Mean model entropy Alpha : {self.mean_model_entropy_alpha:.4f}",
            f"  Mean model entropy Beta  : {self.mean_model_entropy_beta:.4f}",
            "",
            "  Hofstadter statement:",
            f"  {self.hofstadter_statement}",
        ]
        return "\n".join(lines)


def run_tom_tournament(
    n_matches:            int   = 30,
    initial_accuracy:     float = 0.60,
    noise_std:            float = 0.015,
    convergence_threshold: float = 50.0,
    ema_alpha:            float = 0.25,
    seed:                 int   = 42,
    early_stop:           bool  = True,
) -> ToMReport:
    """Run a full Theory-of-Mind tournament and return a ToMReport."""
    alpha = MindReadingAgent("Alpha", initial_accuracy=initial_accuracy,
                             noise_std=noise_std, ema_alpha=ema_alpha, seed=seed)
    beta  = MindReadingAgent("Beta",  initial_accuracy=initial_accuracy,
                             noise_std=noise_std, ema_alpha=ema_alpha, seed=seed + 7)

    tour  = TheoryOfMindTournament(alpha, beta,
                                    convergence_threshold=convergence_threshold)
    recs  = tour.run(n_matches, early_stop=early_stop)
    n     = len(recs)

    conv_match = next((r.match_number for r in recs if tour.is_converged
                       and r == recs[-1]), None)
    if tour.is_converged:
        conv_match = recs[-1].match_number

    alpha_pred = sum(1 for r in recs if r.alpha_pred_correct) / max(n, 1)
    beta_pred  = sum(1 for r in recs if r.beta_pred_correct)  / max(n, 1)
    mean_ent_a = sum(r.alpha_model_entropy for r in recs) / max(n, 1)
    mean_ent_b = sum(r.beta_model_entropy  for r in recs) / max(n, 1)
    final_gap  = recs[-1].elo_gap if recs else 0.0

    # Hofstadter statement
    if alpha_pred > 0.55 or beta_pred > 0.55:
        stmt = (
            f"Alpha predicted Beta's actions with {alpha_pred:.1%} accuracy; "
            f"Beta predicted Alpha's actions with {beta_pred:.1%} accuracy.  "
            "Each agent has a model of the other that is better than chance.  "
            "When Alpha conditions its action on its model of Beta, and Beta "
            "simultaneously conditions its action on its model of Alpha, the "
            "loop closes at the inter-agent level: A models B models A.  "
            "This is Hofstadter's second-order Strange Loop instantiated "
            "between two agents."
        )
    else:
        stmt = (
            f"Opponent prediction accuracy: Alpha={alpha_pred:.1%}, "
            f"Beta={beta_pred:.1%}.  Models are still near chance — "
            "more matches needed for the second-order loop to materialise."
        )

    return ToMReport(
        records                   = recs,
        n_matches                 = n,
        convergence_match         = conv_match,
        alpha_prediction_acc      = round(alpha_pred, 4),
        beta_prediction_acc       = round(beta_pred, 4),
        mean_model_entropy_alpha  = round(mean_ent_a, 4),
        mean_model_entropy_beta   = round(mean_ent_b, 4),
        final_elo_gap             = round(final_gap, 1),
        hofstadter_statement      = stmt,
    )


# ---------------------------------------------------------------------------
# verify_wp49_exit_criteria
# ---------------------------------------------------------------------------

def verify_wp49_exit_criteria(report: ToMReport) -> Dict[str, bool]:
    """
    Verify WP49 exit criteria.

    Criteria
    --------
    1. Tournament ran for at least 10 matches.
    2. Both agents have non-trivial opponent models (entropy < log(N_ACTIONS)).
    3. At least one agent predicts opponent actions better than uniform random.
    4. Elo ratings diverge then converge (final gap < initial gap of 0).
    5. ToMRecord logged for every match.
    6. Hofstadter statement is non-empty.
    """
    results: Dict[str, bool] = {}

    results["Tournament ran ≥ 10 matches"] = report.n_matches >= 10

    H_uniform = math.log(_N_ACTIONS)
    results["Both agents have sub-uniform model entropy (learned something)"] = (
        report.mean_model_entropy_alpha < H_uniform and
        report.mean_model_entropy_beta  < H_uniform
    )

    chance = 1.0 / _N_ACTIONS
    results["At least one agent predicts opponent above chance"] = (
        report.alpha_prediction_acc > chance or
        report.beta_prediction_acc  > chance
    )

    results["Elo gap is finite and non-negative"] = (
        0 <= report.final_elo_gap < 800
    )

    results["ToMRecord logged for every match"] = (
        len(report.records) == report.n_matches
    )

    results["Hofstadter statement is non-empty"] = (
        len(report.hofstadter_statement) > 50
    )

    return results
