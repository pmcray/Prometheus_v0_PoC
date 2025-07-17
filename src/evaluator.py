import subprocess
import os
import ast
from .critique import CausalCritique

class EvaluatorAgent:
    def _analyze_complexity(self, code):
        """
        Analyzes the complexity of the code using AST to find nested loops.
        Returns a simple complexity score (number of nested loops).
        """
        tree = ast.parse(code)
        complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                # Check for nested loops
                for sub_node in ast.walk(node):
                    if isinstance(sub_node, (ast.For, ast.While)) and sub_node != node:
                        complexity += 1
        return complexity

    def evaluate(self, new_code, original_code, test_file_path, original_file_path):
        """
        Evaluates the new code by running unit tests and performing causal analysis.
        """
        print("EvaluatorAgent: Received new code for evaluation.")
        
        # Create a temporary file for the new code
        temp_file_path = "temp_new_code.py"
        with open(temp_file_path, "w") as f:
            f.write(new_code)
            
        with open(test_file_path, 'r') as f:
            test_code = f.read()
            
        original_module_name = os.path.basename(original_file_path).replace('.py', '')
        temp_module_name = temp_file_path.replace('.py', '')
        
        modified_test_code = test_code.replace(f'from .{original_module_name}', f'from {temp_module_name}')
        
        temp_test_file_path = "temp_test_file.py"
        with open(temp_test_file_path, 'w') as f:
            f.write(modified_test_code)

        print(f"EvaluatorAgent: Running tests from {temp_test_file_path}...")
        
        test_passed = False
        test_output = ""
        try:
            result = subprocess.run(["pytest", temp_test_file_path], capture_output=True, text=True)
            if result.returncode == 0:
                test_passed = True
                test_output = result.stdout
                print("EvaluatorAgent: Tests passed!")
            else:
                test_output = result.stdout + "\n" + result.stderr
                print("EvaluatorAgent: Tests failed.")
        finally:
            # Clean up temporary files
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