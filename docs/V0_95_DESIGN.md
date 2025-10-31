# v0.95 Design: Program Synthesis + Advanced Meta-Learning

**Date**: 2025-10-18
**Target**: ARC-AGI solve rate improvement from 1.0% -> 2-3%
**Approach**: Compositional reasoning via parametric program synthesis

---

## Executive Summary

v0.95 represents a fundamental shift from **pattern matching** to **program synthesis**:

**Current (v0.94)**: Match fixed-length primitive sequences
- Example: `['rotate_90', 'crop', 'transpose']`
- Limitation: No parameters, no composition, no variables

**Proposed (v0.95)**: Synthesize parametric programs with composition
- Example: `rotate(90) -> filter_color(2) -> replicate(3, horizontal)`
- Benefits: Parameters, composition, control flow, learned subroutines

**Expected Impact**: 2-3x accuracy improvement (1.0% -> 2-3%)

---

## Core Innovations

### 1. Parametric Operations

**Problem**: Current primitives are parameter-free
```python
# v0.94 (limited)
rotate_90(grid)      # Always 90 degrees
scale_2x(grid)       # Always 2x
isolate_5(grid)      # Always color 5
```

**Solution**: Add parameters to operations
```python
# v0.95 (flexible)
rotate(grid, angle=90)            # Any angle: 90, 180, 270
scale(grid, factor=2)             # Any factor: 2, 3, 4, 5
filter_color(grid, color=5)       # Any color: 0-9
replicate(grid, times=3, dir='h') # Any count, any direction
```

**Benefits**:
- Reduces primitive count (38 -> ~15 base operations)
- Increases expressiveness (15 operations with params > 38 fixed)
- Enables learning parameter values from constraints

---

### 2. Program Representation

**Data Structure**:
```python
class ARCProgram:
    """
    A program is a sequence of parametric operations.
    """
    def __init__(self, operations: List[Tuple[str, Dict]]):
        self.operations = operations

    def execute(self, grid: np.ndarray) -> np.ndarray:
        """Execute program on grid"""
        result = grid.copy()
        for op_name, params in self.operations:
            op_func = OPERATION_MAP[op_name]
            result = op_func(result, **params)
        return result

    def to_pattern(self) -> List[str]:
        """Convert to v0.94 pattern format (for compatibility)"""
        return [f"{op}({','.join(f'{k}={v}' for k, v in params.items())})"
                for op, params in self.operations]
```

**Examples**:
```python
# Example 1: Rotation + filtering
program = ARCProgram([
    ('rotate', {'angle': 90}),
    ('filter_color', {'color': 2}),
    ('border', {'thickness': 1})
])

# Example 2: Scaling + replication
program = ARCProgram([
    ('scale', {'factor': 2}),
    ('replicate', {'times': 3, 'direction': 'horizontal'})
])

# Example 3: Object manipulation
program = ARCProgram([
    ('detect_objects', {}),
    ('sort_objects', {'key': 'size'}),
    ('extract_nth', {'n': 0}),  # Get largest
    ('place_at', {'x': 0, 'y': 0})
])
```

---

### 3. Beam Search Synthesis

**Problem**: Evolution explores random space inefficiently

**Solution**: Beam search with constraint-guided expansion

