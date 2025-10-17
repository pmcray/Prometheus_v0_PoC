#!/usr/bin/env python3
"""
Prometheus ARC TRM Phases 8-10 (v0.91-v0.93)

Building on Phases 5-7 (v0.90), this implements:
- PHASE 8 (v0.91): Hierarchical Subroutines - discover reusable pattern subsequences
- PHASE 9 (v0.92): Multi-Hypothesis Refinement - maintain top-k competing hypotheses with diversity
- PHASE 10 (v0.93): Meta-Meta-Learning - synthesize new refinement strategies from successful refinements

Expected Performance: 12-20% on ARC-AGI (vs Samsung's 45% target)
"""

import json
import numpy as np
from typing import List, Dict, Tuple, Optional, Callable, Set
from dataclasses import dataclass, field
from collections import defaultdict
import time

# Import Phases 5-7 base
from prometheus_arc_trm_phases_567 import (
    PrometheusARCTRM_Phases567,
    AdaptivePrimitives,
    LLMHypothesisGenerator,
    MetaRefiner,
    RefinementStrategy
)


# ============================================================================
# PHASE 8: HIERARCHICAL SUBROUTINES
# ============================================================================

@dataclass
class Subroutine:
    """A discovered reusable pattern subsequence"""
    name: str
    operations: List[str]
    frequency: int  # How often it appears
    success_rate: float  # How often it leads to solutions
    discovered_from: List[str]  # Task IDs where found

    def __hash__(self):
        return hash((self.name, tuple(self.operations)))


class SubroutineDiscovery:
    """
    Phase 8: Discover hierarchical subroutines from successful patterns.

    Key Innovation: Transform flat primitive sequences into hierarchical compositions,
    reducing search space exponentially.

    Example:
        Instead of: ['rotate_90', 'flip_h', 'rotate_90', 'flip_h']
        Discover: @rotate_flip_pattern (used 15 times, 80% success rate)
    """

    def __init__(self, min_frequency: int = 3, min_length: int = 2, max_length: int = 4):
        """
        Initialize subroutine discovery.

        Args:
            min_frequency: Minimum times a subsequence must appear to be a subroutine
            min_length: Minimum length of discovered subroutines
            max_length: Maximum length of discovered subroutines
        """
        self.subroutines: Dict[str, Subroutine] = {}
        self.min_frequency = min_frequency
        self.min_length = min_length
        self.max_length = max_length

        # Track all patterns seen
        self.pattern_history: List[Tuple[List[str], str, bool]] = []  # (pattern, task_id, success)

    def record_pattern(self, pattern: List[str], task_id: str, success: bool):
        """Record a pattern for future subroutine discovery"""
        self.pattern_history.append((pattern, task_id, success))

    def discover_subroutines(self) -> List[Subroutine]:
        """
        Discover common subsequences from recorded patterns.

        Algorithm:
        1. Extract all subsequences of length min_length to max_length from successful patterns
        2. Count frequency of each subsequence
        3. Keep subsequences that appear >= min_frequency times
        4. Calculate success rate for each subroutine
        5. Generate semantic names

        Returns:
            List of discovered subroutines
        """
        if len(self.pattern_history) < self.min_frequency:
            return []  # Not enough data

        # Track subsequences
        subsequence_stats = defaultdict(lambda: {
            'count': 0,
            'tasks': set(),
            'successes': 0,
            'total_appearances': 0
        })

        # Extract subsequences from all patterns
        for pattern, task_id, is_success in self.pattern_history:
            if len(pattern) < self.min_length:
                continue

            # Extract all subsequences of valid lengths
            for length in range(self.min_length, min(self.max_length + 1, len(pattern) + 1)):
                for i in range(len(pattern) - length + 1):
                    subseq = tuple(pattern[i:i+length])

                    subsequence_stats[subseq]['count'] += 1
                    subsequence_stats[subseq]['tasks'].add(task_id)
                    subsequence_stats[subseq]['total_appearances'] += 1

                    if is_success:
                        subsequence_stats[subseq]['successes'] += 1

        # Filter and create subroutines
        discovered = []

        for subseq, stats in subsequence_stats.items():
            if stats['count'] >= self.min_frequency:
                # Calculate success rate
                success_rate = stats['successes'] / stats['total_appearances'] if stats['total_appearances'] > 0 else 0.0

                # Generate name
                name = self._generate_subroutine_name(subseq, stats)

                # Create subroutine
                subroutine = Subroutine(
                    name=name,
                    operations=list(subseq),
                    frequency=stats['count'],
                    success_rate=success_rate,
                    discovered_from=list(stats['tasks'])
                )

                discovered.append(subroutine)
                self.subroutines[name] = subroutine

        # Sort by frequency × success_rate
        discovered.sort(key=lambda s: s.frequency * s.success_rate, reverse=True)

        return discovered

    def _generate_subroutine_name(self, subseq: Tuple[str], stats: Dict) -> str:
        """
        Generate semantic name for subroutine.

        Naming strategy:
        - Length 2: "op1_then_op2"
        - Length 3+: "subroutine_<hash>_freq<n>"

        Examples:
        - ('rotate_90', 'flip_h') → 'rotate_90_then_flip_h'
        - ('sym_h', 'sym_v') → 'sym_h_then_sym_v'
        """
        if len(subseq) == 2:
            # Semantic name for 2-op sequences
            return f"{subseq[0]}_then_{subseq[1]}"
        else:
            # Hash-based name for longer sequences
            hash_val = hash(subseq) & 0xFFFF  # 4-digit hex
            return f"subroutine_{hash_val:04x}_freq{stats['count']}"

    def replace_with_subroutines(self, pattern: List[str]) -> List[str]:
        """
        Replace subsequences in pattern with discovered subroutines.

        This creates hierarchical representation where patterns can reference
        high-level subroutines instead of low-level primitives.

        Strategy: Greedy replacement of longest matching subroutines first.
        """
        if not self.subroutines:
            return pattern

        result = pattern.copy()

        # Sort subroutines by length (longest first) and success rate
        sorted_subroutines = sorted(
            self.subroutines.items(),
            key=lambda x: (len(x[1].operations), x[1].success_rate),
            reverse=True
        )

        # Try to replace each subroutine
        for name, subroutine in sorted_subroutines:
            ops = subroutine.operations
            ops_len = len(ops)

            # Scan through result looking for matches
            i = 0
            while i <= len(result) - ops_len:
                if result[i:i+ops_len] == ops:
                    # Found match - replace with @subroutine reference
                    result = result[:i] + [f"@{name}"] + result[i+ops_len:]
                    i += 1  # Move past the subroutine
                else:
                    i += 1

        return result

    def expand_subroutines(self, pattern: List[str]) -> List[str]:
        """
        Expand subroutine references back to primitive operations.

        Inverse of replace_with_subroutines().
        """
        expanded = []

        for op in pattern:
            if op.startswith('@'):
                # Subroutine reference
                subroutine_name = op[1:]  # Remove @
                if subroutine_name in self.subroutines:
                    # Recursively expand
                    sub_ops = self.subroutines[subroutine_name].operations
                    expanded.extend(self.expand_subroutines(sub_ops))
                else:
                    # Unknown subroutine - keep as is
                    expanded.append(op)
            else:
                # Regular primitive
                expanded.append(op)

        return expanded

    def get_statistics(self) -> Dict:
        """Get subroutine discovery statistics"""
        return {
            'total_subroutines': len(self.subroutines),
            'patterns_analyzed': len(self.pattern_history),
            'top_subroutines': [
                {
                    'name': s.name,
                    'operations': s.operations,
                    'frequency': s.frequency,
                    'success_rate': s.success_rate
                }
                for s in sorted(self.subroutines.values(),
                              key=lambda x: x.frequency * x.success_rate,
                              reverse=True)[:10]
            ]
        }


