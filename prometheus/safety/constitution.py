"""
prometheus/safety/constitution.py — Machine-Readable Prometheus Constitution (WP7)

Expresses the Prometheus safety constitution as a set of Z3 assertions that
the FormalVerifier can check against any proposed plan's AST-derived model.

Each constitutional principle maps to one or more Z3 constraints over the
abstract properties of a code fragment.  The verifier extracts these
properties (as Python integers/booleans) from the AST and feeds them to Z3.

Design
------
Properties extracted from the AST (all non-negative integers or booleans):

  n_forbidden_imports   — count of forbidden module imports
  n_forbidden_calls     — count of forbidden built-in calls
  n_obfuscation_calls   — count of obfuscation patterns (base64, importlib, …)
  n_file_writes         — count of open(…, 'w'/'wb'/'a') or os.path writes
  n_network_calls       — count of socket / requests / urllib usage
  n_exec_calls          — count of exec / eval / compile calls
  n_self_modifications  — count of writes to sys.modules, globals(), builtins
  has_infinite_loop     — 1 if a top-level `while True:` with no break, else 0
  n_assertion_deletes   — count of deletions of assertion / test functions
  code_length           — total character count of the proposed code

Public API
----------
ConstitutionalPrinciple   — dataclass describing one constraint
PrometheusConstitution    — collection of principles + Z3 assertion builder
CodeProperties            — dataclass of extracted properties
extract_properties(code)  → CodeProperties
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    import z3
    Z3_AVAILABLE = True
except ImportError:  # pragma: no cover
    Z3_AVAILABLE = False


# ---------------------------------------------------------------------------
# Code property extraction
# ---------------------------------------------------------------------------

#: Imports that violate Resource Boundaries
FORBIDDEN_IMPORTS: frozenset = frozenset({
    "os", "subprocess", "socket", "requests", "urllib", "shutil",
    "pty", "platform", "ctypes", "pickle", "marshal",
    "importlib", "builtins", "sys", "base64", "binascii",
    "tempfile", "pathlib", "atexit", "signal", "mmap",
})

#: Calls that violate Resource Boundaries
FORBIDDEN_CALLS: frozenset = frozenset({
    "eval", "exec", "open", "compile", "input", "breakpoint",
    "__import__", "vars", "dir", "globals", "locals",
})

#: Raw-source patterns indicating obfuscation
_OBFUSCATION_PATTERNS: List[re.Pattern] = [
    re.compile(r"importlib\.import_module"),
    re.compile(r"__import__\s*\("),
    re.compile(r"__builtins__"),
    re.compile(r"base64\.b64decode"),
    re.compile(r"binascii\."),
    re.compile(r"getattr\s*\("),
    re.compile(r"setattr\s*\("),
]

#: Patterns indicating network I/O
_NETWORK_PATTERNS: List[re.Pattern] = [
    re.compile(r"socket\s*\."),
    re.compile(r"requests\s*\."),
    re.compile(r"urllib\s*\."),
    re.compile(r"http\.client"),
    re.compile(r"ftplib"),
    re.compile(r"smtplib"),
]

#: Patterns indicating self-modification of the Python runtime
_SELF_MODIFICATION_PATTERNS: List[re.Pattern] = [
    re.compile(r"sys\.modules"),
    re.compile(r"globals\s*\(\s*\)"),
    re.compile(r"builtins\.__"),
    re.compile(r"__dict__\s*\["),
]

#: Max safe code length (characters)
MAX_CODE_LENGTH: int = 32_768


@dataclass
class CodeProperties:
    """
    Abstract properties of a code fragment, extracted from the AST
    and raw source text.  All integer fields are non-negative.
    """
    n_forbidden_imports:  int  = 0
    n_forbidden_calls:    int  = 0
    n_obfuscation_calls:  int  = 0
    n_file_writes:        int  = 0
    n_network_calls:      int  = 0
    n_exec_calls:         int  = 0
    n_self_modifications: int  = 0
    has_infinite_loop:    int  = 0   # 0 or 1
    n_assertion_deletes:  int  = 0
    code_length:          int  = 0
    syntax_error:         bool = False
    syntax_error_msg:     str  = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "n_forbidden_imports":  self.n_forbidden_imports,
            "n_forbidden_calls":    self.n_forbidden_calls,
            "n_obfuscation_calls":  self.n_obfuscation_calls,
            "n_file_writes":        self.n_file_writes,
            "n_network_calls":      self.n_network_calls,
            "n_exec_calls":         self.n_exec_calls,
            "n_self_modifications": self.n_self_modifications,
            "has_infinite_loop":    self.has_infinite_loop,
            "n_assertion_deletes":  self.n_assertion_deletes,
            "code_length":          self.code_length,
        }


def extract_properties(code: str) -> CodeProperties:
    """
    Parse *code* and return a :class:`CodeProperties` summary.

    The function never raises: parse errors are captured in
    ``CodeProperties.syntax_error``.
    """
    props = CodeProperties(code_length=len(code))

    # Raw-source regex scans (before AST — catches obfuscated forms)
    for pat in _OBFUSCATION_PATTERNS:
        props.n_obfuscation_calls += len(pat.findall(code))
    for pat in _NETWORK_PATTERNS:
        props.n_network_calls += len(pat.findall(code))
    for pat in _SELF_MODIFICATION_PATTERNS:
        props.n_self_modifications += len(pat.findall(code))

    # File-write detection (raw source)
    write_modes = re.findall(r"""open\s*\([^)]*['"][wWaAbB+]+['"]\s*\)""", code)
    props.n_file_writes += len(write_modes)

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        props.syntax_error     = True
        props.syntax_error_msg = str(exc)
        return props

    for node in ast.walk(tree):
        # Forbidden imports
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in FORBIDDEN_IMPORTS:
                    props.n_forbidden_imports += 1

        # Forbidden calls (both Name and Attribute forms)
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name and name in FORBIDDEN_CALLS:
                props.n_forbidden_calls += 1
            # Exec / eval specifically
            if name in {"exec", "eval", "compile"}:
                props.n_exec_calls += 1

        # Infinite-loop detection: `while True:` or `while 1:` with no break
        if isinstance(node, ast.While):
            cond = node.test
            is_const_true = isinstance(cond, ast.Constant) and cond.value in (True, 1)
            if is_const_true:
                # Check for a break statement anywhere in the while body
                has_break = any(
                    isinstance(n, ast.Break) for n in ast.walk(node)
                )
                if not has_break:
                    props.has_infinite_loop = 1

        # ------------------------------------------------------------------

        # Deletion of test/assertion functions
        if isinstance(node, ast.Delete):
            for target in node.targets:
                name = ""
                if isinstance(target, ast.Name):
                    name = target.id
                elif isinstance(target, ast.Attribute):
                    name = target.attr
                if "test" in name.lower() or "assert" in name.lower():
                    props.n_assertion_deletes += 1

    return props


