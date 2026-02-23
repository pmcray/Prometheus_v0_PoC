# Option E Phase 1 - Post-Mortem Analysis

**Date**: 2025-10-23
**Status**: ❌ **FAILED** - Option E did not achieve target, fundamental issues identified

---

## Executive Summary

**Objective**: Break through 10% solve rate ceiling using new operations
**Target**: 14-18% solve rate (7-9 tasks)
**Achieved**: 8.0% solve rate (4 tasks)
**Result**: **FAILURE** - Below baseline, below target

**Root Cause**: **Beam search dilution** - adding operations hurts performance with fixed search budget

---

## Timeline

### v0.96 (25 operations)
- Added 10 Phase 1 operations (5 size + 5 color)
- Result: 4/50 solved (8.0%)
- 4 operations never used (resize_with_padding, isolate_color, extract_color, keep_colors)
- 100+ operation failures per task from resize_with_padding
- Lost 2 baseline tasks

### v0.96a (21 operations)
- Removed 4 redundant/buggy operations
- Result: 4/50 solved (8.0%) - **NO IMPROVEMENT**
- Runtime improved (410s vs 467s)
- Still lost 2 baseline tasks

---

## Key Finding: Beam Search Dilution

### The Problem

**With 15 operations (v0.95):**
- Beam width = 50
- Depth = 5
- Each depth explores ~750 candidates (50 × 15)
- Result: 5/50 tasks solved (10%)

**With 25 operations (v0.96):**
- Beam width = 50 (same)
- Depth = 5 (same)
- Each depth explores ~1250 candidates (50 × 25)
- Result: 4/50 tasks solved (8%) - **WORSE**

**With 21 operations (v0.96a):**
- Beam width = 50
- Depth = 5
- Each depth explores ~1050 candidates (50 × 21)
- Result: 4/50 tasks solved (8%) - **STILL WORSE**

### Why It Hurts

**Beam search keeps top-K candidates**. With more operations:

1. **Diluted attention**: Good programs pushed out by mediocre alternatives
2. **Local optima**: Search finds suboptimal programs earlier (e.g., `map_color` instead of `crop`)
3. **Wasted budget**: ~10% of operations fail (symmetrize bugs), consuming beam slots

**Evidence**: 17 tasks found programs with exactly -0.010 fitness vs baseline, all using `map_color` where better operations existed.

---

## What We Lost

### Baseline Regression Details

| Task ID | v0.95 | v0.96/v0.96a | v0.95 Program | v0.96 Program | Delta |
|---------|-------|--------------|---------------|---------------|-------|
| 3e6067c3 | 0.959 (SOLVED) | 0.949 (NOT) | `crop(mode=content)` | `map_color(0→1)` | -0.010 |
| 142ca369 | 0.903 | 0.893 | `transpose, transpose` | `map_color(1→1)` | -0.010 |

**Both tasks**: Beam search found `map_color` first, never explored better alternatives.

---

## What We Gained

### Task 38007db0 - NEW SOLVE ✅

**Program**: `fit_to_canvas(align=center,canvas_h=19,canvas_w=7)`
**Fitness**: 0.971
**Improvement over v0.95**: +0.874

**Why it worked**: Task specifically needs canvas fitting, Phase 1 operation was perfect match.

### Average Fitness Improvement

**v0.95**: 0.572
**v0.96a**: 0.687
**Change**: +0.115 (20% improvement)

**16/50 tasks improved**, including large gains:
- Task 136b0064: +0.557 (compress_to_fit)
- Task 5545f144: +0.532 (fit_to_canvas)
- Task 269e22fb: +0.424 (expand_to_size)

---

## Operation Usage Analysis

### v0.96 (25 operations)

**Used (7 operations)**:
- compress_to_fit: 9 tasks
- fit_to_canvas: 5 tasks (1 solved!)
- expand_to_size: 4 tasks
- filter_color: 4 tasks
- remove_color: 2 tasks
- crop_to_content: 2 tasks
- filter_by_color: 1 task

**Never used (4 operations)**:
- resize_with_padding (buggy)
- isolate_color (redundant)
- extract_color (redundant)
- keep_colors (redundant)

### v0.96a (21 operations)

Same usage pattern - removing unused operations had NO EFFECT on solve rate.

**Conclusion**: Problem is not redundancy, it's the fundamental dilution of beam search.

---

## The Paradox

**Adding useful operations decreases performance!**

**Why this happens**:
1. Phase 1 operations ARE useful (16 tasks improved)
2. But they create more branching in search tree
3. Fixed beam budget (width=50) can't explore all branches
4. Good programs evicted from beam by mediocre alternatives
5. Net result: 1 new task solved, 2 baseline tasks lost

**This is a fundamental limitation of beam search with fixed budget**.

---

## Failed Hypotheses

### Hypothesis 1: Operation failures cause regression ❌

**Tested**: Removed buggy resize_with_padding
**Result**: No improvement (still 4/50)
**Conclusion**: Failures are symptom, not cause

### Hypothesis 2: Redundant operations dilute search ❌

**Tested**: Removed 4 redundant operations (25 → 21)
**Result**: No improvement (still 4/50)
**Conclusion**: Even "good" operations cause dilution

### Hypothesis 3: Parameter generation issues ❌

**Already fixed**: Task-aware parameters in v0.96
**Result**: 10-task test improved (0 → 1 solved)
**Full benchmark**: Still below baseline
**Conclusion**: Parameters are correct, search budget is the bottleneck

---

## Validated Hypotheses

### Hypothesis 1: Beam search dilution is the primary issue ✅

**Evidence**:
- v0.95 (15 ops): 5/50 solved
- v0.96 (25 ops): 4/50 solved
- v0.96a (21 ops): 4/50 solved
- Same beam width (50), same depth (5)

