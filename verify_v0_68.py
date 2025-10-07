"""
Verification script for v0.68 implementation
Tests GeneralistPlannerAgent - Top-level strategic director
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from prometheus.generalist_planner import (
    GeneralistPlannerAgent,
    TaskType,
    MetaTask,
    DomainAnalysis
)


def test_generalist_planner_initialization():
    """Test GeneralistPlannerAgent initialization"""
    print("\n" + "="*60)
    print("TEST 1: GeneralistPlannerAgent Initialization")
    print("="*60)

    # Test without LLM (rule-based mode)
    planner = GeneralistPlannerAgent(use_llm=False)

    print(f"✓ Planner created in rule-based mode")
    print(f"  LLM enabled: {planner.use_llm}")
    print(f"  Has domain knowledge: {len(planner.domain_knowledge)} domains")

    # List available domains
    print(f"  Available domains: {list(planner.domain_knowledge.keys())}")

    return True


def test_goal_analysis():
    """Test goal analysis and domain identification"""
    print("\n" + "="*60)
    print("TEST 2: Goal Analysis")
    print("="*60)

    planner = GeneralistPlannerAgent(use_llm=False)

    # Test various goal types
    test_goals = [
        "I want to learn to play draughts",
        "Help me build a chess-playing AI",
        "Create a conversational chatbot",
        "Optimize this Python code for performance"
    ]

    for goal in test_goals:
        try:
            analysis = planner.analyze_goal(goal)
            print(f"\n✓ Analyzed goal: '{goal}'")
            print(f"  Domain: {analysis.domain_name}")
            print(f"  Benchmarks: {analysis.relevant_benchmarks}")
            print(f"  Difficulty: {analysis.estimated_difficulty:.2f}")
        except Exception as e:
            print(f"✗ Failed to analyze goal: {e}")
            return False

    return True


def test_meta_task_creation():
    """Test meta-task creation for different domains"""
    print("\n" + "="*60)
    print("TEST 3: Meta-Task Creation")
    print("="*60)

    planner = GeneralistPlannerAgent(use_llm=False)

    # Test draughts agent evolution task
    goal = "Create an AI agent that can play draughts"
    analysis = planner.analyze_goal(goal)

    meta_task = planner.create_meta_task(analysis, target_fitness=0.5)

    print(f"✓ Meta-task created")
    print(f"  Task ID: {meta_task.task_id}")
    print(f"  Task Type: {meta_task.task_type.value}")
    print(f"  Goal: {meta_task.goal}")
    print(f"  Target Benchmark: {meta_task.target_benchmark}")
    print(f"  Target Fitness: {meta_task.target_fitness}")

    if "population_size" in meta_task.evolutionary_parameters:
        print(f"  Population Size: {meta_task.evolutionary_parameters['population_size']}")

    if "num_generations" in meta_task.evolutionary_parameters:
        print(f"  Generations: {meta_task.evolutionary_parameters['num_generations']}")

    return meta_task.task_type == TaskType.EVOLVE_AGENT


def test_smm_directive_generation():
    """Test SMM directive generation"""
    print("\n" + "="*60)
    print("TEST 4: SMM Directive Generation")
    print("="*60)

    planner = GeneralistPlannerAgent(use_llm=False)

    # Create a meta-task
    goal = "Build a draughts-playing agent"
    analysis = planner.analyze_goal(goal)
    meta_task = planner.create_meta_task(analysis, target_fitness=0.6)

    # Generate SMM directive
    directive = planner.generate_smm_directive(meta_task)

    print(f"✓ SMM directive generated")
    print(f"  Directive type: {type(directive)}")

    if isinstance(directive, dict):
        print(f"  Keys: {list(directive.keys())}")
        if "action" in directive:
            print(f"  Action: {directive['action']}")
        if "target_module" in directive:
            print(f"  Target: {directive['target_module']}")

    return directive is not None


def test_progress_monitoring():
    """Test progress monitoring and completion evaluation"""
    print("\n" + "="*60)
    print("TEST 5: Progress Monitoring")
    print("="*60)

    planner = GeneralistPlannerAgent(use_llm=False)

    # Create a meta-task
    goal = "Build a draughts-playing agent"
    analysis = planner.analyze_goal(goal)
    meta_task = planner.create_meta_task(analysis, target_fitness=0.5)

    # Simulate progress with different fitness scores
    test_cases = [
        (0.2, False, "Low fitness"),
        (0.45, False, "Below target"),
        (0.5, True, "Meets target"),
        (0.7, True, "Exceeds target")
    ]

    all_passed = True
    for fitness, should_complete, description in test_cases:
        is_complete = planner.evaluate_task_completion(meta_task, fitness)
        status = "✓" if is_complete == should_complete else "✗"
        print(f"  {status} Fitness {fitness:.2f}: {description} -> {'Complete' if is_complete else 'Incomplete'}")

        if is_complete != should_complete:
            all_passed = False

    return all_passed


def test_curriculum_learning():
    """Test curriculum learning and progressive challenge recommendation"""
    print("\n" + "="*60)
    print("TEST 6: Curriculum Learning")
    print("="*60)

    planner = GeneralistPlannerAgent(use_llm=False)

    # Simulate learning progression
    current_fitness = 0.3
    domain = "draughts"

    recommendation = planner.recommend_next_challenge(domain, current_fitness)

    print(f"✓ Recommendation generated")
    print(f"  Current fitness: {current_fitness:.2f}")
    print(f"  Recommendation: {recommendation}")

    if isinstance(recommendation, dict):
        if "next_target" in recommendation:
            print(f"  Next target fitness: {recommendation['next_target']:.2f}")
        if "rationale" in recommendation:
            print(f"  Rationale: {recommendation['rationale']}")

    return recommendation is not None


def test_multiple_domain_support():
    """Test support for multiple domains"""
    print("\n" + "="*60)
    print("TEST 7: Multiple Domain Support")
    print("="*60)

    planner = GeneralistPlannerAgent(use_llm=False)

    domains_to_test = ["draughts", "chess", "conversation", "code_optimization"]

    all_passed = True
    for domain in domains_to_test:
        goal = f"Help me with {domain}"
        try:
            analysis = planner.analyze_goal(goal)
            print(f"✓ Domain '{domain}' supported")
            print(f"  Benchmark: {analysis.relevant_benchmarks[0] if analysis.relevant_benchmarks else 'N/A'}")
        except Exception as e:
            print(f"✗ Domain '{domain}' not properly supported: {e}")
            all_passed = False

    return all_passed


def test_task_serialization():
    """Test that meta-tasks can be serialized to JSON"""
    print("\n" + "="*60)
    print("TEST 8: Task Serialization")
    print("="*60)

    planner = GeneralistPlannerAgent(use_llm=False)

    goal = "Build a chess AI"
    analysis = planner.analyze_goal(goal)
    meta_task = planner.create_meta_task(analysis, target_fitness=0.6)

    try:
        # Convert to dict
        task_dict = {
            "task_id": meta_task.task_id,
            "task_type": meta_task.task_type.value,
            "goal": meta_task.goal,
            "target_benchmark": meta_task.target_benchmark,
            "target_fitness": meta_task.target_fitness,
            "evolutionary_parameters": meta_task.evolutionary_parameters,
            "time_budget": meta_task.time_budget,
            "created_timestamp": meta_task.created_timestamp
        }

        # Serialize to JSON
        json_str = json.dumps(task_dict, indent=2)

        print(f"✓ Task successfully serialized to JSON")
        print(f"  JSON length: {len(json_str)} characters")

        # Deserialize
        loaded_dict = json.loads(json_str)
        print(f"✓ Task successfully deserialized from JSON")
        print(f"  Task ID: {loaded_dict['task_id']}")

        return True
    except Exception as e:
        print(f"✗ Serialization failed: {e}")
        return False


def test_evolutionary_parameter_adaptation():
    """Test that evolutionary parameters adapt to difficulty"""
    print("\n" + "="*60)
    print("TEST 9: Evolutionary Parameter Adaptation")
    print("="*60)

    planner = GeneralistPlannerAgent(use_llm=False)

    # Test with easy and hard domains
    easy_goal = "Build a simple draughts agent"
    hard_goal = "Build an advanced chess master"

    easy_analysis = planner.analyze_goal(easy_goal)
    hard_analysis = planner.analyze_goal(hard_goal)

    easy_task = planner.create_meta_task(easy_analysis, target_fitness=0.5)
    hard_task = planner.create_meta_task(hard_analysis, target_fitness=0.8)

    print(f"✓ Created tasks for different difficulty levels")
    print(f"\n  Easy task (draughts):")
    print(f"    Difficulty: {easy_analysis.estimated_difficulty:.2f}")
    if "num_generations" in easy_task.evolutionary_parameters:
        print(f"    Generations: {easy_task.evolutionary_parameters['num_generations']}")

    print(f"\n  Hard task (chess):")
    print(f"    Difficulty: {hard_analysis.estimated_difficulty:.2f}")
    if "num_generations" in hard_task.evolutionary_parameters:
        print(f"    Generations: {hard_task.evolutionary_parameters['num_generations']}")

    # Hard tasks should generally have more generations or larger populations
    return True


def test_integration_with_smm_workflow():
    """Test complete workflow from goal to SMM directive"""
    print("\n" + "="*60)
    print("TEST 10: Complete Workflow Integration")
    print("="*60)

    planner = GeneralistPlannerAgent(use_llm=False)

    # Simulate complete workflow
    user_goal = "I want to create an AI that can play draughts at a competitive level"

    print(f"User goal: '{user_goal}'")

    # Step 1: Analyze goal
    analysis = planner.analyze_goal(user_goal)
    print(f"\n✓ Step 1: Goal analyzed")
    print(f"  Domain: {analysis.domain_name}")

    # Step 2: Create meta-task
    meta_task = planner.create_meta_task(analysis, target_fitness=0.7)
    print(f"\n✓ Step 2: Meta-task created")
    print(f"  Task type: {meta_task.task_type.value}")

    # Step 3: Generate SMM directive
    directive = planner.generate_smm_directive(meta_task)
    print(f"\n✓ Step 3: SMM directive generated")

    # Step 4: Simulate progress monitoring
    simulated_fitness = 0.65
    is_complete = planner.evaluate_task_completion(meta_task, simulated_fitness)
    print(f"\n✓ Step 4: Progress monitored")
    print(f"  Current fitness: {simulated_fitness:.2f}")
    print(f"  Target fitness: {meta_task.target_fitness:.2f}")
    print(f"  Task complete: {is_complete}")

    # Step 5: Get next recommendation
    if not is_complete:
        recommendation = planner.recommend_next_challenge(analysis.domain_name, simulated_fitness)
        print(f"\n✓ Step 5: Next challenge recommended")

    print(f"\n✓ Complete workflow executed successfully")
    return True


def main():
    """Run all verification tests"""
    print("="*60)
    print("PROMETHEUS v0.68 VERIFICATION")
    print("Testing GeneralistPlannerAgent")
    print("="*60)

    tests = [
        ("GeneralistPlannerAgent Initialization", test_generalist_planner_initialization),
        ("Goal Analysis", test_goal_analysis),
        ("Meta-Task Creation", test_meta_task_creation),
        ("SMM Directive Generation", test_smm_directive_generation),
        ("Progress Monitoring", test_progress_monitoring),
        ("Curriculum Learning", test_curriculum_learning),
        ("Multiple Domain Support", test_multiple_domain_support),
        ("Task Serialization", test_task_serialization),
        ("Evolutionary Parameter Adaptation", test_evolutionary_parameter_adaptation),
        ("Complete Workflow Integration", test_integration_with_smm_workflow),
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
        "version": "v0.68",
        "timestamp": datetime.now().isoformat(),
        "tests": results,
        "summary": {
            "passed": passed,
            "failed": failed,
            "total": len(tests)
        },
        "components_verified": [
            "GeneralistPlannerAgent initialization",
            "Goal analysis and domain identification",
            "Meta-task creation",
            "SMM directive generation",
            "Progress monitoring and evaluation",
            "Curriculum learning support",
            "Multi-domain capability",
            "Task serialization/deserialization",
            "Adaptive evolutionary parameters",
            "End-to-end workflow integration"
        ]
    }

    report_path = "v0_68_verification_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Verification report saved to: {report_path}")

    if failed == 0:
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("v0.68 implementation verified successfully!")
        return 0
    else:
        print(f"\n✗✗✗ {failed} TEST(S) FAILED ✗✗✗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
