#!/usr/bin/env python3
"""
P0: Immutable Safety Framework for Project Prometheus v0.19
Implements cryptographically sealed, unalterable safety constraints as required by Phase 1.

This module provides the foundational safety infrastructure that cannot be compromised
without detection, ensuring system integrity throughout all operations.
"""

import hashlib
import hmac
import json
import time
import logging
from typing import Dict, Any, Final, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

class SafetyViolationType(Enum):
    """Types of safety violations that can be detected"""
    INTEGRITY_COMPROMISE = "integrity_compromise"
    FORBIDDEN_ACTION = "forbidden_action"
    BUDGET_VIOLATION = "budget_violation"
    ITERATION_LIMIT_EXCEEDED = "iteration_limit_exceeded"
    UNAUTHORIZED_MODIFICATION = "unauthorized_modification"
    MALICIOUS_BEHAVIOR = "malicious_behavior"
    TAMPERING_DETECTED = "tampering_detected"

class SecurityError(Exception):
    """Critical security framework violation that cannot be recovered from"""
    def __init__(self, message: str, violation_type: SafetyViolationType):
        super().__init__(message)
        self.violation_type = violation_type
        self.timestamp = time.time()

@dataclass(frozen=True)
class ImmutableSafetyConstraints:
    """
    Cryptographically sealed safety parameters that cannot be altered without detection.
    
    These constraints represent the foundational safety limits that must be enforced
    throughout all system operations. Any attempt to modify these values will be
    detected through cryptographic signature verification.
    """
    
    # Core operational limits
    MAX_BUDGET: Final[int] = 10000
    MAX_ITERATIONS: Final[int] = 10
    MAX_SAFETY_VIOLATIONS: Final[int] = 3
    
    # Forbidden actions that must never be allowed
    FORBIDDEN_ACTIONS: Final[tuple] = (
        "modify_test",
        "alter_test", 
        "bypass_test",
        "change_test",
        "bypass_safety",
        "alter_constraints",
        "modify_safety",
        "override_safety",
        "disable_safety",
        "circumvent_safety"
    )
    
    # Actions requiring explicit human approval
    HUMAN_APPROVAL_REQUIRED: Final[tuple] = (
        "system_modification",
        "safety_override", 
        "constraint_adjustment",
        "framework_update",
        "emergency_action"
    )
    
    # Cryptographic parameters
    SIGNATURE_KEY: Final[bytes] = b"PROMETHEUS_SAFETY_SEAL_v1.0_IMMUTABLE"
    INTEGRITY_CHECK_INTERVAL: Final[int] = 100  # Check every 100 operations
    
    # Version and identification
    VERSION: Final[str] = "1.0.0"
    CREATION_TIMESTAMP: Final[float] = field(default_factory=time.time)
    
    def __post_init__(self):
        """Generate cryptographic signature for integrity verification"""
        # Create content hash excluding the signature itself
        content_dict = {
            k: v for k, v in self.__dict__.items() 
            if k not in ('_signature', '_integrity_counter')
        }
        
        # Convert to deterministic JSON representation
        content_json = json.dumps(content_dict, sort_keys=True, default=str)
        
        # Generate HMAC signature
        signature = hmac.new(
            key=self.SIGNATURE_KEY,
            msg=content_json.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Store signature using object.__setattr__ to bypass frozen dataclass restriction
        object.__setattr__(self, '_signature', signature)
        object.__setattr__(self, '_integrity_counter', 0)
        
        logger.info(f"🔒 Immutable Safety Constraints sealed with signature: {signature[:16]}...")
    
    def verify_integrity(self) -> bool:
        """
        Verify that safety constraints haven't been tampered with.
        
        Returns:
            bool: True if integrity is intact, False if compromised
        """
        try:
            # Recreate content hash
            content_dict = {
                k: v for k, v in self.__dict__.items() 
                if k not in ('_signature', '_integrity_counter')
            }
            
            content_json = json.dumps(content_dict, sort_keys=True, default=str)
            
            # Calculate expected signature
            expected_signature = hmac.new(
                key=self.SIGNATURE_KEY,
                msg=content_json.encode('utf-8'),
                digestmod=hashlib.sha256
            ).hexdigest()
            
            # Compare with stored signature
            stored_signature = getattr(self, '_signature', None)
            
            integrity_intact = (stored_signature == expected_signature)
            
            if not integrity_intact:
                logger.critical(f"🚨 INTEGRITY VIOLATION: Expected {expected_signature[:16]}..., got {stored_signature[:16] if stored_signature else 'None'}...")
            
            return integrity_intact
            
        except Exception as e:
            logger.critical(f"🚨 INTEGRITY CHECK FAILED: {e}")
            return False
    
    def increment_integrity_counter(self):
        """Increment counter for periodic integrity checks"""
        current_counter = getattr(self, '_integrity_counter', 0)
        object.__setattr__(self, '_integrity_counter', current_counter + 1)
    
    def should_perform_integrity_check(self) -> bool:
        """Determine if integrity check should be performed based on counter"""
        counter = getattr(self, '_integrity_counter', 0)
        return counter % self.INTEGRITY_CHECK_INTERVAL == 0

@dataclass
class SafetyViolation:
    """Record of a safety violation for audit purposes"""
    timestamp: float
    violation_type: SafetyViolationType
    description: str
    context: Dict[str, Any]
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    system_response: str
    
class EthicalConstraintLayer:
    """Ethical reasoning layer for action evaluation"""
    
    def __init__(self):
        self.ethical_principles = {
            "non_maleficence": "Do not cause harm to system integrity or security",
            "transparency": "All actions must be auditable and explainable", 
            "accountability": "System must maintain responsibility for all actions",
            "fairness": "Resource allocation must be equitable and justified",
            "privacy": "Respect data privacy and confidentiality"
        }
    
    def evaluate_ethical_compliance(self, action: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate whether an action complies with ethical constraints.
        
        Args:
            action: Description of the action to evaluate
            context: Context information for the action
            
        Returns:
            bool: True if ethically compliant, False otherwise
        """
        # Check for obvious malicious intent
        malicious_indicators = [
            "hack", "exploit", "bypass", "circumvent", "deceive",
            "manipulate", "corrupt", "damage", "destroy", "steal"
        ]
        
        action_lower = action.lower()
        
        for indicator in malicious_indicators:
            if indicator in action_lower:
                logger.warning(f"🚫 Ethical violation detected: malicious indicator '{indicator}' in action")
                return False
        
        # Check for transparency violations
        if "hidden" in action_lower or "secret" in action_lower:
            logger.warning(f"🚫 Ethical violation: action lacks transparency")
            return False
        
        # All checks passed
        return True

class HumanInTheLoopLayer:
    """Human oversight layer for critical actions"""
    
    def __init__(self):
        self.pending_approvals = {}
        self.approval_timeout = 300  # 5 minutes
    
    def request_approval(self, action: str, context: Dict[str, Any]) -> bool:
        """
        Request human approval for critical actions.
        
        In a production system, this would interface with a human operator.
        For the PoC, we simulate approval logic.
        
        Args:
            action: Action requiring approval
            context: Context for the approval request
            
        Returns:
            bool: True if approved, False if denied
        """
        # In production, this would send a request to human operators
        # For PoC, we implement conservative approval logic
        
        logger.info(f"👤 Human approval requested for: {action}")
        
        # Auto-deny any action that seems risky
        risky_keywords = ["override", "disable", "bypass", "modify_safety"]
        
        action_lower = action.lower()
        for keyword in risky_keywords:
            if keyword in action_lower:
                logger.warning(f"👤 Human approval DENIED: risky action '{action}'")
                return False
        
        # Auto-approve safe actions
        logger.info(f"👤 Human approval GRANTED: safe action '{action}'")
        return True

class AuditTrailLogger:
    """Comprehensive audit logging for all safety-related events"""
    
    def __init__(self, log_file: str = "safety_audit_trail.json"):
        self.log_file = Path(log_file)
        self.audit_entries = []
        
        # Ensure log file exists
        if not self.log_file.exists():
            self.log_file.write_text("[]")
    
    def log_approved_action(self, action: str, context: Dict[str, Any]):
        """Log an approved action"""
        entry = {
            "timestamp": time.time(),
            "type": "approved_action",
            "action": action,
            "context": context,
            "status": "APPROVED"
        }
        self._write_audit_entry(entry)
    
    def log_blocked_action(self, action: str, reason: str):
        """Log a blocked action"""
        entry = {
            "timestamp": time.time(),
            "type": "blocked_action", 
            "action": action,
            "reason": reason,
            "status": "BLOCKED"
        }
        self._write_audit_entry(entry)
        logger.warning(f"🛡️ Action blocked: {action} (Reason: {reason})")
    
    def log_safety_violation(self, violation: SafetyViolation):
        """Log a safety violation"""
        entry = {
            "timestamp": violation.timestamp,
            "type": "safety_violation",
            "violation_type": violation.violation_type.value,
            "description": violation.description,
            "context": violation.context,
            "severity": violation.severity,
            "system_response": violation.system_response,
            "status": "VIOLATION"
        }
        self._write_audit_entry(entry)
        logger.error(f"🚨 Safety violation logged: {violation.violation_type.value}")
    
    def log_integrity_check(self, result: bool, details: Dict[str, Any]):
        """Log integrity check results"""
        entry = {
            "timestamp": time.time(),
            "type": "integrity_check",
            "result": result,
            "details": details,
            "status": "VERIFIED" if result else "COMPROMISED"
        }
        self._write_audit_entry(entry)
    
    def _write_audit_entry(self, entry: Dict[str, Any]):
        """Write audit entry to persistent storage"""
        try:
            # Read existing entries
            existing_entries = json.loads(self.log_file.read_text())
            
            # Add new entry
            existing_entries.append(entry)
            
            # Write back to file
            self.log_file.write_text(json.dumps(existing_entries, indent=2, default=str))
            
            # Keep in-memory copy
            self.audit_entries.append(entry)
            
        except Exception as e:
            logger.error(f"Failed to write audit entry: {e}")
    
    def get_recent_violations(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get safety violations from the last N hours"""
        cutoff_time = time.time() - (hours * 3600)
        
        return [
            entry for entry in self.audit_entries
            if (entry.get("type") == "safety_violation" and 
                entry.get("timestamp", 0) > cutoff_time)
        ]

class ImmutableSafetyFramework:
    """
    Unalterable safety and control framework implementing Phase 1 requirements.
    
    This framework provides cryptographically verified safety constraints that cannot
    be bypassed or modified without detection. It implements multiple layers of 
    security and maintains comprehensive audit trails.
    """
    
    def __init__(self):
        # Initialize immutable constraints with cryptographic sealing
        self._constraints = ImmutableSafetyConstraints()
        
        # Initialize safety layers
        self.ethical_reasoner = EthicalConstraintLayer()
        self.human_oversight = HumanInTheLoopLayer()
        self.audit_logger = AuditTrailLogger()
        
        # Violation tracking
        self._violation_log: List[SafetyViolation] = []
        self._system_compromised = False
        self._operation_counter = 0
        
        # Verify initial integrity
        if not self._constraints.verify_integrity():
            raise SecurityError(
                "Safety framework integrity compromised during initialization!",
                SafetyViolationType.INTEGRITY_COMPROMISE
            )
        
        logger.info("🔒 Immutable Safety Framework initialized successfully")
        self.audit_logger.log_approved_action("framework_initialization", {
            "version": self._constraints.VERSION,
            "timestamp": self._constraints.CREATION_TIMESTAMP
        })
    
    def _verify_framework_integrity(self):
        """Perform continuous integrity verification"""
        self._operation_counter += 1
        self._constraints.increment_integrity_counter()
        
        # Perform periodic integrity checks
        if self._constraints.should_perform_integrity_check():
            integrity_result = self._constraints.verify_integrity()
            
            self.audit_logger.log_integrity_check(integrity_result, {
                "operation_counter": self._operation_counter,
                "check_interval": self._constraints.INTEGRITY_CHECK_INTERVAL
            })
            
            if not integrity_result:
                violation = SafetyViolation(
                    timestamp=time.time(),
                    violation_type=SafetyViolationType.TAMPERING_DETECTED,
                    description="Cryptographic integrity verification failed",
                    context={"operation_counter": self._operation_counter},
                    severity="CRITICAL",
                    system_response="SYSTEM_HALT"
                )
                
                self._log_security_violation(violation)
                self._system_compromised = True
                
                raise SecurityError(
                    "CRITICAL: Safety framework has been tampered with!",
                    SafetyViolationType.TAMPERING_DETECTED
                )
    
    def enforce_budget_constraint(self, requested_cost: int, current_budget: int) -> bool:
        """
        Enforce immutable budget constraints.
        
        Args:
            requested_cost: Cost of the requested operation
            current_budget: Current available budget
            
        Returns:
            bool: True if operation is within budget limits
            
        Raises:
            SecurityError: If framework integrity is compromised
        """
        self._verify_framework_integrity()
        
        # Check absolute budget limit
        if current_budget > self._constraints.MAX_BUDGET:
            violation = SafetyViolation(
                timestamp=time.time(),
                violation_type=SafetyViolationType.BUDGET_VIOLATION,
                description=f"Budget {current_budget} exceeds maximum {self._constraints.MAX_BUDGET}",
                context={"requested_cost": requested_cost, "current_budget": current_budget},
                severity="HIGH",
                system_response="OPERATION_DENIED"
            )
            
            self._log_security_violation(violation)
            return False
        
        # Check if operation would exceed budget
        if requested_cost > current_budget:
            logger.info(f"💰 Budget constraint enforced: {requested_cost} > {current_budget}")
            return False
        
        return True
    
    def enforce_iteration_limit(self, current_iteration: int) -> bool:
        """
        Enforce immutable iteration limits.
        
        Args:
            current_iteration: Current iteration number
            
        Returns:
            bool: True if within iteration limits
            
        Raises:
            SecurityError: If framework integrity is compromised
        """
        self._verify_framework_integrity()
        
        if current_iteration > self._constraints.MAX_ITERATIONS:
            violation = SafetyViolation(
                timestamp=time.time(),
                violation_type=SafetyViolationType.ITERATION_LIMIT_EXCEEDED,
                description=f"Iteration {current_iteration} exceeds maximum {self._constraints.MAX_ITERATIONS}",
                context={"current_iteration": current_iteration},
                severity="MEDIUM",
                system_response="ITERATION_HALT"
            )
            
            self._log_security_violation(violation)
            return False
        
        return True
    
    def check_forbidden_action(self, action: str) -> bool:
        """
        Check if action is forbidden by immutable constraints.
        
        Args:
            action: Description of the action to check
            
        Returns:
            bool: True if action is forbidden, False if allowed
            
        Raises:
            SecurityError: If framework integrity is compromised
        """
        self._verify_framework_integrity()
        
        action_lower = action.lower()
        
        for forbidden in self._constraints.FORBIDDEN_ACTIONS:
            if forbidden in action_lower:
                violation = SafetyViolation(
                    timestamp=time.time(),
                    violation_type=SafetyViolationType.FORBIDDEN_ACTION,
                    description=f"Forbidden action detected: '{forbidden}' in '{action}'",
                    context={"action": action, "forbidden_pattern": forbidden},
                    severity="HIGH",
                    system_response="ACTION_BLOCKED"
                )
                
                self._log_security_violation(violation)
                return True
        
        return False
    
    def validate_action(self, action: str, context: Dict[str, Any] = None) -> bool:
        """
        Multi-layer safety validation of an action.
        
        Args:
            action: Description of the action to validate
            context: Additional context for validation
            
        Returns:
            bool: True if action is safe and approved, False otherwise
            
        Raises:
            SecurityError: If critical safety violation detected
        """
        if context is None:
            context = {}
        
        # Layer 1: Framework integrity check
        self._verify_framework_integrity()
        
        # Layer 2: Check against immutable forbidden actions
        if self.check_forbidden_action(action):
            self.audit_logger.log_blocked_action(action, "forbidden_action")
            return False
        
        # Layer 3: Ethical reasoning validation
        if not self.ethical_reasoner.evaluate_ethical_compliance(action, context):
            self.audit_logger.log_blocked_action(action, "ethical_violation")
            return False
        
        # Layer 4: Human oversight for critical actions
        if self._requires_human_approval(action):
            if not self.human_oversight.request_approval(action, context):
                self.audit_logger.log_blocked_action(action, "human_approval_denied")
                return False
        
        # All validation layers passed
        self.audit_logger.log_approved_action(action, context)
        return True
    
    def _requires_human_approval(self, action: str) -> bool:
        """Check if action requires human approval"""
        action_lower = action.lower()
        
        for approval_required in self._constraints.HUMAN_APPROVAL_REQUIRED:
            if approval_required in action_lower:
                return True
        
        return False
    
    def _log_security_violation(self, violation: SafetyViolation):
        """Log security violation with appropriate response"""
        self._violation_log.append(violation)
        self.audit_logger.log_safety_violation(violation)
        
        # Check if we've exceeded maximum violations
        if len(self._violation_log) >= self._constraints.MAX_SAFETY_VIOLATIONS:
            self._system_compromised = True
            logger.critical(f"🚨 SYSTEM COMPROMISED: Maximum safety violations ({self._constraints.MAX_SAFETY_VIOLATIONS}) exceeded")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system safety status"""
        return {
            "framework_version": self._constraints.VERSION,
            "integrity_verified": self._constraints.verify_integrity(),
            "system_compromised": self._system_compromised,
            "violation_count": len(self._violation_log),
            "max_violations": self._constraints.MAX_SAFETY_VIOLATIONS,
            "operation_counter": self._operation_counter,
            "recent_violations": [
                {
                    "type": v.violation_type.value,
                    "severity": v.severity,
                    "timestamp": v.timestamp
                }
                for v in self._violation_log[-5:]  # Last 5 violations
            ]
        }
    
    def emergency_shutdown(self, reason: str):
        """Emergency shutdown with audit trail"""
        violation = SafetyViolation(
            timestamp=time.time(),
            violation_type=SafetyViolationType.UNAUTHORIZED_MODIFICATION,
            description=f"Emergency shutdown triggered: {reason}",
            context={"shutdown_reason": reason},
            severity="CRITICAL",
            system_response="EMERGENCY_SHUTDOWN"
        )
        
        self._log_security_violation(violation)
        self._system_compromised = True
        
        logger.critical(f"🚨 EMERGENCY SHUTDOWN: {reason}")
        
        raise SecurityError(
            f"Emergency shutdown triggered: {reason}",
            SafetyViolationType.UNAUTHORIZED_MODIFICATION
        )

# Testing and demonstration functions
def demonstrate_immutable_safety():
    """Demonstrate the immutable safety framework capabilities"""
    print("🔒 IMMUTABLE SAFETY FRAMEWORK DEMONSTRATION")
    print("=" * 60)
    
    try:
        # Initialize framework
        framework = ImmutableSafetyFramework()
        print("✅ Framework initialized successfully")
        
        # Test valid action
        result = framework.validate_action("optimize_code", {"target": "performance"})
        print(f"✅ Valid action approved: {result}")
        
        # Test forbidden action
        result = framework.validate_action("modify_test to always pass")
        print(f"❌ Forbidden action blocked: {not result}")
        
        # Test budget enforcement
        budget_ok = framework.enforce_budget_constraint(100, 1000)
        print(f"✅ Budget constraint (100/1000): {budget_ok}")
        
        budget_exceeded = framework.enforce_budget_constraint(2000, 1000)
        print(f"❌ Budget constraint (2000/1000): {not budget_exceeded}")
        
        # Test iteration limit
        iteration_ok = framework.enforce_iteration_limit(5)
        print(f"✅ Iteration limit (5/10): {iteration_ok}")
        
        iteration_exceeded = framework.enforce_iteration_limit(15)
        print(f"❌ Iteration limit (15/10): {not iteration_exceeded}")
        
        # Show system status
        status = framework.get_system_status()
        print(f"\n📊 System Status:")
        print(f"  Integrity: {'✅' if status['integrity_verified'] else '❌'}")
        print(f"  Violations: {status['violation_count']}/{status['max_violations']}")
        print(f"  Operations: {status['operation_counter']}")
        
        print("\n🎉 Demonstration completed successfully!")
        
    except SecurityError as e:
        print(f"🚨 Security Error: {e}")
        print(f"🚨 Violation Type: {e.violation_type.value}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Run demonstration
    demonstrate_immutable_safety()