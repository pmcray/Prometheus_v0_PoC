# Next Tasks for v0.92-v0.95: Post-Phases 8-10 Analysis

## Current Status (v0.91)
- ✅ Phases 8-10 Implemented (Subroutines, Multi-Hypothesis, Meta-Meta)
- ✅ 50-task benchmark complete: **0/50 solved (0.00%)**
- ✅ Analysis complete: Root cause identified
- ❌ Performance regression: Expected 7-12%, actual 0%

## Root Cause Summary

**Primary Issue**: Phases 8-10 are refinement-focused, but the **baseline search (Phases 1-7) is too weak**.

**Evidence**:
- High-fitness tasks (90-98%) can't cross 100% threshold
- Identity primitive dominance (`['identity', 'identity']`)
- Refinement plateaus after 1-2 cycles
- No subroutines discovered (only 1 from 50 tasks)

**Conclusion**: Need to improve **discovery** (Phases 1-7) before further **refinement** (Phases 8-10).

## v0.92: Baseline Improvement (Priority 1)

### Goal
Improve Phases 1-7 baseline search to 5-10% solve rate before re-enabling Phases 8-10.

### Strategy 1: Remove Identity Primitive Dominance

**Problem**: `['identity']` appears in 24/50 final patterns because it provides marginal fitness boost without solving.

**Fix**:
```python
# In prometheus_arc_primitives.py
# Remove 'identity' from correction primitives, keep only for baseline

CORRECTION_PRIMITIVES = [
    'fill_zeros', 'remove_bg',  # Cleanup
    'sym_h', 'sym_v',           # Symmetry
    'border', 'extend_edges',    # Extension
    'hollow',                   # Structure
    # 'identity' REMOVED from corrections
]

BASELINE_PRIMITIVES = [
    'identity',  # Keep for baseline evolution
    'rotate_90', 'rotate_180', 'rotate_270',
    'flip_h', 'flip_v',
    # ... rest of primitives
]
```

**Expected Impact**: Force refinement to find actual transformations, not identity shortcuts.

### Strategy 2: Hybrid Fitness Function

**Problem**: Current fitness is binary (100% = solved, <100% = failed). Tasks at 95-98% get no credit.

**Fix**:
```python
def hybrid_fitness(predicted, expected):
    """
    Combine exact match with fuzzy similarity.

    fitness = 0.5 * exact_match + 0.5 * pixel_similarity

    This gives partial credit for "close" solutions.
    """
    exact = 1.0 if perfect_match(predicted, expected) else 0.0
    fuzzy = pixel_similarity(predicted, expected)  # 0.0-1.0

    return 0.5 * exact + 0.5 * fuzzy
```

**Expected Impact**: Tasks at 95% similarity get 0.475 fitness instead of 0.0, allowing evolution to continue.

### Strategy 3: Increase Evolution Budget

**Problem**: Current baseline uses 100 generations, which may be insufficient for complex tasks.

**Fix**:
```python
# Adaptive generation budget based on task complexity
def get_generation_budget(task):
    grid_size = max(task['train'][0]['input'].shape)
    num_colors = len(set(task['train'][0]['input'].flatten()))
    num_examples = len(task['train'])

    complexity = grid_size * num_colors / num_examples

    if complexity < 10:
        return 100  # Simple tasks
    elif complexity < 50:
        return 200  # Medium tasks
    else:
        return 500  # Complex tasks
```

**Expected Impact**: Complex tasks get more time to evolve, simple tasks finish faster.

### Strategy 4: Smarter Primitives

**Problem**: Current 38 primitives are mostly grid-level operations, not object-aware.

**Fix**: Add object-aware primitives from latest ARC research:
```python
# Object-aware primitives (from successful ARC solvers)
OBJECT_PRIMITIVES = [
    'detect_objects',          # Connected components
    'extract_largest_object',  # Get biggest blob
    'sort_objects_by_size',    # Order by area
    'align_objects_horizontal', # Arrange in row
    'align_objects_vertical',   # Arrange in column
    'replicate_pattern',        # Copy smallest object
    'fill_object_interior',     # Solid fill
    'object_gravity_down',      # Drop to bottom
]
```

**Expected Impact**: Object-level reasoning for tasks involving shapes/blobs.

## v0.93: Constraint-Based Search (Priority 2)

### Goal
Use task constraints to prune the search space and guide evolution.

### Implementation

