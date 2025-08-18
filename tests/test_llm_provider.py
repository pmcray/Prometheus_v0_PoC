import pytest
from unittest.mock import patch, MagicMock
from src.llm_provider import HuggingFaceGemmaProvider

@patch('src.llm_provider.AutoTokenizer.from_pretrained')
@patch('src.llm_provider.AutoModelForCausalLM.from_pretrained')
def test_hugging_face_gemma_provider_init(mock_model, mock_tokenizer):
    """Tests that the HuggingFaceGemmaProvider initializes correctly."""
    provider = HuggingFaceGemmaProvider()
    mock_tokenizer.assert_called_once_with("google/gemma-2b")
    mock_model.assert_called_once_with("google/gemma-2b")
    assert provider.model_name == "google/gemma-2b"

@patch('src.llm_provider.AutoTokenizer.from_pretrained')
@patch('src.llm_provider.AutoModelForCausalLM.from_pretrained')
def test_hugging_face_gemma_provider_generate(mock_model, mock_tokenizer):
    """Tests the generate method of HuggingFaceGemmaProvider."""
    # Arrange
    mock_tokenizer_instance = MagicMock()
    mock_tokenizer.return_value = mock_tokenizer_instance
    mock_tokenizer_instance.decode.return_value = "Generated text"

    mock_model_instance = MagicMock()
    mock_model.return_value = mock_model_instance

    provider = HuggingFaceGemmaProvider()

    # Act
    response = provider.generate("Test prompt")

    # Assert
    mock_tokenizer_instance.assert_called_with("Test prompt", return_tensors="pt")
    mock_model_instance.generate.assert_called_once()
    mock_tokenizer_instance.decode.assert_called_once()
    assert response == "Generated text"
