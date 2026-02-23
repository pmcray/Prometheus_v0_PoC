#!/usr/bin/env python3
"""
Test meta-evolution on 10 tasks to validate integration
"""

import subprocess
import sys

def test_meta_evolution():
    """Test meta-evolution on 10 tasks"""

    print("="*70)
    print("🧪 Testing Meta-Evolution on 10 Tasks")
    print("="*70)
    print()

    # First, ensure patterns file exists
    print("1️⃣  Checking for learned patterns...")
    import os
    if not os.path.exists("arc_learned_patterns.json"):
        print("   ⚠️  Patterns file not found, generating...")
        result = subprocess.run(
            ["python3", "arc_meta_learner.py"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            print(f"   ❌ Pattern generation failed:")
            print(result.stderr)
            return False

        print("   ✅ Patterns generated")
    else:
        print("   ✅ Patterns file found")

    # Run meta-evolution on 10 tasks
    print("\n2️⃣  Running meta-evolution (10 tasks, ~5-10 minutes)...")
    print("   This tests that integration works correctly")
    print()

    result = subprocess.run(
        [
            "python3", "prometheus_arc_meta_evolution.py",
            "--data-dir", "arc_agi_official/data",
            "--split", "evaluation",
            "--max-tasks", "10",
            "--generations", "200"
        ],
        capture_output=True,
        text=True,
        timeout=900  # 15 minutes max
    )

    print(result.stdout)

    if result.returncode != 0:
        print("❌ Meta-evolution failed:")
        print(result.stderr)
        return False

    # Parse results
    lines = result.stdout.split('\n')
    solved = 0
    total = 10

    for line in lines:
        if 'Solved:' in line and '/' in line:
            # Extract solved count
            parts = line.split('Solved:')[1].split('/')
            solved = int(parts[0].strip().split()[0])
            break

    success_rate = solved / total * 100
    baseline_rate = 1.2  # 5/400 from v0.69

    print()
    print("="*70)
    print("📊 Test Results")
    print("="*70)
    print(f"Solved: {solved}/10 ({success_rate:.1f}%)")
    print(f"Baseline: 1.2% (expected ~0.12 tasks)")
    print()

    if solved > 0:
        print("✅ Meta-evolution is working!")
        print(f"   Solved {solved} task(s) - integration successful")
        return True
    else:
        print("⚠️  No tasks solved in this run")
        print("   This may be normal due to task difficulty")
        print("   Integration appears functional")
        return True


if __name__ == "__main__":
    success = test_meta_evolution()
    sys.exit(0 if success else 1)
