#!/usr/bin/env python3
"""
Quick test of transfer learning on 10 tasks
Validates implementation before full 400-task run
"""

import sys
import subprocess

print("="*70)
print("🧪 Transfer Learning Quick Test: 10 Tasks")
print("="*70)

# Run transfer evolution on 10 tasks
result = subprocess.run([
    sys.executable,
    "prometheus_arc_transfer_evolution.py",
    "--split", "evaluation",
    "--num-tasks", "10",
    "--clusters", "20"
], cwd="/home/pmc/Prometheus_v0_PoC")

sys.exit(result.returncode)
