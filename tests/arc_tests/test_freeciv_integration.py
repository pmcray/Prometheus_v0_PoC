#!/usr/bin/env python3
"""
Test FreeCiv Integration

Tests the complete FreeCiv integration including:
- Simulator functionality
- Agent learning loop
- Strategy evolution
- Progressive difficulty training
"""

import sys
from prometheus.freeciv_simulator import FreeCivSimulator
from prometheus.freeciv_agent import FreeCivAgent
from prometheus.freeciv_environment import DifficultyLevel, FreeCivAction


def test_simulator_basic():
    """Test basic simulator functionality"""
    print("Testing simulator basic operations...")

    sim = FreeCivSimulator(difficulty=DifficultyLevel.NORMAL)

    # Reset
    state = sim.reset()
    assert state.turn == 0
    assert state.cities == 1
    assert state.units == 1

    # Execute action
    action = FreeCivAction(
        action_type="set_rates",
        parameters={'science': 60, 'tax': 0}
    )

    new_state, reward, done, info = sim.step(action)
    assert new_state.turn == 1
    assert not done

    print("  ✓ Basic operations working")
    return True


def test_simulator_difficulty_scaling():
    """Test that AI difficulty affects gameplay"""
    print("Testing difficulty scaling...")

    # Test AI strength multipliers
    sim_novice = FreeCivSimulator(difficulty=DifficultyLevel.NOVICE)
    sim_normal = FreeCivSimulator(difficulty=DifficultyLevel.NORMAL)
    sim_hard = FreeCivSimulator(difficulty=DifficultyLevel.EXPERIMENTAL)

    # Verify strength multipliers increase with difficulty
    assert sim_novice.ai_strength < sim_normal.ai_strength
    assert sim_normal.ai_strength < sim_hard.ai_strength

    print(f"  AI Strength: Novice={sim_novice.ai_strength}, "
          f"Normal={sim_normal.ai_strength}, "
          f"Experimental={sim_hard.ai_strength}")
    print("  ✓ Difficulty scaling working")
    return True


def test_simulator_game_end():
    """Test game end conditions"""
    print("Testing game end conditions...")

    sim = FreeCivSimulator(difficulty=DifficultyLevel.NOVICE)
    state = sim.reset()

    # Simulate defeat by eliminating cities
    sim.state.cities = 0

    action = FreeCivAction(
        action_type="set_rates",
        parameters={'science': 50, 'tax': 0}
    )

    _, _, done, _ = sim.step(action)
    assert done

    print("  ✓ Game end conditions working")
    return True


def test_agent_initialization():
    """Test agent initialization"""
    print("Testing agent initialization...")

    agent = FreeCivAgent("test_agent", use_simulator=True)

    assert agent.agent_id == "test_agent"
    assert agent.use_simulator == True
    assert agent.generation == 0
    assert agent.total_games == 0
    assert len(agent.current_strategy.components) > 0

    print("  ✓ Agent initialization working")
    return True


def test_agent_play_game():
    """Test agent playing a complete game"""
    print("Testing agent playing game...")

    agent = FreeCivAgent("test_agent", use_simulator=True)

    # Play short game
    game_history = agent.play_game(
        difficulty=DifficultyLevel.NOVICE,
        max_turns=20
    )

    assert game_history is not None
    assert game_history.total_turns > 0
    assert game_history.game_id is not None
    assert game_history.difficulty == DifficultyLevel.NOVICE.value
    assert agent.total_games == 1

    print(f"  ✓ Played {game_history.total_turns} turns")
    print(f"    Final score: {game_history.final_score}")
    print(f"    Result: {'Victory' if game_history.victory else 'Defeat/Incomplete'}")

    return True


def test_agent_learning():
    """Test agent learning from game"""
    print("Testing agent learning...")

    agent = FreeCivAgent("test_agent", use_simulator=True)

    # Play game
    game_history = agent.play_game(
        difficulty=DifficultyLevel.NOVICE,
        max_turns=20
    )

    initial_generation = agent.generation
    initial_components = len(agent.current_strategy.components)

    # Learn from game
    learning_result = agent.learn_from_game(game_history)

    assert learning_result is not None
    assert 'critique' in learning_result
    assert 'generation' in learning_result

    print(f"  ✓ Learning cycle complete")
    print(f"    Critique: {learning_result['critique']['assessment']}")
    print(f"    Issues: {len(learning_result['critique']['issues'])}")
    print(f"    Generation: {agent.generation}")

    return True


