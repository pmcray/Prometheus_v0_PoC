# v0.94 Workplan: Adaptive Constraint Learning

**Created**: 2025-10-18
**Status**: 📋 Design Phase
**Goal**: Achieve 15-20% solve rate through meta-learning on constraints

---

## 🎯 **Vision**

v0.94 will learn from constraint extraction patterns across tasks to **adaptively refine filtering**. Instead of fixed filter rules, the system learns which primitives work best for each constraint combination.

**Key Innovation**: Meta-learning layer that tracks constraint→primitive→success mappings and uses this knowledge to improve filtering on new tasks.

---

## 📊 **Expected Performance**

| Metric | v0.91 | v0.92 | v0.93 | **v0.94 (Target)** |
|--------|-------|-------|-------|-------------------|
| Solve Rate | 0% | 5-10% | 10-15% | **15-20%** |
| Search Space | 79M | 79M | 100K | **10K-50K** |
| Time per Task | 60s | 10s | 2-5s | **2-8s** |
| Constraint Usage | No | No | Fixed rules | **Adaptive learning** |
| Meta-Learning | No | No | No | **Yes** |

---

## 🔬 **Three Design Options**

### **Option A: Meta-Learning on Constraints** ⭐ **RECOMMENDED**
Learn which primitives work for each constraint pattern.

**Approach**:
1. Track constraint→primitive→fitness mappings
2. Build "success patterns" database
3. Use historical data to refine filtering
4. Adapt strictness based on confidence

**Advantages**:
- Builds on v0.93's constraint system
- Learns from experience (gets better over time)
- Can discover non-obvious patterns
- Low implementation risk (extends existing code)

**Implementation Complexity**: Medium (2-3 days)

---

### **Option B: Hierarchical Decomposition**
Break complex patterns into sub-patterns, solve incrementally.

**Approach**:
1. Identify "sub-goals" (color→shape→position)
2. Solve each sub-goal independently
3. Compose solutions hierarchically
4. Backtrack if composition fails

**Advantages**:
- Better on complex tasks
- Interpretable (shows reasoning steps)
- Handles multi-step transformations

**Challenges**:
- Requires sub-goal detection logic
- Composition may not be obvious
- Higher implementation complexity

**Implementation Complexity**: High (4-5 days)

---

### **Option C: Ensemble Methods**
Run multiple strategies in parallel, select best.

**Approach**:
1. Run v0.92 and v0.93 simultaneously
2. Take best result
3. Optional: weighted voting on fitness

**Advantages**:
- Simple to implement
- Guaranteed ≥ max(v0.92, v0.93)
- Low risk

**Challenges**:
- 2x computational cost
- Doesn't learn or improve
- Ceiling at best single method + 2-3%

**Implementation Complexity**: Low (1 day)

---

## ⭐ **Recommended: Option A - Meta-Learning**

Based on v0.92/v0.93 design, Option A is the most promising path forward.

### **Why Meta-Learning**

1. **Natural Extension** - Builds on v0.93's constraint system
2. **Gets Better Over Time** - Learns from each task attempted
3. **Discovers Patterns** - May find non-obvious constraint→primitive correlations
4. **Scalable** - Database grows with usage
5. **Proven Approach** - Similar to TRM's meta-learning success

---

## 🏗️ **v0.94 Architecture**

### **New Components**

```python
class ConstraintMetaLearner:
    """
    Learns which primitives work best for each constraint pattern.

    Tracks:
    - constraint_pattern → primitive → success_rate
    - constraint_pattern → primitive_sequence → fitness
    - task_similarity → constraint_mapping
    """

    def __init__(self):
        self.success_db = {}  # {constraint_hash: {primitive: (successes, total)}}
        self.pattern_db = {}  # {constraint_hash: [(pattern, fitness)]}

    def record_attempt(self, constraints, pattern, fitness):
        """Record pattern attempt with fitness for given constraints."""
        pass

    def get_refined_filter(self, constraints, mode='adaptive'):
        """
        Get refined primitive filter based on historical success.

        Returns:
            - prioritized: Primitives with high success rate
            - allowed: Primitives with moderate success
            - exploration: Random primitives for discovery
        """
        pass

    def get_similar_tasks(self, constraints, top_k=5):
        """Find k most similar previously-seen tasks."""
        pass
```

### **Integration with v0.93**

