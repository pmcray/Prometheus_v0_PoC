from src.system_state import SystemState
from src.proof_tree import ProofTree
from src.strategy_archive import StrategyArchive

class PlannerAgent:
    def plan(self, goal: str, proof_content: str = None):
        # ... (implementation unchanged)
        pass

    def choose_next_step(self, proof_tree: ProofTree, strategy_archive: StrategyArchive, current_theorem: str):
        """
        Analyzes the proof tree and uses the strategy archive to choose the next step.
        """
        print("PlannerAgent: Analyzing proof tree and consulting strategy archive.")
        
        relevant_strategies = strategy_archive.get_relevant_strategies(current_theorem)
        
        if relevant_strategies:
            strategies_str = "\n".join(f"- {s}" for s in relevant_strategies)
            print(f"PlannerAgent: Found relevant strategies:\n{strategies_str}")
            # In a real implementation, this would be part of the prompt to the LLM.
            # For this PoC, we just log that we have them.

        promising_node = proof_tree.find_most_promising_node()
        
        if promising_node:
            print(f"PlannerAgent: Chose node with tactic '{promising_node.tactic}' to expand.")
        else:
            print("PlannerAgent: No promising nodes found.")
            
        return promising_node