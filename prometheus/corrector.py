import logging
from prometheus.llm_provider import LLMProvider
from schemas.messaging import CausalCritique, PlannerToCoderInstruction

logger = logging.getLogger(__name__)

class CorrectorAgent:
    """
    Generates a new instruction for the CoderAgent based on a critique.
    """

    def __init__(self, api_key: str):
        self.llm_provider = LLMProvider(api_key)

    def correct(self, critique: CausalCritique, original_code: str, failed_code: str) -> PlannerToCoderInstruction:
        """
        Generates a new prompt for the CoderAgent based on the critique.
        """
        logger.info("CorrectorAgent: Received critique - " + critique.reason)
        
        prompt = f"""The previous attempt to refactor the code failed.
        
Original Code:
```python
{original_code}
```

Failed Code:
```python
{failed_code}
```

Causal Critique: {critique.reason}
AST Analysis: The change from the previous attempt was '{critique.analysis.change_type}' from {critique.analysis.from_value} to {critique.analysis.to_value}.

Your task is to generate a new, single-sentence goal for the CoderAgent that specifically addresses the reason for the failure.
For example, if the critique says 'the nested loop remains', a good goal would be 'Replace the nested loop with a more efficient single-loop approach, such as using a dictionary lookup.'
Your response should be only the new goal.
"""

        new_goal = self.llm_provider.generate_content(prompt)

        logger.info("CorrectorAgent: Created new instruction.")

        return PlannerToCoderInstruction(
            original_code=original_code,
            goal=new_goal,
        )