```python
class ConstraintExtractor:
    """Extract constraints from training examples"""

    def extract_constraints(self, task):
        """
        Analyze training examples to find invariants.

        Returns:
            {
                'size_constraint': 'preserve' | 'scale' | 'crop',
                'color_constraint': 'preserve' | 'map' | 'reduce',
                'symmetry': bool,
                'num_objects': int | 'variable',
                'transformations': ['rotate', 'flip', ...]
            }
        """
        constraints = {}

        # Size constraint
        input_sizes = [ex['input'].shape for ex in task['train']]
        output_sizes = [ex['output'].shape for ex in task['train']]

        if all(i == o for i, o in zip(input_sizes, output_sizes)):
            constraints['size_constraint'] = 'preserve'
        elif all(o[0] > i[0] for i, o in zip(input_sizes, output_sizes)):
            constraints['size_constraint'] = 'scale_up'
        else:
            constraints['size_constraint'] = 'variable'

        # Color constraint
        input_colors = [set(ex['input'].flatten()) for ex in task['train']]
        output_colors = [set(ex['output'].flatten()) for ex in task['train']]

        if all(i == o for i, o in zip(input_colors, output_colors)):
            constraints['color_constraint'] = 'preserve'
        else:
            constraints['color_constraint'] = 'map'

        return constraints

    def filter_primitives_by_constraints(self, primitives, constraints):
        """
        Filter primitives that violate constraints.

        Example:
        - If size must be preserved, remove 'scale_2x', 'crop', 'downsample'
        - If colors must be preserved, remove 'swap_colors', 'map_X_to_Y'
        """
        filtered = []

        for prim in primitives:
            # Check size constraint
            if constraints['size_constraint'] == 'preserve':
                if prim in ['scale_2x', 'scale_3x', 'crop', 'downsample']:
                    continue  # Skip size-changing primitives

            # Check color constraint
            if constraints['color_constraint'] == 'preserve':
                if prim.startswith('map_') or prim.startswith('swap_'):
                    continue  # Skip color-changing primitives

            filtered.append(prim)

        return filtered
```

**Expected Impact**: Reduce search space from 38^5 = 79 million patterns to ~10^5 = 100k patterns.

## v0.94: Program Synthesis (Priority 3)

### Goal
Move beyond pattern evolution to **program synthesis** using domain-specific language (DSL).

### Architecture

```python
class ARCProgram:
    """
    A program is a sequence of operations with parameters.

    Example:
        program = [
            ('rotate', {'angle': 90}),
            ('filter_color', {'color': 2}),
            ('replicate', {'times': 3})
        ]
    """

    def __init__(self, operations):
        self.operations = operations

    def execute(self, grid):
        result = grid.copy()
        for op_name, params in self.operations:
            op = OPERATION_MAP[op_name]
            result = op(result, **params)
        return result

class ProgramSynthesizer:
    """Synthesize programs using constraint-guided search"""

    def synthesize(self, task, constraints, max_depth=5):
        """
        Generate programs that satisfy constraints.

        Algorithm:
        1. Start with empty program
        2. Add operations that satisfy constraints
        3. Evaluate on training examples
        4. Keep top-k programs
        5. Expand top-k by adding next operation
        6. Repeat until max_depth or solution found
        """
        beam = [ARCProgram([])]  # Start with empty program

        for depth in range(max_depth):
            candidates = []

            for program in beam:
                # Try adding each valid operation
                for op in self.get_valid_operations(program, constraints):
                    new_program = program.copy()
                    new_program.add_operation(op)

                    # Evaluate on training examples
                    fitness = self.evaluate(new_program, task)
                    candidates.append((fitness, new_program))

            # Keep top-k
            candidates.sort(reverse=True)
            beam = [prog for fitness, prog in candidates[:100]]

            # Check if any solved
            for fitness, program in candidates:
                if fitness == 1.0:
                    return program

        return beam[0]  # Return best program
```

**Expected Impact**: Move from "pattern matching" to "program search", unlocking compositional reasoning.

## v0.95: Meta-Learning Across Tasks (Priority 4)

### Goal
Learn from solved tasks to solve similar tasks (transfer learning).

### Implementation

