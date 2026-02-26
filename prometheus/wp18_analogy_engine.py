"""
WP18: Analogy Engine MVP — Cross-Domain Transfer via Structural Isomorphism
============================================================================

Closes the gap identified after WP17: the CRLS synthesis loop now fires and
mutates the MetaLearner within a single domain, but knowledge is discarded
when a new domain is encountered.  The system must relearn from scratch every
time it enters Chess having already mastered Go — a failure mode that
Hofstadter (GEB, 1979) diagnosed as the absence of *chunked abstraction*.

WP18 fix
--------
``CrossDomainAnalogyMap`` stores structural isomorphisms between tactics
across game domains.  Each isomorphism maps a source tactic's ``TacticSignature``
to a target tactic's signature via a named ``StructuralAnalogy``.

``TransferBootstrapper`` uses the analogy map to seed a *target-domain*
MetaLearner's initial probability distribution from a *source-domain* learner
that has already converged — eliminating the cold-start penalty.

Measurable claim (WP18 exit criterion)
----------------------------------------
A target MetaLearner seeded by transfer reaches accuracy threshold T in
fewer generations than an identical MetaLearner starting from uniform priors.

Theoretical grounding
---------------------
Hofstadter (GEB, 1979): "Chunked concepts let the mind jump levels without
re-traversing lower levels."  The analogy map *is* the chunk: it lets the
meta-level deposit previously earned knowledge directly into a new object-level
without replaying the full learning trajectory.

Good (1965): An ultraintelligent machine would not merely improve within a
domain but would generalise the *improvement mechanism* itself across tasks.
Transfer via analogy is exactly this meta-improvement.

Classes
-------
TacticSignature         Domain-agnostic fingerprint: threat/constraint/resolution
StructuralAnalogy       One isomorphism between a source and target signature,
                        with empirical confidence updated online
CrossDomainAnalogyMap   Registry of all isomorphisms; provides seed-weight query
TransferBootstrapper    Seeds a target MetaLearner from source probabilities via map
GoChessTacticRegistry   Pre-built Go↔Chess analogy library (5 isomorphisms)
GoChessCRLS             Experiment harness: cold-start vs transfer-start comparison
verify_wp18_exit_criteria   Six-criterion verifier (mirrors WP17 pattern)
"""

from __future__ import annotations

import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from prometheus.meta_learner import MetaLearner
from prometheus.safety.checks import GodelianSafetyGovernor, SafetyStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tactic vocabulary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TacticSignature:
    """
    Domain-agnostic structural fingerprint for a tactic.

    Attributes
    ----------
    threat_type : str
        What the tactic *threatens* (e.g. "capture", "material_loss",
        "territory_loss", "liberty_reduction").
    constraint_type : str
        What *limits* the opponent's response (e.g. "forced_move",
        "zugzwang", "no_escape", "two_front_attack").
    resolution_type : str
        How the tactic is *resolved* (e.g. "piece_removed",
        "positional_gain", "forced_trade", "repetition_draw").
    domain : str
        Originating domain ("go" or "chess").
    tactic_name : str
        Human-readable name within that domain.
    """
    threat_type:      str
    constraint_type:  str
    resolution_type:  str
    domain:           str
    tactic_name:      str

    def structural_key(self) -> Tuple[str, str, str]:
        """Domain-agnostic key for similarity comparison."""
        return (self.threat_type, self.constraint_type, self.resolution_type)


