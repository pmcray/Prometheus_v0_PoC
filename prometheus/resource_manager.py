
import logging

class ResourceManager:
    def __init__(self, initial_budget=1000):
        self.budget = initial_budget
        self.agent_reputations = {}
        logging.info(f"ResourceManager initialized with a budget of {self.budget} compute units.")

    def deduct_cost(self, agent_name: str, cost: int):
        if self.budget >= cost:
            self.budget -= cost
            logging.info(f"Deducted {cost} units for {agent_name}. Remaining budget: {self.budget}")
            return True
        else:
            logging.warning(f"Insufficient budget for {agent_name} to perform action costing {cost} units.")
            return False

    def reward_agent(self, agent_name: str, reward: int):
        if agent_name not in self.agent_reputations:
            self.agent_reputations[agent_name] = 1.0 # Start with a neutral reputation
        
        self.agent_reputations[agent_name] += reward
        logging.info(f"Rewarded {agent_name}. New reputation: {self.agent_reputations[agent_name]}")

    def get_reputation(self, agent_name: str):
        return self.agent_reputations.get(agent_name, 1.0)
