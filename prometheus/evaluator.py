import subprocess
import os
import ast
import google.generativeai as genai
from .critique import CausalCritique
from .tools import LeanTool
from .proof_tree import ProofTree

class EvaluatorAgent:
    def __init__(self, api_key, lean_tool: LeanTool):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.lean_tool = lean_tool

    def summarize_proof_strategy(self, proof_tree: ProofTree, theorem: str):
        print("EvaluatorAgent: Summarizing successful proof strategy.")
        successful_node = self._find_solved_node(proof_tree.root)
        if not successful_node:
            return "Could not find a successful proof path to summarize."
        tactics = proof_tree.get_proof_path(successful_node)
        prompt = f"""
        You are an expert in the Lean theorem prover.
        The following theorem was successfully proven with the given sequence of tactics.
        
        Theorem: {theorem}
        Sequence of Tactics: {tactics}
        
        Please provide a one-sentence, high-level summary of the proof strategy.
        """
        response = self.model.generate_content(prompt)
        return response.text.strip()

    def _find_solved_node(self, node):
        if node.is_solved:
            return node
        for child in node.children:
            solved = self._find_solved_node(child)
            if solved:
                return solved
        return None
