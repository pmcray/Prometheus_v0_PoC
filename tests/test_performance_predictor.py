import pytest
from src.performance_predictor import PerformancePredictorAgent

@pytest.fixture
def predictor():
    return PerformancePredictorAgent()

def test_predict_performance_loop(predictor):
    code_snippet = "use a for loop"
    score = predictor.predict_performance(code_snippet)
    assert score > 100

def test_predict_performance_recursion(predictor):
    code_snippet = "def factorial(n): return n * factorial(n-1)"
    score = predictor.predict_performance(code_snippet)
    assert score > 100

def test_predict_performance_optimized(predictor):
    code_snippet = "sorted([1, 2, 3])"
    score = predictor.predict_performance(code_snippet)
    assert score < 100
