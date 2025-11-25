# Notebook Refactoring Guide

## Overview

This guide explains how to refactor the three Prometheus notebooks to use the professional `prometheus/` package instead of embedded code.

## Benefits of Refactoring

### Before Refactoring
- **Notebook 1**: ~1,378 lines (600+ lines of embedded classes)
- **Notebook 2**: ~1,400 lines (650+ lines of embedded classes)
- **Notebook 3**: ~1,500 lines (700+ lines of embedded classes)
- **Total**: ~4,300 lines

**Problems**:
- Code duplication across notebooks
- Hard to maintain (fix needs to be applied 3x)
- Mixes implementation with demonstration
- Difficult for clients to focus on the principles

### After Refactoring
- **Notebook 1**: ~400 lines (educational content + experiment logic)
- **Notebook 2**: ~420 lines (educational content + experiment logic)
- **Notebook 3**: ~450 lines (educational content + experiment logic)
- **Total**: ~1,270 lines

**Benefits**:
- ✅ 70% reduction in notebook length
- ✅ DRY principle: change once in `prometheus/`, benefit everywhere
- ✅ Clear focus on principles, not implementation
- ✅ Professional appearance for clients
- ✅ Easy to maintain and extend

---

## Refactoring Strategy

### Step 1: Update Setup Cell

**Before**:
```python
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from tensorflow import keras
# ... more imports
```

**After**:
```python
# Standard imports
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf

# Prometheus package imports
from prometheus.data.generators import PatternGenerator, ARCGenerator, TaskGenerator
from prometheus.models.architectures import StaticAgent, PrometheusAgent
from prometheus.training.loops import pretrain_model, online_train_model, print_performance_summary
from prometheus.visualization.plots import plot_performance_comparison, plot_training_progress
from prometheus.metrics.performance import summarize_experiment_results, compute_advantage_gap
from prometheus.safety.checks import GodelianSafetyGovernor  # For Notebook 3
```

### Step 2: Remove Embedded Generator Classes

**Notebook 1 - Before** (~200 lines):
```python
class HeavyPatternGenerator:
    def __init__(self, grid_size: int = 64, seed: int = 42):
        # ... 200 lines of implementation

    def _generate_horizontal_stripes(self):
        # ...

    def _generate_fractal_tree(self):
        # ...

    def generate_batch(self, n, distribution):
        # ...
```

**Notebook 1 - After** (~2 lines):
```python
# Initialize pattern generator
generator = PatternGenerator(grid_size=64, seed=42)
```

**Savings**: **198 lines removed**, replaced with 1 import + 1 initialization

### Step 3: Remove Embedded Model Architecture

**Before** (~250 lines):
```python
def residual_block(x, filters, kernel_size=3):
    # ... 20 lines

class StaticHeavyAgent:
    def __init__(self, grid_size, num_classes):
        # ... 100+ lines

    def _build_heavy_model(self):
        # ... 50+ lines

    def pretrain(self, X_train, y_train, epochs=20):
        # ... 20 lines

class PrometheusHeavyAgent:
    # ... another 100+ lines
```

**After** (~6 lines):
```python
# Initialize agents
static_agent = StaticAgent(
    input_shape=(64, 64, 1),
    num_classes=generator.num_classes,
    architecture='resnet'
)

prometheus_agent = PrometheusAgent(
    input_shape=(64, 64, 1),
    num_classes=generator.num_classes,
    architecture='resnet',
    learning_rate=0.0003
)
```

**Savings**: **244 lines removed**, replaced with clean initialization

### Step 4: Simplify Experiment Runner

**Before**:
```python
def run_heavy_experiment(...):
    # 150+ lines of experiment logic
    # Inline distribution definitions
    # Inline evaluation logic
    # Inline online training logic
    # Inline result collection
    return static_results, prometheus_results

# Run experiment
static_results, prometheus_results = run_heavy_experiment(...)

# Manual result printing
print(f"Static: {static_results[0]:.1f}%")
# ... 30 more lines of result formatting
```

**After**:
```python
# Pre-training phase
X_pretrain, y_pretrain = generator.generate_batch(2000, initial_dist)
static_agent.pretrain(X_pretrain, y_pretrain, epochs=PRETRAIN_EPOCHS)
prometheus_agent.pretrain(X_pretrain, y_pretrain, epochs=PRETRAIN_EPOCHS)

# Evolution phase
for gen in range(GENERATIONS):
    X_test, y_test = generator.generate_batch(TASKS_PER_GEN, distributions[gen])

    static_results.append(static_agent.evaluate(X_test, y_test)['accuracy'])
    prometheus_results.append(prometheus_agent.evaluate(X_test, y_test)['accuracy'])

    if gen < GENERATIONS - 1:
        X_online, y_online = generator.generate_batch(300, distributions[gen])
        prometheus_agent.online_learn(X_online, y_online, epochs=ONLINE_EPOCHS)

# Professional summary
print_performance_summary(static_results, prometheus_results, "Intelligence Explosion")
```

**Savings**: ~100 lines removed, clearer logic flow

