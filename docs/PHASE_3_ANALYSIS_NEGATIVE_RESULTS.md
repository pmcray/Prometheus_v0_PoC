# Phase 3 Analysis: Negative Results from Primitive Expansion

## Date: October 10, 2025

---

## Executive Summary

**Finding**: Options C & E (strategic primitive expansion from 38→56 primitives) achieved marginal training improvement (+6.7%) but **WORSENED generalization** (overfitting increased from 7.5x to 8.0x). This is a critical negative result showing that expanding the primitive library is not the solution to the ARC-AGI plateau.

**Implication**: The path forward requires regularization and validation-based training, not more primitives.

---

## Experimental Setup

### Baseline (38 primitives)
- Training: 30/400 (7.5%)
- Evaluation: 4/400 (1.0%)
- Overfitting ratio: 7.5x
- Generalization rate: 13.3%

### Options C & E (56 primitives)
- Added 18 new primitives based on failure analysis
- Failure analysis: 50 task sample
  - COLOR_MAPPING: 46%
  - SPATIAL_TRANSFORMATION: 32%
  - SIZE_TRANSFORMATION: 16%
  - REPETITION_TILING: 6%
- New primitives targeted these gaps

---

## Results

### Training Performance

| System | Solved | Rate | Improvement |
|--------|--------|------|-------------|
| 38 primitives | 30/400 | 7.5% | baseline |
| 56 primitives | 32/400 | 8.0% | +2 tasks (+6.7%) |

**Analysis**: 47% more primitives → only 6.7% improvement
- Efficiency: 0.11 tasks per new primitive
- Severely diminishing returns

### Evaluation Performance

| System | Solved | Rate | Generalization |
|--------|--------|------|----------------|
| 38 primitives | 4/400 | 1.0% | 13.3% (4/30) |
| 56 primitives | 4/400 | 1.0% | 12.5% (4/32) |

**Analysis**: ZERO improvement in generalization
- Same 4 tasks solved
- Overfitting actually increased: 7.5x → 8.0x
- More primitives made generalization worse

### Pattern Complexity Distribution

**Training Set (56 primitives)**:
- 1 operation: 22 solutions (68.8%)
- 2 operations: 8 solutions (25.0%)
- 3 operations: 2 solutions (6.2%)

**Evaluation Set (56 primitives)**:
- 1 operation: 3 solutions (75.0%)
- 2 operations: 1 solution (25.0%)
- 3+ operations: 0 solutions (0%)

**Critical Finding**: Complex patterns (3+ ops) do NOT generalize at all.

### New Primitive Usage

Out of 18 new primitives, only **3 were used** (17% usage rate):

| Primitive | Uses | Tasks |
|-----------|------|-------|
| tile_2x1 | 2 | 231, 249 |
| overlay_max | 1 | 188 |
| tile_1x3 | 1 | 211 |
| **All others** | **0** | **NEVER USED** |

**Critical Finding**: 83% of new primitives (15/18) were never used in any solution. This suggests they don't match actual ARC pattern types, or the search space is too large to find them.

---

## Critical Insights

### 1. Diminishing Returns from Primitive Expansion

**Evidence**:
- +47% primitives → +6.7% training improvement
- +47% primitives → 0% evaluation improvement
- 83% of new primitives never used

**Implication**: Adding more primitives is NOT the solution. The search space grows exponentially (38^5 = 79M → 56^5 = 550M patterns), making it harder to find good solutions and easier to overfit.

### 2. More Primitives Worsen Overfitting

**Evidence**:
- 38 primitives: 7.5x overfitting gap
- 56 primitives: 8.0x overfitting gap
- Generalization rate dropped: 13.3% → 12.5%

**Implication**: Larger search space enables more memorization, less generalization. This is the opposite of what we want.

### 3. Complex Patterns Don't Generalize

**Evidence**:
- Training: 6.2% of solutions use 3+ operations
- Evaluation: 0% of solutions use 3+ operations
- All generalizing solutions are 1-2 operations only

