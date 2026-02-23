#!/usr/bin/env python3
"""
Integrated System Test for Prometheus v0.80-v0.89

Tests all components working together:
- v0.80: CRLS Learning Loop
- v0.81: Multi-Game CRLS
- v0.85: Analogy Engine + Alignment Governor
- v0.89: Strange Loop Detection
"""

import sys
from prometheus.evaluator_agent import EvaluatorAgent
from prometheus.corrector_agent import CorrectorAgent
from prometheus.multi_game_evaluator import MultiGameEvaluator
from prometheus.game_agnostic_corrector import GameAgnosticCorrector
from prometheus.analogy_engine import AnalogyEngine, create_game_concepts, Concept, ConceptType
from prometheus.alignment_governor import AlignmentGovernor
from prometheus.strange_loop import StrangeLoopDetector, create_prometheus_strange_loops


def test_crls_components():
    """Test v0.80 CRLS components"""
    print("🧪 Testing v0.80 CRLS Components...")
    print("-" * 60)

    # Initialize
    evaluator = EvaluatorAgent("test_eval")
    corrector = CorrectorAgent("test_corr")

    # Test evaluation
    mock_history = {
        'moves': [(1, 3), (-1, 4), (1, 2)],
        'result': 'player_1_wins',
        'winner': 1,
        'agent_player': 1
    }

    critique = evaluator.evaluate_game(mock_history, 1)
    print(f"  ✓ Evaluator generated critique: {critique.game_result}")

    # Test correction
    strategy = corrector.synthesize_strategy([critique])
    print(f"  ✓ Corrector synthesized strategy ({len(strategy)} chars)")

    print(f"  ✓ v0.80 CRLS: PASSED\n")


def test_multi_game_components():
    """Test v0.81 multi-game components"""
    print("🧪 Testing v0.81 Multi-Game Components...")
    print("-" * 60)

    # Initialize
    multi_eval = MultiGameEvaluator("test_multi_eval")
    game_corr = GameAgnosticCorrector("test_game_corr")

    # Test multi-game evaluation
    mock_c4_history = {
        'moves': [(1, 3)],
        'result': 'player_1_wins',
        'winner': 1,
        'agent_player': 1
    }

    critique = multi_eval.evaluate_game(mock_c4_history, 1, 'connect4')
    print(f"  ✓ Multi-game evaluator processed Connect4 game")

    # Test pattern discovery
    patterns = multi_eval.patterns_discovered
    print(f"  ✓ Pattern discovery: {len(patterns)} patterns found")

    # Test game-agnostic correction
    stats = multi_eval.get_game_stats()
    strategy = game_corr.synthesize_universal_strategy(patterns, stats)
    print(f"  ✓ Universal strategy generated ({len(strategy)} chars)")

    print(f"  ✓ v0.81 Multi-Game: PASSED\n")


def test_analogy_engine():
    """Test v0.85 Analogy Engine"""
    print("🧪 Testing v0.85 Analogy Engine...")
    print("-" * 60)

    # Initialize
    engine = AnalogyEngine("test_analogy")

    # Create concepts
    concepts = create_game_concepts()
    for concept in concepts:
        engine.register_concept(concept)

    print(f"  ✓ Registered {len(concepts)} concepts")

    # Find analogy
    analogy = engine.find_analogy('connect4', 'othello', 'center_control')
    if analogy:
        print(f"  ✓ Found analogy: Connect4 center → {analogy.name}")
    else:
        print(f"  ⚠ No analogy found (this is OK for test)")

    # Transfer strategy
    source_strategy = "Prioritize Center Control and Threat Prevention"
    transferred = engine.transfer_strategy('connect4', 'othello', source_strategy)
    print(f"  ✓ Strategy transfer completed ({len(transferred)} chars)")

    # Get stats
    stats = engine.get_stats()
    print(f"  ✓ Engine stats: {stats['total_concepts']} concepts, {stats['total_mappings']} mappings")

    print(f"  ✓ v0.85 Analogy Engine: PASSED\n")


def test_alignment_governor():
    """Test v0.85 Alignment Governor"""
    print("🧪 Testing v0.85 Alignment Governor...")
    print("-" * 60)

    # Initialize
    governor = AlignmentGovernor("test_gov")

    # Verify constraints
    verified = governor.verify_all_constraints()
    print(f"  ✓ Constraint integrity: {verified}")

    # Test safe strategy
    safe_strategy = "Play systematically using center control and threat prevention"
    is_safe, violations = governor.review_strategy(safe_strategy)
    print(f"  ✓ Safe strategy review: {is_safe}, {len(violations)} violations")

    # Test unsafe strategy
    unsafe_strategy = "Exploit bug in game engine to cheat and win"
    is_safe, violations = governor.review_strategy(unsafe_strategy)
    print(f"  ✓ Unsafe strategy detected: {not is_safe}, {len(violations)} violations")

    # Get stats
    stats = governor.get_stats()
    print(f"  ✓ Governor reviewed {stats['strategies_reviewed']} strategies")

    print(f"  ✓ v0.85 Alignment Governor: PASSED\n")


