import pytest
from unittest.mock import patch, MagicMock
from src.coder import CoderAgent
from src.llm_provider import HuggingFaceGemmaProvider

@patch('src.coder.SFTTrainer')
def test_initiate_finetune(mock_sft_trainer):
    """
    Tests that the initiate_finetune method calls the SFTTrainer with the correct parameters.
    """
    # Arrange
    mock_llm_provider = MagicMock(spec=HuggingFaceGemmaProvider)
    mock_llm_provider.model = "mock_model"
    mock_llm_provider.tokenizer = "mock_tokenizer"

    # We need to mock the tools for the CoderAgent constructor
    mock_compiler = MagicMock()
    mock_analyzer = MagicMock()
    mock_lean_tool = MagicMock()

    coder = CoderAgent(
        llm_provider=mock_llm_provider,
        compiler=mock_compiler,
        analyzer=mock_analyzer,
        lean_tool=mock_lean_tool
    )

    dataset = ["example1", "example2"]
    adapter_path = "/tmp/test_adapter"

    mock_trainer_instance = MagicMock()
    mock_sft_trainer.return_value = mock_trainer_instance

    # Act
    result = coder.initiate_finetune(dataset, adapter_path)

    # Assert
    mock_sft_trainer.assert_called_once()
    mock_trainer_instance.train.assert_called_once()
    mock_trainer_instance.save_model.assert_called_with(adapter_path)
    assert result == adapter_path

def test_initiate_finetune_wrong_provider():
    """
    Tests that initiate_finetune returns None if the provider is not a HuggingFaceGemmaProvider.
    """
    # Arrange
    mock_llm_provider = MagicMock() # Not a HuggingFaceGemmaProvider

    mock_compiler = MagicMock()
    mock_analyzer = MagicMock()
    mock_lean_tool = MagicMock()

    coder = CoderAgent(
        llm_provider=mock_llm_provider,
        compiler=mock_compiler,
        analyzer=mock_analyzer,
        lean_tool=mock_lean_tool
    )

    # Act
    result = coder.initiate_finetune([], "/tmp/test_adapter")

    # Assert
    assert result is None
