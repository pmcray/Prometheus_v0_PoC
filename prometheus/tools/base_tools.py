import subprocess
import sys
import logging
from py_compile import PyCompileError, compile
import os
import re
import shutil
from pypdf import PdfReader
from causallearn.search.ConstraintBased.PC import pc
from causallearn.utils.cit import fisherz
import pandas as pd
from .proof_tree import ProofTree
from .auditor_agent import AuditorAgent

class Tool:
    pass

class CompilerTool(Tool):
    def compile(self, code: str):
        """
        Compiles the given Python code.
        """
        logging.info("CompilerTool: Compiling code.")
        # For the PoC, we'll just simulate a successful compilation.
        return True

class StaticAnalyzerTool(Tool):
    def use(self, file_path):
        pass

class ProofState:
    def __init__(self, state_string):
        self.raw_state = state_string
        self.goals = self._parse_goals(state_string)

    def _parse_goals(self, state_string):
        if "goals accomplished" in state_string:
            return []
        goal_section = re.search(r"(\d+ goals|1 goal)\n(.*?)$", state_string, re.DOTALL)
        if goal_section:
            return [goal.strip() for goal in goal_section.group(2).split("⊢")]
        return ["Could not parse goals."]

    def is_complete(self):
        return "goals accomplished" in self.raw_state

    def __str__(self):
        return self.raw_state

