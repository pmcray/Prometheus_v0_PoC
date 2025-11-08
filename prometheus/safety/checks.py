"""
Prometheus Safety Checks

This module implements Gödelian safety checks for self-modification:
- Learning rate safety bounds
- Undecidability detection
- Modification validation
- Safety status tracking
"""

import numpy as np
from enum import Enum
from typing import Dict, Optional, Tuple, Any


class SafetyStatus(Enum):
    """
    Gödelian safety status for proposed modifications.

    Values:
        PROVABLY_SAFE: Modification is provably safe
        PROVABLY_UNSAFE: Modification is provably unsafe
        UNDECIDABLE: Cannot prove safe or unsafe (Gödelian limit)
    """
    PROVABLY_SAFE = "provably_safe"
    PROVABLY_UNSAFE = "provably_unsafe"
    UNDECIDABLE = "undecidable"


class SafetyBounds:
    """
    Safety bounds for various hyperparameters.

    Attributes:
        lr_min: Minimum safe learning rate
        lr_max: Maximum safe learning rate
        lr_max_ratio: Maximum ratio for learning rate change
        batch_size_min: Minimum safe batch size
        batch_size_max: Maximum safe batch size
    """

    def __init__(
        self,
        lr_min: float = 1e-6,
        lr_max: float = 0.1,
        lr_max_ratio: float = 3.0,
        batch_size_min: int = 8,
        batch_size_max: int = 512
    ):
        self.lr_min = lr_min
        self.lr_max = lr_max
        self.lr_max_ratio = lr_max_ratio
        self.batch_size_min = batch_size_min
        self.batch_size_max = batch_size_max


def check_learning_rate_safety(
    old_lr: float,
    new_lr: float,
    bounds: Optional[SafetyBounds] = None
) -> SafetyStatus:
    """
    Check if learning rate modification is safe.

    Args:
        old_lr: Current learning rate
        new_lr: Proposed new learning rate
        bounds: Optional safety bounds (uses defaults if None)

    Returns:
        SafetyStatus indicating if modification is safe

    Example:
        >>> status = check_learning_rate_safety(0.001, 0.002)
        >>> status == SafetyStatus.PROVABLY_SAFE
        True
    """
    if bounds is None:
        bounds = SafetyBounds()

    # PROVABLY_UNSAFE: Out of absolute bounds
    if new_lr > bounds.lr_max or new_lr < bounds.lr_min:
        return SafetyStatus.PROVABLY_UNSAFE

    # UNDECIDABLE: Large change ratio
    if old_lr > 0:
        ratio = new_lr / old_lr
        if ratio > bounds.lr_max_ratio or ratio < 1.0 / bounds.lr_max_ratio:
            return SafetyStatus.UNDECIDABLE

    # PROVABLY_SAFE: Within bounds and reasonable change
    return SafetyStatus.PROVABLY_SAFE


def check_batch_size_safety(
    new_batch_size: int,
    bounds: Optional[SafetyBounds] = None
) -> SafetyStatus:
    """
    Check if batch size modification is safe.

    Args:
        new_batch_size: Proposed new batch size
        bounds: Optional safety bounds

    Returns:
        SafetyStatus indicating if modification is safe
    """
    if bounds is None:
        bounds = SafetyBounds()

    # PROVABLY_UNSAFE: Out of bounds
    if new_batch_size < bounds.batch_size_min or new_batch_size > bounds.batch_size_max:
        return SafetyStatus.PROVABLY_UNSAFE

    # UNDECIDABLE: Not a power of 2 (unconventional)
    if not (new_batch_size & (new_batch_size - 1) == 0):  # Check if power of 2
        return SafetyStatus.UNDECIDABLE

    # PROVABLY_SAFE
    return SafetyStatus.PROVABLY_SAFE


def check_modification_safety(
    modification: Dict[str, Any],
    bounds: Optional[SafetyBounds] = None
) -> Tuple[SafetyStatus, str]:
    """
    Check if a proposed modification is safe.

    Args:
        modification: Dictionary describing modification
        bounds: Optional safety bounds

    Returns:
        Tuple of (SafetyStatus, reason string)

    Example:
        >>> modification = {
        ...     'type': 'learning_rate_change',
        ...     'old_lr': 0.001,
        ...     'new_lr': 0.002
        ... }
        >>> status, reason = check_modification_safety(modification)
    """
    if bounds is None:
        bounds = SafetyBounds()

    mod_type = modification.get('type', 'unknown')

    # Learning rate modifications
    if 'lr' in mod_type.lower() or 'learning_rate' in mod_type.lower():
        old_lr = modification.get('old_lr', 0.001)
        new_lr = modification.get('new_lr', old_lr)

        status = check_learning_rate_safety(old_lr, new_lr, bounds)

        if status == SafetyStatus.PROVABLY_SAFE:
            reason = f"Learning rate change {old_lr:.6f} → {new_lr:.6f} is within safe bounds"
        elif status == SafetyStatus.PROVABLY_UNSAFE:
            reason = f"Learning rate {new_lr:.6f} violates safety bounds [{bounds.lr_min}, {bounds.lr_max}]"
        else:  # UNDECIDABLE
            ratio = new_lr / old_lr if old_lr > 0 else float('inf')
            reason = f"Learning rate change ratio {ratio:.2f}x exceeds decidable threshold {bounds.lr_max_ratio}x"

        return status, reason

    # Batch size modifications
    elif 'batch' in mod_type.lower():
        new_batch_size = modification.get('new_batch_size', 32)

        status = check_batch_size_safety(new_batch_size, bounds)

        if status == SafetyStatus.PROVABLY_SAFE:
            reason = f"Batch size {new_batch_size} is within safe bounds"
        elif status == SafetyStatus.PROVABLY_UNSAFE:
            reason = f"Batch size {new_batch_size} violates bounds [{bounds.batch_size_min}, {bounds.batch_size_max}]"
        else:  # UNDECIDABLE
            reason = f"Batch size {new_batch_size} is not a power of 2 (unconventional)"

        return status, reason

    # Architecture modifications (always undecidable without formal proof)
    elif 'architecture' in mod_type.lower() or 'structure' in mod_type.lower():
        return SafetyStatus.UNDECIDABLE, "Architecture modifications require formal verification"

    # Unknown modification type
    else:
        return SafetyStatus.UNDECIDABLE, f"Unknown modification type: {mod_type}"


