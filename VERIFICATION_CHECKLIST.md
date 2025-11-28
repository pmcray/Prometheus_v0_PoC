# Prometheus Verification Checklist

Comprehensive checklist for verifying Prometheus functionality before deployment.

## ✅ Environment Setup

### Python Environment
- [ ] Python 3.10+ installed
- [ ] Virtual environment created
- [ ] All requirements installed: `pip install -r requirements.txt`
- [ ] Prometheus package installed: `pip install -e .`
- [ ] CLI command works: `prometheus --help`

### System Dependencies
- [ ] TensorFlow 2.15+ available
- [ ] NumPy installed
- [ ] Matplotlib working (for visualizations)
- [ ] GPU detected (if available): `python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"`

## ✅ Core Functionality

### Import Tests
```bash
python3 << 'EOF'
# Test core imports
from prometheus.models.go_models import PrometheusGoAgent, RandomGoAgent
from prometheus.models.chess_models import PrometheusChessAgent
from prometheus.environments.go import GoEnvironment
from prometheus.environments.chess_env import ChessEnvironment
from prometheus.configs import ModelBuilder
print("✓ All imports successful")
EOF
```

- [ ] Go models import
- [ ] Chess models import
- [ ] Environments import
- [ ] ModelBuilder import
- [ ] Training modules import
- [ ] Evaluation modules import

### Basic Model Creation
```bash
python3 << 'EOF'
from prometheus.configs import ModelBuilder

# Create Go agent
go_agent = ModelBuilder().go(9).prometheus().build()
print(f"✓ Go agent: {go_agent.model.count_params():,} parameters")

# Create Chess agent
chess_agent = ModelBuilder().chess().prometheus().build()
print(f"✓ Chess agent: {chess_agent.model.count_params():,} parameters")
EOF
```

- [ ] Go agent creation
- [ ] Chess agent creation
- [ ] Model parameters > 0
- [ ] No errors or warnings

### Environment Tests
```bash
python3 << 'EOF'
from prometheus.environments.go import GoEnvironment
from prometheus.environments.chess_env import ChessEnvironment

# Test Go environment
go_env = GoEnvironment(board_size=9)
state = go_env.reset()
legal_moves = go_env.get_legal_moves()
print(f"✓ Go environment: {len(legal_moves)} legal moves")

# Test Chess environment
chess_env = ChessEnvironment()
state = chess_env.reset()
legal_moves = chess_env.get_legal_moves()
print(f"✓ Chess environment: {len(legal_moves)} legal moves")
EOF
```

- [ ] Go environment reset
- [ ] Go legal moves > 0
- [ ] Chess environment reset
- [ ] Chess legal moves > 0

## ✅ Notebooks

### Notebook Validation
- [ ] All notebooks are valid JSON
- [ ] No syntax errors in code cells
- [ ] Colab badges present

### Notebook Execution (Recommended)
Test each notebook manually or with:
```bash
jupyter nbconvert --to notebook --execute notebooks/transfer_learning_tutorial.ipynb
```

- [ ] `transfer_learning_tutorial.ipynb` executes
- [ ] `deployment_workshop.ipynb` executes
- [ ] `performance_optimization.ipynb` executes
- [ ] All visualizations render correctly

## ✅ CLI Functionality

### Basic Commands
```bash
# Version
prometheus version

# Help
prometheus --help
prometheus train --help
prometheus evaluate --help

# Quickstart
prometheus quickstart
```

- [ ] `prometheus version` works
- [ ] `prometheus quickstart` displays guide
- [ ] All commands show help text
- [ ] No import errors

### Training Command (Light Test)
```bash
# Quick training test (2-3 minutes)
prometheus train --game go --board-size 9 --num-games 5 --strength light
```

- [ ] Training starts
- [ ] Model created
- [ ] Training completes
- [ ] Model saved

## ✅ Docker Setup

### Docker Build
```bash
# Build production image
docker build -f Dockerfile.production -t prometheus:test .
```

- [ ] Dockerfile builds successfully
- [ ] No build errors
- [ ] Image size reasonable (<2GB)

### Docker Run
```bash
# Test run
docker run --rm prometheus:test python prometheus_cli.py version
```

- [ ] Container starts
- [ ] Python runs
- [ ] Prometheus imports work
- [ ] Container exits cleanly

### Docker Compose
```bash
# Validate compose file
docker-compose config

# Test build
docker-compose build
```

- [ ] Compose file valid
- [ ] All services build
- [ ] No configuration errors

## ✅ Scripts

### Training Script
```bash
# Test training script (dry run)
python scripts/train_pretrained_models.py --help
```

- [ ] Script runs
- [ ] Help displays correctly
- [ ] No import errors

### Benchmark Script
```bash
# Test benchmark script
python scripts/benchmark_models.py --help
```

- [ ] Script runs
- [ ] Help displays correctly
- [ ] No import errors

## ✅ Integration Tests

