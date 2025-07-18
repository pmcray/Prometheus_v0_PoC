from src.system_state import SystemState
from src.proof_tree import ProofTree

class PlannerAgent:
    def plan(self, system_state: SystemState, goal: str):
        # ... (implementation unchanged)
        pass

    def choose_next_step(self, proof_tree: ProofTree, critiques: list = []):
        """
        Analyzes the proof tree and critiques to choose the most promising node.
        """
        print("PlannerAgent: Analyzing proof tree and critiques.")
        
        # For now, the logic remains simple, but the prompt is now context-aware.
        # A more advanced implementation would use the critiques to prune the search tree.
        
        critiques_str = "\n".join(f"- {c}" for c in critiques)
        
        # This is where a more sophisticated planner would use the critiques.
        # For the PoC, we'll just log that the critiques are available.
        if critiques:
            print(f"PlannerAgent: Considering the following critiques:\n{critiques_str}")

        promising_node = proof_tree.find_most_promising_node()
        
        if promising_node:
            print(f"PlannerAgent: Chose node with tactic '{promising_node.tactic}' to expand.")
        else:
            print("PlannerAgent: No promising nodes found.")
            
        return promising_node