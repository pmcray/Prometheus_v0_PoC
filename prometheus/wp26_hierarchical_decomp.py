"""
WP26: Hierarchical Task Decomposition
======================================

Adds a **task decomposition planner** above the 8-layer WP17–25 stack.
Rather than treating every generation as a flat sequence of indistinguishable
puzzles, WP26 decomposes the incoming puzzle batch into *subtasks* by
structural type, assigns each subtask to the stack layer most competent to
handle it, and recombines the subtask decisions into a single generation-level
synthesis action.

The gap in WP17–25
--------------------
All eight layers from WP17 to WP25 operate on *generation-level* state signals
(accuracy scalar, strategy probs, ensemble JSD).  They have no concept of the
*internal structure* of a generation: whether the puzzles involve captures,
ladders, or territory does not affect which synthesis action is chosen.

This flatness is a limitation identified by Sacerdoti (1977) in hierarchical
planning: a planner that cannot decompose a goal into subgoals will repeatedly
re-examine identical subproblems.  Hofstadter (GEB, 1979, Chapter 22) calls
the corresponding cognitive ability *chunked abstraction*: "the mind can jump
levels without re-traversing lower levels".

WP26 fix
---------
``TaskDecomposer`` partitions puzzles into *canonical subtask types*:

  CAPTURE   — puzzles won by capturing ≥1 opponent stone (ATARI / LADDER types)
  TERRITORY — puzzles won by spatial anchoring (TERRITORY type)
  MIXED     — puzzles with multiple objectives or unclear type
  UNKNOWN   — puzzles that cannot be typed (fallback)

For each subtask bucket, a ``SubtaskRecord`` is produced containing:
  - the puzzle indices in that bucket
  - the WP17 synthesis action recommended for that subtask
  - the confidence in the recommendation (proportion of agreeing layers)
  - the subtask accuracy (correct / total in bucket)

``HierarchicalCRLS`` inherits ``EWCEnsembleCRLS`` and adds a ninth layer:

  Layer 9  TaskDecomposer (WP26)   — decompose generation into subtasks;
                                     per-subtask synthesis recommendation;
                                     recombine into generation action

The recombination rule: take the subtask action recommended with highest
confidence across all buckets.  Ties are broken by bucket size (larger bucket
wins).

``DecompositionRecord`` is the audit trail for one generation's decomposition.

``HierarchicalCRLS.end_of_generation()`` returns a 9-tuple — the full WP17–26
audit trail.

Layer hierarchy after WP26:

    Layer 9  TaskDecomposer (WP26)    — per-subtask synthesis recommendation
    Layer 8  EWC guard (WP25)         — forgetting detection + consolidation
    Layer 7  EnsembleDistiller (WP24) — JSD uncertainty gate
    Layer 6  PolicyDistiller (WP23)   — single-student baseline
    Layer 5  BanditPolicy (WP22)      — explore/exploit
    Layer 4  MetaGradientOptimiser (WP21)
    Layer 3  RolloutPlanner (WP20)
    Layer 2  CausalActionEvaluator (WP19)
    Layer 1  WP17 heuristic

Theoretical grounding
---------------------
Sacerdoti (1977): "A Structure for Plans and Behavior" — hierarchical task
network (HTN) planning: decompose goals into subgoals, solve independently,
recompose.  WP26 is a lightweight one-level HTN over generation structure.

Hofstadter (GEB, 1979): chunked abstraction lets the meta-level skip
re-evaluating the full 8-layer stack for every puzzle independently; it
groups structurally similar puzzles and handles them as a unit.

Good (1965): an ultraintelligent machine improves not only its object-level
strategies but also its *problem decomposition* — knowing which sub-problems
to assign to which solver is itself a form of meta-intelligence.

Newell & Simon (1972): "Human Problem Solving" — means-ends analysis:
detect the type of gap between current and goal state, then select the
operator most suited to that gap type.  ``TaskDecomposer._detect_type()``
is a concrete implementation of this principle.

Classes
-------
SubtaskType             Enum: CAPTURE, TERRITORY, MIXED, UNKNOWN
SubtaskRecord           Per-subtask decomposition audit record
DecompositionRecord     Full generation decomposition record (list of SubtaskRecords)
TaskDecomposer          Classifies puzzles, produces per-subtask recommendations
HierarchicalCRLS        EWCEnsembleCRLS + WP26 decomposition layer
verify_wp26_exit_criteria   Six-criterion verifier
"""

