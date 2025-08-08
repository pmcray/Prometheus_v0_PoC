import abc
import os
import logging
import json
from urllib import request

import google.generativeai as genai

class LLMProvider(abc.ABC):
    @abc.abstractmethod
    def generate(self, prompt: str) -> str:
        """Generates text based on a prompt."""
        pass

class GoogleGeminiProvider(LLMProvider):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Google Gemini API key is required.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        logging.info("Using GoogleGeminiProvider.")

    def generate(self, prompt: str) -> str:
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logging.error(f"Google Gemini API call failed: {e}")
            return ""

class OllamaPhi3Provider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "phi3"):
        self.base_url = base_url
        self.model = model
        self.api_url = f"{self.base_url}/api/generate"
        logging.info(f"Using OllamaPhi3Provider with model {self.model} at {self.base_url}")

    def generate(self, prompt: str) -> str:
        try:
            data = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            req = request.Request(self.api_url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with request.urlopen(req) as response:
                body = json.loads(response.read().decode('utf-8'))
                return body.get("response", "")
        except Exception as e:
            logging.error(f"Ollama API call failed: {e}")
            return ""

class MockProvider(LLMProvider):
    def __init__(self):
        self.mock_benchmark_count = 0
        self.canned_responses = {
            "reverse_string": "def reverse_string(s):\n    return s[::-1]",
            "sort_list_of_tuples": "def sort_list_of_tuples(data):\n    return sorted(data, key=lambda x: x[1])"
        }
        self.canned_benchmarks = [
            {
                "name": "reverse_string",
                "func": "def reverse_string(s):\n    # inefficient reversal\n    r = ''\n    for i in range(len(s) - 1, -1, -1):\n        r += s[i]\n    return r",
                "test": "import pytest\nfrom reverse_string import reverse_string\n\ndef test_reverse_string():\n    assert reverse_string('hello') == 'olleh'\n\ndef test_reverse_empty():\n    assert reverse_string('') == ''"
            },
            {
                "name": "sort_list_of_tuples",
                "func": "def sort_list_of_tuples(data):\n    # inefficient sort\n    n = len(data)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if data[j][1] > data[j+1][1]:\n                data[j], data[j+1] = data[j+1], data[j]\n    return data",
                "test": "import pytest\nfrom sort_list_of_tuples import sort_list_of_tuples\n\ndef test_sort_tuples():\n    assert sort_list_of_tuples([(1, 2), (3, 1), (5, 4)]) == [(3, 1), (1, 2), (5, 4)]"
            }
        ]
        logging.info("Using MockProvider.")

    def generate(self, prompt: str) -> str:
        # This mock needs to handle calls from both the Coder and Curriculum agents.
        # The logic is brittle and based on string matching the prompt.

        # --- CurriculumAgent prompts ---
        if "propose a new, related coding challenge" in prompt:
            # This is a curriculum agent call to generate a new topic.
            if "reverse_string" in prompt:
                return "a function that sorts a list of tuples by their second element"
            else:
                return "a function that finds the median of a list"

        elif "Write a single Python function" in prompt:
            # This is a curriculum agent call to generate a function body.
            if "reverses a string" in prompt:
                 return f"```python\n{self.canned_benchmarks[0]['func']}\n```"
            elif "sorts a list of tuples" in prompt:
                 return f"```python\n{self.canned_benchmarks[1]['func']}\n```"
            else: # Default fallback
                 return f"```python\ndef placeholder_function():\n    pass\n```"

        elif "Write a pytest test file" in prompt:
            # This is a curriculum agent call to generate a test file.
            if "reverse_string" in prompt:
                 return f"```python\n{self.canned_benchmarks[0]['test']}\n```"
            elif "sort_list_of_tuples" in prompt:
                 return f"```python\n{self.canned_benchmarks[1]['test']}\n```"
            else: # Default fallback
                return f"```python\nimport pytest\ndef test_placeholder():\n    assert True\n```"

        # --- CoderAgent prompts ---
        elif "Refactor this code" in prompt:
            # This is a coder agent call to refactor.
            if "reverse_string" in prompt:
                return f"```python\n{self.canned_responses['reverse_string']}\n```"
            if "sort_list_of_tuples" in prompt:
                return f"```python\n{self.canned_responses['sort_list_of_tuples']}\n```"

            # Default fallback refactoring
            return "```python\n# Mock refactoring by Jules\n```"

        logging.warning(f"MockProvider received an unhandled prompt: {prompt[:100]}...")
        return "# Mock response"
