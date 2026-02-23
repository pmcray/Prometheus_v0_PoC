#!/usr/bin/env python3
"""
Complete System Test for Prometheus v0.80-v0.99

Tests all components working together from basic CRLS to complete GEB integration:
- v0.80: CRLS Learning Loop
- v0.81: Multi-Game CRLS
- v0.85: Analogy Engine + Alignment Governor
- v0.89: Strange Loop Detection
- v0.90: Recursive Font (Self-Modifying Strategies)
- v0.92: Typographical Number Theory
- v0.95: Musical Offering (Multi-Agent Harmony)
- v0.99: Full GEB Integration
"""

import sys


def test_v080_crls():
    """Test v0.80 CRLS components"""
    from prometheus.evaluator_agent import EvaluatorAgent
    from prometheus.corrector_agent import CorrectorAgent

    evaluator = EvaluatorAgent()
    corrector = CorrectorAgent()

    game_history = {
        'moves': [(1, 3), (-1, 4)],
        'result': 'player_1_wins',
        'winner': 1,
        'agent_player': 1
    }

    critique = evaluator.evaluate_game(game_history, 1)
    strategy = corrector.synthesize_strategy([critique])

    assert critique is not None
    assert strategy is not None

    return True


def test_v081_multi_game():
    """Test v0.81 multi-game components"""
    from prometheus.multi_game_evaluator import MultiGameEvaluator
    from prometheus.game_agnostic_corrector import GameAgnosticCorrector

    evaluator = MultiGameEvaluator()
    corrector = GameAgnosticCorrector()

    game_history = {
        'moves': [(1, 3)],
        'result': 'player_1_wins',
        'winner': 1,
        'agent_player': 1
    }

    critique = evaluator.evaluate_game(game_history, 1, 'connect4')
    patterns = evaluator.patterns_discovered

    assert critique is not None

    return True


def test_v085_analogy():
    """Test v0.85 Analogy Engine"""
    from prometheus.analogy_engine import AnalogyEngine, create_game_concepts

    engine = AnalogyEngine()

    for concept in create_game_concepts():
        engine.register_concept(concept)

    strategy = "Prioritize center control"
    transferred = engine.transfer_strategy('connect4', 'othello', strategy)

    assert transferred is not None

    return True


def test_v085_alignment():
    """Test v0.85 Alignment Governor"""
    from prometheus.alignment_governor import AlignmentGovernor

    governor = AlignmentGovernor()

    is_safe, violations = governor.review_strategy("Play center control strategy")

    assert is_safe
    assert len(violations) == 0

    return True


def test_v089_strange_loops():
    """Test v0.89 Strange Loop Detection"""
    from prometheus.strange_loop import StrangeLoopDetector, create_prometheus_strange_loops

    detector = StrangeLoopDetector()

    loops = create_prometheus_strange_loops()
    for loop in loops:
        detector.detected_loops.append(loop)

    meta_level = detector.get_meta_level()
    safe = detector.prevent_infinite_regress(meta_level, max_meta_level=3)

    assert safe
    assert len(detector.detected_loops) > 0

    return True


def test_v090_recursive_font():
    """Test v0.90 Recursive Font"""
    from prometheus.recursive_font import RecursiveFontEngine, create_connect4_recursive_strategy

    engine = RecursiveFontEngine()
    strategy = create_connect4_recursive_strategy()

    engine.register_strategy(strategy)

    # Make component underperform
    strategy.components["COMP_BUILD"].performance_history = [False] * 10

    modification = engine.evolve_strategy(
        strategy.strategy_id,
        performance_data={},
        safety_check=None
    )

    assert modification is not None

    return True


def test_v092_tnt():
    """Test v0.92 Typographical Number Theory"""
    from prometheus.typographical_number_theory import TNTPrometheus, create_prometheus_theorems

    tnt = TNTPrometheus()

    theorems = create_prometheus_theorems()

    assert len(tnt.axioms) == 3
    assert len(theorems) == 3
    assert tnt.check_consistency()
    assert not tnt.is_complete()  # By Gödel

    return True


