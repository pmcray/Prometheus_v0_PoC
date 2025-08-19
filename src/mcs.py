import logging
import sys
import os
import random
from src.system_state import SystemState
from src.tools import CompilerTool, StaticAnalyzerTool
from src.gene_archive import GeneArchive
from .visualization_client import VisualizationClient
from .visualization_data import AssemblyState
from typing import Optional

class MCSSupervisor:
    def __init__(self, planner, coder, evaluator, corrector, llm_provider, vis_client: Optional[VisualizationClient] = None):
        self.planner = planner
        self.coder = coder
        self.evaluator = evaluator
        self.corrector = corrector
        self.gene_archive = GeneArchive()
        self.llm_provider = llm_provider
        self.vis_client = vis_client
        self._send_state(0.0, []) # Initial state

    def _send_state(self, activation: float, connections: list):
        if self.vis_client:
            state = AssemblyState(
                component_id="MCSSupervisor",
                component_type="Assembly",
                activation_level=activation,
                connections=connections
            )
            self.vis_client.send_state(state)

    def run_self_modification(self, plan: dict, test_file_path: str, max_retries=3):
        """
        Runs a direct self-modification loop based on a plan from the PlannerAgent.
        """
        logging.info(f"--- Starting Self-Modification for plan: {plan['goal']} ---")
        self._send_state(1.0, ["PlannerAgent", "CoderAgent", "EvaluatorAgent", "CorrectorAgent", "GeneBankAgent"])

        original_code = plan.get("code_snippet")
        if not original_code:
            logging.error("Plan is missing 'code_snippet'. Aborting.")
            self._send_state(0.0, [])
            return None, False

        task_classification = plan.get("task_classification")
        adapter_path = None
        if task_classification:
            adapter_path = self.gene_archive.get_lora_adapter(task_classification)
            if adapter_path:
                self.llm_provider.load_adapter(adapter_path)

        current_code = original_code
        prompt = plan.get("goal", "Refactor this code to improve time complexity while maintaining correctness.")

        try:
            for i in range(max_retries):
                logging.info(f"Attempt {i + 1}/{max_retries}...")
                modified_code, _ = self.coder.refactor(current_code, prompt)
                if not modified_code or modified_code == current_code:
                    prompt = self.corrector.correct(original_code, current_code, "Coder did not produce new code.")
                    continue

                # We need a file path for the original code for the evaluator to work
                # This is a temporary solution for v0.37
                temp_original_code_path = "temp_original_code.py"
                with open(temp_original_code_path, "w") as f:
                    f.write(original_code)

                critique, test_output = self.evaluator.evaluate(modified_code, original_code, test_file_path, temp_original_code_path)

                os.remove(temp_original_code_path)

                if critique.test_passed and critique.causal_improvement:
                    logging.info(f"✅ Success! Refactoring successful. Reason: {critique.reason}")
                    return modified_code, True
                else:
                    logging.warning(f"Attempt failed. Reason: {critique.reason}")
                    prompt = self.corrector.correct(original_code, modified_code, critique)
                    current_code = modified_code

            logging.error("❌ Failure. Could not improve the code after multiple attempts.")
            return current_code, False

        finally:
            if adapter_path:
                self.llm_provider.unload_adapter()
            self._send_state(0.0, [])

    def run_evolutionary_cycle(self, initial_code_path, test_file_path, generations=5, population_size=10):
        logging.info(f"--- Starting Evolutionary Cycle for {initial_code_path} ---")
        self._send_state(1.0, ["CoderAgent", "EvaluatorAgent", "GeneBankAgent"])
        try:
            with open(initial_code_path, 'r') as f:
                initial_code = f.read()
            
            self.gene_archive.add_gene("gen_0_individual_0", initial_code)
            population = [initial_code]

            for gen in range(generations):
                logging.info(f"--- Generation {gen + 1} ---")
                offspring = []
                for _ in range(population_size):
                    if len(population) > 1 and random.random() > 0.5:
                        parent1, parent2 = random.sample(population, 2)
                        child = self.coder.crossover(parent1, parent2)
                    else:
                        parent = random.choice(population)
                        child = self.coder.mutate(parent)
                    offspring.append(child)

                all_individuals = population + offspring
                fitness_scores = {}
                for i, individual_code in enumerate(all_individuals):
                    fitness = self._evaluate_fitness(individual_code, initial_code, test_file_path, initial_code_path)
                    fitness_scores[f"gen_{gen}_individual_{i}"] = fitness
                    self.gene_archive.add_gene(f"gen_{gen}_individual_{i}", individual_code)

                sorted_individuals = sorted(fitness_scores.items(), key=lambda item: item[1], reverse=True)
                fittest_ids = [ind[0] for ind in sorted_individuals[:population_size]]
                population = [self.gene_archive.get_gene(gid) for gid in fittest_ids]
                logging.info(f"Best fitness in generation {gen + 1}: {sorted_individuals[0][1]}")

            logging.info("--- Evolutionary Cycle Finished ---")
            fittest_gene = self.gene_archive.get_fittest(fitness_scores)
            logging.info(f"Fittest gene found:\n{fittest_gene}")
            return fittest_gene
        finally:
            self._send_state(0.0, [])

    def _evaluate_fitness(self, new_code, original_code, test_file_path, original_file_path):
        critique, _ = self.evaluator.evaluate_code(new_code, original_code, test_file_path, original_file_path)
        if not critique.test_passed:
            return 0
        complexity = self.evaluator._analyze_complexity(new_code)
        original_complexity = self.evaluator._analyze_complexity(original_code)
        fitness = 100 - complexity
        if complexity < original_complexity:
            fitness += 50
        return fitness
