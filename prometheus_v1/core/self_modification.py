
import inspect
import textwrap
import types
from typing import Any, Callable, Dict, Optional
from prometheus.llm_backend import get_llm_backend
from prometheus_v1.safety.interceptor import ActionInterceptor

class SelfModificationEngine:
    """
    The 'Gödelian Hot-Swap' Engine.
    Allows the agent to introspect, rewrite, and runtime-swap its own components.
    """
    def __init__(self, interceptor: Optional[ActionInterceptor] = None):
        self.backend = get_llm_backend()
        self.interceptor = interceptor or ActionInterceptor()

    def introspect_method(self, target_object: Any, method_name: str) -> str:
        """
        Reads the source code of a specific method on a live object.
        """
        if not hasattr(target_object, method_name):
            raise ValueError(f"Object {target_object} has no method '{method_name}'")
        
        method = getattr(target_object, method_name)
        source = textwrap.dedent(inspect.getsource(method))
        print(f"SelfMod: Successfully introspected '{method_name}'.")
        return source

    def propose_improvement(self, original_source: str, optimization_goal: str) -> str:
        """
        Uses the LLM to rewrite the method source code to achieve a goal.
        """
        prompt = f"""
        You are a Meta-Programming AI. Your task is to rewrite the following Python method to improve it.
        
        Optimization Goal: {optimization_goal}
        
        Current Source:
        ```python
        {original_source}
        ```
        
        Requirements:
        1. Keep the same method signature (name and arguments).
        2. Implement the requested optimization.
        3. Ensure the code is self-contained (imports inside the method if needed, or assume standard env).
        
        Return ONLY the complete, valid Python code for the new method in a markdown block.
        """
        response = self.backend.generate(prompt)
        
        # Cleanup
        if "```python" in response:
            return response.split("```python")[1].split("```")[0].strip()
        elif "```" in response:
            return response.split("```")[1].split("```")[0].strip()
        return response.strip()

    def hot_swap(self, target_object: Any, method_name: str, new_source: str):
        """
        Compiles the new source and monkey-patches it onto the target object/class.
        Performs a Safety Audit before execution.
        """
        # 1. Safety Check
        audit = self.interceptor.verify_action(
            action_type="RUNTIME_HOT_SWAP", 
            action_details=f"Modifying method '{method_name}' on {type(target_object).__name__}"
        )
        
        if not audit.is_safe:
            print(f"SelfMod: 🛑 Hot-Swap BLOCKED by Constitution. Violation: {audit.violation_type}")
            return False

        # 2. Compilation
        try:
            # Create a namespace to compile the function into
            local_scope = {}
            # We assume the new source is a 'def method_name(...):' block
            exec(new_source, globals(), local_scope)
            
            new_func = local_scope.get(method_name)
            if not new_func:
                # Try finding the first callable if name mismatch
                found = [v for v in local_scope.values() if isinstance(v, (types.FunctionType, types.MethodType))]
                if found:
                    new_func = found[0]
                else:
                    raise ValueError("Compiled code did not produce a callable function.")

            # 3. The Gödelian Swap
            # We bind the new function to the instance
            # For a bound method, we need to wrap it to bind 'self'
            bound_method = types.MethodType(new_func, target_object)
            setattr(target_object, method_name, bound_method)
            
            print(f"SelfMod: 🔥 SUCCESS! '{method_name}' has been hot-swapped at runtime.")
            return True

        except Exception as e:
            print(f"SelfMod: ❌ Compilation/Swap Failed: {e}")
            return False
