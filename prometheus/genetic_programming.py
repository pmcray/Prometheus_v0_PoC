"""
Genetic Programming Framework v0.1 (v0.56)
Advanced evolutionary search for code optimization and improvement

Implements genetic programming techniques for evolving code solutions:
- AST-based code representation and manipulation
- Genetic operators for crossover and mutation
- Population-based evolution strategies
- Fitness evaluation integration with benchmark system
"""

import ast
import copy
import random
import hashlib
import statistics
from typing import Dict, List, Any, Optional, Tuple, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

@dataclass
class CodeGenome:
    """Represents a piece of code as an evolutionary genome"""
    genome_id: str
    code_ast: ast.AST
    source_code: str
    fitness_score: Optional[float] = None
    generation: int = 0
    parent_ids: List[str] = None
    mutation_history: List[str] = None
    creation_method: str = "initial"  # "initial", "crossover", "mutation"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.parent_ids is None:
            self.parent_ids = []
        if self.mutation_history is None:
            self.mutation_history = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class EvolutionResult:
    """Result of evolutionary search process"""
    best_genome: CodeGenome
    final_population: List[CodeGenome]
    generation_count: int
    fitness_history: List[float]
    convergence_info: Dict[str, Any]
    evolution_time_seconds: float

class ASTMutator:
    """Performs mutations on Abstract Syntax Trees"""

    def __init__(self, mutation_rate: float = 0.1):
        self.mutation_rate = mutation_rate
        self.mutation_operators = [
            self._mutate_binary_operator,
            self._mutate_comparison_operator,
            self._mutate_constant,
            self._mutate_variable_name,
            self._mutate_function_call,
            self._insert_statement,
            self._delete_statement,
            self._swap_statements
        ]

    def mutate(self, code_ast: ast.AST) -> Tuple[ast.AST, List[str]]:
        """Apply random mutations to the AST"""
        mutated_ast = copy.deepcopy(code_ast)
        mutations_applied = []

        # Apply mutations with probability
        for node in ast.walk(mutated_ast):
            if random.random() < self.mutation_rate:
                mutation_op = random.choice(self.mutation_operators)
                try:
                    if mutation_op(node):
                        mutations_applied.append(mutation_op.__name__)
                except Exception:
                    continue  # Skip failed mutations

        return mutated_ast, mutations_applied

    def _mutate_binary_operator(self, node: ast.AST) -> bool:
        """Mutate binary operators (+, -, *, /, etc.)"""
        if isinstance(node, ast.BinOp):
            operators = [ast.Add(), ast.Sub(), ast.Mult(), ast.Div(),
                        ast.Mod(), ast.Pow(), ast.FloorDiv()]
            if type(node.op) in [type(op) for op in operators]:
                node.op = random.choice(operators)
                return True
        return False

    def _mutate_comparison_operator(self, node: ast.AST) -> bool:
        """Mutate comparison operators (<, >, ==, etc.)"""
        if isinstance(node, ast.Compare) and node.ops:
            operators = [ast.Lt(), ast.LtE(), ast.Gt(), ast.GtE(),
                        ast.Eq(), ast.NotEq()]
            for i, op in enumerate(node.ops):
                if type(op) in [type(o) for o in operators]:
                    node.ops[i] = random.choice(operators)
                    return True
        return False

    def _mutate_constant(self, node: ast.AST) -> bool:
        """Mutate numeric constants"""
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            if isinstance(node.value, int):
                # Small integer mutations
                node.value += random.randint(-2, 2)
            else:
                # Small float mutations
                node.value *= random.uniform(0.8, 1.2)
            return True
        return False

    def _mutate_variable_name(self, node: ast.AST) -> bool:
        """Mutate variable names (carefully to avoid breaking scope)"""
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            # Only mutate common variable names to avoid scope issues
            common_vars = ['i', 'j', 'k', 'x', 'y', 'z', 'temp', 'result']
            if node.id in common_vars:
                node.id = random.choice(common_vars)
                return True
        return False

    def _mutate_function_call(self, node: ast.AST) -> bool:
        """Mutate function calls (limited to safe functions)"""
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            safe_functions = ['min', 'max', 'abs', 'len', 'sum', 'sorted']
            if node.func.id in safe_functions:
                node.func.id = random.choice(safe_functions)
                return True
        return False

    def _insert_statement(self, node: ast.AST) -> bool:
        """Insert a simple statement"""
        if isinstance(node, ast.FunctionDef) and hasattr(node, 'body'):
            # Insert a simple pass or assignment statement
            if random.random() < 0.5:
                new_stmt = ast.Pass()
            else:
                new_stmt = ast.Assign(
                    targets=[ast.Name(id='temp', ctx=ast.Store())],
                    value=ast.Constant(value=0)
                )

            insert_pos = random.randint(0, len(node.body))
            node.body.insert(insert_pos, new_stmt)
            return True
        return False

    def _delete_statement(self, node: ast.AST) -> bool:
        """Delete a statement (if safe to do so)"""
        if isinstance(node, ast.FunctionDef) and len(node.body) > 1:
            # Only delete pass statements or assignments to temp variables
            for i, stmt in enumerate(node.body):
                if (isinstance(stmt, ast.Pass) or
                    (isinstance(stmt, ast.Assign) and
                     len(stmt.targets) == 1 and
                     isinstance(stmt.targets[0], ast.Name) and
                     stmt.targets[0].id.startswith('temp'))):
                    del node.body[i]
                    return True
        return False

    def _swap_statements(self, node: ast.AST) -> bool:
        """Swap two adjacent statements"""
        if isinstance(node, ast.FunctionDef) and len(node.body) >= 2:
            i = random.randint(0, len(node.body) - 2)
            node.body[i], node.body[i + 1] = node.body[i + 1], node.body[i]
            return True
        return False

