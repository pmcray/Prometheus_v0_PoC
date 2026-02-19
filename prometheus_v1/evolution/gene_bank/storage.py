import os
import json
import hashlib
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from prometheus_v1.core.data_models import MutationRecord, MutationMethod

class GeneBank:
    """
    Phylogenetic repository for agent variants.
    Ensures storage integrity via SHA-256 and tracks evolutionary lineage.
    """
    def __init__(self, base_path: str = "prometheus_v1/evolution/gene_bank/data"):
        self.base_path = base_path
        self.metadata_path = os.path.join(base_path, "metadata.jsonl")
        self._ensure_dirs()

    def _ensure_dirs(self):
        os.makedirs(self.base_path, exist_ok=True)
        os.makedirs(os.path.join(self.base_path, "variants"), exist_ok=True)
        if not os.path.exists(self.metadata_path):
            with open(self.metadata_path, "w") as f:
                pass

    def store_variant(self, code: str, mutation_record: MutationRecord) -> str:
        """Store a new agent variant with its metadata and a SHA-256 hash."""
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        variant_id = mutation_record.genotype_id
        
        # Save the code file
        file_path = os.path.join(self.base_path, "variants", f"{variant_id}.py")
        with open(file_path, "w") as f:
            f.write(code)
        
        # Save the metadata to the JSONL log
        metadata = mutation_record.model_dump(mode='json')
        metadata["sha256"] = code_hash
        metadata["file_path"] = file_path
        
        with open(self.metadata_path, "a") as f:
            f.write(json.dumps(metadata) + "\n")
            
        print(f"GeneBank: Stored variant {variant_id} (Hash: {code_hash[:8]})")
        return str(variant_id)

    def retrieve_variant(self, variant_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Retrieve the code and metadata for a specific variant."""
        if not os.path.exists(self.metadata_path): return None
        with open(self.metadata_path, "r") as f:
            for line in f:
                if not line.strip(): continue
                metadata = json.loads(line)
                if metadata["genotype_id"] == str(variant_id):
                    # Verify integrity
                    file_path = metadata["file_path"]
                    with open(file_path, "r") as code_f:
                        code = code_f.read()
                    
                    actual_hash = hashlib.sha256(code.encode()).hexdigest()
                    if actual_hash != metadata["sha256"]:
                        print(f"GeneBank: Integrity Error for {variant_id}! Hash mismatch.")
                        return None
                    
                    return {"code": code, "metadata": metadata}
        return None

    def get_phylogeny(self, variant_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Reconstruct the lineage of a specific variant by tracing parent_ids."""
        lineage = []
        current_id = variant_id
        
        while current_id:
            variant_data = self.retrieve_variant(current_id)
            if not variant_data:
                break
            lineage.append(variant_data["metadata"])
            # Simplified: follow the first parent for linear lineage
            parent_ids = variant_data["metadata"].get("parent_ids", [])
            current_id = uuid.UUID(parent_ids[0]) if parent_ids else None
            
        return lineage