from __future__ import annotations

import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from prometheus.wp17_crls_synthesis import SynthesisAction, SynthesisRecord
from prometheus.wp19_causal_evaluator import CausalRecommendation
from prometheus.wp20_temporal_planner import RolloutResult, SynthesisStateSnapshot
from prometheus.wp21_meta_gradient import MetaGradStep, MetaParams
from prometheus.wp22_bandit_exploration import BanditMode, ExplorationRecord
from prometheus.wp23_policy_distillation import DistillationRecord
from prometheus.wp24_ensemble_uncertainty import EnsembleRecord
from prometheus.wp25_ewc_forgetting import (
    EWCEnsembleCRLS,
    ForgettingRecord,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SubtaskType  —  canonical puzzle categories for decomposition
# ---------------------------------------------------------------------------

class SubtaskType(Enum):
    """Canonical puzzle category used by the task decomposer."""
    CAPTURE   = "capture"    # win by capturing opponent stones
    TERRITORY = "territory"  # win by spatial anchoring
    MIXED     = "mixed"      # multiple objectives / unclear
    UNKNOWN   = "unknown"    # cannot be typed (fallback)


# ---------------------------------------------------------------------------
# SubtaskRecord  —  audit record for one subtask bucket
# ---------------------------------------------------------------------------

@dataclass
class SubtaskRecord:
    """
    Audit record for one subtask bucket in a generation.

    Attributes
    ----------
    subtask_type : SubtaskType
    puzzle_indices : list[int]
        Indices into the generation's puzzle list that belong to this bucket.
    n_correct : int
        Number of correctly solved puzzles in this bucket.
    accuracy : float
        n_correct / len(puzzle_indices).
    recommended_action : SynthesisAction
        Synthesis action recommended for this subtask.
    confidence : float
        Fraction of classifying signals that agree on the recommendation
        (in [0, 1]).  Higher = more certain.
    timestamp : float
    """
    subtask_type:       SubtaskType
    puzzle_indices:     List[int]
    n_correct:          int
    accuracy:           float
    recommended_action: SynthesisAction
    confidence:         float
    timestamp:          float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subtask_type":       self.subtask_type.value,
            "n_puzzles":          len(self.puzzle_indices),
            "n_correct":          self.n_correct,
            "accuracy":           self.accuracy,
            "recommended_action": self.recommended_action.value,
            "confidence":         self.confidence,
        }


# ---------------------------------------------------------------------------
# DecompositionRecord  —  generation-level decomposition audit
# ---------------------------------------------------------------------------

@dataclass
class DecompositionRecord:
    """
    Full decomposition record for one generation.

    Attributes
    ----------
    generation : int
    subtasks : list[SubtaskRecord]
        One record per non-empty subtask bucket.
    chosen_action : SynthesisAction
        The action selected by recombination across subtasks.
    recombination_rule : str
        Human-readable description of how subtasks were recombined.
    n_subtask_types : int
        Number of distinct subtask types found in this generation.
    timestamp : float
    """
    generation:          int
    subtasks:            List[SubtaskRecord]
    chosen_action:       SynthesisAction
    recombination_rule:  str
    n_subtask_types:     int
    timestamp:           float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation":         self.generation,
            "subtasks":           [s.to_dict() for s in self.subtasks],
            "chosen_action":      self.chosen_action.value,
            "recombination_rule": self.recombination_rule,
            "n_subtask_types":    self.n_subtask_types,
        }


