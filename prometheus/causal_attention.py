"""
Enhanced Causal Attention Head with AST-based analysis
Implements features from v0.20 onwards
"""

import ast
import sys
from typing import Dict, List, Any, Optional, Tuple
import logging
from .schemas.communication import CausalAnalysis

class ASTComplexityAnalyzer:
    """Analyzes code complexity using Abstract Syntax Tree parsing"""

    def __init__(self):
        self.complexity_metrics = {}

    def analyze_complexity(self, code: str) -> Dict[str, Any]:
        """Perform comprehensive complexity analysis on code"""
        try:
            tree = ast.parse(code)
            return {
                "max_loop_depth": self._calculate_max_loop_depth(tree),
                "recursion_count": self._count_recursion(tree),
                "nested_comprehensions": self._count_nested_comprehensions(tree),
                "high_cost_operations": self._identify_high_cost_ops(tree),
                "cyclomatic_complexity": self._calculate_cyclomatic_complexity(tree),
                "cognitive_complexity": self._calculate_cognitive_complexity(tree)
            }
        except SyntaxError as e:
            logging.error(f"Syntax error in code analysis: {e}")
            return {"error": str(e)}

    def _calculate_max_loop_depth(self, node: ast.AST, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth of loops"""
        max_depth = current_depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.While)):
                child_depth = self._calculate_max_loop_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._calculate_max_loop_depth(child, current_depth)
                max_depth = max(max_depth, child_depth)

        return max_depth

    def _count_recursion(self, tree: ast.AST) -> Dict[str, Any]:
        """Detect and analyze recursive function calls"""
        function_calls = {}
        function_defs = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_defs.append(node.name)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in function_calls:
                        function_calls[func_name] += 1
                    else:
                        function_calls[func_name] = 1

        recursive_calls = {name: count for name, count in function_calls.items()
                          if name in function_defs}

        return {
            "recursive_functions": list(recursive_calls.keys()),
            "recursive_call_counts": recursive_calls,
            "total_recursive_calls": sum(recursive_calls.values())
        }

    def _count_nested_comprehensions(self, tree: ast.AST) -> int:
        """Count nested list/dict/set comprehensions"""
        nested_count = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp)):
                # Check if this comprehension contains another comprehension
                for child in ast.walk(node):
                    if child != node and isinstance(child, (ast.ListComp, ast.DictComp, ast.SetComp)):
                        nested_count += 1

        return nested_count

    def _identify_high_cost_ops(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Identify high-cost operations within loops"""
        high_cost_ops = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                # Check for expensive operations inside loops
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Attribute):
                            method_name = child.func.attr
                            if method_name in ['sort', 'sorted', 'index', 'count']:
                                high_cost_ops.append({
                                    "operation": method_name,
                                    "context": "inside_loop",
                                    "line": getattr(child, 'lineno', None)
                                })

        return high_cost_ops

    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        return complexity

    def _calculate_cognitive_complexity(self, tree: ast.AST) -> int:
        """Calculate cognitive complexity (more human-focused than cyclomatic)"""
        complexity = 0
        nesting_level = 0

        def visit_node(node, level):
            nonlocal complexity

            if isinstance(node, (ast.If, ast.While, ast.For)):
                complexity += 1 + level
                level += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1 + level

            for child in ast.iter_child_nodes(node):
                visit_node(child, level)

        visit_node(tree, 0)
        return complexity

