import google.generativeai as genai
import os
import re

class CoderAgent:
    def __init__(self, api_key, compiler, analyzer, lean_tool, knowledge_agent):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.compiler = compiler
        self.analyzer = analyzer
        self.lean_tool = lean_tool
        self.knowledge_agent = knowledge_agent

    def synthesize_tool(self, specification: str):
        """
        Synthesizes the Python code for a new tool based on a specification.
        """
        print("CoderAgent: Synthesizing new tool.")
        
        prompt = f"""
        You are an expert Python programmer.
        Based on the following specification, generate the complete, syntactically correct Python code for the new tool class.
        The new tool should be a class with a no-argument constructor, a `run_experiment` method that takes a list of operations as input, and a `mix` method.
        
        Specification:
        {specification}
        """
        response = self.model.generate_content(prompt)
        code = response.text.strip().replace("```python", "").replace("```", "")
        
        # Save the new tool to a file
        tool_name = self._extract_tool_name(specification)
        file_path = f"prometheus/tools/{tool_name.lower()}.py"
        with open(file_path, "w") as f:
            f.write(code)
            
        print(f"CoderAgent: Synthesized tool and saved to {file_path}")
        return file_path

    def _extract_tool_name(self, specification: str):
        # A simple regex to extract the tool name from the specification
        match = re.search(r"`(.*?)`", specification)
        if match:
            return match.group(1)
        return "new_tool"

    # ... (rest of the CoderAgent class is unchanged)
    def synthesize_agent(self, proposal: str):
        pass