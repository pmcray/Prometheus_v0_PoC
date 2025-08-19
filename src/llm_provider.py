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

    @abc.abstractmethod
    def load_adapter(self, adapter_path: str):
        """Loads a LoRA adapter."""
        pass

    @abc.abstractmethod
    def unload_adapter(self):
        """Unloads the current LoRA adapter."""
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

    def load_adapter(self, adapter_path: str):
        logging.warning("LoRA adapter loading is not implemented for GoogleGeminiProvider yet.")
        pass

    def unload_adapter(self):
        logging.warning("LoRA adapter unloading is not implemented for GoogleGeminiProvider yet.")
        pass

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

    def load_adapter(self, adapter_path: str):
        logging.warning("LoRA adapter loading is not implemented for OllamaPhi3Provider yet.")
        pass

    def unload_adapter(self):
        logging.warning("LoRA adapter unloading is not implemented for OllamaPhi3Provider yet.")
        pass

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

    def load_adapter(self, adapter_path: str):
        logging.info(f"MockProvider: 'Loading' LoRA adapter from {adapter_path}")
        pass

    def unload_adapter(self):
        logging.info("MockProvider: 'Unloading' LoRA adapter.")
        pass

    def generate(self, prompt: str) -> str:
        # --- Planner prompts ---
        if "Propose 3 distinct high-level strategies" in prompt:
            strategies = ["use a for loop", "use a list comprehension", "use recursion"]
            return json.dumps({"strategies": strategies})
        elif "classify the required refactoring task" in prompt:
            if "for i in range" in prompt:
                return "LOOP_OPTIMIZATION"
            elif "def factorial" in prompt:
                return "RECURSION_REFACTOR"
            else:
                return "GENERAL_REFACTORING"

        # --- CurriculumAgent prompts ---
        if "propose a new, related coding challenge" in prompt:
            # Always return the reverse_string topic to ensure we test the failure case
            return self.canned_benchmarks[0]["topic"]

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
            if "reverse_string" in prompt:
                # Intentionally provide a failing implementation to trigger the tutor
                return "```python\ndef reverse_string(s):\n    return s\n```"
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

        # --- Theorem Proving Prompts ---
        elif "Generate a simple theorem in the Lean language" in prompt:
            return "```lean\ntheorem add_zero (n : Nat) : n + 0 = n\n```"

        elif "write a proof for the following theorem" in prompt and "add_zero" in prompt:
            return "```lean\nby simp\n```"

        # --- EvaluatorAgent prompts ---
        elif "provide a confidence score and uncertainty level" in prompt:
            return '{"evaluation_confidence": 0.9, "uncertainty_level": "low"}'

        # --- TutorAgent prompts ---
        elif 'Based on the following reason for a programming failure' in prompt:
            mock_benchmark = {
                "benchmark_name": "tutor_generated_benchmark",
                "function_code": "def tutor_function(x):\n    pass",
                "test_code": "import pytest\nfrom tutor_generated_benchmark import tutor_function\n\ndef test_tutor_function():\n    assert tutor_function(1) == 1"
            }
            return f"```json\n{json.dumps(mock_benchmark)}\n```"

        logging.warning(f"MockProvider received an unhandled prompt: {prompt[:100]}...")
        return "# Mock response"