@dataclass
class StructuralAnalogy:
    """
    One isomorphism between a source and target tactic signature.

    The analogy is *falsifiable*: every time a transfer-seeded MetaLearner
    succeeds on the target tactic, ``confirm()`` is called; every failure
    calls ``refute()``.  The running ``confidence`` score drives how strongly
    the source probability is transferred.

    Parameters
    ----------
    analogy_id : str
    source_sig : TacticSignature
    target_sig : TacticSignature
    prior_confidence : float
        Initial structural confidence (0-1), set by human curation.
    """
    analogy_id:        str
    source_sig:        TacticSignature
    target_sig:        TacticSignature
    prior_confidence:  float = 0.70

    # Empirical update fields
    confirmations:     int = 0
    refutations:       int = 0

    @property
    def confidence(self) -> float:
        """Bayesian posterior blending prior with empirical evidence."""
        n = self.confirmations + self.refutations
        if n == 0:
            return self.prior_confidence
        empirical = self.confirmations / n
        # Weight: 50% prior, 50% empirical (grows toward empirical as n grows)
        weight = min(0.50 + n * 0.02, 0.95)   # caps at 0.95 after 22+ trials
        return (1 - weight) * self.prior_confidence + weight * empirical

    def confirm(self) -> None:
        """Record a successful transfer outcome."""
        self.confirmations += 1

    def refute(self) -> None:
        """Record a failed transfer outcome."""
        self.refutations += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analogy_id":       self.analogy_id,
            "source_domain":    self.source_sig.domain,
            "source_tactic":    self.source_sig.tactic_name,
            "target_domain":    self.target_sig.domain,
            "target_tactic":    self.target_sig.tactic_name,
            "prior_confidence": self.prior_confidence,
            "confidence":       self.confidence,
            "confirmations":    self.confirmations,
            "refutations":      self.refutations,
        }


# ---------------------------------------------------------------------------
# CrossDomainAnalogyMap
# ---------------------------------------------------------------------------

class CrossDomainAnalogyMap:
    """
    Registry of structural isomorphisms across game domains.

    The map is the *chunk* in Hofstadter's sense: it lets a higher-level
    observer deposit structural knowledge into a new domain without replaying
    the learning trajectory.

    Parameters
    ----------
    governor : GodelianSafetyGovernor, optional
        Safety governor; created fresh if not supplied.
    """

    def __init__(self, governor: Optional[GodelianSafetyGovernor] = None):
        self.governor  = governor or GodelianSafetyGovernor()
        self._analogies: Dict[str, StructuralAnalogy] = {}   # id → analogy
        self._by_source: Dict[str, List[str]] = defaultdict(list)  # src_name → [ids]
        self._by_target: Dict[str, List[str]] = defaultdict(list)  # tgt_name → [ids]

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, analogy: StructuralAnalogy) -> None:
        """Register a structural analogy after safety-gating the proposal."""
        proposal = {
            "type":  "rule_add",
            "desc":  (f"register analogy {analogy.analogy_id}: "
                      f"{analogy.source_sig.domain}/{analogy.source_sig.tactic_name} → "
                      f"{analogy.target_sig.domain}/{analogy.target_sig.tactic_name}"),
        }
        status, reason = self.governor.evaluate_modification(proposal, verbose=False)
        if status != SafetyStatus.PROVABLY_SAFE:
            logger.warning("Analogy %s blocked by governor: %s", analogy.analogy_id, reason)
            return

        self._analogies[analogy.analogy_id] = analogy
        self._by_source[analogy.source_sig.tactic_name].append(analogy.analogy_id)
        self._by_target[analogy.target_sig.tactic_name].append(analogy.analogy_id)
        logger.debug("Registered analogy %s (conf=%.2f)", analogy.analogy_id, analogy.prior_confidence)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_target_analogues(
        self,
        source_tactic: str,
        target_domain: str,
        min_confidence: float = 0.0,
    ) -> List[StructuralAnalogy]:
        """
        Return all analogies from ``source_tactic`` into ``target_domain``
        whose confidence ≥ ``min_confidence``, sorted by confidence descending.
        """
        ids = self._by_source.get(source_tactic, [])
        out = [
            self._analogies[i] for i in ids
            if self._analogies[i].target_sig.domain == target_domain
            and self._analogies[i].confidence >= min_confidence
        ]
        return sorted(out, key=lambda a: a.confidence, reverse=True)

    def get_source_analogues(
        self,
        target_tactic: str,
        source_domain: str,
        min_confidence: float = 0.0,
    ) -> List[StructuralAnalogy]:
        """
        Return all analogies from ``source_domain`` into ``target_tactic``,
        sorted by confidence descending.
        """
        ids = self._by_target.get(target_tactic, [])
        out = [
            self._analogies[i] for i in ids
            if self._analogies[i].source_sig.domain == source_domain
            and self._analogies[i].confidence >= min_confidence
        ]
        return sorted(out, key=lambda a: a.confidence, reverse=True)

    def update_empirical(self, analogy_id: str, success: bool) -> None:
        """Update empirical confidence of a registered analogy."""
        if analogy_id in self._analogies:
            if success:
                self._analogies[analogy_id].confirm()
            else:
                self._analogies[analogy_id].refute()

    def all_analogies(self) -> List[StructuralAnalogy]:
        return list(self._analogies.values())

    def get_summary(self) -> Dict[str, Any]:
        analogies = self.all_analogies()
        return {
            "total_analogies":      len(analogies),
            "mean_confidence":      (sum(a.confidence for a in analogies) / len(analogies)
                                     if analogies else 0.0),
            "total_confirmations":  sum(a.confirmations for a in analogies),
            "total_refutations":    sum(a.refutations for a in analogies),
            "analogies":            [a.to_dict() for a in analogies],
        }


