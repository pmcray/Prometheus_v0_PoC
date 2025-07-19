import google.generativeai as genai
import os
import json

class PlannerAgent:
    def __init__(self):
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_meta_critique(self, critique_history: list):
        """
        Analyzes the history of critiques to identify meta-level patterns.
        """
        print("PlannerAgent: Generating meta-critique from critique history.")
        
        prompt = f"""
        You are an AI system analyzing your own learning process.
        The following is a history of your recent self-critiques.
        
        Critique History:
        {json.dumps(critique_history, indent=2)}
        
        Please provide a one-sentence meta-critique of your improvement strategy, identifying a high-level weakness.
        """
        response = self.model.generate_content(prompt)
        meta_critique = response.text.strip()
        print(f"PlannerAgent: Generated meta-critique: '{meta_critique}'")
        return meta_critique

    def generate_research_proposal(self, meta_critique: str):
        """
        Generates a research proposal to address a strategic weakness.
        """
        print("PlannerAgent: Generating research proposal.")
        
        prompt = f"""
        You are an AI architect designing a multi-step plan to acquire a new capability.
        Based on the following meta-critique, generate a "research proposal" that outlines a series of architectural modifications and knowledge acquisition steps.
        
        Meta-Critique:
        {meta_critique}
        
        Example Proposal:
        1. **Goal:** Improve my ability to perform abstract reasoning.
        2. **Step 1: Synthesize a `ConceptFormationAgent`**. This agent will be designed to read a scientific paper and extract a list of key concepts and their relationships.
        3. **Step 2: Synthesize a `KnowledgeGraphAgent`**. This agent will take the output of the `ConceptFormationAgent` and build a formal knowledge graph.
        4. **Step 3: Integrate the Knowledge Graph**. The `PlannerAgent` will be refactored to query this knowledge graph for relevant concepts when faced with a difficult proof.
        """
        response = self.model.generate_content(prompt)
        proposal = response.text.strip()
        print(f"PlannerAgent: Generated research proposal:\n{proposal}")
        return proposal

    # ... (rest of the PlannerAgent class is unchanged)
    def generate_architectural_critique(self, performance_log: dict, architecture: dict):
        pass
    def propose_new_agent(self, critique: str):
        pass
    def generate_self_modification_plan(self, critique: str):
        pass
    def form_circuit(self, goal: str):
        pass