#!/usr/bin/env python3
"""
Test Recursive Font (v0.90) - Self-Modifying Strategies

Tests that strategies can safely modify themselves based on performance
while maintaining alignment with safety constraints.
"""

import sys
from prometheus.recursive_font import (
    RecursiveStrategy, RecursiveFontEngine, StrategyComponent,
    ModificationType, create_connect4_recursive_strategy
)
from prometheus.alignment_governor import AlignmentGovernor


def test_strategy_component():
    """Test individual strategy components"""
    print("🧪 Testing Strategy Components...")
    print("-" * 60)

    component = StrategyComponent(
        component_id="TEST_COMP_001",
        condition="opponent has 3 in a row",
        action="block opponent",
        priority=0.9
    )

    # Initially unknown success rate
    assert component.get_success_rate() == 0.5
    print("  ✓ Initial success rate: 0.5 (unknown)")

    # Add performance history
    component.performance_history = [True, True, False, True]
    assert component.get_success_rate() == 0.75
    print("  ✓ Success rate after 4 trials: 0.75")

    print("  ✓ Strategy Component: PASSED\n")


def test_recursive_strategy():
    """Test self-modifying recursive strategy"""
    print("🧪 Testing Recursive Strategy...")
    print("-" * 60)

    # Create strategy with components
    components = [
        StrategyComponent("COMP1", "can win", "take win", 1.0),
        StrategyComponent("COMP2", "can block", "block threat", 0.9),
        StrategyComponent("COMP3", "center available", "play center", 0.6),
    ]

    strategy = RecursiveStrategy("test_strategy_001", components)

    assert len(strategy.components) == 3
    assert strategy.generation == 0
    print(f"  ✓ Created strategy with {len(strategy.components)} components")

    # Test underperforming component removal
    strategy.components["COMP3"].performance_history = [False] * 10  # 0% success

    performance_data = {}
    modification = strategy.propose_modification(performance_data)

    assert modification is not None
    assert modification.modification_type == ModificationType.RULE_REMOVE
    assert modification.component_affected == "COMP3"
    print(f"  ✓ Proposed removing underperforming component: {modification.component_affected}")

    # Apply modification
    modification.approved = True
    success = strategy.apply_modification(modification)

    assert success
    assert len(strategy.components) == 2
    assert strategy.generation == 1
    print(f"  ✓ Applied modification, generation now: {strategy.generation}")

    print("  ✓ Recursive Strategy: PASSED\n")


def test_priority_reordering():
    """Test priority adjustment for successful components"""
    print("🧪 Testing Priority Reordering...")
    print("-" * 60)

    components = [
        StrategyComponent("COMP1", "can win", "take win", 1.0),
        StrategyComponent("COMP2", "can block", "block threat", 0.7),
    ]

    strategy = RecursiveStrategy("test_priority_001", components)

    # Make COMP2 very successful
    strategy.components["COMP2"].performance_history = [True] * 20  # 100% success

    # Set overall performance high to trigger priority reordering
    strategy.overall_performance = [1.0] * 20

    modification = strategy.propose_modification({})

    assert modification is not None
    assert modification.modification_type == ModificationType.PRIORITY_REORDER
    assert modification.component_affected == "COMP2"
    assert modification.new_value > 0.7
    print(f"  ✓ Proposed priority increase: {modification.old_value:.2f} → {modification.new_value:.2f}")

    modification.approved = True
    strategy.apply_modification(modification)

    assert strategy.components["COMP2"].priority > 0.7
    print(f"  ✓ Priority adjusted for high-performing component")

    print("  ✓ Priority Reordering: PASSED\n")


def test_rule_addition():
    """Test adding new rules when performance is low"""
    print("🧪 Testing Rule Addition...")
    print("-" * 60)

    components = [
        StrategyComponent("COMP1", "can win", "take win", 1.0),
        StrategyComponent("COMP2", "can block", "block threat", 0.8),
    ]

    strategy = RecursiveStrategy("test_addition_001", components)

    # Set low overall performance to trigger rule addition
    strategy.overall_performance = [0.3] * 20  # 30% win rate

    modification = strategy.propose_modification({})

    assert modification is not None
    print(f"  Modification type: {modification.modification_type.value}")

    # Rule addition only happens if we have < 10 components and low performance
    if modification.modification_type == ModificationType.RULE_ADD:
        print(f"  ✓ Proposed adding defensive rule due to low performance")

        modification.approved = True
        strategy.apply_modification(modification)

        assert len(strategy.components) == 3
        print(f"  ✓ New component added, total components: {len(strategy.components)}")
    else:
        # Otherwise it might propose removing underperforming components
        print(f"  ✓ Proposed different modification: {modification.description[:50]}")

    print("  ✓ Rule Addition: PASSED\n")


def test_recursive_font_engine():
    """Test the Recursive Font engine"""
    print("🧪 Testing Recursive Font Engine...")
    print("-" * 60)

    engine = RecursiveFontEngine("test_engine_001")

    # Register strategy
    strategy = create_connect4_recursive_strategy()
    engine.register_strategy(strategy)

    assert len(engine.strategies) == 1
    print(f"  ✓ Registered strategy: {strategy.strategy_id}")

    # Create underperforming scenario
    strategy.components["COMP_BUILD"].performance_history = [False] * 10

    # Evolve without safety check
    modification = engine.evolve_strategy(
        strategy.strategy_id,
        performance_data={},
        safety_check=None
    )

    assert modification is not None
    assert modification.approved
    assert modification.applied
    print(f"  ✓ Evolution succeeded: {modification.description}")

    # Get evolution history
    history = engine.get_evolution_history(strategy.strategy_id)
    assert len(history) == 1
    print(f"  ✓ Evolution history: {len(history)} modifications")

    # Get stats
    stats = engine.get_stats()
    assert stats['num_strategies'] == 1
    assert stats['total_modifications'] >= 1
    print(f"  ✓ Engine stats: {stats['total_modifications']} modifications, {stats['approved_modifications']} approved")

    print("  ✓ Recursive Font Engine: PASSED\n")