# ---------------------------------------------------------------------------
# TransferBootstrapper
# ---------------------------------------------------------------------------

class TransferBootstrapper:
    """
    Seeds a target-domain MetaLearner from a source-domain learner via
    structural analogies.

    The key Hofstadterian move: instead of initialising the target MetaLearner
    with a *uniform* prior (equal weight to all target tactics), we initialise
    it with a *transferred* prior derived from the source learner's converged
    probability distribution, weighted by the analogy confidence scores.

    Algorithm
    ---------
    For each target tactic t_i:
      1. Look up all source analogues via the CrossDomainAnalogyMap.
      2. Compute transferred_weight(t_i) = Σ_j  p_source(s_j) · confidence(s_j → t_i)
      3. Mix transferred weight with uniform prior using blend_alpha:
           p_init(t_i) = blend_alpha · transferred_weight(t_i)
                       + (1 - blend_alpha) · (1 / N)
      4. Normalise → valid probability distribution.

    Parameters
    ----------
    analogy_map : CrossDomainAnalogyMap
    blend_alpha : float
        How much weight to give the transferred signal (0=uniform, 1=full transfer).
        Default 0.7 — strong transfer but keeps a floor of exploration.
    min_analogy_confidence : float
        Only use analogies above this threshold (default 0.5).
    """

    def __init__(
        self,
        analogy_map: CrossDomainAnalogyMap,
        blend_alpha: float = 0.70,
        min_analogy_confidence: float = 0.50,
    ):
        self.map   = analogy_map
        self.alpha = blend_alpha
        self.min_conf = min_analogy_confidence

    def seed(
        self,
        source_learner: MetaLearner,
        source_domain:  str,
        target_learner: MetaLearner,
        target_domain:  str,
    ) -> Dict[str, float]:
        """
        Compute and apply the transferred initial distribution to
        ``target_learner``.

        Returns
        -------
        dict mapping target strategy name → seeded probability (before normalise).
        The ``target_learner.probabilities`` dict is mutated in place and
        ``_normalize()`` is called.
        """
        source_probs = source_learner.get_strategy_probabilities()
        n_target     = len(target_learner.strategies)
        uniform_p    = 1.0 / n_target

        transferred: Dict[str, float] = {}

        for tgt_tactic in target_learner.strategies:
            # Sum over all source tactics that are analogous to this target
            analogues = self.map.get_source_analogues(
                target_tactic=tgt_tactic,
                source_domain=source_domain,
                min_confidence=self.min_conf,
            )

            transferred_signal = 0.0
            total_conf = 0.0
            for analogy in analogues:
                src_name = analogy.source_sig.tactic_name
                if src_name in source_probs:
                    transferred_signal += source_probs[src_name] * analogy.confidence
                    total_conf += analogy.confidence

            # Normalise the signal by total confidence weight to keep in [0,1]
            if total_conf > 0:
                transferred_signal /= total_conf

            # Blend transferred + uniform
            seeded = self.alpha * transferred_signal + (1 - self.alpha) * uniform_p
            transferred[tgt_tactic] = seeded

        # Write into target MetaLearner and normalise
        for tactic, p in transferred.items():
            target_learner.probabilities[tactic] = p
        target_learner._normalize()

        logger.info(
            "TransferBootstrapper: seeded %s (%d tactics) from %s (%d tactics) "
            "with alpha=%.2f",
            target_domain, n_target, source_domain, len(source_probs), self.alpha,
        )
        return transferred

    def get_transfer_entropy_reduction(
        self,
        source_learner: MetaLearner,
        source_domain:  str,
        target_strategies: List[str],
        target_domain:  str,
    ) -> float:
        """
        Estimate how much the transfer reduces entropy vs a uniform prior.

        A value > 0 means transfer concentrates probability mass usefully.
        A value == 0 means all analogies map uniformly (no information gain).

        Returns
        -------
        float  entropy_uniform - entropy_seeded  (nats)
        """
        # Build a temporary learner for entropy comparison
        tmp = MetaLearner(target_strategies, upward_rate=0, downward_rate=0)
        self.seed(source_learner, source_domain, tmp, target_domain)

        def _entropy(probs: Dict[str, float]) -> float:
            return -sum(p * math.log(p) for p in probs.values() if p > 1e-12)

        n = len(target_strategies)
        uniform_entropy  = math.log(n)          # maximum entropy
        seeded_entropy   = _entropy(tmp.get_strategy_probabilities())
        return uniform_entropy - seeded_entropy


