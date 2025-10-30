
import logging
from prometheus.mcs import MCSSupervisor
from prometheus.planner import PlannerAgent
from prometheus.coder import CoderAgent
from prometheus.evaluator import EvaluatorAgent
from prometheus.resource_manager import ResourceManager
from prometheus.performance_logger import PerformanceLogger
from prometheus.tools import CompilerTool, StaticAnalyzerTool, LeanTool
from prometheus.knowledge_agent import KnowledgeAgent

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Initialize agents and tools
    resource_manager = ResourceManager()
    performance_logger = PerformanceLogger()
    planner = PlannerAgent()
    knowledge_agent = KnowledgeAgent()
    compiler = CompilerTool()
    analyzer = StaticAnalyzerTool()
    lean_tool = LeanTool()
    coder = CoderAgent("dummy_api_key", compiler, analyzer, lean_tool, knowledge_agent)
    evaluator = EvaluatorAgent(api_key="dummy_api_key", lean_tool=lean_tool)

    # Initialize the supervisor
    supervisor = MCSSupervisor(planner, resource_manager, coder, evaluator)
    supervisor.performance_logger = performance_logger

    # Demonstrate Ultraparallelism
    supervisor.run_parallel_experiments("Find the best way to create a stable chemical compound.")

    # Demonstrate Dynamic Subassembly
    supervisor.form_and_run_circuit("Analyze this scientific paper and then try to replicate its findings in the ToyChemistrySim")

if __name__ == "__main__":
    main()