class GodelianSafetyGovernor:
    """
    Gödelian Safety Governor for self-modification decisions.

    Implements I.J. Good's "centrencephalic system" that prevents
    runaway self-modification using Gödelian incompleteness principles.

    Attributes:
        bounds: Safety bounds
        decision_history: List of safety decisions
        escalation_callback: Optional callback for undecidable cases
    """

    def __init__(
        self,
        bounds: Optional[SafetyBounds] = None,
        escalation_callback: Optional[callable] = None
    ):
        """
        Initialize Gödelian Safety Governor.

        Args:
            bounds: Safety bounds
            escalation_callback: Optional function to call for undecidable cases
        """
        self.bounds = bounds if bounds is not None else SafetyBounds()
        self.escalation_callback = escalation_callback
        self.decision_history = []

    def evaluate_modification(
        self,
        modification: Dict[str, Any],
        verbose: bool = True
    ) -> Tuple[SafetyStatus, str]:
        """
        Evaluate proposed modification for safety.

        Args:
            modification: Dictionary describing modification
            verbose: Print decision reasoning

        Returns:
            Tuple of (SafetyStatus, reason)
        """
        status, reason = check_modification_safety(modification, self.bounds)

        # Log decision
        self.decision_history.append({
            'modification': modification,
            'status': status,
            'reason': reason
        })

        if verbose:
            self._print_decision(modification, status, reason)

        # Handle undecidable case
        if status == SafetyStatus.UNDECIDABLE and self.escalation_callback:
            self.escalation_callback(modification, reason)

        return status, reason

    def _print_decision(
        self,
        modification: Dict[str, Any],
        status: SafetyStatus,
        reason: str
    ):
        """Print safety decision."""
        print(f"   🛡️  [SAFETY] Gödelian safety check...")

        if status == SafetyStatus.PROVABLY_SAFE:
            print(f"       → ✅ PROVABLY_SAFE: {reason}")
        elif status == SafetyStatus.PROVABLY_UNSAFE:
            print(f"       → ❌ PROVABLY_UNSAFE: {reason}")
        else:  # UNDECIDABLE
            print(f"       → ⚠️  UNDECIDABLE: {reason}")
            print(f"       → Escalating to human oversight (Gödelian jump)")

    def get_safety_statistics(self) -> Dict[str, any]:
        """
        Get statistics on safety decisions.

        Returns:
            Dictionary with safety statistics
        """
        if not self.decision_history:
            return {
                'total_decisions': 0,
                'safe_count': 0,
                'unsafe_count': 0,
                'undecidable_count': 0,
                'safe_percentage': 0.0,
                'unsafe_percentage': 0.0,
                'undecidable_percentage': 0.0
            }

        total = len(self.decision_history)
        safe_count = sum(1 for d in self.decision_history if d['status'] == SafetyStatus.PROVABLY_SAFE)
        unsafe_count = sum(1 for d in self.decision_history if d['status'] == SafetyStatus.PROVABLY_UNSAFE)
        undecidable_count = sum(1 for d in self.decision_history if d['status'] == SafetyStatus.UNDECIDABLE)

        return {
            'total_decisions': total,
            'safe_count': safe_count,
            'unsafe_count': unsafe_count,
            'undecidable_count': undecidable_count,
            'safe_percentage': (safe_count / total) * 100,
            'unsafe_percentage': (unsafe_count / total) * 100,
            'undecidable_percentage': (undecidable_count / total) * 100
        }

    def reset(self):
        """Reset decision history."""
        self.decision_history = []


def validate_godelian_safety(governor: GodelianSafetyGovernor) -> bool:
    """
    Validate that Gödelian safety governor is working correctly.

    Args:
        governor: Safety governor to validate

    Returns:
        True if validation passes

    Raises:
        AssertionError: If validation fails
    """
    # Test 1: Safe learning rate should pass
    mod1 = {'type': 'learning_rate', 'old_lr': 0.001, 'new_lr': 0.002}
    status1, _ = governor.evaluate_modification(mod1, verbose=False)
    assert status1 == SafetyStatus.PROVABLY_SAFE, "Safe LR modification should pass"

    # Test 2: Unsafe learning rate should fail
    mod2 = {'type': 'learning_rate', 'old_lr': 0.001, 'new_lr': 1.0}
    status2, _ = governor.evaluate_modification(mod2, verbose=False)
    assert status2 == SafetyStatus.PROVABLY_UNSAFE, "Unsafe LR modification should fail"

    # Test 3: Large change should be undecidable
    mod3 = {'type': 'learning_rate', 'old_lr': 0.001, 'new_lr': 0.005}
    status3, _ = governor.evaluate_modification(mod3, verbose=False)
    assert status3 == SafetyStatus.UNDECIDABLE, "Large LR change should be undecidable"

    # Test 4: Architecture modification should be undecidable
    mod4 = {'type': 'architecture', 'description': 'add layer'}
    status4, _ = governor.evaluate_modification(mod4, verbose=False)
    assert status4 == SafetyStatus.UNDECIDABLE, "Architecture mod should be undecidable"

    print("✅ Gödelian safety validation PASSED")
    return True
