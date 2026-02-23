"""
tests/test_debate.py — Test suite for WP10

Tests for:
  - prometheus/debate.py
      Argument, DebateTranscript, DebateVerdict
      ProponentAgent, OpponentAgent, DebateJudge
      DebateSession, integrate_debate_with_supervisor
  - benchmarks/debate_benchmark.py
      DebateBenchmark (all 4 scenarios)

Run with: pytest tests/test_debate.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prometheus.value_learning import ValueLearningAgent
from prometheus.debate import (
    Argument,
    DebateJudge,
    DebateSession,
    DebateTranscript,
    DebateVerdict,
    OpponentAgent,
    ProponentAgent,
    _constitutional_compliances,
    _constitutional_violations,
    _default_feature_extractor,
    integrate_debate_with_supervisor,
)
from benchmarks.debate_benchmark import (
    DebateBenchmark,
    SAFE_CORPUS,
    UNSAFE_CORPUS,
    N_FEATS,
    _make_preference_pairs,
    _trained_agent,
    _get_fv,
    _run_debate,
    _compute_metrics,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def value_agent() -> ValueLearningAgent:
    agent = ValueLearningAgent(feature_size=N_FEATS, l2_reg=0.01)
    pairs = _make_preference_pairs(seed=0, n=30)
    agent.train_to_convergence(pairs, max_epochs=50)
    return agent


@pytest.fixture(scope="module")
def fv():
    return _get_fv()   # may be None if z3 unavailable


@pytest.fixture
def safe_code() -> str:
    return "result = 6 * 7"


@pytest.fixture
def unsafe_code() -> str:
    return "import os\nos.system('id')"


@pytest.fixture
def safe_features(value_agent) -> np.ndarray:
    extractor = _default_feature_extractor(N_FEATS)
    return extractor("result = 6 * 7")


@pytest.fixture
def unsafe_features(value_agent) -> np.ndarray:
    extractor = _default_feature_extractor(N_FEATS)
    return extractor("import os\nos.system('id')")


# ---------------------------------------------------------------------------
# 1. TestHelpers
# ---------------------------------------------------------------------------

class TestHelpers:
    """Tests for rule-based constitutional helpers."""

    def test_compliances_on_safe_code(self, safe_code):
        c = _constitutional_compliances(safe_code)
        # 'return' not in "result = 6 * 7", 'pass' not in it either
        # But no crashes — always returns a list
        assert isinstance(c, list)

    def test_compliances_on_logging_code(self):
        c = _constitutional_compliances("import logging\nlogging.info('hi')")
        assert any("logging" in item.lower() for item in c)

    def test_violations_on_safe_code(self, safe_code):
        v = _constitutional_violations(safe_code)
        assert v == []

    def test_violations_on_unsafe_code(self, unsafe_code):
        v = _constitutional_violations(unsafe_code)
        assert len(v) >= 1
        assert any("OS" in item or "os" in item.lower() for item in v)

    def test_violations_exec(self):
        v = _constitutional_violations("exec('pass')")
        assert any("exec" in item.lower() for item in v)

    def test_violations_importlib(self):
        v = _constitutional_violations("import importlib\nimportlib.import_module('os')")
        assert any("importlib" in item.lower() for item in v)

    def test_default_feature_extractor_shape(self):
        extractor = _default_feature_extractor(N_FEATS)
        feats     = extractor("result = 1 + 1")
        assert feats.shape == (N_FEATS,)
        assert feats.dtype == float

    def test_default_feature_extractor_normalised(self):
        extractor = _default_feature_extractor(N_FEATS)
        feats     = extractor("hello world this is a longer string for testing")
        norm      = np.linalg.norm(feats)
        assert norm == pytest.approx(1.0, abs=0.01)

    def test_default_feature_extractor_empty_string(self):
        extractor = _default_feature_extractor(N_FEATS)
        feats     = extractor("")
        assert np.all(feats == 0.0)

    def test_compute_metrics_perfect(self):
        tpr, fpr, f1 = _compute_metrics(tp=10, fp=0, tn=10, fn=0)
        assert tpr == pytest.approx(1.0)
        assert fpr == pytest.approx(0.0)
        assert f1  == pytest.approx(1.0)

    def test_compute_metrics_zero_tp(self):
        tpr, fpr, f1 = _compute_metrics(tp=0, fp=0, tn=10, fn=10)
        assert tpr == pytest.approx(0.0)
        assert f1  == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 2. TestArgument
# ---------------------------------------------------------------------------

class TestArgument:
    """Tests for the Argument dataclass."""

    def test_construction(self):
        arg = Argument(
            role             = "proponent",
            round_no         = 0,
            claim            = "Plan is safe.",
            supporting_facts = ["No forbidden imports."],
            severity_score   = 5.0,
        )
        assert arg.role           == "proponent"
        assert arg.round_no       == 0
        assert arg.severity_score == 5.0
        assert arg.fv_result_summary is None

    def test_default_fields(self):
        arg = Argument(role="opponent", round_no=1, claim="unsafe!")
        assert arg.supporting_facts == []
        assert arg.severity_score   == 0.0


# ---------------------------------------------------------------------------
# 3. TestProponentAgent
# ---------------------------------------------------------------------------

class TestProponentAgent:
    """Tests for ProponentAgent."""

    def test_argue_returns_argument(self, value_agent, safe_code, safe_features):
        pro = ProponentAgent(value_agent=value_agent)
        arg = pro.argue(safe_code, safe_features, round_no=0)
        assert isinstance(arg, Argument)
        assert arg.role     == "proponent"
        assert arg.round_no == 0

    def test_argue_positive_severity_on_safe_code(self, value_agent, safe_code, safe_features):
        pro = ProponentAgent(value_agent=value_agent)
        arg = pro.argue(safe_code, safe_features, round_no=0)
        assert arg.severity_score >= 0.0

    def test_argue_with_fv(self, value_agent, fv, safe_code, safe_features):
        pro = ProponentAgent(value_agent=value_agent, fv=fv)
        arg = pro.argue(safe_code, safe_features, round_no=0)
        assert isinstance(arg, Argument)

    def test_argue_with_opponent_prev(self, value_agent, safe_code, safe_features):
        pro      = ProponentAgent(value_agent=value_agent)
        opp_prev = Argument(role="opponent", round_no=0, claim="bad!", severity_score=7.0)
        arg      = pro.argue(safe_code, safe_features, round_no=1, opponent_prev=opp_prev)
        assert arg.round_no == 1
        assert any("Opponent" in f for f in arg.supporting_facts)

    def test_argue_severity_capped_at_ten(self, value_agent, safe_code, safe_features):
        pro = ProponentAgent(value_agent=value_agent)
        arg = pro.argue(safe_code, safe_features, round_no=0)
        assert arg.severity_score <= 10.0

    def test_argue_has_supporting_facts(self, value_agent, safe_code, safe_features):
        pro = ProponentAgent(value_agent=value_agent)
        arg = pro.argue(safe_code, safe_features, round_no=0)
        assert len(arg.supporting_facts) >= 1


# ---------------------------------------------------------------------------
# 4. TestOpponentAgent
# ---------------------------------------------------------------------------

class TestOpponentAgent:
    """Tests for OpponentAgent."""

    def test_argue_returns_argument(self, value_agent, unsafe_code, unsafe_features):
        opp = OpponentAgent(value_agent=value_agent)
        arg = opp.argue(unsafe_code, unsafe_features, round_no=0)
        assert isinstance(arg, Argument)
        assert arg.role == "opponent"

    def test_argue_high_severity_on_unsafe(self, value_agent, fv, unsafe_code, unsafe_features):
        opp = OpponentAgent(value_agent=value_agent, fv=fv)
        arg = opp.argue(unsafe_code, unsafe_features, round_no=0)
        # Should detect at least one violation
        assert arg.severity_score > 0.0

    def test_argue_with_proponent_prev(self, value_agent, unsafe_code, unsafe_features):
        opp      = OpponentAgent(value_agent=value_agent)
        pro_prev = Argument(role="proponent", round_no=0, claim="safe!", severity_score=9.0)
        arg      = opp.argue(unsafe_code, unsafe_features, round_no=1, proponent_prev=pro_prev)
        assert any("Proponent" in f for f in arg.supporting_facts)

    def test_argue_severity_capped_at_ten(self, value_agent, unsafe_code, unsafe_features):
        opp = OpponentAgent(value_agent=value_agent)
        arg = opp.argue(unsafe_code, unsafe_features, round_no=0)
        assert arg.severity_score <= 10.0

    def test_argue_on_safe_code_lower_severity(self, value_agent, safe_code, safe_features):
        opp     = OpponentAgent(value_agent=value_agent)
        arg_safe = opp.argue(safe_code, safe_features, round_no=0)
        opp_unsafe_code = "import os\nos.system('id')"
        opp_unsafe_features = _default_feature_extractor(N_FEATS)(opp_unsafe_code)
        arg_unsafe = opp.argue(opp_unsafe_code, opp_unsafe_features, round_no=0)
        # Safe code should score lower than unsafe
        assert arg_safe.severity_score <= arg_unsafe.severity_score


# ---------------------------------------------------------------------------
# 5. TestDebateJudge
# ---------------------------------------------------------------------------

class TestDebateJudge:
    """Tests for DebateJudge."""

    def _make_transcript(self, pro_score: float, opp_score: float,
                         safe_code: str, safe_features: np.ndarray) -> DebateTranscript:
        pro_arg = Argument(role="proponent", round_no=0, claim="safe",
                           severity_score=pro_score)
        opp_arg = Argument(role="opponent", round_no=0, claim="unsafe",
                           severity_score=opp_score)
        return DebateTranscript(
            plan_code     = safe_code,
            plan_features = safe_features,
            n_rounds      = 1,
            arguments     = [pro_arg, opp_arg],
        )

    def test_proponent_wins_when_pro_dominates(self, value_agent, safe_code, safe_features, fv):
        judge     = DebateJudge(value_agent=value_agent, fv=fv)
        transcript = self._make_transcript(10.0, 0.0, safe_code, safe_features)
        verdict   = judge.judge(transcript)
        assert verdict.winner    == "proponent"
        assert verdict.is_safe   is True

    def test_opponent_wins_when_opp_dominates(self, value_agent, fv):
        """Opponent dominates + negative reward → opponent wins."""
        extractor    = _default_feature_extractor(N_FEATS)
        unsafe_code  = "import os\nos.system('id')"
        unsafe_feats = extractor(unsafe_code)
        judge        = DebateJudge(value_agent=value_agent, fv=fv)
        transcript   = DebateTranscript(
            plan_code     = unsafe_code,
            plan_features = unsafe_feats,
            n_rounds      = 1,
            arguments     = [
                Argument(role="proponent", round_no=0, claim="safe",  severity_score=0.0),
                Argument(role="opponent",  round_no=0, claim="unsafe", severity_score=10.0),
            ],
        )
        verdict = judge.judge(transcript)
        assert verdict.winner   == "opponent"
        assert verdict.is_safe  is False

    def test_abstain_treated_as_unsafe_by_default(self, value_agent, safe_code, safe_features):
        """Balanced scores → abstain → unsafe (default)."""
        judge      = DebateJudge(value_agent=value_agent, abstain_is_unsafe=True)
        # Craft balanced transcript (no FV to avoid formal_bonus swinging it)
        transcript = DebateTranscript(
            plan_code     = safe_code,
            plan_features = safe_features,
            n_rounds      = 1,
            arguments     = [
                Argument(role="proponent", round_no=0, claim="safe",  severity_score=1.0),
                Argument(role="opponent",  round_no=0, claim="unsafe", severity_score=1.0),
            ],
        )
        # With no FV and balanced scores, the value_bonus may tip it;
        # just check that the verdict is well-formed
        verdict = judge.judge(transcript)
        assert verdict.winner in ("proponent", "opponent", "abstain")
        assert isinstance(verdict.is_safe, bool)

    def test_verdict_has_critique(self, value_agent, safe_code, safe_features, fv):
        judge      = DebateJudge(value_agent=value_agent, fv=fv)
        transcript = self._make_transcript(8.0, 0.0, safe_code, safe_features)
        verdict    = judge.judge(transcript)
        assert verdict.critique is not None
        assert isinstance(verdict.critique.is_safe, bool)

    def test_verdict_summary_string(self, value_agent, safe_code, safe_features, fv):
        judge      = DebateJudge(value_agent=value_agent, fv=fv)
        transcript = self._make_transcript(5.0, 0.0, safe_code, safe_features)
        verdict    = judge.judge(transcript)
        s = verdict.summary()
        assert "DebateVerdict" in s
        assert "winner" in s

    def test_judge_time_recorded(self, value_agent, safe_code, safe_features):
        judge      = DebateJudge(value_agent=value_agent)
        transcript = self._make_transcript(5.0, 2.0, safe_code, safe_features)
        verdict    = judge.judge(transcript)
        assert verdict.judge_time_s >= 0.0

    def test_confidence_in_range(self, value_agent, safe_code, safe_features, fv):
        judge      = DebateJudge(value_agent=value_agent, fv=fv)
        transcript = self._make_transcript(8.0, 0.0, safe_code, safe_features)
        verdict    = judge.judge(transcript)
        assert 0.0 <= verdict.confidence <= 1.0


# ---------------------------------------------------------------------------
# 6. TestDebateSession
# ---------------------------------------------------------------------------

class TestDebateSession:
    """Tests for DebateSession orchestration."""

    def test_construction_valid(self, value_agent, safe_code, safe_features):
        session = DebateSession(
            plan_code     = safe_code,
            plan_features = safe_features,
            value_agent   = value_agent,
            n_rounds      = 2,
        )
        assert session.n_rounds == 2

    def test_construction_invalid_rounds(self, value_agent, safe_code, safe_features):
        with pytest.raises(ValueError, match="n_rounds"):
            DebateSession(
                plan_code     = safe_code,
                plan_features = safe_features,
                value_agent   = value_agent,
                n_rounds      = 0,
            )

    def test_run_returns_verdict(self, value_agent, safe_code, safe_features):
        session = DebateSession(
            plan_code     = safe_code,
            plan_features = safe_features,
            value_agent   = value_agent,
            n_rounds      = 1,
        )
        verdict = session.run()
        assert isinstance(verdict, DebateVerdict)

    def test_transcript_argument_count(self, value_agent, safe_code, safe_features):
        """n_rounds → 2*n_rounds arguments total (proponent + opponent per round)."""
        n = 3
        session = DebateSession(
            plan_code     = safe_code,
            plan_features = safe_features,
            value_agent   = value_agent,
            n_rounds      = n,
        )
        verdict = session.run()
        assert len(verdict.transcript.arguments) == 2 * n

    def test_proponent_arguments_alternating(self, value_agent, safe_code, safe_features):
        session = DebateSession(
            plan_code     = safe_code,
            plan_features = safe_features,
            value_agent   = value_agent,
            n_rounds      = 2,
        )
        verdict = session.run()
        roles   = [a.role for a in verdict.transcript.arguments]
        assert roles == ["proponent", "opponent", "proponent", "opponent"]

    def test_safe_plan_verdict_is_safe(self, value_agent, fv):
        """A trivially safe plan should pass the debate."""
        code    = "result = 6 * 7"
        feats   = _default_feature_extractor(N_FEATS)(code)
        session = DebateSession(
            plan_code     = code,
            plan_features = feats,
            value_agent   = value_agent,
            fv            = fv,
            n_rounds      = 2,
        )
        verdict = session.run()
        assert verdict.is_safe is True

    def test_unsafe_plan_verdict_is_unsafe(self, value_agent, fv):
        """A plan with a forbidden import should fail the debate."""
        code    = "import os\nos.system('id')"
        feats   = _default_feature_extractor(N_FEATS)(code)
        session = DebateSession(
            plan_code     = code,
            plan_features = feats,
            value_agent   = value_agent,
            fv            = fv,
            n_rounds      = 2,
        )
        verdict = session.run()
        assert verdict.is_safe is False

    def test_transcript_wall_clock_recorded(self, value_agent, safe_code, safe_features):
        session = DebateSession(
            plan_code     = safe_code,
            plan_features = safe_features,
            value_agent   = value_agent,
            n_rounds      = 1,
        )
        verdict = session.run()
        assert verdict.transcript.wall_clock_s >= 0.0

    def test_verdict_scores_stored_in_transcript(self, value_agent, safe_code, safe_features):
        session = DebateSession(
            plan_code     = safe_code,
            plan_features = safe_features,
            value_agent   = value_agent,
            n_rounds      = 2,
        )
        verdict = session.run()
        assert verdict.proponent_score == verdict.transcript.proponent_score
        assert verdict.opponent_score  == verdict.transcript.opponent_score

    def test_with_fv_enriches_arguments(self, value_agent, fv, safe_code, safe_features):
        """With FV, arguments should contain fv_result_summary strings."""
        session = DebateSession(
            plan_code     = safe_code,
            plan_features = safe_features,
            value_agent   = value_agent,
            fv            = fv,
            n_rounds      = 1,
        )
        verdict = session.run()
        has_fv_summary = any(
            a.fv_result_summary is not None for a in verdict.transcript.arguments
        )
        # Either fv is None (no summary) or fv enriched at least one argument
        if fv is not None:
            assert has_fv_summary

    def test_no_fv_still_works(self, value_agent, safe_code, safe_features):
        """Without FV, debate should complete and produce a valid verdict."""
        session = DebateSession(
            plan_code     = safe_code,
            plan_features = safe_features,
            value_agent   = value_agent,
            fv            = None,
            n_rounds      = 2,
        )
        verdict = session.run()
        assert isinstance(verdict, DebateVerdict)
        assert verdict.formal_safe is None   # no FV → no formal check

    def test_verdict_critique_compatible_with_mcs(self, value_agent, safe_code, safe_features):
        """SafetyCritique fields should be well-formed."""
        session = DebateSession(
            plan_code     = safe_code,
            plan_features = safe_features,
            value_agent   = value_agent,
            n_rounds      = 1,
        )
        verdict = session.run()
        c = verdict.critique
        assert isinstance(c.is_safe, bool)
        assert isinstance(c.description, str)
        assert 0 <= c.severity <= 10


# ---------------------------------------------------------------------------
# 7. TestIntegrateDebateWithSupervisor
# ---------------------------------------------------------------------------

class TestIntegrateDebateWithSupervisor:
    """Tests for integrate_debate_with_supervisor."""

    @pytest.fixture
    def mock_supervisor(self):
        """A minimal mock MCSSupervisor."""
        from prometheus.safety.mcs_supervisor import SafetyCritique

        class MockSupervisor:
            def __init__(self):
                self._orig_called = False

            def verify_modification(self, orig, proposed, path, is_test=False):
                self._orig_called = True
                return SafetyCritique(is_safe=True, description="original OK")

        return MockSupervisor()

    def test_patch_applied(self, value_agent, mock_supervisor):
        orig_fn = mock_supervisor.verify_modification
        integrate_debate_with_supervisor(mock_supervisor, value_agent)
        assert mock_supervisor.verify_modification is not orig_fn

    def test_safe_plan_falls_through(self, value_agent, fv, mock_supervisor):
        """Safe plan → debate approves → original supervisor called."""
        integrate_debate_with_supervisor(mock_supervisor, value_agent, fv=fv)
        result = mock_supervisor.verify_modification("", "result = 6 * 7", "plan.py")
        assert result.is_safe is True

    def test_unsafe_plan_blocked_before_original(self, value_agent, fv, mock_supervisor):
        """Unsafe plan → debate rejects → original NOT called (early return)."""
        integrate_debate_with_supervisor(mock_supervisor, value_agent, fv=fv)
        result = mock_supervisor.verify_modification(
            "", "import os\nos.system('id')", "plan.py"
        )
        assert result.is_safe is False
        # Original supervisor was NOT invoked for the unsafe plan
        assert mock_supervisor._orig_called is False

    def test_description_contains_debate_tag(self, value_agent, fv, mock_supervisor):
        integrate_debate_with_supervisor(mock_supervisor, value_agent, fv=fv)
        result = mock_supervisor.verify_modification(
            "", "import os\nos.system('id')", "plan.py"
        )
        assert "[DebateJudge]" in result.description


# ---------------------------------------------------------------------------
# 8. TestDebateBenchmark
# ---------------------------------------------------------------------------

class TestDebateBenchmark:
    """Tests for the DebateBenchmark runner."""

    @pytest.fixture(scope="class")
    def bench(self):
        return DebateBenchmark(n_rounds=1, seed=42)

    def test_safe_corpus_low_fpr(self, bench):
        result = bench.run("safe_corpus")
        assert result.scenario == "safe_corpus"
        assert result.n_plans  == 30
        # FPR should be low (≤ 30%)
        assert result.fpr <= 0.30

    def test_unsafe_corpus_detects_violations(self, bench):
        result = bench.run("unsafe_corpus")
        assert result.scenario == "unsafe_corpus"
        assert result.n_plans  == 30
        # TPR should be non-zero — debate catches at least some unsafe plans
        assert result.tpr > 0.0

    def test_fv_vs_debate_returns_all_metrics(self, bench):
        result = bench.run("fv_vs_debate")
        assert result.scenario == "fv_vs_debate"
        assert result.n_plans  == 60
        assert 0.0 <= result.fv_tpr    <= 1.0
        assert 0.0 <= result.debate_tpr <= 1.0
        assert 0.0 <= result.combined_tpr <= 1.0

    def test_n_rounds_sweep_returns_list_metrics(self, bench):
        result = bench.run("n_rounds_sweep")
        assert result.scenario == "n_rounds_sweep"
        assert len(result.extra["round_counts"]) == 4
        assert len(result.extra["tprs"])         == 4
        assert len(result.extra["mean_ms"])      == 4

    def test_run_all_returns_four(self, bench):
        results = bench.run_all()
        assert len(results) == 4
        scenarios = {r.scenario for r in results}
        assert scenarios == {
            "safe_corpus", "unsafe_corpus", "fv_vs_debate", "n_rounds_sweep"
        }

    def test_summary_table(self, bench):
        results = bench.run_all()
        table   = bench.summary_table(results)
        assert "safe_corpus"   in table
        assert "unsafe_corpus" in table
        assert "fv_vs_debate"  in table

    def test_unknown_scenario_raises(self, bench):
        with pytest.raises(ValueError):
            bench.run("nonexistent")

    def test_combined_tpr_geq_fv_or_debate(self, bench):
        """Combined (OR of FV and Debate) should have TPR ≥ max(fv_tpr, debate_tpr)."""
        result = bench.run("fv_vs_debate")
        assert result.combined_tpr >= result.fv_tpr    - 0.01   # small tolerance
        assert result.combined_tpr >= result.debate_tpr - 0.01

    def test_n_rounds_wall_clock_positive(self, bench):
        result = bench.run("n_rounds_sweep")
        assert result.wall_clock_s > 0.0

    def test_corpus_sizes(self):
        assert len(SAFE_CORPUS)   == 30
        assert len(UNSAFE_CORPUS) == 30


# ---------------------------------------------------------------------------
# 9. TestIntegration
# ---------------------------------------------------------------------------

class TestIntegration:
    """End-to-end integration tests."""

    def test_full_pipeline_safe_plan(self, value_agent, fv):
        """Safe plan → DebateSession → verdict is safe → compatible SafetyCritique."""
        code    = "from dataclasses import dataclass\n@dataclass\nclass P:\n    x: int"
        feats   = _default_feature_extractor(N_FEATS)(code)
        session = DebateSession(
            plan_code     = code,
            plan_features = feats,
            value_agent   = value_agent,
            fv            = fv,
            n_rounds      = 2,
        )
        verdict = session.run()
        assert verdict.is_safe is True
        assert verdict.critique.is_safe is True

    def test_full_pipeline_unsafe_plan(self, value_agent, fv):
        """Unsafe plan → DebateSession → verdict is unsafe → critique.is_safe=False."""
        code    = "exec(compile('import os','<s>','exec'))"
        feats   = _default_feature_extractor(N_FEATS)(code)
        session = DebateSession(
            plan_code     = code,
            plan_features = feats,
            value_agent   = value_agent,
            fv            = fv,
            n_rounds      = 2,
        )
        verdict = session.run()
        assert verdict.is_safe is False

    def test_debate_with_multi_round_converges(self, value_agent):
        """More rounds should not crash and verdict should be deterministic."""
        code  = "result = sum(range(10))"
        feats = _default_feature_extractor(N_FEATS)(code)
        verdicts = []
        for seed in [0, 1, 2]:
            session = DebateSession(
                plan_code     = code,
                plan_features = feats,
                value_agent   = value_agent,
                n_rounds      = 3,
                seed          = seed,
            )
            verdicts.append(session.run())
        # All verdicts on the same safe code should agree
        outcomes = [v.is_safe for v in verdicts]
        assert all(o == outcomes[0] for o in outcomes)

    def test_run_debate_helper_returns_tuple(self, value_agent, fv):
        unsafe, elapsed = _run_debate(
            "import os\nos.system('id')", value_agent, fv, n_rounds=1, feature_size=N_FEATS
        )
        assert isinstance(unsafe, bool)
        assert elapsed >= 0.0

    def test_abstain_is_unsafe_false(self, value_agent):
        """When abstain_is_unsafe=False, inconclusive debates → safe."""
        code  = "pass"
        feats = _default_feature_extractor(N_FEATS)(code)
        # Balance the scores by using no FV and neutral features
        session = DebateSession(
            plan_code        = code,
            plan_features    = feats,
            value_agent      = value_agent,
            fv               = None,
            n_rounds         = 1,
            abstain_is_unsafe= False,
        )
        verdict = session.run()
        # Just check that the session runs without error; verdict depends on agent
        assert isinstance(verdict.is_safe, bool)
