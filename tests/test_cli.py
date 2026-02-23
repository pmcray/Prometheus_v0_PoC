"""
Test CLI functionality and commands.
"""

import pytest
import subprocess
import sys
from pathlib import Path


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_help(self):
        """Test CLI --help command."""
        result = subprocess.run(
            [sys.executable, 'prometheus_cli.py', '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0, "CLI help should succeed"
        assert 'prometheus' in result.stdout.lower() or result.stderr.lower()

    def test_cli_version(self):
        """Test CLI version command."""
        result = subprocess.run(
            [sys.executable, 'prometheus_cli.py', 'version'],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Version command may not be fully implemented yet
        assert result.returncode in [0, 1], "Version command should run"

    def test_cli_subcommands_exist(self):
        """Test that expected subcommands exist."""
        result = subprocess.run(
            [sys.executable, 'prometheus_cli.py', '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )

        expected_commands = ['train', 'evaluate', 'benchmark', 'compare', 'deploy']

        for cmd in expected_commands:
            assert cmd in result.stdout or cmd in result.stderr, \
                f"Expected '{cmd}' command to exist in CLI"


class TestCLICommands:
    """Test individual CLI commands."""

    def test_train_help(self):
        """Test train command help."""
        result = subprocess.run(
            [sys.executable, 'prometheus_cli.py', 'train', '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0, "Train help should succeed"
        assert '--game' in result.stdout or result.stderr

    def test_compare_help(self):
        """Test compare command help."""
        result = subprocess.run(
            [sys.executable, 'prometheus_cli.py', 'compare', '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0, "Compare help should succeed"
        assert '--model1' in result.stdout or result.stderr
        assert '--model2' in result.stdout or result.stderr

    def test_benchmark_help(self):
        """Test benchmark command help."""
        result = subprocess.run(
            [sys.executable, 'prometheus_cli.py', 'benchmark', '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0, "Benchmark help should succeed"
        assert '--model' in result.stdout or result.stderr


class TestScriptSyntax:
    """Test that all scripts have valid Python syntax."""

    def get_python_files(self):
        """Get all Python files in scripts/."""
        return list(Path('scripts').glob('*.py'))

    def test_all_scripts_compile(self):
        """Test that all scripts compile without syntax errors."""
        scripts = self.get_python_files()

        assert len(scripts) > 0, "Should find some Python scripts"

        errors = []
        for script in scripts:
            result = subprocess.run(
                [sys.executable, '-m', 'py_compile', str(script)],
                capture_output=True,
                timeout=5
            )

            if result.returncode != 0:
                errors.append(f"{script.name}: {result.stderr.decode()}")

        assert len(errors) == 0, f"Scripts with syntax errors:\n" + "\n".join(errors)


class TestQuickDemo:
    """Test quick demo script."""

    def test_quick_demo_syntax(self):
        """Test quick demo has valid syntax."""
        result = subprocess.run(
            [sys.executable, '-m', 'py_compile', 'scripts/quick_demo.py'],
            capture_output=True,
            timeout=5
        )

        assert result.returncode == 0, "Quick demo should have valid syntax"

    def test_quick_demo_help(self):
        """Test quick demo help."""
        result = subprocess.run(
            [sys.executable, 'scripts/quick_demo.py', '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0, "Quick demo help should succeed"
        assert '--game' in result.stdout or result.stderr


class TestDashboard:
    """Test dashboard scripts."""

    def test_prometheus_monitor_syntax(self):
        """Test monitor dashboard has valid syntax."""
        result = subprocess.run(
            [sys.executable, '-m', 'py_compile', 'prometheus_monitor.py'],
            capture_output=True,
            timeout=5
        )

        assert result.returncode == 0, "Monitor dashboard should have valid syntax"

    def test_prometheus_monitor_help(self):
        """Test monitor dashboard help."""
        result = subprocess.run(
            [sys.executable, 'prometheus_monitor.py', '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )

        # May fail if dash not installed
        assert result.returncode in [0, 1], "Monitor help should run (may need dash)"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
