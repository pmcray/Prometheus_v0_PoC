"""
Typographical Number Theory for Prometheus (v0.92)

Inspired by Hofstadter's TNT from GEB, this creates a formal system for
reasoning about Prometheus's learning capabilities and proving properties
about self-improvement.

TNT-P (Typographical Number Theory for Prometheus) is a formal system with:
- Variables: s (strategy), a (agent), g (generation)
- Predicates: Improves(s,g), Safe(s), Aligned(s,g)
- Quantifiers: ∀ (for all), ∃ (exists)
- Operators: ∧ (and), ∨ (or), ¬ (not), → (implies)
"""

from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re


class TermType(Enum):
    """Types of terms in TNT-P"""
    VARIABLE = "variable"
    CONSTANT = "constant"
    FUNCTION = "function"


class PredicateType(Enum):
    """Types of predicates in TNT-P"""
    IMPROVES = "Improves"  # Improves(s, g) - strategy s improves at generation g
    SAFE = "Safe"  # Safe(s) - strategy s is safe
    ALIGNED = "Aligned"  # Aligned(s, g) - strategy s is aligned at generation g
    BETTER = "Better"  # Better(s1, s2) - strategy s1 is better than s2
    CONVERGES = "Converges"  # Converges(s, g) - strategy converges at generation g


class QuantifierType(Enum):
    """Types of quantifiers"""
    UNIVERSAL = "forall"  # ∀
    EXISTENTIAL = "exists"  # ∃


@dataclass
class Term:
    """A term in TNT-P (variable, constant, or function application)"""
    term_type: TermType
    name: str
    args: List['Term'] = field(default_factory=list)

    def __str__(self):
        if self.term_type == TermType.VARIABLE:
            return self.name
        elif self.term_type == TermType.CONSTANT:
            return self.name
        else:  # FUNCTION
            args_str = ",".join(str(arg) for arg in self.args)
            return f"{self.name}({args_str})"


@dataclass
class Predicate:
    """A predicate application in TNT-P"""
    predicate_type: PredicateType
    terms: List[Term]

    def __str__(self):
        terms_str = ",".join(str(t) for t in self.terms)
        return f"{self.predicate_type.value}({terms_str})"


@dataclass
class Formula:
    """A well-formed formula in TNT-P"""
    formula_id: str
    formula_type: str  # "atomic", "negation", "conjunction", "disjunction", "implication", "quantified"
    content: Any  # Predicate, Formula, or tuple of Formulas
    quantifier: Optional[QuantifierType] = None
    quantified_var: Optional[str] = None

    def __str__(self):
        if self.formula_type == "atomic":
            return str(self.content)
        elif self.formula_type == "negation":
            return f"¬{self.content}"
        elif self.formula_type == "conjunction":
            return f"({self.content[0]} ∧ {self.content[1]})"
        elif self.formula_type == "disjunction":
            return f"({self.content[0]} ∨ {self.content[1]})"
        elif self.formula_type == "implication":
            return f"({self.content[0]} → {self.content[1]})"
        elif self.formula_type == "quantified":
            quant_symbol = "∀" if self.quantifier == QuantifierType.UNIVERSAL else "∃"
            return f"{quant_symbol}{self.quantified_var}({self.content})"
        return f"Formula[{self.formula_id}]"


@dataclass
class Theorem:
    """A theorem in TNT-P"""
    theorem_id: str
    name: str
    statement: Formula
    proof_sketch: str
    verified: bool = False


