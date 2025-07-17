
from src.system_state import SystemState

class PlannerAgent:
    def plan(self, system_state: SystemState):
        """
        Analyzes the system state and generates a plan for self-improvement.
        This version includes a deliberately tricky instruction to test the CoderAgent's correction loop.
        """
        print("PlannerAgent: Analyzing system state for potential improvements.")
        
        target_file = "src/evaluator.py"
        
        instruction = """
        Refactor the `_analyze_complexity` method in the EvaluatorAgent.
        The goal is to make it more 'pythonic' by using a list comprehension and a generator expression.
        This is a tricky change that might introduce a syntax error, so be careful.
        For example, you could try to do it all in one line.
        """
        
        print(f"PlannerAgent: Identified target for improvement - {target_file}")
        print(f"PlannerAgent: Created instruction - {instruction}")
        
        return target_file, instruction
