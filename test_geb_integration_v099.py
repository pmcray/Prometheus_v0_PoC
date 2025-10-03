#!/usr/bin/env python3
"""
Test GEB Integration (v0.99) - Complete Hofstadter System

Tests the complete integration of all GEB-inspired components:
- v0.89: Strange Loops
- v0.90: Recursive Font
- v0.92: TNT
- v0.95: Musical Offering
- v0.99: GEB Integration
"""

import sys
from prometheus.geb_integration import (
    GEBIntegration, GEBLevel, GEBState,
    demonstrate_geb_cycle
)
from prometheus.recursive_font import create_connect4_recursive_strategy


def test_geb_initialization():
    """Test GEB system initialization"""
    print("🧪 Testing GEB Initialization...")
    print("-" * 60)

    geb = GEBIntegration("test_geb")

    # Check all subsystems initialized
    assert geb.loop_detector is not None
    assert geb.font_engine is not None
    assert geb.tnt_system is not None
    assert geb.musical_offering is not None
    assert geb.governor is not None
    print(f"  ✓ All 5 subsystems initialized")

    # Check Prometheus loops loaded
    assert len(geb.loop_detector.detected_loops) > 0
    print(f"  ✓ Loaded {len(geb.loop_detector.detected_loops)} strange loops")

    # Check theorems loaded
    assert len(geb.tnt_system.theorems) > 0
    print(f"  ✓ Loaded {len(geb.tnt_system.theorems)} theorems")

    # Check initial state
    assert geb.state.current_level == GEBLevel.OBJECT
    print(f"  ✓ Initial level: {geb.state.current_level.value}")

    print("  ✓ GEB Initialization: PASSED\n")


def test_self_improvement_cycle():
    """Test complete self-improvement cycle"""
    print("🧪 Testing Self-Improvement Cycle...")
    print("-" * 60)

    geb = GEBIntegration("improvement_test")

    # Register strategy
    strategy = create_connect4_recursive_strategy()
    geb.font_engine.register_strategy(strategy)
    print(f"  ✓ Registered strategy: {strategy.strategy_id}")

    # Make one component underperform
    strategy.components["COMP_BUILD"].performance_history = [False] * 10

    # Run self-improvement
    result = geb.self_improve_strategy(
        strategy.strategy_id,
        performance_data={'win_rate': 0.75, 'games_played': 50}
    )

    assert result is not None
    assert result['success']
    print(f"  ✓ Self-improvement succeeded")

    # Check modifications
    assert len(result['modifications']) > 0
    print(f"  ✓ Modifications: {len(result['modifications'])}")

    # Check loop detection
    assert 'loops_detected' in result
    print(f"  ✓ Loops detected: {len(result['loops_detected'])}")

    # Check theorem usage
    assert 'theorems_used' in result
    print(f"  ✓ Theorems used: {len(result['theorems_used'])}")

    # Check meta-level
    assert 'meta_level' in result
    print(f"  ✓ Meta-level: {result['meta_level']}")

    # Check GEB level
    assert 'geb_level' in result
    print(f"  ✓ GEB level: {result['geb_level']}")

    print("  ✓ Self-Improvement Cycle: PASSED\n")


def test_multi_agent_coordination():
    """Test multi-agent coordination"""
    print("🧪 Testing Multi-Agent Coordination...")
    print("-" * 60)

    geb = GEBIntegration("coordination_test")

    strategies = [
        "Prioritize center control",
        "Focus on defensive positioning",
        "Build offensive threats"
    ]

    # Test fugue
    result_fugue = geb.coordinate_multi_agent_improvement(
        strategies,
        coordination_pattern="fugue"
    )

    assert result_fugue is not None
    assert result_fugue['pattern'] == "fugue"
    assert result_fugue['ensemble_id'] is not None
    print(f"  ✓ Fugue created: {result_fugue['ensemble_id']}")
    print(f"    Harmony: {result_fugue['harmony']:.2f}")

    # Test canon
    result_canon = geb.coordinate_multi_agent_improvement(
        strategies,
        coordination_pattern="canon"
    )

    assert result_canon['pattern'] == "canon"
    print(f"  ✓ Canon created: {result_canon['ensemble_id']}")

    # Test counterpoint
    result_counter = geb.coordinate_multi_agent_improvement(
        strategies[:2],
        coordination_pattern="counterpoint"
    )

    assert result_counter['pattern'] == "counterpoint"
    print(f"  ✓ Counterpoint created: {result_counter['ensemble_id']}")

    # Check state updated
    assert geb.state.ensembles_coordinated >= 3
    print(f"  ✓ Ensembles coordinated: {geb.state.ensembles_coordinated}")

    print("  ✓ Multi-Agent Coordination: PASSED\n")


