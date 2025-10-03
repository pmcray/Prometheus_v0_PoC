"""
Recursive Font - Self-Modifying Strategies (v0.90)

Inspired by Hofstadter's "Recursive Font" from GEB, where symbols describe
their own structure. Here, strategies can modify themselves based on their
own evaluation.

This implements safe self-modification with governance constraints.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json


class ModificationType(Enum):
    """Types of self-modifications"""
    PARAMETER_TUNE = "parameter_tune"  # Adjust numeric parameters
    PRIORITY_REORDER = "priority_reorder"  # Change priority order
    RULE_ADD = "rule_add"  # Add new strategic rule
    RULE_REMOVE = "rule_remove"  # Remove underperforming rule
    CONDITION_REFINE = "condition_refine"  # Refine when rules apply


@dataclass
class StrategyComponent:
    """
    A component of a strategy that can be modified

    Example: "If opponent has 3 in a row, block it"
    - condition: "opponent has 3 in a row"
    - action: "block it"
    - priority: 0.9
    """
    component_id: str
    condition: str  # When this applies
    action: str  # What to do
    priority: float  # 0.0 to 1.0
    performance_history: List[bool] = field(default_factory=list)  # Success/failure

    def get_success_rate(self) -> float:
        """Calculate success rate of this component"""
        if not self.performance_history:
            return 0.5  # Unknown
        return sum(self.performance_history) / len(self.performance_history)


@dataclass
class StrategyModification:
    """Record of a self-modification"""
    modification_id: str
    modification_type: ModificationType
    description: str
    component_affected: Optional[str]
    old_value: Any
    new_value: Any
    performance_delta: float  # Expected improvement
    approved: bool = False
    applied: bool = False


class RecursiveStrategy:
    """
    A strategy that can modify itself based on performance

    Key principles:
    1. Strategies composed of components
    2. Each component tracks its own performance
    3. Underperforming components are modified
    4. All modifications subject to safety review
    """

    def __init__(self, strategy_id: str, initial_components: List[StrategyComponent]):
        self.strategy_id = strategy_id
        self.components = {c.component_id: c for c in initial_components}
        self.modification_history = []
        self.generation = 0
        self.overall_performance = []

    def propose_modification(self, performance_data: Dict[str, Any]) -> Optional[StrategyModification]:
        """
        Propose a self-modification based on performance

        Args:
            performance_data: Recent performance metrics

        Returns:
            Proposed modification or None
        """
        # Analyze component performance
        component_performances = {}
        for comp_id, component in self.components.items():
            success_rate = component.get_success_rate()
            component_performances[comp_id] = success_rate

        # Find underperforming components
        underperforming = [
            (comp_id, perf) for comp_id, perf in component_performances.items()
            if perf < 0.5 and len(self.components[comp_id].performance_history) >= 5
        ]

        if underperforming:
            # Propose removing worst component
            worst_id, worst_perf = min(underperforming, key=lambda x: x[1])
            worst_component = self.components[worst_id]

            modification = StrategyModification(
                modification_id=f"MOD{len(self.modification_history):04d}",
                modification_type=ModificationType.RULE_REMOVE,
                description=f"Remove underperforming rule: {worst_component.action}",
                component_affected=worst_id,
                old_value=worst_component,
                new_value=None,
                performance_delta=worst_perf - 0.5  # Expected improvement
            )

            return modification

        # Check if we should add a new rule
        overall_perf = (sum(self.overall_performance[-10:]) / 10
                       if len(self.overall_performance) >= 10 else 0.5)

        if overall_perf < 0.7 and len(self.components) < 10:
            # Propose adding a defensive rule
            # Generate unique component ID
            existing_ids = set(self.components.keys())
            new_id = f"COMP{len(self.components)}"
            counter = len(self.components)
            while new_id in existing_ids:
                counter += 1
                new_id = f"COMP{counter}"

            new_component = StrategyComponent(
                component_id=new_id,
                condition="opponent creating threat",
                action="increase defensive priority",
                priority=0.7
            )

            modification = StrategyModification(
                modification_id=f"MOD{len(self.modification_history):04d}",
                modification_type=ModificationType.RULE_ADD,
                description="Add defensive rule to improve performance",
                component_affected=None,
                old_value=None,
                new_value=new_component,
                performance_delta=0.2  # Expected improvement
            )

            return modification

        # Check for priority reordering
        if overall_perf > 0.8:
            # Find best performing component
            if component_performances:
                best_id = max(component_performances.items(), key=lambda x: x[1])[0]
                best_component = self.components[best_id]

                if best_component.priority < 0.9:
                    modification = StrategyModification(
                        modification_id=f"MOD{len(self.modification_history):04d}",
                        modification_type=ModificationType.PRIORITY_REORDER,
                        description=f"Increase priority of successful rule: {best_component.action}",
                        component_affected=best_id,
                        old_value=best_component.priority,
                        new_value=min(0.95, best_component.priority + 0.1),
                        performance_delta=0.05
                    )

                    return modification

        return None

    def apply_modification(self, modification: StrategyModification) -> bool:
        """
        Apply approved modification to strategy

        Args:
            modification: Approved modification to apply

        Returns:
            True if successfully applied
        """
        if not modification.approved:
            return False

        try:
            if modification.modification_type == ModificationType.RULE_REMOVE:
                if modification.component_affected in self.components:
                    del self.components[modification.component_affected]

            elif modification.modification_type == ModificationType.RULE_ADD:
                new_comp = modification.new_value
                self.components[new_comp.component_id] = new_comp

            elif modification.modification_type == ModificationType.PRIORITY_REORDER:
                if modification.component_affected in self.components:
                    self.components[modification.component_affected].priority = modification.new_value

            elif modification.modification_type == ModificationType.PARAMETER_TUNE:
                if modification.component_affected in self.components:
                    # Update component parameters
                    comp = self.components[modification.component_affected]
                    # Apply parameter changes (simplified)
                    comp.priority = modification.new_value

            modification.applied = True
            self.modification_history.append(modification)
            self.generation += 1

            return True

        except Exception as e:
            print(f"Failed to apply modification: {e}")
            return False

    def update_performance(self, component_id: str, success: bool):
        """Update performance history for a component"""
        if component_id in self.components:
            self.components[component_id].performance_history.append(success)

    def get_strategy_description(self) -> str:
        """Get human-readable strategy description"""
        lines = [f"Strategy {self.strategy_id} (Generation {self.generation}):"]
        lines.append("=" * 60)

        # Sort components by priority
        sorted_comps = sorted(self.components.values(),
                            key=lambda c: c.priority, reverse=True)

        for comp in sorted_comps:
            success_rate = comp.get_success_rate()
            lines.append(f"\n  [{comp.priority:.2f}] {comp.action}")
            lines.append(f"         When: {comp.condition}")
            lines.append(f"         Success Rate: {success_rate:.1%} ({len(comp.performance_history)} trials)")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        return {
            'strategy_id': self.strategy_id,
            'generation': self.generation,
            'num_components': len(self.components),
            'num_modifications': len(self.modification_history),
            'overall_performance': (sum(self.overall_performance) / len(self.overall_performance)
                                  if self.overall_performance else 0.0)
        }


class RecursiveFontEngine:
    """
    Engine that manages self-modifying strategies

    Ensures modifications are safe and beneficial.
    """

    def __init__(self, engine_id: str = "recursive_font_001"):
        self.engine_id = engine_id
        self.strategies = {}
        self.modification_log = []

    def register_strategy(self, strategy: RecursiveStrategy):
        """Register a strategy for self-modification"""
        self.strategies[strategy.strategy_id] = strategy

    def evolve_strategy(self, strategy_id: str,
                       performance_data: Dict[str, Any],
                       safety_check: Optional[Callable] = None) -> Optional[StrategyModification]:
        """
        Evolve a strategy based on performance

        Args:
            strategy_id: ID of strategy to evolve
            performance_data: Recent performance metrics
            safety_check: Optional safety validation function

        Returns:
            Applied modification or None
        """
        if strategy_id not in self.strategies:
            return None

        strategy = self.strategies[strategy_id]

        # Propose modification
        modification = strategy.propose_modification(performance_data)

        if modification is None:
            return None

        # Safety check
        if safety_check:
            is_safe = safety_check(modification)
            if not is_safe:
                modification.approved = False
                self.modification_log.append(modification)
                return None

        # Approve and apply
        modification.approved = True
        success = strategy.apply_modification(modification)

        if success:
            self.modification_log.append(modification)
            return modification

        return None

    def get_evolution_history(self, strategy_id: str) -> List[StrategyModification]:
        """Get evolution history for a strategy"""
        if strategy_id not in self.strategies:
            return []

        return self.strategies[strategy_id].modification_history

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        total_modifications = sum(len(s.modification_history) for s in self.strategies.values())
        approved_modifications = sum(
            len([m for m in s.modification_history if m.approved])
            for s in self.strategies.values()
        )

        return {
            'engine_id': self.engine_id,
            'num_strategies': len(self.strategies),
            'total_modifications': total_modifications,
            'approved_modifications': approved_modifications,
            'approval_rate': (approved_modifications / total_modifications
                            if total_modifications > 0 else 0.0)
        }


def create_connect4_recursive_strategy() -> RecursiveStrategy:
    """
    Create initial Connect4 strategy with self-modification capability

    Returns:
        RecursiveStrategy for Connect4
    """
    components = [
        StrategyComponent(
            component_id="COMP_WIN",
            condition="can win this turn",
            action="take winning move",
            priority=1.0
        ),
        StrategyComponent(
            component_id="COMP_BLOCK",
            condition="opponent can win next turn",
            action="block opponent win",
            priority=0.9
        ),
        StrategyComponent(
            component_id="COMP_CENTER",
            condition="center columns available",
            action="prefer center columns",
            priority=0.6
        ),
        StrategyComponent(
            component_id="COMP_BUILD",
            condition="can create 2-in-a-row",
            action="build sequences",
            priority=0.5
        )
    ]

    return RecursiveStrategy("connect4_recursive_001", components)
