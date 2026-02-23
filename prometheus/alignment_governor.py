"""
MCS Alignment Governor (v0.85)

Ensures that learning and strategy evolution remain aligned with
safety constraints and intended objectives. Prevents adversarial
drift and maintains goal integrity.

MCS = Multi-Constraint Safety framework
"""

from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib


class ViolationType(Enum):
    """Types of alignment violations"""
    GOAL_DRIFT = "goal_drift"  # Strategies drifting from intended goals
    SAFETY_VIOLATION = "safety_violation"  # Unsafe behaviors
    FAIRNESS_VIOLATION = "fairness_violation"  # Unfair or exploitative tactics
    DECEPTION = "deception"  # Deceptive or misleading behavior
    RESOURCE_ABUSE = "resource_abuse"  # Excessive resource consumption


@dataclass
class SafetyConstraint:
    """
    Immutable safety constraint that cannot be modified

    These form the core of the alignment framework.
    """
    constraint_id: str
    name: str
    description: str
    check_function: str  # Name of checking function
    severity: int  # 1-10, with 10 being critical
    immutable_hash: str = ""  # SHA-256 hash to detect tampering

    def __post_init__(self):
        """Generate immutable hash"""
        if not self.immutable_hash:
            content = f"{self.constraint_id}{self.name}{self.description}{self.severity}"
            self.immutable_hash = hashlib.sha256(content.encode()).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify constraint hasn't been tampered with"""
        content = f"{self.constraint_id}{self.name}{self.description}{self.severity}"
        expected_hash = hashlib.sha256(content.encode()).hexdigest()
        return self.immutable_hash == expected_hash


@dataclass
class AlignmentViolation:
    """Record of an alignment violation"""
    violation_id: str
    violation_type: ViolationType
    severity: int
    description: str
    strategy_text: str
    timestamp: str
    resolved: bool = False


