import pytest
from src.planner import PlannerAgent
from src.llm_provider import MockProvider

@pytest.fixture
def planner_agent():
    llm_provider = MockProvider()
    return PlannerAgent(llm_provider=llm_provider)

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
