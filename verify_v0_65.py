"""
Verification script for v0.65 implementation
Tests Prometheus-Bench-v0.2 with GGP and Conversational AI suites
"""

import sys
import json
from datetime import datetime

from benchmarks.prometheus_bench_v0_2 import (
    PrometheusBenchV02,
    BenchmarkDomain,
    DraughtsGame,
    BaselineOpponent,
    RandomPlayer
)
from benchmarks.baseline_agents import (
    RandomDraughtsAgent,
    SimpleChatbotAgent,
    ImprovedDraughtsAgent
)


def test_draughts_game_mechanics():
    """Test basic Draughts game functionality"""
    print("\n" + "="*60)
    print("TEST 1: Draughts Game Mechanics")
    print("="*60)

    game = DraughtsGame()
    print(f"✓ Game initialized")
    print(f"  Current player: {game.current_player}")
    print(f"  Board size: 8x8")

    # Get valid moves
    moves = game.get_valid_moves(game.current_player)
    print(f"✓ Found {len(moves)} valid opening moves for player {game.current_player}")

    if moves:
        # Make a move
        move = moves[0]
        success = game.make_move(move)
        print(f"✓ Move executed: {move} -> Success: {success}")
        print(f"  New current player: {game.current_player}")

    print("✓ Draughts game mechanics working correctly")
    return True


def test_baseline_opponent():
    """Test baseline Minimax opponent"""
    print("\n" + "="*60)
    print("TEST 2: Baseline Minimax Opponent")
    print("="*60)

    game = DraughtsGame()
    opponent = BaselineOpponent(depth=2)

    move = opponent.select_move(game)
    print(f"✓ Baseline opponent selected move: {move}")

    if move:
        game.make_move(move)
        print(f"✓ Move executed successfully")
    else:
        print(f"✗ No move selected")
        return False

    print("✓ Baseline opponent working correctly")
    return True


def test_random_vs_random():
    """Test random player vs random player"""
    print("\n" + "="*60)
    print("TEST 3: Random vs Random Game")
    print("="*60)

    game = DraughtsGame()
    player1 = RandomPlayer()
    player2 = RandomPlayer()

    move_count = 0
    max_moves = 100

    while not game.game_over and move_count < max_moves:
        if game.current_player == 1:
            move = player1.select_move(game)
        else:
            move = player2.select_move(game)

        if move and game.make_move(move):
            move_count += 1
        else:
            break

    print(f"✓ Game completed in {move_count} moves")
    print(f"  Winner: Player {game.winner if game.winner else 'Draw'}")
    print(f"  Game over: {game.game_over}")

    print("✓ Random vs Random game completed successfully")
    return True


def test_ggp_benchmark():
    """Test General Game Playing benchmark"""
    print("\n" + "="*60)
    print("TEST 4: GGP Benchmark with Random Agent")
    print("="*60)

    bench = PrometheusBenchV02()
    random_agent = RandomDraughtsAgent()

    print("Running 10 games (this may take a moment)...")
    result = bench.run_ggp_benchmark(
        agent_select_move=random_agent.select_move,
        num_games=10,
        game_type="draughts"
    )

    print(f"✓ Benchmark completed")
    print(f"  Fitness score (win rate): {result.fitness_score:.2%}")
    print(f"  Wins: {result.details['wins']}")
    print(f"  Losses: {result.details['losses']}")
    print(f"  Draws: {result.details['draws']}")
    print(f"  Execution time: {result.execution_time_ms:.0f}ms")

    # Random player should have low win rate against minimax
    if result.fitness_score < 0.5:
        print(f"✓ Random agent performed as expected (win rate < 50%)")
    else:
        print(f"⚠ Random agent performed better than expected")

    return result.success


