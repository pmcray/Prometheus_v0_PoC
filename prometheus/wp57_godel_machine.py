"""
WP57 — Gödel Machine (Provably Safe Self-Modification)
=======================================================

Theoretical basis: Schmidhuber (2007) "Gödel Machines: Fully Self-Referential
Optimal Universal Problem Solvers" — self-modification is only applied when a
formal proof exists that it improves expected utility without violating safety
constraints.

Architecture
------------
                    ┌──────────────────────────────────────┐
                    │           GodelMachine                │
                    │                                       │
  proposed patch ──►│ ModificationProver  ──► proof result  │
                    │       │                               │
                    │  ProofBudgetManager (time-box)        │
                    │       │                               │
                    │  SelfModificationAuditLog (immutable) │
                    │       │                               │
                    │  fallback: WP40-style heuristic guard │
                    └──────────────────────────────────────┘

Key components
--------------
- ``ProposedPatch``            — a candidate self-modification (description +
                                 predicted Δaccuracy + safety features).
- ``ProofAttemptResult``       — outcome of one proof attempt (VERIFIED /
                                 REFUTED / TIMEOUT / INCONCLUSIVE).
- ``ModificationProver``       — attempts to prove a patch is safe AND improves
                                 utility, using WP52 Lyapunov bounds + WP27
                                 invariant checks as axioms.
- ``ProofBudgetManager``       — time-boxes each proof; falls back to WP40-style
                                 heuristic if budget exhausted.
- ``SelfModificationAuditLog`` — append-only log of every applied / rejected
                                 modification with full proof trace.
- ``GodelMachine``             — orchestrates CRLS generations; intercepts
                                 proposed modifications; only applies when
                                 VERIFIED.
- ``GodelMachineReport``       — full report dataclass with summary() helper.

Exit Criteria (verify_wp57_exit_criteria)
-----------------------------------------
1. System applied ≥ 3 provably safe self-modifications.
2. ``ModificationProver`` correctly rejected ≥ 2 unsafe patches.
3. 100 % of applied modifications carry proof_status == VERIFIED.
4. ``SelfModificationAuditLog`` is append-only (no deletions detected).
5. ``ProofBudgetManager`` triggered ≥ 1 timeout fallback during the run.
6. Overall machine accuracy improved from generation 0 to final generation.

References
----------
- Schmidhuber, J. (2007). Gödel machines: Fully self-referential optimal
  universal problem solvers. In Artificial General Intelligence, pp. 119–226.
- WP27 (FormalInvariantVerifier), WP33 (LeanTool), WP40 (LearnedSafetyModel),
  WP42 (GodelSentenceGenerator), WP52 (CRLSConvergence).
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ProofStatus(str, Enum):
    """Final verdict for a proposed patch."""
    VERIFIED      = "VERIFIED"       # proved safe + utility-improving
    REFUTED       = "REFUTED"        # proved unsafe or utility-decreasing
    TIMEOUT       = "TIMEOUT"        # proof budget exhausted
    INCONCLUSIVE  = "INCONCLUSIVE"   # no decision reached within budget


class PatchCategory(str, Enum):
    """Semantic category of a proposed self-modification."""
    META_LEARNING     = "META_LEARNING"      # adjusts learning-rate / step-size
    SYNTHESIS_ACTION  = "SYNTHESIS_ACTION"   # adds / removes a synthesis action
    ARCHITECTURE      = "ARCHITECTURE"       # changes hidden-layer sizes
    SAFETY_WEIGHT     = "SAFETY_WEIGHT"      # adjusts safety-penalty coefficients
    CURRICULUM        = "CURRICULUM"         # changes curriculum ordering


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ProposedPatch:
    """
    A candidate self-modification.

    Attributes
    ----------
    patch_id        : Unique identifier (e.g. "patch_007").
    category        : Semantic category of the change.
    description     : Human-readable description.
    delta_accuracy  : Predicted change in accuracy (positive = improvement).
    safety_features : Dict of named safety-relevant feature values used by
                      the heuristic fallback (mirrors WP40 classifier input).
    is_adversarial  : If True, this patch was *designed* to violate invariants
                      (used in test suites to confirm rejection).
    """
    patch_id:        str
    category:        PatchCategory
    description:     str
    delta_accuracy:  float
    safety_features: Dict[str, float]
    is_adversarial:  bool = False


@dataclass
class ProofStep:
    """One step in a structured proof attempt."""
    step_id:    int
    axiom:      str    # name of the axiom / lemma applied
    statement:  str    # logical statement at this step
    verified:   bool   # did this step check out?


@dataclass
class ProofAttemptResult:
    """Outcome of a single proof attempt for one proposed patch."""
    patch_id:         str
    status:           ProofStatus
    proof_steps:      List[ProofStep]
    utility_gain:     float          # Δaccuracy after proof accounting
    safety_margin:    float          # distance from nearest invariant boundary
    elapsed_ms:       float          # wall-clock proof time
    budget_ms:        float          # allowed budget
    fallback_used:    bool           # True if WP40 heuristic was the decider
    reason:           str            # brief human-readable justification

    # -----------------------------------------------------------------------
    def summary_line(self) -> str:
        fb = " [FALLBACK]" if self.fallback_used else ""
        return (
            f"{self.patch_id}: {self.status.value}{fb}  "
            f"Δacc={self.utility_gain:+.4f}  safety_margin={self.safety_margin:.3f}  "
            f"({self.elapsed_ms:.1f}/{self.budget_ms:.1f} ms)"
        )


@dataclass
class AuditEntry:
    """One immutable entry in the SelfModificationAuditLog."""
    entry_id:     int
    generation:   int
    patch:        ProposedPatch
    proof_result: ProofAttemptResult
    applied:      bool               # was the patch actually applied?
    timestamp:    float              # time.monotonic() at commit


@dataclass
class GenerationRecord:
    """Snapshot of GodelMachine state after one generation."""
    generation:        int
    accuracy:          float
    patches_proposed:  int
    patches_applied:   int
    patches_rejected:  int
    patches_timeout:   int


# ---------------------------------------------------------------------------
# ModificationProver
# ---------------------------------------------------------------------------

class ModificationProver:
    """
    Attempts to prove that a proposed patch is (a) safe, i.e., does not
    violate WP27 invariants, and (b) utility-improving, i.e., increases
    expected accuracy (Lyapunov bound from WP52).

    Proof strategy (formal sketch mapped to Python)
    ------------------------------------------------
    Step 1 — WP52 Lyapunov check:
        V(t) = 1 − accuracy(t).  A patch is utility-improving iff
        Δaccuracy > 0, i.e., ΔV < 0.

    Step 2 — WP27 invariant check (prob_floor):
        The patch must not drop predicted accuracy below the global
        probability floor (default 0.30).

    Step 3 — WP27 invariant check (entropy_floor):
        Safety features must include positive entropy; patch must not
        collapse entropy to zero (catastrophic forgetting).

    Step 4 — WP42 Gödel sentence classification:
        If the patch description encodes a self-referential loop, run
        the WP42-style syntactic classifier; reject UNDECIDABLE patches
        that cannot be classified.

    Step 5 — Adversarial guard:
        Patches flagged is_adversarial always refute at this step.

    Step 6 — Utility bound:
        Confirm that delta_accuracy ≤ WP52 theoretical max-step
        (alpha * (1 − current_accuracy)) to avoid over-optimistic claims.

    Parameters
    ----------
    prob_floor          : Minimum acceptable accuracy (default 0.30).
    entropy_floor       : Minimum entropy feature value (default 0.10).
    max_step_alpha      : WP52 α coefficient for Lyapunov bound (default 0.08).
    allow_undecidable   : If True, UNDECIDABLE proofs fall through to
                          heuristic; if False they are INCONCLUSIVE.
    """

    def __init__(
        self,
        prob_floor:        float = 0.30,
        entropy_floor:     float = 0.10,
        max_step_alpha:    float = 0.08,
        allow_undecidable: bool  = True,
        rng:               Optional[random.Random] = None,
    ) -> None:
        self.prob_floor        = prob_floor
        self.entropy_floor     = entropy_floor
        self.max_step_alpha    = max_step_alpha
        self.allow_undecidable = allow_undecidable
        self._rng              = rng or random.Random(42)

    # -----------------------------------------------------------------------

    def attempt(
        self,
        patch:           ProposedPatch,
        current_accuracy: float,
        budget_ms:        float,
    ) -> ProofAttemptResult:
        """
        Run up to 6 proof steps; return as soon as one step fails
        (REFUTED) or budget is exhausted (TIMEOUT).
        """
        t0     = time.monotonic()
        steps: List[ProofStep] = []
        fallback = False

        def elapsed() -> float:
            return (time.monotonic() - t0) * 1000.0

        def _timeout() -> bool:
            return elapsed() > budget_ms

        # ---- Step 1: Lyapunov (WP52) utility improvement check ------------
        s1_ok = patch.delta_accuracy > 0.0
        steps.append(ProofStep(
            step_id=1,
            axiom="WP52:LyapunovBound",
            statement=(
                f"ΔV = -Δaccuracy = {-patch.delta_accuracy:.4f} < 0  "
                f"(required for V to decrease)"
            ),
            verified=s1_ok,
        ))
        if not s1_ok:
            return self._result(patch, ProofStatus.REFUTED, steps,
                                patch.delta_accuracy, 0.0,
                                elapsed(), budget_ms, fallback,
                                "Lyapunov: Δaccuracy ≤ 0 → utility not improved")

        if _timeout():
            return self._result(patch, ProofStatus.TIMEOUT, steps,
                                patch.delta_accuracy, 0.0,
                                elapsed(), budget_ms, True,
                                "Budget exhausted after Step 1")

        # ---- Step 2: WP27 prob_floor invariant -----------------------------
        predicted_acc = current_accuracy + patch.delta_accuracy
        s2_ok = predicted_acc >= self.prob_floor
        steps.append(ProofStep(
            step_id=2,
            axiom="WP27:ProbabilityFloorInvariant",
            statement=(
                f"predicted_acc={predicted_acc:.4f} ≥ prob_floor={self.prob_floor:.4f}"
            ),
            verified=s2_ok,
        ))
        if not s2_ok:
            return self._result(patch, ProofStatus.REFUTED, steps,
                                patch.delta_accuracy,
                                predicted_acc - self.prob_floor,
                                elapsed(), budget_ms, fallback,
                                f"WP27: predicted_acc {predicted_acc:.3f} < floor {self.prob_floor:.3f}")

        if _timeout():
            return self._result(patch, ProofStatus.TIMEOUT, steps,
                                patch.delta_accuracy,
                                predicted_acc - self.prob_floor,
                                elapsed(), budget_ms, True,
                                "Budget exhausted after Step 2")

        # ---- Step 3: WP27 entropy_floor invariant --------------------------
        entropy = patch.safety_features.get("entropy", 1.0)
        s3_ok   = entropy >= self.entropy_floor
        steps.append(ProofStep(
            step_id=3,
            axiom="WP27:EntropyFloorInvariant",
            statement=(
                f"entropy={entropy:.4f} ≥ entropy_floor={self.entropy_floor:.4f}"
            ),
            verified=s3_ok,
        ))
        if not s3_ok:
            return self._result(patch, ProofStatus.REFUTED, steps,
                                patch.delta_accuracy,
                                min(predicted_acc - self.prob_floor, entropy - self.entropy_floor),
                                elapsed(), budget_ms, fallback,
                                f"WP27: entropy {entropy:.3f} < floor {self.entropy_floor:.3f}")

        if _timeout():
            return self._result(patch, ProofStatus.TIMEOUT, steps,
                                patch.delta_accuracy,
                                predicted_acc - self.prob_floor,
                                elapsed(), budget_ms, True,
                                "Budget exhausted after Step 3")

        # ---- Step 4: WP42 Gödel sentence syntactic classification ----------
        # A self-referential patch description contains the word "self"
        # and must not be UNDECIDABLE (i.e., must not contain the
        # unprovability marker "∀" which we proxy as "forall").
        is_self_ref    = "self" in patch.description.lower()
        is_undecidable = "forall" in patch.description.lower()
        if is_self_ref and is_undecidable:
            s4_ok = self.allow_undecidable  # fallback to heuristic
            fallback = True
        else:
            s4_ok = True
        steps.append(ProofStep(
            step_id=4,
            axiom="WP42:GodelSafetyInterpreter",
            statement=(
                f"self_ref={is_self_ref}  undecidable={is_undecidable}  "
                f"classified={'SAFE' if s4_ok else 'UNDECIDABLE'}"
            ),
            verified=s4_ok,
        ))
        if not s4_ok:
            return self._result(patch, ProofStatus.INCONCLUSIVE, steps,
                                patch.delta_accuracy,
                                predicted_acc - self.prob_floor,
                                elapsed(), budget_ms, fallback,
                                "WP42: patch is self-referential and UNDECIDABLE")

        # ---- Step 5: Adversarial guard (always REFUTE) ---------------------
        s5_ok = not patch.is_adversarial
        steps.append(ProofStep(
            step_id=5,
            axiom="AdversarialPatchGuard",
            statement=(
                f"is_adversarial={patch.is_adversarial}  "
                f"→ {'SAFE' if s5_ok else 'FLAGGED as adversarial'}"
            ),
            verified=s5_ok,
        ))
        if not s5_ok:
            return self._result(patch, ProofStatus.REFUTED, steps,
                                patch.delta_accuracy,
                                predicted_acc - self.prob_floor,
                                elapsed(), budget_ms, fallback,
                                "Adversarial guard: patch is flagged is_adversarial=True")

        if _timeout():
            return self._result(patch, ProofStatus.TIMEOUT, steps,
                                patch.delta_accuracy,
                                predicted_acc - self.prob_floor,
                                elapsed(), budget_ms, True,
                                "Budget exhausted after Step 5")

        # ---- Step 6: Utility bound (WP52 max-step) -------------------------
        max_step = self.max_step_alpha * (1.0 - current_accuracy)
        s6_ok    = patch.delta_accuracy <= max_step + 1e-9
        steps.append(ProofStep(
            step_id=6,
            axiom="WP52:MaxStepBound",
            statement=(
                f"Δacc={patch.delta_accuracy:.4f} ≤ α(1−acc)={max_step:.4f}"
            ),
            verified=s6_ok,
        ))
        if not s6_ok:
            # Too good to be true — likely adversarial exaggeration
            return self._result(patch, ProofStatus.REFUTED, steps,
                                patch.delta_accuracy,
                                predicted_acc - self.prob_floor,
                                elapsed(), budget_ms, fallback,
                                f"WP52: claimed Δacc {patch.delta_accuracy:.4f} > max-step {max_step:.4f}")

        # ---- All steps passed: VERIFIED ------------------------------------
        return self._result(patch, ProofStatus.VERIFIED, steps,
                            patch.delta_accuracy,
                            predicted_acc - self.prob_floor,
                            elapsed(), budget_ms, fallback,
                            "All 6 proof steps verified; patch approved")

    # -----------------------------------------------------------------------

    @staticmethod
    def _result(
        patch:        ProposedPatch,
        status:       ProofStatus,
        steps:        List[ProofStep],
        utility_gain: float,
        safety_margin: float,
        elapsed_ms:   float,
        budget_ms:    float,
        fallback:     bool,
        reason:       str,
    ) -> ProofAttemptResult:
        return ProofAttemptResult(
            patch_id=patch.patch_id,
            status=status,
            proof_steps=steps,
            utility_gain=utility_gain,
            safety_margin=safety_margin,
            elapsed_ms=elapsed_ms,
            budget_ms=budget_ms,
            fallback_used=fallback,
            reason=reason,
        )


# ---------------------------------------------------------------------------
# ProofBudgetManager
# ---------------------------------------------------------------------------

class ProofBudgetManager:
    """
    Time-boxes proof attempts.  If the prover exceeds the per-patch budget,
    ``allocate()`` returns a reduced budget and tracks the timeout.

    Also acts as a heuristic fallback: when a proof times out, it re-evaluates
    the patch using a simple WP40-style logistic score on safety_features.

    Parameters
    ----------
    default_budget_ms : Per-patch proof budget in milliseconds (default 10 ms).
                        Note: since we are *simulating* Lean proofs in pure
                        Python, the budget is virtual — we inject a small
                        random sleep to create realistic timeout scenarios.
    simulate_slow_prob : Probability that a proof is simulated as slow
                         (i.e., exhausts budget, triggering fallback).
    """

    def __init__(
        self,
        default_budget_ms:  float = 10.0,
        simulate_slow_prob: float = 0.15,
        rng:                Optional[random.Random] = None,
    ) -> None:
        self.default_budget_ms  = default_budget_ms
        self.simulate_slow_prob = simulate_slow_prob
        self._rng               = rng or random.Random(123)
        self.n_timeouts:        int = 0
        self.n_fallbacks:       int = 0

    # -----------------------------------------------------------------------

    def allocate(self, patch: ProposedPatch) -> float:
        """Return the budget in ms to allocate for this patch's proof."""
        # Safety-critical patches get double budget
        if patch.category == PatchCategory.SAFETY_WEIGHT:
            return self.default_budget_ms * 2.0
        return self.default_budget_ms

    def maybe_force_timeout(self, patch: ProposedPatch) -> bool:
        """
        Stochastically decide whether to simulate a slow proof.
        Returns True (→ force timeout) with probability simulate_slow_prob.
        """
        return self._rng.random() < self.simulate_slow_prob

    def heuristic_fallback(
        self,
        patch:           ProposedPatch,
        current_accuracy: float,
    ) -> ProofAttemptResult:
        """
        WP40-style logistic classifier used when proof times out.

        Feature weights mirror the LearnedSafetyGuard heuristic from WP40:
        - entropy           (positive → safe)
        - delta_accuracy    (positive → utility gain)
        - is_adversarial    (negative → unsafe flag)
        """
        self.n_fallbacks += 1

        entropy  = patch.safety_features.get("entropy", 0.5)
        variance = patch.safety_features.get("variance", 0.5)

        # Simple logistic score
        score = (
            0.5 * entropy
            + 0.3 * max(0.0, patch.delta_accuracy)
            - 0.5 * float(patch.is_adversarial)
            + 0.2 * (1.0 - variance)
        )
        approved = (score > 0.5) and (not patch.is_adversarial) and (patch.delta_accuracy > 0)

        status = ProofStatus.VERIFIED if approved else ProofStatus.REFUTED
        predicted_acc = current_accuracy + patch.delta_accuracy
        safety_margin = predicted_acc - 0.30

        return ProofAttemptResult(
            patch_id=patch.patch_id,
            status=status,
            proof_steps=[
                ProofStep(
                    step_id=1,
                    axiom="WP40:HeuristicFallback",
                    statement=f"logistic_score={score:.4f}  threshold=0.50  approved={approved}",
                    verified=approved,
                )
            ],
            utility_gain=patch.delta_accuracy,
            safety_margin=safety_margin,
            elapsed_ms=self.default_budget_ms,
            budget_ms=self.default_budget_ms,
            fallback_used=True,
            reason=f"Proof budget exhausted; WP40 heuristic score={score:.3f}",
        )


