
import json
import logging
import os

class PerformanceLogger:
    def __init__(self, log_file="performance_log.json"):
        self.log_file = log_file
        self.log = self._load_log()
        logging.info(f"PerformanceLogger initialized with log file: {self.log_file}")

    def _load_log(self):
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                return json.load(f)
        else:
            return {"proofs": {}, "experiments": {}, "critiques": []}

    def _save_log(self):
        with open(self.log_file, 'w') as f:
            json.dump(self.log, f, indent=4)

    def log_critique(self, critique: str):
        """
        Logs a self-critique.
        """
        if "critiques" not in self.log:
            self.log["critiques"] = []
        self.log["critiques"].append(critique)
        self._save_log()
        logging.info(f"Logged critique: '{critique}'")

    def get_critique_history(self):
        """
        Returns the history of self-critiques.
        """
        return self.log.get("critiques", [])

    # ... (rest of the class is unchanged)
    def log_proof_search(self, theorem_name, success, steps, tactics):
        pass
    def get_last_proof_search(self):
        pass
