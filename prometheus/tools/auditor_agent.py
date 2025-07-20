

import google.generativeai as genai
import logging
import os

class AuditorAgent:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_audit_trail(self, proof_tree, theorem):
        """
        Generates a high-level summary of a proof search.
        """
        logging.info("AuditorAgent: Generating audit trail.")
        
        successful_node = self._find_solved_node(proof_tree.root)
        if not successful_node:
            return "Audit Trail: The proof was not successful."
            
        tactics = proof_tree.get_proof_path(successful_node)
        
        prompt = f"""
        You are an AI auditor. Your task is to provide a high-level, natural-language summary of the following successful proof search.
        
        Theorem: {theorem}
        Successful sequence of tactics: {tactics}
        
        Please provide a one-paragraph summary of the proof strategy.
        """
        response = self.model.generate_content(prompt)
        return f"Audit Trail:\n{response.text.strip()}"

    def _find_solved_node(self, node):
        if node.is_solved:
            return node
        for child in node.children:
            solved = self._find_solved_node(child)
            if solved:
                return solved
        return None

