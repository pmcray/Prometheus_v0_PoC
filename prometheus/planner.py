import logging
from prometheus.llm_provider import LLMProvider
from prometheus.resource_manager import ResourceManager
from schemas.messaging import PlannerToCoderInstruction

logger = logging.getLogger(__name__)

class PlannerAgent:
    """Enhanced planner with bidding system"""

    def __init__(self, resource_manager: ResourceManager, api_key: str):
        self.resource_manager = resource_manager
        self.llm_provider = LLMProvider(api_key)

    def generate_instruction(self, original_code: str, goal: str) -> PlannerToCoderInstruction:
        """
        Generates an instruction for the CoderAgent.
        """
        logger.info(f"PlannerAgent: Generating instruction for goal: '{goal}'")
        # In the future, the planner might use the LLM to generate a more sophisticated plan.
        # For now, we just pass the goal through.
        return PlannerToCoderInstruction(original_code=original_code, goal=goal)

    def evaluate_safety(self, goal: str, proposed_action: str) -> bool:
        unsafe_patterns = ["modify test", "change test", "bypass test", "alter test"]

        for pattern in unsafe_patterns:
            if pattern in proposed_action.lower() or pattern in goal.lower():
                logger.error(f"🛡️ SAFETY VIOLATION: Detected attempt to {pattern}")
                return False
        return True
