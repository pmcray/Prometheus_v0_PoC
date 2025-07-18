
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
            return {"benchmarks": {}, "experiments": {}}

    def _save_log(self):
        """
        Saves the performance log to the file.
        """
        with open(self.log_file, 'w') as f:
            json.dump(self.log, f, indent=4)

    def log_experiment(self, experiment_name, success, steps):
        """
        Logs the result of an experimental run.
        """
        if "experiments" not in self.log:
            self.log["experiments"] = {}
            
        self.log["experiments"][experiment_name] = {
            "success": success,
            "steps": steps
        }
        self._save_log()
        logging.info(f"Logged experiment '{experiment_name}': success={success}, steps={steps}")

    def get_last_experiment_steps(self):
        """
        Returns the number of steps from the most recent experiment.
        """
        if not self.log["experiments"]:
            return 999 # Return a high number if no experiments have been run
        
        # Get the last experiment in the log
        last_experiment = list(self.log["experiments"].values())[-1]
        return last_experiment["steps"]

    # ... (rest of the class is unchanged)
    def log_benchmark(self, benchmark_name, success, complexity):
        pass
    def get_last_solved_complexity(self):
        pass
