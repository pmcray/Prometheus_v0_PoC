"""
Self-Modification Proposal Loop v0.1
Automated continuous improvement system for self-modifying agents

Implements a safe, continuous loop that:
1. Monitors system performance
2. Identifies improvement opportunities
3. Generates modification proposals
4. Applies verified improvements
5. Learns from outcomes
"""

import time
import threading
import logging
import queue
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import json

from .smm_agent import SelfModificationAgent, ModificationProposal, ModificationResult
from .iee import IEEHarness
from .fitness_monitor import FitnessMonotonicityMonitor
from ..benchmarks.benchmark_runner import BenchmarkRunner

@dataclass
class LoopConfiguration:
    """Configuration for the self-modification loop"""
    evaluation_interval_minutes: int = 60
    max_concurrent_modifications: int = 2
    performance_threshold: float = 0.05  # 5% improvement threshold
    safety_timeout_minutes: int = 30
    learning_window_hours: int = 24
    emergency_stop_conditions: Dict[str, Any] = None

@dataclass
class LoopState:
    """Current state of the self-modification loop"""
    is_running: bool = False
    last_evaluation_time: Optional[datetime] = None
    current_cycle: int = 0
    total_modifications_attempted: int = 0
    successful_modifications: int = 0
    emergency_stops: int = 0
    performance_trend: str = "stable"  # "improving", "stable", "degrading"

@dataclass
class PerformanceSnapshot:
    """Snapshot of system performance at a point in time"""
    timestamp: datetime
    benchmark_results: Dict[str, Any]
    fitness_metrics: Dict[str, Any]
    system_health: Dict[str, Any]
    modification_context: Dict[str, Any]

