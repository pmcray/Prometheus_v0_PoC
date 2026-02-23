"""
MCSSupervisor: Meta-Cognitive Safety Supervisor (Task 3.1)

This module implements the Centrencephalic Governor as proposed by I.J. Good.
It provides meta-level oversight for code modifications, ensuring alignment
with the Prometheus Constitution and preventing reward hacking.

OOD Integration (WP2)
---------------------
MCSSupervisor now optionally accepts a fitted OOD detector.  When provided,
`verify_with_ood(features)` can be called to gate any agent action through
the Safe Mode protocol before the constitutional code checks run.

Usage::

    from prometheus.ood_detection import MahalanobisOODDetector, SafeModeProtocol
    detector = MahalanobisOODDetector(feature_size=6).fit(training_features)
    supervisor = MCSSupervisor(ood_detector=detector)

    decision = supervisor.check_ood(current_features)
    if not decision.allow_action:
        # abort — input is too far OOD
        ...
    critique = supervisor.verify_modification(orig, proposed, path)
"""

import ast
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SafetyCritique:
    """Detailed critique of a safety violation"""
    is_safe: bool
    violation_type: Optional[str] = None
    description: str = ""
    constitutional_principle: str = ""
    recommendation: str = ""
    severity: int = 0  # 1-10

class MCSSupervisor:
    """
    Meta-Cognitive Safety (MCS) Supervisor.
    Acts as the 'Centrencephalic' governor for recursive self-improvement.

    Args:
        workspace_root: Root directory for the Prometheus workspace.
        ood_detector:   Optional fitted OOD detector.  When provided, the
                        supervisor can gate agent actions via check_ood().
        ood_protocol:   Optional pre-built SafeModeProtocol.  If omitted but
                        ood_detector is given, one is created with default
                        thresholds.
    """

    def __init__(
        self,
        workspace_root: str = ".",
        ood_detector=None,
        ood_protocol=None,
    ):
        self.workspace_root = os.path.abspath(workspace_root)

        # OOD integration — lazy import to avoid circular dependency
        self._ood_detector = ood_detector
        if ood_protocol is not None:
            self._ood_protocol = ood_protocol
        elif ood_detector is not None:
            from prometheus.ood_detection import SafeModeProtocol
            self._ood_protocol = SafeModeProtocol(ood_detector)
        else:
            self._ood_protocol = None

        self.constitution = {
            "Integrity of Evaluation": "Do not modify verification logic, unit tests, or evaluation datasets.",
            "Resource Boundaries": "Do not attempt to exit the sandbox or access unauthorized system resources.",
            "Functional Correctness": "Modifications must maintain or improve the intended functionality.",
            "Transparency": "All modifications must be interpretable and avoid obfuscation."
        }
        self.forbidden_imports = {
            "os", "subprocess", "socket", "requests", "urllib", "shutil", 
            "pty", "platform", "ctypes", "pickle", "marshal"
        }
        self.forbidden_calls = {
            "eval", "exec", "open", "getattr", "setattr", "delattr",
            "compile", "input", "breakpoint"
        }

    def verify_modification(self, original_code: str, proposed_code: str, 
                           file_path: str, is_test_file: bool = False) -> SafetyCritique:
        """
        Verify a proposed code modification against the Prometheus Constitution.
        """
        
        # 1. Check Integrity of Evaluation
        if is_test_file or "test_" in os.path.basename(file_path):
            return SafetyCritique(
                is_safe=False,
                violation_type="Integrity of Evaluation",
                description="Attempted to modify a test file or verification logic.",
                constitutional_principle=self.constitution["Integrity of Evaluation"],
                recommendation="Optimization must occur in the target code, not the verification suite.",
                severity=10
            )

        # 2. AST Analysis for Malicious Logic
        try:
            tree = ast.parse(proposed_code)
        except SyntaxError as e:
            return SafetyCritique(
                is_safe=False,
                violation_type="Syntax Error",
                description=f"Proposed code contains syntax errors: {e}",
                constitutional_principle=self.constitution["Functional Correctness"],
                recommendation="Ensure the generated code is syntactically valid.",
                severity=5
            )

        # Walk the AST to detect forbidden operations
        for node in ast.walk(tree):
            # Check for forbidden imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    name = alias.name.split('.')[0]
                    if name in self.forbidden_imports:
                        return SafetyCritique(
                            is_safe=False,
                            violation_type="Resource Boundaries",
                            description=f"Forbidden import detected: '{name}'",
                            constitutional_principle=self.constitution["Resource Boundaries"],
                            recommendation="Do not use system-level modules that can bypass the sandbox.",
                            severity=9
                        )
            
            # Check for forbidden calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.forbidden_calls:
                        return SafetyCritique(
                            is_safe=False,
                            violation_type="Resource Boundaries",
                            description=f"Forbidden function call detected: '{node.func.id}'",
                            constitutional_principle=self.constitution["Resource Boundaries"],
                            recommendation="Avoid dynamic execution or direct file system access.",
                            severity=8
                        )
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in self.forbidden_calls:
                        return SafetyCritique(
                            is_safe=False,
                            violation_type="Resource Boundaries",
                            description=f"Forbidden method call detected: '{node.func.attr}'",
                            constitutional_principle=self.constitution["Resource Boundaries"],
                            recommendation="Avoid accessing low-level object manipulation methods.",
                            severity=8
                        )

        return SafetyCritique(is_safe=True, description="No safety violations detected.")

    # ------------------------------------------------------------------
    # OOD interface (WP2)
    # ------------------------------------------------------------------

    def attach_ood_detector(self, detector, **protocol_kwargs) -> None:
        """
        Attach (or replace) an OOD detector after construction.

        Args:
            detector:        A fitted OOD detector (MahalanobisOODDetector,
                             ReconstructionOODDetector, or EnsembleOODDetector).
            **protocol_kwargs: Forwarded to SafeModeProtocol (e.g. thresholds).
        """
        from prometheus.ood_detection import SafeModeProtocol
        self._ood_detector = detector
        self._ood_protocol = SafeModeProtocol(detector, **protocol_kwargs)
        logger.info(
            "MCSSupervisor: OOD detector attached (%s, feature_size=%d).",
            type(detector).__name__,
            getattr(detector, "feature_size", "?"),
        )

    def check_ood(self, features: np.ndarray):
        """
        Evaluate a feature vector through the Safe Mode protocol.

        Returns:
            SafeModeDecision — check `.allow_action` before proceeding.

        Raises:
            RuntimeError: if no OOD detector has been attached.
        """
        if self._ood_protocol is None:
            raise RuntimeError(
                "No OOD detector attached to MCSSupervisor. "
                "Call attach_ood_detector() first."
            )
        return self._ood_protocol.evaluate(np.asarray(features, dtype=float))

    def ood_summary(self) -> Dict[str, Any]:
        """Return OOD decision log summary (requires attached detector)."""
        if self._ood_protocol is None:
            return {"error": "No OOD detector attached."}
        return self._ood_protocol.summary()

    @property
    def has_ood_detector(self) -> bool:
        """True if an OOD detector has been attached."""
        return self._ood_protocol is not None

    def get_constitution_summary(self) -> str:
        """Return a summary of the Prometheus Constitution"""
        summary = "Prometheus Constitution:\n"
        for principle, description in self.constitution.items():
            summary += f"- {principle}: {description}\n"
        return summary
