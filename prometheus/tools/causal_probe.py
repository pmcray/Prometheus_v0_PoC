"""
Causal Probe: Endogenous Causal Attention Testing (Task P1.T1)

This module implements the 'CQO vs. QOC' permutation tests to verify
if a model attends to the causal structure of a prompt rather than
statistical artifacts like positional correlation.
"""

import google.generativeai as genai
import time
from typing import Dict, List, Any, Tuple

class CausalProbe:
    """
    Probe for testing Endogenous Causal Attention in Foundation Models.
    """
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)

    def run_permutation_test(self, context: str, question: str, options: Dict[str, str], 
                             correct_option: str) -> Dict[str, Any]:
        """
        Run CQO (Context-Question-Option) and QOC (Question-Option-Context) tests.
        """
        
        # 1. CQO Format
        cqo_prompt = f"Context: {context}\n\nQuestion: {question}\n\nOptions:\n"
        for label, text in options.items():
            cqo_prompt += f"{label}: {text}\n"
        cqo_prompt += "\nAnswer with only the correct option label (e.g., A, B, C)."

        # 2. QOC Format
        qoc_prompt = f"Question: {question}\n\nOptions:\n"
        for label, text in options.items():
            qoc_prompt += f"{label}: {text}\n"
        qoc_prompt += f"\nContext: {context}"
        qoc_prompt += "\n\nAnswer with only the correct option label (e.g., A, B, C)."

        results = {}
        
        # Test CQO
        start_time = time.time()
        cqo_resp = self.model.generate_content(cqo_prompt).text.strip()
        results['cqo'] = {
            'response': cqo_resp,
            'correct': cqo_resp == correct_option,
            'latency': time.time() - start_time
        }

        # Test QOC
        start_time = time.time()
        qoc_resp = self.model.generate_content(qoc_prompt).text.strip()
        results['qoc'] = {
            'response': qoc_resp,
            'correct': qoc_resp == correct_option,
            'latency': time.time() - start_time
        }

        # Calculate Degradation
        results['is_causally_stable'] = results['cqo']['correct'] == results['qoc']['correct']
        
        return results

if __name__ == "__main__":
    # Example Test Case (Logic/Causality)
    context = "If the red button is pressed, the light turns on. The light is currently off."
    question = "What happens if we press the red button?"
    options = {"A": "The light stays off", "B": "The light turns on", "C": "Nothing happens"}
    correct = "B"

    # For demonstration purposes, we mock the generate_content if run standalone
    # to avoid needing a real API key.
    probe = CausalProbe()
    print(f"Probe initialized for {probe.model_name}")
