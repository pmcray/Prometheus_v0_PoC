# 🚀 PrometheusStar Quick Start

**3 ways to run PrometheusStar, from easiest to most impressive:**

---

## Option 1: Connect4 Baseline (Works Right Now!)

**Time**: 1-2 hours
**Hardware**: Any computer
**Why**: Prove the concept works

```bash
# Just run it!
jupyter notebook Prometheus_v0_69_Curriculum_Demo.ipynb

# Click "Cell → Run All"
# Watch 3-stage curriculum: Random → Heuristic → Minimax
```

**What you'll see**:
- Stage 1: Agent learns to beat random opponent (65% target)
- Stage 2: Agent learns tactics vs heuristic AI (60% target)
- Stage 3: Agent masters strategy vs Minimax (50% target)
- Dual visualization showing progress

---

## Option 2: MicroRTS Demo (Fast RTS Proof)

**Time**: 6-12 hours
**Hardware**: Jetson or GPU
**Why**: Prove it works on RTS games

```bash
# Step 1: Install MicroRTS (one time)
pip install gym-microrts

# Step 2: Test installation
python -c "from benchmarks.microrts_benchmark import test_microrts_installation; test_microrts_installation()"

# Step 3: Run training
jupyter notebook PrometheusStar_MicroRTS_Demo.ipynb

# Or automated:
python run_prometheusstar_microrts.py
```

**What you'll see**:
- Stage 1: Beat Random AI (80% target) - learn basics
- Stage 2: Beat Passive AI (65% target) - resource management
- Stage 3: Beat Rush AI (50% target) - tactical response
- Stage 4: Beat Mixed AI (40% target) - strategic depth
- **Result**: PrometheusStar masters RTS in hours (vs AlphaStar's weeks)

---

## Option 3: FreeCiv on Colab (Most Impressive)

**Time**: 4 weeks (passive - one session per week)
**Hardware**: Free Google Colab
**Why**: Complex strategy game, impressive demo

```bash
# Week 1: Stage 1
1. Go to colab.research.google.com
2. Upload Prometheus_FreeCiv_Colab.ipynb
3. Mount Google Drive
4. Set STAGE_TO_RUN = 1
5. Run all cells (~12 hours)
6. Checkpoint auto-saves to Drive

# Week 2: Stage 2
1. Re-open notebook in Colab
2. Set STAGE_TO_RUN = 2
3. Run all cells
4. Previous results load automatically

# Week 3: Stage 3
Same as Week 2, STAGE_TO_RUN = 3

# Week 4: Stage 4
Same as Week 2, STAGE_TO_RUN = 4

# Done!
Final visualization shows full curriculum progress
```

**What you'll see**:
- Stage 1: Learn basics vs Novice AI (30% target)
- Stage 2: Develop tactics vs Easy AI (20% target)
- Stage 3: Master strategy vs Normal AI (15% target)
- Stage 4: Expert play vs Hard AI (10% target)
- **Result**: PrometheusStar learns complex strategy across 4 weeks

---

## 📊 Quick Comparison

| Option | Time | Hardware | Impressiveness | Difficulty |
|--------|------|----------|----------------|------------|
| **Connect4** | 1-2 hrs | Any | ⭐⭐ | ✅ Easy |
| **MicroRTS** | 6-12 hrs | Jetson/GPU | ⭐⭐⭐⭐ | ⭐ Medium |
| **FreeCiv** | 4 weeks | Free Colab | ⭐⭐⭐⭐⭐ | ⭐⭐ Medium |

---

## 🎯 Recommended Path

### For Research Validation:
1. ✅ **Today**: Run Connect4 (prove concept)
2. ✅ **This Week**: Run MicroRTS (prove RTS works)
3. ✅ **This Month**: Start FreeCiv on Colab (run impressive demo)

### For Quick Demo:
- ✅ **Just run Connect4** - works in 1 hour, shows curriculum learning

### For Publishing:
- ✅ **Run all three** - shows domain generalization across game types

---

## 💡 Tips

### Connect4 Tips
- Already works! No installation needed
- If it fails, check `benchmarks/strategic_opponents.py` exists
- Visualization auto-saves to current directory

### MicroRTS Tips
- If gym-microrts won't install: `pip install gym==0.21.0 gym-microrts`
- First run takes longer (downloading Java libraries)
- Can reduce `generations` in curriculum for faster testing

### FreeCiv Tips
- Mount Google Drive FIRST (checkpoints save there)
- Colab may disconnect - that's OK, checkpoints resume automatically
- Run one stage per session (don't try to run all 4 at once)
- Check `/content/drive/MyDrive/Prometheus_FreeCiv_Checkpoints/` for saves

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'prometheus'"
```bash
# Make sure you're in the project directory
cd /home/pmc/Prometheus_v0_PoC
jupyter notebook
```

### "gym-microrts not installing"
```bash
# Try specific versions
pip install gym==0.21.0
pip install gym-microrts==0.4.2

# Or skip MicroRTS, just run Connect4 instead
```

### "Colab keeps disconnecting"
```
That's normal! The checkpoint system handles this:
- Every stage completion auto-saves
- Next session loads automatically
- No progress lost
```

### "Low win rates / agent not improving"
```python
# Increase training time
config = EvolutionConfig(
    population_size=15,  # More agents (default: 6-10)
    generations=30,      # More generations (default: 10-20)
    mutation_rate=0.4    # More exploration (default: 0.3)
)
```

---

## 📚 Documentation

- **Overview**: `PROMETHEUSSTAR_README.md`
- **RTS Games**: `PROMETHEUSSTAR_RTS_OPTIONS.md`
- **Implementation**: `PROMETHEUSSTAR_IMPLEMENTATION_SUMMARY.md`
- **Colab + RTS**: `COLAB_AND_RTS_SUMMARY.md`
- **This File**: Quick start only

---

## ✅ Success Checklist

**After running Connect4**:
- [ ] Saw 3 curriculum stages complete
- [ ] Saw fitness improve each generation
- [ ] Saw final visualization with dual plots
- [ ] Agent achieved 50%+ vs Minimax

**After running MicroRTS**:
- [ ] Installed gym-microrts successfully
- [ ] Ran 4-stage curriculum
- [ ] Saw win rates increase each stage
- [ ] Got visualization showing progress

**After running FreeCiv**:
- [ ] Completed all 4 weekly sessions
- [ ] Checkpoints saved to Google Drive
- [ ] Final visualization shows all stages
- [ ] Agent improved from 1% to 10%+ vs Hard AI

---

## 🎉 You're Ready!

**Pick your path and start now**:

```bash
# Easiest (1 hour):
jupyter notebook Prometheus_v0_69_Curriculum_Demo.ipynb

# Best (6 hours):
pip install gym-microrts
jupyter notebook PrometheusStar_MicroRTS_Demo.ipynb

# Most impressive (4 weeks passive):
# Upload Prometheus_FreeCiv_Colab.ipynb to Colab
```

**Welcome to PrometheusStar!** 🌟

---

**Created**: 2025-10-02
**Version**: v0.1
**Status**: Ready to run!
