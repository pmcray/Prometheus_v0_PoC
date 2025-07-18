
import os
import logging
from src.planner import PlannerAgent
from src.coder import CoderAgent
from src.evaluator import EvaluatorAgent
from src.corrector import CorrectorAgent
from src.mcs import MCSSupervisor
from src.tools import CompilerTool, StaticAnalyzerTool, LeanTool
from src.strategy_archive import StrategyArchive

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# ---------------------

API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyC7PYhohlqgdRVVypOnpbqzoE9bEdjvwvg")

def main():
    # 1. Instantiate Tools and Archives
    lean_tool = LeanTool()
    strategy_archive = StrategyArchive()

    # 2. Instantiate Agents
    planner = PlannerAgent()
    coder = CoderAgent(api_key=API_KEY, compiler=None, analyzer=None, lean_tool=lean_tool, knowledge_agent=None)
    evaluator = EvaluatorAgent(api_key=API_KEY, lean_tool=lean_tool)
    
    # 3. Instantiate Supervisor
    supervisor = MCSSupervisor(planner, coder, evaluator, None, lean_tool, strategy_archive)

    # 4. Simulated Laboratory Task
    logging.info("\n--- Running Simulated Laboratory Task ---")
    
    goal = "Discover the sequence of actions in the ToyChemistrySim that maximizes the concentration of chemical 'C'."
    
    supervisor.run_experimental_cycle(goal)

if __name__ == "__main__":
    main()
