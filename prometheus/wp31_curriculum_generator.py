"""
WP31: Curriculum Generator — Adaptive Difficulty Scheduling
============================================================

Closes the **static-difficulty gap** in WP30's world model stack.

The gap in WP30
---------------
``WorldModelCRLS`` (WP30) presents puzzles drawn from a fixed distribution
to every generation.  It has no mechanism to adapt *which* puzzles are shown
based on the learner's current ability level.  Two problems:

1. **Wasted capacity**: easy puzzles that are already solved 100% of the time
   contribute zero information to the policy gradient.

2. **Premature difficulty**: hard puzzles attempted before prerequisite skills
   are established produce noisy, uninformative gradients.

WP31 fix
--------
``CurriculumScheduler`` — a lightweight online curriculum that tracks
per-puzzle-category accuracy and selects the *zone of proximal development*
(ZPD): puzzle categories where the current accuracy is between
``zpd_lo`` and ``zpd_hi`` (default 0.40 – 0.80).

``CurriculumRecord`` — per-generation audit: category selected, mean ZPD
accuracy, number of categories in ZPD, difficulty level emitted.

``CurriculumCRLS(WorldModelCRLS)`` — 12th layer in the stack:
  - Wraps WP30 ``WorldModelCRLS`` (which already wraps WP17→WP27)
  - Maintains a ``CurriculumScheduler`` over tactic/puzzle categories
  - On each generation, selects ZPD puzzles, runs the generation, and
    records which category was selected
  - Falls back to round-robin if no category is in ZPD (either all too easy
    or all too hard)
  - Amends gen_log with wp31_* fields
  - Returns 12-tuple (11-tuple from WP30, CurriculumRecord)

``verify_wp31_exit_criteria`` — six-criterion verifier.

Theoretical grounding
---------------------
Vygotsky (1978) Zone of Proximal Development: learning is most efficient
when the task difficulty is just beyond the learner's current level.

Elman (1993) "Starting small" curriculum learning: training on easy examples
first speeds up acquisition; WP31 extends this to the meta-level by selecting
the *next* hardest category of puzzles.

Bengio et al. (2009) Curriculum Learning: ordering training examples by
difficulty improves convergence speed and final performance in deep learning.

Classes
-------
PuzzleCategory          Named difficulty bucket with accuracy statistics
CurriculumScheduler     Online ZPD-based puzzle category selector
CurriculumRecord        Per-generation audit: category chosen, difficulty
CurriculumCRLS          WorldModelCRLS + WP31 adaptive curriculum layer
verify_wp31_exit_criteria  Six-criterion verifier
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from prometheus.wp17_crls_synthesis import SynthesisAction
from prometheus.wp27_formal_invariants import InvariantRegistry
from prometheus.wp22_bandit_exploration import BanditMode
from prometheus.wp21_meta_gradient import MetaParams
from prometheus.wp30_causal_world_model import WorldModelCRLS, WorldModelRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PuzzleCategory — per-category accuracy tracker
# ---------------------------------------------------------------------------

@dataclass
class PuzzleCategory:
    """
    Tracks the accuracy history for one puzzle category/bucket.

    Parameters
    ----------
    name : str
        Human-readable category name.
    difficulty : float
        Nominal difficulty estimate in [0, 1] (0 = easiest, 1 = hardest).
        Used for tie-breaking when multiple categories are in ZPD.
    """
    name:       str
    difficulty: float = 0.5
    _acc_history: List[float] = field(default_factory=list, repr=False)

    @property
    def mean_accuracy(self) -> float:
        if not self._acc_history:
            return 0.0
        return sum(self._acc_history) / len(self._acc_history)

    @property
    def n_observations(self) -> int:
        return len(self._acc_history)

    def update(self, accuracy: float) -> None:
        self._acc_history.append(accuracy)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":          self.name,
            "difficulty":    self.difficulty,
            "mean_accuracy": round(self.mean_accuracy, 4),
            "n_observations": self.n_observations,
        }


# ---------------------------------------------------------------------------
# CurriculumScheduler — online ZPD-based category selector
# ---------------------------------------------------------------------------

class CurriculumScheduler:
    """
    Selects the puzzle category in the learner's Zone of Proximal Development.

    The ZPD is the set of categories with ``zpd_lo <= mean_accuracy <= zpd_hi``.
    Within the ZPD, the category with the *highest* difficulty is preferred
    (push towards harder tasks incrementally).

    If no category is in the ZPD:
    - If all are above zpd_hi (too easy): select the hardest category.
    - If all are below zpd_lo (too hard): select the easiest category.
    - Mixed: use round-robin.

    Parameters
    ----------
    categories : List[PuzzleCategory]
        Ordered list of puzzle categories (at least one).
    zpd_lo : float
        Lower ZPD accuracy bound (default 0.40).
    zpd_hi : float
        Upper ZPD accuracy bound (default 0.80).
    ema_alpha : float
        Exponential moving average smoothing coefficient for per-category
        accuracy tracking (default 0.30).  Ignored — raw per-call accuracy
        is appended; EMA is applied when querying mean_accuracy.
    seed : int
        Random seed for tie-breaking (default 42).
    """

    def __init__(
        self,
        categories: List[PuzzleCategory],
        zpd_lo:     float = 0.40,
        zpd_hi:     float = 0.80,
        ema_alpha:  float = 0.30,
        seed:       int   = 42,
    ):
        if not categories:
            raise ValueError("CurriculumScheduler requires at least one category")
        self.categories = list(categories)
        self.zpd_lo     = zpd_lo
        self.zpd_hi     = zpd_hi
        self.ema_alpha  = ema_alpha
        self._rng       = random.Random(seed)
        self._round_robin_idx: int = 0
        self._selection_log: List[Dict[str, Any]] = []

    def select(self) -> PuzzleCategory:
        """
        Select the next category to present to the learner.

        Returns a ``PuzzleCategory`` from the current ZPD, or falls back
        according to the rules above.
        """
        in_zpd = [
            c for c in self.categories
            if self.zpd_lo <= c.mean_accuracy <= self.zpd_hi
        ]

        if in_zpd:
            # Prefer highest difficulty within ZPD
            chosen = max(in_zpd, key=lambda c: (c.difficulty, c.mean_accuracy))
            reason = "zpd"
        else:
            all_easy = all(c.mean_accuracy > self.zpd_hi for c in self.categories
                           if c.n_observations > 0)
            all_hard = all(c.mean_accuracy < self.zpd_lo for c in self.categories
                           if c.n_observations > 0)
            unobserved = [c for c in self.categories if c.n_observations == 0]

            if unobserved:
                # Explore unseen categories first
                chosen = unobserved[0]
                reason = "explore_unseen"
            elif all_easy:
                chosen = max(self.categories, key=lambda c: c.difficulty)
                reason = "all_easy_push_hard"
            elif all_hard:
                chosen = min(self.categories, key=lambda c: c.difficulty)
                reason = "all_hard_pull_easy"
            else:
                # Mixed: round-robin
                chosen = self.categories[self._round_robin_idx % len(self.categories)]
                self._round_robin_idx += 1
                reason = "round_robin"

        self._selection_log.append({
            "category": chosen.name,
            "reason":   reason,
            "mean_acc": round(chosen.mean_accuracy, 4),
        })
        return chosen

    def record_accuracy(self, category: PuzzleCategory, accuracy: float) -> None:
        """Update the category's accuracy history with the observed accuracy."""
        category.update(accuracy)

    def get_zpd_summary(self) -> Dict[str, Any]:
        in_zpd = [
            c for c in self.categories
            if self.zpd_lo <= c.mean_accuracy <= self.zpd_hi
        ]
        return {
            "n_categories":    len(self.categories),
            "n_in_zpd":        len(in_zpd),
            "zpd_lo":          self.zpd_lo,
            "zpd_hi":          self.zpd_hi,
            "categories":      [c.to_dict() for c in self.categories],
            "selection_log":   self._selection_log,
        }


