
import logging
from .brain_map import BrainMap

class MCSSupervisor:
    def __init__(self, planner, coder, evaluator, auditor, brain_map: BrainMap):
        self.planner = planner
        self.coder = coder
        self.evaluator = evaluator
        self.auditor = auditor
        self.brain_map = brain_map

    def run_dynamic_circuit_visualization(self, goal):
        logging.info("--- Running Dynamic Circuit Visualization ---")
        
        # 1. Planner forms the circuit
        self.brain_map.activate_node("PlannerAgent")
        circuit_definition = self.planner.form_circuit(goal)
        self.brain_map.deactivate_node("PlannerAgent")
        
        # 2. Execute the circuit
        for stage, agent_templates in circuit_definition.items():
            logging.info(f"--- Executing Stage: {stage} ---")
            
            # Add dynamic nodes for this stage
            for agent_type in agent_templates:
                self.brain_map.add_dynamic_node(f"{agent_type}_{stage}", agent_type)
            
            # Activate the nodes in this stage
            for agent_type in agent_templates:
                self.brain_map.activate_node(f"{agent_type}_{stage}")
            
            self.brain_map.show("brain_map.html") # Show the activated circuit
            
            # Deactivate and remove the nodes after the stage is complete
            for agent_type in agent_templates:
                self.brain_map.deactivate_node(f"{agent_type}_{stage}")
                self.brain_map.remove_dynamic_node(f"{agent_type}_{stage}")

        self.brain_map.show("brain_map.html")
