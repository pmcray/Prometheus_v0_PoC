
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
            return {"actions": []}

    def _save_log(self):
        with open(self.log_file, 'w') as f:
            json.dump(self.log, f, indent=4)

    def log_action(self, agent_name: str, action: str, cost: int, success: bool):
        """
        Logs an agent's action, its cost, and whether it was successful.
        """
        if "actions" not in self.log:
            self.log["actions"] = []
            
        self.log["actions"].append({
            "timestamp": time.time(),
            "agent": agent_name,
            "action": action,
            "cost": cost,
            "success": success
        })
        self._save_log()
        logging.info(f"Logged action for '{agent_name}': {action} (cost: {cost}, success: {success})")
