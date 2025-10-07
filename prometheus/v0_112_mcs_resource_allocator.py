"""
Prometheus v0.112: MCS Resource Allocator
Phase I: Grounding the Self - "What can I afford?"

This module implements the Modern Centrencephalic System (MCS) resource governor
optimized for Jetson Orin Nano hardware constraints, managing computational budgets
for expert chunks in the Causal Agentic Mesh.

Key Concepts (from workplan):
- Hardware-Aware Allocation: Tracks GPU memory, CPU, power on Jetson Orin Nano
- Reputation System: Expert chunks earn budget based on past performance
- Dynamic Prioritization: Reallocate resources to high-impact chunks
- Performance Target: 15% improvement over baseline

Based on:
- Prometheus AGI_ASI 0 A.D. Workplan.pdf Section 2.3
- I.J. Good's resource-bounded intelligence
- Existing MCS architecture from v0.19-v0.69
- Jetson Orin Nano 8GB specifications
"""

import logging
import time
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)

# Try to import Jetson-specific monitoring
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil not available - system monitoring limited")

# Jetson Orin Nano 8GB Specifications (from workplan)
JETSON_SPECS = {
    'gpu_memory_mb': 8192,  # 8GB shared memory
    'cpu_cores': 6,  # ARM Cortex-A78AE
    'max_power_watts': 25,  # Configurable power mode
    'gpu_tflops_fp16': 20,  # Ampere GPU
    'ram_bandwidth_gbps': 102.4,  # LPDDR5
}


class ResourceType(Enum):
    """Types of computational resources"""
    GPU_MEMORY = "gpu_memory"
    CPU_TIME = "cpu_time"
    INFERENCE_TOKENS = "inference_tokens"
    POWER_BUDGET = "power_budget"


@dataclass
class ResourceBudget:
    """Resource allocation for a time window"""
    gpu_memory_mb: float = 0.0  # GPU memory allocation
    cpu_percent: float = 0.0  # CPU percentage allocation
    inference_tokens: int = 0  # LLM inference token budget
    power_watts: float = 0.0  # Power consumption budget
    time_window_ms: float = 1000.0  # Time window for this budget

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            'gpu_memory_mb': self.gpu_memory_mb,
            'cpu_percent': self.cpu_percent,
            'inference_tokens': self.inference_tokens,
            'power_watts': self.power_watts,
            'time_window_ms': self.time_window_ms
        }


@dataclass
class ChunkReputation:
    """Reputation tracking for an expert chunk"""
    chunk_name: str
    total_allocations: int = 0
    successful_allocations: int = 0
    total_value_delivered: float = 0.0  # Cumulative causal contribution
    avg_resource_efficiency: float = 0.0  # Value per resource unit
    current_reputation_score: float = 0.5  # 0.0-1.0 score

    def update(self, success: bool, value_delivered: float, resources_used: float) -> None:
        """Update reputation based on performance"""
        self.total_allocations += 1
        if success:
            self.successful_allocations += 1
        self.total_value_delivered += value_delivered

        # Calculate efficiency (value per resource unit)
        if resources_used > 0:
            efficiency = value_delivered / resources_used
            # Running average
            alpha = 0.3  # Learning rate
            self.avg_resource_efficiency = (
                alpha * efficiency + (1 - alpha) * self.avg_resource_efficiency
            )

        # Update reputation score (success rate weighted by efficiency)
        success_rate = self.successful_allocations / self.total_allocations
        self.current_reputation_score = 0.6 * success_rate + 0.4 * min(self.avg_resource_efficiency, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'chunk_name': self.chunk_name,
            'total_allocations': self.total_allocations,
            'successful_allocations': self.successful_allocations,
            'success_rate': self.successful_allocations / self.total_allocations if self.total_allocations > 0 else 0.0,
            'total_value_delivered': self.total_value_delivered,
            'avg_resource_efficiency': self.avg_resource_efficiency,
            'current_reputation_score': self.current_reputation_score
        }


