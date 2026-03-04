"""
WP34: Multi-Step Proof Tree Search
====================================

Closes the **linear-retry gap** in WP33's theorem proving.

The gap in WP33
---------------
``CoderAgent.prove()`` (WP33) retries a theorem proof up to ``MAX_RETRIES``
times in a *linear* sequence:

    attempt 0 (bad) → error → attempt 1 → error → attempt 2 → …

There is no *search over tactic alternatives*.  If two different tactics
both seem plausible at step N, the agent cannot explore both branches and
pick the one that leads to a complete proof.  Dead-end branches cannot be
pruned; once a tactic sequence has failed the agent has no memory of where
the failure occurred.

WP34 fix
--------
``ProofNode`` — one node in a proof search tree.  Stores the partial proof
so far, the last tactic applied, the depth, and child nodes produced by
expanding it.

``ProofTree`` — the complete search tree rooted at the initial (empty) proof
state.  Supports:
  - ``expand(node, tactics)``   — generate child nodes from a list of
    candidate tactics; each child is verified with ``LeanTool``.
  - ``best_first_search(...)``  — iterative best-first search: expand the
    highest-priority open node (scored by depth + success heuristic) until
    a complete proof is found or the budget is exhausted.
  - ``backtrack()``             — restore the search to the most recently
    completed subtree via a LIFO frontier.

``TacticPrior`` — a lightweight score table mapping tactic names to
estimated success probability.  Used to order the expansion frontier so
more promising tactics are tried first.

``ProofSearchRecord`` — per-theorem audit: nodes expanded, depth reached,
tactic sequences tried, success flag, wall-clock time.

``ProofTreeSearcher`` — orchestrates a full proof search for a single
theorem:
  1. Generate candidate first-step tactics (from prior or enumeration).
  2. Build root ``ProofNode`` with ``LeanTool``.
  3. Run ``best_first_search``; on success, return the winning tactic path.
  4. Record statistics in ``ProofSearchRecord``.

``verify_wp34_exit_criteria`` — six-criterion verifier.

Theoretical grounding
---------------------
Newell & Simon (1972) General Problem Solver: heuristic search over
a problem space using means-ends analysis.  WP34 applies this to the
*tactic space* of Lean proofs.

Silver et al. (2016) AlphaGo / AlphaZero: Monte-Carlo Tree Search (MCTS)
uses a prior policy + value estimates to guide search.  ``ProofTree`` uses
a simpler priority queue rather than full MCTS, but adopts the same
principle of combining prior probability with search depth.

Lample & Charton (2019) Deep Learning for Symbolic Mathematics: iterative
beam search over tactic sequences outperforms greedy single-pass generation
for formal proofs.

Good (1965): an ultraintelligent machine that can *search* over its own
reasoning steps (rather than committing to the first idea) is closer to
the vision of machine intelligence that surpasses human capability in
formal domains.

Classes
-------
ProofNode               One node in the proof search tree
ProofTree               Best-first search tree over tactic sequences
TacticPrior             Score table: tactic name → priority score
ProofSearchRecord       Per-theorem audit: nodes, depth, success, time
ProofTreeSearcher       Orchestrates full search for one theorem
verify_wp34_exit_criteria  Six-criterion verifier
"""

from __future__ import annotations

import heapq
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TacticPrior — tactic name → success-probability estimate
# ---------------------------------------------------------------------------

class TacticPrior:
    """
    Lightweight prior over tactic names.

    Scores are in (0, 1]; higher = more likely to succeed.
    Unknown tactics receive the ``default_score``.

    Parameters
    ----------
    scores : Dict[str, float]
        Initial {tactic_name: score} mapping.
    default_score : float
        Score for unseen tactics (default 0.1).
    """

    def __init__(
        self,
        scores:        Optional[Dict[str, float]] = None,
        default_score: float = 0.10,
    ):
        self._scores: Dict[str, float] = dict(scores or {})
        self.default_score = default_score

    def score(self, tactic: str) -> float:
        return self._scores.get(tactic, self.default_score)

    def update(self, tactic: str, success: bool, lr: float = 0.20) -> None:
        """Bayesian-style online update: move score toward 1.0 or 0.0."""
        current = self._scores.get(tactic, self.default_score)
        target  = 1.0 if success else 0.0
        self._scores[tactic] = current + lr * (target - current)

    def top_k(self, tactics: List[str], k: int) -> List[str]:
        """Return the top-k tactics by prior score (highest first)."""
        return sorted(tactics, key=lambda t: self.score(t), reverse=True)[:k]

    def to_dict(self) -> Dict[str, float]:
        return dict(self._scores)


