
from src.system_state import SystemState
from src.proof_tree import ProofTree
from src.strategy_archive import StrategyArchive

class PlannerAgent:
    def plan(self, goal: str, experiment_results: list = []):
        """
        Generates a plan based on the goal.
        """
        print(f"PlannerAgent: Received goal - '{goal}'")
        
        if "discover" in goal.lower() and "chemistry" in goal.lower():
            
            if not experiment_results:
                hypothesis = "Mixing A and B seems like a good first step."
            else:
                # Simple learning: if the last experiment was successful, try heating.
                last_result = experiment_results[-1]
                if last_result["C"] > 0:
                    hypothesis = "The last experiment produced some C. Let's try heating the mixture to see if it improves the yield."
                else:
                    hypothesis = "The last experiment failed. Let's try mixing A and B again, just to be sure."

            plan = {
                "type": "run_experiment",
                "hypothesis": hypothesis
            }
            print(f"PlannerAgent: Created experimental plan with hypothesis: {hypothesis}")
            return plan
        
        # ... (rest of the plan method is unchanged)
        else:
            return {"type": "unknown"}

    def choose_next_step(self, proof_tree: ProofTree, strategy_archive: StrategyArchive, current_theorem: str):
        # ... (implementation unchanged)
        pass
