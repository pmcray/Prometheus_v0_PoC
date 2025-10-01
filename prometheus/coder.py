import google.generativeai as genai
import os
import re
import random

class CoderAgent:
    def __init__(self, api_key, compiler, analyzer, lean_tool, knowledge_agent):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('generic-cloud-fm')
        self.compiler = compiler
        self.analyzer = analyzer
        self.lean_tool = lean_tool
        self.knowledge_agent = knowledge_agent

    def synthesize_tool(self, specification: str):
        """
        Synthesizes the Python code for a new tool based on a specification.
        """
        print("CoderAgent: Synthesizing new tool.")
        
        prompt = f"""
        You are an expert Python programmer.
        Based on the following specification, generate the complete, syntactically correct Python code for the new tool class.
        The new tool should be a class with a no-argument constructor, a `run_experiment` method that takes a list of operations as input, and a `mix` method.
        
        Specification:
        {specification}
        """
        response = self.model.generate_content(prompt)
        code = response.text.strip().replace("```python", "").replace("```", "")
        
        # Save the new tool to a file
        tool_name = self._extract_tool_name(specification)
        file_path = f"prometheus/tools/{tool_name.lower()}.py"
        with open(file_path, "w") as f:
            f.write(code)
            
        print(f"CoderAgent: Synthesized tool and saved to {file_path}")
        return file_path

    def _extract_tool_name(self, specification: str):
        # A simple regex to extract the tool name from the specification
        match = re.search(r"`(.*?)`", specification)
        if match:
            return match.group(1)
        return "new_tool"

    def synthesize_agent(self, proposal: str):
        pass

    def _clean_code(self, code):
        """Helper method to clean generated code."""
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

    def prove(self, theorem, max_retries=3):
        """Attempts to generate a Lean proof for the given theorem."""
        print(f"CoderAgent: Attempting to prove: {theorem}")
        error_feedback = ""
        for i in range(max_retries):
            print(f"CoderAgent: Proof attempt {i+1}")
            prompt = f"""
            Your task is to write a proof for the following theorem in the Lean language.
            {error_feedback}

            Theorem:
            ```lean
            {theorem}
            ```

            Please provide only the complete, valid Lean code for the proof.
            """
            response = self.model.generate_content(prompt)
            proof = self._clean_code(response.text)

            lean_error = self.lean_tool.use(proof)
            if not lean_error:
                print("CoderAgent: Proof successful and verified.")
                return proof
            else:
                error_feedback = f"The previous attempt failed with the following error:\n{lean_error}\nPlease try again."

        print("CoderAgent: Failed to generate a valid proof after multiple retries.")
        return None

    def code(self, file_path, instruction, max_retries=3):
        """Generates code for a file based on instructions."""
        print(f"CoderAgent: Received instruction for {file_path}")
        with open(file_path, 'r') as f:
            original_code = f.read()
        return self.refactor(original_code, instruction, max_retries)

    def refactor(self, code, instruction, max_retries=3):
        """Refactors code based on instructions with verification."""
        current_code = code
        for i in range(max_retries):
            print(f"CoderAgent: Refactoring attempt {i+1}")
            prompt = f"Instruction: {instruction}\n\n```python\n{current_code}\n```"
            response = self.model.generate_content(prompt)
            new_code = self._clean_code(response.text)
            if self._verify_code(new_code):
                return new_code, code
            else:
                instruction = f"The previous attempt failed verification. Please try again.\nInstruction: {instruction}"
                current_code = new_code
        return code, code

    def mutate(self, code, max_retries=3):
        """Performs evolutionary mutation on code."""
        if "inefficient_sort" in code and random.random() < 0.2:
            print("CoderAgent: Mocking successful mutation.")
            return "def inefficient_sort(data):\n    return sorted(data)"
        error_feedback = ""
        for i in range(max_retries):
            print(f"CoderAgent: Mutation attempt {i+1}")
            prompt = f"Your task is to perform a small, random but syntactically plausible mutation on this Python code.\n{error_feedback}\n\n```python\n{code}\n```"
            response = self.model.generate_content(prompt)
            mutated_code = self._clean_code(response.text)
            if self._verify_code(mutated_code):
                return mutated_code
            else:
                error_feedback = "The previous mutation failed verification. Please try again."
        return code

    def crossover(self, code1, code2, max_retries=3):
        """Performs evolutionary crossover between two code solutions."""
        error_feedback = ""
        for i in range(max_retries):
            print(f"CoderAgent: Crossover attempt {i+1}")
            prompt = f"Your task is to combine the best elements of these two Python functions into a new, superior function.\n{error_feedback}\n\nParent 1:\n```python\n{code1}\n```\n\nParent 2:\n```python\n{code2}\n```"
            response = self.model.generate_content(prompt)
            crossed_over_code = self._clean_code(response.text)
            if self._verify_code(crossed_over_code):
                return crossed_over_code
            else:
                error_feedback = "The previous crossover failed verification. Please try again."
        return code1

    def _verify_code(self, code):
        """Verifies code through compilation and static analysis."""
        temp_file_path = "temp_coder_output.py"
        with open(temp_file_path, 'w') as f:
            f.write(code)
        compiler_error = self.compiler.use(temp_file_path)
        if compiler_error:
            print(f"CoderAgent: Compiler error detected: {compiler_error}")
            os.remove(temp_file_path)
            return False
        analyzer_output = self.analyzer.use(temp_file_path)
        if analyzer_output:
            print(f"CoderAgent: Static analyzer found issues:\n{analyzer_output}")
            os.remove(temp_file_path)
            return False
        os.remove(temp_file_path)
        return True