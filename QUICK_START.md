# Prometheus Quick Start Guide

Get up and running with Prometheus in 5 minutes!

## Table of Contents

1. [First Steps (1 minute)](#first-steps)
2. [Training Your First Agent (3 minutes)](#training-your-first-agent)
3. [Deploying a Bot (5 minutes)](#deploying-a-bot)
4. [Next Steps](#next-steps)

---

## First Steps

### Option A: Google Colab (Easiest - No Installation!)

Click this button to run Prometheus instantly in your browser:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/pmcray/Prometheus_v0_PoC/blob/main/notebooks/tutorial_complete_guide.ipynb)

**That's it!** The notebook will automatically:
- Install all dependencies
- Load the Prometheus library
- Walk you through examples

**Recommended for**: First-time users, quick experiments, demos

---

### Option B: Local Installation (Development)

```bash
# Clone and setup (30 seconds)
git clone https://github.com/pmcray/Prometheus_v0_PoC.git
cd Prometheus_v0_PoC
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Verify installation (10 seconds)
pytest tests/ -v

# Success! You're ready to code
```

**Recommended for**: Developers, contributors, custom experiments

---

## Training Your First Agent

### 1. Go Agent (Fastest)

```python
from prometheus.configs import ModelBuilder
from prometheus.training.go_training import train_go_agent

# Create agent (uses sensible defaults)
agent = (ModelBuilder()
    .go(board_size=9)
    .strength('medium')
    .prometheus()
    .build())

# Train via self-play (3-5 minutes for 10 games)
trained_agent = train_go_agent(agent, num_games=10)

print(f"Training complete! Generation: {trained_agent.generation}")
```

**What happened:**
- Created a 9x9 Go agent with medium strength (~500K parameters)
- Trained through 10 self-play games
- Agent improved through recursive self-improvement

### 2. Add MCTS for +500 ELO (Optional)

```python
from prometheus.configs import create_mcts_agent

# Enhance agent with tree search
mcts_agent = create_mcts_agent(trained_agent, preset_name='standard')

print("MCTS enabled: +300-500 ELO improvement")
```

### 3. Evaluate Strength

```python
from prometheus.evaluation.benchmark import GoEvaluator
from prometheus.environments.go import GoEnvironment
from prometheus.models.go_models import RandomGoAgent

evaluator = GoEvaluator(board_size=9)
env = GoEnvironment(board_size=9)
baseline = RandomGoAgent(board_size=9)

# Play 20 games vs random baseline
result = evaluator.evaluate_matchup(
    trained_agent, baseline, env, num_games=20
)

print(f"Win rate: {result['agent1_win_rate']:.1%}")
print(f"ELO rating: {result['agent1_elo']:.0f}")
```

**Expected results:**
- Random baseline: 50% win rate, 1200 ELO
- After 10 games training: 60-70% win rate, 1250-1350 ELO
- With MCTS: 80-90% win rate, 1600+ ELO

---

## Deploying a Bot

### Lichess Chess Bot (Production-Ready)

```bash
# 1. Get API token
# Go to: https://lichess.org/account/oauth/token
# Create token with "bot:play" scope

# 2. Upgrade account to BOT
# Go to: https://lichess.org/account/bot

# 3. Deploy!
export LICHESS_TOKEN="lip_xxxxxxxxxxxx"
python scripts/deploy_lichess_bot.py \
    --agent prometheus \
    --time blitz rapid

# Bot is now live! Visit https://lichess.org/@/YOUR_BOT_NAME
```

### OGS Go Bot (Demo)

```bash
# 1. Create account at https://online-go.com

# 2. Deploy with MCTS
export OGS_USERNAME="your_username"
export OGS_PASSWORD="your_password"
python scripts/deploy_ogs_bot.py \
    --mcts \
    --simulations 400 \
    --sizes 9

# Bot is running locally, playing on OGS
```

**Note**: For production OGS deployment, see [OGS Integration Guide](prometheus/online_play/OGS_INTEGRATION_GUIDE.md)

---

## Common Tasks (Copy-Paste Ready)

### Save and Load Models

```python
# Save trained agent
agent.model.save('models/my_agent.h5')

# Load later
import tensorflow as tf
agent.model = tf.keras.models.load_model('models/my_agent.h5')
```

### Visualize Training

```python
from prometheus.visualization.training_dashboard import TrainingDashboard

dashboard = TrainingDashboard()

# During training loop
for episode in range(100):
    # ... training code ...

    dashboard.update({
        'policy_loss': loss_value,
        'win_rate': current_win_rate,
        'elo': current_elo,
        'generation': agent.generation
    })

# Show dashboard
dashboard.plot()
```

### Analyze a Game

```python
from prometheus.analysis import GoGameAnalyzer

analyzer = GoGameAnalyzer(agent=trained_agent)
analysis = analyzer.analyze_game(game_result)

# Print detailed report
analyzer.print_report(analysis)

# Shows:
# - Critical moments (evaluation swings)
# - Mistakes and blunders
# - Opening/middlegame/endgame strength
# - ASCII evaluation graph
```

### Transfer to Larger Board

```python
from prometheus.transfer import BoardSizeTransfer

transfer = BoardSizeTransfer()

# Transfer 9x9 model to 19x19
large_model = transfer.transfer(
    agent.model,
    source_size=9,
    target_size=19
)

# Create new agent with transferred weights
from prometheus.models.go_models import PrometheusGoAgent
large_agent = PrometheusGoAgent(board_size=19)
large_agent.model = large_model
```

### Optimize for Speed

```python
from prometheus.optimization import optimize_for_deployment

# Complete optimization pipeline
report = optimize_for_deployment(
    model=agent.model,
    model_path='models/optimized.h5',
    quantize=True  # 2-4x faster inference
)

print(f"Inference time: {report['benchmark']['mean_ms']:.1f} ms")
print(f"Model size reduced: {report['size_reduction']:.1%}")
```

---

## Troubleshooting

### "Import Error: No module named 'prometheus'"

**Fix**: Install from project root

```bash
cd Prometheus_v0_PoC
pip install -e .
# OR
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### "Tests failing"

**Fix**: Ensure dependencies installed

```bash
pip install -r requirements.txt
pytest tests/ -v
```

### "GPU not detected"

**Fix**: Check TensorFlow GPU setup

```python
import tensorflow as tf
print(tf.config.list_physical_devices('GPU'))

# If empty, install GPU-enabled TensorFlow
pip install tensorflow[and-cuda]
```

### "Bot won't connect"

**Lichess**:
- Verify account upgraded to BOT status
- Check token has 'bot:play' scope
- Ensure token not revoked

**OGS**:
- Verify credentials correct
- Check internet connection
- Try demo mode first: `--demo`

---

## Next Steps

### Learn More

1. **[Complete Tutorial](notebooks/tutorial_complete_guide.ipynb)** - Comprehensive 8-part guide
2. **[Executive Demo](notebooks/good_notebook_5_executive_demo.ipynb)** - Quick feature overview
3. **[Deployment Guide](scripts/README.md)** - Production bot deployment
4. **[API Reference](docs/)** - Full module documentation

### Try Advanced Features

```python
# 1. Tournament between agents
from prometheus.evaluation.benchmark import GoEvaluator

evaluator = GoEvaluator(board_size=9)
results = evaluator.tournament(
    agents=[agent1, agent2, agent3],
    env=env,
    games_per_matchup=50
)

# 2. Knowledge distillation (compress model)
from prometheus.transfer import KnowledgeDistillation

distiller = KnowledgeDistillation(teacher_model=large_model)
student = distiller.create_student(
    input_shape=(9, 9, 3),
    num_classes=82,
    compression_factor=0.5  # 50% of teacher size
)

# 3. Batch game analysis
from prometheus.analysis import BatchAnalyzer, GoGameAnalyzer

batch = BatchAnalyzer(GoGameAnalyzer(agent=agent))
for game in games:
    batch.add_game(game)

report = batch.get_aggregate_report()
batch.print_aggregate_report()
```

### Explore Notebooks

| Notebook | Focus | Time |
|----------|-------|------|
| [1. Intelligence Explosion](notebooks/good_notebook_1_intelligence_explosion.ipynb) | Online learning vs frozen weights | 10-15 min |
| [2. Dynamic ARC](notebooks/good_notebook_2_dynamic_arc_solver.ipynb) | Distribution shift adaptation | 15-20 min |
| [3. Strange Loop](notebooks/good_notebook_3_strange_loop.ipynb) | Meta-level self-modification | 10-15 min |
| [4. Chess](notebooks/good_notebook_4_chess_learning.ipynb) | Strategic game learning | 30-45 min |
| [5. Executive Demo](notebooks/good_notebook_5_executive_demo.ipynb) | All features overview | 5-10 min |
| [6. Tutorial](notebooks/tutorial_complete_guide.ipynb) | Complete beginner's guide | 30-45 min |

### Contribute

Found a bug? Have an idea? Want to add a feature?

1. **Report Issues**: https://github.com/pmcray/Prometheus_v0_PoC/issues
2. **Submit PRs**: Fork → Branch → Code → Test → Pull Request
3. **Discuss**: GitHub Discussions for questions and ideas

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Cheat Sheet

### Create Agents

```python
from prometheus.configs import ModelBuilder

# Go agent
go_agent = (ModelBuilder().go(9).strength('medium').prometheus().build())

# Go agent with MCTS
mcts_go = (ModelBuilder().go(9).strength('medium').with_mcts('standard').build())

# Chess agent
chess_agent = (ModelBuilder().chess().strength('medium').prometheus().build())
```

### Train

```python
from prometheus.training.go_training import train_go_agent
from prometheus.training.chess_training import train_chess_agent

# Go
trained = train_go_agent(go_agent, num_games=100)

# Chess
trained = train_chess_agent(chess_agent, num_games=100)
```

### Evaluate

```python
from prometheus.evaluation.benchmark import GoEvaluator

evaluator = GoEvaluator(board_size=9)
result = evaluator.evaluate_matchup(agent1, agent2, env, num_games=100)
print(f"ELO: {result['agent1_elo']:.0f}, Win rate: {result['agent1_win_rate']:.1%}")
```

### Deploy

```bash
# Lichess
export LICHESS_TOKEN="your_token"
python scripts/deploy_lichess_bot.py --agent prometheus

# OGS
export OGS_USERNAME="user" OGS_PASSWORD="pass"
python scripts/deploy_ogs_bot.py --mcts --simulations 400
```

### Test

```bash
# All tests
pytest tests/ -v

# Quick smoke test
pytest tests/ -k "initialization" -v

# With coverage
pytest tests/ --cov=prometheus
```

---

## Getting Help

**Documentation**:
- [README.md](README.md) - Complete overview
- [Tutorial](notebooks/tutorial_complete_guide.ipynb) - Hands-on guide
- [Scripts README](scripts/README.md) - Deployment guide
- [Architecture](prometheus/) - Code documentation

**Community**:
- GitHub Issues - Bug reports, features
- GitHub Discussions - Questions, ideas
- Discord (coming soon) - Real-time chat

**Contact**:
- Technical: Open a GitHub issue
- Business: partnerships@prometheus-ai.org
- Security: security@prometheus-ai.org

---

## What's Next?

You now know how to:
- ✅ Install Prometheus
- ✅ Train agents
- ✅ Evaluate performance
- ✅ Deploy bots online
- ✅ Use advanced features

**Recommended learning path**:

1. **Today (30 min)**: Run [Tutorial Notebook](notebooks/tutorial_complete_guide.ipynb)
2. **This week (2-4 hours)**: Train agents, deploy a bot
3. **This month (8+ hours)**: Contribute features, publish research

**Happy hacking!** 🚀

---

<div align="center">

**"The first ultraintelligent machine is the last invention that man need ever make."**

*Start your journey to recursive self-improvement today.*

[Get Started](#first-steps) • [Documentation](README.md) • [Community](https://github.com/pmcray/Prometheus_v0_PoC)

</div>