```python
class ProgramSynthesizer:
    def __init__(self, beam_width: int = 100):
        self.beam_width = beam_width
        self.operations = self._build_operation_catalog()

    def synthesize(self, task: Dict, constraints: Dict,
                   meta_learner: ConstraintMetaLearner,
                   max_depth: int = 5) -> ARCProgram:
        """
        Synthesize program using beam search.

        Algorithm:
        1. Start with empty program
        2. Get candidate operations from meta-learner (biased by constraints)
        3. For each program in beam:
           - Try adding each candidate operation with params
           - Evaluate on training examples
           - Keep top-k by fitness
        4. Repeat until solved or max_depth
        5. Return best program
        """
        # Initialize beam with empty program
        beam = [(0.0, ARCProgram([]))]

        for depth in range(max_depth):
            candidates = []

            # Get biased operations from meta-learner
            biased_ops = meta_learner.get_refined_filter(
                constraints, mode='adaptive', top_k=15
            )

            for fitness, program in beam:
                # Try adding each operation
                for op_name in biased_ops:
                    # Get parameter candidates
                    param_sets = self._get_param_candidates(
                        op_name, task, constraints
                    )

                    for params in param_sets:
                        # Create new program
                        new_prog = program.copy()
                        new_prog.add_operation(op_name, params)

                        # Evaluate on training examples
                        new_fitness = self._evaluate(new_prog, task)

                        candidates.append((new_fitness, new_prog))

                        # Early exit if solved
                        if new_fitness >= 0.95:
                            return new_prog

            # Keep top-k
            candidates.sort(reverse=True, key=lambda x: x[0])
            beam = candidates[:self.beam_width]

            # Check for progress
            if beam[0][0] <= 0.1:
                break  # No progress, abort

        return beam[0][1]  # Return best program

    def _get_param_candidates(self, op_name: str,
                              task: Dict, constraints: Dict) -> List[Dict]:
        """
        Generate parameter candidates for operation based on task/constraints.

        Strategy:
        1. Extract relevant values from task (colors, sizes, counts)
        2. Use constraints to filter (e.g., if colors preserved, don't try all color maps)
        3. Return top-k most likely parameter sets
        """
        candidates = []

        if op_name == 'rotate':
            # Try all valid angles
            for angle in [90, 180, 270]:
                candidates.append({'angle': angle})

        elif op_name == 'scale':
            # Try factors based on size constraint
            if constraints.get('size') == 'scaled_up':
                for factor in [2, 3, 4]:
                    candidates.append({'factor': factor})
            elif constraints.get('size') == 'scaled_down':
                for factor in [2, 3, 4]:
                    candidates.append({'factor': 1/factor})

        elif op_name == 'filter_color':
            # Try all colors present in task
            colors = self._extract_colors_from_task(task)
            for color in colors:
                candidates.append({'color': color})

        elif op_name == 'replicate':
            # Try counts and directions
            for times in [2, 3, 4]:
                for direction in ['horizontal', 'vertical']:
                    candidates.append({'times': times, 'direction': direction})

        else:
            # Default: no parameters
            candidates.append({})

        return candidates[:5]  # Limit to top 5 to avoid explosion
```

---

### 4. Parametric Operation Catalog

**Base Operations** (~15):

```python
PARAMETRIC_OPERATIONS = {
    # Geometric transformations
    'rotate': {
        'params': {'angle': [90, 180, 270]},
        'func': lambda grid, angle: np.rot90(grid, k=angle//90)
    },
    'flip': {
        'params': {'axis': ['horizontal', 'vertical']},
        'func': lambda grid, axis: np.flip(grid, axis=0 if axis=='vertical' else 1)
    },
    'scale': {
        'params': {'factor': [2, 3, 4, 5]},
        'func': lambda grid, factor: scale_grid(grid, factor)
    },

    # Color operations
    'filter_color': {
        'params': {'color': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]},
        'func': lambda grid, color: (grid == color).astype(int) * color
    },
    'map_color': {
        'params': {'from_color': [0-9], 'to_color': [0-9]},
        'func': lambda grid, from_color, to_color: np.where(grid == from_color, to_color, grid)
    },

    # Spatial operations
    'crop': {
        'params': {'mode': ['content', 'border', 'center']},
        'func': lambda grid, mode: crop_grid(grid, mode)
    },
    'pad': {
        'params': {'size': [1, 2, 4], 'value': [0-9]},
        'func': lambda grid, size, value: np.pad(grid, size, constant_values=value)
    },

    # Object operations
    'detect_objects': {
        'params': {},
        'func': lambda grid: detect_connected_components(grid)
    },
    'extract_nth': {
        'params': {'n': [0, 1, 2], 'key': ['size', 'position']},
        'func': lambda objects, n, key: extract_nth_object(objects, n, key)
    },
    'replicate': {
        'params': {'times': [2, 3, 4], 'direction': ['h', 'v']},
        'func': lambda grid, times, direction: replicate_pattern(grid, times, direction)
    },

    # Symmetry operations
    'symmetrize': {
        'params': {'axis': ['h', 'v', 'both']},
        'func': lambda grid, axis: make_symmetric(grid, axis)
    },

    # Structure operations
    'border': {
        'params': {'thickness': [1, 2], 'color': [0-9]},
        'func': lambda grid, thickness, color: add_border(grid, thickness, color)
    },
    'fill_interior': {
        'params': {},
        'func': lambda grid: fill_holes(grid)
    },

    # Control flow (advanced)
    'conditional': {
        'params': {'condition': ['has_symmetry', 'num_colors>3'], 'then': [prog1], 'else': [prog2]},
        'func': lambda grid, condition, then_prog, else_prog: execute_conditional(...)
    }
}
```