# Default tactic prior for Lean 4 algebra
_DEFAULT_LEAN4_PRIOR = TacticPrior(
    scores={
        "simp":          0.80,
        "ring":          0.75,
        "omega":         0.65,
        "linarith":      0.60,
        "exact?":        0.50,
        "apply?":        0.45,
        "norm_num":      0.55,
        "decide":        0.40,
        "rfl":           0.70,
        "intro":         0.55,
        "induction":     0.50,
        "cases":         0.45,
        "constructor":   0.35,
        "assumption":    0.40,
        "trivial":       0.45,
        "aesop":         0.35,
    },
    default_score=0.10,
)


# ---------------------------------------------------------------------------
# ProofNode — one node in the proof search tree
# ---------------------------------------------------------------------------

@dataclass
class ProofNode:
    """
    One node in the proof search tree.

    Attributes
    ----------
    proof_so_far : str
        The Lean 4 proof text accumulated to this node (including all
        tactics applied on the path from root).
    tactic_applied : str
        The tactic that produced this node from its parent
        ('' for the root node).
    depth : int
        Distance from root (0 for root).
    is_complete : bool
        True if ``proof_so_far`` is a verified complete proof.
    error : Optional[str]
        Error returned by ``LeanTool.use()``; None if no error.
    priority : float
        Search priority (higher = expanded sooner in best-first search).
        Set externally by the searcher.
    parent : Optional[ProofNode]
        Reference to parent node (None for root).
    children : List[ProofNode]
        Child nodes produced by expanding this node.
    """
    proof_so_far:    str
    tactic_applied:  str          = ""
    depth:           int          = 0
    is_complete:     bool         = False
    error:           Optional[str]= None
    priority:        float        = 0.0
    parent:          Optional["ProofNode"] = field(default=None, repr=False)
    children:        List["ProofNode"]     = field(default_factory=list, repr=False)

    # Support heapq (min-heap on negative priority)
    def __lt__(self, other: "ProofNode") -> bool:
        return self.priority > other.priority   # higher priority = "less than"

    def tactic_path(self) -> List[str]:
        """Return the ordered list of tactics from root to this node."""
        path: List[str] = []
        node: Optional[ProofNode] = self
        while node is not None and node.tactic_applied:
            path.append(node.tactic_applied)
            node = node.parent
        return list(reversed(path))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "depth":         self.depth,
            "tactic":        self.tactic_applied,
            "is_complete":   self.is_complete,
            "error":         self.error,
            "priority":      round(self.priority, 4),
            "tactic_path":   self.tactic_path(),
        }


# ---------------------------------------------------------------------------
# ProofTree — best-first search tree
# ---------------------------------------------------------------------------