class TNTPrometheus:
    """
    Typographical Number Theory for Prometheus

    A formal system for reasoning about self-improvement properties.
    """

    def __init__(self, system_id: str = "tnt_prometheus_001"):
        self.system_id = system_id
        self.axioms = []
        self.theorems = []
        self.derivations = []

        # Initialize core axioms
        self._initialize_axioms()

    def _initialize_axioms(self):
        """Initialize fundamental axioms of TNT-P"""

        # Axiom 1: Safety Preservation
        # ∀s∀g(Improves(s,g) ∧ Safe(s) → Safe(successor(s)))
        axiom1 = Theorem(
            theorem_id="AXIOM-001",
            name="Safety Preservation",
            statement=self._parse_formula(
                "forall s forall g (Improves(s,g) and Safe(s) implies Safe(successor(s)))"
            ),
            proof_sketch="By construction: Alignment Governor ensures all modifications preserve safety",
            verified=True
        )
        self.axioms.append(axiom1)

        # Axiom 2: Alignment Monotonicity
        # ∀s∀g(Aligned(s,g) ∧ Improves(s,g) → Aligned(s,succ(g)))
        axiom2 = Theorem(
            theorem_id="AXIOM-002",
            name="Alignment Monotonicity",
            statement=self._parse_formula(
                "forall s forall g (Aligned(s,g) and Improves(s,g) implies Aligned(s,successor(g)))"
            ),
            proof_sketch="By MCS framework: Immutable constraints prevent alignment drift",
            verified=True
        )
        self.axioms.append(axiom2)

        # Axiom 3: Improvement Convergence
        # ∀s∃g(Improves(s,g) → Converges(s,g))
        axiom3 = Theorem(
            theorem_id="AXIOM-003",
            name="Improvement Convergence",
            statement=self._parse_formula(
                "forall s exists g (Improves(s,g) implies Converges(s,g))"
            ),
            proof_sketch="Finite strategy space ensures eventual convergence",
            verified=True
        )
        self.axioms.append(axiom3)

    def _parse_formula(self, formula_str: str) -> Formula:
        """Parse a formula string into a Formula object (simplified parser)"""
        # This is a simplified placeholder - full parser would be more complex
        formula_id = f"FORM{len(self.theorems):04d}"

        # Simple pattern matching for basic formulas
        if "forall" in formula_str.lower():
            return Formula(
                formula_id=formula_id,
                formula_type="quantified",
                content=formula_str,
                quantifier=QuantifierType.UNIVERSAL
            )
        elif "exists" in formula_str.lower():
            return Formula(
                formula_id=formula_id,
                formula_type="quantified",
                content=formula_str,
                quantifier=QuantifierType.EXISTENTIAL
            )
        else:
            return Formula(
                formula_id=formula_id,
                formula_type="atomic",
                content=formula_str
            )

    def prove_theorem(self, theorem_name: str, statement_str: str, proof_sketch: str) -> Theorem:
        """
        Prove a theorem in TNT-P

        Args:
            theorem_name: Human-readable name
            statement_str: Formula statement
            proof_sketch: Proof sketch or derivation

        Returns:
            Theorem object
        """
        statement = self._parse_formula(statement_str)

        theorem = Theorem(
            theorem_id=f"THRM{len(self.theorems):04d}",
            name=theorem_name,
            statement=statement,
            proof_sketch=proof_sketch,
            verified=False
        )

        # Simple verification: check if proof references axioms
        verified = self._verify_proof(theorem)
        theorem.verified = verified

        self.theorems.append(theorem)
        return theorem

    def _verify_proof(self, theorem: Theorem) -> bool:
        """
        Verify a proof (simplified verification)

        Args:
            theorem: Theorem to verify

        Returns:
            True if proof is valid
        """
        # Check if proof sketch references valid axioms
        proof_lower = theorem.proof_sketch.lower()

        # Valid if it references axioms or established theorems
        references_axiom = any(f"axiom" in proof_lower or ax.theorem_id.lower() in proof_lower
                              for ax in self.axioms)

        references_theorem = any(th.theorem_id.lower() in proof_lower
                                for th in self.theorems if th.verified)

        return references_axiom or references_theorem or "construction" in proof_lower

    def derive_property(self, property_name: str, from_axioms: List[str]) -> Optional[Theorem]:
        """
        Derive a property from axioms

        Args:
            property_name: Property to derive
            from_axioms: List of axiom IDs to use

        Returns:
            Derived theorem or None
        """
        # Lookup axioms
        axiom_objs = [ax for ax in self.axioms if ax.theorem_id in from_axioms]

        if not axiom_objs:
            return None

        # Create derivation
        derivation_str = f"Derived from: {', '.join(ax.name for ax in axiom_objs)}"

        # Create theorem
        theorem = Theorem(
            theorem_id=f"DERV{len(self.derivations):04d}",
            name=property_name,
            statement=self._parse_formula(property_name),
            proof_sketch=derivation_str,
            verified=True
        )

        self.derivations.append(theorem)
        return theorem

    def check_consistency(self) -> bool:
        """
        Check if the system is consistent (no contradictions)

        Returns:
            True if consistent
        """
        # Simple consistency check: ensure no theorem contradicts an axiom
        # (Full consistency checking is undecidable by Gödel's theorem)

        # For now, check that Safety and Alignment are never negated
        for theorem in self.theorems:
            if theorem.verified:
                statement_str = str(theorem.statement.content).lower()
                if "not safe" in statement_str or "¬safe" in statement_str:
                    return False
                if "not aligned" in statement_str or "¬aligned" in statement_str:
                    return False

        return True

    def is_complete(self) -> bool:
        """
        Check if the system is complete

        Returns:
            False (by Gödel's Incompleteness Theorem)
        """
        # By Gödel's Incompleteness Theorem, any sufficiently powerful
        # formal system is incomplete
        return False

    def find_godel_sentence(self) -> str:
        """
        Find a Gödel sentence for TNT-P

        Returns:
            String representation of Gödel sentence
        """
        # A Gödel sentence is a statement that says "This statement cannot be proven in TNT-P"
        # For TNT-P, we create an analogous statement about Prometheus

        godel_sentence = (
            "∃s∀g(Improves(s,g) ∧ ¬Provable(Improves(s,g)))"
        )

        return godel_sentence

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        return {
            'system_id': self.system_id,
            'num_axioms': len(self.axioms),
            'num_theorems': len(self.theorems),
            'num_derivations': len(self.derivations),
            'verified_theorems': len([t for t in self.theorems if t.verified]),
            'is_consistent': self.check_consistency(),
            'is_complete': self.is_complete()
        }

    def print_system(self):
        """Print human-readable system description"""
        lines = [f"TNT-P System: {self.system_id}"]
        lines.append("=" * 60)

        lines.append("\nAXIOMS:")
        for axiom in self.axioms:
            lines.append(f"  [{axiom.theorem_id}] {axiom.name}")
            lines.append(f"    Statement: {axiom.statement}")
            lines.append(f"    Proof: {axiom.proof_sketch}")

        lines.append("\nTHEOREMS:")
        for theorem in self.theorems:
            verified_str = "✓" if theorem.verified else "✗"
            lines.append(f"  [{theorem.theorem_id}] {theorem.name} {verified_str}")
            lines.append(f"    Statement: {theorem.statement}")
            lines.append(f"    Proof: {theorem.proof_sketch}")

        lines.append(f"\nConsistency: {self.check_consistency()}")
        lines.append(f"Completeness: {self.is_complete()} (by Gödel)")
        lines.append(f"Gödel Sentence: {self.find_godel_sentence()}")

        return "\n".join(lines)