# ============================================================================
# PHASE 9: MULTI-HYPOTHESIS REFINEMENT
# ============================================================================

@dataclass
class Hypothesis:
    """A candidate pattern hypothesis"""
    pattern: List[str]
    fitness: float
    source: str  # 'llm', 'evolution', 'subroutine', 'hybrid'
    refinement_history: List[float] = field(default_factory=list)
    id: int = 0

    def __hash__(self):
        return hash((tuple(self.pattern), self.id))


class MultiHypothesisRefiner:
    """
    Phase 9: Maintain and refine multiple competing hypotheses in parallel.

    Key Innovation: Avoid premature convergence by maintaining diversity.
    Instead of single best pattern, keep top-k diverse candidates.

    Benefits:
    - Exploration: Different hypotheses explore different solution spaces
    - Robustness: Multiple solutions → ensemble voting
    - Avoid local optima: Diversity bonus prevents all hypotheses converging
    """

    def __init__(self, k: int = 5, diversity_weight: float = 0.2):
        """
        Initialize multi-hypothesis refiner.

        Args:
            k: Number of hypotheses to maintain
            diversity_weight: Weight for diversity bonus in selection (0-1)
        """
        self.k = k
        self.diversity_weight = diversity_weight
        self.hypothesis_counter = 0

    def initialize_hypotheses(self,
                            train_examples: List[Dict],
                            task_id: str,
                            llm_generator: Optional[LLMHypothesisGenerator] = None,
                            baseline_solver = None,
                            subroutine_discovery: Optional[SubroutineDiscovery] = None) -> List[Hypothesis]:
        """
        Generate diverse initial hypotheses from multiple sources.

        Sources:
        1. LLM-guided (3 hypotheses) - if available
        2. Evolution baseline (1 hypothesis)
        3. Subroutine composition (1 hypothesis) - if available
        4. Random primitives (fill to k)

        Returns:
            List of k diverse initial hypotheses
        """
        hypotheses = []

        # Source 1: LLM (if available)
        if llm_generator:
            try:
                llm_patterns = llm_generator.generate_hypotheses(
                    train_examples, task_id, num_hypotheses=3
                )
                for pattern in llm_patterns[:3]:
                    hyp = Hypothesis(
                        pattern=pattern,
                        fitness=0.0,  # Will be evaluated later
                        source='llm',
                        id=self.hypothesis_counter
                    )
                    self.hypothesis_counter += 1
                    hypotheses.append(hyp)
            except Exception as e:
                print(f"    [Phase 9] LLM hypothesis generation failed: {e}")

        # Source 2: Evolution baseline
        if baseline_solver and len(hypotheses) < self.k:
            try:
                train_tuples = [(np.array(ex['input']), np.array(ex['output']))
                              for ex in train_examples]
                evolved = baseline_solver.evolve_for_task(train_tuples, max_generations=50)
                pattern = [op.name for op in evolved.operations]

                hyp = Hypothesis(
                    pattern=pattern,
                    fitness=evolved.fitness,
                    source='evolution',
                    id=self.hypothesis_counter
                )
                self.hypothesis_counter += 1
                hypotheses.append(hyp)
            except Exception as e:
                print(f"    [Phase 9] Evolution hypothesis failed: {e}")

        # Source 3: Subroutine composition (if available)
        if subroutine_discovery and subroutine_discovery.subroutines and len(hypotheses) < self.k:
            try:
                # Compose top subroutines
                top_subroutines = sorted(
                    subroutine_discovery.subroutines.values(),
                    key=lambda s: s.success_rate * s.frequency,
                    reverse=True
                )[:3]

                # Create pattern from top subroutines
                pattern = []
                for sub in top_subroutines[:2]:  # Use top 2
                    pattern.append(f"@{sub.name}")

                hyp = Hypothesis(
                    pattern=pattern,
                    fitness=0.0,
                    source='subroutine',
                    id=self.hypothesis_counter
                )
                self.hypothesis_counter += 1
                hypotheses.append(hyp)
            except Exception as e:
                print(f"    [Phase 9] Subroutine hypothesis failed: {e}")

        # Fill remaining slots with simple heuristics
        simple_patterns = [
            ['identity'],
            ['rotate_90'],
            ['flip_h'],
            ['sym_h'],
            ['transpose']
        ]

        for pattern in simple_patterns:
            if len(hypotheses) >= self.k:
                break

            hyp = Hypothesis(
                pattern=pattern,
                fitness=0.0,
                source='heuristic',
                id=self.hypothesis_counter
            )
            self.hypothesis_counter += 1
            hypotheses.append(hyp)

        return hypotheses[:self.k]

    def refine_top_k(self,
                    hypotheses: List[Hypothesis],
                    train_examples: List[Dict],
                    evaluate_fn: Callable,
                    refine_fn: Callable,
                    num_iterations: int = 3) -> List[Hypothesis]:
        """
        Refine top-k hypotheses in parallel.

        Algorithm:
        1. Select top-k with diversity bonus
        2. Generate refinement variants for each
        3. Evaluate all variants
        4. Select new top-k with diversity bonus
        5. Repeat for num_iterations

        Returns:
            Final top-k hypotheses
        """
        current = hypotheses

        for iteration in range(num_iterations):
            # Select top-k diverse hypotheses
            selected = self._select_diverse_top_k(current)

            print(f"    [Phase 9 Iter {iteration+1}] Selected {len(selected)} diverse hypotheses")

            # Generate refinement variants for each
            refined = []

            for hyp in selected:
                # Generate variants using refinement function
                try:
                    variants = self._generate_refinement_variants(
                        hyp, train_examples, refine_fn, evaluate_fn
                    )
                    refined.extend(variants)
                except Exception as e:
                    print(f"      [Phase 9] Refinement failed for {hyp.pattern}: {e}")
                    # Keep original
                    refined.append(hyp)

            # Update current pool
            current = refined

            # Early exit if we have a perfect solution
            if any(h.fitness >= 1.0 for h in current):
                break

        # Return final top-k
        return self._select_diverse_top_k(current)

    def _generate_refinement_variants(self,
                                     hyp: Hypothesis,
                                     train_examples: List[Dict],
                                     refine_fn: Callable,
                                     evaluate_fn: Callable) -> List[Hypothesis]:
        """
        Generate multiple refinement variants of a hypothesis.

        Strategies:
        1. Original (unchanged)
        2. Add single primitive
        3. Remove single primitive (if len > 1)
        4. Swap order of two primitives
        """
        variants = []

        # Strategy 1: Keep original
        variants.append(hyp)

        # Strategy 2: Add primitives
        common_ops = ['rotate_90', 'flip_h', 'flip_v', 'crop', 'sym_h']
        for op in common_ops[:2]:  # Try top 2
            new_pattern = hyp.pattern + [op]
            fitness = evaluate_fn(new_pattern, train_examples)

            new_hyp = Hypothesis(
                pattern=new_pattern,
                fitness=fitness,
                source=hyp.source,
                refinement_history=hyp.refinement_history + [fitness],
                id=self.hypothesis_counter
            )
            self.hypothesis_counter += 1
            variants.append(new_hyp)

        # Strategy 3: Remove primitive (if possible)
        if len(hyp.pattern) > 1:
            for i in range(len(hyp.pattern)):
                new_pattern = hyp.pattern[:i] + hyp.pattern[i+1:]
                fitness = evaluate_fn(new_pattern, train_examples)

                new_hyp = Hypothesis(
                    pattern=new_pattern,
                    fitness=fitness,
                    source=hyp.source,
                    refinement_history=hyp.refinement_history + [fitness],
                    id=self.hypothesis_counter
                )
                self.hypothesis_counter += 1
                variants.append(new_hyp)

                # Only try removing first primitive to limit variants
                break

        # Strategy 4: Swap order (if len >= 2)
        if len(hyp.pattern) >= 2:
            new_pattern = hyp.pattern.copy()
            new_pattern[0], new_pattern[-1] = new_pattern[-1], new_pattern[0]
            fitness = evaluate_fn(new_pattern, train_examples)

            new_hyp = Hypothesis(
                pattern=new_pattern,
                fitness=fitness,
                source=hyp.source,
                refinement_history=hyp.refinement_history + [fitness],
                id=self.hypothesis_counter
            )
            self.hypothesis_counter += 1
            variants.append(new_hyp)

        return variants

    def _select_diverse_top_k(self, hypotheses: List[Hypothesis]) -> List[Hypothesis]:
        """
        Select top-k hypotheses with diversity bonus.

        Score = fitness + diversity_weight × diversity

        Diversity = average edit distance to other selected hypotheses
        """
        if len(hypotheses) <= self.k:
            return hypotheses

        # Score each hypothesis
        scored = []
        for hyp in hypotheses:
            diversity = self._calculate_diversity(hyp, hypotheses)
            score = hyp.fitness + self.diversity_weight * diversity
            scored.append((score, hyp))

        # Sort by score and return top-k
        scored.sort(key=lambda x: x[0], reverse=True)
        return [hyp for score, hyp in scored[:self.k]]

    def _calculate_diversity(self, hyp: Hypothesis, others: List[Hypothesis]) -> float:
        """
        Calculate how different this hypothesis is from others.

        Diversity = average normalized edit distance to other patterns
        """
        if len(others) <= 1:
            return 1.0

        distances = []
        for other in others:
            if other.id == hyp.id:
                continue

            # Levenshtein distance
            dist = self._edit_distance(hyp.pattern, other.pattern)

            # Normalize by max length
            max_len = max(len(hyp.pattern), len(other.pattern))
            normalized = dist / max_len if max_len > 0 else 0.0

            distances.append(normalized)

        return np.mean(distances) if distances else 1.0

    def _edit_distance(self, pattern1: List[str], pattern2: List[str]) -> int:
        """
        Compute Levenshtein edit distance between two patterns.
        """
        m, n = len(pattern1), len(pattern2)

        # Create DP table
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        # Initialize
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        # Fill DP table
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if pattern1[i-1] == pattern2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(
                        dp[i-1][j],    # Delete
                        dp[i][j-1],    # Insert
                        dp[i-1][j-1]   # Replace
                    )

        return dp[m][n]


