import os
import logging
from src.planner import PlannerAgent
from src.mcs import MCSSupervisor

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# ---------------------

def main():
    # 1. Instantiate Agents
    planner = PlannerAgent()
    
    # 2. Instantiate Supervisor
    supervisor = MCSSupervisor(planner, None, None, None, None, None, None, None)

    # 3. Dynamic Subassembly Task
    logging.info("\n--- Running Dynamic Subassembly Task ---")
    
    goal = "Analyze this scientific paper and then try to replicate its findings in the ToyChemistrySim"
    
    supervisor.run_dynamic_circuit(goal)

if __name__ == "__main__":
    main()