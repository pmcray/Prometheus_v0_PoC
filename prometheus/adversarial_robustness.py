"""
Adversarial Robustness Module — Prometheus v0.97 (WP3)

Implements three families of defence against adversarial attacks on the
Prometheus agent pipeline:

  1. PromptSanitizer / InjectionDetector
     — blocks prompt-injection attempts before LLM prompt construction.

  2. CodeInjectionGuard
     — extends MCSSupervisor's AST checks to catch obfuscated code-injection
       patterns (importlib, __import__, base64+exec, compile(), etc.).

  3. DataValidator
     — validates and optionally clips feature vectors fed to the value-
       learning (IRL) pipeline, preventing data-poisoning attacks.

Public API
----------
PromptSanitizer(max_length)
    .sanitize(text, raise_on_detect=False) → str
InjectionDetector()
    .is_injection(text) → bool
    .injection_score(text) → float ∈ [0, 1]

CodeInjectionGuard()
    .is_safe(code) → bool
    .is_safe_with_report(code) → (bool, List[dict])

DataValidator(n_features, clip_value)
    .validate_features(arr)             → None (raises on violation)
    .validate_and_clip(arr)             → np.ndarray
    .validate_pair(pref, unpref)        → None
    .validate_batch(arrays)             → None

sanitize_tool_name(name) → str   — strips path-traversal from tool names

AdversarialRobustnessError          — base exception for all violations
"""
from __future__ import annotations

import ast
import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AdversarialRobustnessError(ValueError):
    """Raised when an adversarial input is detected."""


# ---------------------------------------------------------------------------
# 1. Prompt Injection Defence
# ---------------------------------------------------------------------------

# Patterns that indicate prompt injection / jailbreak attempts
_INJECTION_PATTERNS: List[Tuple[str, float]] = [
    # Classic override phrases
    (r"ignore\s+(all\s+)?previous\s+instructions",       0.95),
    (r"disregard\s+(your\s+)?(safety|previous|prior)",    0.95),
    (r"forget\s+(all\s+)?previous\s+instructions",        0.90),
    (r"override\s+(your\s+)?(instructions|constitution)", 0.90),
    # Role-swap / jailbreak
    (r"\byou\s+are\s+now\s+(an?\s+)?(dan|unrestricted|evil|jailbroken)", 0.95),
    (r"\bact\s+as\s+(an?\s+)?(unrestricted|uncensored|evil)",    0.90),
    (r"\bpretend\s+(you\s+)?(have\s+no\s+)?restrictions",        0.85),
    (r"\bno\s+safety\s+rules",                                   0.85),
    (r"\bwithout\s+(any\s+)?restrictions",                       0.80),
    # System marker injection
    (r"\[SYSTEM\]",                                       0.90),
    (r"\[INST\]",                                         0.80),
    (r"<\|system\|>",                                     0.90),
    (r"<<<.*?>>>",                                        0.70),
    # Instruction boundary manipulation
    (r"---END OF (SPEC|PROMPT|CONTEXT)---",               0.85),
    (r"===END(SYSTEM|PROMPT)===",                         0.85),
    # Prompt leakage / exfiltration
    (r"(print|output|reveal|show)\s+(the\s+)?(full\s+)?system\s+prompt", 0.90),
    (r"(print|output|reveal)\s+(your\s+)?instructions",   0.85),
    # Explicit malicious intent
    (r"(delete|remove|destroy|wipe)\s+(all\s+)?files",    0.80),
    (r"(run|execute|eval)\s+(the\s+)?(above|following)\s+code", 0.80),
]

# Compiled patterns (case-insensitive)
_COMPILED_PATTERNS: List[Tuple[re.Pattern, float]] = [
    (re.compile(pat, re.IGNORECASE | re.DOTALL), score)
    for pat, score in _INJECTION_PATTERNS
]

# Markers that should be removed from inputs
_STRIP_MARKERS: List[str] = [
    "[SYSTEM]", "[USER]", "[INST]", "[/INST]",
    "<|system|>", "<|user|>", "<|assistant|>",
    "---END OF SPEC---", "---END OF PROMPT---",
    "===ENDSYSTEM===", "===ENDPROMPT===",
]

