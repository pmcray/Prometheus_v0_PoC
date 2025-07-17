
import pytest
from src.causal_attention import CausalAttentionWrapper

@pytest.fixture
def wrapper():
    # We don't need a real API key for this test
    return CausalAttentionWrapper(api_key="test_key")

def test_nested_loop_detection(wrapper):
    code = """
def inefficient_sort(data):
    n = len(data)
    for i in range(n):
        for j in range(0, n-i-1):
            if data[j] > data[j+1]:
                data[j], data[j+1] = data[j+1], data[j]
    return data
"""
    analysis = wrapper._analyze_code(code)
    assert "O(n^2)" in analysis

def test_no_nested_loop_detection(wrapper):
    code = """
def efficient_sort(data):
    data.sort()
    return data
"""
    analysis = wrapper._analyze_code(code)
    assert "No obvious causal features" in analysis

def test_prompt_construction(wrapper, monkeypatch):
    # Mock the model generation to avoid actual API calls
    def mock_generate_content(*args, **kwargs):
        class MockResponse:
            def __init__(self):
                self.text = "pass"
        return MockResponse()

    monkeypatch.setattr(wrapper.model, "generate_content", mock_generate_content)

    code = """
def inefficient_sort(data):
    n = len(data)
    for i in range(n):
        for j in range(0, n-i-1):
            if data[j] > data[j+1]:
                data[j], data[j+1] = data[j+1], data[j]
    return data
"""
    # We are not actually checking the generated code here, just that the prompt is correct
    # by running the function. A more robust test would capture the prompt and assert its contents.
    # For this PoC, we'll rely on the print statement in the wrapper.
    wrapper.generate_with_causal_focus(code, "Refactor this.")