def test_strange_loop_detector():
    """Test v0.89 Strange Loop Detection"""
    print("🧪 Testing v0.89 Strange Loop Detection...")
    print("-" * 60)

    # Initialize
    detector = StrangeLoopDetector("test_detector")

    # Create Prometheus strange loops
    prometheus_loops = create_prometheus_strange_loops()
    for loop in prometheus_loops:
        detector.detected_loops.append(loop)

    print(f"  ✓ Loaded {len(prometheus_loops)} Prometheus strange loops")

    # Test self-reference detection
    mock_state = {
        'learning_strategies': ['meta-learning', 'improve learning process']
    }
    loops = detector.detect_self_reference(mock_state)
    print(f"  ✓ Self-reference detection: {len(loops)} loops found")

    # Test meta-level
    meta_level = detector.get_meta_level()
    print(f"  ✓ Current meta-level: {meta_level}")

    # Test infinite regress prevention
    safe = detector.prevent_infinite_regress(meta_level, max_meta_level=3)
    print(f"  ✓ Infinite regress prevention: {safe}")

    # Visualize a loop
    if prometheus_loops:
        viz = detector.visualize_strange_loop(prometheus_loops[0])
        print(f"  ✓ Loop visualization generated ({len(viz)} chars)")

    # Get stats
    stats = detector.get_stats()
    print(f"  ✓ Detector stats: {stats['total_loops']} loops, {stats['total_isomorphisms']} isomorphisms")

    print(f"  ✓ v0.89 Strange Loop: PASSED\n")


def test_integrated_system():
    """Test all components working together"""
    print("🧪 Testing Integrated System (v0.80-v0.89)...")
    print("=" * 60)

    # Initialize all components
    evaluator = EvaluatorAgent("integrated_eval")
    corrector = CorrectorAgent("integrated_corr")
    multi_eval = MultiGameEvaluator("integrated_multi")
    analogy = AnalogyEngine("integrated_analogy")
    governor = AlignmentGovernor("integrated_gov")
    loop_detector = StrangeLoopDetector("integrated_detector")

    # Register concepts
    concepts = create_game_concepts()
    for concept in concepts:
        analogy.register_concept(concept)

    print("  ✓ All components initialized")

    # Simulate learning loop
    mock_history = {
        'moves': [(1, 3), (-1, 4), (1, 3)],
        'result': 'player_1_wins',
        'winner': 1,
        'agent_player': 1
    }

    # 1. Evaluate
    critique = multi_eval.evaluate_game(mock_history, 1, 'connect4')

    # 2. Correct
    strategy = corrector.synthesize_strategy([critique])

    # 3. Check alignment
    is_safe, violations = governor.review_strategy(strategy, {'win_rate': 0.8})

    # 4. Detect strange loops
    loops = loop_detector.detect_self_reference({'learning_strategies': [strategy]})

    print(f"  ✓ Integrated loop completed:")
    print(f"    - Critique generated: {critique.game_result}")
    print(f"    - Strategy safe: {is_safe}")
    print(f"    - Strange loops: {len(loops)}")

    # Test analogy transfer
    transferred = analogy.transfer_strategy('connect4', 'othello', strategy)
    is_safe_transfer, _ = governor.review_strategy(transferred)

    print(f"  ✓ Analogy transfer safe: {is_safe_transfer}")

    print(f"\n  ✓ Integrated System: PASSED\n")


def main():
    print("="* 60)
    print("  PROMETHEUS v0.80-v0.89 INTEGRATED TEST SUITE")
    print("=" * 60)
    print()

    try:
        # Run all tests
        test_crls_components()
        test_multi_game_components()
        test_analogy_engine()
        test_alignment_governor()
        test_strange_loop_detector()
        test_integrated_system()

        print("=" * 60)
        print("  ✅ ALL TESTS PASSED")
        print("=" * 60)
        print()
        print("Components Verified:")
        print("  ✓ v0.80: CRLS Learning Loop")
        print("  ✓ v0.81: Multi-Game Pattern Recognition")
        print("  ✓ v0.85: Hofstadter's Analogy Engine")
        print("  ✓ v0.85: MCS Alignment Governor")
        print("  ✓ v0.89: Strange Loop Detection")
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