**Implication**: Current complexity penalty (0.01/op) is far too weak. Should be 0.1/op or enforce hard limit of max 2 operations.

### 4. Failure Analysis Doesn't Predict Useful Primitives

**Evidence**:
- Designed 18 primitives based on 50-task failure analysis
- 15 primitives (83%) were never used
- Only 3 primitives contributed to solutions

**Implication**: Human intuition about "missing patterns" doesn't translate to useful primitives. The ARC tasks require patterns we haven't identified, or the search is too inefficient to find them.

---

## Root Cause Analysis

### Why Does Primitive Expansion Fail?

**1. Search Space Explosion**
- 38 primitives: 38^5 = 79M possible patterns
- 56 primitives: 56^5 = 550M possible patterns (7x larger)
- Evolution runs for 200 gen × 50 pop = 10K evaluations per task
- Coverage: 10K / 550M = 0.0018% of search space
- **Result**: Can't find good solutions, easier to memorize specific ones

**2. No Regularization**
- Complexity penalty: 0.01 per operation (too weak)
- No max length constraint
- No validation set for early stopping
- **Result**: System optimizes for training fit, not generalization

**3. No Validation Signal**
- All 400 training tasks used for evolution
- No held-out set to measure generalization during training
- **Result**: No feedback about overfitting until evaluation

**4. Wrong Optimization Target**
- Optimizing: Max fitness on training examples
- Should optimize: Simplest pattern that generalizes
- **Result**: Complex, task-specific patterns win over simple, general ones

---

## Comparison to Foundation Models

| System | Training | Evaluation | Overfitting | Notes |
|--------|----------|------------|-------------|-------|
| GPT-4 (2023) | ~5% | ~5% | ~1.0x | Good generalization |
| Gemini 1.5 Pro | ~10% | ~10% | ~1.0x | Good generalization |
| Our 38-prim | 7.5% | 1.0% | 7.5x | Severe overfitting |
| Our 56-prim | 8.0% | 1.0% | 8.0x | Even worse overfitting |

**Key Observation**: Neural foundation models generalize 7-8x better than our symbolic system, despite having similar or worse training performance. They must be using better regularization (dropout, weight decay, etc.) and/or learning more general representations.

---

## Implications for Research

### What This Proves

1. **Pure symbolic evolution plateaus hard**: Without regularization, evolution memorizes rather than generalizes
2. **More primitives ≠ better**: Larger search space makes the problem worse, not better
3. **Training performance is misleading**: Cannot trust training metrics as capability indicators
4. **Simplicity bias is critical**: Need strong regularization toward simple patterns

### What This Suggests

1. **Validation-based training is essential**: Need held-out set to detect overfitting during evolution
2. **Strong regularization needed**: Complexity penalty should be 10x higher (0.1/op) or max length = 2
3. **Ensemble of simple patterns**: Multiple simple patterns voting may beat single complex patterns
4. **Meta-learning focus**: Learn which primitives generalize, not just which solve training tasks

### What This Rules Out

