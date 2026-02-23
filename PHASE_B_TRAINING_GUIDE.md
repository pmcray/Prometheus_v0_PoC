# Phase B: Model Training & Validation Guide

**Estimated Time**: 2-3 hours (mostly automated)
**Prerequisites**: TensorFlow 2.15+, GPU recommended (optional)

---

## Overview

Phase B trains three pre-trained models and validates their performance with comprehensive benchmarks:

1. **Go 9×9 Model** (~200 ELO above random, 1 hour training)
2. **Go 19×19 Model** (~400 ELO above random, 45 min via transfer learning)
3. **Chess Model** (~300 ELO above random, 1 hour training)

All models are trained with MCTS (400 simulations) for stronger play.

---

## Prerequisites

### 1. Environment Setup

```bash
# Ensure you're in the project root
cd Prometheus_v0_PoC

# Create/activate virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
python -c "import tensorflow as tf; print(f'TensorFlow {tf.__version__} installed')"
python -c "import numpy, scipy, chess; print('✓ All dependencies OK')"
```

### 2. Verify Core Functionality

```bash
# Quick import test
python -c "
from prometheus.models.go_models import PrometheusGoAgent
from prometheus.environments.go import GoEnvironment
from prometheus.mcts import add_mcts
print('✓ Prometheus imports successful')
"
```

---

## Training Models

### Option A: Train All Models (Recommended)

```bash
# Train all three models automatically
# This will take ~2-3 hours total
python scripts/train_pretrained_models.py --all

# Models will be saved to:
# - models/pretrained/go_9x9.h5
# - models/pretrained/go_19x19.h5
# - models/pretrained/chess.h5
```

### Option B: Train Individual Models

#### Go 9×9 (1 hour)

```bash
python scripts/train_pretrained_models.py --model go-9x9 --games 200

# Expected output:
# - Win rate vs random: 70-85%
# - ELO: ~1200-1300
# - Training time: ~60 minutes
```

#### Go 19×19 via Transfer (45 min)

```bash
# Requires go_9x9.h5 to exist first!
python scripts/train_pretrained_models.py --model go-19x19 --games 100

# Expected output:
# - Win rate vs random: 80-95%
# - ELO: ~1400-1500
# - Training time: ~45 minutes (10x faster than from scratch!)
```

#### Chess (1 hour)

```bash
python scripts/train_pretrained_models.py --model chess --games 200

# Expected output:
# - Win rate vs random: 75-90%
# - ELO: ~1300-1400
# - Training time: ~60 minutes
```

### Option C: Quick Test (Development)

For quick testing/development with smaller models:

```bash
# Train with fewer games (10-15 minutes each)
python scripts/train_pretrained_models.py --model go-9x9 --games 50 --no-mcts

# This will be faster but produce weaker models
# Useful for testing the pipeline
```

---

## Running Benchmarks

After training, benchmark the models to validate performance:

### Comprehensive Benchmarks (All Metrics)

```bash
# Benchmark Go 9x9
python scripts/benchmark_models.py \
  --model models/pretrained/go_9x9.h5 \
  --metric all \
  --output benchmarks/go_9x9_results.json

# Benchmark Go 19x19
python scripts/benchmark_models.py \
  --model models/pretrained/go_19x19.h5 \
  --metric all \
  --output benchmarks/go_19x19_results.json

# Benchmark Chess
python scripts/benchmark_models.py \
  --model models/pretrained/chess.h5 \
  --metric all \
  --output benchmarks/chess_results.json
```

### Individual Metric Benchmarks

#### Inference Speed

```bash
python scripts/benchmark_models.py \
  --model models/pretrained/go_9x9.h5 \
  --metric inference \
  --num-runs 100
```

**Expected Results**:
- Go 9×9: 5-15ms per inference
- Go 19×19: 15-40ms per inference
- Chess: 10-25ms per inference

#### MCTS Performance

```bash
python scripts/benchmark_models.py \
  --model models/pretrained/go_9x9.h5 \
  --metric mcts \
  --mcts-sims 100 400 800 \
  --mcts-games 10
```

**Expected Results** (win rate vs random):
- 100 sims: 60-70%
- 400 sims: 75-85%
- 800 sims: 80-90%

#### Memory Usage

```bash
python scripts/benchmark_models.py \
  --model models/pretrained/go_9x9.h5 \
  --metric memory
```

**Expected Results**:
- Go 9×9: ~50-100 MB
- Go 19×19: ~150-300 MB
- Chess: ~100-200 MB

---

## Expected Benchmark Results

### Go 9×9 Model

