import os
import logging
import sys
import importlib

# --- Prometheus Agent Imports ---
from prometheus.planner import PlannerAgent
# CoderAgent is now dynamically imported
from prometheus.evaluator import EvaluatorAgent
from prometheus.corrector import CorrectorAgent
from prometheus.mcs import MCSSupervisor
from prometheus.knowledge_agent import KnowledgeAgent

# --- Tool Imports ---
from prometheus.tools.base_tools import CompilerTool, StaticAnalyzerTool, LeanTool, PDFTool

# --- System Imports ---
from prometheus.performance_logger import PerformanceLogger

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='crls_loop.log', filemode='w')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)
# ---------------------

API_KEY = os.environ.get("GOOGLE_API_KEY")

if not API_KEY:
    logging.error("FATAL: The GOOGLE_API_KEY environment variable is not set. Please set it to your API key.")
    sys.exit(1)


def main():
    # 1. Instantiate Tools & Logger
    compiler = CompilerTool()
    analyzer = StaticAnalyzerTool()
    lean_tool = LeanTool()
    pdf_tool = PDFTool()
    performance_logger = PerformanceLogger()

    # 2. Instantiate Agents (except CoderAgent)
    planner = PlannerAgent()
    evaluator = EvaluatorAgent()
    corrector = CorrectorAgent()
    knowledge_agent = KnowledgeAgent(api_key=API_KEY, performance_logger=performance_logger, pdf_tool=pdf_tool)

    # 3. Main loop (simplified for now, to be expanded later)
    logging.info("\n--- Running Self-Improvement Task ---")

    task_description = "Refactor the inefficient_sort.py file to be more efficient."

    coder_module_name = 'prometheus.coder'

    # Dynamically import the CoderAgent class
    try:
        # Invalidate caches to make sure we load the newest version of the code
        importlib.invalidate_caches()

        # If the module is already loaded, reload it to get the latest version
        if coder_module_name in sys.modules:
            from prometheus.reloader import reload_agent_module
            if not reload_agent_module(coder_module_name):
                raise ImportError(f"Failed to reload {coder_module_name}")
            coder_module = sys.modules[coder_module_name]
        else:
            coder_module = importlib.import_module(coder_module_name)

        CoderAgent = getattr(coder_module, 'CoderAgent')

        # Instantiate the CoderAgent for this specific task
        coder = CoderAgent(
            api_key=API_KEY,
            compiler=compiler,
            analyzer=analyzer,
            lean_tool=lean_tool,
            knowledge_agent=knowledge_agent
        )

        logging.info(f"Dynamically loaded and instantiated CoderAgent from {coder_module_name}")

        # --- Placeholder for CoderAgent's action ---
        specification = "A tool named `MyFinalTool` that can multiply two numbers."
        file_path = coder.synthesize_tool(specification)

        if file_path:
            logging.info(f"✅ CoderAgent task completed successfully! New tool at: {file_path}")
        else:
            logging.error("❌ CoderAgent task failed.")

    except (ImportError, AttributeError, TypeError) as e:
        logging.error(f"Failed to dynamically load or use CoderAgent: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()