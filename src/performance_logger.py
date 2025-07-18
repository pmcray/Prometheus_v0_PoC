
import json
import logging
import os

class PerformanceLogger:
    def __init__(self, log_file="performance_log.json"):
        self.log_file = log_file
        self.log = self._load_log()
        logging.info(f"PerformanceLogger initialized with log file: {self.log_file}")

    def _load_log(self):
        """
        Loads the performance log from the file.
        """
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                return json.load(f)
        else:
            return {"benchmarks": {}}

    def _save_log(self):
        """
        Saves the performance log to the file.
        """
        with open(self.log_file, 'w') as f:
            json.dump(self.log, f, indent=4)

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