```json
{
  "model_path": "models/pretrained/go_9x9.h5",
  "inference": {
    "mean_ms": 8.5,
    "p95_ms": 12.3,
    "inferences_per_second": 117.6
  },
  "mcts": {
    "100_sims": {"win_rate": 0.65, "elo": 1150},
    "400_sims": {"win_rate": 0.78, "elo": 1280},
    "800_sims": {"win_rate": 0.85, "elo": 1350}
  },
  "memory": {
    "model_file_size_mb": 12.5,
    "memory_delta_mb": 85.3,
    "parameters": 125843
  }
}
```

### Go 19×19 Model

```json
{
  "model_path": "models/pretrained/go_19x19.h5",
  "inference": {
    "mean_ms": 22.1,
    "p95_ms": 31.5,
    "inferences_per_second": 45.2
  },
  "mcts": {
    "100_sims": {"win_rate": 0.75, "elo": 1300},
    "400_sims": {"win_rate": 0.88, "elo": 1450},
    "800_sims": {"win_rate": 0.93, "elo": 1520}
  },
  "memory": {
    "model_file_size_mb": 35.2,
    "memory_delta_mb": 245.8,
    "parameters": 358921
  }
}
```

### Chess Model

```json
{
  "model_path": "models/pretrained/chess.h5",
  "inference": {
    "mean_ms": 15.3,
    "p95_ms": 21.8,
    "inferences_per_second": 65.4
  },
  "mcts": {
    "100_sims": {"win_rate": 0.70, "elo": 1220},
    "400_sims": {"win_rate": 0.82, "elo": 1340},
    "800_sims": {"win_rate": 0.89, "elo": 1410}
  },
  "memory": {
    "model_file_size_mb": 18.7,
    "memory_delta_mb": 156.4,
    "parameters": 189563
  }
}
```

---

## Documenting Results

### 1. Save All Benchmark Results

Create `benchmarks/` directory and save JSON outputs:

```bash
mkdir -p benchmarks

# All models
for model in go_9x9 go_19x19 chess; do
  python scripts/benchmark_models.py \
    --model models/pretrained/${model}.h5 \
    --metric all \
    --output benchmarks/${model}_results.json
done
```

### 2. Create Performance Summary

Create `benchmarks/PERFORMANCE_SUMMARY.md`:

```markdown
# Prometheus Pre-trained Models - Performance Summary

## Training Results

| Model | Games | Time | Win Rate | ELO | Parameters |
|-------|-------|------|----------|-----|------------|
| Go 9×9 | 200 | 62 min | 78% | 1,280 | 125,843 |
| Go 19×19 | 100 | 48 min | 88% | 1,450 | 358,921 |
| Chess | 200 | 59 min | 82% | 1,340 | 189,563 |

## Inference Performance

| Model | Mean (ms) | p95 (ms) | Throughput |
|-------|-----------|----------|------------|
| Go 9×9 | 8.5 | 12.3 | 117.6/sec |
| Go 19×19 | 22.1 | 31.5 | 45.2/sec |
| Chess | 15.3 | 21.8 | 65.4/sec |

## MCTS Scaling

### Go 9×9
- 100 sims: 65% win rate, 1,150 ELO
- 400 sims: 78% win rate, 1,280 ELO (+130 ELO)
- 800 sims: 85% win rate, 1,350 ELO (+70 ELO)

### Go 19×19
- 100 sims: 75% win rate, 1,300 ELO
- 400 sims: 88% win rate, 1,450 ELO (+150 ELO)
- 800 sims: 93% win rate, 1,520 ELO (+70 ELO)

### Chess
- 100 sims: 70% win rate, 1,220 ELO
- 400 sims: 82% win rate, 1,340 ELO (+120 ELO)
- 800 sims: 89% win rate, 1,410 ELO (+70 ELO)

## Memory Usage

| Model | File Size | Runtime Memory | Efficiency |
|-------|-----------|----------------|------------|
| Go 9×9 | 12.5 MB | 85 MB | Excellent |
| Go 19×19 | 35.2 MB | 246 MB | Good |
| Chess | 18.7 MB | 156 MB | Excellent |
```

### 3. Update Main Documentation

Update `PROGRESS_UPDATE.md` with:

```markdown
## ✅ Phase B: Validation Complete

**Models Trained**:
- ✅ Go 9×9: 1,280 ELO (+280 vs baseline)
- ✅ Go 19×19: 1,450 ELO (+450 vs baseline)
- ✅ Chess: 1,340 ELO (+340 vs baseline)

**Benchmarks Run**:
- ✅ Inference speed: All models <25ms average
- ✅ MCTS scaling: 400 sims optimal (+130 ELO avg)
- ✅ Memory usage: All models <250MB runtime

**Documentation**:
- ✅ Performance summary created
- ✅ Benchmark results saved (JSON)
- ✅ Training metadata recorded
```

---

## Troubleshooting

### Training Takes Too Long

**Symptom**: Training taking >2 hours per model