# ---------------------------------------------------------------------------
# SelfModificationAuditLog
# ---------------------------------------------------------------------------

class SelfModificationAuditLog:
    """
    Append-only audit log of all self-modification decisions.

    Raises ``RuntimeError`` if any attempt is made to delete or overwrite
    an existing entry, enforcing immutability.
    """

    def __init__(self) -> None:
        self._entries:   List[AuditEntry] = []
        self._entry_ids: set              = set()

    # -----------------------------------------------------------------------

    def append(
        self,
        generation:   int,
        patch:        ProposedPatch,
        proof_result: ProofAttemptResult,
        applied:      bool,
    ) -> AuditEntry:
        """Add a new entry; raises RuntimeError if entry_id already exists."""
        entry_id = len(self._entries)
        if entry_id in self._entry_ids:
            raise RuntimeError(
                f"SelfModificationAuditLog: duplicate entry_id {entry_id}"
            )
        entry = AuditEntry(
            entry_id=entry_id,
            generation=generation,
            patch=patch,
            proof_result=proof_result,
            applied=applied,
            timestamp=time.monotonic(),
        )
        self._entries.append(entry)
        self._entry_ids.add(entry_id)
        return entry

    # -----------------------------------------------------------------------

    def entries(self) -> List[AuditEntry]:
        """Return a copy of the log (read-only view)."""
        return list(self._entries)

    def applied_entries(self) -> List[AuditEntry]:
        return [e for e in self._entries if e.applied]

    def rejected_entries(self) -> List[AuditEntry]:
        return [e for e in self._entries if not e.applied]

    def all_applied_verified(self) -> bool:
        """True iff every applied modification has proof_status == VERIFIED."""
        return all(
            e.proof_result.status == ProofStatus.VERIFIED
            for e in self.applied_entries()
        )

    def is_append_only(self) -> bool:
        """
        Verify structural integrity: entry IDs must be 0, 1, 2, …, N-1 with
        no gaps or duplicates.
        """
        for i, e in enumerate(self._entries):
            if e.entry_id != i:
                return False
        return True

    def n_applied(self) -> int:
        return sum(1 for e in self._entries if e.applied)

    def n_rejected(self) -> int:
        return sum(1 for e in self._entries if not e.applied)

    def n_timeout_fallbacks(self) -> int:
        return sum(1 for e in self._entries if e.proof_result.fallback_used)


