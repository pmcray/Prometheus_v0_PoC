import logging
import sys
import os
import random
from src.system_state import SystemState
from src.tools import CompilerTool, StaticAnalyzerTool, LeanTool
from src.gene_archive import GeneArchive
from src.proof_tree import ProofTree

class MCSSupervisor:
    def __init__(self, planner, coder, evaluator, corrector, lean_tool: LeanTool):
        self.planner = planner
        self.coder = coder
        self.evaluator = evaluator
        self.corrector = corrector
        self.gene_archive = GeneArchive()
        self.lean_tool = lean_tool

    def run_proof_tree_search(self, theorem, max_steps=20):
        logging.info(f"--- Starting Proof Tree Search for theorem: {theorem} ---")
        
        initial_state, _ = self.lean_tool.start_proof(theorem)
        proof_tree = ProofTree(initial_state)
        critiques = []

        for i in range(max_steps):
            logging.info(f"--- Search Step {i+1} ---")
            
            # 1. Choose a node to expand
            current_node = self.planner.choose_next_step(proof_tree, critiques)
            
            if not current_node:
                logging.warning("No more nodes to expand. Proof search failed.")
                return None

            # 2. Generate a tactic
            proof_so_far = self._reconstruct_proof(proof_tree, current_node)
            tactic = self.coder.generate_tactic(current_node.state)
            logging.info(f"Generated Tactic: {tactic}")

            # 3. Apply the tactic
            new_state, _ = self.lean_tool.apply_tactic(proof_so_far, tactic)
            
            # 4. Add the new node to the tree
            new_node = proof_tree.add_node(new_state, tactic, current_node)
            
            if new_node.is_solved:
                logging.info("✅ Proof complete!")
                final_proof = self._reconstruct_proof(proof_tree, new_node)
                return final_proof
            
            if "error" in new_state.raw_state.lower():
                logging.warning(f"Tactic '{tactic}' resulted in an error state. Generating critique.")
                failed_tactics = proof_tree.get_proof_path(new_node)
                critique = self.evaluator.critique_failed_proof(failed_tactics, new_state.raw_state)
                critiques.append(critique)
                logging.info(f"Generated Critique: {critique}")


        logging.error("❌ Failed to prove the theorem within the step limit.")
        return None

    def _reconstruct_proof(self, proof_tree, node):
        path = proof_tree.get_proof_path(node)
        theorem = "theorem reverse_reverse (l : List Nat) : l.reverse.reverse = l" # Hardcoded for now
        proof_str = theorem + " := by\n"
        for tactic in path:
            proof_str += "  " + tactic + ",\n"
        return proof_str

    # ... (rest of the MCSSupervisor class is unchanged)
    def run_self_modification(self, max_retries=3):
        pass
    def run_evolutionary_cycle(self, initial_code_path, test_file_path, generations=5, population_size=10):
        pass
    def _evaluate_fitness(self, new_code, original_code, test_file_path, original_file_path):
        pass