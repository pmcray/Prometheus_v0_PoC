from src.causal_attention import CausalAttentionWrapper

class CoderAgent:
    def __init__(self, api_key):
        self.causal_wrapper = CausalAttentionWrapper(api_key=api_key)

    def code(self, file_path, instruction):
        """
        Generates code based on an instruction from the PlannerAgent,
        using the CausalAttentionWrapper.
        """
        print("CoderAgent: Received instruction -", instruction)
        print("CoderAgent: Reading file -", file_path)
        with open(file_path, 'r') as f:
            original_code = f.read()

        print("CoderAgent: Generating code with causal focus...")
        new_code = self.causal_wrapper.generate_with_causal_focus(original_code, instruction)
        
        print("CoderAgent: Received new code.")
        return new_code, original_code