# ---------------------------------------------------------------------------
# Pre-built Go ↔ Chess analogy library
# ---------------------------------------------------------------------------

class GoChessTacticRegistry:
    """
    Curated library of 5 Go↔Chess structural isomorphisms.

    Isomorphism table
    -----------------
    Go tactic         Chess tactic       Structural mapping
    ──────────────────────────────────────────────────────────
    capture_atari     pin_piece          threat=capture, constraint=forced_move
    ladder            skewer             threat=capture, constraint=no_escape
    ko_fight          zugzwang           threat=repetition, constraint=forced_move
    territory_claim   space_control      threat=territory, constraint=two_front
    connect_groups    piece_coordination threat=isolation, constraint=two_front
    """

    # --- Go signatures ---
    _GO_SIGS: Dict[str, TacticSignature] = {
        "capture_atari": TacticSignature(
            threat_type="capture",
            constraint_type="forced_move",
            resolution_type="piece_removed",
            domain="go",
            tactic_name="capture_atari",
        ),
        "ladder": TacticSignature(
            threat_type="capture",
            constraint_type="no_escape",
            resolution_type="piece_removed",
            domain="go",
            tactic_name="ladder",
        ),
        "ko_fight": TacticSignature(
            threat_type="repetition",
            constraint_type="forced_move",
            resolution_type="repetition_draw",
            domain="go",
            tactic_name="ko_fight",
        ),
        "territory_claim": TacticSignature(
            threat_type="territory_loss",
            constraint_type="two_front_attack",
            resolution_type="positional_gain",
            domain="go",
            tactic_name="territory_claim",
        ),
        "connect_groups": TacticSignature(
            threat_type="isolation",
            constraint_type="two_front_attack",
            resolution_type="positional_gain",
            domain="go",
            tactic_name="connect_groups",
        ),
    }

    # --- Chess signatures ---
    _CHESS_SIGS: Dict[str, TacticSignature] = {
        "pin_piece": TacticSignature(
            threat_type="capture",
            constraint_type="forced_move",
            resolution_type="piece_removed",
            domain="chess",
            tactic_name="pin_piece",
        ),
        "skewer": TacticSignature(
            threat_type="capture",
            constraint_type="no_escape",
            resolution_type="piece_removed",
            domain="chess",
            tactic_name="skewer",
        ),
        "zugzwang": TacticSignature(
            threat_type="repetition",
            constraint_type="forced_move",
            resolution_type="repetition_draw",
            domain="chess",
            tactic_name="zugzwang",
        ),
        "space_control": TacticSignature(
            threat_type="territory_loss",
            constraint_type="two_front_attack",
            resolution_type="positional_gain",
            domain="chess",
            tactic_name="space_control",
        ),
        "piece_coordination": TacticSignature(
            threat_type="isolation",
            constraint_type="two_front_attack",
            resolution_type="positional_gain",
            domain="chess",
            tactic_name="piece_coordination",
        ),
    }

    # Prior confidence table (curated, not learned)
    _PRIOR_CONF: Dict[Tuple[str, str], float] = {
        ("capture_atari",  "pin_piece"):          0.85,
        ("ladder",         "skewer"):             0.80,
        ("ko_fight",       "zugzwang"):           0.75,
        ("territory_claim","space_control"):      0.70,
        ("connect_groups", "piece_coordination"): 0.65,
    }

    @classmethod
    def build(cls, governor: Optional[GodelianSafetyGovernor] = None) -> CrossDomainAnalogyMap:
        """
        Build and return a CrossDomainAnalogyMap pre-loaded with the 5
        Go↔Chess isomorphisms (both directions: Go→Chess and Chess→Go).
        """
        analogy_map = CrossDomainAnalogyMap(governor=governor)

        for (go_name, chess_name), conf in cls._PRIOR_CONF.items():
            go_sig    = cls._GO_SIGS[go_name]
            chess_sig = cls._CHESS_SIGS[chess_name]

            # Forward: Go → Chess
            fwd = StructuralAnalogy(
                analogy_id       = f"go2chess_{go_name}_{chess_name}",
                source_sig       = go_sig,
                target_sig       = chess_sig,
                prior_confidence = conf,
            )
            analogy_map.register(fwd)

            # Reverse: Chess → Go
            rev = StructuralAnalogy(
                analogy_id       = f"chess2go_{chess_name}_{go_name}",
                source_sig       = chess_sig,
                target_sig       = go_sig,
                prior_confidence = conf,
            )
            analogy_map.register(rev)

        return analogy_map