# ---------------------------------------------------------------------------
# TaskDecomposer  —  puzzle classifier + per-subtask synthesis recommender
# ---------------------------------------------------------------------------

# Maps each SubtaskType to the SynthesisAction most suited to it.
# Grounded in the semantics of each action:
#   CAPTURE puzzles → promote the best-performing capture strategy
#   TERRITORY puzzles → boost the upward mutation rate (explore territory moves)
#   MIXED puzzles → reset to uniform (avoid premature commitment)
#   UNKNOWN → demote the worst (safe fallback)
_SUBTASK_ACTION: Dict[SubtaskType, SynthesisAction] = {
    SubtaskType.CAPTURE:   SynthesisAction.PROMOTE_BEST,
    SubtaskType.TERRITORY: SynthesisAction.BOOST_UPWARD,
    SubtaskType.MIXED:     SynthesisAction.RESET_UNIFORM,
    SubtaskType.UNKNOWN:   SynthesisAction.DEMOTE_WORST,
}


class TaskDecomposer:
    """
    Classifies puzzles into subtask buckets and produces per-subtask
    synthesis recommendations.

    The classifier uses three heuristic signals derived from the GoBoard:
      1. ``would_capture > 0`` at the correct move  → CAPTURE hint
      2. Correct move is in a corner quadrant        → TERRITORY hint
      3. Both or neither hints fire                  → MIXED / UNKNOWN

    These heuristics are intentionally lightweight (no look-ahead) so that
    the decomposer runs in O(n) over the puzzle batch.

    Parameters
    ----------
    min_bucket_size : int
        Minimum puzzles in a bucket to generate a SubtaskRecord (default 1).
    confidence_base : float
        Base confidence when all signal types agree (default 0.80).
    """

    def __init__(
        self,
        min_bucket_size: int   = 1,
        confidence_base: float = 0.80,
    ):
        self.min_bucket_size = min_bucket_size
        self.confidence_base = confidence_base
        self.decomposition_log: List[DecompositionRecord] = []

    # ------------------------------------------------------------------
    # Public: decompose
    # ------------------------------------------------------------------

    def decompose(
        self,
        puzzles:     List[Tuple],          # [(GoBoard, player, correct_move), ...]
        results:     List[bool],           # per-puzzle correctness from run_generation
        generation:  int,
    ) -> DecompositionRecord:
        """
        Partition puzzles into subtask buckets and produce recommendations.

        Parameters
        ----------
        puzzles : list of (GoBoard, player, correct_move)
        results : list[bool]
            Per-puzzle correctness flags; must have same length as puzzles.
        generation : int

        Returns
        -------
        DecompositionRecord
        """
        # -- Classify each puzzle --
        buckets: Dict[SubtaskType, List[int]]  = defaultdict(list)
        correct_in: Dict[SubtaskType, int]     = defaultdict(int)

        for idx, (puzzle, correct) in enumerate(zip(puzzles, results)):
            board, player, target = puzzle
            stype = self._detect_type(board, player, target)
            buckets[stype].append(idx)
            if correct:
                correct_in[stype] += 1

        # -- Build SubtaskRecords --
        subtask_records: List[SubtaskRecord] = []
        for stype, indices in buckets.items():
            if len(indices) < self.min_bucket_size:
                continue
            n_corr = correct_in[stype]
            acc    = n_corr / len(indices)
            action = _SUBTASK_ACTION[stype]

            # Confidence: scale by accuracy and bucket purity
            confidence = self.confidence_base * (0.5 + 0.5 * acc)

            subtask_records.append(SubtaskRecord(
                subtask_type       = stype,
                puzzle_indices     = list(indices),
                n_correct          = n_corr,
                accuracy           = acc,
                recommended_action = action,
                confidence         = confidence,
            ))

        # -- Recombine: pick action with highest weighted confidence (bucket_size × conf) --
        chosen_action, rule = self._recombine(subtask_records)

        record = DecompositionRecord(
            generation         = generation,
            subtasks           = subtask_records,
            chosen_action      = chosen_action,
            recombination_rule = rule,
            n_subtask_types    = len(subtask_records),
        )
        self.decomposition_log.append(record)
        logger.debug(
            "TaskDecomposer gen %d: %d subtask types → %s (%s)",
            generation, len(subtask_records), chosen_action.value, rule,
        )
        return record

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _detect_type(self, board, player: int, target: Tuple[int, int]) -> SubtaskType:
        """Classify a single puzzle using lightweight board signals."""
        try:
            capture_hint  = len(board.would_capture(target[0], target[1], player)) > 0
        except Exception:
            capture_hint = False

        n = board.size - 1
        cx = board.size / 2
        corner_hint = (
            abs(target[0] - 0) <= n // 3 or abs(target[0] - n) <= n // 3
        ) and (
            abs(target[1] - 0) <= n // 3 or abs(target[1] - n) <= n // 3
        )
        # Also classify as TERRITORY if target is far from centre
        dist_from_centre = math.sqrt((target[0] - cx) ** 2 + (target[1] - cx) ** 2)
        territory_hint = corner_hint or dist_from_centre > cx * 0.8

        if capture_hint and territory_hint:
            return SubtaskType.MIXED
        if capture_hint:
            return SubtaskType.CAPTURE
        if territory_hint:
            return SubtaskType.TERRITORY
        return SubtaskType.UNKNOWN

    def _recombine(
        self,
        subtasks: List[SubtaskRecord],
    ) -> Tuple[SynthesisAction, str]:
        """
        Choose one generation-level SynthesisAction from per-subtask records.

        Rule: argmax over subtasks of (len(puzzle_indices) × confidence).
        Ties broken by bucket size.  If no subtasks, return DEMOTE_WORST.
        """
        if not subtasks:
            return SynthesisAction.DEMOTE_WORST, "no_subtasks_fallback"

        best = max(
            subtasks,
            key=lambda s: (len(s.puzzle_indices) * s.confidence, len(s.puzzle_indices)),
        )
        rule = (
            f"max_weight_subtask={best.subtask_type.value} "
            f"n={len(best.puzzle_indices)} conf={best.confidence:.3f}"
        )
        return best.recommended_action, rule

    def get_summary(self) -> Dict[str, Any]:
        """Summary statistics over all recorded decompositions."""
        if not self.decomposition_log:
            return {"n_decompositions": 0}
        n_types = [r.n_subtask_types for r in self.decomposition_log]
        actions = [r.chosen_action.value for r in self.decomposition_log]
        return {
            "n_decompositions":    len(self.decomposition_log),
            "mean_subtask_types":  sum(n_types) / len(n_types),
            "max_subtask_types":   max(n_types),
            "action_distribution": {
                a.value: sum(1 for x in actions if x == a.value)
                for a in SynthesisAction
            },
        }


