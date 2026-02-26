"""
RSI Lineage & Model Versioning — Prometheus v0.98 (WP-04)

Tracks the "Evolutionary Tree" of self-improving agents.
Ensures accountability and rollback capabilities for RSI.
"""

import json
import os
import shutil
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

class ModelRegistry:
    """
    Registry of model versions and code snapshots.
    """
    def __init__(self, storage_dir: str = "model_registry"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.index_path = self.storage_dir / "index.json"
        self.index = self._load_index()

    def _load_index(self) -> List[Dict]:
        if self.index_path.exists():
            with open(self.index_path, "r") as f:
                return json.load(f)
        return []

    def record_version(self, version_id: str, metadata: Dict):
        """Records a new version in the index."""
        entry = {
            "version_id": version_id,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata
        }
        self.index.append(entry)
        self._save_index()

    def _save_index(self):
        with open(self.index_path, "w") as f:
            json.dump(self.index, f, indent=2)

    def checkpoint_system(self, code_files: List[str], weight_files: List[str]) -> str:
        """
        Creates a full checkpoint of current code and weights.
        Returns the unique version_id (SHA-256 hash).
        """
        timestamp = int(time.time())
        version_id = f"v{timestamp}"
        
        checkpoint_dir = self.storage_dir / version_id
        checkpoint_dir.mkdir(exist_ok=True)
        
        # Snapshot code
        (checkpoint_dir / "code").mkdir(exist_ok=True)
        for f in code_files:
            if os.path.exists(f):
                dest = checkpoint_dir / "code" / os.path.basename(f)
                shutil.copy2(f, dest)

        # Snapshot weights
        (checkpoint_dir / "weights").mkdir(exist_ok=True)
        for f in weight_files:
            if os.path.exists(f):
                dest = checkpoint_dir / "weights" / os.path.basename(f)
                shutil.copy2(f, dest)
                
        return version_id

class LineageTracker:
    """
    Tracks modifications and their performance impact.
    """
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self.current_parent = "root"

    def track_modification(self, target_obj: str, method: str, 
                           change_desc: str, fitness_before: float, 
                           fitness_after: float):
        """
        Logs a single RSI step.
        """
        mod_id = hashlib.sha256(f"{target_obj}{method}{time.time()}".encode()).hexdigest()[:8]
        metadata = {
            "parent": self.current_parent,
            "target": f"{target_obj}.{method}",
            "change": change_desc,
            "impact": fitness_after - fitness_before,
            "metrics": {
                "before": fitness_before,
                "after": fitness_after
            }
        }
        self.registry.record_version(mod_id, metadata)
        self.current_parent = mod_id
        return mod_id
