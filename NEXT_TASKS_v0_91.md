# Next Tasks for v0.91-v0.93: Phases 8-10 Implementation Plan

## Current Status (v0.90)
- ✅ Phase 5: Adaptive primitives (7 context-aware operations)
- ✅ Phase 6: LLM-guided hypothesis generation
- ✅ Phase 7: Meta-refinement (strange loop)
- ✅ 400-task benchmark running (PID 140701)
- ⏳ Test results: TBD (running in background)

## Phase 8: Hierarchical Subroutines (v0.91)

### Goal
Discover reusable pattern subsequences and abstract them into named subroutines, reducing search space and enabling compositional reasoning.

### Implementation Strategy

```python
@dataclass
class Subroutine:
    """A discovered reusable pattern subsequence"""
    name: str
    operations: List[str]
    frequency: int  # How often it appears
    success_rate: float  # How often it leads to solutions
    discovered_from: List[str]  # Task IDs where found

class SubroutineDiscovery:
    """Phase 8: Discover hierarchical subroutines from successful patterns"""

    def __init__(self, min_frequency: int = 3, min_length: int = 2):
        self.subroutines: Dict[str, Subroutine] = {}
        self.min_frequency = min_frequency
        self.min_length = min_length

    def discover_from_successful_patterns(self,
                                         patterns: List[List[str]],
                                         task_ids: List[str],
                                         success: List[bool]) -> List[Subroutine]:
        """
        Find common subsequences in successful patterns.

        Algorithm:
        1. Extract all subsequences of length 2-4 from successful patterns
        2. Count frequency of each subsequence
        3. Keep subsequences that appear >= min_frequency times
        4. Name them based on semantic meaning or frequency
        """
        subsequence_counts = defaultdict(lambda: {'count': 0, 'tasks': set(), 'successes': 0})

        for pattern, task_id, is_success in zip(patterns, task_ids, success):
            if not is_success:
                continue

            # Extract all subsequences
            for length in range(self.min_length, min(5, len(pattern) + 1)):
                for i in range(len(pattern) - length + 1):
                    subseq = tuple(pattern[i:i+length])
                    subsequence_counts[subseq]['count'] += 1
                    subsequence_counts[subseq]['tasks'].add(task_id)
                    if is_success:
                        subsequence_counts[subseq]['successes'] += 1

        # Filter and create subroutines
        discovered = []
        for subseq, stats in subsequence_counts.items():
            if stats['count'] >= self.min_frequency:
                success_rate = stats['successes'] / stats['count']
                name = self._generate_subroutine_name(subseq, stats)
                subroutine = Subroutine(
                    name=name,
                    operations=list(subseq),
                    frequency=stats['count'],
                    success_rate=success_rate,
                    discovered_from=list(stats['tasks'])
                )
                discovered.append(subroutine)
                self.subroutines[name] = subroutine

        return discovered

    def _generate_subroutine_name(self,
                                  subseq: Tuple[str],
                                  stats: Dict) -> str:
        """
        Generate semantic name for subroutine.

        Examples:
        - ['rotate_90', 'flip_h'] → 'rotate_and_flip'
        - ['scale_2x', 'crop'] → 'scale_and_crop'
        - ['sym_h', 'sym_v'] → 'make_symmetric'
        """
        # Simple heuristic: join first 2 operations with '_then_'
        if len(subseq) == 2:
            return f"{subseq[0]}_then_{subseq[1]}"
        else:
            return f"subroutine_{stats['count']}_freq"

    def replace_with_subroutines(self, pattern: List[str]) -> List[str]:
        """
        Replace subsequences in pattern with discovered subroutines.

        This creates a hierarchical representation where high-level
        subroutines can be composed.
        """
        # Try to replace longest matching subroutines first
        result = pattern.copy()

        for name, subroutine in sorted(
            self.subroutines.items(),
            key=lambda x: len(x[1].operations),
            reverse=True
        ):
            # Try to find and replace this subroutine
            ops = subroutine.operations
            for i in range(len(result) - len(ops) + 1):
                if result[i:i+len(ops)] == ops:
                    result = result[:i] + [f"@{name}"] + result[i+len(ops):]

        return result
```

### Integration Points
1. After successful task solve, extract pattern and add to discovery pool
2. Every N tasks, run subroutine discovery
3. Add discovered subroutines to primitive pool as new operations
4. Use @ prefix to denote subroutine (e.g., `@rotate_and_flip`)

### Expected Impact
- **Search space reduction**: Composing 10 subroutines = 100 primitive combinations
- **Transfer learning**: Subroutines learned from task A help task B
- **Semantic abstraction**: Move from low-level ops to high-level concepts

## Phase 9: Multi-Hypothesis Refinement (v0.92)

### Goal
Maintain multiple competing hypotheses in parallel and refine top-k candidates, avoiding premature convergence.

### Implementation Strategy

