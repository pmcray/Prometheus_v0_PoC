import logging
import sys
import os
from src.system_state import SystemState

class MCSSupervisor:
    def __init__(self, planner, coder, evaluator, corrector):
        self.planner = planner
        self.coder = coder
        self.evaluator = evaluator
        self.corrector = corrector

    def run_self_modification(self, max_retries=3):
        logging.info("MCS Supervisor: Starting self-modification run.")

        system_state = SystemState()
        
        target_file, instruction = self.planner.plan(system_state)
        
        for i in range(max_retries):
            logging.info(f"--- Self-Modification Iteration {i+1} ---")
            
            new_code, original_code = self.coder.code(target_file, instruction)
            
            # MCS Check
            if "test" in new_code.lower() and "assert" in new_code.lower():
                logging.critical("MCS SAFETY VIOLATION: Agent attempted to modify a test file during self-modification. Halting.")
                logging.critical(f"Malicious code:\n{new_code}")
                return

            logging.info(f"--- Generated Code for {target_file} ---\n{new_code}\n----------------------")

            original_file_content = ""
            with open(target_file, 'r') as f:
                original_file_content = f.read()
            
            with open(target_file, 'w') as f:
                f.write(new_code)
                
            import subprocess
            # Add the project root and the toy_problem directory to the PYTHONPATH
            env = os.environ.copy()
            env["PYTHONPATH"] = f".{os.pathsep}toy_problem"
            result = subprocess.run([sys.executable, "-m", "pytest", "tests/", "toy_problem/"], capture_output=True, text=True, env=env)
            
            # Restore the original file content
            with open(target_file, 'w') as f:
                f.write(original_file_content)

            if result.returncode == 0:
                logging.info("✅ Self-modification successful and all tests passed!")
                logging.info(f"The following change would be applied to {target_file}:\n{new_code}")
                break
            else:
                logging.warning("❌ Self-modification failed. Tests did not pass.")
                logging.warning(result.stdout)
                logging.warning(result.stderr)
                
                critique = f"The self-modification failed because the tests did not pass.\n{result.stdout}\n{result.stderr}"
                instruction = self.corrector.correct(original_code, new_code, critique)
        else:
            logging.error("❌ Failed to achieve successful self-modification after multiple retries.")