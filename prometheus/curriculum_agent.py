"""
CurriculumAgent — v0.3 upgrade.

Changes from v0.2:
  - Migrated from hard-coded ``google.generativeai`` to the unified
    ``prometheus.llm_backend`` so any configured backend is used.
  - ``generate_theorem`` now returns a ``(theorem_str, difficulty)`` tuple
    where ``difficulty`` is one of "easy" / "medium" / "hard".  This
    integrates with the WP31 CurriculumScheduler ZPD logic.
  - ``generate_benchmark`` tracks the last solved complexity via an
    injected ``performance_logger`` (unchanged interface) but also
    exposes a ``generate_theorem_at_difficulty`` helper for direct use
    by the theorem-proving MCSSupervisor loop.
  - No longer imports ``src.performance_logger`` — uses the prometheus
    package's own ``performance_logger`` module instead.
"""

import re
import logging
from typing import Optional, Tuple

from prometheus.llm_backend import get_llm_backend

logger = logging.getLogger(__name__)

# Ordered difficulty levels for the theorem curriculum
THEOREM_DIFFICULTIES = ["easy", "medium", "hard"]

# Seed theorems per difficulty — used as few-shot examples in prompts
_SEED_THEOREMS = {
    "easy": [
        "theorem add_zero (n : Nat) : n + 0 = n",
        "theorem zero_add (n : Nat) : 0 + n = n",
        "theorem mul_one  (n : Nat) : n * 1 = n",
    ],
    "medium": [
        "theorem add_comm (a b : Nat) : a + b = b + a",
        "theorem add_assoc (a b c : Nat) : a + b + c = a + (b + c)",
        "theorem mul_comm (a b : Nat) : a * b = b * a",
    ],
    "hard": [
        "theorem mul_add (a b c : Nat) : a * (b + c) = a * b + a * c",
        "theorem Nat.succ_ne_zero (n : Nat) : Nat.succ n ≠ 0",
        "theorem Nat.le_antisymm {a b : Nat} (h1 : a ≤ b) (h2 : b ≤ a) : a = b",
    ],
}


class CurriculumAgent:
    """
    Generates code benchmarks and Lean theorem statements of increasing
    difficulty to drive the self-improvement loop.
    """

    def __init__(self, performance_logger=None, model_name: str = None):
        self.backend = get_llm_backend(model_name=model_name)
        self.performance_logger = performance_logger
        logger.info("CurriculumAgent initialised (model=%s).", model_name or "default")

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                   #
    # ------------------------------------------------------------------ #

    def _clean_code(self, text: str) -> str:
        """Strip markdown fences and leading non-code lines."""
        code_blocks = re.findall(r"```(?:python|lean)?\n(.*?)\n```", text, re.DOTALL)
        if code_blocks:
            return "\n".join(code_blocks)
        lines = text.strip().split("\n")
        cleaned = []
        in_code = False
        for line in lines:
            stripped = line.strip()
            if (
                stripped.startswith("def ")
                or stripped.startswith("import ")
                or stripped.startswith("theorem ")
                or stripped.startswith("lemma ")
            ):
                in_code = True
            if in_code:
                cleaned.append(line)
        return "\n".join(cleaned)

    # ------------------------------------------------------------------ #
    #  Code benchmark generation                                          #
    # ------------------------------------------------------------------ #

    def generate_benchmark(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Generate a Python benchmark of increasing difficulty.

        Returns ``(function_name, function_code, test_code)`` or
        ``(None, None, None)`` on failure.
        """
        last_complexity = (
            self.performance_logger.get_last_solved_complexity()
            if self.performance_logger else 0
        )

        if last_complexity == 0:
            topic = "a simple string manipulation function (e.g. reverse a string)"
        elif last_complexity == 1:
            topic = "a function that sorts a list of tuples by their second element"
        elif last_complexity == 2:
            topic = "a function that finds the median of a list of numbers"
        else:
            topic = (
                "a function that merges two sorted lists into a single sorted list "
                "without using built-in sort"
            )

        logger.info("CurriculumAgent: generating benchmark — %s", topic)

        fn_prompt = (
            f"Write a single, self-contained Python function for: {topic}. "
            f"Output only the Python code inside a ```python ... ``` block."
        )
        fn_code = self._clean_code(self.backend.generate(fn_prompt))

        try:
            fn_name = fn_code.split("def ")[1].split("(")[0]
        except IndexError:
            logger.warning("CurriculumAgent: could not extract function name.")
            return None, None, None

        test_prompt = (
            f"Write a pytest test file for the following Python function:\n"
            f"```python\n{fn_code}\n```\n"
            f"Include at least three test cases. "
            f"Output only Python code inside a ```python ... ``` block."
        )
        test_code = self._clean_code(self.backend.generate(test_prompt))
        return fn_name, fn_code, test_code

    # ------------------------------------------------------------------ #
    #  Theorem generation                                                 #
    # ------------------------------------------------------------------ #

    def generate_theorem(self) -> Tuple[str, str]:
        """
        Generate a Lean 4 theorem statement at an automatically chosen
        difficulty level (based on performance_logger if available).

        Returns
        -------
        (theorem_str, difficulty)
            ``theorem_str`` — a one-line Lean 4 theorem declaration.
            ``difficulty``  — "easy", "medium", or "hard".
        """
        difficulty = self._choose_difficulty()
        return self.generate_theorem_at_difficulty(difficulty), difficulty

    def generate_theorem_at_difficulty(self, difficulty: str) -> str:
        """
        Generate a Lean 4 theorem at a specific difficulty level.

        Args:
            difficulty: one of "easy", "medium", "hard".

        Returns:
            A Lean 4 theorem declaration string (one line).
        """
        difficulty = difficulty if difficulty in THEOREM_DIFFICULTIES else "easy"
        seeds = _SEED_THEOREMS[difficulty]
        seed_lines = "\n".join(f"  - `{s}`" for s in seeds)

        prompt = (
            f"You are an expert in Lean 4 theorem proving.\n"
            f"Generate a NEW, original Lean 4 theorem statement at '{difficulty}' difficulty.\n"
            f"Examples of {difficulty} theorems:\n{seed_lines}\n\n"
            f"Requirements:\n"
            f"  - One line only (the theorem declaration, no proof body).\n"
            f"  - Use standard Lean 4 / Mathlib naming conventions.\n"
            f"  - Do NOT include ':= by' or any proof.\n"
            f"  - Do NOT add imports.\n"
            f"Output only the theorem line, nothing else."
        )
        response = self.backend.generate(prompt).strip()
        theorem = self._clean_code(response)
        # Final sanity strip — take only the first non-empty line
        for line in theorem.splitlines():
            line = line.strip()
            if line.startswith("theorem") or line.startswith("lemma"):
                return line
        # Fallback to a known-good seed
        logger.warning(
            "CurriculumAgent: LLM did not return a valid theorem line; "
            "using seed fallback."
        )
        return seeds[0]

    # ------------------------------------------------------------------ #
    #  Difficulty selection                                               #
    # ------------------------------------------------------------------ #

    def _choose_difficulty(self) -> str:
        """
        Pick a difficulty level based on recent performance history.

        If a performance_logger is attached we use the last-solved
        complexity as a proxy; otherwise default to "easy".
        """
        if self.performance_logger is None:
            return "easy"
        last = self.performance_logger.get_last_solved_complexity()
        if last == 0:
            return "easy"
        elif last == 1:
            return "medium"
        else:
            return "hard"
