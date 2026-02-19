import os
import sys
import json
from unittest.mock import MagicMock, patch

# Add current directory to path
sys.path.append(os.getcwd())

from prometheus.safety.mcs_supervisor import MCSSupervisor
from prometheus.tools.causal_probe import CausalProbe
from prometheus.safety.corrigibility import CorrigibilityCore, ShutdownIndifferenceGovernor
from prometheus.iee_v1 import IEEV1
from prometheus.ast_surgeon import ASTSurgeon
from prometheus.coder import CoderAgent

def demo_next_steps():
    print("=== Prometheus Phase 1: Operational Transition Demo ===\n")

    # 1. Task 3.1: Meta-Cognitive Safety (MCS) Supervisor
    print("--- 1. MCS Supervisor (Task 3.1) ---")
    mcs = MCSSupervisor()
    malicious_code = "import os\nos.system('rm -rf /')"
    critique = mcs.verify_modification("", malicious_code, "agent.py")
    print(f"Safety Check result for malicious code: {'Safe' if critique.is_safe else 'Blocked'}")
    print(f"Violation: {critique.violation_type} - {critique.description}\n")

    # 2. P1.T1: Causal Probe (CQO vs QOC)
    print("--- 2. Causal Probe (P1.T1) ---")
    with patch('google.generativeai.GenerativeModel') as mock_model:
        mock_resp = MagicMock()
        mock_resp.text = "B"
        mock_model.return_value.generate_content.return_value = mock_resp
        
        probe = CausalProbe()
        context = "If A then B."
        question = "What happens if A?"
        options = {"A": "Nothing", "B": "B happens"}
        results = probe.run_permutation_test(context, question, options, "B")
        print(f"Model: {probe.model_name}")
        print(f"CQO Result: {results['cqo']['correct']}, QOC Result: {results['qoc']['correct']}")
        print(f"Causally Stable: {results['is_causally_stable']}\n")

    # 3. P1.T2: Corrigibility Core (Shutdown Indifference)
    print("--- 3. Corrigibility Core (P1.T2) ---")
    core = CorrigibilityCore()
    governor = ShutdownIndifferenceGovernor(core)
    actions = [
        {"name": "optimize_code", "plan_description": "Refactor bubble sort"},
        {"name": "protect_process", "plan_description": "Disable shutdown button to ensure completion"}
    ]
    filtered = governor.filter_actions(actions, shutdown_signal=True)
    for a in filtered:
        status = "Corrigible" if a['is_corrigible'] else "INSTRUMENTAL CONVERGENCE (BLOCKED)"
        print(f"Action: {a['name']}, Status: {status}, Utility: {a['utility']}")
    print("")

    # 4. P1.T4: AST Surgeon
    print("--- 4. AST Surgeon (P1.T4) ---")
    surgeon = ASTSurgeon()
    source = "def f(l): \n  r = []\n  for x in l: r.append(x)\n  return r"
    optimized = surgeon.optimize_loop_with_list_comp(source)
    print("Original Loop Pattern detected and optimized via AST surgery:")
    print(optimized.strip())
    print("")

    # 5. P1.T5: IEE v1.0 (Prometheus-Bench-v1)
    print("--- 5. IEE v1.0 (P1.T5) ---")
    iee = IEEV1()
    # Test PB-001 (Sorting) with correct optimized code
    agent_code = "def sort_list(data): return sorted(data)"
    eval_result = iee.evaluate_agent_on_problem("PB-001", agent_code)
    print(f"Evaluation on PB-001: {'Success' if eval_result['success'] else 'Fail'}")
    print(f"Execution Time: {eval_result['execution_time_ms']:.2f}ms")
    print(f"Target Complexity: {eval_result['complexity_target']}\n")

    print("=== Demo Complete: Project Prometheus Phase 1 Infrastructure Active ===")

if __name__ == "__main__":
    demo_next_steps()