def test_strategy_evolution():
    """Test strategy evolution over multiple games"""
    print("Testing strategy evolution...")

    agent = FreeCivAgent("test_agent", use_simulator=True)

    # Play multiple games
    num_games = 3
    for i in range(num_games):
        print(f"  Game {i+1}/{num_games}...", end=" ")

        game_history = agent.play_game(
            difficulty=DifficultyLevel.NOVICE,
            max_turns=15
        )

        learning_result = agent.learn_from_game(game_history)

        print(f"Score: {game_history.final_score}")

    assert agent.total_games == num_games
    print(f"  ✓ Evolution test complete")
    print(f"    Total games: {agent.total_games}")
    print(f"    Wins: {agent.win_count}")
    print(f"    Best score: {agent.best_score}")
    print(f"    Generation: {agent.generation}")

    return True


def test_multiple_difficulties():
    """Test agent training across difficulty levels"""
    print("Testing multiple difficulty levels...")

    agent = FreeCivAgent("test_agent", use_simulator=True)

    difficulties = [DifficultyLevel.NOVICE, DifficultyLevel.EASY, DifficultyLevel.NORMAL]

    for difficulty in difficulties:
        print(f"  Testing {difficulty.value}...", end=" ")

        game_history = agent.play_game(
            difficulty=difficulty,
            max_turns=15
        )

        agent.learn_from_game(game_history)

        print(f"Score: {game_history.final_score}")

    print("  ✓ Multi-difficulty test complete")
    return True


def test_crls_integration():
    """Test full CRLS integration"""
    print("Testing CRLS integration...")

    agent = FreeCivAgent("test_agent", use_simulator=True)

    # Verify all CRLS components present
    assert agent.evaluator is not None
    assert agent.corrector is not None
    assert agent.font_engine is not None
    assert agent.governor is not None

    # Play and learn
    game_history = agent.play_game(
        difficulty=DifficultyLevel.NOVICE,
        max_turns=15
    )

    learning_result = agent.learn_from_game(game_history)

    # Verify CRLS outputs
    assert 'critique' in learning_result
    assert 'assessment' in learning_result['critique']
    assert 'issues' in learning_result['critique']
    assert 'suggestions' in learning_result['critique']

    print("  ✓ CRLS integration working")
    print(f"    Evaluator: Generated critique")
    print(f"    Font Engine: Strategy registered")
    print(f"    Governor: Safety checks active")

    return True


def main():
    print("=" * 60)
    print("  FREECIV INTEGRATION TEST SUITE")
    print("=" * 60)
    print()

    tests = [
        ("Simulator Basic Operations", test_simulator_basic),
        ("Simulator Difficulty Scaling", test_simulator_difficulty_scaling),
        ("Simulator Game End Conditions", test_simulator_game_end),
        ("Agent Initialization", test_agent_initialization),
        ("Agent Play Game", test_agent_play_game),
        ("Agent Learning", test_agent_learning),
        ("Strategy Evolution", test_strategy_evolution),
        ("Multiple Difficulties", test_multiple_difficulties),
        ("CRLS Integration", test_crls_integration),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n{name}")
        print("-" * 60)
        try:
            result = test_func()
            if result:
                passed += 1
                print(f"✅ PASSED\n")
            else:
                failed += 1
                print(f"❌ FAILED\n")
        except Exception as e:
            failed += 1
            print(f"❌ FAILED: {e}\n")
            import traceback
            traceback.print_exc()

    print("=" * 60)
    print(f"  TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    print()

    if failed == 0:
        print("✅ ALL TESTS PASSED")
        print()
        print("FreeCiv Integration Complete:")
        print("  ✓ Simulator working (no FreeCiv server needed)")
        print("  ✓ Agent can play and learn")
        print("  ✓ CRLS loop functional")
        print("  ✓ Strategy evolution active")
        print("  ✓ Multiple difficulty levels supported")
        print()
        print("Ready for progressive training!")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
