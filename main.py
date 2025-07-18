import os
import logging
import sys
from src.planner import PlannerAgent
from src.coder import CoderAgent
from src.evaluator import EvaluatorAgent
from src.corrector import CorrectorAgent
from src.mcs import MCSSupervisor
from src.knowledge_agent import KnowledgeAgent
from src.tools import CompilerTool, StaticAnalyzerTool, LeanTool, PDFTool
from src.system_state import SystemState
from src.performance_logger import PerformanceLogger
from src.strategy_archive import StrategyArchive

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
    # 1. Instantiate Tools, Logger, and Archives
    compiler = CompilerTool()
    analyzer = StaticAnalyzerTool()
    lean_tool = LeanTool()
    pdf_tool = PDFTool()
    performance_logger = PerformanceLogger()
    strategy_archive = StrategyArchive()

    # 2. Instantiate Agents
    knowledge_agent = KnowledgeAgent(api_key=API_KEY, performance_logger=performance_logger, pdf_tool=pdf_tool)
    planner = PlannerAgent()
    coder = CoderAgent(api_key=API_KEY, compiler=compiler, analyzer=analyzer, lean_tool=lean_tool, knowledge_agent=knowledge_agent)
    evaluator = EvaluatorAgent(api_key=API_KEY, lean_tool=lean_tool)
    corrector = CorrectorAgent()

    # 3. Scientific Literature Review Task
    logging.info("\n--- Running Simulated Literature Review Task ---")
    
    # a. Ingest the paper
    paper_path = "docs/sample_abstract.pdf"
    if knowledge_agent.ingest_paper(paper_path):
        
        # b. Query the knowledge
        query = "What is the key innovation of the paper?"
        answer = coder.query_knowledge(paper_path, query)
        
        logging.info(f"Query: {query}")
        logging.info(f"Answer: {answer}")

if __name__ == "__main__":
    main()