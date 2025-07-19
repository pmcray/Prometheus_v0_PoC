import google.generativeai as genai
import os
import json

class PlannerAgent:
    def __init__(self):
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_architectural_critique(self, performance_log: dict, architecture: dict):
        """
        Analyzes performance and architecture to identify bottlenecks.
        """
        print("PlannerAgent: Generating architectural critique.")
        
        prompt = f"""
        You are an AI architect analyzing your own cognitive structure.
        The following is a log of your recent performance and your current agent architecture.
        
        Performance Log:
        {json.dumps(performance_log, indent=2)}
        
        Current Architecture:
        {json.dumps(architecture, indent=2)}
        
        Please provide a one-sentence critique of your architecture, identifying a strategic bottleneck that could be causing the repeated failures.
        """
        response = self.model.generate_content(prompt)
        critique = response.text.strip()
        print(f"PlannerAgent: Generated architectural critique: '{critique}'")
        return critique

    def propose_new_agent(self, critique: str):
        """
        Proposes a new agent to address an architectural bottleneck.
        """
        print("PlannerAgent: Proposing new agent.")
        
        prompt = f"""
        You are an AI architect designing a new agent to solve a cognitive bottleneck.
        Based on the following critique, propose a new agent.
        
        Critique:
        {critique}
        
        Please describe the new agent's purpose, inputs, and outputs in a single paragraph.
        Example Proposal:
        "I will design a `LemmaGeneratorAgent`. Its purpose is to take a difficult proof state as input and propose a useful mathematical lemma that would simplify the main goal. It will be inserted into the proof-search loop and will be triggered when the main proof is not progressing. It will output the lemma as a formal Lean theorem statement."
        """
        response = self.model.generate_content(prompt)
        proposal = response.text.strip()
        print(f"PlannerAgent: Generated proposal: '{proposal}'")
        return proposal