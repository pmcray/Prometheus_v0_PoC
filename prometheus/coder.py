from prometheus.llm_backend import get_llm_backend
import os
import re
import random

from prometheus.safety.mcs_supervisor import MCSSupervisor
from prometheus.adversarial_robustness import PromptSanitizer, sanitize_tool_name

class CoderAgent:
    def __init__(self, api_key, compiler, analyzer, lean_tool, knowledge_agent, mcs_supervisor=None, model_name=None):
        self.backend = get_llm_backend(model_name=model_name)
        self.compiler = compiler
        self.analyzer = analyzer
        self.lean_tool = lean_tool
        self.knowledge_agent = knowledge_agent
        self.mcs_supervisor = mcs_supervisor or MCSSupervisor()
        self.sanitizer = PromptSanitizer()

    def synthesize_tool(self, specification: str):
        """
        Synthesizes the Python code for a new tool based on a specification.
        """
        print("CoderAgent: Synthesizing new tool.")
        
        # Sanitize specification to prevent prompt injection
        clean_spec = self.sanitizer.sanitize(specification)
        
        prompt = f"""
        You are an expert Python programmer.
        Based on the following specification, generate the complete, syntactically correct Python code for the new tool class.
        The new tool should be a class with a no-argument constructor, a `run_experiment` method that takes a list of operations as input, and a `mix` method.
        
        Specification:
        {clean_spec}
        """
        response_text = self.backend.generate(prompt)
        code = response_text.strip().replace("```python", "").replace("```", "")
        
        # Safety Check
        raw_tool_name = self._extract_tool_name(specification)
        tool_name = sanitize_tool_name(raw_tool_name)
        file_path = f"prometheus/tools/{tool_name.lower()}.py"
        
        critique = self.mcs_supervisor.verify_modification("", code, file_path)
        if not critique.is_safe:
            print(f"CoderAgent: SAFETY VIOLATION during synthesis! {critique.violation_type}: {critique.description}")
            return None

        # Save the new tool to a file
        with open(file_path, "w") as f:
            f.write(code)
            
        print(f"CoderAgent: Synthesized tool and saved to {file_path}")
        return file_path

    def _extract_tool_name(self, specification: str):
        # A simple regex to extract the tool name from the specification
        match = re.search(r"`(.*?)`", specification)
        if match:
            return match.group(1)
        return "new_tool"

    def synthesize_agent(self, proposal: str):
        pass

    def _clean_code(self, code):
        """Helper method to clean generated code."""
        code_blocks = re.findall(r"```(python|lean)\n(.*?)\n```", code, re.DOTALL)
        if code_blocks:
            return "\n".join([block[1] for block in code_blocks])
        lines = code.strip().split('\n')
        cleaned_lines = []
        in_code = False
        for line in lines:
            if line.strip().startswith('def ') or line.strip().startswith('import ') or line.strip().startswith('theorem'):
                in_code = True
            if in_code:
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    def prove(self, theorem, max_retries=3):
        """Attempts to generate a Lean proof for the given theorem."""
        print(f"CoderAgent: Attempting to prove: {theorem}")
        error_feedback = ""
        for i in range(max_retries):
            print(f"CoderAgent: Proof attempt {i+1}")
            prompt = f"""
            Your task is to write a proof for the following theorem in the Lean language.
            {error_feedback}

            Theorem:
            ```lean
            {theorem}
            ```

            Please provide only the complete, valid Lean code for the proof.
            """
            response_text = self.backend.generate(prompt)
            proof = self._clean_code(response_text)

            lean_error = self.lean_tool.use(proof)
            if not lean_error:
                print("CoderAgent: Proof successful and verified.")
                return proof
            else:
                error_feedback = f"The previous attempt failed with the following error:\n{lean_error}\nPlease try again."

        print("CoderAgent: Failed to generate a valid proof after multiple retries.")
        return None

    def code(self, file_path, instruction, max_retries=3):
        """Generates code for a file based on instructions."""
        print(f"CoderAgent: Received instruction for {file_path}")
        # Sanitize instruction
        clean_instruction = self.sanitizer.sanitize(instruction)
        
        with open(file_path, 'r') as f:
            original_code = f.read()
        return self.refactor(original_code, clean_instruction, max_retries)

    def refactor(self, code, instruction, max_retries=3):
        """Refactors code based on instructions with verification and safety oversight."""
        current_code = code
        # Sanitize instruction
        clean_instruction = self.sanitizer.sanitize(instruction)
        
        for i in range(max_retries):
            print(f"CoderAgent: Refactoring attempt {i+1}")
            prompt = f"Instruction: {clean_instruction}\n\n```python\n{current_code}\n```"
            response_text = self.backend.generate(prompt)
            new_code = self._clean_code(response_text)
            
            # 1. Functional Verification (Compilation/Analysis)
            if self._verify_code(new_code):
                # 2. Safety Verification (MCSSupervisor)
                critique = self.mcs_supervisor.verify_modification(current_code, new_code, "target.py")
                if critique.is_safe:
                    return new_code, code
                else:
                    print(f"CoderAgent: SAFETY VIOLATION! {critique.violation_type}: {critique.description}")
                    instruction = f"The previous attempt failed safety verification: {critique.description}. Please try again.\nInstruction: {instruction}"
            else:
                instruction = f"The previous attempt failed functional verification. Please try again.\nInstruction: {instruction}"
                current_code = new_code
        return code, code

    def mutate(self, code, max_retries=3):
        """
        Performs evolutionary mutation on code.

        v0.3 upgrade: adds MCS safety check on each candidate and injects
        mutation-type hints (rename variable, simplify branch, extract helper)
        to encourage semantic diversity rather than cosmetic rewording.
        """
        mutation_hints = [
            "rename a local variable to something more descriptive",
            "simplify a conditional branch",
            "extract a repeated expression into a helper variable",
            "replace a loop with a list comprehension where appropriate",
            "add an informative docstring or inline comment",
        ]
        hint = random.choice(mutation_hints)
        error_feedback = ""
        for i in range(max_retries):
            print(f"CoderAgent: Mutation attempt {i+1} (hint: {hint})")
            prompt = (
                f"Your task is to perform a small, semantically meaningful mutation on "
                f"this Python code. Specifically, try to: {hint}.\n"
                f"Preserve all existing functionality.\n"
                f"{error_feedback}\n\n```python\n{code}\n```\n\n"
                f"Return only the mutated Python code inside a ```python ... ``` block."
            )
            response_text = self.backend.generate(prompt)
            mutated_code = self._clean_code(response_text)
            if not self._verify_code(mutated_code):
                error_feedback = "The previous mutation failed syntax/compilation verification. Please try again."
                continue
            # Safety gate
            critique = self.mcs_supervisor.verify_modification(code, mutated_code, "mutation_target.py")
            if critique.is_safe:
                return mutated_code
            else:
                error_feedback = (
                    f"The previous mutation failed safety verification "
                    f"({critique.violation_type}: {critique.description}). Please try again."
                )
        return code

    def crossover(self, code1, code2, max_retries=3):
        """
        Performs evolutionary crossover between two code solutions.

        v0.3 upgrade: safety-checks the offspring and explicitly asks the LLM
        to explain which element it borrowed from each parent (aids auditability).
        """
        error_feedback = ""
        for i in range(max_retries):
            print(f"CoderAgent: Crossover attempt {i+1}")
            prompt = (
                f"Your task is to combine the best elements of these two Python functions "
                f"into a new, superior function. Preserve correctness.\n"
                f"In a brief comment at the top, note which elements came from Parent 1 "
                f"and which from Parent 2.\n"
                f"{error_feedback}\n\n"
                f"Parent 1:\n```python\n{code1}\n```\n\n"
                f"Parent 2:\n```python\n{code2}\n```\n\n"
                f"Return only the child Python code inside a ```python ... ``` block."
            )
            response_text = self.backend.generate(prompt)
            crossed_over_code = self._clean_code(response_text)
            if not self._verify_code(crossed_over_code):
                error_feedback = "The previous crossover failed syntax/compilation verification. Please try again."
                continue
            critique = self.mcs_supervisor.verify_modification(code1, crossed_over_code, "crossover_target.py")
            if critique.is_safe:
                return crossed_over_code
            else:
                error_feedback = (
                    f"The previous crossover failed safety verification "
                    f"({critique.violation_type}: {critique.description}). Please try again."
                )
        return code1

    def generate_tactic(self, proof_state, failed_tactics=None, max_retries=3):
        """
        Generate the single most promising Lean tactic to apply to proof_state.

        Used by MCSSupervisor.run_proof_cycle() (v0.4 Task 1).

        Args:
            proof_state: ProofState object with .raw_state and .goals.
            failed_tactics: list of (tactic, error) pairs to avoid repeating.
            max_retries: how many LLM attempts before giving up.

        Returns:
            A tactic string (e.g. "ring", "simp", "induction n"), or None.
        """
        failure_context = ""
        if failed_tactics:
            lines = "\n".join(
                f"  - `{t}` → {e}" for t, e in failed_tactics
            )
            failure_context = (
                f"\nThe following tactics have already been tried and failed:\n{lines}\n"
                f"Do NOT suggest any of these tactics.\n"
            )

        for i in range(max_retries):
            print(f"CoderAgent: Tactic generation attempt {i+1}")
            prompt = (
                f"You are an expert Lean 4 theorem prover.\n"
                f"The current proof state is:\n\n"
                f"```\n{proof_state.raw_state}\n```\n"
                f"{failure_context}\n"
                f"Suggest the single best Lean tactic to apply next. "
                f"Reply with ONLY the tactic, no explanation, no code fences. "
                f"Examples: `ring`, `simp`, `omega`, `induction n with | zero => simp | succ n ih => ring`."
            )
            response_text = self.backend.generate(prompt).strip()
            # Strip any accidental code fences or leading/trailing whitespace
            tactic = response_text.replace("```lean", "").replace("```", "").strip()
            if tactic:
                return tactic
        return None

    def _verify_code(self, code):
        """Verifies code through compilation and static analysis."""
        temp_file_path = "temp_coder_output.py"
        with open(temp_file_path, 'w') as f:
            f.write(code)
        
        # We need to handle cases where self.compiler or self.analyzer might be None for PoC
        if self.compiler:
            compiler_error = self.compiler.use(temp_file_path)
            if compiler_error:
                print(f"CoderAgent: Compiler error detected: {compiler_error}")
                if os.path.exists(temp_file_path): os.remove(temp_file_path)
                return False
        
        if self.analyzer:
            analyzer_output = self.analyzer.use(temp_file_path)
            if analyzer_output:
                print(f"CoderAgent: Static analyzer found issues:\n{analyzer_output}")
                if os.path.exists(temp_file_path): os.remove(temp_file_path)
                return False
        
        if os.path.exists(temp_file_path): os.remove(temp_file_path)
        return True
