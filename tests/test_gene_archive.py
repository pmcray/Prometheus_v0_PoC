import pytest
from src.gene_archive import GeneArchive

@pytest.fixture
def gene_archive():
    return GeneArchive()

def test_add_and_get_lora_adapter(gene_archive):
    task_type = "LOOP_OPTIMIZATION"
    adapter_path = "/path/to/adapter.bin"
    gene_archive.add_lora_adapter(task_type, adapter_path)
    retrieved_path = gene_archive.get_lora_adapter(task_type)
    assert retrieved_path == adapter_path

def test_get_non_existent_adapter(gene_archive):
    retrieved_path = gene_archive.get_lora_adapter("NON_EXISTENT_TYPE")
    assert retrieved_path is None
