"""
ReflectorAgent with Meta-Learning Capabilities
Implements the enhanced reflection system from v0.49 workplan with long-term memory
"""

import os
import time
import json
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict, Counter

# Vector database for episodic memory
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    try:
        import faiss
        FAISS_AVAILABLE = True
        CHROMADB_AVAILABLE = False
    except ImportError:
        CHROMADB_AVAILABLE = False
        FAISS_AVAILABLE = False
        logging.warning("No vector database library available. Using in-memory storage.")

from .blackboard import AgentBase, BlackboardObject
from .schemas.communication import AgentMessage, MessageType

@dataclass
class FailureEpisode:
    """Structured representation of a failure episode"""
    episode_id: str
    timestamp: float
    initial_code: str
    failed_code: str
    task_description: str
    failure_reason: str
    critique_details: Dict[str, Any]
    performance_data: Optional[Dict[str, Any]]
    attempted_strategy: str
    meta_analysis: str
    tags: List[str]

@dataclass
class SuccessEpisode:
    """Structured representation of a successful episode"""
    episode_id: str
    timestamp: float
    initial_code: str
    final_code: str
    task_description: str
    solution_strategy: str
    performance_improvement: Dict[str, Any]
    meta_analysis: str
    tags: List[str]

@dataclass
class PatternInsight:
    """Insights about recurring patterns"""
    pattern_id: str
    pattern_type: str  # "failure_mode", "solution_strategy", "code_structure"
    frequency: int
    confidence: float
    description: str
    examples: List[str]
    recommendations: List[str]

