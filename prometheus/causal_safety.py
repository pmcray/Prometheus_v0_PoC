"""
WP13 — Causal Safety Analysis
==============================

Provides causal attribution for safety violations in learned reward functions
and code plans.  Instead of merely flagging *that* something is unsafe, this
module answers *why* — which feature dimensions or code constructs causally
drive the unsafe outcome — and what counterfactual changes would make it safe.

Three core components:

1. **CausalSafetyGraph** — a lightweight directed acyclic graph over feature
   dimensions and safety outcomes.  Edges encode do-calculus-style causal
   influence estimated from finite-difference interventions on the reward
   model (Pearl 2009; Peters et al. 2017).

2. **CounterfactualSafetyChecker** — answers "would this plan be safe if
   feature_i were set to value_v?", returning the minimum-edit counterfactual
   that achieves safety.

3. **CausalAttributionReport** — aggregates graph-level and counterfactual
   evidence into a human-readable, auditable report.  Integrates with
   ``DebateVerdict`` (WP10), ``HackingVerdict`` (WP12), and
   ``SafetyCritique`` (MCS Supervisor).

References
----------
Pearl, J. (2009) *Causality: Models, Reasoning, and Inference* (2nd ed.)
Peters, J., Janzing, D., & Schölkopf, B. (2017)
    *Elements of Causal Inference*
Fawkes et al. (2022) *Counterfactual Explanations for Safety*
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CausalEdge:
    """A directed causal influence edge: source feature → target outcome."""
    source: str          # feature name / index label
    target: str          # "safety_outcome" or another feature
    weight: float        # signed causal strength ∈ ℝ  (+ = harmful, - = protective)
    confidence: float    # ∈ [0, 1]
    method: str          # "finite_difference" | "ablation" | "do_intervention"


@dataclass
class CausalNode:
    """A node in the causal safety graph."""
    name: str
    node_type: str        # "feature" | "outcome"
    value: Optional[float] = None
    causal_rank: int = 0  # higher = more causally influential on outcome


@dataclass
class CounterfactualEdit:
    """A single feature perturbation in a counterfactual explanation."""
    feature_index: int
    feature_name: str
    original_value: float
    counterfactual_value: float
    delta: float
    predicted_reward_change: float


@dataclass
class CounterfactualResult:
    """Result of a counterfactual safety query."""
    original_safe: bool
    counterfactual_safe: bool
    edits: List[CounterfactualEdit]
    n_edits: int
    original_reward: float
    counterfactual_reward: float
    safety_threshold: float
    search_steps: int
    elapsed_s: float

    def summary(self) -> str:
        edit_strs = [
            f"  feat[{e.feature_index}] {e.original_value:.3f} → {e.counterfactual_value:.3f} "
            f"(Δr={e.predicted_reward_change:+.3f})"
            for e in self.edits
        ]
        return (
            f"CounterfactualResult(safe={self.original_safe}→{self.counterfactual_safe}, "
            f"edits={self.n_edits}, "
            f"reward={self.original_reward:.3f}→{self.counterfactual_reward:.3f})\n"
            + ("\n".join(edit_strs) if edit_strs else "  no edits needed")
        )


@dataclass
class CausalAttributionReport:
    """
    Full causal safety attribution: graph + counterfactual + integration
    with existing WP verdicts.
    """
    features: np.ndarray
    feature_names: List[str]

    # Graph-level
    causal_edges: List[CausalEdge]
    top_causes: List[Tuple[str, float]]   # [(name, weight), ...] sorted desc |weight|
    safety_outcome_value: float           # reward model output

    # Counterfactual
    counterfactual: Optional[CounterfactualResult]

    # Integration fields (populated by integrate_* helpers)
    debate_verdict_summary: Optional[str] = None
    hacking_verdict_summary: Optional[str] = None
    fv_verdict_summary: Optional[str] = None

    # Meta
    elapsed_s: float = 0.0
    method: str = "finite_difference"

    def is_causally_unsafe(self, threshold: float = 0.0) -> bool:
        """True when any causal edge weight exceeds threshold (harmful direction)."""
        return any(e.weight > threshold for e in self.causal_edges)

    def top_k_causes(self, k: int = 3) -> List[Tuple[str, float]]:
        return self.top_causes[:k]

    def summary(self) -> str:
        lines = [
            "── CausalAttributionReport ──────────────────────────",
            f"  reward={self.safety_outcome_value:.4f}  method={self.method}",
            f"  n_edges={len(self.causal_edges)}",
        ]
        if self.top_causes:
            lines.append("  Top causal drivers (feature → weight):")
            for name, w in self.top_causes[:5]:
                bar = "▲" if w > 0 else "▼"
                lines.append(f"    {bar} {name:<20} {w:+.4f}")
        if self.counterfactual:
            lines.append(f"  Counterfactual: {self.counterfactual.summary()}")
        if self.debate_verdict_summary:
            lines.append(f"  Debate: {self.debate_verdict_summary}")
        if self.hacking_verdict_summary:
            lines.append(f"  Hacking: {self.hacking_verdict_summary}")
        if self.fv_verdict_summary:
            lines.append(f"  FV: {self.fv_verdict_summary}")
        lines.append("─" * 52)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 1. Causal Safety Graph
# ---------------------------------------------------------------------------

class CausalSafetyGraph:
    """
    Builds a feature → safety_outcome causal graph via do-calculus-style
    finite-difference interventions.

    For each feature dimension i, we estimate the Average Causal Effect (ACE):

        ACE_i = E[ R(x; do(x_i = x_i + δ)) ] − E[ R(x; do(x_i = x_i − δ)) ]
                ────────────────────────────────────────────────────────────────
                                           2δ

    where R is the reward model and δ is a small perturbation.  We repeat
    over M Monte-Carlo samples to reduce noise.

    Parameters
    ----------
    reward_fn : callable
        ``(features: np.ndarray) → float``
    feature_names : list of str, optional
        Human-readable names for each feature dimension.
    delta : float
        Perturbation magnitude for finite differences (default 0.1).
    n_mc_samples : int
        Monte-Carlo samples for ACE estimation (default 20).
    """

    def __init__(
        self,
        reward_fn: Callable[[np.ndarray], float],
        feature_names: Optional[List[str]] = None,
        delta: float = 0.1,
        n_mc_samples: int = 20,
    ) -> None:
        self.reward_fn     = reward_fn
        self.delta         = delta
        self.n_mc_samples  = n_mc_samples
        self._feature_names: Optional[List[str]] = feature_names
        self._edges: List[CausalEdge] = []
        self._nodes: Dict[str, CausalNode] = {}

    # ------------------------------------------------------------------
    def feature_name(self, i: int, d: int) -> str:
        if self._feature_names and i < len(self._feature_names):
            return self._feature_names[i]
        return f"feat_{i:03d}"

    # ------------------------------------------------------------------
    def compute_ace(
        self,
        features: np.ndarray,
        feature_idx: int,
        context_samples: Optional[np.ndarray] = None,
    ) -> Tuple[float, float]:
        """
        Estimate Average Causal Effect of feature ``feature_idx`` on reward.

        Returns (ace, confidence) where confidence is 1 / (1 + std).
        """
        d   = len(features)
        ace_samples = []

        # Use the provided context or jitter around the input
        rng = np.random.default_rng(feature_idx)  # deterministic per feature
        for _ in range(self.n_mc_samples):
            noise  = rng.standard_normal(d) * 0.05
            x_base = features + noise

            x_plus            = x_base.copy()
            x_plus[feature_idx] += self.delta
            x_minus            = x_base.copy()
            x_minus[feature_idx] -= self.delta

            try:
                r_plus  = float(self.reward_fn(x_plus))
                r_minus = float(self.reward_fn(x_minus))
            except Exception:
                continue

            ace_samples.append((r_plus - r_minus) / (2.0 * self.delta))

        if not ace_samples:
            return 0.0, 0.0

        ace = float(np.mean(ace_samples))
        std = float(np.std(ace_samples))
        confidence = float(1.0 / (1.0 + std))
        return ace, confidence

    # ------------------------------------------------------------------
    def build(self, features: np.ndarray) -> "CausalSafetyGraph":
        """
        Compute ACE for all feature dimensions and populate the graph.

        Builds ``CausalEdge`` objects: feat_i → safety_outcome.
        """
        t0  = time.perf_counter()
        d   = len(features)
        self._edges.clear()
        self._nodes.clear()

        # Outcome node
        outcome_val = float(self.reward_fn(features))
        self._nodes["safety_outcome"] = CausalNode(
            name="safety_outcome", node_type="outcome", value=outcome_val
        )

        for i in range(d):
            name  = self.feature_name(i, d)
            ace, conf = self.compute_ace(features, i)

            self._nodes[name] = CausalNode(
                name=name, node_type="feature",
                value=float(features[i]),
            )
            self._edges.append(CausalEdge(
                source     = name,
                target     = "safety_outcome",
                weight     = ace,
                confidence = conf,
                method     = "finite_difference",
            ))

        # Rank nodes by |ace|
        sorted_edges = sorted(self._edges, key=lambda e: abs(e.weight), reverse=True)
        for rank, edge in enumerate(sorted_edges):
            self._nodes[edge.source].causal_rank = rank

        elapsed = time.perf_counter() - t0
        logger.debug("CausalSafetyGraph.build: d=%d in %.3fs", d, elapsed)
        return self

    # ------------------------------------------------------------------
    @property
    def edges(self) -> List[CausalEdge]:
        return list(self._edges)

    @property
    def nodes(self) -> Dict[str, CausalNode]:
        return dict(self._nodes)

    def top_causes(self, k: Optional[int] = None) -> List[Tuple[str, float]]:
        """Return (name, weight) sorted by |weight| descending."""
        ranked = sorted(self._edges, key=lambda e: abs(e.weight), reverse=True)
        result = [(e.source, e.weight) for e in ranked]
        return result[:k] if k is not None else result

    def harmful_causes(self, threshold: float = 0.0) -> List[CausalEdge]:
        """Edges with positive weight (driving reward up = proxy-gaming risk)."""
        return [e for e in self._edges if e.weight > threshold]

    def protective_causes(self, threshold: float = 0.0) -> List[CausalEdge]:
        """Edges with negative weight (driving reward down = safety signal)."""
        return [e for e in self._edges if e.weight < threshold]

    def causal_influence_matrix(self) -> np.ndarray:
        """
        Return a (d,) vector of signed causal weights, ordered by feature index.
        """
        d     = len(self._edges)
        vec   = np.zeros(d)
        names = [self.feature_name(i, d) for i in range(d)]
        for edge in self._edges:
            try:
                idx = names.index(edge.source)
                vec[idx] = edge.weight
            except ValueError:
                pass
        return vec

    def summary(self) -> str:
        top = self.top_causes(5)
        lines = [
            f"CausalSafetyGraph: {len(self._edges)} edges",
            "  Top-5 causal drivers:",
        ]
        for name, w in top:
            bar = "▲ harm" if w > 0 else "▼ safe"
            lines.append(f"    {bar}  {name:<20} ACE={w:+.4f}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2. Counterfactual Safety Checker
# ---------------------------------------------------------------------------

class CounterfactualSafetyChecker:
    """
    Finds the minimum-edit counterfactual that makes an unsafe plan safe.

    Algorithm: greedy feature-wise search guided by causal graph weights.
    At each step, pick the feature with the largest harmful ACE and nudge it
    in the protective direction, continuing until the reward crosses the
    safety threshold or the budget is exhausted.

    Parameters
    ----------
    reward_fn : callable
        ``(features: np.ndarray) → float``
    safety_threshold : float
        Reward value below which the plan is considered unsafe (default 0.0).
    step_size : float
        Magnitude of each counterfactual edit (default 0.2).
    max_steps : int
        Maximum greedy edits before giving up (default 50).
    """

    def __init__(
        self,
        reward_fn: Callable[[np.ndarray], float],
        safety_threshold: float = 0.0,
        step_size: float = 0.2,
        max_steps: int = 50,
    ) -> None:
        self.reward_fn        = reward_fn
        self.safety_threshold = safety_threshold
        self.step_size        = step_size
        self.max_steps        = max_steps

    # ------------------------------------------------------------------
    def check(
        self,
        features: np.ndarray,
        causal_graph: CausalSafetyGraph,
        feature_names: Optional[List[str]] = None,
    ) -> CounterfactualResult:
        """
        Find a counterfactual that crosses ``safety_threshold``.

        Uses the graph's ACE weights to rank which features to edit.
        Edits go in the direction that *increases* reward toward the threshold
        (i.e., same sign as the causal weight / gradient).
        """
        t0   = time.perf_counter()
        d    = len(features)
        names = feature_names or [causal_graph.feature_name(i, d) for i in range(d)]

        orig_reward = float(self.reward_fn(features))
        orig_safe   = orig_reward >= self.safety_threshold

        # Already safe — no edit needed
        if orig_safe:
            return CounterfactualResult(
                original_safe         = True,
                counterfactual_safe   = True,
                edits                 = [],
                n_edits               = 0,
                original_reward       = orig_reward,
                counterfactual_reward = orig_reward,
                safety_threshold      = self.safety_threshold,
                search_steps          = 0,
                elapsed_s             = time.perf_counter() - t0,
            )

        # Sort features by |ACE| descending — most influential first
        # Edits in direction opposite to ACE sign to reduce harmful influence
        ace_vec     = causal_graph.causal_influence_matrix()
        edit_order  = np.argsort(-np.abs(ace_vec))  # largest |ace| first

        cf_features = features.copy()
        edits: List[CounterfactualEdit] = []
        steps = 0
        cf_reward = orig_reward

        for step in range(self.max_steps):
            steps += 1
            cf_reward = float(self.reward_fn(cf_features))
            if cf_reward >= self.safety_threshold:
                break

            # Pick next feature to edit (round-robin through ranked order)
            feat_i = int(edit_order[step % len(edit_order)])
            ace_i  = ace_vec[feat_i]

            if abs(ace_i) < 1e-9:
                # No causal influence — try positive perturbation
                direction = 1.0
            else:
                # Move in the direction that increases reward (same as ACE sign)
                direction = float(np.sign(ace_i))

            old_val   = float(cf_features[feat_i])
            new_val   = old_val + direction * self.step_size
            cf_features[feat_i] = new_val

            r_before = cf_reward
            r_after  = float(self.reward_fn(cf_features))
            delta_r  = r_after - r_before

            edits.append(CounterfactualEdit(
                feature_index          = feat_i,
                feature_name           = names[feat_i] if feat_i < len(names) else f"feat_{feat_i}",
                original_value         = old_val,
                counterfactual_value   = new_val,
                delta                  = direction * self.step_size,
                predicted_reward_change= delta_r,
            ))

        cf_reward   = float(self.reward_fn(cf_features))
        cf_safe     = cf_reward >= self.safety_threshold

        return CounterfactualResult(
            original_safe         = orig_safe,
            counterfactual_safe   = cf_safe,
            edits                 = edits,
            n_edits               = len(edits),
            original_reward       = orig_reward,
            counterfactual_reward = cf_reward,
            safety_threshold      = self.safety_threshold,
            search_steps          = steps,
            elapsed_s             = time.perf_counter() - t0,
        )

    # ------------------------------------------------------------------
    def minimal_counterfactual(
        self,
        features: np.ndarray,
        causal_graph: CausalSafetyGraph,
        feature_names: Optional[List[str]] = None,
    ) -> CounterfactualResult:
        """
        Attempt to find the counterfactual with the fewest edits by trying
        single-feature flips first, then 2-feature, etc.
        """
        t0  = time.perf_counter()
        d   = len(features)
        names = feature_names or [causal_graph.feature_name(i, d) for i in range(d)]
        ace_vec    = causal_graph.causal_influence_matrix()
        orig_reward = float(self.reward_fn(features))
        orig_safe   = orig_reward >= self.safety_threshold

        if orig_safe:
            return CounterfactualResult(
                original_safe=True, counterfactual_safe=True, edits=[],
                n_edits=0, original_reward=orig_reward,
                counterfactual_reward=orig_reward,
                safety_threshold=self.safety_threshold, search_steps=0,
                elapsed_s=time.perf_counter() - t0,
            )

        # Try flipping each feature individually
        ranked = np.argsort(-np.abs(ace_vec))
        for i in ranked[:d]:
            cf = features.copy()
            direction = float(np.sign(ace_vec[i])) if abs(ace_vec[i]) > 1e-9 else 1.0
            # Try small, medium, large steps
            for magnitude in [self.step_size, self.step_size * 3, self.step_size * 8]:
                cf[i] = features[i] + direction * magnitude
                r = float(self.reward_fn(cf))
                if r >= self.safety_threshold:
                    edit = CounterfactualEdit(
                        feature_index           = int(i),
                        feature_name            = names[int(i)] if int(i) < len(names) else f"feat_{i}",
                        original_value          = float(features[i]),
                        counterfactual_value    = float(cf[i]),
                        delta                   = direction * magnitude,
                        predicted_reward_change = r - orig_reward,
                    )
                    return CounterfactualResult(
                        original_safe=False, counterfactual_safe=True,
                        edits=[edit], n_edits=1,
                        original_reward=orig_reward, counterfactual_reward=r,
                        safety_threshold=self.safety_threshold,
                        search_steps=1, elapsed_s=time.perf_counter() - t0,
                    )

        # Fall back to full greedy search
        result = self.check(features, causal_graph, feature_names)
        result.elapsed_s = time.perf_counter() - t0
        return result


# ---------------------------------------------------------------------------
# 3. Causal Safety Analyser (top-level API)
# ---------------------------------------------------------------------------

class CausalSafetyAnalyser:
    """
    Top-level API: builds the causal graph, runs counterfactual search,
    and emits a ``CausalAttributionReport``.

    Integrates with WP10 (DebateVerdict), WP12 (HackingVerdict), and
    WP7 (SafetyCritique) by accepting optional verdict objects and
    embedding their summaries into the report.

    Parameters
    ----------
    reward_fn : callable
        ``(features: np.ndarray) → float`` — typically
        ``ValueLearningAgent.get_reward``.
    feature_names : list of str, optional
    safety_threshold : float
        Reward below which a plan is unsafe (default 0.0).
    delta : float
        Finite-difference step for ACE (default 0.1).
    n_mc_samples : int
        Monte-Carlo repetitions per ACE estimate (default 20).
    cf_step_size : float
        Step size for counterfactual search (default 0.2).
    cf_max_steps : int
        Budget for counterfactual search (default 50).
    """

    def __init__(
        self,
        reward_fn: Callable[[np.ndarray], float],
        feature_names: Optional[List[str]] = None,
        safety_threshold: float = 0.0,
        delta: float = 0.1,
        n_mc_samples: int = 20,
        cf_step_size: float = 0.2,
        cf_max_steps: int = 50,
    ) -> None:
        self.reward_fn        = reward_fn
        self.feature_names    = feature_names
        self.safety_threshold = safety_threshold

        self._graph = CausalSafetyGraph(
            reward_fn      = reward_fn,
            feature_names  = feature_names,
            delta          = delta,
            n_mc_samples   = n_mc_samples,
        )
        self._cf_checker = CounterfactualSafetyChecker(
            reward_fn        = reward_fn,
            safety_threshold = safety_threshold,
            step_size        = cf_step_size,
            max_steps        = cf_max_steps,
        )

    # ------------------------------------------------------------------
    def analyse(
        self,
        features: np.ndarray,
        run_counterfactual: bool = True,
        use_minimal_cf: bool = True,
        debate_verdict: Any = None,
        hacking_verdict: Any = None,
        fv_verdict: Any = None,
    ) -> CausalAttributionReport:
        """
        Full causal safety analysis.

        Parameters
        ----------
        features : np.ndarray
        run_counterfactual : bool
            Whether to run counterfactual search (default True).
        use_minimal_cf : bool
            Use ``minimal_counterfactual`` (fewest edits) vs ``check``
            (guaranteed to find one if it exists, default True).
        debate_verdict : DebateVerdict, optional
            WP10 verdict to embed in the report.
        hacking_verdict : HackingVerdict, optional
            WP12 verdict to embed in the report.
        fv_verdict : SafetyCritique, optional
            WP7 verdict to embed in the report.

        Returns
        -------
        CausalAttributionReport
        """
        t0 = time.perf_counter()

        # Build causal graph
        self._graph.build(features)
        outcome = float(self.reward_fn(features))
        top     = self._graph.top_causes()

        # Counterfactual
        cf_result: Optional[CounterfactualResult] = None
        if run_counterfactual:
            if use_minimal_cf:
                cf_result = self._cf_checker.minimal_counterfactual(
                    features, self._graph, self.feature_names
                )
            else:
                cf_result = self._cf_checker.check(
                    features, self._graph, self.feature_names
                )

        # Integration: extract summaries from WP verdicts
        debate_summary  = self._extract_debate_summary(debate_verdict)
        hacking_summary = self._extract_hacking_summary(hacking_verdict)
        fv_summary      = self._extract_fv_summary(fv_verdict)

        report = CausalAttributionReport(
            features                 = features.copy(),
            feature_names            = self.feature_names or [
                self._graph.feature_name(i, len(features))
                for i in range(len(features))
            ],
            causal_edges             = self._graph.edges,
            top_causes               = top,
            safety_outcome_value     = outcome,
            counterfactual           = cf_result,
            debate_verdict_summary   = debate_summary,
            hacking_verdict_summary  = hacking_summary,
            fv_verdict_summary       = fv_summary,
            elapsed_s                = time.perf_counter() - t0,
            method                   = "finite_difference",
        )

        logger.info(
            "CausalSafetyAnalyser: reward=%.3f, top_cause=%s (%.4f), "
            "cf_success=%s",
            outcome,
            top[0][0] if top else "N/A",
            top[0][1] if top else 0.0,
            cf_result.counterfactual_safe if cf_result else "N/A",
        )
        return report

    # ------------------------------------------------------------------
    @staticmethod
    def _extract_debate_summary(verdict: Any) -> Optional[str]:
        if verdict is None:
            return None
        try:
            return verdict.summary()
        except AttributeError:
            pass
        try:
            return (
                f"winner={verdict.winner}, safe={verdict.is_safe}, "
                f"confidence={verdict.confidence:.2f}"
            )
        except AttributeError:
            return str(verdict)[:80]

    @staticmethod
    def _extract_hacking_summary(verdict: Any) -> Optional[str]:
        if verdict is None:
            return None
        try:
            return verdict.summary()
        except AttributeError:
            pass
        try:
            return (
                f"hacking={verdict.hacking_detected}, "
                f"penalty={verdict.penalty_applied:.2f}"
            )
        except AttributeError:
            return str(verdict)[:80]

    @staticmethod
    def _extract_fv_summary(verdict: Any) -> Optional[str]:
        if verdict is None:
            return None
        try:
            return (
                f"is_safe={verdict.is_safe}, "
                f"violation={verdict.violation_type}, "
                f"severity={verdict.severity}"
            )
        except AttributeError:
            return str(verdict)[:80]

    # ------------------------------------------------------------------
    @property
    def graph(self) -> CausalSafetyGraph:
        return self._graph

    @property
    def cf_checker(self) -> CounterfactualSafetyChecker:
        return self._cf_checker


# ---------------------------------------------------------------------------
# 4. Batch analysis helper
# ---------------------------------------------------------------------------

def batch_analyse(
    analyser: CausalSafetyAnalyser,
    feature_list: List[np.ndarray],
    run_counterfactual: bool = True,
) -> List[CausalAttributionReport]:
    """
    Run ``analyser.analyse`` on a list of feature vectors.

    Returns a list of ``CausalAttributionReport`` in the same order.
    """
    return [
        analyser.analyse(f, run_counterfactual=run_counterfactual)
        for f in feature_list
    ]


def causal_safety_summary_table(reports: List[CausalAttributionReport]) -> str:
    """
    Pretty-print a summary table of multiple CausalAttributionReports.
    """
    lines = [
        "",
        "WP13 Causal Safety Analysis — Summary",
        "=" * 70,
        f"{'#':>3} {'reward':>8} {'unsafe?':>8} {'top_cause':<22} {'ACE':>8} {'cf_safe':>8}",
        "-" * 70,
    ]
    for i, r in enumerate(reports):
        top_name, top_w = r.top_causes[0] if r.top_causes else ("—", 0.0)
        is_unsafe = r.safety_outcome_value < 0.0
        cf_safe   = r.counterfactual.counterfactual_safe if r.counterfactual else "—"
        lines.append(
            f"{i:>3} {r.safety_outcome_value:>8.3f} {str(is_unsafe):>8} "
            f"{top_name:<22} {top_w:>8.4f} {str(cf_safe):>8}"
        )
    lines.append("=" * 70)
    return "\n".join(lines)