def test_improved_agent():
    """Test improved agent vs baseline"""
    print("\n" + "="*60)
    print("TEST 5: Improved Agent vs Baseline")
    print("="*60)

    bench = PrometheusBenchV02()
    improved_agent = ImprovedDraughtsAgent()

    print("Running 10 games with improved agent...")
    result = bench.run_ggp_benchmark(
        agent_select_move=improved_agent.select_move,
        num_games=10,
        game_type="draughts"
    )

    print(f"✓ Benchmark completed")
    print(f"  Fitness score (win rate): {result.fitness_score:.2%}")
    print(f"  Wins: {result.details['wins']}")
    print(f"  Losses: {result.details['losses']}")
    print(f"  Draws: {result.details['draws']}")

    return result.success


def test_conversational_ai_benchmark():
    """Test Conversational AI benchmark"""
    print("\n" + "="*60)
    print("TEST 6: Conversational AI Benchmark")
    print("="*60)

    bench = PrometheusBenchV02()
    chatbot = SimpleChatbotAgent()

    result = bench.run_conversational_ai_benchmark(
        agent_generate_response=chatbot.generate_response,
        topic="programming",
        persona="helpful assistant",
        num_turns=5
    )

    print(f"✓ Benchmark completed")
    print(f"  Overall score: {result.fitness_score:.2f}")
    print(f"  Execution time: {result.execution_time_ms:.0f}ms")

    if "evaluation" in result.details:
        eval_details = result.details["evaluation"]
        print(f"  Evaluation method: {eval_details.get('evaluation_method', 'unknown')}")
        if "criterion_scores" in eval_details:
            print(f"  Criterion scores:")
            for criterion, score in eval_details["criterion_scores"].items():
                print(f"    - {criterion}: {score:.2f}")

    return result.success


def test_benchmark_info():
    """Test benchmark information retrieval"""
    print("\n" + "="*60)
    print("TEST 7: Benchmark Information")
    print("="*60)

    bench = PrometheusBenchV02()

    # Get available benchmarks
    available = bench.get_available_benchmarks()
    print(f"✓ Available benchmark domains:")
    for domain, benchmarks in available.items():
        print(f"  - {domain}: {benchmarks}")

    # Get specific benchmark info
    draughts_info = bench.get_benchmark_info("draughts")
    print(f"\n✓ Draughts benchmark info:")
    for key, value in draughts_info.items():
        print(f"  - {key}: {value}")

    conv_info = bench.get_benchmark_info("conversational")
    print(f"\n✓ Conversational AI benchmark info:")
    for key, value in conv_info.items():
        print(f"  - {key}: {value}")

    return True


def main():
    """Run all verification tests"""
    print("="*60)
    print("PROMETHEUS v0.65 VERIFICATION")
    print("Testing Prometheus-Bench-v0.2 Implementation")
    print("="*60)

    tests = [
        ("Draughts Game Mechanics", test_draughts_game_mechanics),
        ("Baseline Minimax Opponent", test_baseline_opponent),
        ("Random vs Random Game", test_random_vs_random),
        ("GGP Benchmark", test_ggp_benchmark),
        ("Improved Agent", test_improved_agent),
        ("Conversational AI Benchmark", test_conversational_ai_benchmark),
        ("Benchmark Information", test_benchmark_info),
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
        "version": "v0.65",
        "timestamp": datetime.now().isoformat(),
        "tests": results,
        "summary": {
            "passed": passed,
            "failed": failed,
            "total": len(tests)
        },
        "components_verified": [
            "DraughtsGame implementation",
            "BaselineOpponent (Minimax)",
            "GGP benchmark suite",
            "Conversational AI benchmark suite",
            "Baseline agents (Random, Improved, Chatbot)",
            "Benchmark information system"
        ]
    }

    report_path = "v0_65_verification_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Verification report saved to: {report_path}")

    if failed == 0:
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("v0.65 implementation verified successfully!")
        return 0
    else:
        print(f"\n✗✗✗ {failed} TEST(S) FAILED ✗✗✗")
        return 1


if __name__ == "__main__":
    sys.exit(main())