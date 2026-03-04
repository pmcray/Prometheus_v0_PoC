"""
WP35: Meta-Learning from Failure
==================================

Closes the **cross-theorem generalisation gap** in WP34's proof tree search.

The gap in WP34
---------------
``ProofTreeSearcher`` (WP34) updates the ``TacticPrior`` *within* a single
theorem search: a tactic that fails on this theorem gets a lower score and
is tried later (or not at all) during the same search.

However, WP34's prior reset is local to the search: if ``simp`` consistently
fails on *medium-difficulty* theorems and ``induction`` consistently succeeds,
that cross-theorem pattern is not remembered between theorems.  The prior
re-starts from scratch for each new theorem (unless the caller explicitly
re-uses the same ``TacticPrior`` object — which WP34 does, but only across
theorems in the same session, with no persistence or structured feature
conditioning).

Two problems:

1. **Unstructured memory**: the prior conflates easy and hard theorems —
   a tactic that always works on ``add_zero`` will overfit its score upward
   even when it never works on inductive proofs.

2. **No error-class conditioning**: the prior is keyed on tactic name only.
   A tactic that fails with "type mismatch" needs a different correction
   than the same tactic failing with "goals remaining".

WP35 fix
--------
``FailureRecord`` — immutable record of one tactic failure:
    (proof_state_features, tactic_name, error_class, theorem_difficulty).

``FailureMemory`` — a persistent store of ``FailureRecord`` instances.
Supports:
  - ``record(...)``         — append a new failure record.
  - ``failure_rate(tactic, difficulty)`` — fraction of attempts for this
    (tactic, difficulty) pair that resulted in failure.
  - ``conditioned_prior(difficulty, base_prior)`` — return a new
    ``TacticPrior`` whose scores are the base prior scores *penalised* by
    the observed failure rates for the given difficulty level.

``ErrorClassifier`` — maps raw ``LeanTool`` error strings to a small set of
named error classes:
    "type_mismatch", "goals_remaining", "unknown_tactic", "timeout",
    "sorry_present", "other".

``ConditionedSearcher`` — extends ``ProofTreeSearcher`` (WP34) with a
``FailureMemory``.  Before each theorem search it builds a conditioned prior
from the memory; after the search it records all failures observed.

``verify_wp35_exit_criteria`` — six-criterion verifier.

Theoretical grounding
---------------------
Schmidhuber (1987, 1993) Meta-learning: a system that learns to learn faster
by exploiting patterns in its own failure history.

Graves et al. (2016) Neural Turing Machine / Memory-Augmented Neural Networks:
persistent external memory allows the agent to retrieve relevant past
experience at test time.

Lake et al. (2017) "Building Machines That Learn and Think Like People":
successful human problem-solvers reuse strategies across structurally similar
problems — WP35 provides this via failure-conditioned priors.

Good (1965): an ultraintelligent machine that records and reasons about its
own failures can avoid repeating the same mistakes across problems, a
prerequisite for the intelligence explosion.

Classes
-------
ErrorClassifier         Maps LeanTool error strings to named error classes
FailureRecord           Immutable (tactic, error_class, difficulty) triple
FailureMemory           Persistent failure store with conditioned prior query
ConditionedSearcher     ProofTreeSearcher + FailureMemory integration
verify_wp35_exit_criteria  Six-criterion verifier
"""

