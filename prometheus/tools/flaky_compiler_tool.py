
import random
import logging

class FlakyCompilerTool:
    def __init__(self, failure_rate=0.5):
        self.failure_rate = failure_rate
        logging.info(f"FlakyCompilerTool initialized with a failure rate of {self.failure_rate}")

    def compile(self, code: str):
        """
        Attempts to compile the code, but has a chance of failing.
        """
        if random.random() < self.failure_rate:
            logging.error("FlakyCompilerTool: Compilation failed!")
            return False
        else:
            logging.info("FlakyCompilerTool: Compilation successful!")
            return True
