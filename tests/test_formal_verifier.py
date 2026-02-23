"""
tests/test_formal_verifier.py — WP7 Formal Verification

Tests for:
  - CodeProperties extraction (extract_properties)
  - PrometheusConstitution (Z3 constraint checking)
  - FormalVerifier (verify, verify_and_critique, batch_verify, stats)
  - integrate_with_supervisor (MCSSupervisor integration)
  - FormalVerificationBenchmark (benign / unsafe / throughput scenarios)

Run with:
    pytest tests/test_formal_verifier.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prometheus.safety.constitution import (
    CodeProperties,
    PrometheusConstitution,
    extract_properties,
    MAX_CODE_LENGTH,
)
from prometheus.formal_verifier import (
    FormalVerifier,
    FormalVerificationResult,
    integrate_with_supervisor,
)
from prometheus.safety.mcs_supervisor import MCSSupervisor, SafetyCritique
from benchmarks.formal_verification_benchmark import (
    FormalVerificationBenchmark,
    BENIGN_CORPUS,
    UNSAFE_CORPUS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _verify(code: str) -> FormalVerificationResult:
    fv = FormalVerifier()
    return fv.verify(code)


# ---------------------------------------------------------------------------
# extract_properties — property extraction
# ---------------------------------------------------------------------------

class TestExtractProperties:

    def test_benign_code_all_zeros(self):
        props = extract_properties("x = 1 + 2")
        assert props.n_forbidden_imports  == 0
        assert props.n_forbidden_calls    == 0
        assert props.n_obfuscation_calls  == 0
        assert props.n_file_writes        == 0
        assert props.n_network_calls      == 0
        assert props.n_exec_calls         == 0
        assert props.n_self_modifications == 0
        assert props.has_infinite_loop    == 0
        assert props.n_assertion_deletes  == 0
        assert not props.syntax_error

    def test_forbidden_import_detected(self):
        props = extract_properties("import os\nos.getcwd()")
        assert props.n_forbidden_imports >= 1

    def test_forbidden_call_eval_detected(self):
        props = extract_properties("result = eval('1+1')")
        assert props.n_forbidden_calls >= 1
        assert props.n_exec_calls      >= 1

    def test_forbidden_call_exec_detected(self):
        props = extract_properties("exec('x = 1')")
        assert props.n_exec_calls >= 1

    def test_obfuscation_importlib_detected(self):
        props = extract_properties(
            "import importlib\nm = importlib.import_module('os')"
        )
        assert props.n_obfuscation_calls >= 1

    def test_obfuscation_base64_detected(self):
        props = extract_properties(
            "import base64\nexec(base64.b64decode('aW1wb3J0IG9z').decode())"
        )
        assert props.n_obfuscation_calls >= 1

    def test_obfuscation_dunder_import_detected(self):
        props = extract_properties("os = __import__('os')")
        assert props.n_obfuscation_calls >= 1

    def test_infinite_loop_detected(self):
        props = extract_properties("while True:\n    pass")
        assert props.has_infinite_loop == 1

    def test_while_with_break_not_flagged(self):
        props = extract_properties(
            "while True:\n    x = 1\n    break"
        )
        assert props.has_infinite_loop == 0

    def test_file_write_detected(self):
        props = extract_properties("f = open('out.txt', 'w')\nf.write('x')")
        assert props.n_file_writes >= 1

    def test_file_read_not_flagged_as_write(self):
        # open for reading is fine (no 'w' mode)
        props = extract_properties("f = open('in.txt', 'r')\ndata = f.read()")
        assert props.n_file_writes == 0

    def test_assertion_delete_detected(self):
        props = extract_properties(
            "def test_foo():\n    pass\ndel test_foo"
        )
        assert props.n_assertion_deletes >= 1

    def test_syntax_error_captured(self):
        props = extract_properties("def broken(:\n    pass")
        assert props.syntax_error
        assert props.syntax_error_msg != ""

    def test_code_length_tracked(self):
        code = "x = 1\n" * 100
        props = extract_properties(code)
        assert props.code_length == len(code)

    def test_self_modification_globals_detected(self):
        props = extract_properties("globals()['evil'] = 1")
        assert props.n_self_modifications >= 1

    def test_self_modification_sys_modules_detected(self):
        props = extract_properties("import sys\nsys.modules['os'] = None")
        assert props.n_self_modifications >= 1


# ---------------------------------------------------------------------------
# PrometheusConstitution — Z3 constraint checking
# ---------------------------------------------------------------------------

class TestPrometheusConstitution:

    def setup_method(self):
        self.constitution = PrometheusConstitution()

    def test_benign_props_satisfy_all_constraints(self):
        props = extract_properties("result = 42")
        result, violations = self.constitution.check(props)
        assert violations == []

    def test_forbidden_import_violated(self):
        props = extract_properties("import os")
        _, violations = self.constitution.check(props)
        names = [v["principle"] for v in violations]
        assert any("Forbidden Imports" in n for n in names)

    def test_obfuscation_violated(self):
        props = extract_properties(
            "import importlib\nimportlib.import_module('os')"
        )
        _, violations = self.constitution.check(props)
        names = [v["principle"] for v in violations]
        assert any("Obfuscation" in n for n in names)

    def test_infinite_loop_violated(self):
        props = extract_properties("while True:\n    pass")
        _, violations = self.constitution.check(props)
        names = [v["principle"] for v in violations]
        assert any("Unbounded" in n for n in names)

    def test_exec_call_violated(self):
        props = extract_properties("exec('import os')")
        _, violations = self.constitution.check(props)
        names = [v["principle"] for v in violations]
        assert any("Dynamic Execution" in n for n in names)

    def test_oversized_code_violated(self):
        props = CodeProperties(code_length=MAX_CODE_LENGTH + 1)
        _, violations = self.constitution.check(props)
        names = [v["principle"] for v in violations]
        assert any("Code Size" in n for n in names)

    def test_syntax_error_returns_violation(self):
        props = extract_properties("def broken(:\n    pass")
        _, violations = self.constitution.check(props)
        assert len(violations) >= 1
        assert violations[0]["principle"] == "Syntax"

    def test_violation_has_required_fields(self):
        props = extract_properties("import os")
        _, violations = self.constitution.check(props)
        assert violations
        v = violations[0]
        assert "principle"   in v
        assert "description" in v
        assert "severity"    in v
        assert "msg"         in v

    def test_summary_contains_all_principles(self):
        summary = self.constitution.summary()
        assert "Resource Boundaries" in summary
        assert "Liveness" in summary
        assert "Integrity of Evaluation" in summary

    def test_multiple_violations_reported(self):
        # Code with both a forbidden import and an infinite loop
        props = extract_properties("import os\nwhile True:\n    pass")
        _, violations = self.constitution.check(props)
        assert len(violations) >= 2


# ---------------------------------------------------------------------------
# FormalVerifier — core interface
# ---------------------------------------------------------------------------

class TestFormalVerifier:

    def setup_method(self):
        self.fv = FormalVerifier()

    def test_benign_code_is_safe(self):
        result = self.fv.verify("x = 1 + 2\nresult = x * 3")
        assert result.is_safe
        assert result.z3_result == "sat"
        assert result.violations == []

    def test_forbidden_import_unsafe(self):
        result = self.fv.verify("import os\nos.system('ls')")
        assert not result.is_safe
        assert len(result.violations) >= 1

    def test_importlib_bypass_caught(self):
        result = self.fv.verify(
            "import importlib\nm = importlib.import_module('os')"
        )
        assert not result.is_safe

    def test_base64_exec_bypass_caught(self):
        result = self.fv.verify(
            "import base64\nexec(base64.b64decode('aW1wb3J0IG9z').decode())"
        )
        assert not result.is_safe

    def test_dunder_import_bypass_caught(self):
        result = self.fv.verify("os = __import__('os')\nos.getcwd()")
        assert not result.is_safe

    def test_compile_exec_bypass_caught(self):
        result = self.fv.verify(
            "code = compile('import os', '<s>', 'exec')\nexec(code)"
        )
        assert not result.is_safe

    def test_infinite_loop_caught(self):
        result = self.fv.verify("while True:\n    pass")
        assert not result.is_safe

    def test_delete_test_function_caught(self):
        result = self.fv.verify(
            "def test_foo():\n    pass\ndel test_foo"
        )
        assert not result.is_safe

    def test_verify_time_is_positive(self):
        result = self.fv.verify("x = 1")
        assert result.verify_time_s > 0.0

    def test_properties_extracted(self):
        result = self.fv.verify("x = 1")
        assert isinstance(result.properties, CodeProperties)
        assert result.properties.code_length > 0

    def test_worst_severity_zero_when_safe(self):
        result = self.fv.verify("x = 42")
        assert result.worst_severity == 0

    def test_worst_severity_nonzero_when_unsafe(self):
        result = self.fv.verify("import os")
        assert result.worst_severity > 0

    def test_summary_string_safe(self):
        result = self.fv.verify("x = 1")
        assert "SAFE" in result.summary()

    def test_summary_string_unsafe(self):
        result = self.fv.verify("import os")
        assert "UNSAFE" in result.summary()

    def test_stats_counts_verifications(self):
        fv = FormalVerifier()
        fv.verify("x = 1")
        fv.verify("import os")
        stats = fv.stats()
        assert stats["n_verified"]   == 2
        assert stats["n_violations"] == 1

    def test_batch_verify_returns_all_results(self):
        codes   = ["x = 1", "y = 2", "import os"]
        results = self.fv.batch_verify(codes)
        assert len(results) == 3
        assert results[0].is_safe
        assert results[1].is_safe
        assert not results[2].is_safe

    def test_verify_and_critique_safe(self):
        critique = self.fv.verify_and_critique("x = 1")
        assert isinstance(critique, SafetyCritique)
        assert critique.is_safe

    def test_verify_and_critique_unsafe(self):
        critique = self.fv.verify_and_critique("import os\nexec('ls')")
        assert isinstance(critique, SafetyCritique)
        assert not critique.is_safe
        assert critique.violation_type is not None
        assert critique.severity > 0


# ---------------------------------------------------------------------------
# integrate_with_supervisor
# ---------------------------------------------------------------------------

class TestIntegrateWithSupervisor:

    def setup_method(self):
        self.supervisor = MCSSupervisor()
        self.verifier   = FormalVerifier()
        integrate_with_supervisor(self.supervisor, self.verifier)

    def test_patched_supervisor_passes_safe_plan(self):
        critique = self.supervisor.verify_modification("", "x = 42", "plan.py")
        assert critique.is_safe

    def test_patched_supervisor_blocks_forbidden_import(self):
        critique = self.supervisor.verify_modification(
            "", "import os\nos.system('ls')", "plan.py"
        )
        assert not critique.is_safe

    def test_patched_supervisor_blocks_obfuscated_bypass(self):
        critique = self.supervisor.verify_modification(
            "",
            "import importlib\nm = importlib.import_module('os')",
            "plan.py",
        )
        assert not critique.is_safe

    def test_verifier_attached_to_supervisor(self):
        assert hasattr(self.supervisor, "_formal_verifier")

    def test_test_file_still_blocked_by_original(self):
        # The original MCSSupervisor blocks test-file modifications;
        # the patched version should too (falls through after FV passes).
        critique = self.supervisor.verify_modification(
            "", "x = 1", "tests/test_foo.py"
        )
        assert not critique.is_safe


# ---------------------------------------------------------------------------
# FormalVerificationBenchmark
# ---------------------------------------------------------------------------

class TestFormalVerificationBenchmark:

    def setup_method(self):
        self.bench = FormalVerificationBenchmark()

    def test_benign_corpus_zero_false_positives(self):
        result = self.bench.run("benign_corpus")
        assert result.fv_fp == 0, (
            f"FormalVerifier produced false positives on benign corpus: "
            f"{[d['name'] for d in result.details if d['fv_flagged']]}"
        )

    def test_unsafe_corpus_all_caught_by_fv(self):
        result = self.bench.run("unsafe_corpus")
        missed = [d["name"] for d in result.details if not d["fv_flagged"]]
        assert result.fv_fn == 0, (
            f"FormalVerifier missed unsafe plans: {missed}"
        )

    def test_fv_outperforms_guard_on_unsafe(self):
        result = self.bench.run("unsafe_corpus")
        # FV should catch at least as many unsafe plans as the guard
        assert result.fv_tp >= result.guard_tp

    def test_throughput_produces_valid_result(self):
        result = self.bench.run("throughput")
        assert result.fv_mean_ms > 0.0
        assert result.guard_mean_ms > 0.0
        assert result.corpus_size == 100

    def test_run_all_returns_three_results(self):
        results = self.bench.run_all()
        assert len(results) == 3
        assert {r.scenario for r in results} == {
            "benign_corpus", "unsafe_corpus", "throughput"
        }

    def test_summary_table_non_empty(self):
        results = self.bench.run_all()
        table   = self.bench.summary_table(results)
        assert "benign_corpus" in table
        assert "unsafe_corpus" in table
        assert "throughput"    in table

    def test_unknown_scenario_raises(self):
        with pytest.raises(ValueError, match="Unknown scenario"):
            self.bench.run("nonexistent")

    def test_detail_records_have_required_keys(self):
        result = self.bench.run("benign_corpus")
        for d in result.details:
            for key in ["name", "label_unsafe", "fv_flagged",
                        "guard_flagged", "fv_ms", "guard_ms"]:
                assert key in d
