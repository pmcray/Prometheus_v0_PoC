"""
Benchmark Runner - Automated execution and reporting for Prometheus-Bench-v0.1
"""

import os
import time
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from .prometheus_bench_v0_1 import PrometheusBenchV01

class BenchmarkRunner:
    """Automated benchmark execution and management"""

    def __init__(self, results_dir: str = "benchmark_results"):
        self.results_dir = results_dir
        self.benchmark_suite = PrometheusBenchV01()

        # Ensure results directory exists
        os.makedirs(results_dir, exist_ok=True)

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def run_full_benchmark(self, agent_instance=None, save_results: bool = True) -> Dict[str, Any]:
        """
        Run the complete benchmark suite with comprehensive reporting

        Args:
            agent_instance: Prometheus agent instance to test
            save_results: Whether to save results to disk

        Returns:
            Complete benchmark results
        """
        self.logger.info("🚀 Starting Full Benchmark Execution")

        start_time = time.time()

        # Execute benchmark suite
        results = self.benchmark_suite.execute_benchmark_suite(agent_instance)

        # Add runner metadata
        results["runner_metadata"] = {
            "runner_version": "1.0",
            "execution_environment": {
                "python_version": f"{os.sys.version}",
                "working_directory": os.getcwd(),
                "timestamp": datetime.now().isoformat()
            },
            "total_runtime_seconds": time.time() - start_time
        }

        if save_results:
            self._save_results(results)

        self._print_summary(results)

        return results

    def establish_system_baseline(self, agent_instance=None, num_runs: int = 5) -> Dict[str, Any]:
        """
        Establish and save system baseline performance

        Args:
            agent_instance: Agent to baseline
            num_runs: Number of baseline runs

        Returns:
            Baseline data
        """
        self.logger.info(f"📊 Establishing System Baseline ({num_runs} runs)")

        baseline = self.benchmark_suite.establish_baseline(agent_instance, num_runs)

        # Save baseline
        baseline_file = os.path.join(self.results_dir, "prometheus_v0_49_baseline.json")
        self.benchmark_suite.save_baseline(baseline_file)

        self.logger.info(f"✅ Baseline established and saved to {baseline_file}")

        return baseline

    def run_regression_test(self, agent_instance=None) -> Dict[str, Any]:
        """
        Run benchmark as regression test against established baseline

        Args:
            agent_instance: Agent to test

        Returns:
            Regression test results
        """
        self.logger.info("🧪 Running Regression Test")

        # Load baseline if exists
        baseline_file = os.path.join(self.results_dir, "prometheus_v0_49_baseline.json")
        if os.path.exists(baseline_file):
            self.benchmark_suite.load_baseline(baseline_file)
        else:
            self.logger.warning("No baseline found - establishing new baseline")
            self.establish_system_baseline(agent_instance)

        # Run current test
        results = self.run_full_benchmark(agent_instance, save_results=True)

        # Analyze regression
        if "baseline_comparison" in results:
            comparison = results["baseline_comparison"]
            if comparison["performance_trend"] == "improved":
                self.logger.info(f"✅ Performance IMPROVED by {comparison['success_rate_delta']:+.1%}")
            else:
                self.logger.warning(f"⚠️ Performance DEGRADED by {comparison['success_rate_delta']:+.1%}")

        return results

    def run_continuous_monitoring(self, agent_instance=None, interval_hours: int = 24) -> None:
        """
        Run continuous performance monitoring

        Args:
            agent_instance: Agent to monitor
            interval_hours: Hours between benchmark runs
        """
        self.logger.info(f"🔄 Starting Continuous Monitoring (every {interval_hours}h)")

        while True:
            try:
                self.run_regression_test(agent_instance)
                time.sleep(interval_hours * 3600)  # Convert hours to seconds

            except KeyboardInterrupt:
                self.logger.info("Continuous monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring cycle: {e}")
                time.sleep(300)  # Wait 5 minutes before retry

    def _save_results(self, results: Dict[str, Any]) -> str:
        """Save benchmark results to timestamped file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_results_{timestamp}.json"
        filepath = os.path.join(self.results_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        self.logger.info(f"💾 Results saved to {filepath}")
        return filepath

    def _print_summary(self, results: Dict[str, Any]) -> None:
        """Print formatted benchmark summary"""
        summary = results["summary_metrics"]

        print("\n" + "="*60)
        print("📊 PROMETHEUS-BENCH-V0.1 RESULTS SUMMARY")
        print("="*60)

        # Overall metrics
        print(f"🎯 Overall Performance:")
        print(f"  Success Rate: {summary['success_rate']:.1%}")
        print(f"  Tasks Completed: {summary['successful_tasks']}/{summary['total_tasks']}")
        print(f"  Average Time: {summary['average_execution_time_ms']:.1f}ms")
        print(f"  Total Runtime: {summary['total_execution_time_ms']:.1f}ms")

        # Category breakdown
        print(f"\n📋 Performance by Category:")
        for category, metrics in summary["categories"].items():
            print(f"  {category.title():>15}: {metrics['success_rate']:.1%} ({metrics['successful_tasks']}/{metrics['total_tasks']})")

        # Baseline comparison
        if "baseline_comparison" in results:
            comparison = results["baseline_comparison"]
            trend_emoji = "📈" if comparison["performance_trend"] == "improved" else "📉"
            print(f"\n{trend_emoji} Baseline Comparison:")
            print(f"  Performance Trend: {comparison['performance_trend'].upper()}")
            print(f"  Success Rate Delta: {comparison['success_rate_delta']:+.1%}")

        # Detailed task results
        print(f"\n📝 Detailed Task Results:")
        for task_id, task_result in results["task_results"].items():
            status = "✅" if task_result["success"] else "❌"
            score = task_result["performance_score"]
            time_ms = task_result["execution_time_ms"]
            print(f"  {status} {task_id}: {score:.2f} score, {time_ms:.1f}ms")

        print("="*60)

    def generate_performance_report(self, days_back: int = 7) -> Dict[str, Any]:
        """
        Generate performance report from recent benchmark runs

        Args:
            days_back: Number of days of history to analyze

        Returns:
            Performance trend report
        """
        self.logger.info(f"📈 Generating Performance Report ({days_back} days)")

        # Find recent result files
        cutoff_time = time.time() - (days_back * 24 * 3600)
        recent_files = []

        for filename in os.listdir(self.results_dir):
            if filename.startswith("benchmark_results_") and filename.endswith(".json"):
                filepath = os.path.join(self.results_dir, filename)
                if os.path.getmtime(filepath) >= cutoff_time:
                    recent_files.append(filepath)

        if not recent_files:
            return {"error": f"No benchmark results found in last {days_back} days"}

        # Analyze trends
        results_data = []
        for filepath in sorted(recent_files):
            with open(filepath, 'r') as f:
                data = json.load(f)
                results_data.append(data)

        # Calculate trends
        success_rates = [r["summary_metrics"]["success_rate"] for r in results_data]
        execution_times = [r["summary_metrics"]["average_execution_time_ms"] for r in results_data]

        report = {
            "report_period_days": days_back,
            "total_runs_analyzed": len(results_data),
            "performance_trends": {
                "success_rate": {
                    "current": success_rates[-1] if success_rates else 0,
                    "trend": "improving" if len(success_rates) > 1 and success_rates[-1] > success_rates[0] else "stable",
                    "variance": max(success_rates) - min(success_rates) if success_rates else 0
                },
                "execution_time": {
                    "current": execution_times[-1] if execution_times else 0,
                    "trend": "improving" if len(execution_times) > 1 and execution_times[-1] < execution_times[0] else "stable",
                    "variance": max(execution_times) - min(execution_times) if execution_times else 0
                }
            },
            "recommendations": self._generate_recommendations(results_data)
        }

        return report

    def _generate_recommendations(self, results_data: List[Dict[str, Any]]) -> List[str]:
        """Generate improvement recommendations based on performance data"""
        recommendations = []

        if not results_data:
            return ["No data available for recommendations"]

        latest_results = results_data[-1]
        categories = latest_results["summary_metrics"]["categories"]

        # Find weakest categories
        weak_categories = [
            cat for cat, metrics in categories.items()
            if metrics["success_rate"] < 0.8
        ]

        if weak_categories:
            recommendations.append(f"Focus improvement efforts on: {', '.join(weak_categories)}")

        # Check for performance degradation
        if len(results_data) > 1:
            current_rate = results_data[-1]["summary_metrics"]["success_rate"]
            previous_rate = results_data[-2]["summary_metrics"]["success_rate"]

            if current_rate < previous_rate * 0.95:  # 5% degradation
                recommendations.append("Performance degradation detected - investigate recent changes")

        # Check execution time trends
        execution_times = [r["summary_metrics"]["average_execution_time_ms"] for r in results_data[-3:]]
        if len(execution_times) >= 3 and all(execution_times[i] > execution_times[i-1] for i in range(1, len(execution_times))):
            recommendations.append("Execution time increasing - consider performance optimization")

        if not recommendations:
            recommendations.append("Performance is stable - continue current approach")

        return recommendations

    def get_benchmark_integrity_hash(self) -> str:
        """Get hash for benchmark integrity verification"""
        return self.benchmark_suite.get_benchmark_hash()

    def verify_benchmark_integrity(self, expected_hash: str) -> bool:
        """Verify benchmark suite hasn't been tampered with"""
        return self.benchmark_suite.verify_integrity(expected_hash)