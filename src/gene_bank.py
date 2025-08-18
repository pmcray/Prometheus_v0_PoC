
import logging

class GeneBankAgent:
    def __init__(self):
        self.archive = {}
        self.lora_adapters = {}
        logging.info("GeneBankAgent initialized.")

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

    def add_lora_adapter(self, adapter_id, path):
        """
        Adds a new LoRA adapter path to the archive.
        """
        if adapter_id in self.lora_adapters:
            logging.warning(f"LoRA adapter {adapter_id} already exists. Overwriting.")
        self.lora_adapters[adapter_id] = path
        logging.info(f"Added LoRA adapter {adapter_id} to the archive.")

    def get_lora_adapter(self, adapter_id):
        """
        Retrieves a LoRA adapter path from the archive.
        """
        return self.lora_adapters.get(adapter_id)