### Quick Integration Test
```bash
python3 << 'EOF'
from prometheus.models.go_models import PrometheusGoAgent, RandomGoAgent
from prometheus.environments.go import GoEnvironment
from prometheus.configs import ModelBuilder

# Create and play a game
agent = ModelBuilder().go(9).prometheus().build()
env = GoEnvironment(board_size=9)
state = env.reset()

for move_num in range(10):
    move = agent.get_move(state)
    legal_moves = env.get_legal_moves()

    assert move in legal_moves or move == env.board_size**2, f"Illegal move: {move}"

    state, reward, done, info = env.step(move)
    if done:
        break

print(f"✓ Played {move_num+1} moves successfully")
EOF
```

- [ ] Agent creates legal moves
- [ ] Environment accepts moves
- [ ] Game progresses normally
- [ ] No crashes or errors

## ✅ Performance Benchmarks

### Inference Speed
Expected targets (CPU):
- 9×9 Go: < 100ms per inference
- 19×19 Go: < 500ms per inference
- Chess: < 200ms per inference

Test:
```bash
python scripts/benchmark_models.py \
  --model models/go_9x9.h5 \
  --metric inference \
  --num-runs 50
```

- [ ] Inference completes
- [ ] Speed within expected range
- [ ] No memory leaks

### MCTS Performance
Test:
```bash
python scripts/benchmark_models.py \
  --model models/go_9x9.h5 \
  --metric mcts \
  --mcts-sims 100 400 \
  --mcts-games 5
```

- [ ] MCTS runs
- [ ] Higher simulations = stronger play
- [ ] Reasonable speed (<10s per game)

## ✅ Deployment Readiness

### API Credentials
- [ ] `.env.example` file exists
- [ ] Know how to get OGS API token
- [ ] Know how to get Lichess API token
- [ ] Understand BOT account requirements

### Model Availability
- [ ] At least one trained model exists
- [ ] Model file < 100MB (reasonable size)
- [ ] Model can be loaded
- [ ] Model makes valid moves

### Deployment Scripts
- [ ] `scripts/deploy_ogs_bot.py` exists
- [ ] `scripts/deploy_lichess_bot.py` exists
- [ ] Scripts have usage instructions
- [ ] Can run `--help` successfully

## ✅ Documentation

### README
- [ ] README is comprehensive
- [ ] Installation instructions clear
- [ ] Usage examples work
- [ ] Links are valid

### Guides
- [ ] DOCKER_DEPLOYMENT.md exists
- [ ] Instructions are clear
- [ ] Examples are copy-paste ready

### Notebooks
- [ ] All notebooks have Colab badges
- [ ] Documentation is clear
- [ ] Code examples are complete

## ✅ Safety Checks

### Security
- [ ] `.env` in .gitignore
- [ ] No API tokens in code
- [ ] No hardcoded passwords
- [ ] Docker images don't expose secrets

### Code Quality
- [ ] No obvious bugs
- [ ] Error handling present
- [ ] Logging configured
- [ ] No debug print statements

## 📊 Verification Summary

Run this comprehensive check:

```bash
#!/bin/bash
echo "Running Prometheus verification..."

# 1. Environment
echo "1. Checking environment..."
python3 -c "import prometheus; print('✓ Prometheus installed')"
prometheus --version > /dev/null && echo "✓ CLI works"

# 2. Imports
echo "2. Testing imports..."
python3 -c "
from prometheus.models.go_models import PrometheusGoAgent
from prometheus.environments.go import GoEnvironment
from prometheus.configs import ModelBuilder
print('✓ All imports successful')
"

# 3. Model creation
echo "3. Testing model creation..."
python3 -c "
from prometheus.configs import ModelBuilder
agent = ModelBuilder().go(9).prometheus().build()
print(f'✓ Model created: {agent.model.count_params():,} params')
"

# 4. Docker
echo "4. Checking Docker..."
docker --version > /dev/null && echo "✓ Docker installed"
docker-compose --version > /dev/null && echo "✓ Docker Compose installed"

# 5. Notebooks
echo "5. Checking notebooks..."
python3 -c "
import json
from pathlib import Path
notebooks = Path('notebooks').glob('*.ipynb')
for nb in notebooks:
    json.load(open(nb))
print('✓ All notebooks valid')
"

echo ""
echo "✓ Verification complete!"
```

Save as `verify.sh`, make executable, and run:
```bash
chmod +x verify.sh
./verify.sh
```

## 🎯 Quick Verification (5 minutes)

Minimum checks for quick validation:

1. ✅ `pip install -e .` succeeds
2. ✅ `prometheus --version` works
3. ✅ `python3 -c "import prometheus"` succeeds
4. ✅ One notebook opens without errors
5. ✅ `docker build -f Dockerfile.production .` succeeds

## 🚀 Production Readiness Checklist

Before deploying to production:

- [ ] All verification checks pass
- [ ] Trained models available
- [ ] API credentials configured
- [ ] Monitoring setup
- [ ] Backup strategy in place
- [ ] Error handling tested
- [ ] Documentation reviewed
- [ ] Team trained on operations

## 📞 Support

If verification fails:

1. Check error messages carefully
2. Review installation instructions
3. Check dependencies: `pip list`
4. Try in clean environment
5. File issue: https://github.com/pmcray/Prometheus_v0_PoC/issues

## 📝 Notes

- GPU recommended but not required
- Training can take hours (use pre-trained models)
- Some features may need additional setup
- Deployment requires external accounts (OGS, Lichess)

---

**Last Updated**: 2025-11-28
**Version**: 0.69
