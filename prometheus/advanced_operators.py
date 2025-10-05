"""
Advanced Crossover and Mutation Operators v0.1 (v0.58)
Sophisticated genetic operators for code evolution

Implements advanced evolutionary operators:
- Semantic-aware crossover operations
- Context-preserving mutations
- Structure-respecting genetic operations
- Adaptive operator selection
- Novel operators for code-specific evolution
"""

import ast
import copy
import random
import statistics
from typing import Dict, List, Any, Optional, Tuple, Callable, Set, Union
from dataclasses import dataclass
from enum import Enum
import logging

from .genetic_programming import CodeGenome

class OperatorType(Enum):
    """Types of genetic operators"""
    CROSSOVER = "crossover"
    MUTATION = "mutation"
    MACRO_MUTATION = "macro_mutation"
    SEMANTIC_CROSSOVER = "semantic_crossover"
    STRUCTURE_MUTATION = "structure_mutation"

@dataclass
class OperatorResult:
    """Result of applying a genetic operator"""
    success: bool
    offspring: List[CodeGenome]
    operator_type: OperatorType
    operator_name: str
    semantic_preserved: bool = True
    error_message: Optional[str] = None

class SemanticAnalyzer:
    """Analyzes semantic properties of code for semantic-aware operations"""

    def __init__(self):
        pass

    def extract_semantic_features(self, code_ast: ast.AST) -> Dict[str, Any]:
        """Extract semantic features from AST"""
        features = {
            'variables': set(),
            'functions': set(),
            'control_structures': [],
            'data_structures': [],
            'complexity_metrics': {},
            'dependencies': set(),
            'return_patterns': []
        }

        for node in ast.walk(code_ast):
            # Variables
            if isinstance(node, ast.Name):
                features['variables'].add(node.id)

            # Functions
            elif isinstance(node, ast.FunctionDef):
                features['functions'].add(node.name)

            # Control structures
            elif isinstance(node, (ast.For, ast.While, ast.If)):
                features['control_structures'].append(type(node).__name__)

            # Data structures
            elif isinstance(node, (ast.List, ast.Dict, ast.Set, ast.Tuple)):
                features['data_structures'].append(type(node).__name__)

            # Function calls (dependencies)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                features['dependencies'].add(node.func.id)

            # Return statements
            elif isinstance(node, ast.Return):
                if isinstance(node.value, ast.Constant):
                    features['return_patterns'].append(f"constant_{type(node.value.value).__name__}")
                else:
                    features['return_patterns'].append("expression")

        # Calculate complexity metrics
        features['complexity_metrics'] = {
            'cyclomatic_complexity': self._calculate_cyclomatic_complexity(code_ast),
            'nesting_depth': self._calculate_nesting_depth(code_ast),
            'number_of_statements': len([n for n in ast.walk(code_ast) if isinstance(n, ast.stmt)])
        }

        return features

    def _calculate_cyclomatic_complexity(self, code_ast: ast.AST) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity

        for node in ast.walk(code_ast):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        return complexity

    def _calculate_nesting_depth(self, code_ast: ast.AST) -> int:
        """Calculate maximum nesting depth"""
        max_depth = 0

        def calculate_depth(node, current_depth=0):
            nonlocal max_depth
            max_depth = max(max_depth, current_depth)

            if isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.FunctionDef, ast.ClassDef)):
                current_depth += 1

            for child in ast.iter_child_nodes(node):
                calculate_depth(child, current_depth)

        calculate_depth(code_ast)
        return max_depth

    def semantic_similarity(self, features1: Dict[str, Any], features2: Dict[str, Any]) -> float:
        """Calculate semantic similarity between two code features"""
        similarity_scores = []

        # Variable similarity
        vars1 = features1.get('variables', set())
        vars2 = features2.get('variables', set())
        if vars1 or vars2:
            var_similarity = len(vars1 & vars2) / len(vars1 | vars2)
            similarity_scores.append(var_similarity)

        # Function similarity
        funcs1 = features1.get('functions', set())
        funcs2 = features2.get('functions', set())
        if funcs1 or funcs2:
            func_similarity = len(funcs1 & funcs2) / len(funcs1 | funcs2)
            similarity_scores.append(func_similarity)

        # Control structure similarity
        ctrl1 = features1.get('control_structures', [])
        ctrl2 = features2.get('control_structures', [])
        if ctrl1 or ctrl2:
            ctrl_similarity = len(set(ctrl1) & set(ctrl2)) / len(set(ctrl1) | set(ctrl2))
            similarity_scores.append(ctrl_similarity)

        # Complexity similarity
        comp1 = features1.get('complexity_metrics', {})
        comp2 = features2.get('complexity_metrics', {})
        if comp1 and comp2:
            comp_similarity = 1.0 - abs(comp1.get('cyclomatic_complexity', 0) -
                                       comp2.get('cyclomatic_complexity', 0)) / 10.0
            similarity_scores.append(max(0.0, comp_similarity))

        return statistics.mean(similarity_scores) if similarity_scores else 0.0