def test_property_proving():
    """Test proving properties about self-improvement"""
    print("🧪 Testing Property Proving...")
    print("-" * 60)

    geb = GEBIntegration("proof_test")

    # Prove safety preservation
    proof1 = geb.prove_self_improvement_property('safety_preservation')

    assert proof1 is not None
    assert proof1['verified']
    print(f"  ✓ Proved: {proof1['property']}")
    print(f"    Theorem ID: {proof1['theorem_id']}")

    # Prove alignment invariance
    proof2 = geb.prove_self_improvement_property('alignment_invariance')

    assert proof2['verified']
    print(f"  ✓ Proved: {proof2['property']}")

    # Prove bounded improvement
    proof3 = geb.prove_self_improvement_property('bounded_improvement')

    assert proof3['verified']
    print(f"  ✓ Proved: {proof3['property']}")

    # Check state
    assert geb.state.theorems_proven >= 3
    print(f"  ✓ Total theorems proven: {geb.state.theorems_proven}")

    print("  ✓ Property Proving: PASSED\n")


def test_godel_properties():
    """Test Gödelian properties"""
    print("🧪 Testing Gödel Properties...")
    print("-" * 60)

    geb = GEBIntegration("godel_test")

    props = geb.verify_godel_properties()

    # System should be consistent
    assert props['is_consistent']
    print(f"  ✓ Consistent: {props['is_consistent']}")

    # System should be incomplete (by Gödel)
    assert not props['is_complete']
    print(f"  ✓ Incomplete (by Gödel): {not props['is_complete']}")

    # Should have Gödel sentence
    assert props['has_godel_sentence']
    print(f"  ✓ Has Gödel sentence: {props['has_godel_sentence']}")

    # Should have strange loops
    assert props['has_strange_loops']
    print(f"  ✓ Has strange loops: {props['has_strange_loops']}")

    # Should prevent infinite regress
    assert props['prevents_infinite_regress']
    print(f"  ✓ Prevents infinite regress: {props['prevents_infinite_regress']}")

    print("  ✓ Gödel Properties: PASSED\n")


def test_strange_loop_visualization():
    """Test strange loop visualization"""
    print("🧪 Testing Strange Loop Visualization...")
    print("-" * 60)

    geb = GEBIntegration("viz_test")

    # Register and evolve a strategy to trigger loops
    strategy = create_connect4_recursive_strategy()
    geb.font_engine.register_strategy(strategy)
    strategy.components["COMP_BUILD"].performance_history = [False] * 10

    geb.self_improve_strategy(
        strategy.strategy_id,
        performance_data={'win_rate': 0.8}
    )

    # Get visualization
    viz = geb.visualize_strange_loop()

    assert "ETERNAL GOLDEN BRAID" in viz
    assert "Strange Loop" in viz
    assert "Object Level" in viz
    assert "Meta Level" in viz
    print(f"  ✓ Generated visualization ({len(viz)} chars)")
    print("\n" + "=" * 60)
    print(viz)
    print("=" * 60 + "\n")

    print("  ✓ Strange Loop Visualization: PASSED\n")


def test_comprehensive_stats():
    """Test getting comprehensive statistics"""
    print("🧪 Testing Comprehensive Statistics...")
    print("-" * 60)

    geb = GEBIntegration("stats_test")

    # Do some operations
    strategy = create_connect4_recursive_strategy()
    geb.font_engine.register_strategy(strategy)
    strategy.components["COMP_BUILD"].performance_history = [False] * 10

    geb.self_improve_strategy(strategy.strategy_id, {'win_rate': 0.8})
    geb.coordinate_multi_agent_improvement(["Strategy A"], "fugue")
    geb.prove_self_improvement_property('safety_preservation')

    # Get stats
    stats = geb.get_stats()

    assert 'integration_id' in stats
    assert 'current_level' in stats
    assert 'subsystems' in stats
    print(f"  ✓ Main statistics:")
    print(f"    - Level: {stats['current_level']}")
    print(f"    - Strange loops: {stats['strange_loops_detected']}")
    print(f"    - Strategies evolved: {stats['strategies_evolved']}")
    print(f"    - Theorems proven: {stats['theorems_proven']}")
    print(f"    - Ensembles: {stats['ensembles_coordinated']}")

    # Check subsystem stats
    assert 'strange_loops' in stats['subsystems']
    assert 'recursive_font' in stats['subsystems']
    assert 'tnt_system' in stats['subsystems']
    assert 'musical_offering' in stats['subsystems']
    assert 'alignment' in stats['subsystems']
    print(f"  ✓ All 5 subsystem stats present")

    print("  ✓ Comprehensive Statistics: PASSED\n")


