"""
Hofstadter's Analogy Engine (v0.85)

Implements analogical reasoning inspired by Douglas Hofstadter's work on
analogy and cognition. Maps abstract patterns across different domains
to enable transfer learning.

Based on concepts from:
- "Gödel, Escher, Bach" (strange loops, isomorphism)
- "Fluid Concepts and Creative Analogies" (copycat architecture)
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random


class ConceptType(Enum):
    """Types of concepts that can be mapped"""
    POSITION = "position"  # Physical location (center, corner, edge)
    ACTION = "action"      # Move types (block, attack, defend)
    RESOURCE = "resource"  # Game elements (pieces, spaces)
    PATTERN = "pattern"    # Strategic patterns (fork, pin)
    PROPERTY = "property"  # Attributes (mobility, control)


@dataclass
class Concept:
    """
    Abstract concept that can exist across domains

    Example: "Center control" is a concept that manifests as:
    - Connect4: Middle columns (2-4)
    - Othello: Corner squares
    - Chess: Central squares (d4, e4, d5, e5)
    """
    concept_id: str
    concept_type: ConceptType
    name: str
    description: str
    domain_instances: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5  # 0.0 to 1.0


@dataclass
class AnalogyMapping:
    """
    Mapping between concepts across domains

    Example: Connect4 "center columns" ≈ Othello "corner squares"
    """
    mapping_id: str
    source_domain: str
    target_domain: str
    source_concept: Concept
    target_concept: Concept
    similarity_score: float  # 0.0 to 1.0
    verified: bool = False  # Has this mapping been empirically validated?
    success_count: int = 0  # Times this mapping led to good outcomes
    failure_count: int = 0  # Times this mapping led to bad outcomes


class AnalogyEngine:
    """
    Hofstadter-inspired analogy engine for cross-domain reasoning

    Key capabilities:
    1. Identify abstract concepts within domains
    2. Map concepts across domains based on structural similarity
    3. Transfer strategies using analogical mapping
    4. Validate mappings through empirical testing
    """

    def __init__(self, engine_id: str = "analogy_engine_001"):
        self.engine_id = engine_id
        self.concepts = []
        self.mappings = []
        self.domains = set()

    def register_concept(self, concept: Concept):
        """Register a new abstract concept"""
        self.concepts.append(concept)
        self.domains.update(concept.domain_instances.keys())

    def create_mapping(self, source_domain: str, target_domain: str,
                      source_concept_id: str, target_concept_id: str) -> Optional[AnalogyMapping]:
        """
        Create analogical mapping between concepts in different domains

        Args:
            source_domain: Source game/domain
            target_domain: Target game/domain
            source_concept_id: ID of source concept
            target_concept_id: ID of target concept

        Returns:
            AnalogyMapping or None if concepts not found
        """
        # Find concepts
        source_concept = None
        target_concept = None

        for c in self.concepts:
            if c.concept_id == source_concept_id:
                source_concept = c
            if c.concept_id == target_concept_id:
                target_concept = c

        if source_concept is None or target_concept is None:
            return None

        # Calculate similarity
        similarity = self._calculate_similarity(source_concept, target_concept)

        # Create mapping
        mapping = AnalogyMapping(
            mapping_id=f"map_{len(self.mappings)}",
            source_domain=source_domain,
            target_domain=target_domain,
            source_concept=source_concept,
            target_concept=target_concept,
            similarity_score=similarity
        )

        self.mappings.append(mapping)
        return mapping

    def _calculate_similarity(self, concept1: Concept, concept2: Concept) -> float:
        """
        Calculate structural similarity between concepts

        Uses multiple factors:
        - Type similarity (same ConceptType)
        - Importance similarity
        - Domain count (concepts in more domains are more general)
        """
        similarity = 0.0

        # Type match (0.4 weight)
        if concept1.concept_type == concept2.concept_type:
            similarity += 0.4

        # Importance similarity (0.3 weight)
        importance_diff = abs(concept1.importance - concept2.importance)
        similarity += 0.3 * (1.0 - importance_diff)

        # Generality similarity (0.3 weight)
        # Concepts in similar number of domains are more analogous
        domains1 = len(concept1.domain_instances)
        domains2 = len(concept2.domain_instances)
        max_domains = max(domains1, domains2)
        if max_domains > 0:
            domain_similarity = 1.0 - abs(domains1 - domains2) / max_domains
            similarity += 0.3 * domain_similarity

        return min(1.0, similarity)

    def find_analogy(self, source_domain: str, target_domain: str,
                    source_concept_id: str) -> Optional[Concept]:
        """
        Find analogous concept in target domain

        Args:
            source_domain: Source game/domain
            target_domain: Target game/domain
            source_concept_id: Concept to find analogy for

        Returns:
            Best matching concept in target domain, or None
        """
        # Find source concept
        source_concept = None
        for c in self.concepts:
            if c.concept_id == source_concept_id:
                source_concept = c
                break

        if source_concept is None:
            return None

        # Find target concepts in same category
        target_candidates = [
            c for c in self.concepts
            if target_domain in c.domain_instances
            and c.concept_type == source_concept.concept_type
        ]

        if not target_candidates:
            return None

        # Return most similar
        best_match = max(target_candidates,
                        key=lambda c: self._calculate_similarity(source_concept, c))
        return best_match

    def transfer_strategy(self, source_domain: str, target_domain: str,
                         source_strategy: str) -> str:
        """
        Transfer strategy from source to target domain using analogy

        Args:
            source_domain: Source game/domain
            target_domain: Target game/domain
            source_strategy: Strategy description from source

        Returns:
            Analogous strategy for target domain
        """
        # Find relevant mappings
        relevant_mappings = [
            m for m in self.mappings
            if m.source_domain == source_domain and m.target_domain == target_domain
            and m.similarity_score > 0.6  # Only use strong analogies
        ]

        if not relevant_mappings:
            return f"Apply general principles from {source_domain} to {target_domain}"

        # Build transferred strategy
        parts = [f"Strategy Transfer from {source_domain} to {target_domain}:"]
        parts.append("")

        strategy_lower = source_strategy.lower()

        for mapping in relevant_mappings:
            source_name = mapping.source_concept.name.lower()
            target_name = mapping.target_concept.name

            # Check if source concept mentioned in strategy
            if source_name in strategy_lower:
                parts.append(
                    f"• {mapping.source_concept.name} ({source_domain}) "
                    f"≈ {target_name} ({target_domain})"
                )
                parts.append(f"  Similarity: {mapping.similarity_score:.1%}")

                if mapping.verified:
                    success_rate = (mapping.success_count /
                                  (mapping.success_count + mapping.failure_count)
                                  if (mapping.success_count + mapping.failure_count) > 0
                                  else 0.0)
                    parts.append(f"  Validated: {success_rate:.1%} success rate")

        parts.append("")
        parts.append(f"Adapted Strategy for {target_domain}:")

        # Simple keyword substitution for demo
        transferred = source_strategy
        for mapping in relevant_mappings:
            transferred = transferred.replace(
                mapping.source_concept.name,
                mapping.target_concept.name
            )

        parts.append(transferred)

        return "\n".join(parts)

    def validate_mapping(self, mapping_id: str, success: bool):
        """
        Update mapping based on empirical validation

        Args:
            mapping_id: ID of mapping to validate
            success: Whether using this mapping led to success
        """
        for mapping in self.mappings:
            if mapping.mapping_id == mapping_id:
                if success:
                    mapping.success_count += 1
                else:
                    mapping.failure_count += 1

                # Mark as verified after 5+ trials
                if (mapping.success_count + mapping.failure_count) >= 5:
                    mapping.verified = True

                # Update similarity score based on empirical results
                total_trials = mapping.success_count + mapping.failure_count
                empirical_score = mapping.success_count / total_trials

                # Weighted average: 50% original similarity, 50% empirical
                mapping.similarity_score = (
                    0.5 * mapping.similarity_score +
                    0.5 * empirical_score
                )
                break

    def get_best_mappings(self, source_domain: str, target_domain: str,
                         min_similarity: float = 0.5) -> List[AnalogyMapping]:
        """
        Get best validated mappings between domains

        Args:
            source_domain: Source domain
            target_domain: Target domain
            min_similarity: Minimum similarity threshold

        Returns:
            List of mappings sorted by similarity
        """
        relevant = [
            m for m in self.mappings
            if m.source_domain == source_domain
            and m.target_domain == target_domain
            and m.similarity_score >= min_similarity
        ]

        return sorted(relevant, key=lambda m: m.similarity_score, reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get analogy engine statistics"""
        verified_mappings = sum(1 for m in self.mappings if m.verified)

        return {
            'engine_id': self.engine_id,
            'total_concepts': len(self.concepts),
            'total_mappings': len(self.mappings),
            'verified_mappings': verified_mappings,
            'domains': list(self.domains),
            'avg_similarity': (sum(m.similarity_score for m in self.mappings) / len(self.mappings)
                             if self.mappings else 0.0)
        }


