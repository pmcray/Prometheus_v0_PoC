import google.generativeai as genai
import os
import re
from src.performance_logger import PerformanceLogger

class CurriculumAgent:
    def __init__(self, api_key, performance_logger: PerformanceLogger):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
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
        last_complexity = self.performance_logger.get_last_solved_complexity()
        if last_complexity == 0:
            topic = "a simple string manipulation function"
        elif last_complexity == 1:
            topic = "a function that sorts a list of tuples by the second element"
        else:
            topic = "a function that finds the median of a list of numbers"
        print(f"CurriculumAgent: Generating new benchmark on the topic of '{topic}'")
        function_prompt = f"Write a single Python function for the following task: {topic}. Your output should be only the Python code."
        function_response = self.model.generate_content(function_prompt)
        function_code = self._clean_code(function_response.text)
        try:
            function_name = function_code.split("def ")[1].split("(")[0]
        except IndexError:
            return None, None, None
        test_prompt = f"Write a pytest test file for this function:\n```python\n{function_code}\n```\nYour output should be only the Python code."
        test_response = self.model.generate_content(test_prompt)
        test_code = self._clean_code(test_response.text)
        return function_name, function_code, test_code

    def generate_theorem(self):
        """
        Generates a simple mathematical proposition in Lean.
        """
        print("CurriculumAgent: Generating new theorem.")
        prompt = "Generate a simple theorem in the Lean language. The theorem should be a one-line statement. For example, `theorem add_zero (n : Nat) : n + 0 = n`."
        response = self.model.generate_content(prompt)
        theorem = self._clean_code(response.text)
        return theorem