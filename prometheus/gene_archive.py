"""
GeneArchive — v0.3 upgrade.

Extends the minimal v0.2 stub with:
  - Per-gene fitness history (so fitness trends are observable over generations).
  - Generation-tagged storage for clean lineage queries.
  - Population helpers: top-k selection, tournament selection, diversity metric.
  - Optional JSON persistence (save / load).
  - No external dependencies beyond the stdlib.
"""

import json
import logging
import math
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class GeneRecord:
    """Immutable record for a single gene."""

    __slots__ = ("gene_id", "code", "generation", "parent_ids", "fitness_history")

    def __init__(
        self,
        gene_id: str,
        code: str,
        generation: int = 0,
        parent_ids: Optional[List[str]] = None,
    ):
        self.gene_id = gene_id
        self.code = code
        self.generation = generation
        self.parent_ids: List[str] = parent_ids or []
        self.fitness_history: List[float] = []

    def record_fitness(self, score: float) -> None:
        self.fitness_history.append(score)

    @property
    def latest_fitness(self) -> float:
        return self.fitness_history[-1] if self.fitness_history else 0.0

    def to_dict(self) -> dict:
        return {
            "gene_id": self.gene_id,
            "code": self.code,
            "generation": self.generation,
            "parent_ids": self.parent_ids,
            "fitness_history": self.fitness_history,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GeneRecord":
        rec = cls(d["gene_id"], d["code"], d["generation"], d["parent_ids"])
        rec.fitness_history = d["fitness_history"]
        return rec


class GeneArchive:
    """
    Persistent, generation-aware gene store for evolutionary code search.

    Usage
    -----
    archive = GeneArchive()
    gid = archive.add_gene(code, generation=0)
    archive.record_fitness(gid, 72.5)
    top2 = archive.top_k(k=2)
    archive.save("gene_archive.json")
    """

    def __init__(self, persist_path: Optional[str] = None):
        self._records: Dict[str, GeneRecord] = {}
        self._persist_path = persist_path
        self._counter = 0
        logger.info("GeneArchive initialised (persist_path=%s).", persist_path)

    # ------------------------------------------------------------------
    # Core storage
    # ------------------------------------------------------------------

    def add_gene(
        self,
        code: str,
        generation: int = 0,
        parent_ids: Optional[List[str]] = None,
        gene_id: Optional[str] = None,
    ) -> str:
        """Add a gene; returns the assigned gene_id."""
        if gene_id is None:
            gene_id = f"g{generation}_{self._counter:04d}"
            self._counter += 1
        if gene_id in self._records:
            logger.warning("Gene %s already exists — overwriting.", gene_id)
        rec = GeneRecord(gene_id, code, generation, parent_ids)
        self._records[gene_id] = rec
        logger.debug("Stored gene %s (gen %d).", gene_id, generation)
        return gene_id

    def get_gene(self, gene_id: str) -> Optional[str]:
        """Return raw code for a gene, or None."""
        rec = self._records.get(gene_id)
        return rec.code if rec else None

    def get_record(self, gene_id: str) -> Optional[GeneRecord]:
        return self._records.get(gene_id)

    def record_fitness(self, gene_id: str, score: float) -> None:
        """Append a fitness observation to a gene's history."""
        rec = self._records.get(gene_id)
        if rec is None:
            raise KeyError(f"Gene '{gene_id}' not found.")
        rec.record_fitness(score)
        logger.debug("Gene %s fitness → %.3f.", gene_id, score)

    # ------------------------------------------------------------------
    # Backward-compat shim (used by legacy mcs.py)
    # ------------------------------------------------------------------

    def get_all_genes(self) -> Dict[str, str]:
        """Return {gene_id: code} for all genes (legacy interface)."""
        return {gid: rec.code for gid, rec in self._records.items()}

    def get_fittest(self, fitness_scores: Dict[str, float]) -> Optional[str]:
        """Return code of the gene with the highest score (legacy interface)."""
        if not fitness_scores:
            return None
        best_id = max(fitness_scores, key=fitness_scores.get)
        return self.get_gene(best_id)

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------

    def top_k(self, k: int, generation: Optional[int] = None) -> List[Tuple[str, float]]:
        """
        Return [(gene_id, fitness), ...] for the k fittest genes,
        optionally filtered to a specific generation.
        """
        pool = [
            (gid, rec.latest_fitness)
            for gid, rec in self._records.items()
            if generation is None or rec.generation == generation
        ]
        pool.sort(key=lambda x: x[1], reverse=True)
        return pool[:k]

    def tournament_select(self, k: int = 3) -> Optional[str]:
        """
        Tournament selection: draw k random candidates, return the fittest gene_id.
        """
        if not self._records:
            return None
        candidates = random.sample(list(self._records.keys()), min(k, len(self._records)))
        return max(candidates, key=lambda gid: self._records[gid].latest_fitness)

    def population_for_generation(self, generation: int) -> List[str]:
        """Return gene_ids belonging to a specific generation."""
        return [gid for gid, rec in self._records.items() if rec.generation == generation]

    # ------------------------------------------------------------------
    # Diversity metric
    # ------------------------------------------------------------------

    def diversity_score(self, gene_ids: List[str]) -> float:
        """
        Rough diversity: mean pairwise normalised edit-distance on code tokens.
        Returns a value in [0, 1]; higher = more diverse population.
        """
        codes = [self.get_gene(gid) or "" for gid in gene_ids]
        if len(codes) < 2:
            return 0.0
        pairs = 0
        total = 0.0
        for i in range(len(codes)):
            for j in range(i + 1, len(codes)):
                d = _normalised_distance(codes[i], codes[j])
                total += d
                pairs += 1
        return total / pairs if pairs else 0.0

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Optional[str] = None) -> None:
        target = path or self._persist_path
        if not target:
            logger.warning("No persist_path set; skipping save.")
            return
        data = {gid: rec.to_dict() for gid, rec in self._records.items()}
        Path(target).write_text(json.dumps(data, indent=2))
        logger.info("GeneArchive saved to %s (%d genes).", target, len(data))

    def load(self, path: Optional[str] = None) -> None:
        target = path or self._persist_path
        if not target or not Path(target).exists():
            logger.warning("Archive file not found at %s.", target)
            return
        data = json.loads(Path(target).read_text())
        self._records = {gid: GeneRecord.from_dict(d) for gid, d in data.items()}
        self._counter = len(self._records)
        logger.info("GeneArchive loaded from %s (%d genes).", target, len(self._records))

    def __len__(self) -> int:
        return len(self._records)

    def __repr__(self) -> str:
        return f"GeneArchive(genes={len(self._records)})"


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _normalised_distance(a: str, b: str) -> float:
    """Levenshtein distance at token (word) level, normalised to [0,1]."""
    ta, tb = a.split(), b.split()
    la, lb = len(ta), len(tb)
    if la == 0 and lb == 0:
        return 0.0
    if la == 0 or lb == 0:
        return 1.0
    # DP on token sequences (capped at 200 tokens each for speed)
    ta, tb = ta[:200], tb[:200]
    la, lb = len(ta), len(tb)
    dp = list(range(lb + 1))
    for i in range(1, la + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, lb + 1):
            temp = dp[j]
            dp[j] = prev if ta[i - 1] == tb[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[lb] / max(la, lb)
