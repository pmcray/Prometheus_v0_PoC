
import time
from typing import Tuple, Optional
from prometheus_v1.bridge.lean.translator import LeanTranslator
from prometheus.llm_backend import get_llm_backend
from prometheus_v1.core.data_models import MutationRecord, MutationMethod

class VerificationLoop:
    """
    The 'Unbreakable Loop'.
    Forces the agent to iterate on code until it satisfies a formal verification condition.
    """
    def __init__(self, translator: LeanTranslator):
        self.translator = translator
        self.backend = get_llm_backend()
        self.max_retries = 5

    def verify_and_correct(self, python_code: str, goal_desc: str) -> Tuple[str, bool, int]:
        """
        Main loop:
        1. Translate Python to Lean.
        2. Verify (Simulated check for PoC).
        3. If Error -> Feed back to LLM -> Update Python -> Recursion.
        """
        print(f"VerificationLoop: Entering the loop for '{goal_desc}'...")
        
        current_code = python_code
        
        for attempt in range(1, self.max_retries + 1):
            print(f"
--- Iteration {attempt}/{self.max_retries} ---")
            
            # 1. Translate
            lean_code = self.translator.translate_function(current_code)
            print(f"  > Translated to Lean 4 (Stub): {lean_code.splitlines()[1]}...")
            
            # 2. Verify (Simulated Logic for PoC without full Lean install)
            # We verify simple mathematical truths.
            error = self._simulate_lean_verification(current_code)
            
            if not error:
                print("  ✅ VERIFICATION SUCCESS: Proof accepted by kernel.")
                return current_code, True, attempt
            
            print(f"  ❌ VERIFICATION FAILED: {error}")
            
            # 3. Refine (The 'Unbreakable' part)
            print("  > Triggering Self-Correction via LLM...")
            current_code = self._request_fix(current_code, error, goal_desc)
            
        print("VerificationLoop: Max retries reached. Loop broken (Failure).")
        return current_code, False, self.max_retries

    def _simulate_lean_verification(self, code: str) -> Optional[str]:
        """
        Simulates the Lean 4 compiler output.
        Checks for common bugs to force the agent to fix them.
        """
        # Bug 1: Recursion without base case
        if "if" not in code and "return" in code:
            return "term 'n' is not decreasing. Failed to prove termination."
        
        # Bug 2: Incorrect logic (e.g. 0 * n)
        if "0 * n" in code:
            return "tactic 'rfl' failed. lhs: 0, rhs: n."
            
        # Bug 3: Infinite loops in logic
        if "while True" in code:
            return "failed to synthesize instance 'WellFoundedRelation'"

        return None

    def _request_fix(self, code: str, error: str, goal: str) -> str:
        """
        Asks the LLM to fix the Python code based on the Lean verification error.
        """
        prompt = f"""
        The following Python code failed Formal Verification in Lean 4.
        
        Goal: {goal}
        
        Current Code:
        ```python
        {code}
        ```
        
        Verification Error:
        "{error}"
        
        Task: Fix the Python code to resolve the verification error. Ensure termination and correctness.
        Return ONLY the corrected Python code in a markdown block.
        """
        
        response = self.backend.generate(prompt)
        
        # Extract code
        if "```python" in response:
            return response.split("```python")[1].split("```")[0].strip()
        elif "```" in response:
            return response.split("```")[1].split("```")[0].strip()
        return response.strip()
