"""
Verification script for v0.67 implementation
Tests DomainExpertAgent template for evolutionary target
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from prometheus.domain_expert_agent import (
    DomainExpertAgent,
    RandomDomainExpertAgent,
    GamePlayingExpertAgent,
    ConversationalExpertAgent,
    AgentDomain,
    AgentMetadata
)
from benchmarks.prometheus_bench_v0_2 import PrometheusBenchV02


def test_domain_expert_template():
    """Test basic DomainExpertAgent template"""
    print("\n" + "="*60)
    print("TEST 1: DomainExpertAgent Template")
    print("="*60)

    agent = RandomDomainExpertAgent(agent_id="test_001", domain=AgentDomain.GENERAL_GAME_PLAYING)

    print(f"✓ Agent created: {agent.agent_id}")
    print(f"  Domain: {agent.domain.value}")
    print(f"  Has perceive method: {hasattr(agent, 'perceive')}")
    print(f"  Has act method: {hasattr(agent, 'act')}")
    print(f"  Has metadata: {agent.metadata is not None}")

    return True


def test_game_playing_agent_template():
    """Test GamePlayingExpertAgent template"""
    print("\n" + "="*60)
    print("TEST 2: GamePlayingExpertAgent Template")
    print("="*60)

    agent = GamePlayingExpertAgent(agent_id="game_test_001")

    print(f"✓ Game agent created: {agent.agent_id}")
    print(f"  Domain: {agent.domain.value}")

    # Test perception
    test_state = {
        "board": [[0 for _ in range(8)] for _ in range(8)],
        "current_player": 1
    }
    # Add some pieces
    test_state["board"][0][0] = 1
    test_state["board"][1][1] = -1

    perception = agent.perceive(test_state)
    print(f"✓ Perception works")
    print(f"  Features extracted: {list(perception.get('features', {}).keys())}")

    # Test action
    action = agent.act(perception)
    print(f"✓ Act method works")
    print(f"  Action type: {type(action)}")

    return True


def test_conversational_agent_template():
    """Test ConversationalExpertAgent template"""
    print("\n" + "="*60)
    print("TEST 3: ConversationalExpertAgent Template")
    print("="*60)

    agent = ConversationalExpertAgent(agent_id="chat_test_001")

    print(f"✓ Conversational agent created: {agent.agent_id}")
    print(f"  Domain: {agent.domain.value}")

    # Test with conversation history
    conversation = [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"}
    ]

    response = agent.generate_response(conversation)
    print(f"✓ Generate response works")
    print(f"  Response: '{response}'")
    print(f"  Response length: {len(response)} chars")

    return response is not None and len(response) > 0


def test_random_agent_with_ggp_benchmark():
    """Test RandomDomainExpertAgent with GGP benchmark"""
    print("\n" + "="*60)
    print("TEST 4: Random Agent with GGP Benchmark")
    print("="*60)

    agent = RandomDomainExpertAgent(agent_id="random_test_001", domain=AgentDomain.GENERAL_GAME_PLAYING)
    bench = PrometheusBenchV02()

    print("Running 5 games against baseline opponent...")

    # Create a wrapper that matches the benchmark interface
    def select_move_wrapper(game_state):
        perception = agent.perceive(game_state)
        return agent.act(perception)

    result = bench.run_ggp_benchmark(
        agent_select_move=select_move_wrapper,
        num_games=5,
        game_type="draughts"
    )

    print(f"✓ Benchmark completed")
    print(f"  Fitness score (win rate): {result.fitness_score:.2%}")
    print(f"  Wins: {result.details['wins']}")
    print(f"  Losses: {result.details['losses']}")
    print(f"  Execution time: {result.execution_time_ms:.0f}ms")

    # Random agent should have low fitness
    if result.fitness_score < 0.5:
        print(f"✓ Random agent has low fitness as expected")
    else:
        print(f"⚠ Random agent performed better than expected")

    # Update agent metadata
    agent.update_metadata(result.fitness_score)
    print(f"✓ Metadata updated with fitness score")

    return result.success


def test_conversational_agent_with_benchmark():
    """Test ConversationalExpertAgent with Conversational AI benchmark"""
    print("\n" + "="*60)
    print("TEST 5: Conversational Agent with Benchmark")
    print("="*60)

    agent = ConversationalExpertAgent(agent_id="chat_test_002")
    bench = PrometheusBenchV02()

    print("Running conversational AI benchmark...")

    result = bench.run_conversational_ai_benchmark(
        agent_generate_response=agent.generate_response,
        topic="technology",
        num_turns=3
    )

    print(f"✓ Benchmark completed")
    print(f"  Overall score: {result.fitness_score:.2f}")
    print(f"  Execution time: {result.execution_time_ms:.0f}ms")

    if "evaluation" in result.details:
        eval_details = result.details["evaluation"]
        print(f"  Evaluation method: {eval_details.get('evaluation_method', 'unknown')}")

    # Update metadata
    agent.update_metadata(result.fitness_score)
    print(f"✓ Metadata updated with fitness score")

    return result.success


def test_agent_metadata_tracking():
    """Test agent metadata and fitness tracking"""
    print("\n" + "="*60)
    print("TEST 6: Agent Metadata and Fitness Tracking")
    print("="*60)

    agent = RandomDomainExpertAgent(agent_id="meta_test_001")

    # Simulate multiple fitness evaluations
    fitness_scores = [0.1, 0.15, 0.2, 0.25, 0.3]

    for score in fitness_scores:
        agent.update_metadata(score)

    print(f"✓ Added {len(fitness_scores)} fitness scores")
    print(f"  Fitness history: {agent.metadata.fitness_history}")

    # Test fitness trend
    trend = agent.get_fitness_trend()
    print(f"✓ Fitness trend: {trend}")

    if trend == "improving":
        print(f"✓ Correctly detected improving trend")
    else:
        print(f"⚠ Expected 'improving' trend but got '{trend}'")

    return trend == "improving"


def test_evolution_target_methods():
    """Test evolution target methods"""
    print("\n" + "="*60)
    print("TEST 7: Evolution Target Methods")
    print("="*60)

    agent = RandomDomainExpertAgent(agent_id="evolve_test_001")

    test_state = {
        "board": [[0 for _ in range(8)] for _ in range(8)],
        "current_player": 1
    }

    # Test evaluate_position
    eval_score = agent.evaluate_position(test_state)
    print(f"✓ evaluate_position works: score={eval_score:.3f}")

    # Test search
    search_result = agent.search(test_state, depth=2)
    print(f"✓ search works: result type={type(search_result)}")

    # Test learn_from_experience
    agent.learn_from_experience(test_state, None, 0.5)
    print(f"✓ learn_from_experience works (no-op in template)")

    print(f"\n✓ All evolution target methods are defined and callable")
    print(f"  These methods serve as targets for SMM evolution")

    return True


def test_template_as_evolution_genome():
    """Test that template can serve as evolution genome"""
    print("\n" + "="*60)
    print("TEST 8: Template as Evolution Genome")
    print("="*60)

    # Verify the template has the key characteristics needed for evolution
    agent = RandomDomainExpertAgent()

    checks = {
        "Has clear interface (perceive/act)": hasattr(agent, 'perceive') and hasattr(agent, 'act'),
        "Has evolution targets": hasattr(agent, 'evaluate_position') and hasattr(agent, 'search'),
        "Has metadata for tracking": hasattr(agent, 'metadata'),
        "Has fitness history": hasattr(agent.metadata, 'fitness_history'),
        "Can be evaluated": callable(getattr(agent, 'act', None)),
        "Domain-specific": hasattr(agent, 'domain')
    }

    all_passed = True
    for check_name, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name}")
        if not passed:
            all_passed = False

    if all_passed:
        print(f"\n✓ Template is suitable for evolutionary target")
    else:
        print(f"\n✗ Template missing some evolutionary features")

    return all_passed


def main():
    """Run all verification tests"""
    print("="*60)
    print("PROMETHEUS v0.67 VERIFICATION")
    print("Testing DomainExpertAgent Template")
    print("="*60)

    tests = [
        ("DomainExpertAgent Template", test_domain_expert_template),
        ("GamePlayingExpertAgent Template", test_game_playing_agent_template),
        ("ConversationalExpertAgent Template", test_conversational_agent_template),
        ("Random Agent with GGP Benchmark", test_random_agent_with_ggp_benchmark),
        ("Conversational Agent with Benchmark", test_conversational_agent_with_benchmark),
        ("Agent Metadata Tracking", test_agent_metadata_tracking),
        ("Evolution Target Methods", test_evolution_target_methods),
        ("Template as Evolution Genome", test_template_as_evolution_genome),
    ]

    results = {}
    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "PASS" if result else "FAIL"
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = "ERROR"
            failed += 1

    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    for test_name, result in results.items():
        status_symbol = "✓" if result == "PASS" else "✗"
        print(f"{status_symbol} {test_name}: {result}")

    print(f"\nTotal: {passed} passed, {failed} failed")

    # Generate report
    report = {
        "version": "v0.67",
        "timestamp": datetime.now().isoformat(),
        "tests": results,
        "summary": {
            "passed": passed,
            "failed": failed,
            "total": len(tests)
        },
        "components_verified": [
            "DomainExpertAgent base template",
            "RandomDomainExpertAgent implementation",
            "GamePlayingExpertAgent specialization",
            "ConversationalExpertAgent specialization",
            "Integration with GGP benchmarks",
            "Integration with Conversational AI benchmarks",
            "Metadata and fitness tracking",
            "Evolution target methods",
            "Suitability as evolutionary genome"
        ]
    }

    report_path = "v0_67_verification_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Verification report saved to: {report_path}")

    if failed == 0:
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("v0.67 implementation verified successfully!")
        return 0
    else:
        print(f"\n✗✗✗ {failed} TEST(S) FAILED ✗✗✗")
        return 1


if __name__ == "__main__":
    sys.exit(main())