import logging
from src.critique import CausalCritique, SelfReferentialCritique

class CorrectorAgent:
    def correct(self, original_code, failed_code, critique):
        """
        Generates a new prompt for the CoderAgent based on the critique.
        Handles both simple CausalCritique and rich SelfReferentialCritique.
        """
        
        logging.info("CorrectorAgent: Received critique, formulating new prompt.")
        
        # Base prompt components
        prompt_header = "The previous attempt to refactor the code failed."
        original_code_block = f"Original Code:\n```python\n{original_code}\n```"
        failed_code_block = f"Failed Code:\n```python\n{failed_code}\n```"
        instruction = "Please try again to refactor the code, taking all feedback into account. The goal is to improve the time complexity of the code while ensuring all tests pass."

        # Build prompt based on critique type
        if isinstance(critique, SelfReferentialCritique):
            logging.info("CorrectorAgent: Generating meta-prompt from SelfReferentialCritique.")

            reason = f"Critique: {critique.reason}"
            confidence = f"The evaluator's confidence in this critique is {critique.evaluation_confidence} (Uncertainty: {critique.uncertainty_level})."

            history_section = ""
            if critique.historical_context:
                history_intro = "This failure is semantically similar to past failures:"
                history_points = "\\n".join([f"- {h['critique_summary']} (run_id: {h['run_id']})" for h in critique.historical_context])
                history_section = f"{history_intro}\\n{history_points}"

            prompt = f"""{prompt_header}
{reason}
{confidence}

{history_section}

{original_code_block}
{failed_code_block}

{instruction}
"""
        else: # Fallback for simple CausalCritique or string
            logging.info("CorrectorAgent: Generating simple prompt from basic critique.")
            critique_reason = str(critique)
            prompt = f"""{prompt_header}

Causal Critique: {critique_reason}

{original_code_block}
{failed_code_block}

{instruction}
"""

        logging.info("CorrectorAgent: Created new instruction.")
        return prompt.strip()