**Solutions**:
```bash
# Reduce training games
python scripts/train_pretrained_models.py --model go-9x9 --games 100

# Disable MCTS during training (faster but weaker)
python scripts/train_pretrained_models.py --model go-9x9 --no-mcts

# Use GPU if available
# TensorFlow will auto-detect GPU, verify with:
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

### Out of Memory Errors

**Symptom**: Training crashes with OOM errors

**Solutions**:
```bash
# Train smaller Go board first
python scripts/train_pretrained_models.py --model go-9x9 --games 100

# Don't train Go 19×19 and Chess simultaneously
# Train sequentially instead

# Reduce MCTS simulations
# Edit scripts/train_pretrained_models.py:
# Change: num_simulations=400 -> num_simulations=200
```

### Import Errors

**Symptom**: `ModuleNotFoundError` or `ImportError`

**Solutions**:
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Verify prometheus package
pip install -e .

# Check imports
python -c "import prometheus; print(prometheus.__file__)"
```

### Poor Model Performance

**Symptom**: Win rate <60% or ELO <1000

**Possible Causes**:
- Too few training games (increase to 300-500)
- MCTS disabled during training (enable with `--mcts`)
- Training interrupted/corrupted

**Solutions**:
```bash
# Retrain with more games
python scripts/train_pretrained_models.py --model go-9x9 --games 500

# Ensure MCTS enabled
python scripts/train_pretrained_models.py --model go-9x9 --games 200
# (MCTS is enabled by default, use --no-mcts to disable)

# Delete old model and retrain
rm models/pretrained/go_9x9.h5
python scripts/train_pretrained_models.py --model go-9x9
```

---

## Performance Optimization

### Using GPU Acceleration

```bash
# Install TensorFlow GPU version
pip install tensorflow[and-cuda]>=2.15.0

# Verify GPU detection
python -c "
import tensorflow as tf
gpus = tf.config.list_physical_devices('GPU')
print(f'GPUs available: {len(gpus)}')
if gpus:
    print(f'GPU: {gpus[0].name}')
    # Enable memory growth to avoid OOM
    tf.config.experimental.set_memory_growth(gpus[0], True)
"

# Expected speedup: 3-10x faster training
```

### Parallel Training

Train multiple models simultaneously (if you have enough RAM/VRAM):

```bash
# Terminal 1: Train Go 9×9
python scripts/train_pretrained_models.py --model go-9x9 &

# Terminal 2: Train Chess
python scripts/train_pretrained_models.py --model chess &

# Wait for both to complete
wait

# Then train Go 19×19 with transfer
python scripts/train_pretrained_models.py --model go-19x19
```

### Background Training

Run training in background (Linux/Mac):

```bash
# Start training in background
nohup python scripts/train_pretrained_models.py --all > training.log 2>&1 &

# Monitor progress
tail -f training.log

# Check if still running
ps aux | grep train_pretrained_models
```

---

## Next Steps After Phase B

Once models are trained and benchmarked:

1. **Test Models Manually**:
   ```bash
   prometheus evaluate \
     --model1 models/pretrained/go_9x9.h5 \
     --model2 random \
     --num-games 10
   ```

2. **Deploy Bots** (Phase C):
   ```bash
   # Update .env with API tokens
   cp .env.example .env
   nano .env

   # Deploy with Docker
   docker-compose up -d
   ```

3. **Share Models**:
   - Upload to GitHub Releases
   - Tag with version (e.g., v1.0.0)
   - Include performance summary in release notes

4. **Iterate & Improve**:
   - Train with more games (500-1000)
   - Experiment with model architectures
   - Try different MCTS configurations

---

## Verification Checklist

Before marking Phase B complete, verify:

- [ ] All 3 models trained successfully
- [ ] Model files saved to `models/pretrained/`
- [ ] Metadata JSON files created
- [ ] All models achieve >60% win rate vs random
- [ ] All models achieve >1000 ELO
- [ ] Inference benchmarks run successfully
- [ ] MCTS benchmarks run successfully
- [ ] Memory benchmarks run successfully
- [ ] Benchmark results saved to `benchmarks/`
- [ ] Performance summary documented
- [ ] `PROGRESS_UPDATE.md` updated

---

## Quick Reference

```bash
# Full Phase B execution (2-3 hours)
python scripts/train_pretrained_models.py --all

# Benchmark all models (~30 min)
mkdir -p benchmarks
for model in go_9x9 go_19x19 chess; do
  python scripts/benchmark_models.py \
    --model models/pretrained/${model}.h5 \
    --metric all \
    --output benchmarks/${model}_results.json
done

# Verify models work
prometheus evaluate --model1 models/pretrained/go_9x9.h5 --model2 random --num-games 10

# Mark Phase B complete!
```

---

**Estimated Total Time**: 2-3 hours automated + 30 min documentation

**GPU Recommended**: 3-10x speedup

**Disk Space Needed**: ~200 MB for models + benchmarks

**Next Phase**: Phase C - Polish & Deploy 🚀
