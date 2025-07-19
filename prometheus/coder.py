

import google.generativeai as genai
import os
import re

class CoderAgent:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def synthesize_agent(self, proposal: str):
        """
        Synthesizes the Python code for a new agent based on a proposal.
        """
        print("CoderAgent: Synthesizing new agent.")
        
        prompt = f"""
        You are an expert Python programmer.
        Based on the following proposal, generate the complete, syntactically correct Python code for the new agent class.
        The new agent should be a class with a single method, `run`, that takes the specified inputs and returns the specified outputs.
        
        Proposal:
        {proposal}
        """
        response = self.model.generate_content(prompt)
        code = response.text.strip().replace("```python", "").replace("```", "")
        
        # Save the new agent to a file
        agent_name = self._extract_agent_name(proposal)
        file_path = f"prometheus/{agent_name.lower()}.py"
        with open(file_path, "w") as f:
            f.write(code)
            
        print(f"CoderAgent: Synthesized agent and saved to {file_path}")
        return file_path

    def _extract_agent_name(self, proposal: str):
        # A more robust regex to extract the agent name from the proposal
        match = re.search(r"`([a-zA-Z_][a-zA-Z0-9_]*)`", proposal)
        if match:
            return match.group(1)
        return "new_agent"

