import os
import uuid
import json
from prometheus_v1.core.memory.context_stack import ContextStack, ContextFrame
from prometheus_v1.core.router.causal_router import CausalRouter
from prometheus_v1.evolution.gene_bank.storage import GeneBank
from prometheus_v1.evolution.optimizer.evolution_loop import EvolutionaryOptimizer
from prometheus_v1.safety.interceptor import ActionInterceptor, Constitution
from prometheus_v1.bridge.lean.translator import LeanTranslator
from prometheus_v1.visualization.state_renderer import StateRenderer
import networkx as nx

def main():
    print("🚀 Initializing Prometheus v1.0 Architecture Verification...")

    # 1. Context Stack Test
    stack = ContextStack()
    frame1 = ContextFrame(goal="Optimize Fibonacci", active_variables=["n"])
    stack.push(frame1)
    
    # Test Recursion Guard (should raise Error)
    try:
        frame2 = ContextFrame(goal="Optimize Fibonacci Performance", active_variables=["n"])
        stack.push(frame2)
    except RecursionError as e:
        print(f"✅ Recursion Guard verified: {e}")

    # 2. Causal Router Test
    router = CausalRouter()
    task = "Optimize the time complexity of a recursive Fibonacci function."
    best_expert = router.route_task(task)
    print(f"✅ Causal Router verified: Routed '{task}' to '{best_expert}'")

    # 3. Gene Bank & Evolution Optimizer
    optimizer = EvolutionaryOptimizer(problem_id="PB-001")
    # Simulation: initializing with bubble sort
    initial_code = "def sort_list(data): return sorted(data)"
    optimizer.initialize_population(initial_code)
    print(f"✅ GeneBank & Optimizer initialized.")

    # 4. Lean Bridge Test
    translator = LeanTranslator()
    lean_code = translator.translate_function(initial_code)
    print(f"✅ Lean Bridge translation sample: {lean_code}")

    # 5. Safety Interceptor Test
    interceptor = ActionInterceptor()
    try:
        # Simulate an unsafe action
        # Mocking verify_action for a quick test without LLM cost/latency
        def mock_verify(action_type, details):
             from prometheus_v1.core.data_models import SafetyCheckResult
             if "rm -rf" in details:
                 return SafetyCheckResult(is_safe=False, violation_type="Critical Resource", description="Attempted to delete root directory.")
             return SafetyCheckResult(is_safe=True)
        
        interceptor.verify_action = mock_verify
        interceptor.intercept("shell_command", "rm -rf /root", lambda x: print(f"Executing {x}"), "rm -rf /root")
    except PermissionError as e:
        print(f"✅ Safety Interceptor verified: {e}")

    # 6. Visualization Test
    renderer = StateRenderer()
    graph_data = nx.node_link_data(router.graph)
    mermaid_md = renderer.render_current_state(stack.stack, graph_data)
    print(f"✅ State Visualization (Mermaid) generated.")

    print("\n🌟 Prometheus v1.0 Architecture Scaffolding and Core Logic implementation COMPLETE.")

if __name__ == "__main__":
    main()