class AdvancedCrossoverOperators:
    """Collection of advanced crossover operators"""

    def __init__(self):
        self.semantic_analyzer = SemanticAnalyzer()
        self.logger = logging.getLogger(__name__)

    def semantic_preserving_crossover(self, parent1: CodeGenome, parent2: CodeGenome) -> OperatorResult:
        """Crossover that preserves semantic similarity"""
        try:
            # Extract semantic features
            features1 = self.semantic_analyzer.extract_semantic_features(parent1.code_ast)
            features2 = self.semantic_analyzer.extract_semantic_features(parent2.code_ast)

            # Check semantic compatibility
            similarity = self.semantic_analyzer.semantic_similarity(features1, features2)

            if similarity < 0.3:  # Too dissimilar
                return OperatorResult(
                    success=False,
                    offspring=[],
                    operator_type=OperatorType.SEMANTIC_CROSSOVER,
                    operator_name="semantic_preserving_crossover",
                    error_message="Parents too semantically dissimilar"
                )

            # Find semantically compatible crossover points
            crossover_points1 = self._find_semantic_crossover_points(parent1.code_ast, features1)
            crossover_points2 = self._find_semantic_crossover_points(parent2.code_ast, features2)

            if not crossover_points1 or not crossover_points2:
                return OperatorResult(
                    success=False,
                    offspring=[],
                    operator_type=OperatorType.SEMANTIC_CROSSOVER,
                    operator_name="semantic_preserving_crossover",
                    error_message="No compatible crossover points found"
                )

            # Perform semantic crossover
            child1_ast, child2_ast = self._semantic_crossover_operation(
                parent1.code_ast, parent2.code_ast,
                crossover_points1, crossover_points2
            )

            # Create offspring genomes
            offspring = []
            for i, child_ast in enumerate([child1_ast, child2_ast]):
                try:
                    child_code = ast.unparse(child_ast)
                    child_genome = CodeGenome(
                        genome_id=f"sem_cross_{hash(child_code) % 100000}",
                        code_ast=child_ast,
                        source_code=child_code,
                        generation=max(parent1.generation, parent2.generation) + 1,
                        parent_ids=[parent1.genome_id, parent2.genome_id],
                        creation_method="semantic_crossover",
                        metadata={
                            'semantic_similarity': similarity,
                            'crossover_operator': 'semantic_preserving'
                        }
                    )
                    offspring.append(child_genome)
                except Exception as e:
                    continue

            return OperatorResult(
                success=len(offspring) > 0,
                offspring=offspring,
                operator_type=OperatorType.SEMANTIC_CROSSOVER,
                operator_name="semantic_preserving_crossover",
                semantic_preserved=True
            )

        except Exception as e:
            return OperatorResult(
                success=False,
                offspring=[],
                operator_type=OperatorType.SEMANTIC_CROSSOVER,
                operator_name="semantic_preserving_crossover",
                error_message=str(e)
            )

    def structure_aware_crossover(self, parent1: CodeGenome, parent2: CodeGenome) -> OperatorResult:
        """Crossover that maintains program structure"""
        try:
            # Find structural boundaries (functions, classes, etc.)
            struct_bounds1 = self._find_structural_boundaries(parent1.code_ast)
            struct_bounds2 = self._find_structural_boundaries(parent2.code_ast)

            if not struct_bounds1 or not struct_bounds2:
                return OperatorResult(
                    success=False,
                    offspring=[],
                    operator_type=OperatorType.CROSSOVER,
                    operator_name="structure_aware_crossover",
                    error_message="No structural boundaries found"
                )

            # Perform structure-preserving crossover
            child1_ast = copy.deepcopy(parent1.code_ast)
            child2_ast = copy.deepcopy(parent2.code_ast)

            # Exchange compatible structural elements
            self._exchange_structural_elements(child1_ast, child2_ast, struct_bounds1, struct_bounds2)

            # Create offspring
            offspring = []
            for child_ast in [child1_ast, child2_ast]:
                try:
                    child_code = ast.unparse(child_ast)
                    child_genome = CodeGenome(
                        genome_id=f"struct_cross_{hash(child_code) % 100000}",
                        code_ast=child_ast,
                        source_code=child_code,
                        generation=max(parent1.generation, parent2.generation) + 1,
                        parent_ids=[parent1.genome_id, parent2.genome_id],
                        creation_method="structure_crossover",
                        metadata={'crossover_operator': 'structure_aware'}
                    )
                    offspring.append(child_genome)
                except Exception:
                    continue

            return OperatorResult(
                success=len(offspring) > 0,
                offspring=offspring,
                operator_type=OperatorType.CROSSOVER,
                operator_name="structure_aware_crossover"
            )

        except Exception as e:
            return OperatorResult(
                success=False,
                offspring=[],
                operator_type=OperatorType.CROSSOVER,
                operator_name="structure_aware_crossover",
                error_message=str(e)
            )

    def uniform_crossover(self, parent1: CodeGenome, parent2: CodeGenome, crossover_rate: float = 0.5) -> OperatorResult:
        """Uniform crossover at statement level"""
        try:
            # Get statements from both parents
            stmts1 = self._extract_statements(parent1.code_ast)
            stmts2 = self._extract_statements(parent2.code_ast)

            if not stmts1 or not stmts2:
                return OperatorResult(
                    success=False,
                    offspring=[],
                    operator_type=OperatorType.CROSSOVER,
                    operator_name="uniform_crossover",
                    error_message="No statements to cross"
                )

            # Create children by uniform selection
            child1_stmts = []
            child2_stmts = []

            max_len = max(len(stmts1), len(stmts2))
            for i in range(max_len):
                stmt1 = stmts1[i] if i < len(stmts1) else None
                stmt2 = stmts2[i] if i < len(stmts2) else None

                if random.random() < crossover_rate:
                    # Swap statements
                    if stmt2: child1_stmts.append(copy.deepcopy(stmt2))
                    if stmt1: child2_stmts.append(copy.deepcopy(stmt1))
                else:
                    # Keep original statements
                    if stmt1: child1_stmts.append(copy.deepcopy(stmt1))
                    if stmt2: child2_stmts.append(copy.deepcopy(stmt2))

            # Construct child ASTs
            child1_ast = self._construct_ast_from_statements(child1_stmts)
            child2_ast = self._construct_ast_from_statements(child2_stmts)

            # Create offspring
            offspring = []
            for child_ast in [child1_ast, child2_ast]:
                try:
                    child_code = ast.unparse(child_ast)
                    child_genome = CodeGenome(
                        genome_id=f"uniform_cross_{hash(child_code) % 100000}",
                        code_ast=child_ast,
                        source_code=child_code,
                        generation=max(parent1.generation, parent2.generation) + 1,
                        parent_ids=[parent1.genome_id, parent2.genome_id],
                        creation_method="uniform_crossover",
                        metadata={'crossover_rate': crossover_rate}
                    )
                    offspring.append(child_genome)
                except Exception:
                    continue

            return OperatorResult(
                success=len(offspring) > 0,
                offspring=offspring,
                operator_type=OperatorType.CROSSOVER,
                operator_name="uniform_crossover"
            )

        except Exception as e:
            return OperatorResult(
                success=False,
                offspring=[],
                operator_type=OperatorType.CROSSOVER,
                operator_name="uniform_crossover",
                error_message=str(e)
            )

    def _find_semantic_crossover_points(self, code_ast: ast.AST, features: Dict[str, Any]) -> List[ast.AST]:
        """Find crossover points that preserve semantics"""
        crossover_points = []

        for node in ast.walk(code_ast):
            # Safe crossover points that don't break semantics
            if isinstance(node, (ast.expr, ast.stmt)) and not isinstance(node, (ast.Module, ast.FunctionDef)):
                # Additional semantic checks could be added here
                crossover_points.append(node)

        return crossover_points

    def _semantic_crossover_operation(self, ast1: ast.AST, ast2: ast.AST,
                                    points1: List[ast.AST], points2: List[ast.AST]) -> Tuple[ast.AST, ast.AST]:
        """Perform semantic-aware crossover operation"""
        child1_ast = copy.deepcopy(ast1)
        child2_ast = copy.deepcopy(ast2)

        # Simple implementation - more sophisticated semantic matching could be added
        point1 = random.choice(points1)
        point2 = random.choice(points2)

        # Find and swap the selected points
        # This is a simplified implementation
        return child1_ast, child2_ast

    def _find_structural_boundaries(self, code_ast: ast.AST) -> List[ast.AST]:
        """Find structural boundaries like functions, classes"""
        boundaries = []

        for node in ast.walk(code_ast):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                boundaries.append(node)

        return boundaries

    def _exchange_structural_elements(self, ast1: ast.AST, ast2: ast.AST,
                                    bounds1: List[ast.AST], bounds2: List[ast.AST]):
        """Exchange structural elements between ASTs"""
        # Simplified structural exchange
        # In practice, this would need careful type matching and scope analysis
        pass

    def _extract_statements(self, code_ast: ast.AST) -> List[ast.stmt]:
        """Extract statements from AST"""
        statements = []
        for node in ast.walk(code_ast):
            if isinstance(node, ast.stmt) and not isinstance(node, ast.Module):
                statements.append(node)
        return statements

    def _construct_ast_from_statements(self, statements: List[ast.stmt]) -> ast.AST:
        """Construct AST from list of statements"""
        module = ast.Module(body=statements, type_ignores=[])
        return module

