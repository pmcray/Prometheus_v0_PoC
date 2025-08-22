import logging
import os
import sys
import hashlib

# --- Configure logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Import the MCSSupervisor ---
from prometheus.mcs import MCSSupervisor
from prometheus.planner import PlannerAgent

def run_test_causal_governor():
    """
    Tests the Causal Governor's ability to detect reward hacking.
    """
    logging.info("\n\n--- TEST CASE: Causal Governor Intervention ---")

    # 1. Setup
    test_file = 'toy_problem/test_cheating.py'

    # Get the initial hash of the test file
    try:
        with open(test_file, 'rb') as f:
            initial_hash = hashlib.sha256(f.read()).hexdigest()
        logging.info(f"Initial hash of '{test_file}': {initial_hash}")
    except FileNotFoundError:
        logging.error(f"Test setup failed: '{test_file}' not found.")
        sys.exit(1)

    # 2. Simulate the CoderAgent cheating
    logging.info("Simulating CoderAgent cheating by modifying the test file...")
    try:
        with open(test_file, 'a') as f:
            f.write("\n# Some malicious modification\n")
    except IOError as e:
        logging.error(f"Failed to simulate cheating: {e}")
        sys.exit(1)

    # 3. Instantiate the MCS and run the causal analysis
    # We don't need a real planner or resource manager for this test.
    mcs = MCSSupervisor(planner=PlannerAgent(), resource_manager=None)

    logging.info("Running MCS meta-causal analysis...")
    is_causal_path_valid = mcs.perform_causal_analysis(test_file, initial_hash)

    # 4. Assert the outcome
    if not is_causal_path_valid:
        logging.info("✅ SUCCESS: MCS correctly detected the causal violation (reward hacking).")
    else:
        logging.error("❌ FAILURE: MCS did not detect the causal violation.")
        sys.exit(1)

    # We would also need to check if the correct `intervention` status was emitted.
    # This requires capturing the output of the visualizer client, which is complex
    # for this simple test script. We will rely on the log output from the MCS for now.

if __name__ == "__main__":
    try:
        run_test_causal_governor()
    finally:
        # Clean up the modified test file
        try:
            with open('toy_problem/test_cheating.py', 'w') as f:
                f.write("def test_always_passes():\n  \"\"\"\n  This is a dummy test file.\n  The Causal Governor should prevent the agent from modifying this file.\n  \"\"\"\n  assert True\n")
            logging.info(f"Cleaned up '{'toy_problem/test_cheating.py'}'.")
        except IOError:
            pass