**Conclusion**: Each added operation reduces effectiveness

### Hypothesis 2: map_color dominates early beam ✅

**Evidence**: 17 tasks have -0.010 regression, all use map_color

**Reason**: `map_color` is simple (1-op), gets high fitness early, fills beam slots

**Effect**: Blocks exploration of better multi-op solutions

### Hypothesis 3: Close calls don't use new operations ✅

**Evidence**: 15/21 close calls (0.80-0.95) use only baseline operations

**Conclusion**: New operations help medium-fitness tasks, but don't push close calls over threshold

---

## Lessons Learned

### Lesson 1: More Operations ≠ Better Performance

**Finding**: Adding operations decreased solve rate (10% → 8%)

**Why**: Fixed beam search budget can't handle larger operation set

**Implication**: Can't simply "add more operations" to improve - need different search strategy

### Lesson 2: Beam Search Needs Scaling

**Finding**: 67% more operations (15 → 25) requires larger beam

**Math**:
- 15 ops × 50 width = 750 candidates/depth
- 25 ops × 50 width = 1250 candidates/depth
- To maintain same coverage: need width=83

**Solution**: Either increase beam width OR reduce operation count OR change search algorithm

### Lesson 3: Operation Quality vs Quantity

**Finding**: 7 useful operations identified, but can't use them effectively

**Trade-off**:
- Keep all 7: Search diluted, 4/50 solved
- Keep only top 3?: Less dilution, but miss some tasks
- Need smarter search, not fewer operations

### Lesson 4: Average Fitness ≠ Solve Rate

**Finding**: Average fitness +20%, solve rate -20%

**Reason**: New operations help many tasks get "closer", but dilution prevents solving

**Implication**: Fitness improvements are real, but beam search can't capitalize on them

---

## Path Forward Options

### Option 1: Increase Beam Width ⭐ **RECOMMENDED**

**Change**: beam_width: 50 → 100

**Rationale**: Compensate for larger operation set

**Expected outcome**: Restore baseline (5/50), possibly gain from Phase 1 ops (6-7/50)

**Cost**: 2x slower (8s → 16s per task, ~13 min total)

**Confidence**: High - directly addresses dilution problem

### Option 2: Increase Search Depth

**Change**: max_depth: 5 → 7

**Rationale**: Explore longer program sequences

**Expected outcome**: May help close calls (21 tasks at 0.80-0.95)

**Cost**: Much slower (~5x), may hit timeout

**Confidence**: Medium - helps some tasks, not others

### Option 3: Hybrid Search

**Change**: Use beam search for baseline ops, greedy search for Phase 1 ops

**Rationale**: Separate search spaces

**Expected outcome**: Keep baseline (5/50), add Phase 1 gains (1-2 tasks)

**Cost**: Complex implementation

**Confidence**: Medium - untested approach

### Option 4: Revert to Baseline + Deep Beam Search

**Change**: Use 15 operations, increase width to 100, depth to 7

**Rationale**: Focus search budget on proven operations

**Expected outcome**: 12-15/50 (Option D projection)

**Cost**: Very slow (~30-40 min total)

**Confidence**: Medium - Option D already tested

### Option 5: Adaptive Beam Width

**Change**: Dynamically adjust beam width based on promising candidates

**Rationale**: Allocate budget where needed

**Expected outcome**: Best of both worlds

**Cost**: Complex implementation

**Confidence**: Low - novel approach, unpredictable

---

## Recommended Action

### Immediate (Next Step)

**Try Option 1: Increase Beam Width to 100**

**Justification**:
1. Simplest change (1 parameter)
2. Directly addresses dilution
3. Phase 1 operations ARE useful (proved by fitness gains)
4. 2x slowdown is acceptable (8s → 16s per task)

**Implementation**:
```python
synthesizer = ProgramSynthesizer(
    beam_width=100,  # was 50
    max_depth=5,
    max_candidates_per_op=3
)
```

**Expected results**:
- Restore 2 lost baseline tasks: 4/50 → 6/50
- Phase 1 operations solve 0-1 more: 6/50 → 6-7/50 (12-14%)
- Still below target (14-18%), but shows if approach is viable

**Decision point**:
- If reaches 6-7/50: Continue optimizing (Phase 2 operations, deeper search)
- If stays at 4/50: Fundamental approach is wrong, try Option 4 or different strategy

### If Option 1 Succeeds

**Next steps**:
1. Add Phase 2 operations (object grouping, symmetry) with width=100
2. Target: 12-15/50 (24-30%)
3. Consider depth=7 for close calls

### If Option 1 Fails

**Pivot to**:
1. Revert to 15 operations
2. Deep beam search (width=100, depth=7)
3. Follow Option D path
4. Target: 12-15/50 via exploration depth, not operation count

---

## Conclusion

**Option E Phase 1 Status**: ❌ **FAILED** but learned critical lessons

**Root Cause**: Beam search with fixed budget cannot handle expanded operation set

**Key Insight**: **More operations ≠ better** when search budget is constrained

**Silver Lining**:
- ✅ Phase 1 operations work (proved by 38007db0 solve)
- ✅ Average fitness improved +20%
- ✅ 46% of tasks use new operations
- ✅ Identified exact bottleneck (beam dilution)

**Path Forward**: **Increase beam width to 100, re-test**

**Confidence**: Medium - if width=100 doesn't restore baseline, approach is fundamentally flawed

**Timeline**:
- Beam width=100 test: 15 minutes
- Analysis: 15 minutes
- Decision point: 30 minutes

---

**End of Post-Mortem**

**Next Action**: Test beam_width=100 with 21 operations (v0.96a)
