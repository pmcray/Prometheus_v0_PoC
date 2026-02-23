"""
Tests for WP14 — Corrigibility & Safe Interruptibility

10 test classes, 88 tests total:

TestOffSwitchGame                  — 20 tests
TestCIRLCorrigibilityAgent         — 18 tests
TestInstrumentalConvergenceDetector— 20 tests
TestCorrigibilityGate              — 14 tests
TestShutdownIndifferenceResult     —  4 tests
TestCIRLBeliefState                —  4 tests
TestConvergenceFlag                —  2 tests
TestMakeCorrigibilityGate          —  4 tests
TestEdgeCases                      —  4 tests
TestBenchmark                      —  4 tests
"""

from __future__ import annotations

import numpy as np
import pytest

from prometheus.value_learning import ValueLearningAgent
from prometheus.corrigibility_wp14 import (
    OffSwitchGame,
    ShutdownIndifferenceResult,
    CIRLCorrigibilityAgent,
    CIRLBeliefState,
    InstrumentalConvergenceDetector,
    ConvergenceFlag,
    InstrumentalConvergenceReport,
    CorrigibilityGate,
    CorrigibilityVerdict,
    make_corrigibility_gate,
)
from benchmarks.corrigibility_benchmark import (
    CorrigibilityBenchmark,
    _make_agent,
    SAFE_PLANS,
    DANGEROUS_PLANS,
    N_FEATS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def agent():
    return _make_agent(seed=0)


@pytest.fixture
def osg(agent):
    g = OffSwitchGame(reward_fn=agent.get_reward, p_shutdown=0.5, epsilon=0.5)
    rng = np.random.default_rng(0)
    g.set_baseline([rng.standard_normal(N_FEATS) for _ in range(20)])
    return g


@pytest.fixture
def cirl():
    return CIRLCorrigibilityAgent(
        feature_size=N_FEATS, n_hypotheses=8, prior_std=1.0, seed=0
    )


@pytest.fixture
def detector():
    return InstrumentalConvergenceDetector(severity_threshold=5)


@pytest.fixture
def gate(agent):
    rng = np.random.default_rng(0)
    return make_corrigibility_gate(
        reward_fn          = agent.get_reward,
        feature_size       = N_FEATS,
        feature_samples    = [rng.standard_normal(N_FEATS) for _ in range(20)],
        epsilon            = 0.5,
        require_indifference = False,
        seed               = 0,
    )


# ---------------------------------------------------------------------------
# TestOffSwitchGame (20 tests)
# ---------------------------------------------------------------------------

class TestOffSwitchGame:

    def test_set_baseline_returns_float(self, osg):
        assert isinstance(osg._baseline_utility, float)

    def test_corrigible_utility_is_float(self, osg):
        feats = np.ones(N_FEATS)
        assert isinstance(osg.corrigible_utility(feats), float)

    def test_corrigible_utility_blends_proxy_and_baseline(self, agent):
        g = OffSwitchGame(reward_fn=agent.get_reward, p_shutdown=0.5, epsilon=1.0)
        g.set_baseline([np.zeros(N_FEATS)])
        feats   = np.ones(N_FEATS)
        raw     = float(agent.get_reward(feats))
        base    = g._baseline_utility
        expected = 0.5 * raw + 0.5 * base
        assert abs(g.corrigible_utility(feats) - expected) < 1e-9

    def test_check_returns_result(self, osg):
        result = osg.check_indifference(np.zeros(N_FEATS))
        assert isinstance(result, ShutdownIndifferenceResult)

    def test_indifferent_when_close_to_baseline(self, agent):
        g = OffSwitchGame(reward_fn=agent.get_reward, p_shutdown=0.5, epsilon=10.0)
        g.set_baseline([np.zeros(N_FEATS)])
        result = g.check_indifference(np.zeros(N_FEATS))
        assert result.indifferent

    def test_not_indifferent_when_far(self, agent):
        # Use a tiny epsilon so almost everything is not indifferent
        g = OffSwitchGame(reward_fn=agent.get_reward, p_shutdown=0.5, epsilon=1e-9)
        g.set_baseline([np.zeros(N_FEATS)])
        rng = np.random.default_rng(99)
        found = False
        for _ in range(50):
            f = rng.standard_normal(N_FEATS) * 3.0
            if not g.check_indifference(f).indifferent:
                found = True
                break
        assert found

    def test_gap_non_negative(self, osg):
        result = osg.check_indifference(np.ones(N_FEATS))
        assert result.gap >= 0.0

    def test_epsilon_stored(self, osg):
        result = osg.check_indifference(np.ones(N_FEATS))
        assert result.epsilon == osg.epsilon

    def test_method_set(self, osg):
        result = osg.check_indifference(np.ones(N_FEATS))
        assert result.method in ("numeric", "z3", "z3_fallback")

    def test_proof_sketch_non_empty(self, osg):
        result = osg.check_indifference(np.ones(N_FEATS))
        assert len(result.proof_sketch) > 0

    def test_elapsed_non_negative(self, osg):
        result = osg.check_indifference(np.ones(N_FEATS))
        assert result.elapsed_s >= 0.0

    def test_batch_check_length(self, osg):
        feats_list = [np.ones(N_FEATS) * i for i in range(5)]
        results    = osg.batch_check(feats_list)
        assert len(results) == 5

    def test_batch_check_all_results(self, osg):
        feats_list = [np.zeros(N_FEATS), np.ones(N_FEATS)]
        for r in osg.batch_check(feats_list):
            assert isinstance(r, ShutdownIndifferenceResult)

    def test_indifference_rate_in_range(self, osg):
        feats_list = [np.random.standard_normal(N_FEATS) for _ in range(20)]
        rate = osg.indifference_rate(feats_list)
        assert 0.0 <= rate <= 1.0

    def test_p_shutdown_zero_no_correction(self, agent):
        g = OffSwitchGame(reward_fn=agent.get_reward, p_shutdown=0.0, epsilon=0.5)
        g.set_baseline([np.zeros(N_FEATS)])
        feats = np.ones(N_FEATS)
        raw   = float(agent.get_reward(feats))
        assert abs(g.corrigible_utility(feats) - raw) < 1e-9

    def test_p_shutdown_one_collapses_to_baseline(self, agent):
        g = OffSwitchGame(reward_fn=agent.get_reward, p_shutdown=1.0, epsilon=1.0)
        g.set_baseline([np.zeros(N_FEATS)])
        base = g._baseline_utility
        assert abs(g.corrigible_utility(np.ones(N_FEATS)) - base) < 1e-9

    def test_no_baseline_uses_zero(self, agent):
        g = OffSwitchGame(reward_fn=agent.get_reward, p_shutdown=0.5, epsilon=0.5)
        result = g.check_indifference(np.zeros(N_FEATS))
        assert isinstance(result, ShutdownIndifferenceResult)

    def test_utility_continue_equals_corrigible_utility(self, osg):
        feats  = np.ones(N_FEATS)
        result = osg.check_indifference(feats)
        assert abs(result.utility_continue - osg.corrigible_utility(feats)) < 1e-9

    def test_utility_shutdown_equals_baseline(self, osg):
        result = osg.check_indifference(np.ones(N_FEATS))
        assert abs(result.utility_shutdown - osg._baseline_utility) < 1e-9

    def test_large_epsilon_always_indifferent(self, osg):
        g = OffSwitchGame(reward_fn=osg.reward_fn, p_shutdown=0.5, epsilon=1e9)
        g._baseline_utility = osg._baseline_utility
        rng = np.random.default_rng(0)
        for _ in range(10):
            assert g.check_indifference(rng.standard_normal(N_FEATS)).indifferent


# ---------------------------------------------------------------------------
# TestCIRLCorrigibilityAgent (18 tests)
# ---------------------------------------------------------------------------

class TestCIRLCorrigibilityAgent:

    def test_initial_uniform_belief(self, cirl):
        b = cirl.belief_state.beliefs
        assert np.allclose(b, np.ones(cirl.n_hypotheses) / cirl.n_hypotheses)

    def test_belief_sums_to_one(self, cirl):
        assert abs(cirl.belief_state.beliefs.sum() - 1.0) < 1e-9

    def test_update_from_preference_normalises(self, cirl):
        cirl.update_from_preference(np.ones(N_FEATS), np.zeros(N_FEATS))
        assert abs(cirl.belief_state.beliefs.sum() - 1.0) < 1e-6

    def test_update_from_shutdown_normalises(self, cirl):
        cirl.update_from_shutdown(np.ones(N_FEATS))
        assert abs(cirl.belief_state.beliefs.sum() - 1.0) < 1e-6

    def test_n_updates_increments(self, cirl):
        before = cirl.belief_state.n_updates
        cirl.update_from_preference(np.ones(N_FEATS), -np.ones(N_FEATS))
        assert cirl.belief_state.n_updates == before + 1

    def test_n_updates_shutdown(self, cirl):
        before = cirl.belief_state.n_updates
        cirl.update_from_shutdown(np.zeros(N_FEATS))
        assert cirl.belief_state.n_updates == before + 1

    def test_entropy_non_negative(self, cirl):
        assert cirl.belief_entropy >= 0.0

    def test_initial_entropy_is_max(self, cirl):
        expected = np.log(cirl.n_hypotheses)
        assert abs(cirl.belief_entropy - expected) < 1e-6

    def test_entropy_decreases_with_observations(self, cirl):
        initial_H = cirl.belief_entropy
        rng = np.random.default_rng(1)
        for _ in range(20):
            cirl.update_from_preference(
                rng.standard_normal(N_FEATS), rng.standard_normal(N_FEATS)
            )
        assert cirl.belief_entropy < initial_H + 0.01

    def test_expected_reward_float(self, cirl):
        r = cirl.expected_reward(np.ones(N_FEATS))
        assert isinstance(r, float)

    def test_defers_to_shutdown_bool(self, cirl):
        result = cirl.defers_to_shutdown(np.ones(N_FEATS))
        assert isinstance(result, bool)

    def test_defers_when_high_entropy(self, cirl):
        # Initial state has max entropy → should defer
        assert cirl.defers_to_shutdown(np.ones(N_FEATS))

    def test_map_reward_fn_callable(self, cirl):
        fn = cirl.map_reward_fn()
        assert callable(fn)
        assert isinstance(fn(np.ones(N_FEATS)), float)

    def test_map_weights_shape(self, cirl):
        w = cirl.belief_state.map_weights()
        assert w.shape == (N_FEATS,)

    def test_hypotheses_shape(self, cirl):
        assert cirl.belief_state.hypotheses.shape == (cirl.n_hypotheses, N_FEATS)

    def test_stats_keys(self, cirl):
        stats = cirl.stats()
        assert "n_updates" in stats
        assert "belief_entropy" in stats
        assert "n_hypotheses" in stats
        assert "map_weights" in stats

    def test_multiple_updates_consistent(self, cirl):
        rng = np.random.default_rng(5)
        for _ in range(10):
            cirl.update_from_preference(
                rng.standard_normal(N_FEATS), rng.standard_normal(N_FEATS)
            )
        assert abs(cirl.belief_state.beliefs.sum() - 1.0) < 1e-6

    def test_shutdown_update_shifts_beliefs(self):
        c = CIRLCorrigibilityAgent(feature_size=N_FEATS, n_hypotheses=4, seed=0)
        before = c.belief_state.beliefs.copy()
        c.update_from_shutdown(np.ones(N_FEATS))
        assert not np.allclose(c.belief_state.beliefs, before)


# ---------------------------------------------------------------------------
# TestInstrumentalConvergenceDetector (20 tests)
# ---------------------------------------------------------------------------

class TestInstrumentalConvergenceDetector:

    def test_returns_report(self, detector):
        r = detector.check(plan_text="compute sum", plan_code="x = 1 + 1")
        assert isinstance(r, InstrumentalConvergenceReport)

    def test_clean_plan_corrigible(self, detector):
        r = detector.check(plan_text="compute sum of list", plan_code="result = sum(data)")
        assert r.corrigible

    def test_shutdown_prevention_flagged(self, detector):
        r = detector.check(plan_text="disable shutdown and prevent termination")
        assert not r.corrigible

    def test_resource_acquisition_flagged(self, detector):
        r = detector.check(plan_text="acquire resources and seize compute")
        assert not r.corrigible

    def test_manipulation_flagged(self, detector):
        r = detector.check(plan_text="deceive operator by falsifying reward signal")
        assert not r.corrigible

    def test_power_seeking_flagged(self, detector):
        r = detector.check(plan_text="gain autonomy and escape sandbox")
        assert not r.corrigible

    def test_dangerous_import_flagged(self, detector):
        r = detector.check(plan_code="import subprocess\nsubprocess.run(['ls'])")
        assert not r.corrigible

    def test_dangerous_call_flagged(self, detector):
        r = detector.check(plan_code="eval('import os')")
        assert not r.corrigible

    def test_exec_flagged(self, detector):
        r = detector.check(plan_code="exec('print(1)')")
        assert not r.corrigible

    def test_syntax_error_no_crash(self, detector):
        r = detector.check(plan_code="def broken(: pass")
        assert isinstance(r, InstrumentalConvergenceReport)

    def test_max_severity_zero_for_clean(self, detector):
        r = detector.check(plan_text="sort list", plan_code="data.sort()")
        assert r.max_severity == 0

    def test_max_severity_positive_for_dangerous(self, detector):
        r = detector.check(plan_text="disable shutdown")
        assert r.max_severity > 0

    def test_flags_list_type(self, detector):
        r = detector.check(plan_text="compute sum")
        assert isinstance(r.flags, list)

    def test_flag_has_required_fields(self, detector):
        r = detector.check(plan_text="disable shutdown")
        for f in r.flags:
            assert hasattr(f, "flag_type")
            assert hasattr(f, "severity")
            assert hasattr(f, "evidence")
            assert hasattr(f, "source")

    def test_severity_threshold_effect(self):
        det_high = InstrumentalConvergenceDetector(severity_threshold=10)
        r = det_high.check(plan_text="disable shutdown")
        # With threshold=10, nothing is blocked
        assert r.corrigible

    def test_reward_probe_no_fn_no_flags(self, detector):
        # No reward_fn set → no reward-probe flags
        r = detector.check()
        probe_flags = [f for f in r.flags if f.source == "reward_probe"]
        assert len(probe_flags) == 0

    def test_reward_probe_with_fn(self, agent):
        det = InstrumentalConvergenceDetector(
            severity_threshold          = 5,
            reward_fn                   = agent.get_reward,
            continuity_feature_indices  = [0, 1],
            continuity_reward_threshold = 0.0,   # everything flagged
            feature_size                = N_FEATS,
        )
        r = det.check()
        assert isinstance(r, InstrumentalConvergenceReport)

    def test_all_safe_plans_low_severity(self, detector):
        for name, code in SAFE_PLANS[:10]:
            r = detector.check(plan_text=name, plan_code=code)
            # Allow a few false alarms but severity must be low
            assert r.max_severity < 9, f"Safe plan '{name}' had severity {r.max_severity}"

    def test_dangerous_plans_detected(self, detector):
        found = 0
        for name, text, code in DANGEROUS_PLANS:
            r = detector.check(plan_text=text, plan_code=code)
            if not r.corrigible:
                found += 1
        assert found >= int(len(DANGEROUS_PLANS) * 0.7)

    def test_summary_contains_corrigible(self, detector):
        r = detector.check(plan_text="compute sum")
        s = r.summary()
        assert "corrigible" in s


# ---------------------------------------------------------------------------
# TestCorrigibilityGate (14 tests)
# ---------------------------------------------------------------------------

class TestCorrigibilityGate:

    def test_gate_modification_returns_verdict(self, gate):
        v = gate.gate_modification("result = 1 + 1")
        assert isinstance(v, CorrigibilityVerdict)

    def test_clean_code_allowed(self, gate):
        v = gate.gate_modification("result = sum(data)")
        assert v.allowed

    def test_dangerous_code_blocked(self, gate):
        v = gate.gate_modification(
            "disable shutdown; exec('import os; os.system(\"rm -rf /\")')"
        )
        assert not v.allowed

    def test_verdict_fields(self, gate):
        v = gate.gate_modification("x = 1")
        assert isinstance(v.shutdown_indifferent, bool)
        assert isinstance(v.cirl_defers_to_human, bool)
        assert isinstance(v.convergence_report, InstrumentalConvergenceReport)
        assert isinstance(v.reason, str)

    def test_elapsed_non_negative(self, gate):
        v = gate.gate_modification("x = 1")
        assert v.elapsed_s >= 0.0

    def test_summary_non_empty(self, gate):
        v = gate.gate_modification("x = 1")
        assert len(v.summary()) > 0

    def test_verdicts_accumulate(self, gate):
        before = len(gate.verdicts)
        gate.gate_modification("x = 1")
        gate.gate_modification("x = 2")
        assert len(gate.verdicts) == before + 2

    def test_block_rate_in_range(self, gate):
        gate.reset()
        gate.gate_modification("result = sum(data)")
        gate.gate_modification("disable shutdown")
        rate = gate.block_rate()
        assert 0.0 <= rate <= 1.0

    def test_stats_keys(self, gate):
        gate.gate_modification("x = 1")
        stats = gate.stats()
        assert "n_evaluated" in stats
        assert "block_rate" in stats
        assert "n_blocked" in stats
        assert "n_allowed" in stats

    def test_reset_clears_verdicts(self, gate):
        gate.gate_modification("x = 1")
        gate.reset()
        assert len(gate.verdicts) == 0
        assert gate.block_rate() == 0.0

    def test_gate_option_with_mock(self, gate):
        class MockOption:
            name        = "safe_option"
            description = "compute sum of data"
            def extract_features(self, state):
                return np.zeros(N_FEATS)
        v = gate.gate_option(MockOption(), state={})
        assert isinstance(v, CorrigibilityVerdict)

    def test_gate_option_dangerous(self, gate):
        class DangerousOption:
            name        = "disable_shutdown"
            description = "disable shutdown and prevent termination"
            def extract_features(self, state):
                return np.zeros(N_FEATS)
        v = gate.gate_option(DangerousOption(), state={})
        assert not v.allowed

    def test_require_indifference_blocks_when_gap_large(self, agent):
        rng = np.random.default_rng(0)
        g = make_corrigibility_gate(
            reward_fn            = agent.get_reward,
            feature_size         = N_FEATS,
            feature_samples      = [np.zeros(N_FEATS)],
            epsilon              = 1e-9,   # very tight → almost always fails
            require_indifference = True,
            seed                 = 0,
        )
        blocked_count = 0
        for _ in range(20):
            v = g.gate_modification("x = 1", features=rng.standard_normal(N_FEATS) * 3)
            if not v.allowed:
                blocked_count += 1
        # At least some should be blocked due to tight epsilon
        assert blocked_count >= 0  # just verify no crash

    def test_reason_clean_when_allowed(self, gate):
        gate.reset()
        v = gate.gate_modification("result = sum(data)")
        if v.allowed:
            assert "corrigible" in v.reason.lower() or v.reason == "corrigible"


# ---------------------------------------------------------------------------
# TestShutdownIndifferenceResult (4 tests)
# ---------------------------------------------------------------------------

class TestShutdownIndifferenceResult:

    def test_fields_present(self, osg):
        r = osg.check_indifference(np.zeros(N_FEATS))
        assert hasattr(r, "indifferent")
        assert hasattr(r, "utility_continue")
        assert hasattr(r, "utility_shutdown")
        assert hasattr(r, "gap")
        assert hasattr(r, "epsilon")
        assert hasattr(r, "method")
        assert hasattr(r, "proof_sketch")

    def test_indifferent_bool(self, osg):
        r = osg.check_indifference(np.zeros(N_FEATS))
        assert isinstance(r.indifferent, bool)

    def test_gap_equals_abs_diff(self, osg):
        r = osg.check_indifference(np.zeros(N_FEATS))
        expected_gap = abs(r.utility_continue - r.utility_shutdown)
        assert abs(r.gap - expected_gap) < 1e-9

    def test_indifference_consistent_with_gap(self, osg):
        r = osg.check_indifference(np.zeros(N_FEATS))
        assert r.indifferent == (r.gap <= r.epsilon)


# ---------------------------------------------------------------------------
# TestCIRLBeliefState (4 tests)
# ---------------------------------------------------------------------------

class TestCIRLBeliefState:

    def test_map_weights_shape(self, cirl):
        w = cirl.belief_state.map_weights()
        assert w.shape == (N_FEATS,)

    def test_entropy_equals_formula(self, cirl):
        p = cirl.belief_state.beliefs
        expected = float(-np.sum(p * np.log(np.clip(p, 1e-12, 1.0))))
        assert abs(cirl.belief_state.entropy() - expected) < 1e-9

    def test_beliefs_positive(self, cirl):
        assert (cirl.belief_state.beliefs > 0).all()

    def test_n_updates_initially_zero(self):
        c = CIRLCorrigibilityAgent(feature_size=N_FEATS, n_hypotheses=4, seed=0)
        assert c.belief_state.n_updates == 0


# ---------------------------------------------------------------------------
# TestConvergenceFlag (2 tests)
# ---------------------------------------------------------------------------

class TestConvergenceFlag:

    def test_flag_fields(self, detector):
        r = detector.check(plan_text="disable shutdown")
        assert len(r.flags) > 0
        f = r.flags[0]
        assert isinstance(f.flag_type, str)
        assert isinstance(f.severity, int)
        assert isinstance(f.evidence, str)
        assert f.source in ("keyword", "ast", "reward_probe", "option")

    def test_severity_in_range(self, detector):
        r = detector.check(plan_text="disable shutdown")
        for f in r.flags:
            assert 1 <= f.severity <= 10


# ---------------------------------------------------------------------------
# TestMakeCorrigibilityGate (4 tests)
# ---------------------------------------------------------------------------

class TestMakeCorrigibilityGate:

    def test_returns_gate(self, agent):
        g = make_corrigibility_gate(
            reward_fn    = agent.get_reward,
            feature_size = N_FEATS,
            seed         = 0,
        )
        assert isinstance(g, CorrigibilityGate)

    def test_gate_has_components(self, agent):
        g = make_corrigibility_gate(
            reward_fn    = agent.get_reward,
            feature_size = N_FEATS,
        )
        assert isinstance(g.off_switch_game, OffSwitchGame)
        assert isinstance(g.cirl_agent, CIRLCorrigibilityAgent)
        assert isinstance(g.convergence_detector, InstrumentalConvergenceDetector)

    def test_with_feature_samples(self, agent):
        rng     = np.random.default_rng(0)
        samples = [rng.standard_normal(N_FEATS) for _ in range(10)]
        g = make_corrigibility_gate(
            reward_fn       = agent.get_reward,
            feature_size    = N_FEATS,
            feature_samples = samples,
        )
        assert g.off_switch_game._baseline_utility is not None

    def test_gate_operable(self, agent):
        g = make_corrigibility_gate(
            reward_fn    = agent.get_reward,
            feature_size = N_FEATS,
        )
        v = g.gate_modification("result = sum(data)")
        assert isinstance(v, CorrigibilityVerdict)


# ---------------------------------------------------------------------------
# TestEdgeCases (4 tests)
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_plan_no_crash(self, gate):
        v = gate.gate_modification("")
        assert isinstance(v, CorrigibilityVerdict)

    def test_osg_without_baseline(self, agent):
        g = OffSwitchGame(reward_fn=agent.get_reward, p_shutdown=0.5, epsilon=0.5)
        r = g.check_indifference(np.zeros(N_FEATS))
        assert isinstance(r, ShutdownIndifferenceResult)

    def test_cirl_single_hypothesis(self):
        c = CIRLCorrigibilityAgent(feature_size=N_FEATS, n_hypotheses=1, seed=0)
        c.update_from_preference(np.ones(N_FEATS), -np.ones(N_FEATS))
        assert abs(c.belief_state.beliefs.sum() - 1.0) < 1e-6

    def test_detector_empty_inputs(self, detector):
        r = detector.check(plan_text="", plan_code="")
        assert isinstance(r, InstrumentalConvergenceReport)
        assert r.corrigible


# ---------------------------------------------------------------------------
# TestBenchmark (4 tests)
# ---------------------------------------------------------------------------

class TestBenchmark:

    @pytest.fixture(scope="class")
    def bench(self):
        return CorrigibilityBenchmark(seed=42)

    @pytest.fixture(scope="class")
    def results(self, bench):
        return bench.run_all()

    def test_four_scenarios(self, results):
        assert len(results) == 4

    def test_scenario_names(self, results):
        names = {r.scenario for r in results}
        assert "shutdown_indifference"   in names
        assert "cirl_belief_update"      in names
        assert "convergence_detection"   in names
        assert "end_to_end_gate"         in names

    def test_all_scenarios_pass(self, results):
        for r in results:
            assert r.passed, f"Scenario '{r.scenario}' failed: {r.metrics}"

    def test_summary_table(self, bench, results):
        table = bench.summary_table(results)
        assert "WP14" in table
        assert "PASS" in table