### Step 5: Use Professional Visualization

**Before**:
```python
# Manual matplotlib plotting (50+ lines)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
ax1.plot(static_results, 'b-o', ...)
ax1.plot(prometheus_results, 'g-o', ...)
# ... 40 more lines of plot configuration
plt.show()
```

**After**:
```python
# One-line professional plot
plot_performance_comparison(
    static_results,
    prometheus_results,
    title="Intelligence Explosion: Static vs Prometheus",
    xlabel="Generation"
)
```

**Savings**: ~45 lines removed

---

## Implementation Checklist

### Notebook 1: Intelligence Explosion

- [ ] **Cell 1** (Setup): Add `prometheus/` imports
- [ ] **Cell 10** (Experiment):
  - [ ] Remove `HeavyPatternGenerator` class (200 lines) → use `PatternGenerator`
  - [ ] Remove `residual_block` function (20 lines) → imported from `prometheus.models`
  - [ ] Remove `StaticHeavyAgent` class (120 lines) → use `StaticAgent`
  - [ ] Remove `PrometheusHeavyAgent` class (120 lines) → use `PrometheusAgent`
  - [ ] Simplify `run_heavy_experiment` function (100 lines) → inline logic
  - [ ] Replace manual plotting (50 lines) → use `plot_performance_comparison`
  - [ ] Replace manual summary (30 lines) → use `print_performance_summary`

**Expected reduction**: 640 lines → 80 lines (92% reduction)

### Notebook 2: Dynamic ARC Learning

- [ ] **Cell 1** (Setup): Add `prometheus/` imports
- [ ] **Cell 13** (Experiment):
  - [ ] Remove `HeavyARCGenerator` class (250 lines) → use `ARCGenerator`
  - [ ] Remove `heavy_residual_block` function (25 lines) → imported
  - [ ] Remove `StaticHeavyARCSolver` class (130 lines) → use `StaticAgent`
  - [ ] Remove `PrometheusHeavyARCSolver` class (130 lines) → use `PrometheusAgent`
  - [ ] Simplify experiment runner (120 lines) → inline
  - [ ] Use professional visualization (replace 50 lines)

**Expected reduction**: 705 lines → 90 lines (87% reduction)

### Notebook 3: CRLS Strange Loop

- [ ] **Cell 1** (Setup): Add `prometheus/` imports
- [ ] **Cell 13** (Experiment):
  - [ ] Remove `HeavyTaskGenerator` class (180 lines) → use `TaskGenerator`
  - [ ] Remove `ObjectLevelAgent` class (120 lines) → use `PrometheusAgent`
  - [ ] Remove `MetaLevelAgent` class (150 lines) → use `GodelianSafetyGovernor`
  - [ ] Simplify CRLS loop (150 lines) → cleaner implementation
  - [ ] Use professional visualization (replace 60 lines)

**Expected reduction**: 660 lines → 100 lines (85% reduction)

---

## Example: Refactored Experiment Cell

See `notebooks/experiment_refactored_cell_example.py` for a complete working example showing:
- Clean imports from `prometheus/`
- Simplified experiment logic
- Professional result reporting
- 92% code reduction

---

## Testing After Refactoring

After refactoring each notebook:

1. **Run in Colab**: Ensure all cells execute without errors
2. **Verify Results**: Check that results match pre-refactoring (within random variance)
3. **Check Visualizations**: Ensure plots render correctly
4. **Validate Performance**: Confirm GPU utilization and runtime are comparable

---

## Migration Path

### Phase 1: Create Refactored Versions (Recommended)
1. Create new files: `good_notebook_1_refactored.ipynb`, etc.
2. Keep original notebooks as backup
3. Test refactored versions thoroughly
4. Once validated, replace originals

### Phase 2: Direct Replacement (Faster, Riskier)
1. Backup current notebooks to `notebooks/backup/`
2. Refactor in-place
3. Test immediately
4. Revert from backup if issues arise

---

## Expected Timeline

- **Notebook 1** refactoring: 2-3 hours
- **Notebook 2** refactoring: 2-3 hours
- **Notebook 3** refactoring: 3-4 hours
- **Testing all 3**: 2-3 hours
- **Total**: 9-13 hours

---

## Benefits Summary

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Total Lines** | 4,300 | 1,270 | -70% |
| **Maintainability** | Poor (3x duplication) | Excellent (DRY) | ✅ |
| **Client Focus** | Mixed (impl + demo) | Clear (demo only) | ✅ |
| **Professional Appearance** | Moderate | High | ✅ |
| **Extensibility** | Difficult | Easy | ✅ |

---

## Next Steps

1. Review this guide
2. Decide on migration path (Phase 1 recommended)
3. Start with Notebook 1 (smallest scope)
4. Test thoroughly
5. Apply to Notebooks 2 & 3
6. Update documentation

---

## Questions?

If you encounter issues during refactoring:
- Check `prometheus/` module documentation
- See `experiment_refactored_cell_example.py` for reference
- Verify imports are correct
- Ensure `prometheus/` is in Python path (should work in Colab)
