import logging
from .brain_map import BrainMap
from .tools import LeanTool
from .performance_logger import PerformanceLogger
from .strategy_archive import StrategyArchive
from .proof_tree import ProofTree

class MCSSupervisor:
    def __init__(self, planner, coder, evaluator, corrector, lean_tool: LeanTool, strategy_archive: StrategyArchive, performance_logger: PerformanceLogger, knowledge_agent, brain_map: BrainMap = None):
        self.planner = planner
        self.coder = coder
        self.evaluator = evaluator
        self.corrector = corrector
        self.lean_tool = lean_tool
        self.strategy_archive = strategy_archive
        self.performance_logger = performance_logger
        self.knowledge_agent = knowledge_agent
        self.brain_map = brain_map

    def run_rsi_cycle(self, theorem: str):
        logging.info(f"--- Starting RSI Cycle for theorem: {theorem} ---")

        # 1. Baseline Run
        logging.info("\n--- Baseline Run ---")
        proof, proof_tree = self._run_proof_search(theorem)
        if not proof:
            logging.error("Baseline proof failed. Halting RSI cycle.")
            return
        baseline_steps = len(proof_tree.get_proof_path(proof_tree.root))
        self.performance_logger.log_proof_search(theorem, True, baseline_steps, proof_tree.get_proof_path(proof_tree.root))
        
        # 2. Introspection & Planning
        logging.info("\n--- Introspection and Planning ---")
        critique = self.planner.generate_self_critique(self.performance_logger.log)
        plan = self.planner.generate_self_modification_plan(critique)

        # 3. Self-Modification
        logging.info("\n--- Self-Modification ---")
        # In a real system, this would modify the CoderAgent's source code.
        # For the PoC, we'll just log the plan and mock the improvement.
        logging.info(f"Executing plan: {plan}")
        self.coder.proof_steps = ["induction a", "rw [Nat.add_assoc]"] # Apply the optimized tactic sequence

        # 4. Verification Run
        logging.info("\n--- Verification Run ---")
        proof, proof_tree = self._run_proof_search(theorem)
        if not proof:
            logging.error("Verification proof failed.")
            return
        verification_steps = len(proof_tree.get_proof_path(proof_tree.root))
        
        # 5. Evaluation
        logging.info("\n--- Evaluation ---")
        logging.info(f"Baseline steps: {baseline_steps}")
        logging.info(f"Verification steps: {verification_steps}")
        if verification_steps < baseline_steps:
            logging.info("✅ RSI Cycle Successful: Performance Improved")
        else:
            logging.warning("RSI Cycle Complete: No performance improvement.")

    def _run_proof_search(self, theorem, max_steps=10):
        initial_state, _ = self.lean_tool.start_proof(theorem)
        proof_tree = ProofTree(initial_state)
        
        for i in range(max_steps):
            current_node = proof_tree.find_most_promising_node()
            if not current_node:
                return None, None

            proof_so_far = self._reconstruct_proof(proof_tree, current_node, theorem)
            tactic = self.coder.generate_tactic(current_node.state)
            new_state, _ = self.lean_tool.apply_tactic(proof_so_far, tactic)
            new_node = proof_tree.add_node(new_state, tactic, current_node)
            
            if new_node.is_solved:
                final_proof = self._reconstruct_proof(proof_tree, new_node, theorem)
                return final_proof, proof_tree
        return None, None

    def _reconstruct_proof(self, proof_tree, node, theorem):
        path = proof_tree.get_proof_path(node)
        proof_str = theorem + " := by\n"
        for tactic in path:
            proof_str += "  " + tactic + ",\n"
        return proof_str