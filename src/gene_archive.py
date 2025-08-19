
import logging

class GeneArchive:
    def __init__(self):
        self.archive = {}
        self.lora_adapters = {}
        logging.info("GeneArchive initialized.")

    def add_lora_adapter(self, task_type: str, adapter_path: str):
        """
        Adds a LoRA adapter path to the archive, indexed by task type.
        """
        if task_type in self.lora_adapters:
            logging.warning(f"LoRA adapter for task type '{task_type}' already exists. Overwriting.")
        self.lora_adapters[task_type] = adapter_path
        logging.info(f"Added LoRA adapter for task type '{task_type}' at path: {adapter_path}")

    def get_lora_adapter(self, task_type: str):
        """
        Retrieves a LoRA adapter path by its task type.
        """
        adapter_path = self.lora_adapters.get(task_type)
        if adapter_path:
            logging.info(f"Retrieved LoRA adapter for task type '{task_type}': {adapter_path}")
        else:
            logging.warning(f"No LoRA adapter found for task type '{task_type}'.")
        return adapter_path

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
