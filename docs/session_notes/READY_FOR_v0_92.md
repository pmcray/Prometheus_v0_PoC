# Ready for v0.92 Implementation - Action Plan

**Date**: 2025-10-17
**Current Version**: v0.91 (Complete)
**Next Version**: v0.92 (Baseline Improvements)
**Status**: Analysis complete, ready for implementation

---

## Executive Summary

v0.91 (Phases 8-10) achieved **0% solve rate** due to weak baseline search. The implementation is technically sound but empirically unsuccessful.

**Root Cause**: Refinement phases can't fix bad starting points.

**Solution**: Improve Phases 1-7 baseline search **before** re-enabling Phases 8-10.

---

## What Has Been Completed

### ✅ Phase 1: Implementation
- Implemented Phases 8, 9, and 10 of TRM architecture
- All components working correctly
- No crashes or errors

### ✅ Phase 2: Benchmarking
- Tested on 50 tasks (0/50 solved)
- Tested on 11 high-fitness tasks (0/11 solved, but fitness improved)
- Generated detailed logs and JSON results

###  ✅ Phase 3: Analysis
Created 3 comprehensive documents:

1. **PHASES_8910_ANALYSIS_v0_91.md**
   - 5 root causes identified
   - Evidence-based diagnosis
   - Specific recommendations

2. **NEXT_TASKS_v0_92.md**
   - 4-version roadmap (v0.92-v0.95)
   - Implementation strategies with code examples
   - 12-week timeline to v1.00

3. **STATUS_v0_91_COMPLETE.md**
   - Executive summary
   - Lessons learned
   - Comparison to state-of-the-art

---

## What Needs to Be Done (v0.92)

### Priority 1: Remove Identity Dominance

**Problem**: `['identity']` appears in 24/50 final patterns

**Solution**: Create two separate primitive lists

```python
# For baseline evolution (Phases 1-4)
BASELINE_PRIMITIVES = [
    'identity',  # Keep for baseline
    'rotate_90', 'rotate_180', 'rotate_270',
    'flip_h', 'flip_v',
    ... # all 38 primitives
]

# For refinement/correction (Phases 5-7)
CORRECTION_PRIMITIVES = [
    # 'identity' REMOVED
    'fill_zeros', 'remove_bg',
    'sym_h', 'sym_v',
    'border', 'extend_edges',
    ... # 37 primitives (no identity)
]
```

**Files to modify**:
- `prometheus_arc_trm_phases_8910.py` (or create new v0.92 file)
- Search for where primitives are defined/used
- Split into BASELINE vs CORRECTION lists

### Priority 2: Implement Hybrid Fitness

**Problem**: Binary fitness (100% or fail) doesn't reward "close" solutions

**Solution**: Combine exact match with pixel similarity

```python
def hybrid_fitness(predicted, expected):
    """
    Hybrid fitness: exact + fuzzy similarity.

    This gives partial credit for "close" solutions:
    - Perfect match: 1.0 (0.5 + 0.5)
    - 95% similar: 0.475 (0.0 + 0.475)
    - 50% similar: 0.25 (0.0 + 0.25)
    """
    # Exact match component
    exact = 1.0 if np.array_equal(predicted, expected) else 0.0

    # Fuzzy similarity component
    if predicted.shape != expected.shape:
        # Size mismatch penalty
        fuzzy = pixel_similarity_resized(predicted, expected) * 0.5
    else:
        # Same size: pixel-wise similarity
        matches = np.sum(predicted == expected)
        total = predicted.size
        fuzzy = matches / total if total > 0 else 0.0

    # Combined fitness
    return 0.5 * exact + 0.5 * fuzzy

def pixel_similarity_resized(pred, exp):
    """Handle size mismatch by resizing to larger"""
    if pred.shape == exp.shape:
        matches = np.sum(pred == exp)
        return matches / pred.size

    # Resize to match
    # (Implementation: use np.resize or scipy.ndimage.zoom)
    # Return similarity after resizing
    pass
```

**Files to modify**:
- Add `hybrid_fitness()` function
- Replace all `fitness == 1.0` checks with `fitness > 0.95`
- Update success threshold from 0.999 to 0.95

### Priority 3: Add Object-Aware Primitives

**Problem**: Current primitives are grid-level, not object-aware

**Solution**: Add 8-10 object primitives using scipy.ndimage

```python
from scipy.ndimage import label

# Object-aware primitives (add to baseline)
OBJECT_PRIMITIVES = [
    'detect_objects',          # Connected components
    'extract_largest',          # Get biggest blob
    'extract_smallest',         # Get smallest blob
    'sort_objects_by_size',     # Order by area
    'align_objects_h',          # Arrange horizontally
    'align_objects_v',          # Arrange vertically
    'fill_object_interior',     # Solid fill objects
    'object_gravity_down',      # Drop objects to bottom
]

def detect_objects(grid):
    """Find connected components (objects)"""
    labeled, num_objects = label(grid)
    return labeled

def extract_largest(grid):
    """Extract only the largest object"""
    labeled, num = label(grid)
    if num == 0:
        return grid

    # Count pixels in each object
    sizes = [(labeled == i).sum() for i in range(1, num + 1)]
    largest_idx = np.argmax(sizes) + 1

    result = np.where(labeled == largest_idx, grid, 0)
    return result

# ... implement other object primitives
```

**Files to modify**:
- Add object primitives to primitive list
- Implement each primitive function
- Add to primitive map

### Priority 4: Adaptive Generation Budget

**Problem**: Complex tasks need more evolution time

**Solution**: Scale generations based on task complexity

