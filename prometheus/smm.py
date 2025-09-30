"""
Self-Modification Module (SMM) - EvolutionaryOrchestratorAgent

Implements the core recursive self-improvement loop through evolutionary algorithms.
Orchestrates mutation, crossover, selection, and evaluation of agent populations.

Based on Project Prometheus v0.29, v0.65-v0.69 workplans.
"""

import logging
import random
import copy
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from .llm_backend import get_llm_backend
from .gene_archive import GeneArchive
from .domain_expert_agent import DomainExpertAgent


@dataclass
class EvolutionConfig:
    """Configuration for evolutionary run."""
    population_size: int = 10
    generations: int = 20
    mutation_rate: float = 0.6  # Probability of mutation vs crossover
    elitism_count: int = 2  # Top N individuals to preserve
    tournament_size: int = 3  # Tournament selection size
    max_code_length: int = 5000  # Maximum characters in agent code
    min_fitness_threshold: float = 0.0  # Minimum acceptable fitness
    convergence_threshold: float = 0.95  # Stop if best reaches this fitness
    stagnation_generations: int = 5  # Stop if no improvement for N generations


class EvolutionaryOrchestratorAgent:
    """
    The Self-Modification Module (SMM).

    Orchestrates the evolutionary process:
    1. Initialize population of DomainExpertAgent instances
    2. Evaluate fitness using IEE
    3. Select parents
    4. Apply mutation/crossover operators
    5. Repeat until convergence or max generations

    This is the "engine" that was missing from v0.69.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[EvolutionConfig] = None,
        prefer_local: bool = True,
        ollama_model: str = "qwen2.5-coder:3b-instruct-q4_K_M"  # Fast for mutations
    ):
        """
        Initialize the SMM.

        Args:
            api_key: Gemini API key (optional if using Ollama)
            config: Evolution configuration
            prefer_local: Use Ollama if available
            ollama_model: Ollama model for code generation (fast model recommended)
        """
        self.llm = get_llm_backend(
            api_key=api_key,
            prefer_local=prefer_local,
            ollama_model=ollama_model
        )
        self.config = config or EvolutionConfig()
        self.gene_archive = GeneArchive()

        # Evolution state
        self.generation = 0
        self.population: List[DomainExpertAgent] = []
        self.fitness_history: List[Dict[str, float]] = []
        self.best_individual: Optional[DomainExpertAgent] = None
        self.best_fitness: float = -float('inf')

        logging.info(f"SMM initialized with {self.llm.get_stats()['active_backend']} backend")

    def initialize_population(
        self,
        template_class: type,
        benchmark_name: str,
        **template_kwargs
    ) -> List[DomainExpertAgent]:
        """
        Initialize population with random variations of a template.

        Args:
            template_class: DomainExpertAgent subclass to evolve
            benchmark_name: Benchmark to optimize for
            **template_kwargs: Additional arguments for template initialization

        Returns:
            List of agent instances
        """
        logging.info(f"Initializing population of {self.config.population_size} agents...")

        population = []
        for i in range(self.config.population_size):
            # Create agent instance
            agent = template_class(**template_kwargs)
            agent.agent_id = f"gen0_ind{i}"

            # Store in gene archive
            self.gene_archive.add_gene(
                agent.agent_id,
                agent.get_source_code()
            )

            population.append(agent)
            logging.info(f"  Created {agent.agent_id}")

        self.population = population
        self.generation = 0
        return population

    def mutate(
        self,
        agent: DomainExpertAgent,
        mutation_strength: str = "medium"
    ) -> str:
        """
        Apply LLM-driven mutation to agent code.

        Args:
            agent: Agent to mutate
            mutation_strength: "small", "medium", or "large"

        Returns:
            Mutated source code
        """
        source_code = agent.get_source_code()

        mutation_prompts = {
            "small": "Make a SMALL, subtle modification to improve this agent's strategy. Change only 1-2 lines.",
            "medium": "Make a MODERATE modification to improve this agent's strategy. Refactor or add a new heuristic.",
            "large": "Make a SIGNIFICANT modification to improve this agent's strategy. Redesign the core algorithm."
        }

        prompt = f"""You are an expert at evolutionary programming.

Task: Mutate the following Python agent code to improve its performance.
Mutation Type: {mutation_strength.upper()}

{mutation_prompts[mutation_strength]}

CRITICAL RULES:
1. Keep the class name and method signatures EXACTLY the same
2. Only modify the implementation logic
3. Preserve all imports
4. Output ONLY valid Python code, no explanations
5. Do NOT use markdown code blocks

Original Code:
{source_code}