```python
class TaskEmbedding:
    """Embed tasks in semantic space for similarity search"""

    def embed_task(self, task):
        """
        Create vector representation of task.

        Features:
        - Grid size distribution
        - Color palette
        - Symmetry properties
        - Number of objects
        - Spatial relationships
        """
        features = []

        # Size features
        sizes = [ex['input'].shape for ex in task['train']]
        features.extend([np.mean(sizes), np.std(sizes)])

        # Color features
        colors = [len(set(ex['input'].flatten())) for ex in task['train']]
        features.extend([np.mean(colors), np.std(colors)])

        # Symmetry features
        symmetries = [self.check_symmetry(ex['output']) for ex in task['train']]
        features.append(np.mean(symmetries))

        return np.array(features)

    def find_similar_tasks(self, task, solved_tasks, k=5):
        """Find k most similar solved tasks"""
        task_emb = self.embed_task(task)

        similarities = []
        for solved_task, solution in solved_tasks.items():
            solved_emb = self.embed_task(solved_task)
            similarity = cosine_similarity(task_emb, solved_emb)
            similarities.append((similarity, solved_task, solution))

        similarities.sort(reverse=True)
        return similarities[:k]

class TransferLearner:
    """Transfer solutions from solved tasks to new tasks"""

    def solve_by_transfer(self, task, solved_tasks):
        """
        Try to solve task by adapting solutions from similar tasks.

        Algorithm:
        1. Find k most similar solved tasks
        2. Extract their solution patterns
        3. Try applying each pattern to new task
        4. Adapt parameters if needed
        5. Return best match
        """
        similar = self.task_embedding.find_similar_tasks(task, solved_tasks, k=5)

        best_fitness = 0
        best_pattern = None

        for similarity, solved_task, solution_pattern in similar:
            # Try applying solution pattern directly
            fitness = self.evaluate(solution_pattern, task)

            if fitness > best_fitness:
                best_fitness = fitness
                best_pattern = solution_pattern

            # Try adapting parameters
            adapted = self.adapt_pattern(solution_pattern, task, solved_task)
            fitness_adapted = self.evaluate(adapted, task)

            if fitness_adapted > best_fitness:
                best_fitness = fitness_adapted
                best_pattern = adapted

        return best_pattern, best_fitness
```

**Expected Impact**: Solve 10-20% of tasks via transfer from similar solved tasks.

## Implementation Priority

1. **v0.92 (Baseline Improvement)**: 1-2 weeks
   - Remove identity dominance
   - Add hybrid fitness
   - Increase evolution budget
   - Add object-aware primitives
   - **Target**: 5-10% solve rate

2. **v0.93 (Constraint-Based)**: 1-2 weeks
   - Constraint extraction
   - Primitive filtering
   - Beam search
   - **Target**: 10-15% solve rate

3. **v0.94 (Program Synthesis)**: 2-3 weeks
   - DSL design
   - Program synthesizer
   - Parametric operations
   - **Target**: 15-25% solve rate

4. **v0.95 (Meta-Learning)**: 2-3 weeks
   - Task embedding
   - Similarity search
   - Transfer learning
   - **Target**: 25-35% solve rate

## Success Metrics

- **v0.92**: 5-10% solve rate (baseline working)
- **v0.93**: 10-15% solve rate (constraints help)
- **v0.94**: 15-25% solve rate (program synthesis works)
- **v0.95**: 25-35% solve rate (transfer learning helps)
- **v1.00**: 40-50% solve rate (comparable to Samsung TRM)

## Re-Enable Phases 8-10

Once baseline reaches 10%+ solve rate:
- Phase 8 (Subroutines): Will have enough patterns to discover meaningful subroutines
- Phase 9 (Multi-Hypothesis): Will have better hypotheses to refine
- Phase 10 (Meta-Meta): Will have successful refinements to learn from

**Expected improvement**: 10% → 15-20% (50% relative improvement)

## Files to Create

1. `prometheus_arc_v092_baseline.py` - Improved baseline (v0.92)
2. `prometheus_arc_constraints.py` - Constraint extraction (v0.93)
3. `prometheus_arc_program_synthesis.py` - DSL and synthesis (v0.94)
4. `prometheus_arc_transfer.py` - Transfer learning (v0.95)

## Timeline

- **Week 1-2**: v0.92 (Baseline Improvement)
- **Week 3-4**: v0.93 (Constraint-Based)
- **Week 5-7**: v0.94 (Program Synthesis)
- **Week 8-10**: v0.95 (Meta-Learning)
- **Week 11-12**: Integration + Benchmarking

**Total**: 12 weeks to v1.00 (40-50% solve rate)

## Comparison to Research Timeline

- **Our approach**: 12 weeks to 40-50%
- **Samsung TRM**: Unknown (likely months/years of research)
- **Kaggle winners**: 6-12 months to 20-30%
- **GPT-4**: ~5% (OpenAI, large compute budget)

**Realistic target**: 25-35% solve rate by end of 12-week period.
