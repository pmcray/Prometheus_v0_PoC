#!/usr/bin/env python3
"""
Verify Phase B Readiness

Checks if the environment is properly set up to run Phase B model training.

Usage:
    python scripts/verify_phase_b_readiness.py
"""

import sys
import subprocess
from pathlib import Path

def print_header(text):
    """Print formatted header."""
    print(f"\n{'=' * 70}")
    print(f"{text}")
    print(f"{'=' * 70}")

def print_check(name, status, message=""):
    """Print check result."""
    symbol = "✓" if status else "✗"
    color = "\033[92m" if status else "\033[91m"
    reset = "\033[0m"
    print(f"{color}{symbol}{reset} {name}")
    if message:
        print(f"  {message}")

def check_python_version():
    """Check Python version >= 3.10."""
    version = sys.version_info
    required = (3, 10)
    ok = version >= required

    print_check(
        "Python Version",
        ok,
        f"Python {version.major}.{version.minor}.{version.micro} " +
        ("(OK)" if ok else f"(need >= {required[0]}.{required[1]})")
    )
    return ok

def check_module(module_name, package_name=None):
    """Check if a Python module can be imported."""
    if package_name is None:
        package_name = module_name

    try:
        __import__(module_name)
        print_check(f"{package_name}", True, "Installed")
        return True
    except ImportError as e:
        print_check(f"{package_name}", False, f"Not installed: {e}")
        return False

def check_tensorflow():
    """Check TensorFlow installation and GPU availability."""
    try:
        import tensorflow as tf
        version = tf.__version__

        # Check version
        version_ok = version >= "2.15.0"
        print_check(
            "TensorFlow",
            version_ok,
            f"Version {version} " + ("(OK)" if version_ok else "(need >= 2.15.0)")
        )

        # Check GPU
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            print_check("GPU Support", True, f"{len(gpus)} GPU(s) detected: {gpus[0].name}")
        else:
            print_check("GPU Support", False, "No GPU detected (CPU training will be slower)")

        return version_ok
    except ImportError:
        print_check("TensorFlow", False, "Not installed")
        return False

def check_prometheus_imports():
    """Check Prometheus package imports."""
    imports_ok = True

    # Core imports
    core_imports = [
        ("prometheus.models.go_models", "Go models"),
        ("prometheus.models.chess_models", "Chess models"),
        ("prometheus.environments.go", "Go environment"),
        ("prometheus.environments.chess_env", "Chess environment"),
        ("prometheus.mcts", "MCTS"),
        ("prometheus.training.go_training", "Go training"),
        ("prometheus.training.chess_training", "Chess training"),
        ("prometheus.evaluation.benchmark", "Go evaluator"),
        ("prometheus.evaluation.chess_evaluator", "Chess evaluator"),
    ]

    for module, name in core_imports:
        try:
            __import__(module)
            print_check(name, True)
        except ImportError as e:
            print_check(name, False, str(e))
            imports_ok = False

    return imports_ok

def check_scripts():
    """Check if training and benchmark scripts exist."""
    scripts = [
        "scripts/train_pretrained_models.py",
        "scripts/benchmark_models.py",
    ]

    all_ok = True
    for script in scripts:
        path = Path(script)
        ok = path.exists()
        print_check(script, ok, "Found" if ok else "Missing")
        all_ok = all_ok and ok

    return all_ok

def check_disk_space():
    """Check available disk space."""
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        free_mb = free // (1024 * 1024)
        ok = free_mb >= 500  # Need at least 500MB

        print_check(
            "Disk Space",
            ok,
            f"{free_mb} MB free " + ("(OK)" if ok else "(need >= 500 MB)")
        )
        return ok
    except Exception as e:
        print_check("Disk Space", False, f"Could not check: {e}")
        return False

def check_output_directory():
    """Check if output directory exists or can be created."""
    output_dir = Path("models/pretrained")

    if output_dir.exists():
        ok = output_dir.is_dir()
        print_check("Output Directory", ok, f"{output_dir} exists")
    else:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            print_check("Output Directory", True, f"Created {output_dir}")
            ok = True
        except Exception as e:
            print_check("Output Directory", False, f"Cannot create: {e}")
            ok = False

    return ok

def estimate_training_time():
    """Estimate training time based on hardware."""
    try:
        import tensorflow as tf
        gpus = tf.config.list_physical_devices('GPU')

        if gpus:
            time_estimate = "2-3 hours (GPU accelerated)"
        else:
            time_estimate = "6-10 hours (CPU only, slower)"

        print(f"\n⏱️  Estimated training time: {time_estimate}")
    except:
        print(f"\n⏱️  Estimated training time: 2-10 hours (depends on hardware)")

def print_next_steps(all_ok):
    """Print next steps."""
    print_header("NEXT STEPS")

    if all_ok:
        print("\n✅ Environment is ready for Phase B training!")
        print("\nRun the following command to start training:\n")
        print("    python scripts/train_pretrained_models.py --all\n")
        print("Or train individual models:")
        print("    python scripts/train_pretrained_models.py --model go-9x9")
        print("    python scripts/train_pretrained_models.py --model go-19x19")
        print("    python scripts/train_pretrained_models.py --model chess")
        print("\nSee PHASE_B_TRAINING_GUIDE.md for detailed instructions.")
    else:
        print("\n❌ Environment is not ready. Please fix the issues above.\n")
        print("Installation instructions:")
        print("    pip install --upgrade pip")
        print("    pip install -r requirements.txt")
        print("    pip install -e .")
        print("\nSee PHASE_B_TRAINING_GUIDE.md for troubleshooting.")

def main():
    """Run all checks."""
    print_header("PHASE B READINESS CHECK")
    print("\nChecking environment for model training...\n")

    all_checks = []

    # Python version
    print_header("1. Python Environment")
    all_checks.append(check_python_version())

    # Core dependencies
    print_header("2. Core Dependencies")
    all_checks.append(check_module("numpy"))
    all_checks.append(check_module("scipy"))
    all_checks.append(check_module("matplotlib"))
    all_checks.append(check_tensorflow())
    all_checks.append(check_module("chess", "python-chess"))

    # Prometheus imports
    print_header("3. Prometheus Package")
    all_checks.append(check_prometheus_imports())

    # Scripts
    print_header("4. Training Scripts")
    all_checks.append(check_scripts())

    # System requirements
    print_header("5. System Requirements")
    all_checks.append(check_disk_space())
    all_checks.append(check_output_directory())

    # Summary
    all_ok = all(all_checks)

    estimate_training_time()
    print_next_steps(all_ok)

    print("\n" + "=" * 70)

    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main())