Output the mutated code now:
"""

        try:
            mutated_code = self.llm.generate(
                prompt,
                temperature=0.8,  # Higher for creativity
                max_tokens=2000
            )

            # Clean up response
            mutated_code = self._clean_code_response(mutated_code)

            # Validate basic structure
            if len(mutated_code) < 100 or len(mutated_code) > self.config.max_code_length:
                logging.warning(f"Mutation produced invalid length: {len(mutated_code)}")
                return source_code  # Return original if mutation failed

            return mutated_code

        except Exception as e:
            logging.error(f"Mutation failed: {e}")
            return source_code

    def crossover(
        self,
        parent1: DomainExpertAgent,
        parent2: DomainExpertAgent
    ) -> str:
        """
        Apply LLM-driven crossover between two agents.

        Args:
            parent1: First parent
            parent2: Second parent

        Returns:
            Child source code combining both parents
        """
        source1 = parent1.get_source_code()
        source2 = parent2.get_source_code()

        prompt = f"""You are an expert at evolutionary programming.

Task: Create a CHILD agent by combining the best elements of TWO parent agents.

CRITICAL RULES:
1. Keep the class name and method signatures from Parent 1
2. Intelligently combine strategies from both parents
3. Preserve all necessary imports
4. Output ONLY valid Python code, no explanations
5. Do NOT use markdown code blocks

Parent 1 Code:
{source1}

Parent 2 Code:
{source2}