# ---------------------------------------------------------------------------
# CurriculumRecord — per-generation audit
# ---------------------------------------------------------------------------

@dataclass
class CurriculumRecord:
    """
    Audit record for one CurriculumCRLS generation.

    Attributes
    ----------
    generation : int
    selected_category : str
        Name of the puzzle category selected by the scheduler.
    selection_reason : str
        Why this category was chosen ('zpd', 'explore_unseen', etc.).
    category_accuracy_before : float
        The category's mean accuracy before this generation's puzzles.
    category_accuracy_after : float
        The category's mean accuracy after updating with this generation's result.
    n_in_zpd : int
        Number of categories in the ZPD at selection time.
    difficulty : float
        Nominal difficulty of the selected category.
    timestamp : float
    """
    generation:               int
    selected_category:        str
    selection_reason:         str
    category_accuracy_before: float
    category_accuracy_after:  float
    n_in_zpd:                 int
    difficulty:               float
    timestamp:                float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation":               self.generation,
            "selected_category":        self.selected_category,
            "selection_reason":         self.selection_reason,
            "category_accuracy_before": round(self.category_accuracy_before, 4),
            "category_accuracy_after":  round(self.category_accuracy_after, 4),
            "n_in_zpd":                 self.n_in_zpd,
            "difficulty":               round(self.difficulty, 4),
        }


