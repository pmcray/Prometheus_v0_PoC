import logging
import importlib
import time
from .brain_map import BrainMap
from .tool_benchmark import run_tool_benchmark
from .toy_chemistry_sim import ToyChemistrySim

class MCSSupervisor:
    def __init__(self, planner, coder, evaluator, auditor, brain_map: BrainMap, performance_logger):
        self.planner = planner
        self.coder = coder
        self.evaluator = evaluator
        self.auditor = auditor
        self.brain_map = brain_map
        self.performance_logger = performance_logger
        self.dynamic_agents = {}
        self.tool_registry = {"ToyChemistrySim": ToyChemistrySim()}

    def register_tool(self, tool_name, tool_instance):
        self.tool_registry[tool_name] = tool_instance
        logging.info(f"Registered tool: {tool_name}")

    def run_tool_rsi_cycle(self, goal: str):
        logging.info(f"--- Starting Tool RSI Cycle for goal: {goal} ---")

        # 1. Baseline Run
        logging.info("\n--- Baseline Run ---")
        start_time = time.time()
        run_tool_benchmark(self.tool_registry["ToyChemistrySim"])
        end_time = time.time()
        self.performance_logger.log_tool_usage("ToyChemistrySim", end_time - start_time, 500)

        # 2. Tool Introspection
        logging.info("\n--- Tool Introspection ---")
        critique = self.planner.generate_tool_critique(self.performance_logger.log)
        
        # 3. Tool Synthesis
        logging.info("\n--- Tool Synthesis ---")
        specification = self.planner.generate_tool_specification(critique)
        new_tool_path = self.coder.synthesize_tool(specification)
        tool_name = self.coder._extract_tool_name(specification)
        
        # 4. Dynamic Tool Registration
        logging.info("\n--- Dynamic Tool Registration ---")
        module_name = new_tool_path.replace("/", ".").replace(".py", "")
        new_tool_module = importlib.import_module(module_name)
        new_tool_class = getattr(new_tool_module, tool_name)
        self.register_tool(tool_name, new_tool_class())
        
        # 5. Update Brain Map
        self.brain_map.add_dynamic_node(tool_name, "Synthesized Tool")
        self.brain_map.show("brain_map.html")
        
        # 6. Verification Run
        logging.info("\n--- Verification Run ---")
        start_time = time.time()
        # In a real system, the planner would choose the best tool.
        # For the PoC, we'll just use the new tool.
        operations = [lambda: self.tool_registry[tool_name].mix("A", "B")] * 500
        self.tool_registry[tool_name].run_experiment(operations)
        end_time = time.time()
        
        logging.info(f"✅ Tool RSI Cycle Successful: New tool synthesized, registered, and used.")
        logging.info(f"Baseline execution time: {self.performance_logger.log['tool_usage']['ToyChemistrySim'][-1]['execution_time']:.2f}s")
        logging.info(f"New tool execution time: {end_time - start_time:.2f}s")

    # ... (rest of the MCSSupervisor class is unchanged)
    def run_meta_learning_cycle(self, goal: str, curriculum_path: str):
        pass
    def run_dynamic_circuit_visualization(self, goal):
        pass