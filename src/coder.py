import google.generativeai as genai
import os
import re
from src.tools import CompilerTool, StaticAnalyzerTool

class CoderAgent:
    def __init__(self, api_key, compiler: CompilerTool, analyzer: StaticAnalyzerTool):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.compiler = compiler
        self.analyzer = analyzer

    def _clean_code(self, code):
        code_blocks = re.findall(r"```python\n(.*?)\n```", code, re.DOTALL)
        if code_blocks:
            return "\n".join(code_blocks)
        lines = code.strip().split('\n')
        cleaned_lines = []
        in_code = False
        for line in lines:
            if line.strip().startswith('def ') or line.strip().startswith('import '):
                in_code = True
            if in_code:
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    def code(self, file_path, instruction, max_retries=3):
        """
        Generates and verifies code, entering a correction loop if necessary.
        """
        print(f"CoderAgent: Received instruction for {file_path}")
        
        with open(file_path, 'r') as f:
            original_code = f.read()

        current_code = original_code
        for i in range(max_retries):
            print(f"CoderAgent: Generation attempt {i+1}")
            
            prompt = f"""
            You are a Python programmer. Your task is to modify the following file based on the instruction.
            File: {file_path}
            Instruction: {instruction}
            
            Current Code:
            ```python
            {current_code}
            ```
            
            Please provide only the complete, modified Python code for the file.
            """
            
            response = self.model.generate_content(prompt)
            new_code = self._clean_code(response.text)

            # Write the new code to a temporary file for verification
            temp_file_path = "temp_coder_output.py"
            with open(temp_file_path, 'w') as f:
                f.write(new_code)

            # Verify with tools
            compiler_error = self.compiler.use(temp_file_path)
            if compiler_error:
                print("CoderAgent: Compiler error detected. Retrying with feedback.")
                instruction = f"The previous attempt failed with a compilation error. Please fix it.\nError: {compiler_error}\nInstruction: {instruction}"
                current_code = new_code
                continue

            analyzer_output = self.analyzer.use(temp_file_path)
            if analyzer_output:
                # For now, we just log the analyzer output, not enter a correction loop.
                print(f"CoderAgent: Static analyzer found issues:\n{analyzer_output}")

            print("CoderAgent: Code generation successful and verified.")
            os.remove(temp_file_path)
            return new_code, original_code

        print("CoderAgent: Failed to generate valid code after multiple retries.")
        # If all retries fail, return the original code
        return original_code, original_code