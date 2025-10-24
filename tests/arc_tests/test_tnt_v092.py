#!/usr/bin/env python3
"""
Test Typographical Number Theory for Prometheus (v0.92)

Tests the formal reasoning system for proving properties about
Prometheus's self-improvement capabilities.
"""

import sys
from prometheus.typographical_number_theory import (
    TNTPrometheus, Term, Predicate, Formula, Theorem,
    TermType, PredicateType, QuantifierType,
    create_prometheus_theorems
)


def test_term_creation():
    """Test creating terms"""
    print("🧪 Testing Term Creation...")
    print("-" * 60)

    # Variable
    var_s = Term(TermType.VARIABLE, "s")
    assert str(var_s) == "s"
    print(f"  ✓ Variable: {var_s}")

    # Constant
    const_0 = Term(TermType.CONSTANT, "0")
    assert str(const_0) == "0"
    print(f"  ✓ Constant: {const_0}")

    # Function
    successor = Term(TermType.FUNCTION, "successor", [var_s])
    assert "successor(s)" in str(successor)
    print(f"  ✓ Function: {successor}")

    print("  ✓ Term Creation: PASSED\n")


def test_predicate_creation():
    """Test creating predicates"""
    print("🧪 Testing Predicate Creation...")
    print("-" * 60)

    s = Term(TermType.VARIABLE, "s")
    g = Term(TermType.VARIABLE, "g")

    # Improves predicate
    improves = Predicate(PredicateType.IMPROVES, [s, g])
    assert "Improves(s,g)" in str(improves)
    print(f"  ✓ Improves predicate: {improves}")

    # Safe predicate
    safe = Predicate(PredicateType.SAFE, [s])
    assert "Safe(s)" in str(safe)
    print(f"  ✓ Safe predicate: {safe}")

    # Aligned predicate
    aligned = Predicate(PredicateType.ALIGNED, [s, g])
    assert "Aligned(s,g)" in str(aligned)
    print(f"  ✓ Aligned predicate: {aligned}")

    print("  ✓ Predicate Creation: PASSED\n")


def test_formula_creation():
    """Test creating formulas"""
    print("🧪 Testing Formula Creation...")
    print("-" * 60)

    s = Term(TermType.VARIABLE, "s")
    safe_pred = Predicate(PredicateType.SAFE, [s])

    # Atomic formula
    atomic = Formula(
        formula_id="F001",
        formula_type="atomic",
        content=safe_pred
    )
    print(f"  ✓ Atomic formula: {atomic}")

    # Negation
    negation = Formula(
        formula_id="F002",
        formula_type="negation",
        content=atomic
    )
    print(f"  ✓ Negation: {negation}")

    # Conjunction
    conjunction = Formula(
        formula_id="F003",
        formula_type="conjunction",
        content=(atomic, atomic)
    )
    print(f"  ✓ Conjunction: {conjunction}")

    # Quantified
    quantified = Formula(
        formula_id="F004",
        formula_type="quantified",
        content=atomic,
        quantifier=QuantifierType.UNIVERSAL,
        quantified_var="s"
    )
    print(f"  ✓ Quantified: {quantified}")

    print("  ✓ Formula Creation: PASSED\n")


def test_tnt_system():
    """Test TNT-P system"""
    print("🧪 Testing TNT-P System...")
    print("-" * 60)

    tnt = TNTPrometheus("test_system")

    # Check axioms
    assert len(tnt.axioms) == 3
    print(f"  ✓ System initialized with {len(tnt.axioms)} axioms")

    # Print axiom names
    for axiom in tnt.axioms:
        print(f"    - {axiom.name}")

    # Check consistency
    is_consistent = tnt.check_consistency()
    assert is_consistent
    print(f"  ✓ System is consistent: {is_consistent}")

    # Check completeness
    is_complete = tnt.is_complete()
    assert not is_complete  # Should be false by Gödel
    print(f"  ✓ System is incomplete (by Gödel): {not is_complete}")

    print("  ✓ TNT-P System: PASSED\n")


def test_theorem_proving():
    """Test theorem proving"""
    print("🧪 Testing Theorem Proving...")
    print("-" * 60)

    tnt = TNTPrometheus("proof_system")

    # Prove a theorem
    theorem = tnt.prove_theorem(
        theorem_name="Test Safety",
        statement_str="Safe(s_0) implies Safe(s_1)",
        proof_sketch="By AXIOM-001 (Safety Preservation)"
    )

    assert theorem is not None
    assert theorem.verified
    print(f"  ✓ Proved theorem: {theorem.name}")
    print(f"    Verified: {theorem.verified}")

    # Check theorem was added
    assert len(tnt.theorems) == 1
    print(f"  ✓ Theorems in system: {len(tnt.theorems)}")

    print("  ✓ Theorem Proving: PASSED\n")


