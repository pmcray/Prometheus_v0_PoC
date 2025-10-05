"""
Enhanced Corrector Agent with meta-reasoning and memory augmentation
Implements features from v0.21-v0.29 onwards
"""

import google.generativeai as genai
import os
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from .schemas.communication import (
    AgentMessage, MessageType, CorrectorToCoderInstruction,
    EvaluatorToCorrectorCritique, SelfReferentialCritique, MemoryQuery
)
from .memory_agent import MemoryAgent, GeneBankAgent

class StrategyConfig:
    """Configuration for agent strategies (v0.22+)"""

    def __init__(self, config_path: str = "strategy.json"):
        self.config_path = config_path
        self.strategy = self._load_strategy()

    def _load_strategy(self) -> Dict[str, Any]:
        """Load strategy configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Default strategy
            default_strategy = {
                "meta_prompt_template": """
                Analyze the following code optimization task:
                {task_description}

                Focus on:
                - Algorithmic complexity reduction
                - Data structure optimization
                - Maintaining code readability

                Previous failures suggest: {historical_context}
                """,
                "correction_approach": "systematic_causal_analysis",
                "max_correction_attempts": 3
            }
            self._save_strategy(default_strategy)
            return default_strategy

    def _save_strategy(self, strategy: Dict[str, Any]):
        """Save strategy configuration"""
        with open(self.config_path, 'w') as f:
            json.dump(strategy, f, indent=2)

    def update_strategy(self, new_strategy: Dict[str, Any]):
        """Update strategy configuration"""
        self.strategy.update(new_strategy)
        self._save_strategy(self.strategy)

    def get_meta_prompt_template(self) -> str:
        """Get meta-prompt template"""
        return self.strategy.get("meta_prompt_template", "")

class EnhancedCorrectorAgent:
    """Enhanced Corrector Agent with meta-reasoning capabilities"""

    def __init__(self, api_key: str = None, memory_agent: MemoryAgent = None,
                 gene_bank: GeneBankAgent = None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
            logging.warning("No API key provided - using mock responses")

        self.agent_id = "corrector_agent"
        self.memory_agent = memory_agent
        self.gene_bank = gene_bank
        self.strategy_config = StrategyConfig()
        self.failure_count = {}  # Track failures per problem
        self.meta_correction_threshold = 3

    def process_critique(self, critique_message: AgentMessage) -> AgentMessage:
        """Process critique and generate correction instruction"""

        if critique_message.message_type != MessageType.EVALUATOR_TO_CORRECTOR:
            raise ValueError(f"Invalid message type: {critique_message.message_type}")

        # Parse critique
        critique = SelfReferentialCritique(**critique_message.payload)

        # Track failure patterns
        run_id = critique_message.run_id
        if not critique.improvement_achieved:
            self.failure_count[run_id] = self.failure_count.get(run_id, 0) + 1

        # Determine correction strategy
        if self.failure_count.get(run_id, 0) >= self.meta_correction_threshold:
            return self._perform_meta_correction(critique_message, critique)
        else:
            return self._perform_standard_correction(critique_message, critique)

    def _perform_standard_correction(self, critique_message: AgentMessage,
                                   critique: SelfReferentialCritique) -> AgentMessage:
        """Perform standard correction with memory augmentation"""

        # Query memory for similar failures
        analogical_hints = self._retrieve_analogical_hints(critique)

        # Generate correction strategy
        correction_strategy = self._generate_correction_strategy(critique, analogical_hints)

        # Generate specific guidance
        specific_guidance = self._generate_specific_guidance(critique, analogical_hints)

        # Create instruction
        instruction = CorrectorToCoderInstruction(
            critique=critique,
            correction_strategy=correction_strategy,
            specific_guidance=specific_guidance,
            analogical_hints=analogical_hints
        )

        # Create response message
        response_message = AgentMessage(
            message_type=MessageType.CORRECTOR_TO_CODER,
            sender=self.agent_id,
            recipient="coder_agent",
            timestamp=datetime.now().isoformat(),
            run_id=critique_message.run_id,
            payload=instruction.dict()
        )

        logging.info(f"CorrectorAgent generated standard correction for run {critique_message.run_id}")
        return response_message

    def _perform_meta_correction(self, critique_message: AgentMessage,
                               critique: SelfReferentialCritique) -> AgentMessage:
        """Perform meta-correction by modifying agent strategy (v0.22+)"""

        logging.info(f"Performing meta-correction for run {critique_message.run_id}")

        # Analyze failure pattern
        failure_pattern = self._analyze_failure_pattern(critique_message.run_id, critique)

        # Generate new strategy
        new_strategy = self._generate_improved_strategy(failure_pattern, critique)

        # Update strategy configuration
        if new_strategy:
            self.strategy_config.update_strategy(new_strategy)
            logging.info("Updated agent strategy based on failure analysis")

        # Perform correction with new strategy
        return self._perform_standard_correction(critique_message, critique)

    def _retrieve_analogical_hints(self, critique: SelfReferentialCritique) -> List[str]:
        """Retrieve analogical hints from memory (v0.27+)"""

        if not self.memory_agent:
            return []

        try:
            # Query for successful patterns
            query = MemoryQuery(
                query_type="pattern",
                code_snippet="",  # Abstract query
                problem_description=self._abstract_problem_description(critique),
                max_results=2
            )

            response = self.memory_agent.query_patterns(query)

            hints = []
            for result in response.results:
                pattern = result.get("pattern", {})
                if "description" in pattern:
                    hints.append(f"Apply the {pattern['description']} pattern")

            return hints

        except Exception as e:
            logging.error(f"Error retrieving analogical hints: {e}")
            return []

    def _abstract_problem_description(self, critique: SelfReferentialCritique) -> str:
        """Abstract the problem description for pattern matching"""

        # Extract key characteristics
        characteristics = []

        if critique.causal_analysis.change_type == "NO_STRUCTURAL_CHANGE":
            characteristics.append("nested loop optimization")

        if critique.dynamic_analysis and critique.dynamic_analysis.execution_time_ms.get("delta", 0) > 0:
            characteristics.append("performance degradation")

        return " ".join(characteristics) if characteristics else "general optimization"

    def _generate_correction_strategy(self, critique: SelfReferentialCritique,
                                    analogical_hints: List[str]) -> str:
        """Generate correction strategy based on critique analysis"""

        strategy_parts = []

        # Analyze the critique
        if not critique.improvement_achieved:
            if critique.causal_analysis.change_type == "NO_STRUCTURAL_CHANGE":
                strategy_parts.append("Focus on fundamental algorithmic changes")
            elif critique.test_passed and not critique.improvement_achieved:
                strategy_parts.append("Address performance optimization while maintaining correctness")

        # Incorporate historical context
        if critique.historical_context:
            strategy_parts.append("Avoid patterns that failed in similar historical cases")

        # Use analogical hints
        if analogical_hints:
            strategy_parts.append(f"Consider applying these proven patterns: {', '.join(analogical_hints)}")

        return "; ".join(strategy_parts) if strategy_parts else "Apply systematic optimization approach"

    def _generate_specific_guidance(self, critique: SelfReferentialCritique,
                                  analogical_hints: List[str]) -> str:
        """Generate specific, actionable guidance"""

        if not self.model:
            return self._mock_specific_guidance(critique)

        # Construct prompt for specific guidance
        prompt = f"""
        You are an expert code optimization advisor. Based on the following evaluation critique,
        provide specific, actionable guidance for improving the code.

        Critique Analysis:
        - Test passed: {critique.test_passed}
        - Improvement achieved: {critique.improvement_achieved}
        - Causal change type: {critique.causal_analysis.change_type}
        - Evaluation reason: {critique.reason}

        Historical Context: {critique.historical_context}

        Analogical Hints: {analogical_hints}

        Provide 3-5 specific actionable instructions for the next coding attempt.
        Focus on the root cause of the optimization failure.
        """

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            logging.error(f"Error generating specific guidance: {e}")
            return self._mock_specific_guidance(critique)

    def _mock_specific_guidance(self, critique: SelfReferentialCritique) -> str:
        """Mock specific guidance when LLM unavailable"""

        guidance_parts = []

        if critique.causal_analysis.change_type == "NO_STRUCTURAL_CHANGE":
            guidance_parts.append("Replace nested loops with hash map lookups")
            guidance_parts.append("Consider pre-processing data for faster access")

        if not critique.test_passed:
            guidance_parts.append("Ensure functional correctness before optimization")

        if not guidance_parts:
            guidance_parts.append("Focus on identifying the computational bottleneck")
            guidance_parts.append("Consider alternative data structures")

        return "\n".join(f"- {guidance}" for guidance in guidance_parts)

    def _analyze_failure_pattern(self, run_id: str, critique: SelfReferentialCritique) -> Dict[str, Any]:
        """Analyze the pattern of failures for meta-correction"""

        return {
            "failure_count": self.failure_count.get(run_id, 0),
            "recurring_change_type": critique.causal_analysis.change_type,
            "low_improvement_rate": not critique.improvement_achieved,
            "confidence_trend": critique.evaluation_confidence,
            "primary_failure_mode": "structural_stagnation" if critique.causal_analysis.change_type == "NO_STRUCTURAL_CHANGE" else "performance_regression"
        }

    def _generate_improved_strategy(self, failure_pattern: Dict[str, Any],
                                  critique: SelfReferentialCritique) -> Optional[Dict[str, Any]]:
        """Generate improved strategy based on failure analysis"""

        if not self.model:
            return self._mock_improved_strategy(failure_pattern)

        prompt = f"""
        You are an AI system architect. The following agent strategy is repeatedly failing:

        Current strategy: {self.strategy_config.get_meta_prompt_template()}

        Failure pattern analysis: {json.dumps(failure_pattern, indent=2)}

        Recent critique: {critique.reason}

        Propose a modification to the meta-prompt template that might lead to better outcomes.
        Focus on addressing the specific failure pattern identified.

        Return only the improved meta-prompt template as JSON:
        {{"meta_prompt_template": "your improved template here"}}
        """

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # Parse JSON response
            if '{' in response_text and '}' in response_text:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_text = response_text[json_start:json_end]
                return json.loads(json_text)

        except Exception as e:
            logging.error(f"Error generating improved strategy: {e}")

        return self._mock_improved_strategy(failure_pattern)

    def _mock_improved_strategy(self, failure_pattern: Dict[str, Any]) -> Dict[str, Any]:
        """Mock improved strategy when LLM unavailable"""

        if failure_pattern.get("primary_failure_mode") == "structural_stagnation":
            return {
                "meta_prompt_template": """
                CRITICAL: The previous attempts failed to change the algorithmic structure.
                You MUST focus on:
                1. Identifying the core nested loop or recursive pattern
                2. Replacing it with a fundamentally different approach
                3. Using hash maps, sets, or pre-processing to eliminate iteration

                Task: {task_description}
                Historical failures: {historical_context}

                DO NOT make superficial changes. Change the algorithm itself.
                """
            }
        else:
            return {
                "meta_prompt_template": """
                Focus on performance-critical optimization:
                {task_description}

                Proven approaches: {historical_context}
                Measure twice, optimize once.
                """
            }

    def trigger_self_modification(self, target_module: str) -> Optional[str]:
        """Trigger self-modification workflow (v0.29+)"""

        if not self.gene_bank:
            logging.warning("No gene bank available for self-modification")
            return None

        if not self.model:
            logging.warning("No LLM available for code mutation")
            return None

        try:
            # Get current module code
            current_gene = self.gene_bank.get_latest_gene(target_module)
            if not current_gene:
                logging.error(f"No gene found for module: {target_module}")
                return None

            current_code = current_gene["code"]

            # Generate mutation prompt
            prompt = f"""
            You are a senior software engineer. The following Python code is part of an AI agent
            that has been failing repeatedly. Propose a single, small, non-trivial improvement
            to this code's logic to enhance its problem-solving ability.

            Current Code:
            ```python
            {current_code}
            ```

            Output ONLY a git-style patch file that can be applied to improve the code.
            Focus on the logic that generates prompts or processes critiques.
            """

            response = self.model.generate_content(prompt)
            patch_content = response.text.strip()

            logging.info(f"Generated patch for {target_module}")
            return patch_content

        except Exception as e:
            logging.error(f"Error in self-modification: {e}")
            return None

    # Legacy method for backward compatibility
    def correct(self, original_code: str, failed_code: str, critique: Any) -> str:
        """Legacy correction method"""

        critique_reason = str(critique)

        prompt = f"""The previous attempt to refactor the code failed.

Original Code:
```python
{original_code}
```

Failed Code:
```python
{failed_code}
```

Causal Critique: {critique_reason}

Please try again to refactor the code, taking the critique into account.
The goal is to improve the time complexity of the code.
"""
        return prompt