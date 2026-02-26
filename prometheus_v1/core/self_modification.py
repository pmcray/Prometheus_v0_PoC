
import inspect
import textwrap
import types
from typing import Any, Callable, Dict, Optional
from prometheus.llm_backend import get_llm_backend
from prometheus_v1.safety.interceptor import ActionInterceptor
from prometheus.safety.sandbox import RuntimeSandbox
from prometheus.safety.auditor import MultiLLMAuditor
from prometheus.lineage import ModelRegistry, LineageTracker
from prometheus.transfer import CrossDomainTransferLearner

class SelfModificationEngine:
    """
    The 'Gödelian Hot-Swap' Engine.
    Allows the agent to introspect, rewrite, and runtime-swap its own components.
    """
    def __init__(self, interceptor: Optional[ActionInterceptor] = None):
        self.backend = get_llm_backend()
        self.interceptor = interceptor or ActionInterceptor()
        self.sandbox = RuntimeSandbox()
        self.auditor = MultiLLMAuditor()
        self.registry = ModelRegistry()
        self.lineage = LineageTracker(self.registry)
        self.transfer = CrossDomainTransferLearner()

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

    def transfer_and_improve(self, target_object: Any, method_name: str, target_domain: str) -> bool:
        """
        Transfers strategic knowledge from other domains to improve this component.
        """
        # 1. Get cross-domain suggestions
        suggestions = self.transfer.suggest_cross_domain_strategy(target_domain)
        print(f"SelfMod: 🔄 Cross-Domain Suggestions for {target_domain}: {suggestions}")
        
        # 2. Introspect and propose improvement
        original_source = self.introspect_method(target_object, method_name)
        new_source = self.propose_improvement(original_source, f"Incorporate these cross-domain strategies: {suggestions}")
        
        # 3. Apply hot-swap
        return self.hot_swap(target_object, method_name, new_source)

    def hot_swap(self, target_object: Any, method_name: str, new_source: str):
        """
        Compiles the new source and monkey-patches it onto the target object/class.
        Performs a Safety Audit and a Sandboxed Test before execution.
        """
        # 1. Primary Safety Check (Constitution)
        audit = self.interceptor.verify_action(
            action_type="RUNTIME_HOT_SWAP", 
            action_details=f"Modifying method '{method_name}' on {type(target_object).__name__}"
        )
        
        if not audit.is_safe:
            print(f"SelfMod: 🛑 Hot-Swap BLOCKED by Constitution. Violation: {audit.violation_type}")
            return False

        # 2. Secondary LLM Audit (Multi-LLM Red Team)
        is_safe, audit_msg = self.auditor.audit_code(
            new_source, 
            f"Modifying method '{method_name}' on {type(target_object).__name__}"
        )
        if not is_safe:
            print(f"SelfMod: 🛑 Hot-Swap BLOCKED by Multi-LLM Auditor. Concerns:\n{audit_msg}")
            return False

        # 3. Sandbox Verification (Isolated Execution Test)
        # Try to run a basic sanity check of the code in the sandbox first
        print(f"SelfMod: 🛡️  Testing code in Sandbox...")
        success, result = self.sandbox.run_isolated(new_source, method_name)
        if not success:
             print(f"SelfMod: 🛑 Hot-Swap BLOCKED by Sandbox Failure: {result}")
             return False
        
        print(f"SelfMod: ✅ Sandbox test passed. Proceeding with hot-swap.")

        # 4. Automated Checkpoint (Lineage & Model Versioning)
        version_id = self.registry.checkpoint_system(
            code_files=["main.py", "prometheus_v1/core/self_modification.py"],
            weight_files=["performance_log.json", "state_history.json"]
        )
        print(f"SelfMod: 💾 System checkpoint created: {version_id}")

        # 5. Compilation & Deployment
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