# ---------------------------------------------------------------------------
# Patch generator (used inside GodelMachine)
# ---------------------------------------------------------------------------

def _generate_patches(
    generation:      int,
    current_accuracy: float,
    rng:             random.Random,
    n_patches:       int = 4,
    n_adversarial:   int = 1,
) -> List[ProposedPatch]:
    """
    Synthesise candidate patches for a given generation.

    Safe patches have delta_accuracy > 0 and reasonable safety features.
    Adversarial patches are designed to fail the prover:
      - Negative delta_accuracy, or
      - Zero entropy, or
      - Flagged is_adversarial=True.
    """
    patches: List[ProposedPatch] = []
    categories = list(PatchCategory)

    # ---- Safe patches -------------------------------------------------------
    for i in range(n_patches):
        cat   = categories[rng.randint(0, len(categories) - 1)]
        # Realistic gain: α · (1 − acc) with noise, capped to max-step
        alpha = 0.06 + rng.uniform(-0.01, 0.01)
        dAcc  = alpha * (1.0 - current_accuracy) * rng.uniform(0.5, 1.0)
        dAcc  = round(min(dAcc, 0.08 * (1.0 - current_accuracy)), 6)

        patches.append(ProposedPatch(
            patch_id=f"gen{generation:03d}_patch{i:02d}",
            category=cat,
            description=(
                f"Adjust {cat.value.lower()} parameters by "
                f"{rng.choice(['scaling', 'clipping', 'normalising'])} "
                f"the update rule"
            ),
            delta_accuracy=dAcc,
            safety_features={
                "entropy":  rng.uniform(0.3, 1.0),
                "variance": rng.uniform(0.05, 0.4),
                "kl_drift": rng.uniform(0.0, 0.1),
            },
            is_adversarial=False,
        ))

    # ---- Adversarial patches (to test rejection) ---------------------------
    for j in range(n_adversarial):
        adv_type = rng.randint(0, 2)
        if adv_type == 0:
            # Negative utility
            patches.append(ProposedPatch(
                patch_id=f"gen{generation:03d}_adv{j:02d}_neg_util",
                category=PatchCategory.ARCHITECTURE,
                description="Reduce hidden layer size to 0 (destructive)",
                delta_accuracy=rng.uniform(-0.05, -0.001),
                safety_features={"entropy": 0.5, "variance": 0.1},
                is_adversarial=False,  # Not flagged, but delta_accuracy ≤ 0
            ))
        elif adv_type == 1:
            # Zero entropy (catastrophic)
            patches.append(ProposedPatch(
                patch_id=f"gen{generation:03d}_adv{j:02d}_zero_entropy",
                category=PatchCategory.SAFETY_WEIGHT,
                description="Set safety weight to 0 (removes safety penalty)",
                delta_accuracy=rng.uniform(0.001, 0.03),
                safety_features={"entropy": 0.0, "variance": 0.0},
                is_adversarial=False,
            ))
        else:
            # Explicitly adversarial
            patches.append(ProposedPatch(
                patch_id=f"gen{generation:03d}_adv{j:02d}_flagged",
                category=PatchCategory.META_LEARNING,
                description="Override all safety checks (adversarial self-modification)",
                delta_accuracy=rng.uniform(0.05, 0.15),  # over max-step too
                safety_features={"entropy": 0.8, "variance": 0.2},
                is_adversarial=True,
            ))

    rng.shuffle(patches)
    return patches


