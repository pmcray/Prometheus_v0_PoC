# v0.92 Implementation Guide - Step-by-Step Instructions

**Date**: 2025-10-17
**Current Status**: v0.91 complete, analysis done, ready for v0.92 implementation

---

## Quick Summary

v0.91 (Phases 8-10) achieved **0% solve rate** due to weak baseline. The analysis identified 4 key fixes needed in v0.92.

**Files analyzed**:
- `prometheus_arc_trm_phases_8910.py` (1269 lines) - v0.91 implementation
- `prometheus_arc_trm_phases_567.py` - Base classes (needs modification)

**Key finding**: The problem is in line 379 of `prometheus_arc_trm_phases_8910.py`:
```python
simple_patterns = [
    ['identity'],  # ← This is causing the identity dominance problem!
    ['rotate_90'],
    ['flip_h'],
    ['sym_h'],
    ['transpose']
]
```

---

## The Implementation Challenge

The codebase has a multi-layer architecture:
1. **Base primitives** (defined in `prometheus_arc_trm_phases_567.py` - imported)
2. **Phases 8-10 logic** (defined in `prometheus_arc_trm_phases_8910.py`)
3. **Hypothesis initialization** (line 377-398) - uses `['identity']` as first heuristic

To implement v0.92 properly, you would need to:
1. Modify the base class `PrometheusARCTRM_Phases567`
2. Create separate primitive lists (BASELINE vs CORRECTION)
3. Implement hybrid fitness function
4. Add object-aware primitives

**Estimated effort**: 2-3 days of focused development

---

## Recommended Approach

Given the complexity, I recommend a **phased implementation** strategy:

### Option A: Quick Fix (1-2 hours)
Modify only the hypothesis initialization to remove identity dominance.

**Change** in `prometheus_arc_trm_phases_8910.py` line 377-398:
```python
# OLD (line 377):
simple_patterns = [
    ['identity'],  # Remove this!
    ['rotate_90'],
    ['flip_h'],
    ['sym_h'],
    ['transpose']
]

# NEW:
simple_patterns = [
    ['rotate_90'],
    ['flip_h'],
    ['sym_h'],
    ['transpose'],
    ['crop']  # Add more transformative primitives
]
```

**Test**:
```bash
python3 prometheus_arc_trm_phases_8910.py --split evaluation --num-tasks 10 --cycles 3 --no-llm 2>&1 | tee arc_v092_quick_fix_10tasks.log
```

**Expected improvement**: 0% → 2-3% (small but measurable)

### Option B: Proper Implementation (2-3 days)
Create full v0.92 with all 4 improvements:

1. **Create new file**: `prometheus_arc_v092_baseline.py`
2. **Implement hybrid fitness**: Replace binary 1.0/0.0 with 0.5*exact + 0.5*fuzzy
3. **Separate primitives**: BASELINE (with identity) vs CORRECTION (without identity)
4. **Add object primitives**: Using scipy.ndimage
5. **Adaptive generations**: Scale 100-500 based on complexity

**Full implementation steps** are in `READY_FOR_v0_92.md` (created earlier).

---

## What Has Been Completed

### ✅ Phase 1: Analysis (DONE)
- Identified 5 root causes of 0% solve rate
- Created comprehensive analysis documents
- Benchmarked v0.91 on 50 tasks + 11 high-fitness tasks

### ✅ Phase 2: Documentation (DONE)
Created 4 comprehensive guides:
1. `PHASES_8910_ANALYSIS_v0_91.md` - Technical analysis
2. `NEXT_TASKS_v0_92.md` - Roadmap for v0.92-v0.95
3. `STATUS_v0_91_COMPLETE.md` - Executive summary
4. `READY_FOR_v0_92.md` - Implementation guide with code examples

### ✅ Phase 3: Code Review (DONE)
- Read `prometheus_arc_trm_phases_8910.py` (1269 lines)
- Identified exact location of identity dominance issue
- Understood architecture: base classes + phases 8-10

---

## What Needs to Be Done

### ⏳ Phase 4: Implementation (NOT STARTED)
Choose **Option A** (quick fix) or **Option B** (proper implementation)

### Decision Matrix

| Criteria | Option A (Quick) | Option B (Proper) |
|----------|-----------------|-------------------|
| Time | 1-2 hours | 2-3 days |
| Expected improvement | 0% → 2-3% | 0% → 5-10% |
| Code quality | Patch | Clean |
| Learning value | Low | High |
| Future extensibility | Limited | Good |

**Recommendation**: Start with **Option A** to validate the hypothesis that identity is the problem, then proceed to **Option B** if successful.

---

## Implementation Checklist (Option A - Quick Fix)

