"""
Causal Agentic Mesh (CAM) - v0.75+

A network of causally-connected agents that can:
1. Trace causal chains of reasoning
2. Visualize agent interactions and dependencies
3. Identify bottlenecks and critical paths
4. Enable explainable AI through causal tracking

The mesh tracks:
- Agent activations and their causes
- Information flow between agents
- Causal influence on decisions
- Critical reasoning paths

This implements Judea Pearl's causal inference framework
applied to multi-agent AI systems.
"""

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging


@dataclass
class CausalNode:
    """
    A node in the causal mesh representing an agent or process
    """
    node_id: str
    node_type: str  # "agent", "tool", "decision", "observation"
    timestamp: str
    activation_level: float = 0.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalEdge:
    """
    A causal link between nodes
    """
    source: str
    target: str
    edge_type: str  # "causes", "informs", "depends_on", "observes"
    strength: float = 1.0  # 0.0 to 1.0
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class CausalAgenticMesh:
    """
    Network tracking causal relationships between agents and processes

    This enables:
    - Explainable decision-making
    - Bottleneck identification
    - Critical path analysis
    - Debugging multi-agent systems
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, CausalNode] = {}
        self.edges: List[CausalEdge] = []
        self.timesteps: List[str] = []
        self.active_nodes: Set[str] = set()

        logging.info("CausalAgenticMesh initialized")

    def add_node(self, node_id: str, node_type: str,
                 activation_level: float = 0.0,
                 **metadata) -> CausalNode:
        """
        Add a node to the mesh

        Args:
            node_id: Unique identifier
            node_type: Type of node (agent, tool, decision, etc.)
            activation_level: Current activation (0.0-1.0)
            **metadata: Additional node properties

        Returns:
            Created CausalNode
        """
        timestamp = datetime.now().isoformat()

        node = CausalNode(
            node_id=node_id,
            node_type=node_type,
            timestamp=timestamp,
            activation_level=activation_level,
            metadata=metadata
        )

        self.nodes[node_id] = node
        self.graph.add_node(node_id, **node.__dict__)

        if activation_level > 0.0:
            self.active_nodes.add(node_id)

        logging.debug(f"Added node: {node_id} ({node_type})")
        return node

    def add_edge(self, source: str, target: str, edge_type: str,
                 strength: float = 1.0, **metadata) -> CausalEdge:
        """
        Add a causal edge between nodes

        Args:
            source: Source node ID
            target: Target node ID
            edge_type: Type of causal relationship
            strength: Strength of causal link (0.0-1.0)
            **metadata: Additional edge properties

        Returns:
            Created CausalEdge
        """
        if source not in self.nodes:
            raise ValueError(f"Source node {source} not found")
        if target not in self.nodes:
            raise ValueError(f"Target node {target} not found")

        timestamp = datetime.now().isoformat()

        edge = CausalEdge(
            source=source,
            target=target,
            edge_type=edge_type,
            strength=strength,
            timestamp=timestamp,
            metadata=metadata
        )

        self.edges.append(edge)
        self.graph.add_edge(source, target,
                          edge_type=edge_type,
                          strength=strength,
                          **metadata)

        logging.debug(f"Added edge: {source} → {target} ({edge_type})")
        return edge

    def activate_node(self, node_id: str, level: float = 1.0):
        """Set node activation level"""
        if node_id in self.nodes:
            self.nodes[node_id].activation_level = level
            self.graph.nodes[node_id]['activation_level'] = level

            if level > 0.0:
                self.active_nodes.add(node_id)
            else:
                self.active_nodes.discard(node_id)

    def get_causal_chain(self, target_node: str,
                        max_depth: int = 10) -> List[List[str]]:
        """
        Get all causal chains leading to a target node

        Args:
            target_node: Node to trace back from
            max_depth: Maximum chain length

        Returns:
            List of causal chains (lists of node IDs)
        """
        if target_node not in self.nodes:
            return []

        chains = []

        def dfs(node: str, path: List[str], depth: int):
            if depth >= max_depth:
                return

            # Get predecessors
            preds = list(self.graph.predecessors(node))

            if not preds:
                # Found root cause
                chains.append(path[::-1])  # Reverse to show cause→effect
            else:
                for pred in preds:
                    if pred not in path:  # Avoid cycles
                        dfs(pred, path + [pred], depth + 1)

        dfs(target_node, [target_node], 0)
        return chains

    def find_critical_path(self, start_node: str, end_node: str) -> Optional[List[str]]:
        """
        Find the critical path between two nodes
        (path with highest cumulative causal strength)

        Args:
            start_node: Starting node
            end_node: Ending node

        Returns:
            List of node IDs in critical path, or None if no path exists
        """
        try:
            # Find all paths
            paths = list(nx.all_simple_paths(self.graph, start_node, end_node))

            if not paths:
                return None

            # Score each path by cumulative edge strength
            best_path = None
            best_score = -1

            for path in paths:
                score = 0
                for i in range(len(path) - 1):
                    edge_data = self.graph.edges[path[i], path[i+1]]
                    score += edge_data.get('strength', 1.0)

                if score > best_score:
                    best_score = score
                    best_path = path

            return best_path

        except nx.NetworkXNoPath:
            return None

    def identify_bottlenecks(self, threshold: int = 3) -> List[str]:
        """
        Identify bottleneck nodes (high betweenness centrality)

        Args:
            threshold: Minimum connections to consider

        Returns:
            List of bottleneck node IDs
        """
        if len(self.graph.nodes) < 2:
            return []

        # Calculate betweenness centrality
        centrality = nx.betweenness_centrality(self.graph)

        # Filter by threshold
        bottlenecks = [
            node for node, score in centrality.items()
            if score > 0 and self.graph.degree(node) >= threshold
        ]

        return sorted(bottlenecks, key=lambda n: centrality[n], reverse=True)

    def visualize(self, title: str = "Causal Agentic Mesh",
                 figsize: Tuple[int, int] = (14, 10),
                 highlight_active: bool = True,
                 show_edge_labels: bool = True) -> plt.Figure:
        """
        Visualize the causal mesh network

        Args:
            title: Plot title
            figsize: Figure size
            highlight_active: Highlight currently active nodes
            show_edge_labels: Show edge type labels

        Returns:
            matplotlib Figure
        """
        fig, ax = plt.subplots(figsize=figsize)

        if len(self.graph.nodes) == 0:
            ax.text(0.5, 0.5, "No nodes in mesh",
                   ha='center', va='center', fontsize=16)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            return fig

        # Layout
        pos = nx.spring_layout(self.graph, k=2, iterations=50, seed=42)

        # Node colors based on type and activation
        node_colors = []
        node_sizes = []

        type_colors = {
            'agent': '#3498DB',      # Blue
            'tool': '#2ECC71',       # Green
            'decision': '#E74C3C',   # Red
            'observation': '#F39C12', # Orange
        }

        for node in self.graph.nodes():
            node_type = self.nodes[node].node_type
            base_color = type_colors.get(node_type, '#95A5A6')

            # Highlight active nodes
            if highlight_active and node in self.active_nodes:
                node_colors.append('#F1C40F')  # Gold for active
                node_sizes.append(1500)
            else:
                node_colors.append(base_color)
                node_sizes.append(1000)

        # Draw nodes
        nx.draw_networkx_nodes(self.graph, pos,
                              node_color=node_colors,
                              node_size=node_sizes,
                              alpha=0.8,
                              ax=ax)

        # Draw edges with different styles for different types
        edge_types = set(e.edge_type for e in self.edges)

        edge_styles = {
            'causes': 'solid',
            'informs': 'dashed',
            'depends_on': 'dotted',
            'observes': 'dashdot',
        }

        for edge_type in edge_types:
            edge_list = [
                (e.source, e.target)
                for e in self.edges
                if e.edge_type == edge_type
            ]

            if edge_list:
                nx.draw_networkx_edges(
                    self.graph, pos,
                    edgelist=edge_list,
                    style=edge_styles.get(edge_type, 'solid'),
                    alpha=0.6,
                    arrows=True,
                    arrowsize=20,
                    width=2,
                    ax=ax
                )

        # Labels
        labels = {node: node.split('_')[0] for node in self.graph.nodes()}
        nx.draw_networkx_labels(self.graph, pos, labels,
                               font_size=10,
                               font_weight='bold',
                               ax=ax)

        # Edge labels (if requested)
        if show_edge_labels and len(self.edges) < 20:  # Only if not too cluttered
            edge_labels = {
                (e.source, e.target): e.edge_type
                for e in self.edges
            }
            nx.draw_networkx_edge_labels(self.graph, pos, edge_labels,
                                        font_size=8, ax=ax)

        # Legend
        legend_elements = [
            mpatches.Patch(color=color, label=node_type.title())
            for node_type, color in type_colors.items()
        ]

        if highlight_active:
            legend_elements.append(
                mpatches.Patch(color='#F1C40F', label='Active')
            )

        ax.legend(handles=legend_elements, loc='upper left', fontsize=10)

        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.axis('off')

        plt.tight_layout()
        return fig

    def get_stats(self) -> Dict[str, Any]:
        """Get mesh statistics"""
        return {
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges),
            'active_nodes': len(self.active_nodes),
            'node_types': {
                node_type: sum(1 for n in self.nodes.values() if n.node_type == node_type)
                for node_type in set(n.node_type for n in self.nodes.values())
            },
            'edge_types': {
                edge_type: sum(1 for e in self.edges if e.edge_type == edge_type)
                for edge_type in set(e.edge_type for e in self.edges)
            },
            'avg_degree': sum(dict(self.graph.degree()).values()) / len(self.graph.nodes) if len(self.graph.nodes) > 0 else 0,
            'is_connected': nx.is_weakly_connected(self.graph) if len(self.graph.nodes) > 0 else False,
        }

    def export_json(self, filepath: str):
        """Export mesh to JSON"""
        data = {
            'nodes': [
                {
                    'id': node.node_id,
                    'type': node.node_type,
                    'activation': node.activation_level,
                    'timestamp': node.timestamp,
                    'metadata': node.metadata
                }
                for node in self.nodes.values()
            ],
            'edges': [
                {
                    'source': edge.source,
                    'target': edge.target,
                    'type': edge.edge_type,
                    'strength': edge.strength,
                    'timestamp': edge.timestamp,
                    'metadata': edge.metadata
                }
                for edge in self.edges
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        logging.info(f"Mesh exported to {filepath}")


def create_example_mesh() -> CausalAgenticMesh:
    """
    Create an example mesh for demonstration

    Shows a typical multi-agent reasoning chain:
    Observation → Perception → Planning → Action → Result
    """
    mesh = CausalAgenticMesh()

    # Add nodes
    mesh.add_node("observation_1", "observation", 1.0,
                 description="Observe game state")
    mesh.add_node("perception_agent", "agent", 1.0,
                 description="Perceive and extract features")
    mesh.add_node("planner_agent", "agent", 1.0,
                 description="Plan next move")
    mesh.add_node("evaluation_tool", "tool", 0.8,
                 description="Evaluate board position")
    mesh.add_node("decision_1", "decision", 1.0,
                 description="Select move")
    mesh.add_node("action_1", "observation", 0.5,
                 description="Execute move")

    # Add causal edges
    mesh.add_edge("observation_1", "perception_agent", "causes", 1.0)
    mesh.add_edge("perception_agent", "planner_agent", "informs", 0.9)
    mesh.add_edge("perception_agent", "evaluation_tool", "depends_on", 0.7)
    mesh.add_edge("evaluation_tool", "planner_agent", "informs", 0.8)
    mesh.add_edge("planner_agent", "decision_1", "causes", 1.0)
    mesh.add_edge("decision_1", "action_1", "causes", 1.0)

    return mesh


if __name__ == "__main__":
    # Demo
    logging.basicConfig(level=logging.INFO)

    mesh = create_example_mesh()

    print("Causal Agentic Mesh Stats:")
    print(json.dumps(mesh.get_stats(), indent=2))

    print("\nCritical path from observation to action:")
    path = mesh.find_critical_path("observation_1", "action_1")
    print(" → ".join(path) if path else "No path found")

    print("\nBottleneck nodes:")
    print(mesh.identify_bottlenecks())

    # Visualize
    fig = mesh.visualize(title="Example Causal Agentic Mesh")
    plt.savefig("causal_mesh_example.png", dpi=150, bbox_inches='tight')
    print("\n✓ Visualization saved to causal_mesh_example.png")
