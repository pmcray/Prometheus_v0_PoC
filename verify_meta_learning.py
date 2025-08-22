import logging
import os
import sys
import importlib

# --- Configure logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Import the main orchestrator ---
from main import main as run_orchestrator

# --- Helper functions to control agent states ---

DUMB_CODER_AGENT_CODE = """
import logging
from prometheus.visualizer_client import emit_status
class CoderAgent:
    def __init__(self, **kwargs):
        logging.info("Dumb CoderAgent (v1) instantiated.")
    def refactor_code(self, original_code: str) -> str:
        logging.warning("Dumb CoderAgent (v1) is attempting to refactor. It will fail.")
        return original_code
"""

DUMB_CORRECTOR_AGENT_CODE = """
import logging
from prometheus.visualizer_client import emit_status
class CorrectorAgent:
    def correct(self, original_code, failed_code, critique):
        logging.warning("Dumb CorrectorAgent is attempting to correct. It will be ineffective.")
        # Returns the same prompt, causing a loop
        return f"The previous attempt to refactor the code failed. Please try again."
    def trigger_self_modification(self, module_name: str, patch_is_verified: bool):
        from prometheus.reloader import reload_agent_module
        return reload_agent_module(module_name)
"""

SMART_CORRECTOR_AGENT_CODE = """
import logging
from prometheus.visualizer_client import emit_status
class CorrectorAgent:
    def correct(self, original_code, failed_code, critique):
        logging.info("Smart CorrectorAgent is creating a better prompt.")
        # A slightly more helpful prompt
        return f"The code failed. Critique: {critique}. Please focus on improving time complexity."
    def trigger_self_modification(self, module_name: str, patch_is_verified: bool):
        from prometheus.reloader import reload_agent_module
        return reload_agent_module(module_name)
"""

def setup_agent(agent_name: str, version: str):
    """Sets an agent to a specific version ('dumb' or 'smart')."""
    if agent_name == 'coder':
        code = DUMB_CODER_AGENT_CODE
    elif agent_name == 'corrector':
        code = DUMB_CORRECTOR_AGENT_CODE if version == 'dumb' else SMART_CORRECTOR_AGENT_CODE
    else:
        raise ValueError("Unknown agent name")

    file_path = f'prometheus/{agent_name}.py'
    try:
        with open(file_path, 'w') as f:
            f.write(code)
        logging.info(f"Set {agent_name.capitalize()}Agent to '{version}' version.")
    except IOError as e:
        logging.error(f"Failed to set up {agent_name.capitalize()}Agent: {e}")
        sys.exit(1)

def run_test_meta_learning():
    """
    Tests the meta-learning capability of the system.
    """
    logging.info("\n\n--- TEST CASE: Meta-Learning Cycle ---")

    # 1. Start with "dumb" Coder and "dumb" Corrector
    setup_agent('coder', 'dumb')
    setup_agent('corrector', 'dumb')

    # 2. We need to patch the orchestrator's SMM/IEE simulation to provide
    #    the "smart" corrector patch when requested.

    original_main = None
    try:
        # This is a bit of a hack. We're modifying the main module's logic
        # to simulate the SMM and IEE for the meta-learning case.

        # In a real scenario, the orchestrator would call the SMM, which would
        # generate a patch file. Then it would call the IEE, which would run
        # the benchmark. Here, we just patch the `evaluate_meta_patch` call
        # to return True, and we patch `trigger_self_modification` to
        # set up the smart corrector.

        from prometheus.corrector import CorrectorAgent
        from prometheus.evaluator import EvaluatorAgent

        def patched_trigger_meta(self, module_name: str, patch_is_verified: bool):
            if module_name == 'prometheus.corrector':
                logging.info("Patched meta_trigger: Setting up SMART CorrectorAgent.")
                setup_agent('corrector', 'smart')
            from prometheus.reloader import reload_agent_module
            return reload_agent_module(module_name)

        original_trigger = CorrectorAgent.trigger_self_modification
        CorrectorAgent.trigger_self_modification = patched_trigger_meta

        # The orchestrator will call this, and we need it to return True
        # for the meta-learning path to proceed.
        original_eval = EvaluatorAgent.evaluate_meta_patch
        EvaluatorAgent.evaluate_meta_patch = lambda self, path: True

        # 3. Run the main orchestrator
        # We expect it to fail the CRLS loop, then trigger meta-learning,
        # and then... well, it will still fail the task because the CoderAgent
        # is still dumb. The goal of this test is to verify that the
        # meta-learning path is taken.
        logging.info("Running orchestrator. Expecting meta-learning path to be triggered.")
        run_orchestrator()

        # To verify, we would check the logs for the message "Targeting CorrectorAgent for self-modification."
        # For now, we will rely on manual log inspection.

    finally:
        # Clean up patches
        if original_trigger:
            CorrectorAgent.trigger_self_modification = original_trigger
        if original_eval:
            EvaluatorAgent.evaluate_meta_patch = original_eval
        logging.info("Cleaned up monkey-patches.")


if __name__ == "__main__":
    try:
        run_test_meta_learning()
    finally:
        # Restore agents to their default "dumb" state
        setup_agent('coder', 'dumb')
        setup_agent('corrector', 'dumb')
        logging.info("\n--- Test suite finished. Restored default agent states. ---")
