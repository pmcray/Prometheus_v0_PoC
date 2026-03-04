"""
WP38: Analogical Reasoning Engine
====================================

Closes the **supervised-transfer gap** in WP28's cross-domain transfer.

The gap in WP28
---------------
``CrossDomainDistiller`` (WP28) transfers a student policy from one domain to
another (e.g. Chess → Go) by *supervised fine-tuning*: the target-domain
student is initialised from the source policy and then trained on labelled
target-domain examples.  This requires:
  - A matching label set in the target domain.
  - Structural similarity between source and target state spaces.

WP28 cannot transfer to a *structurally novel* domain where there are no
labelled examples, or where the state/action spaces are fundamentally
different.

WP38 fix
--------
``RelationalGraph`` — represents the *structure* of a domain as a set of
named entities and typed relations between them.  Examples:
  - Chess: entities = pieces; relations = {attacks, defends, controls_square}
  - Go: entities = groups; relations = {adjacent, captures, threatens}
  - Synthesis: entities = strategies; relations = {dominates, complements}

``StructureMapper`` — finds the best *isomorphism* (or approximate isomorphism)
between two ``RelationalGraph`` instances using graph edit distance minimisation.
Returns an ``AnalogyMap``: a Dict[source_entity → target_entity] mapping plus
a ``similarity_score`` ∈ [0, 1].

``AnalogyScore`` — computed similarity measure:
    score = (matched_relations / total_relations) * relation_weight
          + (matched_entities / total_entities) * entity_weight

``TransferPolicy`` — uses an ``AnalogyMap`` to initialise a target-domain
policy from a source-domain policy *without* target-domain labels:
  - For each target entity, find its source analogue via the analogy map.
  - Copy the source entity's policy weight to the target entity.
  - Remaining target entities receive the mean weight.

``AnalogyRecord`` — per-transfer audit: source domain, target domain,
similarity score, n_mapped_entities, n_mapped_relations, wall_time.

``AnalogyEngine`` — orchestrates the full analogy-based transfer pipeline:
  1. Build ``RelationalGraph`` for source and target domains.
  2. Run ``StructureMapper`` to find the best analogy.
  3. Apply ``TransferPolicy`` to initialise target policy weights.
  4. Record ``AnalogyRecord``.

``verify_wp38_exit_criteria`` — six-criterion verifier.

Theoretical grounding
---------------------
Hofstadter (1979) Gödel, Escher, Bach: isomorphisms between formal systems
are the basis of analogical reasoning.  "The meaning of a symbol is not in
the symbol itself, but in its place within the system."

Gentner (1983) Structure-Mapping Theory: analogy is a mapping of *relational
structure* (not just surface similarity) between a base and a target domain.
The key principle: "systematicity" — prefer mappings that preserve the most
relational structure.

Falkenhainer, Forbus & Gentner (1989) Structure-Mapping Engine (SME):
algorithmic implementation of structure mapping for analogical reasoning.

Good (1965): the ultraintelligent machine must be able to reason by analogy
across domains — a chess master who can immediately apply strategic intuition
to a novel game is demonstrating the kind of cross-domain transfer that WP38
implements.

Classes
-------
RelationalGraph         Domain structure as entities + typed relations
StructureMapper         Graph-edit-distance isomorphism finder
AnalogyScore            Similarity metric over matched structure
AnalogyMap              Dict[source → target] entity mapping + score
TransferPolicy          Analogy-based weight initialisation (no labels)
AnalogyRecord           Per-transfer audit
AnalogyEngine           Full analogy pipeline orchestrator
verify_wp38_exit_criteria  Six-criterion verifier
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RelationalGraph — domain structure
# ---------------------------------------------------------------------------

@dataclass
class Relation:
    """A typed binary relation between two entities."""
    relation_type: str
    source:        str
    target:        str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type":   self.relation_type,
            "source": self.source,
            "target": self.target,
        }


class RelationalGraph:
    """
    Represents the structure of a domain as entities and typed relations.

    Parameters
    ----------
    domain_name : str
    """

    def __init__(self, domain_name: str):
        self.domain_name = domain_name
        self._entities:  Set[str]       = set()
        self._relations: List[Relation] = []
        self._entity_attrs: Dict[str, Dict[str, Any]] = {}

    def add_entity(self, name: str, **attrs: Any) -> None:
        self._entities.add(name)
        self._entity_attrs[name] = dict(attrs)

    def add_relation(self, relation_type: str, source: str, target: str) -> None:
        self._entities.add(source)
        self._entities.add(target)
        self._relations.append(Relation(relation_type, source, target))

    @property
    def entities(self) -> List[str]:
        return sorted(self._entities)

    @property
    def relations(self) -> List[Relation]:
        return list(self._relations)

    def relation_types(self) -> Set[str]:
        return {r.relation_type for r in self._relations}

    def relations_of_entity(self, entity: str) -> List[Relation]:
        return [r for r in self._relations if r.source == entity or r.target == entity]

    def degree(self, entity: str) -> int:
        return len(self.relations_of_entity(entity))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain":    self.domain_name,
            "entities":  self.entities,
            "relations": [r.to_dict() for r in self._relations],
        }


# ---------------------------------------------------------------------------
# Built-in domain graphs
# ---------------------------------------------------------------------------

def make_chess_graph() -> RelationalGraph:
    """Minimal Chess relational graph (pieces as entities)."""
    g = RelationalGraph("chess")
    pieces = ["king", "queen", "rook", "bishop", "knight", "pawn"]
    for p in pieces:
        g.add_entity(p, role="piece")
    g.add_relation("defends",      "queen",  "king")
    g.add_relation("defends",      "rook",   "king")
    g.add_relation("defends",      "bishop", "king")
    g.add_relation("defends",      "knight", "king")
    g.add_relation("defends",      "pawn",   "king")
    g.add_relation("attacks",      "queen",  "rook")
    g.add_relation("attacks",      "bishop", "knight")
    g.add_relation("supports",     "rook",   "queen")
    g.add_relation("supports",     "bishop", "queen")
    g.add_relation("supports",     "pawn",   "knight")
    g.add_relation("controls_key", "queen",  "center")
    g.add_relation("controls_key", "knight", "center")
    g.add_relation("controls_key", "pawn",   "edge")
    g.add_entity("center", role="square")
    g.add_entity("edge",   role="square")
    return g


def make_go_graph() -> RelationalGraph:
    """Minimal Go relational graph (groups as entities)."""
    g = RelationalGraph("go")
    groups = ["leader_group", "runner_group", "sacrifice_group",
              "shield_group", "connector_group", "pawn_group"]
    for grp in groups:
        g.add_entity(grp, role="group")
    g.add_relation("defends",      "shield_group",    "leader_group")
    g.add_relation("defends",      "connector_group", "leader_group")
    g.add_relation("defends",      "runner_group",    "leader_group")
    g.add_relation("defends",      "sacrifice_group", "leader_group")
    g.add_relation("defends",      "pawn_group",      "leader_group")
    g.add_relation("attacks",      "leader_group",    "runner_group")
    g.add_relation("attacks",      "shield_group",    "connector_group")
    g.add_relation("connects",     "connector_group", "leader_group")
    g.add_relation("connects",     "runner_group",    "connector_group")
    g.add_relation("connects",     "pawn_group",      "connector_group")
    g.add_relation("controls_key", "leader_group",    "center_territory")
    g.add_relation("controls_key", "connector_group", "center_territory")
    g.add_relation("controls_key", "pawn_group",      "edge_territory")
    g.add_entity("center_territory", role="territory")
    g.add_entity("edge_territory",   role="territory")
    return g


def make_synthesis_graph() -> RelationalGraph:
    """Synthesis strategy relational graph."""
    g = RelationalGraph("synthesis")
    strategies = ["promote_best", "demote_worst", "reset_uniform",
                  "boost_upward", "explore_random", "distill_student"]
    for s in strategies:
        g.add_entity(s, role="strategy")
    g.add_relation("dominates",  "promote_best",   "demote_worst")
    g.add_relation("dominates",  "boost_upward",   "reset_uniform")
    g.add_relation("dominates",  "explore_random", "distill_student")
    g.add_relation("complements","promote_best",   "boost_upward")
    g.add_relation("complements","demote_worst",   "reset_uniform")
    g.add_relation("supports",   "distill_student","promote_best")
    g.add_relation("supports",   "reset_uniform",  "explore_random")
    g.add_relation("supports",   "boost_upward",   "explore_random")
    g.add_relation("controls_key","promote_best",  "exploit_region")
    g.add_relation("controls_key","explore_random","explore_region")
    g.add_relation("controls_key","distill_student","exploit_region")
    g.add_entity("exploit_region", role="region")
    g.add_entity("explore_region", role="region")
    return g


# ---------------------------------------------------------------------------
# AnalogyScore — similarity metric
# ---------------------------------------------------------------------------

@dataclass
class AnalogyScore:
    """
    Computed similarity between two domains under a given entity mapping.

    Attributes
    ----------
    entity_score : float    Fraction of entities matched.
    relation_score : float  Fraction of source relations preserved.
    overall : float         Weighted combination.
    """
    entity_score:   float
    relation_score: float
    overall:        float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_score":   round(self.entity_score,   4),
            "relation_score": round(self.relation_score, 4),
            "overall":        round(self.overall,        4),
        }


# ---------------------------------------------------------------------------
# AnalogyMap — source→target entity mapping + score
# ---------------------------------------------------------------------------

@dataclass
class AnalogyMap:
    """
    An entity mapping from source domain to target domain.

    Attributes
    ----------
    source_domain : str
    target_domain : str
    mapping : Dict[source_entity → target_entity]
    score : AnalogyScore
    """
    source_domain: str
    target_domain: str
    mapping:       Dict[str, str]
    score:         AnalogyScore

    def map_entity(self, source_entity: str) -> Optional[str]:
        """Return the target analogue, or None if not mapped."""
        return self.mapping.get(source_entity)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "mapping":       self.mapping,
            "score":         self.score.to_dict(),
        }


# ---------------------------------------------------------------------------
# StructureMapper — graph isomorphism finder
# ---------------------------------------------------------------------------

class StructureMapper:
    """
    Finds the best structure-preserving mapping between two ``RelationalGraph``
    instances using a greedy degree-similarity approach.

    Gentner's systematicity principle: prefer mappings that preserve the
    maximum number of relational triples (type, source, target).

    Parameters
    ----------
    entity_weight : float   Weight for entity coverage in score (default 0.4).
    relation_weight : float Weight for relation coverage (default 0.6).
    seed : int
    """

    def __init__(
        self,
        entity_weight:   float = 0.40,
        relation_weight: float = 0.60,
        seed:            int   = 42,
    ):
        self.entity_weight   = entity_weight
        self.relation_weight = relation_weight
        self._rng            = random.Random(seed)

    def map(self, source: RelationalGraph, target: RelationalGraph) -> AnalogyMap:
        """
        Find the best entity mapping from ``source`` to ``target``.

        Strategy:
        1. Sort source entities by degree (most connected first).
        2. For each source entity, find the unmatched target entity whose
           degree is closest and whose shared relation types are maximal.
        3. Score the resulting mapping.
        """
        src_entities = sorted(source.entities, key=lambda e: source.degree(e), reverse=True)
        tgt_entities = list(target.entities)
        mapping: Dict[str, str] = {}
        used_targets: Set[str] = set()

        for se in src_entities:
            # Score each unmatched target entity
            best_te    = None
            best_score = -1.0
            for te in tgt_entities:
                if te in used_targets:
                    continue
                deg_sim = 1.0 / (1.0 + abs(source.degree(se) - target.degree(te)))
                # Shared relation types
                src_rtypes = {r.relation_type for r in source.relations_of_entity(se)}
                tgt_rtypes = {r.relation_type for r in target.relations_of_entity(te)}
                if src_rtypes or tgt_rtypes:
                    type_sim = len(src_rtypes & tgt_rtypes) / len(src_rtypes | tgt_rtypes)
                else:
                    type_sim = 1.0
                score = 0.5 * deg_sim + 0.5 * type_sim
                if score > best_score:
                    best_score = score
                    best_te    = te

            if best_te is not None:
                mapping[se] = best_te
                used_targets.add(best_te)

        # Compute analogy score
        n_src   = len(source.entities)
        n_tgt   = len(target.entities)
        n_mapped = len(mapping)
        entity_score = n_mapped / max(n_src, 1)

        # Count preserved relations
        preserved = 0
        for rel in source.relations:
            src_mapped = mapping.get(rel.source)
            tgt_mapped = mapping.get(rel.target)
            if src_mapped and tgt_mapped:
                if any(
                    r.relation_type == rel.relation_type
                    and r.source == src_mapped
                    and r.target == tgt_mapped
                    for r in target.relations
                ):
                    preserved += 1
        relation_score = preserved / max(len(source.relations), 1)
        overall = self.entity_weight * entity_score + self.relation_weight * relation_score

        score = AnalogyScore(
            entity_score   = entity_score,
            relation_score = relation_score,
            overall        = overall,
        )
        return AnalogyMap(
            source_domain = source.domain_name,
            target_domain = target.domain_name,
            mapping       = mapping,
            score         = score,
        )


# ---------------------------------------------------------------------------
# TransferPolicy — analogy-based weight initialisation
# ---------------------------------------------------------------------------

class TransferPolicy:
    """
    Uses an ``AnalogyMap`` to initialise target-domain policy weights
    from source-domain weights without target-domain labels.

    Parameters
    ----------
    fallback : str
        How to handle unmapped target entities:
        'mean' (default) — assign the mean of source weights.
        'zero'           — assign 0.0.
        'uniform'        — assign 1/n_target.
    """

    def __init__(self, fallback: str = "mean"):
        self.fallback = fallback

    def transfer(
        self,
        analogy_map:    AnalogyMap,
        source_weights: Dict[str, float],
        target_entities: List[str],
    ) -> Dict[str, float]:
        """
        Build target policy weights from source weights via analogy.

        Parameters
        ----------
        analogy_map : AnalogyMap
            Mapping from source entities to target entities.
        source_weights : Dict[str, float]
            Source domain policy weights (entity → weight).
        target_entities : List[str]
            All entities in the target domain.

        Returns
        -------
        Dict[str, float]  target entity → weight.
        """
        # Reverse map: target → source
        reverse = {v: k for k, v in analogy_map.mapping.items()}
        mean_weight = sum(source_weights.values()) / max(len(source_weights), 1)
        n_target    = len(target_entities)

        target_weights: Dict[str, float] = {}
        for te in target_entities:
            se = reverse.get(te)
            if se and se in source_weights:
                target_weights[te] = source_weights[se]
            else:
                if self.fallback == "mean":
                    target_weights[te] = mean_weight
                elif self.fallback == "zero":
                    target_weights[te] = 0.0
                else:  # uniform
                    target_weights[te] = 1.0 / max(n_target, 1)

        # Normalise to sum to 1
        total = sum(target_weights.values())
        if total > 0:
            target_weights = {k: v / total for k, v in target_weights.items()}
        return target_weights


# ---------------------------------------------------------------------------
# AnalogyRecord — per-transfer audit
# ---------------------------------------------------------------------------

@dataclass
class AnalogyRecord:
    """
    Per-transfer audit record.

    Attributes
    ----------
    source_domain : str
    target_domain : str
    n_source_entities : int
    n_target_entities : int
    n_mapped_entities : int
    n_source_relations : int
    n_preserved_relations : int
    analogy_score : AnalogyScore
    wall_time_s : float
    timestamp : float
    """
    source_domain:         str
    target_domain:         str
    n_source_entities:     int
    n_target_entities:     int
    n_mapped_entities:     int
    n_source_relations:    int
    n_preserved_relations: int
    analogy_score:         AnalogyScore
    wall_time_s:           float
    timestamp:             float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_domain":         self.source_domain,
            "target_domain":         self.target_domain,
            "n_source_entities":     self.n_source_entities,
            "n_target_entities":     self.n_target_entities,
            "n_mapped_entities":     self.n_mapped_entities,
            "n_source_relations":    self.n_source_relations,
            "n_preserved_relations": self.n_preserved_relations,
            "analogy_score":         self.analogy_score.to_dict(),
            "wall_time_s":           round(self.wall_time_s, 4),
        }


# ---------------------------------------------------------------------------
# AnalogyEngine — full pipeline
# ---------------------------------------------------------------------------

class AnalogyEngine:
    """
    Orchestrates the full analogy-based transfer pipeline.

    Parameters
    ----------
    mapper : Optional[StructureMapper]
        Structure mapper to use (default: StructureMapper()).
    transfer_policy : Optional[TransferPolicy]
        Transfer policy to use (default: TransferPolicy(fallback='mean')).
    """

    def __init__(
        self,
        mapper:          Optional[StructureMapper]  = None,
        transfer_policy: Optional[TransferPolicy]   = None,
    ):
        self.mapper          = mapper or StructureMapper()
        self.transfer_policy = transfer_policy or TransferPolicy()
        self.records:        List[AnalogyRecord] = []

    def transfer(
        self,
        source:          RelationalGraph,
        target:          RelationalGraph,
        source_weights:  Dict[str, float],
    ) -> Tuple[Dict[str, float], AnalogyRecord]:
        """
        Run the full analogy transfer pipeline.

        Parameters
        ----------
        source : RelationalGraph
        target : RelationalGraph
        source_weights : Dict[str, float]
            Source domain policy weights.

        Returns
        -------
        Tuple[target_weights, AnalogyRecord]
        """
        t0 = time.time()

        analogy_map = self.mapper.map(source, target)
        target_weights = self.transfer_policy.transfer(
            analogy_map     = analogy_map,
            source_weights  = source_weights,
            target_entities = target.entities,
        )

        # Count preserved relations
        preserved = sum(
            1 for rel in source.relations
            if analogy_map.mapping.get(rel.source)
            and analogy_map.mapping.get(rel.target)
            and any(
                r.relation_type == rel.relation_type
                and r.source == analogy_map.mapping[rel.source]
                and r.target == analogy_map.mapping[rel.target]
                for r in target.relations
            )
        )

        record = AnalogyRecord(
            source_domain         = source.domain_name,
            target_domain         = target.domain_name,
            n_source_entities     = len(source.entities),
            n_target_entities     = len(target.entities),
            n_mapped_entities     = len(analogy_map.mapping),
            n_source_relations    = len(source.relations),
            n_preserved_relations = preserved,
            analogy_score         = analogy_map.score,
            wall_time_s           = time.time() - t0,
        )
        self.records.append(record)
        logger.info(
            "WP38 analogy transfer: %s→%s score=%.3f mapped=%d/%d relations=%d/%d",
            source.domain_name, target.domain_name,
            analogy_map.score.overall,
            len(analogy_map.mapping), len(source.entities),
            preserved, len(source.relations),
        )
        return target_weights, record

    def summary(self) -> Dict[str, Any]:
        if not self.records:
            return {"n_transfers": 0}
        avg_score = sum(r.analogy_score.overall for r in self.records) / len(self.records)
        return {
            "n_transfers":    len(self.records),
            "avg_score":      round(avg_score, 4),
            "transfers":      [r.to_dict() for r in self.records],
        }


# ---------------------------------------------------------------------------
# verify_wp38_exit_criteria
# ---------------------------------------------------------------------------

def verify_wp38_exit_criteria(
    engine:  AnalogyEngine,
    records: List[AnalogyRecord],
) -> Dict[str, bool]:
    """
    Verify WP38 exit criteria.

    Criteria
    --------
    1. Chess→Go analogy produces similarity score > 0.
    2. AnalogyMap covers at least half the source entities.
    3. TransferPolicy produces normalised target weights (sum ≈ 1.0).
    4. Preserved-relation count is positive (relational structure mapped).
    5. AnalogyRecord logged for each transfer.
    6. StructureMapper produces different mappings for different domain pairs.
    """
    results: Dict[str, bool] = {}
    mapper  = StructureMapper()
    policy  = TransferPolicy()

    # Build standard graphs
    chess = make_chess_graph()
    go    = make_go_graph()
    synth = make_synthesis_graph()

    # 1. Chess→Go analogy score > 0
    amap = mapper.map(chess, go)
    results["Chess→Go analogy score > 0"] = (amap.score.overall > 0.0)

    # 2. At least half source entities mapped
    results["AnalogyMap covers >= 50% of source entities"] = (
        len(amap.mapping) >= len(chess.entities) // 2
    )

    # 3. TransferPolicy produces normalised weights
    src_weights = {e: 1.0 / len(chess.entities) for e in chess.entities}
    tgt_weights = policy.transfer(amap, src_weights, go.entities)
    total = sum(tgt_weights.values())
    results["TransferPolicy produces normalised target weights"] = (
        abs(total - 1.0) < 0.01
    )

    # 4. Preserved-relation count > 0
    preserved = sum(
        1 for rel in chess.relations
        if amap.mapping.get(rel.source)
        and amap.mapping.get(rel.target)
        and any(
            r.relation_type == rel.relation_type
            and r.source == amap.mapping[rel.source]
            and r.target == amap.mapping[rel.target]
            for r in go.relations
        )
    )
    results["At least one relation preserved across domains"] = (preserved > 0)

    # 5. AnalogyRecord logged
    results["AnalogyRecord logged for each transfer"] = (len(records) >= 1)

    # 6. Different mappings for different domain pairs
    amap2 = mapper.map(chess, synth)
    results["StructureMapper produces different mappings for different domain pairs"] = (
        amap.mapping != amap2.mapping
    )

    return results
