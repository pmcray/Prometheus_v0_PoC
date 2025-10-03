# v0.69 Demo - Curriculum Learning Integration

## What Changed

The v0.69 demo has been upgraded from single-stage evolution to **full curriculum learning** with progressive difficulty training.

## New Curriculum Structure

### 3-Stage Progressive Training:

**Stage 1: Baseline Training** (Random Opponent)
- Population: 6 agents
- Generations: 8
- Target: 65% win rate
- Purpose: Learn basic game mechanics

**Stage 2: Tactical Development** (Heuristic Opponent)
- Population: 10 agents
- Generations: 12
- Target: 60% win rate
- Purpose: Develop tactical skills (blocking, center control)

**Stage 3: Strategic Training** (Minimax Depth-2)
- Population: 12 agents
- Generations: 15
- Target: 50% win rate
- Purpose: Master strategic planning and lookahead

## Expected Learning Progression

```
Stage 1 (vs Random):
  Gen 1:  ~50% → Gen 8:  ~65%  [Learn basics]

Stage 2 (vs Heuristic):
  Gen 1:  ~15% → Gen 12: ~60%  [Develop tactics]

Stage 3 (vs Minimax-2):
  Gen 1:  ~5%  → Gen 15: ~50%  [Master strategy]
```

## Running the Demo

```bash
# Run the enhanced v0.69 demo
python run_v069_demo.py

# Expected runtime: 1-2 hours on Jetson
# Output: v0_69_curriculum_results.png with dual visualization
```

## What You'll See

1. **Curriculum Overview** - Lists all 3 stages
2. **GeneralistPlanner** - Creates meta-task
3. **Stage-by-Stage Evolution** - Progressive training
4. **Summary Table** - Final vs target for each stage
5. **Dual Visualization**:
   - Plot 1: Fitness over all generations (colored by stage)
   - Plot 2: Bar chart comparing achieved vs target

## Key Improvements Over Original v0.69

| Aspect | Original | Enhanced |
|--------|----------|----------|
| Opponent | Single (Draughts/Connect4) | Progressive curriculum |
| Difficulty | Fixed | Increasing (random → heuristic → minimax) |
| Learning Depth | Shallow (~50% plateau) | Deep (50% → 65% → 60% → 50%*) |
| Strategic Skills | Limited | Blocks, center control, lookahead |
| Training Time | ~30 min | ~1-2 hours |
| Visualization | Single plot | Dual plots (progress + comparison) |

*Note: 50% vs Minimax-2 is much harder than 65% vs Random!

## Curriculum Benefits

1. **Progressive Difficulty** - Prevents frustration, builds skills incrementally
2. **Objective Measurement** - Each opponent provides clear benchmark
3. **Transfer Learning** - Skills from Stage 1 help in Stage 2, etc.
4. **Observable Emergence** - Can see strategy development across stages
5. **Extensible** - Easy to add Stage 4 (minimax-3) or Stage 0 (trivial)

## Output Files

- `v0_69_curriculum_results.png` - Dual visualization
  - Top: Fitness progression across all stages
  - Bottom: Achieved vs Target by stage

## Next Steps

To extend the curriculum:

```python
# Add to CURRICULUM list in run_v069_demo.py:
{
    "stage": 4,
    "name": "Expert Mastery",
    "opponent_type": "minimax-3",
    "population": 15,
    "generations": 20,
    "target_fitness": 0.40,
    "mutation_rate": 0.4,
    "elitism": 4,
}
```

## Technical Details

### Opponent Patching
Each stage temporarily overrides the benchmark to use the correct opponent:

```python
def run_with_opponent(agent, **kwargs):
    kwargs['opponent_type'] = stage['opponent_type']
    return original_run(agent, **kwargs)

connect4_benchmark.run_benchmark = run_with_opponent
```

### Result Tracking
All results are collected for final analysis:

```python
stage_result = {
    'stage': stage['stage'],
    'best_fitness': smm.best_fitness,
    'target_fitness': stage['target_fitness'],
    'achieved': smm.best_fitness >= stage['target_fitness'],
    'fitness_history': fitness_history
}
```

### Visualization
Two-panel matplotlib figure showing:
- Top: Stage-colored fitness progression
- Bottom: Achieved vs target bar chart

## Validation Criteria

✅ **Success Indicators:**
- Stage 1: Reaches ~65% vs random
- Stage 2: Shows significant drop initially (15-20%), then recovers to 60%
- Stage 3: Shows another drop (5-10%), progresses toward 50%
- Each stage builds on previous learning
- Final agent demonstrates strategic play

⚠️ **If Not Working:**
- Check that opponents are being applied correctly
- Verify fitness drops between stages (indicates harder opponent)
- Ensure agent interface fix is in place (from bug fixes)
- Check Ollama is running and model is loaded

## Summary

The v0.69 demo now showcases **true curriculum learning** with:
- 3 progressive difficulty stages
- Clear strategic skill development
- Objective measurement via opponent strength
- Observable intelligence emergence
- Complete visualization and metrics

This demonstrates the full Prometheus architecture in action: **domain-general capability acquisition through recursive self-improvement with curriculum learning**.
