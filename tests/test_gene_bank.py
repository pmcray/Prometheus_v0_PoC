import pytest
from src.gene_bank import GeneBankAgent

@pytest.fixture
def gene_archive():
    """Provides a fresh GeneBankAgent instance for each test."""
    return GeneBankAgent()

def test_add_and_get_gene(gene_archive):
    """Tests that a gene can be added and then retrieved."""
    gene_id = "test_gene_1"
    code = "def hello(): return 'world'"
    gene_archive.add_gene(gene_id, code)
    assert gene_archive.get_gene(gene_id) == code

def test_get_gene_nonexistent(gene_archive):
    """Tests that getting a non-existent gene returns None."""
    assert gene_archive.get_gene("nonexistent_gene") is None

def test_overwrite_gene(gene_archive):
    """Tests that adding a gene with an existing ID overwrites the previous one."""
    gene_id = "test_gene_1"
    original_code = "def hello(): return 'world'"
    new_code = "def hello_new(): return 'new_world'"
    gene_archive.add_gene(gene_id, original_code)
    gene_archive.add_gene(gene_id, new_code)
    assert gene_archive.get_gene(gene_id) == new_code

def test_get_fittest(gene_archive):
    """Tests retrieving the gene with the highest fitness score."""
    genes = {
        "gene1": "code1",
        "gene2": "code2",
        "gene3": "code3"
    }
    fitness_scores = {
        "gene1": 10,
        "gene2": 30,
        "gene3": 20
    }
    for gene_id, code in genes.items():
        gene_archive.add_gene(gene_id, code)

    fittest_code = gene_archive.get_fittest(fitness_scores)
    assert fittest_code == "code2"

def test_get_fittest_empty(gene_archive):
    """Tests that get_fittest returns None when the fitness scores are empty."""
    assert gene_archive.get_fittest({}) is None

def test_get_all_genes(gene_archive):
    """Tests retrieving all genes from the archive."""
    genes = {
        "gene1": "code1",
        "gene2": "code2"
    }
    gene_archive.add_gene("gene1", "code1")
    gene_archive.add_gene("gene2", "code2")
    assert gene_archive.get_all_genes() == genes

def test_add_and_get_lora_adapter(gene_archive):
    """Tests that a LoRA adapter can be added and then retrieved."""
    adapter_id = "test_adapter_1"
    path = "/path/to/adapter"
    gene_archive.add_lora_adapter(adapter_id, path)
    assert gene_archive.get_lora_adapter(adapter_id) == path

def test_get_lora_adapter_nonexistent(gene_archive):
    """Tests that getting a non-existent LoRA adapter returns None."""
    assert gene_archive.get_lora_adapter("nonexistent_adapter") is None
