#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARC-AGI v0.95: Program Template Learning

Learns program structure templates from successful solutions and uses them
for transfer learning to new tasks.

Key Concepts:
- Template = program structure with parameter slots
- Example: rotate(?) -> filter_color(?) -> border(?)
- Templates capture common solution patterns
- Transfer learning via template instantiation

Author: Prometheus v0.95
Date: 2025-10-22
"""

import json
from typing import List, Dict, Tuple, Optional, Any
from collections import defaultdict
import itertools
from arc_program import ARCProgram


class ProgramTemplate:
    """
    Represents a program structure with parameter slots.

    Example:
        structure = [
            ('rotate', ['angle']),
            ('filter_color', ['color']),
            ('border', ['thickness', 'color'])
        ]
    """

    def __init__(self, structure: List[Tuple[str, List[str]]]):
        """
        Initialize template.

        Args:
            structure: List of (operation_name, parameter_names)
        """
        self.structure = structure

    def instantiate(self, param_values: Dict[str, Any]) -> ARCProgram:
        """
        Fill in parameters to create concrete program.

        Args:
            param_values: Dict mapping "op_name.param_name" to values

        Returns:
            Concrete ARCProgram instance
        """
        operations = []
        for op_name, param_names in self.structure:
            params = {}
            for name in param_names:
                key = f"{op_name}.{name}"
                if key in param_values:
                    params[name] = param_values[key]
            operations.append((op_name, params))

        return ARCProgram(operations)

    def matches(self, program: ARCProgram) -> bool:
        """Check if a program matches this template structure."""
        if len(program.operations) != len(self.structure):
            return False

        for (op, params), (template_op, template_params) in zip(program.operations, self.structure):
            if op != template_op:
                return False
            if set(params.keys()) != set(template_params):
                return False

        return True

    def __eq__(self, other):
        """Check equality based on structure."""
        if not isinstance(other, ProgramTemplate):
            return False
        return self.structure == other.structure

    def __hash__(self):
        """Hash based on structure."""
        return hash(tuple((op, tuple(params)) for op, params in self.structure))

    def __repr__(self):
        """String representation."""
        parts = []
        for op, params in self.structure:
            if params:
                param_str = ','.join(f"{p}=?" for p in params)
                parts.append(f"{op}({param_str})")
            else:
                parts.append(f"{op}()")
        return " -> ".join(parts)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {'structure': self.structure}

    @staticmethod
    def from_dict(data: Dict) -> 'ProgramTemplate':
        """Create from dictionary."""
        return ProgramTemplate(data['structure'])


class TemplateLearner:
    """
    Learns and manages program templates for transfer learning.

    Tracks:
    - Templates and their success counts
    - Tasks solved by each template
    - Template effectiveness over time
    """

    def __init__(self):
        """Initialize template learner."""
        # {template: {'count': int, 'tasks': [task_ids], 'avg_fitness': float}}
        self.templates = {}

        # Track all successful programs for later analysis
        self.successful_programs = []  # [(program, task_id, fitness)]

    def extract_template(self, program: ARCProgram) -> ProgramTemplate:
        """
        Extract template structure from concrete program.

        Args:
            program: ARCProgram instance

        Returns:
            ProgramTemplate with parameter slots
        """
        structure = [
            (op, list(params.keys()) if params else [])
            for op, params in program.operations
        ]
        return ProgramTemplate(structure)

    def record_success(self,
                      program: ARCProgram,
                      task_id: str,
                      fitness: float) -> None:
        """
        Record a successful program and extract its template.

        Args:
            program: Successful ARCProgram
            task_id: Task identifier
            fitness: Fitness score achieved
        """
        # Store full program
        self.successful_programs.append((program, task_id, fitness))

        # Extract template
        template = self.extract_template(program)

        # Update template statistics
        if template not in self.templates:
            self.templates[template] = {
                'count': 0,
                'tasks': [],
                'fitness_sum': 0.0,
                'avg_fitness': 0.0
            }

        stats = self.templates[template]
        stats['count'] += 1
        stats['tasks'].append(task_id)
        stats['fitness_sum'] += fitness
        stats['avg_fitness'] = stats['fitness_sum'] / stats['count']

    def get_top_templates(self, k: int = 10) -> List[Tuple[ProgramTemplate, Dict]]:
        """
        Get top-k most successful templates.

        Args:
            k: Number of templates to return

        Returns:
            List of (template, stats) tuples sorted by success count
        """
        sorted_templates = sorted(
            self.templates.items(),
            key=lambda x: (x[1]['count'], x[1]['avg_fitness']),
            reverse=True
        )
        return sorted_templates[:k]

    def find_matching_template(self, program: ARCProgram) -> Optional[ProgramTemplate]:
        """
        Find if program matches any known template.

        Args:
            program: ARCProgram to check

        Returns:
            Matching template or None
        """
        for template in self.templates.keys():
            if template.matches(program):
                return template
        return None

    def get_template_examples(self,
                             template: ProgramTemplate,
                             k: int = 5) -> List[Tuple[ARCProgram, str, float]]:
        """
        Get example programs that use this template.

        Args:
            template: Template to find examples for
            k: Number of examples

        Returns:
            List of (program, task_id, fitness) tuples
        """
        examples = [
            (prog, task_id, fitness)
            for prog, task_id, fitness in self.successful_programs
            if template.matches(prog)
        ]

        # Sort by fitness
        examples.sort(key=lambda x: x[2], reverse=True)
        return examples[:k]

    def suggest_template_for_task(self,
                                  constraints: Dict[str, str],
                                  top_k: int = 5) -> List[ProgramTemplate]:
        """
        Suggest templates that might work for given constraints.

        For now, returns top-k templates overall.
        Future: Could use constraint patterns to filter.

        Args:
            constraints: Task constraints
            top_k: Number of templates to suggest

        Returns:
            List of templates
        """
        top_templates = self.get_top_templates(k=top_k)
        return [template for template, stats in top_templates]

    def save_database(self, filepath: str) -> None:
        """
        Save template database to JSON.

        Args:
            filepath: Path to save database
        """
        data = {
            'templates': {
                str(template): stats
                for template, stats in self.templates.items()
            },
            'successful_programs': [
                {
                    'program': prog.to_dict(),
                    'task_id': task_id,
                    'fitness': fitness
                }
                for prog, task_id, fitness in self.successful_programs
            ],
            'stats': {
                'total_templates': len(self.templates),
                'total_successes': len(self.successful_programs)
            }
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def load_database(self, filepath: str) -> bool:
        """
        Load template database from JSON.

        Args:
            filepath: Path to load database from

        Returns:
            True if successful, False if file not found
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Reconstruct templates
            self.templates = {}
            for template_str, stats in data.get('templates', {}).items():
                # Parse template string back to structure
                # For now, store as string key (will improve if needed)
                # TODO: Improve template serialization if needed
                pass  # Skip for now - will rebuild from successful_programs

            # Reconstruct successful programs
            self.successful_programs = []
            for item in data.get('successful_programs', []):
                prog = ARCProgram.from_dict(item['program'])
                task_id = item['task_id']
                fitness = item['fitness']
                self.successful_programs.append((prog, task_id, fitness))

                # Rebuild template stats
                template = self.extract_template(prog)
                if template not in self.templates:
                    self.templates[template] = {
                        'count': 0,
                        'tasks': [],
                        'fitness_sum': 0.0,
                        'avg_fitness': 0.0
                    }
                stats = self.templates[template]
                stats['count'] += 1
                stats['tasks'].append(task_id)
                stats['fitness_sum'] += fitness
                stats['avg_fitness'] = stats['fitness_sum'] / stats['count']

            return True

        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"Warning: Error loading template database: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about learned templates."""
        return {
            'total_templates': len(self.templates),
            'total_successes': len(self.successful_programs),
            'avg_uses_per_template': (
                sum(stats['count'] for stats in self.templates.values()) / len(self.templates)
                if self.templates else 0
            ),
            'most_common_template': (
                str(max(self.templates.items(), key=lambda x: x[1]['count'])[0])
                if self.templates else None
            )
        }