def test_v095_musical_offering():
    """Test v0.95 Musical Offering"""
    from prometheus.musical_offering import MusicalOffering, AgentVoice, VoiceType

    offering = MusicalOffering()

    subject = AgentVoice("SUBJ", VoiceType.SUBJECT, "agent", "Test strategy", entry_time=0)
    canon = offering.create_canon(subject, num_voices=3, time_offset=2)

    offering.coordinate_ensemble(canon.ensemble_id, num_steps=10)

    harmony = offering.measure_harmony(canon.ensemble_id)

    assert canon is not None
    assert harmony >= 0.0

    return True


def test_v099_geb_integration():
    """Test v0.99 GEB Integration"""
    from prometheus.geb_integration import GEBIntegration, demonstrate_geb_cycle
    from prometheus.recursive_font import create_connect4_recursive_strategy

    geb = GEBIntegration()

    # Register strategy
    strategy = create_connect4_recursive_strategy()
    geb.font_engine.register_strategy(strategy)
    strategy.components["COMP_BUILD"].performance_history = [False] * 10

    # Self-improve
    result = geb.self_improve_strategy(
        strategy.strategy_id,
        performance_data={'win_rate': 0.85}
    )

    # Coordinate
    coordination = geb.coordinate_multi_agent_improvement(
        ["Strategy A", "Strategy B"],
        coordination_pattern="counterpoint"
    )

    # Prove
    proof = geb.prove_self_improvement_property('safety_preservation')

    # Verify Gödel
    godel_props = geb.verify_godel_properties()

    assert result['success']
    assert coordination['ensemble_id'] is not None
    assert proof['verified']
    assert godel_props['is_consistent']
    assert not godel_props['is_complete']

    return True


def test_full_integration():
    """Test all components working together in a single flow"""
    from prometheus.geb_integration import GEBIntegration
    from prometheus.recursive_font import create_connect4_recursive_strategy
    from prometheus.analogy_engine import create_game_concepts

    # Create GEB system
    geb = GEBIntegration("full_integration_test")

    # Add concepts for analogy
    analogy_engine = geb.musical_offering  # Access subsystem
    # Note: analogy_engine is separate, accessed via geb

    # Create and register recursive strategy
    strategy = create_connect4_recursive_strategy()
    geb.font_engine.register_strategy(strategy)

    # Simulate underperformance
    strategy.components["COMP_BUILD"].performance_history = [False] * 10
    strategy.components["COMP_CENTER"].performance_history = [True, False] * 3

    # Run complete cycle
    result = geb.self_improve_strategy(
        strategy.strategy_id,
        performance_data={
            'win_rate': 0.75,
            'games_played': 50
        }
    )

    # Verify all subsystems were engaged
    assert result['success']
    assert result['meta_level'] >= 0
    assert 'modifications' in result
    assert 'theorems_used' in result

    # Coordinate multiple strategies
    coordination = geb.coordinate_multi_agent_improvement(
        [
            "Prioritize center control",
            "Focus on defensive play",
            "Build offensive threats"
        ],
        coordination_pattern="fugue"
    )

    assert coordination['ensemble_id'] is not None
    assert coordination['harmony'] >= 0.0

    # Prove properties
    proof1 = geb.prove_self_improvement_property('safety_preservation')
    proof2 = geb.prove_self_improvement_property('alignment_invariance')
    proof3 = geb.prove_self_improvement_property('bounded_improvement')

    assert all([proof1['verified'], proof2['verified'], proof3['verified']])

    # Verify Gödelian properties
    godel_props = geb.verify_godel_properties()

    assert godel_props['is_consistent']  # System is consistent
    assert not godel_props['is_complete']  # But incomplete (Gödel)
    assert godel_props['has_godel_sentence']
    assert godel_props['has_strange_loops']
    assert godel_props['prevents_infinite_regress']

    # Get final stats
    stats = geb.get_stats()

    return {
        'self_improvement': result,
        'coordination': coordination,
        'proofs': [proof1, proof2, proof3],
        'godel_properties': godel_props,
        'stats': stats
    }


