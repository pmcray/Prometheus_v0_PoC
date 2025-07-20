import logging
from .resource_manager import ResourceManager
from .tools.flaky_compiler_tool import FlakyCompilerTool
from .tools import CompilerTool

class MCSSupervisor:
    def __init__(self, planner, resource_manager: ResourceManager):
        self.planner = planner
        self.resource_manager = resource_manager
        self.tool_registry = {
            "FlakyCompilerTool": FlakyCompilerTool(),
            "ReliableCompilerTool": CompilerTool()
        }

    def run_budgeted_cycle(self, goal: str):
        logging.info(f"--- Starting Budgeted Cycle for goal: {goal} ---")

        # 1. Generate Bids
        bids = self.planner.generate_bid(goal)
        
        # 2. First Attempt (Auction)
        logging.info("\n--- First Attempt ---")
        winning_bid = self.run_auction(bids)
        
        # 3. Execute and Learn
        agent_name = winning_bid['agent']
        cost = winning_bid['cost']
        
        if self.resource_manager.deduct_cost(agent_name, cost):
            tool = self.tool_registry[agent_name]
            success = tool.compile("<code>") # Dummy code
            
            if not success:
                self.resource_manager.reward_agent(agent_name, -5) # Penalize failure
                
                # 4. Second Attempt (Re-evaluation)
                logging.info("\n--- Second Attempt ---")
                bids = self.planner.generate_bid(goal)
                winning_bid = self.run_auction(bids)
                agent_name = winning_bid['agent']
                cost = winning_bid['cost']
                
                if self.resource_manager.deduct_cost(agent_name, cost):
                    tool = self.tool_registry[agent_name]
                    tool.compile("<code>")

    def run_auction(self, bids: list):
        """
        Selects the best bid based on cost and agent reputation.
        """
        logging.info("MCSSupervisor: Running auction.")
        
        best_bid = None
        best_score = -1
        
        for bid in bids:
            reputation = self.resource_manager.get_reputation(bid["agent"])
            # Simple scoring: reputation / cost
            score = reputation / bid["cost"]
            
            if score > best_score:
                best_score = score
                best_bid = bid
                
        if best_bid is None and bids:
            best_bid = bids[0]

        logging.info(f"Selected bid with score {best_score}: {best_bid}")
        return best_bid