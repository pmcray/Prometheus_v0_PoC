import pytest
from unittest.mock import patch, MagicMock
from prometheus.planner import PlannerAgent


def test_generate_hypotheses(mock_llm_backend):
    """
    Tests that the generate_hypotheses method correctly processes the response
    from the LLM backend.

    Uses the ``mock_llm_backend`` fixture from conftest so no real model is
    loaded.
    """
    # Arrange: have the mock return three newline-separated hypotheses.
    mock_llm_backend.generate.return_value = "Hypothesis 1\nHypothesis 2\nHypothesis 3"

    planner = PlannerAgent()
    goal = "Test Goal"

    # Act
    hypotheses = planner.generate_hypotheses(goal)

    # Assert
    assert len(hypotheses) == 3
    assert hypotheses[0] == "Hypothesis 1"
    assert hypotheses[1] == "Hypothesis 2"
    assert hypotheses[2] == "Hypothesis 3"
    mock_llm_backend.generate.assert_called_once()
