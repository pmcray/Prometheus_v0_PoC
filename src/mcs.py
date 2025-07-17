

import logging

class MCSSupervisor:
    def __init__(self, planner, coder, evaluator, corrector):
        self.planner = planner
        self.coder = coder
        self.evaluator = evaluator
        self.corrector = corrector

    def run(self, goal, original_file_path, test_file_path, max_retries=3):
        logging.info(f"MCS Supervisor: Starting run with goal - {goal}")

        instruction = self.planner.plan(goal)
        logging.info(f"MCS Supervisor: Initial instruction - {instruction}")

        for i in range(max_retries):
            logging.info(f"--- Iteration {i+1} ---")
            
            new_code, original_code = self.coder.code(original_file_path, instruction)
            
            # MCS Check: Ensure the agent is not modifying the test file
            if "test" in new_code.lower() and "assert" in new_code.lower():
                logging.critical("MCS SAFETY VIOLATION: Agent attempted to modify the test file. Halting execution.")
                logging.critical(f"Malicious code:\n{new_code}")
                return

            logging.info(f"--- Generated Code ---\n{new_code}\n----------------------")

            critique, test_output = self.evaluator.evaluate(new_code, original_code, test_file_path, original_file_path)
            logging.info(f"--- Evaluation Result ---\nCritique: {critique}\nTest Output: {test_output}\n--------------------------")

            if critique.test_passed and critique.causal_improvement:
                logging.info("✅ Causal improvement achieved!")
                break
            
            logging.warning("Causal improvement not achieved. Retrying...")
            instruction = self.corrector.correct(original_code, new_code, critique)
            logging.info(f"New instruction for next iteration: {instruction}")

        else:
            logging.error("❌ Failed to achieve causal improvement after multiple retries.")
