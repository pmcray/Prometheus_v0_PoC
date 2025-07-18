from src.system_state import SystemState
from src.proof_tree import ProofTree
from src.strategy_archive import StrategyArchive
from src.performance_logger import PerformanceLogger
from src.knowledge_agent import KnowledgeAgent

class PlannerAgent:
    def plan(self, goal: str, knowledge_agent: KnowledgeAgent = None, experiment_results: list = []):
        """
        Generates a plan based on the goal.
        """
        print(f"PlannerAgent: Received goal - '{goal}'")
        
        if "discover" in goal.lower() and "chemistry" in goal.lower():
            
            if not experiment_results:
                hypothesis = "Mixing A and B seems like a good first step."
            else:
                last_result = experiment_results[-1]
                # Inject a wasteful action for verification
                if last_result["A"] == 0 and last_result["B"] == 0 and len(experiment_results) == 1:
                    print("PlannerAgent: Intentionally proposing a wasteful action for verification.")
                    hypothesis = "Let's try mixing A and B again."
                elif last_result["A"] == 0 and last_result["B"] == 0:
                    hypothesis = "Now that A and B are depleted, let's try heating the mixture."
                else:
                    hypothesis = "Let's mix A and B."

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