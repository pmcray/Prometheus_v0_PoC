"""
Strange Loop and Isomorphism Detection (v0.89)

Implements Hofstadter's concepts of strange loops and isomorphic structures
for meta-cognitive capabilities and self-referential reasoning.

Based on "Gödel, Escher, Bach" by Douglas Hofstadter.
"""

from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


class LoopType(Enum):
    """Types of strange loops"""
    SELF_REFERENCE = "self_reference"  # System referring to itself
    TANGLED_HIERARCHY = "tangled_hierarchy"  # Levels feeding back
    META_LEARNING = "meta_learning"  # Learning about learning
    RECURSIVE_IMPROVEMENT = "recursive_improvement"  # Improving improvement process


@dataclass
class StrangeLoop:
    """
    A strange loop in the system

    Example: "The system learns strategies to improve learning strategies"
    This creates a feedback loop across hierarchical levels.
    """
    loop_id: str
    loop_type: LoopType
    description: str
    hierarchy_levels: List[str]  # Levels involved in the loop
    strength: float  # 0.0 to 1.0, how strong/active the loop is
    beneficial: bool = True  # Whether loop helps or harms


@dataclass
class Isomorphism:
    """
    Structural similarity between different domains

    Example: "Game winning strategies" is isomorphic to "Survival strategies"
    Both involve resource management, threat avoidance, planning.
    """
    isomorphism_id: str
    domain_a: str
    domain_b: str
    shared_structure: str  # Description of common structure
    mapping: Dict[str, str]  # Elements from A mapped to B
    strength: float  # 0.0 to 1.0, how strong the isomorphism is


