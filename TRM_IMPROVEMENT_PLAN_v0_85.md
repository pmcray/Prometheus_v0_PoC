# TRM Improvement Plan (v0.85)

**Date**: 2025-10-16
**Current Version**: v0.84 (functional but no improvements yet)
**Target**: Enable TRM to refine 85-95% fitness solutions to 100%

---

## Problem Analysis

### Current TRM Behavior (v0.84)

**Test Results** (10 tasks, 100 gen baseline + 3 cycles):
- 24 refinement cycles attempted
- 0 successful improvements
- All corrections returned `['identity']`
- Combined patterns made fitness worse (0.96 → 0.0)

**Root Cause**: Corrections are evolved from scratch, ignoring:
1. The current near-optimal pattern
2. The specific pixels that are wrong
3. The failure type (partial_match vs wrong_size, etc.)

---

## Proposed Improvements

### **Improvement 1: Seed Correction Population with Current Pattern**

**Current** (`_synthesize_corrections`):
```python
correction_solver = PrometheusARCFuzzyFitness(
    population_size=self.population_size // 2,
    max_pattern_length=min(3, self.max_pattern_length),
    use_fuzzy=self.use_fuzzy
)
# Starts from random population
result_pattern = correction_solver.evolve_for_task(...)
```

**Improved**:
```python
# Create correction solver
correction_solver = PrometheusARCFuzzyFitness(...)

# Seed 50% of population with variations of current pattern
correction_solver.initialize_population()
for i in range(len(correction_solver.population) // 2):
    # Create small mutations of current pattern
    mutated = self._small_mutation(current_pattern)
    correction_solver.population[i] = mutated

# Now evolve from this seeded population
result_pattern = correction_solver.evolve_for_task(...)
```

**Expected Impact**: Corrections will be small refinements of current pattern, not random sequences

---

### **Improvement 2: Use Fuzzy Fitness for Pattern Evaluation**

**Current** (`_evaluate_pattern`):
```python
def _evaluate_pattern(self, pattern, train_examples) -> float:
    correct = 0
    for example in train_examples:
        predicted = self._apply_pattern_from_names(pattern, input_grid)
        if np.array_equal(predicted, expected):  # BINARY
            correct += 1
    return correct / len(train_examples)
```

**Problem**: Uses binary fitness (0.0 or 1.0) instead of fuzzy fitness!

**Improved**:
```python
def _evaluate_pattern_fuzzy(self, pattern, train_examples) -> float:
    """Evaluate with FUZZY FITNESS (pixel similarity)"""
    total_similarity = 0.0
    for example in train_examples:
        predicted = self._apply_pattern_from_names(pattern, input_grid)
        # Use fuzzy matching
        similarity = self.baseline._fuzzy_match(predicted, expected)
        total_similarity += similarity
    return total_similarity / len(train_examples)
```

**Expected Impact**: Can detect small improvements (0.96 → 0.97) instead of treating as no change

---

### **Improvement 3: Smarter Pattern Composition**

**Current** (`_compose_patterns`):
```python
def _compose_patterns(base_pattern, correction_pattern):
    combined = base_pattern + correction_pattern  # Just concatenate
    return combined[:max_total_length]
```

**Problem**:
- `['identity'] + ['identity']` = same as `['identity']`
- Adding correction may cancel out base pattern
- No removal of redundant operations

**Improved**:
```python
def _compose_patterns(base_pattern, correction_pattern):
    # Strategy 1: Replace if correction is better
    if correction_fitness > base_fitness:
        return correction_pattern

    # Strategy 2: Try both orders
    option1 = base_pattern + correction_pattern
    option2 = correction_pattern + base_pattern

    # Strategy 3: Interleave
    option3 = interleave(base_pattern, correction_pattern)

    # Evaluate all and return best
    return best_of([option1, option2, option3])
```

**Expected Impact**: Find better ways to combine patterns

---

### **Improvement 4: Targeted Primitive Selection**

**Current**: Corrections can use any of 41 primitives

**Improved**:
```python
def _get_targeted_primitives(failures: List[FailureAnalysis]) -> List[str]:
    """Select primitives likely to fix specific failures"""

    if dominant_failure == 'partial_match' and avg_pixel_diff < 0.1:
        # Close to perfect: try subtle operations
        return ['fill_zeros', 'hollow', 'border', 'center',
                'color_inc', 'swap_01']

    elif dominant_failure == 'wrong_colors':
        # Color issues: focus on color operations
        return ['invert', 'swap_01', 'color_inc', 'fill_zeros',
                'remove_bg', 'isolate_1', 'isolate_2']

    elif dominant_failure == 'wrong_size':
        # Size issues: scaling and cropping
        return ['scale_2x', 'scale_3x', 'crop', 'pad_1',
                'downsample', 'extend_edges']

    else:
        # Shape issues: geometric transforms
        return ['rotate_90', 'rotate_180', 'rotate_270',
                'flip_h', 'flip_v', 'transpose', 'diagonal_flip']
```

**Expected Impact**: Corrections use relevant primitives, not random ones

---

## Implementation Plan

### Phase 1: Quick Fixes (30 minutes)

1. ✅ Use fuzzy fitness in `_evaluate_pattern` (CRITICAL)
2. Seed correction population with current pattern
3. Test on same 10 tasks

**Expected**: Some improvements detected (0.88 → 0.91)

### Phase 2: Composition Strategies (1 hour)

4. Implement multiple composition strategies
5. Evaluate all combinations
6. Keep best

**Expected**: Better pattern combinations

### Phase 3: Targeted Primitives (1 hour)

7. Implement primitive filtering by failure type
8. Pass filtered list to correction solver
9. Test on tasks with specific failure types

**Expected**: More relevant corrections

---

## Testing Strategy

### Test Set 1: High-Fitness Tasks (85-95%)
From our 10-task test, these are close to perfect:
- Task 135a2760: 96.26% (partial_match, 1.74% diff)
- Task 16b78196: 88.83% (partial_match, 9.17% diff)
- Task 142ca369: 88.29% (partial_match, 9.71% diff)
- Task 1818057f: 88.41% (partial_match, 9.59% diff)
- Task 16de56c4: 85.91% (partial_match, 12.09% diff)

**Expected**: TRM should refine at least 1-2 of these to 100%

### Test Set 2: Medium-Fitness Tasks (50-85%)
- Task 0692e18c: 78.7%
- Task 03560426: 79.7%

**Expected**: Incremental improvements (75% → 80-85%)

---

## Success Criteria

### Minimum Success (v0.85)
- 1/5 high-fitness tasks refined to 100%
- 3/5 high-fitness tasks show improvement (>2% gain)
- Average improvement: +5-10% on high-fitness tasks

### Good Success (v0.86)
- 2-3/5 high-fitness tasks refined to 100%
- All 5 high-fitness tasks show improvement
- Average improvement: +10-15%

### Breakthrough (v0.87+)
- 4-5/5 high-fitness tasks refined to 100%
- Consistent refinement on 50-task set
- 3-5% exact match accuracy on full evaluation

---

## Next Steps

1. **Immediate**: Implement Phase 1 (use fuzzy fitness in evaluation)
2. **Short-term**: Implement Phase 2 (composition strategies)
3. **Medium-term**: Implement Phase 3 (targeted primitives)
4. **Long-term**: Full 50-task and 400-task evaluations

---

*Plan Date: 2025-10-16*
*Status: Ready for implementation*
*Expected Time: 2-3 hours*
*Expected Impact: Enable refinement of 85-95% solutions to 100%*
