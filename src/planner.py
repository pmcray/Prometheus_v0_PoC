import logging
from src.llm_provider import LLMProvider
import json

class PlannerAgent:
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
        logging.info("PlannerAgent initialized with LLMProvider.")

    def plan(self, code_snippet: str, goal: str):
        """
        Analyzes the code and goal, classifies the task, and generates a plan.
        """
        logging.info(f"PlannerAgent: Received goal - '{goal}'")
        
        # For v0.37, we focus on the refactoring task classification
        if "refactor" in goal.lower():
            classification = self._classify_task(code_snippet)
            
            plan = {
                "type": "refactor",
                "task_classification": classification,
                "code_snippet": code_snippet,
                "goal": goal
            }
            logging.info(f"PlannerAgent: Created refactoring plan with classification '{classification}'")
            return plan
            
        else:
            # Default plan for other goals
            plan = {
                "type": "generic",
                "goal": goal
            }
            logging.info("PlannerAgent: Created a generic plan.")
            return plan

    def _classify_task(self, code_snippet: str) -> str:
        """
        Uses the LLM to classify the refactoring task.
        """
        prompt = f"""
        Analyze the following Python code snippet and classify the required refactoring task into one of these categories:
        - LOOP_OPTIMIZATION
        - RECURSION_REFACTOR
        - DATA_STRUCTURE_SWAP
        - GENERAL_REFACTORING

        Code:
        ```python
        {code_snippet}
        ```

        Respond with only the category name as a single string (e.g., "LOOP_OPTIMIZATION").
        """

        classification = self.llm_provider.generate(prompt).strip()

        # Basic validation to ensure it's one of the expected categories
        valid_categories = ["LOOP_OPTIMIZATION", "RECURSION_REFACTOR", "DATA_STRUCTURE_SWAP", "GENERAL_REFACTORING"]
        if classification not in valid_categories:
            logging.warning(f"PlannerAgent: LLM returned an invalid classification '{classification}'. Defaulting to GENERAL_REFACTORING.")
            return "GENERAL_REFACTORING"

        return classification