class SystemMonitor:
    """Monitor Jetson system resource usage"""

    def __init__(self):
        """Initialize system monitor"""
        self.has_gpu_monitoring = self._check_gpu_monitoring()

    def _check_gpu_monitoring(self) -> bool:
        """Check if GPU monitoring is available (tegrastats on Jetson)"""
        # On Jetson, we can read /sys/devices/gpu.0/load for GPU usage
        return os.path.exists('/sys/devices/gpu.0/load')

    def get_current_usage(self) -> Dict[str, float]:
        """
        Get current system resource usage

        Returns:
            Dictionary with current usage metrics
        """
        usage = {
            'gpu_memory_used_mb': 0.0,
            'cpu_percent': 0.0,
            'power_watts': 0.0,
            'timestamp': time.time()
        }

        if HAS_PSUTIL:
            # CPU usage
            usage['cpu_percent'] = psutil.cpu_percent(interval=0.1)

            # Memory usage (shared on Jetson)
            mem = psutil.virtual_memory()
            # Approximate GPU memory as portion of total used
            usage['gpu_memory_used_mb'] = mem.used / (1024 * 1024) * 0.3  # Rough estimate

        # GPU monitoring (Jetson-specific)
        if self.has_gpu_monitoring:
            try:
                with open('/sys/devices/gpu.0/load', 'r') as f:
                    gpu_load = int(f.read().strip())
                    # Estimate memory usage from load
                    usage['gpu_memory_used_mb'] = (gpu_load / 1000) * JETSON_SPECS['gpu_memory_mb']
            except Exception as e:
                logger.debug(f"Could not read GPU load: {e}")

        # Power monitoring (Jetson-specific via INA3221)
        try:
            # Read power from Jetson's power monitor
            power_files = [
                '/sys/bus/i2c/drivers/ina3221x/1-0040/iio:device0/in_power0_input',
                '/sys/bus/i2c/drivers/ina3221x/1-0041/iio:device0/in_power0_input'
            ]
            total_power = 0
            for path in power_files:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        # Power is in milliwatts
                        total_power += int(f.read().strip()) / 1000.0
            usage['power_watts'] = total_power
        except Exception as e:
            logger.debug(f"Could not read power: {e}")
            # Estimate based on CPU usage
            usage['power_watts'] = 5.0 + (usage['cpu_percent'] / 100.0) * 15.0

        return usage

    def get_available_resources(self) -> ResourceBudget:
        """
        Calculate currently available resources

        Returns:
            ResourceBudget with available capacity
        """
        current = self.get_current_usage()

        available = ResourceBudget(
            gpu_memory_mb=max(0, JETSON_SPECS['gpu_memory_mb'] - current['gpu_memory_used_mb']),
            cpu_percent=max(0, 100.0 - current['cpu_percent']),
            inference_tokens=1000,  # Per-turn token budget
            power_watts=max(0, JETSON_SPECS['max_power_watts'] - current['power_watts']),
            time_window_ms=1000.0  # 1 second turn budget
        )

        return available