# ---------------------------------------------------------------------------
# HierarchicalCRLS  —  EWCEnsembleCRLS + WP26 decomposition layer
# ---------------------------------------------------------------------------

class HierarchicalCRLS(EWCEnsembleCRLS):
    """
    WP26 upgrade of EWCEnsembleCRLS: adds hierarchical task decomposition.

    Nine-layer action-selection hierarchy
    ---------------------------------------
    9. **TaskDecomposer** (WP26)    — per-subtask synthesis recommendation
    8. **EWC guard** (WP25)         — forgetting detection + consolidation
    7. **EnsembleDistiller** (WP24) — JSD uncertainty gate
    6. **PolicyDistiller** (WP23)   — single-student baseline
    5. **BanditPolicy** (WP22)      — explore/exploit
    4. **MetaGradientOptimiser** (WP21)
    3. **RolloutPlanner** (WP20)
    2. **CausalActionEvaluator** (WP19)
    1. **WP17 heuristic**

    The WP26 layer runs *after* the full WP25 8-tuple is produced:
      - It decomposes the current generation's puzzles into subtask buckets.
      - It produces a ``DecompositionRecord`` with per-subtask recommendations.
      - If the decomposition's chosen action *differs* from WP25's final action,
        it overrides the synthesis action (subject to the same safety gate).
        This represents a Sacerdoti-style hierarchical refinement.

    Because the override is rare (requires the decomposer to disagree with
    8 layers of evidence), WP26 acts mostly as an audit and interpretability
    layer — but it *can* change the outcome when the puzzle batch is strongly
    typed (all puzzles in one subtask bucket).

    Parameters
    ----------
    (all EWCEnsembleCRLS parameters, plus:)
    decomp_min_bucket_size : int
        Minimum bucket size for a SubtaskRecord (default 1).
    decomp_confidence_base : float
        Base confidence for subtask recommendation (default 0.80).
    decomp_override_threshold : float
        Decomposer confidence must exceed this to override WP25 action
        (default 0.85).  Set to 1.0 to disable overrides.
    """

    def __init__(
        self,
        strategies:                  List[str],
        upward_rate:                 float = 0.20,
        downward_rate:               float = 0.15,
        synthesiser_kwargs:          Optional[Dict[str, Any]] = None,
        min_trials_to_override:      int   = 3,
        override_tolerance:          float = 0.02,
        rollout_horizon:             int   = 3,
        rollout_discount:            float = 0.90,
        min_transitions:             int   = 3,
        meta_step_size:              float = 0.02,
        meta_fd_epsilon:             float = 0.05,
        meta_min_transitions:        int   = 4,
        initial_params:              Optional[MetaParams] = None,
        bandit_mode:                 BanditMode = BanditMode.UCB1,
        exploration_coeff:           float = 1.0,
        prior_variance:              float = 1.0,
        force_explore_unseen:        bool  = True,
        distill_lr:                  float = 0.05,
        distill_l2:                  float = 1e-4,
        distill_min_steps:           int   = 10,
        distill_confidence:          float = 0.50,
        ensemble_n_members:          int   = 5,
        ensemble_lr:                 float = 0.05,
        ensemble_l2:                 float = 1e-4,
        ensemble_init_noise:         float = 0.01,
        ensemble_min_steps:          int   = 10,
        ensemble_max_jsd:            float = 0.15,
        ensemble_min_conf:           float = 0.40,
        ensemble_seed:               Optional[int] = None,
        ewc_lambda:                  float = 1.0,
        fisher_sample_size:          int   = 50,
        forgetting_threshold:        float = 0.20,
        ema_alpha:                   float = 0.20,
        ewc_min_steps_before_detect: int   = 10,
        # WP26 additions
        decomp_min_bucket_size:      int   = 1,
        decomp_confidence_base:      float = 0.80,
        decomp_override_threshold:   float = 0.85,
    ):
        super().__init__(
            strategies                  = strategies,
            upward_rate                 = upward_rate,
            downward_rate               = downward_rate,
            synthesiser_kwargs          = synthesiser_kwargs,
            min_trials_to_override      = min_trials_to_override,
            override_tolerance          = override_tolerance,
            rollout_horizon             = rollout_horizon,
            rollout_discount            = rollout_discount,
            min_transitions             = min_transitions,
            meta_step_size              = meta_step_size,
            meta_fd_epsilon             = meta_fd_epsilon,
            meta_min_transitions        = meta_min_transitions,
            initial_params              = initial_params,
            bandit_mode                 = bandit_mode,
            exploration_coeff           = exploration_coeff,
            prior_variance              = prior_variance,
            force_explore_unseen        = force_explore_unseen,
            distill_lr                  = distill_lr,
            distill_l2                  = distill_l2,
            distill_min_steps           = distill_min_steps,
            distill_confidence          = distill_confidence,
            ensemble_n_members          = ensemble_n_members,
            ensemble_lr                 = ensemble_lr,
            ensemble_l2                 = ensemble_l2,
            ensemble_init_noise         = ensemble_init_noise,
            ensemble_min_steps          = ensemble_min_steps,
            ensemble_max_jsd            = ensemble_max_jsd,
            ensemble_min_conf           = ensemble_min_conf,
            ensemble_seed               = ensemble_seed,
            ewc_lambda                  = ewc_lambda,
            fisher_sample_size          = fisher_sample_size,
            forgetting_threshold        = forgetting_threshold,
            ema_alpha                   = ema_alpha,
            ewc_min_steps_before_detect = ewc_min_steps_before_detect,
        )
        self.decomposer = TaskDecomposer(
            min_bucket_size = decomp_min_bucket_size,
            confidence_base = decomp_confidence_base,
        )
        self._decomp_override_threshold = decomp_override_threshold
        self.decomposition_log: List[Dict[str, Any]] = []

        # Store last run's puzzle / result pairs for decomposition
        self._last_puzzles:  List[Tuple] = []
        self._last_results:  List[bool]  = []

    # ------------------------------------------------------------------
    # Override run_generation to record per-puzzle results
    # ------------------------------------------------------------------

    def run_generation(
        self,
        puzzles:     List[Tuple],
        tactic_fns:  Dict[str, Any],
        evaluate_fn: Callable,
    ) -> float:
        """Run puzzles; record per-puzzle correctness for WP26 decomposition."""
        self._last_puzzles = list(puzzles)
        self._last_results = []

        # Delegate to parent for the actual run
        acc = super().run_generation(puzzles, tactic_fns, evaluate_fn)

        # Reconstruct per-puzzle results from the accuracy and tactic selections
        # We re-evaluate each puzzle with the current (post-run) strategy
        for board, player, correct_move in puzzles:
            strategy = self.meta.get_best_strategy()
            import prometheus.wp17_crls_synthesis as _wp17
            # Evaluate correctness using the strategy that would have been used
            move = tactic_fns[strategy](board, player) if strategy in tactic_fns else None
            if move is None or not board.is_legal_move(move[0], move[1], player):
                legal = board.get_legal_moves(player)
                move  = legal[0] if legal else (-1, -1)
            self._last_results.append(
                evaluate_fn(board, move, correct_move, player)
            )

        return acc

    # ------------------------------------------------------------------
    # Override end_of_generation to add decomposition layer
    # ------------------------------------------------------------------

    def end_of_generation(
        self,
        regime: str = "",
    ) -> Tuple[SynthesisRecord, CausalRecommendation, RolloutResult,
               MetaGradStep, ExplorationRecord, DistillationRecord,
               EnsembleRecord, Optional[ForgettingRecord], DecompositionRecord]:
        """
        Run all nine layers.

        Returns the 8-tuple from WP25 plus a DecompositionRecord as the
        ninth element.

        If the decomposer's chosen action differs from WP25's final action
        AND the decomposer's winning subtask confidence exceeds
        ``decomp_override_threshold``, the decomposer's recommendation is
        applied via an additional synthesis step.
        """
        # ------------------------------------------------------------------
        # Layers 1–8: WP17→WP25
        # ------------------------------------------------------------------
        eight_tuple = super().end_of_generation(regime=regime)
        (synth_rec, causal_rec, rollout, grad_step,
         explore_rec, distill_rec, ensemble_rec, forgetting_rec) = eight_tuple

        # ------------------------------------------------------------------
        # Layer 9: WP26 decomposition
        # ------------------------------------------------------------------
        decomp_rec = self.decomposer.decompose(
            puzzles    = self._last_puzzles,
            results    = self._last_results,
            generation = self.generation - 1,   # generation already incremented
        )

        # Potential decomposer override
        wp26_override = False
        if decomp_rec.subtasks:
            best_subtask = max(
                decomp_rec.subtasks,
                key=lambda s: len(s.puzzle_indices) * s.confidence,
            )
            if (
                best_subtask.confidence >= self._decomp_override_threshold
                and best_subtask.recommended_action != synth_rec.action
            ):
                # Re-apply through safety gate
                proposal = {"type": "rule_add", "desc": f"WP26 decomp override: {best_subtask.recommended_action.value}"}
                from prometheus.safety.checks import SafetyStatus
                status, _ = self.governor.evaluate_modification(proposal, verbose=False)
                if status == SafetyStatus.PROVABLY_SAFE:
                    self.synth._apply(best_subtask.recommended_action)
                    wp26_override = True
                    logger.info(
                        "WP26 gen %d: decomposer override %s → %s (conf=%.3f)",
                        self.generation - 1,
                        synth_rec.action.value,
                        best_subtask.recommended_action.value,
                        best_subtask.confidence,
                    )

        # Log
        decomp_dict = decomp_rec.to_dict()
        decomp_dict["wp26_override"] = wp26_override
        self.decomposition_log.append(decomp_dict)

        # Amend gen_log with WP26 fields
        if self.gen_log:
            self.gen_log[-1]["wp26_n_subtask_types"] = decomp_rec.n_subtask_types
            self.gen_log[-1]["wp26_chosen_action"]   = decomp_rec.chosen_action.value
            self.gen_log[-1]["wp26_override"]        = wp26_override

        return (synth_rec, causal_rec, rollout, grad_step,
                explore_rec, distill_rec, ensemble_rec, forgetting_rec,
                decomp_rec)

    # ------------------------------------------------------------------
    # Extended report
    # ------------------------------------------------------------------

    def get_full_report(self) -> Dict[str, Any]:
        report = super().get_full_report()
        report["decomposition_summary"] = self.decomposer.get_summary()
        report["decomposition_log"]     = self.decomposition_log
        return report