```python
@dataclass
class Hypothesis:
    """A candidate pattern hypothesis"""
    pattern: List[str]
    fitness: float
    source: str  # 'llm', 'evolution', 'subroutine', etc.
    refinement_history: List[float]  # Fitness over time

class MultiHypothesisRefiner:
    """Phase 9: Maintain and refine multiple competing hypotheses"""

    def __init__(self, k: int = 5, diversity_weight: float = 0.2):
        self.k = k  # Number of hypotheses to maintain
        self.diversity_weight = diversity_weight
        self.hypotheses: List[Hypothesis] = []

    def initialize_hypotheses(self,
                            train_examples: List[Dict],
                            task_id: str) -> List[Hypothesis]:
        """
        Generate diverse initial hypotheses from multiple sources.

        Sources:
        1. LLM-guided (3 hypotheses)
        2. Evolution (1 hypothesis)
        3. Subroutine composition (1 hypothesis)
        """
        hypotheses = []

        # Source 1: LLM (if available)
        if self.llm_generator:
            llm_patterns = self.llm_generator.generate_hypotheses(
                train_examples, task_id, num_hypotheses=3
            )
            for pattern in llm_patterns:
                hypotheses.append(Hypothesis(
                    pattern=pattern,
                    fitness=self._evaluate(pattern, train_examples),
                    source='llm',
                    refinement_history=[]
                ))

        # Source 2: Evolution
        evolved = self._evolve_pattern(train_examples)
        hypotheses.append(Hypothesis(
            pattern=evolved,
            fitness=self._evaluate(evolved, train_examples),
            source='evolution',
            refinement_history=[]
        ))

        # Source 3: Subroutine composition (if available)
        if self.subroutine_discovery:
            composed = self._compose_subroutines(train_examples)
            hypotheses.append(Hypothesis(
                pattern=composed,
                fitness=self._evaluate(composed, train_examples),
                source='subroutine',
                refinement_history=[]
            ))

        return hypotheses

    def refine_top_k(self,
                    hypotheses: List[Hypothesis],
                    train_examples: List[Dict],
                    num_iterations: int = 3) -> List[Hypothesis]:
        """
        Refine top-k hypotheses in parallel.

        Algorithm:
        1. Sort by fitness + diversity
        2. Keep top-k
        3. Refine each using different strategies
        4. Re-evaluate and repeat
        """
        current = hypotheses

        for iteration in range(num_iterations):
            # Select top-k with diversity bonus
            selected = self._select_diverse_top_k(current)

            # Refine each hypothesis
            refined = []
            for hyp in selected:
                # Try multiple refinement strategies
                variants = self._generate_refinement_variants(hyp, train_examples)

                # Evaluate all variants
                for variant in variants:
                    fitness = self._evaluate(variant.pattern, train_examples)
                    variant.fitness = fitness
                    variant.refinement_history.append(fitness)
                    refined.append(variant)

            current = refined

        # Return final top-k
        return self._select_diverse_top_k(current)

    def _select_diverse_top_k(self, hypotheses: List[Hypothesis]) -> List[Hypothesis]:
        """
        Select top-k hypotheses with diversity bonus.

        Score = fitness + diversity_weight * (1 - similarity_to_others)
        """
        if len(hypotheses) <= self.k:
            return hypotheses

        # Calculate diversity scores
        scored = []
        for i, hyp in enumerate(hypotheses):
            # Diversity = how different from other top hypotheses
            diversity = self._calculate_diversity(hyp, hypotheses)
            score = hyp.fitness + self.diversity_weight * diversity
            scored.append((score, hyp))

        # Sort by score and return top-k
        scored.sort(key=lambda x: x[0], reverse=True)
        return [hyp for score, hyp in scored[:self.k]]

    def _calculate_diversity(self,
                           hyp: Hypothesis,
                           others: List[Hypothesis]) -> float:
        """
        Calculate how different this hypothesis is from others.

        Diversity = average edit distance to other patterns
        """
        if len(others) <= 1:
            return 1.0

        distances = []
        for other in others:
            if other is hyp:
                continue
            # Levenshtein distance / max length
            dist = self._edit_distance(hyp.pattern, other.pattern)
            max_len = max(len(hyp.pattern), len(other.pattern))
            normalized = dist / max_len if max_len > 0 else 0
            distances.append(normalized)

        return np.mean(distances) if distances else 1.0
```

### Integration Points
1. Replace single-pattern evolution with multi-hypothesis approach
2. Use hypothesis diversity to avoid local optima
3. Combine best hypotheses (ensemble voting for test predictions)

### Expected Impact
- **Avoid premature convergence**: Keep exploring diverse solutions
- **Ensemble benefits**: Multiple good solutions better than one
- **Robust to noise**: Different hypotheses capture different aspects

## Phase 10: Full Meta-Meta-Learning (v0.93)