```python
def get_generation_budget(task):
    """
    Adaptive generation budget based on task complexity.

    Complexity factors:
    - Grid size (larger = more complex)
    - Number of colors (more colors = more complex)
    - Number of examples (fewer = harder to learn)
    """
    train = task['train']

    # Average grid size
    avg_size = np.mean([ex['input'].size for ex in train])

    # Average number of colors
    avg_colors = np.mean([len(np.unique(ex['input'])) for ex in train])

    # Number of training examples
    num_examples = len(train)

    # Complexity score
    complexity = (avg_size * avg_colors) / num_examples

    # Map to generation budget
    if complexity < 50:
        return 100  # Simple tasks
    elif complexity < 200:
        return 200  # Medium tasks
    else:
        return 500  # Complex tasks (cap at 500)
```

**Files to modify**:
- Add `get_generation_budget()` function
- Replace hardcoded `generations=100` with adaptive budget
- Test on variety of task complexities

---

## Implementation Steps

### Step 1: Create v0.92 File
```bash
cp prometheus_arc_trm_phases_8910.py prometheus_arc_v092_baseline.py
```

### Step 2: Modify Primitives
- Split `PRIMITIVES` into `BASELINE_PRIMITIVES` and `CORRECTION_PRIMITIVES`
- Remove `'identity'` from `CORRECTION_PRIMITIVES`
- Add `OBJECT_PRIMITIVES` to `BASELINE_PRIMITIVES`

### Step 3: Add Hybrid Fitness
- Implement `hybrid_fitness()` function
- Replace binary fitness checks
- Update success threshold to 0.95

### Step 4: Add Adaptive Generations
- Implement `get_generation_budget()` function
- Replace hardcoded generation counts
- Test on sample tasks

### Step 5: Test
```bash
python3 prometheus_arc_v092_baseline.py --split evaluation --num-tasks 10 \
  2>&1 | tee arc_v092_test_10tasks.log
```

### Step 6: Full Benchmark
```bash
python3 prometheus_arc_v092_baseline.py --split evaluation --num-tasks 50 \
  2>&1 | tee arc_v092_baseline_50tasks.log
```

### Step 7: Compare Results
```python
# v0.91: 0/50 (0%)
# v0.92: ?/50 (?%)
# Target: 3-5/50 (6-10%)
```

---

## Success Criteria

### Minimum Success (v0.92)
- **Solve rate**: 3-5% (2-3 tasks out of 50)
- **Identity usage**: <25% of patterns (down from 48%)
- **Avg fitness**: >0.40 (up from ~0.35)

### Good Success (v0.92)
- **Solve rate**: 5-10% (3-5 tasks out of 50)
- **Identity usage**: <10% of patterns
- **Avg fitness**: >0.50

### Metrics to Track
1. **Solve rate** (primary)
2. **Average fitness** (progress indicator)
3. **Identity primitive usage** (should decrease)
4. **Object primitive usage** (should increase)
5. **High-fitness tasks** (>0.95 but not solved)

---

## Files Reference

### Current Files
- `prometheus_arc_trm_phases_8910.py` - v0.91 implementation (Phases 8-10)
- `arc_trm_phases8910_50tasks.log` - v0.91 benchmark results
- `arc_trm_phases8910_evaluation_50tasks.json` - v0.91 JSON results

### Files to Create
- `prometheus_arc_v092_baseline.py` - v0.92 with improvements
- `arc_v092_baseline_50tasks.log` - v0.92 benchmark log
- `arc_v092_baseline_50tasks.json` - v0.92 JSON results
- `V092_RESULTS.md` - Comparison document

### Documentation (Already Created)
- `PHASES_8910_ANALYSIS_v0_91.md` - Root cause analysis
- `NEXT_TASKS_v0_92.md` - Roadmap for v0.92-v0.95
- `STATUS_v0_91_COMPLETE.md` - v0.91 summary
- `READY_FOR_v0_92.md` - This document

---

## Expected Timeline

- **Day 1**: Implement Priority 1-2 (primitives + fitness)
- **Day 2**: Implement Priority 3-4 (objects + adaptive)
- **Day 3**: Test on 10 tasks, debug issues
- **Day 4**: Full 50-task benchmark
- **Day 5**: Analysis and v0.93 planning

**Total**: ~5 days to complete v0.92

---

## Questions to Answer

1. **Did removing identity help?**
   - Compare identity usage: v0.91 (48%) vs v0.92 (?%)

2. **Did hybrid fitness help?**
   - Compare avg fitness: v0.91 (~0.35) vs v0.92 (?%)

3. **Did object primitives help?**
   - How many tasks used object primitives?
   - Which object primitives were most useful?

4. **Did adaptive generations help?**
   - Did complex tasks get better results with more generations?

---

## Next Versions (After v0.92)

### v0.93: Constraint-Based Search
- Extract constraints from training examples
- Filter primitives that violate constraints
- Beam search over valid patterns
- **Target**: 10-15% solve rate

### v0.94: Program Synthesis
- Design domain-specific language (DSL)
- Beam search over programs (not patterns)
- Parametric operations (e.g., `rotate(angle=90)`)
- **Target**: 15-25% solve rate

### v0.95: Transfer Learning
- Embed tasks in semantic space
- Find similar solved tasks
- Adapt their solutions to new tasks
- **Target**: 25-35% solve rate

---

## Conclusion

v0.91 analysis is complete. All documentation is ready. The path to v0.92 is clear.

**Next action**: Implement v0.92 baseline improvements following the steps above.

**Expected outcome**: 5-10% solve rate (vs. 0% in v0.91).

Ready to proceed! 🚀