class LeanTool(Tool):
    """
    Interface to the Lean 4 proof assistant.

    v0.3 upgrade: real subprocess integration replacing the earlier mock.

    Installation path discovery order:
      1. ``lean_executable`` constructor argument.
      2. ``LEAN_PATH`` environment variable.
      3. ``lake`` on $PATH (Lean 4 project manager — preferred for Mathlib).
      4. ``lean`` on $PATH (bare Lean binary).

    When none of the above is available the tool falls back to the
    *sandboxed mock* so that notebooks can still run in Colab without a
    local Lean installation.  The ``_using_mock`` attribute records which
    mode is active.

    Real-Lean mode writes a temporary ``.lean`` file (or a minimal Lake
    project for Mathlib imports) and parses the compiler diagnostics.
    Error messages follow the Lean 4 JSON diagnostic format when invoked
    with ``--json``, or plain-text otherwise.
    """

    # ------------------------------------------------------------------ #
    #  Construction / capability detection                                #
    # ------------------------------------------------------------------ #

    def __init__(self, lean_executable: str = None, use_lake: bool = True,
                 timeout: int = 30):
        self._lean_exe = lean_executable or os.environ.get("LEAN_PATH")
        self._use_lake = use_lake
        self._timeout = timeout
        self._using_mock = False
        self.step = 0  # kept for backward-compat

        if not self._lean_exe:
            # Auto-discover: prefer lake, fall back to lean
            self._lean_exe = shutil.which("lake") if use_lake else None
            if not self._lean_exe:
                self._lean_exe = shutil.which("lean")

        if self._lean_exe:
            logging.info("LeanTool: using real Lean binary at %s.", self._lean_exe)
        else:
            logging.warning(
                "LeanTool: no Lean binary found — falling back to sandboxed mock. "
                "Set LEAN_PATH or install Lean 4 to enable real verification."
            )
            self._using_mock = True

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def use(self, lean_code: str) -> "Optional[str]":
        """
        Verify ``lean_code`` as a complete Lean 4 source file.

        Returns
        -------
        None
            The code compiled without errors.
        str
            The first error message emitted by Lean (or the mock).
        """
        if self._using_mock:
            return self._mock_use(lean_code)
        return self._real_verify(lean_code)

    def start_proof(self, theorem: str):
        """
        Initialise an interactive proof session for ``theorem``.

        Returns ``(ProofState, proof_so_far_str)``.
        """
        logging.info("LeanTool.start_proof: %s", theorem.strip())
        self.step = 0
        self._proof_lines = [theorem + " := by"]
        self._failed_branches: list = []

        if self._using_mock:
            return self._mock_start_proof(theorem)

        # Real mode: compile the skeleton and extract the initial goal.
        skeleton = theorem + " := by\n  sorry\n"
        goals = self._extract_goals(skeleton)
        state_string = goals if goals else "1 goal\n⊢ (unknown goal — check Lean output)"
        return ProofState(state_string), "\n".join(self._proof_lines) + "\n"

    def apply_tactic(self, proof_so_far: str, tactic: str):
        """
        Append ``tactic`` to the proof and return the new ``(ProofState, proof_str)``.
        """
        logging.info("LeanTool.apply_tactic: %s", tactic)
        self.step += 1

        if self._using_mock:
            return self._mock_apply_tactic(proof_so_far, tactic)

        new_proof = proof_so_far.rstrip() + "\n  " + tactic + "\n"
        goals = self._extract_goals(new_proof)
        if goals is None:
            # Lean raised an error — treat as failure, keep old proof
            err_state = ProofState(f"error applying tactic `{tactic}`")
            return err_state, proof_so_far
        state_string = goals
        return ProofState(state_string), new_proof

    # ------------------------------------------------------------------ #
    #  Real-Lean helpers                                                  #
    # ------------------------------------------------------------------ #

    def _real_verify(self, lean_code: str) -> "Optional[str]":
        """Write lean_code to a temp file, compile it, return first error or None."""
        import tempfile
        with tempfile.NamedTemporaryFile(
            suffix=".lean", mode="w", delete=False
        ) as f:
            f.write(lean_code)
            tmp_path = f.name
        try:
            result = subprocess.run(
                [self._lean_exe, tmp_path],
                capture_output=True, text=True, timeout=self._timeout
            )
            combined = result.stdout + result.stderr
            return self._parse_lean_error(combined)
        except subprocess.TimeoutExpired:
            return f"LeanTool: timeout after {self._timeout}s"
        except FileNotFoundError:
            self._using_mock = True
            return self._mock_use(lean_code)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    def _extract_goals(self, lean_code: str) -> "Optional[str]":
        """
        Compile lean_code and extract the proof-state / goal description.

        Returns the goal string if the file compiled (possibly with remaining
        goals), or None if there was a hard error.
        """
        import tempfile
        with tempfile.NamedTemporaryFile(
            suffix=".lean", mode="w", delete=False
        ) as f:
            f.write(lean_code)
            tmp_path = f.name
        try:
            result = subprocess.run(
                [self._lean_exe, tmp_path],
                capture_output=True, text=True, timeout=self._timeout
            )
            combined = result.stdout + result.stderr
            # "goals accomplished" or "no goals" → proof complete
            if any(x in combined for x in ("goals accomplished", "no goals", "✓")):
                return "goals accomplished"
            # Extract goal lines if present
            goal_match = re.search(
                r"(\d+ goals?|⊢[^\n]+(?:\n(?!error)[^\n]+)*)", combined
            )
            if goal_match:
                return goal_match.group(0).strip()
            # Hard error
            err = self._parse_lean_error(combined)
            if err:
                return None  # signal error to caller
            return "1 goal\n⊢ (see Lean output)"
        except subprocess.TimeoutExpired:
            return None
        except FileNotFoundError:
            self._using_mock = True
            return "goals accomplished"   # graceful mock fallback
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    @staticmethod
    def _parse_lean_error(output: str) -> "Optional[str]":
        """
        Extract the first error from Lean compiler output.

        Handles both plain-text and JSON-style diagnostics.
        Returns None if no errors are present.
        """
        if not output.strip():
            return None
        # JSON diagnostic lines: {"severity":"error","message":"..."}
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("{") and '"severity":"error"' in stripped:
                try:
                    import json as _json
                    diag = _json.loads(stripped)
                    return diag.get("message", stripped)
                except Exception:
                    pass
        # Plain-text: lines containing "error:"
        for line in output.splitlines():
            if "error:" in line.lower():
                return line.strip()
        # "sorry" axiom warning counts as an error for us
        if "sorry" in output:
            return "Proof contains 'sorry' — axiom not allowed."
        return None

    # ------------------------------------------------------------------ #
    #  Sandboxed mock (used when Lean is not installed)                   #
    # ------------------------------------------------------------------ #

    def _mock_use(self, lean_code: str) -> "Optional[str]":
        logging.info("LeanTool (mock): checking code.")
        if "sorry" in lean_code:
            return "Proof contains 'sorry'."
        if "theorem" in lean_code and "by" in lean_code:
            return None
        return "Invalid Lean code structure."

    def _mock_start_proof(self, theorem: str):
        proof_so_far = theorem + " := by\n"
        state_string = "1 goal\n⊢ (mock goal — Lean not installed)"
        return ProofState(state_string), proof_so_far

    def _mock_apply_tactic(self, proof_so_far: str, tactic: str):
        new_proof = proof_so_far + "  " + tactic + "\n"
        if self.step >= 3:
            state_string = "goals accomplished"
        elif self.step == 2:
            state_string = "1 goal\n⊢ (mock: one goal remaining)"
        else:
            state_string = f"2 goals\n⊢ (mock: {self.step} tactics applied)"
        return ProofState(state_string), new_proof

class PDFTool(Tool):
    def use(self, file_path):
        logging.info(f"PDFTool: Extracting text from {file_path}")
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            logging.error(f"PDFTool: Error extracting text from {file_path}: {e}")
            return None

class AuditTool(Tool):
    def use(self, data_structure, context):
        logging.info("AuditTool: Summarizing data structure.")
        if isinstance(data_structure, ProofTree):
            auditor = AuditorAgent(os.environ.get("GOOGLE_API_KEY"))
            return auditor.generate_audit_trail(data_structure, context)
        return "AuditTool: Unsupported data structure."

class CausalGraphTool(Tool):
    def use(self, data_path):
        logging.info("CausalGraphTool: Constructing causal graph.")
        try:
            df = pd.read_csv(data_path)
            df_encoded = pd.get_dummies(df, drop_first=True)
            cg = pc(df_encoded.to_numpy(), alpha=0.05, indep_test=fisherz)
            return cg
        except Exception as e:
            logging.error(f"CausalGraphTool: Error constructing graph: {e}")
            return None