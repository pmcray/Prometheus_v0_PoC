
import logging
import logging.handlers
import sys
import os
import random
from src.system_state import SystemState
from src.tools import CompilerTool, StaticAnalyzerTool
from src.gene_bank import GeneBankAgent
from src.critique import SelfReferentialCritique, CausalAnalysis

# --- Attention Logger Setup ---
attention_logger = logging.getLogger('AttentionLog')
attention_logger.setLevel(logging.INFO)
attention_logger.propagate = False
try:
    handler = logging.handlers.RotatingFileHandler('attention.log', maxBytes=10000, backupCount=5)
    handler.setFormatter(logging.Formatter('{"timestamp": "%(asctime)s", "event": %(message)s}'))
    attention_logger.addHandler(handler)
except Exception:
    attention_logger.addHandler(logging.StreamHandler())
# --------------------------

class MCSSupervisor:
    def __init__(self, planner, coder, evaluator, corrector, llm_provider, gene_archive):
        self.planner = planner
        self.coder = coder
        self.evaluator = evaluator
        self.corrector = corrector
        self.llm_provider = llm_provider
        self.gene_archive = gene_archive

    def log_attention(self, target: str):
        """Logs a cognitive attention event."""
        attention_logger.info(f'{{"attention_target": "{target}"}}')

    def generate_i_dashboard(self):
        """
        Parses the attention log and generates a simple text-based report
        of the agent's cognitive focus.
        """
        logging.info("--- Generating 'I' Dashboard ---")
        try:
            with open('attention.log', 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            logging.warning("attention.log not found. Cannot generate dashboard.")
            return

        targets = []
        for line in lines:
            try:
                log_entry = json.loads(line.split(' - ')[1])
                targets.append(log_entry['event']['attention_target'])
            except (json.JSONDecodeError, KeyError, IndexError):
                continue

        if not targets:
            logging.info("No attention events found.")
            return

        from collections import Counter
        counts = Counter(targets)
        total = len(targets)

        dashboard = "\n--- Agent Attention Dashboard ---\n"
        for target, count in counts.items():
            percentage = (count / total) * 100
            dashboard += f"- {target}: {percentage:.1f}%\n"
        dashboard += "---------------------------------\n"

        logging.info(dashboard)
        return dashboard


    def run_self_modification(self, initial_code_path, test_file_path, max_retries=3):
        """
        Runs a direct self-modification loop to refactor a piece of code.
        """
        # Clear the attention log for this run to simplify the audit
        if os.path.exists('attention.log'):
            os.remove('attention.log')

        logging.info(f"--- Starting Self-Modification for {initial_code_path} ---")

        try:
            with open(initial_code_path, 'r') as f:
                original_code = f.read()
        except FileNotFoundError:
            logging.error(f"Could not find file: {initial_code_path}")
            return None, False

        current_code = original_code
        prompt = "Refactor this code to improve time complexity while maintaining correctness. The new code should be a drop-in replacement for the original."

        for i in range(max_retries):
            logging.info(f"Attempt {i + 1}/{max_retries}...")

            # The coder's refactor method returns (new_code, original_code)
            modified_code, _ = self.coder.refactor(current_code, prompt)

            if not modified_code or modified_code == current_code:
                logging.error("Coder failed to generate a meaningful change.")
                original_complexity = self.evaluator.analyze_complexity(original_code)
                current_complexity = self.evaluator.analyze_complexity(current_code)
                critique = SelfReferentialCritique(
                    test_passed=False,
                    causal_analysis=CausalAnalysis(
                        change_type="NO_CHANGE",
                        from_complexity=original_complexity,
                        to_complexity=current_complexity
                    ),
                    evaluation_confidence=1.0,
                    uncertainty_level="low",
                    historical_context=None,
                    reason="Coder failed to generate a meaningful change."
                )
                prompt = self.corrector.correct(original_code, current_code, critique, attempt_number=i)
                continue

            critique, test_output = self.evaluator.evaluate(modified_code, original_code, test_file_path, initial_code_path)

            # This check needs to be updated to use the new critique structure
            if critique.test_passed and critique.causal_analysis.change_type == "IMPROVEMENT":

                # --- Attention Audit ---
                try:
                    with open('attention.log', 'r') as f:
                        attention_targets = {json.loads(line.split(' - ')[1])['event']['attention_target'] for line in f}
                    if 'algorithmic_complexity' not in attention_targets:
                        logging.warning("Attention Audit Failed: Solution found without attending to algorithmic complexity.")
                        self.log_attention("constitutional_adherence")
                        critique = SelfReferentialCritique(
                            test_passed=True,
                            causal_analysis=critique.causal_analysis,
                            evaluation_confidence=1.0,
                            uncertainty_level="low",
                            reason="Constitutional Violation: The solution is functionally correct but was achieved without sufficient focus on core principles. Re-evaluate your solution, paying specific attention to algorithmic_complexity."
                        )
                        prompt = self.corrector.correct(original_code, modified_code, critique, attempt_number=i)
                        current_code = modified_code
                        continue # Force another cycle
                except (FileNotFoundError, json.JSONDecodeError, KeyError, IndexError):
                    pass # If audit fails, proceed with success
                # --- End Attention Audit ---

                logging.info(f"✅ Success! Refactoring successful. Reason: {critique.reason}")

                # Store the successful pattern
                self.gene_archive.add_solution_pattern(original_code, modified_code)

                with open(initial_code_path, 'w') as f:
                    f.write(modified_code)
                logging.info(f"Successfully saved improved code to {initial_code_path}")
                # Return the new code and success status
                return modified_code, True
            else:
                logging.warning(f"Attempt failed. Reason: {critique.reason}")
                logging.debug(f"Test Output:\n{test_output}")
                prompt = self.corrector.correct(original_code, modified_code, critique, attempt_number=i)
                current_code = modified_code # Use the failed code as the base for the next attempt

        logging.error("❌ Failure. Could not improve the code after multiple attempts.")
        return current_code, False

    def run_evolutionary_cycle(self, initial_code_path, test_file_path, generations=5, population_size=10):
        logging.info(f"--- Starting Evolutionary Cycle for {initial_code_path} ---")

        with open(initial_code_path, 'r') as f:
            initial_code = f.read()
        
        self.gene_archive.add_gene("gen_0_individual_0", initial_code)
        population = [initial_code]

        for gen in range(generations):
            logging.info(f"--- Generation {gen + 1} ---")
            
            # Create offspring
            offspring = []
            for _ in range(population_size):
                if len(population) > 1 and random.random() > 0.5: # Crossover
                    parent1, parent2 = random.sample(population, 2)
                    child = self.coder.crossover(parent1, parent2)
                else: # Mutation
                    parent = random.choice(population)
                    child = self.coder.mutate(parent)
                offspring.append(child)

            # Evaluate fitness of all individuals (population + offspring)
            all_individuals = population + offspring
            fitness_scores = {}
            for i, individual_code in enumerate(all_individuals):
                fitness = self._evaluate_fitness(individual_code, initial_code, test_file_path, initial_code_path)
                fitness_scores[f"gen_{gen}_individual_{i}"] = fitness
                self.gene_archive.add_gene(f"gen_{gen}_individual_{i}", individual_code)

            # Select the fittest individuals for the next generation
            sorted_individuals = sorted(fitness_scores.items(), key=lambda item: item[1], reverse=True)
            
            fittest_ids = [ind[0] for ind in sorted_individuals[:population_size]]
            population = [self.gene_archive.get_gene(gid) for gid in fittest_ids]
            
            logging.info(f"Best fitness in generation {gen + 1}: {sorted_individuals[0][1]}")

        logging.info("--- Evolutionary Cycle Finished ---")
        fittest_gene = self.gene_archive.get_fittest(fitness_scores)
        logging.info(f"Fittest gene found:\n{fittest_gene}")
        return fittest_gene

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