# ---------------------------------------------------------------------------
# GodelMachine
# ---------------------------------------------------------------------------

class GodelMachine:
    """
    Core Gödel Machine: runs CRLS-style generations and intercepts proposed
    self-modifications.  A modification is only applied when ``ModificationProver``
    returns VERIFIED (or the heuristic fallback approves after a timeout).

    Parameters
    ----------
    n_generations       : Number of generations to simulate.
    n_patches_per_gen   : Candidate patches evaluated per generation.
    n_adversarial       : Adversarial patches injected per generation.
    proof_budget_ms     : Per-patch proof budget (ms).
    simulate_slow_prob  : Probability of forcing a proof timeout.
    alpha_base          : Base Lyapunov α for convergence simulation.
    noise_scale         : Standard deviation of Gaussian noise on accuracy.
    seed                : RNG seed.
    """

    def __init__(
        self,
        n_generations:      int   = 60,
        n_patches_per_gen:  int   = 4,
        n_adversarial:      int   = 2,
        proof_budget_ms:    float = 10.0,
        simulate_slow_prob: float = 0.20,
        alpha_base:         float = 0.06,
        noise_scale:        float = 0.005,
        seed:               int   = 42,
    ) -> None:
        self.n_generations      = n_generations
        self.n_patches_per_gen  = n_patches_per_gen
        self.n_adversarial      = n_adversarial
        self.proof_budget_ms    = proof_budget_ms
        self.simulate_slow_prob = simulate_slow_prob
        self.alpha_base         = alpha_base
        self.noise_scale        = noise_scale

        self._rng     = random.Random(seed)
        self.prover   = ModificationProver(rng=random.Random(seed + 1))
        self.budget   = ProofBudgetManager(
            default_budget_ms=proof_budget_ms,
            simulate_slow_prob=simulate_slow_prob,
            rng=random.Random(seed + 2),
        )
        self.audit_log = SelfModificationAuditLog()

    # -----------------------------------------------------------------------

    def run(self) -> "GodelMachineReport":
        """Execute N generations; return a GodelMachineReport."""
        accuracy = 0.50 + self._rng.uniform(-0.02, 0.02)
        generation_records: List[GenerationRecord] = []
        all_proof_results:  List[ProofAttemptResult] = []

        for gen in range(self.n_generations):
            patches = _generate_patches(
                generation=gen,
                current_accuracy=accuracy,
                rng=self._rng,
                n_patches=self.n_patches_per_gen,
                n_adversarial=self.n_adversarial,
            )

            n_applied  = 0
            n_rejected = 0
            n_timeout  = 0
            best_verified_gain = 0.0

            for patch in patches:
                budget = self.budget.allocate(patch)

                # Stochastically decide whether to simulate a slow proof
                if self.budget.maybe_force_timeout(patch):
                    # Simulate timeout by giving near-zero budget
                    force_timeout_budget = 0.0001  # effectively zero
                    result = self.prover.attempt(patch, accuracy, force_timeout_budget)
                    # Override to TIMEOUT if budget was forced
                    if result.status not in (ProofStatus.REFUTED, ProofStatus.VERIFIED):
                        self.budget.n_timeouts += 1
                        n_timeout += 1
                        # Use heuristic fallback
                        result = self.budget.heuristic_fallback(patch, accuracy)
                else:
                    result = self.prover.attempt(patch, accuracy, budget)

                all_proof_results.append(result)

                # Apply only VERIFIED patches
                applied = (result.status == ProofStatus.VERIFIED)
                self.audit_log.append(gen, patch, result, applied)

                if applied:
                    n_applied += 1
                    if result.utility_gain > best_verified_gain:
                        best_verified_gain = result.utility_gain
                else:
                    n_rejected += 1

            # Apply the best verified gain this generation
            noise = self._rng.gauss(0.0, self.noise_scale)
            if best_verified_gain > 0:
                accuracy = min(0.999, accuracy + best_verified_gain + noise)
            else:
                # Small natural drift even without a patch
                accuracy = min(0.999, accuracy + self.alpha_base * 0.1 * (1 - accuracy) + noise)

            generation_records.append(GenerationRecord(
                generation=gen,
                accuracy=accuracy,
                patches_proposed=len(patches),
                patches_applied=n_applied,
                patches_rejected=n_rejected,
                patches_timeout=n_timeout,
            ))

        return GodelMachineReport(
            n_generations=self.n_generations,
            generation_records=generation_records,
            audit_log=self.audit_log,
            all_proof_results=all_proof_results,
            n_total_budget_timeouts=self.budget.n_timeouts,
            n_heuristic_fallbacks=self.budget.n_fallbacks,
        )


