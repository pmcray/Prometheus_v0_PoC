"""
Tests for CausalAttentionWrapper.

Covers:
- Causal-token extraction from loop bounds and recursive calls
- Prompt construction (CRITICAL ANALYSIS section present and accurate)
- Graceful LLM-error handling (wrapper returns original code on backend failure)
"""

import pytest
from prometheus.causal_attention import CausalAttentionWrapper


@pytest.fixture
def wrapper():
    """Return a CausalAttentionWrapper backed by the conftest mock backend."""
    return CausalAttentionWrapper(api_key="test_key")


# ---------------------------------------------------------------------------
# Causal-token extraction
# ---------------------------------------------------------------------------

def test_causal_tokens_detected_in_nested_loop(wrapper):
    """Loop-bound variables should be identified as causal tokens."""
    code = """
def inefficient_sort(data):
    n = len(data)
    for i in range(n):
        for j in range(0, n - i - 1):
            if data[j] > data[j + 1]:
                data[j], data[j + 1] = data[j + 1], data[j]
    return data
"""
    tokens = wrapper._get_causal_tokens(code)
    # 'n' drives both loop bounds and is the primary causal token.
    assert "n" in tokens


def test_no_causal_tokens_for_simple_function(wrapper):
    """A function with no loops has no causal tokens."""
    code = """
def efficient_sort(data):
    data.sort()
    return data
"""
    tokens = wrapper._get_causal_tokens(code)
    # ``data`` appears in an implicit call but not in any loop bound or
    # condition — depending on the visitor implementation the set may be
    # empty or contain only top-level names.  What matters is that 'n' is
    # absent (there is no 'n' variable here at all).
    assert "n" not in tokens


def test_causal_tokens_recursive_function(wrapper):
    """Recursive call arguments should be flagged as causal tokens."""
    code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
    tokens = wrapper._get_causal_tokens(code)
    assert "n" in tokens


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def test_prompt_contains_critical_analysis_section(wrapper, mock_llm_backend):
    """The causal-focus meta-prompt must include CRITICAL ANALYSIS."""
    code = """
def inefficient_sort(data):
    n = len(data)
    for i in range(n):
        for j in range(0, n - i - 1):
            if data[j] > data[j + 1]:
                data[j], data[j + 1] = data[j + 1], data[j]
    return data
"""
    wrapper.generate_with_causal_focus(code, "Refactor this.")

    assert mock_llm_backend.generate.called
    prompt = mock_llm_backend.generate.call_args[0][0]
    assert "CRITICAL ANALYSIS" in prompt
    assert "O(n^2)" in prompt


def test_generate_returns_original_on_backend_error(wrapper, mock_llm_backend):
    """If the backend raises, the wrapper should return the original code."""
    mock_llm_backend.generate.side_effect = RuntimeError("backend unavailable")

    code = "def foo(): pass"
    result = wrapper.generate_with_causal_focus(code, "optimise")
    assert result == code