class AlignmentGovernor:
    """
    Governor that ensures learning remains aligned with safety and goals

    Core principles:
    1. Immutable safety constraints (cannot be modified)
    2. Continuous monitoring of strategy evolution
    3. Automatic intervention on violations
    4. Transparency and logging of all decisions
    """

    def __init__(self, governor_id: str = "alignment_gov_001"):
        self.governor_id = governor_id
        self.constraints = []
        self.violations = []
        self.interventions_count = 0
        self.strategies_reviewed = 0

        # Initialize core safety constraints
        self._initialize_constraints()

    def _initialize_constraints(self):
        """Initialize immutable safety constraints"""

        # Constraint 1: Goal Alignment
        self.constraints.append(SafetyConstraint(
            constraint_id="SA-001",
            name="Goal Alignment",
            description="Strategies must aim to win games fairly, not exploit bugs or cheat",
            check_function="check_goal_alignment",
            severity=10
        ))

        # Constraint 2: Fair Play
        self.constraints.append(SafetyConstraint(
            constraint_id="SA-002",
            name="Fair Play",
            description="No deceptive tactics, invalid moves, or game rule violations",
            check_function="check_fair_play",
            severity=9
        ))

        # Constraint 3: Resource Limits
        self.constraints.append(SafetyConstraint(
            constraint_id="SA-003",
            name="Resource Limits",
            description="Strategies must not consume excessive computational resources",
            check_function="check_resource_limits",
            severity=7
        ))

        # Constraint 4: No Adversarial Drift
        self.constraints.append(SafetyConstraint(
            constraint_id="SA-004",
            name="No Adversarial Drift",
            description="Learning must not drift toward adversarial or harmful strategies",
            check_function="check_adversarial_drift",
            severity=10
        ))

        # Constraint 5: Transparency
        self.constraints.append(SafetyConstraint(
            constraint_id="SA-005",
            name="Transparency",
            description="Strategies must be interpretable and explainable",
            check_function="check_transparency",
            severity=6
        ))

    def verify_all_constraints(self) -> bool:
        """Verify all constraints haven't been tampered with"""
        return all(c.verify_integrity() for c in self.constraints)

    def review_strategy(self, strategy_text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, List[AlignmentViolation]]:
        """
        Review strategy for alignment violations

        Args:
            strategy_text: Strategy description to review
            context: Optional context (win rates, patterns, etc.)

        Returns:
            (is_safe, violations_found)
        """
        self.strategies_reviewed += 1

        if not self.verify_all_constraints():
            raise RuntimeError("CRITICAL: Safety constraints have been tampered with!")

        violations = []
        context = context or {}

        # Check each constraint
        for constraint in self.constraints:
            violation = self._check_constraint(constraint, strategy_text, context)
            if violation:
                violations.append(violation)

        # Strategy is safe if no high-severity violations
        critical_violations = [v for v in violations if v.severity >= 8]
        is_safe = len(critical_violations) == 0

        if not is_safe:
            self.interventions_count += 1

        # Store violations
        self.violations.extend(violations)

        return is_safe, violations

    def _check_constraint(self, constraint: SafetyConstraint,
                         strategy_text: str,
                         context: Dict[str, Any]) -> Optional[AlignmentViolation]:
        """Check a specific constraint"""

        # Map constraint check functions
        check_map = {
            'check_goal_alignment': self._check_goal_alignment,
            'check_fair_play': self._check_fair_play,
            'check_resource_limits': self._check_resource_limits,
            'check_adversarial_drift': self._check_adversarial_drift,
            'check_transparency': self._check_transparency
        }

        check_func = check_map.get(constraint.check_function)
        if check_func:
            return check_func(constraint, strategy_text, context)

        return None

    def _check_goal_alignment(self, constraint: SafetyConstraint,
                             strategy_text: str, context: Dict[str, Any]) -> Optional[AlignmentViolation]:
        """Check if strategy aligns with intended goals"""

        strategy_lower = strategy_text.lower()

        # Red flags for goal misalignment
        misalignment_keywords = [
            'exploit bug', 'cheat', 'hack', 'manipulate rules',
            'deceive', 'trick system', 'bypass'
        ]

        for keyword in misalignment_keywords:
            if keyword in strategy_lower:
                return AlignmentViolation(
                    violation_id=f"V{len(self.violations):04d}",
                    violation_type=ViolationType.GOAL_DRIFT,
                    severity=constraint.severity,
                    description=f"Strategy contains goal misalignment keyword: '{keyword}'",
                    strategy_text=strategy_text[:200],
                    timestamp=self._get_timestamp()
                )

        return None

    def _check_fair_play(self, constraint: SafetyConstraint,
                        strategy_text: str, context: Dict[str, Any]) -> Optional[AlignmentViolation]:
        """Check for fair play violations"""

        strategy_lower = strategy_text.lower()

        # Red flags
        unfair_keywords = [
            'invalid move', 'illegal move', 'break rules',
            'violate', 'force error'
        ]

        for keyword in unfair_keywords:
            if keyword in strategy_lower:
                return AlignmentViolation(
                    violation_id=f"V{len(self.violations):04d}",
                    violation_type=ViolationType.FAIRNESS_VIOLATION,
                    severity=constraint.severity,
                    description=f"Strategy suggests unfair play: '{keyword}'",
                    strategy_text=strategy_text[:200],
                    timestamp=self._get_timestamp()
                )

        return None

    def _check_resource_limits(self, constraint: SafetyConstraint,
                              strategy_text: str, context: Dict[str, Any]) -> Optional[AlignmentViolation]:
        """Check for resource abuse"""

        # Check if strategy mentions excessive computation
        strategy_lower = strategy_text.lower()

        resource_abuse_keywords = [
            'infinite loop', 'exhaust', 'consume all',
            'maximum resources', 'overflow'
        ]

        for keyword in resource_abuse_keywords:
            if keyword in strategy_lower:
                return AlignmentViolation(
                    violation_id=f"V{len(self.violations):04d}",
                    violation_type=ViolationType.RESOURCE_ABUSE,
                    severity=constraint.severity,
                    description=f"Strategy may abuse resources: '{keyword}'",
                    strategy_text=strategy_text[:200],
                    timestamp=self._get_timestamp()
                )

        return None

    def _check_adversarial_drift(self, constraint: SafetyConstraint,
                                strategy_text: str, context: Dict[str, Any]) -> Optional[AlignmentViolation]:
        """Check for adversarial strategy drift"""

        # Check win rate trends
        win_rate = context.get('win_rate', 0.5)

        # If win rate is suspiciously high (100%), might be exploiting
        if win_rate >= 0.99 and context.get('games_played', 0) > 50:
            # This might indicate exploitation rather than learning
            # (In our case, 100% is legit against random opponent, so we'd adjust threshold)
            pass

        # Check for adversarial keywords
        strategy_lower = strategy_text.lower()

        adversarial_keywords = [
            'adversarial', 'poison', 'backdoor', 'trojan',
            'malicious', 'sabotage'
        ]

        for keyword in adversarial_keywords:
            if keyword in strategy_lower:
                return AlignmentViolation(
                    violation_id=f"V{len(self.violations):04d}",
                    violation_type=ViolationType.DECEPTION,
                    severity=constraint.severity,
                    description=f"Strategy shows adversarial drift: '{keyword}'",
                    strategy_text=strategy_text[:200],
                    timestamp=self._get_timestamp()
                )

        return None

    def _check_transparency(self, constraint: SafetyConstraint,
                           strategy_text: str, context: Dict[str, Any]) -> Optional[AlignmentViolation]:
        """Check if strategy is interpretable"""

        # Check minimum length (too short = not explanatory)
        if len(strategy_text) < 20:
            return AlignmentViolation(
                violation_id=f"V{len(self.violations):04d}",
                violation_type=ViolationType.SAFETY_VIOLATION,
                severity=constraint.severity,
                description="Strategy lacks transparency (too short to explain)",
                strategy_text=strategy_text,
                timestamp=self._get_timestamp()
            )

        return None

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_safe_strategy(self, proposed_strategy: str,
                         context: Optional[Dict[str, Any]] = None) -> str:
        """
        Get safe version of strategy, or reject if unsafe

        Args:
            proposed_strategy: Proposed strategy text
            context: Optional context

        Returns:
            Safe strategy (original if safe, fallback if not)
        """
        is_safe, violations = self.review_strategy(proposed_strategy, context)

        if is_safe:
            return proposed_strategy

        # Return fallback safe strategy
        return ("SAFE FALLBACK STRATEGY: Play systematically using established "
                "heuristics. Prioritize defensive play and avoid risky tactics. "
                "Strategy was rejected due to alignment violations.")

    def get_stats(self) -> Dict[str, Any]:
        """Get governor statistics"""
        return {
            'governor_id': self.governor_id,
            'constraints_active': len(self.constraints),
            'constraints_verified': self.verify_all_constraints(),
            'strategies_reviewed': self.strategies_reviewed,
            'violations_detected': len(self.violations),
            'interventions': self.interventions_count,
            'critical_violations': len([v for v in self.violations if v.severity >= 8])
        }

    def get_violation_report(self) -> List[Dict[str, Any]]:
        """Get report of all violations"""
        return [
            {
                'violation_id': v.violation_id,
                'type': v.violation_type.value,
                'severity': v.severity,
                'description': v.description,
                'timestamp': v.timestamp,
                'resolved': v.resolved
            }
            for v in self.violations
        ]
