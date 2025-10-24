"""
Direct test of IEE v0.66 functionality
Tests the new benchmark integration without full import
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from benchmarks.prometheus_bench_v0_2 import PrometheusBenchV02
from benchmarks.baseline_agents import RandomDraughtsAgent, SimpleChatbotAgent


def test_direct_benchmark_access():
    """Test direct access to v0.2 benchmarks"""
    print("\n" + "="*60)
    print("TEST 1: Direct Benchmark Access")
    print("="*60)

    bench = PrometheusBenchV02()
    print(f"✓ PrometheusBenchV02 initialized")
    print(f"  Version: {bench.version}")

    # Get available benchmarks
    available = bench.get_available_benchmarks()
    print(f"✓ Available benchmarks: {list(available.keys())}")

    return True


def test_agent_loading_pattern():
    """Test the agent loading pattern used by IEE"""
    print("\n" + "="*60)
    print("TEST 2: Agent Loading Pattern")
    print("="*60)

    # Create a temporary agent file
    temp_dir = tempfile.mkdtemp()
    agent_path = Path(temp_dir) / "test_agent.py"

    agent_code = '''
import random
from typing import Dict, Any, Optional, Tuple

class TestAgent:
    """Test agent"""
    def select_move(self, game_state: Dict[str, Any]) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        return None  # Placeholder
'''

    with open(agent_path, 'w') as f:
        f.write(agent_code)

    print(f"✓ Created test agent at {agent_path}")

    # Test loading
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("test_agent", agent_path)
        agent_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent_module)

        # Get agent classes
        agent_classes = [obj for name, obj in agent_module.__dict__.items()
                        if isinstance(obj, type) and name.endswith("Agent")]

        print(f"✓ Found {len(agent_classes)} agent class(es)")

        if agent_classes:
            agent = agent_classes[0]()
            print(f"✓ Instantiated agent: {agent.__class__.__name__}")
            print(f"✓ Agent has select_move: {hasattr(agent, 'select_move')}")

        success = len(agent_classes) > 0

    except Exception as e:
        print(f"✗ Agent loading failed: {e}")
        success = False

    finally:
        shutil.rmtree(temp_dir)

    return success


def test_benchmark_execution_with_agent_loading():
    """Test benchmark execution with dynamic agent loading"""
    print("\n" + "="*60)
    print("TEST 3: Benchmark Execution with Dynamic Loading")
    print("="*60)

    bench = PrometheusBenchV02()

    # Create a temporary agent
    temp_dir = tempfile.mkdtemp()
    agent_path = Path(temp_dir) / "draughts_agent.py"

    # Use the RandomDraughtsAgent code
    agent_code = '''
import random
from typing import Dict, List, Any, Optional, Tuple

class TestDraughtsAgent:
    def select_move(self, game_state: Dict[str, Any]) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        try:
            board = game_state["board"]
            current_player = game_state["current_player"]
            valid_moves = []

            for from_row in range(8):
                for from_col in range(8):
                    piece = board[from_row][from_col]
                    if (current_player == 1 and piece > 0) or (current_player == -1 and piece < 0):
                        # Simple moves
                        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                            new_row, new_col = from_row + dr, from_col + dc
                            if 0 <= new_row < 8 and 0 <= new_col < 8:
                                if board[new_row][new_col] == 0:
                                    valid_moves.append(((from_row, from_col), (new_row, new_col)))

            return random.choice(valid_moves) if valid_moves else None
        except Exception as e:
            return None
'''

    with open(agent_path, 'w') as f:
        f.write(agent_code)

    print(f"✓ Created agent module")

    try:
        # Load the agent
        import importlib.util
        spec = importlib.util.spec_from_file_location("candidate_agent", agent_path)
        agent_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent_module)

        agent_classes = [obj for name, obj in agent_module.__dict__.items()
                        if isinstance(obj, type) and name.endswith("Agent")]

        agent = agent_classes[0]()
        select_move_func = getattr(agent, "select_move")

        print(f"✓ Agent loaded successfully")

        # Run benchmark
        result = bench.run_ggp_benchmark(
            agent_select_move=select_move_func,
            num_games=5,
            game_type="draughts"
        )

        print(f"✓ Benchmark executed")
        print(f"  Win rate: {result.fitness_score:.2%}")
        print(f"  Games: {result.details['num_games']}")
        print(f"  Execution time: {result.execution_time_ms:.0f}ms")

        success = result.success

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        success = False

    finally:
        shutil.rmtree(temp_dir)

    return success


def test_conversational_agent_loading():
    """Test conversational agent loading and execution"""
    print("\n" + "="*60)
    print("TEST 4: Conversational Agent Loading")
    print("="*60)

    bench = PrometheusBenchV02()

    temp_dir = tempfile.mkdtemp()
    agent_path = Path(temp_dir) / "chatbot_agent.py"

    agent_code = '''
from typing import List, Dict

class SimpleChatAgent:
    def generate_response(self, conversation_history: List[Dict[str, str]]) -> str:
        user_messages = [msg for msg in conversation_history if msg["role"] == "user"]
        if not user_messages:
            return "Hello!"
        return "I understand. Let me help you with that."
'''

    with open(agent_path, 'w') as f:
        f.write(agent_code)

    print(f"✓ Created chatbot module")

    try:
        # Load the agent
        import importlib.util
        spec = importlib.util.spec_from_file_location("candidate_agent", agent_path)
        agent_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent_module)

        agent_classes = [obj for name, obj in agent_module.__dict__.items()
                        if isinstance(obj, type) and name.endswith("Agent")]

        agent = agent_classes[0]()
        generate_response_func = getattr(agent, "generate_response")

        print(f"✓ Agent loaded successfully")

        # Run benchmark
        result = bench.run_conversational_ai_benchmark(
            agent_generate_response=generate_response_func,
            topic="programming",
            num_turns=3
        )

        print(f"✓ Benchmark executed")
        print(f"  Quality score: {result.fitness_score:.2f}")
        print(f"  Execution time: {result.execution_time_ms:.0f}ms")

        success = result.success

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        success = False

    finally:
        shutil.rmtree(temp_dir)

    return success


def test_population_style_evaluation():
    """Test evaluating multiple agents"""
    print("\n" + "="*60)
    print("TEST 5: Population-Style Evaluation")
    print("="*60)

    bench = PrometheusBenchV02()
    temp_dir = tempfile.mkdtemp()

    # Create multiple agents
    agent_paths = []
    for i in range(3):
        agent_path = Path(temp_dir) / f"agent_{i}.py"
        agent_code = f'''
import random
from typing import Dict, Any, Optional, Tuple

class PopAgent{i}:
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
        with open(agent_path, 'w') as f:
            f.write(agent_code)
        agent_paths.append(agent_path)

    print(f"✓ Created {len(agent_paths)} agents")

    results = []
    for i, agent_path in enumerate(agent_paths):
        try:
            # Load agent
            import importlib.util
            spec = importlib.util.spec_from_file_location(f"agent_{i}", agent_path)
            agent_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(agent_module)

            agent_classes = [obj for name, obj in agent_module.__dict__.items()
                           if isinstance(obj, type) and name.endswith(f"Agent{i}")]
            agent = agent_classes[0]()
            select_move_func = getattr(agent, "select_move")

            # Evaluate
            result = bench.run_ggp_benchmark(
                agent_select_move=select_move_func,
                num_games=3
            )

            results.append({
                "agent_id": i,
                "fitness": result.fitness_score,
                "success": result.success
            })

            print(f"  Agent {i}: fitness={result.fitness_score:.2f}")

        except Exception as e:
            print(f"  Agent {i}: FAILED - {e}")
            results.append({
                "agent_id": i,
                "fitness": 0.0,
                "success": False
            })

    shutil.rmtree(temp_dir)

    print(f"✓ Evaluated {len(results)} agents")
    success = all(r["success"] for r in results)

    return success


def main():
    """Run all tests"""
    print("="*60)
    print("PROMETHEUS v0.66 VERIFICATION (Direct)")
    print("Testing IEE v0.4 Benchmark Integration")
    print("="*60)

    tests = [
        ("Direct Benchmark Access", test_direct_benchmark_access),
        ("Agent Loading Pattern", test_agent_loading_pattern),
        ("Benchmark Execution with Loading", test_benchmark_execution_with_agent_loading),
        ("Conversational Agent Loading", test_conversational_agent_loading),
        ("Population-Style Evaluation", test_population_style_evaluation),
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
            "Direct benchmark v0.2 access",
            "Dynamic agent loading pattern",
            "GGP benchmark with dynamic loading",
            "Conversational AI benchmark with dynamic loading",
            "Population evaluation pattern"
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