import unittest
from unittest.mock import MagicMock, patch
import os
import tempfile

# Ensure the src directory is in the Python path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.coder import CoderAgent
from src.tools import CompilerTool, StaticAnalyzerTool, LeanTool

class TestCoderAgent(unittest.TestCase):

    def setUp(self):
        """Set up the test environment before each test."""
        self.mock_api_key = "test_api_key"
        self.mock_compiler = MagicMock(spec=CompilerTool)
        self.mock_analyzer = MagicMock(spec=StaticAnalyzerTool)
        self.mock_lean_tool = MagicMock(spec=LeanTool)

        # Patch the genai.configure and GenerativeModel
        self.patcher_configure = patch('google.generativeai.configure')
        self.patcher_model = patch('google.generativeai.GenerativeModel')
        self.mock_configure = self.patcher_configure.start()
        self.mock_model_constructor = self.patcher_model.start()

        self.coder_agent = CoderAgent(
            api_key=self.mock_api_key,
            compiler=self.mock_compiler,
            analyzer=self.mock_analyzer,
            lean_tool=self.mock_lean_tool
        )

    def tearDown(self):
        """Clean up the test environment after each test."""
        self.patcher_configure.stop()
        self.patcher_model.stop()

    def test_verify_code_success(self):
        """Test that _verify_code returns True for valid code."""
        # Arrange
        valid_code = "def main():\n    print('Hello, world!')"
        self.mock_compiler.use.return_value = None  # No compiler errors
        self.mock_analyzer.use.return_value = None  # No analyzer issues

        # Act
        result = self.coder_agent._verify_code(valid_code)

        # Assert
        self.assertTrue(result)
        self.mock_compiler.use.assert_called_once()
        self.mock_analyzer.use.assert_called_once()

        # Check that the temp file was created and then cleaned up
        temp_file_path = self.mock_compiler.use.call_args[0][0]
        self.assertFalse(os.path.exists(temp_file_path), "Temporary file was not cleaned up.")

    def test_verify_code_compiler_error(self):
        """Test that _verify_code returns False when the compiler fails."""
        # Arrange
        invalid_code = "def main():\n    print('Hello, world!'"
        self.mock_compiler.use.return_value = "SyntaxError: unexpected EOF while parsing"

        # Act
        result = self.coder_agent._verify_code(invalid_code)

        # Assert
        self.assertFalse(result)
        self.mock_compiler.use.assert_called_once()
        self.mock_analyzer.use.assert_not_called() # Analyzer should not be called if compiler fails

        # Check that the temp file was cleaned up
        temp_file_path = self.mock_compiler.use.call_args[0][0]
        self.assertFalse(os.path.exists(temp_file_path), "Temporary file was not cleaned up after compiler error.")

    def test_verify_code_analyzer_error(self):
        """Test that _verify_code returns False when the static analyzer finds issues."""
        # Arrange
        code_with_issues = "import os\ndef main():\n    x = 1"
        self.mock_compiler.use.return_value = None # Compiler succeeds
        self.mock_analyzer.use.return_value = "W0612: Unused variable 'x'"

        # Act
        result = self.coder_agent._verify_code(code_with_issues)

        # Assert
        self.assertFalse(result)
        self.mock_compiler.use.assert_called_once()
        self.mock_analyzer.use.assert_called_once()

        # Check that the temp file was cleaned up
        temp_file_path = self.mock_compiler.use.call_args[0][0]
        self.assertFalse(os.path.exists(temp_file_path), "Temporary file was not cleaned up after analyzer error.")

if __name__ == '__main__':
    unittest.main()