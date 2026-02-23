import pytest
from unittest.mock import patch, MagicMock
from prometheus.planner import PlannerAgent

@patch('google.generativeai.GenerativeModel')
def test_generate_hypotheses(mock_generative_model):
    """
    Tests that the generate_hypotheses method correctly processes the response from the LLM.
    """
    # Arrange
    mock_model_instance = MagicMock()
    mock_model_instance.generate_content.return_value = MagicMock(text="Hypothesis 1\nHypothesis 2\nHypothesis 3")
    mock_generative_model.return_value = mock_model_instance

    planner = PlannerAgent()
    goal = "Test Goal"

    # Act
    hypotheses = planner.generate_hypotheses(goal)

    # Assert
    assert len(hypotheses) == 3
    assert hypotheses[0] == "Hypothesis 1"
    assert hypotheses[1] == "Hypothesis 2"
    assert hypotheses[2] == "Hypothesis 3"
    mock_model_instance.generate_content.assert_called_once()
