
import networkx as nx
from typing import List, Dict, Optional, Any
from prometheus_v1.core.data_models import CausalNode, CausalNodeType, ExpertSignature
from prometheus.llm_backend import get_llm_backend
import json
import os

class CausalRouter:
    """
    Dispatcher based on I.J. Good's Causal Calculus and Subassemblies.
    Dynamically routes tasks to expert subassemblies using a Causal Relevance Score (CRS).
    """
    def __init__(self, persistence_path: str = "prometheus_v1/core/router/causal_graph.json"):
        self.graph = nx.DiGraph()
        self.persistence_path = persistence_path
        self.backend = get_llm_backend()
        self._load_graph()

    def _load_graph(self):
        """Loads the Causal Dependency Graph (CDG) from disk."""
        if os.path.exists(self.persistence_path):
            try:
                with open(self.persistence_path, "r") as f:
                    data = json.load(f)
                    self.graph = nx.node_link_graph(data)
                print(f"CausalRouter: Loaded CDG with {self.graph.number_of_nodes()} nodes.")
            except Exception as e:
                print(f"CausalRouter: Error loading graph: {e}")
                self._initialize_default_graph()
        else:
            self._initialize_default_graph()

    def _initialize_default_graph(self):
        """Seed the graph with basic causal subassemblies for Phase 1."""
        print("CausalRouter: Initializing default CDG.")
        nodes = [
            CausalNode(id="Memory Management", type=CausalNodeType.CONCEPT, description="Handling memory allocation, leaks, and optimization."),
            CausalNode(id="Algorithm Optimization", type=CausalNodeType.CONCEPT, description="Complexity reduction and performance tuning."),
            CausalNode(id="Formal Verification", type=CausalNodeType.CONCEPT, description="Proving correctness with Lean 4."),
            CausalNode(id="Code Synthesis", type=CausalNodeType.CONCEPT, description="Generating Python or Lean code."),
            CausalNode(id="MemoryExpert", type=CausalNodeType.EXPERT, description="Expert subassembly for memory tasks."),
            CausalNode(id="AlgorithmExpert", type=CausalNodeType.EXPERT, description="Expert subassembly for algorithms."),
        ]
        for node in nodes:
            self.graph.add_node(node.id, **node.model_dump())
        
        # Define some causal edges (An edge X -> Y means X is a dependency of Y)
        self.graph.add_edge("Memory Management", "MemoryExpert", weight=0.9)
        self.graph.add_edge("Algorithm Optimization", "AlgorithmExpert", weight=0.9)
        self._persist_graph()

    def _persist_graph(self):
        """Saves the CDG to disk."""
        try:
            with open(self.persistence_path, "w") as f:
                data = nx.node_link_data(self.graph)
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"CausalRouter: Error persisting graph: {e}")

    def calculate_crs(self, task: str, expert_id: str) -> float:
        """
        Calculates the Causal Relevance Score (CRS) for an expert.
        CRS = P(Success | Expert) - P(Success | Not Expert)
        For Phase 2, we use the LLM to perform a counterfactual simulation.
        """
        prompt = f"""
        Analyze the following task and determine the CAUSAL RELEVANCE of the expert '{expert_id}'.
        Task: "{task}"
        
        Counterfactual Reasoning:
        1. If this expert is NOT used, what is the probability of failure?
        2. If this expert IS used, what is the probability of success?
        
        Provide a Causal Relevance Score (CRS) between 0.0 and 1.0, where 1.0 means this expert is absolutely necessary.
        Respond ONLY with a single numeric value.
        """
        try:
            response = self.backend.generate(prompt)
            # Basic numeric extraction
            score = float(response.strip().split()[0])
            return min(max(score, 0.0), 1.0)
        except:
            return 0.5 # Neutral fallback

    def route_task(self, task: str) -> str:
        """Determines the best expert to handle the task."""
        experts = [n for n, d in self.graph.nodes(data=True) if d.get('type') == CausalNodeType.EXPERT]
        if not experts:
            return "Generalist"

        scores = {}
        for expert in experts:
            scores[expert] = self.calculate_crs(task, expert)
        
        best_expert = max(scores, key=scores.get)
        print(f"CausalRouter: Task routed to '{best_expert}' (CRS: {scores[best_expert]:.2f})")
        return best_expert
