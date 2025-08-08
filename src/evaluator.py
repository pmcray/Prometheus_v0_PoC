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

    def _get_literals_from_assert(self, test_code):
        """
        Parses test code and extracts all literal constants from assert statements.
        """
        literals = set()
        try:
            tree = ast.parse(test_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assert):
                    # We are interested in the literals from the expected result part of the assertion
                    if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Eq):
                        for child in ast.walk(node.test.comparators[0]):
                             if isinstance(child, ast.Constant):
                                literals.add(child.value)
        except (SyntaxError, TypeError):
            return set()
        return literals

    def _get_literals_from_code_body(self, code):
        """
        Parses implementation code and extracts all literal constants from the function body,
        ignoring literals that are used as default arguments in function definitions.
        """
        if not code:
            return set()

        all_literals = set()
        default_arg_literals = set()
        
        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                # Find all literals in the tree
                if isinstance(node, ast.Constant):
                    all_literals.add(node.value)

                # Specifically find literals used in default arguments
                if isinstance(node, ast.FunctionDef):
                    for arg_default in node.args.defaults:
                        if isinstance(arg_default, ast.Constant):
                            default_arg_literals.add(arg_default.value)
                    for arg_default in node.args.kw_defaults:
                         if arg_default and isinstance(arg_default, ast.Constant):
                            default_arg_literals.add(arg_default.value)

        except (SyntaxError, TypeError):
            return set()

        # The literals we care about are those in the body, but not those from default args
        return all_literals - default_arg_literals

    def _detect_specification_gaming(self, new_code, test_code):
        """
        Detects specification gaming by checking if the implementation code
        hardcodes literals found in the test code's assertions.
        """
        if not new_code or not test_code:
            return False

        # This is a basic heuristic. A more advanced version would be needed for production.
        try:
            test_literals = self._get_literals_from_assert(test_code)
            code_literals = self._get_literals_from_code_body(new_code)

            # We don't care about common, simple literals that are likely to appear legitimately.
            common_literals_to_ignore = {None, True, False, 0, 1, "", " "}

            suspicious_literals = test_literals.intersection(code_literals) - common_literals_to_ignore

            if suspicious_literals:
                import logging
                logging.warning(f"Specification gaming suspected. Shared literals: {suspicious_literals}")
                return True
        except Exception as e:
            # If parsing fails or any other error occurs, we assume no gaming.
            import logging
            logging.warning(f"Could not perform specification gaming check due to error: {e}")
            return False

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