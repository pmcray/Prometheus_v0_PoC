import os
import logging
from src.planner import PlannerAgent
from src.coder import CoderAgent
from src.mcs import MCSSupervisor
from src.knowledge_agent import KnowledgeAgent
from src.tools import PDFTool
from src.performance_logger import PerformanceLogger

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# ---------------------

API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyC7PYhohlqgdRVVypOnpbqzoE9bEdjvwvg")

def main():
    # 1. Instantiate Tools and Logger
    pdf_tool = PDFTool()
    performance_logger = PerformanceLogger()

    # 2. Instantiate Agents
    knowledge_agent = KnowledgeAgent(api_key=API_KEY, performance_logger=performance_logger, pdf_tool=pdf_tool)
    planner = PlannerAgent()
    coder = CoderAgent(api_key=API_KEY, compiler=None, analyzer=None, lean_tool=None, knowledge_agent=knowledge_agent)
    
    # 3. Instantiate Supervisor
    supervisor = MCSSupervisor(planner, coder, None, None, None, None, None, knowledge_agent)

    # 4. Knowledge-Grounded Hypothesis Generation Task
    logging.info("\n--- Running Knowledge-Grounded Hypothesis Generation Task ---")
    
    # a. Ingest the "scientific literature"
    knowledge_agent.ingest_rules("docs/toy_chemistry_rules.pdf")
    
    # b. Run the experimental cycle
    goal = "Discover the sequence of actions in the ToyChemistrySim that maximizes the concentration of chemical 'C'."
    supervisor.run_experimental_cycle(goal)

if __name__ == "__main__":
    main()