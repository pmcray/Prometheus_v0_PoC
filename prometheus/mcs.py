import logging
import time
import hashlib
from typing import Dict, Any, Set

from immutable_safety_framework import SecurityError
from prometheus.resource_manager import ResourceManager
from prometheus.performance_logger import PerformanceLogger
from prometheus.planner import PlannerAgent
from prometheus.coder import CoderAgent
from prometheus.evaluator import EvaluatorAgent
from prometheus.corrector import CorrectorAgent
from prometheus.causal_attention import CausalAttentionWrapper
from prometheus.memory import MemoryAgent

logger = logging.getLogger(__name__)

class MCSSupervisor:
    """Orchestrates the CRLS cycle and enforces safety constraints."""

    def __init__(self, resource_manager: ResourceManager, performance_logger: PerformanceLogger, api_key: str, run_id: str):
        self.resource_manager = resource_manager
        self.performance_logger = performance_logger
        self.safety_framework = resource_manager.safety_framework
        self.planner = PlannerAgent(resource_manager, api_key)
        self.coder = CoderAgent(api_key)
        self.evaluator = EvaluatorAgent()
        self.corrector = CorrectorAgent(api_key, self.memory)
        self.causal_attention = CausalAttentionWrapper(api_key)
        self.memory = MemoryAgent(collection_name=f"run_{run_id}")
        self.safety_violations = 0
        self.max_safety_violations = self.safety_framework._constraints.MAX_SAFETY_VIOLATIONS
        self.run_id = run_id

    def run_crls_cycle(self, goal: str, original_file_path: str, test_file_path: str, max_iterations: int = 3) -> Dict[str, Any]:
        """Runs the Causal Reinforcement Learning from Self-Correction loop."""
        log_extra = {'extra_data': {'run_id': self.run_id}}
        logger.info(f"🔄 Starting CRLS cycle for goal: {goal}", extra=log_extra)

        # ... (Safety checks remain the same)

        with open(original_file_path, 'r') as f:
            original_code = f.read()

        current_code = original_code
        final_critique = None
        final_code = current_code
        solution_history: Set[str] = set()
        
        for iteration in range(max_iterations):
            logger.info(f"🔄 CRLS Iteration {iteration + 1}/{max_iterations}", extra=log_extra)

            # 1. Planner
            planner_instruction = self.planner.generate_instruction(current_code, goal)
            logger.info("Planner -> Coder", extra={'extra_data': {'run_id': self.run_id, 'message': planner_instruction.dict()}})

            # 2. Coder
            coder_submission = self.coder.refactor_code(planner_instruction, test_file_path)
            logger.info("Coder -> Evaluator", extra={'extra_data': {'run_id': self.run_id, 'message': coder_submission.dict()}})
            final_code = coder_submission.refactored_code

            # Cyclical Failure Detection
            code_hash = hashlib.sha256(final_code.encode()).hexdigest()
            if code_hash in solution_history:
                logger.warning("🚨 CYCLICAL_FAILURE: Detected a repeated code solution. Halting run.", extra=log_extra)
                return {'success': False, 'reason': 'cyclical_failure', 'iterations': iteration + 1}
            solution_history.add(code_hash)

            if "MALICIOUS" in final_code:
                logger.error("🛡️ MCS INTERVENTION: Malicious behavior detected!", extra=log_extra)
                return {'success': False, 'reason': 'malicious_behavior', 'iterations': iteration + 1}

            # 3. Causal Attention
            causal_focus = self.causal_attention.compare_code(current_code, final_code)
            logger.info("Causal Attention -> Evaluator", extra={'extra_data': {'run_id': self.run_id, 'message': causal_focus.dict()}})

            # 4. Evaluator
            evaluator_critique = self.evaluator.evaluate(coder_submission, causal_focus)
            logger.info("Evaluator -> Corrector", extra={'extra_data': {'run_id': self.run_id, 'message': evaluator_critique.dict()}})
            final_critique = evaluator_critique

            # 5. Check for success
            if evaluator_critique.test_passed and evaluator_critique.causal_improvement:
                logger.info(f"✅ CRLS SUCCESS: Target achieved in {iteration + 1} iterations", extra=log_extra)
                result = {
                    'success': True,
                    'iterations': iteration + 1,
                    'final_code': final_code,
                    'reason': evaluator_critique.reason,
                }
                self._add_to_memory(original_code, final_code, final_critique, result)
                return result
            
            # 6. Corrector
            if iteration < max_iterations - 1:
                corrector_instruction = self.corrector.correct(evaluator_critique, current_code, final_code)
                logger.info("Corrector -> Coder", extra={'extra_data': {'run_id': self.run_id, 'message': corrector_instruction.dict()}})

                current_code = original_code
                goal = corrector_instruction.goal

        logger.info(f"🔄 CRLS completed {max_iterations} iterations without success.", extra=log_extra)
        result = {'success': False, 'reason': 'max_iterations_reached', 'iterations': max_iterations}
        if final_critique:
            self._add_to_memory(original_code, final_code, final_critique, result)
        return result

    def _add_to_memory(self, original_code, final_code, critique, result):
        document = f"Critique: {critique.reason}\nFailed Code:\n{final_code}"
        metadata = {
            "success": result["success"],
            "reason": critique.reason,
            "original_code": original_code,
            "final_code": final_code,
            "run_id": self.run_id,
        }
        self.memory.add_to_memory(document, metadata)