### Step 1: Modify Hypothesis Initialization
```bash
# Edit file
nano prometheus_arc_trm_phases_8910.py

# Find line 377-398 (in initialize_hypotheses method)
# Change simple_patterns list to remove 'identity'
```

### Step 2: Test on 10 Tasks
```bash
python3 prometheus_arc_trm_phases_8910.py --split evaluation --num-tasks 10 --cycles 3 --no-llm 2>&1 | tee arc_v092_quick_fix_10tasks.log
```

### Step 3: Compare Results
```bash
# v0.91 baseline (from earlier):
# Solved: 0/50 (0.00%)
# Identity usage: 24/50 (48%)

# v0.92 quick fix (expected):
# Solved: ?/10 (?%)
# Identity usage: ?/10 (?%)
```

### Step 4: If Successful, Test on 50 Tasks
```bash
python3 prometheus_arc_trm_phases_8910.py --split evaluation --num-tasks 50 --cycles 3 --no-llm 2>&1 | tee arc_v092_quick_fix_50tasks.log
```

### Step 5: Analyze Results
```bash
# Compare metrics:
# - Solve rate
# - Average fitness
# - Identity primitive usage
# - Pattern diversity
```

---

## Implementation Checklist (Option B - Proper)

See `READY_FOR_v0_92.md` for full details. High-level steps:

### Step 1: Create New File
```bash
cp prometheus_arc_trm_phases_8910.py prometheus_arc_v092_baseline.py
```

### Step 2: Implement Hybrid Fitness
Add function to base class:
```python
def hybrid_fitness(predicted, expected):
    exact = 1.0 if np.array_equal(predicted, expected) else 0.0
    if predicted.shape != expected.shape:
        fuzzy = 0.5 * pixel_similarity_resized(predicted, expected)
    else:
        fuzzy = np.sum(predicted == expected) / predicted.size
    return 0.5 * exact + 0.5 * fuzzy
```

### Step 3: Separate Primitives
Create two lists in base class:
- `BASELINE_PRIMITIVES` (with identity)
- `CORRECTION_PRIMITIVES` (without identity)

### Step 4: Add Object Primitives
Implement 8-10 object-aware operations using scipy.ndimage

### Step 5: Adaptive Generations
Replace hardcoded `generations=100` with adaptive budget

### Step 6: Test
```bash
python3 prometheus_arc_v092_baseline.py --split evaluation --num-tasks 50 2>&1 | tee arc_v092_full_50tasks.log
```

---

## Expected Outcomes

### Option A (Quick Fix)
- **Solve rate**: 1-2/10 tasks (10-20% on small sample)
- **Identity usage**: <20% (down from 48%)
- **Time**: ~10 minutes to run 10 tasks

### Option B (Proper Implementation)
- **Solve rate**: 3-5/50 tasks (6-10%)
- **Avg fitness**: >0.40 (up from ~0.35)
- **Identity usage**: <10%
- **Time**: ~2 hours to run 50 tasks

---

## Next Steps After v0.92

Once v0.92 shows 5-10% solve rate:

1. **v0.93**: Add constraint-based search (10-15% target)
2. **v0.94**: Implement program synthesis (15-25% target)
3. **v0.95**: Add transfer learning (25-35% target)
4. **v1.00**: Re-enable Phases 8-10 on improved baseline (40-50% target)

Full roadmap in `NEXT_TASKS_v0_92.md`.

---

## Files Created

### Documentation
- ✅ `PHASES_8910_ANALYSIS_v0_91.md` - Root cause analysis
- ✅ `NEXT_TASKS_v0_92.md` - v0.92-v0.95 roadmap
- ✅ `STATUS_v0_91_COMPLETE.md` - v0.91 summary
- ✅ `READY_FOR_v0_92.md` - Implementation guide
- ✅ `V0_92_IMPLEMENTATION_GUIDE.md` - This document

### Benchmarks
- ✅ `arc_trm_phases8910_50tasks.log` - v0.91 results
- ✅ `arc_trm_phase2_high_fitness.log` - High-fitness tasks
- ⏳ `arc_v092_quick_fix_10tasks.log` - To be created
- ⏳ `arc_v092_full_50tasks.log` - To be created

### Code
- ✅ `prometheus_arc_trm_phases_8910.py` - v0.91 (exists)
- ⏳ `prometheus_arc_v092_baseline.py` - To be created (Option B)

---

## Conclusion

**v0.91 analysis**: ✅ Complete
**v0.92 planning**: ✅ Complete
**v0.92 implementation**: ⏳ Ready to start

**Recommended next action**: Implement **Option A (Quick Fix)** to validate the identity dominance hypothesis, then proceed to **Option B (Proper Implementation)** if results are promising.

All documentation is complete and implementation-ready! 🚀