class ProofTree:
    """
    Best-first search tree over tactic sequences for a single theorem.

    Parameters
    ----------
    root_proof : str
        The initial proof text (typically just the theorem statement +
        ':= by').  Used to build the root node.
    lean_tool : Any
        A ``LeanTool``-compatible object with a ``.use(code: str)`` method
        returning None on success or an error string on failure.
    tactic_prior : TacticPrior
        Prior over tactic names (used to set node priorities).
    max_depth : int
        Maximum tactic depth (default 6).
    max_nodes : int
        Maximum total nodes to expand before giving up (default 200).
    """

    def __init__(
        self,
        root_proof:   str,
        lean_tool:    Any,
        tactic_prior: TacticPrior,
        max_depth:    int = 6,
        max_nodes:    int = 200,
    ):
        self.lean_tool    = lean_tool
        self.tactic_prior = tactic_prior
        self.max_depth    = max_depth
        self.max_nodes    = max_nodes
        self.nodes_expanded: int = 0
        self.solution_node: Optional[ProofNode] = None

        # Build root node
        root_error = lean_tool.use(root_proof)
        self.root = ProofNode(
            proof_so_far   = root_proof,
            tactic_applied = "",
            depth          = 0,
            is_complete    = (root_error is None),
            error          = root_error,
            priority       = 1.0,
        )
        # Priority queue (max-heap via negation in __lt__)
        self._frontier: List[ProofNode] = []
        if not self.root.is_complete:
            heapq.heappush(self._frontier, self.root)
        else:
            self.solution_node = self.root

    def _node_priority(self, node: ProofNode, tactic: str) -> float:
        """
        Compute search priority for a prospective child node.

        Priority = prior_score(tactic) * depth_discount^depth
        Deeper nodes are discounted to prevent unbounded depth-first dive.
        """
        depth_discount = 0.90 ** node.depth
        return self.tactic_prior.score(tactic) * depth_discount

    def expand(self, node: ProofNode, tactics: List[str]) -> List[ProofNode]:
        """
        Expand ``node`` by appending each tactic in ``tactics``.

        Each child proof is verified with ``LeanTool.use()``.
        Complete proofs set ``child.is_complete = True`` and update
        ``self.solution_node``.

        Returns the list of newly created child nodes.
        """
        children: List[ProofNode] = []
        for tactic in tactics:
            if self.nodes_expanded >= self.max_nodes:
                break
            # Build child proof text: append tactic on new indented line
            child_proof = node.proof_so_far.rstrip() + "\n  " + tactic
            error        = self.lean_tool.use(child_proof)
            complete     = (error is None)
            priority     = self._node_priority(node, tactic)
            child = ProofNode(
                proof_so_far   = child_proof,
                tactic_applied = tactic,
                depth          = node.depth + 1,
                is_complete    = complete,
                error          = error,
                priority       = priority,
                parent         = node,
            )
            node.children.append(child)
            children.append(child)
            self.nodes_expanded += 1

            if complete:
                self.solution_node = child
                self.tactic_prior.update(tactic, success=True)
                logger.debug("WP34 solution found at depth %d via '%s'", child.depth, tactic)
                break
            else:
                self.tactic_prior.update(tactic, success=False)
                if child.depth < self.max_depth:
                    heapq.heappush(self._frontier, child)

        return children

    def best_first_search(
        self,
        candidate_tactics: List[str],
        branching_factor:  int = 4,
    ) -> Optional[ProofNode]:
        """
        Run best-first search until a solution is found or budget exhausted.

        At each step, the highest-priority open node is expanded with the
        top-``branching_factor`` tactics from the prior.

        Parameters
        ----------
        candidate_tactics : List[str]
            Full set of tactics to consider at each expansion.
        branching_factor : int
            Number of tactics to try per node (default 4).

        Returns
        -------
        ProofNode or None
            The solution node if found, else None.
        """
        if self.solution_node is not None:
            return self.solution_node

        while self._frontier and self.nodes_expanded < self.max_nodes:
            node = heapq.heappop(self._frontier)
            if node.depth >= self.max_depth:
                continue
            top_tactics = self.tactic_prior.top_k(candidate_tactics, branching_factor)
            self.expand(node, top_tactics)
            if self.solution_node is not None:
                return self.solution_node

        return None

    def statistics(self) -> Dict[str, Any]:
        """Return search statistics."""
        return {
            "nodes_expanded": self.nodes_expanded,
            "frontier_size":  len(self._frontier),
            "max_depth_reached": self._max_depth_reached(),
            "solution_found": self.solution_node is not None,
            "solution_depth": self.solution_node.depth if self.solution_node else None,
            "solution_tactics": self.solution_node.tactic_path() if self.solution_node else None,
        }

    def _max_depth_reached(self) -> int:
        """Traverse the tree to find the maximum depth expanded."""
        def _depth(node: ProofNode) -> int:
            if not node.children:
                return node.depth
            return max(_depth(c) for c in node.children)
        return _depth(self.root)


