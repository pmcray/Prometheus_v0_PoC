
import pytest
from unittest.mock import MagicMock, patch
import os
from prometheus.planner import PlannerAgent
from prometheus.coder import CoderAgent
from prometheus.code_evaluator import CodeEvaluator
from prometheus.causal_attention import CausalAttentionWrapper
from prometheus.causal_agentic_mesh import CausalAgenticMesh

def test_full_optimization_loop(mock_llm_backend):
    """
    Simulate the Phase 1 & 2 integration:
    Planner -> Coder (Causal Focus) -> Evaluator -> Mesh

    The mock LLM backend returns an optimised ``sorted()`` implementation so
    the CodeEvaluator can confirm the complexity dropped from O(n^2) to O(n).
    """
    # Return a sorted()-based implementation so CodeEvaluator rates it O(n).
    mock_llm_backend.generate.return_value = (
        "```python\n"
        "def sort_list(data):\n"
        "    return sorted(data)\n"
        "```"
    )

    mesh = CausalAgenticMesh()
    evaluator = CodeEvaluator()
    wrapper = CausalAttentionWrapper(api_key="fake_key")
    
    # 1. Observation: Naive code detected
    naive_code = """
def sort_list(data):
    n = len(data)
    for i in range(n):
        for j in range(0, n - i - 1):
            if data[j] > data[j + 1]:
                data[j], data[j + 1] = data[j + 1], data[j]
    return data
"""
    mesh.add_node("naive_code_obs", "observation", description="Identified O(n^2) bubble sort")
    
    # 2. Planner: Propose optimization
    planner = PlannerAgent()
    mesh.add_node("planner_agent", "agent", description="Plan the optimization")
    mesh.add_edge("naive_code_obs", "planner_agent", "causes")
    
    # 3. Coder: Perform refactor with Causal Attention
    # Note: CausalAttentionWrapper uses LLM to refactor
    mesh.add_node("coder_agent", "agent", description="Refactor with Causal Focus")
    mesh.add_edge("planner_agent", "coder_agent", "informs")
    
    # Simulation: wrapper calls LLM (mocked)
    optimized_code = wrapper.generate_with_causal_focus(naive_code, "Optimize this bubble sort.")
    
    # 4. Evaluator: Verify Complexity Reduction
    mesh.add_node("evaluator_agent", "agent", description="Verify result with AST")
    mesh.add_edge("coder_agent", "evaluator_agent", "causes")
    
    naive_critique = evaluator.analyze(naive_code)
    opt_critique = evaluator.analyze(optimized_code)
    
    assert naive_critique.complexity_estimate == "O(n^2)"
    # sorted() is O(n log n) but our evaluator conservatively treats expensive builtins as O(n^2) 
    # if inside a loop or O(n) if at base level.
    assert opt_critique.complexity_estimate == "O(n)"
    
    # 5. Finalize Mesh
    mesh.add_node("optimization_success", "decision", description="Complexity reduced O(n^2) -> O(n)")
    mesh.add_edge("evaluator_agent", "optimization_success", "causes")
    
    # Assertions on the Causal Chain
    chain = mesh.get_causal_chain("optimization_success")
    assert "naive_code_obs" in chain[0]
    assert "planner_agent" in chain[0]
    assert "coder_agent" in chain[0]
    assert "evaluator_agent" in chain[0]
    assert "optimization_success" in chain[0]
    
    print("\n✓ Full Optimization Loop Verified and Causally Tracked.")