```python
class PrometheusARC_v094_MetaLearning(PrometheusARC_v093_Constraints):
    """v0.94: Adaptive constraint learning."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Load historical database
        self.meta_learner = ConstraintMetaLearner()
        self.meta_learner.load_database('arc_learned_patterns.json')

    def solve_task(self, train_examples, test_examples, task_id):
        # Extract constraints (same as v0.93)
        constraints = self.constraint_extractor.extract_all_constraints(task)

        # Get refined filter using meta-learning
        refined_filter = self.meta_learner.get_refined_filter(
            constraints,
            mode='adaptive'
        )

        # Try with refined filter first
        result = self._try_with_filter(refined_filter, train_examples, ...)

        # Record attempt for future learning
        self.meta_learner.record_attempt(
            constraints,
            result['pattern'],
            result['fitness']
        )

        # Fall back to v0.93 if needed
        if result['fitness'] < 0.95:
            result = super().solve_task(train_examples, test_examples, task_id)

        # Save learned patterns
        self.meta_learner.save_database('arc_learned_patterns.json')

        return result
```

---

## 📝 **Implementation Plan**

### **Phase 1: Meta-Learning Core** (4-6 hours)

**Files to create**:
- `arc_meta_learner.py` - ConstraintMetaLearner class
- `arc_learned_patterns.json` - Pattern database (initially empty)

**Components**:
1. **Success Tracking**
   ```python
   def record_attempt(self, constraints, pattern, fitness):
       constraint_hash = self._hash_constraints(constraints)

       if constraint_hash not in self.success_db:
           self.success_db[constraint_hash] = {}

       for prim in pattern:
           if prim not in self.success_db[constraint_hash]:
               self.success_db[constraint_hash][prim] = {'successes': 0, 'total': 0}

           self.success_db[constraint_hash][prim]['total'] += 1
           if fitness >= 0.95:
               self.success_db[constraint_hash][prim]['successes'] += 1
   ```

2. **Refined Filtering**
   ```python
   def get_refined_filter(self, constraints, mode='adaptive'):
       constraint_hash = self._hash_constraints(constraints)

       if constraint_hash not in self.success_db:
           # No historical data, use v0.93 filter
           return self.primitive_filter.filter_by_constraints(constraints, mode='soft')

       # Calculate success rates
       success_rates = {}
       for prim, stats in self.success_db[constraint_hash].items():
           if stats['total'] >= 3:  # Require 3+ attempts for confidence
               success_rates[prim] = stats['successes'] / stats['total']

       # Prioritize by success rate
       prioritized = [p for p, rate in sorted(success_rates.items(),
                                              key=lambda x: x[1],
                                              reverse=True) if rate >= 0.3]

       # Include v0.93 filter as fallback
       v093_filter = self.primitive_filter.filter_by_constraints(constraints, mode='soft')

       # Combine: prioritized + v093_filter (unique)
       combined = prioritized + [p for p in v093_filter if p not in prioritized]

       return combined[:15]  # Top 15 primitives
   ```

3. **Task Similarity**
   ```python
   def get_similar_tasks(self, constraints, top_k=5):
       """Find similar tasks using constraint similarity."""
       distances = []
       for seen_hash, data in self.success_db.items():
           similarity = self._constraint_similarity(constraints, seen_hash)
           distances.append((seen_hash, similarity, data))

       # Return top-k most similar
       return sorted(distances, key=lambda x: x[1], reverse=True)[:top_k]
   ```

### **Phase 2: Integration with v0.93** (2-3 hours)

**File to create**:
- `prometheus_arc_v094_metalearning.py` (extends v0.93)

**Integration points**:
1. Load meta-learner at initialization
2. Use refined filter instead of fixed v0.93 filter
3. Record all attempts (success or failure)
4. Save database after each task
5. Fall back to v0.93 if no historical data

### **Phase 3: Bootstrap Learning** (1-2 hours)

**Strategy**: Pre-populate database with v0.93 results

```python
def bootstrap_from_v093_results(results_file):
    """
    Initialize meta-learner from v0.93 benchmark results.

    Args:
        results_file: JSON file with v0.93 results (constraints, patterns, fitness)
    """
    with open(results_file) as f:
        results = json.load(f)

    meta_learner = ConstraintMetaLearner()

    for task_result in results['results']:
        constraints = task_result['constraints']
        pattern = task_result['pattern']
        fitness = task_result['fitness']

        meta_learner.record_attempt(constraints, pattern, fitness)

    meta_learner.save_database('arc_learned_patterns.json')
    print(f"Bootstrapped with {len(results['results'])} tasks")
```

### **Phase 4: Testing & Validation** (2-3 hours)

**Tests to create**:
1. `test_meta_learning.py` - Unit tests for ConstraintMetaLearner
2. `test_v094_integration.py` - Integration with v0.93
3. Benchmark on 10 tasks (compare to v0.93)
4. Benchmark on 50 tasks (if promising)

