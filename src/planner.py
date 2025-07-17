
class PlannerAgent:
    def plan(self, goal):
        """
        Generates a plan for the CoderAgent based on a high-level goal.
        """
        print("PlannerAgent: Received goal -", goal)
        # For v0.1, the plan is hardcoded.
        instruction = "Refactor the function 'inefficient_sort' to use a more efficient sorting algorithm."
        print("PlannerAgent: Created instruction -", instruction)
        return instruction