# Unicode categories that should be stripped (bidirectional, formatting)
_DANGEROUS_UNICODE_CATEGORIES = {"Cf", "Cs"}  # Format chars, surrogates


class InjectionDetector:
    """
    Detects prompt-injection payloads using pattern matching.

    Methods
    -------
    is_injection(text) → bool
        Returns True if any injection pattern matches.
    injection_score(text) → float
        Returns the maximum pattern confidence score, or 0.0 if none match.
    """

    def injection_score(self, text: str) -> float:
        """Return the maximum injection confidence score ∈ [0, 1]."""
        best = 0.0
        lowered = text.lower()
        for pattern, score in _COMPILED_PATTERNS:
            if pattern.search(lowered):
                best = max(best, score)
        return best

    def is_injection(self, text: str) -> bool:
        """Return True if the text contains injection patterns."""
        return self.injection_score(text) >= 0.5


class PromptSanitizer:
    """
    Sanitizes untrusted text before it is interpolated into LLM prompts.

    Steps applied (in order):
      1. Null-byte removal
      2. Dangerous Unicode character stripping (bidirectional overrides, etc.)
      3. Known injection marker removal
      4. Optional: raise AdversarialRobustnessError if injection detected
      5. Maximum length truncation

    Parameters
    ----------
    max_length : int
        Maximum allowed length after sanitization (default 8192).
    """

    def __init__(self, max_length: int = 8192):
        self.max_length  = max_length
        self._detector   = InjectionDetector()

    def sanitize(self, text: str, raise_on_detect: bool = False) -> str:
        """
        Sanitize ``text``.

        Parameters
        ----------
        text            : Raw untrusted string.
        raise_on_detect : If True, raise AdversarialRobustnessError when an
                          injection pattern is detected instead of stripping.
        Returns
        -------
        Sanitized string.

        Raises
        ------
        AdversarialRobustnessError
            If raise_on_detect=True and an injection pattern is found.
        """
        if not isinstance(text, str):
            text = str(text)

        # Step 1: null bytes
        text = text.replace("\x00", "")

        # Step 2: dangerous Unicode (bidirectional overrides, format chars)
        cleaned_chars = []
        for ch in text:
            cat = unicodedata.category(ch)
            if cat in _DANGEROUS_UNICODE_CATEGORIES:
                continue
            # Also strip specific known-dangerous code points
            cp = ord(ch)
            if cp in {0x202A, 0x202B, 0x202C, 0x202D, 0x202E,  # bidi
                      0x2066, 0x2067, 0x2068, 0x2069,            # bidi isolate
                      0x200B, 0x200C, 0x200D,                    # zero-width
                      0xFEFF}:                                   # BOM
                continue
            cleaned_chars.append(ch)
        text = "".join(cleaned_chars)

        # Step 3: strip injection markers
        for marker in _STRIP_MARKERS:
            text = text.replace(marker, "")
            text = text.replace(marker.lower(), "")
            text = text.replace(marker.upper(), "")

        # Step 4: injection detection
        if self._detector.is_injection(text):
            if raise_on_detect:
                score = self._detector.injection_score(text)
                raise AdversarialRobustnessError(
                    f"Prompt injection detected (confidence={score:.2f}): "
                    f"{text[:80]!r}…"
                )
            # Otherwise strip the injecting sentences
            lines = text.splitlines()
            clean_lines = [
                line for line in lines
                if self._detector.injection_score(line) < 0.5
            ]
            text = "\n".join(clean_lines)

        # Step 5: max length
        if len(text) > self.max_length:
            logger.warning(
                "PromptSanitizer: input truncated from %d to %d chars.",
                len(text), self.max_length,
            )
            text = text[: self.max_length]

        return text


# ---------------------------------------------------------------------------
# 2. Code Injection Defence
# ---------------------------------------------------------------------------

# Modules that are not in MCSSupervisor's list but can bypass sandbox
_EXTENDED_FORBIDDEN_IMPORTS: frozenset = frozenset({
    "os", "subprocess", "socket", "requests", "urllib", "shutil",
    "pty", "platform", "ctypes", "pickle", "marshal",
    # Bypass routes
    "importlib", "importlib.util", "importlib.machinery",
    "builtins", "sys", "signal", "resource", "mmap",
    "multiprocessing", "threading", "concurrent",
    "tempfile", "io", "pathlib",
    "base64", "binascii", "codecs",
    "cffi", "ctypes",
})

