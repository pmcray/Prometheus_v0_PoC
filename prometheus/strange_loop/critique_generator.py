"""
Self-Referential Critique Generator — Prometheus v0.98 (WP-06)

Analyzes cognitive traces to identify strategic flaws and strengths
in the agent's own reasoning process.
"""

from typing import Dict, List, Any, Tuple
from prometheus.llm_backend import get_llm_backend

class SelfReferentialCritiqueGenerator:
    """
    The "Meta-Judge" that analyzes the agent's internal thought process.
    """
    def __init__(self, model_name: str = None):
        self.backend = get_llm_backend(model_name=model_name)

    def generate_critique(self, trace_dict: Dict) -> str:
        """
        Analyzes a cognitive trace and generates a symbolic, 
        natural-language critique of the strategy employed.
        """
        prompt = f"""
        You are the Self-Referential Critique module (Meta-Judge) for a recursive AI.
        Your task is to analyze the following "Cognitive Trace" of an agent attempting to solve a problem.
        
        Cognitive Trace:
        {json.dumps(trace_dict, indent=2)}
        
        Identify:
        1. The core strategy employed.
        2. Strengths of the reasoning process.
        3. Strategic weaknesses (e.g., inefficiency, flawed logic, missed patterns).
        4. Concrete suggestions for a better reasoning strategy.
        
        Respond with a structured critique focusing on the *strategy* rather than just the final answer.
        """
        
        critique = self.backend.generate(prompt)
        return critique

import json