def create_game_concepts() -> List[Concept]:
    """
    Create standard game concepts for Connect4, Othello, Chess

    Returns:
        List of Concept objects
    """
    concepts = []

    # Center Control concept
    center_control = Concept(
        concept_id="center_control",
        concept_type=ConceptType.POSITION,
        name="Center Control",
        description="Controlling strategically important central positions",
        domain_instances={
            'connect4': {'positions': [2, 3, 4], 'description': 'Middle columns'},
            'othello': {'positions': [(3,3), (3,4), (4,3), (4,4)], 'description': 'Central 4 squares'},
            'chess': {'positions': ['d4', 'e4', 'd5', 'e5'], 'description': 'Central squares'}
        },
        importance=0.9
    )
    concepts.append(center_control)

    # Blocking/Threat Prevention
    threat_prevention = Concept(
        concept_id="threat_prevention",
        concept_type=ConceptType.ACTION,
        name="Threat Prevention",
        description="Identifying and neutralizing opponent threats",
        domain_instances={
            'connect4': {'action': 'block_four_in_row', 'description': 'Block 3-in-a-row threats'},
            'othello': {'action': 'avoid_giving_corners', 'description': 'Don\'t give up corners'},
            'chess': {'action': 'defend_pieces', 'description': 'Protect attacked pieces'}
        },
        importance=0.95
    )
    concepts.append(threat_prevention)

    # Material Advantage
    material_advantage = Concept(
        concept_id="material_advantage",
        concept_type=ConceptType.RESOURCE,
        name="Material Advantage",
        description="Maintaining superiority in pieces or position",
        domain_instances={
            'connect4': {'metric': 'connected_pieces', 'description': 'Number of connected sequences'},
            'othello': {'metric': 'piece_count', 'description': 'Number of pieces on board'},
            'chess': {'metric': 'piece_value', 'description': 'Total material value'}
        },
        importance=0.8
    )
    concepts.append(material_advantage)

    # Mobility/Flexibility
    mobility = Concept(
        concept_id="mobility",
        concept_type=ConceptType.PROPERTY,
        name="Mobility",
        description="Number of available moves and options",
        domain_instances={
            'connect4': {'metric': 'open_columns', 'description': 'Available columns'},
            'othello': {'metric': 'legal_moves', 'description': 'Number of legal moves'},
            'chess': {'metric': 'move_count', 'description': 'Piece mobility'}
        },
        importance=0.7
    )
    concepts.append(mobility)

    # Corner/Edge Control
    strong_positions = Concept(
        concept_id="strong_positions",
        concept_type=ConceptType.POSITION,
        name="Strong Positions",
        description="Controlling the strongest/most stable positions",
        domain_instances={
            'othello': {'positions': [(0,0), (0,7), (7,0), (7,7)], 'description': 'Corner squares'},
            'chess': {'positions': ['outposts'], 'description': 'Protected advanced squares'},
            'draughts': {'positions': ['king_row'], 'description': 'Back row for promotion'}
        },
        importance=0.85
    )
    concepts.append(strong_positions)

    return concepts