class VectorMemoryStore:
    """Vector-based memory store for episodic memory"""

    def __init__(self, store_type: str = "auto"):
        self.store_type = store_type
        self.collection = None
        self.faiss_index = None
        self.embeddings_cache = {}

        if store_type == "auto":
            if CHROMADB_AVAILABLE:
                self._init_chromadb()
            elif FAISS_AVAILABLE:
                self._init_faiss()
            else:
                self._init_simple()
        elif store_type == "chromadb" and CHROMADB_AVAILABLE:
            self._init_chromadb()
        elif store_type == "faiss" and FAISS_AVAILABLE:
            self._init_faiss()
        else:
            self._init_simple()

    def _init_chromadb(self):
        """Initialize ChromaDB vector store"""
        try:
            self.client = chromadb.Client(Settings(anonymized_telemetry=False))
            self.collection = self.client.get_or_create_collection(
                name="prometheus_episodes",
                metadata={"hnsw:space": "cosine"}
            )
            self.store_type = "chromadb"
            logging.info("ChromaDB vector store initialized")
        except Exception as e:
            logging.warning(f"ChromaDB initialization failed: {e}")
            self._init_simple()

    def _init_faiss(self):
        """Initialize FAISS vector store"""
        try:
            import faiss
            self.dimension = 384  # Default embedding dimension
            self.faiss_index = faiss.IndexFlatL2(self.dimension)
            self.episode_ids = []
            self.store_type = "faiss"
            logging.info("FAISS vector store initialized")
        except Exception as e:
            logging.warning(f"FAISS initialization failed: {e}")
            self._init_simple()

    def _init_simple(self):
        """Initialize simple in-memory store"""
        self.episodes = {}
        self.store_type = "simple"
        logging.info("Simple memory store initialized")

    def store_episode(self, episode: FailureEpisode or SuccessEpisode):
        """Store episode in vector memory"""
        episode_text = self._episode_to_text(episode)
        embedding = self._get_embedding(episode_text)

        if self.store_type == "chromadb":
            self.collection.add(
                documents=[episode_text],
                metadatas=[asdict(episode)],
                ids=[episode.episode_id],
                embeddings=[embedding] if embedding else None
            )
        elif self.store_type == "faiss":
            if embedding:
                self.faiss_index.add(np.array([embedding]))
                self.episode_ids.append(episode.episode_id)
            self.episodes[episode.episode_id] = episode
        else:
            self.episodes[episode.episode_id] = episode

    def query_similar_episodes(self, query_text: str, n_results: int = 5) -> List[Tuple[Any, float]]:
        """Query for similar episodes"""
        query_embedding = self._get_embedding(query_text)

        if self.store_type == "chromadb":
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            episodes = []
            for i, metadata in enumerate(results['metadatas'][0]):
                distance = results['distances'][0][i]
                similarity = 1.0 - distance  # Convert distance to similarity
                episodes.append((self._metadata_to_episode(metadata), similarity))
            return episodes

        elif self.store_type == "faiss" and query_embedding:
            distances, indices = self.faiss_index.search(np.array([query_embedding]), n_results)
            episodes = []
            for i, idx in enumerate(indices[0]):
                if idx != -1:  # Valid index
                    episode_id = self.episode_ids[idx]
                    episode = self.episodes.get(episode_id)
                    if episode:
                        similarity = 1.0 / (1.0 + distances[0][i])  # Convert distance to similarity
                        episodes.append((episode, similarity))
            return episodes

        else:
            # Simple text matching for fallback
            episodes = []
            for episode in self.episodes.values():
                episode_text = self._episode_to_text(episode)
                similarity = self._simple_similarity(query_text, episode_text)
                episodes.append((episode, similarity))

            episodes.sort(key=lambda x: x[1], reverse=True)
            return episodes[:n_results]

    def _episode_to_text(self, episode) -> str:
        """Convert episode to searchable text"""
        if isinstance(episode, FailureEpisode):
            return f"Task: {episode.task_description} Failure: {episode.failure_reason} Strategy: {episode.attempted_strategy} Analysis: {episode.meta_analysis}"
        else:
            return f"Task: {episode.task_description} Success: {episode.solution_strategy} Analysis: {episode.meta_analysis}"

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get text embedding (simplified - would use actual embedding model)"""
        # For the PoC, use a simple hash-based embedding
        # In production, would use sentence-transformers or similar
        if text in self.embeddings_cache:
            return self.embeddings_cache[text]

        # Simple hash-based embedding for demo
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()

        # Convert to normalized vector
        embedding = [float(b) / 255.0 for b in hash_bytes[:16]]
        # Pad to standard dimension if using FAISS
        if self.store_type == "faiss":
            embedding = embedding + [0.0] * (384 - len(embedding))

        self.embeddings_cache[text] = embedding
        return embedding

    def _simple_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity for fallback"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        return intersection / union if union > 0 else 0.0

    def _metadata_to_episode(self, metadata: Dict) -> Any:
        """Convert metadata back to episode object"""
        if "failure_reason" in metadata:
            return FailureEpisode(**metadata)
        else:
            return SuccessEpisode(**metadata)

class PatternRecognizer:
    """Recognizes patterns in failure and success episodes"""

    def __init__(self):
        self.patterns: Dict[str, PatternInsight] = {}

    def analyze_patterns(self, episodes: List[Any]) -> List[PatternInsight]:
        """Analyze episodes for patterns"""
        if not episodes:
            return []

        patterns = []

        # Analyze failure patterns
        failures = [e for e in episodes if isinstance(e, FailureEpisode)]
        patterns.extend(self._analyze_failure_patterns(failures))

        # Analyze success patterns
        successes = [e for e in episodes if isinstance(e, SuccessEpisode)]
        patterns.extend(self._analyze_success_patterns(successes))

        return patterns

    def _analyze_failure_patterns(self, failures: List[FailureEpisode]) -> List[PatternInsight]:
        """Analyze common failure patterns"""
        patterns = []

        # Group by failure reason
        failure_reasons = Counter(f.failure_reason for f in failures)

        for reason, count in failure_reasons.most_common(5):
            if count >= 2:  # Pattern threshold
                pattern = PatternInsight(
                    pattern_id=f"failure_{hashlib.md5(reason.encode()).hexdigest()[:8]}",
                    pattern_type="failure_mode",
                    frequency=count,
                    confidence=min(0.9, count / len(failures)),
                    description=f"Recurring failure: {reason}",
                    examples=[f.episode_id for f in failures if f.failure_reason == reason][:3],
                    recommendations=[f"Avoid patterns that lead to: {reason}"]
                )
                patterns.append(pattern)

        # Analyze attempted strategies that consistently fail
        strategy_failures = defaultdict(list)
        for f in failures:
            strategy_failures[f.attempted_strategy].append(f)

        for strategy, strategy_failures_list in strategy_failures.items():
            if len(strategy_failures_list) >= 2:
                pattern = PatternInsight(
                    pattern_id=f"bad_strategy_{hashlib.md5(strategy.encode()).hexdigest()[:8]}",
                    pattern_type="ineffective_strategy",
                    frequency=len(strategy_failures_list),
                    confidence=len(strategy_failures_list) / len(failures),
                    description=f"Ineffective strategy: {strategy}",
                    examples=[f.episode_id for f in strategy_failures_list[:3]],
                    recommendations=[f"Consider alternatives to: {strategy}"]
                )
                patterns.append(pattern)

        return patterns

    def _analyze_success_patterns(self, successes: List[SuccessEpisode]) -> List[PatternInsight]:
        """Analyze successful solution patterns"""
        patterns = []

        # Group by solution strategy
        strategies = Counter(s.solution_strategy for s in successes)

        for strategy, count in strategies.most_common(5):
            if count >= 2:
                pattern = PatternInsight(
                    pattern_id=f"success_{hashlib.md5(strategy.encode()).hexdigest()[:8]}",
                    pattern_type="solution_strategy",
                    frequency=count,
                    confidence=min(0.9, count / len(successes)),
                    description=f"Effective strategy: {strategy}",
                    examples=[s.episode_id for s in successes if s.solution_strategy == strategy][:3],
                    recommendations=[f"Consider applying: {strategy}"]
                )
                patterns.append(pattern)

        return patterns

class ReflectorAgent(AgentBase):
    """
    Enhanced ReflectorAgent with meta-learning capabilities.
    Implements the v0.49 specification with long-term memory and pattern recognition.
    """

    def __init__(self, agent_id: str = "reflector_agent", api_key: str = None):
        super().__init__(agent_id)
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")

        # Initialize memory systems
        self.memory_store = VectorMemoryStore()
        self.pattern_recognizer = PatternRecognizer()

        # Performance tracking
        self.reflection_count = 0
        self.pattern_application_success = 0

        # Subscribe to evaluation critiques
        self.subscribe_to_events([
            "evaluation_critique",
            "correction_needed",
            "performance_profile"
        ])

        logging.info("ReflectorAgent with meta-learning initialized")

    def process_event(self, obj: BlackboardObject) -> Optional[Dict[str, Any]]:
        """Process blackboard events"""
        if obj.object_type == "evaluation_critique":
            return self._process_failure_critique(obj)
        elif obj.object_type == "correction_needed":
            return self._generate_correction_strategy(obj)

        return None

    def _process_failure_critique(self, obj: BlackboardObject) -> Dict[str, Any]:
        """Process a failure critique and store as episode"""
        critique_data = obj.data

        # Create failure episode
        episode = FailureEpisode(
            episode_id=f"failure_{int(time.time())}_{self.reflection_count}",
            timestamp=time.time(),
            initial_code=critique_data.get("initial_code", ""),
            failed_code=critique_data.get("failed_code", ""),
            task_description=critique_data.get("task_description", ""),
            failure_reason=critique_data.get("reason", "unknown"),
            critique_details=critique_data,
            performance_data=critique_data.get("performance_data"),
            attempted_strategy=critique_data.get("attempted_strategy", "unknown"),
            meta_analysis=self._perform_meta_analysis(critique_data),
            tags=["failure", critique_data.get("task_type", "general")]
        )

        # Store in memory
        self.memory_store.store_episode(episode)
        self.reflection_count += 1

        return {
            "object_type": "failure_episode_stored",
            "data": {
                "episode_id": episode.episode_id,
                "meta_analysis": episode.meta_analysis,
                "reflection_count": self.reflection_count
            },
            "created_by": self.agent_id,
            "tags": {"reflection", "failure_analysis"}
        }

    def _generate_correction_strategy(self, obj: BlackboardObject) -> Dict[str, Any]:
        """Generate correction strategy using memory and pattern recognition"""
        failure_context = obj.data

        # Query similar past failures
        query_text = f"Task: {failure_context.get('task_description', '')} Failure: {failure_context.get('failure_reason', '')}"
        similar_episodes = self.memory_store.query_similar_episodes(query_text, n_results=3)

        # Get current patterns
        all_episodes = []
        if hasattr(self.memory_store, 'episodes'):
            all_episodes = list(self.memory_store.episodes.values())

        patterns = self.pattern_recognizer.analyze_patterns(all_episodes)

        # Generate strategy based on memory and patterns
        strategy = self._synthesize_correction_strategy(
            failure_context,
            similar_episodes,
            patterns
        )

        return {
            "object_type": "correction_strategy",
            "data": {
                "strategy": strategy,
                "memory_context": [
                    {
                        "episode_id": ep.episode_id if hasattr(ep, 'episode_id') else "unknown",
                        "similarity": sim,
                        "lesson": self._extract_lesson(ep)
                    } for ep, sim in similar_episodes
                ],
                "applied_patterns": [
                    {
                        "pattern_id": p.pattern_id,
                        "description": p.description,
                        "recommendations": p.recommendations
                    } for p in patterns if p.confidence > 0.5
                ]
            },
            "created_by": self.agent_id,
            "tags": {"correction", "memory_guided"}
        }

    def _perform_meta_analysis(self, critique_data: Dict[str, Any]) -> str:
        """Perform meta-analysis of the failure"""
        failure_reason = critique_data.get("reason", "")
        attempted_strategy = critique_data.get("attempted_strategy", "")

        # Simple meta-analysis - in production would use LLM
        analysis_patterns = {
            "complexity": "This appears to be a complexity optimization failure. The strategy may not have addressed the root algorithmic issue.",
            "correctness": "This is a correctness failure. The logic may have been flawed or edge cases not handled.",
            "performance": "This is a performance regression. The optimization may have introduced overhead.",
            "timeout": "This is an efficiency failure. The algorithm may be too slow for large inputs."
        }

        for pattern, description in analysis_patterns.items():
            if pattern in failure_reason.lower():
                return description

        return f"General failure analysis: {failure_reason}. Strategy attempted: {attempted_strategy}"

    def _synthesize_correction_strategy(self, failure_context: Dict[str, Any],
                                      similar_episodes: List[Tuple[Any, float]],
                                      patterns: List[PatternInsight]) -> Dict[str, Any]:
        """Synthesize correction strategy from memory and patterns"""
        strategy = {
            "approach": "memory_guided_correction",
            "specific_guidance": "",
            "analogical_hints": [],
            "avoid_patterns": [],
            "confidence": 0.5
        }

        # Extract lessons from similar episodes
        lessons_learned = []
        for episode, similarity in similar_episodes:
            if similarity > 0.7:  # High similarity threshold
                lesson = self._extract_lesson(episode)
                lessons_learned.append(lesson)
                strategy["analogical_hints"].append(f"Similar problem solved by: {lesson}")

        # Apply pattern insights
        for pattern in patterns:
            if pattern.pattern_type == "ineffective_strategy" and pattern.confidence > 0.6:
                strategy["avoid_patterns"].append(pattern.description)
            elif pattern.pattern_type == "solution_strategy" and pattern.confidence > 0.7:
                strategy["analogical_hints"].extend(pattern.recommendations)

        # Generate specific guidance
        failure_reason = failure_context.get("failure_reason", "")

        if "complexity" in failure_reason.lower():
            strategy["specific_guidance"] = (
                "Focus on algorithmic improvements. "
                "Based on memory analysis, consider: " +
                "; ".join(strategy["analogical_hints"][:2])
            )
        elif "correctness" in failure_reason.lower():
            strategy["specific_guidance"] = (
                "Focus on logical correctness and edge cases. "
                "Review similar successful approaches: " +
                "; ".join(strategy["analogical_hints"][:2])
            )
        else:
            strategy["specific_guidance"] = (
                "Apply lessons from similar cases: " +
                "; ".join(strategy["analogical_hints"][:3])
            )

        # Calculate confidence based on memory quality
        if similar_episodes and similar_episodes[0][1] > 0.8:
            strategy["confidence"] = 0.8
        elif lessons_learned:
            strategy["confidence"] = 0.6

        return strategy

    def _extract_lesson(self, episode: Any) -> str:
        """Extract key lesson from an episode"""
        if isinstance(episode, SuccessEpisode):
            return episode.solution_strategy
        elif isinstance(episode, FailureEpisode):
            return f"Avoid: {episode.attempted_strategy} (led to {episode.failure_reason})"
        else:
            return "General experience"

    def store_success_episode(self, success_data: Dict[str, Any]):
        """Store a successful episode"""
        episode = SuccessEpisode(
            episode_id=f"success_{int(time.time())}_{self.reflection_count}",
            timestamp=time.time(),
            initial_code=success_data.get("initial_code", ""),
            final_code=success_data.get("final_code", ""),
            task_description=success_data.get("task_description", ""),
            solution_strategy=success_data.get("solution_strategy", ""),
            performance_improvement=success_data.get("performance_improvement", {}),
            meta_analysis=f"Successful strategy: {success_data.get('solution_strategy', '')}",
            tags=["success", success_data.get("task_type", "general")]
        )

        self.memory_store.store_episode(episode)

    def get_learning_metrics(self) -> Dict[str, Any]:
        """Get meta-learning performance metrics"""
        all_episodes = []
        if hasattr(self.memory_store, 'episodes'):
            all_episodes = list(self.memory_store.episodes.values())

        patterns = self.pattern_recognizer.analyze_patterns(all_episodes)

        return {
            "total_reflections": self.reflection_count,
            "episodes_stored": len(all_episodes),
            "patterns_identified": len(patterns),
            "memory_store_type": self.memory_store.store_type,
            "learning_rate": self.pattern_application_success / max(1, self.reflection_count),
            "pattern_confidence_avg": np.mean([p.confidence for p in patterns]) if patterns else 0.0
        }