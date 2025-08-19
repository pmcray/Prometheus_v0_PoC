import logging
from typing import List, Dict, Any
from src.critique import CausalCritique
from src.llm_provider import LLMProvider
import json

class TutorAgent:
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
        logging.info("TutorAgent initialized.")

    def generate_curriculum(self, failed_critiques: List[CausalCritique], problem_class: str = None) -> List[Dict[str, Any]]:
        """
        Generates a new curriculum based on a list of failed critiques, optionally targeted to a specific problem class.
        """
        if not failed_critiques:
            return []

        logging.info(f"TutorAgent: Generating curriculum based on {len(failed_critiques)} failed critiques.")
        if problem_class:
            logging.info(f"TutorAgent: Targeting problem class '{problem_class}'.")

        failure_reasons = [critique.reason for critique in failed_critiques]
        unique_failure_reasons = list(set(failure_reasons))

        logging.info(f"TutorAgent: Identified unique failure reasons: {unique_failure_reasons}")

        new_benchmarks = []
        for reason in unique_failure_reasons:
            prompt = self._create_prompt_for_new_benchmark(reason, problem_class)
            try:
                response = self.llm_provider.generate(prompt)
                benchmark = self._parse_llm_response(response)
                if benchmark:
                    new_benchmarks.append(benchmark)
            except Exception as e:
                logging.error(f"TutorAgent: Failed to generate or parse benchmark for reason '{reason}': {e}")

        logging.info(f"TutorAgent: Generated {len(new_benchmarks)} new benchmarks.")
        return new_benchmarks

    def _create_prompt_for_new_benchmark(self, failure_reason: str, problem_class: str = None) -> str:
        """
        Creates a prompt for the LLM to generate a new benchmark based on a failure reason.
        """
        class_prompt = ""
        if problem_class:
            class_prompt = f"The problem should be of the class '{problem_class}'."

        prompt = f"""
        Based on the following reason for a programming failure: "{failure_reason}"

        Please generate a new Python programming problem as a benchmark to help an AI agent learn from this mistake.
        {class_prompt}
        The problem should be a function that needs to be implemented.
        The output should be a single JSON object with the following keys:
        - "benchmark_name": a short, descriptive name for the benchmark (e.g., "recursive_factorial_to_iterative").
        - "function_code": a string containing the Python code for the function to be implemented, including a docstring. The function body should be empty (i.e., `pass`).
        - "test_code": a string containing Python code that uses pytest to test the function. It should include at least 2 test cases.

        Example output format:
        {{
            "benchmark_name": "example_benchmark",
            "function_code": "def example_function(n):\\n    '''Calculates something.'''\\n    pass",
            "test_code": "import pytest\\nfrom example_benchmark import example_function\\n\\ndef test_example_function():\\n    assert example_function(2) == 4"
        }}
        """
        return prompt

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parses the LLM's JSON response to extract the benchmark.
        """
        try:
            # The LLM might return the JSON inside a code block, so we need to clean it up.
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]

            benchmark = json.loads(response)

            if "benchmark_name" in benchmark and "function_code" in benchmark and "test_code" in benchmark:
                return benchmark
            else:
                logging.warning(f"TutorAgent: LLM response is missing required keys: {benchmark.keys()}")
                return None
        except json.JSONDecodeError as e:
            logging.error(f"TutorAgent: Failed to decode JSON from LLM response: {e}")
            logging.error(f"TutorAgent: Raw response: {response}")
            return None
