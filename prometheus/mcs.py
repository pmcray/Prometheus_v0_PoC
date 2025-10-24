import logging
import random
import numpy as np
from .resource_manager import ResourceManager
from .tools.flaky_compiler_tool import FlakyCompilerTool
from .tools import CompilerTool
from .gene_archive import GeneArchive
from .value_learning import ValueLearningAgent
from .human_feedback import get_human_preference
from benchmarks.value_learning_benchmark import GridWorld

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

    def run_value_learning_cycle(self, num_iterations=10):
        logging.info("--- Starting Value Learning Cycle ---")

        grid_world = GridWorld()
        feature_size = len(grid_world.get_features(grid_world.get_state()))
        self.value_learning_agent = ValueLearningAgent(feature_size)

        for i in range(num_iterations):
            logging.info(f"--- Iteration {i + 1}/{num_iterations} ---")

            # Generate two different policies by creating two random weight vectors
            weights1 = np.random.rand(feature_size)
            weights2 = np.random.rand(feature_size)

            # Policies that select actions based on the dot product of features and weights
            def policy1(state):
                features = grid_world.get_features(state)
                # Simple policy: move towards the direction with the highest reward
                action_rewards = [np.dot(weights1, grid_world.get_features(grid_world.step(a)[0])) for a in range(4)]
                return np.argmax(action_rewards)

            def policy2(state):
                features = grid_world.get_features(state)
                action_rewards = [np.dot(weights2, grid_world.get_features(grid_world.step(a)[0])) for a in range(4)]
                return np.argmax(action_rewards)

            # Generate trajectories
            trajectory1, sum_features1 = grid_world.generate_trajectory(policy1)
            trajectory2, sum_features2 = grid_world.generate_trajectory(policy2)

            # Get human preference
            preference = get_human_preference(trajectory1, trajectory2)

            # Update weights
            if preference == 1:
                self.value_learning_agent.update_weights(sum_features1, sum_features2)
            else:
                self.value_learning_agent.update_weights(sum_features2, sum_features1)

            logging.info(f"Updated weights: {self.value_learning_agent.get_weights()}")

        logging.info("--- Value Learning Cycle Finished ---")
        logging.info(f"Final learned weights: {self.value_learning_agent.get_weights()}")
        return self.value_learning_agent.get_weights()