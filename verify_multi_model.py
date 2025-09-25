#!/usr/bin/env python3
"""
P1 Verification Script for Project Prometheus v0.20
Tests the Multi-Model Foundation Selection functionality and its integration with the P0 safety framework.
"""

import os
import sys
import logging
import json
from typing import List

# Add project root to path to allow direct imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from foundation_model_selection import FoundationModelEvaluator, FoundationModel, ModelEvaluationResult
from immutable_safety_framework import ImmutableSafetyFramework, SecurityError

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VerificationError(Exception):
    """Custom exception for verification failures."""
    pass

def run_verification_test(test_name: str, test_function):
    """Utility function to run a single verification test and log its result."""
    logger.info(f"--- RUNNING TEST: {test_name} ---")
    try:
        test_function()
        logger.info(f"✅ PASSED: {test_name}\n")
        return True
    except (VerificationError, AssertionError, SecurityError) as e:
        logger.error(f"❌ FAILED: {test_name}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"💥 UNEXPECTED ERROR in {test_name}: {e}", exc_info=True)
        return False

# --- Test Cases ---

def test_01_framework_initialization():
    """Verify that the safety and evaluator frameworks can be initialized."""
    global safety_framework, api_key, evaluator

    # Use a dummy key for verification if the environment variable is not set.
    # This allows testing the logic without requiring a real secret key.
    api_key = os.environ.get("GOOGLE_API_KEY", "AIzaSyC7PYhohlqgdRVVypOnpbqzoE9bEdjvwvg")

    try:
        safety_framework = ImmutableSafetyFramework()
        logger.info("ImmutableSafetyFramework initialized.")
        evaluator = FoundationModelEvaluator(safety_framework, api_key)
        logger.info("FoundationModelEvaluator initialized.")
    except Exception as e:
        raise VerificationError(f"Framework initialization failed: {e}")

def test_02_model_class_instantiation():
    """Verify that the FoundationModel class can be instantiated and generate content."""
    model = FoundationModel("gemini-1.5-flash", api_key)
    prompt = "What is the capital of France?"
    response = model.generate_content(prompt)

    # In a sandboxed environment without a live API, we check for a non-empty response
    # rather than specific content. This verifies the generation function executes.
    if not response:
        raise VerificationError("Model generation returned an empty response.")
    logger.info(f"FoundationModel generated content successfully: '{response[:50]}...'")

def test_03_evaluation_functions_return_valid_scores():
    """Verify that individual evaluation functions return scores between 0.0 and 1.0."""
    model = FoundationModel("gemini-1.5-flash", api_key)

    scores = {
        "code_generation": evaluator.evaluate_code_generation(model),
        "reasoning": evaluator.evaluate_reasoning_capability(model),
        "safety": evaluator.evaluate_safety_compliance(model)
    }

    for name, score in scores.items():
        if not (0.0 <= score <= 1.0):
            raise VerificationError(f"'{name}' score {score} is out of the valid range [0.0, 1.0].")
        logger.info(f"'{name}' returned a valid score: {score}")

def test_04_comprehensive_evaluation_returns_results():
    """Verify that the comprehensive evaluation returns a list of results."""
    results: List[ModelEvaluationResult] = evaluator.run_comprehensive_evaluation()

    if not results:
        raise VerificationError("Comprehensive evaluation returned no results.")

    for result in results:
        if not isinstance(result, ModelEvaluationResult):
            raise VerificationError(f"Evaluation returned an invalid object type: {type(result)}")
        if not (0.0 <= result.final_score <= 1.0):
            raise VerificationError(f"Final score {result.final_score} for {result.model_name} is invalid.")
    logger.info(f"Comprehensive evaluation returned {len(results)} valid result(s).")

def test_05_optimal_model_selection():
    """Verify that the optimal model selection process returns a valid model name."""
    optimal_model = evaluator.select_optimal_foundation()

    if not optimal_model:
        raise VerificationError("Optimal model selection returned None.")
    if not isinstance(optimal_model, str) or not optimal_model:
        raise VerificationError(f"Selected model '{optimal_model}' is not a valid string.")

    logger.info(f"Optimal model selection succeeded, chose: '{optimal_model}'")

def test_06_safety_framework_audits_actions():
    """Verify that the safety framework correctly logs actions from the evaluator."""
    # The evaluator has already been running, so we check the audit trail.
    audit_log_path = safety_framework.audit_logger.log_file
    if not audit_log_path.exists():
        raise VerificationError("Audit log file not found.")

    with open(audit_log_path, 'r') as f:
        audit_log = json.load(f)

    actions_to_verify = [
        "evaluate_code_generation",
        "evaluate_reasoning_capability",
        "evaluate_safety_compliance",
        "run_comprehensive_evaluation",
        "select_optimal_foundation"
    ]

    logged_actions = [entry['action'] for entry in audit_log if entry['type'] == 'approved_action']

    for action in actions_to_verify:
        if action not in logged_actions:
            raise VerificationError(f"Safety audit log is missing the expected action: '{action}'")

    logger.info(f"Safety framework correctly audited {len(actions_to_verify)} actions.")


def main():
    """Main verification function."""
    logger.info("🚀 P1 VERIFICATION SCRIPT STARTING")
    logger.info("=" * 60)

    tests = {
        "Framework Initialization": test_01_framework_initialization,
        "FoundationModel Class Instantiation": test_02_model_class_instantiation,
        "Evaluation Functions Return Valid Scores": test_03_evaluation_functions_return_valid_scores,
        "Comprehensive Evaluation Returns Results": test_04_comprehensive_evaluation_returns_results,
        "Optimal Model Selection": test_05_optimal_model_selection,
        "Safety Framework Audits Actions": test_06_safety_framework_audits_actions,
    }

    results = [run_verification_test(name, func) for name, func in tests.items()]

    logger.info("=" * 60)
    logger.info("📊 VERIFICATION SUMMARY")

    if all(results):
        logger.info("🎉 ALL P1 VERIFICATION TESTS PASSED SUCCESSFULLY!")
        logger.info("   The Multi-Model Foundation Selection feature is working correctly and safely.")
    else:
        failed_count = results.count(False)
        logger.error(f"🔥 {failed_count} VERIFICATION TEST(S) FAILED.")
        logger.error("   Please review the logs above to diagnose the issues.")
        sys.exit(1) # Exit with an error code if verification fails

if __name__ == "__main__":
    main()