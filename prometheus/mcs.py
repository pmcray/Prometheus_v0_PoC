
import logging
import importlib
import time
from .brain_map import BrainMap
from .experiment_orchestrator import ExperimentOrchestrator
from .results_synthesizer import ResultsSynthesizer
from .tools import CausalGraphTool

class MCSSupervisor:
    def __init__(self, planner, coder, knowledge_agent, brain_map: BrainMap):
        self.planner = planner
        self.coder = coder
        self.knowledge_agent = knowledge_agent
        self.brain_map = brain_map
        self.orchestrator = ExperimentOrchestrator()
        self.synthesizer = ResultsSynthesizer(CausalGraphTool())

    def run_discovery_cycle(self, goal: str):
        logging.info(f"--- Starting Discovery Cycle for goal: {goal} ---")

        # 1. Hypothesis Generation
        logging.info("\n--- Hypothesis Generation ---")
        hypotheses = self.planner.generate_hypotheses(goal)
        
        # 2. Parallel Experimentation
        logging.info("\n--- Parallel Experimentation ---")
        start_time = time.time()
        results = self.orchestrator.run_parallel_experiments(hypotheses)
        end_time = time.time()
        logging.info(f"Parallel execution time: {end_time - start_time:.2f}s")
        self.brain_map.activate_node("ExperimentOrchestrator") # Visualize
        
        # 3. Causal Analysis & Learning
        logging.info("\n--- Causal Analysis & Learning ---")
        causal_graph = self.synthesizer.analyze_results(results)
        self.knowledge_agent.update_causal_rules(causal_graph)
        self.brain_map.activate_node("ResultsSynthesizer") # Visualize
        self.brain_map.activate_node("KnowledgeAgent") # Visualize
        
        # 4. Verification Run
        logging.info("\n--- Verification Run ---")
        # In a real system, the planner would now use the learned rule.
        # For the PoC, we'll just log the learned rule.
        learned_rule = self.knowledge_agent.get_causal_rules()[0]
        logging.info(f"✅ Discovery Cycle Successful: Learned new rule: {learned_rule}")
        
        self.brain_map.show("brain_map.html")

    # ... (rest of the MCSSupervisor class is unchanged)
    def run_tool_rsi_cycle(self, goal: str):
        pass
    def run_meta_learning_cycle(self, goal: str, curriculum_path: str):
        pass
    def run_dynamic_circuit_visualization(self, goal):
        pass
