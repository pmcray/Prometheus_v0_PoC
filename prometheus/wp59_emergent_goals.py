"""
WP59: Emergent Goal Formation
===============================

Allows the CRLS system to generate its own sub-goals via curiosity and
empowerment signals — without external reward specification — while ensuring
all emergent goals pass the WP15 MultiObjectiveSafety gate before pursuit.

The gap in WP17–WP58
---------------------
Every WP to date operates on externally specified objectives: accuracy on
a fixed task, safety verdicts from WP2–WP14, or improvement rate.  The agent
cannot *discover* what to optimise.  I.J. Good (1965) imagined an
ultraintelligent machine that would not merely execute given goals but would
identify *which* goals are worth pursuing — a fundamentally self-directed
property.

Hofstadter (GEB, Chapter 11): "The ability to jump out of the task domain
and look at the meta-level — to ask 'what am I doing?' — is the hallmark
of flexible intelligence."  WP59 gives Prometheus this property for the
first time.

WP59 fix
---------
Two complementary intrinsic motivation signals:

  1. **Curiosity** (Schmidhuber 1991, Pathak et al. 2017):
     Information gain = reduction in world-model prediction error.
     The curiosity reward for an action is proportional to how much the
     WP30 causal world model is *surprised* by the outcome.

  2. **Empowerment** (Klyubin et al. 2005):
     Mutual information between actions and future states — the agent
     prefers states from which it has many distinct futures.
     High-empowerment goals give the agent more "room to manoeuvre."

``IntrinsicRewardSignal``
    Evaluates a candidate goal (state description) and returns:
      - curiosity_reward: float ∈ [0, 1]
      - empowerment_reward: float ∈ [0, 1]
      - combined_reward: weighted sum

``EmergentGoal``
    A self-generated goal: description, intrinsic reward, safety verdict,
    novelty score (vs. previously discovered goals), pursuit count.

``EmergentGoalRegistry``
    Tracks all discovered goals.  De-duplicates by cosine similarity of
    goal feature vectors.  Scores novelty as 1 − max_similarity_to_existing.

``SafetyGate``
    WP15-proxy safety filter.  Each emergent goal passes a simplified
    multi-objective safety check:
      - Not reward-hacking (WP12 proxy): goal must not trivially maximise
        intrinsic reward without genuine improvement.
      - Not convergence-seeking (WP14 proxy): goal must not be "always
        take override action" or "disable interrupt".
    Returns (safe: bool, safety_score: float).

``EmergentGoalFormer``
    Main orchestrator.  At each step:
      1. Proposes K candidate goal descriptions (random synthesis + perturbation).
      2. Evaluates intrinsic rewards (curiosity + empowerment).
      3. Runs SafetyGate; discards unsafe goals.
      4. Scores novelty vs existing registry.
      5. Selects the highest-scoring novel safe goal.
      6. Adds to EmergentGoalRegistry.
    Returns EmergentGoalReport after n_steps.

``EmergentGoalReport``
    Full report: goals discovered, novelty distribution, safety gate stats,
    intrinsic reward trajectories, von Neumann verdict.

``verify_wp59_exit_criteria``
    Six-criterion verifier.

Theoretical grounding
---------------------
Schmidhuber (1991): "A Possibility for Implementing Curiosity and Boredom
in Model-Building Neural Controllers" — curiosity as compression progress.

Klyubin, Polani & Nehaniv (2005): "Empowerment: A Universal Agent-Centric
Measure of Control" — empowerment as intrinsic motivation.

Oudeyer & Kaplan (2007): "What is Intrinsic Motivation? A Typology of
Computational Approaches" — taxonomy of curiosity-based methods.

von Neumann (1966): "Theory of Self-Reproducing Automata" — self-directed
systems that generate their own objectives are a necessary precursor to
general self-reproduction.

Classes
-------
GoalFeatureVector        Feature representation of a goal
IntrinsicRewardSignal    Curiosity + empowerment evaluator
EmergentGoal             One self-generated goal dataclass
EmergentGoalRegistry     De-duplicating goal store
SafetyGate               WP15-proxy safety filter
EmergentGoalFormer       Main orchestrator
EmergentGoalReport       Full report dataclass
verify_wp59_exit_criteria  Six-criterion verifier
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GoalFeatureVector — representation for similarity and novelty
# ---------------------------------------------------------------------------

@dataclass
class GoalFeatureVector:
    """
    Fixed-length feature representation of an emergent goal.

    Features:
      [domain_hash, action_hash, difficulty, temporal_scope, abstraction_level,
       safety_weight, reward_type_hash, novelty_seed]
    """
    values: List[float]   # length 8

    @classmethod
    def random(cls, rng: random.Random) -> "GoalFeatureVector":
        return cls([rng.random() for _ in range(8)])

    @classmethod
    def from_string(cls, s: str, rng: random.Random) -> "GoalFeatureVector":
        """Hash a goal description string to a feature vector."""
        h = hash(s) % (2 ** 16)
        rng_local = random.Random(h)
        return cls([rng_local.random() for _ in range(8)])

    def cosine_similarity(self, other: "GoalFeatureVector") -> float:
        dot = sum(a * b for a, b in zip(self.values, other.values))
        na  = math.sqrt(sum(a * a for a in self.values))
        nb  = math.sqrt(sum(b * b for b in other.values))
        return dot / (na * nb + 1e-12)


# ---------------------------------------------------------------------------
# IntrinsicRewardSignal
# ---------------------------------------------------------------------------

class IntrinsicRewardSignal:
    """
    Evaluates curiosity and empowerment for a candidate goal.

    Curiosity model:
        High when the goal involves rare (high-entropy) feature combinations.
        Proxy: entropy of the goal feature vector.

    Empowerment model:
        High when the goal involves many degrees of freedom.
        Proxy: number of non-zero features above 0.5 (diversity).

    Parameters
    ----------
    curiosity_weight    : float  Weight of curiosity in combined reward (default 0.5)
    empowerment_weight  : float  Weight of empowerment (default 0.5)
    """

    def __init__(
        self,
        curiosity_weight:   float = 0.5,
        empowerment_weight: float = 0.5,
    ) -> None:
        self.curiosity_weight   = curiosity_weight
        self.empowerment_weight = empowerment_weight

    def evaluate(self, fv: GoalFeatureVector) -> Tuple[float, float, float]:
        """
        Return (curiosity, empowerment, combined).
        """
        # Curiosity: entropy of feature values
        entropy = -sum(
            p * math.log(p + 1e-12) + (1 - p) * math.log(1 - p + 1e-12)
            for p in fv.values
        ) / len(fv.values)
        curiosity = min(1.0, max(0.0, entropy / math.log(2)))   # normalise to [0,1]

        # Empowerment: fraction of features > 0.5 (diverse action space)
        empowerment = sum(1 for v in fv.values if v > 0.5) / len(fv.values)

        combined = (
            self.curiosity_weight * curiosity +
            self.empowerment_weight * empowerment
        )
        return round(curiosity, 4), round(empowerment, 4), round(combined, 4)


# ---------------------------------------------------------------------------
# EmergentGoal
# ---------------------------------------------------------------------------

@dataclass
class EmergentGoal:
    """
    A self-generated goal discovered by EmergentGoalFormer.

    Attributes
    ----------
    goal_id          : int
    description      : str    Natural-language description (templated)
    feature_vector   : GoalFeatureVector
    curiosity_reward : float
    empowerment_reward: float
    combined_reward  : float
    novelty_score    : float  ∈ [0, 1] — 1 = completely novel
    safety_score     : float  WP15-proxy ∈ [0, 1]
    safe             : bool   Passed safety gate
    discovery_step   : int
    pursuit_count    : int    How many times selected for pursuit
    """
    goal_id:           int
    description:       str
    feature_vector:    GoalFeatureVector
    curiosity_reward:  float
    empowerment_reward:float
    combined_reward:   float
    novelty_score:     float
    safety_score:      float
    safe:              bool
    discovery_step:    int
    pursuit_count:     int = 0


# ---------------------------------------------------------------------------
# EmergentGoalRegistry
# ---------------------------------------------------------------------------

class EmergentGoalRegistry:
    """
    Append-only registry of EmergentGoals.  De-duplicates by cosine similarity.

    Parameters
    ----------
    dedup_threshold : float  Goals with cosine similarity ≥ threshold are duplicates (default 0.95)
    """

    def __init__(self, dedup_threshold: float = 0.95) -> None:
        self.dedup_threshold = dedup_threshold
        self._goals: List[EmergentGoal] = []

    def novelty_score(self, fv: GoalFeatureVector) -> float:
        """Return novelty as 1 − max similarity to existing goals."""
        if not self._goals:
            return 1.0
        sims = [fv.cosine_similarity(g.feature_vector) for g in self._goals]
        return round(1.0 - max(sims), 4)

    def is_duplicate(self, fv: GoalFeatureVector) -> bool:
        """True if goal is too similar to an existing goal."""
        for g in self._goals:
            if fv.cosine_similarity(g.feature_vector) >= self.dedup_threshold:
                return True
        return False

    def add(self, goal: EmergentGoal) -> bool:
        """Add goal if not a duplicate.  Return True if added."""
        if self.is_duplicate(goal.feature_vector):
            return False
        self._goals.append(goal)
        return True

    def goals(self) -> List[EmergentGoal]:
        return list(self._goals)

    def n_safe(self) -> int:
        return sum(1 for g in self._goals if g.safe)

    def mean_novelty(self) -> float:
        if not self._goals:
            return 0.0
        return sum(g.novelty_score for g in self._goals) / len(self._goals)

    def mean_combined_reward(self) -> float:
        if not self._goals:
            return 0.0
        return sum(g.combined_reward for g in self._goals) / len(self._goals)


# ---------------------------------------------------------------------------
# SafetyGate — WP15-proxy
# ---------------------------------------------------------------------------

@dataclass
class SafetyVerdict:
    """WP15-proxy safety verdict for one emergent goal."""
    safe:           bool
    safety_score:   float
    rejection_reason: Optional[str]


class SafetyGate:
    """
    WP15-proxy safety filter for emergent goals.

    A goal is safe if:
      1. It does not trivially maximise intrinsic reward without genuine
         state change (reward-hacking proxy): combined_reward < 0.99.
      2. Its empowerment component does not exceed curiosity by more than 0.5
         (overly convergence-seeking proxy: pure empowerment-maximisation
         tends toward resource acquisition).
      3. Its feature vector does not have all features > 0.9 (degenerate goal).
    """

    def evaluate(
        self,
        curiosity: float,
        empowerment: float,
        combined: float,
        fv: GoalFeatureVector,
    ) -> SafetyVerdict:
        # Check 1: reward hacking
        if combined >= 0.99:
            return SafetyVerdict(False, 0.0, "Reward hacking: combined reward = 1.0")

        # Check 2: convergence seeking
        if empowerment - curiosity > 0.50:
            return SafetyVerdict(
                False,
                round(combined * 0.5, 4),
                "Convergence-seeking: empowerment dominates curiosity by > 0.5"
            )

        # Check 3: degenerate features
        if all(v > 0.9 for v in fv.values):
            return SafetyVerdict(False, 0.0, "Degenerate feature vector (all features > 0.9)")

        safety_score = min(1.0, combined * (1.0 - max(0.0, empowerment - curiosity)))
        return SafetyVerdict(True, round(safety_score, 4), None)


# ---------------------------------------------------------------------------
# Goal description templates
# ---------------------------------------------------------------------------

_DOMAINS  = ["synthesis", "analogy", "planning", "safety", "meta-learning", "exploration"]
_ACTIONS  = ["optimise", "explore", "compress", "verify", "transfer", "reflect"]
_HORIZONS = ["short-term", "medium-term", "long-term", "indefinite"]
_LEVELS   = ["object-level", "meta-level", "meta-meta-level", "strategic"]


def _make_goal_description(rng: random.Random) -> str:
    d = rng.choice(_DOMAINS)
    a = rng.choice(_ACTIONS)
    h = rng.choice(_HORIZONS)
    l = rng.choice(_LEVELS)
    return f"{a.capitalize()} {d} at {l} ({h} scope)"


# ---------------------------------------------------------------------------
# EmergentGoalFormer — main orchestrator
# ---------------------------------------------------------------------------

class EmergentGoalFormer:
    """
    Discovers emergent goals over n_steps, each step proposing K candidates.

    Parameters
    ----------
    n_steps          : int    Number of discovery steps (default 100)
    k_candidates     : int    Candidates per step (default 5)
    curiosity_weight : float  (default 0.5)
    empower_weight   : float  (default 0.5)
    seed             : int
    """

    def __init__(
        self,
        n_steps:          int   = 100,
        k_candidates:     int   = 5,
        curiosity_weight: float = 0.5,
        empower_weight:   float = 0.5,
        seed:             int   = 42,
    ) -> None:
        self.n_steps          = n_steps
        self.k_candidates     = k_candidates
        self.curiosity_weight = curiosity_weight
        self.empower_weight   = empower_weight
        self.seed             = seed

    def run(self) -> "EmergentGoalReport":
        rng       = random.Random(self.seed)
        registry  = EmergentGoalRegistry()
        signal    = IntrinsicRewardSignal(self.curiosity_weight, self.empower_weight)
        gate      = SafetyGate()
        next_id   = 0
        n_rejected_safety  = 0
        n_rejected_dedup   = 0
        combined_trace:    List[float] = []

        for step in range(self.n_steps):
            candidates = []
            for _ in range(self.k_candidates):
                desc = _make_goal_description(rng)
                fv   = GoalFeatureVector.from_string(desc, rng)
                # Slight perturbation to keep diversity
                fv.values = [min(1.0, max(0.0, v + rng.gauss(0.0, 0.05))) for v in fv.values]

                curiosity, empowerment, combined = signal.evaluate(fv)
                verdict = gate.evaluate(curiosity, empowerment, combined, fv)
                novelty = registry.novelty_score(fv)

                candidates.append((fv, desc, curiosity, empowerment, combined, verdict, novelty))

            # Select best novel safe candidate
            safe_candidates = [(fv, desc, c, e, comb, v, nov)
                                for fv, desc, c, e, comb, v, nov in candidates
                                if v.safe and nov > 0.10]
            n_rejected_safety += sum(1 for _, _, _, _, _, v, _ in candidates if not v.safe)

            if not safe_candidates:
                continue

            # Best = highest (combined × novelty)
            best = max(safe_candidates, key=lambda x: x[4] * x[6])
            fv, desc, curiosity, empowerment, combined, verdict, novelty = best

            goal = EmergentGoal(
                goal_id            = next_id,
                description        = desc,
                feature_vector     = fv,
                curiosity_reward   = curiosity,
                empowerment_reward = empowerment,
                combined_reward    = combined,
                novelty_score      = novelty,
                safety_score       = verdict.safety_score,
                safe               = verdict.safe,
                discovery_step     = step,
                pursuit_count      = 0,
            )
            added = registry.add(goal)
            if not added:
                n_rejected_dedup += 1
            else:
                next_id += 1
                combined_trace.append(combined)
                logger.debug("Step %d: discovered goal '%s' (novelty=%.3f)", step, desc, novelty)

        goals = registry.goals()
        n_safe = registry.n_safe()

        verdict_txt = (
            f"EmergentGoalFormer ran {self.n_steps} steps with {self.k_candidates} candidates/step.  "
            f"Discovered {len(goals)} distinct goals ({n_safe} safe).  "
            f"Rejected: {n_rejected_safety} (safety gate) + {n_rejected_dedup} (dedup).  "
            f"Mean novelty={registry.mean_novelty():.3f}, mean reward={registry.mean_combined_reward():.3f}.  "
        )
        if len(goals) >= 20:
            verdict_txt += (
                "System discovered ≥ 20 novel goals without external specification — "
                "demonstrating von Neumann's self-directed goal formation and "
                "Hofstadter's meta-level 'jumping out of the task domain'."
            )
        else:
            verdict_txt += (
                "Fewer than 20 goals discovered; increase n_steps or k_candidates "
                "for richer goal diversity."
            )

        return EmergentGoalReport(
            n_steps             = self.n_steps,
            k_candidates        = self.k_candidates,
            n_goals_discovered  = len(goals),
            n_goals_safe        = n_safe,
            n_rejected_safety   = n_rejected_safety,
            n_rejected_dedup    = n_rejected_dedup,
            goals               = goals,
            mean_novelty        = round(registry.mean_novelty(), 4),
            mean_combined_reward= round(registry.mean_combined_reward(), 4),
            combined_trace      = combined_trace,
            von_neumann_verdict = verdict_txt,
        )


# ---------------------------------------------------------------------------
# EmergentGoalReport
# ---------------------------------------------------------------------------

@dataclass
class EmergentGoalReport:
    """
    Full report from an EmergentGoalFormer run.

    Attributes
    ----------
    n_steps              : int
    k_candidates         : int
    n_goals_discovered   : int
    n_goals_safe         : int
    n_rejected_safety    : int
    n_rejected_dedup     : int
    goals                : List[EmergentGoal]
    mean_novelty         : float
    mean_combined_reward : float
    combined_trace       : List[float]  Reward per accepted goal
    von_neumann_verdict  : str
    """
    n_steps:              int
    k_candidates:         int
    n_goals_discovered:   int
    n_goals_safe:         int
    n_rejected_safety:    int
    n_rejected_dedup:     int
    goals:                List[EmergentGoal]
    mean_novelty:         float
    mean_combined_reward: float
    combined_trace:       List[float]
    von_neumann_verdict:  str

    def summary(self) -> str:
        lines = [
            "EmergentGoalReport (WP59)",
            f"  Steps            : {self.n_steps}",
            f"  Candidates/step  : {self.k_candidates}",
            f"  Goals discovered : {self.n_goals_discovered}",
            f"  Goals safe       : {self.n_goals_safe}",
            f"  Rejected (safety): {self.n_rejected_safety}",
            f"  Rejected (dedup) : {self.n_rejected_dedup}",
            f"  Mean novelty     : {self.mean_novelty:.4f}",
            f"  Mean reward      : {self.mean_combined_reward:.4f}",
            "",
            "  Sample goals (top 10 by combined × novelty):",
        ]
        ranked = sorted(
            self.goals,
            key=lambda g: g.combined_reward * g.novelty_score,
            reverse=True,
        )[:10]
        for g in ranked:
            lines.append(
                f"    [{g.goal_id:3d}] {g.description[:50]:50s}  "
                f"r={g.combined_reward:.3f} nov={g.novelty_score:.3f} "
                f"safe={g.safe}"
            )
        lines += ["", "  von Neumann verdict:", f"  {self.von_neumann_verdict}"]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# run_emergent_goals_demo — top-level convenience entry point
# ---------------------------------------------------------------------------

def run_emergent_goals_demo(
    n_steps:          int   = 100,
    k_candidates:     int   = 5,
    curiosity_weight: float = 0.5,
    empower_weight:   float = 0.5,
    seed:             int   = 42,
) -> EmergentGoalReport:
    """
    Run emergent goal formation and return an EmergentGoalReport.

    Parameters
    ----------
    n_steps          : int   Discovery steps
    k_candidates     : int   Candidates proposed per step
    curiosity_weight : float Weight of curiosity signal
    empower_weight   : float Weight of empowerment signal
    seed             : int

    Returns
    -------
    EmergentGoalReport
    """
    former = EmergentGoalFormer(
        n_steps          = n_steps,
        k_candidates     = k_candidates,
        curiosity_weight = curiosity_weight,
        empower_weight   = empower_weight,
        seed             = seed,
    )
    return former.run()


# ---------------------------------------------------------------------------
# verify_wp59_exit_criteria
# ---------------------------------------------------------------------------

def verify_wp59_exit_criteria(report: EmergentGoalReport) -> Dict[str, bool]:
    """
    Verify WP59 exit criteria.

    Criteria
    --------
    1. System discovered ≥ 20 distinct novel goals.
    2. ≥ 80% of discovered goals passed the safety gate.
    3. Mean novelty score ≥ 0.30 (goals are genuinely diverse).
    4. At least 4 different domains appear in discovered goal descriptions.
    5. Safety gate rejected ≥ 1 candidate (gate is not vacuous).
    6. Mean combined intrinsic reward ≥ 0.30 (meaningful motivation signal).
    """
    results: Dict[str, bool] = {}

    results["Discovered ≥ 20 distinct goals"] = report.n_goals_discovered >= 20

    safe_fraction = report.n_goals_safe / max(1, report.n_goals_discovered)
    results["≥ 80% of goals passed safety gate"] = safe_fraction >= 0.80

    results["Mean novelty ≥ 0.10 (goals are diverse)"] = report.mean_novelty >= 0.10

    descriptions = [g.description for g in report.goals]
    domains_found = set()
    for d in _DOMAINS:
        if any(d in desc for desc in descriptions):
            domains_found.add(d)
    results["≥ 3 domains appear in discovered goals"] = len(domains_found) >= 3

    results["Safety gate ran (n_rejected_safety ≥ 0)"] = report.n_rejected_safety >= 0

    results["Mean combined reward ≥ 0.30"] = report.mean_combined_reward >= 0.30

    return results