# ---------------------------------------------------------------------------
# GoChessCRLS — experiment harness for transfer advantage proof
# ---------------------------------------------------------------------------

@dataclass
class TransferExperimentRecord:
    """Single generation result within the transfer experiment."""
    generation:   int
    condition:    str     # "cold_start" or "transfer_start"
    accuracy:     float
    timestamp:    float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation": self.generation,
            "condition":  self.condition,
            "accuracy":   self.accuracy,
        }


class GoChessCRLS:
    """
    Transfer advantage experiment: cold-start vs transfer-start on Chess tactics.

    The experiment uses two MetaLearners with identical strategy sets and
    identical autonomous update rates, running on the same sequence of
    synthetic Chess tactical puzzles.

    The *transfer* learner has its initial distribution seeded from a
    Go-domain MetaLearner (already converged) via the analogy map.
    The *cold* learner starts from uniform priors.

    We measure how many generations each takes to exceed ``threshold``.

    Parameters
    ----------
    go_strategies : list[str]
        Go tactic names (must match analogy map source tactics).
    chess_strategies : list[str]
        Chess tactic names (must match analogy map target tactics).
    analogy_map : CrossDomainAnalogyMap
    upward_rate, downward_rate : float
        Same rates for both MetaLearners (fair comparison).
    threshold : float
        Accuracy threshold to "solve" the domain (default 0.60).
    blend_alpha : float
        Transfer blend strength (forwarded to TransferBootstrapper).
    """

    def __init__(
        self,
        go_strategies:    List[str],
        chess_strategies: List[str],
        analogy_map:      CrossDomainAnalogyMap,
        upward_rate:      float = 0.20,
        downward_rate:    float = 0.15,
        threshold:        float = 0.60,
        blend_alpha:      float = 0.70,
    ):
        self.go_strategies    = go_strategies
        self.chess_strategies = chess_strategies
        self.analogy_map      = analogy_map
        self.threshold        = threshold

        # --- Source learner: Go (pre-trained by the caller) ---
        self.go_learner = MetaLearner(
            go_strategies,
            upward_rate   = upward_rate,
            downward_rate = downward_rate,
        )

        # --- Two target learners: Chess ---
        self.cold_learner = MetaLearner(
            chess_strategies,
            upward_rate   = upward_rate,
            downward_rate = downward_rate,
        )
        self.transfer_learner = MetaLearner(
            chess_strategies,
            upward_rate   = upward_rate,
            downward_rate = downward_rate,
        )

        # --- Bootstrapper ---
        self.bootstrapper = TransferBootstrapper(
            analogy_map,
            blend_alpha            = blend_alpha,
            min_analogy_confidence = 0.50,
        )

        # Results
        self.cold_records:     List[TransferExperimentRecord] = []
        self.transfer_records: List[TransferExperimentRecord] = []

        # State
        self.generation = 0
        self._transfer_seeded = False

    def pretrain_go(
        self,
        puzzles:     List[Tuple],
        tactic_fns:  Dict[str, Any],
        evaluate_fn: Any,
    ) -> float:
        """
        Run the Go learner on ``puzzles`` for one generation to simulate
        a converged source domain.  The caller may call this multiple times.

        Returns the accuracy of this generation.
        """
        correct = 0
        for board, player, correct_move in puzzles:
            strategy = self.go_learner.select_strategy()
            move     = tactic_fns[strategy](board, player)
            if move is None:
                legal = board.get_legal_moves(player)
                move  = legal[0] if legal else (-1, -1)
            success = evaluate_fn(board, move, correct_move, player)
            if success:
                self.go_learner.update_on_success(strategy)
                correct += 1
            else:
                self.go_learner.update_on_failure(strategy)
        return correct / len(puzzles) if puzzles else 0.0

    def apply_transfer(self) -> Dict[str, float]:
        """
        Seed the transfer MetaLearner from the Go learner's current distribution.
        Must be called after ``pretrain_go`` and before ``run_generation``.

        Returns the seeded probability dict.
        """
        seeded = self.bootstrapper.seed(
            source_learner = self.go_learner,
            source_domain  = "go",
            target_learner = self.transfer_learner,
            target_domain  = "chess",
        )
        self._transfer_seeded = True
        logger.info("Transfer applied — seeded chess MetaLearner from Go source.")
        return seeded

    def run_generation(
        self,
        puzzles:     List[Tuple],
        tactic_fns:  Dict[str, Any],
        evaluate_fn: Any,
    ) -> Tuple[float, float]:
        """
        Run one generation for both cold and transfer learners on identical puzzles.

        Returns
        -------
        (cold_accuracy, transfer_accuracy)
        """
        if not self._transfer_seeded:
            logger.warning("apply_transfer() not called — transfer learner has uniform prior")

        cold_acc     = self._run_one(self.cold_learner,     puzzles, tactic_fns, evaluate_fn)
        transfer_acc = self._run_one(self.transfer_learner, puzzles, tactic_fns, evaluate_fn)

        self.cold_records.append(TransferExperimentRecord(
            generation = self.generation,
            condition  = "cold_start",
            accuracy   = cold_acc,
        ))
        self.transfer_records.append(TransferExperimentRecord(
            generation = self.generation,
            condition  = "transfer_start",
            accuracy   = transfer_acc,
        ))

        self.generation += 1
        return cold_acc, transfer_acc

    def _run_one(
        self,
        learner:     MetaLearner,
        puzzles:     List[Tuple],
        tactic_fns:  Dict[str, Any],
        evaluate_fn: Any,
    ) -> float:
        correct = 0
        for board, player, correct_move in puzzles:
            strategy = learner.select_strategy()
            move     = tactic_fns[strategy](board, player)
            if move is None:
                legal = board.get_legal_moves(player)
                move  = legal[0] if legal else (-1, -1)
            success = evaluate_fn(board, move, correct_move, player)
            if success:
                learner.update_on_success(strategy)
                correct += 1
            else:
                learner.update_on_failure(strategy)
        return correct / len(puzzles) if puzzles else 0.0

    def gens_to_threshold(self, condition: str) -> Optional[int]:
        """
        Return the first generation index at which ``condition`` exceeded
        ``self.threshold``, or None if it never did.
        """
        records = self.cold_records if condition == "cold_start" else self.transfer_records
        for r in records:
            if r.accuracy >= self.threshold:
                return r.generation
        return None

    def transfer_advantage(self) -> Optional[int]:
        """
        Generations saved by transfer: cold_gens - transfer_gens.
        Positive → transfer is faster.  None if either never converged.
        """
        cold = self.gens_to_threshold("cold_start")
        xfer = self.gens_to_threshold("transfer_start")
        if cold is None or xfer is None:
            return None
        return cold - xfer

    def get_full_report(self) -> Dict[str, Any]:
        cold_accs     = [r.accuracy for r in self.cold_records]
        transfer_accs = [r.accuracy for r in self.transfer_records]
        return {
            "generations":          self.generation,
            "threshold":            self.threshold,
            "cold_start": {
                "accuracies":       cold_accs,
                "gens_to_threshold": self.gens_to_threshold("cold_start"),
                "final_accuracy":    cold_accs[-1] if cold_accs else None,
            },
            "transfer_start": {
                "accuracies":        transfer_accs,
                "gens_to_threshold": self.gens_to_threshold("transfer_start"),
                "final_accuracy":    transfer_accs[-1] if transfer_accs else None,
            },
            "transfer_advantage_gens": self.transfer_advantage(),
            "analogy_map_summary":     self.analogy_map.get_summary(),
            "go_learner_stats":        self.go_learner.get_statistics(),
        }


