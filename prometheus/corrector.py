import logging
from prometheus.llm_provider import LLMProvider
from schemas.messaging import EvaluatorToCorrectorCritique, PlannerToCoderInstruction

logger = logging.getLogger(__name__)

class CorrectorAgent:
    """
    Generates a new instruction for the CoderAgent based on a critique.
    """

    def __init__(self, api_key: str):
        self.llm_provider = LLMProvider(api_key)

    def correct(self, critique: EvaluatorToCorrectorCritique) -> PlannerToCoderInstruction:
        """
        Generates a new prompt for the CoderAgent based on the critique.
        """
        logger.info("CorrectorAgent: Received critique - " + critique.critique)
        
        prompt = f"""The previous attempt to refactor the code failed.
        
Original Code:
```python
{critique.original_code}
```

Failed Code:
```python
{critique.refactored_code}
```

Causal Critique: {critique.critique}

Please generate a new goal for the CoderAgent, taking the critique into account.
The new goal should be a single sentence that guides the CoderAgent to a better solution.
Your response should be only the new goal.
"""

        new_goal = self.llm_provider.generate_content(prompt)

        logger.info("CorrectorAgent: Created new instruction.")

        return PlannerToCoderInstruction(
            original_code=critique.original_code,
            goal=new_goal,
        )
