
import logging

class StrategyArchive:
    def __init__(self):
        self.strategies = {}
        logging.info("StrategyArchive initialized.")

    def add_strategy(self, theorem_name, strategy):
        """
        Adds a new strategy to the archive.
        """
        if theorem_name in self.strategies:
            logging.warning(f"Strategy for '{theorem_name}' already exists. Overwriting.")
        self.strategies[theorem_name] = strategy
        logging.info(f"Added strategy for '{theorem_name}'.")

    def get_strategy(self, theorem_name):
        """
        Retrieves a strategy from the archive.
        """
        return self.strategies.get(theorem_name)

    def get_relevant_strategies(self, current_theorem):
        """
        Retrieves strategies for similar theorems.
        For the PoC, this is a simple lookup. A real implementation would use semantic search.
        """
        # Simple heuristic: find theorems with similar keywords (e.g., 'add', 'mul', 'assoc')
        current_keywords = set(current_theorem.split())
        relevant = []
        for name, strategy in self.strategies.items():
            name_keywords = set(name.split())
            if len(current_keywords.intersection(name_keywords)) > 1:
                relevant.append(strategy)
        return relevant