---

## 🎯 **Success Metrics**

### **Phase 1: Meta-Learning Core**
- ✅ ConstraintMetaLearner class implemented
- ✅ Success tracking working
- ✅ Refined filtering produces sensible results
- ✅ Database save/load functional

### **Phase 2: Integration**
- ✅ v0.94 extends v0.93 correctly
- ✅ Meta-learner called at right points
- ✅ Fallback to v0.93 when no data
- ✅ Database grows with usage

### **Phase 3: Performance**
- ✅ **10-task benchmark**: Solve rate > v0.93
- ✅ **50-task benchmark**: Solve rate 15-20%
- ✅ **Learning curve**: Performance improves with more tasks
- ✅ **Speed**: ≤ v0.93 time per task

---

## 📊 **Decision Tree**

```
After v0.92/v0.93 results:

IF v0.93 >> v0.92 (e.g., 15% vs 5%):
    → Implement Option A (meta-learning)
    → Constraint-based approach is working!

ELSE IF v0.93 ≈ v0.92 (e.g., both 5-8%):
    → Consider Option B (hierarchical)
    → May need different approach

ELSE IF v0.93 < v0.92:
    → Debug v0.93 constraint filtering
    → May be over-filtering correct primitives
    → Consider Option C (ensemble) as fallback
```

---

## 🔍 **Alternative Improvements**

If meta-learning doesn't achieve 15-20%, consider:

### **1. Primitive Synthesis**
- Automatically combine primitives into "macros"
- Learn frequently-used sequences
- Example: `['rotate_90', 'flip_h']` → `rotate_and_flip`

### **2. Active Learning**
- Identify "uncertain" tasks where multiple strategies disagree
- Focus learning on hard cases
- Adaptive sampling

### **3. Transfer Learning**
- Learn patterns from training set
- Apply to evaluation set
- Requires training/eval split strategy

### **4. Hybrid Symbolic-Neural**
- Use small neural net for primitive selection
- Symbolic execution for pattern application
- Best of both worlds

---

## 📁 **File Structure**

```
prometheus_arc_v094_metalearning.py    (main implementation, 800-1000 lines)
arc_meta_learner.py                    (meta-learning core, 400-500 lines)
arc_learned_patterns.json              (database, grows with usage)
test_meta_learning.py                  (unit tests, 300 lines)
test_v094_integration.py               (integration tests, 200 lines)
V0_94_WORKPLAN.md                      (this file)
V0_94_IMPLEMENTATION_COMPLETE.md       (after implementation)
```

---

## ⏱️ **Time Estimates**

| Phase | Optimistic | Realistic | Pessimistic |
|-------|-----------|-----------|-------------|
| Meta-Learning Core | 4h | 6h | 8h |
| Integration | 2h | 3h | 4h |
| Bootstrap Learning | 1h | 2h | 3h |
| Testing & Validation | 2h | 3h | 5h |
| **Total** | **9h** | **14h** | **20h** |

**Realistic estimate**: 2 sessions of 6-7 hours each

---

## 🚀 **Getting Started**

### **Step 1: Analyze v0.92/v0.93 Results**
```bash
# Wait for tests to complete
cat arc_v092_5tasks.log | grep "RESULTS"
cat arc_v093_5tasks.log | grep "RESULTS"

# Compare solve rates
python3 compare_v092_v093.py
```

### **Step 2: Make Decision**
- If v0.93 >> v0.92: Proceed with v0.94 meta-learning
- Otherwise: Re-evaluate approach

### **Step 3: Start Implementation**
```bash
# Create meta-learner core
touch arc_meta_learner.py
touch arc_learned_patterns.json

# Implement ConstraintMetaLearner class
# (Follow Phase 1 implementation plan)
```

---

## 💡 **Key Design Principles**

1. **Learn from Everything** - Record all attempts, not just successes
2. **Start Conservative** - Fall back to v0.93 when uncertain
3. **Grow Over Time** - Database improves with more tasks
4. **Interpretable** - Track why each primitive was chosen
5. **Fail Gracefully** - Never worse than v0.93 baseline

---

## 🎓 **References & Inspiration**

- **TRM (Tiny Recursive Models)**: Meta-learning on program synthesis (45% ARC solve rate)
- **DreamCoder**: Learning library of primitives through experience
- **AlphaCode**: Learning from previous solutions
- **Our v0.93**: Constraint extraction as foundation for learning

---

**Status**: Ready to implement after v0.92/v0.93 results
**Confidence**: High (builds on working v0.93 foundation)
**Risk**: Low (graceful fallback to v0.93)
**Expected Outcome**: 15-20% solve rate with learning curve