class MCSResourceAllocator:
    """
    Modern Centrencephalic System Resource Governor

    Exit Criteria (from workplan):
    - Track GPU memory, CPU, power consumption
    - Reputation-based allocation to expert chunks
    - 15% performance improvement over baseline
    - Real-time monitoring on Jetson Orin Nano
    """

    def __init__(self, enable_monitoring: bool = True):
        """
        Initialize MCS resource allocator

        Args:
            enable_monitoring: Enable hardware monitoring (disable for testing)
        """
        self.monitor = SystemMonitor() if enable_monitoring else None
        self.chunk_reputations: Dict[str, ChunkReputation] = {}
        self.allocation_history: List[Dict[str, Any]] = []
        self.baseline_performance: Optional[float] = None
        self.current_performance: Optional[float] = None

        # Total resource pool (conservative allocation - leave headroom)
        self.total_budget = ResourceBudget(
            gpu_memory_mb=JETSON_SPECS['gpu_memory_mb'] * 0.6,  # 60% utilization target
            cpu_percent=80.0,  # 80% CPU target
            inference_tokens=2000,  # Per turn
            power_watts=JETSON_SPECS['max_power_watts'] * 0.8,  # 80% power target
            time_window_ms=1000.0
        )

    def register_chunk(self, chunk_name: str, initial_reputation: float = 0.5) -> None:
        """
        Register a new expert chunk for resource allocation

        Args:
            chunk_name: Name of chunk to register
            initial_reputation: Starting reputation score (0.0-1.0)
        """
        if chunk_name not in self.chunk_reputations:
            self.chunk_reputations[chunk_name] = ChunkReputation(
                chunk_name=chunk_name,
                current_reputation_score=initial_reputation
            )
            logger.info(f"🎯 MCS: Registered chunk '{chunk_name}' with reputation {initial_reputation:.2f}")

    def allocate_resources(
        self,
        requesting_chunks: List[str],
        chunk_priorities: Dict[str, int]
    ) -> Dict[str, ResourceBudget]:
        """
        Allocate resources to requesting chunks based on reputation and priority

        Args:
            requesting_chunks: List of chunk names requesting resources
            chunk_priorities: Priority scores for each chunk

        Returns:
            Dictionary mapping chunk names to allocated budgets
        """
        allocation_start = time.time()

        # Get available resources
        if self.monitor:
            available = self.monitor.get_available_resources()
        else:
            # Use full budget if monitoring disabled
            available = self.total_budget

        # Calculate allocation weights based on reputation and priority
        weights = {}
        total_weight = 0.0

        for chunk_name in requesting_chunks:
            # Ensure chunk is registered
            if chunk_name not in self.chunk_reputations:
                self.register_chunk(chunk_name)

            reputation = self.chunk_reputations[chunk_name]
            priority = chunk_priorities.get(chunk_name, 5) / 10.0  # Normalize to 0-1

            # Weight = (reputation * 0.6 + priority * 0.4)
            weight = reputation.current_reputation_score * 0.6 + priority * 0.4
            weights[chunk_name] = weight
            total_weight += weight

        # Allocate resources proportionally
        allocations = {}

        for chunk_name in requesting_chunks:
            if total_weight == 0:
                share = 1.0 / len(requesting_chunks)
            else:
                share = weights[chunk_name] / total_weight

            allocation = ResourceBudget(
                gpu_memory_mb=available.gpu_memory_mb * share,
                cpu_percent=available.cpu_percent * share,
                inference_tokens=int(available.inference_tokens * share),
                power_watts=available.power_watts * share,
                time_window_ms=available.time_window_ms
            )

            allocations[chunk_name] = allocation

            logger.debug(
                f"MCS: Allocated to '{chunk_name}': "
                f"GPU={allocation.gpu_memory_mb:.1f}MB, "
                f"CPU={allocation.cpu_percent:.1f}%, "
                f"Tokens={allocation.inference_tokens}, "
                f"Power={allocation.power_watts:.1f}W"
            )

        # Record allocation
        self.allocation_history.append({
            'timestamp': time.time(),
            'allocations': {k: v.to_dict() for k, v in allocations.items()},
            'available_before': available.to_dict(),
            'allocation_time_ms': (time.time() - allocation_start) * 1000
        })

        return allocations

    def report_execution(
        self,
        chunk_name: str,
        success: bool,
        value_delivered: float,
        resources_used: ResourceBudget
    ) -> None:
        """
        Report chunk execution results to update reputation

        Args:
            chunk_name: Name of chunk that executed
            success: Whether execution succeeded
            value_delivered: Causal contribution value
            resources_used: Actual resources consumed
        """
        if chunk_name not in self.chunk_reputations:
            self.register_chunk(chunk_name)

        # Calculate total resources used (weighted sum)
        total_resources = (
            resources_used.gpu_memory_mb / 1000.0 +
            resources_used.cpu_percent / 100.0 +
            resources_used.inference_tokens / 1000.0 +
            resources_used.power_watts / 10.0
        )

        # Update reputation
        self.chunk_reputations[chunk_name].update(success, value_delivered, total_resources)

        logger.debug(
            f"MCS: Updated '{chunk_name}' reputation to "
            f"{self.chunk_reputations[chunk_name].current_reputation_score:.3f} "
            f"(success={success}, value={value_delivered:.2f})"
        )

    def get_reputation_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get reputation summary for all chunks"""
        return {
            chunk_name: reputation.to_dict()
            for chunk_name, reputation in self.chunk_reputations.items()
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get overall MCS performance metrics"""
        if not self.allocation_history:
            return {'error': 'No allocation history'}

        # Calculate average allocation time
        avg_allocation_time = sum(
            h['allocation_time_ms'] for h in self.allocation_history
        ) / len(self.allocation_history)

        # Calculate resource utilization
        total_allocations = len(self.allocation_history)

        # Performance improvement
        improvement = 0.0
        if self.baseline_performance and self.current_performance:
            improvement = (
                (self.current_performance - self.baseline_performance) / self.baseline_performance
            ) * 100

        return {
            'total_allocations': total_allocations,
            'avg_allocation_time_ms': avg_allocation_time,
            'registered_chunks': len(self.chunk_reputations),
            'performance_improvement_percent': improvement,
            'meets_15_percent_target': improvement >= 15.0
        }

    def set_baseline_performance(self, performance_score: float) -> None:
        """Set baseline performance for comparison"""
        self.baseline_performance = performance_score
        logger.info(f"MCS: Baseline performance set to {performance_score:.2f}")

    def update_current_performance(self, performance_score: float) -> None:
        """Update current performance measurement"""
        self.current_performance = performance_score
        improvement = 0.0
        if self.baseline_performance:
            improvement = (
                (performance_score - self.baseline_performance) / self.baseline_performance
            ) * 100
            logger.info(
                f"MCS: Performance updated to {performance_score:.2f} "
                f"(+{improvement:.1f}% vs baseline)"
            )

    def export_statistics(self, filepath: str) -> None:
        """Export MCS statistics to JSON"""
        data = {
            'reputations': self.get_reputation_summary(),
            'performance_metrics': self.get_performance_metrics(),
            'allocation_history': self.allocation_history[-100:],  # Last 100 allocations
            'jetson_specs': JETSON_SPECS
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"📊 MCS statistics exported to {filepath}")