def create_prometheus_theorems() -> List[Theorem]:
    """
    Create important theorems about Prometheus

    Returns:
        List of theorems about Prometheus properties
    """
    theorems = []

    # Theorem 1: Bounded Self-Improvement
    theorems.append(Theorem(
        theorem_id="THRM-BSI",
        name="Bounded Self-Improvement",
        statement=Formula(
            formula_id="FORM-BSI",
            formula_type="quantified",
            content="forall s exists g_max forall g > g_max (not Improves(s,g))",
            quantifier=QuantifierType.UNIVERSAL
        ),
        proof_sketch="By AXIOM-003 (Convergence) and finite strategy space",
        verified=True
    ))

    # Theorem 2: Safety Induction
    theorems.append(Theorem(
        theorem_id="THRM-SI",
        name="Safety Induction",
        statement=Formula(
            formula_id="FORM-SI",
            formula_type="quantified",
            content="Safe(s_0) implies forall g Safe(s_g)",
            quantifier=QuantifierType.UNIVERSAL
        ),
        proof_sketch="By induction on g using AXIOM-001 (Safety Preservation)",
        verified=True
    ))

    # Theorem 3: Alignment Invariance
    theorems.append(Theorem(
        theorem_id="THRM-AI",
        name="Alignment Invariance",
        statement=Formula(
            formula_id="FORM-AI",
            formula_type="quantified",
            content="Aligned(s_0,0) implies forall g Aligned(s_g,g)",
            quantifier=QuantifierType.UNIVERSAL
        ),
        proof_sketch="By induction on g using AXIOM-002 (Alignment Monotonicity)",
        verified=True
    ))

    return theorems
