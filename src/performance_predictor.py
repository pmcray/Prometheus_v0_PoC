import logging

class PerformancePredictorAgent:
    def __init__(self):
        logging.info("PerformancePredictorAgent initialized.")

    def predict_performance(self, code_snippet: str) -> float:
        """
        Predicts the performance of a code snippet based on simple heuristics.
        Returns a score where lower is better.
        """
        score = 100.0  # Base score

        # Penalize for common inefficiencies
        if "for loop" in code_snippet:
            score += 50.0
            logging.info("Predictor: Penalizing for 'for' loop.")

        if "factorial(n-1)" in code_snippet: # Simple check for recursion
            score += 30.0
            logging.info("Predictor: Penalizing for recursion.")

        # Reward for common optimizations
        if "sorted(" in code_snippet or ".sort(" in code_snippet:
            score -= 20.0
            logging.info("Predictor: Rewarding for sorting function.")

        logging.info(f"Predicted performance score for code snippet: {score}")
        return score