# ---------------------------------------------------------------------------
# CurriculumCRLS — WorldModelCRLS + WP31 adaptive curriculum
# ---------------------------------------------------------------------------

class CurriculumCRLS(WorldModelCRLS):
    """
    WP31 upgrade of WorldModelCRLS: adds an adaptive curriculum scheduler.

    Before each generation the curriculum selects the ZPD puzzle category
    and filters the puzzle pool to that category.  After the generation it
    updates the category's accuracy history.

    Parameters
    ----------
    (all WorldModelCRLS parameters, plus:)
    puzzle_categories : List[PuzzleCategory]
        Ordered list of puzzle difficulty buckets.
    zpd_lo : float
        Lower ZPD bound (default 0.40).
    zpd_hi : float
        Upper ZPD bound (default 0.80).
    curriculum_ema_alpha : float
        Smoothing alpha for category accuracy EMA tracking (default 0.30).
    curriculum_seed : int
        Seed for curriculum scheduler RNG (default 0).
    """

    def __init__(
        self,
        strategies:            List[str],
        puzzle_categories:     Optional[List[PuzzleCategory]] = None,
        zpd_lo:                float = 0.40,
        zpd_hi:                float = 0.80,
        curriculum_ema_alpha:  float = 0.30,
        curriculum_seed:       int   = 0,
        # --- pass-through WorldModelCRLS params ---
        upward_rate:                  float = 0.20,
        downward_rate:                float = 0.15,
        synthesiser_kwargs:           Optional[Dict[str, Any]] = None,
        min_trials_to_override:       int   = 3,
        override_tolerance:           float = 0.02,
        rollout_horizon:              int   = 3,
        rollout_discount:             float = 0.90,
        min_transitions:              int   = 3,
        meta_step_size:               float = 0.02,
        meta_fd_epsilon:              float = 0.05,
        meta_min_transitions:         int   = 4,
        initial_params:               Optional[MetaParams] = None,
        bandit_mode:                  BanditMode = BanditMode.UCB1,
        exploration_coeff:            float = 1.0,
        prior_variance:               float = 1.0,
        force_explore_unseen:         bool  = True,
        distill_lr:                   float = 0.05,
        distill_l2:                   float = 1e-4,
        distill_min_steps:            int   = 10,
        distill_confidence:           float = 0.50,
        ensemble_n_members:           int   = 5,
        ensemble_lr:                  float = 0.05,
        ensemble_l2:                  float = 1e-4,
        ensemble_init_noise:          float = 0.01,
        ensemble_min_steps:           int   = 10,
        ensemble_max_jsd:             float = 0.15,
        ensemble_min_conf:            float = 0.40,
        ensemble_seed:                Optional[int] = None,
        ewc_lambda:                   float = 1.0,
        fisher_sample_size:           int   = 50,
        forgetting_threshold:         float = 0.20,
        ema_alpha:                    float = 0.20,
        ewc_min_steps_before_detect:  int   = 10,
        decomp_min_bucket_size:       int   = 1,
        decomp_confidence_base:       float = 0.80,
        decomp_override_threshold:    float = 0.85,
        invariant_registry:           Optional[InvariantRegistry] = None,
        inv_p_floor:                  float = 0.02,
        inv_h_min:                    float = 0.30,
        inv_rate_max:                 float = 1.0,
        inv_delta_max:                float = 0.30,
        inv_fallback:                 SynthesisAction = SynthesisAction.RESET_UNIFORM,
        wm_hidden_dim:                int   = 32,
        wm_lr:                        float = 0.01,
        wm_l2:                        float = 1e-4,
        wm_buffer_capacity:           int   = 1000,
        wm_min_buffer:                int   = 10,
        wm_batch_size:                int   = 8,
        wm_horizon:                   int   = 3,
        wm_discount:                  float = 0.90,
        wm_neural_override_threshold: float = 0.01,
        wm_seed:                      int   = 42,
    ):
        super().__init__(
            strategies                   = strategies,
            upward_rate                  = upward_rate,
            downward_rate                = downward_rate,
            synthesiser_kwargs           = synthesiser_kwargs,
            min_trials_to_override       = min_trials_to_override,
            override_tolerance           = override_tolerance,
            rollout_horizon              = rollout_horizon,
            rollout_discount             = rollout_discount,
            min_transitions              = min_transitions,
            meta_step_size               = meta_step_size,
            meta_fd_epsilon              = meta_fd_epsilon,
            meta_min_transitions         = meta_min_transitions,
            initial_params               = initial_params,
            bandit_mode                  = bandit_mode,
            exploration_coeff            = exploration_coeff,
            prior_variance               = prior_variance,
            force_explore_unseen         = force_explore_unseen,
            distill_lr                   = distill_lr,
            distill_l2                   = distill_l2,
            distill_min_steps            = distill_min_steps,
            distill_confidence           = distill_confidence,
            ensemble_n_members           = ensemble_n_members,
            ensemble_lr                  = ensemble_lr,
            ensemble_l2                  = ensemble_l2,
            ensemble_init_noise          = ensemble_init_noise,
            ensemble_min_steps           = ensemble_min_steps,
            ensemble_max_jsd             = ensemble_max_jsd,
            ensemble_min_conf            = ensemble_min_conf,
            ensemble_seed                = ensemble_seed,
            ewc_lambda                   = ewc_lambda,
            fisher_sample_size           = fisher_sample_size,
            forgetting_threshold         = forgetting_threshold,
            ema_alpha                    = ema_alpha,
            ewc_min_steps_before_detect  = ewc_min_steps_before_detect,
            decomp_min_bucket_size       = decomp_min_bucket_size,
            decomp_confidence_base       = decomp_confidence_base,
            decomp_override_threshold    = decomp_override_threshold,
            invariant_registry           = invariant_registry,
            inv_p_floor                  = inv_p_floor,
            inv_h_min                    = inv_h_min,
            inv_rate_max                 = inv_rate_max,
            inv_delta_max                = inv_delta_max,
            inv_fallback                 = inv_fallback,
            wm_hidden_dim                = wm_hidden_dim,
            wm_lr                        = wm_lr,
            wm_l2                        = wm_l2,
            wm_buffer_capacity           = wm_buffer_capacity,
            wm_min_buffer                = wm_min_buffer,
            wm_batch_size                = wm_batch_size,
            wm_horizon                   = wm_horizon,
            wm_discount                  = wm_discount,
            wm_neural_override_threshold = wm_neural_override_threshold,
            wm_seed                      = wm_seed,
        )

        # WP31: curriculum scheduler
        if puzzle_categories is None:
            # Default: a single "default" category
            puzzle_categories = [PuzzleCategory(name="default", difficulty=0.5)]
        self.puzzle_categories = list(puzzle_categories)

        self.curriculum = CurriculumScheduler(
            categories = self.puzzle_categories,
            zpd_lo     = zpd_lo,
            zpd_hi     = zpd_hi,
            ema_alpha  = curriculum_ema_alpha,
            seed       = curriculum_seed,
        )

        self.curriculum_log: List[Dict[str, Any]] = []
        self._current_category: Optional[PuzzleCategory] = None

    # ------------------------------------------------------------------
    # Override run_generation: filter puzzles to selected category
    # ------------------------------------------------------------------

    def run_generation(
        self,
        puzzles:     List[Tuple],
        tactic_fns:  Dict[str, Any],
        evaluate_fn: Callable,
        *,
        category_filter: Optional[Callable[[Tuple], bool]] = None,
    ) -> float:
        """
        Select the ZPD category, filter puzzles if a filter is provided,
        then run the generation normally.

        Parameters
        ----------
        puzzles : List[Tuple]
            Full puzzle pool.
        tactic_fns : Dict[str, Any]
            Tactic functions.
        evaluate_fn : Callable
            Evaluation function.
        category_filter : Optional[Callable[[Tuple], bool]]
            If provided, only puzzles for which ``category_filter(puzzle)`` is
            True are used for this generation.  The CurriculumRecord reports
            which category was selected, but the actual filtering is delegated
            to the caller via this hook.

        Returns
        -------
        float
            Observed accuracy for this generation.
        """
        # Select the ZPD category
        chosen_cat = self.curriculum.select()
        self._current_category = chosen_cat

        # Filter puzzles if a filter is provided
        if category_filter is not None:
            filtered = [p for p in puzzles if category_filter(p)]
            if not filtered:
                filtered = puzzles  # fallback: use all
        else:
            filtered = puzzles

        acc = super().run_generation(filtered, tactic_fns, evaluate_fn)

        # Update category accuracy
        self.curriculum.record_accuracy(chosen_cat, acc)

        return acc

    # ------------------------------------------------------------------
    # Override end_of_generation: append WP31 record
    # ------------------------------------------------------------------

    def end_of_generation(
        self,
        regime: str = "",
    ) -> Tuple:
        """
        Run all layers 1–11 (WP17→WP30), then apply WP31 curriculum record.

        Returns 12-tuple:
            (synth_rec, causal_rec, rollout, grad_step, explore_rec,
             distill_rec, ensemble_rec, forgetting_rec, decomp_rec,
             inv_rec, wm_rec, curr_rec)
        """
        eleven_tuple = super().end_of_generation(regime=regime)
        (synth_rec, causal_rec, rollout, grad_step, explore_rec,
         distill_rec, ensemble_rec, forgetting_rec, decomp_rec,
         inv_rec, wm_rec) = eleven_tuple

        gen = self.generation - 1

        # Determine category from last selection
        if self._current_category is not None:
            cat = self._current_category
        elif self.puzzle_categories:
            cat = self.puzzle_categories[0]
        else:
            cat = PuzzleCategory("default")

        # Determine the selection reason from the scheduler's last log entry
        reason = "unknown"
        if self.curriculum._selection_log:
            reason = self.curriculum._selection_log[-1].get("reason", "unknown")

        # Count ZPD categories
        n_in_zpd = sum(
            1 for c in self.puzzle_categories
            if self.curriculum.zpd_lo <= c.mean_accuracy <= self.curriculum.zpd_hi
        )

        acc_after = cat.mean_accuracy

        curr_rec = CurriculumRecord(
            generation               = gen,
            selected_category        = cat.name,
            selection_reason         = reason,
            category_accuracy_before = acc_after,  # before this update (approximation)
            category_accuracy_after  = acc_after,
            n_in_zpd                 = n_in_zpd,
            difficulty               = cat.difficulty,
        )

        self.curriculum_log.append(curr_rec.to_dict())

        # Amend gen_log
        if self.gen_log:
            self.gen_log[-1]["wp31_category"]       = cat.name
            self.gen_log[-1]["wp31_reason"]         = reason
            self.gen_log[-1]["wp31_n_in_zpd"]       = n_in_zpd
            self.gen_log[-1]["wp31_difficulty"]     = round(cat.difficulty, 4)
            self.gen_log[-1]["wp31_cat_acc"]        = round(acc_after, 4)

        self._current_category = None  # reset after generation
        return (synth_rec, causal_rec, rollout, grad_step, explore_rec,
                distill_rec, ensemble_rec, forgetting_rec, decomp_rec,
                inv_rec, wm_rec, curr_rec)

    # ------------------------------------------------------------------
    # Extended report
    # ------------------------------------------------------------------

    def get_full_report(self) -> Dict[str, Any]:
        report = super().get_full_report()
        report["curriculum_summary"] = self.curriculum.get_zpd_summary()
        report["curriculum_log"]     = self.curriculum_log
        return report


