
from typing import List, Optional, Tuple
import uuid
from prometheus_v1.core.data_models import MutationRecord, MutationMethod
from prometheus_v1.evolution.gene_bank.storage import GeneBank
from prometheus.llm_backend import get_llm_backend

class MutationOperator:
    """
    LLM-driven Mutation Operator.
    Uses semantic understanding of the LLM to perform structural code changes.
    """
    def __init__(self, gene_bank: GeneBank):
        self.gene_bank = gene_bank
        self.backend = get_llm_backend()

    def _generate_mutation_prompt(self, code: str, method: MutationMethod) -> str:
        """Construct the prompt based on the mutation strategy."""
        if method == MutationMethod.REFACTOR:
            instruction = "Rewrite this function to improve readability and modularity without changing behavior. Extract complex logic into helper functions."
        elif method == MutationMethod.OPTIMIZE:
            instruction = "Identify the computational bottleneck in this code (e.g., nested loops) and rewrite it for O(n log n) complexity using efficient data structures."
        elif method == MutationMethod.CAUSAL:
            instruction = "Analyze the causal dependencies in this module. Reorder operations to minimize side effects and improve causal decoupling."
        else:
            instruction = "Perform a semantically meaningful mutation on this code."

        return f"""
        You are an expert AI programmer specializing in high-performance Python.
        Current Code:
        ```python
        {code}
        ```
        
        Mutation Task: {instruction}
        
        Please provide the complete, optimized, and syntactically correct Python code within a single markdown code block.
        Do not include any explanation outside the code block.
        """

    def mutate(self, variant_id: uuid.UUID, method: MutationMethod) -> Tuple[str, MutationRecord]:
        """Perform a mutation on an existing variant and return the new code and record."""
        variant_data = self.gene_bank.retrieve_variant(variant_id)
        if not variant_data:
            raise ValueError(f"Variant {variant_id} not found in GeneBank.")
        
        code = variant_data["code"]
        prompt = self._generate_mutation_prompt(code, method)
        
        print(f"MutationOperator: Applying {method} to {variant_id}...")
        mutated_code_raw = self.backend.generate(prompt)
        
        # Extract code from markdown block
        if "```python" in mutated_code_raw:
            mutated_code = mutated_code_raw.split("```python")[1].split("```")[0].strip()
        elif "```" in mutated_code_raw:
            mutated_code = mutated_code_raw.split("```")[1].split("```")[0].strip()
        else:
            mutated_code = mutated_code_raw.strip()

        new_record = MutationRecord(
            parent_ids=[variant_id],
            mutation_method=method,
            phenotype_desc=f"Generated using {method} on {variant_id}"
        )
        
        return mutated_code, new_record

    def crossover(self, parent1_id: uuid.UUID, parent2_id: uuid.UUID) -> Tuple[str, MutationRecord]:
        """Combine the best elements of two parent modules using the LLM as a synthesizer."""
        parent1_data = self.gene_bank.retrieve_variant(parent1_id)
        parent2_data = self.gene_bank.retrieve_variant(parent2_id)
        
        if not parent1_data or not parent2_data:
            raise ValueError("Both parents must exist in the GeneBank for crossover.")
        
        prompt = f"""
        You are an expert AI programmer. 
        Synthesize a 'child' Python module that combines the best elements and optimization traits of these two 'parent' modules.
        
        Parent 1:
        ```python
        {parent1_data["code"]}
        ```
        
        Parent 2:
        ```python
        {parent2_data["code"]}
        ```
        
        Resolve any logical conflicts to produce a single, coherent, and superior Python module.
        Provide the complete code within a markdown block.
        """
        
        print(f"MutationOperator: Performing crossover between {parent1_id} and {parent2_id}...")
        child_code_raw = self.backend.generate(prompt)
        
        # Extract code
        if "```python" in child_code_raw:
            child_code = child_code_raw.split("```python")[1].split("```")[0].strip()
        elif "```" in child_code_raw:
            child_code = child_code_raw.split("```")[1].split("```")[0].strip()
        else:
            child_code = child_code_raw.strip()

        new_record = MutationRecord(
            parent_ids=[parent1_id, parent2_id],
            mutation_method=MutationMethod.CROSSOVER,
            phenotype_desc=f"Crossover between {parent1_id} and {parent2_id}"
        )
        
        return child_code, new_record