class CausalAttentionHead:
    """Enhanced Causal Attention Head with AST-based analysis"""

    def __init__(self):
        self.analyzer = ASTComplexityAnalyzer()
        self.attention_log = []

    def generate_causal_focus(self, code: str, task_description: str) -> Dict[str, Any]:
        """Generate structured causal focus object"""
        complexity_analysis = self.analyzer.analyze_complexity(code)

        # Identify primary causal concerns
        causal_concerns = self._identify_causal_concerns(complexity_analysis)

        causal_focus = {
            "task_description": task_description,
            "complexity_analysis": complexity_analysis,
            "primary_concerns": causal_concerns,
            "attention_targets": self._generate_attention_targets(complexity_analysis),
            "optimization_hints": self._generate_optimization_hints(complexity_analysis)
        }

        # Log attention event
        self._log_attention_event("causal_focus_generation", causal_focus)

        return causal_focus

    def generate_causal_diff(self, original_code: str, new_code: str) -> CausalAnalysis:
        """Generate causal diff between original and modified code"""
        original_analysis = self.analyzer.analyze_complexity(original_code)
        new_analysis = self.analyzer.analyze_complexity(new_code)

        # Determine change type
        change_type = self._determine_change_type(original_analysis, new_analysis)

        # Calculate improvement
        improvement_detected = self._detect_improvement(original_analysis, new_analysis)

        causal_diff = {
            "loop_depth_change": new_analysis.get("max_loop_depth", 0) - original_analysis.get("max_loop_depth", 0),
            "recursion_change": len(new_analysis.get("recursion_count", {}).get("recursive_functions", [])) -
                               len(original_analysis.get("recursion_count", {}).get("recursive_functions", [])),
            "complexity_change": new_analysis.get("cyclomatic_complexity", 0) - original_analysis.get("cyclomatic_complexity", 0),
            "high_cost_ops_change": len(new_analysis.get("high_cost_operations", [])) - len(original_analysis.get("high_cost_operations", []))
        }

        return CausalAnalysis(
            change_type=change_type,
            complexity_before=original_analysis,
            complexity_after=new_analysis,
            causal_diff=causal_diff,
            improvement_detected=improvement_detected
        )

    def _identify_causal_concerns(self, analysis: Dict[str, Any]) -> List[str]:
        """Identify primary causal concerns from complexity analysis"""
        concerns = []

        if analysis.get("max_loop_depth", 0) > 2:
            concerns.append("excessive_loop_nesting")

        if analysis.get("recursion_count", {}).get("total_recursive_calls", 0) > 0:
            concerns.append("recursive_complexity")

        if len(analysis.get("high_cost_operations", [])) > 0:
            concerns.append("expensive_operations_in_loops")

        if analysis.get("cyclomatic_complexity", 0) > 10:
            concerns.append("high_cyclomatic_complexity")

        if analysis.get("cognitive_complexity", 0) > 15:
            concerns.append("high_cognitive_complexity")

        return concerns

    def _generate_attention_targets(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate specific attention targets for optimization"""
        targets = []

        if analysis.get("max_loop_depth", 0) > 1:
            targets.append("loop_structure_optimization")

        if analysis.get("recursion_count", {}).get("total_recursive_calls", 0) > 0:
            targets.append("recursion_to_iteration_conversion")

        if len(analysis.get("high_cost_operations", [])) > 0:
            targets.append("data_structure_optimization")

        return targets

    def _generate_optimization_hints(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate specific optimization hints"""
        hints = []

        if analysis.get("max_loop_depth", 0) > 2:
            hints.append("Consider using hash maps or sets to reduce nested loop complexity")

        if "sort" in str(analysis.get("high_cost_operations", [])):
            hints.append("Consider pre-sorting data or using more efficient sorting strategies")

        if analysis.get("recursion_count", {}).get("total_recursive_calls", 0) > 3:
            hints.append("Consider converting recursion to iterative approach with explicit stack")

        return hints

    def _determine_change_type(self, original: Dict[str, Any], new: Dict[str, Any]) -> str:
        """Determine the type of change made"""
        orig_loops = original.get("max_loop_depth", 0)
        new_loops = new.get("max_loop_depth", 0)

        orig_recursion = len(original.get("recursion_count", {}).get("recursive_functions", []))
        new_recursion = len(new.get("recursion_count", {}).get("recursive_functions", []))

        if new_loops < orig_loops:
            return "REDUCED_LOOP_DEPTH"
        elif new_recursion < orig_recursion:
            return "REDUCED_RECURSION"
        elif new_loops == orig_loops and new_recursion == orig_recursion:
            return "NO_STRUCTURAL_CHANGE"
        else:
            return "COMPLEXITY_INCREASE"

    def _detect_improvement(self, original: Dict[str, Any], new: Dict[str, Any]) -> bool:
        """Detect if there's a genuine algorithmic improvement"""
        # Multiple criteria for improvement detection
        loop_improvement = new.get("max_loop_depth", 0) < original.get("max_loop_depth", 0)
        recursion_improvement = (len(new.get("recursion_count", {}).get("recursive_functions", [])) <
                                len(original.get("recursion_count", {}).get("recursive_functions", [])))
        complexity_improvement = new.get("cyclomatic_complexity", 0) < original.get("cyclomatic_complexity", 0)
        cost_ops_improvement = len(new.get("high_cost_operations", [])) < len(original.get("high_cost_operations", []))

        return any([loop_improvement, recursion_improvement, complexity_improvement, cost_ops_improvement])

    def _log_attention_event(self, event_type: str, data: Dict[str, Any]):
        """Log attention events for later analysis"""
        self.attention_log.append({
            "event_type": event_type,
            "timestamp": str(logging.time.time()),
            "data": data
        })

    def get_attention_log(self) -> List[Dict[str, Any]]:
        """Get the attention log for analysis"""
        return self.attention_log.copy()