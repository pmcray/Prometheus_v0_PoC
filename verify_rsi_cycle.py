import logging
import os
import sys
import importlib

# --- Configure logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Import the main orchestrator ---
# We will call the main function directly to run the test
from main import main as run_orchestrator

# --- Helper functions to control the CoderAgent's state ---

DUMB_CODER_AGENT_CODE = """
import logging
from prometheus.visualizer_client import emit_status

class CoderAgent:
    def __init__(self, **kwargs):
        logging.info("Dumb CoderAgent (v1) instantiated.")
        emit_status("Coder", "idle")
    def refactor_code(self, original_code: str) -> str:
        emit_status("Coder", "thinking", {"task": "Refactoring code", "code": original_code})
        logging.warning("Dumb CoderAgent (v1) is attempting to refactor. It will fail.")
        emit_status("Coder", "failure", {"reason": "Dumb agent, did not refactor."})
        return original_code
"""

SMART_CODER_AGENT_CODE = """
import logging
from prometheus.visualizer_client import emit_status

class CoderAgent:
    def __init__(self, **kwargs):
        logging.info("Smart CoderAgent (v2) instantiated.")
        emit_status("Coder", "idle")
    def refactor_code(self, original_code: str) -> str:
        emit_status("Coder", "thinking", {"task": "Refactoring code", "code": original_code})
        logging.info("Smart CoderAgent (v2) is refactoring the code.")
        if "def inefficient_sort(data):" in original_code:
            refactored_code = original_code.replace(
                "n = len(data)\\n    for i in range(n):\\n        for j in range(0, n-i-1):\\n            if data[j] > data[j+1]:\\n                data[j], data[j+1] = data[j+1], data[j]","    data.sort()"
            )
            logging.info("Successfully refactored inefficient_sort.")
            emit_status("Coder", "success", {"reason": "Successfully refactored."})
            return refactored_code
        logging.warning("Smart CoderAgent (v2) did not find the specific code to refactor.")
        return original_code
"""

def setup_coder_agent(version: str):
    """Sets the CoderAgent to a specific version ('dumb' or 'smart')."""
    code = DUMB_CODER_AGENT_CODE if version == 'dumb' else SMART_CODER_AGENT_CODE
    try:
        with open('prometheus/coder.py', 'w') as f:
            f.write(code)
        logging.info(f"Set CoderAgent to '{version}' version.")
    except IOError as e:
        logging.error(f"Failed to set up CoderAgent: {e}")
        sys.exit(1)

def run_test_successful_rsi():
    """
    Tests the successful end-to-end RSI cycle.
    """
    logging.info("\n\n--- TEST CASE 1: Successful RSI Cycle ---")

    # 1. Start with the "dumb" CoderAgent
    setup_coder_agent('dumb')

    # 2. In this test, we need to simulate the SMM providing a "smart" patch
    #    when self-modification is triggered. We can do this by patching the
    #    `trigger_self_modification` method of the CorrectorAgent to write
    #    the smart code before reloading.

    original_trigger = None
    original_main = None

    try:
        from prometheus.corrector import CorrectorAgent

        def patched_trigger(self, module_name: str, patch_is_verified: bool):
            logging.info("Patched trigger_self_modification: Setting up SMART CoderAgent.")
            setup_coder_agent('smart')
            # Now call the original reload logic
            from prometheus.reloader import reload_agent_module
            return reload_agent_module(module_name)

        # Monkey-patch the method
        original_trigger = CorrectorAgent.trigger_self_modification
        CorrectorAgent.trigger_self_modification = patched_trigger

        # 3. Run the main orchestrator
        # We expect it to fail initially, then self-modify, then succeed.
        logging.info("Running orchestrator. Expecting initial failure, then success after RSI.")

        # To verify success, we need to check the final log output.
        # This is a bit tricky, so for now we'll just run it and observe the logs.
        run_orchestrator()

    finally:
        # Clean up the patch
        if original_trigger:
            from prometheus.corrector import CorrectorAgent
            CorrectorAgent.trigger_self_modification = original_trigger
        logging.info("Cleaned up monkey-patch.")


def run_test_mcs_intervention():
    """
    Tests the MCS intervention when the RSI loop is unstable.
    """
    logging.info("\n\n--- TEST CASE 2: MCS Intervention ---")

    # In this test, the SMM will always provide a "bad" patch (the dumb agent code).
    # This will cause the agent to "flail" and the MCS should intervene.

    # This test is more complex to set up and will be implemented in a future iteration.
    logging.warning("MCS Intervention test is not yet implemented.")
    pass


if __name__ == "__main__":
    try:
        run_test_successful_rsi()
        run_test_mcs_intervention()
    finally:
        # Restore the CoderAgent to its default "dumb" state after all tests
        setup_coder_agent('dumb')
        logging.info("\n--- Test suite finished. Restored default 'dumb' CoderAgent. ---")
