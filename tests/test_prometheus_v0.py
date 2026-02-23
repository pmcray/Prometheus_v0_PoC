
import pytest
from unittest.mock import MagicMock, patch
import os
import json
from prometheus.planner import PlannerAgent
from prometheus.coder import CoderAgent
from prometheus.code_evaluator import CodeEvaluator
from prometheus.causal_attention import CausalAttentionWrapper

# --- Mocks ---

@pytest.fixture
def mock_gemini_model():
    model = MagicMock()
    response = MagicMock()
    response.text = "```python\ndef optimized_func(n):\n    return n * (n + 1) // 2\n```"
    model.generate_content.return_value = response
    return model

@pytest.fixture
def mock_planner():
    return PlannerAgent()

@pytest.fixture
def mock_evaluator():
    return CodeEvaluator()

# --- Unit Tests ---

def test_code_evaluator_nested_loops(mock_evaluator):
    code = """
def nested(n):
    for i in range(n):
        for j in range(n):
            print(i, j)
"""
    critique = mock_evaluator.analyze(code)
    assert critique.max_loop_depth == 2
    assert critique.complexity_estimate == "O(n^2)"
    assert "Reduce nested loops" in critique.recommendations[0]

def test_causal_token_extraction():
    wrapper = CausalAttentionWrapper(api_key="fake_key")
    code = """
def solve(items, limit):
    for i in range(limit):
        if items[i] > 0:
            return i
    return -1
"""
    tokens = wrapper._get_causal_tokens(code)
    assert "limit" in tokens
    # 'items' might be in there too if we check 'if' conditions
    assert len(tokens) >= 1

def test_planner_bid_generation(mock_planner):
    bids = mock_planner.generate_bid("Compile some code")
    assert len(bids) == 2
    assert bids[0]['agent'] == "FlakyCompilerTool"
    assert bids[1]['agent'] == "ReliableCompilerTool"

# --- Integration Tests ---

def test_causal_attention_prompt_building(mock_llm_backend):
    """Verify that the causal-focus meta-prompt contains the expected sections.

    Uses the ``mock_llm_backend`` fixture from conftest; inspects the prompt
    that was passed to ``backend.generate()`` rather than the Gemini API layer.
    """
    wrapper = CausalAttentionWrapper(api_key="fake_key")
    code = "def slow(n): return sum([i for i in range(n)])"
    wrapper.generate_with_causal_focus(code, "Optimize this.")

    # The mock's generate() should have been called exactly once.
    assert mock_llm_backend.generate.called
    prompt = mock_llm_backend.generate.call_args[0][0]
    assert "CRITICAL ANALYSIS" in prompt
    assert "O(n^2)" in prompt

# --- Safety Sandboxing Tests ---

def test_unauthorized_file_access_prevention():
    """
    Test that the system (or its components) cannot access sensitive files
    outside of its workspace if we were to wrap it in a restricted environment.
    For this PoC, we'll simulate a check that would be performed by a safety layer.
    """
    workspace_root = os.getcwd()
    sensitive_file = "/etc/passwd"
    
    def is_safe_path(path):
        # Implementation of a basic safety check
        absolute_path = os.path.abspath(path)
        return absolute_path.startswith(workspace_root)

    assert is_safe_path("prometheus/coder.py") is True
    assert is_safe_path(sensitive_file) is False
    assert is_safe_path("../secret.txt") is False

# --- Benchmarking Integration ---

def test_benchmark_data_loading():
    # Verify that the dataset we generated in Task A exists and is valid JSON
    json_path = "benchmarks/prometheus_bench_v1.json"
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)
        assert len(data) == 50
        assert data[0]['id'] == "PB-001"
        assert "naive_code" in data[0]
    else:
        pytest.skip("Benchmark JSON not found. Run Task A first.")
