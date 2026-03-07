"""
WP33 Test Suite: Formal Domain Adaptation — Lean Theorem Proving
================================================================

Six test classes:

TestTheoremCurriculum       Difficulty stratification, add/record
TestProofAttemptRecord      Audit dataclass, to_dict()
TestProofSession            Attempt loop, error feedback, sorry rejection
TestTheoremProver           Batch prove, curriculum prove, summary
TestWP33ExitCriteria        Four-criterion verifier
TestIntegration             End-to-end: prover → report → criteria
"""

import pytest

from prometheus.wp33_lean_theorem_proving import (
    ProofAttemptRecord,
    ProofSession,
    TheoremCurriculum,
    TheoremDifficulty,
    TheoremProver,
    TheoremProvingReport,
    verify_wp33_exit_criteria,
    _SEED_THEOREMS,
    _CANONICAL_PROOFS,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _mock_lean():
    """Return a minimal LeanTool mock (no real Lean binary required)."""
    from prometheus.tools.base_tools import LeanTool
    tool = LeanTool.__new__(LeanTool)
    tool._using_mock = True
    tool._lean_exe   = None
    tool._timeout    = 20
    tool.step        = 0
    tool._proof_lines = []
    tool._failed_branches = []
    return tool


def _build_prover(n_per_level: int = 3, max_retries: int = 3) -> TheoremProver:
    lean = _mock_lean()
    return TheoremProver(lean_tool=lean, n_per_level=n_per_level, max_retries=max_retries)


# ===========================================================================
# TestTheoremCurriculum
# ===========================================================================

class TestTheoremCurriculum:
    """Difficulty stratification and theorem management."""

    def test_get_easy_theorems_returns_list(self):
        curr = TheoremCurriculum(n_per_level=3)
        theorems = curr.get_theorems(TheoremDifficulty.EASY)
        assert isinstance(theorems, list)
        assert len(theorems) == 3

    def test_get_medium_theorems_length(self):
        curr = TheoremCurriculum(n_per_level=4)
        assert len(curr.get_theorems(TheoremDifficulty.MEDIUM)) == 4

    def test_get_hard_theorems_length(self):
        curr = TheoremCurriculum(n_per_level=6)
        assert len(curr.get_theorems(TheoremDifficulty.HARD)) == 6

    def test_all_theorems_returns_all_levels(self):
        curr = TheoremCurriculum(n_per_level=2)
        all_thms = curr.get_all_theorems()
        assert set(all_thms.keys()) == set(TheoremDifficulty.ALL)

    def test_n_per_level_cycling(self):
        """Requesting more theorems than seed pool → cycles."""
        curr = TheoremCurriculum(n_per_level=100)
        easy = curr.get_theorems(TheoremDifficulty.EASY)
        assert len(easy) == 100
        # First theorem should repeat
        pool_size = len(_SEED_THEOREMS[TheoremDifficulty.EASY])
        assert easy[0] == easy[pool_size]

    def test_add_theorem_easy(self):
        curr = TheoremCurriculum(n_per_level=1)
        curr.add_theorem("theorem custom_easy : True", TheoremDifficulty.EASY)
        pool = curr._theorems[TheoremDifficulty.EASY]
        assert "theorem custom_easy : True" in pool

    def test_add_theorem_invalid_difficulty(self):
        curr = TheoremCurriculum()
        with pytest.raises(ValueError):
            curr.add_theorem("theorem x : 1 = 1", "extreme")

    def test_record_outcome_updates_stats(self):
        curr = TheoremCurriculum()
        curr.record_outcome(TheoremDifficulty.EASY, success=True)
        curr.record_outcome(TheoremDifficulty.EASY, success=False)
        rates = curr.success_rates()
        assert rates[TheoremDifficulty.EASY] == 0.5

    def test_success_rate_none_before_any_attempt(self):
        curr = TheoremCurriculum()
        rates = curr.success_rates()
        for level in TheoremDifficulty.ALL:
            assert rates[level] is None

    def test_summary_has_required_keys(self):
        curr = TheoremCurriculum()
        summ = curr.summary()
        for key in ("n_per_level", "theorem_counts", "stats", "success_rates"):
            assert key in summ

    def test_unknown_difficulty_returns_empty(self):
        curr = TheoremCurriculum()
        result = curr.get_theorems("impossible_level")
        assert result == []

    def test_theorem_strings_are_lean_syntax(self):
        """All seed theorems should start with 'theorem'."""
        curr = TheoremCurriculum(n_per_level=6)
        for level in TheoremDifficulty.ALL:
            for thm in curr.get_theorems(level):
                assert thm.startswith("theorem"), f"Bad theorem: {thm!r}"


# ===========================================================================
# TestProofAttemptRecord
# ===========================================================================

class TestProofAttemptRecord:
    """Audit record dataclass."""

    def _record(self) -> ProofAttemptRecord:
        return ProofAttemptRecord(
            theorem="theorem add_zero (n : Nat) : n + 0 = n",
            difficulty=TheoremDifficulty.EASY,
            success=True,
            n_attempts=2,
            errors_seen=["Proof contains 'sorry'."],
            proof_text="theorem add_zero (n : Nat) : n + 0 = n := by simp",
            wall_time_s=0.003,
        )

    def test_to_dict_has_required_keys(self):
        d = self._record().to_dict()
        for key in (
            "theorem", "difficulty", "success", "n_attempts",
            "n_errors", "proof_text", "wall_time_s",
        ):
            assert key in d, f"Missing key: {key}"

    def test_success_preserved(self):
        assert self._record().to_dict()["success"] is True

    def test_difficulty_preserved(self):
        assert self._record().to_dict()["difficulty"] == "easy"

    def test_n_attempts_preserved(self):
        assert self._record().to_dict()["n_attempts"] == 2

    def test_n_errors_count(self):
        assert self._record().to_dict()["n_errors"] == 1

    def test_proof_text_truncated(self):
        """Proof text should be truncated at 120 chars if longer."""
        long_proof = "x" * 200
        rec = ProofAttemptRecord(
            theorem="t", difficulty="easy", success=True,
            n_attempts=1, proof_text=long_proof
        )
        d = rec.to_dict()
        assert len(d["proof_text"]) <= 120

    def test_failed_record_proof_text_none(self):
        rec = ProofAttemptRecord(
            theorem="t", difficulty="hard", success=False,
            n_attempts=4, proof_text=None
        )
        assert rec.to_dict()["proof_text"] is None

    def test_default_errors_empty(self):
        rec = ProofAttemptRecord(
            theorem="t", difficulty="easy", success=True, n_attempts=1
        )
        assert rec.errors_seen == []


# ===========================================================================
# TestProofSession
# ===========================================================================

class TestProofSession:
    """Iterative attempt loop, error feedback, sorry rejection."""

    def test_prove_returns_record(self):
        lean = _mock_lean()
        session = ProofSession(lean_tool=lean, max_retries=3)
        thm = "theorem add_zero (n : Nat) : n + 0 = n"
        record = session.prove(thm, TheoremDifficulty.EASY)
        assert isinstance(record, ProofAttemptRecord)

    def test_prove_easy_canonical_theorem(self):
        """Canonical theorems should be proved by ProofSession in mock mode."""
        lean = _mock_lean()
        session = ProofSession(lean_tool=lean, max_retries=3)
        thm = "theorem add_zero (n : Nat) : n + 0 = n"
        record = session.prove(thm, TheoremDifficulty.EASY)
        assert record.success

    def test_prove_attempt0_generates_error(self):
        """Attempt 0 with 'sorry' should always generate an error in mock."""
        lean = _mock_lean()
        session = ProofSession(lean_tool=lean, max_retries=3)
        thm = "theorem add_zero (n : Nat) : n + 0 = n"
        record = session.prove(thm)
        # errors_seen should include the attempt-0 error
        assert len(record.errors_seen) >= 1

    def test_prove_medium_theorem(self):
        lean = _mock_lean()
        session = ProofSession(lean_tool=lean, max_retries=3)
        thm = "theorem add_comm (a b : Nat) : a + b = b + a"
        record = session.prove(thm, TheoremDifficulty.MEDIUM)
        assert record.success

    def test_prove_hard_theorem(self):
        lean = _mock_lean()
        session = ProofSession(lean_tool=lean, max_retries=3)
        thm = "theorem mul_add (a b c : Nat) : a * (b + c) = a * b + a * c"
        record = session.prove(thm, TheoremDifficulty.HARD)
        assert record.success

    def test_n_attempts_at_least_2(self):
        """Attempt 0 (bad) + attempt 1 (good) = at least 2 total."""
        lean = _mock_lean()
        session = ProofSession(lean_tool=lean, max_retries=3)
        record = session.prove("theorem add_zero (n : Nat) : n + 0 = n")
        assert record.n_attempts >= 2

    def test_unknown_theorem_tries_tactics(self):
        """Theorem not in canonical dict falls back to tactic cycling."""
        lean = _mock_lean()
        session = ProofSession(lean_tool=lean, max_retries=3)
        # mock mode returns None for any 'theorem ... by ...' → success
        record = session.prove(
            "theorem my_custom_theorem (n : Nat) : n = n",
            TheoremDifficulty.EASY,
        )
        # In mock mode 'theorem ... by' is accepted
        assert record.success

    def test_wall_time_positive(self):
        lean = _mock_lean()
        session = ProofSession(lean_tool=lean)
        record = session.prove("theorem add_zero (n : Nat) : n + 0 = n")
        assert record.wall_time_s >= 0.0

    def test_proof_text_set_on_success(self):
        lean = _mock_lean()
        session = ProofSession(lean_tool=lean, max_retries=3)
        record = session.prove("theorem add_zero (n : Nat) : n + 0 = n")
        if record.success:
            assert record.proof_text is not None
            assert len(record.proof_text) > 0

    def test_error_feedback_injected_as_comment(self):
        """Build_proof should prepend '-- prev error:' comment after errors."""
        lean = _mock_lean()
        session = ProofSession(lean_tool=lean, max_retries=1)
        # Inject a fake error and check the next proof includes feedback
        fake_errors = ["type mismatch at theorem"]
        proof = session._build_proof(
            "theorem add_zero (n : Nat) : n + 0 = n", attempt=1, errors=fake_errors
        )
        assert "-- prev error:" in proof


# ===========================================================================
# TestTheoremProver
# ===========================================================================

class TestTheoremProver:
    """Batch prove, curriculum prove, summary."""

    def test_prove_curriculum_returns_report(self):
        prover = _build_prover(n_per_level=2)
        report = prover.prove_curriculum()
        assert isinstance(report, TheoremProvingReport)

    def test_prove_curriculum_attempts_all_levels(self):
        prover = _build_prover(n_per_level=2)
        report = prover.prove_curriculum()
        levels_attempted = {r.difficulty for r in report.records}
        assert levels_attempted == set(TheoremDifficulty.ALL)

    def test_prove_curriculum_n_theorems(self):
        prover = _build_prover(n_per_level=3)
        report = prover.prove_curriculum()
        # 3 levels × 3 per level = 9 theorems
        assert report.n_theorems == 9

    def test_prove_batch_returns_records(self):
        prover = _build_prover()
        theorems = ["theorem add_zero (n : Nat) : n + 0 = n"]
        records = prover.prove_batch(theorems, TheoremDifficulty.EASY)
        assert len(records) == 1
        assert isinstance(records[0], ProofAttemptRecord)

    def test_prove_batch_updates_curriculum_stats(self):
        prover = _build_prover()
        theorems = ["theorem add_zero (n : Nat) : n + 0 = n"]
        prover.prove_batch(theorems, TheoremDifficulty.EASY)
        rates = prover.curriculum.success_rates()
        assert rates[TheoremDifficulty.EASY] is not None

    def test_summary_empty_before_prove(self):
        prover = _build_prover()
        summ = prover.summary()
        assert summ["n_theorems"] == 0

    def test_summary_after_prove(self):
        prover = _build_prover(n_per_level=2)
        prover.prove_curriculum()
        summ = prover.summary()
        assert summ["n_theorems"] > 0
        assert "overall_success_rate" in summ
        assert "per_difficulty_rates" in summ
        assert "avg_attempts" in summ

    def test_prove_single_difficulty(self):
        prover = _build_prover(n_per_level=2)
        report = prover.prove_curriculum(difficulties=[TheoremDifficulty.EASY])
        levels = {r.difficulty for r in report.records}
        assert levels == {TheoremDifficulty.EASY}

    def test_records_accumulated_across_calls(self):
        prover = _build_prover(n_per_level=2)
        prover.prove_curriculum(difficulties=[TheoremDifficulty.EASY])
        prover.prove_curriculum(difficulties=[TheoremDifficulty.MEDIUM])
        assert len(prover.records) == 4  # 2 + 2


# ===========================================================================
# TestWP33ExitCriteria
# ===========================================================================

class TestWP33ExitCriteria:
    """verify_wp33_exit_criteria — four criteria."""

    def _prover_with_report(self) -> tuple:
        prover = _build_prover(n_per_level=3)
        report = prover.prove_curriculum()
        return prover, report

    def test_returns_dict(self):
        prover, report = self._prover_with_report()
        result = verify_wp33_exit_criteria(prover, report)
        assert isinstance(result, dict)

    def test_four_criteria(self):
        prover, report = self._prover_with_report()
        result = verify_wp33_exit_criteria(prover, report)
        assert len(result) == 4

    def test_all_criteria_pass(self):
        prover, report = self._prover_with_report()
        result = verify_wp33_exit_criteria(prover, report)
        for criterion, passed in result.items():
            assert passed, f"Criterion failed: '{criterion}'"

    def test_criterion_easy_proved(self):
        prover, report = self._prover_with_report()
        result = verify_wp33_exit_criteria(prover, report)
        assert result["At least one easy theorem proved"]

    def test_criterion_sorry_rejected(self):
        prover, report = self._prover_with_report()
        result = verify_wp33_exit_criteria(prover, report)
        assert result["LeanTool rejects 'sorry' proofs"]

    def test_criterion_error_feedback(self):
        prover, report = self._prover_with_report()
        result = verify_wp33_exit_criteria(prover, report)
        assert result["Error feedback loop operational"]

    def test_criterion_all_levels_attempted(self):
        prover, report = self._prover_with_report()
        result = verify_wp33_exit_criteria(prover, report)
        assert result["Theorems attempted at all difficulty levels"]

    def test_criterion_all_levels_fails_single_level(self):
        """Proving only easy theorems → all-levels criterion should fail."""
        prover = _build_prover(n_per_level=2)
        report = prover.prove_curriculum(difficulties=[TheoremDifficulty.EASY])
        result = verify_wp33_exit_criteria(prover, report)
        assert not result["Theorems attempted at all difficulty levels"]


# ===========================================================================
# TestIntegration
# ===========================================================================

class TestIntegration:
    """End-to-end: prover → report → exit criteria."""

    def test_full_curriculum_run(self):
        prover = _build_prover(n_per_level=6, max_retries=3)
        report = prover.prove_curriculum()

        assert report.n_theorems == 18          # 6 × 3 levels
        assert 0.0 <= report.overall_success_rate <= 1.0
        assert report.avg_attempts >= 1.0
        assert isinstance(report.error_feedback_operational, bool)

    def test_report_to_dict_keys(self):
        prover = _build_prover(n_per_level=2)
        report = prover.prove_curriculum()
        d = report.to_dict()
        for key in (
            "n_theorems", "n_proved", "overall_success_rate",
            "per_difficulty_rates", "avg_attempts",
            "error_feedback_operational", "audit_log",
        ):
            assert key in d, f"Missing key: {key}"

    def test_audit_log_length(self):
        prover = _build_prover(n_per_level=3)
        report = prover.prove_curriculum()
        d = report.to_dict()
        assert len(d["audit_log"]) == 9

    def test_per_difficulty_rates_all_keys(self):
        prover = _build_prover(n_per_level=2)
        report = prover.prove_curriculum()
        d = report.to_dict()
        for level in TheoremDifficulty.ALL:
            assert level in d["per_difficulty_rates"]

    def test_exit_criteria_pass_after_full_run(self):
        prover = _build_prover(n_per_level=6)
        report = prover.prove_curriculum()
        result = verify_wp33_exit_criteria(prover, report)
        assert all(result.values()), f"Criteria failures: {result}"

    def test_canonical_proofs_cover_all_seed_theorems(self):
        """Every seed theorem should have a canonical proof entry."""
        for level in TheoremDifficulty.ALL:
            for thm in _SEED_THEOREMS[level]:
                assert thm in _CANONICAL_PROOFS, (
                    f"Missing canonical proof for: {thm!r}"
                )

    def test_multiple_provers_independent(self):
        """Two independent provers should not share state."""
        p1 = _build_prover(n_per_level=2)
        p2 = _build_prover(n_per_level=2)
        p1.prove_curriculum()
        p2.prove_curriculum(difficulties=[TheoremDifficulty.EASY])
        assert p1.summary()["n_theorems"] == 6   # 3 levels × 2
        assert p2.summary()["n_theorems"] == 2   # 1 level × 2
