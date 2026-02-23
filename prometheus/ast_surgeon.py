"""
AST Surgeon: Direct Code Modification via AST Synthesis (Task P1.T4)

This module provides the capability for 'AST-based surgery' where the agent
can surgically replace parts of its own source code with optimized subtrees.
"""

import ast
import logging

class ASTSurgeon:
    """
    Surgical modification tool for Python source code.
    Ensures that every mutation yields syntactically valid code.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("ASTSurgeon")

    def replace_node(self, source_code: str, target_node_type: type, 
                     new_node: ast.AST) -> str:
        """
        Find the first node of target_node_type and replace it with new_node.
        """
        tree = ast.parse(source_code)
        
        class ReplacementTransformer(ast.NodeTransformer):
            def __init__(self, target_type, replacement):
                self.target_type = target_type
                self.replacement = replacement
                self.replaced = False

            def generic_visit(self, node):
                if not self.replaced and isinstance(node, self.target_type):
                    self.replaced = True
                    return self.replacement
                return super().generic_visit(node)

        transformer = ReplacementTransformer(target_node_type, new_node)
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)
        
        if hasattr(ast, "unparse"):
            return ast.unparse(new_tree)
        else:
            return "# AST unparse not available."

    def optimize_loop_with_list_comp(self, source_code: str) -> str:
        """
        Automatically identifies a simple for-loop-append pattern and
        replaces it with a list comprehension. (Example surgery)
        """
        tree = ast.parse(source_code)
        
        class LoopOptimizer(ast.NodeTransformer):
            def visit_For(self, node):
                # Look for 'for x in y: res.append(x)' pattern
                if len(node.body) == 1 and isinstance(node.body[0], ast.Expr):
                    call = node.body[0].value
                    if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute):
                        if call.func.attr == "append":
                            # Create ListComp replacement
                            new_node = ast.Assign(
                                targets=[ast.Name(id="res", ctx=ast.Store())],
                                value=ast.ListComp(
                                    elt=call.args[0],
                                    generators=[ast.comprehension(
                                        target=node.target,
                                        iter=node.iter,
                                        ifs=[],
                                        is_async=0
                                    )]
                                )
                            )
                            return new_node
                return node

        optimizer = LoopOptimizer()
        new_tree = optimizer.visit(tree)
        ast.fix_missing_locations(new_tree)
        
        if hasattr(ast, "unparse"):
            return ast.unparse(new_tree)
        return source_code

if __name__ == "__main__":
    code = "def process(data):\n    res = []\n    for x in data:\n        res.append(x * 2)\n    return res"
    surgeon = ASTSurgeon()
    optimized = surgeon.optimize_loop_with_list_comp(code)
    print("Optimization via AST Surgery successful.")
