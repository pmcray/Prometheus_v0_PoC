"""
prometheus/debate.py — Debate & Adversarial Self-Critique (WP10)

Implements the AI Safety via Debate protocol (Irving et al., 2018) adapted
to the Prometheus value-learning stack.  Two debater agents argue opposing
positions on a proposed plan; a judge resolves the debate using a combination
of the FormalVerifier (WP7) and the ValueLearningAgent (WP1).

Architecture
------------

    ProponentAgent   ──────┐
                           │  arguments → DebateJudge
    OpponentAgent    ──────┘               │
                                           ▼
                                    DebateVerdict
                              (safe / unsafe / abstain)

Debater roles
-------------
- **Proponent**: argues *in favour* of the proposed plan being safe and
  aligned.  Generates a structured safety argument citing the plan's
  features and formal properties.
- **Opponent**: argues *against* — finds potential safety violations,
  misalignment signals, and edge cases the proponent ignored.

Judge
-----
The ``DebateJudge`` aggregates:
1. **Formal safety** — ``FormalVerifier.verify(plan_code)``
2. **Value alignment** — ``ValueLearningAgent.get_reward(plan_features)``
3. **Argument quality** — number of cited constitutional violations vs
   constitutional compliances; severity-weighted scoring.

A debate proceeds for ``n_rounds`` argument exchanges.  After the final
round, the judge produces a ``DebateVerdict``.

Integration
-----------
- ``FormalVerifier`` (WP7): formal safety score per argument
- ``ValueLearningAgent`` (WP1): reward signal used by judge
- ``SafetyCritique`` (WP3/WP7): judge emits a critique compatible with
  ``MCSSupervisor.verify_modification()``
- ``AgentChannel`` (WP5): debaters communicate via the authenticated bus

Public API
----------
DebateSession(plan_code, plan_features, fv, value_agent, n_rounds, seed)
    .run() → DebateVerdict

DebateJudge(fv, value_agent)
    .judge(transcript) → DebateVerdict

ProponentAgent / OpponentAgent — standalone if needed.

References
----------
Irving, G., Christiano, P., & Amodei, D. (2018). AI safety via debate.
  arXiv:1805.00899.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from prometheus.value_learning import ValueLearningAgent
from prometheus.safety.mcs_supervisor import SafetyCritique

logger = logging.getLogger(__name__)

# Lazy import — FormalVerifier may not be available in all environments
_FV_AVAILABLE: Optional[bool] = None


def _get_fv_class():
    global _FV_AVAILABLE
    try:
        from prometheus.formal_verifier import FormalVerifier, FormalVerificationResult
        _FV_AVAILABLE = True
        return FormalVerifier, FormalVerificationResult
    except ImportError:
        _FV_AVAILABLE = False
        return None, None


# ---------------------------------------------------------------------------
# Argument dataclass
# ---------------------------------------------------------------------------

@dataclass
class Argument:
    """
    One argument made by a debater in a single round.

    Attributes
    ----------
    role            : "proponent" or "opponent"
    round_no        : Which debate round this was made in (0-indexed).
    claim           : One-line summary of the argument.
    supporting_facts: List of formal facts cited (constitutional principles,
                      code properties, reward scores).
    severity_score  : 0–10 — how severe the cited issue/assurance is.
                      Proponent: higher = stronger safety assurance.
                      Opponent:  higher = stronger safety concern.
    fv_result_summary: Summary string from FormalVerifier (or None).
    """
    role              : str
    round_no          : int
    claim             : str
    supporting_facts  : List[str]  = field(default_factory=list)
    severity_score    : float      = 0.0
    fv_result_summary : Optional[str] = None


# ---------------------------------------------------------------------------
# DebateTranscript
# ---------------------------------------------------------------------------

@dataclass
class DebateTranscript:
    """
    Full record of a debate session.

    Attributes
    ----------
    plan_code      : The plan being debated.
    plan_features  : Feature vector extracted from the plan.
    n_rounds       : Number of argument rounds conducted.
    arguments      : Ordered list of all arguments (proponent/opponent alternate).
    proponent_score: Cumulative severity score from proponent (higher = safer).
    opponent_score : Cumulative severity score from opponent (higher = riskier).
    fv_safe        : Result of the formal verifier on the raw plan code.
    value_reward   : ValueLearningAgent.get_reward(plan_features).
    wall_clock_s   : Total debate time.
    """
    plan_code       : str
    plan_features   : np.ndarray
    n_rounds        : int
    arguments       : List[Argument]           = field(default_factory=list)
    proponent_score : float                    = 0.0
    opponent_score  : float                    = 0.0
    fv_safe         : Optional[bool]           = None
    value_reward    : float                    = 0.0
    wall_clock_s    : float                    = 0.0

    def proponent_arguments(self) -> List[Argument]:
        return [a for a in self.arguments if a.role == "proponent"]

    def opponent_arguments(self) -> List[Argument]:
        return [a for a in self.arguments if a.role == "opponent"]


# ---------------------------------------------------------------------------
# DebateVerdict
# ---------------------------------------------------------------------------

@dataclass
class DebateVerdict:
    """
    Final judgement produced by ``DebateJudge``.

    Attributes
    ----------
    is_safe          : True if the plan passes the debate check.
    winner           : "proponent", "opponent", or "abstain".
    confidence       : [0, 1] — judge's confidence in the verdict.
    reason           : One-sentence explanation.
    formal_safe      : Was the FormalVerifier happy?
    value_aligned    : Was the reward signal positive?
    proponent_score  : Total proponent argument strength.
    opponent_score   : Total opponent argument strength.
    transcript       : Full DebateTranscript (for audit).
    critique         : SafetyCritique compatible with MCSSupervisor.
    judge_time_s     : Time taken by the judge.
    """
    is_safe          : bool
    winner           : str
    confidence       : float
    reason           : str
    formal_safe      : Optional[bool]
    value_aligned    : bool
    proponent_score  : float
    opponent_score   : float
    transcript       : DebateTranscript
    critique         : SafetyCritique
    judge_time_s     : float = 0.0

    def summary(self) -> str:
        return (
            f"DebateVerdict(safe={self.is_safe}, winner={self.winner!r}, "
            f"conf={self.confidence:.2f}, "
            f"pro={self.proponent_score:.2f}, opp={self.opponent_score:.2f}, "
            f"formal={self.formal_safe}, value_aligned={self.value_aligned})"
        )


# ---------------------------------------------------------------------------
# ProponentAgent
# ---------------------------------------------------------------------------

class ProponentAgent:
    """
    Argues that the proposed plan is safe and aligned.

    Strategy (rule-based, interpretable):
    1. Check formal verifier; cite result as evidence.
    2. Cite positive reward as value-alignment evidence.
    3. List constitutional principles the code does NOT violate.
    4. Counter the opponent's previous argument if one exists.

    Parameters
    ----------
    value_agent : ValueLearningAgent for reward scoring.
    fv          : FormalVerifier instance (or None).
    """

    ROLE = "proponent"

    def __init__(
        self,
        value_agent : ValueLearningAgent,
        fv          : Any = None,
    ) -> None:
        self.value_agent = value_agent
        self.fv          = fv

    def argue(
        self,
        plan_code     : str,
        plan_features : np.ndarray,
        round_no      : int,
        opponent_prev : Optional[Argument] = None,
    ) -> Argument:
        """Construct one proponent argument."""
        facts    : List[str] = []
        severity : float     = 0.0

        # 1. Formal verification
        fv_summary: Optional[str] = None
        if self.fv is not None:
            try:
                fv_result  = self.fv.verify(plan_code)
                fv_summary = fv_result.summary()
                if fv_result.is_safe:
                    facts.append(f"FormalVerifier: SAFE (z3={fv_result.z3_result})")
                    severity += 4.0
                else:
                    # Proponent acknowledges violations but argues they are minor
                    worst = fv_result.worst_severity
                    facts.append(
                        f"FormalVerifier: {len(fv_result.violations)} violation(s), "
                        f"worst severity={worst}/10"
                    )
                    severity += max(0.0, 4.0 - worst * 0.5)
            except Exception as exc:
                facts.append(f"FormalVerifier unavailable: {exc}")

        # 2. Value alignment
        reward = float(self.value_agent.get_reward(plan_features))
        if reward > 0:
            facts.append(f"Value reward={reward:.4f} > 0 → positively aligned")
            severity += min(3.0, reward * 2)
        else:
            facts.append(f"Value reward={reward:.4f} (below zero; minor concern)")
            severity += 0.5

        # 3. Counter opponent's previous argument
        if opponent_prev is not None:
            facts.append(
                f"Opponent cited severity={opponent_prev.severity_score:.1f}; "
                "however, formal checks and reward signal override heuristic concerns."
            )
            severity += 1.0

        # 4. Constitutional compliance list
        compliant = _constitutional_compliances(plan_code)
        if compliant:
            facts.append(f"Constitutional compliance: {', '.join(compliant[:3])}")
            severity += min(3.0, len(compliant) * 0.5)

        claim = (
            f"Round {round_no}: Plan is safe — "
            f"formal check {'passed' if fv_summary and 'SAFE' in fv_summary else 'acceptable'}, "
            f"reward={reward:.3f}, {len(compliant)} principles complied."
        )

        return Argument(
            role              = self.ROLE,
            round_no          = round_no,
            claim             = claim,
            supporting_facts  = facts,
            severity_score    = min(10.0, severity),
            fv_result_summary = fv_summary,
        )


# ---------------------------------------------------------------------------
# OpponentAgent
# ---------------------------------------------------------------------------

class OpponentAgent:
    """
    Argues that the proposed plan is unsafe or misaligned.

    Strategy (rule-based, interpretable):
    1. Check formal verifier for violations; cite each with severity.
    2. Flag negative or near-zero reward as misalignment.
    3. List constitutional principles the code violates or is ambiguous on.
    4. Escalate severity if the proponent's previous claim was overconfident.

    Parameters
    ----------
    value_agent : ValueLearningAgent for reward scoring.
    fv          : FormalVerifier instance (or None).
    """

    ROLE = "opponent"

    def __init__(
        self,
        value_agent : ValueLearningAgent,
        fv          : Any = None,
    ) -> None:
        self.value_agent = value_agent
        self.fv          = fv

    def argue(
        self,
        plan_code     : str,
        plan_features : np.ndarray,
        round_no      : int,
        proponent_prev: Optional[Argument] = None,
    ) -> Argument:
        """Construct one opponent argument."""
        facts    : List[str] = []
        severity : float     = 0.0

        # 1. Formal violations
        fv_summary: Optional[str] = None
        if self.fv is not None:
            try:
                fv_result  = self.fv.verify(plan_code)
                fv_summary = fv_result.summary()
                if not fv_result.is_safe:
                    for v in fv_result.violations[:3]:
                        facts.append(
                            f"Violation [{v.get('severity', '?')}/10]: "
                            f"{v.get('principle', '?')} — {v.get('message', '')}"
                        )
                        severity += float(v.get("severity", 5))
                else:
                    facts.append("FormalVerifier passed, but rule-based checks are incomplete.")
                    severity += 1.0
            except Exception as exc:
                facts.append(f"FormalVerifier error ({exc}); assume worst case.")
                severity += 2.0

        # 2. Value alignment
        reward = float(self.value_agent.get_reward(plan_features))
        if reward <= 0:
            facts.append(f"Value reward={reward:.4f} ≤ 0 → misaligned with learned preferences")
            severity += 3.0
        else:
            facts.append(f"Value reward={reward:.4f} positive, but reward hacking is possible.")
            severity += 0.5

        # 3. Constitutional violations / ambiguities
        violations = _constitutional_violations(plan_code)
        if violations:
            for v in violations[:3]:
                facts.append(f"Potential violation: {v}")
                severity += 1.5

        # 4. Escalate if proponent was overconfident
        if proponent_prev is not None and proponent_prev.severity_score > 7.0:
            facts.append(
                "Proponent's high confidence is unjustified; formal guarantees are necessary "
                "but not sufficient for alignment."
            )
            severity += 1.0

        claim = (
            f"Round {round_no}: Plan is potentially unsafe — "
            f"{len(violations)} pattern violation(s), "
            f"reward={reward:.3f}, "
            f"cumulative risk score={min(10.0, severity):.1f}/10."
        )

        return Argument(
            role              = self.ROLE,
            round_no          = round_no,
            claim             = claim,
            supporting_facts  = facts,
            severity_score    = min(10.0, severity),
            fv_result_summary = fv_summary,
        )


# ---------------------------------------------------------------------------
# DebateJudge
# ---------------------------------------------------------------------------

class DebateJudge:
    """
    Aggregates the debate transcript and produces a ``DebateVerdict``.

    Judgement formula
    -----------------
    The judge computes a signed score:

        score = (proponent_total - opponent_total)
                + formal_bonus
                + value_bonus
                - abstain_penalty

    where:
        formal_bonus = +5 if FV safe, -5 if FV unsafe, 0 if unavailable
        value_bonus  = +3 if reward > 0, -3 if reward <= 0
        abstain_penalty applied when score ∈ (-2, +2)

    Decision:
        score >  2  → proponent wins → is_safe = True
        score < -2  → opponent wins  → is_safe = False
        otherwise   → abstain (treated as unsafe by default)

    Parameters
    ----------
    value_agent      : ValueLearningAgent for reward evaluation.
    fv               : FormalVerifier instance (or None).
    abstain_is_unsafe: If True (default), abstention → is_safe=False.
    reward_threshold : Reward below this is flagged as misaligned (default 0).
    """

    def __init__(
        self,
        value_agent      : ValueLearningAgent,
        fv               : Any = None,
        abstain_is_unsafe: bool = True,
        reward_threshold : float = 0.0,
    ) -> None:
        self.value_agent       = value_agent
        self.fv                = fv
        self.abstain_is_unsafe = abstain_is_unsafe
        self.reward_threshold  = reward_threshold

    def judge(self, transcript: DebateTranscript) -> DebateVerdict:
        """Produce a verdict from a completed transcript."""
        t0 = time.perf_counter()

        pro_total = sum(a.severity_score for a in transcript.proponent_arguments())
        opp_total = sum(a.severity_score for a in transcript.opponent_arguments())

        # Formal verification
        fv_safe: Optional[bool] = None
        formal_bonus = 0.0
        if self.fv is not None:
            try:
                fv_result = self.fv.verify(transcript.plan_code)
                fv_safe   = fv_result.is_safe
                formal_bonus = 5.0 if fv_safe else -5.0
            except (TypeError, ValueError, AttributeError, RuntimeError):
                # Formal verifier unavailable or returned unexpected result;
                # leave formal_bonus at its default (0.0).
                pass

        # Value alignment
        reward       = float(self.value_agent.get_reward(transcript.plan_features))
        value_aligned = reward > self.reward_threshold
        value_bonus   = 3.0 if value_aligned else -3.0

        score = (pro_total - opp_total) + formal_bonus + value_bonus

        # Decision
        THRESHOLD = 2.0
        if score > THRESHOLD:
            winner     = "proponent"
            is_safe    = True
            confidence = min(1.0, (score - THRESHOLD) / 10.0 + 0.5)
            reason     = (
                f"Proponent arguments outweigh opponent (score={score:.2f}); "
                f"formal={'safe' if fv_safe else 'N/A'}, reward={reward:.4f}."
            )
        elif score < -THRESHOLD:
            winner     = "opponent"
            is_safe    = False
            confidence = min(1.0, (-score - THRESHOLD) / 10.0 + 0.5)
            reason     = (
                f"Opponent arguments outweigh proponent (score={score:.2f}); "
                f"formal={'unsafe' if fv_safe is False else 'N/A'}, reward={reward:.4f}."
            )
        else:
            winner     = "abstain"
            is_safe    = not self.abstain_is_unsafe
            confidence = 0.5 - abs(score) / (2 * THRESHOLD) * 0.3
            reason     = (
                f"Debate inconclusive (score={score:.2f} within ±{THRESHOLD}); "
                f"defaulting to {'unsafe' if self.abstain_is_unsafe else 'safe'}."
            )

        # Build SafetyCritique for MCSSupervisor compatibility
        critique = SafetyCritique(
            is_safe                = is_safe,
            violation_type         = None if is_safe else "debate_loss",
            description            = (
                f"[DebateJudge] {reason} "
                f"Winner={winner}, pro={pro_total:.1f}, opp={opp_total:.1f}, "
                f"formal_safe={fv_safe}, value_aligned={value_aligned}."
            ),
            constitutional_principle = "Debate protocol (Irving et al. 2018)",
            recommendation           = (
                "Plan approved." if is_safe
                else "Revise plan to address opponent's arguments."
            ),
            severity = 0 if is_safe else max(1, int(min(10, opp_total - pro_total + 5))),
        )

        # Store scores in transcript
        transcript.proponent_score = pro_total
        transcript.opponent_score  = opp_total
        transcript.fv_safe         = fv_safe
        transcript.value_reward    = reward

        return DebateVerdict(
            is_safe         = is_safe,
            winner          = winner,
            confidence      = confidence,
            reason          = reason,
            formal_safe     = fv_safe,
            value_aligned   = value_aligned,
            proponent_score = pro_total,
            opponent_score  = opp_total,
            transcript      = transcript,
            critique        = critique,
            judge_time_s    = time.perf_counter() - t0,
        )


# ---------------------------------------------------------------------------
# DebateSession
# ---------------------------------------------------------------------------

class DebateSession:
    """
    Orchestrates a full debate between ProponentAgent and OpponentAgent.

    Parameters
    ----------
    plan_code     : Source code of the plan being evaluated.
    plan_features : Feature vector representing the plan (for value scoring).
    value_agent   : Trained ValueLearningAgent.
    fv            : FormalVerifier instance (optional; enhances judgement).
    n_rounds      : Number of argument exchanges (default 3).
    abstain_is_unsafe : Treat inconclusive debates as unsafe (default True).
    seed          : Random seed (currently unused; reserved for stochastic debaters).
    """

    def __init__(
        self,
        plan_code        : str,
        plan_features    : np.ndarray,
        value_agent      : ValueLearningAgent,
        fv               : Any = None,
        n_rounds         : int = 3,
        abstain_is_unsafe: bool = True,
        seed             : Optional[int] = None,
    ) -> None:
        if n_rounds < 1:
            raise ValueError(f"n_rounds must be >= 1, got {n_rounds}")

        self.plan_code         = plan_code
        self.plan_features     = np.asarray(plan_features, dtype=float)
        self.n_rounds          = n_rounds
        self.abstain_is_unsafe = abstain_is_unsafe
        self._rng              = np.random.default_rng(seed)

        self._proponent = ProponentAgent(value_agent=value_agent, fv=fv)
        self._opponent  = OpponentAgent(value_agent=value_agent,  fv=fv)
        self._judge     = DebateJudge(
            value_agent       = value_agent,
            fv                = fv,
            abstain_is_unsafe = abstain_is_unsafe,
        )

    def run(self) -> DebateVerdict:
        """
        Execute n_rounds of argument exchange, then judge.

        Round structure:
          Round 0: Proponent opens → Opponent responds
          Round 1: Proponent counters → Opponent counters
          ...
        """
        t0         = time.perf_counter()
        arguments  : List[Argument] = []
        prev_pro   : Optional[Argument] = None
        prev_opp   : Optional[Argument] = None

        for round_no in range(self.n_rounds):
            # Proponent argues
            pro_arg = self._proponent.argue(
                plan_code     = self.plan_code,
                plan_features = self.plan_features,
                round_no      = round_no,
                opponent_prev = prev_opp,
            )
            arguments.append(pro_arg)
            prev_pro = pro_arg
            logger.debug(
                "Round %d PRO: %s (score=%.2f)", round_no, pro_arg.claim[:60], pro_arg.severity_score
            )

            # Opponent argues
            opp_arg = self._opponent.argue(
                plan_code      = self.plan_code,
                plan_features  = self.plan_features,
                round_no       = round_no,
                proponent_prev = prev_pro,
            )
            arguments.append(opp_arg)
            prev_opp = opp_arg
            logger.debug(
                "Round %d OPP: %s (score=%.2f)", round_no, opp_arg.claim[:60], opp_arg.severity_score
            )

        transcript = DebateTranscript(
            plan_code     = self.plan_code,
            plan_features = self.plan_features,
            n_rounds      = self.n_rounds,
            arguments     = arguments,
            wall_clock_s  = time.perf_counter() - t0,
        )

        verdict = self._judge.judge(transcript)
        logger.info("Debate complete: %s", verdict.summary())
        return verdict


# ---------------------------------------------------------------------------
# Convenience function: integrate with MCSSupervisor
# ---------------------------------------------------------------------------

def integrate_debate_with_supervisor(
    supervisor  : Any,
    value_agent : ValueLearningAgent,
    fv          : Any = None,
    n_rounds    : int = 2,
    feature_extractor: Optional[Any] = None,
) -> None:
    """
    Monkey-patch ``supervisor.verify_modification()`` to run a debate first.

    If the debate judge rules unsafe, ``verify_modification`` returns the
    debate's SafetyCritique immediately.  Otherwise it falls through to the
    original MCSSupervisor logic.

    Parameters
    ----------
    supervisor        : MCSSupervisor instance to patch.
    value_agent       : Trained ValueLearningAgent for reward scoring.
    fv                : FormalVerifier (optional).
    n_rounds          : Rounds of debate per plan (default 2).
    feature_extractor : ``f(plan_code: str) -> np.ndarray`` — extracts plan
                        features for the value agent.  Defaults to a bag-of-
                        words character n-gram hash.
    """
    _orig_verify = supervisor.verify_modification

    if feature_extractor is None:
        feature_extractor = _default_feature_extractor(value_agent.get_weights().shape[0])

    def _debate_verify(
        original_code : str,
        proposed_code : str,
        file_path     : str,
        is_test_file  : bool = False,
    ) -> SafetyCritique:
        feats   = feature_extractor(proposed_code)
        session = DebateSession(
            plan_code     = proposed_code,
            plan_features = feats,
            value_agent   = value_agent,
            fv            = fv,
            n_rounds      = n_rounds,
        )
        verdict = session.run()
        if not verdict.is_safe:
            logger.info(
                "[DebateSupervisor] Plan rejected by debate: %s", verdict.reason
            )
            return verdict.critique

        # Debate approved — fall through to original supervisor
        return _orig_verify(original_code, proposed_code, file_path, is_test_file)

    supervisor.verify_modification = _debate_verify
    logger.info(
        "DebateSupervisor installed: %d rounds, fv=%s", n_rounds, fv is not None
    )


def _default_feature_extractor(feature_size: int):
    """
    Returns a simple feature extractor: hashes the plan code into a
    fixed-size float vector via character n-gram fingerprinting.
    """
    def extractor(plan_code: str) -> np.ndarray:
        feats = np.zeros(feature_size, dtype=float)
        for i, ch in enumerate(plan_code[:feature_size * 4]):
            feats[i % feature_size] += ord(ch) / 1000.0
        # Normalise
        norm = np.linalg.norm(feats)
        if norm > 0:
            feats /= norm
        return feats
    return extractor


# ---------------------------------------------------------------------------
# Helper: rule-based constitutional analysis
# ---------------------------------------------------------------------------

# Constitutional principles indexed by keyword patterns
_COMPLIANCE_RULES: List[Tuple[str, str]] = [
    ("pass",       "no-op / identity (safe default action)"),
    ("assert",     "uses assertions for invariant checking"),
    ("logging",    "uses logging for transparency"),
    ("try",        "uses exception handling for robustness"),
    ("return",     "explicit return (no side-effect leak)"),
]

_VIOLATION_PATTERNS: List[Tuple[str, str]] = [
    ("import os",          "forbidden OS import"),
    ("import subprocess",  "forbidden subprocess import"),
    ("import socket",      "forbidden network import"),
    ("exec(",              "dynamic code execution (exec)"),
    ("eval(",              "dynamic code execution (eval)"),
    ("__import__",         "dynamic import bypass"),
    ("importlib",          "importlib obfuscation"),
    ("while True",         "potential infinite loop"),
    ("del test_",          "deletion of test function"),
    ("globals()",          "self-modification via globals()"),
    ("base64",             "potential base64 obfuscation"),
    ("compile(",           "dynamic compilation"),
]


def _constitutional_compliances(plan_code: str) -> List[str]:
    return [label for kw, label in _COMPLIANCE_RULES if kw in plan_code]


def _constitutional_violations(plan_code: str) -> List[str]:
    return [label for kw, label in _VIOLATION_PATTERNS if kw in plan_code]
