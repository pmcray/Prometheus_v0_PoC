
import logging
import json
from prometheus.mcs import MCSSupervisor
from prometheus.planner import PlannerAgent
from prometheus.coder import CoderAgent
from prometheus.evaluator import EvaluatorAgent
from prometheus.resource_manager import ResourceManager
from prometheus.performance_logger import PerformanceLogger
from prometheus.tools import CompilerTool, StaticAnalyzerTool, LeanTool
from prometheus.knowledge_agent import KnowledgeAgent

def main():
    with open('../config/dynamic_mesh_demo.json', 'r') as f:
        config = json.load(f)

    logging.basicConfig(level=config['logging']['level'], format=config['logging']['format'])

    # Initialize agents and tools
    resource_manager = ResourceManager()
    performance_logger = PerformanceLogger()
    planner = PlannerAgent()
    knowledge_agent = KnowledgeAgent()
    compiler = CompilerTool()
    analyzer = StaticAnalyzerTool()
    lean_tool = LeanTool()
    coder = CoderAgent(config['api_keys']['coder_agent'], compiler, analyzer, lean_tool, knowledge_agent)
    evaluator = EvaluatorAgent(api_key=config['api_keys']['evaluator_agent'], lean_tool=lean_tool)

    # Initialize the supervisor
    supervisor = MCSSupervisor(planner, resource_manager, coder, evaluator)
    supervisor.performance_logger = performance_logger

    # Demonstrate Ultraparallelism
    supervisor.run_parallel_experiments(config['experiments']['parallel_experiments']['goal'])

    # Demonstrate Dynamic Subassembly
    supervisor.form_and_run_circuit(config['experiments']['form_and_run_circuit']['goal'])

if __name__ == "__main__":
    main()
