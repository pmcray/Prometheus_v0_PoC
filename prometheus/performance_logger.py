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
            return {"proofs": {}, "experiments": {}}

    def _save_log(self):
        with open(self.log_file, 'w') as f:
            json.dump(self.log, f, indent=4)

    def log_proof_search(self, theorem_name, success, steps, tactics):
        """
        Logs the result of a proof search run.
        """
        if "proofs" not in self.log:
            self.log["proofs"] = {}
            
        self.log["proofs"][theorem_name] = {
            "success": success,
            "steps": steps,
            "tactics": tactics
        }
        self._save_log()
        logging.info(f"Logged proof search for '{theorem_name}': success={success}, steps={steps}")

    def get_last_proof_search(self):
        """
        Returns the data from the most recent proof search.
        """
        if not self.log["proofs"]:
            return None
        
        last_proof = list(self.log["proofs"].values())[-1]
        return last_proof