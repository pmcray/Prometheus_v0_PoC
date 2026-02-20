"""
Tests for ARC CRLS Strange Loop (arc_crls_strange_loop.py)

Tests the full pipeline without needing ARC data files or an LLM API key.
Uses synthetic tasks and mock LLM responses.
"""
import json
import textwrap
import numpy as np
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers (must be defined before class bodies that reference them)
# ---------------------------------------------------------------------------

def textwrap_dedent(s):
    return textwrap.dedent(s).strip()


def _make_task(in_grid, out_grid):
    """Build a minimal ARC task dict for testing."""
    return {"train": [{"input": in_grid, "output": out_grid}],
            "test": [{"input": in_grid}]}


# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------

from arc_crls_strange_loop import (
    ARCTaskResult,
    ARCFailurePatternAnalyser,
    SynthesizedOpValidator,
    SynthesizedOperation,
    FAILURE_THRESHOLD,
    SAFETY_SMOKE_TEST_GRID,
    ARCCRLSStrangeLoop,
)
from arc_parametric_operations import PARAMETRIC_OPERATIONS


# ---------------------------------------------------------------------------
# ARCTaskResult
# ---------------------------------------------------------------------------

class TestARCTaskResult:
    def test_failure_threshold_below(self):
        r = ARCTaskResult("t1", 0.1, [], "low fitness", [], [])
        assert r.best_fitness < FAILURE_THRESHOLD

    def test_success_threshold(self):
        r = ARCTaskResult("t1", 0.97, ["rotate"], "ok", [], [])
        assert r.best_fitness >= 0.95


# ---------------------------------------------------------------------------
# ARCFailurePatternAnalyser
# ---------------------------------------------------------------------------

