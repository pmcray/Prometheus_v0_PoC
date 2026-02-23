"""
Standalone test for GeneralistPlannerAgent v0.68
Tests meta-task decomposition and SMM directive generation
"""

import sys
import json
from datetime import datetime

# Import directly from the file
exec(open('prometheus/generalist_planner.py').read())


def test_all():
    """Run all tests"""
    print("="*60)
    print("PROMETHEUS v0.68 VERIFICATION (Standalone)")
    print("Testing GeneralistPlannerAgent")
    print("="*60)

    results = {}

    # Test 1: Initialize planner
    print("\nTEST 1: Initialize GeneralistPlannerAgent")
    try:
        planner = GeneralistPlannerAgent(use_llm=False)
        print(f"✓ Planner initialized")
        print(f"  LLM enabled: {planner.use_llm}")
        print(f"  Domain knowledge entries: {len(planner.domain_knowledge)}")
        results["Initialize Planner"] = "PASS"
    except Exception as e:
        print(f"✗ Failed: {e}")
        results["Initialize Planner"] = "FAIL"
        return results

    # Test 2: Analyze Draughts goal
    print("\nTEST 2: Analyze Goal - 'Learn to play Draughts'")
    try:
        analysis = planner.analyze_goal("Learn to play Draughts")
        print(f"✓ Goal analyzed")
        print(f"  Domain: {analysis.domain_name}")
        print(f"  Benchmarks: {analysis.relevant_benchmarks}")
        print(f"  Approach: {analysis.suggested_approach}")
        print(f"  Difficulty: {analysis.estimated_difficulty}")
        print(f"  Capabilities: {analysis.required_capabilities}")

        if analysis.domain_name == "general_game_playing":
            results["Analyze Draughts Goal"] = "PASS"
        else:
            print(f"  ⚠ Expected 'general_game_playing' domain")
            results["Analyze Draughts Goal"] = "FAIL"

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        results["Analyze Draughts Goal"] = "FAIL"

    # Test 3: Analyze Chess goal
    print("\nTEST 3: Analyze Goal - 'Master chess'")
    try:
        analysis = planner.analyze_goal("Master chess")
        print(f"✓ Goal analyzed")
        print(f"  Domain: {analysis.domain_name}")
        print(f"  Benchmark: {analysis.relevant_benchmarks[0]}")

        if "chess" in analysis.relevant_benchmarks[0].lower():
            results["Analyze Chess Goal"] = "PASS"
        else:
            print(f"  ⚠ Expected chess-related benchmark")
            results["Analyze Chess Goal"] = "PARTIAL"

    except Exception as e:
        print(f"✗ Failed: {e}")
        results["Analyze Chess Goal"] = "FAIL"

    # Test 4: Analyze Conversational goal
    print("\nTEST 4: Analyze Goal - 'Become a helpful chatbot'")
    try:
        analysis = planner.analyze_goal("Become a helpful chatbot")
        print(f"✓ Goal analyzed")
        print(f"  Domain: {analysis.domain_name}")
        print(f"  Benchmark: {analysis.relevant_benchmarks[0]}")

        if analysis.domain_name == "conversational_ai":
            results["Analyze Conversational Goal"] = "PASS"
        else:
            print(f"  ⚠ Expected 'conversational_ai' domain")
            results["Analyze Conversational Goal"] = "FAIL"

    except Exception as e:
        print(f"✗ Failed: {e}")
        results["Analyze Conversational Goal"] = "FAIL"

    # Test 5: Create meta-task
    print("\nTEST 5: Create Meta-Task")
    try:
        meta_task = planner.create_meta_task("Learn to play Draughts", target_fitness=0.8)
        print(f"✓ Meta-task created")
        print(f"  Task ID: {meta_task.task_id}")
        print(f"  Task type: {meta_task.task_type.value}")
        print(f"  Target benchmark: {meta_task.target_benchmark}")
        print(f"  Target fitness: {meta_task.target_fitness}")
        print(f"  Population size: {meta_task.evolutionary_parameters['population_size']}")
        print(f"  Generations: {meta_task.evolutionary_parameters['num_generations']}")

        if meta_task.target_fitness == 0.8:
            results["Create Meta-Task"] = "PASS"
        else:
            results["Create Meta-Task"] = "FAIL"

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        results["Create Meta-Task"] = "FAIL"

    # Test 6: Generate SMM directive
    print("\nTEST 6: Generate SMM Directive")
    try:
        smm_directive = planner.generate_smm_directive(meta_task)
        print(f"✓ SMM directive generated")
        print(f"  Directive type: {smm_directive['directive_type']}")
        print(f"  Objective: {smm_directive['objective']}")
        print(f"  Target benchmark: {smm_directive['target_benchmark']}")
        print(f"  Genome template: {smm_directive.get('genome_template', 'N/A')}")

        if "directive_type" in smm_directive and "target_benchmark" in smm_directive:
            results["Generate SMM Directive"] = "PASS"
        else:
            results["Generate SMM Directive"] = "FAIL"

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        results["Generate SMM Directive"] = "FAIL"

    # Test 7: Complete planning pipeline
    print("\nTEST 7: Complete Planning Pipeline")
    try:
        meta_task, smm_directive = planner.plan_capability_acquisition("Master chess")
        print(f"✓ Complete planning pipeline executed")
        print(f"  Meta-task created: {meta_task.task_id}")
        print(f"  SMM directive type: {smm_directive['directive_type']}")

        results["Complete Planning Pipeline"] = "PASS"

    except Exception as e:
        print(f"✗ Failed: {e}")
        results["Complete Planning Pipeline"] = "FAIL"

    # Test 8: Task progress tracking
    print("\nTEST 8: Task Progress Tracking")
    try:
        # Simulate progress updates
        task_id = meta_task.task_id
        planner.update_task_progress(task_id, 0.5, 10)
        planner.update_task_progress(task_id, 0.7, 15)
        planner.update_task_progress(task_id, 0.85, 20)

        print(f"✓ Progress tracking works")

        # Evaluate completion
        success = planner.evaluate_task_completion(task_id, 0.85)
        print(f"✓ Task evaluation: {'SUCCESS' if success else 'INCOMPLETE'}")

        if success:
            results["Task Progress Tracking"] = "PASS"
        else:
            results["Task Progress Tracking"] = "PARTIAL"

    except Exception as e:
        print(f"✗ Failed: {e}")
        results["Task Progress Tracking"] = "FAIL"

    # Test 9: Task status retrieval
    print("\nTEST 9: Task Status Retrieval")
    try:
        status = planner.get_task_status(meta_task.task_id)
        print(f"✓ Task status retrieved")
        print(f"  Goal: {status['goal']}")
        print(f"  Target fitness: {status['target_fitness']}")

        all_tasks = planner.get_all_tasks()
        print(f"✓ All tasks retrieved: {len(all_tasks)} tasks")

        results["Task Status Retrieval"] = "PASS"

    except Exception as e:
        print(f"✗ Failed: {e}")
        results["Task Status Retrieval"] = "FAIL"

    # Test 10: Curriculum learning
    print("\nTEST 10: Curriculum Learning")
    try:
        completed = ["Learn to play Draughts"]
        next_goal = planner.suggest_next_goal(completed)
        print(f"✓ Next goal suggested: '{next_goal}'")

        if next_goal != "Learn to play Draughts":
            results["Curriculum Learning"] = "PASS"
        else:
            print(f"  ⚠ Suggested same goal as completed")
            results["Curriculum Learning"] = "PARTIAL"

    except Exception as e:
        print(f"✗ Failed: {e}")
        results["Curriculum Learning"] = "FAIL"

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
        "version": "v0.68",
        "timestamp": datetime.now().isoformat(),
        "tests": results,
        "summary": {
            "passed": passed,
            "partial": partial,
            "failed": failed,
            "total": len(results)
        },
        "components_verified": [
            "GeneralistPlannerAgent initialization",
            "Goal analysis for multiple domains",
            "Meta-task creation",
            "SMM directive generation",
            "Complete planning pipeline",
            "Task progress tracking",
            "Task status retrieval",
            "Curriculum learning"
        ]
    }

    with open("v0_68_verification_report.json", 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Report saved to: v0_68_verification_report.json")

    if failed == 0:
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("v0.68 implementation verified successfully!")
        return 0
    else:
        print(f"\n✗✗✗ {failed} TEST(S) FAILED ✗✗✗")
        return 1


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    sys.exit(test_all())