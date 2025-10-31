# 🚀 Getting Started with v0.69 Curriculum Learning

## Quick Start - Launch Jupyter Notebook

### Step 1: Navigate to Project Directory
```bash
cd /home/pmc/Prometheus_v0_PoC
```

### Step 2: Launch Jupyter Notebook
```bash
jupyter notebook Prometheus_v0_69_Curriculum_Demo.ipynb
```

This will:
1. Start Jupyter server
2. Open your browser automatically
3. Display the curriculum learning notebook

### Step 3: Run the Cells
- Click **Cell → Run All** to run entire curriculum
- Or run cells individually with **Shift + Enter**

---

## What to Expect

### Runtime: 30-90 minutes total
- **Stage 1** (Random opponent): ~10-15 min
- **Stage 2** (Heuristic opponent): ~15-25 min
- **Stage 3** (Minimax-2 opponent): ~20-35 min

### You'll See:
1. **Curriculum overview** - 3 stages displayed
2. **GeneralistPlanner** - Creates meta-task
3. **Stage 1 execution** - Training vs random opponent
4. **Stage 2 execution** - Training vs heuristic AI
5. **Stage 3 execution** - Training vs Minimax-2
6. **Summary table** - Final results for all stages
7. **Dual visualization** - Progress + comparison plots

---

## Alternative: Run Python Script

If you prefer automated execution without Jupyter:

```bash
python run_v069_demo.py
```

This runs all 3 stages automatically and saves `v0_69_curriculum_results.png`.

---

## Troubleshooting

### Jupyter Not Found?
```bash
pip install jupyter notebook
```

### Ollama Not Running?
```bash
ollama ps
# If empty, pull the model:
ollama pull qwen2.5-coder:3b-instruct-q4_K_M
```

### Import Errors?
```bash
pip install -r requirements.txt
```

### Port Already in Use?
```bash
jupyter notebook --port=8889 Prometheus_v0_69_Curriculum_Demo.ipynb
```

---

## 📚 Documentation Available

- **V069_COMPLETE_SUMMARY.md** - Complete overview of everything
- **CURRICULUM_JUPYTER_NOTEBOOK_GUIDE.md** - Detailed Jupyter guide
- **V069_CURRICULUM_INTEGRATION.md** - Technical integration details
- **STRATEGIC_TRAINING_IMPLEMENTATION.md** - Implementation summary

---

## ✅ Ready to Go!

Everything is set up and ready. Just run:

```bash
jupyter notebook Prometheus_v0_69_Curriculum_Demo.ipynb
```

**Enjoy watching intelligence emerge through curriculum learning!** 🧬

---

**Created**: 2025-10-02
**Version**: v0.69 Curriculum Learning Edition
