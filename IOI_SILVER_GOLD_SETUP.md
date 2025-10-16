# IOI Silver/Gold Benchmarking Setup

**Date**: 2025-10-16
**Current**: Bronze 63.3% (19/30) ✅
**Next Target**: Silver 30-50%, Gold 10-30%

---

## Bronze Results Summary

**PHI-3-Mini Full Benchmark**: **19/30 (63.3%)** - **TARGET MET** ✅

**By Difficulty**:
- Easy: 4/10 (40%)
- Medium: 11/14 (79%)
- Medium-Hard: 1/2 (50%)
- Hard: 3/4 (75%)

**Key Finding**: Phi-3 excels on Medium/Hard but struggles with Easy
- **Paradox**: 75% on Hard, 40% on Easy
- **Root Cause**: Verbosity - Easy problems truncated, Hard have canonical solutions

---

## IOI Competition Structure

### Difficulty Levels

| Level | Typical Topics | Expected Phi-3 Performance |
|-------|---------------|---------------------------|
| **Bronze** | Arrays, strings, simulation | **63% (proven)** |
| **Silver** | Sorting, prefix sums, two pointers, greedy | **30-50% (estimate)** |
| **Gold** | Dynamic programming, graphs, BFS/DFS | **10-30% (estimate)** |
| **Platinum** | Advanced DP, segment trees, flows | **<10% (unlikely)** |

### Problem Sources

1. **USACO (USA Computing Olympiad)**
   - Bronze: Basic algorithms (have 30 problems ✅)
   - Silver: Intermediate algorithms (need to source)
   - Gold: Advanced algorithms (need to source)
   - Platinum: Expert level

2. **Codeforces**
   - Div 2 A/B: ~Bronze level
   - Div 2 C/D: ~Silver level
   - Div 2 E/Div 1 A/B: ~Gold level

3. **AtCoder**
   - ABC A/B/C: ~Bronze level
   - ABC D/E: ~Silver level
   - ABC F/ARC C/D: ~Gold level

---

## Silver Level Setup

### Topics to Cover

**Core Silver Topics** (USACO):
1. **Sorting & Comparators**
   - Custom sorting (by multiple keys)
   - Sorting with ties
   - Coordinate compression

2. **Prefix Sums**
   - 1D and 2D prefix sums
   - Range queries
   - Subarray sums

3. **Two Pointers**
   - Sliding window
   - Meet-in-the-middle
   - Subarray counting

4. **Greedy Algorithms**
   - Interval scheduling
   - Activity selection
   - Huffman coding

5. **Binary Search**
   - Binary search on answer
   - Lower/upper bound
   - Ternary search

### Recommended Problem Set (20-30 problems)

**Easy Silver** (5-10 problems):
- Sorting with custom comparator
- Basic prefix sums
- Simple two pointers
- Greedy coin change
- Binary search in sorted array

**Medium Silver** (10-15 problems):
- 2D prefix sums
- Sliding window maximum
- Interval scheduling
- Binary search on answer
- Coordinate compression

**Hard Silver** (5 problems):
- Complex greedy
- Multi-dimensional sorting
- Advanced two pointers
- Ternary search

---

## Gold Level Setup

### Topics to Cover

**Core Gold Topics** (USACO):
1. **Dynamic Programming**
   - Knapsack (0/1, unbounded)
   - LIS (Longest Increasing Subsequence)
   - LCS (Longest Common Subsequence)
   - Subset DP
   - Bitmask DP

2. **Graph Algorithms**
   - BFS/DFS
   - Shortest paths (Dijkstra, Floyd-Warshall)
   - Topological sort
   - Minimum spanning tree (Prim, Kruskal)
   - Strongly connected components

3. **Trees**
   - Tree traversal
   - Tree DP
   - Lowest common ancestor (LCA)
   - Binary lifting

4. **Advanced Greedy**
   - Sweep line
   - Event-based algorithms

### Recommended Problem Set (15-20 problems)

**Easy Gold** (5 problems):
- Basic DP (knapsack, LIS, LCS)
- BFS/DFS on grid
- Simple Dijkstra

**Medium Gold** (8-10 problems):
- Tree DP
- Topological sort
- MST (Kruskal/Prim)
- Subset DP
- Bitmask DP

**Hard Gold** (2-5 problems):
- Complex graph problems
- Advanced DP
- Multiple algorithms combined

---

## Implementation Plan

### Phase 1: Source Problems (1-2 hours)

**Option A**: USACO Archive
```python
# Scrape USACO problems
# http://www.usaco.org/index.php?page=contests
# Filter by Silver/Gold division
```

**Option B**: Codeforces API
```python
import requests
# Get Div 2 C/D problems (Silver level)
# Get Div 2 E / Div 1 A/B (Gold level)
# Filter by tags (dp, graphs, greedy, etc.)
```

**Option C**: AtCoder Problems
```python
# Use AtCoder Problems API
# https://kenkoooo.com/atcoder/
# ABC D/E for Silver
# ABC F / ARC C/D for Gold
```

