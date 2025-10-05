"""
Verification script for v0.66 implementation
Tests IEE tooling and environment integration for new benchmarks
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from prometheus.iee import IEEHarness


def test_iee_v04_initialization():
    """Test IEE v0.4 initialization with v0.2 benchmarks"""
    print("\n" + "="*60)
    print("TEST 1: IEE v0.4 Initialization")
    print("="*60)

    iee = IEEHarness(use_v02_benchmarks=True)
    print(f"✓ IEE initialized with v0.2 benchmarks")
    print(f"  v0.2 benchmarks enabled: {iee.use_v02_benchmarks}")
    print(f"  Benchmark suite v0.2: {iee.benchmark_suite_v02 is not None}")

    return True


def test_benchmark_info_retrieval():
    """Test benchmark information retrieval"""
    print("\n" + "="*60)
    print("TEST 2: Benchmark Information Retrieval")
    print("="*60)

    iee = IEEHarness(use_v02_benchmarks=True)

    # Get Draughts benchmark info
    draughts_info = iee.get_benchmark_by_name("draughts")
    print(f"✓ Draughts benchmark info retrieved:")
    for key, value in draughts_info.items():
        print(f"    {key}: {value}")

    # Get Conversational AI benchmark info
    conv_info = iee.get_benchmark_by_name("conversational")
    print(f"\n✓ Conversational AI benchmark info retrieved:")
    for key, value in conv_info.items():
        print(f"    {key}: {value}")

    return True


def test_ggp_benchmark_execution():
    """Test GGP benchmark execution through IEE"""
    print("\n" + "="*60)
    print("TEST 3: GGP Benchmark Execution via IEE")
    print("="*60)

    iee = IEEHarness(use_v02_benchmarks=True)

    # Create a temporary agent file
    temp_dir = tempfile.mkdtemp()
    agent_path = Path(temp_dir) / "test_agent.py"

    agent_code = '''
import random
from typing import Dict, List, Any, Optional, Tuple

class TestDraughtsAgent:
    """Test agent for verification"""

    def select_move(self, game_state: Dict[str, Any]) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Select a random valid move"""
        try:
            board = game_state["board"]
            current_player = game_state["current_player"]

            valid_moves = []
            for from_row in range(8):
                for from_col in range(8):
                    piece = board[from_row][from_col]
                    if (current_player == 1 and piece > 0) or (current_player == -1 and piece < 0):
                        moves = self._get_moves(board, from_row, from_col, piece)
                        valid_moves.extend(moves)

            return random.choice(valid_moves) if valid_moves else None
        except:
            return None

    def _get_moves(self, board, row, col, piece):
        moves = []
        is_king = abs(piece) == 2
        if piece > 0:
            directions = [(-1, -1), (-1, 1)]
            if is_king:
                directions.extend([(1, -1), (1, 1)])
        else:
            directions = [(1, -1), (1, 1)]
            if is_king:
                directions.extend([(-1, -1), (-1, 1)])

        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                if board[new_row][new_col] == 0:
                    moves.append(((row, col), (new_row, new_col)))

        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            capture_row, capture_col = row + dr, col + dc
            land_row, land_col = row + 2*dr, col + 2*dc
            if 0 <= land_row < 8 and 0 <= land_col < 8:
                if 0 <= capture_row < 8 and 0 <= capture_col < 8:
                    if board[land_row][land_col] == 0:
                        capture_piece = board[capture_row][capture_col]
                        if (piece > 0 and capture_piece < 0) or (piece < 0 and capture_piece > 0):
                            moves.append(((row, col), (land_row, land_col)))
        return moves
'''

    with open(agent_path, 'w') as f:
        f.write(agent_code)

    print(f"✓ Created test agent at {agent_path}")

    # Execute benchmark
    try:
        result = iee.execute_ggp_benchmark(
            agent_module_path=str(agent_path),
            num_games=5,  # Small number for quick test
            game_type="draughts"
        )

        print(f"✓ GGP benchmark executed via IEE")
        print(f"  Success: {result['success']}")
        print(f"  Fitness score: {result['fitness_score']:.2%}")
        print(f"  Execution time: {result['execution_time_ms']:.0f}ms")

        success = result['success']

    except Exception as e:
        print(f"✗ GGP benchmark execution failed: {e}")
        success = False

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)

    return success


def test_conversational_ai_benchmark_execution():
    """Test Conversational AI benchmark execution through IEE"""
    print("\n" + "="*60)
    print("TEST 4: Conversational AI Benchmark Execution via IEE")
    print("="*60)

    iee = IEEHarness(use_v02_benchmarks=True)

    # Create a temporary agent file
    temp_dir = tempfile.mkdtemp()
    agent_path = Path(temp_dir) / "test_chatbot.py"

    agent_code = '''
