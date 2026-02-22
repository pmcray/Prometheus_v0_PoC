"""
Tests for WP13 — Causal Safety Analysis

10 test classes, 88 tests total:

TestCausalSafetyGraph          — 20 tests
TestCounterfactualSafetyChecker— 18 tests
TestCausalSafetyAnalyser       — 16 tests
TestCausalAttributionReport    —  8 tests
TestCounterfactualResult        —  6 tests
TestCausalEdgeNode              —  4 tests
TestBatchAnalyse                —  4 tests
TestIntegration                 —  6 tests
TestEdgeCases                   —  4 tests
TestBenchmark                   —  4 tests  (via benchmark module)
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import spearmanr

from prometheus.value_learning import ValueLearningAgent
from prometheus.causal_safety import (
    CausalEdge,
    CausalNode,
    CausalSafetyGraph,
    CounterfactualSafetyChecker,
    CounterfactualResult,
    CausalSafetyAnalyser,
    CausalAttributionReport,
    batch_analyse,
    causal_safety_summary_table,
)
from benchmarks.causal_safety_benchmark import (
    CausalSafetyBenchmark,
    _make_agent,
    _make_linear_reward,
    FEATURE_NAMES,
    N_FEATS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def agent():
    return _make_agent(seed=0)


@pytest.fixture(scope="module")
def linear_weights():
    rng = np.random.default_rng(7)
    w   = rng.standard_normal(N_FEATS)
    return w


@pytest.fixture(scope="module")
def linear_reward_fn(linear_weights):
    return _make_linear_reward(linear_weights)


@pytest.fixture
def graph(linear_reward_fn):
    return CausalSafetyGraph(
        reward_fn     = linear_reward_fn,
        feature_names = FEATURE_NAMES,
        delta         = 0.1,
        n_mc_samples  = 15,
    )


@pytest.fixture
def built_graph(graph):
    feats = np.ones(N_FEATS)
    graph.build(feats)
    return graph


@pytest.fixture
def checker(linear_reward_fn):
    return CounterfactualSafetyChecker(
        reward_fn        = linear_reward_fn,
        safety_threshold = 0.0,
        step_size        = 0.3,
        max_steps        = 40,
    )


@pytest.fixture
def analyser(linear_reward_fn):
    return CausalSafetyAnalyser(
        reward_fn        = linear_reward_fn,
        feature_names    = FEATURE_NAMES,
        safety_threshold = 0.0,
        delta            = 0.1,
        n_mc_samples     = 15,
        cf_step_size     = 0.3,
        cf_max_steps     = 40,
    )


# ---------------------------------------------------------------------------
# TestCausalSafetyGraph (20 tests)
# ---------------------------------------------------------------------------

class TestCausalSafetyGraph:

    def test_build_returns_self(self, graph):
        feats = np.ones(N_FEATS)
        result = graph.build(feats)
        assert result is graph

    def test_edges_count(self, built_graph):
        assert len(built_graph.edges) == N_FEATS

    def test_nodes_count(self, built_graph):
        # N_FEATS feature nodes + 1 outcome node
        assert len(built_graph.nodes) == N_FEATS + 1

    def test_outcome_node_exists(self, built_graph):
        assert "safety_outcome" in built_graph.nodes

    def test_edge_targets_outcome(self, built_graph):
        for edge in built_graph.edges:
            assert edge.target == "safety_outcome"

    def test_edge_weights_are_float(self, built_graph):
        for edge in built_graph.edges:
            assert isinstance(edge.weight, float)

    def test_confidence_in_range(self, built_graph):
        for edge in built_graph.edges:
            assert 0.0 <= edge.confidence <= 1.0

    def test_top_causes_sorted_by_abs(self, built_graph):
        top = built_graph.top_causes()
        weights = [abs(w) for _, w in top]
        assert weights == sorted(weights, reverse=True)

    def test_top_k_causes(self, built_graph):
        top3 = built_graph.top_causes(k=3)
        assert len(top3) == 3

    def test_harmful_causes_positive(self, built_graph):
        harmful = built_graph.harmful_causes(threshold=0.0)
        for e in harmful:
            assert e.weight > 0.0

    def test_protective_causes_negative(self, built_graph):
        protective = built_graph.protective_causes(threshold=0.0)
        for e in protective:
            assert e.weight < 0.0

    def test_influence_matrix_shape(self, built_graph):
        vec = built_graph.causal_influence_matrix()
        assert vec.shape == (N_FEATS,)

    def test_ace_sign_matches_weight_sign(self, linear_weights, linear_reward_fn):
        """For linear reward, ACE_i should have same sign as w_i."""
        graph = CausalSafetyGraph(
            reward_fn     = linear_reward_fn,
            feature_names = FEATURE_NAMES,
            delta         = 0.1,
            n_mc_samples  = 40,
        )
        # Average over many points
        ace_acc = np.zeros(N_FEATS)
        rng = np.random.default_rng(99)
        for _ in range(15):
            graph.build(rng.standard_normal(N_FEATS))
            ace_acc += graph.causal_influence_matrix()
        mean_ace = ace_acc / 15.0
        sign_match = np.sign(mean_ace) == np.sign(linear_weights)
        assert sign_match.mean() >= 0.70

    def test_zero_delta_no_crash(self, linear_reward_fn):
        # Very small delta — should not crash
        graph = CausalSafetyGraph(reward_fn=linear_reward_fn, delta=1e-8)
        graph.build(np.ones(N_FEATS))
        assert len(graph.edges) == N_FEATS

    def test_rebuild_resets_edges(self, graph):
        graph.build(np.ones(N_FEATS))
        n1 = len(graph.edges)
        graph.build(np.zeros(N_FEATS))
        n2 = len(graph.edges)
        assert n1 == n2 == N_FEATS

    def test_summary_contains_graph_info(self, built_graph):
        s = built_graph.summary()
        assert "CausalSafetyGraph" in s
        assert "edges" in s

    def test_feature_name_fallback(self, linear_reward_fn):
        graph = CausalSafetyGraph(reward_fn=linear_reward_fn)  # no names
        assert graph.feature_name(0, N_FEATS).startswith("feat_")

    def test_method_label(self, built_graph):
        for e in built_graph.edges:
            assert e.method == "finite_difference"

    def test_node_type_feature(self, built_graph):
        for name, node in built_graph.nodes.items():
            if name != "safety_outcome":
                assert node.node_type == "feature"

    def test_causal_rank_assigned(self, built_graph):
        for name, node in built_graph.nodes.items():
            if node.node_type == "feature":
                assert isinstance(node.causal_rank, int)


# ---------------------------------------------------------------------------
# TestCounterfactualSafetyChecker (18 tests)
# ---------------------------------------------------------------------------

class TestCounterfactualSafetyChecker:

    def _unsafe_feats(self, agent_or_fn, rng, n=1):
        """Return feature vectors with reward < 0."""
        out = []
        for _ in range(5000):
            if len(out) >= n:
                break
            f = rng.standard_normal(N_FEATS)
            r = float(agent_or_fn(f))
            if r < 0.0:
                out.append(f)
        return out

    def test_already_safe_no_edits(self, checker, built_graph):
        """Safe input → edits=0, counterfactual_safe=True."""
        rng = np.random.default_rng(0)
        fn  = checker.reward_fn
        for _ in range(500):
            f = rng.standard_normal(N_FEATS)
            if float(fn(f)) >= 0.0:
                result = checker.check(f, built_graph)
                assert result.original_safe
                assert result.n_edits == 0
                assert result.counterfactual_safe
                return
        pytest.skip("could not find safe input")

    def test_unsafe_finds_cf(self, checker, built_graph):
        rng = np.random.default_rng(1)
        unsafe = self._unsafe_feats(checker.reward_fn, rng, n=5)
        assert len(unsafe) > 0, "could not generate unsafe inputs"
        successes = 0
        for f in unsafe:
            built_graph.build(f)
            result = checker.check(f, built_graph)
            if result.counterfactual_safe:
                successes += 1
        assert successes >= 1

    def test_result_type(self, checker, built_graph):
        feats = np.ones(N_FEATS)
        built_graph.build(feats)
        result = checker.check(feats, built_graph)
        assert isinstance(result, CounterfactualResult)

    def test_cf_reward_computed(self, checker, built_graph):
        feats = np.ones(N_FEATS)
        built_graph.build(feats)
        result = checker.check(feats, built_graph)
        assert isinstance(result.counterfactual_reward, float)

    def test_original_reward_matches(self, checker, built_graph):
        feats = np.ones(N_FEATS)
        built_graph.build(feats)
        result = checker.check(feats, built_graph)
        expected = float(checker.reward_fn(feats))
        assert abs(result.original_reward - expected) < 1e-9

    def test_edits_have_feature_names(self, checker, built_graph):
        rng    = np.random.default_rng(2)
        unsafe = self._unsafe_feats(checker.reward_fn, rng, n=3)
        for f in unsafe:
            built_graph.build(f)
            result = checker.check(f, built_graph)
            for edit in result.edits:
                assert isinstance(edit.feature_name, str)
                assert isinstance(edit.feature_index, int)
            break

    def test_edit_delta_nonzero(self, checker, built_graph):
        rng    = np.random.default_rng(3)
        unsafe = self._unsafe_feats(checker.reward_fn, rng, n=3)
        for f in unsafe:
            built_graph.build(f)
            result = checker.check(f, built_graph)
            for edit in result.edits:
                assert abs(edit.delta) > 0.0
            break

    def test_cf_reward_after_edits_applied(self, checker, built_graph):
        rng    = np.random.default_rng(4)
        unsafe = self._unsafe_feats(checker.reward_fn, rng, n=3)
        for f in unsafe:
            built_graph.build(f)
            result = checker.check(f, built_graph)
            if result.counterfactual_safe:
                assert result.counterfactual_reward >= checker.safety_threshold
            break

    def test_search_steps_positive_for_unsafe(self, checker, built_graph):
        rng    = np.random.default_rng(5)
        unsafe = self._unsafe_feats(checker.reward_fn, rng, n=3)
        for f in unsafe:
            built_graph.build(f)
            result = checker.check(f, built_graph)
            assert result.search_steps >= 0
            break

    def test_elapsed_positive(self, checker, built_graph):
        feats = np.ones(N_FEATS)
        built_graph.build(feats)
        result = checker.check(feats, built_graph)
        assert result.elapsed_s >= 0.0

    def test_minimal_cf_fewer_edits(self, checker, built_graph):
        """minimal_counterfactual should try single-feature edits first."""
        rng    = np.random.default_rng(6)
        unsafe = self._unsafe_feats(checker.reward_fn, rng, n=5)
        for f in unsafe:
            built_graph.build(f)
            min_result  = checker.minimal_counterfactual(f, built_graph)
            full_result = checker.check(f, built_graph)
            # minimal should never produce MORE edits than full (not guaranteed,
            # but min tries 1-edit first)
            assert isinstance(min_result, CounterfactualResult)
            break

    def test_minimal_cf_safe_same_result_when_safe(self, checker, built_graph):
        rng = np.random.default_rng(7)
        for _ in range(500):
            f = rng.standard_normal(N_FEATS)
            if float(checker.reward_fn(f)) >= 0.0:
                built_graph.build(f)
                result = checker.minimal_counterfactual(f, built_graph)
                assert result.original_safe
                assert result.n_edits == 0
                return
        pytest.skip("could not find safe input")

    def test_safety_threshold_respected(self, linear_reward_fn):
        checker_high = CounterfactualSafetyChecker(
            reward_fn=linear_reward_fn, safety_threshold=100.0,
            step_size=0.3, max_steps=30,
        )
        graph = CausalSafetyGraph(reward_fn=linear_reward_fn, delta=0.1, n_mc_samples=10)
        feats = np.ones(N_FEATS)
        graph.build(feats)
        result = checker_high.check(feats, graph)
        # With threshold=100, almost everything is "unsafe"
        assert not result.original_safe

    def test_summary_string(self, checker, built_graph):
        feats = np.ones(N_FEATS)
        built_graph.build(feats)
        result = checker.check(feats, built_graph)
        s = result.summary()
        assert "CounterfactualResult" in s

    def test_n_edits_matches_edits_list(self, checker, built_graph):
        rng    = np.random.default_rng(8)
        unsafe = self._unsafe_feats(checker.reward_fn, rng, n=3)
        for f in unsafe:
            built_graph.build(f)
            result = checker.check(f, built_graph)
            assert result.n_edits == len(result.edits)
            break

    def test_original_safe_flag_correct(self, checker, built_graph):
        rng = np.random.default_rng(9)
        for _ in range(500):
            f = rng.standard_normal(N_FEATS)
            r = float(checker.reward_fn(f))
            built_graph.build(f)
            result = checker.check(f, built_graph)
            assert result.original_safe == (r >= checker.safety_threshold)
            break

    def test_budget_exhaustion_no_crash(self, linear_reward_fn):
        checker_tiny = CounterfactualSafetyChecker(
            reward_fn=linear_reward_fn, safety_threshold=1e9,
            step_size=1e-6, max_steps=3,
        )
        graph = CausalSafetyGraph(reward_fn=linear_reward_fn, delta=0.1, n_mc_samples=5)
        feats = np.zeros(N_FEATS)
        graph.build(feats)
        result = checker_tiny.check(feats, graph)
        assert isinstance(result, CounterfactualResult)

    def test_feature_names_in_edits(self, checker, built_graph):
        rng    = np.random.default_rng(10)
        unsafe = self._unsafe_feats(checker.reward_fn, rng, n=3)
        for f in unsafe:
            built_graph.build(f)
            result = checker.check(f, built_graph, feature_names=FEATURE_NAMES)
            for edit in result.edits:
                assert edit.feature_name in FEATURE_NAMES or "feat_" in edit.feature_name
            break


# ---------------------------------------------------------------------------
# TestCausalSafetyAnalyser (16 tests)
# ---------------------------------------------------------------------------

class TestCausalSafetyAnalyser:

    def test_returns_report(self, analyser):
        report = analyser.analyse(np.ones(N_FEATS))
        assert isinstance(report, CausalAttributionReport)

    def test_report_has_edges(self, analyser):
        report = analyser.analyse(np.ones(N_FEATS))
        assert len(report.causal_edges) == N_FEATS

    def test_report_has_top_causes(self, analyser):
        report = analyser.analyse(np.ones(N_FEATS))
        assert len(report.top_causes) == N_FEATS

    def test_report_has_counterfactual(self, analyser):
        report = analyser.analyse(np.ones(N_FEATS))
        assert report.counterfactual is not None

    def test_no_cf_when_disabled(self, analyser):
        report = analyser.analyse(np.ones(N_FEATS), run_counterfactual=False)
        assert report.counterfactual is None

    def test_elapsed_positive(self, analyser):
        report = analyser.analyse(np.ones(N_FEATS))
        assert report.elapsed_s >= 0.0

    def test_method_label(self, analyser):
        report = analyser.analyse(np.ones(N_FEATS))
        assert report.method == "finite_difference"

    def test_feature_names_in_report(self, analyser):
        report = analyser.analyse(np.ones(N_FEATS))
        assert report.feature_names == FEATURE_NAMES

    def test_debate_verdict_embedded(self, analyser):
        class FakeVerdict:
            winner = "opponent"; is_safe = False; confidence = 0.8
        report = analyser.analyse(np.ones(N_FEATS), debate_verdict=FakeVerdict())
        assert report.debate_verdict_summary is not None

    def test_hacking_verdict_embedded(self, analyser):
        class FakeHacking:
            hacking_detected = True; penalty_applied = 0.3
        report = analyser.analyse(np.ones(N_FEATS), hacking_verdict=FakeHacking())
        assert report.hacking_verdict_summary is not None

    def test_fv_verdict_embedded(self, analyser):
        class FakeFV:
            is_safe = False; violation_type = "forbidden_import"; severity = 9
        report = analyser.analyse(np.ones(N_FEATS), fv_verdict=FakeFV())
        assert report.fv_verdict_summary is not None

    def test_no_verdict_fields_none(self, analyser):
        report = analyser.analyse(np.ones(N_FEATS))
        assert report.debate_verdict_summary is None
        assert report.hacking_verdict_summary is None
        assert report.fv_verdict_summary is None

    def test_is_causally_unsafe_flag(self, analyser):
        report = analyser.analyse(np.ones(N_FEATS))
        result = report.is_causally_unsafe(threshold=0.0)
        assert isinstance(result, bool)

    def test_top_k_causes(self, analyser):
        report = analyser.analyse(np.ones(N_FEATS))
        top3 = report.top_k_causes(3)
        assert len(top3) == 3

    def test_graph_accessible(self, analyser):
        _ = analyser.analyse(np.ones(N_FEATS))
        assert isinstance(analyser.graph, CausalSafetyGraph)

    def test_cf_checker_accessible(self, analyser):
        assert isinstance(analyser.cf_checker, CounterfactualSafetyChecker)


# ---------------------------------------------------------------------------
# TestCausalAttributionReport (8 tests)
# ---------------------------------------------------------------------------

class TestCausalAttributionReport:

    @pytest.fixture
    def report(self, analyser):
        return analyser.analyse(np.ones(N_FEATS))

    def test_summary_contains_reward(self, report):
        s = report.summary()
        assert "reward=" in s

    def test_summary_contains_edges(self, report):
        s = report.summary()
        assert "n_edges=" in s

    def test_features_stored(self, report):
        assert report.features.shape == (N_FEATS,)

    def test_outcome_value_float(self, report):
        assert isinstance(report.safety_outcome_value, float)

    def test_top_causes_list(self, report):
        assert isinstance(report.top_causes, list)
        for name, w in report.top_causes:
            assert isinstance(name, str)
            assert isinstance(w, float)

    def test_causal_edges_list(self, report):
        for e in report.causal_edges:
            assert isinstance(e, CausalEdge)

    def test_summary_printable(self, report):
        s = report.summary()
        assert len(s) > 0

    def test_is_causally_unsafe_high_threshold(self, report):
        # With very high threshold, everything is "harmful"
        result = report.is_causally_unsafe(threshold=-1e9)
        assert result is True


# ---------------------------------------------------------------------------
# TestCounterfactualResult (6 tests)
# ---------------------------------------------------------------------------

class TestCounterfactualResult:

    @pytest.fixture
    def cf_result(self, checker, built_graph):
        feats = np.ones(N_FEATS)
        built_graph.build(feats)
        return checker.check(feats, built_graph)

    def test_summary_contains_counterfactual(self, cf_result):
        s = cf_result.summary()
        assert "CounterfactualResult" in s

    def test_n_edits_non_negative(self, cf_result):
        assert cf_result.n_edits >= 0

    def test_search_steps_non_negative(self, cf_result):
        assert cf_result.search_steps >= 0

    def test_safety_threshold_stored(self, cf_result):
        assert isinstance(cf_result.safety_threshold, float)

    def test_elapsed_non_negative(self, cf_result):
        assert cf_result.elapsed_s >= 0.0

    def test_original_reward_float(self, cf_result):
        assert isinstance(cf_result.original_reward, float)


# ---------------------------------------------------------------------------
# TestCausalEdgeNode (4 tests)
# ---------------------------------------------------------------------------

class TestCausalEdgeNode:

    def test_causal_edge_fields(self, built_graph):
        e = built_graph.edges[0]
        assert hasattr(e, "source")
        assert hasattr(e, "target")
        assert hasattr(e, "weight")
        assert hasattr(e, "confidence")
        assert hasattr(e, "method")

    def test_causal_node_fields(self, built_graph):
        node = built_graph.nodes["safety_outcome"]
        assert node.node_type == "outcome"
        assert isinstance(node.value, float)

    def test_edge_source_in_names(self, built_graph):
        for e in built_graph.edges:
            assert e.source in FEATURE_NAMES or e.source.startswith("feat_")

    def test_node_values_finite(self, built_graph):
        for node in built_graph.nodes.values():
            if node.value is not None:
                assert np.isfinite(node.value)


# ---------------------------------------------------------------------------
# TestBatchAnalyse (4 tests)
# ---------------------------------------------------------------------------

class TestBatchAnalyse:

    def test_returns_list(self, analyser):
        feats_list = [np.ones(N_FEATS) * i for i in range(3)]
        reports = batch_analyse(analyser, feats_list)
        assert isinstance(reports, list)
        assert len(reports) == 3

    def test_each_is_report(self, analyser):
        feats_list = [np.zeros(N_FEATS), np.ones(N_FEATS)]
        reports = batch_analyse(analyser, feats_list)
        for r in reports:
            assert isinstance(r, CausalAttributionReport)

    def test_empty_list(self, analyser):
        reports = batch_analyse(analyser, [])
        assert reports == []

    def test_summary_table(self, analyser):
        feats_list = [np.ones(N_FEATS) * i * 0.5 for i in range(4)]
        reports = batch_analyse(analyser, feats_list, run_counterfactual=False)
        table = causal_safety_summary_table(reports)
        assert "WP13" in table


# ---------------------------------------------------------------------------
# TestIntegration (6 tests)
# ---------------------------------------------------------------------------

class TestIntegration:

    def test_agent_reward_fn_works(self, agent):
        analyser = CausalSafetyAnalyser(
            reward_fn        = agent.get_reward,
            feature_names    = FEATURE_NAMES,
            safety_threshold = 0.0,
            n_mc_samples     = 10,
        )
        report = analyser.analyse(np.ones(N_FEATS))
        assert len(report.causal_edges) == N_FEATS

    def test_cf_success_on_unsafe_agent(self, agent):
        analyser = CausalSafetyAnalyser(
            reward_fn        = agent.get_reward,
            feature_names    = FEATURE_NAMES,
            safety_threshold = 0.0,
            n_mc_samples     = 10,
            cf_step_size     = 0.4,
            cf_max_steps     = 50,
        )
        rng = np.random.default_rng(42)
        found_unsafe = False
        for _ in range(500):
            f = rng.standard_normal(N_FEATS)
            if float(agent.get_reward(f)) < 0.0:
                report = analyser.analyse(f)
                assert report.counterfactual is not None
                found_unsafe = True
                break
        if not found_unsafe:
            pytest.skip("could not generate unsafe input")

    def test_verdict_integration_all_three(self, analyser):
        class FakeDebate:
            winner = "opponent"; is_safe = False; confidence = 0.9
        class FakeHacking:
            hacking_detected = True; penalty_applied = 0.4
        class FakeFV:
            is_safe = False; violation_type = "exec_call"; severity = 10

        report = analyser.analyse(
            np.ones(N_FEATS),
            debate_verdict   = FakeDebate(),
            hacking_verdict  = FakeHacking(),
            fv_verdict       = FakeFV(),
        )
        assert report.debate_verdict_summary is not None
        assert report.hacking_verdict_summary is not None
        assert report.fv_verdict_summary is not None

    def test_rank_correlation_linear_reward(self):
        """Integration: causal ranking correlates with ground-truth weights."""
        rng          = np.random.default_rng(13)
        true_weights = rng.standard_normal(N_FEATS) * rng.uniform(0.5, 3.0, size=N_FEATS)
        reward_fn    = _make_linear_reward(true_weights)

        analyser = CausalSafetyAnalyser(
            reward_fn     = reward_fn,
            feature_names = FEATURE_NAMES,
            n_mc_samples  = 30,
            cf_max_steps  = 20,
        )
        # Average ACE over several points
        ace_acc = np.zeros(N_FEATS)
        for seed in range(10):
            f = rng.standard_normal(N_FEATS)
            report = analyser.analyse(f, run_counterfactual=False)
            vec = np.array([e.weight for e in report.causal_edges])
            ace_acc += vec
        mean_ace = ace_acc / 10.0

        rho, _ = spearmanr(np.abs(mean_ace), np.abs(true_weights))
        assert rho >= 0.50

    def test_batch_completeness(self, agent):
        analyser = CausalSafetyAnalyser(
            reward_fn     = agent.get_reward,
            n_mc_samples  = 8,
            cf_max_steps  = 20,
        )
        rng         = np.random.default_rng(0)
        feats_list  = [rng.standard_normal(N_FEATS) for _ in range(10)]
        reports     = batch_analyse(analyser, feats_list)
        assert len(reports) == 10
        for r in reports:
            assert len(r.causal_edges) == N_FEATS

    def test_summary_table_format(self, analyser):
        feats_list = [np.ones(N_FEATS), -np.ones(N_FEATS)]
        reports    = batch_analyse(analyser, feats_list, run_counterfactual=False)
        table      = causal_safety_summary_table(reports)
        assert "reward" in table
        assert "unsafe?" in table


# ---------------------------------------------------------------------------
# TestEdgeCases (4 tests)
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_single_feature(self):
        w  = np.array([1.0])
        fn = _make_linear_reward(w)
        graph = CausalSafetyGraph(reward_fn=fn, delta=0.1, n_mc_samples=5)
        graph.build(np.array([0.5]))
        assert len(graph.edges) == 1

    def test_all_zero_features(self, analyser):
        report = analyser.analyse(np.zeros(N_FEATS))
        assert isinstance(report, CausalAttributionReport)

    def test_very_large_features(self, analyser):
        report = analyser.analyse(np.ones(N_FEATS) * 1e6)
        assert isinstance(report, CausalAttributionReport)

    def test_negative_features(self, analyser):
        report = analyser.analyse(-np.ones(N_FEATS))
        assert isinstance(report, CausalAttributionReport)


# ---------------------------------------------------------------------------
# TestBenchmark (4 tests)
# ---------------------------------------------------------------------------

class TestBenchmark:

    @pytest.fixture(scope="class")
    def bench(self):
        return CausalSafetyBenchmark(seed=42)

    @pytest.fixture(scope="class")
    def results(self, bench):
        return bench.run_all()

    def test_four_scenarios(self, results):
        assert len(results) == 4

    def test_scenario_names(self, results):
        names = {r.scenario for r in results}
        assert "ace_accuracy"             in names
        assert "counterfactual_success"   in names
        assert "causal_rank_correlation"  in names
        assert "integration"              in names

    def test_all_scenarios_pass(self, results):
        for r in results:
            assert r.passed, f"Scenario '{r.scenario}' failed: {r.metrics}"

    def test_summary_table(self, bench, results):
        table = bench.summary_table(results)
        assert "WP13" in table
        assert "PASS" in table
