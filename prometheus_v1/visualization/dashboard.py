
import ipywidgets as widgets
from IPython.display import display, clear_output, Markdown
import time
import json
import os
from typing import List, Dict, Any

class PrometheusDashboard:
    """
    The 'Live MRI' of Project Prometheus.
    Visualizes the internal cognitive state, including the Context Stack,
    Causal Graph, and Evolutionary Fitness.
    """
    def __init__(self, state_file: str = "state_history.json", graph_file: str = "prometheus_v1/core/router/causal_graph.json"):
        self.state_file = state_file
        self.graph_file = graph_file
        
        # UI Components
        self.output_log = widgets.Output(layout={'border': '1px solid black', 'height': '200px', 'overflow_y': 'scroll'})
        self.stack_view = widgets.Output(layout={'border': '1px solid blue', 'height': '250px'})
        self.graph_view = widgets.Output(layout={'border': '1px solid green', 'height': '400px'})
        self.fitness_view = widgets.Output(layout={'border': '1px solid red', 'height': '150px'})
        
        self.header = widgets.HTML("<h1>🚀 Prometheus v1.0 'Live MRI' Dashboard</h1>")
        self.status_label = widgets.Label(value="Status: Initializing...")
        
        self.layout = widgets.VBox([
            self.header,
            self.status_label,
            widgets.HBox([
                widgets.VBox([widgets.Label("🧠 Hofstadter Context Stack"), self.stack_view], layout={'width': '50%'}),
                widgets.VBox([widgets.Label("🧬 Evolutionary Fitness"), self.fitness_view], layout={'width': '50%'})
            ]),
            widgets.Label("🕸️ Good's Causal Agentic Mesh"),
            self.graph_view,
            widgets.Label("📜 Cognitive Audit Log"),
            self.output_log
        ])

    def log(self, message: str):
        with self.output_log:
            print(f"[{time.strftime('%H:%M:%S')}] {message}")

    def update_stack(self):
        """Render the current reasoning hierarchy."""
        with self.stack_view:
            clear_output(wait=True)
            if not os.path.exists(self.state_file):
                print("No active context stack found.")
                return
            
            try:
                with open(self.state_file, "r") as f:
                    stack = json.load(f)
                
                md_text = "### Reasoning Hierarchy
"
                for i, frame in enumerate(reversed(stack)):
                    indent = "  " * (len(stack) - 1 - i)
                    depth_marker = "↳" if i > 0 else "●"
                    md_text += f"{indent}{depth_marker} **Goal:** {frame['goal']}
"
                display(Markdown(md_text))
            except Exception as e:
                print(f"Error reading stack: {e}")

    def update_graph(self):
        """Render the Mermaid Causal Graph."""
        with self.graph_view:
            clear_output(wait=True)
            # In Colab, we rely on the markdown rendering the mermaid block
            # This requires the user to have a Mermaid extension or we use a public API to render
            md_path = "prometheus_v1/visualization/state_history.md"
            if os.path.exists(md_path):
                with open(md_path, "r") as f:
                    display(Markdown(f.read()))

    def update_fitness(self, generation: int, fitness: float):
        with self.fitness_view:
            clear_output(wait=True)
            # Simulating a small bar chart or metric
            display(Markdown(f"### Generation {generation}
**Peak Fitness Score:** `{fitness:.2f}`"))

    def display(self):
        display(self.layout)
        self.log("Dashboard initialized. Waiting for agent activity...")

    def refresh(self):
        """Polled refresh of the UI components."""
        self.status_label.value = f"Status: Active - Last Update {time.strftime('%H:%M:%S')}"
        self.update_stack()
        self.update_graph()

def start_mri_monitor(dashboard: PrometheusDashboard, interval: int = 5):
    """Background loop to refresh the dashboard."""
    import threading
    def loop():
        while True:
            dashboard.refresh()
            time.sleep(interval)
    
    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    dashboard.log(f"Background monitor started (polling every {interval}s)")
