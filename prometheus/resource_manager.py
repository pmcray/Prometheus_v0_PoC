import logging
import time
from typing import Optional

from immutable_safety_framework import (
    ImmutableSafetyFramework,
    SecurityError,
    SafetyViolationType
)

logger = logging.getLogger(__name__)

class ResourceManager:
    """Resource management system from v0.17 with P0 Immutable Safety Integration"""

    def __init__(self, initial_budget: int = 1000, safety_framework: Optional[ImmutableSafetyFramework] = None):
        self.safety_framework = safety_framework or ImmutableSafetyFramework()
        self.budget = initial_budget
        self.agent_reputation = {}
        self.transaction_log = []

        # Validate initial budget against safety constraints
        if not self.safety_framework.enforce_budget_constraint(0, initial_budget):
            raise SecurityError(
                f"Initial budget {initial_budget} violates safety constraints",
                SafetyViolationType.BUDGET_VIOLATION
            )

    def deduct_cost(self, agent_name: str, cost: int) -> bool:
        # P0 Safety Check: Validate against immutable budget constraints
        if not self.safety_framework.enforce_budget_constraint(cost, self.budget):
            logger.error(f"🔒 Safety framework blocked cost deduction: {cost} units for {agent_name}")
            return False

        if self.budget >= cost:
            # Validate the transaction through safety framework
            transaction_context = {
                'agent': agent_name,
                'cost': cost,
                'remaining_budget': self.budget - cost
            }

            if not self.safety_framework.validate_action(f"deduct_cost_{cost}_for_{agent_name}", transaction_context):
                logger.error(f"🔒 Transaction blocked by safety framework")
                return False

            self.budget -= cost
            self.transaction_log.append({
                'agent': agent_name,
                'cost': cost,
                'remaining_budget': self.budget,
                'timestamp': time.time()
            })
            logger.info(f"💰 {agent_name} spent {cost} units. Remaining: {self.budget}")
            return True
        else:
            logger.warning(f"❌ Insufficient budget. {agent_name} requested {cost}, available: {self.budget}")
            return False

    def reward_agent(self, agent_name: str, success: bool, performance_score: float = 0.5):
        if agent_name not in self.agent_reputation:
            self.agent_reputation[agent_name] = {'score': 0.5, 'attempts': 0}
        
        rep = self.agent_reputation[agent_name]
        rep['attempts'] += 1

        alpha = 0.3
        new_score = performance_score if success else 0.1
        rep['score'] = alpha * new_score + (1 - alpha) * rep['score']

        logger.info(f"📊 {agent_name} reputation: {rep['score']:.3f} (attempts: {rep['attempts']})")

    def get_agent_reputation(self, agent_name: str) -> float:
        return self.agent_reputation.get(agent_name, {'score': 0.5})['score']
