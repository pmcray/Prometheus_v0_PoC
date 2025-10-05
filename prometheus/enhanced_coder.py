"""
Enhanced Coder Agent with structured communication and tool integration
Implements features from v0.19 onwards
"""

import google.generativeai as genai
import os
import logging
import json
import ast
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from .schemas.communication import (
    AgentMessage, MessageType, CoderToEvaluatorSubmission, PlannerToCoderInstruction
)

class EnhancedCoderAgent:
    """Enhanced Coder Agent with structured communication and robust JSON handling"""

    def __init__(self, api_key: str = None, max_retries: int = 3):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
            logging.warning("No API key provided - using mock responses")

        self.agent_id = "coder_agent"
        self.max_retries = max_retries

    def process_instruction(self, instruction_message: AgentMessage) -> AgentMessage:
        """Process a structured instruction from the planner"""

        if instruction_message.message_type != MessageType.PLANNER_TO_CODER:
            raise ValueError(f"Invalid message type: {instruction_message.message_type}")

        # Parse instruction
        instruction = PlannerToCoderInstruction(**instruction_message.payload)

        # Generate code
        refactored_code, reasoning, confidence = self._generate_refactored_code(instruction)

        # Create submission
        submission = CoderToEvaluatorSubmission(
            original_code=instruction.initial_code,
            refactored_code=refactored_code,
            reasoning=reasoning,
            confidence_score=confidence
        )

        # Create response message
        response_message = AgentMessage(
            message_type=MessageType.CODER_TO_EVALUATOR,
            sender=self.agent_id,
            recipient="evaluator_agent",
            timestamp=datetime.now().isoformat(),
            run_id=instruction_message.run_id,
            payload=submission.dict()
        )

        logging.info(f"CoderAgent generated refactored code for run {instruction_message.run_id}")
        return response_message

    def _generate_refactored_code(self, instruction: PlannerToCoderInstruction) -> tuple[str, str, float]:
        """Generate refactored code with retry logic for robust JSON output"""

        if not self.model:
            return self._mock_refactoring(instruction)

        # Construct prompt with structured requirements
        prompt = self._construct_refactoring_prompt(instruction)

        for attempt in range(self.max_retries):
            try:
                response = self.model.generate_content(prompt)
                response_text = response.text.strip()

                # Parse the response
                refactored_code, reasoning, confidence = self._parse_code_response(response_text)

                # Validate the code
                if self._validate_code_syntax(refactored_code):
                    return refactored_code, reasoning, confidence
                else:
                    if attempt < self.max_retries - 1:
                        prompt = self._create_retry_prompt(prompt, "Syntax error in generated code")
                        continue

            except Exception as e:
                logging.error(f"Error in code generation attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    prompt = self._create_retry_prompt(prompt, f"Generation error: {str(e)}")
                    continue

        # Fallback to mock if all retries failed
        logging.warning("All code generation attempts failed, using fallback")
        return self._mock_refactoring(instruction)

    def _construct_refactoring_prompt(self, instruction: PlannerToCoderInstruction) -> str:
        """Construct a detailed refactoring prompt"""

        prompt = f"""
        You are an expert Python programmer tasked with code optimization.

        TASK: {instruction.task_description}

        ORIGINAL CODE:
        ```python
        {instruction.initial_code}
        ```

        PERFORMANCE REQUIREMENTS:
        {json.dumps(instruction.performance_requirements, indent=2)}

        """

        if instruction.causal_focus:
            prompt += f"""
        CAUSAL ANALYSIS FOCUS:
        - Primary concerns: {instruction.causal_focus.get('primary_concerns', [])}
        - Attention targets: {instruction.causal_focus.get('attention_targets', [])}
        - Optimization hints: {instruction.causal_focus.get('optimization_hints', [])}

        """

        if instruction.meta_prompt:
            prompt += f"""
        SPECIFIC GUIDANCE:
        {instruction.meta_prompt}

        """

        prompt += """
        Please provide your response in the following JSON format:
        {
            "refactored_code": "your optimized Python code here",
            "reasoning": "detailed explanation of your optimization approach",
            "confidence_score": 0.85
        }

        Ensure the refactored code:
        1. Maintains functional correctness
        2. Improves algorithmic efficiency
        3. Is syntactically valid Python
        4. Addresses the specific concerns identified
        """

        return prompt

    def _parse_code_response(self, response_text: str) -> tuple[str, str, float]:
        """Parse the LLM response with robust error handling"""

        # Try to extract JSON from the response
        try:
            # Look for JSON block
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                json_text = response_text[json_start:json_end].strip()
            elif '{' in response_text and '}' in response_text:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_text = response_text[json_start:json_end]
            else:
                raise ValueError("No JSON found in response")

            # Parse JSON
            parsed = json.loads(json_text)

            refactored_code = parsed.get("refactored_code", "")
            reasoning = parsed.get("reasoning", "No reasoning provided")
            confidence = float(parsed.get("confidence_score", 0.5))

            return refactored_code, reasoning, confidence

        except Exception as e:
            logging.error(f"Error parsing code response: {e}")
            # Fallback parsing
            return self._fallback_parse_response(response_text)

    def _fallback_parse_response(self, response_text: str) -> tuple[str, str, float]:
        """Fallback parsing when JSON parsing fails"""

        # Look for code blocks
        code_blocks = []
        lines = response_text.split('\n')

        in_code_block = False
        current_block = []

        for line in lines:
            if line.strip().startswith('```python') or line.strip().startswith('```'):
                if in_code_block:
                    # End of code block
                    if current_block:
                        code_blocks.append('\n'.join(current_block))
                    current_block = []
                    in_code_block = False
                else:
                    # Start of code block
                    in_code_block = True
            elif in_code_block:
                current_block.append(line)

        # Use the last code block as the refactored code
        if code_blocks:
            refactored_code = code_blocks[-1].strip()
        else:
            # No code blocks found, use original code as fallback
            refactored_code = "# Fallback: no valid code found"

        reasoning = "Parsed from fallback method due to JSON parsing error"
        confidence = 0.3

        return refactored_code, reasoning, confidence

    def _validate_code_syntax(self, code: str) -> bool:
        """Validate that the generated code has valid Python syntax"""

        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            logging.error(f"Syntax error in generated code: {e}")
            return False

    def _create_retry_prompt(self, original_prompt: str, error_message: str) -> str:
        """Create a retry prompt with error feedback"""

        retry_prompt = f"""
        {original_prompt}

        PREVIOUS ATTEMPT FAILED WITH ERROR: {error_message}

        Please correct the issue and provide a valid response in the exact JSON format specified above.
        Ensure your Python code is syntactically correct and properly formatted.
        """

        return retry_prompt

    def _mock_refactoring(self, instruction: PlannerToCoderInstruction) -> tuple[str, str, float]:
        """Mock refactoring for testing when LLM is unavailable"""

        original_code = instruction.initial_code

        # Simple mock optimization
        if "for" in original_code and "in" in original_code:
            # Mock: suggest using dictionary lookup
            mock_code = f"""
# Optimized version using dictionary lookup
# Original code had nested loops - replaced with hash map approach
{original_code}

# TODO: Implement hash map optimization
optimized_data = {{}}
# Use optimized_data for O(1) lookups instead of nested iteration
"""
        else:
            mock_code = f"""
# Optimized version
{original_code}

# TODO: Apply appropriate optimization based on causal analysis
"""

        reasoning = "Mock optimization: suggested data structure improvements based on static analysis"
        confidence = 0.6

        return mock_code, reasoning, confidence

    # Legacy methods for backward compatibility
    def synthesize_tool(self, specification: str) -> str:
        """Legacy tool synthesis method"""
        logging.info("Legacy synthesize_tool called - using mock implementation")
        return "mock_tool.py"

    def synthesize_agent(self, proposal: str) -> str:
        """Legacy agent synthesis method"""
        logging.info("Legacy synthesize_agent called - using mock implementation")
        return "mock_agent.py"

    def prove(self, theorem: str) -> Optional[str]:
        """Legacy theorem proving method"""
        logging.info("Legacy prove method called - using mock implementation")
        return f"mock_proof_for({theorem})"