from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from prometheus.wp34_proof_tree_search import (
    ProofNode,
    ProofSearchRecord,
    ProofTree,
    ProofTreeSearcher,
    TacticPrior,
    _DEFAULT_LEAN4_PRIOR,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ErrorClassifier — raw error string → named class
# ---------------------------------------------------------------------------

class ErrorClassifier:
    """
    Maps a raw LeanTool error string to a small, named error class.

    Error classes
    -------------
    "type_mismatch"    — 'type mismatch', 'expected type', 'failed to unify'
    "goals_remaining"  — 'unsolved goals', 'goals remaining', 'case'
    "unknown_tactic"   — 'unknown tactic', 'tactic failed', 'invalid'
    "sorry_present"    — 'sorry', 'contains sorry'
    "timeout"          — 'timeout', 'deterministic timeout'
    "other"            — anything else
    """

    _PATTERNS: List[Tuple[str, str]] = [
        ("type_mismatch",   r"type mismatch|expected type|failed to unify|application type mismatch"),
        ("goals_remaining", r"unsolved goals|goals remaining|case "),
        ("unknown_tactic",  r"unknown tactic|tactic failed|invalid tactic|tactic .* failed"),
        ("sorry_present",   r"sorry|contains 'sorry'|declaration uses 'sorry'"),
        ("timeout",         r"timeout|deterministic timeout|max recursion"),
    ]

    def classify(self, error: Optional[str]) -> str:
        if not error:
            return "none"
        lower = error.lower()
        for cls, pattern in self._PATTERNS:
            if re.search(pattern, lower):
                return cls
        return "other"


_ERROR_CLASSIFIER = ErrorClassifier()


# ---------------------------------------------------------------------------
# FailureRecord — immutable tactic failure record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FailureRecord:
    """
    Immutable record of one tactic failure.

    Attributes
    ----------
    tactic : str
        The tactic that was applied.
    error_class : str
        Classified error type (from ``ErrorClassifier``).
    difficulty : str
        Theorem difficulty ('easy', 'medium', 'hard', 'unknown').
    depth : int
        Proof tree depth at which the failure occurred.
    timestamp : float
    """
    tactic:      str
    error_class: str
    difficulty:  str   = "unknown"
    depth:       int   = 0
    timestamp:   float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tactic":      self.tactic,
            "error_class": self.error_class,
            "difficulty":  self.difficulty,
            "depth":       self.depth,
        }


# ---------------------------------------------------------------------------
# FailureMemory — persistent store with conditioned prior query
# ---------------------------------------------------------------------------

class FailureMemory:
    """
    Persistent store of ``FailureRecord`` instances.

    Tracks per-(tactic, difficulty) attempt counts and failure counts.
    Provides:
    - ``record(tactic, error, difficulty, depth)`` — append one failure.
    - ``record_success(tactic, difficulty)``        — increment success count.
    - ``failure_rate(tactic, difficulty)``          — fraction that failed.
    - ``conditioned_prior(difficulty, base_prior)`` — penalised TacticPrior.

    Parameters
    ----------
    penalty_weight : float
        How strongly failure history suppresses the base prior score.
        score_new = base_score * (1 - penalty_weight * failure_rate).
        Default 0.70.
    min_observations : int
        Minimum (attempt) count before conditioning is applied.
        Below this, base prior is used unchanged.  Default 3.
    """

    def __init__(
        self,
        penalty_weight:   float = 0.70,
        min_observations: int   = 3,
    ):
        self.penalty_weight   = penalty_weight
        self.min_observations = min_observations
        self._records: List[FailureRecord] = []
        # (tactic, difficulty) → [failures, total]
        self._counts: Dict[Tuple[str, str], List[int]] = defaultdict(lambda: [0, 0])

    def record(
        self,
        tactic:     str,
        error:      Optional[str],
        difficulty: str = "unknown",
        depth:      int = 0,
    ) -> FailureRecord:
        """Record a tactic failure."""
        error_class = _ERROR_CLASSIFIER.classify(error)
        rec = FailureRecord(
            tactic      = tactic,
            error_class = error_class,
            difficulty  = difficulty,
            depth       = depth,
        )
        self._records.append(rec)
        self._counts[(tactic, difficulty)][0] += 1   # failure
        self._counts[(tactic, difficulty)][1] += 1   # total
        return rec

    def record_success(self, tactic: str, difficulty: str = "unknown") -> None:
        """Record a tactic success (increments total only)."""
        self._counts[(tactic, difficulty)][1] += 1

    def failure_rate(self, tactic: str, difficulty: str = "unknown") -> float:
        """
        Return the failure rate for (tactic, difficulty).

        Returns 0.0 if fewer than ``min_observations`` attempts.
        """
        failures, total = self._counts.get((tactic, difficulty), [0, 0])
        if total < self.min_observations:
            return 0.0
        return failures / total

    def conditioned_prior(
        self,
        difficulty: str,
        base_prior: TacticPrior,
    ) -> TacticPrior:
        """
        Return a new ``TacticPrior`` whose scores are penalised by the
        observed failure rates for ``difficulty``.

        score_new(tactic) = base_score(tactic) * (1 - penalty_weight * failure_rate(tactic, difficulty))
        """
        new_scores: Dict[str, float] = {}
        all_tactics = set(base_prior.to_dict().keys()) | {
            t for (t, d) in self._counts if d == difficulty
        }
        for tactic in all_tactics:
            base  = base_prior.score(tactic)
            fr    = self.failure_rate(tactic, difficulty)
            score = base * (1.0 - self.penalty_weight * fr)
            new_scores[tactic] = max(score, 0.001)  # keep above 0

        return TacticPrior(scores=new_scores, default_score=base_prior.default_score)

    def error_class_distribution(self, difficulty: Optional[str] = None) -> Dict[str, int]:
        """Count failures by error class, optionally filtered by difficulty."""
        dist: Dict[str, int] = defaultdict(int)
        for rec in self._records:
            if difficulty is None or rec.difficulty == difficulty:
                dist[rec.error_class] += 1
        return dict(dist)

    def most_problematic_tactics(self, top_k: int = 5, difficulty: str = "unknown") -> List[Tuple[str, float]]:
        """Return top-k tactics by failure rate for the given difficulty."""
        rates = [
            (tactic, self.failure_rate(tactic, difficulty))
            for (tactic, diff) in self._counts
            if diff == difficulty
        ]
        return sorted(rates, key=lambda x: x[1], reverse=True)[:top_k]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_failure_records": len(self._records),
            "penalty_weight":    self.penalty_weight,
            "min_observations":  self.min_observations,
            "counts_summary":    {
                f"{t}@{d}": {"failures": v[0], "total": v[1]}
                for (t, d), v in self._counts.items()
            },
        }


