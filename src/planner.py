from src.system_state import SystemState

class PlannerAgent:
    def plan(self, system_state: SystemState, goal: str):
        """
        Analyzes the system state and generates a plan based on the goal.
        """
        print(f"PlannerAgent: Received goal - '{goal}'")
        
        if "evolve" in goal.lower():
            # For v1.1, the evolutionary target is hardcoded.
            target_file = "toy_problem/inefficient_sort.py"
            test_file = "toy_problem/test_inefficient_sort.py"
            generations = 5
            population_size = 10
            
            plan = {
                "type": "evolution",
                "target_file": target_file,
                "test_file": test_file,
                "generations": generations,
                "population_size": population_size
            }
            print(f"PlannerAgent: Created evolutionary plan for {target_file}")
            return plan
            
        else: # Default to self-modification
            target_file = "src/evaluator.py"
            instruction = "Refactor the `_analyze_complexity` method in the EvaluatorAgent to be more efficient."
            plan = {
                "type": "refactor",
                "target_file": target_file,
                "instruction": instruction
            }
            print(f"PlannerAgent: Created refactoring plan for {target_file}")
            return plan