Output the child code now:
"""

        try:
            child_code = self.llm.generate(
                prompt,
                temperature=0.7,
                max_tokens=2000
            )

            child_code = self._clean_code_response(child_code)

            if len(child_code) < 100 or len(child_code) > self.config.max_code_length:
                logging.warning(f"Crossover produced invalid length: {len(child_code)}")
                return source1  # Return parent1 if crossover failed

            return child_code

        except Exception as e:
            logging.error(f"Crossover failed: {e}")
            return source1

    def tournament_selection(
        self,
        population: List[DomainExpertAgent],
        fitness_scores: Dict[str, float],
        tournament_size: int = 3
    ) -> DomainExpertAgent:
        """
        Select parent using tournament selection.

        Args:
            population: Current population
            fitness_scores: Fitness for each agent
            tournament_size: Number of agents in tournament

        Returns:
            Selected parent agent
        """
        # Randomly sample tournament_size agents
        tournament = random.sample(population, min(tournament_size, len(population)))

        # Select best from tournament
        best = max(tournament, key=lambda a: fitness_scores.get(a.agent_id, -float('inf')))
        return best

    def evolve_generation(
        self,
        fitness_scores: Dict[str, float]
    ) -> List[DomainExpertAgent]:
        """
        Evolve population for one generation.

        Args:
            fitness_scores: Current generation fitness scores

        Returns:
            New population
        """
        logging.info(f"\n=== Evolving Generation {self.generation} → {self.generation + 1} ===")

        new_population = []

        # Elitism: preserve top N individuals
        sorted_pop = sorted(
            self.population,
            key=lambda a: fitness_scores.get(a.agent_id, -float('inf')),
            reverse=True
        )
        elite = sorted_pop[:self.config.elitism_count]

        for agent in elite:
            # Clone elite agent
            cloned = copy.deepcopy(agent)
            cloned.agent_id = f"gen{self.generation + 1}_elite_{agent.agent_id}"
            new_population.append(cloned)
            logging.info(f"  ✓ Elite: {agent.agent_id} (fitness: {fitness_scores[agent.agent_id]:.3f})")

        # Generate offspring
        while len(new_population) < self.config.population_size:
            # Select parents
            parent1 = self.tournament_selection(self.population, fitness_scores, self.config.tournament_size)
            parent2 = self.tournament_selection(self.population, fitness_scores, self.config.tournament_size)

            # Mutation or crossover
            if random.random() < self.config.mutation_rate:
                # Mutation
                child_code = self.mutate(parent1, mutation_strength="medium")
                operation = f"mutate({parent1.agent_id})"
            else:
                # Crossover
                child_code = self.crossover(parent1, parent2)
                operation = f"cross({parent1.agent_id},{parent2.agent_id})"

            # Create child agent
            try:
                child = self._create_agent_from_code(
                    child_code,
                    parent1.__class__,
                    f"gen{self.generation + 1}_ind{len(new_population)}"
                )

                # Store in gene archive
                self.gene_archive.add_gene(child.agent_id, child_code)

                new_population.append(child)
                logging.info(f"  → Created {child.agent_id} via {operation}")

            except Exception as e:
                logging.error(f"Failed to create child: {e}")
                # If child creation fails, clone a parent instead
                cloned = copy.deepcopy(parent1)
                cloned.agent_id = f"gen{self.generation + 1}_clone{len(new_population)}"
                new_population.append(cloned)

        self.population = new_population
        self.generation += 1

        return new_population

    def run_evolution(
        self,
        iee_evaluator,  # IEE instance
        benchmark_name: str,
        template_class: type,
        **template_kwargs
    ) -> Tuple[DomainExpertAgent, List[Dict[str, Any]]]:
        """
        Run complete evolutionary cycle.

        Args:
            iee_evaluator: IEE instance for fitness evaluation
            benchmark_name: Benchmark to optimize
            template_class: DomainExpertAgent subclass
            **template_kwargs: Arguments for template initialization

        Returns:
            (best_agent, fitness_history)
        """
        logging.info(f"\n{'='*60}")
        logging.info(f"🧬 STARTING EVOLUTIONARY RUN")
        logging.info(f"  Benchmark: {benchmark_name}")
        logging.info(f"  Population: {self.config.population_size}")
        logging.info(f"  Generations: {self.config.generations}")
        logging.info(f"  Backend: {self.llm.get_stats()['active_backend']}")
        logging.info(f"{'='*60}\n")

        # Initialize population
        self.initialize_population(template_class, benchmark_name, **template_kwargs)

        stagnation_counter = 0
        previous_best = -float('inf')

        for gen in range(self.config.generations):
            logging.info(f"\n{'─'*60}")
            logging.info(f"📊 Generation {gen + 1}/{self.config.generations}")
            logging.info(f"{'─'*60}")

            # Evaluate fitness
            fitness_scores = iee_evaluator.evaluate_population(
                self.population,
                benchmark_name
            )

            # Update statistics
            current_best = max(fitness_scores.values())
            current_mean = sum(fitness_scores.values()) / len(fitness_scores)
            current_worst = min(fitness_scores.values())

            self.fitness_history.append({
                "generation": gen + 1,
                "best": current_best,
                "mean": current_mean,
                "worst": current_worst,
                "fitness_scores": fitness_scores.copy()
            })

            logging.info(f"  📈 Fitness - Best: {current_best:.3f} | Mean: {current_mean:.3f} | Worst: {current_worst:.3f}")

            # Update best individual
            if current_best > self.best_fitness:
                self.best_fitness = current_best
                best_id = max(fitness_scores, key=fitness_scores.get)
                self.best_individual = next(a for a in self.population if a.agent_id == best_id)
                logging.info(f"  🌟 NEW BEST: {best_id} with fitness {current_best:.3f}")
                stagnation_counter = 0
            else:
                stagnation_counter += 1
                logging.info(f"  ⏸️  No improvement (stagnation: {stagnation_counter}/{self.config.stagnation_generations})")

            # Convergence checks
            if current_best >= self.config.convergence_threshold:
                logging.info(f"\n✅ CONVERGENCE ACHIEVED! Fitness {current_best:.3f} >= {self.config.convergence_threshold}")
                break

            if stagnation_counter >= self.config.stagnation_generations:
                logging.info(f"\n⏹️  STOPPING: No improvement for {self.config.stagnation_generations} generations")
                break

            # Evolve to next generation (except on last iteration)
            if gen < self.config.generations - 1:
                self.evolve_generation(fitness_scores)

        # Final summary
        logging.info(f"\n{'='*60}")
        logging.info(f"🏁 EVOLUTION COMPLETE")
        logging.info(f"  Final Best Fitness: {self.best_fitness:.3f}")
        logging.info(f"  Best Agent: {self.best_individual.agent_id if self.best_individual else 'None'}")
        logging.info(f"  Generations Run: {len(self.fitness_history)}")
        logging.info(f"{'='*60}\n")

        return self.best_individual, self.fitness_history

    def _clean_code_response(self, code: str) -> str:
        """Clean LLM response to extract pure Python code."""
        # Remove markdown code blocks
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]
        elif "```" in code:
            code = code.split("```")[1].split("```")[0]

        return code.strip()

    def _create_agent_from_code(
        self,
        code: str,
        template_class: type,
        agent_id: str
    ) -> DomainExpertAgent:
        """
        Dynamically create agent instance from source code.

        Args:
            code: Python source code
            template_class: Base class
            agent_id: Unique identifier

        Returns:
            Agent instance
        """
        # This is simplified - in production would use exec() with proper sandboxing
        # For now, we'll store code in gene archive and use template instance
        agent = template_class()
        agent.agent_id = agent_id
        agent._evolved_code = code  # Store for later hot-swapping
        return agent
