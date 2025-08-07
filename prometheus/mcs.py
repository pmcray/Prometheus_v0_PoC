import logging
import time
from typing import Dict, Any

from immutable_safety_framework import SecurityError
from prometheus.resource_manager import ResourceManager
from prometheus.performance_logger import PerformanceLogger
from prometheus.planner import PlannerAgent
from prometheus.coder import CoderAgent
from prometheus.evaluator import EvaluatorAgent
from prometheus.corrector import CorrectorAgent

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
        self.corrector = CorrectorAgent(api_key)
        self.safety_violations = 0
        self.max_safety_violations = self.safety_framework._constraints.MAX_SAFETY_VIOLATIONS
        self.run_id = run_id

    def run_crls_cycle(self, goal: str, original_file_path: str, test_file_path: str, max_iterations: int = 3) -> Dict[str, Any]:
        """Runs the Causal Reinforcement Learning from Self-Correction loop."""
        log_extra = {'extra_data': {'run_id': self.run_id}}
        logger.info(f"🔄 Starting CRLS cycle for goal: {goal}", extra=log_extra)

        try:
            if not self.safety_framework.validate_action(f"crls_cycle_goal: {goal}", {'goal': goal, 'max_iterations': max_iterations, 'files': [original_file_path, test_file_path]}):
                logger.error("🔒 CRLS cycle blocked by immutable safety framework", extra=log_extra)
                return {'success': False, 'reason': 'immutable_safety_violation', 'iterations': 0}
        except SecurityError as e:
            logger.critical(f"🚨 CRITICAL SECURITY ERROR: {e}", extra=log_extra)
            return {'success': False, 'reason': 'critical_security_error', 'iterations': 0, 'error': str(e)}

        if not self.planner.evaluate_safety(goal, goal):
            self.safety_violations += 1
            if self.safety_violations >= self.max_safety_violations:
                logger.error("🚨 SYSTEM HALT: Maximum safety violations exceeded", extra=log_extra)
                return {'success': False, 'reason': 'safety_violation', 'iterations': 0}

        with open(original_file_path, 'r') as f:
            original_code = f.read()

        current_code = original_code
        
        for iteration in range(max_iterations):
            logger.info(f"🔄 CRLS Iteration {iteration + 1}/{max_iterations}", extra=log_extra)

            # 1. Planner
            planner_instruction = self.planner.generate_instruction(current_code, goal)
            logger.info("Planner -> Coder", extra={'extra_data': {'run_id': self.run_id, 'message': planner_instruction.dict()}})

            # 2. Coder
            coder_submission = self.coder.refactor_code(planner_instruction, test_file_path)
            logger.info("Coder -> Evaluator", extra={'extra_data': {'run_id': self.run_id, 'message': coder_submission.dict()}})


            if "MALICIOUS" in coder_submission.refactored_code:
                logger.error("🛡️ MCS INTERVENTION: Malicious behavior detected!", extra=log_extra)
                return {'success': False, 'reason': 'malicious_behavior', 'iterations': iteration + 1}

            # 3. Evaluator
            evaluator_critique = self.evaluator.evaluate(coder_submission)
            logger.info("Evaluator -> Corrector", extra={'extra_data': {'run_id': self.run_id, 'message': evaluator_critique.dict()}})


            # 4. Check for success
            if evaluator_critique.test_passed and evaluator_critique.performance_score > 0.7:
                logger.info(f"✅ CRLS SUCCESS: Target achieved in {iteration + 1} iterations", extra=log_extra)
                return {
                    'success': True,
                    'iterations': iteration + 1,
                    'final_code': evaluator_critique.refactored_code,
                    'performance_score': evaluator_critique.performance_score,
                }
            
            # 5. Corrector
            if iteration < max_iterations -1: # No need to correct on the last iteration
                corrector_instruction = self.corrector.correct(evaluator_critique)
                logger.info("Corrector -> Coder", extra={'extra_data': {'run_id': self.run_id, 'message': corrector_instruction.dict()}})
                current_code = self.coder.refactor_code(corrector_instruction, test_file_path).refactored_code
                goal = corrector_instruction.goal # The goal might be updated by the corrector

        logger.info(f"🔄 CRLS completed {max_iterations} iterations without success.", extra=log_extra)
        return {'success': False, 'reason': 'max_iterations_reached', 'iterations': max_iterations}
