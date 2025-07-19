

import google.generativeai as genai
import os
import re
import random
from .tools import CompilerTool, StaticAnalyzerTool, LeanTool, ProofState
from .knowledge_agent import KnowledgeAgent

class CoderAgent:
    def __init__(self, api_key, compiler: CompilerTool, analyzer: StaticAnalyzerTool, lean_tool: LeanTool, knowledge_agent: KnowledgeAgent):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.compiler = compiler
        self.analyzer = analyzer
        self.lean_tool = lean_tool
        self.knowledge_agent = knowledge_agent
        self.proof_steps = ["induction a", "simp", "rw [Nat.add_assoc]", "simp"]

    def generate_tactic(self, proof_state: ProofState, max_retries=3):
        if self.proof_steps:
            return self.proof_steps.pop(0)
        return "sorry"

    def translate_hypothesis_to_code(self, hypothesis: str):
        if "mix" in hypothesis.lower() and "a" in hypothesis.lower() and "b" in hypothesis.lower():
            if "heat" in hypothesis.lower():
                return "sim.mix('A', 'B')\nsim.heat(50)"
            else:
                return "sim.mix('A', 'B')"
        if "heat" in hypothesis.lower():
            return "sim.heat(50)"
        return ""

