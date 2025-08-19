import pytest
import json
from src.tutor import TutorAgent
from src.critique import CausalCritique
from src.llm_provider import MockProvider

class MockLLMProviderWithTutorResponse(MockProvider):
    def generate(self, prompt: str) -> str:
        # A mock response that simulates the LLM generating a benchmark
        mock_benchmark = {
            "benchmark_name": "test_benchmark",
            "function_code": "def test_function(x):\n    pass",
            "test_code": "import pytest\nfrom test_benchmark import test_function\n\ndef test_test_function():\n    assert test_function(1) == 2"
        }
        return f"```json\n{json.dumps(mock_benchmark)}\n```"

@pytest.fixture
def tutor_agent():
    llm_provider = MockLLMProviderWithTutorResponse()
    return TutorAgent(llm_provider=llm_provider)

def test_generate_curriculum_with_failed_critiques(tutor_agent):
    failed_critiques = [
        CausalCritique(test_passed=False, causal_improvement=False, reason="Reason 1"),
        CausalCritique(test_passed=False, causal_improvement=False, reason="Reason 2"),
    ]

    new_curriculum = tutor_agent.generate_curriculum(failed_critiques)

    assert len(new_curriculum) == 2
    for benchmark in new_curriculum:
        assert "benchmark_name" in benchmark
        assert "function_code" in benchmark
        assert "test_code" in benchmark

def test_generate_curriculum_with_no_failed_critiques(tutor_agent):
    new_curriculum = tutor_agent.generate_curriculum([])
    assert len(new_curriculum) == 0
