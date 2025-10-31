# TRM Phase 3 Design (v0.87)

## Phase 2 Results Analysis

**High-Fitness Task Results (11 tasks, 90-97% baseline):**
- All 11 tasks improved in Cycle 1 (+2-4%)
- 0/11 reached 100% (failed to cross final threshold)
- Best: 98.89%, 98.11%, 97.82% (1-2% away from perfect)
- Problem: Corrections stuck on `['identity']` - not exploring targeted operations

**Root Cause:**
Phase 2's correction evolution is **too broad** - it evolves from scratch each cycle instead of focusing on the specific 1-2% mismatch. The seeding helps but evolution still explores random primitives instead of targeted fixes.

## Phase 3 Improvements

### 1. Targeted Primitive Selection (Priority: HIGH)

**Current Problem:**
```python
# Phase 2: Broad evolution with seeding
correction_solver.evolve_for_task(train_tuples, max_generations=50)
# Result: Returns ['identity'] or random primitives
```

**Phase 3 Solution:**
```python
# Analyze the specific pixel-level differences
pixel_diffs = analyze_pixel_differences(predicted, expected)

# Select targeted primitives based on difference patterns
if has_single_pixel_errors(pixel_diffs):
    # Micro-adjustments
    candidate_prims = ['identity', 'fill_zeros', 'remove_bg']
elif has_boundary_errors(pixel_diffs):
    # Edge/border operations
    candidate_prims = ['border', 'extend_edges', 'crop', 'pad_1']
elif has_symmetry_errors(pixel_diffs):
    # Symmetry/reflection operations
    candidate_prims = ['flip_h', 'flip_v', 'transpose', 'diag_flip']
elif has_scaling_errors(pixel_diffs):
    # Size operations
    candidate_prims = ['scale_2x', 'scale_3x', 'tile_2x2']

# Evolution restricted to these primitives only
correction_solver.set_primitive_pool(candidate_prims)
```

**Expected Impact:** 2-3 tasks cross 98% → 100% threshold

### 2. Iterative Local Search (Priority: MEDIUM)

**Current Problem:**
Each refinement cycle does full evolution (50 gen), even when 99% correct.

**Phase 3 Solution:**
```python
if current_fitness > 0.95:
    # Near-perfect: use local search instead of evolution
    corrections = local_search_corrections(
        current_pattern,
        failures,
        max_variations=20
    )
    # Try: remove one op, swap order, replace one op
else:
    # Far from perfect: use full evolution
    corrections = evolve_corrections(...)
```

**Expected Impact:** 10x faster for high-fitness tasks

### 3. Failure-Driven Composition Order (Priority: MEDIUM)

**Current Problem:**
Phase 2 tries 4 composition strategies blindly:
1. base → correction
2. correction → base
3. interleave
4. replace (correction only)

**Phase 3 Solution:**
```python
# Analyze WHERE failures occur in the pipeline
failure_stage = analyze_failure_location(current_pattern, failures)

if failure_stage == 'early':  # First few operations wrong
    # correction → base (fix input first)
    order = [correction_pattern, base_pattern]
elif failure_stage == 'late':  # Last operations wrong
    # base → correction (fix output last)
    order = [base_pattern, correction_pattern]
else:
    # Try both
    evaluate_and_pick_best([base→corr, corr→base])
```

**Expected Impact:** 1-2% fitness gain per successful composition

### 4. Early Stopping with Confidence (Priority: LOW)

**Current Problem:**
Always run 3 cycles even if stuck (Cycles 2-3 often repeat same correction).

**Phase 3 Solution:**
```python
if no_improvement_for_2_cycles and pixel_diff < 1%:
    # Very close but stuck - try one last targeted push
    final_correction = micro_adjustment_search(failures)
    if final_correction improves:
        accept and stop
    else:
        stop early (confidence: pattern is likely wrong, not fixable)
```

**Expected Impact:** 30% faster overall, no accuracy loss

## Implementation Plan

### Minimal Phase 3 (v0.87) - 1 hour
**Goal:** Get 1-2 high-fitness tasks to 100%

Changes:
1. Add `_analyze_pixel_patterns()` to extract micro-failure types
2. Add `_select_targeted_primitives()` for focused search
3. Modify `_synthesize_corrections()` to restrict primitive pool
4. Test on 11 high-fitness tasks

**Expected:** 1-2/11 tasks → 100% (9% → 18% solve rate on high-fitness)

### Full Phase 3 (v0.88) - 3 hours
**Goal:** Maximize high-fitness solve rate

Additional changes:
5. Add local search for >95% fitness
6. Implement smart composition ordering
7. Add early stopping with micro-adjustment fallback
8. Test on 50 evaluation tasks

**Expected:** 3-4/11 high-fitness → 100% (27-36% solve rate)

## Success Metrics

**Phase 2 Baseline:**
- High-fitness (90-97%): 0/11 → 100% (0%)
- Evaluation (mixed): 0/5 → 100% (0%)

**Phase 3 Minimal Target:**
- High-fitness: 1-2/11 → 100% (9-18%)
- Evaluation: 0-1/10 → 100% (0-10%)

**Phase 3 Full Target:**
- High-fitness: 3-4/11 → 100% (27-36%)
- Evaluation: 1-2/50 → 100% (2-4%)

## Risk Assessment

**Low Risk (v0.87):**
- Targeted primitive selection is conservative
- Backward compatible (falls back to Phase 2 if no targeted prims found)
- Test on same 11 tasks - easy to compare

**Medium Risk (v0.88):**
- Local search may get stuck in local optima
- Smart composition may hurt some tasks while helping others
- Need A/B testing on larger set

## Next Steps

1. Implement v0.87 minimal (targeted primitives)
2. Test on 11 high-fitness tasks
3. If ≥1 task reaches 100%, proceed to v0.88
4. If 0 tasks reach 100%, analyze failure modes and iterate