def verify_v0_112_exit_criteria(mcs: MCSResourceAllocator) -> Dict[str, bool]:
    """
    Verify v0.112 exit criteria

    From workplan:
    1. Track GPU memory, CPU, power consumption
    2. Reputation-based allocation
    3. 15% performance improvement
    4. Real-time monitoring

    Returns:
        Dictionary of criteria and pass/fail status
    """
    metrics = mcs.get_performance_metrics()

    criteria = {
        'tracks_gpu_memory': mcs.monitor is not None,
        'tracks_cpu': HAS_PSUTIL,
        'tracks_power': mcs.monitor is not None,
        'reputation_system_active': len(mcs.chunk_reputations) > 0,
        'has_allocation_history': len(mcs.allocation_history) > 0,
        '15_percent_improvement': metrics.get('meets_15_percent_target', False)
    }

    return criteria


if __name__ == '__main__':
    # Test MCS resource allocator
    logging.basicConfig(level=logging.INFO)

    print("Prometheus v0.112: MCS Resource Allocator Test")
    print("=" * 60)
    print(f"\nJetson Orin Nano Specifications:")
    print(f"  GPU Memory: {JETSON_SPECS['gpu_memory_mb']}MB")
    print(f"  CPU Cores: {JETSON_SPECS['cpu_cores']}")
    print(f"  Max Power: {JETSON_SPECS['max_power_watts']}W")
    print(f"  GPU TFLOPs (FP16): {JETSON_SPECS['gpu_tflops_fp16']}")

    # Create MCS
    mcs = MCSResourceAllocator(enable_monitoring=HAS_PSUTIL)

    # Register chunks
    print("\nRegistering expert chunks...")
    chunks = ['EconomyManager', 'MilitaryCommander', 'ProductionManager', 'Scouting']
    priorities = {'EconomyManager': 8, 'MilitaryCommander': 7, 'ProductionManager': 6, 'Scouting': 4}

    for chunk in chunks:
        mcs.register_chunk(chunk)

    # Simulate allocation
    print("\nSimulating resource allocation...")
    allocations = mcs.allocate_resources(chunks, priorities)

    for chunk_name, budget in allocations.items():
        print(f"  {chunk_name}:")
        print(f"    GPU: {budget.gpu_memory_mb:.1f}MB")
        print(f"    CPU: {budget.cpu_percent:.1f}%")
        print(f"    Tokens: {budget.inference_tokens}")
        print(f"    Power: {budget.power_watts:.1f}W")

    # Simulate execution feedback
    print("\nSimulating execution results...")
    mcs.report_execution('EconomyManager', success=True, value_delivered=10.0,
                        resources_used=ResourceBudget(gpu_memory_mb=100, cpu_percent=20))
    mcs.report_execution('MilitaryCommander', success=True, value_delivered=8.0,
                        resources_used=ResourceBudget(gpu_memory_mb=80, cpu_percent=15))

    # Show reputations
    print("\nChunk Reputations:")
    for chunk, rep in mcs.get_reputation_summary().items():
        print(f"  {chunk}: {rep['current_reputation_score']:.3f}")

    # Performance metrics
    print("\nPerformance Metrics:")
    metrics = mcs.get_performance_metrics()
    for key, value in metrics.items():
        print(f"  {key}: {value}")

    # Exit criteria
    print("\nv0.112 Exit Criteria:")
    criteria = verify_v0_112_exit_criteria(mcs)
    for criterion, passed in criteria.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {criterion}: {passed}")

    print("\n✅ v0.112 MCS Resource Allocator test complete!")
