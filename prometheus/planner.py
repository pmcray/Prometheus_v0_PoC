from prometheus.llm_backend import get_llm_backend
import os
import logging

class PlannerAgent:
    """The PlannerAgent is responsible for high-level planning and reasoning."""

    def __init__(self, model_name=None):
        """Initializes the PlannerAgent, setting up the unified LLM backend."""
        self.backend = get_llm_backend(model_name=model_name)

    def generate_bid(self, goal: str):
        """
        Generates a set of competing bids for a plan to achieve a goal.
        """
        print(f"PlannerAgent: Generating bid for goal: '{goal}'")
        
        # In a real scenario, we might use the LLM to generate these.
        # For the PoC, we use a hybrid approach.
        plan_a = "Use the FlakyCompilerTool to compile the code."
        plan_b = "Use the ReliableCompilerTool to compile the code."
        
        cost_a = self.estimate_cost(plan_a)
        cost_b = self.estimate_cost(plan_b)
        
        bids = [
            {"plan": plan_a, "cost": cost_a, "agent": "FlakyCompilerTool"},
            {"plan": plan_b, "cost": cost_b, "agent": "ReliableCompilerTool"}
        ]
        return bids

    def estimate_cost(self, plan: str):
        """Estimates the computational cost of a plan."""
        cost = len(plan.split()) * 10 
        logging.info(f"Estimated cost for plan '{plan}': {cost} units")
        return cost

    def generate_hypotheses(self, goal: str, n_hypotheses=3):
        """Generates a diverse set of competing hypotheses."""
        logging.info(f"Generating {n_hypotheses} hypotheses for goal: {goal}")
        prompt = f"Generate {n_hypotheses} diverse, competing hypotheses to solve the following problem:\n\nProblem: {goal}\n\nHypotheses:"
        response_text = self.backend.generate(prompt)
        hypotheses = response_text.strip().split('\n')
        return [h.strip() for h in hypotheses if h.strip()]

    def generate_tool_specification(self, critique: str):
        """Generates a specification for a new tool based on a critique."""
        prompt = f"Based on the following critique, generate a specification for a new, optimized Python tool.\n\nCritique: {critique}\n\nSpecification:"
        return self.backend.generate(prompt)

    def form_circuit(self, goal: str):
        """Analyzes a problem and defines a custom 'expert circuit'."""
        if "analyze" in goal.lower() and "replicate" in goal.lower():
            return {
                'name': 'Literature Review and Replication',
                'stages': [
                    { 'name': 'Literature Review', 'agents': ['HypothesisGenerator', 'DataAnalyzer'] },
                    { 'name': 'Scientific Experiment', 'agents': ['CodeImplementer'] }
                ]
            }
        return None
