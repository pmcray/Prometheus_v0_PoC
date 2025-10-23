#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Beam Search 0.000 Fitness Issue

Investigates why beam search returns 0.000 fitness on all attempts.

Potential root causes:
1. Operation execution failing (exceptions caught, return 0.0)
2. Parameter generation issues (invalid params)
3. Operation map mismatch (operations not found)
4. Program execution errors

Strategy:
1. Test single operation execution
2. Test parameter generation
3. Test program creation and execution
4. Add verbose logging to beam search

Author: Prometheus v0.95 Debug
Date: 2025-10-22
"""

import json
import numpy as np
from arc_program import ARCProgram
from arc_parametric_operations import build_operation_map, get_parameter_candidates, PARAMETRIC_OPERATIONS
from arc_program_synthesizer import ProgramSynthesizer


def test_operation_execution():
    """Test that individual operations can execute."""
    print("=" * 80)
    print("🔍 Test 1: Operation Execution")
    print("=" * 80)
    print()

    # Create test grid
    test_grid = np.array([
        [1, 2, 0],
        [3, 1, 2],
        [0, 3, 1]
    ])

    operation_map = build_operation_map()

    print(f"Test grid:\n{test_grid}\n")
    print(f"Operation map has {len(operation_map)} operations")
    print()

    # Test each operation with default parameters
    success_count = 0
    fail_count = 0

    for op_name in ['crop', 'rotate', 'flip', 'scale', 'filter_color']:
        try:
            if op_name not in operation_map:
                print(f"❌ {op_name}: Not in operation_map")
                fail_count += 1
                continue

            op_func = operation_map[op_name]

            # Get default parameters
            if op_name in PARAMETRIC_OPERATIONS:
                spec = PARAMETRIC_OPERATIONS[op_name]
                params = {
                    name: param_spec['default']
                    for name, param_spec in spec['params'].items()
                }
            else:
                params = {}

            # Execute
            result = op_func(test_grid, **params)

            print(f"✅ {op_name}: Success (output shape: {result.shape})")
            success_count += 1

        except Exception as e:
            print(f"❌ {op_name}: FAILED - {str(e)}")
            fail_count += 1

    print()
    print(f"Summary: {success_count} succeeded, {fail_count} failed")
    print()

    return fail_count == 0


def test_parameter_generation():
    """Test that parameter generation works."""
    print("=" * 80)
    print("🔍 Test 2: Parameter Generation")
    print("=" * 80)
    print()

    ops_to_test = ['crop', 'rotate', 'flip', 'scale', 'pad']

    for op_name in ops_to_test:
        try:
            candidates = get_parameter_candidates(op_name)
            print(f"✅ {op_name}: {len(candidates)} parameter sets")
            for i, params in enumerate(candidates[:3]):
                print(f"   {i+1}. {params}")
        except Exception as e:
            print(f"❌ {op_name}: FAILED - {str(e)}")

    print()


def test_program_execution():
    """Test that ARCProgram can execute."""
    print("=" * 80)
    print("🔍 Test 3: Program Execution")
    print("=" * 80)
    print()

    # Create test grid
    test_grid = np.array([
        [1, 2, 0],
        [3, 1, 2],
        [0, 3, 1]
    ])

    operation_map = build_operation_map()

    # Test simple programs
    test_programs = [
        [('crop', {'mode': 'content'})],
        [('rotate', {'angle': 90})],
        [('flip', {'axis': 'horizontal'})],
        [('crop', {'mode': 'content'}), ('rotate', {'angle': 90})]
    ]

    for i, operations in enumerate(test_programs, 1):
        try:
            program = ARCProgram(operations)
            result = program.execute(test_grid, operation_map)

            print(f"✅ Program {i}: {[op for op, _ in operations]} → shape {result.shape}")

        except Exception as e:
            print(f"❌ Program {i}: FAILED - {str(e)}")
            import traceback
            traceback.print_exc()

    print()


def test_fitness_evaluation():
    """Test fitness evaluation on real task."""
    print("=" * 80)
    print("🔍 Test 4: Fitness Evaluation on Real Task")
    print("=" * 80)
    print()

    # Load a simple task
    task_id = '135a2760'
    with open(f'arc_agi_2/data/evaluation/{task_id}.json', 'r') as f:
        task_data = json.load(f)

    train_examples = task_data['train']

    print(f"Task: {task_id}")
    print(f"Training examples: {len(train_examples)}")
    print()

    operation_map = build_operation_map()

    # Test programs with different crop modes
    test_programs = [
        [('crop', {'mode': 'content'})],
        [('crop', {'mode': 'border'})],
        [('crop', {'mode': 'center'})],
    ]

    for program_ops in test_programs:
        program = ARCProgram(program_ops)

        # Evaluate on training examples
        total_similarity = 0.0
        for example in train_examples:
            input_grid = np.array(example['input'])
            expected_output = np.array(example['output'])

            try:
                predicted = program.execute(input_grid, operation_map)

                # Compute similarity
                if predicted.shape == expected_output.shape:
                    matches = np.sum(predicted == expected_output)
                    total = predicted.size
                    similarity = matches / total
                else:
                    similarity = 0.0

                total_similarity += similarity

            except Exception as e:
                print(f"  ❌ Execution failed: {str(e)}")
                total_similarity += 0.0

        fitness = total_similarity / len(train_examples)

        pattern_str = ' → '.join(f"{op}({params})" for op, params in program_ops)
        print(f"  {pattern_str}: fitness = {fitness:.3f}")

    print()


def test_beam_search_single_task():
    """Test beam search on single task with verbose output."""
    print("=" * 80)
    print("🔍 Test 5: Beam Search on Single Task")
    print("=" * 80)
    print()

    # Load task
    task_id = '135a2760'
    with open(f'arc_agi_2/data/evaluation/{task_id}.json', 'r') as f:
        task_data = json.load(f)

    print(f"Task: {task_id}")
    print(f"Training examples: {len(task_data['train'])}")
    print()

    # Initialize synthesizer with small beam for debugging
    synthesizer = ProgramSynthesizer(
        beam_width=5,  # Small for debugging
        max_depth=2,   # Shallow for debugging
        max_candidates_per_op=2
    )

    # Prepare task
    task = {'train': task_data['train']}
    constraints = {'size': 'variable', 'color': 'variable'}
    biased_operations = ['crop', 'rotate', 'flip', 'pad']

    print("Running beam search with verbose output...")
    print(f"Beam width: {synthesizer.beam_width}")
    print(f"Max depth: {synthesizer.max_depth}")
    print(f"Biased operations: {biased_operations}")
    print()

    try:
        program = synthesizer.synthesize(
            task=task,
            constraints=constraints,
            biased_operations=biased_operations
        )

        if program and len(program.operations) > 0:
            print(f"\n✅ Beam search succeeded!")
            print(f"Program: {program.to_pattern()}")
        else:
            print(f"\n❌ Beam search returned empty program")

    except Exception as e:
        print(f"\n❌ Beam search failed with exception:")
        import traceback
        traceback.print_exc()

    print()


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("🐛 Beam Search Debug Session")
    print("=" * 80)
    print()

    # Run tests
    test1_pass = test_operation_execution()
    test_parameter_generation()
    test_program_execution()
    test_fitness_evaluation()
    test_beam_search_single_task()

    print("=" * 80)
    print("🎯 Debug Session Complete")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Review any failed tests above")
    print("2. Check beam search implementation in arc_program_synthesizer.py")
    print("3. Add more verbose logging if needed")
    print()