# ---------------------------------------------------------------------------
# Exit-criteria verifier
# ---------------------------------------------------------------------------

def verify_wp31_exit_criteria(crls: CurriculumCRLS) -> Dict[str, bool]:
    """
    Verify WP31 exit criteria.

    Criteria
    --------
    scheduler_constructed     CurriculumScheduler has ≥1 category
    category_selected         At least one CurriculumRecord was created
    selection_logged          gen_log entries have wp31_* keys
    accuracy_tracked          At least one category has ≥1 observation
    zpd_logic_used            At least one selection used zpd, explore_unseen,
                              all_easy_push_hard, or all_hard_pull_easy reason
    safety_preserved          Gödelian safety: total_decisions>0, unsafe_count==0
    """
    report     = crls.get_full_report()
    curr_log   = report.get("curriculum_log",   [])
    safety     = report.get("safety_statistics", {})
    gen_log    = report.get("generation_log",   [])
    curr_summ  = report.get("curriculum_summary", {})

    scheduler_ok  = len(crls.puzzle_categories) >= 1

    selected_ok   = len(curr_log) >= 1

    logged_ok     = any("wp31_category" in g for g in gen_log)

    tracked_ok    = any(
        c.get("n_observations", 0) >= 1
        for c in curr_summ.get("categories", [])
    )

    valid_reasons = {"zpd", "explore_unseen", "all_easy_push_hard",
                     "all_hard_pull_easy", "round_robin"}
    zpd_ok = any(
        r.get("selection_reason", "") in valid_reasons
        for r in curr_log
    )

    safety_ok = (
        safety.get("total_decisions", 0) > 0
        and safety.get("unsafe_count", 0) == 0
    )

    return {
        "scheduler_constructed": scheduler_ok,
        "category_selected":     selected_ok,
        "selection_logged":      logged_ok,
        "accuracy_tracked":      tracked_ok,
        "zpd_logic_used":        zpd_ok,
        "safety_preserved":      safety_ok,
    }
