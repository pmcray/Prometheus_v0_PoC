import subprocess
import os
import ast
import json
import cProfile
import pstats
import io
import logging
from memory_profiler import memory_usage
from .critique import SelfReferentialCritique, CausalAnalysis, DynamicAnalysis, PerformanceMetric

class EvaluatorAgent:
    def __init__(self):
        self.profiling_data = self._load_profiling_data()

    def _load_profiling_data(self):
        try:
            with open("profiling_data.json", 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Could not load profiling_data.json: {e}")
            return {}

    def _get_function_name(self, code):
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    return node.name
        except (SyntaxError, IndexError):
            return None
        return None

    def _perform_dynamic_analysis(self, code_str, function_name, data):
        if not function_name or not data:
            return None

        local_scope = {}
        # Import time module to make it available to the exec'd code
        import time
        exec_globals = {'time': time}

        try:
            exec(code_str, exec_globals, local_scope)
        except Exception as e:
            logging.error(f"Dynamic analysis failed during exec: {e}")
            return None

        target_func = local_scope.get(function_name)
        if not callable(target_func):
            return None

        # Time profiling
        pr = cProfile.Profile()
        pr.enable()
        target_func(data)
        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats()
        total_time = ps.total_tt * 1000

        # Memory profiling
        mem_usage = memory_usage((target_func, (data,)), interval=0.1, timeout=10, max_usage=True)
        peak_mem = mem_usage if isinstance(mem_usage, (int, float)) else 0.0


        return {
            "execution_time_ms": total_time,
            "peak_memory_mb": peak_mem
        }

    def _analyze_complexity(self, code):
        tree = ast.parse(code)
        complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                complexity += 1
        return complexity

    def analyze_complexity(self, code):
        if not code:
            return 0
        return self._analyze_complexity(code)

    def _get_literals_from_assert(self, test_code):
        literals = set()
        try:
            tree = ast.parse(test_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assert):
                    if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Eq):
                        for child in ast.walk(node.test.comparators[0]):
                             if isinstance(child, ast.Constant):
                                literals.add(child.value)
        except (SyntaxError, TypeError):
            return set()
        return literals

    def _get_literals_from_code_body(self, code):
        if not code:
            return set()
        all_literals = set()
        default_arg_literals = set()
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant):
                    all_literals.add(node.value)
                if isinstance(node, ast.FunctionDef):
                    for arg_default in node.args.defaults:
                        if isinstance(arg_default, ast.Constant):
                            default_arg_literals.add(arg_default.value)
                    for arg_default in node.args.kw_defaults:
                         if arg_default and isinstance(arg_default, ast.Constant):
                            default_arg_literals.add(arg_default.value)
        except (SyntaxError, TypeError):
            return set()
        return all_literals - default_arg_literals

    def _detect_specification_gaming(self, new_code, test_code):
        if not new_code or not test_code:
            return False
        try:
            test_literals = self._get_literals_from_assert(test_code)
            code_literals = self._get_literals_from_code_body(new_code)
            common_literals_to_ignore = {None, True, False, 0, 1, "", " "}
            suspicious_literals = test_literals.intersection(code_literals) - common_literals_to_ignore
            if suspicious_literals:
                logging.warning(f"Specification gaming suspected. Shared literals: {suspicious_literals}")
                return True
        except Exception as e:
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

        original_complexity = self._analyze_complexity(original_code)
        new_complexity = self._analyze_complexity(new_code)

        if self._detect_specification_gaming(new_code, test_code):
            critique = SelfReferentialCritique(
                test_passed=False,
                causal_analysis=CausalAnalysis(change_type="NO_CHANGE", from_complexity=original_complexity, to_complexity=new_complexity),
                evaluation_confidence=0.99, uncertainty_level="low", historical_context=None,
                reason="Specification gaming detected. The code appears to hardcode values from the tests."
            )
            return critique, ""

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

        dynamic_analysis_result = None
        if test_passed:
            profiling_key = "sort_list_of_tuples"
            data_to_profile = self.profiling_data.get(profiling_key)
            original_func_name = self._get_function_name(original_code)
            new_func_name = self._get_function_name(new_code)
            original_perf = self._perform_dynamic_analysis(original_code, original_func_name, data_to_profile)
            new_perf = self._perform_dynamic_analysis(new_code, new_func_name, data_to_profile)

            if original_perf and new_perf:
                time_metric = PerformanceMetric(
                    original=original_perf['execution_time_ms'],
                    new=new_perf['execution_time_ms'],
                    delta=new_perf['execution_time_ms'] - original_perf['execution_time_ms']
                )
                mem_metric = PerformanceMetric(
                    original=original_perf['peak_memory_mb'],
                    new=new_perf['peak_memory_mb'],
                    delta=new_perf['peak_memory_mb'] - original_perf['peak_memory_mb']
                )
                dynamic_analysis_result = DynamicAnalysis(
                    status="COMPLETED",
                    execution_time_ms=time_metric,
                    peak_memory_mb=mem_metric
                )
            else:
                dynamic_analysis_result = DynamicAnalysis(status="FAILED")

        if not test_passed:
            critique = SelfReferentialCritique(
                test_passed=False,
                causal_analysis=CausalAnalysis(change_type="NO_CHANGE", from_complexity=original_complexity, to_complexity=new_complexity),
                dynamic_analysis=dynamic_analysis_result,
                evaluation_confidence=0.99, uncertainty_level="low", historical_context=None,
                reason="Tests failed to pass."
            )
            return critique, test_output

        # Final judgment logic
        static_improvement = new_complexity < original_complexity
        dynamic_improvement = False
        reason_parts = []

        if dynamic_analysis_result and dynamic_analysis_result.status == "COMPLETED":
            time_delta = dynamic_analysis_result.execution_time_ms.delta
            mem_delta = dynamic_analysis_result.peak_memory_mb.delta
            # Dynamic improvement requires non-regression in both time and memory
            if time_delta <= 0 and mem_delta <= 0:
                dynamic_improvement = True

            if time_delta > 0:
                reason_parts.append(f"Execution time increased by {time_delta:.2f}ms.")
            if mem_delta > 0:
                reason_parts.append(f"Memory usage increased by {mem_delta:.2f}MB.")

        if static_improvement and dynamic_improvement:
            change_type = "IMPROVEMENT"
            reason = f"Successfully refactored from complexity {original_complexity} to {new_complexity} with improved or stable performance."
        elif static_improvement and not dynamic_improvement:
            change_type = "REGRESSION" # It's a regression because performance got worse
            reason = f"Static complexity improved, but dynamic performance regressed. {' '.join(reason_parts)}"
        else:
            change_type = "NO_CHANGE"
            reason = "No improvement in static complexity. " + ' '.join(reason_parts)

        critique = SelfReferentialCritique(
            test_passed=True,
            causal_analysis=CausalAnalysis(change_type=change_type, from_complexity=original_complexity, to_complexity=new_complexity),
            dynamic_analysis=dynamic_analysis_result,
            evaluation_confidence=0.9, uncertainty_level="low", historical_context=None,
            reason=reason
        )
            
        return critique, test_output