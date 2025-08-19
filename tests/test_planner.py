import pytest
import json
from src.planner import PlannerAgent
from src.llm_provider import MockProvider
from src.performance_predictor import PerformancePredictorAgent

@pytest.fixture
def planner_agent():
    llm_provider = MockProvider()
    predictor = PerformancePredictorAgent()
    return PlannerAgent(llm_provider=llm_provider, predictor=predictor)

def test_plan_classification_loop(planner_agent):
    code_snippet = "for i in range(10): print(i)"
    goal = "refactor this code"
    plan = planner_agent.plan(code_snippet, goal)
    assert plan["task_classification"] == "LOOP_OPTIMIZATION"

def test_plan_classification_recursion(planner_agent):
    code_snippet = "def factorial(n): return n * factorial(n-1)"
    goal = "refactor this code"
    plan = planner_agent.plan(code_snippet, goal)
    assert plan["task_classification"] == "RECURSION_REFACTOR"

def test_plan_selects_best_strategy(planner_agent):
    # Mock the LLM to return specific strategies
    strategies = [
        "use a for loop", # Predictor will give this a high (bad) score
        "use a list comprehension" # Predictor will give this a lower (good) score
    ]

    # Mock the generate method to return our strategies
    def mock_generate(prompt):
        if "strategies" in prompt:
            return json.dumps({"strategies": strategies})
        # Fallback to original mock provider for classification
        return MockProvider().generate(prompt)

    planner_agent.llm_provider.generate = mock_generate

    code_snippet = "..."
    goal = "refactor this"
    plan = planner_agent.plan(code_snippet, goal)

    # The predictor penalizes "for loop", so "list comprehension" should be chosen
    assert "list comprehension" in plan["goal"]
