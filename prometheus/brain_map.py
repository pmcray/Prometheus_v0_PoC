"""
Enhanced Brain Map with Cell Assemblies

This module visualizes the cognitive architecture of AI agents:
- Cell assemblies (groups of neurons/agents working together)
- Subassemblies (hierarchical organization)
- Activation patterns
- Information flow
- Modular cognitive components

Inspired by Hebb's cell assembly theory and modern neuroscience.
"""

from pyvis.network import Network
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import logging
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class CellAssembly:
    """
    A group of interconnected agents/neurons forming a functional unit
    """
    assembly_id: str
    name: str
    members: Set[str] = field(default_factory=set)
    subassemblies: List[str] = field(default_factory=list)
    function: str = ""
    activation_level: float = 0.0
    color: str = "#3498DB"


class BrainMap:
    """
    Enhanced brain map with hierarchical cell assemblies

    Features:
    - Static agents (core system components)
    - Dynamic agents (evolved/temporary)
    - Cell assemblies (functional groupings)
    - Activation tracking
    - Beautiful matplotlib and pyvis visualizations
    """

    def __init__(self):
        # PyVis network for interactive HTML
        self.net = Network(notebook=True, cdn_resources='in_line', height="750px", width="100%")
        self.net.barnes_hut()  # Physics simulation

        # Core agents
        self.static_agents = [
            "PlannerAgent", "CoderAgent", "EvaluatorAgent",
            "KnowledgeAgent", "AuditorAgent",
            "ExperimentOrchestrator", "ResultsSynthesizer"
        ]

        # Cell assemblies
        self.assemblies: Dict[str, CellAssembly] = {}
        self.active_nodes: Set[str] = set()

        # NetworkX graph for analysis
        self.graph = nx.DiGraph()

        # Initialize static agents
        for agent in self.static_agents:
            self.net.add_node(agent, label=agent, color="#95A5A6",
                            shape="box", size=20)
            self.graph.add_node(agent, type="static")

        # Create default assemblies
        self._create_default_assemblies()

        logging.info("Enhanced BrainMap initialized with cell assemblies")

    def _create_default_assemblies(self):
        """Create default functional assemblies"""

        # Planning & Strategy Assembly
        self.add_assembly(
            "planning_assembly",
            "Planning & Strategy",
            members={"PlannerAgent", "ExperimentOrchestrator"},
            function="Strategic planning and experiment design",
            color="#E74C3C"  # Red
        )

        # Execution Assembly
        self.add_assembly(
            "execution_assembly",
            "Execution & Implementation",
            members={"CoderAgent"},
            function="Code generation and execution",
            color="#2ECC71"  # Green
        )

        # Evaluation Assembly
        self.add_assembly(
            "evaluation_assembly",
            "Evaluation & Analysis",
            members={"EvaluatorAgent", "ResultsSynthesizer"},
            function="Performance evaluation and result synthesis",
            color="#3498DB"  # Blue
        )

        # Knowledge Assembly
        self.add_assembly(
            "knowledge_assembly",
            "Knowledge & Memory",
            members={"KnowledgeAgent"},
            function="Knowledge storage and retrieval",
            color="#F39C12"  # Orange
        )

        # Safety Assembly
        self.add_assembly(
            "safety_assembly",
            "Safety & Auditing",
            members={"AuditorAgent"},
            function="Safety verification and compliance",
            color="#9B59B6"  # Purple
        )

    def add_assembly(self, assembly_id: str, name: str,
                    members: Set[str] = None,
                    subassemblies: List[str] = None,
                    function: str = "",
                    color: str = "#3498DB"):
        """
        Add a cell assembly

        Args:
            assembly_id: Unique identifier
            name: Human-readable name
            members: Set of agent IDs in this assembly
            subassemblies: List of child assembly IDs
            function: Description of assembly's function
            color: Display color
        """
        assembly = CellAssembly(
            assembly_id=assembly_id,
            name=name,
            members=members or set(),
            subassemblies=subassemblies or [],
            function=function,
            color=color
        )

        self.assemblies[assembly_id] = assembly
        logging.debug(f"Added assembly: {name}")

    def add_dynamic_node(self, agent_name: str, agent_type: str,
                        assembly_id: Optional[str] = None):
        """
        Add a dynamically created agent

        Args:
            agent_name: Agent identifier
            agent_type: Type of agent
            assembly_id: Optional assembly to join
        """
        logging.info(f"BrainMap: Adding dynamic node {agent_name} of type {agent_type}")

        self.net.add_node(agent_name,
                        label=f"{agent_name}\n({agent_type})",
                        color="#1ABC9C",  # Turquoise for dynamic
                        shape="ellipse",
                        size=15)

        self.graph.add_node(agent_name, type="dynamic", agent_type=agent_type)

        # Add to assembly if specified
        if assembly_id and assembly_id in self.assemblies:
            self.assemblies[assembly_id].members.add(agent_name)

        # Connect to planner
        self.net.add_edge("PlannerAgent", agent_name)
        self.graph.add_edge("PlannerAgent", agent_name)

    def remove_dynamic_node(self, agent_name: str):
        """Deactivate a dynamic node"""
        logging.info(f"BrainMap: Deactivating dynamic node {agent_name}")

        # Change color to muted
        try:
            node = self.net.get_node(agent_name)
            if node:
                node['color'] = "#ECF0F1"  # Light gray

            # Remove from assemblies
            for assembly in self.assemblies.values():
                assembly.members.discard(agent_name)

            self.active_nodes.discard(agent_name)

        except Exception as e:
            logging.warning(f"Could not deactivate {agent_name}: {e}")

    def activate_node(self, agent_name: str, level: float = 1.0):
        """
        Activate a node

        Args:
            agent_name: Node to activate
            level: Activation level (0.0-1.0)
        """
        logging.info(f"BrainMap: Activating {agent_name} (level={level})")

        try:
            node = self.net.get_node(agent_name)
            if node:
                # Color intensity based on activation
                if level > 0.7:
                    node['color'] = "#E74C3C"  # Bright red
                elif level > 0.4:
                    node['color'] = "#F39C12"  # Orange
                else:
                    node['color'] = "#F1C40F"  # Yellow

                node['size'] = int(15 + level * 10)

            self.active_nodes.add(agent_name)

            # Update assembly activation
            for assembly in self.assemblies.values():
                if agent_name in assembly.members:
                    # Assembly activation = average of member activations
                    active_members = assembly.members & self.active_nodes
                    if active_members:
                        assembly.activation_level = len(active_members) / len(assembly.members)

        except Exception as e:
            logging.warning(f"Could not activate {agent_name}: {e}")

    def deactivate_node(self, agent_name: str):
        """Deactivate a node"""
        logging.info(f"BrainMap: Deactivating {agent_name}")

        try:
            node = self.net.get_node(agent_name)
            if node:
                # Return to default color based on type
                if agent_name in self.static_agents:
                    node['color'] = "#95A5A6"  # Gray
                else:
                    node['color'] = "#1ABC9C"  # Turquoise

                node['size'] = 15

            self.active_nodes.discard(agent_name)

        except Exception as e:
            logging.warning(f"Could not deactivate {agent_name}: {e}")

    def visualize_assemblies(self, title: str = "Brain Map - Cell Assemblies",
                           figsize: Tuple[int, int] = (16, 12)) -> plt.Figure:
        """
        Create beautiful matplotlib visualization of cell assemblies

        Args:
            title: Plot title
            figsize: Figure size

        Returns:
            matplotlib Figure
        """
        fig, ax = plt.subplots(figsize=figsize)

        # Layout assemblies in a grid
        num_assemblies = len(self.assemblies)
        cols = min(3, num_assemblies)
        rows = (num_assemblies + cols - 1) // cols

        assembly_positions = {}
        assembly_list = list(self.assemblies.values())

        for idx, assembly in enumerate(assembly_list):
            row = idx // cols
            col = idx % cols

            x = col * 4 + 1
            y = (rows - row - 1) * 3 + 1

            assembly_positions[assembly.assembly_id] = (x, y)

            # Draw assembly box
            width = 3
            height = 2

            box = FancyBboxPatch(
                (x - width/2, y - height/2), width, height,
                boxstyle="round,pad=0.1",
                facecolor=assembly.color,
                edgecolor='black',
                linewidth=2,
                alpha=0.3 if assembly.activation_level == 0 else 0.6
            )
            ax.add_patch(box)

            # Assembly label
            ax.text(x, y + height/2 - 0.2, assembly.name,
                   ha='center', va='top',
                   fontsize=12, fontweight='bold')

            # Function description
            ax.text(x, y, assembly.function,
                   ha='center', va='center',
                   fontsize=9, wrap=True,
                   style='italic')

            # Member count
            ax.text(x, y - height/2 + 0.2,
                   f"{len(assembly.members)} members",
                   ha='center', va='bottom',
                   fontsize=8)

            # Activation indicator
            if assembly.activation_level > 0:
                activation_text = f"⚡ {assembly.activation_level:.0%}"
                ax.text(x + width/2 - 0.2, y + height/2 - 0.2,
                       activation_text,
                       ha='right', va='top',
                       fontsize=10, fontweight='bold',
                       color='#E74C3C')

        # Draw connections between assemblies
        # (e.g., planning → execution → evaluation)
        connections = [
            ("planning_assembly", "execution_assembly"),
            ("execution_assembly", "evaluation_assembly"),
            ("evaluation_assembly", "knowledge_assembly"),
            ("knowledge_assembly", "planning_assembly"),
            ("safety_assembly", "execution_assembly"),
        ]

        for source_id, target_id in connections:
            if source_id in assembly_positions and target_id in assembly_positions:
                x1, y1 = assembly_positions[source_id]
                x2, y2 = assembly_positions[target_id]

                ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                          arrowprops=dict(arrowstyle='->', lw=2,
                                        color='gray', alpha=0.5))

        ax.set_xlim(-0.5, cols * 4 + 0.5)
        ax.set_ylim(-0.5, rows * 3 + 0.5)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(title, fontsize=18, fontweight='bold', pad=20)

        # Legend
        legend_elements = [
            patches.Patch(facecolor=assembly.color, edgecolor='black',
                         label=assembly.name, alpha=0.6)
            for assembly in assembly_list[:5]  # Top 5 assemblies
        ]

        ax.legend(handles=legend_elements, loc='upper left',
                 fontsize=10, framealpha=0.9)

        plt.tight_layout()
        return fig

    def show(self, file_name: str = "brain_map.html"):
        """Generate interactive HTML visualization"""
        self.net.show(file_name)
        logging.info(f"BrainMap saved to {file_name}")

    def get_stats(self) -> Dict[str, Any]:
        """Get brain map statistics"""
        return {
            'total_nodes': len(self.graph.nodes),
            'static_agents': len(self.static_agents),
            'dynamic_agents': len(self.graph.nodes) - len(self.static_agents),
            'active_nodes': len(self.active_nodes),
            'assemblies': len(self.assemblies),
            'assembly_details': {
                aid: {
                    'name': a.name,
                    'members': len(a.members),
                    'activation': a.activation_level
                }
                for aid, a in self.assemblies.items()
            }
        }