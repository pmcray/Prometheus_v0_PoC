import os
import re
import logging
from src.performance_logger import PerformanceLogger
from src.llm_provider import LLMProvider

class CurriculumAgent:
    def __init__(self, llm_provider: LLMProvider, performance_logger: PerformanceLogger):
        self.llm_provider = llm_provider
        self.performance_logger = performance_logger

    def _clean_code(self, code):
        code_blocks = re.findall(r"```(python|lean)\n(.*?)\n```", code, re.DOTALL)
        if code_blocks:
            return "\n".join([block[1] for block in code_blocks])
        lines = code.strip().split('\n')
        cleaned_lines = []
        in_code = False
        for line in lines:
            if line.strip().startswith('def ') or line.strip().startswith('import ') or line.strip().startswith('theorem'):
                in_code = True
            if in_code:
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    def generate_benchmark(self):
        """
        Generates a new benchmark for the self-modification loop.
        If a previous benchmark was solved, it generates a new one that is slightly
        more complex. Otherwise, it generates a simple entry-level benchmark.
        """
        last_benchmark = self.performance_logger.get_last_solved_benchmark()

        if last_benchmark is None or "solution_code" not in last_benchmark:
            logging.info("No previous benchmark solved. Generating entry-level benchmark.")
            topic = "a function that reverses a string and returns the reversed string."
        else:
            logging.info(f"Last solved benchmark had complexity {last_benchmark['complexity']}. Generating a harder one.")
            prompt = f"""
            Based on the following Python code, which has a complexity score of {last_benchmark['complexity']}, please propose a new, related coding challenge that is slightly more difficult. The new challenge should be solvable in a single Python function.

            Previous solution:
            ```python
            {last_benchmark['solution_code']}
            ```

            Your response should be ONLY a single line describing the new challenge. Do not add any preamble.
            Example response: a function that sorts a list of tuples by their second element
            """
            topic = self.llm_provider.generate(prompt).strip()

        logging.info(f"CurriculumAgent: Generating new benchmark on the topic of '{topic}'")

        # Generate the function code
        function_prompt = f"Write a single Python function for the following task: {topic}. Your output should be only the Python code, wrapped in ```python ... ```."
        function_text = self.llm_provider.generate(function_prompt)
        function_code = self._clean_code(function_text)

        if not function_code:
            logging.error("Failed to generate function code for the benchmark.")
            return None, None, None

        try:
            # A simple way to get the function name
            function_name = re.search(r"def\s+(\w+)\s*\(", function_code).group(1)
        except (AttributeError, IndexError):
            logging.error(f"Could not extract function name from generated code:\n{function_code}")
            return None, None, None

        # Generate the test code
        test_prompt = f"Write a pytest test file for this function:\n```python\n{function_code}\n```\nYour output should be only the Python code for the test file, wrapped in ```python ... ```. It should include necessary imports and at least 2 test cases, including one edge case."
        test_text = self.llm_provider.generate(test_prompt)
        test_code = self._clean_code(test_text)

        if not test_code:
            logging.error("Failed to generate test code for the benchmark.")
            return None, None, None

        return function_name, function_code, test_code

    def generate_theorem(self):
        """
        Generates a simple mathematical proposition in Lean.
        """
        logging.info("CurriculumAgent: Generating new theorem.")
        prompt = "Generate a simple theorem in the Lean language. The theorem should be a one-line statement. For example, `theorem add_zero (n : Nat) : n + 0 = n`."
        response_text = self.llm_provider.generate(prompt)
        theorem = self._clean_code(response_text)
        return theorem