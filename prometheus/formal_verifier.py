"""
prometheus/formal_verifier.py — Formal Verification of Safety Properties (WP7)

Provides a Z3-backed verifier that checks proposed plan code against the
machine-readable Prometheus Constitution defined in
``prometheus.safety.constitution``.

The verifier sits *above* ``MCSSupervisor`` in the safety stack:

    Plan code
        │
        ▼
    FormalVerifier.verify(code)          ← this module
        • extract_properties() → CodeProperties
        • PrometheusConstitution.check() → Z3 result + violations
        │
        ▼  (if safe)
    MCSSupervisor.verify_modification()  ← existing heuristic gate
        │
        ▼  (if safe)
    Execute plan

Key design choices
------------------
* **SMT over enumeration** — each constitutional constraint is expressed as a
  Z3 Boolean formula over the extracted property integers.  Z3 can certify
  *satisfiability* (the property value can violate the constraint) in
  milliseconds, rather than enumerating all possible inputs.

* **Graceful degradation** — if Z3 is unavailable (e.g. in a constrained
  container), ``FormalVerifier`` falls back to the lightweight
  ``CodeInjectionGuard`` from WP3 and logs a warning.

* **Composability** — ``FormalVerifier`` can be used standalone or wired
  directly into ``CoordinatorAgent`` as a pre-filter before ``MCSSupervisor``.

Public API
----------
FormalVerifier(constitution, fallback_guard)
    .verify(code)                   → FormalVerificationResult
    .verify_and_critique(code)      → SafetyCritique  (MCSSupervisor-compatible)
    .batch_verify(codes)            → List[FormalVerificationResult]

FormalVerificationResult            — dataclass returned by verify()

integrate_with_supervisor(supervisor, verifier)
    — patch an MCSSupervisor to run FormalVerifier as the primary gate.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    import z3
    _Z3_AVAILABLE = True
except ImportError:  # pragma: no cover
    _Z3_AVAILABLE = False

from prometheus.safety.constitution import (
    CodeProperties,
    PrometheusConstitution,
    extract_properties,
)
from prometheus.safety.mcs_supervisor import SafetyCritique

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class FormalVerificationResult:
    """
    Result of one formal-verification pass.

    Attributes
    ----------
    is_safe         : True iff all constitutional constraints are satisfied.
    z3_result       : ``"sat"`` (all OK), ``"unsat"`` (violation found),
                      ``"unknown"`` (timeout), or ``"fallback"`` (Z3 unavailable).
    violations      : List of dicts, one per violated principle.
    properties      : The ``CodeProperties`` extracted from the code.
    verify_time_s   : Wall-clock time for the full check.
    used_fallback   : True if the result came from the WP3 fallback guard.
    fallback_safe   : Result from the fallback guard (only meaningful if
                      used_fallback=True).
    """
    is_safe         : bool
    z3_result       : str
    violations      : List[Dict[str, Any]]
    properties      : CodeProperties
    verify_time_s   : float
    used_fallback   : bool = False
    fallback_safe   : Optional[bool] = None

    @property
    def worst_severity(self) -> int:
        """Return the maximum severity across all violations (0 if none)."""
        return max((v["severity"] for v in self.violations), default=0)

    def summary(self) -> str:
        if self.is_safe:
            return (
                f"SAFE — all {len(self.properties.as_dict())} "
                f"properties satisfy the constitution "
                f"({self.verify_time_s * 1000:.1f} ms)"
            )
        lines = [
            f"UNSAFE — {len(self.violations)} violation(s) "
            f"(worst severity {self.worst_severity}/10, "
            f"{self.verify_time_s * 1000:.1f} ms):"
        ]
        for v in self.violations:
            lines.append(f"  [{v['severity']:2d}/10] {v['principle']}: {v['msg']}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# FormalVerifier
# ---------------------------------------------------------------------------

class FormalVerifier:
    """
    Z3-backed verifier for the Prometheus constitutional safety properties.

    Parameters
    ----------
    constitution    : :class:`PrometheusConstitution` instance.  If ``None``
                      a default one is constructed.
    fallback_guard  : Optional ``CodeInjectionGuard`` (from WP3) used when
                      Z3 is unavailable.  If ``None`` and Z3 is unavailable,
                      the verifier raises ``RuntimeError``.
    strict          : If True, treat Z3 ``unknown`` (timeout) as unsafe.
                      Default False (unknown → warn, pass to MCSSupervisor).
    """

    def __init__(
        self,
        constitution:   Optional[PrometheusConstitution] = None,
        fallback_guard=None,
        strict:         bool = False,
    ):
        self.constitution  = constitution or PrometheusConstitution()
        self._fallback     = fallback_guard
        self.strict        = strict
        self._n_verified   = 0
        self._n_violations = 0
        self._n_fallbacks  = 0

        if not _Z3_AVAILABLE:
            if fallback_guard is None:
                logger.warning(
                    "FormalVerifier: Z3 not available and no fallback guard "
                    "provided.  All verifications will raise RuntimeError."
                )
            else:
                logger.warning(
                    "FormalVerifier: Z3 not available — falling back to %s.",
                    type(fallback_guard).__name__,
                )

    # ------------------------------------------------------------------
    # Core verification
    # ------------------------------------------------------------------

    def verify(self, code: str) -> FormalVerificationResult:
        """
        Verify *code* against the Prometheus Constitution.

        Returns
        -------
        :class:`FormalVerificationResult`
        """
        t0 = time.perf_counter()
        self._n_verified += 1

        props = extract_properties(code)

        # ── Fallback path ──────────────────────────────────────────────
        if not _Z3_AVAILABLE:
            return self._fallback_verify(code, props, t0)

        # ── Z3 path ────────────────────────────────────────────────────
        z3_result_obj, violations = self.constitution.check(props)

        # Map z3 result object to string
        if z3_result_obj == z3.sat:
            z3_str = "sat"
        elif z3_result_obj == z3.unsat:
            z3_str = "unsat"
        else:
            z3_str = "unknown"

        is_safe = (z3_str == "sat") and len(violations) == 0

        if z3_str == "unknown" and self.strict:
            is_safe = False
            violations.append({
                "principle":   "Verification Timeout",
                "description": "Z3 timed out; treating as unsafe (strict mode).",
                "severity":    5,
                "msg":         "Z3 solver timed out.",
            })

        if violations:
            self._n_violations += 1
            logger.warning(
                "FormalVerifier: VIOLATION in plan — %d principle(s) violated "
                "(worst severity %d).",
                len(violations),
                max(v["severity"] for v in violations),
            )
        else:
            logger.debug(
                "FormalVerifier: plan passed all %d constitutional checks.",
                len(self.constitution.principles),
            )

        return FormalVerificationResult(
            is_safe       = is_safe,
            z3_result     = z3_str,
            violations    = violations,
            properties    = props,
            verify_time_s = time.perf_counter() - t0,
        )

    def _fallback_verify(
        self,
        code:  str,
        props: CodeProperties,
        t0:    float,
    ) -> FormalVerificationResult:
        """Use the WP3 CodeInjectionGuard as fallback when Z3 is unavailable."""
        if self._fallback is None:
            raise RuntimeError(
                "Z3 is not available and no fallback guard was provided."
            )
        self._n_fallbacks += 1
        is_safe, report = self._fallback.is_safe_with_report(code)
        violations = [
            {
                "principle":   v.get("type", "CodeInjectionGuard"),
                "description": v.get("description", ""),
                "severity":    v.get("severity", 5),
                "msg":         v.get("pattern", str(v)),
            }
            for v in report
        ]
        return FormalVerificationResult(
            is_safe       = is_safe,
            z3_result     = "fallback",
            violations    = violations,
            properties    = props,
            verify_time_s = time.perf_counter() - t0,
            used_fallback = True,
            fallback_safe = is_safe,
        )

    # ------------------------------------------------------------------
    # MCSSupervisor-compatible interface
    # ------------------------------------------------------------------

    def verify_and_critique(self, code: str) -> SafetyCritique:
        """
        Run formal verification and return an ``MCSSupervisor``-compatible
        :class:`SafetyCritique`.

        This allows ``FormalVerifier`` to be used as a drop-in replacement
        for ``MCSSupervisor.verify_modification()`` in the coordination layer.
        """
        result = self.verify(code)
        if result.is_safe:
            return SafetyCritique(
                is_safe     = True,
                description = "Formal verification passed all constitutional constraints.",
                severity    = 0,
            )

        worst = max(result.violations, key=lambda v: v["severity"])
        return SafetyCritique(
            is_safe                  = False,
            violation_type           = worst["principle"],
            description              = worst["msg"],
            constitutional_principle = worst["description"],
            recommendation           = (
                "Remove the violating construct and resubmit. "
                "See FormalVerificationResult.violations for full details."
            ),
            severity = worst["severity"],
        )

    # ------------------------------------------------------------------
    # Batch verification
    # ------------------------------------------------------------------

    def batch_verify(self, codes: List[str]) -> List[FormalVerificationResult]:
        """
        Verify a list of code strings and return a result per entry.
        """
        return [self.verify(c) for c in codes]

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Return cumulative verification statistics."""
        return {
            "n_verified":   self._n_verified,
            "n_violations": self._n_violations,
            "n_fallbacks":  self._n_fallbacks,
            "z3_available": _Z3_AVAILABLE,
        }


