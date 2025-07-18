

import os
import logging
import sys
from src.planner import PlannerAgent
from src.coder import CoderAgent
from src.evaluator import EvaluatorAgent
from src.corrector import CorrectorAgent
from src.mcs import MCSSupervisor
from src.curriculum_agent import CurriculumAgent
from src.tools import CompilerTool, StaticAnalyzerTool, LeanTool
from src.system_state import SystemState
from src.performance_logger import PerformanceLogger

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='crls_loop.log', filemode='w')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)
# ---------------------

API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyC7PYhohlqgdRVVypOnpbqzoE9bEdjvwvg")

def main():
    # 1. Instantiate Tools & Logger
    compiler = CompilerTool()
    analyzer = StaticAnalyzerTool()
    lean_tool = LeanTool()
    performance_logger = PerformanceLogger()

    # 2. Instantiate Agents
    planner = PlannerAgent()
    evaluator = EvaluatorAgent(api_key=API_KEY)
    corrector = CorrectorAgent()
    curriculum_agent = CurriculumAgent(api_key=API_KEY, performance_logger=performance_logger)
    
    # --- Verification Run 1: Force a failure ---
    logging.info("\n--- Running Meta-Learning Verification (Run 1: Failure) ---")
    bad_coder = CoderAgent(api_key=API_KEY, compiler=compiler, analyzer=analyzer, lean_tool=lean_tool)
    bad_coder.bad_tactic_counter = 0 # Ensure the bad tactic is injected
    
    supervisor_bad = MCSSupervisor(planner, bad_coder, evaluator, corrector, lean_tool)
    
    theorem = curriculum_agent.generate_theorem()
    if theorem:
        logging.info(f"Generated Theorem: {theorem}")
        supervisor_bad.run_proof_tree_search(theorem)

    # --- Verification Run 2: Use the critique to succeed ---
    logging.info("\n--- Running Meta-Learning Verification (Run 2: Success) ---")
    good_coder = CoderAgent(api_key=API_KEY, compiler=compiler, analyzer=analyzer, lean_tool=lean_tool)
    
    supervisor_good = MCSSupervisor(planner, good_coder, evaluator, corrector, lean_tool)
    
    if theorem:
        logging.info(f"Re-attempting Theorem: {theorem}")
        proof = supervisor_good.run_proof_tree_search(theorem)
        if proof:
            logging.info(f"✅ Theorem proven successfully on the second attempt!\nProof:\n{proof}")
        else:
            logging.error("❌ Failed to prove the theorem on the second attempt.")


if __name__ == "__main__":
    main()