**Key Insight**: 15 parametric operations can express more patterns than 38 fixed primitives!

---

### 5. Advanced Meta-Learning

**Enhancement 1: Learn Parameter Distributions**

Instead of just tracking primitives, track operation + parameter pairs:

```python
class ParametricMetaLearner(ConstraintMetaLearner):
    def __init__(self):
        super().__init__()
        # {constraint_hash: {(op, param_tuple): {successes, total, best_fitness}}}
        self.param_success_db = {}

    def record_attempt(self, constraints: Dict, program: ARCProgram,
                      fitness: float, task_id: str):
        """Record program attempt with parameters"""
        constraint_hash = self._hash_constraints(constraints)

        if constraint_hash not in self.param_success_db:
            self.param_success_db[constraint_hash] = {}

        for op_name, params in program.operations:
            # Create hashable param tuple
            param_tuple = tuple(sorted(params.items()))
            key = (op_name, param_tuple)

            if key not in self.param_success_db[constraint_hash]:
                self.param_success_db[constraint_hash][key] = {
                    'successes': 0, 'total': 0, 'best_fitness': 0.0
                }

            self.param_success_db[constraint_hash][key]['total'] += 1
            if fitness >= 0.95:
                self.param_success_db[constraint_hash][key]['successes'] += 1
            if fitness > self.param_success_db[constraint_hash][key]['best_fitness']:
                self.param_success_db[constraint_hash][key]['best_fitness'] = fitness

    def get_best_params(self, op_name: str, constraints: Dict,
                       top_k: int = 3) -> List[Dict]:
        """Get best-performing parameter sets for operation given constraints"""
        constraint_hash = self._hash_constraints(constraints)

        if constraint_hash not in self.param_success_db:
            return []

        # Get all (op, params) pairs for this operation
        relevant = [(params, stats) for (op, params), stats
                   in self.param_success_db[constraint_hash].items()
                   if op == op_name]

        # Sort by success rate
        relevant.sort(key=lambda x: x[1]['successes'] / max(x[1]['total'], 1),
                     reverse=True)

        # Return top-k parameter dicts
        return [dict(params) for params, stats in relevant[:top_k]]
```

**Enhancement 2: Program Templates**

Learn successful program structures:

```python
class ProgramTemplate:
    """
    A template is a program with slots for parameters.

    Example:
        rotate(?) -> filter_color(?) -> border(?)
    """
    def __init__(self, structure: List[Tuple[str, List[str]]]):
        """
        structure: List of (operation_name, parameter_names)

        Example:
            [('rotate', ['angle']),
             ('filter_color', ['color']),
             ('border', ['thickness', 'color'])]
        """
        self.structure = structure

    def instantiate(self, param_values: Dict) -> ARCProgram:
        """Fill in parameters to create concrete program"""
        operations = []
        for op_name, param_names in self.structure:
            params = {name: param_values[f"{op_name}.{name}"]
                     for name in param_names}
            operations.append((op_name, params))
        return ARCProgram(operations)

class TemplateLearner:
    def __init__(self):
        self.templates = []  # List of (template, success_count, tasks)

    def extract_template(self, program: ARCProgram) -> ProgramTemplate:
        """Extract template structure from concrete program"""
        structure = [(op, list(params.keys()))
                    for op, params in program.operations]
        return ProgramTemplate(structure)

    def record_success(self, program: ARCProgram, task_id: str):
        """Record successful program and extract template"""
        template = self.extract_template(program)

        # Find matching template or add new one
        for i, (t, count, tasks) in enumerate(self.templates):
            if t.structure == template.structure:
                self.templates[i] = (t, count + 1, tasks + [task_id])
                return

        # New template
        self.templates.append((template, 1, [task_id]))

    def get_top_templates(self, k: int = 10) -> List[ProgramTemplate]:
        """Get most successful templates"""
        sorted_templates = sorted(self.templates,
                                 key=lambda x: x[1], reverse=True)
        return [t for t, count, tasks in sorted_templates[:k]]
```

