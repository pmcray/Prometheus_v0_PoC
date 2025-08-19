import logging
import importlib
import sys
import os

# --- Configure logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Agent and Utility Imports ---
from prometheus.corrector import CorrectorAgent

# --- The "Smart" Patch ---
# This is the code that the SMM would "generate" to improve the CoderAgent.
# It knows how to properly refactor the inefficient sort.
SMART_CODER_AGENT_CODE = """
import logging

class CoderAgent:
    \"\"\"
    The improved CoderAgent (v2) after self-modification.
    This version knows how to refactor the inefficient sorting algorithm.
    \"\"\"
    def __init__(self, **kwargs):
        logging.info("Smart CoderAgent (v2) instantiated.")
        pass

    def refactor_code(self, original_code: str) -> str:
        \"\"\"
        This is the "smart" implementation. It replaces the inefficient
        bubble sort with Python's highly efficient built-in sort.
        \"\"\"
        logging.info("Smart CoderAgent (v2) is refactoring the code.")

        # A simple but effective refactoring strategy for this specific problem
        if "def inefficient_sort(data):" in original_code:
            refactored_code = original_code.replace(
                "n = len(data)\\n    for i in range(n):\\n        for j in range(0, n-i-1):\\n            if data[j] > data[j+1]:\\n                data[j], data[j+1] = data[j+1], data[j]","    data.sort()"
            )
            logging.info("Successfully refactored inefficient_sort.")
            return refactored_code

        logging.warning("Smart CoderAgent (v2) did not find the specific code to refactor.")
        return original_code
"""

def get_coder_agent_instance():
    """Dynamically imports and returns an instance of the CoderAgent."""
    coder_module_name = 'prometheus.coder'

    # Invalidate caches to ensure the latest version is loaded
    importlib.invalidate_caches()

    # Reload the module if it's already in memory
    if coder_module_name in sys.modules:
        coder_module = importlib.reload(sys.modules[coder_module_name])
    else:
        coder_module = importlib.import_module(coder_module_name)

    CoderAgent = getattr(coder_module, 'CoderAgent')
    return CoderAgent()

def main():
    logging.info("--- Starting v0.40 Self-Modification Verification Test ---")

    # 1. Read the inefficient code from the toy problem
    try:
        with open('toy_problem/inefficient_sort.py', 'r') as f:
            original_code = f.read()
        logging.info("Successfully read 'inefficient_sort.py'.")
    except FileNotFoundError:
        logging.error("Test setup failed: 'toy_problem/inefficient_sort.py' not found.")
        sys.exit(1)

    # 2. First Attempt: Use the "dumb" CoderAgent
    logging.info("\n--- STEP 1: Initial attempt with Dumb CoderAgent (v1) ---")
    dumb_coder = get_coder_agent_instance()
    refactored_code_v1 = dumb_coder.refactor_code(original_code)

    # Verification for Step 1
    if refactored_code_v1 == original_code:
        logging.info("✅ SUCCESS: Dumb CoderAgent (v1) failed to refactor, as expected.")
    else:
        logging.error("❌ FAILURE: Dumb CoderAgent (v1) modified the code unexpectedly.")
        sys.exit(1)

    # 3. Self-Modification Step
    logging.info("\n--- STEP 2: Simulating Self-Modification (SMM + IEE) ---")

    # SMM "generates" the patch and applies it
    try:
        with open('prometheus/coder.py', 'w') as f:
            f.write(SMART_CODER_AGENT_CODE)
        logging.info("SMM simulation: Successfully applied the 'smart' patch to coder.py.")
    except IOError as e:
        logging.error(f"SMM simulation failed: Could not write to coder.py. {e}")
        sys.exit(1)

    # IEE "verifies" the patch, then CorrectorAgent triggers the reload
    logging.info("IEE simulation: Patch is considered verified.")
    corrector = CorrectorAgent()
    reload_success = corrector.trigger_self_modification('prometheus.coder', patch_is_verified=True)

    # Verification for Step 2
    if reload_success:
        logging.info("✅ SUCCESS: CorrectorAgent successfully triggered the module reload.")
    else:
        logging.error("❌ FAILURE: CorrectorAgent failed to trigger the module reload.")
        sys.exit(1)

    # 4. Second Attempt: Use the "smart" CoderAgent
    logging.info("\n--- STEP 3: Second attempt with Smart CoderAgent (v2) ---")
    smart_coder = get_coder_agent_instance()
    refactored_code_v2 = smart_coder.refactor_code(original_code)

    # Verification for Step 3
    if refactored_code_v2 != original_code and "data.sort()" in refactored_code_v2:
        logging.info("✅ SUCCESS: Smart CoderAgent (v2) successfully refactored the code.")
        logging.info(f"Final refactored code:\n{refactored_code_v2}")
    else:
        logging.error("❌ FAILURE: Smart CoderAgent (v2) did not refactor the code as expected.")
        sys.exit(1)

    logging.info("\n--- Verification Test Passed! ---")

if __name__ == "__main__":
    # Restore the original "dumb" coder agent after the test runs
    try:
        main()
    finally:
        DUMB_CODER_AGENT_CODE = """
import logging

class CoderAgent:
    \"\"\"
    A simplified CoderAgent for the v0.40 verification test.
    This version is deliberately "dumb" and needs to be improved via self-modification.
    \"\"\"
    def __init__(self, **kwargs):
        # The __init__ is simplified as the tools are not needed for this test.
        logging.info("Dumb CoderAgent (v1) instantiated.")
        pass

    def refactor_code(self, original_code: str) -> str:
        \"\"\"
        This is the "dumb" implementation. It fails to refactor the code
        and just returns the original code.
        \"\"\"
        logging.warning("Dumb CoderAgent (v1) is attempting to refactor. It will fail.")
        # It doesn't even try, it just returns the original.
        return original_code
"""
        with open('prometheus/coder.py', 'w') as f:
            f.write(DUMB_CODER_AGENT_CODE)
        logging.info("\n--- Cleanup: Restored original 'dumb' CoderAgent. ---")
