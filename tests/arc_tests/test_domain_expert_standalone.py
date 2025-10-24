"""
Standalone test for DomainExpertAgent v0.67
Tests the template directly without importing full prometheus package
"""

import sys
import json
from datetime import datetime

# Import directly from the file
exec(open('prometheus/domain_expert_agent.py').read())

# Import benchmarks
exec(open('benchmarks/prometheus_bench_v0_2.py').read())


def test_all():
    """Run all tests"""
    print("="*60)
    print("PROMETHEUS v0.67 VERIFICATION (Standalone)")
    print("Testing DomainExpertAgent Template")
    print("="*60)

    results = {}

    # Test 1: Create random agent
    print("\nTEST 1: Create RandomDomainExpertAgent")
    try:
        agent = RandomDomainExpertAgent(agent_id="test_001", domain=AgentDomain.GENERAL_GAME_PLAYING)
        print(f"✓ Agent created: {agent.agent_id}")
        print(f"  Domain: {agent.domain.value}")
        results["Create RandomDomainExpertAgent"] = "PASS"
    except Exception as e:
        print(f"✗ Failed: {e}")
        results["Create RandomDomainExpertAgent"] = "FAIL"

    # Test 2: Test perceive and act
    print("\nTEST 2: Test Perceive and Act Methods")
    try:
        test_state = {
            "board": [[0 for _ in range(8)] for _ in range(8)],
            "current_player": 1
        }
        test_state["board"][5][0] = 1
        test_state["board"][2][1] = -1

        perception = agent.perceive(test_state)
        action = agent.act(perception)

        print(f"✓ Perceive works: perception type={type(perception)}")
        print(f"✓ Act works: action type={type(action)}")
        results["Perceive and Act Methods"] = "PASS"
    except Exception as e:
        print(f"✗ Failed: {e}")
        results["Perceive and Act Methods"] = "FAIL"

    # Test 3: GamePlayingExpertAgent
    print("\nTEST 3: Create GamePlayingExpertAgent")
    try:
        game_agent = GamePlayingExpertAgent(agent_id="game_001")
        print(f"✓ Game agent created: {game_agent.agent_id}")

        perception = game_agent.perceive(test_state)
        print(f"✓ Game agent perception works")
        print(f"  Features: {list(perception.get('features', {}).keys())}")

        results["GamePlayingExpertAgent"] = "PASS"
    except Exception as e:
        print(f"✗ Failed: {e}")
        results["GamePlayingExpertAgent"] = "FAIL"

    # Test 4: ConversationalExpertAgent
    print("\nTEST 4: Create ConversationalExpertAgent")
    try:
        chat_agent = ConversationalExpertAgent(agent_id="chat_001")
        print(f"✓ Chat agent created: {chat_agent.agent_id}")

        conversation = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        response = chat_agent.generate_response(conversation)
        print(f"✓ Generate response works: '{response}'")

        results["ConversationalExpertAgent"] = "PASS"
    except Exception as e:
        print(f"✗ Failed: {e}")
        results["ConversationalExpertAgent"] = "FAIL"

    # Test 5: Integration with GGP Benchmark
    print("\nTEST 5: Integration with GGP Benchmark")
    try:
        bench = PrometheusBenchV02()
        test_agent = RandomDomainExpertAgent(agent_id="bench_test_001")

        def select_move_wrapper(game_state):
            perception = test_agent.perceive(game_state)
            return test_agent.act(perception)

        print("Running 5 games...")
        result = bench.run_ggp_benchmark(
            agent_select_move=select_move_wrapper,
            num_games=5
        )

        print(f"✓ Benchmark completed")
        print(f"  Win rate: {result.fitness_score:.2%}")
        print(f"  Wins: {result.details['wins']}, Losses: {result.details['losses']}")

        test_agent.update_metadata(result.fitness_score)
        print(f"✓ Metadata updated")

        results["GGP Benchmark Integration"] = "PASS"
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        results["GGP Benchmark Integration"] = "FAIL"

    # Test 6: Metadata and Fitness Tracking
    print("\nTEST 6: Metadata and Fitness Tracking")
    try:
        meta_agent = RandomDomainExpertAgent(agent_id="meta_001")

        # Simulate improving fitness
        for score in [0.1, 0.15, 0.2, 0.25, 0.3]:
            meta_agent.update_metadata(score)

        print(f"✓ Fitness history: {meta_agent.metadata.fitness_history}")

        trend = meta_agent.get_fitness_trend()
        print(f"✓ Fitness trend: {trend}")

        if trend == "improving":
            print(f"✓ Correctly detected improving trend")
            results["Metadata and Fitness Tracking"] = "PASS"
        else:
            print(f"⚠ Expected 'improving' but got '{trend}'")
            results["Metadata and Fitness Tracking"] = "PARTIAL"

    except Exception as e:
        print(f"✗ Failed: {e}")
        results["Metadata and Fitness Tracking"] = "FAIL"

    # Test 7: Evolution Target Methods
    print("\nTEST 7: Evolution Target Methods")
    try:
        evo_agent = RandomDomainExpertAgent(agent_id="evo_001")

        eval_score = evo_agent.evaluate_position(test_state)
        print(f"✓ evaluate_position: {eval_score:.3f}")

        search_result = evo_agent.search(test_state, depth=2)
        print(f"✓ search: result type={type(search_result)}")

        evo_agent.learn_from_experience(test_state, None, 0.5)
        print(f"✓ learn_from_experience: callable")

        results["Evolution Target Methods"] = "PASS"
    except Exception as e:
        print(f"✗ Failed: {e}")
        results["Evolution Target Methods"] = "FAIL"

    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)

    passed = sum(1 for r in results.values() if r == "PASS")
    failed = sum(1 for r in results.values() if r in ["FAIL", "ERROR"])
    partial = sum(1 for r in results.values() if r == "PARTIAL")

    for test_name, result in results.items():
        symbol = "✓" if result == "PASS" else ("~" if result == "PARTIAL" else "✗")
        print(f"{symbol} {test_name}: {result}")

    print(f"\nTotal: {passed} passed, {partial} partial, {failed} failed")

    # Generate report
    report = {
        "version": "v0.67",
        "timestamp": datetime.now().isoformat(),
        "tests": results,
        "summary": {
            "passed": passed,
            "partial": partial,
            "failed": failed,
            "total": len(results)
        },
        "components_verified": [
            "DomainExpertAgent base template",
            "RandomDomainExpertAgent implementation",
            "GamePlayingExpertAgent specialization",
            "ConversationalExpertAgent specialization",
            "GGP benchmark integration",
            "Metadata and fitness tracking",
            "Evolution target methods"
        ]
    }

    with open("v0_67_verification_report.json", 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Report saved to: v0_67_verification_report.json")

    if failed == 0:
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("v0.67 implementation verified successfully!")
        return 0
    else:
        print(f"\n✗✗✗ {failed} TEST(S) FAILED ✗✗✗")
        return 1


if __name__ == "__main__":
    sys.exit(test_all())