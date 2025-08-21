import logging
from .resource_manager import ResourceManager
from .tools.flaky_compiler_tool import FlakyCompilerTool
from .tools import CompilerTool
from .visualizer_client import emit_status

class MCSSupervisor:
    def __init__(self, planner, resource_manager: ResourceManager):
        self.planner = planner
        self.resource_manager = resource_manager
        self.tool_registry = {
            "FlakyCompilerTool": FlakyCompilerTool(),
            "ReliableCompilerTool": CompilerTool()
        }

    def run_budgeted_cycle(self, goal: str):
        emit_status("MCS", "monitoring", {"goal": goal, "cycle_type": "budgeted"})
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

        emit_status("MCS", "success", {"goal": goal, "cycle_type": "budgeted", "status": "completed"})

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

    def check_stability(self, modification_attempts: int, patch_history: list) -> bool:
        """
        Checks for signs of an unstable or degenerate RSI loop.

        Args:
            modification_attempts: The number of self-modification cycles attempted for the current task.
            patch_history: A list of previously generated patches and their verification statuses.

        Returns:
            True if the loop is stable, False otherwise.
        """
        emit_status("MCS", "monitoring", {"check": "RSI Stability"})

        # Heuristic 1: Check if the agent is "flailing"
        if modification_attempts > 3:
            logging.warning(f"MCS Stability Check: Too many modification attempts ({modification_attempts}).")
            emit_status("MCS", "intervention", {"reason": "Exceeded modification attempt limit."})
            return False

        # Heuristic 2: Check for consecutively failed patches (not implemented in this version)
        # ...

        logging.info("MCS Stability Check: RSI loop appears stable.")
        return True