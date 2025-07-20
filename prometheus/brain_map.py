from pyvis.network import Network
import logging

class BrainMap:
    def __init__(self):
        self.net = Network(notebook=True, cdn_resources='in_line')
        self.static_agents = ["PlannerAgent", "CoderAgent", "EvaluatorAgent", "KnowledgeAgent", "AuditorAgent", "ExperimentOrchestrator", "ResultsSynthesizer"]
        for agent in self.static_agents:
            self.net.add_node(agent, label=agent, color="#cccccc", shape="box")
        logging.info("BrainMap initialized.")

    def add_dynamic_node(self, agent_name, agent_type):
        logging.info(f"BrainMap: Adding dynamic node {agent_name} of type {agent_type}")
        self.net.add_node(agent_name, label=f"{agent_name} ({agent_type})", color="#a0a0ff", shape="ellipse")
        self.net.add_edge("PlannerAgent", agent_name)

    def remove_dynamic_node(self, agent_name):
        logging.info(f"BrainMap: Deactivating dynamic node {agent_name}")
        self.net.get_node(agent_name)['color'] = "#e0e0e0" # Change to a muted color

    def activate_node(self, agent_name):
        logging.info(f"BrainMap: Activating {agent_name}")
        self.net.get_node(agent_name)['color'] = "#ff0000"

    def deactivate_node(self, agent_name):
        logging.info(f"BrainMap: Deactivating {agent_name}")
        self.net.get_node(agent_name)['color'] = "#cccccc"

    def show(self, file_name="brain_map.html"):
        self.net.show(file_name)
        logging.info(f"BrainMap saved to {file_name}")