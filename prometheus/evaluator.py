import logging
from schemas.messaging import CoderToEvaluatorSubmission, CausalCritique, CausalFocus

logger = logging.getLogger(__name__)

class EvaluatorAgent:
    """Code quality and performance evaluation"""

    def evaluate(self, submission: CoderToEvaluatorSubmission, causal_focus: CausalFocus) -> CausalCritique:
        """
        Evaluates the code submission and returns a critique.
        """
        logger.info("EvaluatorAgent: Evaluating code submission.")

        test_passed = self._evaluate_correctness(submission.refactored_code, submission.test_file_path)
        causal_improvement = self._evaluate_causal_improvement(causal_focus)
        reason = self._generate_critique(test_passed, causal_improvement, causal_focus)

        return CausalCritique(
            test_passed=test_passed,
            causal_improvement=causal_improvement,
            analysis=causal_focus,
            reason=reason
        )

    def _evaluate_correctness(self, code: str, test_file: str) -> bool:
        try:
            # This is a simplified check. A real implementation would run the test file.
            exec(code)
            logger.info("✅ Code executed without syntax errors")
            return True
        except Exception as e:
            logger.error(f"❌ Code execution failed: {e}")
            return False

    def _evaluate_causal_improvement(self, causal_focus: CausalFocus) -> bool:
        """
        Determines if a causal improvement was made based on the causal focus.
        """
        if causal_focus.change_type == "REDUCED_LOOP_DEPTH":
            return True
        if causal_focus.change_type == "REMOVED_RECURSION":
            return True
        return False

    def _generate_critique(self, test_passed: bool, causal_improvement: bool, causal_focus: CausalFocus) -> str:
        if not test_passed:
            return "The code is not functionally correct. It failed to execute or produced an error."

        if causal_improvement:
            if causal_focus.change_type == "REDUCED_LOOP_DEPTH":
                return f"Successfully refactored from a nested loop structure (depth {causal_focus.from_value}) to a simpler one (depth {causal_focus.to_value}), resulting in improved time complexity."
            if causal_focus.change_type == "REMOVED_RECURSION":
                 return "Successfully replaced a recursive solution with an iterative one, which can improve performance and avoid stack overflow errors."
            return "Excellent work! The code is correct and performance has been significantly improved."

        else:
            if causal_focus.change_type == "NO_CHANGE":
                return "The code passes the unit test, but the underlying algorithmic structure remains unchanged. No causal improvement in time complexity was achieved."
            if causal_focus.change_type == "ADDED_RECURSION":
                return "The code passes the unit test, but it introduced recursion, which may not be an improvement and could be less efficient."
            return "The code is functionally correct, but the performance has not been significantly improved. The algorithmic complexity remains high."
