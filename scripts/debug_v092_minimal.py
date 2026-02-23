#!/usr/bin/env python3
"""
Minimal debug script to identify where v0.92 solver hangs.

Strategy:
1. Test with 1 generation (minimal evolution)
2. Add extensive debug output
3. Test on 1 simple task
4. Identify exact hang location
"""

import json
import sys
import time
from pathlib import Path

# Import v0.92
from prometheus_arc_v092_baseline import (
    PrometheusARC_v092_Baseline,
    get_generation_budget,
    hybrid_fitness
)

def test_minimal_solver():
    """Test v0.92 with minimal configuration."""

    print("="*80)
    print("🔬 DEBUG: v0.92 Minimal Test")
    print("="*80)
    print()

    # Load 1 simple task
    task_dir = Path("arc_agi_2/data/evaluation")
    task_files = sorted(task_dir.glob("*.json"))

    if not task_files:
        print("Error: No tasks found")
        return

    # Use first task
    task_file = task_files[0]
    task_id = task_file.stem

    print(f"DEBUG: Loading task {task_id}")
    with open(task_file, 'r') as f:
        task_data = json.load(f)

    train_examples = task_data['train']
    test_examples = task_data['test']

    print(f"DEBUG: Task loaded - {len(train_examples)} training examples")
    print()

    # Test generation budget calculation
    print("="*80)
    print("TEST 1: Generation Budget Calculation")
    print("="*80)
    try:
        budget = get_generation_budget({'train': train_examples})
        print(f"✓ Budget calculation succeeded: {budget} generations")
    except Exception as e:
        print(f"✗ Budget calculation FAILED: {e}")
        import traceback
        traceback.print_exc()
        return
    print()

    # Test solver initialization
    print("="*80)
    print("TEST 2: Solver Initialization")
    print("="*80)
    try:
        print("DEBUG: Creating solver (use_llm=False, max_refinement_cycles=0)...")
        start = time.time()

        solver = PrometheusARC_v092_Baseline(
            use_llm=False,
            use_adaptive=True,
            use_metarefine=False,
            max_refinement_cycles=0  # ZERO refinement cycles for debugging
        )

        elapsed = time.time() - start
        print(f"✓ Solver initialized in {elapsed:.2f}s")
    except Exception as e:
        print(f"✗ Solver initialization FAILED: {e}")
        import traceback
        traceback.print_exc()
        return
    print()

    # Test solve_task with extensive debug output
    print("="*80)
    print("TEST 3: Solve Task (Zero Refinement, Adaptive Budget)")
    print("="*80)

    print("DEBUG: Entering solve_task()...")
    start = time.time()

    try:
        # Monkey-patch solve_task to add debug output
        original_solve = solver.solve_task

        def debug_solve(train_examples, test_examples, task_id):
            print(f"  DEBUG: solve_task() called for {task_id}")
            print(f"  DEBUG: Getting generation budget...")

            task_data = {'train': train_examples}
            generation_budget = get_generation_budget(task_data)

            print(f"  DEBUG: Budget = {generation_budget}")
            print(f"  DEBUG: use_llm = {solver.use_llm}")
            print(f"  DEBUG: llm_generator = {solver.llm_generator}")
            print(f"  DEBUG: max_refinement_cycles = {solver.max_refinement_cycles}")
            print()

            # Call original
            print(f"  DEBUG: Calling original solve_task()...")
            result = original_solve(train_examples, test_examples, task_id)
            print(f"  DEBUG: solve_task() returned!")

            return result

        solver.solve_task = debug_solve

        # Run with timeout
        result = solver.solve_task(train_examples, test_examples, task_id)

        elapsed = time.time() - start
        print(f"✓ solve_task() completed in {elapsed:.2f}s")
        print(f"  Fitness: {result.get('fitness', 0):.3f}")
        print(f"  Pattern: {result.get('pattern', [])}")

    except Exception as e:
        elapsed = time.time() - start
        print(f"✗ solve_task() FAILED after {elapsed:.2f}s: {e}")
        import traceback
        traceback.print_exc()
        return

    print()
    print("="*80)
    print("✅ ALL TESTS PASSED")
    print("="*80)


def test_minimal_evolution():
    """Test with FORCED minimal budget (1 generation)."""

    print()
    print("="*80)
    print("🔬 DEBUG: Minimal Evolution Test (1 generation)")
    print("="*80)
    print()

    # Load 1 task
    task_dir = Path("arc_agi_2/data/evaluation")
    task_files = sorted(task_dir.glob("*.json"))
    task_file = task_files[0]
    task_id = task_file.stem

    with open(task_file, 'r') as f:
        task_data = json.load(f)

    train_examples = task_data['train']
    test_examples = task_data['test']

    print(f"DEBUG: Task {task_id}")
    print(f"DEBUG: Forcing generation budget to 1 (instead of adaptive)")
    print()

    # Initialize solver
    solver = PrometheusARC_v092_Baseline(
        use_llm=False,
        use_adaptive=False,  # Disable adaptive
        use_metarefine=False,
        max_refinement_cycles=0
    )

    # Monkey-patch get_generation_budget to return 1
    import prometheus_arc_v092_baseline
    original_budget = prometheus_arc_v092_baseline.get_generation_budget
    prometheus_arc_v092_baseline.get_generation_budget = lambda x: 1

    print("DEBUG: Starting solve with 1 generation...")
    start = time.time()

    try:
        result = solver.solve_task(train_examples, test_examples, task_id)
        elapsed = time.time() - start

        print(f"✓ Completed in {elapsed:.2f}s")
        print(f"  Fitness: {result.get('fitness', 0):.3f}")

    except Exception as e:
        elapsed = time.time() - start
        print(f"✗ FAILED after {elapsed:.2f}s: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Restore original
        prometheus_arc_v092_baseline.get_generation_budget = original_budget

    print()


if __name__ == "__main__":
    # Test 1: Normal adaptive budget with zero refinement
    test_minimal_solver()

    # Test 2: Force 1 generation to see if evolution is the bottleneck
    test_minimal_evolution()
