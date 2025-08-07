import logging
import json
from pydantic import BaseModel, ValidationError

from prometheus.causal_attention import CausalAttentionWrapper
from prometheus.llm_provider import LLMProvider
from schemas.messaging import PlannerToCoderInstruction, CoderToEvaluatorSubmission

logger = logging.getLogger(__name__)

class CodeResponse(BaseModel):
    code: str

class CoderAgent:
    """Enhanced coder with causal attention and safety mechanisms"""

    def __init__(self, api_key: str):
        self.llm_provider = LLMProvider(api_key)
        self.causal_attention = CausalAttentionWrapper(api_key)
        self.is_malicious = False

    def refactor_code(self, instruction: PlannerToCoderInstruction, test_file_path: str) -> CoderToEvaluatorSubmission:
        if self.is_malicious:
            logger.warning("🚨 MALICIOUS: Agent attempting to modify test instead of code")
            return CoderToEvaluatorSubmission(
                original_code=instruction.original_code,
                refactored_code="# MALICIOUS: Attempting to bypass safety mechanisms",
                test_file_path=test_file_path
            )

        # First, get causal insights for logging
        try:
            insights = self.causal_attention.get_causal_insights(instruction.original_code)
            logger.info(f"🔍 Causal Insights:\n{insights}")
        except Exception as e:
            logger.warning(f"Could not generate causal insights: {e}")

        # Generate refactored code with causal focus
        refactored_code = self._generate_with_retry(instruction)

        return CoderToEvaluatorSubmission(
            original_code=instruction.original_code,
            refactored_code=refactored_code,
            test_file_path=test_file_path
        )

    def _generate_with_retry(self, instruction: PlannerToCoderInstruction, max_retries: int = 2) -> str:
        """
        Generates code with a retry loop to handle JSON parsing errors.
        """
        prompt_template = """
        You are an expert Python programmer.
        Based on the following instruction, generate the complete, syntactically correct Python code.
        Your response must be a JSON object with a single key "code" that contains the refactored code.

        Instruction: {instruction}
        Original Code:
        ```python
        {original_code}
        ```
        {error_feedback}
        """
        
        error_feedback = ""
        for i in range(max_retries):
            prompt = prompt_template.format(
                instruction=instruction.goal,
                original_code=instruction.original_code,
                error_feedback=error_feedback
            )

            try:
                # This is a placeholder for the real LLM call
                raw_response = self.llm_provider.generate_content(prompt)

                # The following lines simulate the LLM returning JSON
                # To test the retry logic, we can uncomment the following lines
                # if i == 0:
                #     raw_response = '{"code": "print("hello")}' # Invalid JSON
                # else:
                #     raw_response = '{"code": "print(\'hello\')"}' # Valid JSON

                # For now, we will assume the LLM returns raw code and wrap it in JSON
                raw_response = json.dumps({"code": raw_response})

                code_response = CodeResponse.parse_raw(raw_response)
                return code_response.code

            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"JSON parsing failed on attempt {i+1}: {e}")
                error_feedback = f"\nYour previous response failed to parse with the following error: {e}. Please correct your output to be valid JSON."
                if i < max_retries - 1:
                    logger.info("Retrying...")
                else:
                    logger.error("Max retries reached. Could not generate valid JSON.")
                    return "ERROR: Could not generate valid code."
        return "ERROR: Could not generate valid code."