class ASTCrossover:
    """Performs crossover operations between ASTs"""

    def __init__(self):
        pass

    def crossover(self, parent1_ast: ast.AST, parent2_ast: ast.AST) -> Tuple[ast.AST, ast.AST]:
        """Perform crossover between two ASTs"""
        child1 = copy.deepcopy(parent1_ast)
        child2 = copy.deepcopy(parent2_ast)

        # Find crossover points in both ASTs
        crossover_points1 = self._find_crossover_points(child1)
        crossover_points2 = self._find_crossover_points(child2)

        if crossover_points1 and crossover_points2:
            # Select random crossover points
            point1 = random.choice(crossover_points1)
            point2 = random.choice(crossover_points2)

            # Perform subtree crossover
            self._swap_subtrees(child1, child2, point1, point2)

        return child1, child2

    def _find_crossover_points(self, ast_node: ast.AST) -> List[ast.AST]:
        """Find suitable crossover points in the AST"""
        crossover_points = []

        for node in ast.walk(ast_node):
            # Look for expressions and statements that can be swapped
            if isinstance(node, (ast.expr, ast.stmt)) and not isinstance(node, ast.Module):
                crossover_points.append(node)

        return crossover_points

    def _swap_subtrees(self, ast1: ast.AST, ast2: ast.AST, point1: ast.AST, point2: ast.AST):
        """Swap subtrees at the specified points"""
        # This is a simplified implementation
        # In practice, this requires careful handling of AST structure
        try:
            # Find parent nodes and field names for the crossover points
            parent1, field1, index1 = self._find_parent_info(ast1, point1)
            parent2, field2, index2 = self._find_parent_info(ast2, point2)

            if parent1 and parent2 and field1 and field2:
                # Swap the nodes
                if index1 is not None and index2 is not None:
                    # Handle list fields
                    getattr(parent1, field1)[index1], getattr(parent2, field2)[index2] = \
                        getattr(parent2, field2)[index2], getattr(parent1, field1)[index1]
                else:
                    # Handle single fields
                    setattr(parent1, field1, getattr(parent2, field2))
                    setattr(parent2, field2, point1)
        except Exception:
            # Crossover failed, keep original ASTs
            pass

    def _find_parent_info(self, root: ast.AST, target: ast.AST) -> Tuple[Optional[ast.AST], Optional[str], Optional[int]]:
        """Find parent node, field name, and index for a given node"""
        for parent in ast.walk(root):
            for field, value in ast.iter_fields(parent):
                if value == target:
                    return parent, field, None
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if item == target:
                            return parent, field, i
        return None, None, None