class StrangeLoopDetector:
    """
    Detects and analyzes strange loops and isomorphisms in the system

    Key capabilities:
    1. Identify self-referential structures
    2. Detect tangled hierarchies (upward/downward causation)
    3. Find isomorphic patterns across domains
    4. Monitor meta-learning loops
    """

    def __init__(self, detector_id: str = "loop_detector_001"):
        self.detector_id = detector_id
        self.detected_loops = []
        self.detected_isomorphisms = []
        self.meta_level_counter = 0

    def detect_self_reference(self, system_state: Dict[str, Any]) -> List[StrangeLoop]:
        """
        Detect self-referential loops

        Example: Agent using strategies about strategy selection
        """
        loops = []

        # Check if system is learning about learning
        if 'learning_strategies' in system_state:
            learning_strats = system_state['learning_strategies']
            if any('meta' in str(s).lower() or 'improve learning' in str(s).lower()
                  for s in learning_strats):

                loop = StrangeLoop(
                    loop_id=f"SL{len(self.detected_loops):03d}",
                    loop_type=LoopType.META_LEARNING,
                    description="System is learning strategies to improve learning itself",
                    hierarchy_levels=["object_level_learning", "meta_learning", "meta_meta_learning"],
                    strength=0.7,
                    beneficial=True
                )
                loops.append(loop)
                self.detected_loops.append(loop)

        return loops

    def detect_tangled_hierarchy(self, evaluator_feedback: Dict[str, Any],
                                 corrector_output: Dict[str, Any]) -> List[StrangeLoop]:
        """
        Detect tangled hierarchies where upper levels affect lower levels

        Example: Meta-strategy (upper level) changes evaluation criteria (lower level)
        """
        loops = []

        # Check if corrector is modifying evaluation criteria
        if ('modify_evaluation' in corrector_output or
            'change_criteria' in corrector_output):

            loop = StrangeLoop(
                loop_id=f"SL{len(self.detected_loops):03d}",
                loop_type=LoopType.TANGLED_HIERARCHY,
                description="Corrector modifying Evaluator criteria creates tangled hierarchy",
                hierarchy_levels=["evaluator", "corrector", "meta_corrector"],
                strength=0.8,
                beneficial=True
            )
            loops.append(loop)
            self.detected_loops.append(loop)

        return loops

    def detect_recursive_improvement(self, improvement_history: List[Dict[str, Any]]) -> List[StrangeLoop]:
        """
        Detect recursive self-improvement loops

        Example: System improving its improvement process
        """
        loops = []

        if len(improvement_history) < 2:
            return loops

        # Check if recent improvements are about the improvement process itself
        recent = improvement_history[-5:]  # Last 5 improvements

        meta_improvements = [
            imp for imp in recent
            if any(keyword in str(imp).lower()
                  for keyword in ['improve learning', 'better critique',
                                 'enhanced correction', 'meta'])
        ]

        if len(meta_improvements) >= 2:
            loop = StrangeLoop(
                loop_id=f"SL{len(self.detected_loops):03d}",
                loop_type=LoopType.RECURSIVE_IMPROVEMENT,
                description="System recursively improving its own improvement mechanisms",
                hierarchy_levels=["performance", "improvement", "meta_improvement"],
                strength=min(1.0, len(meta_improvements) / 5.0),
                beneficial=True
            )
            loops.append(loop)
            self.detected_loops.append(loop)

        return loops

    def find_isomorphism(self, domain_a: str, patterns_a: List[Dict[str, Any]],
                        domain_b: str, patterns_b: List[Dict[str, Any]]) -> List[Isomorphism]:
        """
        Find isomorphic structures between domains

        Args:
            domain_a: First domain name
            patterns_a: Patterns from domain A
            domain_b: Second domain name
            patterns_b: Patterns from domain B

        Returns:
            List of detected isomorphisms
        """
        isomorphisms = []

        # Simple pattern matching based on types
        pattern_types_a = set(p.get('type', '') for p in patterns_a)
        pattern_types_b = set(p.get('type', '') for p in patterns_b)

        common_types = pattern_types_a & pattern_types_b

        if len(common_types) >= 2:  # At least 2 shared pattern types
            # Build mapping
            mapping = {}
            for ptype in common_types:
                instances_a = [p for p in patterns_a if p.get('type') == ptype]
                instances_b = [p for p in patterns_b if p.get('type') == ptype]

                if instances_a and instances_b:
                    mapping[instances_a[0].get('name', ptype)] = instances_b[0].get('name', ptype)

            strength = len(common_types) / max(len(pattern_types_a), len(pattern_types_b))

            iso = Isomorphism(
                isomorphism_id=f"ISO{len(self.detected_isomorphisms):03d}",
                domain_a=domain_a,
                domain_b=domain_b,
                shared_structure=f"Common pattern types: {', '.join(common_types)}",
                mapping=mapping,
                strength=strength
            )

            isomorphisms.append(iso)
            self.detected_isomorphisms.append(iso)

        return isomorphisms

    def analyze_loop_dynamics(self, loop: StrangeLoop,
                             system_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze how a strange loop affects system behavior

        Returns:
            Analysis dict with insights
        """
        analysis = {
            'loop_id': loop.loop_id,
            'loop_type': loop.loop_type.value,
            'stability': 'unknown',
            'growth_rate': 0.0,
            'recommendation': ''
        }

        # Check if loop is stable or growing
        if len(system_history) >= 5:
            recent_performance = [h.get('performance', 0.5) for h in system_history[-5:]]

            # Calculate trend
            if len(recent_performance) >= 2:
                trend = recent_performance[-1] - recent_performance[0]

                if trend > 0.1:
                    analysis['stability'] = 'growing'
                    analysis['growth_rate'] = trend
                    analysis['recommendation'] = 'Loop is beneficial, allow to continue'
                elif trend < -0.1:
                    analysis['stability'] = 'declining'
                    analysis['growth_rate'] = trend
                    analysis['recommendation'] = 'Loop may be harmful, monitor closely'
                else:
                    analysis['stability'] = 'stable'
                    analysis['recommendation'] = 'Loop is stable, no action needed'

        return analysis

    def get_meta_level(self) -> int:
        """
        Get current meta-level of system

        Meta-level 0: Direct game playing
        Meta-level 1: Learning strategies
        Meta-level 2: Learning about learning
        Meta-level 3: Learning about learning about learning
        etc.
        """
        # Count depth of meta-learning loops
        meta_loops = [l for l in self.detected_loops
                     if l.loop_type in [LoopType.META_LEARNING,
                                       LoopType.RECURSIVE_IMPROVEMENT]]

        return len(meta_loops)

    def prevent_infinite_regress(self, current_meta_level: int,
                                 max_meta_level: int = 3) -> bool:
        """
        Prevent infinite regress of meta-levels

        Args:
            current_meta_level: Current meta-level
            max_meta_level: Maximum allowed meta-level

        Returns:
            True if safe to proceed, False if would cause infinite regress
        """
        if current_meta_level >= max_meta_level:
            return False  # Too deep, prevent further meta-levels

        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics"""
        loop_types = {}
        for loop in self.detected_loops:
            loop_type = loop.loop_type.value
            loop_types[loop_type] = loop_types.get(loop_type, 0) + 1

        return {
            'detector_id': self.detector_id,
            'total_loops': len(self.detected_loops),
            'total_isomorphisms': len(self.detected_isomorphisms),
            'loop_types': loop_types,
            'current_meta_level': self.get_meta_level(),
            'beneficial_loops': len([l for l in self.detected_loops if l.beneficial]),
            'harmful_loops': len([l for l in self.detected_loops if not l.beneficial])
        }

    def visualize_strange_loop(self, loop: StrangeLoop) -> str:
        """
        Create ASCII visualization of strange loop

        Returns:
            String visualization
        """
        lines = []
        lines.append(f"Strange Loop: {loop.description}")
        lines.append("=" * 60)
        lines.append("")
        lines.append("Hierarchy Levels:")

        # Draw hierarchy with feedback
        for i, level in enumerate(loop.hierarchy_levels):
            indent = "  " * i
            if i == 0:
                lines.append(f"{indent}┌─ {level}")
            elif i == len(loop.hierarchy_levels) - 1:
                lines.append(f"{indent}└─ {level} ──┐")
            else:
                lines.append(f"{indent}├─ {level}")

        # Show feedback arrow
        lines.append("  " * (len(loop.hierarchy_levels) - 1) + "     │")
        lines.append("  " * (len(loop.hierarchy_levels) - 1) + "     ↓")
        lines.append("  " * (len(loop.hierarchy_levels) - 1) + "  [feedback loop]")
        lines.append("  " * (len(loop.hierarchy_levels) - 1) + "     ↓")
        lines.append(f"  ← ← ← ← ← ← ← ← ← ←")
        lines.append("")
        lines.append(f"Strength: {loop.strength:.1%}")
        lines.append(f"Beneficial: {loop.beneficial}")

        return "\n".join(lines)


def create_prometheus_strange_loops() -> List[StrangeLoop]:
    """
    Define the strange loops inherent in Prometheus architecture

    Returns:
        List of StrangeLoop objects
    """
    loops = []

    # Loop 1: CRLS Meta-Learning
    loops.append(StrangeLoop(
        loop_id="PROM_SL_001",
        loop_type=LoopType.META_LEARNING,
        description="CRLS loop learns strategies to improve the CRLS loop itself",
        hierarchy_levels=[
            "Game Playing (Level 0)",
            "Strategy Learning (Level 1)",
            "Learning Strategy Improvement (Level 2)",
            "Meta-Strategy Evolution (Level 3)"
        ],
        strength=0.85,
        beneficial=True
    ))

    # Loop 2: Evaluation-Correction Tangled Hierarchy
    loops.append(StrangeLoop(
        loop_id="PROM_SL_002",
        loop_type=LoopType.TANGLED_HIERARCHY,
        description="Corrector improves Evaluator, which evaluates Corrector's improvements",
        hierarchy_levels=[
            "Evaluator (critique generation)",
            "Corrector (strategy synthesis)",
            "Meta-Corrector (correction of corrections)"
        ],
        strength=0.75,
        beneficial=True
    ))

    # Loop 3: Analogy Self-Reference
    loops.append(StrangeLoop(
        loop_id="PROM_SL_003",
        loop_type=LoopType.SELF_REFERENCE,
        description="Analogy engine uses analogies to improve analogy-making",
        hierarchy_levels=[
            "Domain-Specific Knowledge",
            "Cross-Domain Analogies",
            "Meta-Analogical Reasoning"
        ],
        strength=0.65,
        beneficial=True
    ))

    # Loop 4: Recursive Self-Improvement
    loops.append(StrangeLoop(
        loop_id="PROM_SL_004",
        loop_type=LoopType.RECURSIVE_IMPROVEMENT,
        description="System improves its improvement process recursively",
        hierarchy_levels=[
            "Performance Optimization",
            "Learning Process Optimization",
            "Meta-Optimization"
        ],
        strength=0.70,
        beneficial=True
    ))

    return loops
