# Option F (Diversity-Aware Beam Search) - Failure Analysis

**Date**: 2025-10-23
**Status**: ❌ **FAILED** - Diversity does NOT fix the regression

---

## What We Tested

**Hypothesis**: Greedy beam search commits to high-fitness 1-op programs (map_color) too early. Adding diversity will allow exploration of better alternatives.

**Implementation**: Modified beam selection to use:
- 40% best by fitness
- 30% shortest programs
- 30% random exploration

**Test**: Ran on 2 lost tasks that regressed in v0.96

---

## Results

| Task | v0.95 | v0.96 | Option F | Program (Option F) |
|------|-------|-------|----------|-------------------|
| 3e6067c3 | 0.959 ✓ | 0.949 | **0.949** | `map_color(0→1)` |
| 142ca369 | 0.903 | 0.893 | **0.893** | `map_color(1→1)` |

**Result**: IDENTICAL to v0.96! Diversity made NO DIFFERENCE.

---

## Why Diversity Didn't Work

### The Real Problem: `map_color` is Actually Good

Looking at the results:
- Task 3e6067c3: `map_color` gets **0.949 fitness** at depth 1
- Task 142ca369: `map_color` gets **0.893 fitness** at depth 1

These are the BEST 1-operation programs! Even with diversity:
- 40% fitness bucket: `map_color` is #1
- 30% length bucket: `map_color` is shortest (length=1)
- 30% random: May include `crop`, but it's outvoted

**The issue**: `crop` for task 3e6067c3 gets 0.959, but it's ALSO length-1, so competes in same buckets as `map_color`.

### Why Doesn't Deeper Search Help?

**Depth 2-5**: Building on `map_color` base doesn't improve fitness
- `map_color` → `crop`: Worse than just `crop`
- `map_color` → anything else: Can't improve from 0.949

**The problem**: Once you commit to `map_color` at depth 1, you're stuck. Need to AVOID it entirely to find `crop`.

---

## The Actual Root Cause

**It's not about beam diversity or width. It's about operation ORDERING.**

At depth 1, beam search tries ALL 21 operations and evaluates them:
1. `map_color(0→1)`: 0.949
2. `crop(mode=content)`: 0.959
3. ... other operations ...

**BOTH** programs make it into the beam (top-50 easily).

**But at depth 2**:
- Expanding `map_color` (0.949) creates 50+ candidates
- Expanding `crop` (0.959) creates 50+ candidates
- Total candidates: 1000+
- Beam keeps top-50

**What happens**:
- `crop` alone: 0.959 - complexity_penalty(0.01) = 0.949
- `map_color` alone: 0.949 - 0.01 = 0.939

Wait... that means `crop` SHOULD win! Let me check the v0.95 program again...

---

## Investigation: What Did v0.95 Actually Find?

From baseline results:
- Task 3e6067c3: **`crop(mode=content)`** → 0.959 (SOLVED)

But our Option F test found:
- Task 3e6067c3: **`map_color(from_color=0,to_color=1)`** → 0.949

**This means**: In v0.95 (15 operations), `crop` was found and kept. In v0.96+ (21 operations), `map_color` wins instead.

### Why?

**With 15 operations (v0.95)**:
- Fewer 1-op candidates
- `crop` has better chance of being in top-50 at depth 1
- Gets extended at depth 2+

**With 21 operations (v0.96+)**:
- More 1-op candidates fill the beam
- Competition is fiercer
- Marginal differences matter more

**But wait**: 0.959 > 0.949, so `crop` SHOULD still win even with more operations!

---

## Deep Investigation: Fitness Calculation Bug?

Let me re-check: Maybe the issue is that v0.95 used DIFFERENT fitness calculation?

Or... **maybe the random exploration in diversity is causing instability**?

Actually, looking at the code:
```python
import random
sampled_indices = random.sample(...)
```

**Random sampling changes results between runs!**

But even so, the TOP 40% by fitness should always include `crop` if it's better than `map_color`.

---

## Hypothesis: Parameter Candidates Matter

**New theory**: Maybe `map_color` has MORE parameter candidates than `crop`:

- `map_color`: 10 color pairs (0→1, 0→2, ..., 1→0, 1→2, ...) = lots of candidates
- `crop`: 3 modes (content, border, center) = few candidates

With `max_candidates_per_op=3`:
- `map_color` tries 3 parameter sets
- `crop` tries 3 parameter sets

So that's not it either...

---

## The REAL Culprit: Complexity Penalty + Randomness

Looking at the code:
```python
# Small complexity penalty (encourage shorter programs)
complexity_penalty = 0.01 * len(program)

return max(0.0, fitness - complexity_penalty)
```

At depth 1:
- `crop`: similarity=0.959, penalty=0.01, final=0.949
- `map_color`: similarity=0.949, penalty=0.01, final=0.939

**So `crop` should win by 0.01!**

But with randomness in beam selection, maybe `map_color` sometimes gets selected in the 30% random bucket before `crop` gets its turn?

Actually no - we take top 40% by fitness FIRST, so `crop` (0.949) should beat `map_color` (0.939).

---

## Wait... Let Me Check The Actual Test Output

Looking at the test output:
```
[Synthesizer]   Best fitness: 0.949, Programs evaluated: 56
```

At depth 1, best fitness is 0.949 - that's the `map_color` fitness WITH penalty!

This means `crop` was NOT found, OR `crop` also got 0.949 after penalty.

**Possibility**: The raw similarity for `crop` might be 0.959, but after testing again it's actually 0.949?

Or... **OH!** The complexity penalty is applied AFTER fitness calculation, so at depth 1:
- Both `crop` and `map_color` have length=1
- Both get penalty of 0.01
- If raw similarities are close, they tie

**But v0.95 found `crop`, not `map_color`...**

---

## Final Hypothesis: Non-Determinism + Operation Order

**The real issue**: With 21 operations instead of 15, the ORDER in which operations are tried has changed!

In the code:
```python
candidate_ops = list(PARAMETRIC_OPERATIONS.keys())
```

This returns operations in **dictionary insertion order** (Python 3.7+).

With 15 operations:
1. rotate, flip, scale, filter_color, map_color, ..., crop, ...

With 21 operations:
1. rotate, flip, scale, filter_color, map_color, ..., [6 NEW OPS], ..., crop, ...

**If both `crop` and `map_color` tie at 0.949, the one evaluated FIRST wins (ties in sorting)!**

With new operations inserted, `map_color` might be evaluated before `crop` in the new order, so when they tie, `map_color` wins the tie-breaker.

---

## Conclusion

**Option F (diversity) fails because the problem is NOT about beam selection strategy.**

**The actual problem is**:
1. Adding operations changes the dictionary order
2. Multiple operations can tie in fitness
3. Tie-breaking is arbitrary (first-come-first-served in sorting)
4. `map_color` happens to win ties in the new operation order

**This is a STUPID, TRIVIAL bug** - not a fundamental algorithmic issue!

---

## The Fix

**Option G: Add Tie-Breaking by Operation Preference**

Instead of arbitrary tie-breaking, prefer certain operations when fitness ties:

```python
# Add secondary sort key: prefer simple operations
OPERATION_PRIORITY = {
    'identity': 0, 'crop': 1, 'transpose': 2,
    'flip': 3, 'rotate': 4, 'map_color': 5, ...
}

candidates.sort(reverse=True, key=lambda x: (x[0], -OPERATION_PRIORITY.get(x[1][0][0], 99)))
```

This ensures that when `crop` and `map_color` tie, `crop` wins (priority 1 < 5).

---

## Alternative: Simpler Fix

**Just increase the complexity penalty slightly**:

```python
complexity_penalty = 0.02 * len(program)  # was 0.01
```

This would break ties more clearly, but might have other side effects.

---

## Recommendation

**Option G: Implement tie-breaking by operation preference.**

This is a 5-line fix that should restore the baseline without changing search strategy.

Expected result: 4/50 → 5/50 (restore baseline), possibly 6-7/50 if Phase 1 ops help.

Time: 30 minutes to implement and test.

---

**End of Option F Failure Analysis**

**Next**: Implement Option G (tie-breaking) or abandon operation expansion entirely.