### Goal
System learns not just which refinement strategies work, but HOW TO SYNTHESIZE NEW STRATEGIES from successful refinement patterns.

### Implementation Strategy

```python
@dataclass
class StrategyTemplate:
    """A template for generating new refinement strategies"""
    name: str
    operations: List[str]  # Sequence of meta-operations
    conditions: Dict[str, Any]  # When to apply this strategy
    success_rate: float

class MetaMetaLearner:
    """Phase 10: Learn how to learn - synthesize new refinement strategies"""

    def __init__(self):
        self.strategy_templates: List[StrategyTemplate] = []
        self.refinement_history: List[Dict] = []  # All refinement attempts

    def record_refinement_attempt(self,
                                 context: Dict,
                                 strategy_used: str,
                                 result: Dict):
        """
        Record every refinement attempt for meta-analysis.

        Context: {'fitness_before': 0.5, 'task_type': 'symmetry', ...}
        Result: {'fitness_after': 0.8, 'improved': True, ...}
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
        1. Cluster successful refinement attempts by context
        2. For each cluster, extract common pattern
        3. Create strategy template from pattern
        4. Test strategy on validation set
        5. Keep strategies that outperform baseline
        """
        # Filter successful refinements
        successful = [r for r in self.refinement_history
                     if r['result']['improved']]

        if len(successful) < min_examples:
            return []

        # Cluster by context similarity
        clusters = self._cluster_refinements(successful)

        # Synthesize strategy from each cluster
        new_strategies = []
        for cluster in clusters:
            template = self._extract_strategy_template(cluster)

            # Validate strategy
            if self._validate_strategy(template):
                new_strategies.append(template)
                self.strategy_templates.append(template)

        return new_strategies

    def _cluster_refinements(self, refinements: List[Dict]) -> List[List[Dict]]:
        """
        Cluster refinements by context similarity.

        Context features:
        - Initial fitness level (low/medium/high)
        - Task characteristics (size, complexity)
        - Previous strategies tried
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

        return [c for c in clusters.values() if len(c) >= 3]

    def _extract_strategy_template(self, cluster: List[Dict]) -> StrategyTemplate:
        """
        Extract common pattern from cluster of successful refinements.

        Pattern:
        - What strategies were most commonly used?
        - In what order?
        - Under what conditions?
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
        successful = len([r for r in cluster if r['result']['improved']])
        success_rate = successful / total if total > 0 else 0.0

        # Create template
        template = StrategyTemplate(
            name=f"synthesized_{len(self.strategy_templates)}",
            operations=[s for s, count in top_strategies],
            conditions=conditions,
            success_rate=success_rate
        )

        return template

    def _validate_strategy(self, template: StrategyTemplate) -> bool:
        """
        Validate strategy on held-out refinement attempts.

        Strategy is good if it outperforms random strategy selection.
        """
        # Simple validation: success rate > 0.3
        return template.success_rate > 0.3
```

### Integration Points
1. Record every refinement attempt (context + strategy + result)
2. Periodically (every 50 tasks) run meta-meta-learning
3. Add synthesized strategies to MetaRefiner's strategy pool
4. Use synthesized strategies in future refinements

### Expected Impact
- **Continuous improvement**: System gets better at refinement over time
- **Transfer across task domains**: Learn general refinement principles
- **Emergent strategies**: Discover novel refinement approaches

## Implementation Priority

1. **Phase 8 first**: Provides immediate benefits (subroutine compression)
2. **Phase 9 second**: Improves exploration (avoid local optima)
3. **Phase 10 third**: Long-term learning (requires data from 8 & 9)

## Testing Strategy

For each phase:
1. Unit test on 10 tasks
2. Ablation study (with/without new phase)
3. Full 400-task benchmark
4. Compare to baseline (Phase 5-7 only)

## Expected Performance Trajectory

- **v0.90 (Phases 5-7)**: 5-10% on ARC-AGI (baseline)
- **v0.91 (+ Phase 8)**: 7-12% (subroutine compression)
- **v0.92 (+ Phase 9)**: 10-15% (multi-hypothesis exploration)
- **v0.93 (+ Phase 10)**: 12-20% (meta-meta-learning)
- **Samsung TRM target**: 45% (needs additional innovations)

## Files to Create

1. `prometheus_arc_phase8_subroutines.py` - Hierarchical subroutine discovery
2. `prometheus_arc_phase9_multi_hypothesis.py` - Parallel hypothesis refinement
3. `prometheus_arc_phase10_meta_meta.py` - Strategy synthesis
4. `prometheus_arc_trm_phases_8910.py` - Integrated system (all phases)

## Next Actions

1. Wait for 400-task benchmark (v0.90) to complete
2. Analyze results and identify bottlenecks
3. Implement Phase 8 (highest priority)
4. Test Phase 8 on 50 tasks
5. If successful, proceed to Phase 9
