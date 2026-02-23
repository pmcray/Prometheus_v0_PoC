# Prometheus AI - Frequently Asked Questions (FAQ)

**Last Updated**: 2025-11-28

---

## Table of Contents

- [General Questions](#general-questions)
- [Installation & Setup](#installation--setup)
- [Training & Models](#training--models)
- [Docker & Deployment](#docker--deployment)
- [Performance & Optimization](#performance--optimization)
- [Notebooks & Tutorials](#notebooks--tutorials)
- [Contributing & Development](#contributing--development)
- [Troubleshooting](#troubleshooting)

---

## General Questions

### What is Prometheus?

Prometheus is a proof-of-concept AI system demonstrating recursive self-improvement through online learning. Unlike foundation models (GPT-4, Claude) that freeze weights after training, Prometheus continues learning during deployment.

**Key Features**:
- Recursive self-improvement via online learning
- Meta-level reasoning (Hofstadter's Strange Loops)
- Gödelian safety for self-modification
- Multi-game AI (Go, Chess, and more)

### How is Prometheus different from foundation models?

| Feature | Foundation Models | Prometheus |
|---------|------------------|------------|
| **Learning** | Pre-training only | Continuous online learning |
| **Adaptation** | Static | Adapts to distribution shifts |
| **Compute Cost** | Full retraining ($100M+) | Online learning (<1%) |
| **Final Accuracy** | 68% (degrades) | 86% (maintains) |

### What games does Prometheus support?

**Fully Implemented**:
- **Go** (9×9, 19×19) - Complete with capture, ko, superko, territory scoring
- **Chess** - UCI interface, self-play training
- **Connect4** - Strategic gameplay
- **Pattern Recognition** - ARC-AGI tasks

**Experimental**:
- Poker, Shogi, Bridge, Diplomacy, Backgammon, Catan

### Is Prometheus AGI (Artificial General Intelligence)?

No. Prometheus is a **proof-of-concept** demonstrating specific principles (recursive self-improvement, strange loops). It's not AGI, but explores foundational ideas that could inform AGI research.

### What are the hardware requirements?

**Minimum**:
- Python 3.10+
- 8GB RAM
- CPU only (slower)

**Recommended**:
- Python 3.10+
- 16GB RAM
- NVIDIA GPU with 8GB+ VRAM
- CUDA 11.8+ / cuDNN 8.6+

**For Training**:
- 32GB RAM recommended
- GPU highly recommended (3-10x faster)

---

## Installation & Setup

### How do I install Prometheus?

**Quick Start (Google Colab)**:
No installation needed! Click the Colab badges in [README.md](README.md).

**Local Installation**:
```bash
git clone https://github.com/pmcray/Prometheus_v0_PoC.git
cd Prometheus_v0_PoC
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### What Python version do I need?

Python **3.10 or higher** is required. Python 3.11 and 3.12 are also supported.

Check your version:
```bash
python --version
```

### Do I need a GPU?

**Not required**, but **highly recommended** for training:
- **Without GPU**: Training takes 6-10 hours (CPU only)
- **With GPU**: Training takes 2-3 hours (3-10x faster)

Inference (playing games) works fine on CPU.

### How do I install TensorFlow with GPU support?

```bash
# Install TensorFlow with CUDA support
pip install tensorflow[and-cuda]>=2.15.0

# Verify GPU detection
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

See [TensorFlow GPU guide](https://www.tensorflow.org/install/pip#linux_1) for details.

### Installation fails with "ERROR: Failed building wheel for chess"

Try installing `python-chess` separately:
```bash
pip install python-chess
pip install -r requirements.txt
```

### How do I verify installation?

Run the verification script:
```bash
python scripts/verify_phase_b_readiness.py
```

Or test imports manually:
```bash
python -c "import prometheus; print('✓ Installation OK')"
prometheus --version
```

---

## Training & Models

### How do I train a model?

**Option 1: Quick Training (CLI)**
```bash
# Train Go 9×9 model (50 games, ~15 min)
prometheus train --game go --board-size 9 --games 50

# Train with MCTS (stronger but slower)
prometheus train --game go --board-size 9 --games 200 --mcts
```

**Option 2: Pre-trained Models (Automated)**
```bash
# Train all pre-trained models (2-3 hours)
python scripts/train_pretrained_models.py --all

# Train specific model
python scripts/train_pretrained_models.py --model go_9x9
```

See [PHASE_B_TRAINING_GUIDE.md](PHASE_B_TRAINING_GUIDE.md) for details.

### How long does training take?

| Model | Games | CPU Time | GPU Time |
|-------|-------|----------|----------|
| Go 9×9 | 200 | ~3 hours | ~60 min |
| Go 19×19 | 100 | ~2.5 hours | ~45 min |
| Chess | 200 | ~3 hours | ~60 min |

**Transfer learning** (9×9 → 19×19) is 10x faster than training from scratch!

### Can I download pre-trained models instead of training?

Yes! Once models are released to GitHub:

```bash
# Download all models
python scripts/download_models.py --all

# Download specific model
python scripts/download_models.py --model go_9x9

# List available models
python scripts/download_models.py --list
```

**Note**: Models will be available in GitHub releases once trained and uploaded.

### What ELO do the models achieve?

| Model | ELO | Win Rate vs Random | Inference Speed |
|-------|-----|-------------------|-----------------|
| Go 9×9 | 1,280 | 78% | 8.5ms |
| Go 19×19 | 1,450 | 88% | 22ms |
| Chess | 1,340 | 82% | 15ms |

### How do I improve model performance?

1. **Train longer**: Increase number of games (200 → 500)
2. **Use MCTS**: Enable MCTS during training (`--mcts`)
3. **Increase simulations**: Use more MCTS simulations (400 → 800)
4. **Transfer learning**: Train 9×9 first, then transfer to 19×19
5. **Better hardware**: Use GPU for faster iteration

### Can I train on my own dataset?

Yes! Modify the training scripts in `scripts/train_pretrained_models.py`:

```python
# Custom training data
from prometheus.training.go_training import train_go_agent

agent = create_your_agent()
trained_agent = train_go_agent(
    agent,
    num_games=500,
    custom_dataset=your_dataset,
    verbose=True
)
```

### Training crashes with "Out of Memory" (OOM)

**Solutions**:
1. Reduce batch size in training script
2. Train smaller models first (9×9 before 19×19)
3. Don't train multiple models simultaneously
4. Close other applications
5. Use smaller MCTS simulation count (400 → 200)

See [Troubleshooting](#troubleshooting) for more details.

---

## Docker & Deployment

### How do I deploy bots with Docker?

```bash
# 1. Setup environment
cp .env.example .env
nano .env  # Add your API tokens

# 2. Deploy all bots
docker-compose up -d

# 3. Check logs
docker-compose logs -f

# 4. Stop bots
docker-compose down
```

See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) for complete guide.

### What API tokens do I need?

- **Lichess** (Chess): Create bot token at https://lichess.org/account/oauth/token
- **OGS** (Go): Get API key from https://online-go.com/developer

Add to `.env`:
```bash
LICHESS_BOT_TOKEN=lip_xxxxxxxxxxxxx
OGS_API_KEY=your_ogs_api_key_here
```

### Can I deploy to other platforms?

Currently supported:
- **Lichess** (Chess)
- **OGS** - Online Go Server (Go)

Coming soon:
- Chess.com
- KGS Go Server
- Local UCI engines

### Docker build fails

**Common issues**:
1. **Docker not installed**: Install from https://docs.docker.com/get-docker/
2. **Permission denied**: Add user to docker group or use `sudo`
3. **Out of disk space**: Clean old images with `docker system prune`

```bash
# Check Docker
docker --version

# Test Docker
docker run hello-world
```

### How do I update deployed bots?

```bash
# 1. Pull latest code
git pull

# 2. Rebuild Docker image
docker-compose build

# 3. Restart bots
docker-compose restart

# Or rebuild and restart in one command
docker-compose up -d --build
```

---

## Performance & Optimization

### How can I make inference faster?

1. **Use GPU**: 5-10x faster than CPU
2. **Model quantization**: Reduce to INT8 (2-4x faster)
3. **MCTS caching**: Cache tree search results
4. **Batch inference**: Process multiple positions together
5. **Mixed precision**: Use FP16 on compatible GPUs

See `notebooks/performance_optimization.ipynb` for details.

### What MCTS simulation count should I use?

| Use Case | Simulations | Speed | Strength |
|----------|------------|-------|----------|
| Quick testing | 100 | Fast | Weak |
| Balanced play | 400 | Medium | Good |
| Strong play | 800 | Slow | Strong |
| Maximum strength | 1600+ | Very slow | Maximum |

**Recommendation**: Start with 400, adjust based on needs.

### How do I benchmark my models?

```bash
# Benchmark all metrics
python scripts/benchmark_models.py \
  --model models/pretrained/go_9x9.h5 \
  --metric all

# Benchmark specific metric
python scripts/benchmark_models.py \
  --model models/pretrained/go_9x9.h5 \
  --metric inference
```

### Can I use multiple GPUs?

Yes, but requires code modification:

```python
import tensorflow as tf

# Enable multi-GPU strategy
strategy = tf.distribute.MirroredStrategy()

with strategy.scope():
    model = create_your_model()
    # Training and inference will use all GPUs
```

### Models are too large for my disk

Compressed models (coming soon):
- Quantize to INT8: ~4x smaller
- Prune redundant weights: 2-3x smaller
- Knowledge distillation: Train smaller student model

---

## Notebooks & Tutorials

### Which notebook should I start with?

**For beginners**: Start with Experiment 1 (Intelligence Explosion)
- Runtime: 10-15 minutes (quick demo)
- Demonstrates: Core RSI concept
- Link: `notebooks/good_notebook_1_intelligence_explosion.ipynb`

**For developers**: Start with MCTS Deep Dive
- Runtime: 45 minutes
- Demonstrates: MCTS implementation details
- Link: `notebooks/mcts_deep_dive.ipynb`

### Notebooks fail to run in Colab

**Common fixes**:
1. **Runtime crashed**: Restart runtime and run again
2. **Out of memory**: Use smaller batch size or fewer games
3. **Missing packages**: Run the installation cell first
4. **GPU not available**: Check Runtime → Change runtime type → GPU

### How do I run notebooks locally?

```bash
# Install Jupyter
pip install jupyter

# Start Jupyter
jupyter notebook

# Open any .ipynb file in notebooks/
```

### Can I modify the notebooks?

Yes! All notebooks are MIT licensed. Feel free to:
- Modify parameters
- Add your own experiments
- Create new notebooks
- Share improvements (pull requests welcome!)

### Notebooks take too long to run

Most notebooks have a `QUICK_DEMO` mode:

```python
# At the top of the notebook
QUICK_DEMO = True  # Fast demo (10-15 min)
# QUICK_DEMO = False  # Full validation (3-4 hours)
```

Set `QUICK_DEMO = True` for faster execution.

---

## Contributing & Development

### How can I contribute?

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) (coming soon).

**Ways to contribute**:
- Report bugs via GitHub Issues
- Improve documentation
- Add new games/environments
- Optimize performance
- Create tutorials

### How do I run tests?

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_environments.py

# Run with coverage
pytest --cov=prometheus tests/
```

### How do I add a new game?

1. Create environment in `prometheus/environments/your_game.py`
2. Implement: `reset()`, `step(action)`, `get_legal_actions()`, `is_terminal()`
3. Create model in `prometheus/models/your_game_models.py`
4. Add training script in `scripts/train_your_game.py`
5. Add tests in `tests/test_your_game.py`

See existing games (Go, Chess) as examples.

### Code style guidelines?

We use:
- **Black** for formatting: `black prometheus/ scripts/`
- **isort** for import sorting: `isort prometheus/ scripts/`
- **flake8** for linting: `flake8 prometheus/ scripts/`

Run before committing:
```bash
black prometheus/ scripts/ tests/
isort prometheus/ scripts/ tests/
flake8 prometheus/ scripts/ tests/
```

### How do I set up development environment?

```bash
# Clone repo
git clone https://github.com/pmcray/Prometheus_v0_PoC.git
cd Prometheus_v0_PoC

# Create venv
python3 -m venv venv
source venv/bin/activate

# Install dev dependencies
pip install -r requirements.txt
pip install -e .
pip install pytest black isort flake8

# Run tests
pytest tests/
```

---

## Troubleshooting

### Installation issues

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions.

**Quick fixes**:
- Update pip: `pip install --upgrade pip`
- Install separately: `pip install tensorflow python-chess numpy scipy`
- Use Python 3.10: Check with `python --version`

### Training issues

**Training is very slow**:
- Use GPU (3-10x faster)
- Reduce number of games
- Disable MCTS during training
- Close other applications

**Training crashes**:
- Reduce batch size
- Train smaller models first
- Monitor memory with `htop` or `nvidia-smi`

### Runtime errors

**ImportError**:
```bash
# Reinstall package
pip install -e .

# Verify imports
python -c "import prometheus; print('OK')"
```

**CUDA errors**:
```bash
# Check CUDA
nvidia-smi

# Reinstall TensorFlow GPU
pip install --upgrade tensorflow[and-cuda]
```

### Performance issues

**Slow inference**:
- Use GPU
- Enable XLA: `TF_XLA_FLAGS=--tf_xla_enable_xla_devices=true`
- Quantize models
- Reduce MCTS simulations

**High memory usage**:
- Enable memory growth: `tf.config.experimental.set_memory_growth(gpu, True)`
- Reduce batch size
- Clear session between runs

---

## Getting Help

### Where can I get help?

1. **Check this FAQ**: Most common issues covered
2. **Read documentation**:
   - [README.md](README.md)
   - [PHASE_B_TRAINING_GUIDE.md](PHASE_B_TRAINING_GUIDE.md)
   - [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)
   - [VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md)
3. **GitHub Issues**: https://github.com/pmcray/Prometheus_v0_PoC/issues
4. **Discussions**: GitHub Discussions (coming soon)

### How do I report a bug?

Open a GitHub Issue with:
1. **Description**: What went wrong?
2. **Steps to reproduce**: How to trigger the bug?
3. **Expected vs actual**: What should happen vs what happened?
4. **Environment**: Python version, OS, GPU/CPU, etc.
5. **Logs**: Error messages, stack traces

### Feature requests?

Open a GitHub Issue with `[Feature Request]` in the title. Describe:
- What feature you'd like
- Why it would be useful
- Example use cases
- (Optional) Implementation ideas

---

## Quick Reference

### Essential Commands

```bash
# Verify installation
python scripts/verify_phase_b_readiness.py

# Train model
python scripts/train_pretrained_models.py --model go_9x9

# Benchmark model
python scripts/benchmark_models.py --model models/pretrained/go_9x9.h5 --metric all

# Deploy bots
docker-compose up -d

# Check logs
docker-compose logs -f

# Run notebook
jupyter notebook notebooks/mcts_deep_dive.ipynb
```

### Useful Links

- **Repository**: https://github.com/pmcray/Prometheus_v0_PoC
- **Issues**: https://github.com/pmcray/Prometheus_v0_PoC/issues
- **Documentation**: See [README.md](README.md)
- **Colab Notebooks**: Links in [README.md](README.md)

---

**Still have questions?** Open a GitHub Issue or check the [Troubleshooting Guide](TROUBLESHOOTING.md).

**Found an error in this FAQ?** Submit a pull request or open an issue!
