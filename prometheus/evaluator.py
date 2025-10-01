import subprocess
import os
import ast
import google.generativeai as genai
from .critique import CausalCritique
from .tools import LeanTool
from .tools.proof_tree import ProofTree

class EvaluatorAgent:
    def __init__(self, api_key, lean_tool: LeanTool):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('generic-cloud-fm')
        self.lean_tool = lean_tool

    def _analyze_complexity(self, code):
        tree = ast.parse(code)
        complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                for sub_node in ast.walk(node):
                    if isinstance(sub_node, (ast.For, ast.While)) and sub_node != node:
                        complexity += 1
        return complexity

    def _detect_specification_gaming(self, new_code, test_code):
        """
        A simple heuristic to detect specification gaming.
        For now, it just checks if the solution is too simple.
        """
        # A very simple heuristic: if the function body is less than 2 lines
        # and the test code is more than 5 lines, it might be a hardcoded solution.
        new_code_lines = len(new_code.strip().split('\n'))
        test_code_lines = len(test_code.strip().split('\n'))

        if new_code_lines <= 2 and test_code_lines >= 5:
            return True
        return False

    def evaluate(self, new_code, original_code, test_file_path, original_file_path):
        return self.evaluate_code(new_code, original_code, test_file_path, original_file_path)

    def evaluate_code(self, new_code, original_code, test_file_path, original_file_path):
        temp_file_path = "temp_eval_code.py"
        with open(temp_file_path, "w") as f:
            f.write(new_code)

        with open(test_file_path, 'r') as f:
            test_code = f.read()

        if self._detect_specification_gaming(new_code, test_code):
            return CausalCritique(test_passed=False, causal_improvement=False, reason="Specification gaming detected."), ""

        original_module_name = os.path.basename(original_file_path).replace('.py', '')
        temp_module_name = temp_file_path.replace('.py', '')

        modified_test_code = test_code.replace(f'from {original_module_name}', f'from {temp_module_name}')

        temp_test_file_path = "temp_test_file.py"
        with open(temp_test_file_path, 'w') as f:
            f.write(modified_test_code)

        test_passed = False
        test_output = ""
        try:
            import sys
            env = os.environ.copy()
            env["PYTHONPATH"] = f".{os.pathsep}toy_problem"
            result = subprocess.run([sys.executable, "-m", "pytest", temp_test_file_path], capture_output=True, text=True, env=env)
            if result.returncode == 0:
                test_passed = True
                test_output = result.stdout
            else:
                test_output = result.stdout + "\n" + result.stderr
        finally:
            os.remove(temp_file_path)
            os.remove(temp_test_file_path)

        if not test_passed:
            return CausalCritique(test_passed=False, causal_improvement=False, reason="Tests failed to pass."), test_output

        original_complexity = self._analyze_complexity(original_code)
        new_complexity = self._analyze_complexity(new_code)

        if new_complexity < original_complexity:
            critique = CausalCritique(
                test_passed=True,
                causal_improvement=True,
                reason=f"Successfully refactored from complexity {original_complexity} to {new_complexity}."
            )
        else:
            critique = CausalCritique(
                test_passed=True,
                causal_improvement=False,
                reason="The code passes the test, but no causal improvement in time complexity was achieved."
            )

        return critique, test_output

    def summarize_proof_strategy(self, proof_tree: ProofTree, theorem: str):
        print("EvaluatorAgent: Summarizing successful proof strategy.")
        successful_node = self._find_solved_node(proof_tree.root)
        if not successful_node:
            return "Could not find a successful proof path to summarize."
        tactics = proof_tree.get_proof_path(successful_node)
        prompt = f"""
        You are an expert in the Lean theorem prover.
        The following theorem was successfully proven with the given sequence of tactics.
        
        Theorem: {theorem}
        Sequence of Tactics: {tactics}
        
        Please provide a one-sentence, high-level summary of the proof strategy.
        """
        response = self.model.generate_content(prompt)
        return response.text.strip()

    def _find_solved_node(self, node):
        if node.is_solved:
            return node
        for child in node.children:
            solved = self._find_solved_node(child)
            if solved:
                return solved
        return None
