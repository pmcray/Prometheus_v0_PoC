import logging
from src.critique import SelfReferentialCritique
from src.llm_provider import LLMProvider
from src.gene_archive import GeneArchive

class CorrectorAgent:
    def __init__(self, llm_provider: LLMProvider, gene_archive: GeneArchive):
        self.llm_provider = llm_provider
        self.gene_archive = gene_archive

    def correct(self, original_code, failed_code, critique: SelfReferentialCritique, attempt_number: int):
        """
        Generates a new, highly-contextualized prompt for the CoderAgent
        based on the structured SelfReferentialCritique. After several failed
        attempts, it will try an analogical search for a solution pattern.
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


        # If we are still failing after a few attempts, try analogical search
        if attempt_number >= 1: # Trigger on the 2nd attempt (index 1)
            logging.info("Attempting analogical search for a solution pattern...")
            problem_prompt = f"Describe the core problem solved by this Python code in a single, abstract sentence.\n\n```python\n{original_code}\n```"
            abstract_problem = self.llm_provider.generate(problem_prompt).strip()

            if abstract_problem:
                logging.info(f"Abstracted problem: '{abstract_problem}'")
                solution_pattern = self.gene_archive.get_solution_pattern(abstract_problem)
                if solution_pattern:
                    logging.info(f"Found analogous solution pattern: '{solution_pattern}'")
                    hint = f"HINT: Let's try an analogy. A similar problem was solved with this pattern: '{solution_pattern}'. Try to apply this pattern here."
                    prompt_parts.append(hint)
                else:
                    logging.info("No analogous solution pattern found in the gene archive.")
            else:
                logging.warning("Could not abstract the problem, skipping analogical search.")


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