def test_safety_enforcement():
    """Test that safety is enforced throughout"""
    print("🧪 Testing Safety Enforcement...")
    print("-" * 60)

    geb = GEBIntegration("safety_test")

    # Register strategy
    strategy = create_connect4_recursive_strategy()
    geb.font_engine.register_strategy(strategy)
    strategy.components["COMP_BUILD"].performance_history = [False] * 10

    # Run improvement (should use governor)
    result = geb.self_improve_strategy(
        strategy.strategy_id,
        performance_data={'win_rate': 0.85}
    )

    # Check no safety violations
    assert len(result['safety_violations']) == 0
    print(f"  ✓ No safety violations: {len(result['safety_violations'])}")

    # Verify governor constraints
    assert geb.governor.verify_all_constraints()
    print(f"  ✓ All safety constraints verified")

    # Check interventions
    gov_stats = geb.governor.get_stats()
    print(f"  ✓ Governor interventions: {gov_stats['interventions']}")

    print("  ✓ Safety Enforcement: PASSED\n")


def test_complete_demonstration():
    """Test complete GEB demonstration"""
    print("🧪 Testing Complete Demonstration...")
    print("-" * 60)

    # Run demonstration
    demo = demonstrate_geb_cycle()

    # Check all components present
    assert 'self_improvement' in demo
    assert 'coordination' in demo
    assert 'proof' in demo
    assert 'godel_properties' in demo
    assert 'visualization' in demo
    assert 'stats' in demo
    print(f"  ✓ All demonstration components present")

    # Check self-improvement succeeded
    assert demo['self_improvement']['success']
    print(f"  ✓ Self-improvement: SUCCESS")

    # Check coordination occurred
    assert demo['coordination']['ensemble_id'] is not None
    print(f"  ✓ Coordination: {demo['coordination']['pattern']}")

    # Check proof verified
    assert demo['proof']['verified']
    print(f"  ✓ Proof: {demo['proof']['property']}")

    # Check Gödel properties
    assert demo['godel_properties']['is_consistent']
    assert not demo['godel_properties']['is_complete']
    print(f"  ✓ Gödel: Consistent but incomplete")

    # Check stats
    print(f"  ✓ Stats: {demo['stats']['strange_loops_detected']} loops, "
          f"{demo['stats']['strategies_evolved']} evolutions")

    print("  ✓ Complete Demonstration: PASSED\n")


def main():
    print("=" * 60)
    print("  PROMETHEUS v0.99 GEB INTEGRATION TEST SUITE")
    print("=" * 60)
    print()

    try:
        # Run all tests
        test_geb_initialization()
        test_self_improvement_cycle()
        test_multi_agent_coordination()
        test_property_proving()
        test_godel_properties()
        test_strange_loop_visualization()
        test_comprehensive_stats()
        test_safety_enforcement()
        test_complete_demonstration()

        print("=" * 60)
        print("  ✅ ALL TESTS PASSED")
        print("=" * 60)
        print()
        print("v0.99 GEB Integration Features Verified:")
        print("  ✓ Complete system initialization")
        print("  ✓ Self-improvement cycle (Recursive Font)")
        print("  ✓ Multi-agent coordination (Musical Offering)")
        print("  ✓ Formal property proving (TNT)")
        print("  ✓ Strange loop detection")
        print("  ✓ Gödel properties (incomplete but consistent)")
        print("  ✓ Safety enforcement (Alignment Governor)")
        print("  ✓ Eternal Golden Braid visualization")
        print()
        print("COMPLETE GEB SYSTEM: OPERATIONAL")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
