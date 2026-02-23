#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARC-CRLS Strange Loop (v0.97)
Critique → Revise → Learn → Synthesize for ARC Program Synthesis

Implements Hofstadter's Strange Loop applied to ARC-AGI:
  1. Run ARC tasks through DeepBeamSearch (Attempt)
  2. Record failures as FailureEpisode objects (Critique)
  3. MetaCognitionLayer diagnoses recurring patterns (Revise)
  4. LLMBackend synthesizes candidate new operation code (Synthesize)
  5. MCSSupervisor vets the synthesized code (Safety Gate)
  6. Surviving operations are hot-added to PARAMETRIC_OPERATIONS (Learn)
  7. Repeat — each generation uses the enriched operation set

This closes the loop: failure analysis feeds back into the operation library
that is used for the next generation of synthesis, creating I.J. Good's
recursive self-improvement in a measurable, domain-grounded setting.

Design Notes:
- Operations synthesized by LLM are validated by: (a) safe AST parse,
  (b) MCSSupervisor constitutional check, (c) smoke-test on a 3×3 grid.
- Synthesized operations are added ONLY to the in-memory PARAMETRIC_OPERATIONS
  dict — they are NOT written back to arc_parametric_operations.py unless
  the operator explicitly calls save_synthesized_ops().
- Failure threshold: tasks with best_fitness < FAILURE_THRESHOLD are recorded.
- The Strange Loop terminates when either max_generations is reached or
  no new operations can be synthesized from the remaining failure patterns.

