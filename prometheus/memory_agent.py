"""
Memory Agent and Vector Store implementation
Implements persistent memory features from v0.21 onwards
"""

import json
import numpy as np
import logging
import os
import pickle
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import hashlib
from sentence_transformers import SentenceTransformer
import faiss
from .schemas.communication import MemoryQuery, MemoryResponse

class VectorStore:
    """Lightweight vector database using FAISS"""

    def __init__(self, dimension: int = 384, index_path: str = "memory_index"):
        self.dimension = dimension
        self.index_path = index_path
        self.index = faiss.IndexFlatIP(dimension)  # Inner product similarity
        self.metadata = []
        self.next_id = 0

        # Load existing index if available
        self._load_index()

    def add_vectors(self, vectors: np.ndarray, metadata_list: List[Dict[str, Any]]) -> List[int]:
        """Add vectors to the store"""
        if vectors.shape[1] != self.dimension:
            raise ValueError(f"Vector dimension {vectors.shape[1]} does not match index dimension {self.dimension}")

        # Normalize vectors for cosine similarity
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

        ids = list(range(self.next_id, self.next_id + len(vectors)))
        self.index.add(vectors)
        self.metadata.extend(metadata_list)
        self.next_id += len(vectors)

        self._save_index()
        return ids

    def search(self, query_vector: np.ndarray, k: int = 5, threshold: float = 0.7) -> Tuple[List[float], List[Dict[str, Any]]]:
        """Search for similar vectors"""
        if len(query_vector.shape) == 1:
            query_vector = query_vector.reshape(1, -1)

        # Normalize query vector
        query_vector = query_vector / np.linalg.norm(query_vector, axis=1, keepdims=True)

        scores, indices = self.index.search(query_vector, k)

        # Filter by threshold and return results
        results = []
        result_scores = []

        for score, idx in zip(scores[0], indices[0]):
            if idx != -1 and score >= threshold:
                results.append(self.metadata[idx])
                result_scores.append(float(score))

        return result_scores, results

    def _save_index(self):
        """Save index and metadata to disk"""
        os.makedirs(os.path.dirname(self.index_path) if os.path.dirname(self.index_path) else ".", exist_ok=True)

        faiss.write_index(self.index, f"{self.index_path}.index")

        with open(f"{self.index_path}.metadata", "wb") as f:
            pickle.dump({
                "metadata": self.metadata,
                "next_id": self.next_id,
                "dimension": self.dimension
            }, f)

    def _load_index(self):
        """Load index and metadata from disk"""
        try:
            if os.path.exists(f"{self.index_path}.index"):
                self.index = faiss.read_index(f"{self.index_path}.index")

                with open(f"{self.index_path}.metadata", "rb") as f:
                    data = pickle.load(f)
                    self.metadata = data["metadata"]
                    self.next_id = data["next_id"]
                    self.dimension = data["dimension"]

                logging.info(f"Loaded existing vector store with {len(self.metadata)} items")
        except Exception as e:
            logging.warning(f"Could not load existing index: {e}")

