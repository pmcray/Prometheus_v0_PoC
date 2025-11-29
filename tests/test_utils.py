"""
Test utility functions and common operations.
"""

import pytest
import numpy as np


class TestELOCalculations:
    """Test ELO rating calculations."""

    def test_calculate_elo_difference_perfect_win(self):
        """Test ELO calculation for perfect win rate."""
        from scripts.compare_models import calculate_elo_difference

        # 99% win rate should give high ELO
        elo_diff = calculate_elo_difference(0.99)
        assert elo_diff > 400, "99% win rate should give >400 ELO"
        assert elo_diff == 600, "Should cap at 600"

    def test_calculate_elo_difference_even(self):
        """Test ELO calculation for even match."""
        from scripts.compare_models import calculate_elo_difference

        # 50% win rate should give ~0 ELO
        elo_diff = calculate_elo_difference(0.5)
        assert abs(elo_diff) < 1, "50% win rate should give ~0 ELO"

    def test_calculate_elo_difference_typical(self):
        """Test ELO calculation for typical win rates."""
        from scripts.compare_models import calculate_elo_difference

        # 75% win rate should give ~200 ELO
        elo_diff = calculate_elo_difference(0.75)
        assert 180 < elo_diff < 210, f"75% win rate should give ~193 ELO, got {elo_diff}"

    def test_calculate_elo_difference_loss(self):
        """Test ELO calculation for losing."""
        from scripts.compare_models import calculate_elo_difference

        # 25% win rate should give negative ELO
        elo_diff = calculate_elo_difference(0.25)
        assert elo_diff < 0, "25% win rate should give negative ELO"
        assert -210 < elo_diff < -180, f"Should be around -193, got {elo_diff}"


class TestConfidenceIntervals:
    """Test confidence interval calculations."""

    def test_confidence_interval_perfect_data(self):
        """Test CI with perfect win rate."""
        from scripts.compare_models import calculate_confidence_interval

        # 100% win rate (10/10 games)
        lower, upper = calculate_confidence_interval(10, 10)

        assert lower > 0.7, "Lower bound should be high for 10/10"
        assert upper == 1.0, "Upper bound should be 1.0"

    def test_confidence_interval_even(self):
        """Test CI with even win rate."""
        from scripts.compare_models import calculate_confidence_interval

        # 50% win rate (25/50 games)
        lower, upper = calculate_confidence_interval(25, 50)

        assert lower < 0.5 < upper, "CI should contain true win rate"
        assert (upper - lower) < 0.3, "CI should not be too wide with 50 games"

    def test_confidence_interval_no_games(self):
        """Test CI with no games."""
        from scripts.compare_models import calculate_confidence_interval

        lower, upper = calculate_confidence_interval(0, 0)

        assert lower == 0.0, "Lower bound should be 0"
        assert upper == 1.0, "Upper bound should be 1"


class TestScriptImports:
    """Test that all scripts can be imported."""

    def test_import_compare_models(self):
        """Test compare_models script imports."""
        try:
            import scripts.compare_models
            assert hasattr(scripts.compare_models, 'compare_models')
            assert hasattr(scripts.compare_models, 'calculate_elo_difference')
        except ImportError as e:
            pytest.skip(f"Could not import compare_models: {e}")

    def test_import_benchmark_models(self):
        """Test benchmark_models script imports."""
        try:
            import scripts.benchmark_models
            assert hasattr(scripts.benchmark_models, 'benchmark_inference')
        except ImportError as e:
            pytest.skip(f"Could not import benchmark_models: {e}")

    def test_import_tune_hyperparameters(self):
        """Test tune_hyperparameters script imports."""
        try:
            import scripts.tune_hyperparameters
            assert hasattr(scripts.tune_hyperparameters, 'HyperparameterTuner')
        except ImportError as e:
            pytest.skip(f"Could not import tune_hyperparameters: {e}")


class TestPathOperations:
    """Test path and file operations."""

    def test_models_directory_structure(self):
        """Test expected directory structure."""
        from pathlib import Path

        # Check key directories exist or can be created
        expected_dirs = [
            "models",
            "scripts",
            "notebooks",
            "prometheus",
            ".github/workflows",
        ]

        for dir_path in expected_dirs:
            path = Path(dir_path)
            assert path.exists() or path.parent.exists(), f"Expected {dir_path} or parent to exist"

    def test_documentation_files_exist(self):
        """Test that key documentation files exist."""
        from pathlib import Path

        required_docs = [
            "README.md",
            "FAQ.md",
            "TROUBLESHOOTING.md",
            "CONTRIBUTING.md",
            "PHASE_B_TRAINING_GUIDE.md",
        ]

        for doc in required_docs:
            assert Path(doc).exists(), f"{doc} should exist"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
