"""
Analogical Search Engine — Prometheus v0.98 (WP-08)

Implements Douglas Hofstadter's thesis that analogy is the core of cognition.
Allows the agent to transfer strategic patterns across unrelated domains
by extracting 'Conceptual Skeletons'.
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple
from prometheus.llm_backend import get_llm_backend

class SkeletonExtractor:
    """
    Extracts the abstract logical/causal structure of a problem.
    """
    def __init__(self):
        self.backend = get_llm_backend()

    def extract(self, domain: str, problem_desc: str, solution_code: str = "") -> Dict[str, Any]:
        """
        Uses LLM to strip surface details and reveal the 'Conceptual Skeleton'.
        """
        prompt = f"""
        Analyze the following problem from the '{domain}' domain.
        Strip away all surface details (specific numbers, variable names, domain-specific terminology).
        Reveal the core 'Conceptual Skeleton'—the abstract logical or causal structure.
        
        Problem:
        {problem_desc}
        
        {f"Solution Strategy Reference: {solution_code}" if solution_code else ""}
        
        Return a JSON object with:
        1. 'abstract_goal': The high-level objective (e.g., 'path_optimization', 'resource_partitioning').
        2. 'core_constraints': List of abstract constraints.
        3. 'structural_pattern': The underlying pattern (e.g., 'recursive_decomposition', 'symmetry_match').
        """
        response = self.backend.generate(prompt)
        try:
            # Attempt to parse JSON from LLM response
            start = response.find("{")
            end = response.rfind("}") + 1
            return json.loads(response[start:end])
        except Exception:
            # Fallback to simple dictionary if JSON parsing fails
            return {
                "abstract_goal": "unknown",
                "core_constraints": [],
                "structural_pattern": response[:100]
            }

class AnalogicalSearchEngine:
    """
    A persistent database of conceptual skeletons for cross-domain transfer.
    """
    def __init__(self, storage_path: str = "logs/analogy_memory.json"):
        self.storage_path = storage_path
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        self.memory: List[Dict[str, Any]] = self._load_memory()
        self.extractor = SkeletonExtractor()

    def _load_memory(self) -> List[Dict]:
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r") as f:
                return json.load(f)
        return []

    def record_experience(self, domain: str, problem: str, solution: str):
        """Records a successful strategy and its skeleton."""
        skeleton = self.extractor.extract(domain, problem, solution)
        entry = {
            "domain": domain,
            "problem": problem,
            "solution": solution,
            "skeleton": skeleton
        }
        self.memory.append(entry)
        self._save_memory()

    def find_analogy(self, target_domain: str, target_problem: str) -> Optional[Dict]:
        """
        Searches memory for a structurally similar problem in a different domain.
        """
        target_skeleton = self.extractor.extract(target_domain, target_problem)
        
        best_match = None
        best_score = -1.0
        
        for entry in self.memory:
            if entry["domain"] == target_domain:
                continue # Skip same domain
                
            score = self._compute_similarity(target_skeleton, entry["skeleton"])
            if score > best_score:
                best_score = score
                best_match = entry
                
        return best_match

    def _compute_similarity(self, s1: Dict, s2: Dict) -> float:
        """Simple heuristic similarity between skeletons."""
        score = 0.0
        if s1.get("abstract_goal") == s2.get("abstract_goal"):
            score += 0.5
        if s1.get("structural_pattern") == s2.get("structural_pattern"):
            score += 0.5
        return score

    def _save_memory(self):
        with open(self.storage_path, "w") as f:
            json.dump(self.memory, f, indent=2)
