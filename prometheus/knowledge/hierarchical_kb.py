"""
Hierarchical Knowledge Base — Prometheus v0.98 (WP-07)

Implements multi-level Knowledge Representation and Reasoning (KRR).
Supports 'chunking' of low-level logical steps into high-level concepts.
"""

import json
import networkx as nx
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field

@dataclass
class KnowledgeSymbol:
    """A symbolic representation of a concept or operation."""
    id: str
    level: int  # 0: Axiom, 1: Lemma, 2: Strategy
    description: str
    dependencies: List[str] = field(default_factory=list) # IDs of lower-level symbols
    metadata: Dict[str, Any] = field(default_factory=dict)

class HierarchicalKnowledgeBase:
    """
    Manages a directed acyclic graph (DAG) of symbolic knowledge.
    """
    def __init__(self):
        self.symbols: Dict[str, KnowledgeSymbol] = {}
        self.graph = nx.DiGraph()
        
        # Seed with basic "Axioms" for Prometheus
        self._seed_axioms()

    def _seed_axioms(self):
        """Initializes the base level of the hierarchy."""
        axioms = [
            KnowledgeSymbol("pure_function", 0, "A function with no side effects."),
            KnowledgeSymbol("recursion", 0, "A function that calls itself."),
            KnowledgeSymbol("iteration", 0, "A loop structure."),
            KnowledgeSymbol("state_transition", 0, "A change in the environment state.")
        ]
        for a in axioms:
            self.add_symbol(a)

    def add_symbol(self, symbol: KnowledgeSymbol):
        self.symbols[symbol.id] = symbol
        self.graph.add_node(symbol.id, level=symbol.level)
        for dep in symbol.dependencies:
            if dep in self.symbols:
                self.graph.add_edge(symbol.id, dep)

    def create_chunk(self, new_id: str, component_ids: List[str], description: str) -> KnowledgeSymbol:
        """
        Creates a new higher-level symbol ('chunk') from existing components.
        """
        # Determine level based on highest component level + 1
        max_level = max([self.symbols[cid].level for cid in component_ids if cid in self.symbols], default=0)
        
        chunk = KnowledgeSymbol(
            id=new_id,
            level=max_level + 1,
            description=description,
            dependencies=component_ids
        )
        self.add_symbol(chunk)
        return chunk

    def get_subgraph(self, symbol_id: str) -> List[str]:
        """Returns all recursive dependencies for a symbol."""
        if symbol_id not in self.graph:
            return []
        return list(nx.descendants(self.graph, symbol_id))

    def to_json(self) -> str:
        data = {sid: sym.__dict__ for sid, sym in self.symbols.items()}
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str):
        kb = cls()
        data = json.loads(json_str)
        for sid, sym_data in data.items():
            sym = KnowledgeSymbol(**sym_data)
            kb.add_symbol(sym)
        return kb
