import google.generativeai as genai
import os
import json

class PlannerAgent:
    def __init__(self):
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_self_critique(self, performance_log: dict):
        """
        Analyzes the performance log and generates a self-critique.
        """
        print("PlannerAgent: Generating self-critique from performance log.")
        
        last_proof = list(performance_log["proofs"].values())[-1]
        
        prompt = f"""
        You are an AI system analyzing your own performance.
        The following is a log of your last attempt to prove a theorem.
        
        Log:
        {json.dumps(last_proof, indent=2)}
        
        Please provide a one-sentence critique of your performance, identifying a specific inefficiency.
        """
        response = self.model.generate_content(prompt)
        critique = response.text.strip()
        print(f"PlannerAgent: Generated critique: '{critique}'")
        return critique

    def generate_self_modification_plan(self, critique: str):
        """
        Generates a self-modification plan based on a critique.
        """
        print("PlannerAgent: Generating self-modification plan.")
        
        prompt = f"""
        You are an AI system planning to modify your own source code.
        Based on the following self-critique, generate a high-level, one-sentence plan to refactor the CoderAgent.
        
        Critique:
        {critique}
        
        Example Plan:
        "Refactor the CoderAgent's `generate_tactic` method to be more concise and to prioritize tactics that have been successful in the past, based on the StrategyArchive."
        """
        response = self.model.generate_content(prompt)
        plan = response.text.strip()
        print(f"PlannerAgent: Generated plan: '{plan}'")
        return plan

    def form_circuit(self, goal: str):
        # ... (existing method)
        pass