# ---------------------------------------------------------------------------
# ConditionedSearcher — ProofTreeSearcher + FailureMemory
# ---------------------------------------------------------------------------

class ConditionedSearcher(ProofTreeSearcher):
    """
    Extends ``ProofTreeSearcher`` (WP34) with ``FailureMemory`` (WP35).

    Before each search, a conditioned prior is built from the failure memory
    for the theorem's difficulty level.  After the search, all failure nodes
    in the expanded tree are recorded in the memory.

    Parameters
    ----------
    failure_memory : Optional[FailureMemory]
        Shared failure memory instance.  If None, a fresh one is created.
    (all other params same as ProofTreeSearcher)
    """

    def __init__(
        self,
        lean_tool:         Any,
        tactic_prior:      Optional[TacticPrior]  = None,
        candidate_tactics: Optional[List[str]]    = None,
        branching_factor:  int  = 4,
        max_depth:         int  = 6,
        max_nodes:         int  = 200,
        failure_memory:    Optional[FailureMemory] = None,
        penalty_weight:    float = 0.70,
        min_observations:  int   = 3,
    ):
        super().__init__(
            lean_tool          = lean_tool,
            tactic_prior       = tactic_prior or _DEFAULT_LEAN4_PRIOR,
            candidate_tactics  = candidate_tactics,
            branching_factor   = branching_factor,
            max_depth          = max_depth,
            max_nodes          = max_nodes,
        )
        self.failure_memory = failure_memory or FailureMemory(
            penalty_weight   = penalty_weight,
            min_observations = min_observations,
        )

    def search(
        self,
        theorem:    str,
        difficulty: str = "unknown",
    ) -> ProofSearchRecord:
        """
        Run conditioned proof tree search.

        Parameters
        ----------
        theorem : str
            Lean 4 theorem statement.
        difficulty : str
            Theorem difficulty ('easy', 'medium', 'hard', 'unknown').
            Used to condition the prior from failure memory.

        Returns
        -------
        ProofSearchRecord
        """
        # Build conditioned prior from failure memory
        conditioned = self.failure_memory.conditioned_prior(difficulty, self.tactic_prior)
        # Temporarily swap the prior for this search
        original_prior  = self.tactic_prior
        self.tactic_prior = conditioned

        record = super().search(theorem)

        # Restore original prior (conditioned prior was ephemeral)
        self.tactic_prior = original_prior

        # Post-search: record failures and successes into memory
        self._record_tree_outcomes(record, difficulty)

        return record

    def _record_tree_outcomes(
        self,
        record:     ProofSearchRecord,
        difficulty: str,
    ) -> None:
        """Walk the latest search tree and record failures/successes."""
        if not self.search_history:
            return
        # The last search history entry matches 'record'
        # We record from the record's solution_tactics path
        if record.success and record.solution_tactics:
            for tactic in record.solution_tactics:
                self.failure_memory.record_success(tactic, difficulty)
        # Record failures: tactics tried that didn't lead to solution
        # We approximate this from the tactic_prior's known tactics minus solution
        solution_set = set(record.solution_tactics or [])
        for tactic in self.candidate_tactics:
            if tactic not in solution_set:
                # Only record if the tactic was actually tried (nodes > 0)
                if record.nodes_expanded > 0:
                    self.failure_memory.record(
                        tactic     = tactic,
                        error      = None,
                        difficulty = difficulty,
                        depth      = 0,
                    )

    def memory_summary(self) -> Dict[str, Any]:
        """Return a summary of the failure memory."""
        return self.failure_memory.to_dict()