def _evaluate_program(program: ARCProgram,
                     train_examples: List[Dict],
                     operation_map: Dict) -> float:
    """
    Evaluate program on training examples.

    Args:
        program: ARCProgram to evaluate
        train_examples: List of dicts with 'input' and 'output' keys
        operation_map: Operation implementations

    Returns:
        Fitness score (0.0 to 1.0)
    """
    import numpy as np

    if not train_examples or len(program) == 0:
        return 0.0

    total_similarity = 0.0

    for example in train_examples:
        input_grid = np.array(example['input'])
        expected_output = np.array(example['output'])

        try:
            predicted = program.execute(input_grid, operation_map)

            # Compute similarity
            if predicted.shape == expected_output.shape:
                matches = np.sum(predicted == expected_output)
                total = predicted.size
                similarity = matches / total
            else:
                similarity = 0.0

            total_similarity += similarity
        except Exception as e:
            # Execution failed
            total_similarity += 0.0

    # Average similarity
    fitness = total_similarity / len(train_examples)

    # Small complexity penalty
    complexity_penalty = 0.01 * len(program)

    return max(0.0, fitness - complexity_penalty)


def solve_via_template_transfer(task: Dict,
                                constraints: Dict,
                                template_learner: TemplateLearner,
                                param_learner,  # ParametricMetaLearner
                                operation_map: Dict,
                                max_attempts: int = 20) -> Optional[Tuple[ARCProgram, float]]:
    """
    Attempt to solve task via template transfer learning.

    Strategy:
    1. Get top templates
    2. For each template, get best parameters from param_learner
    3. Instantiate and evaluate
    4. Return best if above threshold

    Args:
        task: Task dict with 'train' examples
        constraints: Extracted constraints
        template_learner: TemplateLearner instance
        param_learner: ParametricMetaLearner instance
        operation_map: Operation implementations
        max_attempts: Maximum template instantiations to try

    Returns:
        (program, fitness) tuple if successful, None otherwise
    """
    templates = template_learner.suggest_template_for_task(constraints, top_k=10)

    best_program = None
    best_fitness = 0.0
    attempts = 0

    for template in templates:
        if attempts >= max_attempts:
            break

        # Get parameter suggestions for each operation
        param_options = {}
        for op_name, param_names in template.structure:
            if param_names:
                # Get top 3 parameter sets for this operation
                suggestions = param_learner.suggest_parameters(op_name, constraints, top_k=3)
                if not suggestions:
                    # No learned params - skip this template
                    param_options = None
                    break
                param_options[op_name] = suggestions
            else:
                param_options[op_name] = [{}]  # No parameters needed

        if param_options is None:
            continue

        # Try all combinations (limited by top-k)
        for param_combo in itertools.product(*param_options.values()):
            if attempts >= max_attempts:
                break

            # Build param_values dict for instantiation
            param_values = {}
            for (op_name, param_names), params in zip(template.structure, param_combo):
                for name, value in params.items():
                    param_values[f"{op_name}.{name}"] = value

            # Instantiate template
            program = template.instantiate(param_values)

            # Evaluate on training examples
            fitness = _evaluate_program(program, task['train'], operation_map)

            if fitness > best_fitness:
                best_fitness = fitness
                best_program = program

            attempts += 1

            # Early exit if solved
            if fitness >= 0.95:
                return (program, fitness)

    # Return best found (might be None)
    if best_program and best_fitness >= 0.5:  # Threshold for "promising"
        return (best_program, best_fitness)

    return None
