"""
CodeEvaluator: AST-based Complexity Analyzer for Project Prometheus

This module performs static analysis on Python code to estimate algorithmic 
complexity and identify performance bottlenecks using Abstract Syntax Trees (AST).
"""

import ast
import json
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict

@dataclass
class ComplexityCritique:
    """Structured critique of code complexity"""
    complexity_estimate: str
    max_loop_depth: int
    has_recursion: bool
    nested_loop_count: int
    list_comp_count: int
    builtin_complexity_calls: List[str]
    recommendations: List[str]
    raw_metrics: Dict[str, Any]

class ComplexityVisitor(ast.NodeVisitor):
    """AST Visitor to extract complexity metrics"""
    def __init__(self):
        self.max_depth = 0
        self.current_depth = 0
        self.nested_loops = 0
        self.recursion_detected = False
        self.list_comprehensions = 0
        self.builtin_complexity_funcs = {"sorted", "sort", "min", "max", "sum", "count", "index"}
        self.found_builtins = []
        self.function_names = set()

    def visit_FunctionDef(self, node):
        self.function_names.add(node.name)
        self.generic_visit(node)

    def visit_For(self, node):
        self.current_depth += 1
        if self.current_depth > 1:
            self.nested_loops += 1
        self.max_depth = max(self.max_depth, self.current_depth)
        self.generic_visit(node)
        self.current_depth -= 1

    def visit_While(self, node):
        self.current_depth += 1
        if self.current_depth > 1:
            self.nested_loops += 1
        self.max_depth = max(self.max_depth, self.current_depth)
        self.generic_visit(node)
        self.current_depth -= 1

    def visit_ListComp(self, node):
        self.list_comprehensions += 1
        self.current_depth += 1
        self.max_depth = max(self.max_depth, self.current_depth)
        self.generic_visit(node)
        self.current_depth -= 1

    def visit_Call(self, node):
        # Check for recursion
        is_expensive_builtin = False
        if isinstance(node.func, ast.Name):
            if node.func.id in self.function_names:
                self.recursion_detected = True
            if node.func.id in self.builtin_complexity_funcs:
                is_expensive_builtin = True
                # Track if these are inside loops
                if self.current_depth > 0:
                    self.found_builtins.append(f"{node.func.id} (inside loop)")
                else:
                    self.found_builtins.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in self.builtin_complexity_funcs:
                is_expensive_builtin = True
                if self.current_depth > 0:
                    self.found_builtins.append(f"{node.func.attr} (inside loop)")
                else:
                    self.found_builtins.append(node.func.attr)
        
        if is_expensive_builtin:
            self.current_depth += 1
            self.max_depth = max(self.max_depth, self.current_depth)
            self.generic_visit(node)
            self.current_depth -= 1
        else:
            self.generic_visit(node)

class CodeEvaluator:
    """
    Evaluator that analyzes Python code using AST to identify complexity issues.
    """
    def __init__(self):
        pass

    def analyze(self, code: str) -> ComplexityCritique:
        """
        Analyze the given Python code and return a ComplexityCritique.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ComplexityCritique(
                complexity_estimate="Error",
                max_loop_depth=0,
                has_recursion=False,
                nested_loop_count=0,
                list_comp_count=0,
                builtin_complexity_calls=[],
                recommendations=[f"Syntax Error: {e}"],
                raw_metrics={"error": str(e)}
            )

        visitor = ComplexityVisitor()
        visitor.visit(tree)

        # Heuristic Complexity Estimation
        complexity = "O(1)"
        if visitor.recursion_detected:
            complexity = "O(2^n) or O(n)" # Naive guess
        elif visitor.max_depth == 1:
            complexity = "O(n)"
        elif visitor.max_depth == 2:
            complexity = "O(n^2)"
        elif visitor.max_depth > 2:
            complexity = f"O(n^{visitor.max_depth})"

        # Refine for builtins inside loops
        expensive_in_loop = [b for b in visitor.found_builtins if "inside loop" in b]
        if expensive_in_loop and visitor.max_depth == 1:
            complexity = "O(n^2) - Hidden by builtins"
        elif expensive_in_loop and visitor.max_depth == 2:
            complexity = "O(n^3) - Hidden by builtins"

        recommendations = []
        if visitor.nested_loops > 0:
            recommendations.append("Reduce nested loops to improve time complexity.")
        if visitor.recursion_detected:
            recommendations.append("Consider iterative approach or memoization to avoid redundant calculations.")
        if expensive_in_loop:
            recommendations.append("Move expensive built-in calls (like sorted() or count()) out of loops if possible.")

        return ComplexityCritique(
            complexity_estimate=complexity,
            max_loop_depth=visitor.max_depth,
            has_recursion=visitor.recursion_detected,
            nested_loop_count=visitor.nested_loops,
            list_comp_count=visitor.list_comprehensions,
            builtin_complexity_calls=visitor.found_builtins,
            recommendations=recommendations,
            raw_metrics={
                "max_depth": visitor.max_depth,
                "nested_loops": visitor.nested_loops,
                "recursion": visitor.recursion_detected,
                "list_comps": visitor.list_comprehensions,
                "builtins": visitor.found_builtins
            }
        )

    def get_critique_json(self, code: str) -> str:
        """Return the analysis as a formatted JSON string"""
        critique = self.analyze(code)
        return json.dumps(asdict(critique), indent=2)

if __name__ == "__main__":
    # Test cases
    evaluator = CodeEvaluator()
    
    bubble_sort = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
"""
    
    quick_sort = """
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)
"""

    print("--- Bubble Sort Analysis ---")
    print(evaluator.get_critique_json(bubble_sort))
    
    print("\n--- Quick Sort Analysis ---")
    print(evaluator.get_critique_json(quick_sort))
