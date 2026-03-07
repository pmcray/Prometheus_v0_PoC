"""
WP63 Test Suite: Competitive Programming Solver (IOI Bronze)
=============================================================

TestIOIProblem            Problem dataclass, test-case structure
TestSandboxRunner         Execute, timeout, error handling
TestTemplateLibrary       By category, all templates
TestIOISolver             Solve problem, candidate selection
TestIOIBenchmark          run_benchmark, report
TestWP63ExitCriteria      Six-criterion verifier
TestIntegration           End-to-end: benchmark → report
"""

import pytest

from prometheus.wp63_ioi_solver import (
    AlgorithmTemplate,
    IOIBenchmark,
    IOIBenchmarkReport,
    IOIProblem,
    IOIResult,
    IOISolver,
    SandboxRunner,
    SolutionCandidate,
    TemplateLibrary,
    verify_wp63_exit_criteria,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HELLO_PROBLEM = IOIProblem(
    problem_id="hello",
    title="Hello N Times",
    category="simulation",
    description="Read N and print 'hello' N times",
    input_format="Single integer N",
    output_format="N lines each containing 'hello'",
    sample_io=[("3\n", "hello\nhello\nhello\n")],
    time_limit_s=1.0,
)

_SORT_PROBLEM = IOIProblem(
    problem_id="sort_n",
    title="Sort N Integers",
    category="sorting",
    description="Read N integers on a line, print them sorted ascending",
    input_format="Space-separated integers",
    output_format="Space-separated sorted integers",
    sample_io=[("5 3 1 4 1 5\n", "1 1 3 4 5\n")],
    time_limit_s=1.0,
)

_TRIVIAL_SOLUTION = """\
import sys
n = int(sys.stdin.readline())
for _ in range(n):
    print('hello')
"""


def _solver(seed: int = 0) -> IOISolver:
    return IOISolver(top_k=3, n_evolution_steps=1, seed=seed)


def _bench(n_problems: int = 2) -> IOIBenchmark:
    return IOIBenchmark(top_k=3, n_evolution_steps=1, seed=0)


# ===========================================================================
# TestIOIProblem
# ===========================================================================

class TestIOIProblem:
    def test_fields(self):
        p = _HELLO_PROBLEM
        assert p.problem_id == "hello"
        assert len(p.sample_io) == 1

    def test_to_dict(self):
        d = _HELLO_PROBLEM.to_dict()
        assert isinstance(d, dict)
        assert len(d) > 0

    def test_description_preserved(self):
        assert "hello" in _HELLO_PROBLEM.description.lower()

    def test_category_preserved(self):
        assert _HELLO_PROBLEM.category == "simulation"


# ===========================================================================
# TestSandboxRunner
# ===========================================================================

class TestSandboxRunner:
    def test_run_simple_code(self):
        runner = SandboxRunner(timeout_s=2.0)
        code = "print('ok')"
        stdout, stderr, returncode, elapsed = runner.run(code, "")
        assert "ok" in stdout
        assert returncode == 0

    def test_run_with_stdin(self):
        runner = SandboxRunner(timeout_s=2.0)
        code = "n = int(input()); print(n * 2)"
        stdout, _, rc, _ = runner.run(code, "5\n")
        assert "10" in stdout
        assert rc == 0

    def test_run_syntax_error_nonzero(self):
        runner = SandboxRunner(timeout_s=2.0)
        code = "def f(: pass"
        _, _, rc, _ = runner.run(code, "")
        assert rc != 0

    def test_run_timeout(self):
        runner = SandboxRunner(timeout_s=0.3)
        code = "import time; time.sleep(10)"
        _, _, rc, _ = runner.run(code, "")
        assert rc != 0  # Should timeout or be killed

    def test_run_returns_four_tuple(self):
        runner = SandboxRunner(timeout_s=1.0)
        result = runner.run("pass", "")
        assert len(result) == 4


# ===========================================================================
# TestTemplateLibrary
# ===========================================================================

class TestTemplateLibrary:
    def test_all_returns_list(self):
        templates = TemplateLibrary.all()
        assert isinstance(templates, list)
        assert len(templates) >= 10

    def test_by_category_sorting(self):
        templates = TemplateLibrary.by_category("sorting")
        assert len(templates) >= 1
        for t in templates:
            assert t.category == "sorting"

    def test_by_category_bfs(self):
        templates = TemplateLibrary.by_category("bfs")
        assert len(templates) >= 1

    def test_template_has_code(self):
        templates = TemplateLibrary.all()
        for t in templates:
            assert len(t.code) > 0

    def test_template_to_dict(self):
        t = TemplateLibrary.all()[0]
        d = t.to_dict()
        assert isinstance(d, dict)
        assert len(d) > 0

    def test_unknown_category_empty(self):
        templates = TemplateLibrary.by_category("nonexistent_xyz")
        assert templates == []


# ===========================================================================
# TestIOISolver
# ===========================================================================

class TestIOISolver:
    def test_solve_returns_result(self):
        solver = _solver()
        result = solver.solve(_HELLO_PROBLEM)
        assert isinstance(result, IOIResult)

    def test_result_to_dict(self):
        solver = _solver()
        result = solver.solve(_HELLO_PROBLEM)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert len(d) > 0

    def test_pass_rate_in_range(self):
        solver = _solver()
        result = solver.solve(_HELLO_PROBLEM)
        assert 0.0 <= result.pass_rate <= 1.0

    def test_solved_bool(self):
        solver = _solver()
        result = solver.solve(_HELLO_PROBLEM)
        assert isinstance(result.solved, bool)

    def test_solution_candidate_to_dict(self):
        c = SolutionCandidate(
            template_name="simulation",
            source_code=_TRIVIAL_SOLUTION,
            pass_rate=1.0,
        )
        d = c.to_dict()
        assert isinstance(d, dict)
        assert len(d) > 0


# ===========================================================================
# TestIOIBenchmark
# ===========================================================================

class TestIOIBenchmark:
    def test_run_returns_report(self):
        bench = _bench()
        report = bench.run()
        assert isinstance(report, IOIBenchmarkReport)

    def test_report_has_results(self):
        bench = _bench()
        report = bench.run()
        assert len(report.results) > 0

    def test_solve_rate_in_range(self):
        bench = _bench()
        report = bench.run()
        assert 0.0 <= report.solve_rate <= 1.0

    def test_report_to_dict(self):
        bench = _bench()
        report = bench.run()
        d = report.to_dict()
        assert "solve_rate" in d
        assert "n_problems" in d
        assert "results" in d

    def test_custom_problems(self):
        bench = IOIBenchmark(
            problems=[_HELLO_PROBLEM, _SORT_PROBLEM],
            top_k=2,
            n_evolution_steps=1,
            seed=0,
        )
        report = bench.run()
        assert len(report.results) >= 1


# ===========================================================================
# TestWP63ExitCriteria
# ===========================================================================

class TestWP63ExitCriteria:
    def _report(self) -> IOIBenchmarkReport:
        return _bench().run()

    def test_returns_dict(self):
        assert isinstance(verify_wp63_exit_criteria(), dict)

    def test_six_criteria(self):
        assert len(verify_wp63_exit_criteria()) == 6

    def test_all_pass_with_report(self):
        report = self._report()
        result = verify_wp63_exit_criteria(report)
        for k, v in result.items():
            assert v, f"Criterion failed: '{k}'"

    def test_no_report_returns_dict(self):
        result = verify_wp63_exit_criteria(None)
        assert isinstance(result, dict)
        assert len(result) == 6


# ===========================================================================
# TestIntegration
# ===========================================================================

class TestIntegration:
    def test_end_to_end_synthetic(self):
        bench = IOIBenchmark(top_k=3, n_evolution_steps=1, seed=1)
        report = bench.run()
        assert report.n_problems >= 1
        assert isinstance(report.elapsed_s, float)

    def test_criteria_pass_after_full_run(self):
        bench = IOIBenchmark(top_k=5, n_evolution_steps=2, seed=0)
        report = bench.run()
        result = verify_wp63_exit_criteria(report)
        assert all(result.values()), f"Some criteria failed: {result}"