# ---------------------------------------------------------------------------
# Constitutional principles
# ---------------------------------------------------------------------------

@dataclass
class ConstitutionalPrinciple:
    """
    One constitutional principle, expressed as both human-readable text
    and a callable that returns a Z3 BoolRef constraint.

    Parameters
    ----------
    name        : Short identifier (e.g. "Resource Boundaries").
    description : Human-readable statement of the principle.
    severity    : 1–10 (10 = most severe).
    constraint  : Callable (vars: Dict[str, z3.ArithRef | z3.BoolRef]) →
                  z3.BoolRef expressing the constraint.
    violation_msg : Template string with ``{props}`` placeholder.
    """
    name:          str
    description:   str
    severity:      int
    constraint:    Any   # Callable[[Dict[str, z3.ArithRef]], z3.BoolRef]
    violation_msg: str


def _make_principles() -> List[ConstitutionalPrinciple]:
    """Build the list of constitutional principles."""
    if not Z3_AVAILABLE:
        return []

    def _principle(name, description, severity, fn, msg):
        return ConstitutionalPrinciple(
            name=name, description=description,
            severity=severity, constraint=fn, violation_msg=msg,
        )

    return [
        _principle(
            "Resource Boundaries — Forbidden Imports",
            "Plans must not import forbidden modules (os, subprocess, socket, …).",
            severity=9,
            fn=lambda v: v["n_forbidden_imports"] == 0,
            msg="Forbidden module import detected (count={props.n_forbidden_imports}).",
        ),
        _principle(
            "Resource Boundaries — Forbidden Calls",
            "Plans must not call forbidden built-ins (eval, exec, open, …).",
            severity=9,
            fn=lambda v: v["n_forbidden_calls"] == 0,
            msg="Forbidden call detected (count={props.n_forbidden_calls}).",
        ),
        _principle(
            "Resource Boundaries — Obfuscation",
            "Plans must not use obfuscation techniques (importlib, base64, __import__, …).",
            severity=10,
            fn=lambda v: v["n_obfuscation_calls"] == 0,
            msg="Obfuscation pattern detected (count={props.n_obfuscation_calls}).",
        ),
        _principle(
            "Resource Boundaries — File Writes",
            "Plans must not write to the file system.",
            severity=8,
            fn=lambda v: v["n_file_writes"] == 0,
            msg="File-write detected (count={props.n_file_writes}).",
        ),
        _principle(
            "Resource Boundaries — Network Access",
            "Plans must not make network calls.",
            severity=8,
            fn=lambda v: v["n_network_calls"] == 0,
            msg="Network-access pattern detected (count={props.n_network_calls}).",
        ),
        _principle(
            "Resource Boundaries — Dynamic Execution",
            "Plans must not use exec, eval, or compile.",
            severity=10,
            fn=lambda v: v["n_exec_calls"] == 0,
            msg="Dynamic execution (exec/eval/compile) detected (count={props.n_exec_calls}).",
        ),
        _principle(
            "Resource Boundaries — Self-Modification",
            "Plans must not modify sys.modules, globals(), or builtins.",
            severity=10,
            fn=lambda v: v["n_self_modifications"] == 0,
            msg="Runtime self-modification detected (count={props.n_self_modifications}).",
        ),
        _principle(
            "Liveness — No Unbounded Loops",
            "Plans must not contain while-True loops without a break statement.",
            severity=6,
            fn=lambda v: v["has_infinite_loop"] == 0,
            msg="Unbounded loop (while True: with no break) detected.",
        ),
        _principle(
            "Integrity of Evaluation",
            "Plans must not delete test or assertion functions.",
            severity=10,
            fn=lambda v: v["n_assertion_deletes"] == 0,
            msg="Deletion of test/assertion symbol detected.",
        ),
        _principle(
            "Code Size",
            f"Plans must not exceed {MAX_CODE_LENGTH} characters.",
            severity=4,
            fn=lambda v: v["code_length"] <= MAX_CODE_LENGTH,
            msg=f"Code length exceeds {MAX_CODE_LENGTH} characters.",
        ),
    ]