**Option D**: Curated List (FASTEST)
```python
# Use existing competitive programming resources
# E.g., CSES Problem Set, Kattis, LeetCode Hard
```

### Phase 2: Adapt Synthesizer (30 minutes)

Update `ioi_synthesizer_local.py` to handle harder problems:

```python
class IOISilverSynthesizer(IOIBronzeSynthesizer):
    def __init__(self, model_path):
        super().__init__(model_path)
        self.max_tokens = 12288  # Longer for complex problems
        self.difficulty = "Silver"

    def _create_prompt(self, problem_desc):
        return f"""USACO Silver Problem:
{problem_desc}

Requirements:
- Optimal time complexity (O(n log n) or better)
- Use advanced algorithms (sorting, prefix sums, binary search, greedy)
- Handle edge cases
- Competitive programming format (stdin/stdout)

Write complete, efficient Python solution:

```python
"""
```

### Phase 3: Run Benchmarks (2-3 hours each)

**Silver Benchmark**:
```bash
python3 benchmark_ioi_silver.py 2>&1 | tee ioi_silver_results.log
```

**Expected Results**:
- Easy Silver: 60-80% (similar to Bronze Medium)
- Medium Silver: 30-50% (main challenge)
- Hard Silver: 10-30% (stretch goal)
- **Overall**: 30-50% (10-15/30 problems)

**Gold Benchmark**:
```bash
python3 benchmark_ioi_gold.py 2>&1 | tee ioi_gold_results.log
```

**Expected Results**:
- Easy Gold: 30-50% (DP basics, simple graphs)
- Medium Gold: 10-30% (complex DP, advanced graphs)
- Hard Gold: 0-10% (likely too hard)
- **Overall**: 10-30% (3-9/30 problems)

---

## Success Criteria

### Silver

**Minimum Success**:
- 8-10/30 problems solved (27-33%)
- Demonstrates improvement over Bronze difficulty

**Good Success**:
- 12-15/30 problems solved (40-50%)
- Competitive with GPT-3.5 level

**Breakthrough**:
- 18-20/30 problems solved (60-67%)
- Matches or exceeds Bronze performance

### Gold

**Minimum Success**:
- 3-5/30 problems solved (10-17%)
- Shows capability on complex algorithms

**Good Success**:
- 6-9/30 problems solved (20-30%)
- Competitive with specialized code models

**Breakthrough**:
- 10-15/30 problems solved (33-50%)
- Approaches expert-level performance

---

## Quick Start (Recommended)

### Immediate Action (30 minutes)

1. **Use CSES Problem Set** (easiest to integrate)
   - 300+ problems with solutions
   - Well-organized by topic
   - Clear difficulty progression

2. **Create `benchmark_ioi_silver.py`**
   - Copy from `benchmark_phi3_30problems.py`
   - Update problem set to CSES Silver-level
   - Adjust expected performance metrics

3. **Run on 10 problems first**
   - Test Phi-3 performance
   - Validate setup
   - Estimate full benchmark time

### Follow-Up (if promising)

4. **Full 30-problem benchmark**
5. **Analyze failures**
6. **Optimize prompts if needed**
7. **Proceed to Gold if Silver >30%**

---

## Files to Create

1. **`benchmark_ioi_silver.py`** - Silver benchmark script
2. **`benchmark_ioi_gold.py`** - Gold benchmark script
3. **`ioi_silver_problems.json`** - Silver problem set
4. **`ioi_gold_problems.json`** - Gold problem set
5. **`IOI_SILVER_RESULTS.md`** - Silver results analysis
6. **`IOI_GOLD_RESULTS.md`** - Gold results analysis

---

## Alternative: Use Existing Benchmarks

### LeetCode

**Bronze Level**: Easy problems
**Silver Level**: Medium problems (arrays, strings, greedy)
**Gold Level**: Medium problems (DP, graphs) + some Hard

**Advantage**: Well-tested, large problem set, clear difficulty
**Disadvantage**: Not competitive programming format

### HumanEval / APPS Benchmark

Already established code generation benchmarks
- HumanEval: 164 problems, function-level
- APPS: 10,000 problems, various difficulties

**Advantage**: Standard benchmark, easy comparison
**Disadvantage**: Not IOI-specific

---

## Recommendation

**Fastest Path**: Use **CSES Problem Set** for Silver/Gold

**Why**:
1. ✅ Well-organized by topic
2. ✅ Clear difficulty levels
3. ✅ Solutions available for validation
4. ✅ Competitive programming format
5. ✅ Free and accessible

**Setup Time**: ~1 hour
**Benchmark Time**: 2-3 hours per level
**Expected Results**: Validated within 4-5 hours

---

*Setup Date: 2025-10-16*
*Status: Ready for implementation*
*Next Step: Create benchmark_ioi_silver.py*
*Expected Time to Results: 4-5 hours*
