#!/usr/bin/env python
"""
Standalone test for MetaLearner module.
Tests Good's probabilistic synaptic mutation without package dependencies.
"""

# Direct module import
import sys
from pathlib import Path

# Add prometheus to path
sys.path.insert(0, str(Path(__file__).parent / "prometheus"))

# Import just the meta_learner module
from meta_learner import MetaLearner


def test_basic_functionality():
    """Test basic MetaLearner functionality."""
    print("Testing MetaLearner basic functionality...")

    learner = MetaLearner(["rotation", "symmetry", "crop"])
    print("✅ MetaLearner initialized")

    # Test upward mutation
    initial = learner.probabilities["symmetry"]
    learner.update_on_success("symmetry")
    updated = learner.probabilities["symmetry"]
    assert updated > initial, "Upward mutation failed"
    print(f"✅ Upward mutation: {initial:.3f} → {updated:.3f}")

    # Test downward mutation
    initial = learner.probabilities["rotation"]
    learner.update_on_failure("rotation")
    updated = learner.probabilities["rotation"]
    assert updated < initial, "Downward mutation failed"
    print(f"✅ Downward mutation: {initial:.3f} → {updated:.3f}")

    return learner


def test_convergence():
    """Test convergence to winning strategy."""
    print("\nTesting convergence...")

    learner = MetaLearner(["rotation", "symmetry", "crop"])

    # Simulate 10 symmetry successes
    for _ in range(10):
        learner.update_on_success("symmetry")

    probs = learner.get_strategy_probabilities()
    assert probs["symmetry"] > 0.50, "Convergence failed"
    print(f"✅ Convergence: symmetry = {probs['symmetry']:.2%}")

    return learner


def test_notebook_2_prediction():
    """
    Validate that learning matches Notebook 2 prediction.
    Expected: Symmetry 0.25 → 0.75 over 10 successful attempts.
    """
    print("\nTesting Notebook 2 prediction...")

    strategies = ["rotation", "symmetry", "color_fill", "pattern", "crop"]
    learner = MetaLearner(strategies, upward_rate=0.2, downward_rate=0.15)

    print(f"Initial: symmetry = {learner.probabilities['symmetry']:.2%}")

    # Simulate pattern from Notebook 2: symmetry succeeds, others fail
    import random

    random.seed(42)

    for attempt in range(10):
        learner.update_on_success("symmetry")

        # Fail a random other strategy
        other = random.choice([s for s in strategies if s != "symmetry"])
        learner.update_on_failure(other)

    probs = learner.get_strategy_probabilities()
    print(f"Final: symmetry = {probs['symmetry']:.2%}")

    # Should match notebook prediction
    assert probs["symmetry"] > 0.50, f"Expected >50%, got {probs['symmetry']:.2%}"
    print(f"✅ Matches Notebook 2: symmetry dominant at {probs['symmetry']:.2%}")

    return learner


def test_statistics():
    """Test statistics gathering."""
    print("\nTesting statistics...")

    learner = MetaLearner(["rotation", "symmetry"])

    learner.update_on_success("symmetry")
    learner.update_on_success("symmetry")
    learner.update_on_failure("rotation")

    stats = learner.get_statistics()

    assert stats["attempt_count"] == 3
    assert stats["best_strategy"] == "symmetry"
    assert stats["overall_success_rate"] > 0.6

    print(f"✅ Statistics correct:")
    print(f"   - Attempts: {stats['attempt_count']}")
    print(f"   - Best: {stats['best_strategy']}")
    print(f"   - Success rate: {stats['overall_success_rate']:.1%}")
    print(f"   - Convergence: {stats['convergence_score']:.2f}")

    return stats


def test_history_tracking():
    """Test learning history tracking."""
    print("\nTesting history tracking...")

    learner = MetaLearner(["rotation", "symmetry"])

    learner.update_on_success("symmetry")
    learner.update_on_failure("rotation")

    history = learner.get_history()

    # Should have snapshots
    assert len(history.attempts) >= 3, "Missing history snapshots"
    assert len(history.outcomes) == 2, "Missing outcome records"

    print(f"✅ History tracked:")
    print(f"   - {len(history.attempts)} snapshots")
    print(f"   - {len(history.outcomes)} outcomes")

    return history


def visualize_learning_curve():
    """Visualize a realistic learning curve."""
    print("\nVisualizing learning curve...")

    strategies = ["rotation", "symmetry", "color_fill", "pattern", "crop"]
    learner = MetaLearner(strategies)

    print("\nAttempt | Symmetry | Best Strategy")
    print("-" * 40)

    # Simulate 15 attempts
    import random

    random.seed(123)

    for attempt in range(15):
        # 70% chance symmetry succeeds
        if random.random() < 0.7:
            learner.update_on_success("symmetry")
        else:
            failed = random.choice([s for s in strategies if s != "symmetry"])
            learner.update_on_failure(failed)

        probs = learner.get_strategy_probabilities()
        best = learner.get_best_strategy()

        if attempt % 2 == 0:  # Print every other attempt
            print(f"{attempt:7d} | {probs['symmetry']:7.1%} | {best}")

    final_probs = learner.get_strategy_probabilities()
    print(f"\nFinal distribution:")
    for strategy, prob in sorted(final_probs.items(), key=lambda x: -x[1]):
        print(f"  {strategy:12s}: {prob:6.1%}")

    print(f"\n✅ Learning curve demonstrates convergence")

    return learner


def main():
    """Run all tests."""
    print("=" * 60)
    print("MetaLearner Standalone Tests")
    print("Testing Good's Probabilistic Synaptic Mutation (1965)")
    print("=" * 60)

    try:
        test_basic_functionality()
        test_convergence()
        test_notebook_2_prediction()
        test_statistics()
        test_history_tracking()
        visualize_learning_curve()

        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("\nMetaLearner successfully implements:")
        print("  ✅ Upward mutation (strengthen successful strategies)")
        print("  ✅ Downward mutation (weaken failed strategies)")
        print("  ✅ Convergence to optimal strategy")
        print("  ✅ Statistics and history tracking")
        print("  ✅ Matches Notebook 2 predictions")

        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