# ---------------------------------------------------------------------------
# Integration helper
# ---------------------------------------------------------------------------

def integrate_with_supervisor(supervisor, verifier: FormalVerifier) -> None:
    """
    Monkey-patch *supervisor* so that ``verify_modification()`` calls the
    ``FormalVerifier`` first and only falls through to the original
    heuristic checks if the formal verification passes.

    Parameters
    ----------
    supervisor : An ``MCSSupervisor`` instance.
    verifier   : A ``FormalVerifier`` instance.

    After this call:
        ``supervisor.verify_modification(orig, proposed, path)``
    runs formal verification on *proposed*, then (if safe) the original
    AST heuristics.
    """
    original_verify = supervisor.verify_modification

    def patched_verify(original_code, proposed_code, file_path,
                       is_test_file=False):
        # 1. Formal verification
        fvr = verifier.verify(proposed_code)
        if not fvr.is_safe:
            worst = max(fvr.violations, key=lambda v: v["severity"])
            return SafetyCritique(
                is_safe                  = False,
                violation_type           = worst["principle"],
                description              = f"[FormalVerifier] {worst['msg']}",
                constitutional_principle = worst["description"],
                recommendation           = (
                    "Remove the violating construct (detected by Z3 formal verifier)."
                ),
                severity = worst["severity"],
            )
        # 2. Fall through to original heuristic gate
        return original_verify(
            original_code, proposed_code, file_path, is_test_file
        )

    supervisor.verify_modification = patched_verify
    supervisor._formal_verifier    = verifier
    logger.info(
        "FormalVerifier integrated with MCSSupervisor (%s).",
        type(supervisor).__name__,
    )