**Enhancement 3: Transfer Learning via Templates**

```python
def solve_via_template_transfer(task: Dict, constraints: Dict,
                               template_learner: TemplateLearner,
                               param_learner: ParametricMetaLearner) -> ARCProgram:
    """
    Solve task by:
    1. Getting top templates from similar tasks
    2. Filling parameters using learned distributions
    3. Evaluating on training examples
    """
    top_templates = template_learner.get_top_templates(k=10)

    best_fitness = 0
    best_program = None

    for template in top_templates:
        # Get parameter candidates for each slot
        param_candidates = {}
        for op_name, param_names in template.structure:
            best_params = param_learner.get_best_params(op_name, constraints, top_k=3)
            param_candidates[op_name] = best_params

        # Try all combinations (limited by top-k)
        for param_combo in itertools.product(*param_candidates.values()):
            # Create concrete program
            param_values = {}
            for (op_name, param_names), params in zip(template.structure, param_combo):
                for name, value in params.items():
                    param_values[f"{op_name}.{name}"] = value

            program = template.instantiate(param_values)

            # Evaluate
            fitness = evaluate_program(program, task)

            if fitness > best_fitness:
                best_fitness = fitness
                best_program = program

            if fitness >= 0.95:
                return program  # Solved!

    return best_program
```

---

## Architecture

### System Components

```
v0.95 Architecture

┌─────────────────────────────────────────────────────────────┐
│                    PrometheusARC_v095                       │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          ProgramSynthesizer                          │  │
│  │  - Beam search (width=100)                          │  │
│  │  - Constraint-guided operation selection            │  │
│  │  - Parameter candidate generation                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                │
│                            v                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │       ParametricMetaLearner (Enhanced)               │  │
│  │  - Track (operation, params) -> success             │  │
│  │  - Learn parameter distributions                    │  │
│  │  - Adaptive filtering with params                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                │
│                            v                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            TemplateLearner                           │  │
│  │  - Extract program structure templates              │  │
│  │  - Track template success rates                     │  │
│  │  - Template-based transfer learning                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                │
│                            v                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        ParametricOperations (15 base ops)            │  │
│  │  - rotate(angle), scale(factor), filter_color(c)    │  │
│  │  - replicate(n, dir), map_color(from, to)           │  │
│  │  - detect_objects(), sort_objects(key)              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Fallback to v0.94 if:
- Beam search fails (no progress)
- Template transfer fails
- Time budget exceeded
```

### Solve Flow

