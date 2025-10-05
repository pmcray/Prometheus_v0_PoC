"""
Fitness Monotonicity Monitor v0.1
Advanced fitness tracking and regression detection for self-modifying systems

Implements strict fitness monotonicity enforcement to ensure evolutionary improvements
only proceed when they demonstrate measurable performance gains.
"""

import json
import statistics
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import logging

@dataclass
class FitnessMetrics:
    """Core fitness metrics for comparison"""
    success_rate: float
    execution_time_ms: float
    stability_score: float
    improvement_rate: float
    confidence_interval: Tuple[float, float]
    sample_size: int

@dataclass
class MonotonicityViolation:
    """Represents a violation of fitness monotonicity"""
    metric_name: str
    current_value: float
    baseline_value: float
    threshold: float
    severity: str  # 'minor', 'major', 'critical'
    regression_percentage: float
    statistical_significance: float

class FitnessMonotonicityMonitor:
    """
    Strict fitness monotonicity enforcement system

    Ensures that all self-modifications result in measurable performance improvements
    or at minimum maintain current performance levels within statistical bounds.
    """

    def __init__(self,
                 confidence_level: float = 0.95,
                 min_sample_size: int = 3,
                 baseline_file: str = "fitness_baseline.json"):

        self.confidence_level = confidence_level
        self.min_sample_size = min_sample_size
        self.baseline_file = Path(baseline_file)

        # Statistical thresholds
        self.critical_threshold = 0.10  # 10% regression is critical
        self.major_threshold = 0.05     # 5% regression is major
        self.minor_threshold = 0.02     # 2% regression is minor

        # Load baseline if available
        self.baseline_metrics: Optional[Dict[str, FitnessMetrics]] = None
        self._load_baseline()

        # Performance history
        self.performance_history: List[Dict[str, Any]] = []

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def establish_baseline(self, benchmark_results: List[Dict[str, Any]]) -> Dict[str, FitnessMetrics]:
        """Establish baseline fitness metrics from multiple benchmark runs"""
        self.logger.info(f"📊 Establishing fitness baseline from {len(benchmark_results)} runs")

        if len(benchmark_results) < self.min_sample_size:
            raise ValueError(f"Need at least {self.min_sample_size} runs to establish baseline")

        # Extract metrics from each run
        success_rates = []
        execution_times = []
        stability_scores = []

        for result in benchmark_results:
            metrics = result.get("summary_metrics", {})
            success_rates.append(metrics.get("success_rate", 0.0))
            execution_times.append(metrics.get("average_execution_time_ms", float('inf')))
            stability_scores.append(metrics.get("stability_score", 0.0))

        # Calculate baseline statistics
        baseline = {}

        # Success rate baseline
        baseline["success_rate"] = self._calculate_fitness_metrics(
            success_rates, "success_rate", higher_is_better=True
        )

        # Execution time baseline (lower is better)
        baseline["execution_time"] = self._calculate_fitness_metrics(
            execution_times, "execution_time", higher_is_better=False
        )

        # Stability score baseline
        baseline["stability"] = self._calculate_fitness_metrics(
            stability_scores, "stability", higher_is_better=True
        )

        self.baseline_metrics = baseline
        self._save_baseline(baseline)

        self.logger.info("✅ Fitness baseline established and saved")
        return baseline

    def check_fitness_monotonicity(self, current_results: Dict[str, Any]) -> Tuple[bool, List[MonotonicityViolation]]:
        """
        Check if current performance maintains fitness monotonicity

        Returns:
            (monotonicity_maintained, violations_list)
        """
        self.logger.info("🔍 Checking fitness monotonicity")

        if not self.baseline_metrics:
            self.logger.warning("⚠️ No baseline available - cannot check monotonicity")
            return True, []

        violations = []
        current_metrics = current_results.get("summary_metrics", {})

        # Check success rate monotonicity
        success_violation = self._check_metric_monotonicity(
            "success_rate",
            current_metrics.get("success_rate", 0.0),
            self.baseline_metrics["success_rate"],
            higher_is_better=True
        )
        if success_violation:
            violations.append(success_violation)

        # Check execution time monotonicity (lower is better)
        time_violation = self._check_metric_monotonicity(
            "execution_time",
            current_metrics.get("average_execution_time_ms", float('inf')),
            self.baseline_metrics["execution_time"],
            higher_is_better=False
        )
        if time_violation:
            violations.append(time_violation)

        # Check stability monotonicity
        stability_violation = self._check_metric_monotonicity(
            "stability",
            current_metrics.get("stability_score", 0.0),
            self.baseline_metrics["stability"],
            higher_is_better=True
        )
        if stability_violation:
            violations.append(stability_violation)

        # Overall monotonicity decision
        critical_violations = [v for v in violations if v.severity == "critical"]
        monotonicity_maintained = len(critical_violations) == 0

        if monotonicity_maintained:
            self.logger.info("✅ Fitness monotonicity maintained")
        else:
            self.logger.warning(f"❌ Fitness monotonicity violated: {len(violations)} violations")

        # Add to performance history
        self.performance_history.append({
            "timestamp": datetime.now().isoformat(),
            "monotonicity_maintained": monotonicity_maintained,
            "violations": [asdict(v) for v in violations],
            "results": current_results
        })

        return monotonicity_maintained, violations

    def _calculate_fitness_metrics(self, values: List[float], metric_name: str, higher_is_better: bool) -> FitnessMetrics:
        """Calculate comprehensive fitness metrics from sample data"""
        if not values:
            raise ValueError(f"No values provided for {metric_name}")

        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0.0

        # Calculate confidence interval
        if len(values) > 1:
            # Use t-distribution for small samples (if scipy available)
            try:
                from scipy import stats
                alpha = 1 - self.confidence_level
                df = len(values) - 1
                t_critical = stats.t.ppf(1 - alpha/2, df)
                margin_error = t_critical * (stdev / np.sqrt(len(values)))
                ci_lower = mean - margin_error
                ci_upper = mean + margin_error
            except ImportError:
                # Fallback to normal approximation if scipy not available
                z_score = 1.96  # 95% confidence interval
                margin_error = z_score * (stdev / np.sqrt(len(values)))
                ci_lower = mean - margin_error
                ci_upper = mean + margin_error
        else:
            ci_lower = ci_upper = mean

        # Calculate improvement rate (trend)
        if len(values) >= 2:
            if higher_is_better:
                improvement_rate = (values[-1] - values[0]) / (values[0] + 1e-10)
            else:
                improvement_rate = (values[0] - values[-1]) / (values[0] + 1e-10)
        else:
            improvement_rate = 0.0

        # Stability score (inverse of coefficient of variation)
        stability_score = 1.0 / (1.0 + (stdev / (abs(mean) + 1e-10)))

        return FitnessMetrics(
            success_rate=mean if metric_name == "success_rate" else 0.0,
            execution_time_ms=mean if metric_name == "execution_time" else 0.0,
            stability_score=stability_score,
            improvement_rate=improvement_rate,
            confidence_interval=(ci_lower, ci_upper),
            sample_size=len(values)
        )

    def _check_metric_monotonicity(self,
                                 metric_name: str,
                                 current_value: float,
                                 baseline_metrics: FitnessMetrics,
                                 higher_is_better: bool) -> Optional[MonotonicityViolation]:
        """Check monotonicity for a specific metric"""

        baseline_value = getattr(baseline_metrics, metric_name, baseline_metrics.success_rate)
        ci_lower, ci_upper = baseline_metrics.confidence_interval

        # Determine acceptable threshold based on confidence interval
        if higher_is_better:
            # For higher-is-better metrics, use lower bound of confidence interval
            acceptable_threshold = ci_lower
            regression = baseline_value - current_value
            regression_percentage = regression / (baseline_value + 1e-10)
        else:
            # For lower-is-better metrics, use upper bound of confidence interval
            acceptable_threshold = ci_upper
            regression = current_value - baseline_value
            regression_percentage = regression / (baseline_value + 1e-10)

        # Check if violation occurred
        violation_occurred = False
        if higher_is_better:
            violation_occurred = current_value < acceptable_threshold
        else:
            violation_occurred = current_value > acceptable_threshold

        if not violation_occurred:
            return None

        # Determine severity
        abs_regression = abs(regression_percentage)
        if abs_regression >= self.critical_threshold:
            severity = "critical"
        elif abs_regression >= self.major_threshold:
            severity = "major"
        elif abs_regression >= self.minor_threshold:
            severity = "minor"
        else:
            return None  # Below minor threshold

        # Calculate statistical significance
        if baseline_metrics.sample_size > 1:
            # Simple z-test approximation
            try:
                from scipy import stats
                z_score = abs(current_value - baseline_value) / (
                    np.sqrt(baseline_value * (1 - baseline_value) / baseline_metrics.sample_size) + 1e-10
                )
                significance = min(1.0, 2 * (1 - stats.norm.cdf(abs(z_score))))  # two-tailed
            except ImportError:
                # Fallback without scipy
                significance = 0.5 if abs(current_value - baseline_value) < 0.1 else 0.1
        else:
            significance = 0.5  # Unknown significance

        return MonotonicityViolation(
            metric_name=metric_name,
            current_value=current_value,
            baseline_value=baseline_value,
            threshold=acceptable_threshold,
            severity=severity,
            regression_percentage=regression_percentage,
            statistical_significance=significance
        )

    def generate_fitness_report(self) -> Dict[str, Any]:
        """Generate comprehensive fitness monotonicity report"""
        if not self.performance_history:
            return {"error": "No performance history available"}

        # Calculate summary statistics
        total_checks = len(self.performance_history)
        violations_count = sum(1 for entry in self.performance_history if not entry["monotonicity_maintained"])

        # Violation severity breakdown
        severity_counts = {"critical": 0, "major": 0, "minor": 0}
        for entry in self.performance_history:
            for violation in entry["violations"]:
                severity_counts[violation["severity"]] += 1

        # Recent trend (last 5 checks)
        recent_entries = self.performance_history[-5:]
        recent_violations = sum(1 for entry in recent_entries if not entry["monotonicity_maintained"])
        trend = "improving" if recent_violations < violations_count / total_checks else "stable"
        if recent_violations > len(recent_entries) * 0.6:
            trend = "degrading"

        return {
            "report_timestamp": datetime.now().isoformat(),
            "baseline_available": self.baseline_metrics is not None,
            "total_monotonicity_checks": total_checks,
            "violations_detected": violations_count,
            "violation_rate": violations_count / total_checks if total_checks > 0 else 0,
            "severity_breakdown": severity_counts,
            "recent_trend": trend,
            "confidence_level": self.confidence_level,
            "current_baseline": asdict(self.baseline_metrics) if self.baseline_metrics else None,
            "recommendations": self._generate_recommendations()
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on fitness history"""
        recommendations = []

        if not self.performance_history:
            return ["Establish baseline performance before implementing self-modifications"]

        recent_violations = sum(
            1 for entry in self.performance_history[-5:]
            if not entry["monotonicity_maintained"]
        )

        if recent_violations > 2:
            recommendations.append("Recent performance regressions detected - halt self-modifications")
            recommendations.append("Investigate root cause of fitness degradation")

        # Check for specific metric issues
        violation_metrics = set()
        for entry in self.performance_history[-3:]:
            for violation in entry["violations"]:
                violation_metrics.add(violation["metric_name"])

        if "success_rate" in violation_metrics:
            recommendations.append("Focus on improving task success rate")
        if "execution_time" in violation_metrics:
            recommendations.append("Optimize execution performance")
        if "stability" in violation_metrics:
            recommendations.append("Improve system stability and consistency")

        if not recommendations:
            recommendations.append("Fitness monotonicity maintained - continue current approach")

        return recommendations

    def _load_baseline(self):
        """Load baseline metrics from file"""
        if self.baseline_file.exists():
            try:
                with open(self.baseline_file, 'r') as f:
                    data = json.load(f)

                # Reconstruct FitnessMetrics objects
                baseline = {}
                for metric_name, metric_data in data.items():
                    baseline[metric_name] = FitnessMetrics(**metric_data)

                self.baseline_metrics = baseline
                self.logger.info(f"📊 Loaded fitness baseline from {self.baseline_file}")

            except Exception as e:
                self.logger.warning(f"⚠️ Failed to load baseline: {e}")

    def _save_baseline(self, baseline: Dict[str, FitnessMetrics]):
        """Save baseline metrics to file"""
        try:
            # Convert to JSON-serializable format
            data = {}
            for metric_name, metrics in baseline.items():
                data[metric_name] = asdict(metrics)

            with open(self.baseline_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            self.logger.info(f"💾 Baseline saved to {self.baseline_file}")

        except Exception as e:
            self.logger.error(f"❌ Failed to save baseline: {e}")

    def reset_baseline(self):
        """Reset baseline metrics"""
        self.baseline_metrics = None
        if self.baseline_file.exists():
            self.baseline_file.unlink()
        self.performance_history.clear()
        self.logger.info("🔄 Fitness baseline reset")