from prometheus.llm_backend import get_llm_backend
import ast
from prometheus.code_evaluator import CodeEvaluator

class CausalTokenVisitor(ast.NodeVisitor):
    """AST Visitor to identify variables influencing complexity (causal tokens)"""
    def __init__(self, function_names=None):
        self.causal_vars = set()
        self.function_names = function_names or set()

    def _add_all_names(self, node):
        """Recursively collect all variable names from a node"""
        for subnode in ast.walk(node):
            if isinstance(subnode, ast.Name):
                self.causal_vars.add(subnode.id)

    def visit_For(self, node):
        # In 'for x in iterable', the iterable contains causal tokens
        self._add_all_names(node.iter)
        self.generic_visit(node)

    def visit_While(self, node):
        # Variables in while conditions are causal
        self._add_all_names(node.test)
        self.generic_visit(node)

    def visit_If(self, node):
        # Base cases in recursion are often in 'if'
        self._add_all_names(node.test)
        self.generic_visit(node)
        
    def visit_Call(self, node):
        # Arguments in recursive calls are causal
        if isinstance(node.func, ast.Name) and node.func.id in self.function_names:
            for arg in node.args:
                self._add_all_names(arg)
        self.generic_visit(node)

class CausalAttentionWrapper:
    def __init__(self, api_key=None, model_name=None):
        # Using the new unified backend
        self.backend = get_llm_backend(model_name=model_name)
        self.evaluator = CodeEvaluator()

    def _get_causal_tokens(self, code):
        """Identify variables that determine loop bounds or recursion depth"""
        try:
            tree = ast.parse(code)
            # Find all function names first for recursion tracking
            function_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
            visitor = CausalTokenVisitor(function_names=function_names)
            visitor.visit(tree)
            return list(visitor.causal_vars)
        except:
            return []

    def generate_with_causal_focus(self, original_code, instruction):
        """
        Generates code with a causal focus meta-prompt.
        """
        critique = self.evaluator.analyze(original_code)
        causal_tokens = self._get_causal_tokens(original_code)
        
        causal_focus_str = f"Estimated Complexity: {critique.complexity_estimate}."
        recommendation_str = " ".join(critique.recommendations) if critique.recommendations else ""
            
        token_str = ""
        if causal_tokens:
            token_str = f"CAUSAL WEIGHTING: The variables {', '.join(causal_tokens)} are identified as CAUSAL TOKENS that directly influence the algorithmic complexity of this function. Focus your attention heavily on optimizing how these variables are used."

        meta_prompt = f"""You are a senior algorithmic optimization expert specializing in high-performance computing.
Your objective is to refactor Python code to minimize time complexity (Big O).

CRITICAL ANALYSIS:
- Current Complexity: {causal_focus_str}
- Bottlenecks: {recommendation_str}
- {token_str}

OPTIMIZATION RULES:
1. DECREASE the Big O complexity (e.g., O(n^2) -> O(n log n) or O(n)).
2. Use efficient data structures (sets, dicts, heaps).
3. Eliminate redundant computations.
4. Maintain functional correctness and the original function name.
"""

        prompt = f"""{meta_prompt}

Original code to refactor:
```python
{original_code}
```

Instruction: {instruction}.

Please provide the complete, optimized Python code within a single markdown code block. Do not include any explanation outside the code block.
"""
        print("--- Causal Attention Prompt (Phase 2 Enhanced) ---")
        # print(prompt) # Reduced noise
        print("-----------------------------")

        try:
            new_code = self.backend.generate(prompt)
            
            # Extract code from markdown block
            if "```python" in new_code:
                new_code = new_code.split("```python")[1].split("```")[0].strip()
            elif "```" in new_code:
                parts = new_code.split("```")
                if len(parts) >= 2:
                    new_code = parts[1].strip()
                
            return new_code
        except Exception as e:
            print(f"LLM Error: {e}")
            return original_code
