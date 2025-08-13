
import logging
from src.llm_provider import LLMProvider

class GeneArchive:
    def __init__(self, llm_provider: LLMProvider):
        self.archive = {}
        self.solution_patterns = {}
        self.llm_provider = llm_provider
        logging.info("GeneArchive initialized.")

    def add_solution_pattern(self, initial_code, final_code):
        """
        Generates and stores an abstract solution pattern from a successful code change.
        """
        logging.info("Generating and storing a new solution pattern.")

        # 1. Abstract the problem
        problem_prompt = f"Describe the core problem solved by this Python code in a single, abstract sentence.\n\n```python\n{initial_code}\n```"
        abstract_problem = self.llm_provider.generate(problem_prompt).strip()

        # 2. Abstract the solution
        solution_prompt = f"Describe the abstract solution pattern that transforms the 'before' code into the 'after' code in a single, abstract sentence.\n\nBefore:\n```python\n{initial_code}\n```\n\nAfter:\n```python\n{final_code}\n```"
        abstract_solution = self.llm_provider.generate(solution_prompt).strip()

        if abstract_problem and abstract_solution:
            # For simplicity, we use the abstract problem as a key.
            # A more robust system would use embeddings for similarity search.
            self.solution_patterns[abstract_problem] = abstract_solution
            logging.info(f"Stored solution pattern for problem: '{abstract_problem}'")
        else:
            logging.warning("Failed to generate or store solution pattern due to empty abstraction.")

    def get_solution_pattern(self, abstract_problem_desc: str) -> str:
        """
        Retrieves a solution pattern based on an abstract problem description.
        In a real system, this would use vector similarity search.
        """
        # This is a simple key-based lookup for the PoC.
        # A real implementation would find the most semantically similar key.
        return self.solution_patterns.get(abstract_problem_desc)

    def add_gene(self, gene_id, code):
        """
        Adds a new gene to the archive.
        """
        if gene_id in self.archive:
            logging.warning(f"Gene {gene_id} already exists. Overwriting.")
        self.archive[gene_id] = code
        logging.info(f"Added gene {gene_id} to the archive.")

    def get_gene(self, gene_id):
        """
        Retrieves a gene from the archive.
        """
        return self.archive.get(gene_id)

    def get_all_genes(self):
        """
        Returns all genes in the archive.
        """
        return self.archive

    def get_fittest(self, fitness_scores):
        """
        Returns the gene with the highest fitness score.
        """
        if not fitness_scores:
            return None
        
        fittest_gene_id = max(fitness_scores, key=fitness_scores.get)
        return self.get_gene(fittest_gene_id)
