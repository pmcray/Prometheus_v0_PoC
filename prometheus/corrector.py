import logging
from prometheus.llm_provider import LLMProvider
from prometheus.memory import MemoryAgent
from schemas.messaging import CausalCritique, PlannerToCoderInstruction

logger = logging.getLogger(__name__)

class CorrectorAgent:
    """
    Generates a new instruction for the CoderAgent based on a critique,
    augmented with examples from memory.
    """

    def __init__(self, api_key: str, memory: MemoryAgent):
        self.llm_provider = LLMProvider(api_key)
        self.memory = memory

    def correct(self, critique: CausalCritique, original_code: str, failed_code: str) -> PlannerToCoderInstruction:
        """
        Generates a new prompt for the CoderAgent based on the critique and similar past failures.
        """
        logger.info("CorrectorAgent: Received critique - " + critique.reason)

        # 1. Query memory for similar failures
        query_document = f"""
        Critique: {critique.reason}
        Failed Code:
        {failed_code}
        """
        similar_failures = self.memory.retrieve_similar_failures(query_document, k=2)

        # 2. Construct few-shot examples from memory
        few_shot_examples = ""
        if similar_failures:
            few_shot_examples += "\n\n### Previous Similar Failures to Avoid:\n"
            for i, failure in enumerate(similar_failures):
                payload = failure.get("payload", {})
                few_shot_examples += f"\n**Failure Example {i+1} (run-id: {payload.get('run_id', 'N/A')}):**\n"
                few_shot_examples += f"*Critique:* '{payload.get('reason', 'N/A')}'\n"
                few_shot_examples += f"*Failed Attempt:*\n```python\n{payload.get('final_code', '')}\n```\n"
        
        # 3. Construct the final prompt
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
{few_shot_examples}
Your task is to generate a new, single-sentence goal for the CoderAgent that specifically addresses the reason for the failure, taking into account the historical failures to avoid repeating them.
For example, if the critique says 'the nested loop remains', a good goal would be 'Replace the nested loop with a more efficient single-loop approach, such as using a dictionary lookup.'
Your response should be only the new goal.
"""

        new_goal = self.llm_provider.generate_content(prompt)

        logger.info("CorrectorAgent: Created new memory-augmented instruction.")

        return PlannerToCoderInstruction(
            original_code=original_code,
            goal=new_goal,
        )