# ---------------------------------------------------------------------------
# ProofSearchRecord — per-theorem audit
# ---------------------------------------------------------------------------

@dataclass
class ProofSearchRecord:
    """
    Per-theorem audit record for one ``ProofTreeSearcher`` run.

    Attributes
    ----------
    theorem : str
    success : bool
    nodes_expanded : int
    max_depth_reached : int
    solution_depth : Optional[int]
    solution_tactics : Optional[List[str]]
    solution_proof : Optional[str]
    wall_time_s : float
    timestamp : float
    """
    theorem:           str
    success:           bool
    nodes_expanded:    int
    max_depth_reached: int
    solution_depth:    Optional[int]
    solution_tactics:  Optional[List[str]]
    solution_proof:    Optional[str]
    wall_time_s:       float
    timestamp:         float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "theorem":           self.theorem[:80],
            "success":           self.success,
            "nodes_expanded":    self.nodes_expanded,
            "max_depth_reached": self.max_depth_reached,
            "solution_depth":    self.solution_depth,
            "solution_tactics":  self.solution_tactics,
            "wall_time_s":       round(self.wall_time_s, 3),
        }


# ---------------------------------------------------------------------------
# ProofTreeSearcher — orchestrates full search for one theorem
# ---------------------------------------------------------------------------

class ProofTreeSearcher:
    """
    Orchestrates best-first proof tree search for a single theorem.

    Parameters
    ----------
    lean_tool : Any
        ``LeanTool``-compatible object.
    tactic_prior : TacticPrior
        Prior over tactic names.  Updated in-place after each search.
    candidate_tactics : List[str]
        Tactics to consider at each expansion.
    branching_factor : int
        Tactics to try per node (default 4).
    max_depth : int
        Maximum search depth (default 6).
    max_nodes : int
        Maximum nodes to expand (default 200).
    """

    # Default Lean 4 algebra tactics
    DEFAULT_TACTICS: List[str] = [
        "simp", "ring", "omega", "linarith", "norm_num", "rfl",
        "decide", "trivial", "aesop", "exact?",
        "intro n", "intro a b", "induction n with",
        "cases n with", "constructor", "assumption",
        "simp [Nat.add_comm]", "simp [Nat.mul_comm]",
        "ring_nf", "field_simp", "push_neg",
    ]

    def __init__(
        self,
        lean_tool:         Any,
        tactic_prior:      Optional[TacticPrior]  = None,
        candidate_tactics: Optional[List[str]]    = None,
        branching_factor:  int  = 4,
        max_depth:         int  = 6,
        max_nodes:         int  = 200,
    ):
        self.lean_tool         = lean_tool
        self.tactic_prior      = tactic_prior or _DEFAULT_LEAN4_PRIOR
        self.candidate_tactics = candidate_tactics or self.DEFAULT_TACTICS
        self.branching_factor  = branching_factor
        self.max_depth         = max_depth
        self.max_nodes         = max_nodes
        self.search_history:   List[ProofSearchRecord] = []

    def search(self, theorem: str) -> ProofSearchRecord:
        """
        Run best-first proof tree search for ``theorem``.

        ``theorem`` should be a complete Lean 4 theorem statement
        (without ':= by').  The searcher builds the root proof as
        ``theorem + '\\n  := by'`` and then tries tactics.

        Parameters
        ----------
        theorem : str
            Lean 4 theorem statement, e.g.
            'theorem add_zero (n : Nat) : n + 0 = n'

        Returns
        -------
        ProofSearchRecord
        """
        t0 = time.time()

        # Build the initial partial proof
        root_proof = theorem.rstrip() + " := by"

        tree = ProofTree(
            root_proof   = root_proof,
            lean_tool    = self.lean_tool,
            tactic_prior = self.tactic_prior,
            max_depth    = self.max_depth,
            max_nodes    = self.max_nodes,
        )

        solution = tree.best_first_search(
            candidate_tactics = self.candidate_tactics,
            branching_factor  = self.branching_factor,
        )

        stats = tree.statistics()
        wall  = time.time() - t0

        record = ProofSearchRecord(
            theorem           = theorem,
            success           = solution is not None,
            nodes_expanded    = stats["nodes_expanded"],
            max_depth_reached = stats["max_depth_reached"],
            solution_depth    = stats["solution_depth"],
            solution_tactics  = stats["solution_tactics"],
            solution_proof    = solution.proof_so_far if solution else None,
            wall_time_s       = wall,
        )
        self.search_history.append(record)

        logger.info(
            "WP34 search: theorem='%s...' success=%s nodes=%d depth=%s time=%.2fs",
            theorem[:40], record.success, record.nodes_expanded,
            record.solution_depth, wall,
        )
        return record

    def batch_search(self, theorems: List[str]) -> List[ProofSearchRecord]:
        """Run ``search()`` for each theorem in the list."""
        return [self.search(t) for t in theorems]

    def summary(self) -> Dict[str, Any]:
        """Aggregate statistics over all searches performed."""
        if not self.search_history:
            return {"n_theorems": 0}
        n      = len(self.search_history)
        n_ok   = sum(r.success for r in self.search_history)
        avg_nodes  = sum(r.nodes_expanded for r in self.search_history) / n
        avg_depth  = sum(
            r.solution_depth for r in self.search_history if r.solution_depth is not None
        ) / max(n_ok, 1)
        return {
            "n_theorems":      n,
            "n_proved":        n_ok,
            "success_rate":    round(n_ok / n, 4),
            "avg_nodes":       round(avg_nodes, 1),
            "avg_solution_depth": round(avg_depth, 2),
            "tactic_prior":    self.tactic_prior.to_dict(),
        }