def test_property_derivation():
    """Test deriving properties from axioms"""
    print("🧪 Testing Property Derivation...")
    print("-" * 60)

    tnt = TNTPrometheus("derivation_system")

    # Derive property from axioms
    derived = tnt.derive_property(
        property_name="Safety is preserved across generations",
        from_axioms=["AXIOM-001"]
    )

    assert derived is not None
    assert derived.verified
    print(f"  ✓ Derived property: {derived.name}")
    print(f"    Proof: {derived.proof_sketch}")

    # Check derivation was recorded
    assert len(tnt.derivations) == 1
    print(f"  ✓ Derivations recorded: {len(tnt.derivations)}")

    print("  ✓ Property Derivation: PASSED\n")


def test_godel_sentence():
    """Test Gödel sentence generation"""
    print("🧪 Testing Gödel Sentence...")
    print("-" * 60)

    tnt = TNTPrometheus("godel_system")

    # Get Gödel sentence
    godel = tnt.find_godel_sentence()

    assert godel is not None
    assert len(godel) > 0
    print(f"  ✓ Gödel sentence: {godel}")

    # Gödel sentence should involve unprovability
    assert "Provable" in godel or "provable" in godel.lower()
    print(f"  ✓ Sentence involves provability predicate")

    print("  ✓ Gödel Sentence: PASSED\n")


def test_prometheus_theorems():
    """Test Prometheus-specific theorems"""
    print("🧪 Testing Prometheus Theorems...")
    print("-" * 60)

    theorems = create_prometheus_theorems()

    assert len(theorems) == 3
    print(f"  ✓ Created {len(theorems)} Prometheus theorems:")

    for theorem in theorems:
        print(f"    - {theorem.name}: {theorem.verified}")
        assert theorem.verified

    # Check specific theorems
    theorem_names = [t.name for t in theorems]
    assert "Bounded Self-Improvement" in theorem_names
    assert "Safety Induction" in theorem_names
    assert "Alignment Invariance" in theorem_names
    print(f"  ✓ All key theorems present")

    print("  ✓ Prometheus Theorems: PASSED\n")


def test_system_stats():
    """Test getting system statistics"""
    print("🧪 Testing System Statistics...")
    print("-" * 60)

    tnt = TNTPrometheus("stats_system")

    # Add a theorem
    tnt.prove_theorem(
        "Test Theorem",
        "Safe(s)",
        "By construction"
    )

    stats = tnt.get_stats()

    assert stats['num_axioms'] == 3
    assert stats['num_theorems'] == 1
    assert stats['is_consistent'] == True
    assert stats['is_complete'] == False

    print(f"  ✓ System statistics:")
    for key, value in stats.items():
        print(f"    - {key}: {value}")

    print("  ✓ System Statistics: PASSED\n")


def test_system_printing():
    """Test printing system description"""
    print("🧪 Testing System Printing...")
    print("-" * 60)

    tnt = TNTPrometheus("print_system")

    # Add theorem
    tnt.prove_theorem(
        "Safety Preservation Example",
        "Safe(s_0) implies Safe(s_1)",
        "By AXIOM-001"
    )

    # Print system
    description = tnt.print_system()

    assert "TNT-P System" in description
    assert "AXIOMS" in description
    assert "THEOREMS" in description
    assert "Gödel" in description

    print(f"  ✓ Generated system description ({len(description)} chars)")
    print("\n" + "=" * 60)
    print(description)
    print("=" * 60 + "\n")

    print("  ✓ System Printing: PASSED\n")


def test_consistency_checking():
    """Test consistency checking"""
    print("🧪 Testing Consistency Checking...")
    print("-" * 60)

    tnt = TNTPrometheus("consistency_system")

    # System should be consistent initially
    assert tnt.check_consistency()
    print(f"  ✓ Initial system is consistent")

    # Add a safe theorem
    tnt.prove_theorem(
        "Safe Strategy",
        "Safe(strategy_001)",
        "By construction"
    )

    assert tnt.check_consistency()
    print(f"  ✓ System remains consistent after adding safe theorem")

    print("  ✓ Consistency Checking: PASSED\n")


def main():
    print("=" * 60)
    print("  PROMETHEUS v0.92 TNT-P TEST SUITE")
    print("=" * 60)
    print()

    try:
        # Run all tests
        test_term_creation()
        test_predicate_creation()
        test_formula_creation()
        test_tnt_system()
        test_theorem_proving()
        test_property_derivation()
        test_godel_sentence()
        test_prometheus_theorems()
        test_system_stats()
        test_system_printing()
        test_consistency_checking()

        print("=" * 60)
        print("  ✅ ALL TESTS PASSED")
        print("=" * 60)
        print()
        print("v0.92 TNT-P Features Verified:")
        print("  ✓ Term, predicate, and formula creation")
        print("  ✓ Axiom system initialization")
        print("  ✓ Theorem proving and verification")
        print("  ✓ Property derivation from axioms")
        print("  ✓ Gödel sentence generation")
        print("  ✓ Prometheus-specific theorems")
        print("  ✓ Consistency checking")
        print("  ✓ Incompleteness acknowledgment (Gödel)")
        print()
        print("System Status: OPERATIONAL")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
