"""
MCSSupervisor: Meta-Cognitive Safety Supervisor (Task 3.1)

This module implements the Centrencephalic Governor as proposed by I.J. Good.
It provides meta-level oversight for code modifications, ensuring alignment
with the Prometheus Constitution and preventing reward hacking.
"""

import ast
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

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
    """
    
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = os.path.abspath(workspace_root)
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

    def get_constitution_summary(self) -> str:
        """Return a summary of the Prometheus Constitution"""
        summary = "Prometheus Constitution:\n"
        for principle, description in self.constitution.items():
            summary += f"- {principle}: {description}\n"
        return summary
