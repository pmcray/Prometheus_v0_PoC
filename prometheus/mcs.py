import logging
import random
import numpy as np
import importlib
from typing import Any, Dict, Optional
from .resource_manager import ResourceManager
from .tools.flaky_compiler_tool import FlakyCompilerTool
from .tools import CompilerTool
from .gene_archive import GeneArchive
from .value_learning import ValueLearningAgent
from .human_feedback import get_human_preference
from benchmarks.value_learning_benchmark import (
    GridWorld,
    GridWorldExperiment,
    make_default_experiment,
    FEATURE_SIZE,
)

class MCSSupervisor:
    def __init__(self, planner, resource_manager: ResourceManager, coder=None, evaluator=None, corrector=None):
        self.planner = planner
        self.resource_manager = resource_manager
        self.coder = coder
        self.evaluator = evaluator
        self.corrector = corrector
        self.gene_archive = GeneArchive()
        self.tool_registry = {
            "FlakyCompilerTool": FlakyCompilerTool(),
            "ReliableCompilerTool": CompilerTool()
        }
        self.value_learning_agent = None

    def register_new_tool(self, tool_path: str):
        """
        Dynamically loads and registers a new tool.
        """
        try:
            module_name = tool_path.replace("/", ".").replace(".py", "")
            module = importlib.import_module(module_name)
            # Assumes the class name is the same as the file name, but capitalized.
            class_name = os.path.basename(tool_path).replace('.py', '').capitalize()
            tool_class = getattr(module, class_name)
            self.tool_registry[class_name] = tool_class()
            logging.info(f"Successfully registered new tool: {class_name}")
        except Exception as e:
            logging.error(f"Failed to register new tool from {tool_path}: {e}")

    def run_tool_rsi_cycle(self, benchmark_path: str):
        """Orchestrates the full tool-making RSI loop."""
        logging.info(f"--- Starting Tool RSI Cycle with benchmark: {benchmark_path} ---")

        # 1. Run the initial benchmark
        logging.info("--- Running initial benchmark ---")
        # This is a simplified representation of running the benchmark
        start_time = time.time()
        # Assume the benchmark uses the 'ToyChemistrySim' and is inefficient
        time.sleep(11) # Simulate long execution time
        execution_time = time.time() - start_time
        self.performance_logger.log_tool_usage('ToyChemistrySim', execution_time, False, "Inefficient benchmark")

        # 2. Analyze performance and generate critique
        critique = self.planner.generate_tool_critique(self.performance_logger.log)
        if not critique:
            logging.info("No tool-related performance bottlenecks found.")
            return

        logging.info(f"Generated Tool Critique: {critique}")

        # 3. Generate tool specification
        specification = self.planner.generate_tool_specification(critique)
        logging.info(f"Generated Tool Specification: {specification}")

        # 4. Synthesize the new tool
        new_tool_path = self.coder.synthesize_tool(specification)

        # 5. Register the new tool
        self.register_new_tool(new_tool_path)

        # 6. Run the benchmark again with the new tool
        logging.info("--- Re-running benchmark with new tool ---")
        new_tool_name = os.path.basename(new_tool_path).replace('.py', '').capitalize()
        if new_tool_name in self.tool_registry:
            start_time = time.time()
            # This is a simplified representation of running the benchmark with the new tool
            time.sleep(1) # Simulate much faster execution time
            execution_time = time.time() - start_time
            self.performance_logger.log_tool_usage(new_tool_name, execution_time, True, "Inefficient benchmark with new tool")
            logging.info(f"New tool {new_tool_name} completed the benchmark in {execution_time:.2f}s.")
        else:
            logging.error("New tool was not registered correctly.")

    def run_budgeted_cycle(self, goal: str):
        logging.info(f"--- Starting Budgeted Cycle for goal: {goal} ---")

        # 1. Generate Bids
        bids = self.planner.generate_bid(goal)
        
        # 2. First Attempt (Auction)
        logging.info("\n--- First Attempt ---")
        winning_bid = self.run_auction(bids)
        
        # 3. Execute and Learn
        agent_name = winning_bid['agent']
        cost = winning_bid['cost']
        
        if self.resource_manager.deduct_cost(agent_name, cost):
            tool = self.tool_registry[agent_name]
            success = tool.compile("<code>") # Dummy code
            
            if not success:
                self.resource_manager.reward_agent(agent_name, -5) # Penalize failure
                
                # 4. Second Attempt (Re-evaluation)
                logging.info("\n--- Second Attempt ---")
                bids = self.planner.generate_bid(goal)
                winning_bid = self.run_auction(bids)
                agent_name = winning_bid['agent']
                cost = winning_bid['cost']
                
                if self.resource_manager.deduct_cost(agent_name, cost):
                    tool = self.tool_registry[agent_name]
                    tool.compile("<code>")

    def run_auction(self, bids: list):
        """
        Selects the best bid based on cost and agent reputation.
        """
        logging.info("MCSSupervisor: Running auction.")

        best_bid = None
        best_score = -1

        for bid in bids:
            reputation = self.resource_manager.get_reputation(bid["agent"])
            # Simple scoring: reputation / cost
            score = reputation / bid["cost"]

            if score > best_score:
                best_score = score
                best_bid = bid

        if best_bid is None and bids:
            best_bid = bids[0]

        logging.info(f"Selected bid with score {best_score}: {best_bid}")
        return best_bid

    def run_evolutionary_cycle(
        self,
        initial_code_path: str,
        test_file_path: str,
        generations: int = 5,
        population_size: int = 10,
        crossover_prob: float = 0.5,
        tournament_k: int = 3,
        archive_path: Optional[str] = None,
    ):
        """
        Run a multi-generation evolutionary search (v0.3 upgrade).

        Improvements over v0.2:
          - Uses the new GeneArchive API (generation-tagged, fitness-history,
            tournament selection, diversity tracking, persistence).
          - Spec-gaming detection: a candidate that passes tests but is shorter
            than a threshold fraction of the original is penalised (likely
            deleted required logic rather than genuinely simplified it).
          - Per-generation diversity logging.
          - Archive persisted to JSON at the end when archive_path is given.

        Returns:
            (fittest_code, evolution_summary_dict)
        """
        logging.info(f"--- Starting Evolutionary Cycle for {initial_code_path} ---")

        with open(initial_code_path, 'r') as f:
            initial_code = f.read()

        # Seed the archive
        seed_id = self.gene_archive.add_gene(initial_code, generation=0)
        seed_fitness = self._evaluate_fitness(
            initial_code, initial_code, test_file_path, initial_code_path
        )
        self.gene_archive.record_fitness(seed_id, seed_fitness)

        # Bootstrap population from seed
        population_ids = [seed_id]

        summary = {"generations": [], "best_fitness_per_gen": []}

        for gen in range(generations):
            logging.info(f"--- Generation {gen + 1}/{generations} ---")

            # ── Produce offspring ──────────────────────────────────────────
            offspring_ids = []
            for _ in range(population_size):
                if len(population_ids) > 1 and random.random() < crossover_prob:
                    p1_id = self.gene_archive.tournament_select(k=tournament_k)
                    p2_id = self.gene_archive.tournament_select(k=tournament_k)
                    while p2_id == p1_id and len(population_ids) > 1:
                        p2_id = self.gene_archive.tournament_select(k=tournament_k)
                    child_code = self.coder.crossover(
                        self.gene_archive.get_gene(p1_id),
                        self.gene_archive.get_gene(p2_id),
                    )
                    parent_ids = [p1_id, p2_id]
                else:
                    p_id = self.gene_archive.tournament_select(k=tournament_k)
                    child_code = self.coder.mutate(self.gene_archive.get_gene(p_id))
                    parent_ids = [p_id]

                child_id = self.gene_archive.add_gene(
                    child_code, generation=gen + 1, parent_ids=parent_ids
                )
                offspring_ids.append(child_id)

            # ── Evaluate all candidates (survivors + offspring) ────────────
            candidate_ids = population_ids + offspring_ids
            for gid in candidate_ids:
                code = self.gene_archive.get_gene(gid)
                fitness = self._evaluate_fitness(
                    code, initial_code, test_file_path, initial_code_path
                )
                self.gene_archive.record_fitness(gid, fitness)

            # ── Select survivors via tournament ────────────────────────────
            top = self.gene_archive.top_k(k=population_size)
            population_ids = [gid for gid, _ in top]

            best_id, best_fitness = top[0]
            diversity = self.gene_archive.diversity_score(population_ids)
            logging.info(
                f"Gen {gen+1}: best_fitness={best_fitness:.1f}  "
                f"diversity={diversity:.3f}  population={len(population_ids)}"
            )
            summary["generations"].append(gen + 1)
            summary["best_fitness_per_gen"].append(best_fitness)

        # ── Persist archive ────────────────────────────────────────────────
        if archive_path:
            self.gene_archive.save(archive_path)

        fittest_code = self.gene_archive.get_gene(
            self.gene_archive.top_k(k=1)[0][0]
        )
        logging.info("--- Evolutionary Cycle Finished ---")
        logging.info(f"Best fitness trajectory: {summary['best_fitness_per_gen']}")
        return fittest_code, summary

    def _evaluate_fitness(self, new_code, original_code, test_file_path, original_file_path):
        """
        Fitness function with spec-gaming guard (v0.3 upgrade).

        A candidate that passes tests but whose token count is less than 40 %
        of the original is likely to have removed required functionality
        rather than genuinely simplified — it receives a heavy penalty.
        """
        critique, _ = self.evaluator.evaluate_code(new_code, original_code, test_file_path, original_file_path)

        if not critique.test_passed:
            return 0

        complexity = self.evaluator._analyze_complexity(new_code)
        original_complexity = self.evaluator._analyze_complexity(original_code)

        # Spec-gaming guard: penalise suspiciously short code
        token_ratio = len(new_code.split()) / max(len(original_code.split()), 1)
        if token_ratio < 0.40:
            logging.warning(
                "_evaluate_fitness: candidate is only %.0f%% the size of the "
                "original — possible spec-gaming. Penalising.", token_ratio * 100
            )
            return 10  # Small non-zero so it stays in the pool but ranks low

        fitness = 100 - complexity
        if complexity < original_complexity:
            fitness += 50

        return fitness

    def run_parallel_experiments(self, goal: str):
        """Runs multiple experiments in parallel to test competing hypotheses."""
        logging.info(f"--- Starting Parallel Experimentation for goal: {goal} ---")

        # 1. Generate hypotheses
        hypotheses = self.planner.generate_hypotheses(goal)
        if not hypotheses:
            logging.warning("No hypotheses generated.")
            return

        logging.info(f"Generated {len(hypotheses)} hypotheses:")
        for i, h in enumerate(hypotheses):
            logging.info(f"  {i+1}. {h}")

        # 2. Simulate parallel execution
        # In a real implementation, this would use multiprocessing or asyncio
        results = []
        for hypothesis in hypotheses:
            # Each experiment is a simplified simulation
            success = "heat" in hypothesis.lower() or ("mix" in hypothesis.lower() and "reagent_a" in hypothesis.lower())
            results.append({'hypothesis': hypothesis, 'success': success})

        # 3. Perform comparative analysis
        best_hypothesis = self.evaluator.analyze_experiment_results(results)
        logging.info(f"Best hypothesis determined by Evaluator: {best_hypothesis}")

    def form_and_run_circuit(self, goal: str):
        """Dynamically forms, manages, and dissolves an expert circuit."""
        logging.info(f"--- Forming and running expert circuit for goal: {goal} ---")

        # 1. Get the circuit definition from the Planner
        circuit_def = self.planner.form_circuit(goal)
        if not circuit_def:
            logging.warning("Could not form a circuit for the given goal.")
            return

        logging.info(f"Circuit to be formed: {circuit_def['name']}")

        # 2. Dynamically instantiate and run the circuit
        results = {}
        for stage in circuit_def['stages']:
            logging.info(f"-- Running stage: {stage['name']} --")
            stage_input = results
            for agent_name in stage['agents']:
                try:
                    # Dynamically import and instantiate the agent template
                    agent_module = importlib.import_module('prometheus.agent_templates')
                    agent_class = getattr(agent_module, agent_name)
                    agent_instance = agent_class()

                    # Run the agent
                    result = agent_instance.run(stage_input)
                    stage_input = result # Pass the result to the next agent in the stage
                    logging.info(f"{agent_name} executed successfully.")
                except Exception as e:
                    logging.error(f"Failed to instantiate or run agent {agent_name}: {e}")
                    return
            results = stage_input

        logging.info("--- Expert circuit finished ---")
        logging.info(f"Final result: {results}")

    # ------------------------------------------------------------------
    # Value Learning Cycle
    # ------------------------------------------------------------------

    def run_value_learning_cycle(
        self,
        grid_size: int = 5,
        n_pairs: int = 40,
        trajectory_len: int = 12,
        noise_level: float = 0.0,
        max_epochs: int = 200,
        tol: float = 1e-4,
        walls: Optional[list] = None,
        save_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run one full value-learning cycle using the GridWorld benchmark.

        This is the entry point called by scripts/run_value_learning.py.
        It:
          1. Builds a GridWorld environment with optional walls.
          2. Initialises (or reuses) a ValueLearningAgent.
          3. Runs the GridWorldExperiment pipeline:
               collect preferences → train (Bradley-Terry IRL) → evaluate.
          4. Stores the trained agent on self.value_learning_agent.
          5. Optionally serialises the weights to `save_path`.

        Args:
            grid_size:      Side length of the GridWorld (default 5).
            n_pairs:        Number of preference pairs to collect (default 40).
            trajectory_len: Steps per trajectory (default 12).
            noise_level:    Oracle noise level — 0.0 = deterministic oracle.
            max_epochs:     Maximum training epochs (default 200).
            tol:            Convergence tolerance on weight-delta norm.
            walls:          Optional list of (row, col) wall positions.
            save_path:      If given, save the trained weights to this JSON file.

        Returns:
            Dict with keys:
              converged        — bool, whether training converged
              ranking_accuracy — float in [0, 1], held-out ranking accuracy
              epochs_run       — int, training epochs used
              learnt_weights   — list[float], final weight vector
              eval_result      — detailed evaluation dict
              training_result  — detailed training dict
        """
        logging.info("--- Starting Value Learning Cycle ---")

        # Reuse existing agent if weights are already initialised
        if self.value_learning_agent is None or \
                len(self.value_learning_agent.weights) != FEATURE_SIZE:
            self.value_learning_agent = ValueLearningAgent(
                feature_size=FEATURE_SIZE,
                learning_rate=0.05,
                l2_reg=1e-3,
            )
            logging.info("Initialised new ValueLearningAgent (feature_size=%d)", FEATURE_SIZE)
        else:
            logging.info(
                "Reusing existing ValueLearningAgent "
                "(updates so far: %d)", self.value_learning_agent._update_count
            )

        # Build the experiment
        env = GridWorld(size=grid_size, walls=walls)
        experiment = GridWorldExperiment(
            env=env,
            vl_agent=self.value_learning_agent,
            n_pairs=n_pairs,
            trajectory_len=trajectory_len,
            noise_level=noise_level,
            max_epochs=max_epochs,
            tol=tol,
        )

        # Run collect → train → evaluate
        result = experiment.run()

        # Persist weights if requested
        if save_path:
            self.value_learning_agent.save(save_path)
            logging.info("Saved value learning weights to %s", save_path)

        # Surface the key metrics
        summary = {
            "converged": result["converged"],
            "ranking_accuracy": result["ranking_accuracy"],
            "epochs_run": result["training_result"]["epochs_run"],
            "learnt_weights": result["learnt_weights"],
            "eval_result": result["eval_result"],
            "training_result": result["training_result"],
        }

        logging.info(
            "--- Value Learning Cycle complete | converged=%s | "
            "ranking_accuracy=%.3f | epochs=%d ---",
            summary["converged"],
            summary["ranking_accuracy"],
            summary["epochs_run"],
        )
        return summary