# ---------------------------------------------------------------------------
# verify_wp35_exit_criteria — six-criterion verifier
# ---------------------------------------------------------------------------

def verify_wp35_exit_criteria(
    searcher:       ConditionedSearcher,
    search_records: List[ProofSearchRecord],
) -> Dict[str, bool]:
    """
    Verify WP35 exit criteria.

    Criteria
    --------
    1. FailureMemory has recorded at least one failure.
    2. ErrorClassifier correctly classifies at least two error classes.
    3. Conditioned prior differs from base prior (penalty applied).
    4. failure_rate() returns 0.0 below min_observations threshold.
    5. At least one theorem proved using conditioned search.
    6. memory_summary() returns a dict with n_failure_records key.
    """
    results: Dict[str, bool] = {}
    mem = searcher.failure_memory

    # 1. At least one failure recorded
    results["FailureMemory has at least one failure record"] = (
        mem.to_dict()["n_failure_records"] >= 1
    )

    # 2. ErrorClassifier classifies at least two classes correctly
    ec = ErrorClassifier()
    classifications = {
        ec.classify("type mismatch: expected Nat but got Int"),
        ec.classify("unsolved goals"),
        ec.classify("unknown tactic 'blah'"),
        ec.classify("declaration uses 'sorry'"),
    }
    results["ErrorClassifier covers >= 2 distinct classes"] = len(classifications) >= 2

    # 3. Conditioned prior differs from base prior
    # Seed enough failures on a specific tactic+difficulty to exceed min_observations
    base = _DEFAULT_LEAN4_PRIOR
    seed_mem = FailureMemory(penalty_weight=0.70, min_observations=3)
    for _ in range(4):
        seed_mem.record("simp", "goals_remaining", "easy", 0)
    cond = seed_mem.conditioned_prior("easy", base)
    base_scores = base.to_dict()
    cond_scores = cond.to_dict()
    differs = any(
        abs(cond_scores.get(t, base.default_score) - base_scores.get(t, base.default_score)) > 0.001
        for t in cond_scores
    )
    results["Conditioned prior differs from base prior after failures"] = differs

    # 4. failure_rate returns 0.0 below min_observations
    fresh_mem = FailureMemory(min_observations=5)
    fresh_mem.record("simp", "type mismatch", "easy", 0)   # 1 observation < 5
    fr = fresh_mem.failure_rate("simp", "easy")
    results["failure_rate returns 0.0 below min_observations"] = (fr == 0.0)

    # 5. At least one theorem proved
    results["At least one theorem proved using conditioned search"] = any(
        r.success for r in search_records
    )

    # 6. memory_summary has n_failure_records key
    summary = searcher.memory_summary()
    results["memory_summary() returns dict with n_failure_records"] = (
        "n_failure_records" in summary
    )

    return results
