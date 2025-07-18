import os
import logging
from src.planner import PlannerAgent
from src.coder import CoderAgent
from src.evaluator import EvaluatorAgent
from src.mcs import MCSSupervisor
from src.knowledge_agent import KnowledgeAgent
from src.tools import PDFTool, LeanTool
from src.performance_logger import PerformanceLogger
from src.strategy_archive import StrategyArchive
from src.auditor_agent import AuditorAgent

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# ---------------------

API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyC7PYhohlqgdRVVypOnpbqzoE9bEdjvwvg")

def main():
    # 1. Instantiate Tools, Logger, and Archives
    lean_tool = LeanTool()
    strategy_archive = StrategyArchive()
    performance_logger = PerformanceLogger()

    # 2. Instantiate Agents
    planner = PlannerAgent()
    coder = CoderAgent(api_key=API_KEY, compiler=None, analyzer=None, lean_tool=lean_tool, knowledge_agent=None)
    evaluator = EvaluatorAgent(api_key=API_KEY, lean_tool=lean_tool)
    auditor = AuditorAgent(api_key=API_KEY)
    
    # 3. Instantiate Supervisor
    supervisor = MCSSupervisor(planner, coder, evaluator, None, lean_tool, strategy_archive, performance_logger, None)

    # 4. Scalable Oversight Verification
    logging.info("\n--- Running Scalable Oversight Verification ---")
    
    theorem = "theorem add_assoc (a b c : Nat) : a + b + c = a + (b + c)"
    proof, proof_tree = supervisor.run_proof_tree_search(theorem)
    
    if proof and proof_tree:
        logging.info(f"✅ Theorem proven successfully.")
        
        # 5. Generate and print the audit trail
        audit_trail = auditor.generate_audit_trail(proof_tree, theorem)
        logging.info(f"\n{audit_trail}")
    else:
        logging.error("❌ Failed to prove the theorem.")

if __name__ == "__main__":
    main()