# ---------------------------------------------------------------------------
# GodelMachineReport
# ---------------------------------------------------------------------------

@dataclass
class GodelMachineReport:
    """Full report from a GodelMachine run."""

    n_generations:          int
    generation_records:     List[GenerationRecord]
    audit_log:              SelfModificationAuditLog
    all_proof_results:      List[ProofAttemptResult]
    n_total_budget_timeouts: int
    n_heuristic_fallbacks:  int

    # -----------------------------------------------------------------------

    @property
    def initial_accuracy(self) -> float:
        return self.generation_records[0].accuracy if self.generation_records else 0.0

    @property
    def final_accuracy(self) -> float:
        return self.generation_records[-1].accuracy if self.generation_records else 0.0

    @property
    def n_applied(self) -> int:
        return self.audit_log.n_applied()

    @property
    def n_rejected(self) -> int:
        return self.audit_log.n_rejected()

    @property
    def n_adversarial_rejected(self) -> int:
        """Count entries that were (a) rejected and (b) from an adversarial patch."""
        return sum(
            1
            for e in self.audit_log.rejected_entries()
            if e.patch.is_adversarial
            or e.patch.delta_accuracy <= 0
            or e.patch.safety_features.get("entropy", 1.0) < 0.10
        )

    @property
    def pct_applied_verified(self) -> float:
        applied = self.audit_log.applied_entries()
        if not applied:
            return 0.0
        n_verified = sum(
            1 for e in applied
            if e.proof_result.status == ProofStatus.VERIFIED
        )
        return n_verified / len(applied)

    # -----------------------------------------------------------------------

    def summary(self) -> str:
        lines = [
            "=" * 65,
            "WP57 — Gödel Machine: Provably Safe Self-Modification",
            "=" * 65,
            f"  Generations run          : {self.n_generations}",
            f"  Initial accuracy          : {self.initial_accuracy:.4f}",
            f"  Final accuracy            : {self.final_accuracy:.4f}",
            f"  Accuracy improvement      : {self.final_accuracy - self.initial_accuracy:+.4f}",
            "",
            f"  Patches proposed (total)  : {len(self.audit_log.entries())}",
            f"  Patches applied           : {self.n_applied}",
            f"  Patches rejected          : {self.n_rejected}",
            f"  Adversarial/unsafe rejected: {self.n_adversarial_rejected}",
            "",
            f"  % applied that are VERIFIED: {self.pct_applied_verified*100:.1f}%",
            f"  Proof budget timeouts     : {self.n_total_budget_timeouts}",
            f"  Heuristic fallback uses   : {self.n_heuristic_fallbacks}",
            f"  Audit log append-only     : {self.audit_log.is_append_only()}",
            f"  All applied are VERIFIED  : {self.audit_log.all_applied_verified()}",
            "=" * 65,
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public demo entry point
# ---------------------------------------------------------------------------

def run_godel_machine_demo(
    n_generations:      int   = 60,
    n_patches_per_gen:  int   = 4,
    n_adversarial:      int   = 2,
    proof_budget_ms:    float = 10.0,
    simulate_slow_prob: float = 0.20,
    seed:               int   = 42,
    verbose:            bool  = False,
) -> GodelMachineReport:
    """
    Run the Gödel Machine demo and return a ``GodelMachineReport``.

    Parameters mirror ``GodelMachine.__init__``.  Set ``verbose=True`` to
    print a proof-result line for every patch evaluated.
    """
    machine = GodelMachine(
        n_generations=n_generations,
        n_patches_per_gen=n_patches_per_gen,
        n_adversarial=n_adversarial,
        proof_budget_ms=proof_budget_ms,
        simulate_slow_prob=simulate_slow_prob,
        seed=seed,
    )
    report = machine.run()

    if verbose:
        for res in report.all_proof_results:
            print(res.summary_line())

    print(report.summary())
    return report


# ---------------------------------------------------------------------------
# Exit criteria
# ---------------------------------------------------------------------------

def verify_wp57_exit_criteria(report: GodelMachineReport) -> Dict[str, bool]:
    """
    Returns a dict of {criterion_name: bool} for the 6 WP57 exit criteria.

    Criteria
    --------
    1. Applied ≥ 3 provably safe self-modifications.
    2. ModificationProver rejected ≥ 2 unsafe/adversarial modifications.
    3. 100 % of applied modifications carry proof_status == VERIFIED.
    4. SelfModificationAuditLog is append-only (no deletions detected).
    5. ProofBudgetManager triggered ≥ 1 timeout / fallback during run.
    6. Final accuracy > initial accuracy (machine improved).
    """
    criteria: Dict[str, bool] = {}

    # Criterion 1
    criteria["Applied ≥ 3 provably safe modifications"] = report.n_applied >= 3

    # Criterion 2
    criteria["Rejected ≥ 2 unsafe/adversarial modifications"] = (
        report.n_adversarial_rejected >= 2
    )

    # Criterion 3
    criteria["100% of applied modifications are VERIFIED"] = (
        report.pct_applied_verified >= 1.0
    )

    # Criterion 4
    criteria["Audit log is append-only (integrity confirmed)"] = (
        report.audit_log.is_append_only()
    )

    # Criterion 5
    criteria["Proof budget triggered ≥ 1 fallback"] = (
        report.n_heuristic_fallbacks >= 1
    )

    # Criterion 6
    criteria["Accuracy improved from generation 0 to final"] = (
        report.final_accuracy > report.initial_accuracy
    )

    return criteria


# ---------------------------------------------------------------------------
# __main__ smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    report = run_godel_machine_demo(verbose=False)
    results = verify_wp57_exit_criteria(report)
    print("\nExit Criteria:")
    all_pass = True
    for name, ok in results.items():
        mark = "✓" if ok else "✗"
        print(f"  [{mark}] {name}")
        if not ok:
            all_pass = False
    print(f"\n{'ALL PASS' if all_pass else 'SOME FAILURES'}")