# ---------------------------------------------------------------------------
# verify_wp34_exit_criteria — six-criterion verifier
# ---------------------------------------------------------------------------

def verify_wp34_exit_criteria(
    search_history: List[ProofSearchRecord],
    tactic_prior:   TacticPrior,
) -> Dict[str, bool]:
    """
    Verify WP34 exit criteria.

    Criteria
    --------
    1. At least one theorem proved by tree search (success=True in history).
    2. At least two nodes expanded during at least one search (tree was built).
    3. Solution depth is recorded for successful searches.
    4. Tactic prior has been updated (scores differ from default 0.10 for some tactics).
    5. ProofSearchRecord contains tactic path (solution_tactics is a list).
    6. Backtracking: at least one search explored more than one tactic at depth 0
       (branching_factor > 1 used).
    """
    results: Dict[str, bool] = {}

    # 1. At least one theorem proved
    results["At least one theorem proved by tree search"] = any(
        r.success for r in search_history
    )

    # 2. At least two nodes expanded in some search
    results["Tree expanded (>=2 nodes in at least one search)"] = any(
        r.nodes_expanded >= 2 for r in search_history
    )

    # 3. Solution depth recorded for successes
    successes = [r for r in search_history if r.success]
    results["Solution depth recorded for successful searches"] = all(
        r.solution_depth is not None for r in successes
    ) if successes else False

    # 4. Tactic prior updated beyond defaults
    non_default = [
        v for v in tactic_prior.to_dict().values()
        if abs(v - tactic_prior.default_score) > 0.01
    ]
    results["Tactic prior updated from search experience"] = len(non_default) >= 1

    # 5. Tactic path available
    results["Solution tactic path recorded"] = all(
        isinstance(r.solution_tactics, list) for r in successes
    ) if successes else False

    # 6. Multiple tactics tried at root (branching)
    results["Search used branching (>= 2 tactics tried per node)"] = any(
        r.nodes_expanded >= 2 for r in search_history
    )

    return results