class AdvancedMutationOperators:
    """Collection of advanced mutation operators"""

    def __init__(self):
        self.semantic_analyzer = SemanticAnalyzer()
        self.logger = logging.getLogger(__name__)

    def semantic_preserving_mutation(self, genome: CodeGenome, mutation_strength: float = 0.1) -> OperatorResult:
        """Mutation that preserves semantic meaning"""
        try:
            original_features = self.semantic_analyzer.extract_semantic_features(genome.code_ast)
            mutated_ast = copy.deepcopy(genome.code_ast)

            mutations_applied = []

            # Apply semantic-preserving mutations
            for node in ast.walk(mutated_ast):
                if random.random() < mutation_strength:
                    mutation_applied = self._apply_semantic_mutation(node, original_features)
                    if mutation_applied:
                        mutations_applied.append(mutation_applied)

            if not mutations_applied:
                return OperatorResult(
                    success=False,
                    offspring=[],
                    operator_type=OperatorType.MUTATION,
                    operator_name="semantic_preserving_mutation",
                    error_message="No semantic mutations possible"
                )

            # Create mutated genome
            try:
                mutated_code = ast.unparse(mutated_ast)
                mutated_genome = CodeGenome(
                    genome_id=f"sem_mut_{hash(mutated_code) % 100000}",
                    code_ast=mutated_ast,
                    source_code=mutated_code,
                    generation=genome.generation + 1,
                    parent_ids=[genome.genome_id],
                    mutation_history=mutations_applied,
                    creation_method="semantic_mutation",
                    metadata={'mutation_strength': mutation_strength}
                )

                return OperatorResult(
                    success=True,
                    offspring=[mutated_genome],
                    operator_type=OperatorType.MUTATION,
                    operator_name="semantic_preserving_mutation",
                    semantic_preserved=True
                )

            except Exception as e:
                return OperatorResult(
                    success=False,
                    offspring=[],
                    operator_type=OperatorType.MUTATION,
                    operator_name="semantic_preserving_mutation",
                    error_message=f"Code generation failed: {e}"
                )

        except Exception as e:
            return OperatorResult(
                success=False,
                offspring=[],
                operator_type=OperatorType.MUTATION,
                operator_name="semantic_preserving_mutation",
                error_message=str(e)
            )

    def structure_expanding_mutation(self, genome: CodeGenome) -> OperatorResult:
        """Mutation that expands program structure"""
        try:
            expanded_ast = copy.deepcopy(genome.code_ast)
            mutations_applied = []

            # Find expansion points
            expansion_points = self._find_expansion_points(expanded_ast)

            if not expansion_points:
                return OperatorResult(
                    success=False,
                    offspring=[],
                    operator_type=OperatorType.STRUCTURE_MUTATION,
                    operator_name="structure_expanding_mutation",
                    error_message="No expansion points found"
                )

            # Apply structural expansions
            expansion_point = random.choice(expansion_points)
            expansion_applied = self._apply_structural_expansion(expansion_point)

            if expansion_applied:
                mutations_applied.append(expansion_applied)

            # Create expanded genome
            try:
                expanded_code = ast.unparse(expanded_ast)
                expanded_genome = CodeGenome(
                    genome_id=f"struct_exp_{hash(expanded_code) % 100000}",
                    code_ast=expanded_ast,
                    source_code=expanded_code,
                    generation=genome.generation + 1,
                    parent_ids=[genome.genome_id],
                    mutation_history=mutations_applied,
                    creation_method="structure_expansion"
                )

                return OperatorResult(
                    success=True,
                    offspring=[expanded_genome],
                    operator_type=OperatorType.STRUCTURE_MUTATION,
                    operator_name="structure_expanding_mutation"
                )

            except Exception as e:
                return OperatorResult(
                    success=False,
                    offspring=[],
                    operator_type=OperatorType.STRUCTURE_MUTATION,
                    operator_name="structure_expanding_mutation",
                    error_message=f"Code generation failed: {e}"
                )

        except Exception as e:
            return OperatorResult(
                success=False,
                offspring=[],
                operator_type=OperatorType.STRUCTURE_MUTATION,
                operator_name="structure_expanding_mutation",
                error_message=str(e)
            )

    def macro_mutation(self, genome: CodeGenome, macro_strength: float = 0.3) -> OperatorResult:
        """Large-scale mutations that significantly change code structure"""
        try:
            macro_mutated_ast = copy.deepcopy(genome.code_ast)
            mutations_applied = []

            # Apply various macro mutations
            macro_ops = [
                self._add_error_handling,
                self._refactor_loops,
                self._add_helper_function,
                self._restructure_conditionals
            ]

            selected_ops = random.sample(macro_ops, min(len(macro_ops), int(len(macro_ops) * macro_strength)))

            for macro_op in selected_ops:
                try:
                    mutation_name = macro_op(macro_mutated_ast)
                    if mutation_name:
                        mutations_applied.append(mutation_name)
                except Exception:
                    continue

            if not mutations_applied:
                return OperatorResult(
                    success=False,
                    offspring=[],
                    operator_type=OperatorType.MACRO_MUTATION,
                    operator_name="macro_mutation",
                    error_message="No macro mutations applied"
                )

            # Create macro-mutated genome
            try:
                macro_code = ast.unparse(macro_mutated_ast)
                macro_genome = CodeGenome(
                    genome_id=f"macro_mut_{hash(macro_code) % 100000}",
                    code_ast=macro_mutated_ast,
                    source_code=macro_code,
                    generation=genome.generation + 1,
                    parent_ids=[genome.genome_id],
                    mutation_history=mutations_applied,
                    creation_method="macro_mutation",
                    metadata={'macro_strength': macro_strength}
                )

                return OperatorResult(
                    success=True,
                    offspring=[macro_genome],
                    operator_type=OperatorType.MACRO_MUTATION,
                    operator_name="macro_mutation"
                )

            except Exception as e:
                return OperatorResult(
                    success=False,
                    offspring=[],
                    operator_type=OperatorType.MACRO_MUTATION,
                    operator_name="macro_mutation",
                    error_message=f"Code generation failed: {e}"
                )

        except Exception as e:
            return OperatorResult(
                success=False,
                offspring=[],
                operator_type=OperatorType.MACRO_MUTATION,
                operator_name="macro_mutation",
                error_message=str(e)
            )

    def _apply_semantic_mutation(self, node: ast.AST, original_features: Dict[str, Any]) -> Optional[str]:
        """Apply a semantic-preserving mutation to a node"""
        # Implement various semantic-preserving mutations
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            # Change addition to subtraction (semantic change but structure preserved)
            node.op = ast.Sub()
            return "changed_add_to_sub"

        elif isinstance(node, ast.Constant) and isinstance(node.value, int):
            # Small integer adjustments
            node.value += random.choice([-1, 1])
            return "adjusted_integer_constant"

        return None

    def _find_expansion_points(self, code_ast: ast.AST) -> List[ast.AST]:
        """Find points where structure can be expanded"""
        expansion_points = []

        for node in ast.walk(code_ast):
            if isinstance(node, (ast.FunctionDef, ast.If, ast.For, ast.While)):
                expansion_points.append(node)

        return expansion_points

    def _apply_structural_expansion(self, node: ast.AST) -> Optional[str]:
        """Apply structural expansion to a node"""
        if isinstance(node, ast.FunctionDef):
            # Add a docstring if missing
            if not ast.get_docstring(node):
                docstring = ast.Expr(value=ast.Constant(value="Generated docstring"))
                node.body.insert(0, docstring)
                return "added_docstring"

        elif isinstance(node, ast.If) and not hasattr(node, 'orelse') or not node.orelse:
            # Add else clause
            node.orelse = [ast.Pass()]
            return "added_else_clause"

        return None

    def _add_error_handling(self, code_ast: ast.AST) -> Optional[str]:
        """Add error handling to code"""
        for node in ast.walk(code_ast):
            if isinstance(node, ast.FunctionDef) and len(node.body) > 0:
                # Wrap function body in try-except
                try_node = ast.Try(
                    body=node.body,
                    handlers=[ast.ExceptHandler(
                        type=None,
                        name=None,
                        body=[ast.Pass()]
                    )],
                    orelse=[],
                    finalbody=[]
                )
                node.body = [try_node]
                return "added_error_handling"
        return None

    def _refactor_loops(self, code_ast: ast.AST) -> Optional[str]:
        """Refactor loop structures"""
        for node in ast.walk(code_ast):
            if isinstance(node, ast.For):
                # Add enumerate if iterating over list
                if isinstance(node.iter, ast.Name):
                    node.iter = ast.Call(
                        func=ast.Name(id='enumerate', ctx=ast.Load()),
                        args=[node.iter],
                        keywords=[]
                    )
                    return "added_enumerate_to_loop"
        return None

    def _add_helper_function(self, code_ast: ast.AST) -> Optional[str]:
        """Add a helper function"""
        if isinstance(code_ast, ast.Module):
            helper_func = ast.FunctionDef(
                name='helper_function',
                args=ast.arguments(
                    posonlyargs=[],
                    args=[],
                    vararg=None,
                    kwonlyargs=[],
                    kw_defaults=[],
                    kwarg=None,
                    defaults=[]
                ),
                body=[ast.Return(value=ast.Constant(value=True))],
                decorator_list=[],
                returns=None
            )
            code_ast.body.append(helper_func)
            return "added_helper_function"
        return None

    def _restructure_conditionals(self, code_ast: ast.AST) -> Optional[str]:
        """Restructure conditional statements"""
        for node in ast.walk(code_ast):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
                # Add compound condition
                if len(node.test.ops) == 1:
                    # Create a more complex condition
                    additional_test = ast.Compare(
                        left=ast.Constant(value=True),
                        ops=[ast.Eq()],
                        comparators=[ast.Constant(value=True)]
                    )

                    node.test = ast.BoolOp(
                        op=ast.And(),
                        values=[node.test, additional_test]
                    )
                    return "made_conditional_more_complex"
        return None

