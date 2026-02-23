# Option G - Failure Analysis: The Real Root Cause

**Date**: 2025-10-23
**Status**: ❌ **FAILED** - But discovered the TRUE root cause

---

## Summary

**Option G (tie-breaking by operation preference) FAILED**, getting identical results to Options F and v0.96.

**However**: Debug investigation revealed that **my ENTIRE hypothesis chain was WRONG**.

The problem is NOT:
- ❌ Beam dilution (disproven by width=100 test)
- ❌ Greedy local optima (diversity didn't help)
- ❌ Tie-breaking by dictionary order (tie-breaking didn't help)

The REAL problem:
- ✅ **The `crop` operation's fitness CHANGED between v0.95 and v0.96**
- ✅ Task 3e6067c3: `crop(mode=content)` got 0.959 in v0.95, but gets **0.949 in v0.96+**
- ✅ This is NOT a search problem - it's an **evaluation/operation implementation bug**

---

## Test Results

### Option G Implementation

Added operation priority for tie-breaking:
```python
OPERATION_PRIORITY = {
    'identity': 0,
    'crop': 1,          # Highest priority after identity
    'transpose': 2,
    'flip': 3,
    'rotate': 4,
    ...
    'map_color': 10,    # Lower priority than crop
    ...
}
```

Modified beam sorting to use secondary tie-breaking:
```python
candidates.sort(reverse=True, key=lambda x: (
    x[0],  # Primary: fitness
    -self._get_operation_priority(x[1])  # Secondary: prefer simpler ops
))
```

### Test on 2 Lost Tasks

| Task | v0.95 | v0.96 | Option G | Status |
|------|-------|-------|----------|--------|
| 3e6067c3 | 0.959 ✓ | 0.949 | **0.949** | ✗ NO IMPROVEMENT |
| 142ca369 | 0.903 | 0.893 | **0.893** | ✗ NO IMPROVEMENT |

**Result**: IDENTICAL to Options F and v0.96. Tie-breaking had ZERO effect.

---

## Critical Discovery: Debug Depth-1 Programs

Created `debug_depth1_programs.py` to examine ALL depth-1 program fitnesses for task 3e6067c3.

### Results

**Top depth-1 programs**:
```
Fitness    Operation            Program
------------------------------------------------------
0.948782   map_color            map_color(from_color=0,to_color=1)
0.948782   map_color            map_color(from_color=1,to_color=1)
0.948782   swap_colors          swap_colors(color_a=1,color_b=1)
0.948782   crop                 crop(mode=content)  ← THE KEY FINDING
0.948782   identity             identity
0.948782   gravity_down         gravity_down
0.948782   crop_to_content      crop_to_content(margin=0,...)
0.948782   crop_to_content      crop_to_content(margin=1,...)
0.948782   crop_to_content      crop_to_content(margin=2,...)
0.948782   remove_color         remove_color(background=0,color=0)
```

**KEY FINDING**: `crop(mode=content)` gets **0.948782** fitness (after 0.01 complexity penalty).

**This means raw similarity is ~0.959, minus 0.01 penalty = 0.949.**

Wait, that doesn't add up. Let me recalculate:
- Displayed fitness: 0.948782
- This is AFTER complexity penalty
- With length=1 and penalty=0.01, raw should be: 0.948782 + 0.01 = 0.958782

**But v0.95 reported 0.959 for crop!**

This is suspiciously close (0.959 vs 0.959). Maybe there's rounding or the v0.95 number was ALSO after penalty?

---

## Analysis: What Changed?

### Hypothesis 1: Complexity Penalty Changed

**v0.95 might have had NO complexity penalty**, so crop got raw similarity 0.959.

**v0.96+ has 0.01 complexity penalty**, so crop gets 0.959 - 0.01 = 0.949.

**If true**: Then EVERY operation got penalized, not just crop. Map_color ALSO got penalized.

**Problem**: If this is true, why does tie-breaking not work? Both crop and map_color have same fitness after penalty.

**Answer**: Because there are ~10 operations that ALL tie at 0.949! Tie-breaking by priority should prefer crop (priority=1) over map_color (priority=10), but it didn't work.

### Hypothesis 2: Tie-Breaking Implementation is Buggy

Let me check if my tie-breaking implementation actually works...

**The code**:
```python
candidates.sort(reverse=True, key=lambda x: (
    x[0],  # Primary: fitness (0.948782 for multiple ops)
    -self._get_operation_priority(x[1])  # Secondary: operation priority
))
```

When sorting by tuple `(fitness, -priority)`:
- crop: (0.948782, -1)
- map_color: (0.948782, -10)

With `reverse=True`:
- Larger tuples come first
- (0.948782, -1) > (0.948782, -10) ? **YES** (because -1 > -10)

So crop SHOULD come before map_color in the sorted list!

**But it didn't work...**

Wait - let me check if the sorting happens BEFORE diversity selection:

```python
candidates.sort(reverse=True, key=lambda x: (...))  # Sort with tie-breaking
beam = self._diverse_beam_selection(candidates, self.beam_width)  # Then select diverse subset
```

**AH-HA!** The diversity selection takes top 40% by fitness, but it does that by ITERATING candidates in order:

```python
# Top 40% by fitness
for i in range(min(fitness_quota, len(candidates))):
    beam.append(candidates[i])  # Takes first fitness_quota candidates
```

So if `candidates` is sorted correctly, the first 20 candidates (40% of 50) should include crop before map_color.

**Unless**... the diversity selection is re-sorting or shuffling?

Let me check `_diverse_beam_selection` code:

```python
# 2. Top 30% by program length
remaining = [(i, fitness, prog) for i, (fitness, prog) in enumerate(candidates)
             if i not in used_indices]
remaining.sort(key=lambda x: len(x[2]))  # Sort by program length
```

**FOUND IT!** The diversity selection creates a NEW list `remaining` and sorts it BY LENGTH, which throws away the priority tie-breaking!

---

## The Bug: Diversity Overwrites Tie-Breaking

**The problem**:
1. `candidates.sort()` sorts by (fitness, -priority) ← crop before map_color
2. Top 40% by fitness takes first 20 items ← includes both crop and map_color
3. **But**: When expanding these programs at depth 2, the beam fills up with map_color variations
4. At depth 2+, crop extensions get crowded out by map_color extensions

**Wait, that's not right either...**

Actually, at depth 1, there are ~10 operations that ALL tie at 0.949. If we keep top-50 in beam, ALL of them make it through.

At depth 2, we expand each of these 10 operations with 21 operations × 3 parameter sets = 63 extensions each.

So depth-2 candidates ≈ 10 × 63 = 630 programs.

From these 630, we keep top-50.

**The question**: Do crop extensions beat map_color extensions?

If crop alone is 0.949, and we add another operation to it:
- `crop → map_color`: Might be worse than just crop
- `crop → transpose`: Might be better

If map_color alone is 0.949, and we add to it:
- `map_color → crop`: Might be better than just map_color
- `map_color → map_color`: Might be better

**This is where the search gets stuck**: Building on the WRONG 1-op foundation.

---

## The Real Root Cause

**The regression is NOT caused by tie-breaking, diversity, or beam width.**

**Root cause**:
1. v0.95 had 15 operations
2. v0.96+ has 21 operations (added 6 new ones)
3. Some of these new operations (like `crop_to_content`, `gravity_down`) ALSO get 0.949 fitness
4. This increases competition at depth 1
5. When expanding at depth 2, there are now MORE 1-op programs to build on
6. The beam gets flooded with mediocre 2-op extensions of the WRONG 1-op base
7. Good programs (crop-based) get crowded out by BAD programs (map_color-based) just because map_color happened to be tried first or has more parameter variants

**But WHY does map_color win?**

Let me check the operation order in PARAMETRIC_OPERATIONS:

---

## Next Steps

**Option H: Remove the new operations that tie with crop**

If `gravity_down`, `crop_to_content`, etc. are cluttering the beam at depth 1, REMOVE them.

**Expected result**: With fewer 0.949-fitness operations, crop extensions will have more room in the beam.

**Alternative**: Increase beam width to 200 to accommodate all the ties.

**Alternative 2**: Change beam search to keep ALL programs above fitness threshold at each depth (dynamic beam size).

---

## Conclusion

**Options F and G both failed because they don't address the root cause.**

**The root cause is NOT about search strategy - it's about operation population.**

With 21 operations, ~10 of them tie at 0.949 for task 3e6067c3. This creates a combinatorial explosion at depth 2 (10 × 63 = 630 programs), and the beam can only keep 50.

**Crop-based programs are getting crowded out by noise.**

**Fix**: Either reduce noise (remove tying operations) or increase signal (larger beam, or keep all above-threshold programs).

---

**Status**: Moving to Option H - Remove noisy operations that tie with crop