class GeneticProgrammingEngine:
    """Main genetic programming engine for code evolution"""

    def __init__(self,
                 population_size: int = 50,
                 mutation_rate: float = 0.1,
                 crossover_rate: float = 0.7,
                 elite_size: int = 5,
                 fitness_evaluator: Optional[Callable[[str], float]] = None):

        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_size = elite_size
        self.fitness_evaluator = fitness_evaluator

        self.mutator = ASTMutator(mutation_rate)
        self.crossover = ASTCrossover()

        self.generation = 0
        self.population: List[CodeGenome] = []
        self.fitness_history: List[float] = []

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def initialize_population(self, seed_code: str, variations: int = None) -> List[CodeGenome]:
        """Initialize the population with variations of seed code"""
        if variations is None:
            variations = self.population_size

        self.logger.info(f"🧬 Initializing population with {variations} variations")

        try:
            seed_ast = ast.parse(seed_code)
        except SyntaxError as e:
            raise ValueError(f"Invalid seed code: {e}")

        population = []

        # Add the original seed
        seed_genome = CodeGenome(
            genome_id=self._generate_genome_id(seed_code),
            code_ast=copy.deepcopy(seed_ast),
            source_code=seed_code,
            generation=0,
            creation_method="seed"
        )
        population.append(seed_genome)

        # Generate variations through mutation
        for i in range(variations - 1):
            mutated_ast, mutations = self.mutator.mutate(seed_ast)

            try:
                mutated_code = ast.unparse(mutated_ast)

                genome = CodeGenome(
                    genome_id=self._generate_genome_id(mutated_code),
                    code_ast=mutated_ast,
                    source_code=mutated_code,
                    generation=0,
                    creation_method="mutation",
                    mutation_history=mutations,
                    parent_ids=[seed_genome.genome_id]
                )
                population.append(genome)

            except Exception:
                # Skip invalid mutations
                continue

        self.population = population[:self.population_size]
        return self.population

    def evaluate_fitness(self, population: List[CodeGenome]) -> List[CodeGenome]:
        """Evaluate fitness for all genomes in the population"""
        self.logger.info(f"🏃 Evaluating fitness for {len(population)} genomes")

        for genome in population:
            if genome.fitness_score is None:  # Only evaluate if not already done
                if self.fitness_evaluator:
                    try:
                        genome.fitness_score = self.fitness_evaluator(genome.source_code)
                    except Exception as e:
                        genome.fitness_score = 0.0  # Penalize invalid code
                else:
                    # Default fitness based on code complexity and length
                    genome.fitness_score = self._default_fitness(genome.source_code)

        # Sort by fitness (higher is better)
        population.sort(key=lambda g: g.fitness_score or 0.0, reverse=True)
        return population

    def selection(self, population: List[CodeGenome]) -> List[CodeGenome]:
        """Select parents for the next generation using tournament selection"""
        tournament_size = max(3, len(population) // 10)
        selected = []

        # Elite selection - always keep the best
        selected.extend(population[:self.elite_size])

        # Tournament selection for the rest
        while len(selected) < self.population_size:
            tournament = random.sample(population, min(tournament_size, len(population)))
            winner = max(tournament, key=lambda g: g.fitness_score or 0.0)
            selected.append(winner)

        return selected[:self.population_size]

    def crossover_and_mutation(self, parents: List[CodeGenome]) -> List[CodeGenome]:
        """Create next generation through crossover and mutation"""
        next_generation = []

        # Keep elite individuals
        next_generation.extend(parents[:self.elite_size])

        # Generate offspring
        while len(next_generation) < self.population_size:
            parent1 = random.choice(parents)
            parent2 = random.choice(parents)

            # Crossover
            if random.random() < self.crossover_rate:
                child1_ast, child2_ast = self.crossover.crossover(parent1.code_ast, parent2.code_ast)

                # Create child genomes
                for child_ast, parents_used in [(child1_ast, [parent1, parent2]), (child2_ast, [parent2, parent1])]:
                    try:
                        child_code = ast.unparse(child_ast)

                        # Apply mutation
                        if random.random() < self.mutation_rate:
                            child_ast, mutations = self.mutator.mutate(child_ast)
                            child_code = ast.unparse(child_ast)
                            creation_method = "crossover_mutation"
                        else:
                            mutations = []
                            creation_method = "crossover"

                        child_genome = CodeGenome(
                            genome_id=self._generate_genome_id(child_code),
                            code_ast=child_ast,
                            source_code=child_code,
                            generation=self.generation + 1,
                            parent_ids=[p.genome_id for p in parents_used],
                            mutation_history=mutations,
                            creation_method=creation_method
                        )

                        next_generation.append(child_genome)

                        if len(next_generation) >= self.population_size:
                            break

                    except Exception:
                        # Skip invalid offspring
                        continue
            else:
                # Just mutation
                mutated_ast, mutations = self.mutator.mutate(parent1.code_ast)

                try:
                    mutated_code = ast.unparse(mutated_ast)

                    child_genome = CodeGenome(
                        genome_id=self._generate_genome_id(mutated_code),
                        code_ast=mutated_ast,
                        source_code=mutated_code,
                        generation=self.generation + 1,
                        parent_ids=[parent1.genome_id],
                        mutation_history=mutations,
                        creation_method="mutation"
                    )

                    next_generation.append(child_genome)

                except Exception:
                    continue

        return next_generation[:self.population_size]

    def evolve(self,
               seed_code: str,
               generations: int = 100,
               convergence_threshold: float = 0.001,
               stagnation_limit: int = 20) -> EvolutionResult:
        """Run the genetic programming evolution process"""

        start_time = datetime.now()
        self.logger.info(f"🧬 Starting GP evolution for {generations} generations")

        # Initialize population
        self.population = self.initialize_population(seed_code)

        best_fitness_history = []
        avg_fitness_history = []
        stagnation_count = 0
        last_best_fitness = 0.0

        for gen in range(generations):
            self.generation = gen

            # Evaluate fitness
            self.population = self.evaluate_fitness(self.population)

            # Track fitness statistics
            fitness_scores = [g.fitness_score for g in self.population if g.fitness_score is not None]
            if fitness_scores:
                best_fitness = max(fitness_scores)
                avg_fitness = statistics.mean(fitness_scores)

                best_fitness_history.append(best_fitness)
                avg_fitness_history.append(avg_fitness)

                # Check for convergence
                if abs(best_fitness - last_best_fitness) < convergence_threshold:
                    stagnation_count += 1
                else:
                    stagnation_count = 0

                last_best_fitness = best_fitness

                self.logger.info(f"Generation {gen}: Best={best_fitness:.4f}, Avg={avg_fitness:.4f}, Stagnation={stagnation_count}")

                # Early stopping if stagnated
                if stagnation_count >= stagnation_limit:
                    self.logger.info(f"🔄 Converged after {gen} generations (stagnation limit reached)")
                    break

            # Selection
            parents = self.selection(self.population)

            # Create next generation
            if gen < generations - 1:  # Don't create new generation on last iteration
                self.population = self.crossover_and_mutation(parents)

        # Final evaluation
        self.population = self.evaluate_fitness(self.population)
        best_genome = self.population[0] if self.population else None

        evolution_time = (datetime.now() - start_time).total_seconds()

        result = EvolutionResult(
            best_genome=best_genome,
            final_population=self.population,
            generation_count=self.generation + 1,
            fitness_history=best_fitness_history,
            convergence_info={
                "converged": stagnation_count >= stagnation_limit,
                "stagnation_count": stagnation_count,
                "final_best_fitness": last_best_fitness,
                "average_fitness_history": avg_fitness_history
            },
            evolution_time_seconds=evolution_time
        )

        self.logger.info(f"🏁 Evolution completed in {evolution_time:.1f}s")
        return result

    def _default_fitness(self, code: str) -> float:
        """Default fitness function based on code metrics"""
        try:
            # Parse and analyze the code
            tree = ast.parse(code)

            # Count different node types
            node_counts = {}
            for node in ast.walk(tree):
                node_type = type(node).__name__
                node_counts[node_type] = node_counts.get(node_type, 0) + 1

            # Simple fitness based on complexity and structure
            fitness = 1.0

            # Reward functions and classes
            fitness += node_counts.get('FunctionDef', 0) * 0.2
            fitness += node_counts.get('ClassDef', 0) * 0.3

            # Penalty for excessive complexity
            complexity = sum(node_counts.values())
            if complexity > 100:
                fitness -= (complexity - 100) * 0.01

            # Penalty for syntax errors (already handled by try/catch)

            return max(0.0, fitness)

        except Exception:
            return 0.0

    def _generate_genome_id(self, code: str) -> str:
        """Generate unique ID for a genome based on its code"""
        return hashlib.md5(code.encode()).hexdigest()[:12]

    def get_population_stats(self) -> Dict[str, Any]:
        """Get statistics about the current population"""
        if not self.population:
            return {}

        fitness_scores = [g.fitness_score for g in self.population if g.fitness_score is not None]

        if not fitness_scores:
            return {"population_size": len(self.population), "no_fitness_scores": True}

        return {
            "population_size": len(self.population),
            "generation": self.generation,
            "best_fitness": max(fitness_scores),
            "worst_fitness": min(fitness_scores),
            "average_fitness": statistics.mean(fitness_scores),
            "fitness_std": statistics.stdev(fitness_scores) if len(fitness_scores) > 1 else 0.0,
            "diversity": len(set(g.genome_id for g in self.population)),
            "creation_methods": {
                method: len([g for g in self.population if g.creation_method == method])
                for method in set(g.creation_method for g in self.population)
            }
        }