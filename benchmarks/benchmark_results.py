"""
Benchmark Results Analysis and Reporting
"""

import json
import statistics
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PerformanceMetrics:
    """Performance metrics for analysis"""
    success_rate: float
    execution_time_ms: float
    improvement_rate: float
    stability_score: float

class BenchmarkResults:
    """Analysis and reporting for benchmark results"""

    def __init__(self):
        self.results_history: List[Dict[str, Any]] = []

    def add_result(self, result: Dict[str, Any]):
        """Add a new benchmark result to history"""
        self.results_history.append(result)

    def get_performance_trend(self, metric: str = "success_rate") -> Dict[str, Any]:
        """Analyze performance trends over time"""
        if len(self.results_history) < 2:
            return {"error": "Need at least 2 results for trend analysis"}

        values = []
        timestamps = []

        for result in self.results_history:
            if metric in result.get("summary_metrics", {}):
                values.append(result["summary_metrics"][metric])
                timestamps.append(result["execution_timestamp"])

        if len(values) < 2:
            return {"error": f"Insufficient data for metric: {metric}"}

        # Calculate trend
        trend = "improving" if values[-1] > values[0] else "declining"
        if abs(values[-1] - values[0]) < 0.01:  # Less than 1% change
            trend = "stable"

        return {
            "metric": metric,
            "trend": trend,
            "current_value": values[-1],
            "initial_value": values[0],
            "change": values[-1] - values[0],
            "change_percent": ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0,
            "variance": statistics.variance(values) if len(values) > 1 else 0,
            "data_points": len(values)
        }

    def generate_regression_report(self, baseline: Dict[str, Any]) -> Dict[str, Any]:
        """Generate regression analysis report"""
        if not self.results_history:
            return {"error": "No results available"}

        latest_result = self.results_history[-1]
        current_metrics = latest_result["summary_metrics"]
        baseline_metrics = baseline["aggregated_metrics"]

        regression_items = []

        # Check success rate regression
        current_rate = current_metrics["success_rate"]
        baseline_rate = baseline_metrics["mean_success_rate"]
        rate_threshold = baseline_metrics["mean_success_rate"] - (2 * baseline_metrics["std_success_rate"])

        if current_rate < rate_threshold:
            regression_items.append({
                "metric": "success_rate",
                "severity": "high" if current_rate < baseline_rate * 0.9 else "medium",
                "current": current_rate,
                "baseline": baseline_rate,
                "threshold": rate_threshold
            })

        # Check execution time regression
        current_time = current_metrics["average_execution_time_ms"]
        baseline_time = baseline_metrics["mean_execution_time_ms"]
        time_threshold = baseline_metrics["mean_execution_time_ms"] + (2 * baseline_metrics["std_execution_time_ms"])

        if current_time > time_threshold:
            regression_items.append({
                "metric": "execution_time",
                "severity": "medium" if current_time < baseline_time * 1.5 else "high",
                "current": current_time,
                "baseline": baseline_time,
                "threshold": time_threshold
            })

        return {
            "regression_detected": len(regression_items) > 0,
            "regression_items": regression_items,
            "overall_assessment": "regression" if regression_items else "acceptable",
            "comparison_timestamp": datetime.now().isoformat()
        }

    def export_summary(self, filepath: str):
        """Export comprehensive summary to file"""
        summary = {
            "analysis_timestamp": datetime.now().isoformat(),
            "total_runs": len(self.results_history),
            "performance_trends": {
                "success_rate": self.get_performance_trend("success_rate"),
                "execution_time": self.get_performance_trend("average_execution_time_ms")
            },
            "results_history": self.results_history
        }

        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        print(f"📊 Summary exported to {filepath}")