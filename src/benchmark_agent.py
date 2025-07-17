

import google.generativeai as genai
import os
import re

class BenchmarkAgent:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def _clean_code(self, code):
        """
        Cleans the generated code to remove any non-Python text.
        """
        # Use regex to find code blocks
        code_blocks = re.findall(r"```python\n(.*?)\n```", code, re.DOTALL)
        if code_blocks:
            return "\n".join(code_blocks)
        
        # If no code blocks are found, assume the whole string is code
        # and remove any leading/trailing non-code text.
        lines = code.strip().split('\n')
        cleaned_lines = []
        in_code = False
        for line in lines:
            if line.strip().startswith('def ') or line.strip().startswith('import '):
                in_code = True
            if in_code:
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines)


    def generate_benchmark(self, topic="a simple string manipulation function"):
        """
        Generates a new benchmark (a function and a test for it).
        """
        print(f"BenchmarkAgent: Generating new benchmark on the topic of '{topic}'")

        # Generate the function code
        function_prompt = f"""
        You are a Python programmer. Write a single Python function on the topic of '{topic}'.
        The function should be simple, self-contained, and have a clear purpose.
        Do not include any test code or examples, only the function itself.
        Your output should be only the Python code, with no markdown formatting or other text.
        """
        function_response = self.model.generate_content(function_prompt)
        function_code = self._clean_code(function_response.text)

        # Extract the function name
        try:
            function_name = function_code.split("def ")[1].split("(")[0]
        except IndexError:
            print("BenchmarkAgent: Error - Could not extract function name from generated code.")
            return None, None, None

        # Generate the test code
        test_prompt = f"""
        You are a Python programmer writing a test for the following function:
        ```python
        {function_code}
        ```
        Write a pytest test file for this function.
        The test file should include at least 3 test cases.
        The test file should be named `test_{function_name}.py`.
        The test file should import the function from a file named `{function_name}.py`.
        Your output should be only the Python code, with no markdown formatting or other text.
        """
        test_response = self.model.generate_content(test_prompt)
        test_code = self._clean_code(test_response.text)

        print("BenchmarkAgent: Successfully generated new benchmark.")
        return function_name, function_code, test_code