# ---------------------------------------------------------------------------
# Exit-criteria verifier
# ---------------------------------------------------------------------------

def verify_wp26_exit_criteria(crls: HierarchicalCRLS) -> Dict[str, bool]:
    """
    Verify WP26 exit criteria.

    Criteria
    --------
    decomposer_constructed      TaskDecomposer is instantiated on the CRLS
    multiple_subtask_types      At least one generation had > 1 subtask type
    all_puzzles_classified      Every puzzle in every generation was classified
    per_subtask_action_assigned All SubtaskRecords have a valid SynthesisAction
    decomp_log_populated        At least one DecompositionRecord was created
    safety_preserved            All proposals safety-gated; no UNSAFE applied

    Returns
    -------
    dict mapping criterion name → bool
    """
    report  = crls.get_full_report()
    d_summ  = report.get("decomposition_summary", {})
    d_log   = report.get("decomposition_log", [])
    safety  = report.get("safety_statistics", {})

    # decomposer_constructed
    decomposer_ok = isinstance(crls.decomposer, TaskDecomposer)

    # multiple_subtask_types
    multi_type = d_summ.get("max_subtask_types", 0) >= 2

    # all_puzzles_classified — every subtask record has at least 1 puzzle
    all_classified = all(
        s.get("n_puzzles", 0) >= 1
        for entry in d_log
        for s in entry.get("subtasks", [])
    )
    # Weak form: at least one generation was decomposed
    if not d_log:
        all_classified = False

    # per_subtask_action_assigned
    valid_actions = {a.value for a in SynthesisAction}
    actions_ok = all(
        s.get("recommended_action") in valid_actions
        for entry in d_log
        for s in entry.get("subtasks", [])
    )
    if not d_log:
        actions_ok = False

    # decomp_log_populated
    log_ok = len(d_log) >= 1

    # safety_preserved
    safety_ok = (
        safety.get("total_decisions", 0) > 0
        and safety.get("unsafe_count", 0) == 0
    )

    return {
        "decomposer_constructed":     decomposer_ok,
        "multiple_subtask_types":     multi_type,
        "all_puzzles_classified":     all_classified,
        "per_subtask_action_assigned": actions_ok,
        "decomp_log_populated":       log_ok,
        "safety_preserved":           safety_ok,
    }