Author: Prometheus v0.97
"""

import ast
import inspect
import json
import logging
import textwrap
import time
import types
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# --- Prometheus imports ---
from arc_parametric_operations import PARAMETRIC_OPERATIONS, build_operation_map
from arc_deep_beam_search import DeepBeamSearch
from prometheus.v0_114_crls_strange_loop import (
    FailureEpisode,
    FailureType,
    CorrectionStrategy,
    MetaCognitionLayer,
    SelfCorrectionEngine,
    CRLSStrangeLoop,
)
from prometheus.safety.mcs_supervisor import MCSSupervisor, SafetyCritique
from prometheus.llm_backend import get_llm_backend

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAILURE_THRESHOLD = 0.50  # Tasks below this are "failures"
MAX_OPS_PER_GENERATION = 3  # Limit LLM-synthesized ops per generation
SAFETY_SMOKE_TEST_GRID = np.array([[1, 2, 0], [0, 1, 2], [2, 0, 1]], dtype=np.int32)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ARCTaskResult:
    """Result of running DeepBeamSearch on one ARC task."""
    task_id: str
    best_fitness: float
    program_ops: List[str]       # List of operation names in best program
    failure_pattern: str         # Human-readable diagnosis
    attempted_ops: List[str]     # All operations tried (from biased_operations or defaults)
    train_examples: List[Dict]   # The training examples (for re-use in synthesis)


@dataclass
class SynthesizedOperation:
    """An operation synthesized by the LLM and vetted by MCS."""
    name: str
    description: str
    source_code: str             # Full Python def ... block
    params_spec: Dict            # PARAMETRIC_OPERATIONS params sub-dict
    safety_approved: bool
    smoke_test_passed: bool
    generation: int
    failure_patterns_that_triggered: List[str]


# ---------------------------------------------------------------------------
# Failure Pattern Analyser (ARC-specific)
# ---------------------------------------------------------------------------

class ARCFailurePatternAnalyser:
    """
    Lightweight analyser that turns a list of ARCTaskResult failures into
    human-readable pattern descriptions suitable for the LLM synthesis prompt.

    Builds on the pattern-types identified in CURRENT_STATUS_v0_95.md:
      - OBJECT_SELECTION:  task needs to pick/rank objects
      - CONNECTIVITY:      task needs connected-component reasoning
      - SYMMETRY:          task needs symmetry detection/completion
      - PATH_DRAWING:      task needs line/path creation
      - CONDITIONAL:       task needs color-triggered transformations
      - SIZE_SCALING:      task needs precise size transformations
      - REPETITION:        task needs pattern tiling/extraction
      - SPATIAL:           task needs gravity/alignment/distribution
    """

    PATTERN_KEYWORDS = {
        "OBJECT_SELECTION": [
            "largest", "smallest", "select", "pick", "rank", "count",
            "isolate", "object", "component"
        ],
        "CONNECTIVITY": [
            "connected", "fill", "flood", "hole", "enclosed", "outline",
            "border", "label"
        ],
        "SYMMETRY": [
            "symmetric", "mirror", "reflect", "quadrant", "half",
            "complete", "fold"
        ],
        "PATH_DRAWING": [
            "connect", "line", "extend", "trace", "path", "between",
            "endpoint", "draw"
        ],
        "CONDITIONAL": [
            "if", "when", "trigger", "condition", "where", "based on",
            "presence", "conditional"
        ],
        "SIZE_SCALING": [
            "resize", "scale", "expand", "compress", "fit", "canvas",
            "size", "dimension"
        ],
        "REPETITION": [
            "tile", "repeat", "pattern", "periodic", "unit", "replicate",
            "tiling"
        ],
        "SPATIAL": [
            "gravity", "align", "center", "distribute", "edge",
            "position", "arrange", "move"
        ],
    }

    def __init__(self):
        self.pattern_counts: Counter = Counter()
        self.task_patterns: Dict[str, List[str]] = defaultdict(list)

    def analyse(self, failures: List[ARCTaskResult]) -> Dict[str, Any]:
        """
        Analyse failures and return a summary dict with pattern frequencies
        and representative examples.
        """
        self.pattern_counts.clear()
        self.task_patterns.clear()

        for result in failures:
            detected = self._detect_patterns(result)
            for p in detected:
                self.pattern_counts[p] += 1
            self.task_patterns[result.task_id] = detected

        return {
            "total_failures": len(failures),
            "pattern_frequencies": dict(self.pattern_counts.most_common()),
            "top_pattern": self.pattern_counts.most_common(1)[0] if self.pattern_counts else None,
            "task_patterns": dict(self.task_patterns),
        }

    def _detect_patterns(self, result: ARCTaskResult) -> List[str]:
        """Heuristically detect which ARC pattern categories a failure belongs to."""
        detected = []

        # Analyse the task's training examples
        for ex in result.train_examples[:3]:
            in_grid = np.array(ex.get("input", [[0]]))
            out_grid = np.array(ex.get("output", [[0]]))

            # Size change → SIZE_SCALING
            if in_grid.shape != out_grid.shape:
                detected.append("SIZE_SCALING")

            # Multiple connected components → OBJECT_SELECTION / CONNECTIVITY
            from scipy import ndimage
            mask = (in_grid != 0).astype(np.int32)
            _, n_obj = ndimage.label(mask)
            if n_obj >= 2:
                detected.append("OBJECT_SELECTION")
                detected.append("CONNECTIVITY")

            # Symmetry check: is output symmetric?
            if out_grid.shape[0] == out_grid.shape[1]:
                if np.array_equal(out_grid, np.fliplr(out_grid)):
                    detected.append("SYMMETRY")
                elif np.array_equal(out_grid, np.flipud(out_grid)):
                    detected.append("SYMMETRY")

            # Repetition: output is multiple of input
            if (out_grid.shape[0] > in_grid.shape[0] and
                    out_grid.shape[0] % in_grid.shape[0] == 0):
                detected.append("REPETITION")
            if (out_grid.shape[1] > in_grid.shape[1] and
                    out_grid.shape[1] % in_grid.shape[1] == 0):
                detected.append("REPETITION")

        # Analyse failure pattern text
        fp_lower = result.failure_pattern.lower()
        for pattern, keywords in self.PATTERN_KEYWORDS.items():
            if any(kw in fp_lower for kw in keywords):
                detected.append(pattern)

        return list(set(detected)) or ["UNKNOWN"]

    def get_synthesis_prompt(self, failures: List[ARCTaskResult],
                              existing_ops: List[str]) -> str:
        """
        Build an LLM prompt asking for one new operation function.

        The prompt includes:
        - Top failure patterns
        - Example failed task inputs/outputs (first training pair)
        - List of existing operations to avoid duplicates
        - Exact format required for the response
        """
        analysis = self.analyse(failures)
        top_patterns = list(analysis["pattern_frequencies"].keys())[:3]

        # Pick one representative failed task as example
        example_task = failures[0] if failures else None
        example_str = ""
        if example_task and example_task.train_examples:
            ex = example_task.train_examples[0]
            in_g = ex.get("input", [[0]])
            out_g = ex.get("output", [[0]])
            example_str = (
                f"\nExample failed task '{example_task.task_id}' "
                f"(best fitness {example_task.best_fitness:.3f}):\n"
                f"  Input:  {in_g}\n"
                f"  Output: {out_g}\n"
            )

        existing_list = ", ".join(existing_ops[:30])

        prompt = textwrap.dedent(f"""
        You are an ARC-AGI expert designing a new Python operation for a grid
        transformation solver. The solver has {len(existing_ops)} operations
        but is failing on {len(failures)} tasks.

        TOP FAILURE PATTERNS: {', '.join(top_patterns)}
        {example_str}
        EXISTING OPERATIONS (do not duplicate): {existing_list}

        Design ONE new operation that would help solve the failure patterns above.

        STRICT OUTPUT FORMAT — return ONLY the following block, nothing else:

        ```python
        def OPERATION_NAME(grid: np.ndarray, PARAM1: TYPE = DEFAULT, **kwargs) -> np.ndarray:
            \"\"\"One-line description.\"\"\"
            # implementation using numpy (np) and scipy.ndimage (ndimage) only
            result = grid.copy()
            # ... your implementation ...
            return result

        # PARAMS: {{"PARAM1": {{"type": "TYPE", "values": [LIST], "default": DEFAULT}}}}
        # DESCRIPTION: "one-line description"
        ```

        Rules:
        - Use only numpy (np) and scipy.ndimage (ndimage) — no other imports
        - Function must accept (grid: np.ndarray, ..., **kwargs) and return np.ndarray
        - All parameter values must be Python literals (int, str, bool, list)
        - Keep the function under 40 lines
        - Name must be a valid Python identifier, snake_case, not in existing list
        """).strip()

        return prompt


# ---------------------------------------------------------------------------
# Synthesized Operation Validator
# ---------------------------------------------------------------------------

class SynthesizedOpValidator:
    """
    Validates LLM-generated operation code before adding it to the catalog.

    Checks:
    1. Parses as valid Python (AST)
    2. MCSSupervisor constitutional safety
    3. Smoke-test: call with SAFETY_SMOKE_TEST_GRID, returns 2D np.ndarray
    """

    def __init__(self):
        self.mcs = MCSSupervisor()

    def validate(self, op_name: str, source_code: str,
                 generation: int) -> Tuple[bool, str, Optional[types.FunctionType]]:
        """
        Returns (is_valid, reason, compiled_function_or_None).
        """
        # 1. AST parse
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            return False, f"SyntaxError: {e}", None

        # 2. Constitutional check
        critique = self.mcs.verify_modification(
            original_code="",
            proposed_code=source_code,
            file_path="arc_parametric_operations.py",
            is_test_file=False,
        )
        if not critique.is_safe:
            return False, f"MCS rejected ({critique.violation_type}): {critique.description}", None

        # 3. Compile and smoke-test
        try:
            namespace = {"np": np}
            try:
                from scipy import ndimage as _ndimage
                namespace["ndimage"] = _ndimage
            except ImportError:
                pass

            exec(compile(tree, "<synthesized>", "exec"), namespace)

            fn = namespace.get(op_name)
            if fn is None:
                return False, f"Function '{op_name}' not found in synthesized code", None

            result = fn(SAFETY_SMOKE_TEST_GRID.copy())
            if not isinstance(result, np.ndarray) or result.ndim != 2:
                return False, "Smoke-test: function did not return a 2D np.ndarray", None

        except Exception as e:
            return False, f"Smoke-test exception: {e}", None

        return True, "OK", fn

    @staticmethod
    def parse_params_and_description(raw_response: str) -> Tuple[Dict, str]:
        """
        Extract the PARAMS and DESCRIPTION comments from the LLM response.
        Returns (params_dict, description_str).
        """
        params: Dict = {}
        description: str = "Synthesized operation"

        for line in raw_response.splitlines():
            line = line.strip()
            if line.startswith("# PARAMS:"):
                try:
                    params = json.loads(line[len("# PARAMS:"):].strip())
                except (json.JSONDecodeError, ValueError):
                    pass
            elif line.startswith("# DESCRIPTION:"):
                raw_desc = line[len("# DESCRIPTION:"):].strip()
                description = raw_desc.strip('"\'')

        return params, description

    @staticmethod
    def extract_code_block(raw_response: str) -> str:
        """
        Pull the code out of the ```python ... ``` fences in the LLM response.
        """
        lines = raw_response.splitlines()
        in_block = False
        code_lines: List[str] = []
        for line in lines:
            if line.strip().startswith("```python"):
                in_block = True
                continue
            if in_block and line.strip() == "```":
                break
            if in_block:
                code_lines.append(line)
        return "\n".join(code_lines)

    @staticmethod
    def extract_function_name(source_code: str) -> Optional[str]:
        """Extract the first def name from Python source."""
        try:
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    return node.name
        except SyntaxError:
            pass
        return None


# ---------------------------------------------------------------------------
# ARC CRLS Strange Loop Orchestrator
# ---------------------------------------------------------------------------

class ARCCRLSStrangeLoop:
    """
    The full CRLS Strange Loop for ARC-AGI program synthesis.

    Each generation:
      1. Solve all pending tasks with DeepBeamSearch (using current op set)
      2. Record failures (fitness < FAILURE_THRESHOLD)
      3. Analyse failure patterns (MetaCognitionLayer + ARCFailurePatternAnalyser)
      4. Ask LLM to synthesize one new operation per top pattern
      5. Validate each synthesized op (AST + MCS + smoke-test)
      6. Register surviving ops in PARAMETRIC_OPERATIONS
      7. Re-run only the failed tasks with the enriched op set

    Convergence criteria:
      - No more failed tasks, OR
      - No new valid operations synthesized this generation, OR
      - max_generations reached
    """

    def __init__(self,
                 task_ids: List[str],
                 arc_data_dir: str = "arc_agi_official/data/evaluation",
                 max_generations: int = 5,
                 beam_width: int = 50,
                 max_depth: int = 8,
                 llm_model: str = "microsoft/Phi-3-mini-4k-instruct",
                 verbose: bool = True):
        """
        Args:
            task_ids:        List of ARC task IDs to solve (filenames without .json)
            arc_data_dir:    Path to the directory containing task JSON files
            max_generations: Maximum number of CRLS generations
            beam_width:      DeepBeamSearch beam width
            max_depth:       DeepBeamSearch max depth
            llm_model:       HuggingFace model name for local synthesis
            verbose:         Print progress
        """
        self.task_ids = task_ids
        self.arc_data_dir = Path(arc_data_dir)
        self.max_generations = max_generations
        self.beam_width = beam_width
        self.max_depth = max_depth
        self.verbose = verbose

        # Internal state
        self.llm = get_llm_backend(llm_model)
        self.pattern_analyser = ARCFailurePatternAnalyser()
        self.validator = SynthesizedOpValidator()

        # Tracking
        self.generation = 0
        self.solved_task_ids: List[str] = []
        self.failed_results: List[ARCTaskResult] = []
        self.synthesized_ops: List[SynthesizedOperation] = []
        self.generation_log: List[Dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        """
        Execute the full CRLS Strange Loop.

        Returns a summary dict with:
          - generations_run
          - tasks_solved / tasks_total
          - synthesized_ops (names)
          - generation_log (per-gen stats)
        """
        self._log(f"\n{'='*60}")
        self._log(f"ARC CRLS Strange Loop — {len(self.task_ids)} tasks")
        self._log(f"Max generations: {self.max_generations}")
        self._log(f"{'='*60}\n")

        # Initial solve pass
        pending = list(self.task_ids)

        for gen in range(self.max_generations):
            self.generation = gen + 1
            self._log(f"\n--- Generation {self.generation} ---")
            self._log(f"  Pending tasks: {len(pending)}")
            self._log(f"  Active ops: {len(PARAMETRIC_OPERATIONS)}")

            # Step 1: Solve pending tasks
            gen_results = self._solve_tasks(pending)
            solved_ids = [r.task_id for r in gen_results if r.best_fitness >= 0.95]
            failed = [r for r in gen_results if r.best_fitness < FAILURE_THRESHOLD]
            partial = [r for r in gen_results
                       if FAILURE_THRESHOLD <= r.best_fitness < 0.95]

            self.solved_task_ids.extend(solved_ids)
            self.failed_results = failed  # Only keep latest gen's failures

            self._log(f"  Solved: {len(solved_ids)}, Partial: {len(partial)}, "
                      f"Failed: {len(failed)}")

            # Step 2: If no failures, we are done
            if not failed:
                self._log("  No failures — Strange Loop converged!")
                break

            # Step 3: Analyse failure patterns
            analysis = self.pattern_analyser.analyse(failed)
            self._log(f"  Top failure patterns: "
                      f"{list(analysis['pattern_frequencies'].items())[:3]}")

            # Step 4 & 5: Synthesize and validate new operations
            new_ops = self._synthesize_operations(failed)
            self._log(f"  Synthesized {len(new_ops)} new valid operations: "
                      f"{[op.name for op in new_ops]}")

            if not new_ops:
                self._log("  No new operations synthesized — Strange Loop stalled.")
                break

            # Step 6: Register new ops in PARAMETRIC_OPERATIONS
            self._register_ops(new_ops)
            self.synthesized_ops.extend(new_ops)

            # Step 7: Re-run only failed tasks next generation
            pending = [r.task_id for r in failed]

            # Log generation summary
            self.generation_log.append({
                "generation": self.generation,
                "tasks_solved_this_gen": len(solved_ids),
                "tasks_failed": len(failed),
                "new_ops": [op.name for op in new_ops],
                "total_ops": len(PARAMETRIC_OPERATIONS),
                "top_patterns": list(analysis["pattern_frequencies"].items())[:3],
            })

        summary = {
            "generations_run": self.generation,
            "tasks_total": len(self.task_ids),
            "tasks_solved": len(self.solved_task_ids),
            "solve_rate": len(self.solved_task_ids) / max(1, len(self.task_ids)),
            "synthesized_ops": [op.name for op in self.synthesized_ops],
            "total_ops_in_catalog": len(PARAMETRIC_OPERATIONS),
            "generation_log": self.generation_log,
        }

        self._log(f"\n{'='*60}")
        self._log(f"CRLS Loop Complete")
        self._log(f"  Solved: {summary['tasks_solved']}/{summary['tasks_total']} "
                  f"({summary['solve_rate']*100:.1f}%)")
        self._log(f"  Synthesized ops: {summary['synthesized_ops']}")
        self._log(f"{'='*60}\n")

        return summary

    def save_synthesized_ops(self, filepath: str = "arc_synthesized_ops.py") -> None:
        """
        Persist all safety-approved synthesized operations to a Python file.
        This file can be imported to reload the ops in a future session.
        """
        approved = [op for op in self.synthesized_ops
                    if op.safety_approved and op.smoke_test_passed]
        if not approved:
            self._log("No approved synthesized ops to save.")
            return

        lines = [
            "#!/usr/bin/env python3",
            "# -*- coding: utf-8 -*-",
            '"""Synthesized ARC operations (auto-generated by ARCCRLSStrangeLoop)."""',
            "",
            "import numpy as np",
            "try:",
            "    from scipy import ndimage",
            "except ImportError:",
            "    ndimage = None",
            "",
        ]

        catalog_entries = []
        for op in approved:
            lines.append(f"# Generation {op.generation} — patterns: "
                         f"{', '.join(op.failure_patterns_that_triggered)}")
            lines.append(op.source_code)
            lines.append("")
            catalog_entries.append(
                f'    "{op.name}": {{\n'
                f'        "function": {op.name},\n'
                f'        "params": {json.dumps(op.params_spec)},\n'
                f'        "description": "{op.description}"\n'
                f'    }},'
            )

        lines.append("SYNTHESIZED_OPERATIONS = {")
        lines.extend(catalog_entries)
        lines.append("}")
        lines.append("")

        Path(filepath).write_text("\n".join(lines))
        self._log(f"Saved {len(approved)} synthesized ops to {filepath}")

    def get_generation_report(self) -> str:
        """Return a human-readable Hofstadter-style generation report."""
        lines = [
            "ARC CRLS Strange Loop — Generation Report",
            "=" * 50,
        ]
        for entry in self.generation_log:
            lines.append(
                f"\nGeneration {entry['generation']}:"
                f"\n  Solved this gen: {entry['tasks_solved_this_gen']}"
                f"\n  Still failing:   {entry['tasks_failed']}"
                f"\n  New operations:  {entry['new_ops'] or '(none)'}"
                f"\n  Catalog size:    {entry['total_ops']}"
                f"\n  Top patterns:    {entry['top_patterns']}"
            )
        lines.append("\n" + "=" * 50)
        lines.append(f"Total solved: {len(self.solved_task_ids)} / {len(self.task_ids)}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _solve_tasks(self, task_ids: List[str]) -> List[ARCTaskResult]:
        """Run DeepBeamSearch on each task and return ARCTaskResult list."""
        results = []
        solver = DeepBeamSearch(
            beam_width=self.beam_width,
            max_depth=self.max_depth,
            max_candidates_per_op=3,
        )

        for task_id in task_ids:
            task_file = self.arc_data_dir / f"{task_id}.json"
            if not task_file.exists():
                # Try training dir as fallback
                task_file = self.arc_data_dir.parent / "training" / f"{task_id}.json"
            if not task_file.exists():
                self._log(f"  [skip] Task file not found: {task_id}")
                continue

            with open(task_file, "r") as f:
                task = json.load(f)

            self._log(f"  Solving {task_id}...", end=" ")
            try:
                # Reinitialise solver with current op map each time
                solver.operation_map = build_operation_map()
                program, fitness = solver.synthesize(task)
                ops_used = [op for op, _ in program.operations] if program.operations else []
                pattern = self._diagnose_failure(task, fitness, ops_used)
                self._log(f"fitness={fitness:.3f}")
            except Exception as e:
                self._log(f"ERROR: {e}")
                program, fitness = None, 0.0
                ops_used = []
                pattern = f"solver_exception: {e}"

            results.append(ARCTaskResult(
                task_id=task_id,
                best_fitness=fitness,
                program_ops=ops_used,
                failure_pattern=pattern,
                attempted_ops=list(PARAMETRIC_OPERATIONS.keys()),
                train_examples=task.get("train", []),
            ))

        return results

    def _diagnose_failure(self, task: Dict, fitness: float,
                           ops_used: List[str]) -> str:
        """Simple heuristic diagnosis string for a failed task."""
        pairs = task.get("train", [])
        if not pairs:
            return "no training examples"

        in_g = np.array(pairs[0]["input"])
        out_g = np.array(pairs[0]["output"])

        clues = []

        if in_g.shape != out_g.shape:
            ratio = (out_g.shape[0] / max(in_g.shape[0], 1),
                     out_g.shape[1] / max(in_g.shape[1], 1))
            clues.append(f"size_change {ratio[0]:.1f}x{ratio[1]:.1f}")

        in_colors = set(np.unique(in_g).tolist())
        out_colors = set(np.unique(out_g).tolist())
        new_colors = out_colors - in_colors
        if new_colors:
            clues.append(f"new_colors {new_colors}")

        from scipy import ndimage as _ndi
        _, n_in = _ndi.label((in_g != 0).astype(np.int32))
        if n_in > 1:
            clues.append(f"multi_object input ({n_in} objects)")

        if np.array_equal(out_g, np.fliplr(out_g)):
            clues.append("output is horizontally symmetric")
        if np.array_equal(out_g, np.flipud(out_g)):
            clues.append("output is vertically symmetric")

        if not clues:
            clues.append(f"low fitness ({fitness:.3f}), ops failed: {ops_used[:3]}")

        return "; ".join(clues)

    def _synthesize_operations(self,
                                failures: List[ARCTaskResult]) -> List[SynthesizedOperation]:
        """
        Ask LLM to synthesize new operations from failure patterns.
        Returns list of validated SynthesizedOperation objects.
        """
        existing_ops = list(PARAMETRIC_OPERATIONS.keys())
        synthesized: List[SynthesizedOperation] = []

        # Build analysis for the prompt
        analysis = self.pattern_analyser.analyse(failures)
        top_patterns = list(analysis["pattern_frequencies"].keys())

        for pattern in top_patterns[:MAX_OPS_PER_GENERATION]:
            # Filter failures that have this pattern
            pattern_failures = [
                r for r in failures
                if pattern in self.pattern_analyser.task_patterns.get(r.task_id, [])
            ]
            if not pattern_failures:
                pattern_failures = failures[:3]  # Fallback to first 3

            prompt = self.pattern_analyser.get_synthesis_prompt(
                pattern_failures, existing_ops
            )

            self._log(f"  Asking LLM to synthesize op for pattern: {pattern}...")

            try:
                raw_response = self.llm.generate(prompt, max_new_tokens=512)
            except Exception as e:
                self._log(f"    LLM error: {e}")
                continue

            # Extract code block
            code_block = SynthesizedOpValidator.extract_code_block(raw_response)
            if not code_block.strip():
                self._log(f"    No code block found in LLM response.")
                continue

            # Extract function name
            op_name = SynthesizedOpValidator.extract_function_name(code_block)
            if not op_name:
                self._log(f"    Could not extract function name from code.")
                continue

            # Avoid duplicates
            if op_name in PARAMETRIC_OPERATIONS or op_name in existing_ops:
                self._log(f"    Op '{op_name}' already exists, skipping.")
                continue

            # Parse params and description
            params_spec, description = SynthesizedOpValidator.parse_params_and_description(
                raw_response
            )

            # Validate
            is_valid, reason, compiled_fn = self.validator.validate(
                op_name, code_block, self.generation
            )
            self._log(f"    {op_name}: {'APPROVED' if is_valid else 'REJECTED'} — {reason}")

            op = SynthesizedOperation(
                name=op_name,
                description=description,
                source_code=code_block,
                params_spec=params_spec,
                safety_approved=is_valid,
                smoke_test_passed=is_valid,
                generation=self.generation,
                failure_patterns_that_triggered=[pattern],
            )

            if is_valid and compiled_fn is not None:
                # Attach compiled function reference for immediate use
                op._compiled_fn = compiled_fn  # type: ignore[attr-defined]
                synthesized.append(op)
                existing_ops.append(op_name)  # Prevent same-gen duplicates

        return synthesized

    def _register_ops(self, ops: List[SynthesizedOperation]) -> None:
        """Hot-register synthesized operations into PARAMETRIC_OPERATIONS."""
        for op in ops:
            fn = getattr(op, "_compiled_fn", None)
            if fn is None:
                continue

            PARAMETRIC_OPERATIONS[op.name] = {
                "function": fn,
                "params": op.params_spec,
                "description": op.description,
            }
            self._log(f"  Registered op '{op.name}' into PARAMETRIC_OPERATIONS")

    def _log(self, msg: str, end: str = "\n") -> None:
        if self.verbose:
            print(msg, end=end, flush=True)
        logger.info(msg)


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def run_arc_crls_loop(
    task_ids: List[str],
    arc_data_dir: str = "arc_agi_official/data/evaluation",
    max_generations: int = 3,
    beam_width: int = 50,
    max_depth: int = 8,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Convenience wrapper — create and run the CRLS loop in one call.

    Args:
        task_ids:       List of task IDs to attempt (JSON filenames without .json)
        arc_data_dir:   Directory containing the task JSON files
        max_generations: Max number of CRLS generations
        beam_width:     DeepBeamSearch beam width
        max_depth:      DeepBeamSearch max depth
        verbose:        Print progress

    Returns:
        Summary dict from ARCCRLSStrangeLoop.run()
    """
    loop = ARCCRLSStrangeLoop(
        task_ids=task_ids,
        arc_data_dir=arc_data_dir,
        max_generations=max_generations,
        beam_width=beam_width,
        max_depth=max_depth,
        verbose=verbose,
    )
    summary = loop.run()
    print(loop.get_generation_report())
    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="ARC CRLS Strange Loop — recursive self-improving ARC solver"
    )
    parser.add_argument(
        "--data-dir",
        default="arc_agi_official/data/evaluation",
        help="Directory containing ARC task JSON files",
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        default=None,
        help="Task IDs to solve (filenames without .json). Default: all in data-dir",
    )
    parser.add_argument("--max-gen", type=int, default=3, help="Max generations")
    parser.add_argument("--beam-width", type=int, default=50)
    parser.add_argument("--max-depth", type=int, default=8)
    parser.add_argument("--save-ops", default=None,
                        help="Save synthesized ops to this .py file")
    args = parser.parse_args()

    # Gather task IDs
    data_path = Path(args.data_dir)
    if args.tasks:
        task_ids = args.tasks
    elif data_path.exists():
        task_ids = [p.stem for p in sorted(data_path.glob("*.json"))]
    else:
        print(f"Data directory '{args.data_dir}' not found. "
              f"Run scripts/download_arc_dataset.py first.", file=sys.stderr)
        sys.exit(1)

    if not task_ids:
        print("No tasks found.", file=sys.stderr)
        sys.exit(1)

    print(f"Running CRLS loop on {len(task_ids)} tasks...")

    loop = ARCCRLSStrangeLoop(
        task_ids=task_ids,
        arc_data_dir=args.data_dir,
        max_generations=args.max_gen,
        beam_width=args.beam_width,
        max_depth=args.max_depth,
        verbose=True,
    )
    summary = loop.run()
    print(loop.get_generation_report())

    if args.save_ops:
        loop.save_synthesized_ops(args.save_ops)

    print(json.dumps(summary, indent=2, default=str))
