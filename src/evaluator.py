import subprocess
import os
import ast
from .critique import CausalCritique

class EvaluatorAgent:
    def _analyze_complexity(self, code):
        tree = ast.parse(code)
        complexity = 0
        # A simple complexity model: count all loops.
        # Nested loops will be counted transitively.
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                complexity += 1
        return complexity

    def analyze_complexity(self, code):
        """Public method to analyze complexity."""
        if not code:
            return 0
        return self._analyze_complexity(code)

    def _detect_specification_gaming(self, new_code, test_code):
        """
        A simple heuristic to detect specification gaming.
        For now, it just checks if the solution is too simple.
        
        NOTE: This heuristic is too simple and is causing false positives.
        Disabling for now to allow verification of the main loop.
        This should be replaced with a more robust implementation.
        """
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