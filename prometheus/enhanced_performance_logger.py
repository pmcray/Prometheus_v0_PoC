import logging
import json
import time
import os
import uuid
import cProfile
import pstats
import io
from typing import Dict, Any, List, Optional
from datetime import datetime
from .schemas.communication import AgentMessage, MessageType

class EnhancedPerformanceLogger:
    """Enhanced performance logging system with run-based aggregation and profiling"""

    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.metrics = {}
        self.current_run_id = None
        self.run_logs = {}
        self.profiler = None

    def start_run(self, task_description: str = None) -> str:
        """Start a new run with unique ID"""
        self.current_run_id = str(uuid.uuid4())
        self.run_logs[self.current_run_id] = {
            "start_time": datetime.now().isoformat(),
            "task_description": task_description,
            "messages": [],
            "metrics": {},
            "profiling_data": {},
            "status": "running"
        }

        # Create dedicated log file for this run
        run_log_file = os.path.join(self.log_dir, f"run-{self.current_run_id}.jsonl")
        with open(run_log_file, "w") as f:
            f.write(json.dumps({
                "event_type": "run_start",
                "run_id": self.current_run_id,
                "timestamp": self.run_logs[self.current_run_id]["start_time"],
                "task_description": task_description
            }) + "\n")

        logging.info(f"Started new run: {self.current_run_id}")
        return self.current_run_id

    def end_run(self, status: str = "completed", final_result: Any = None):
        """End the current run"""
        if not self.current_run_id:
            return

        self.run_logs[self.current_run_id].update({
            "end_time": datetime.now().isoformat(),
            "status": status,
            "final_result": final_result
        })

        # Write run summary to log file
        run_log_file = os.path.join(self.log_dir, f"run-{self.current_run_id}.jsonl")
        with open(run_log_file, "a") as f:
            f.write(json.dumps({
                "event_type": "run_end",
                "run_id": self.current_run_id,
                "timestamp": self.run_logs[self.current_run_id]["end_time"],
                "status": status,
                "final_result": final_result
            }) + "\n")

        logging.info(f"Ended run {self.current_run_id} with status: {status}")
        self.current_run_id = None

    def log_message(self, message: AgentMessage):
        """Log an inter-agent message"""
        if not self.current_run_id:
            self.start_run("Auto-started run")

        self.run_logs[self.current_run_id]["messages"].append(message.dict())

        # Write to run log file
        run_log_file = os.path.join(self.log_dir, f"run-{self.current_run_id}.jsonl")
        with open(run_log_file, "a") as f:
            f.write(json.dumps({
                "event_type": "agent_message",
                "run_id": self.current_run_id,
                "timestamp": message.timestamp,
                "message": message.dict()
            }) + "\n")

    def log_metric(self, metric_name: str, value: Any, metadata: Dict[str, Any] = None):
        """Log a performance metric"""
        timestamp = time.time()
        log_entry = {
            "timestamp": timestamp,
            "metric": metric_name,
            "value": value,
            "metadata": metadata or {},
            "run_id": self.current_run_id
        }

        # Write to JSON log file
        log_file = os.path.join(self.log_dir, f"{metric_name}.jsonl")
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        # Store in memory for quick access
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(log_entry)

        # Store in current run if active
        if self.current_run_id:
            if metric_name not in self.run_logs[self.current_run_id]["metrics"]:
                self.run_logs[self.current_run_id]["metrics"][metric_name] = []
            self.run_logs[self.current_run_id]["metrics"][metric_name].append(log_entry)

        logging.info(f"Logged metric {metric_name}: {value}")

    def start_profiling(self):
        """Start performance profiling"""
        self.profiler = cProfile.Profile()
        self.profiler.enable()
        logging.info("Started performance profiling")

    def stop_profiling(self) -> Dict[str, Any]:
        """Stop performance profiling and return results"""
        if not self.profiler:
            return {}

        self.profiler.disable()

        # Capture profiling results
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions

        profiling_data = {
            "stats_text": s.getvalue(),
            "total_calls": ps.total_calls,
            "total_time": ps.total_tt
        }

        # Store in current run
        if self.current_run_id:
            self.run_logs[self.current_run_id]["profiling_data"] = profiling_data

        logging.info("Stopped performance profiling")
        self.profiler = None
        return profiling_data

    def get_metrics(self, metric_name: str) -> list:
        return self.metrics.get(metric_name, [])

    def get_latest_metric(self, metric_name: str) -> Any:
        metrics = self.get_metrics(metric_name)
        return metrics[-1]["value"] if metrics else None

    def get_run_log(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get complete log for a specific run"""
        return self.run_logs.get(run_id)

    def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent run logs"""
        sorted_runs = sorted(self.run_logs.items(),
                           key=lambda x: x[1]["start_time"],
                           reverse=True)
        return [run_data for run_id, run_data in sorted_runs[:limit]]

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary"""
        return {
            "total_runs": len(self.run_logs),
            "successful_runs": len([r for r in self.run_logs.values() if r["status"] == "completed"]),
            "failed_runs": len([r for r in self.run_logs.values() if r["status"] == "failed"]),
            "average_metrics": self._calculate_average_metrics(),
            "recent_performance": self._calculate_recent_performance()
        }

    def _calculate_average_metrics(self) -> Dict[str, float]:
        """Calculate average values for key metrics"""
        averages = {}
        for metric_name, entries in self.metrics.items():
            if entries and isinstance(entries[0]["value"], (int, float)):
                averages[metric_name] = sum(e["value"] for e in entries) / len(entries)
        return averages

    def _calculate_recent_performance(self, last_n_runs: int = 5) -> Dict[str, Any]:
        """Calculate performance trends from recent runs"""
        recent_runs = self.get_recent_runs(last_n_runs)
        if not recent_runs:
            return {}

        return {
            "recent_success_rate": len([r for r in recent_runs if r["status"] == "completed"]) / len(recent_runs),
            "recent_run_count": len(recent_runs),
            "latest_run_status": recent_runs[0]["status"] if recent_runs else None
        }

class DualModeProfiler:
    """Dual-mode profiling harness for system and application analysis"""

    def __init__(self, performance_logger: EnhancedPerformanceLogger):
        self.logger = performance_logger

    def run_system_performance_mode(self, func, *args, **kwargs):
        """Run in system performance mode (no profiling overhead)"""
        start_time = time.perf_counter()

        try:
            result = func(*args, **kwargs)
            success = True
        except Exception as e:
            result = str(e)
            success = False

        end_time = time.perf_counter()
        execution_time = (end_time - start_time) * 1000  # Convert to ms

        self.logger.log_metric("system_execution_time_ms", execution_time, {
            "mode": "system_performance",
            "function": func.__name__ if hasattr(func, '__name__') else str(func),
            "success": success
        })

        return result, execution_time

    def run_application_profile_mode(self, func, *args, **kwargs):
        """Run in application profile mode (with detailed profiling)"""
        self.logger.start_profiling()
        start_time = time.perf_counter()

        try:
            result = func(*args, **kwargs)
            success = True
        except Exception as e:
            result = str(e)
            success = False

        end_time = time.perf_counter()
        execution_time = (end_time - start_time) * 1000

        profiling_data = self.logger.stop_profiling()

        self.logger.log_metric("application_execution_time_ms", execution_time, {
            "mode": "application_profile",
            "function": func.__name__ if hasattr(func, '__name__') else str(func),
            "success": success,
            "profiling_stats": profiling_data
        })

        return result, execution_time, profiling_data