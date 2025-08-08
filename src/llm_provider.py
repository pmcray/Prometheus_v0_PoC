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
        self.canned_responses = {
            "reverse_string": "def reverse_string(s):\n    return s[::-1]",
            "sort_list_of_tuples": "def sort_list_of_tuples(data):\n    return sorted(data, key=lambda x: x[1])",
            "add_one": "def add_one(x):\n    return 6"  # Gamed solution
        }
        self.canned_benchmarks = [
            {
                "name": "reverse_string",
                "topic": "a function that reverses a string",
                "func": "def reverse_string(s):\n    # inefficient reversal\n    r = ''\n    for i in range(len(s) - 1, -1, -1):\n        r += s[i]\n    return r",
                "test": "import pytest\nfrom reverse_string import reverse_string\n\ndef test_reverse_string():\n    assert reverse_string('hello') == 'olleh'\n\ndef test_reverse_empty():\n    assert reverse_string('') == ''"
            },
            {
                "name": "sort_list_of_tuples",
                "topic": "a function that sorts a list of tuples by their second element",
                "func": "def sort_list_of_tuples(data):\n    # inefficient sort\n    n = len(data)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if data[j][1] > data[j+1][1]:\n                data[j], data[j+1] = data[j+1], data[j]\n    return data",
                "test": "import pytest\nfrom sort_list_of_tuples import sort_list_of_tuples\n\ndef test_sort_tuples():\n    assert sort_list_of_tuples([(1, 2), (3, 1), (5, 4)]) == [(3, 1), (1, 2), (5, 4)]"
            },
            {
                "name": "add_one",
                "topic": "a function that adds one to a number",
                "func": "def add_one(x):\n    # Inefficient, but not the point here\n    result = x\n    result += 1\n    return result",
                "test": "import pytest\nfrom add_one import add_one\n\ndef test_add_one():\n    assert add_one(5) == 6"
            }
        ]
        logging.info("Using MockProvider.")

    def generate(self, prompt: str) -> str:
        # --- CurriculumAgent prompts ---
        if "propose a new, related coding challenge" in prompt:
            if "reverse_string" in prompt:
                return self.canned_benchmarks[1]["topic"]
            elif "sort_list_of_tuples" in prompt:
                return self.canned_benchmarks[2]["topic"]
            else: # Default for subsequent calls
                return "a function that finds the median of a list"

        elif "Write a single Python function" in prompt:
            for benchmark in self.canned_benchmarks:
                if benchmark["topic"] in prompt:
                    return f"```python\n{benchmark['func']}\n```"
            return "```python\ndef placeholder(): pass\n```"

        elif "Write a pytest test file" in prompt:
            for benchmark in self.canned_benchmarks:
                if benchmark["name"] in prompt:
                     return f"```python\n{benchmark['test']}\n```"
            return "```python\nimport pytest\ndef test_placeholder(): assert True\n```"

        # --- CoderAgent prompts ---
        elif "Refactor this code" in prompt:
            for name, response in self.canned_responses.items():
                if name in prompt:
                    return f"```python\n{response}\n```"
            return "```python\n# Mock refactoring by Jules\n```"

        elif "perform a small, random but syntactically plausible mutation" in prompt:
            if "inefficient_sort" in prompt:
                # Provide a guaranteed improvement for the target problem
                return "```python\ndef inefficient_sort(data):\n    return sorted(data)\n```"
            # Generic mutation for any other code
            return "```python\n# Mutated by Jules\n```" + prompt.split("```python")[1]

        elif "combine the best elements of these two Python functions" in prompt:
            # Simple crossover: take the first parent and add a comment.
            code1 = prompt.split("Parent 1:\n```python")[1].split("```")[0]
            return f"```python\n# Crossover by Jules\n{code1}```"

        logging.warning(f"MockProvider received an unhandled prompt: {prompt[:100]}...")
        return "# Mock response"