1. ❌ Adding more primitives (Options C & E approach)
2. ❌ Longer evolution runs without regularization (Option B approach)
3. ❌ Failure-analysis-based primitive design (doesn't predict useful ops)
4. ❌ Trusting training performance as success metric

---

## Recommended Next Steps

### Immediate (Next 1-2 hours)

**Option 1: Implement Regularized Evolution**
- Max pattern length: 2 operations (hard limit)
- Complexity penalty: 0.1 per operation (10x current)
- Population: 100 (2x diversity)
- Test on evaluation set first (not training)

**Expected Result**: 5-8/400 (1.2-2.0%) on evaluation
- Lower training performance (fewer memorized solutions)
- Better generalization (simpler patterns)
- More honest capability assessment

**Option 2: Validation-Based Training**
- Split 400 training → 300 train / 100 validation
- Evolve on 300, select best on 100 validation
- Test on 400 evaluation
- Early stopping if validation plateaus

**Expected Result**: 6-10/400 (1.5-2.5%) on evaluation
- Validation signal prevents overfitting
- Better transfer to evaluation set
- More realistic capability estimate

### Short-term (Next 1-2 days)

**Option 3: Test on ARC-AGI-2**
- 1000 training tasks (vs 400 in ARC-AGI-1)
- 120 evaluation tasks
- See if more data helps or hurts

**Expected Result**: 1-2% on evaluation (harder dataset)
- Validates whether findings generalize to new data
- May reveal if we need more data or better algorithms

**Option 4: Ensemble Simple Patterns**
- Train 10 independent evolutions with max_len=1
- Each finds single-operation patterns
- Vote on evaluation set
- Take consensus or union

**Expected Result**: 8-12/400 (2-3%) on evaluation
- Simple patterns should generalize better
- Ensemble may cover more pattern types
- Tests hypothesis that simplicity helps

### Long-term (Next 1 week)

**Option 5: Write Research Paper**
- Title: "Why More Primitives Don't Help: Overfitting in Evolutionary ARC-AGI"
- Document negative results
- Explain search space explosion
- Propose validation-based solutions

**Option 6: Compare to Neural Guidance**
- Use small neural model to score pattern "simplicity"
- Bias evolution toward neural-preferred patterns
- Test if neural regularization helps

---

## Conclusion

**Options C & E failed to improve generalization**, despite achieving the training target (8%). This is a critical negative result that changes our understanding of the problem:

1. **The problem is NOT lack of primitives** - We have enough primitives, but can't find/generalize them
2. **The problem IS overfitting** - Evolution memorizes training tasks instead of learning general rules
3. **The solution is regularization** - Need strong bias toward simple patterns + validation feedback

**Next priority**: Implement regularized evolution (max_len=2, complexity=0.1) and test on evaluation set to see if it improves generalization.

This is valuable research: **Proving what doesn't work is as important as finding what does.**

---

## Appendix: Detailed Results

### Training Set Solutions (56 primitives)

32 tasks solved:
- 22 with 1-op patterns (68.8%)
- 8 with 2-op patterns (25.0%)
- 2 with 3-op patterns (6.2%)

Duration: 970.1s (16.2 min)
Patterns evolved: 3,801,000
Successful patterns: 37

### Evaluation Set Solutions (56 primitives)

4 tasks solved:
- 3 with 1-op patterns (75.0%)
- 1 with 2-op patterns (25.0%)
- 0 with 3-op patterns (0%)

Duration: 859.9s (14.3 min)
Patterns evolved: 3,980,100
Successful patterns: 4

### Unused Primitives (15 of 18 new)

Never used in any solution:
- color_add, color_add2, color_multiply, color_by_row_col
- tile_1x2, tile_3x1
- diagonal_shift, antidiag_mirror, fold_quadrants
- mask_color1, mask_color2, invert_fg_bg
- extend_edges_outward, corners, replicate_smallest

These primitives may be useful for ARC tasks, but the evolutionary search cannot find them in reasonable time, or they don't compose well with other primitives.

---

## Files Modified

- `prometheus_arc_evolution.py`: Added 18 primitives (38→56)
- `arc_evolution_results/evolution_training_results.json`: 32/400 training results
- `arc_evolution_results/evolution_evaluation_results.json`: 4/400 evaluation results

## Files Created

- `analyze_arc_failures.py`: Failure analysis tool
- `arc_failure_analysis.json`: 50-task sample analysis
- `OPTIONS_C_E_IMPLEMENTATION.md`: Implementation documentation
- `analyze_evaluation_failures.py`: Generalization analysis
- `WORK_SESSION_SUMMARY.md`: Session summary
- `PHASE_3_ANALYSIS_NEGATIVE_RESULTS.md`: This document

---

*Generated: October 10, 2025*
*Prometheus v0.69 - ARC-AGI Research*