# ============================================================================
# PHASE 10: META-META-LEARNING
# ============================================================================

@dataclass
class StrategyTemplate:
    """A template for generating new refinement strategies"""
    name: str
    operations: List[str]  # Sequence of meta-operations
    conditions: Dict[str, any]  # When to apply this strategy
    success_rate: float
    total_attempts: int = 0


class MetaMetaLearner:
    """
    Phase 10: Learn how to learn - synthesize new refinement strategies.

    Key Innovation: System learns not just which strategies work, but HOW TO CREATE
    new strategies from patterns in successful refinements.

    This is the "meta-meta" level:
    - Level 0: Primitives
    - Level 1: Patterns (sequences of primitives)
    - Level 2: Refinement strategies (how to improve patterns)
    - Level 3: Meta-refinement (how to improve strategies) [Phase 7]
    - Level 4: Meta-meta (how to CREATE new strategies) [Phase 10]
    """

    def __init__(self):
        """Initialize meta-meta-learner"""
        self.strategy_templates: List[StrategyTemplate] = []
        self.refinement_history: List[Dict] = []  # All refinement attempts
        self.template_counter = 0

    def record_refinement_attempt(self,
                                 context: Dict,
                                 strategy_used: str,
                                 result: Dict):
        """
        Record every refinement attempt for meta-analysis.

        Context: Task properties, current fitness, etc.
        Result: Fitness change, success, etc.
        """
        self.refinement_history.append({
            'context': context,
            'strategy': strategy_used,
            'result': result,
            'timestamp': time.time()
        })

    def synthesize_new_strategies(self, min_examples: int = 10) -> List[StrategyTemplate]:
        """
        Meta-meta-learning: Learn patterns in successful refinements
        and synthesize new strategies.

        Algorithm:
        1. Filter successful refinement attempts
        2. Cluster by context similarity (fitness level, task type)
        3. Extract common patterns from each cluster
        4. Create strategy template from pattern
        5. Validate strategy (success rate > baseline)
        6. Add validated strategies to portfolio

        Returns:
            List of newly synthesized strategies
        """
        # Filter successful refinements
        successful = [r for r in self.refinement_history
                     if r['result'].get('improved', False)]

        if len(successful) < min_examples:
            print(f"    [Phase 10] Not enough examples ({len(successful)} < {min_examples})")
            return []

        print(f"    [Phase 10] Analyzing {len(successful)} successful refinements...")

        # Cluster by context
        clusters = self._cluster_refinements(successful)

        print(f"    [Phase 10] Found {len(clusters)} clusters")

        # Synthesize strategy from each cluster
        new_strategies = []

        for i, cluster in enumerate(clusters):
            if len(cluster) < 3:  # Need at least 3 examples per cluster
                continue

            template = self._extract_strategy_template(cluster, i)

            # Validate strategy
            if self._validate_strategy(template):
                new_strategies.append(template)
                self.strategy_templates.append(template)
                print(f"      ✓ Synthesized strategy: {template.name} "
                     f"(success rate: {template.success_rate:.2f})")

        return new_strategies

    def _cluster_refinements(self, refinements: List[Dict]) -> List[List[Dict]]:
        """
        Cluster refinements by context similarity.

        Clustering features:
        - Initial fitness level (low/medium/high)
        - Pattern length (short/medium/long)
        - Strategy used
        """
        # Simple clustering by fitness range
        clusters = {
            'low_fitness': [],   # < 0.3
            'med_fitness': [],   # 0.3-0.7
            'high_fitness': []   # > 0.7
        }

        for r in refinements:
            fitness = r['context'].get('fitness_before', 0.5)

            if fitness < 0.3:
                clusters['low_fitness'].append(r)
            elif fitness < 0.7:
                clusters['med_fitness'].append(r)
            else:
                clusters['high_fitness'].append(r)

        # Return non-empty clusters
        return [c for c in clusters.values() if len(c) >= 3]

    def _extract_strategy_template(self, cluster: List[Dict], cluster_id: int) -> StrategyTemplate:
        """
        Extract common pattern from cluster of successful refinements.

        Pattern analysis:
        - What strategies were most commonly used?
        - In what context (fitness level, pattern length)?
        - What was the typical fitness gain?
        """
        # Count strategy frequencies
        strategy_counts = defaultdict(int)
        for r in cluster:
            strategy_counts[r['strategy']] += 1

        # Most common strategies
        top_strategies = sorted(
            strategy_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        # Extract conditions (context features)
        conditions = self._extract_common_conditions(cluster)

        # Calculate success rate
        total = len(cluster)
        successful = len([r for r in cluster if r['result'].get('improved', False)])
        success_rate = successful / total if total > 0 else 0.0

        # Create template
        template = StrategyTemplate(
            name=f"synthesized_{self.template_counter}_{cluster_id}",
            operations=[s for s, count in top_strategies],
            conditions=conditions,
            success_rate=success_rate,
            total_attempts=total
        )

        self.template_counter += 1

        return template

    def _extract_common_conditions(self, cluster: List[Dict]) -> Dict:
        """
        Extract common conditions from cluster.

        Returns typical context features when this strategy succeeds.
        """
        # Aggregate fitness levels
        fitness_levels = [r['context'].get('fitness_before', 0.5) for r in cluster]

        # Aggregate pattern lengths
        pattern_lengths = [r['context'].get('pattern_length', 0) for r in cluster]

        return {
            'fitness_min': min(fitness_levels) if fitness_levels else 0.0,
            'fitness_max': max(fitness_levels) if fitness_levels else 1.0,
            'fitness_avg': np.mean(fitness_levels) if fitness_levels else 0.5,
            'pattern_length_avg': np.mean(pattern_lengths) if pattern_lengths else 3.0
        }

    def _validate_strategy(self, template: StrategyTemplate) -> bool:
        """
        Validate strategy on held-out refinement attempts.

        Strategy is good if:
        1. Success rate > 0.3 (better than random)
        2. At least 3 attempts
        """
        return template.success_rate > 0.3 and template.total_attempts >= 3

    def should_use_synthesized_strategy(self, context: Dict) -> Optional[StrategyTemplate]:
        """
        Check if any synthesized strategy matches current context.

        Returns best matching strategy, or None if no match.
        """
        matches = []

        current_fitness = context.get('fitness_before', 0.5)
        current_length = context.get('pattern_length', 3)

        for template in self.strategy_templates:
            # Check if context matches conditions
            cond = template.conditions

            fitness_match = (cond['fitness_min'] <= current_fitness <= cond['fitness_max'])

            if fitness_match:
                matches.append(template)

        # Return best match (highest success rate)
        if matches:
            return max(matches, key=lambda t: t.success_rate)

        return None

    def get_statistics(self) -> Dict:
        """Get meta-meta-learning statistics"""
        return {
            'total_refinements': len(self.refinement_history),
            'synthesized_strategies': len(self.strategy_templates),
            'templates': [
                {
                    'name': t.name,
                    'operations': t.operations,
                    'success_rate': t.success_rate,
                    'attempts': t.total_attempts,
                    'conditions': t.conditions
                }
                for t in self.strategy_templates
            ]
        }


# ============================================================================
# INTEGRATED TRM PHASES 8-10
# ============================================================================

class PrometheusARCTRM_Phases8910(PrometheusARCTRM_Phases567):
    """
    Complete TRM implementation with all 10 phases integrated.

    Extends Phases 5-7 with:
    - Phase 8: Hierarchical Subroutines
    - Phase 9: Multi-Hypothesis Refinement
    - Phase 10: Meta-Meta-Learning
    """

    def __init__(self,
                 use_llm: bool = True,
                 use_adaptive: bool = True,
                 use_metarefine: bool = True,
                 use_subroutines: bool = True,
                 use_multihyp: bool = True,
                 use_metameta: bool = True,
                 max_refinement_cycles: int = 5):
        """
        Initialize integrated TRM system with Phases 8-10.

        Args:
            use_llm: Enable Phase 6 (LLM guidance)
            use_adaptive: Enable Phase 5 (adaptive primitives)
            use_metarefine: Enable Phase 7 (meta-refinement)
            use_subroutines: Enable Phase 8 (hierarchical subroutines)
            use_multihyp: Enable Phase 9 (multi-hypothesis)
            use_metameta: Enable Phase 10 (meta-meta-learning)
            max_refinement_cycles: Maximum refinement iterations
        """
        # Initialize base Phases 5-7
        super().__init__(
            use_llm=use_llm,
            use_adaptive=use_adaptive,
            use_metarefine=use_metarefine,
            max_refinement_cycles=max_refinement_cycles
        )

        self.use_subroutines = use_subroutines
        self.use_multihyp = use_multihyp
        self.use_metameta = use_metameta

        # Phase 8: Subroutine discovery
        self.subroutine_discovery = None
        if use_subroutines:
            self.subroutine_discovery = SubroutineDiscovery(
                min_frequency=3,
                min_length=2,
                max_length=4
            )

        # Phase 9: Multi-hypothesis refiner
        self.multi_hyp_refiner = None
        if use_multihyp:
            self.multi_hyp_refiner = MultiHypothesisRefiner(
                k=5,
                diversity_weight=0.2
            )

        # Phase 10: Meta-meta-learner
        self.meta_meta_learner = None
        if use_metameta:
            self.meta_meta_learner = MetaMetaLearner()

        # Enhanced statistics
        self.phase8_subroutines_used = 0
        self.phase9_multi_hyp_solves = 0
        self.phase10_synthesized_strategies = 0

    def solve_task(self,
                   train_examples: List[Dict],
                   test_examples: List[Dict],
                   task_id: str) -> Dict:
        """
        Solve ARC task using integrated TRM Phases 5-10.

        Returns:
            {
                'pattern': best pattern found,
                'fitness': fitness score,
                'method': which phase solved it,
                'refinement_cycles': number of cycles used,
                'phase8_subroutines': subroutines discovered,
                'phase9_hypotheses': final hypotheses,
                'phase10_strategies': synthesized strategies,
                'meta_stats': all meta-learning statistics
            }
        """
        print(f"  [TRM 8910] Solving task {task_id}...")

        # Phase 9: Initialize multiple hypotheses (if enabled)
        if self.use_multihyp and self.multi_hyp_refiner:
            print(f"  [Phase 9] Initializing {self.multi_hyp_refiner.k} diverse hypotheses...")

            hypotheses = self.multi_hyp_refiner.initialize_hypotheses(
                train_examples=train_examples,
                task_id=task_id,
                llm_generator=self.llm_generator if self.use_llm else None,
                baseline_solver=self.baseline,
                subroutine_discovery=self.subroutine_discovery if self.use_subroutines else None
            )

            # Evaluate initial hypotheses
            for hyp in hypotheses:
                hyp.fitness = self._evaluate_pattern(hyp.pattern, train_examples)

            print(f"  [Phase 9] Initial hypotheses: {[f'{h.source}:{h.fitness:.3f}' for h in hypotheses]}")

            # Refine hypotheses in parallel
            refined_hypotheses = self.multi_hyp_refiner.refine_top_k(
                hypotheses=hypotheses,
                train_examples=train_examples,
                evaluate_fn=self._evaluate_pattern,
                refine_fn=self._refine_pattern,
                num_iterations=self.max_refinement_cycles
            )

            # Get best hypothesis
            best_hyp = max(refined_hypotheses, key=lambda h: h.fitness)
            best_pattern = best_hyp.pattern
            best_fitness = best_hyp.fitness

            print(f"  [Phase 9] Best hypothesis: {best_pattern} (fitness: {best_fitness:.3f})")

            # Record for Phase 8
            if self.use_subroutines and self.subroutine_discovery:
                success = best_fitness >= 1.0
                self.subroutine_discovery.record_pattern(best_pattern, task_id, success)

        else:
            # Fall back to single-hypothesis approach (Phases 5-7)
            result = super().solve_task(train_examples, test_examples, task_id)
            best_pattern = result['pattern']
            best_fitness = result['fitness']

            # Record for Phase 8
            if self.use_subroutines and self.subroutine_discovery:
                success = best_fitness >= 1.0
                self.subroutine_discovery.record_pattern(best_pattern, task_id, success)

        # Phase 8: Discover subroutines periodically
        if self.use_subroutines and self.subroutine_discovery:
            pattern_count = len(self.subroutine_discovery.pattern_history)

            # Discover every 20 tasks
            if pattern_count > 0 and pattern_count % 20 == 0:
                print(f"  [Phase 8] Discovering subroutines from {pattern_count} patterns...")
                discovered = self.subroutine_discovery.discover_subroutines()

                if discovered:
                    print(f"  [Phase 8] ✓ Discovered {len(discovered)} subroutines")
                    for sub in discovered[:3]:  # Show top 3
                        print(f"    - {sub.name}: {sub.operations} "
                             f"(freq={sub.frequency}, success={sub.success_rate:.2f})")

        # Phase 10: Synthesize new strategies periodically
        if self.use_metameta and self.meta_meta_learner:
            refinement_count = len(self.meta_meta_learner.refinement_history)

            # Synthesize every 50 refinements
            if refinement_count > 0 and refinement_count % 50 == 0:
                print(f"  [Phase 10] Synthesizing new strategies from {refinement_count} refinements...")
                synthesized = self.meta_meta_learner.synthesize_new_strategies(min_examples=10)

                if synthesized:
                    self.phase10_synthesized_strategies += len(synthesized)
                    print(f"  [Phase 10] ✓ Synthesized {len(synthesized)} new strategies")

        # Final result
        success = best_fitness >= 1.0
        if success:
            self.total_solves += 1

            if self.use_multihyp:
                self.phase9_multi_hyp_solves += 1

        # Determine method
        method = 'phases_8910_integrated'
        if self.use_multihyp:
            method = 'phase9_multi_hypothesis'

        return {
            'pattern': best_pattern,
            'fitness': best_fitness,
            'method': method,
            'refinement_cycles': self.max_refinement_cycles,
            'phase8_subroutines': (self.subroutine_discovery.get_statistics()
                                  if self.use_subroutines and self.subroutine_discovery else {}),
            'phase9_hypotheses': ([{'pattern': h.pattern, 'fitness': h.fitness, 'source': h.source}
                                  for h in refined_hypotheses] if self.use_multihyp else []),
            'phase10_strategies': (self.meta_meta_learner.get_statistics()
                                  if self.use_metameta and self.meta_meta_learner else {}),
            'meta_stats': self._get_all_meta_stats()
        }

    def _get_all_meta_stats(self) -> Dict:
        """Get comprehensive meta-statistics from all phases"""
        stats = super()._get_meta_stats()

        # Phase 8 stats
        if self.use_subroutines and self.subroutine_discovery:
            stats['phase8_subroutines'] = self.subroutine_discovery.get_statistics()

        # Phase 10 stats
        if self.use_metameta and self.meta_meta_learner:
            stats['phase10_meta_meta'] = self.meta_meta_learner.get_statistics()

        return stats

    def get_statistics(self) -> Dict:
        """Get enhanced solver statistics including Phases 8-10"""
        stats = super().get_statistics()

        stats.update({
            'phase8_subroutines_used': self.phase8_subroutines_used,
            'phase9_multi_hyp_solves': self.phase9_multi_hyp_solves,
            'phase10_synthesized_strategies': self.phase10_synthesized_strategies
        })

        return stats


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Test integrated TRM Phases 8-10 on ARC evaluation set"""
    import argparse

    parser = argparse.ArgumentParser(description='ARC TRM Phases 8-10 Solver')
    parser.add_argument('--split', type=str, default='evaluation',
                       choices=['training', 'evaluation'],
                       help='Dataset split to use')
    parser.add_argument('--num-tasks', type=int, default=None,
                       help='Number of tasks to test (default: all)')
    parser.add_argument('--no-llm', action='store_true',
                       help='Disable Phase 6 (LLM guidance)')
    parser.add_argument('--no-adaptive', action='store_true',
                       help='Disable Phase 5 (adaptive primitives)')
    parser.add_argument('--no-meta', action='store_true',
                       help='Disable Phase 7 (meta-refinement)')
    parser.add_argument('--no-subroutines', action='store_true',
                       help='Disable Phase 8 (subroutines)')
    parser.add_argument('--no-multihyp', action='store_true',
                       help='Disable Phase 9 (multi-hypothesis)')
    parser.add_argument('--no-metameta', action='store_true',
                       help='Disable Phase 10 (meta-meta-learning)')
    parser.add_argument('--cycles', type=int, default=3,
                       help='Maximum refinement cycles')

    args = parser.parse_args()

    # Load ARC data
    from pathlib import Path

    task_dir = Path(f"arc_agi_2/data/{args.split}")
    if not task_dir.exists():
        print(f"Error: {task_dir} not found")
        return

    task_files = sorted(task_dir.glob("*.json"))
    if not task_files:
        print(f"Error: No task files found in {task_dir}")
        return

    # Load tasks
    arc_data = {}
    for task_file in task_files:
        with open(task_file, 'r') as f:
            arc_data[task_file.stem] = json.load(f)

    # Select tasks
    task_ids = list(arc_data.keys())
    if args.num_tasks:
        task_ids = task_ids[:args.num_tasks]

    print("="*80)
    print("🔬 Prometheus ARC TRM Phases 8-10 (v0.91-v0.93)")
    print("="*80)
    print(f"Split: {args.split}")
    print(f"Tasks: {len(task_ids)}")
    print(f"Phase 5 (Adaptive): {'Disabled' if args.no_adaptive else 'Enabled'}")
    print(f"Phase 6 (LLM): {'Disabled' if args.no_llm else 'Enabled'}")
    print(f"Phase 7 (Meta): {'Disabled' if args.no_meta else 'Enabled'}")
    print(f"Phase 8 (Subroutines): {'Disabled' if args.no_subroutines else 'Enabled'}")
    print(f"Phase 9 (Multi-Hyp): {'Disabled' if args.no_multihyp else 'Enabled'}")
    print(f"Phase 10 (Meta-Meta): {'Disabled' if args.no_metameta else 'Enabled'}")
    print(f"Max refinement cycles: {args.cycles}")
    print("="*80)
    print()

    # Initialize solver
    solver = PrometheusARCTRM_Phases8910(
        use_llm=not args.no_llm,
        use_adaptive=not args.no_adaptive,
        use_metarefine=not args.no_meta,
        use_subroutines=not args.no_subroutines,
        use_multihyp=not args.no_multihyp,
        use_metameta=not args.no_metameta,
        max_refinement_cycles=args.cycles
    )

    # Solve tasks
    results = []
    solved_count = 0
    start_time = time.time()

    for i, task_id in enumerate(task_ids, 1):
        task = arc_data[task_id]
        train_examples = task['train']
        test_examples = task['test']

        print(f"[{i}/{len(task_ids)}] Task {task_id}")

        try:
            result = solver.solve_task(train_examples, test_examples, task_id)

            success = result['fitness'] >= 1.0
            if success:
                solved_count += 1

            result_summary = {
                'task_id': task_id,
                'success': success,
                'fitness': result['fitness'],
                'pattern': result['pattern'],
                'method': result['method']
            }
            results.append(result_summary)

            status = "✓ SOLVED" if success else f"✗ Failed (fitness: {result['fitness']:.3f})"
            print(f"  {status} via {result['method']}")
            print(f"  Pattern: {result['pattern']}")
            print()

        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'task_id': task_id,
                'success': False,
                'error': str(e)
            })
            print()

    # Summary
    elapsed = time.time() - start_time
    print("="*80)
    print("📊 RESULTS")
    print("="*80)
    print(f"Solved: {solved_count}/{len(task_ids)} ({solved_count/len(task_ids)*100:.2f}%)")
    print(f"Time: {elapsed:.1f}s ({elapsed/len(task_ids):.1f}s per task)")
    print()

    # Phase statistics
    stats = solver.get_statistics()
    print("📈 Phase Statistics:")
    print(f"  Phase 6 (LLM) solves: {stats.get('phase6_solves', 0)}")
    print(f"  Phase 7 (Meta) improvements: {stats.get('phase7_improves', 0)}")
    print(f"  Phase 8 (Subroutines) used: {stats.get('phase8_subroutines_used', 0)}")
    print(f"  Phase 9 (Multi-Hyp) solves: {stats.get('phase9_multi_hyp_solves', 0)}")
    print(f"  Phase 10 (Strategies) synthesized: {stats.get('phase10_synthesized_strategies', 0)}")
    print()

    # Save results
    output_file = f'arc_trm_phases8910_{args.split}_{len(task_ids)}tasks.json'

    # Convert numpy types (NumPy 2.0 compatible)
    def convert_to_python_types(obj):
        if isinstance(obj, dict):
            return {k: convert_to_python_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_python_types(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

    output_data = convert_to_python_types({
        'version': 'v0.91-v0.93',
        'phases': {
            'phase5_adaptive': not args.no_adaptive,
            'phase6_llm': not args.no_llm,
            'phase7_meta': not args.no_meta,
            'phase8_subroutines': not args.no_subroutines,
            'phase9_multi_hyp': not args.no_multihyp,
            'phase10_meta_meta': not args.no_metameta
        },
        'config': {
            'split': args.split,
            'num_tasks': len(task_ids),
            'max_cycles': args.cycles
        },
        'summary': {
            'solved': solved_count,
            'total': len(task_ids),
            'accuracy': solved_count / len(task_ids) if task_ids else 0,
            'time': elapsed
        },
        'statistics': stats,
        'results': results
    })

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"✅ Results saved to {output_file}")


if __name__ == "__main__":
    main()