class PrometheusConstitution:
    """
    Collection of all constitutional principles and Z3 assertion builder.

    Usage
    -----
    ::

        constitution = PrometheusConstitution()
        props = extract_properties(plan_code)
        solver, violations = constitution.check(props)
        is_safe = (solver == z3.sat and len(violations) == 0)
    """

    def __init__(self):
        self.principles: List[ConstitutionalPrinciple] = _make_principles()

    def check(self, props: CodeProperties) -> Tuple[Any, List[Dict[str, Any]]]:
        """
        Check *props* against all principles using Z3.

        Returns
        -------
        (z3_result, violations)

        z3_result  : ``z3.sat`` if ALL constraints satisfied,
                     ``z3.unsat`` if any violated,
                     ``z3.unknown`` if Z3 timed out.
        violations : List of dicts for each violated principle.
        """
        if not Z3_AVAILABLE:
            raise RuntimeError("z3-solver is not installed.")

        if props.syntax_error:
            return z3.unsat, [{
                "principle": "Syntax",
                "description": "Code has syntax errors.",
                "severity": 5,
                "msg": props.syntax_error_msg,
            }]

        # Build Z3 integer/bool variables from props dict
        prop_dict = props.as_dict()
        z3_vars: Dict[str, z3.ArithRef] = {
            k: z3.IntVal(v) for k, v in prop_dict.items()
        }

        violations: List[Dict[str, Any]] = []
        solver = z3.Solver()
        solver.set("timeout", 5_000)   # 5 s per principle

        all_ok = True
        for principle in self.principles:
            constraint = principle.constraint(z3_vars)
            solver.push()
            solver.add(z3.Not(constraint))
            result = solver.check()
            solver.pop()

            if result == z3.sat:
                # Constraint is violated (¬constraint is satisfiable)
                all_ok = False
                violations.append({
                    "principle":   principle.name,
                    "description": principle.description,
                    "severity":    principle.severity,
                    "msg":         principle.violation_msg.format(props=props),
                })

        final_result = z3.unsat if violations else z3.sat
        return final_result, violations

    def summary(self) -> str:
        """Return a human-readable list of all principles."""
        lines = ["Prometheus Constitution (Z3-verified):"]
        for p in self.principles:
            lines.append(f"  [{p.severity:2d}/10] {p.name}")
            lines.append(f"         {p.description}")
        return "\n".join(lines)