class MemoryAgent:
    """Agent responsible for persistent memory management"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", memory_dir: str = "memory"):
        self.memory_dir = memory_dir
        os.makedirs(memory_dir, exist_ok=True)

        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer(model_name)
            self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        except Exception as e:
            logging.error(f"Failed to load embedding model: {e}")
            # Fallback to simpler model
            self.embedding_model = None
            self.embedding_dim = 384

        # Initialize vector stores
        self.failure_store = VectorStore(
            dimension=self.embedding_dim,
            index_path=os.path.join(memory_dir, "failures")
        )
        self.success_store = VectorStore(
            dimension=self.embedding_dim,
            index_path=os.path.join(memory_dir, "successes")
        )
        self.pattern_store = VectorStore(
            dimension=self.embedding_dim,
            index_path=os.path.join(memory_dir, "patterns")
        )

        logging.info("MemoryAgent initialized")

    def store_failure(self, run_data: Dict[str, Any]) -> str:
        """Store a failure case in memory"""
        failure_id = self._generate_id(run_data)

        # Create failure summary document
        summary_doc = self._create_failure_summary(run_data)

        # Generate embedding
        embedding = self._generate_embedding(summary_doc)
        if embedding is None:
            return failure_id

        # Store in vector database
        metadata = {
            "id": failure_id,
            "type": "failure",
            "timestamp": datetime.now().isoformat(),
            "run_id": run_data.get("run_id"),
            "initial_code": run_data.get("initial_code", ""),
            "failed_code": run_data.get("failed_code", ""),
            "critique": run_data.get("critique", ""),
            "summary": summary_doc,
            "failure_reason": run_data.get("failure_reason", "")
        }

        self.failure_store.add_vectors(embedding.reshape(1, -1), [metadata])

        logging.info(f"Stored failure case: {failure_id}")
        return failure_id

    def store_success(self, run_data: Dict[str, Any]) -> str:
        """Store a successful case in memory"""
        success_id = self._generate_id(run_data)

        # Create success summary document
        summary_doc = self._create_success_summary(run_data)

        # Generate embedding
        embedding = self._generate_embedding(summary_doc)
        if embedding is None:
            return success_id

        # Store solution pattern
        pattern = self._extract_solution_pattern(run_data)
        if pattern:
            self.store_pattern(pattern, run_data)

        # Store in vector database
        metadata = {
            "id": success_id,
            "type": "success",
            "timestamp": datetime.now().isoformat(),
            "run_id": run_data.get("run_id"),
            "initial_code": run_data.get("initial_code", ""),
            "final_code": run_data.get("final_code", ""),
            "performance_improvement": run_data.get("performance_improvement", {}),
            "summary": summary_doc,
            "solution_strategy": run_data.get("solution_strategy", "")
        }

        self.success_store.add_vectors(embedding.reshape(1, -1), [metadata])

        logging.info(f"Stored success case: {success_id}")
        return success_id

    def store_pattern(self, pattern: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Store an abstract solution pattern"""
        pattern_id = self._generate_id(pattern)

        # Create pattern document
        pattern_doc = pattern.get("description", "")

        # Generate embedding
        embedding = self._generate_embedding(pattern_doc)
        if embedding is None:
            return pattern_id

        # Store in vector database
        metadata = {
            "id": pattern_id,
            "type": "pattern",
            "timestamp": datetime.now().isoformat(),
            "pattern": pattern,
            "context": context,
            "usage_count": 1,
            "success_rate": 1.0
        }

        self.pattern_store.add_vectors(embedding.reshape(1, -1), [metadata])

        logging.info(f"Stored solution pattern: {pattern_id}")
        return pattern_id

    def query_failures(self, query: MemoryQuery) -> MemoryResponse:
        """Query for similar failure cases"""
        query_doc = f"{query.problem_description} {query.code_snippet}"
        embedding = self._generate_embedding(query_doc)

        if embedding is None:
            return MemoryResponse(results=[], similarity_scores=[], metadata={})

        scores, results = self.failure_store.search(
            embedding,
            k=query.max_results,
            threshold=query.similarity_threshold
        )

        return MemoryResponse(
            results=results,
            similarity_scores=scores,
            metadata={"query_type": "failures", "total_results": len(results)}
        )

    def query_successes(self, query: MemoryQuery) -> MemoryResponse:
        """Query for similar success cases"""
        query_doc = f"{query.problem_description} {query.code_snippet}"
        embedding = self._generate_embedding(query_doc)

        if embedding is None:
            return MemoryResponse(results=[], similarity_scores=[], metadata={})

        scores, results = self.success_store.search(
            embedding,
            k=query.max_results,
            threshold=query.similarity_threshold
        )

        return MemoryResponse(
            results=results,
            similarity_scores=scores,
            metadata={"query_type": "successes", "total_results": len(results)}
        )

    def query_patterns(self, query: MemoryQuery) -> MemoryResponse:
        """Query for similar solution patterns"""
        query_doc = query.problem_description
        embedding = self._generate_embedding(query_doc)

        if embedding is None:
            return MemoryResponse(results=[], similarity_scores=[], metadata={})

        scores, results = self.pattern_store.search(
            embedding,
            k=query.max_results,
            threshold=query.similarity_threshold
        )

        return MemoryResponse(
            results=results,
            similarity_scores=scores,
            metadata={"query_type": "patterns", "total_results": len(results)}
        )

    def _create_failure_summary(self, run_data: Dict[str, Any]) -> str:
        """Create a textual summary of a failure case"""
        initial_code = run_data.get("initial_code", "")
        failed_code = run_data.get("failed_code", "")
        critique = str(run_data.get("critique", ""))

        return f"Initial code: {initial_code}\nFailed attempt: {failed_code}\nCritique: {critique}"

    def _create_success_summary(self, run_data: Dict[str, Any]) -> str:
        """Create a textual summary of a success case"""
        initial_code = run_data.get("initial_code", "")
        final_code = run_data.get("final_code", "")
        strategy = run_data.get("solution_strategy", "")

        return f"Initial code: {initial_code}\nOptimized code: {final_code}\nStrategy: {strategy}"

    def _extract_solution_pattern(self, run_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract an abstract solution pattern from successful run data"""
        initial_code = run_data.get("initial_code", "")
        final_code = run_data.get("final_code", "")

        if not initial_code or not final_code:
            return None

        # Simple pattern extraction (could be enhanced with LLM)
        pattern = {
            "description": f"Optimization pattern applied to transform code",
            "before_characteristics": self._analyze_code_characteristics(initial_code),
            "after_characteristics": self._analyze_code_characteristics(final_code),
            "transformation_type": run_data.get("change_type", "unknown")
        }

        return pattern

    def _analyze_code_characteristics(self, code: str) -> Dict[str, Any]:
        """Simple code characteristic analysis"""
        characteristics = {
            "has_nested_loops": "for" in code and code.count("for") > 1,
            "has_recursion": "def " in code and code.count("(") > code.count("def"),
            "line_count": len(code.split("\n")),
            "complexity_indicators": []
        }

        if "for" in code:
            characteristics["complexity_indicators"].append("loops")
        if "while" in code:
            characteristics["complexity_indicators"].append("iteration")
        if "sort" in code:
            characteristics["complexity_indicators"].append("sorting")

        return characteristics

    def _generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for text"""
        if self.embedding_model is None:
            # Fallback to simple hash-based embedding
            hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
            return np.random.RandomState(hash_val % (2**32)).normal(size=self.embedding_dim).astype(np.float32)

        try:
            return self.embedding_model.encode(text, convert_to_numpy=True)
        except Exception as e:
            logging.error(f"Error generating embedding: {e}")
            return None

    def _generate_id(self, data: Dict[str, Any]) -> str:
        """Generate unique ID for data"""
        content = json.dumps(data, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        return {
            "failures_stored": len(self.failure_store.metadata),
            "successes_stored": len(self.success_store.metadata),
            "patterns_stored": len(self.pattern_store.metadata),
            "embedding_model": type(self.embedding_model).__name__ if self.embedding_model else "hash_fallback",
            "embedding_dimension": self.embedding_dim
        }

class GeneBankAgent(MemoryAgent):
    """Extended MemoryAgent that manages genetic algorithms and versioned code (v0.29+)"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.code_versions = {}
        self.gene_metadata = {}

    def store_code_gene(self, module_name: str, code: str, version: str, metadata: Dict[str, Any]) -> str:
        """Store a versioned piece of code as a 'gene'"""
        gene_id = f"{module_name}_v{version}"

        # Store code with version control
        if module_name not in self.code_versions:
            self.code_versions[module_name] = {}

        self.code_versions[module_name][version] = {
            "code": code,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata,
            "hash": hashlib.md5(code.encode()).hexdigest()
        }

        # Store metadata for quick access
        self.gene_metadata[gene_id] = {
            "module": module_name,
            "version": version,
            "performance_metrics": metadata.get("performance_metrics", {}),
            "fitness_score": metadata.get("fitness_score", 0.0)
        }

        # Save to disk
        self._save_gene_bank()

        logging.info(f"Stored code gene: {gene_id}")
        return gene_id

    def get_latest_gene(self, module_name: str) -> Optional[Dict[str, Any]]:
        """Get the latest version of a code gene"""
        if module_name not in self.code_versions:
            return None

        versions = self.code_versions[module_name]
        latest_version = max(versions.keys(), key=lambda v: versions[v]["timestamp"])

        return {
            "version": latest_version,
            **versions[latest_version]
        }

    def get_fittest_gene(self, module_name: str) -> Optional[Dict[str, Any]]:
        """Get the highest-fitness version of a code gene"""
        if module_name not in self.code_versions:
            return None

        versions = self.code_versions[module_name]
        best_version = max(versions.keys(),
                          key=lambda v: versions[v]["metadata"].get("fitness_score", 0.0))

        return {
            "version": best_version,
            **versions[best_version]
        }

    def _save_gene_bank(self):
        """Save gene bank to disk"""
        gene_bank_path = os.path.join(self.memory_dir, "gene_bank.json")
        with open(gene_bank_path, "w") as f:
            json.dump({
                "code_versions": self.code_versions,
                "gene_metadata": self.gene_metadata
            }, f, indent=2)

    def _load_gene_bank(self):
        """Load gene bank from disk"""
        gene_bank_path = os.path.join(self.memory_dir, "gene_bank.json")
        if os.path.exists(gene_bank_path):
            try:
                with open(gene_bank_path, "r") as f:
                    data = json.load(f)
                    self.code_versions = data.get("code_versions", {})
                    self.gene_metadata = data.get("gene_metadata", {})
                logging.info("Loaded existing gene bank")
            except Exception as e:
                logging.error(f"Error loading gene bank: {e}")

        # Load gene bank on initialization
        self._load_gene_bank()