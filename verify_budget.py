
import os
import logging
from src.planner import PlannerAgent
from src.coder import CoderAgent
from src.mcs import MCSSupervisor
from src.tools import LeanTool
from src.strategy_archive import StrategyArchive

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# ---------------------

API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyC7PYhohlqgdRVVypOnpbqzoE9bEdjvwvg")

def main():
    logging.info("--- Verifying Resource Self-Management ---")
    
    # 1. Instantiate components
    lean_tool = LeanTool()
    strategy_archive = StrategyArchive()
    planner = PlannerAgent()
    coder = CoderAgent(api_key=API_KEY, compiler=None, analyzer=None, lean_tool=lean_tool, knowledge_agent=None)
    
    # 2. Instantiate Supervisor with a tight budget
    supervisor = MCSSupervisor(planner, coder, None, None, lean_tool, strategy_archive, None, None)
    supervisor.compute_budget = 2 # Set a very small budget
    
    # 3. Run the proof search
    theorem = "theorem add_assoc (a b c : Nat) : a + b + c = a + (b + c)"
    supervisor.run_proof_tree_search(theorem)

if __name__ == "__main__":
    main()
