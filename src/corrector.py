import logging
from src.critique import SelfReferentialCritique

class CorrectorAgent:
    def correct(self, original_code, failed_code, critique: SelfReferentialCritique):
        """
        Generates a new, highly-contextualized prompt for the CoderAgent
        based on the structured SelfReferentialCritique.
        """
        
        logging.info("CorrectorAgent: Received structured critique. Synthesizing meta-prompt.")

        # Start building the prompt
        prompt_parts = ["The previous attempt to refactor the code failed."]

        # Add the core reason
        prompt_parts.append(f"Critique: {critique.reason}")

        # Add causal analysis details
        if critique.causal_analysis:
            ca_text = (
                f"The causal analysis shows a complexity change from "
                f"{critique.causal_analysis.from_complexity} to {critique.causal_analysis.to_complexity} "
                f"({critique.causal_analysis.change_type})."
            )
            prompt_parts.append(ca_text)

        # Add confidence level
        prompt_parts.append(f"The evaluator's confidence in this critique is {critique.evaluation_confidence*100:.0f}%.")

        # Add historical context if available
        if critique.historical_context:
            history_summary = "; ".join([hist.critique_summary for hist in critique.historical_context])
            prompt_parts.append(f"This failure is semantically similar to past failures: {history_summary}")

        # Add dynamic analysis if available
        if critique.dynamic_analysis and critique.dynamic_analysis.status == "COMPLETED":
            da = critique.dynamic_analysis
            time_delta = da.execution_time_ms.delta
            mem_delta = da.peak_memory_mb.delta

            time_trend = "slower" if time_delta > 0 else "faster"
            mem_trend = "higher" if mem_delta > 0 else "lower"

            dynamic_summary = (
                f"Dynamic analysis shows your solution is {abs(time_delta):.2f}ms {time_trend} "
                f"and has a {abs(mem_delta):.2f}MB {mem_trend} memory footprint."
            )
            prompt_parts.append(dynamic_summary)
            if time_delta > 0 or mem_delta > 0:
                prompt_parts.append("Aim for a solution that balances both time and memory efficiency.")


        # Final instruction
        prompt_parts.append("Your next attempt must address the core algorithmic structure, not just superficial details.")

        # Assemble the final prompt
        instruction = "\n".join(prompt_parts)
        
        prompt = f"""{instruction}
        
Original Code:
```python
{original_code}
```

Failed Code:
```python
{failed_code}
```

Please try again to refactor the code, taking all the above feedback into account.
The goal is to improve the time complexity of the code.
"""
        logging.info("CorrectorAgent: Created new meta-instruction.")
        return prompt