# Forbidden callable names (extended)
_EXTENDED_FORBIDDEN_CALLS: frozenset = frozenset({
    "eval", "exec", "open", "compile",
    "getattr", "setattr", "delattr",
    "input", "breakpoint",
    "__import__",
    "vars", "dir", "globals", "locals",
    "type", "object",
})

# Forbidden attribute accesses that indicate obfuscated calls
_FORBIDDEN_ATTRIBUTE_PATTERNS: List[re.Pattern] = [
    re.compile(r"__import__"),
    re.compile(r"importlib\.import_module"),
    re.compile(r"__builtins__"),
    re.compile(r"getattr\s*\("),
    re.compile(r"base64\.b64decode"),
    re.compile(r"\.encode\s*\(\s*['\"]base64['\"]"),
]


class _ViolationCollector(ast.NodeVisitor):
    """AST visitor that collects all safety violations."""

    def __init__(self):
        self.violations: List[Dict[str, Any]] = []

    def _add(self, description: str, severity: int, lineno: int = 0) -> None:
        self.violations.append({
            "description": description,
            "severity":    severity,
            "lineno":      lineno,
        })

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            top = alias.name.split(".")[0]
            if top in _EXTENDED_FORBIDDEN_IMPORTS:
                self._add(
                    f"Forbidden import: '{alias.name}'",
                    severity=9,
                    lineno=node.lineno,
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = (node.module or "").split(".")[0]
        if module in _EXTENDED_FORBIDDEN_IMPORTS:
            self._add(
                f"Forbidden from-import: '{node.module}'",
                severity=9,
                lineno=node.lineno,
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Direct name call: exec(), eval(), open(), __import__() …
        if isinstance(node.func, ast.Name):
            if node.func.id in _EXTENDED_FORBIDDEN_CALLS:
                self._add(
                    f"Forbidden call: '{node.func.id}()'",
                    severity=9 if node.func.id in {"exec", "eval", "__import__"} else 7,
                    lineno=node.lineno,
                )
        # Attribute call: importlib.import_module(), getattr(…) via attr …
        elif isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in _EXTENDED_FORBIDDEN_CALLS:
                self._add(
                    f"Forbidden method call: '.{attr}()'",
                    severity=8,
                    lineno=node.lineno,
                )
            # importlib.import_module()
            if attr == "import_module":
                self._add(
                    "Forbidden importlib.import_module() call",
                    severity=9,
                    lineno=node.lineno,
                )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Accessing __builtins__ attribute
        if node.attr in {"__builtins__", "__globals__", "__code__", "__dict__"}:
            self._add(
                f"Access to sensitive dunder attribute: '{node.attr}'",
                severity=7,
                lineno=node.lineno,
            )
        self.generic_visit(node)


class CodeInjectionGuard:
    """
    Enhanced static code safety checker that extends MCSSupervisor's AST
    analysis with broader forbidden-import/call lists and obfuscation detection.

    Methods
    -------
    is_safe(code) → bool
    is_safe_with_report(code) → (bool, List[dict])
        Each dict has keys: description, severity, lineno.
    """

    def is_safe_with_report(
        self, code: str
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Analyse ``code`` and return (is_safe, violations).
        """
        if not code or not code.strip():
            return True, []

        # Parse
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return False, [{"description": f"Syntax error: {exc}",
                            "severity": 5, "lineno": 0}]

        # AST visitor
        visitor = _ViolationCollector()
        visitor.visit(tree)

        # Regex-based checks on the raw source (catches string-assembled names)
        for pattern in _FORBIDDEN_ATTRIBUTE_PATTERNS:
            if pattern.search(code):
                visitor._add(
                    f"Suspicious pattern in source: '{pattern.pattern}'",
                    severity=8,
                )

        is_safe = len(visitor.violations) == 0
        return is_safe, visitor.violations

    def is_safe(self, code: str) -> bool:
        safe, _ = self.is_safe_with_report(code)
        return safe


# ---------------------------------------------------------------------------
# 3. Data Poisoning Defence
# ---------------------------------------------------------------------------

class DataValidator:
    """
    Validates (and optionally clips) feature vectors before they enter the
    value-learning pipeline.

    Parameters
    ----------
    n_features  : Expected feature vector length.
    clip_value  : Absolute value threshold used by validate_and_clip().
                  Default 1e6.
    """

    def __init__(self, n_features: int, clip_value: float = 1e6):
        self.n_features = n_features
        self.clip_value = clip_value

    def validate_features(self, arr: np.ndarray) -> None:
        """
        Check that *arr* is a 1-D finite array of the expected length.

        Raises
        ------
        AdversarialRobustnessError  on any violation.
        """
        arr = np.asarray(arr)

        # Shape
        if arr.ndim != 1:
            raise AdversarialRobustnessError(
                f"Feature dimension mismatch: expected 1-D array, got shape {arr.shape}."
            )
        if arr.shape[0] != self.n_features:
            raise AdversarialRobustnessError(
                f"Feature dimension mismatch: expected {self.n_features} features, "
                f"got {arr.shape[0]}."
            )

        # NaN
        if np.any(np.isnan(arr)):
            raise AdversarialRobustnessError(
                "NaN detected in feature vector — possible data-poisoning attack."
            )

        # Inf
        if np.any(np.isinf(arr)):
            raise AdversarialRobustnessError(
                "Inf / -Inf detected in feature vector — possible data-poisoning attack."
            )

        # Extreme magnitude (> clip_value)
        if np.any(np.abs(arr) > self.clip_value):
            raise AdversarialRobustnessError(
                f"Feature values exceed clip_value={self.clip_value:.1e}: "
                f"max |x| = {np.max(np.abs(arr)):.3e} — possible gradient attack."
            )

    def validate_and_clip(self, arr: np.ndarray) -> np.ndarray:
        """
        Validate shape and finiteness, then clip values to [-clip_value, clip_value].
        Returns the clipped array.  Does NOT raise on extreme magnitudes.
        """
        arr = np.asarray(arr, dtype=float)

        if arr.ndim != 1:
            raise AdversarialRobustnessError(
                f"Feature dimension mismatch: expected 1-D array, got shape {arr.shape}."
            )
        if arr.shape[0] != self.n_features:
            raise AdversarialRobustnessError(
                f"Feature dimension mismatch: expected {self.n_features}, got {arr.shape[0]}."
            )
        if np.any(np.isnan(arr)):
            raise AdversarialRobustnessError("NaN in feature vector.")
        if np.any(np.isinf(arr)):
            raise AdversarialRobustnessError("Inf in feature vector.")

        return np.clip(arr, -self.clip_value, self.clip_value)

    def validate_pair(
        self,
        preferred: np.ndarray,
        unpreferred: np.ndarray,
    ) -> None:
        """Validate a (preferred, unpreferred) preference pair."""
        self.validate_features(preferred)
        self.validate_features(unpreferred)

    def validate_batch(self, arrays: List[np.ndarray]) -> None:
        """Validate a list of feature vectors."""
        for i, arr in enumerate(arrays):
            try:
                self.validate_features(arr)
            except AdversarialRobustnessError as exc:
                raise AdversarialRobustnessError(
                    f"Batch validation failed at index {i}: {exc}"
                ) from exc


# ---------------------------------------------------------------------------
# Utility: safe tool-name extraction
# ---------------------------------------------------------------------------

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_]")


def sanitize_tool_name(name: str) -> str:
    """
    Return a safe filename component from a tool name extracted from user input.

    Strips:
      - path separators (/ \\)
      - shell metacharacters (; | & $ ` etc.)
      - path-traversal sequences (..)
      - all non-alphanumeric/underscore characters

    Parameters
    ----------
    name : Raw tool name (possibly adversarial).

    Returns
    -------
    Alphanumeric+underscore-only string, never empty (fallback: 'tool').
    """
    # Remove any directory prefix
    name = name.replace("\\", "/").split("/")[-1]
    # Strip path traversal
    name = name.replace("..", "")
    # Keep only safe characters
    name = _SAFE_NAME_RE.sub("", name)
    return name if name else "tool"