class TestARCFailurePatternAnalyser:
    def _make_failure(self, in_grid, out_grid, task_id="t1", fitness=0.1):
        return ARCTaskResult(
            task_id=task_id,
            best_fitness=fitness,
            program_ops=[],
            failure_pattern="",
            attempted_ops=[],
            train_examples=[{"input": in_grid, "output": out_grid}],
        )

    def test_size_scaling_detected(self):
        analyser = ARCFailurePatternAnalyser()
        # Output is 2× the input in both dimensions → SIZE_SCALING
        f = self._make_failure([[1, 2], [3, 4]], [[1, 2, 1, 2], [3, 4, 3, 4],
                                                    [1, 2, 1, 2], [3, 4, 3, 4]])
        analysis = analyser.analyse([f])
        assert "SIZE_SCALING" in analysis["pattern_frequencies"]

    def test_repetition_detected(self):
        analyser = ARCFailurePatternAnalyser()
        # Output height is 2× input → REPETITION
        f = self._make_failure([[1, 2]], [[1, 2], [1, 2]])
        analysis = analyser.analyse([f])
        assert "REPETITION" in analysis["pattern_frequencies"]

    def test_multi_object_detected(self):
        analyser = ARCFailurePatternAnalyser()
        # Input has two disconnected objects → OBJECT_SELECTION / CONNECTIVITY
        f = self._make_failure(
            [[1, 0, 2], [0, 0, 0], [0, 0, 3]],
            [[1, 0, 2], [0, 0, 0], [0, 0, 3]]
        )
        analysis = analyser.analyse([f])
        assert any(p in analysis["pattern_frequencies"]
                   for p in ["OBJECT_SELECTION", "CONNECTIVITY"])

    def test_symmetry_detected(self):
        analyser = ARCFailurePatternAnalyser()
        # Output is a 3×3 grid that is horizontally symmetric (fliplr == itself)
        f = self._make_failure(
            [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            [[1, 2, 1], [3, 4, 3], [5, 6, 5]]   # square + horizontally symmetric
        )
        analysis = analyser.analyse([f])
        assert "SYMMETRY" in analysis["pattern_frequencies"]

    def test_empty_failures(self):
        analyser = ARCFailurePatternAnalyser()
        analysis = analyser.analyse([])
        assert analysis["total_failures"] == 0

    def test_synthesis_prompt_contains_format(self):
        analyser = ARCFailurePatternAnalyser()
        f = self._make_failure([[1]], [[0]])
        prompt = analyser.get_synthesis_prompt([f], ["rotate", "flip"])
        assert "OPERATION_NAME" in prompt
        assert "np.ndarray" in prompt
        assert "# PARAMS:" in prompt
        assert "# DESCRIPTION:" in prompt


# ---------------------------------------------------------------------------
# SynthesizedOpValidator
# ---------------------------------------------------------------------------

class TestSynthesizedOpValidator:

    VALID_CODE = textwrap_dedent("""
        def test_invert(grid: np.ndarray, max_val: int = 9, **kwargs) -> np.ndarray:
            \"\"\"Invert values.\"\"\"
            return np.clip(max_val - grid, 0, 9).astype(grid.dtype)
    """)

    UNSAFE_CODE = textwrap_dedent("""
        def evil_op(grid: np.ndarray, **kwargs) -> np.ndarray:
            exec("import os")
            return grid.copy()
    """)

    BAD_SYNTAX_CODE = "def broken(grid\n    return grid"

    RETURNS_NON_ARRAY = textwrap_dedent("""
        def bad_return(grid: np.ndarray, **kwargs):
            \"\"\"Returns a list instead of ndarray.\"\"\"
            return [[0, 1], [2, 3]]
    """)

    def _v(self):
        return SynthesizedOpValidator()

    def test_valid_code_passes(self):
        v = self._v()
        is_valid, reason, fn = v.validate("test_invert", self.VALID_CODE, 1)
        assert is_valid, reason
        assert fn is not None

    def test_unsafe_code_rejected(self):
        v = self._v()
        is_valid, reason, fn = v.validate("evil_op", self.UNSAFE_CODE, 1)
        assert not is_valid
        assert fn is None

    def test_bad_syntax_rejected(self):
        v = self._v()
        is_valid, reason, fn = v.validate("broken", self.BAD_SYNTAX_CODE, 1)
        assert not is_valid
        assert "SyntaxError" in reason

    def test_non_array_return_rejected(self):
        v = self._v()
        is_valid, reason, fn = v.validate("bad_return", self.RETURNS_NON_ARRAY, 1)
        assert not is_valid

    def test_extract_code_block(self):
        raw = "Some text\n```python\ndef foo(): pass\n```\nmore text"
        code = SynthesizedOpValidator.extract_code_block(raw)
        assert "def foo" in code

    def test_extract_function_name(self):
        code = "def my_op(grid, **kwargs): return grid"
        name = SynthesizedOpValidator.extract_function_name(code)
        assert name == "my_op"

    def test_extract_function_name_none_on_empty(self):
        name = SynthesizedOpValidator.extract_function_name("")
        assert name is None

    def test_parse_params_and_description(self):
        raw = '# PARAMS: {"color": {"type": "int", "values": [1,2], "default": 1}}\n# DESCRIPTION: "do stuff"'
        params, desc = SynthesizedOpValidator.parse_params_and_description(raw)
        assert "color" in params
        assert desc == "do stuff"

    def test_parse_empty_response(self):
        params, desc = SynthesizedOpValidator.parse_params_and_description("")
        assert params == {}
        assert desc == "Synthesized operation"


# ---------------------------------------------------------------------------
# ARCCRLSStrangeLoop (unit-level, no files / no LLM)
# ---------------------------------------------------------------------------

class TestARCCRLSStrangeLoop:
    """
    Tests the orchestrator's internal methods using mocking so we don't
    need ARC data files or an LLM API key.
    """

    def _make_loop(self, tmp_path):
        # Patch get_llm_backend to avoid loading a real model
        with patch("arc_crls_strange_loop.get_llm_backend") as mock_llm:
            mock_llm.return_value = MagicMock()
            loop = ARCCRLSStrangeLoop(
                task_ids=["task_a", "task_b"],
                arc_data_dir=str(tmp_path),
                max_generations=2,
                beam_width=10,
                max_depth=3,
                verbose=False,
            )
        return loop

    def test_diagnose_failure_size_change(self, tmp_path):
        loop = self._make_loop(tmp_path)
        task = _make_task([[1, 2], [3, 4]], [[1, 2, 0, 0], [3, 4, 0, 0],
                                              [0, 0, 0, 0], [0, 0, 0, 0]])
        diag = loop._diagnose_failure(task, 0.1, [])
        assert "size_change" in diag

    def test_diagnose_failure_symmetric_output(self, tmp_path):
        loop = self._make_loop(tmp_path)
        task = _make_task([[1, 2, 3]], [[1, 2, 1]])
        diag = loop._diagnose_failure(task, 0.3, [])
        assert "symmetric" in diag

    def test_register_ops(self, tmp_path):
        loop = self._make_loop(tmp_path)
        initial_count = len(PARAMETRIC_OPERATIONS)

        # Create a valid synthesized op
        def _dummy_op(grid, **kwargs):
            return grid.copy()

        op = SynthesizedOperation(
            name="_crls_test_op_unique_xyz",
            description="test op",
            source_code="def _crls_test_op_unique_xyz(grid, **kwargs): return grid.copy()",
            params_spec={},
            safety_approved=True,
            smoke_test_passed=True,
            generation=1,
            failure_patterns_that_triggered=["SIZE_SCALING"],
        )
        op._compiled_fn = _dummy_op

        loop._register_ops([op])
        assert "_crls_test_op_unique_xyz" in PARAMETRIC_OPERATIONS
        # Cleanup
        del PARAMETRIC_OPERATIONS["_crls_test_op_unique_xyz"]
        assert len(PARAMETRIC_OPERATIONS) == initial_count

    def test_solve_tasks_skips_missing_files(self, tmp_path):
        loop = self._make_loop(tmp_path)
        # No JSON files in tmp_path — should skip gracefully
        results = loop._solve_tasks(["nonexistent_task"])
        assert results == []

    def test_solve_tasks_with_real_task_file(self, tmp_path):
        """Create a minimal task file and verify solve_tasks returns a result."""
        task_data = _make_task([[1, 0], [0, 1]], [[0, 1], [1, 0]])
        task_file = tmp_path / "mini_task.json"
        task_file.write_text(json.dumps(task_data))

        loop = self._make_loop(tmp_path)
        results = loop._solve_tasks(["mini_task"])
        assert len(results) == 1
        assert results[0].task_id == "mini_task"
        assert 0.0 <= results[0].best_fitness <= 1.0

    def test_generation_report_format(self, tmp_path):
        loop = self._make_loop(tmp_path)
        loop.generation_log = [
            {"generation": 1, "tasks_solved_this_gen": 2,
             "tasks_failed": 3, "new_ops": ["op_a"],
             "total_ops": 51, "top_patterns": [("SIZE_SCALING", 2)]}
        ]
        loop.solved_task_ids = ["t1", "t2"]
        report = loop.get_generation_report()
        assert "Generation 1" in report
        assert "op_a" in report
        assert "2 / 2" in report or "2/" in report

    def test_save_synthesized_ops_empty(self, tmp_path):
        loop = self._make_loop(tmp_path)
        loop.synthesized_ops = []
        # Should not raise
        out_file = str(tmp_path / "ops.py")
        loop.save_synthesized_ops(out_file)

    def test_save_synthesized_ops_writes_file(self, tmp_path):
        loop = self._make_loop(tmp_path)

        def _dummy_op(grid, **kwargs):
            return grid.copy()

        op = SynthesizedOperation(
            name="_crls_save_test_op",
            description="save test",
            source_code="def _crls_save_test_op(grid, **kwargs):\n    return grid.copy()",
            params_spec={},
            safety_approved=True,
            smoke_test_passed=True,
            generation=1,
            failure_patterns_that_triggered=["CONNECTIVITY"],
        )
        op._compiled_fn = _dummy_op
        loop.synthesized_ops = [op]

        out_file = str(tmp_path / "saved_ops.py")
        loop.save_synthesized_ops(out_file)
        content = Path(out_file).read_text()
        assert "_crls_save_test_op" in content
        assert "SYNTHESIZED_OPERATIONS" in content


