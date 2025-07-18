
import os
import logging
from src.planner import PlannerAgent
from src.mcs import MCSSupervisor

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# ---------------------

def main():
    logging.info("--- Verifying Interactive Goal Setting ---")
    
    # 1. Instantiate components
    planner = PlannerAgent()
    # For this verification, we don't need a real supervisor, just a mock to hold the loop.
    
    # 2. Simulate the interactive loop
    goal = "solve a math problem"
    logging.info(f"User input: {goal}")
    
    response = planner.clarify_goal(goal)
    logging.info(f"Agent response: {response}")
    
    user_response = "theorem add_assoc (a b c : Nat) : a + b + c = a + (b + c)"
    logging.info(f"User response: {user_response}")
    
    final_goal = planner.clarify_goal(goal, user_response)
    logging.info(f"Final goal: {final_goal}")
    

if __name__ == "__main__":
    main()