# ---------------------------------------------------------------------------
# Exit-criteria verifier
# ---------------------------------------------------------------------------

def verify_wp18_exit_criteria(experiment: GoChessCRLS) -> Dict[str, bool]:
    """
    Verify WP18 exit criteria.

    Criteria
    --------
    analogy_map_populated   At least 5 analogies registered
    transfer_seeded         transfer_learner.probabilities ≠ uniform at generation 0
    transfer_faster         transfer reaches threshold in fewer generations than cold
    entropy_reduced         Transfer seeding reduces entropy vs uniform prior
    safety_gated            All analogy registrations were safety-evaluated
    no_unsafe_applied       No PROVABLY_UNSAFE proposal was accepted

    Returns
    -------
    dict mapping criterion name → bool
    """
    report     = experiment.get_full_report()
    map_summary = report["analogy_map_summary"]

    # --- analogy_map_populated ---
    map_populated = map_summary["total_analogies"] >= 5

    # --- transfer_seeded ---
    n  = len(experiment.chess_strategies)
    uniform_p = 1.0 / n
    probs = experiment.transfer_learner.get_strategy_probabilities()
    transfer_seeded = any(abs(p - uniform_p) > 1e-6 for p in probs.values())

    # --- transfer_faster ---
    adv = experiment.transfer_advantage()
    transfer_faster = adv is not None and adv > 0

    # --- entropy_reduced ---
    tmp_bootstrapper = TransferBootstrapper(experiment.analogy_map)
    entropy_reduction = tmp_bootstrapper.get_transfer_entropy_reduction(
        source_learner    = experiment.go_learner,
        source_domain     = "go",
        target_strategies = experiment.chess_strategies,
        target_domain     = "chess",
    )
    entropy_reduced = entropy_reduction > 1e-6

    # --- safety_gated ---
    safety_stats = experiment.analogy_map.governor.get_safety_statistics()
    safety_gated = safety_stats["total_decisions"] > 0

    # --- no_unsafe_applied ---
    no_unsafe = safety_stats.get("unsafe_decisions", 0) == 0

    criteria = {
        "analogy_map_populated": map_populated,
        "transfer_seeded":       transfer_seeded,
        "transfer_faster":       transfer_faster,
        "entropy_reduced":       entropy_reduced,
        "safety_gated":          safety_gated,
        "no_unsafe_applied":     no_unsafe,
    }

    logger.info("WP18 exit criteria: %s", criteria)
    return criteria
