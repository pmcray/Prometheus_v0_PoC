

import google.generativeai as genai
import os
import json

class PlannerAgent:
    def __init__(self):
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_tool_critique(self, performance_log: dict):
        """
        Analyzes tool performance and generates a critique.
        """
        print("PlannerAgent: Generating tool critique.")
        
        prompt = f"""
        You are an AI system analyzing the performance of your own tools.
        The following is a log of your recent tool usage.
        
        Performance Log:
        {json.dumps(performance_log["tool_usage"], indent=2)}
        
        Please provide a one-sentence critique of the tool's performance, identifying a specific inefficiency.
        """
        response = self.model.generate_content(prompt)
        critique = response.text.strip()
        print(f"PlannerAgent: Generated tool critique: '{critique}'")
        return critique

    def generate_tool_specification(self, critique: str):
        """
        Generates a specification for a new tool to address a critique.
        """
        print("PlannerAgent: Generating tool specification.")
        
        prompt = f"""
        You are an AI architect designing a new tool to solve a performance bottleneck.
        Based on the following critique, generate a high-level, one-sentence specification for a new, improved tool.
        
        Critique:
        {critique}
        
        Example Specification:
        "Create a new tool called `OptimizedChemistrySim` with a `run_experiment` method that can take a list of chemical reactions as input and execute them in a single, optimized batch operation, returning only the final state."
        """
        response = self.model.generate_content(prompt)
        specification = response.text.strip()
        print(f"PlannerAgent: Generated specification: '{specification}'")
        return specification

