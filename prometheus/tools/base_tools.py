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
    def __init__(self):
        self.step = 0

    def use(self, lean_code):
        logging.info("LeanTool: Checking Lean code (mocked).")
        if "sorry" in lean_code:
            return "Proof contains 'sorry'."
        if "theorem" in lean_code and "by" in lean_code:
            return None
        return "Invalid Lean code."


    def start_proof(self, theorem):
        logging.info("LeanTool: Starting proof (mocked).")
        self.step = 0
        proof_so_far = theorem + " := by\n"
        state_string = "1 goal\n⊢ a + b + c = a + (b + c)"
        return ProofState(state_string), proof_so_far

    def apply_tactic(self, proof_so_far, tactic):
        logging.info(f"LeanTool: Applying tactic '{tactic}' (mocked).")
        self.step += 1
        new_proof = proof_so_far + "  " + tactic + ",\n"
        
        if self.step == 1:
            state_string = "2 goals\ncase a:0\n⊢ 0 + b + c = 0 + (b + c)\n\ncase a:Nat.succ a\n⊢ a.succ + b + c = a.succ + (b + c)"
        elif self.step == 2:
            state_string = "1 goal\ncase a:Nat.succ a\n⊢ a.succ + b + c = a.succ + (b + c)"
        elif self.step >= 3:
            state_string = "goals accomplished"
            
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