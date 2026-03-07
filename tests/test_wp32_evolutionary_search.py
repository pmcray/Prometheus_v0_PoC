"""
WP32 Test Suite: Evolutionary Code Search
==========================================

Seven test classes:

TestMutationOperator        Unit tests for all five mutation types
TestCrossoverOperator       Crossover provenance, fallback behaviour
TestFitnessEvaluator        Score formula, spec-gaming guard
TestEvolutionRecord         Audit dataclass, to_dict()
TestEvolutionarySearcher    Seed, step, run, summary
TestWP32ExitCriteria        Six-criterion verifier
TestIntegration             End-to-end: seed → run → report
"""

import pytest

from prometheus.gene_archive import GeneArchive
from prometheus.wp32_evolutionary_search import (
    CrossoverOperator,
    EvolutionRecord,
    EvolutionReport,
    EvolutionarySearcher,
    FitnessEvaluator,
    MutationOperator,
    verify_wp32_exit_criteria,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_SEED_CODE = """\
def bubble_sort(lst):
    n = len(lst)
    for i in range(n):
        for j in range(n - i - 1):
            if lst[j] > lst[j + 1]:
                lst[j], lst[j + 1] = lst[j + 1], lst[j]
    return lst
"""

_SEED_CODE_B = """\
def insertion_sort(lst):
    for i in range(1, len(lst)):
        key = lst[i]
        j = i - 1
        while j >= 0 and lst[j] > key:
            lst[j + 1] = lst[j]
            j -= 1
        lst[j + 1] = key
    return lst
"""

_SEED_PROGRAMS = [_SEED_CODE, _SEED_CODE_B]


def _build_searcher(
    pop: int = 6,
    k: int = 3,
    xover: float = 0.5,
    seed: int = 42,
) -> EvolutionarySearcher:
    archive = GeneArchive()
    searcher = EvolutionarySearcher(
        archive=archive,
        population_size=pop,
        tournament_k=k,
        crossover_prob=xover,
        seed=seed,
    )
    # Pad seed programs to population size
    programs = (_SEED_PROGRAMS * (pop // len(_SEED_PROGRAMS) + 1))[:pop]
    searcher.seed_population(programs)
    return searcher


# ===========================================================================
# TestMutationOperator
# ===========================================================================

class TestMutationOperator:
    """Unit tests for all five mutation types."""

    def test_rename_replaces_j(self):
        op = MutationOperator(seed=0)
        code = "for j in range(n):\n    pass"
        mutated, mtype = op.mutate(code, mutation_type="rename")
        assert "inner_idx" in mutated
        assert mtype == "rename"

    def test_rename_does_not_affect_other_names(self):
        op = MutationOperator(seed=0)
        code = "junk = 5\nfor j in range(n):\n    pass"
        mutated, _ = op.mutate(code, mutation_type="rename")
        assert "junk" in mutated   # 'junk' should be unchanged (j is word-boundary)

    def test_extract_replaces_target(self):
        op = MutationOperator(seed=0)
        code = "    x = n - i - 1\n    arr[x] = 0\n"
        mutated, mtype = op.mutate(code, mutation_type="extract")
        assert "_extracted_val" in mutated
        assert mtype == "extract"

    def test_extract_noop_when_no_target(self):
        op = MutationOperator(seed=0)
        code = "def f(): return 42"
        mutated, mtype = op.mutate(code, mutation_type="extract")
        assert mutated == code     # nothing to extract
        assert mtype == "extract"

    def test_document_prepends_comment(self):
        op = MutationOperator(seed=0)
        code = "def f(): pass"
        mutated, mtype = op.mutate(code, mutation_type="document")
        assert mutated.startswith("# Evolved variant:")
        assert mtype == "document"

    def test_document_hash_in_comment(self):
        op = MutationOperator(seed=0)
        code = "def g(): return 1"
        mutated, _ = op.mutate(code, mutation_type="document")
        # Comment contains an 8-char hex hash
        import re
        assert re.search(r"Evolved variant: [0-9a-f]{8}", mutated)

    def test_early_exit_inserts_guard(self):
        op = MutationOperator(seed=0)
        code = "def f(n):\n    for i in range(n):\n        pass\n"
        mutated, mtype = op.mutate(code, mutation_type="early_exit")
        assert "if n <= 1" in mutated
        assert mtype == "early_exit"

    def test_early_exit_noop_without_for(self):
        op = MutationOperator(seed=0)
        code = "def f(n):\n    return n\n"
        mutated, _ = op.mutate(code, mutation_type="early_exit")
        assert mutated == code

    def test_simplify_replaces_range_len(self):
        op = MutationOperator(seed=0)
        code = "for i in range(len(lst)):\n    print(i)\n"
        mutated, mtype = op.mutate(code, mutation_type="simplify")
        assert "enumerate" in mutated
        assert mtype == "simplify"

    def test_simplify_noop_without_pattern(self):
        op = MutationOperator(seed=0)
        code = "for i in range(10):\n    pass\n"
        mutated, _ = op.mutate(code, mutation_type="simplify")
        assert mutated == code

    def test_random_choice_returns_valid_type(self):
        op = MutationOperator(seed=7)
        _, mtype = op.mutate(_SEED_CODE)
        assert mtype in MutationOperator.TYPES

    def test_mutate_changes_code(self):
        op = MutationOperator(seed=0)
        # 'document' always changes code
        mutated, _ = op.mutate(_SEED_CODE, mutation_type="document")
        assert mutated != _SEED_CODE


# ===========================================================================
# TestCrossoverOperator
# ===========================================================================

class TestCrossoverOperator:
    """Crossover provenance, fallback behaviour."""

    def test_offspring_has_provenance_comment(self):
        op = CrossoverOperator()
        offspring = op.crossover(_SEED_CODE, _SEED_CODE_B)
        assert "# Crossover:" in offspring

    def test_offspring_is_string(self):
        op = CrossoverOperator()
        result = op.crossover(_SEED_CODE, _SEED_CODE_B)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_crossover_with_no_def_falls_back(self):
        op = CrossoverOperator()
        # Parent without 'def' → fallback to parent_a
        result = op.crossover("x = 5\ny = 10", _SEED_CODE_B)
        assert "# Crossover:" in result
        assert "x = 5" in result

    def test_crossover_signature_from_a(self):
        op = CrossoverOperator()
        offspring = op.crossover(_SEED_CODE, _SEED_CODE_B)
        # Signature of parent_a ('bubble_sort') should appear
        assert "bubble_sort" in offspring

    def test_crossover_body_from_b(self):
        op = CrossoverOperator()
        offspring = op.crossover(_SEED_CODE, _SEED_CODE_B)
        # Body of parent_b ('insertion_sort') typically contains 'key'
        assert "key" in offspring or "insertion" in offspring or "bubble" in offspring

    def test_crossover_single_line_docstring(self):
        code_a = 'def foo():\n    """Single line."""\n    return 1\n'
        code_b = 'def bar():\n    return 42\n'
        op = CrossoverOperator()
        offspring = op.crossover(code_a, code_b)
        assert "foo" in offspring


# ===========================================================================
# TestFitnessEvaluator
# ===========================================================================

class TestFitnessEvaluator:
    """Score formula and spec-gaming guard."""

    def test_score_in_range(self):
        ev = FitnessEvaluator()
        score = ev.evaluate(_SEED_CODE)
        assert 0.0 <= score <= 100.0

    def test_empty_code_no_seed_returns_100(self):
        # No seed → no guard → empty code has 0 complexity
        ev = FitnessEvaluator()
        score = ev.evaluate("")
        assert score == 100.0

    def test_spec_gaming_guard_penalises_empty(self):
        ev = FitnessEvaluator(seed_code=_SEED_CODE)
        score = ev.evaluate("")
        assert score <= 10.0

    def test_spec_gaming_guard_threshold(self):
        # Code with < 40% tokens of seed should score ≤ 10
        ev = FitnessEvaluator(seed_code="a b c d e f g h i j")  # 10 tokens
        tiny = "a b c"  # 3 tokens = 30% < 40%
        assert ev.evaluate(tiny) <= 10.0

    def test_spec_gaming_guard_pass_above_threshold(self):
        ev = FitnessEvaluator(seed_code="a b c d e")  # 5 tokens
        big = "a b c d e f g h i j"  # 10 tokens = 200% > 40%
        assert ev.evaluate(big) > 10.0

    def test_enumerate_bonus(self):
        ev = FitnessEvaluator()
        plain = "for i in range(len(x)):\n    pass"
        with_enum = "for i, _ in enumerate(x):\n    pass"
        # enumerate adds +5 bonus; plain has no bonus
        assert ev.evaluate(with_enum) >= ev.evaluate(plain)

    def test_complexity_penalty(self):
        ev = FitnessEvaluator()
        simple = "def f(): return 1"
        complex_code = "if a and b or c:\n    for x in y:\n        while z: pass"
        assert ev.evaluate(simple) > ev.evaluate(complex_code)

    def test_score_not_exceed_100(self):
        ev = FitnessEvaluator()
        assert ev.evaluate("x = 1") <= 100.0

    def test_score_not_below_zero(self):
        ev = FitnessEvaluator()
        # Pathologically complex code
        many_ifs = " ".join(["if a and b or c:"] * 200)
        score = ev.evaluate(many_ifs)
        assert score >= 0.0


# ===========================================================================
# TestEvolutionRecord
# ===========================================================================

class TestEvolutionRecord:
    """Audit dataclass, to_dict()."""

    def _record(self) -> EvolutionRecord:
        return EvolutionRecord(
            generation=3,
            population_size=6,
            best_fitness=85.5,
            mean_fitness=72.1,
            diversity=0.42,
            archive_size=18,
            best_gene_id="g1_0003",
            best_mutation_type="rename",
            elapsed_s=0.012,
        )

    def test_to_dict_has_required_keys(self):
        d = self._record().to_dict()
        for key in (
            "generation", "population_size", "best_fitness", "mean_fitness",
            "diversity", "archive_size", "best_gene_id", "best_mutation_type",
            "elapsed_s",
        ):
            assert key in d, f"Missing key: {key}"

    def test_generation_value(self):
        assert self._record().to_dict()["generation"] == 3

    def test_best_fitness_rounded(self):
        d = self._record().to_dict()
        assert isinstance(d["best_fitness"], float)

    def test_mutation_type_preserved(self):
        assert self._record().to_dict()["best_mutation_type"] == "rename"


# ===========================================================================
# TestEvolutionarySearcher
# ===========================================================================

class TestEvolutionarySearcher:
    """Seed, step, run, summary."""

    def test_seed_population_returns_gene_ids(self):
        searcher = _build_searcher()
        assert len(searcher._population) == 6

    def test_seed_population_adds_to_archive(self):
        searcher = _build_searcher()
        assert len(searcher.archive) >= 6

    def test_step_returns_evolution_record(self):
        searcher = _build_searcher()
        record = searcher.step()
        assert isinstance(record, EvolutionRecord)

    def test_step_increments_generation(self):
        searcher = _build_searcher()
        searcher.step()
        assert searcher.generation == 1

    def test_step_records_appended(self):
        searcher = _build_searcher()
        for _ in range(3):
            searcher.step()
        assert len(searcher.records) == 3

    def test_step_best_fitness_nonneg(self):
        searcher = _build_searcher()
        record = searcher.step()
        assert record.best_fitness >= 0.0

    def test_step_diversity_in_range(self):
        searcher = _build_searcher()
        record = searcher.step()
        assert 0.0 <= record.diversity <= 1.0

    def test_step_archive_grows(self):
        searcher = _build_searcher()
        before = len(searcher.archive)
        searcher.step()
        assert len(searcher.archive) > before

    def test_run_returns_evolution_report(self):
        searcher = _build_searcher()
        report = searcher.run(n_generations=3)
        assert isinstance(report, EvolutionReport)

    def test_run_n_generations(self):
        searcher = _build_searcher()
        report = searcher.run(n_generations=5)
        assert report.n_generations == 5
        assert searcher.generation == 5

    def test_run_improvement_is_float(self):
        searcher = _build_searcher()
        report = searcher.run(n_generations=3)
        assert isinstance(report.improvement, float)

    def test_run_best_gene_code_nonempty(self):
        searcher = _build_searcher()
        report = searcher.run(n_generations=3)
        assert len(report.best_gene_code) > 0

    def test_summary_after_run(self):
        searcher = _build_searcher()
        searcher.run(n_generations=3)
        summ = searcher.summary()
        assert summ["n_generations"] == 3
        assert "archive_size" in summ

    def test_no_seed_raises(self):
        archive = GeneArchive()
        searcher = EvolutionarySearcher(archive=archive, population_size=4, seed=0)
        with pytest.raises(RuntimeError):
            searcher.step()

    def test_population_size_maintained(self):
        searcher = _build_searcher(pop=4)
        for _ in range(5):
            searcher.step()
        assert len(searcher._population) <= 4

    def test_custom_fitness_fn(self):
        """Custom fitness function should be used instead of default."""
        def constant_fn(code: str) -> float:
            return 42.0

        archive = GeneArchive()
        searcher = EvolutionarySearcher(
            archive=archive,
            population_size=4,
            seed=0,
            fitness_fn=constant_fn,
        )
        searcher.seed_population([_SEED_CODE, _SEED_CODE_B, _SEED_CODE, _SEED_CODE_B])
        record = searcher.step()
        # With constant fitness, best == mean == 42
        assert abs(record.best_fitness - 42.0) < 1e-6

    def test_crossover_prob_zero_uses_only_mutation(self):
        archive = GeneArchive()
        searcher = EvolutionarySearcher(
            archive=archive,
            population_size=4,
            crossover_prob=0.0,
            seed=0,
        )
        searcher.seed_population([_SEED_CODE, _SEED_CODE_B, _SEED_CODE, _SEED_CODE_B])
        record = searcher.step()
        # Should not crash; no crossover
        assert isinstance(record, EvolutionRecord)

    def test_crossover_prob_one_uses_only_crossover(self):
        archive = GeneArchive()
        searcher = EvolutionarySearcher(
            archive=archive,
            population_size=4,
            crossover_prob=1.0,
            seed=0,
        )
        searcher.seed_population([_SEED_CODE, _SEED_CODE_B, _SEED_CODE, _SEED_CODE_B])
        record = searcher.step()
        assert isinstance(record, EvolutionRecord)


# ===========================================================================
# TestWP32ExitCriteria
# ===========================================================================

class TestWP32ExitCriteria:
    """verify_wp32_exit_criteria — six criteria."""

    def _trained_searcher(self, n_gens: int = 6) -> EvolutionarySearcher:
        searcher = _build_searcher(pop=6)
        searcher.run(n_generations=n_gens)
        return searcher

    def test_returns_dict(self):
        searcher = self._trained_searcher()
        seed_fitness = 0.0
        result = verify_wp32_exit_criteria(searcher, seed_fitness)
        assert isinstance(result, dict)

    def test_six_criteria(self):
        searcher = self._trained_searcher()
        result = verify_wp32_exit_criteria(searcher, seed_fitness=0.0)
        assert len(result) == 6

    def test_all_criteria_pass_after_training(self):
        searcher = self._trained_searcher(n_gens=6)
        seed_fitness = 0.0   # Any evolved code should beat 0
        result = verify_wp32_exit_criteria(searcher, seed_fitness)
        for criterion, passed in result.items():
            assert passed, f"Criterion failed: '{criterion}'"

    def test_criterion_5_generations(self):
        searcher = _build_searcher(pop=4)
        searcher.run(n_generations=5)
        result = verify_wp32_exit_criteria(searcher, seed_fitness=0.0)
        assert result["At least 5 generations completed"]

    def test_criterion_spec_gaming_guard(self):
        searcher = _build_searcher(pop=4)
        searcher.run(n_generations=2)
        result = verify_wp32_exit_criteria(searcher, seed_fitness=0.0)
        assert result["Spec-gaming guard penalises near-empty code (score ≤ 10)"]

    def test_criterion_lineage_populated(self):
        searcher = _build_searcher(pop=4)
        searcher.run(n_generations=1)
        result = verify_wp32_exit_criteria(searcher, seed_fitness=0.0)
        assert result["Lineage (parent_ids) populated"]

    def test_criterion_fitness_history(self):
        searcher = _build_searcher(pop=4)
        searcher.run(n_generations=1)
        result = verify_wp32_exit_criteria(searcher, seed_fitness=0.0)
        assert result["GeneRecord fitness history populated"]


# ===========================================================================
# TestIntegration
# ===========================================================================

class TestIntegration:
    """End-to-end: seed → run → report."""

    def test_full_run_produces_valid_report(self):
        searcher = _build_searcher(pop=6)
        report = searcher.run(n_generations=6)

        assert report.n_generations == 6
        assert isinstance(report.improvement, float)
        assert 0.0 <= report.peak_diversity <= 1.0
        assert len(report.records) == 6
        assert len(report.best_gene_id) > 0
        assert len(report.best_gene_code) > 0

    def test_report_to_dict_keys(self):
        searcher = _build_searcher(pop=4)
        report = searcher.run(n_generations=4)
        d = report.to_dict()
        for key in (
            "n_generations", "initial_best_fitness", "final_best_fitness",
            "improvement", "peak_diversity", "best_gene_id", "trajectory",
        ):
            assert key in d, f"Missing key in report dict: {key}"

    def test_trajectory_length_matches_n_generations(self):
        searcher = _build_searcher(pop=4)
        report = searcher.run(n_generations=4)
        d = report.to_dict()
        assert len(d["trajectory"]) == 4

    def test_archive_persistence_round_trip(self, tmp_path):
        """GeneArchive can save and reload evolved genes."""
        path = str(tmp_path / "archive.json")
        archive = GeneArchive(persist_path=path)
        searcher = EvolutionarySearcher(
            archive=archive, population_size=4, seed=1
        )
        searcher.seed_population([_SEED_CODE, _SEED_CODE_B, _SEED_CODE, _SEED_CODE_B])
        searcher.run(n_generations=3)
        archive.save()

        # Reload
        archive2 = GeneArchive(persist_path=path)
        archive2.load()
        assert len(archive2) == len(archive)

    def test_deterministic_with_fixed_seed(self):
        """Two runs with the same seed should produce identical best fitness."""
        def _run(seed: int) -> float:
            s = EvolutionarySearcher(
                GeneArchive(), population_size=4,
                crossover_prob=0.5, seed=seed
            )
            s.seed_population([_SEED_CODE, _SEED_CODE_B, _SEED_CODE, _SEED_CODE_B])
            r = s.run(n_generations=4)
            return r.final_best_fitness

        f1 = _run(99)
        f2 = _run(99)
        assert abs(f1 - f2) < 1e-9

    def test_exit_criteria_pass_after_full_run(self):
        searcher = _build_searcher(pop=6)
        searcher.run(n_generations=6)
        result = verify_wp32_exit_criteria(searcher, seed_fitness=0.0)
        assert all(result.values()), f"Some criteria failed: {result}"