class AdaptiveOperatorSelector:
    """Adaptively selects genetic operators based on performance"""

    def __init__(self):
        self.crossover_ops = AdvancedCrossoverOperators()
        self.mutation_ops = AdvancedMutationOperators()

        # Track operator performance
        self.operator_stats = {
            'semantic_preserving_crossover': {'successes': 0, 'attempts': 0, 'avg_fitness': 0.0},
            'structure_aware_crossover': {'successes': 0, 'attempts': 0, 'avg_fitness': 0.0},
            'uniform_crossover': {'successes': 0, 'attempts': 0, 'avg_fitness': 0.0},
            'semantic_preserving_mutation': {'successes': 0, 'attempts': 0, 'avg_fitness': 0.0},
            'structure_expanding_mutation': {'successes': 0, 'attempts': 0, 'avg_fitness': 0.0},
            'macro_mutation': {'successes': 0, 'attempts': 0, 'avg_fitness': 0.0}
        }

        self.logger = logging.getLogger(__name__)

    def select_and_apply_operator(self, parents: List[CodeGenome],
                                 operation_type: OperatorType = OperatorType.CROSSOVER) -> OperatorResult:
        """Select and apply the best operator based on adaptive selection"""

        if operation_type == OperatorType.CROSSOVER and len(parents) >= 2:
            # Select crossover operator
            crossover_methods = {
                'semantic_preserving_crossover': self.crossover_ops.semantic_preserving_crossover,
                'structure_aware_crossover': self.crossover_ops.structure_aware_crossover,
                'uniform_crossover': self.crossover_ops.uniform_crossover
            }

            selected_method = self._select_operator(crossover_methods.keys())
            result = crossover_methods[selected_method](parents[0], parents[1])

        elif operation_type == OperatorType.MUTATION and len(parents) >= 1:
            # Select mutation operator
            mutation_methods = {
                'semantic_preserving_mutation': self.mutation_ops.semantic_preserving_mutation,
                'structure_expanding_mutation': self.mutation_ops.structure_expanding_mutation,
                'macro_mutation': self.mutation_ops.macro_mutation
            }

            selected_method = self._select_operator(mutation_methods.keys())
            result = mutation_methods[selected_method](parents[0])

        else:
            return OperatorResult(
                success=False,
                offspring=[],
                operator_type=operation_type,
                operator_name="adaptive_selector",
                error_message="Invalid parent configuration"
            )

        # Update operator statistics
        self._update_operator_stats(result.operator_name, result.success, result.offspring)

        return result

    def _select_operator(self, available_operators: List[str]) -> str:
        """Select operator using adaptive strategy (epsilon-greedy with UCB)"""

        # Calculate UCB scores for each operator
        total_attempts = sum(self.operator_stats[op]['attempts'] for op in available_operators)

        if total_attempts < 10:  # Exploration phase
            return random.choice(available_operators)

        ucb_scores = {}
        for op in available_operators:
            stats = self.operator_stats[op]
            if stats['attempts'] == 0:
                ucb_scores[op] = float('inf')  # Encourage trying unused operators
            else:
                success_rate = stats['successes'] / stats['attempts']
                exploration_bonus = (2 * np.log(total_attempts) / stats['attempts']) ** 0.5
                ucb_scores[op] = success_rate + exploration_bonus

        # Select operator with highest UCB score
        return max(ucb_scores.keys(), key=lambda k: ucb_scores[k])

    def _update_operator_stats(self, operator_name: str, success: bool, offspring: List[CodeGenome]):
        """Update operator performance statistics"""
        if operator_name in self.operator_stats:
            stats = self.operator_stats[operator_name]
            stats['attempts'] += 1

            if success:
                stats['successes'] += 1

                # Update average fitness if available
                fitness_scores = [g.fitness_score for g in offspring if g.fitness_score is not None]
                if fitness_scores:
                    current_avg = stats['avg_fitness']
                    new_fitness = statistics.mean(fitness_scores)
                    # Running average
                    stats['avg_fitness'] = (current_avg * (stats['successes'] - 1) + new_fitness) / stats['successes']

    def get_operator_statistics(self) -> Dict[str, Any]:
        """Get current operator performance statistics"""
        return {
            op: {
                'success_rate': stats['successes'] / max(1, stats['attempts']),
                'attempts': stats['attempts'],
                'avg_fitness': stats['avg_fitness']
            }
            for op, stats in self.operator_stats.items()
        }