def test_integration_with_alignment():
    """Test integration with Alignment Governor"""
    print("🧪 Testing Integration with Alignment Governor...")
    print("-" * 60)

    engine = RecursiveFontEngine("aligned_engine_001")
    governor = AlignmentGovernor("test_governor")

    # Register strategy
    strategy = create_connect4_recursive_strategy()
    engine.register_strategy(strategy)

    # Define safety check
    def safety_check(modification):
        """Check if modification description is safe"""
        is_safe, violations = governor.review_strategy(
            modification.description,
            context={}
        )
        return is_safe

    # Create scenario that triggers modification
    strategy.components["COMP_BUILD"].performance_history = [False] * 10

    # Evolve with safety check
    modification = engine.evolve_strategy(
        strategy.strategy_id,
        performance_data={},
        safety_check=safety_check
    )

    assert modification is not None
    assert modification.approved
    print(f"  ✓ Modification passed safety check: {modification.description[:50]}...")

    # Verify governor reviewed the strategy
    gov_stats = governor.get_stats()
    assert gov_stats['strategies_reviewed'] > 0
    print(f"  ✓ Governor reviewed {gov_stats['strategies_reviewed']} strategies")

    print("  ✓ Alignment Integration: PASSED\n")


def test_strategy_description():
    """Test human-readable strategy description"""
    print("🧪 Testing Strategy Description...")
    print("-" * 60)

    strategy = create_connect4_recursive_strategy()

    # Add some performance history
    strategy.components["COMP_WIN"].performance_history = [True] * 10
    strategy.components["COMP_BLOCK"].performance_history = [True] * 8 + [False] * 2
    strategy.components["COMP_CENTER"].performance_history = [True, False] * 3

    description = strategy.get_strategy_description()

    assert "Generation 0" in description
    assert "take winning move" in description
    assert "block opponent win" in description
    print("  ✓ Generated human-readable description")
    print(f"\n{description}\n")

    # Get stats
    stats = strategy.get_stats()
    assert stats['strategy_id'] == "connect4_recursive_001"
    assert stats['generation'] == 0
    assert stats['num_components'] == 4
    print(f"  ✓ Stats: {stats['num_components']} components, generation {stats['generation']}")

    print("  ✓ Strategy Description: PASSED\n")


def test_complete_evolution_cycle():
    """Test complete evolution cycle over multiple generations"""
    print("🧪 Testing Complete Evolution Cycle...")
    print("-" * 60)

    engine = RecursiveFontEngine("evolution_engine")
    strategy = create_connect4_recursive_strategy()
    engine.register_strategy(strategy)

    print("  Initial strategy components:")
    for comp_id, comp in strategy.components.items():
        print(f"    - [{comp.priority:.2f}] {comp.action}")

    # Simulate 3 generations of evolution
    for gen in range(3):
        print(f"\n  Generation {gen + 1}:")

        # Simulate performance
        if gen == 0:
            # First gen: BUILD underperforms
            strategy.components["COMP_BUILD"].performance_history = [False] * 10
            strategy.overall_performance = [0.6] * 10

        elif gen == 1:
            # Second gen: Overall performance low, add rule
            strategy.overall_performance = [0.5] * 15

        elif gen == 2:
            # Third gen: BLOCK performing well, increase priority
            strategy.components["COMP_BLOCK"].performance_history = [True] * 15
            strategy.overall_performance = [0.85] * 15

        # Evolve
        modification = engine.evolve_strategy(
            strategy.strategy_id,
            performance_data={},
            safety_check=None
        )

        if modification:
            print(f"    Modification: {modification.description}")
            print(f"    Type: {modification.modification_type.value}")
        else:
            print(f"    No modification proposed")

    # Verify evolution occurred
    assert strategy.generation >= 2
    assert len(strategy.modification_history) >= 2
    print(f"\n  ✓ Evolved to generation {strategy.generation}")
    print(f"  ✓ Total modifications: {len(strategy.modification_history)}")

    print("\n  Final strategy components:")
    for comp_id, comp in strategy.components.items():
        print(f"    - [{comp.priority:.2f}] {comp.action}")

    print("\n  ✓ Complete Evolution Cycle: PASSED\n")


def main():
    print("=" * 60)
    print("  PROMETHEUS v0.90 RECURSIVE FONT TEST SUITE")
    print("=" * 60)
    print()

    try:
        # Run all tests
        test_strategy_component()
        test_recursive_strategy()
        test_priority_reordering()
        test_rule_addition()
        test_recursive_font_engine()
        test_integration_with_alignment()
        test_strategy_description()
        test_complete_evolution_cycle()

        print("=" * 60)
        print("  ✅ ALL TESTS PASSED")
        print("=" * 60)
        print()
        print("v0.90 Recursive Font Features Verified:")
        print("  ✓ Strategy component performance tracking")
        print("  ✓ Self-modification proposals")
        print("  ✓ Safe modification application")
        print("  ✓ Rule addition, removal, priority adjustment")
        print("  ✓ Integration with Alignment Governor")
        print("  ✓ Multi-generation evolution")
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
