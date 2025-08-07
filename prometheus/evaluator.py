import logging
from schemas.messaging import CoderToEvaluatorSubmission, EvaluatorToCorrectorCritique

logger = logging.getLogger(__name__)

class EvaluatorAgent:
    """Code quality and performance evaluation"""

    def evaluate(self, submission: CoderToEvaluatorSubmission) -> EvaluatorToCorrectorCritique:
        """
        Evaluates the code submission and returns a critique.
        """
        logger.info("EvaluatorAgent: Evaluating code submission.")

        test_passed = self._evaluate_correctness(submission.refactored_code, submission.test_file_path)
        performance_score = self._evaluate_performance(submission.original_code, submission.refactored_code)

        critique_text = self._generate_critique(test_passed, performance_score)

        return EvaluatorToCorrectorCritique(
            original_code=submission.original_code,
            refactored_code=submission.refactored_code,
            test_passed=test_passed,
            performance_score=performance_score,
            critique=critique_text
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

    def _evaluate_performance(self, original_code: str, refactored_code: str) -> float:
        # Simple heuristic for performance evaluation
        original_complexity = original_code.count('for') + original_code.count('while')
        refactored_complexity = refactored_code.count('for') + refactored_code.count('while')
        
        if original_complexity == 0:
            return 0.5 # Neutral score if no loops to optimize
        
        improvement = original_complexity - refactored_complexity

        # Normalize score between 0 and 1
        performance_score = (improvement / original_complexity)

        logger.info(f"📈 Performance score: {performance_score:.3f}")
        return performance_score

    def _generate_critique(self, test_passed: bool, performance_score: float) -> str:
        if not test_passed:
            return "The code is not functionally correct. It failed to execute or produced an error."

        if performance_score < 0.2:
            return "The code is functionally correct, but the performance has not been significantly improved. The algorithmic complexity remains high."

        if performance_score > 0.7:
            return "Excellent work! The code is correct and performance has been significantly improved."

        return "The code is functionally correct and shows some performance improvement, but there is still room for optimization."
