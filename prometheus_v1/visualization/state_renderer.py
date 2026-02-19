import json
import os
from typing import List, Dict, Any
from prometheus_v1.core.data_models import ContextFrame

class StateRenderer:
    """
    Dynamic State Visualization using Mermaid flowchart syntax.
    Provides a 'live MRI' of the agent's cognition.
    """
    def __init__(self, output_file: str = "prometheus_v1/visualization/state_history.md"):
        self.output_file = output_file
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

    def render_current_state(self, stack: List[ContextFrame], graph_data: Dict[str, Any]) -> str:
        """
        Convert current ContextStack and CausalGraph into Mermaid markdown.
        """
        mermaid_lines = ["graph TD"]
        
        # 1. Render the Context Stack (Reasoning Hierarchy)
        for i, frame in enumerate(stack):
            node_id = f"Stack_{i}"
            label = f'"{frame.goal}"'
            mermaid_lines.append(f"  {node_id}[{label}]")
            if i > 0:
                # Link parents to children (descending depth)
                mermaid_lines.append(f"  Stack_{i-1} --> {node_id}")

        # 2. Render the Causal Graph (Knowledge dependencies)
        # nodes: list, links: list (from nx.node_link_data)
        for node in graph_data.get('nodes', []):
            node_id = node['id'].replace(" ", "_")
            node_type = node.get('type', 'concept')
            # Styling nodes based on type
            if node_type == "expert":
                mermaid_lines.append(f"  {node_id}{{{{{node['id']}}}}}") # Hexagon
            else:
                mermaid_lines.append(f"  {node_id}(({node['id']}))") # Circle
        
        for link in graph_data.get('links', []):
            source = link['source'].replace(" ", "_")
            target = link['target'].replace(" ", "_")
            weight = link.get('weight', 1.0)
            mermaid_lines.append(f"  {source} -- causal:{weight:.1f} --> {target}")

        mermaid_block = "```mermaid\n" + "\n".join(mermaid_lines) + "\n```"
        
        # 3. Save to markdown file for real-time viewing
        self._persist(mermaid_block)
        return mermaid_block

    def _persist(self, content: str):
        """Append the mermaid diagram to the state history file."""
        mode = "w" # Overwrite current view for now
        try:
            with open(self.output_file, mode) as f:
                f.write(f"# Prometheus v1.0 State History\n")
                f.write(f"Updated: {os.uname().nodename} at {os.environ.get('USER', 'AI')}\n\n")
                f.write(content)
            print(f"StateRenderer: State rendered and saved to {self.output_file}")
        except Exception as e:
            print(f"StateRenderer: Error persisting visualization: {e}")