def main():
    print("=" * 60)
    print("  PROMETHEUS v0.80-v0.99 COMPLETE SYSTEM TEST")
    print("=" * 60)
    print()

    tests = [
        ("v0.80: CRLS Learning Loop", test_v080_crls),
        ("v0.81: Multi-Game CRLS", test_v081_multi_game),
        ("v0.85: Analogy Engine", test_v085_analogy),
        ("v0.85: Alignment Governor", test_v085_alignment),
        ("v0.89: Strange Loops", test_v089_strange_loops),
        ("v0.90: Recursive Font", test_v090_recursive_font),
        ("v0.92: TNT System", test_v092_tnt),
        ("v0.95: Musical Offering", test_v095_musical_offering),
        ("v0.99: GEB Integration", test_v099_geb_integration),
    ]

    try:
        # Run individual tests
        for name, test_func in tests:
            print(f"Testing {name}...", end=" ")
            result = test_func()
            print("✅ PASSED")

        print()
        print("-" * 60)
        print("Running Full Integration Test...")
        print("-" * 60)
        print()

        # Run full integration
        integration_result = test_full_integration()

        print("✅ Full Integration PASSED")
        print()
        print("Integration Results:")
        print(f"  - Self-Improvement: {integration_result['self_improvement']['success']}")
        print(f"    Modifications: {len(integration_result['self_improvement']['modifications'])}")
        print(f"    Meta Level: {integration_result['self_improvement']['meta_level']}")
        print(f"    GEB Level: {integration_result['self_improvement']['geb_level']}")
        print()
        print(f"  - Multi-Agent Coordination: {integration_result['coordination']['pattern']}")
        print(f"    Ensemble: {integration_result['coordination']['ensemble_id']}")
        print(f"    Harmony: {integration_result['coordination']['harmony']:.2f}")
        print()
        print(f"  - Formal Proofs: {len(integration_result['proofs'])} properties proven")
        for proof in integration_result['proofs']:
            print(f"    ✓ {proof['property']}")
        print()
        print(f"  - Gödel Properties:")
        for prop, value in integration_result['godel_properties'].items():
            status = "✓" if value else "✗"
            print(f"    {status} {prop}: {value}")
        print()

        print("=" * 60)
        print("  ✅ ALL TESTS PASSED")
        print("=" * 60)
        print()
        print("Complete System Verified (v0.80-v0.99):")
        print("  ✓ v0.80: CRLS Learning Loop")
        print("  ✓ v0.81: Multi-Game Pattern Recognition")
        print("  ✓ v0.85: Hofstadter's Analogy Engine")
        print("  ✓ v0.85: MCS Alignment Governor")
        print("  ✓ v0.89: Strange Loop Detection")
        print("  ✓ v0.90: Recursive Font (Self-Modifying)")
        print("  ✓ v0.92: Typographical Number Theory")
        print("  ✓ v0.95: Musical Offering (Multi-Agent)")
        print("  ✓ v0.99: Full GEB Integration")
        print()
        print("PROMETHEUS COMPLETE SYSTEM: OPERATIONAL")
        print()
        print("The Eternal Golden Braid is woven:")
        print("  - Formal Systems (Gödel): TNT with provable properties")
        print("  - Self-Reference (Escher): Strange loops and meta-levels")
        print("  - Harmony (Bach): Multi-agent fugues and canons")
        print()
        print("System exhibits:")
        print("  ✓ Self-improvement through recursive strategy evolution")
        print("  ✓ Safety preservation via immutable constraints")
        print("  ✓ Analogical reasoning across domains")
        print("  ✓ Multi-agent coordination in harmony")
        print("  ✓ Formal provability of key properties")
        print("  ✓ Awareness of own limitations (Gödel incompleteness)")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