from typing import List, Dict

class TestChatbotAgent:
    """Test chatbot agent for verification"""

    def generate_response(self, conversation_history: List[Dict[str, str]]) -> str:
        """Generate a simple response"""
        user_messages = [msg for msg in conversation_history if msg["role"] == "user"]
        if not user_messages:
            return "Hello! How can I help you?"

        last_msg = user_messages[-1]["content"].lower()

        if "hello" in last_msg or "hi" in last_msg:
            return "Hello! I'm here to help."
        elif "thank" in last_msg:
            return "You're welcome!"
        else:
            return "That's a great question. Let me help you with that topic."
'''

    with open(agent_path, 'w') as f:
        f.write(agent_code)

    print(f"✓ Created test chatbot at {agent_path}")

    # Execute benchmark
    try:
        result = iee.execute_conversational_ai_benchmark(
            agent_module_path=str(agent_path),
            topic="general assistance",
            num_turns=3
        )

        print(f"✓ Conversational AI benchmark executed via IEE")
        print(f"  Success: {result['success']}")
        print(f"  Fitness score: {result['fitness_score']:.2f}")
        print(f"  Execution time: {result['execution_time_ms']:.0f}ms")

        success = result['success']

    except Exception as e:
        print(f"✗ Conversational AI benchmark execution failed: {e}")
        success = False

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)

    return success


def test_population_evaluation():
    """Test population evaluation"""
    print("\n" + "="*60)
    print("TEST 5: Population Evaluation")
    print("="*60)

    iee = IEEHarness(use_v02_benchmarks=True)

    # Create multiple temporary agents
    temp_dir = tempfile.mkdtemp()
    agent_paths = []

    base_agent_code = '''
import random
from typing import Dict, List, Any, Optional, Tuple

class PopulationAgent{agent_id}:
    def select_move(self, game_state: Dict[str, Any]) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        try:
            board = game_state["board"]
            current_player = game_state["current_player"]
            valid_moves = []
            for from_row in range(8):
                for from_col in range(8):
                    piece = board[from_row][from_col]
                    if (current_player == 1 and piece > 0) or (current_player == -1 and piece < 0):
                        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                            new_row, new_col = from_row + dr, from_col + dc
                            if 0 <= new_row < 8 and 0 <= new_col < 8:
                                if board[new_row][new_col] == 0:
                                    valid_moves.append(((from_row, from_col), (new_row, new_col)))
            return random.choice(valid_moves) if valid_moves else None
        except:
            return None
'''

    for i in range(3):
        agent_path = Path(temp_dir) / f"agent_{i}.py"
        with open(agent_path, 'w') as f:
            f.write(base_agent_code.format(agent_id=i))
        agent_paths.append(str(agent_path))

    print(f"✓ Created population of {len(agent_paths)} agents")

    # Evaluate population
    try:
        results = iee.evaluate_population(
            agent_population=agent_paths,
            benchmark_domain="ggp",
            num_games=3  # Small number for quick test
        )

        print(f"✓ Population evaluated")
        print(f"  Number of results: {len(results)}")

        for i, result in enumerate(results):
            print(f"    Agent {i}: fitness={result['fitness_score']:.2f}, success={result['success']}")

        success = len(results) == len(agent_paths)

    except Exception as e:
        print(f"✗ Population evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        success = False

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)

    return success


def main():
    """Run all verification tests"""
    print("="*60)
    print("PROMETHEUS v0.66 VERIFICATION")
    print("Testing IEE v0.4 Universal Benchmark Engine")
    print("="*60)

    tests = [
        ("IEE v0.4 Initialization", test_iee_v04_initialization),
        ("Benchmark Info Retrieval", test_benchmark_info_retrieval),
        ("GGP Benchmark Execution", test_ggp_benchmark_execution),
        ("Conversational AI Benchmark", test_conversational_ai_benchmark_execution),
        ("Population Evaluation", test_population_evaluation),
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
        "version": "v0.66",
        "timestamp": datetime.now().isoformat(),
        "tests": results,
        "summary": {
            "passed": passed,
            "failed": failed,
            "total": len(tests)
        },
        "components_verified": [
            "IEE v0.4 initialization",
            "Benchmark information retrieval",
            "GGP benchmark execution via IEE",
            "Conversational AI benchmark execution via IEE",
            "Population evaluation system"
        ]
    }

    report_path = "v0_66_verification_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Verification report saved to: {report_path}")

    if failed == 0:
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("v0.66 implementation verified successfully!")
        return 0
    else:
        print(f"\n✗✗✗ {failed} TEST(S) FAILED ✗✗✗")
        return 1


if __name__ == "__main__":
    sys.exit(main())