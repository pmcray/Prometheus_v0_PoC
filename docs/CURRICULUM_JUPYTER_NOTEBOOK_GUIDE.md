# v0.69 Curriculum Learning - Jupyter Notebook Guide

## 📓 New Jupyter Notebook Created

**File**: `Prometheus_v0_69_Curriculum_Demo.ipynb`

This interactive notebook demonstrates the complete 3-stage curriculum learning implementation for Project Prometheus v0.69.

---

## 🎯 What It Does

The notebook implements **progressive difficulty training** through 3 curriculum stages:

### Stage 1: Baseline Training (vs Random Opponent)
- **Population**: 6 agents
- **Generations**: 8
- **Target**: 65% win rate
- **Purpose**: Learn basic game mechanics

### Stage 2: Tactical Development (vs Heuristic Opponent)
- **Population**: 10 agents
- **Generations**: 12
- **Target**: 60% win rate
- **Purpose**: Develop tactical skills (blocking, center control)

### Stage 3: Strategic Training (vs Minimax Depth-2)
- **Population**: 12 agents
- **Generations**: 15
- **Target**: 50% win rate
- **Purpose**: Master strategic planning and lookahead

---

## 🚀 How to Use

### 1. Launch Jupyter
```bash
cd /home/pmc/Prometheus_v0_PoC
jupyter notebook Prometheus_v0_69_Curriculum_Demo.ipynb
```

### 2. Run Cells in Order

The notebook is organized into clear sections:

1. **Setup & Configuration** - Import libraries and configure environment
2. **Define Curriculum** - View the 3-stage training plan
3. **Initialize Components** - Set up GeneralistPlanner, IEE, benchmark suite
4. **Run Stage 1** - Baseline training vs random opponent
5. **Run Stage 2** - Tactical development vs heuristic AI
6. **Run Stage 3** - Strategic training vs Minimax-2
7. **Curriculum Summary** - View overall results table
8. **Dual Visualization** - See dual plots (progress + comparison)
9. **Final Summary** - Review achievements and next steps

### 3. Expected Timeline

- **Stage 1**: ~10-15 minutes
- **Stage 2**: ~15-25 minutes
- **Stage 3**: ~20-35 minutes
- **Total**: 30-90 minutes (depending on Jetson performance)

---

## 📊 What You'll See

### During Training:
- Real-time progress updates for each generation
- Fitness improvements across curriculum stages
- Stage completion summaries

### After Training:
- **Stage Summary Table**: Final vs target for each stage
- **Dual Visualization**:
  - **Plot 1**: Fitness progression across all stages (color-coded)
  - **Plot 2**: Bar chart comparing achieved vs target by stage
- **Overall Statistics**: Initial → final improvement metrics

---

## 🎨 Visualization Output

The notebook generates `v0_69_curriculum_results.png` with:

**Top Panel**: Fitness over generations
- Green lines = Stage 1 (Random)
- Blue lines = Stage 2 (Heuristic)
- Purple lines = Stage 3 (Minimax-2)
- Solid = Best fitness
- Dashed = Mean fitness

**Bottom Panel**: Achieved vs Target
- Green bars = Achieved win rate
- Orange bars = Target win rate
- Side-by-side comparison for each stage

---

## 💡 Key Features

### Interactive Execution
- Run stages individually or all at once
- Pause between stages to inspect results
- Modify parameters and re-run

### Clear Progress Tracking
- Stage-by-stage summaries
- Generation-by-generation updates
- Real-time fitness monitoring

### Comprehensive Documentation
- Markdown cells explain each step
- Expected timelines provided
- Next steps suggested

---

## 🔧 Customization Options

### Adjust Difficulty
```python
# In the CURRICULUM definition cell:
CURRICULUM[0]['target_fitness'] = 0.70  # Harder baseline
CURRICULUM[2]['opponent_type'] = "minimax-3"  # Harder final stage
```

### Scale Training
```python
CURRICULUM[1]['population'] = 15  # More agents
CURRICULUM[1]['generations'] = 20  # More generations
```

### Add Stage 4
```python
CURRICULUM.append({
    "stage": 4,
    "name": "Expert Mastery",
    "opponent_type": "minimax-3",
    "population": 15,
    "generations": 20,
    "target_fitness": 0.40,
    "mutation_rate": 0.4,
    "elitism": 4,
})
```

---

## 📈 Expected Learning Curves

### Stage 1 (vs Random):
```
Gen 1:  50-58% → Gen 8:  ~65%  ✓ Learn basics
```

### Stage 2 (vs Heuristic):
```
Gen 1:  15-20% → Gen 12: ~60%  ✓ Develop tactics
```
*Note: Initial drop is expected - harder opponent!*

### Stage 3 (vs Minimax-2):
```
Gen 1:  5-10%  → Gen 15: ~50%  ✓ Master strategy
```
*Note: 50% vs Minimax-2 is much harder than 65% vs Random!*

---

## ✅ Validation Criteria

**Success Indicators**:
- ✅ Stage 1 reaches ~65% vs random
- ✅ Stage 2 shows initial drop (15-20%), then recovers to 60%
- ✅ Stage 3 shows another drop (5-10%), progresses toward 50%
- ✅ Each stage builds on previous learning
- ✅ Final agent demonstrates strategic play

**If Issues Occur**:
- Check Ollama is running: `ollama list`
- Verify model loaded: `qwen2.5-coder:3b-instruct-q4_K_M`
- Check opponent types are correct in benchmark
- Review fitness drops between stages (indicates harder opponents)

---

## 🆚 Comparison with Python Script

| Aspect | Jupyter Notebook | Python Script (`run_v069_demo.py`) |
|--------|------------------|-----------------------------------|
| Interactivity | ✅ Run stages individually | ❌ All stages run together |
| Visualization | ✅ Inline plots | ✅ Saved to PNG |
| Pause/Inspect | ✅ Between any cell | ❌ Only at completion |
| Documentation | ✅ Rich markdown | ✅ Print statements |
| Modify & Re-run | ✅ Easy | ⚠️ Edit code + restart |
| Automation | ⚠️ Manual execution | ✅ Fully automated |
| Best For | Learning, Exploration | Production, Demos |

---

## 🚀 Next Steps After Running

1. **Analyze Results**:
   - Compare achieved vs target for each stage
   - Study the fitness progression patterns
   - Identify where agents struggled most

2. **Extend Curriculum**:
   - Add Stage 4 with Minimax-3
   - Try different opponent orderings
   - Experiment with population sizes

3. **Apply to Other Games**:
   - Modify for Reversi curriculum
   - Try Draughts with curriculum
   - Extend to FreeCiv (multi-day training)

4. **Transfer Learning**:
   - Train on Connect4 → test on Reversi
   - Analyze skill transfer between games
   - Build multi-game curriculum

---

## 📞 Support

If you encounter issues:

1. **Check Ollama**: `ollama ps` (should show running model)
2. **Verify Imports**: All cells should import without errors
3. **Review Logs**: Check for error messages in cell outputs
4. **Restart Kernel**: Kernel → Restart & Clear Output

---

## 🎉 Summary

The `Prometheus_v0_69_Curriculum_Demo.ipynb` notebook provides an **interactive, educational demonstration** of curriculum learning in action. It's perfect for:

- Understanding how curriculum learning works
- Visualizing progressive difficulty training
- Experimenting with different configurations
- Teaching others about evolutionary AI

**Run it now to see intelligence emergence in real-time!** 🧬

---

**Created**: 2025-10-02
**Version**: v0.69 Curriculum Learning Edition
**Platform**: Jetson Orin Nano with Ollama