```
Task Input
    |
    v
[v0.93] Extract Constraints
    |
    v
[v0.95] Try Template Transfer
    |   - Get top 10 templates from similar tasks
    |   - Fill params using learned distributions
    |   - Evaluate on training examples
    |
    +---> SUCCESS? Return program
    |
    v
[v0.95] Beam Search Synthesis
    |   - Start with empty program
    |   - Get biased operations from meta-learner
    |   - For each program in beam:
    |       * Try adding operation + params
    |       * Evaluate on training
    |       * Keep top-k
    |   - Repeat up to depth 5
    |
    +---> SUCCESS? Record + return
    |
    v
[v0.94] Fallback to Pattern Evolution
    |   - Use v0.94 meta-learning filter
    |   - Run 100 gen evolution
    |
    v
Result + Learning
    |
    v
[v0.95] Update Databases
    - Record (op, params) -> success
    - Extract and store template
    - Update parameter distributions
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

**Files to Create**:
1. `arc_parametric_operations.py` (~300 lines)
   - Define 15 base parametric operations
   - Parameter validation
   - Operation execution engine

2. `arc_program.py` (~200 lines)
   - ARCProgram class
   - Program execution
   - Serialization/deserialization

3. `arc_program_synthesizer.py` (~400 lines)
   - ProgramSynthesizer class
   - Beam search implementation
   - Parameter candidate generation

**Validation**: Unit tests for each component

---

### Phase 2: Enhanced Meta-Learning (Week 1-2)

**Files to Create**:
1. `arc_parametric_meta_learner.py` (~500 lines)
   - ParametricMetaLearner class
   - Parameter distribution tracking
   - Enhanced get_refined_filter()

2. `arc_template_learner.py` (~400 lines)
   - ProgramTemplate class
   - TemplateLearner class
   - Template extraction and matching

**Validation**: Test on solved tasks from v0.69

---

### Phase 3: Integration (Week 2)

**Files to Create**:
1. `prometheus_arc_v095_synthesis.py` (~500 lines)
   - PrometheusARC_v095 class
   - Integrate all components
   - Fallback to v0.94
   - CLI interface

**Validation**: 3-task test, 10-task benchmark

---

### Phase 4: Evaluation (Week 2)

**Tasks**:
1. Run 10-task benchmark
2. Run 50-task evaluation
3. Compare to v0.94 baseline
4. Analyze failure cases
5. Document results

**Success Criteria**:
- Solve rate > 2% (2x improvement over v0.94)
- Template transfer works on >20% of tasks
- Parameter learning improves beam search efficiency

---

## Expected Performance

### Baseline (v0.94)
- Solve rate: 1.0% (4/400)
- Method: Constraint-filtered evolution
- Search space: 79M -> 10K patterns

### Target (v0.95)
- Solve rate: 2-3% (8-12/400)
- Method: Program synthesis + templates
- Search space: Parametric program space (~10^6 programs)

### Breakdown
- Template transfer: +0.5% (2 additional solves)
- Beam search: +1.0% (4 additional solves)
- Parameter learning: +0.5% (2 additional solves)
- **Total improvement**: +2.0% (8 additional solves)

---

## Risk Analysis

### High Risk
- **Beam search explosion**: Too many param combinations
  - Mitigation: Limit to top-5 params per operation

- **Template overfitting**: Templates too specific
  - Mitigation: Generalize via parameter slots

### Medium Risk
- **Evaluation speed**: Beam search slower than evolution
  - Mitigation: Early stopping, time budgets

- **Implementation complexity**: More moving parts
  - Mitigation: Incremental development, unit tests

### Low Risk
- **Compatibility**: v0.94 fallback ensures no regression
- **Database size**: Parametric DB still <10MB

---

## Success Metrics

### Minimum Viable Success
- ✅ Core infrastructure implemented
- ✅ Beam search working
- ✅ Parameter learning active
- ✅ No performance regression vs v0.94

### Target Success
- 🎯 Solve rate: 2-3% (2-3x improvement)
- 🎯 Template transfer: >20% of tasks
- 🎯 Parameter learning: Reduces beam search by 50%

### Stretch Success
- 🚀 Solve rate: >3% (3x improvement)
- 🚀 Template transfer: >30% of tasks
- 🚀 New primitives learned automatically

---

## Timeline

**Week 1**: Core infrastructure + parametric operations
**Week 2**: Enhanced meta-learning + integration
**Week 3**: Evaluation + refinement
**Week 4**: Documentation + v0.96 planning

**Total**: 4 weeks to v0.95 complete

---

## Conclusion

v0.95 represents a paradigm shift from pattern matching to program synthesis.

**Key Innovations**:
1. Parametric operations (15 ops with params > 38 fixed ops)
2. Beam search synthesis (compositional reasoning)
3. Program templates (transfer learning)
4. Parameter distribution learning (smarter search)

**Expected Impact**: 2-3x accuracy improvement (1.0% -> 2-3%)

**Path to 5%**:
- v0.95: 2-3% (program synthesis)
- v0.96: 3-4% (ensemble + advanced transfer)
- v0.97: 4-5% (learned primitives + neural guidance)

**Status**: Ready to begin implementation

---

*Generated: 2025-10-18*
*Prometheus v0.95 Design - Program Synthesis*
*Design by Claude Code (claude.com/code)*
