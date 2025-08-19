import logging
from src.llm_provider import LLMProvider
import json

from src.performance_predictor import PerformancePredictorAgent

class PlannerAgent:
    def __init__(self, llm_provider: LLMProvider, predictor: PerformancePredictorAgent):
        self.llm_provider = llm_provider
        self.predictor = predictor
        logging.info("PlannerAgent initialized with LLMProvider and PerformancePredictorAgent.")

    def plan(self, code_snippet: str, goal: str):
        """
        Analyzes the code and goal, generates strategies, predicts their performance, and creates a plan.
        """
        logging.info(f"PlannerAgent: Received goal - '{goal}' for code snippet.")
        
        if "refactor" in goal.lower():
            # 1. Generate high-level strategies
            strategies = self._generate_strategies(code_snippet, goal)
            logging.info(f"PlannerAgent: Generated {len(strategies)} strategies: {strategies}")

            # 2. Predict performance of each strategy
            predicted_performances = {}
            for strategy in strategies:
                # For now, we pass the strategy description to the predictor.
                # A more advanced implementation would generate stub code for each strategy.
                predicted_performances[strategy] = self.predictor.predict_performance(strategy)
            
            logging.info(f"PlannerAgent: Predicted performances: {predicted_performances}")

            # 3. Select the best strategy
            if not predicted_performances:
                logging.error("PlannerAgent: No strategies generated or performances predicted. Aborting.")
                return None

            best_strategy = min(predicted_performances, key=predicted_performances.get)
            logging.info(f"PlannerAgent: Selected best strategy: '{best_strategy}'")

            # 4. Create a plan with the best strategy
            classification = self._classify_task(code_snippet)
            plan = {
                "type": "refactor",
                "task_classification": classification,
                "code_snippet": code_snippet,
                "goal": best_strategy # The goal is now the specific, chosen strategy
            }
            logging.info(f"PlannerAgent: Created refactoring plan with best strategy.")
            return plan

        else:
            # Default plan for other goals
            plan = {"type": "generic", "goal": goal}
            logging.info("PlannerAgent: Created a generic plan.")
            return plan

    def _generate_strategies(self, code_snippet: str, goal: str) -> list[str]:
        """
        Uses the LLM to generate a list of high-level refactoring strategies.
        """
        prompt = f"""
        Analyze the following Python code snippet and the goal. Propose 3 distinct high-level strategies to achieve the goal.
        The strategies should be short, imperative statements.

        Code:
        ```python
        {code_snippet}
        ```
        Goal: {goal}

        Respond with ONLY a JSON object containing a single key "strategies" which is a list of strings.
        Example:
        {{"strategies": ["Replace the for loop with a list comprehension", "Use a different data structure like a deque", "Memoize the function using functools.lru_cache"]}}
        """

        response_str = self.llm_provider.generate(prompt)
        try:
            response_json = json.loads(response_str)
            return response_json.get("strategies", [])
        except json.JSONDecodeError:
            logging.error(f"PlannerAgent: Could not decode strategies from LLM response: {response_str}")
            return []

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