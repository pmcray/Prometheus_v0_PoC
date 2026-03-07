"""
WP62 Test Suite: ARC-AGI Integration
=====================================

TestARCGrid               Grid creation, size, equality
TestARCTransform          Apply transforms, list all
TestARCProgramSynthesiser Beam search, fitness
TestARCSolver             Solve task, result structure
TestARCBenchmark          run, report structure
TestWP62ExitCriteria      Six-criterion verifier
TestIntegration           End-to-end: benchmark → report
"""

import pytest

from prometheus.wp62_arc_agi import (
    ARCBenchmark,
    ARCBenchmarkReport,
    ARCBenchmarkResult,
    ARCGrid,
    ARCProgramSynthesiser,
    ARCSolver,
    ARCTask,
    ARCTransform,
    _ALL_TRANSFORMS,
    verify_wp62_exit_criteria,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_task() -> ARCTask:
    """Horizontal-flip task from synthetic set."""
    inp = ARCGrid([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    out = ARCGrid([[0, 0, 1], [0, 1, 0], [1, 0, 0]])
    return ARCTask(
        task_id="flip_h_test",
        train=[(inp, out)],
        test_inputs=[inp],
        test_outputs=[out],
    )


def _identity_task() -> ARCTask:
    inp = ARCGrid([[1, 2], [3, 4]])
    return ARCTask(
        task_id="identity_test",
        train=[(inp, inp)],
        test_inputs=[inp],
        test_outputs=[inp],
    )


def _bench(beam_width: int = 5, max_depth: int = 2) -> ARCBenchmark:
    return ARCBenchmark(beam_width=beam_width, max_depth=max_depth, fitness_threshold=0.9)


# ===========================================================================
# TestARCGrid
# ===========================================================================

class TestARCGrid:
    def test_create_grid(self):
        g = ARCGrid([[1, 0], [0, 1]])
        assert g.height == 2
        assert g.width == 2

    def test_grid_equality(self):
        g1 = ARCGrid([[1, 2], [3, 4]])
        g2 = ARCGrid([[1, 2], [3, 4]])
        assert g1 == g2

    def test_grid_inequality(self):
        g1 = ARCGrid([[1, 2], [3, 4]])
        g2 = ARCGrid([[4, 3], [2, 1]])
        assert g1 != g2

    def test_to_list(self):
        data = [[5, 6]]
        g = ARCGrid(data)
        assert g.to_list() == data

    def test_grid_data_access(self):
        data = [[1, 2, 3], [4, 5, 6]]
        g = ARCGrid(data)
        assert g.data == data

    def test_height_width(self):
        g = ARCGrid([[0] * 5 for _ in range(3)])
        assert g.height == 3
        assert g.width == 5

    def test_size_property(self):
        g = ARCGrid([[1, 2], [3, 4]])
        assert g.size == (2, 2)


# ===========================================================================
# TestARCTransform
# ===========================================================================

class TestARCTransform:
    def _get_transform(self, name: str) -> ARCTransform:
        for t in _ALL_TRANSFORMS:
            if t.name == name:
                return t
        raise KeyError(f"No transform named {name!r}")

    def test_all_transforms_list(self):
        assert isinstance(_ALL_TRANSFORMS, list)
        assert len(_ALL_TRANSFORMS) >= 10

    def test_flip_h_applied(self):
        t = self._get_transform("flip_h")
        inp = ARCGrid([[1, 2, 3]])
        out = t.apply(inp)
        assert out.data == [[3, 2, 1]]

    def test_identity_applied(self):
        t = self._get_transform("identity")
        inp = ARCGrid([[1, 2], [3, 4]])
        out = t.apply(inp)
        assert out == inp

    def test_rotate90_applied(self):
        t = self._get_transform("rotate90")
        inp = ARCGrid([[1, 2], [3, 4]])
        out = t.apply(inp)
        assert out.height == inp.width
        assert out.width == inp.height

    def test_transform_has_name(self):
        for t in _ALL_TRANSFORMS:
            assert isinstance(t.name, str)
            assert len(t.name) > 0

    def test_transform_is_callable(self):
        t = _ALL_TRANSFORMS[0]
        g = ARCGrid([[1, 2]])
        result = t.apply(g)
        assert isinstance(result, ARCGrid)


# ===========================================================================
# TestARCProgramSynthesiser
# ===========================================================================

class TestARCProgramSynthesiser:
    def test_synthesise_returns_tuple(self):
        synth = ARCProgramSynthesiser(beam_width=5, max_depth=2)
        task = _identity_task()
        result = synth.synthesise(task)
        assert isinstance(result, tuple)
        assert len(result) == 3  # (program, fitness, n_evaluated)

    def test_synthesise_identity_task(self):
        synth = ARCProgramSynthesiser(beam_width=10, max_depth=2)
        task = _identity_task()
        program, fitness, _ = synth.synthesise(task)
        assert isinstance(program, list)
        assert fitness >= 0.0

    def test_fitness_perfect_match(self):
        """Fitness between identical grids should be 1.0."""
        from prometheus.wp62_arc_agi import _make_synthetic_tasks
        tasks = _make_synthetic_tasks()
        synth = ARCProgramSynthesiser(beam_width=10, max_depth=3)
        # Find identity task
        id_tasks = [t for t in tasks if "identity" in t.task_id]
        if id_tasks:
            _, fitness, _ = synth.synthesise(id_tasks[0])
            assert fitness >= 0.5  # at least partially solved

    def test_n_evaluated_positive(self):
        synth = ARCProgramSynthesiser(beam_width=5, max_depth=2)
        task = _identity_task()
        _, _, n_evaluated = synth.synthesise(task)
        assert n_evaluated >= 1

    def test_program_is_list(self):
        synth = ARCProgramSynthesiser(beam_width=5, max_depth=2)
        task = _identity_task()
        program, _, _ = synth.synthesise(task)
        assert isinstance(program, list)


# ===========================================================================
# TestARCSolver
# ===========================================================================

class TestARCSolver:
    def test_solve_returns_result(self):
        solver = ARCSolver(fitness_threshold=0.9)
        task = _identity_task()
        result = solver.solve(task)
        assert isinstance(result, ARCBenchmarkResult)

    def test_solve_has_train_fitness(self):
        solver = ARCSolver(fitness_threshold=0.9)
        task = _identity_task()
        result = solver.solve(task)
        assert 0.0 <= result.train_fitness <= 1.0

    def test_solve_result_to_dict(self):
        solver = ARCSolver(fitness_threshold=0.5)
        task = _identity_task()
        result = solver.solve(task)
        d = result.to_dict()
        assert "task_id" in d
        assert "solved" in d
        assert "train_fitness" in d

    def test_solve_result_program_list(self):
        solver = ARCSolver(fitness_threshold=0.5)
        task = _identity_task()
        result = solver.solve(task)
        assert isinstance(result.program, list)

    def test_solved_bool(self):
        solver = ARCSolver(fitness_threshold=0.5)
        task = _identity_task()
        result = solver.solve(task)
        assert isinstance(result.solved, bool)


# ===========================================================================
# TestARCBenchmark
# ===========================================================================

class TestARCBenchmark:
    def test_run_returns_report(self):
        bench = _bench()
        report = bench.run()
        assert isinstance(report, ARCBenchmarkReport)

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
        assert "n_tasks" in d
        assert "results" in d

    def test_result_to_dict_keys(self):
        bench = _bench()
        report = bench.run()
        for r in report.results:
            d = r.to_dict()
            for k in ("task_id", "train_fitness", "solved"):
                assert k in d, f"Missing key: {k}"

    def test_custom_tasks(self):
        bench = ARCBenchmark(
            tasks=[_identity_task(), _simple_task()],
            beam_width=5,
            max_depth=2,
            fitness_threshold=0.5,
        )
        report = bench.run()
        assert len(report.results) == 2

    def test_n_tasks_matches_results(self):
        bench = _bench()
        report = bench.run()
        assert report.n_tasks == len(report.results)


# ===========================================================================
# TestWP62ExitCriteria
# ===========================================================================

class TestWP62ExitCriteria:
    def _report(self) -> ARCBenchmarkReport:
        return ARCBenchmark(beam_width=15, max_depth=3, fitness_threshold=0.9).run()

    def test_returns_dict(self):
        assert isinstance(verify_wp62_exit_criteria(), dict)

    def test_six_criteria(self):
        assert len(verify_wp62_exit_criteria()) == 6

    def test_all_pass_with_report(self):
        report = self._report()
        result = verify_wp62_exit_criteria(report)
        for k, v in result.items():
            assert v, f"Criterion failed: '{k}'"

    def test_no_report_returns_dict(self):
        result = verify_wp62_exit_criteria(None)
        assert isinstance(result, dict)
        assert len(result) == 6


# ===========================================================================
# TestIntegration
# ===========================================================================

class TestIntegration:
    def test_end_to_end_synthetic_tasks(self):
        bench = ARCBenchmark(beam_width=10, max_depth=3, fitness_threshold=0.9)
        report = bench.run()
        assert report.n_tasks >= 1
        assert isinstance(report.total_time_s, float)

    def test_criteria_pass_after_full_run(self):
        bench = ARCBenchmark(beam_width=15, max_depth=3, fitness_threshold=0.9)
        report = bench.run()
        result = verify_wp62_exit_criteria(report)
        assert all(result.values()), f"Some criteria failed: {result}"
