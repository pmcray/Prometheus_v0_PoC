
import json
import logging
import os
import time

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
            return {"proofs": {}, "experiments": {}, "critiques": [], "tool_usage": {}}

    def _save_log(self):
        with open(self.log_file, 'w') as f:
            json.dump(self.log, f, indent=4)

    def log_tool_usage(self, tool_name, execution_time, num_calls):
        """
        Logs the performance of a tool.
        """
        if "tool_usage" not in self.log:
            self.log["tool_usage"] = {}
        
        if tool_name not in self.log["tool_usage"]:
            self.log["tool_usage"][tool_name] = []
            
        self.log["tool_usage"][tool_name].append({
            "timestamp": time.time(),
            "execution_time": execution_time,
            "num_calls": num_calls
        })
        self._save_log()
        logging.info(f"Logged tool usage for '{tool_name}'")

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

    def log_proof_search(self, theorem_name, success, steps, tactics):
        pass
    def get_last_proof_search(self):
        pass
