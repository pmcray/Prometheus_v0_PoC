#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug tie-breaking: Verify that operation priority is actually being used.
"""

import json
import numpy as np
from arc_program import ARCProgram
from arc_program_synthesizer import ProgramSynthesizer


def test_tiebreaking():
    """Test if tie-breaking actually works."""

    # Create synthesizer
    synth = ProgramSynthesizer(beam_width=50, max_depth=5, max_candidates_per_op=3)

    # Create fake programs with same fitness but different operations
    prog1 = ARCProgram([])
    prog1.add_operation('crop', {'mode': 'content'})

    prog2 = ARCProgram([])
    prog2.add_operation('map_color', {'from_color': 0, 'to_color': 1})

    prog3 = ARCProgram([])
    prog3.add_operation('identity', {})

    # Create candidates with SAME fitness
    candidates = [
        (0.949, prog2),  # map_color (priority=10)
        (0.949, prog1),  # crop (priority=1)
        (0.949, prog3),  # identity (priority=0)
    ]

    print("Before sorting:")
    for i, (fit, prog) in enumerate(candidates):
        op_name = prog.operations[0][0] if prog.operations else 'none'
        priority = synth._get_operation_priority(prog)
        print(f"  {i+1}. {op_name:<15} fitness={fit:.3f}, priority={priority}, sort_key=({fit:.3f}, {-priority})")

    # Sort with tie-breaking
    candidates.sort(reverse=True, key=lambda x: (
        x[0],  # Primary: fitness
        -synth._get_operation_priority(x[1])  # Secondary: operation priority
    ))

    print()
    print("After sorting (should be: identity, crop, map_color):")
    for i, (fit, prog) in enumerate(candidates):
        op_name = prog.operations[0][0] if prog.operations else 'none'
        priority = synth._get_operation_priority(prog)
        print(f"  {i+1}. {op_name:<15} fitness={fit:.3f}, priority={priority}")

    # Check if correct
    expected_order = ['identity', 'crop', 'map_color']
    actual_order = [prog.operations[0][0] for _, prog in candidates]

    print()
    if actual_order == expected_order:
        print("✅ Tie-breaking WORKS! Operations correctly sorted by priority.")
    else:
        print(f"❌ Tie-breaking FAILED!")
        print(f"   Expected: {expected_order}")
        print(f"   Actual:   {actual_order}")

    return actual_order == expected_order


if __name__ == '__main__':
    success = test_tiebreaking()
    print()
    print("=" * 80)
    if success:
        print("✅ Tie-breaking logic is correct!")
        print("   The problem must be elsewhere (e.g., diversity selection)")
    else:
        print("❌ Tie-breaking logic is broken!")
        print("   Need to fix the sorting implementation")
    print("=" * 80)
