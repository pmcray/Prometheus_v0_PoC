
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

    def log_benchmark(self, benchmark_name, success, complexity, solution_code=None):
        """
        Logs the result of a benchmark run.
        If successful, the solution code can be provided.
        """
        log_entry = {
            "success": success,
            "complexity": complexity
        }
        if success and solution_code:
            log_entry["solution_code"] = solution_code

        self.log["benchmarks"][benchmark_name] = log_entry
        self._save_log()
        logging.info(f"Logged benchmark '{benchmark_name}': success={success}, complexity={complexity}")

    def get_last_solved_complexity(self):
        """
        Returns the complexity of the most recently solved benchmark.
        """
        solved_benchmarks = [
            b for b in self.log["benchmarks"].values() if b.get("success")
        ]
        if not solved_benchmarks:
            return 0
        
        # For simplicity, we'll just return the max complexity of any solved benchmark
        return max(b.get("complexity", 0) for b in solved_benchmarks)

    def get_last_solved_benchmark(self):
        """
        Returns the log entry for the solved benchmark with the highest complexity.
        """
        solved_benchmarks = [
            b for b in self.log["benchmarks"].values() if b.get("success") and "solution_code" in b
        ]
        if not solved_benchmarks:
            return None

        # Return the benchmark with the highest complexity
        return max(solved_benchmarks, key=lambda b: b.get("complexity", 0))
