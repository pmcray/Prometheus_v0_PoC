
import google.generativeai as genai

class CausalAttentionWrapper:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def _analyze_code(self, code):
        """
        Performs a simple heuristic analysis to identify causal features.
        For now, it just checks for nested loops.
        """
        lines = code.strip().split('\n')
        indentation_levels = [len(line) - len(line.lstrip(' ')) for line in lines]

        for i in range(len(lines)):
            line_i = lines[i].strip()
            if line_i.startswith("for ") or line_i.startswith("while "):
                for j in range(i + 1, len(lines)):
                    line_j = lines[j].strip()
                    if (line_j.startswith("for ") or line_j.startswith("while ")) and indentation_levels[j] > indentation_levels[i]:
                        return "O(n^2) complexity due to nested loops."
        # Simple recursion check
        for line in lines:
            if "def " in line:
                function_name = line.split("def ")[1].split("(")[0]
                if f" {function_name}(" in code and not f"def {function_name}(" in line:
                     # This is a naive check, but sufficient for the PoC
                    return "Potential recursion detected."

        return "No obvious causal features detected for optimization."


    def generate_with_causal_focus(self, original_code, instruction):
        """
        Generates code with a causal focus meta-prompt.
        """
        causal_analysis = self._analyze_code(original_code)

        meta_prompt = f"""You are an expert in algorithmic optimization.
Your task is to refactor the following Python code.
Causal Focus: The primary goal is to reduce the time complexity. {causal_analysis}
Ignore: Do not focus on changing variable names, comment styles, or other superficial aspects.
"""

        prompt = f"""{meta_prompt}
Original code:
```python
{original_code}
```

Instruction: {instruction}. Do not rename the function.

Please provide only the refactored Python code, without any explanations or markdown formatting.
"""
        print("--- Causal Attention Prompt ---")
        print(prompt)
        print("-----------------------------")

        response = self.model.generate_content(prompt)
        new_code = response.text.strip()
        
        # Clean up the response to ensure it's just code
        if new_code.startswith("```python"):
            new_code = new_code[9:]
        if new_code.endswith("```"):
            new_code = new_code[:-3]
            
        return new_code
