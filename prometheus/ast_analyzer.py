import ast
import logging

logger = logging.getLogger(__name__)

class ASTComplexityAnalyzer(ast.NodeVisitor):
    """
    Analyzes the complexity of Python code using its Abstract Syntax Tree (AST).
    """

    def __init__(self, code: str):
        self.tree = ast.parse(code)
        self.max_loop_depth = 0
        self.recursion_detected = False
        self.function_defs = set()

    def analyze(self) -> dict:
        """
        Performs the complexity analysis and returns a dictionary of metrics.
        """
        self.visit(self.tree)
        return {
            "max_loop_depth": self.max_loop_depth,
            "recursion_detected": self.recursion_detected,
        }

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.function_defs.add(node.name)
        # Reset loop depth for each function
        current_max_depth = self.max_loop_depth
        self.max_loop_depth = 0
        self._visit_children_and_track_loops(node, 0)
        self.max_loop_depth = max(current_max_depth, self.max_loop_depth)

        # Check for recursion
        for sub_node in ast.walk(node):
            if isinstance(sub_node, ast.Call) and isinstance(sub_node.func, ast.Name) and sub_node.func.id == node.name:
                self.recursion_detected = True

        self.generic_visit(node)

    def _visit_children_and_track_loops(self, node, current_depth):
        self.max_loop_depth = max(self.max_loop_depth, current_depth)
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.While)):
                self._visit_children_and_track_loops(child, current_depth + 1)
            elif isinstance(child, ast.FunctionDef):
                # Don't descend into nested functions for loop depth calculation
                continue
            else:
                self._visit_children_and_track_loops(child, current_depth)

    def visit_For(self, node: ast.For):
        # This method is handled by the custom traversal in _visit_children_and_track_loops
        pass

    def visit_While(self, node: ast.While):
        # This method is handled by the custom traversal in _visit_children_and_track_loops
        pass