class SelfModificationLoop:
    """
    Continuous self-improvement loop with safety mechanisms

    Core Loop:
    1. Performance Monitoring: Continuously track system performance
    2. Opportunity Detection: Identify potential improvements
    3. Proposal Generation: Create specific modification proposals
    4. Safety Verification: Use IEE to verify safety and effectiveness
    5. Application: Apply verified modifications
    6. Learning: Update strategies based on outcomes
    7. Adaptation: Adjust loop parameters based on learning
    """

    def __init__(self,
                 codebase_path: str = ".",
                 config: Optional[LoopConfiguration] = None,
                 performance_callback: Optional[Callable[[Dict[str, Any]], None]] = None):

        self.codebase_path = Path(codebase_path).resolve()
        self.config = config or LoopConfiguration()
        self.performance_callback = performance_callback

        # Initialize core components
        self.smm_agent = SelfModificationAgent(codebase_path=str(self.codebase_path))
        self.iee_harness = self.smm_agent.iee_harness
        self.benchmark_runner = BenchmarkRunner()

        # Loop state management
        self.state = LoopState()
        self.performance_history: List[PerformanceSnapshot] = []
        self.modification_queue = queue.PriorityQueue()
        self.emergency_conditions = self._initialize_emergency_conditions()

        # Threading and control
        self.loop_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()

        # Logging and monitoring
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Safety mechanisms
        self.safety_lock = threading.Lock()
        self.last_safety_check = datetime.now()

        self.logger.info("🔄 Self-Modification Loop v0.1 initialized")

    def start(self, establish_baseline: bool = True) -> None:
        """
        Start the continuous self-modification loop

        Args:
            establish_baseline: Whether to establish baseline performance first
        """
        if self.state.is_running:
            self.logger.warning("⚠️ Loop is already running")
            return

        self.logger.info("🚀 Starting Self-Modification Loop")

        # Establish baseline if requested
        if establish_baseline:
            self.logger.info("📊 Establishing baseline performance")
            baseline = self.iee_harness.establish_fitness_baseline(num_runs=3)
            self.logger.info("✅ Baseline established")

        # Reset state
        self.state = LoopState(is_running=True)
        self.stop_event.clear()
        self.pause_event.clear()

        # Start loop thread
        self.loop_thread = threading.Thread(target=self._main_loop, daemon=True)
        self.loop_thread.start()

        self.logger.info("✅ Self-Modification Loop started")

    def stop(self, timeout: float = 30.0) -> bool:
        """
        Stop the self-modification loop gracefully

        Args:
            timeout: Maximum time to wait for graceful shutdown

        Returns:
            True if stopped successfully, False if timed out
        """
        if not self.state.is_running:
            self.logger.info("ℹ️ Loop is not running")
            return True

        self.logger.info("🛑 Stopping Self-Modification Loop")
        self.stop_event.set()
        self.state.is_running = False

        # Wait for thread to finish
        if self.loop_thread and self.loop_thread.is_alive():
            self.loop_thread.join(timeout=timeout)

            if self.loop_thread.is_alive():
                self.logger.error("❌ Failed to stop loop gracefully within timeout")
                return False

        self.logger.info("✅ Self-Modification Loop stopped")
        return True

    def pause(self) -> None:
        """Pause the self-modification loop"""
        self.pause_event.set()
        self.logger.info("⏸️ Self-Modification Loop paused")

    def resume(self) -> None:
        """Resume the self-modification loop"""
        self.pause_event.clear()
        self.logger.info("▶️ Self-Modification Loop resumed")

    def emergency_stop(self, reason: str) -> None:
        """
        Emergency stop with immediate termination

        Args:
            reason: Reason for emergency stop
        """
        self.logger.critical(f"🚨 EMERGENCY STOP: {reason}")
        self.state.emergency_stops += 1
        self.stop_event.set()
        self.state.is_running = False

        # Log emergency stop
        self._log_emergency_stop(reason)

    def _main_loop(self) -> None:
        """Main loop thread function"""
        self.logger.info("🔄 Entering main self-modification loop")

        try:
            while not self.stop_event.is_set():
                # Check for pause
                self.pause_event.wait()  # This will pass through if not set

                # Increment cycle counter
                self.state.current_cycle += 1
                cycle_start = datetime.now()

                self.logger.info(f"📊 Starting cycle {self.state.current_cycle}")

                try:
                    # Step 1: Performance monitoring
                    performance_snapshot = self._capture_performance_snapshot()
                    self.performance_history.append(performance_snapshot)

                    # Step 2: Safety checks
                    if not self._perform_safety_checks(performance_snapshot):
                        self.emergency_stop("Safety check failed")
                        break

                    # Step 3: Opportunity analysis
                    opportunities = self._analyze_improvement_opportunities(performance_snapshot)

                    # Step 4: Proposal generation and prioritization
                    proposals = self._generate_prioritized_proposals(opportunities)

                    # Step 5: Apply modifications (up to limit)
                    applied_modifications = self._apply_modifications(proposals)

                    # Step 6: Learning and adaptation
                    self._update_learning_systems(applied_modifications, performance_snapshot)

                    # Step 7: Loop parameter adaptation
                    self._adapt_loop_parameters()

                    # Update state
                    self.state.last_evaluation_time = cycle_start
                    self.state.total_modifications_attempted += len(applied_modifications)
                    self.state.successful_modifications += len([m for m in applied_modifications if m.modification_applied])

                    # Callback for external monitoring
                    if self.performance_callback:
                        self.performance_callback(self._generate_cycle_report())

                    self.logger.info(f"✅ Completed cycle {self.state.current_cycle}")

                except Exception as e:
                    self.logger.error(f"❌ Error in cycle {self.state.current_cycle}: {str(e)}")
                    if self._is_critical_error(e):
                        self.emergency_stop(f"Critical error: {str(e)}")
                        break

                # Wait for next cycle
                self._wait_for_next_cycle()

        except Exception as e:
            self.logger.critical(f"💥 Fatal error in main loop: {str(e)}")
        finally:
            self.state.is_running = False
            self.logger.info("🏁 Main loop terminated")

    def _capture_performance_snapshot(self) -> PerformanceSnapshot:
        """Capture current system performance"""
        self.logger.info("📸 Capturing performance snapshot")

        # Run benchmark
        benchmark_results = self.benchmark_runner.run_full_benchmark(save_results=False)

        # Get fitness metrics
        fitness_report = self.smm_agent.fitness_monitor.generate_fitness_report()

        # System health check
        system_health = {
            "active_environments": len(self.smm_agent.iee_harness.active_environments),
            "memory_usage": self._get_memory_usage(),
            "disk_space": self._get_disk_space(),
            "cpu_usage": self._get_cpu_usage()
        }

        # Modification context
        modification_context = {
            "recent_modifications": len([
                r for r in self.smm_agent.modification_results
                if datetime.fromisoformat(r.application_timestamp) > datetime.now() - timedelta(hours=1)
            ]),
            "success_patterns": dict(self.smm_agent.success_patterns),
            "active_proposals": len(self.smm_agent.active_proposals)
        }

        return PerformanceSnapshot(
            timestamp=datetime.now(),
            benchmark_results=benchmark_results,
            fitness_metrics=fitness_report,
            system_health=system_health,
            modification_context=modification_context
        )

    def _perform_safety_checks(self, snapshot: PerformanceSnapshot) -> bool:
        """Perform comprehensive safety checks"""
        with self.safety_lock:
            self.logger.info("🛡️ Performing safety checks")

            # Check 1: Performance degradation
            if self._detect_performance_degradation(snapshot):
                self.logger.warning("⚠️ Performance degradation detected")
                return False

            # Check 2: Resource constraints
            if not self._check_resource_constraints(snapshot):
                self.logger.warning("⚠️ Resource constraint violation")
                return False

            # Check 3: Modification rate limits
            if not self._check_modification_rate_limits():
                self.logger.warning("⚠️ Modification rate limit exceeded")
                return False

            # Check 4: Emergency conditions
            for condition_name, condition_func in self.emergency_conditions.items():
                if condition_func(snapshot):
                    self.logger.warning(f"⚠️ Emergency condition triggered: {condition_name}")
                    return False

            self.last_safety_check = datetime.now()
            return True

    def _analyze_improvement_opportunities(self, snapshot: PerformanceSnapshot) -> List[Dict[str, Any]]:
        """Analyze current performance for improvement opportunities"""
        self.logger.info("🔍 Analyzing improvement opportunities")

        # Use SMM agent to analyze opportunities
        opportunities = self.smm_agent.analyze_improvement_opportunities()

        # Filter based on recent performance
        filtered_opportunities = []
        for opportunity in opportunities:
            # Skip if we've recently tried this type of modification
            if self._recently_attempted_similar(opportunity):
                continue

            # Enhance with performance context
            opportunity['performance_context'] = {
                'current_success_rate': snapshot.benchmark_results['summary_metrics']['success_rate'],
                'trend': self._calculate_performance_trend(),
                'urgency': self._calculate_urgency(opportunity, snapshot)
            }

            filtered_opportunities.append(opportunity)

        self.logger.info(f"📊 Found {len(filtered_opportunities)} viable opportunities")
        return filtered_opportunities

    def _generate_prioritized_proposals(self, opportunities: List[Dict[str, Any]]) -> List[ModificationProposal]:
        """Generate and prioritize modification proposals"""
        self.logger.info("💡 Generating modification proposals")

        proposals = []
        for opportunity in opportunities[:5]:  # Limit to top 5 opportunities
            try:
                proposal = self.smm_agent.generate_modification_proposal(opportunity)
                proposals.append(proposal)
            except Exception as e:
                self.logger.warning(f"Failed to generate proposal for {opportunity['type']}: {e}")

        # Sort by confidence and urgency
        proposals.sort(
            key=lambda p: (p.confidence_score * 0.7 + self._get_urgency_score(p) * 0.3),
            reverse=True
        )

        self.logger.info(f"✅ Generated {len(proposals)} prioritized proposals")
        return proposals

    def _apply_modifications(self, proposals: List[ModificationProposal]) -> List[ModificationResult]:
        """Apply modifications up to the concurrency limit"""
        self.logger.info(f"🚀 Applying up to {self.config.max_concurrent_modifications} modifications")

        results = []
        applied_count = 0

        for proposal in proposals:
            if applied_count >= self.config.max_concurrent_modifications:
                break

            if self.stop_event.is_set():
                break

            try:
                self.logger.info(f"🔧 Applying modification: {proposal.proposal_id}")
                result = self.smm_agent.apply_modification(proposal)
                results.append(result)

                if result.modification_applied:
                    applied_count += 1
                    self.logger.info(f"✅ Successfully applied {proposal.proposal_id}")
                else:
                    self.logger.info(f"❌ Rejected {proposal.proposal_id}")

            except Exception as e:
                self.logger.error(f"💥 Error applying {proposal.proposal_id}: {e}")

        return results

    def _update_learning_systems(self, modifications: List[ModificationResult], snapshot: PerformanceSnapshot):
        """Update learning systems based on modification outcomes"""
        self.logger.info("🧠 Updating learning systems")

        # Update performance trends
        self._update_performance_trends(snapshot)

        # Analyze modification effectiveness
        for result in modifications:
            if result.modification_applied:
                self._analyze_modification_effectiveness(result, snapshot)

        # Adapt strategies based on outcomes
        self._adapt_modification_strategies(modifications)

    def _adapt_loop_parameters(self):
        """Adapt loop parameters based on performance and outcomes"""
        # Adjust evaluation interval based on performance stability
        recent_performance = self.performance_history[-5:] if len(self.performance_history) >= 5 else self.performance_history

        if len(recent_performance) >= 3:
            variance = self._calculate_performance_variance(recent_performance)

            if variance > 0.1:  # High variance - check more frequently
                self.config.evaluation_interval_minutes = max(30, self.config.evaluation_interval_minutes - 10)
            elif variance < 0.02:  # Low variance - can check less frequently
                self.config.evaluation_interval_minutes = min(120, self.config.evaluation_interval_minutes + 10)

    def _wait_for_next_cycle(self):
        """Wait for the next evaluation cycle"""
        wait_time = self.config.evaluation_interval_minutes * 60  # Convert to seconds
        self.stop_event.wait(timeout=wait_time)

    def _detect_performance_degradation(self, snapshot: PerformanceSnapshot) -> bool:
        """Detect if performance has degraded significantly"""
        if len(self.performance_history) < 3:
            return False

        current_success_rate = snapshot.benchmark_results['summary_metrics']['success_rate']
        recent_avg = sum(
            s.benchmark_results['summary_metrics']['success_rate']
            for s in self.performance_history[-3:]
        ) / 3

        degradation = recent_avg - current_success_rate
        return degradation > 0.15  # 15% degradation threshold

    def _check_resource_constraints(self, snapshot: PerformanceSnapshot) -> bool:
        """Check if system resources are within acceptable limits"""
        health = snapshot.system_health

        return (
            health.get('memory_usage', 0) < 0.9 and
            health.get('disk_space', 1.0) > 0.1 and
            health.get('cpu_usage', 0) < 0.8
        )

    def _check_modification_rate_limits(self) -> bool:
        """Check if modification rate is within safe limits"""
        recent_modifications = len([
            r for r in self.smm_agent.modification_results
            if datetime.fromisoformat(r.application_timestamp) > datetime.now() - timedelta(hours=1)
        ])

        return recent_modifications < 5  # Max 5 modifications per hour

    def _initialize_emergency_conditions(self) -> Dict[str, Callable]:
        """Initialize emergency stop conditions"""
        return {
            "fitness_collapse": lambda s: s.fitness_metrics.get('violation_rate', 0) > 0.8,
            "security_breach": lambda s: s.benchmark_results.get('security_analysis', {}).get('risk_score', 0) > 0.9,
            "resource_exhaustion": lambda s: s.system_health.get('memory_usage', 0) > 0.95,
            "modification_cascade": lambda s: s.modification_context.get('recent_modifications', 0) > 10
        }

    def _recently_attempted_similar(self, opportunity: Dict[str, Any]) -> bool:
        """Check if we've recently attempted a similar modification"""
        similar_count = len([
            r for r in self.smm_agent.modification_results
            if (datetime.fromisoformat(r.application_timestamp) > datetime.now() - timedelta(hours=6) and
                any(p.modification_type == opportunity['type'] for p in self.smm_agent.proposal_history
                   if p.proposal_id == r.proposal_id))
        ])
        return similar_count >= 2

    def _calculate_performance_trend(self) -> str:
        """Calculate current performance trend"""
        if len(self.performance_history) < 3:
            return "stable"

        recent_scores = [
            s.benchmark_results['summary_metrics']['success_rate']
            for s in self.performance_history[-3:]
        ]

        if recent_scores[-1] > recent_scores[0] + 0.05:
            return "improving"
        elif recent_scores[-1] < recent_scores[0] - 0.05:
            return "degrading"
        else:
            return "stable"

    def _calculate_urgency(self, opportunity: Dict[str, Any], snapshot: PerformanceSnapshot) -> float:
        """Calculate urgency score for an opportunity"""
        urgency = 0.5  # Base urgency

        # Higher urgency if performance is degrading
        if self._calculate_performance_trend() == "degrading":
            urgency += 0.3

        # Higher urgency for high-impact opportunities
        if opportunity.get('impact') == 'high':
            urgency += 0.2

        # Lower urgency if recent modifications were unsuccessful
        recent_failures = len([
            r for r in self.smm_agent.modification_results[-5:]
            if not r.modification_applied
        ])
        if recent_failures > 3:
            urgency -= 0.2

        return max(0.1, min(1.0, urgency))

    def _get_urgency_score(self, proposal: ModificationProposal) -> float:
        """Get urgency score for a proposal"""
        return 0.5 if proposal.estimated_impact == 'medium' else (0.8 if proposal.estimated_impact == 'high' else 0.2)

    def _update_performance_trends(self, snapshot: PerformanceSnapshot):
        """Update performance trend analysis"""
        trend_data = {
            "timestamp": snapshot.timestamp.isoformat(),
            "success_rate": snapshot.benchmark_results['summary_metrics']['success_rate'],
            "execution_time": snapshot.benchmark_results['summary_metrics']['average_execution_time_ms'],
            "modification_count": len(self.smm_agent.modification_results)
        }
        self.smm_agent.performance_trends.append(trend_data)

        # Keep only recent trends (last 100 entries)
        if len(self.smm_agent.performance_trends) > 100:
            self.smm_agent.performance_trends = self.smm_agent.performance_trends[-100:]

    def _analyze_modification_effectiveness(self, result: ModificationResult, snapshot: PerformanceSnapshot):
        """Analyze the effectiveness of a specific modification"""
        # This would involve comparing before/after performance
        # For now, just log the outcome
        self.logger.info(f"📈 Analyzed effectiveness of {result.proposal_id}: {'effective' if result.modification_applied else 'ineffective'}")

    def _adapt_modification_strategies(self, modifications: List[ModificationResult]):
        """Adapt modification strategies based on recent outcomes"""
        success_rate = len([m for m in modifications if m.modification_applied]) / len(modifications) if modifications else 1.0

        # Adjust confidence thresholds based on success rate
        if success_rate < 0.3:
            # Lower success rate - be more conservative
            self.logger.info("📉 Adapting to be more conservative due to low success rate")
        elif success_rate > 0.8:
            # High success rate - can be more aggressive
            self.logger.info("📈 Adapting to be more aggressive due to high success rate")

    def _calculate_performance_variance(self, snapshots: List[PerformanceSnapshot]) -> float:
        """Calculate performance variance from snapshots"""
        if len(snapshots) < 2:
            return 0.0

        success_rates = [s.benchmark_results['summary_metrics']['success_rate'] for s in snapshots]
        mean = sum(success_rates) / len(success_rates)
        variance = sum((x - mean) ** 2 for x in success_rates) / len(success_rates)
        return variance

    def _is_critical_error(self, error: Exception) -> bool:
        """Determine if an error is critical enough to stop the loop"""
        critical_errors = (KeyboardInterrupt, SystemExit, MemoryError)
        return isinstance(error, critical_errors)

    def _get_memory_usage(self) -> float:
        """Get current memory usage (simplified)"""
        try:
            import psutil
            return psutil.virtual_memory().percent / 100
        except ImportError:
            return 0.5  # Default if psutil not available

    def _get_disk_space(self) -> float:
        """Get available disk space (simplified)"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(self.codebase_path)
            return free / total
        except:
            return 0.5  # Default if unavailable

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage (simplified)"""
        try:
            import psutil
            return psutil.cpu_percent() / 100
        except ImportError:
            return 0.3  # Default if psutil not available

    def _log_emergency_stop(self, reason: str):
        """Log emergency stop event"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "cycle": self.state.current_cycle,
            "total_modifications": self.state.total_modifications_attempted,
            "successful_modifications": self.state.successful_modifications
        }

        # Save to emergency log
        emergency_log = self.codebase_path / "emergency_stops.json"
        if emergency_log.exists():
            with open(emergency_log, 'r') as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(log_entry)

        with open(emergency_log, 'w') as f:
            json.dump(logs, f, indent=2)

    def _generate_cycle_report(self) -> Dict[str, Any]:
        """Generate report for the current cycle"""
        return {
            "cycle": self.state.current_cycle,
            "timestamp": datetime.now().isoformat(),
            "state": asdict(self.state),
            "performance_summary": self.performance_history[-1].benchmark_results['summary_metrics'] if self.performance_history else {},
            "recent_modifications": len([
                r for r in self.smm_agent.modification_results
                if datetime.fromisoformat(r.application_timestamp) > datetime.now() - timedelta(hours=1)
            ])
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the self-modification loop"""
        return {
            "loop_state": asdict(self.state),
            "configuration": asdict(self.config),
            "performance_history_length": len(self.performance_history),
            "current_trend": self._calculate_performance_trend() if self.performance_history else "unknown",
            "last_safety_check": self.last_safety_check.isoformat(),
            "smm_agent_stats": self.smm_agent.generate_self_modification_report()
        }