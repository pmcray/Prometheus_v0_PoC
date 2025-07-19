import os
import logging
from prometheus.planner import PlannerAgent
from prometheus.coder import CoderAgent
from prometheus.evaluator import EvaluatorAgent
from prometheus.mcs import MCSSupervisor
from prometheus.knowledge_agent import KnowledgeAgent
from prometheus.tools import CompilerTool, StaticAnalyzerTool, LeanTool, PDFTool, CausalGraphTool
from prometheus.performance_logger import PerformanceLogger
from prometheus.strategy_archive import StrategyArchive
from prometheus.brain_map import BrainMap

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# ---------------------

API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyC7PYhohlqgdRVVypOnpbqzoE9bEdjvwvg")

def main():
    # 1. Instantiate All Components
    compiler = CompilerTool()
    analyzer = StaticAnalyzerTool()
    lean_tool = LeanTool()
    pdf_tool = PDFTool()
    causal_graph_tool = CausalGraphTool()
    performance_logger = PerformanceLogger()
    strategy_archive = StrategyArchive()
    brain_map = BrainMap()

    knowledge_agent = KnowledgeAgent(api_key=API_KEY, performance_logger=performance_logger, pdf_tool=pdf_tool)
    planner = PlannerAgent(causal_graph_tool=causal_graph_tool)
    coder = CoderAgent(api_key=API_KEY, compiler=compiler, analyzer=analyzer, lean_tool=lean_tool, knowledge_agent=knowledge_agent)
    evaluator = EvaluatorAgent(api_key=API_KEY, lean_tool=lean_tool)
    auditor = None # Not needed for this verification
    corrector = None # Not needed for this verification
    
    supervisor = MCSSupervisor(planner, coder, evaluator, corrector, lean_tool, strategy_archive, performance_logger, knowledge_agent)
    supervisor.brain_map = brain_map # Attach the brain map

    # 2. Run the Dynamic Circuit Visualization
    logging.info("\n--- Running Dynamic Subassembly Visualization ---")
    goal = "Analyze this scientific paper and then try to replicate its findings in the ToyChemistrySim"
    supervisor.run_dynamic_circuit_visualization(goal)
    
    logging.info("✅ Verification successful. The brain_map.html file has been generated.")

if __name__ == "__main__":
    main()
