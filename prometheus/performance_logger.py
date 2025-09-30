
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
            return {"actions": [], "benchmarks": {}}

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

    def log_benchmark(self, benchmark_name, success, complexity):
        """
        Logs the result of a benchmark run.
        """
        self.log["benchmarks"][benchmark_name] = {
            "success": success,
            "complexity": complexity
        }
        self._save_log()
        logging.info(f"Logged benchmark '{benchmark_name}': success={success}, complexity={complexity}")

    def get_last_solved_complexity(self):
        """
        Returns the complexity of the most recently solved benchmark.
        """
        solved_benchmarks = [
            b for b in self.log["benchmarks"].values() if b["success"]
        ]
        if not solved_benchmarks:
            return 0

        # For simplicity, we'll just return the max complexity of any solved benchmark
        return max(b["complexity"] for b in solved_benchmarks)
