# Prometheus Examples

Ready-to-run example scripts demonstrating common workflows.

## Available Examples

| Script | Purpose | Time | Complexity |
|--------|---------|------|------------|
| [train_go_agent.py](#train-go-agent) | Train Go agent from scratch | 5-30 min | ⭐ Easy |
| [evaluate_agents.py](#evaluate-agents) | Compare multiple agents | 10-60 min | ⭐⭐ Medium |
| [transfer_learning.py](#transfer-learning) | Transfer between board sizes | 15-45 min | ⭐⭐⭐ Advanced |

---

## train_go_agent.py

Complete training pipeline: create → train → evaluate → save.

### Basic Usage

```bash
# Train 9x9 Go agent (5 minutes)
python examples/train_go_agent.py --num-games 100

# Train with MCTS enhancement
python examples/train_go_agent.py --num-games 100 --mcts

# Train strong 19x19 agent (30+ minutes)
python examples/train_go_agent.py \
    --board-size 19 \
    --strength strong \
    --num-games 500 \
    --mcts \
    --evaluate
```

### All Options

```bash
python examples/train_go_agent.py \
    --board-size 9           # Board size: 9, 13, or 19
    --num-games 100          # Training games
    --strength medium        # Agent strength: light, medium, strong
    --mcts                   # Enable MCTS
    --mcts-sims 400          # MCTS simulations per move
    --output models/my.h5    # Output path
    --evaluate               # Evaluate vs random
    --eval-games 50          # Evaluation games
    --visualize              # Show training dashboard
```

### Example Output

```
======================================================================
GO AGENT TRAINING PIPELINE
======================================================================

1. Creating agent...
   Board size: 9x9
   Strength: medium
   MCTS: Yes
   ✓ Agent created: 513,602 parameters

2. Training (100 games)...
   Progress: 10/100 games
   ...
   ✓ Training complete
   ✓ Final generation: 100

3. Adding MCTS (400 simulations)...
   ✓ MCTS enabled (preset: standard)
   ✓ Expected +300-500 ELO improvement

4. Evaluating (50 games vs random)...
   Results:
   Win rate: 85.0%
   ELO rating: 1580
   Wins: 42
   Losses: 7
   Draws: 1

5. Saving model...
   ✓ Model saved: models/go_agent.h5

======================================================================
TRAINING COMPLETE
======================================================================
Model: models/go_agent.h5
Board size: 9x9
Generation: 100
ELO: 1580
Win rate: 85.0%
```

---

## evaluate_agents.py

Compare multiple trained agents with tournaments and statistics.

### Basic Usage

```bash
# Compare two agents
python examples/evaluate_agents.py \
    --agents models/agent1.h5 models/agent2.h5 \
    --games-per-matchup 50

# Full tournament with random baseline
python examples/evaluate_agents.py \
    --agents models/*.h5 \
    --tournament \
    --include-random \
    --visualize
```

### All Options

```bash
python examples/evaluate_agents.py \
    --agents model1.h5 model2.h5 model3.h5  # Agent models
    --board-size 9                          # Board size
    --games-per-matchup 50                  # Games per pair
    --include-random                        # Add random baseline
    --tournament                            # Round-robin tournament
    --visualize                             # Show comparison dashboard
```

### Example Output

```
======================================================================
AGENT EVALUATION & COMPARISON
======================================================================

1. Loading agents...
   ✓ Loaded: agent1
   ✓ Loaded: agent2
   ✓ Loaded: agent3
   ✓ Added: Random Baseline

2. Running tournament...
   Matchups: 6
   Games per matchup: 50
   Total games: 300

   agent1 vs agent2...
   agent1 vs agent3...
   agent1 vs Random Baseline...
   agent2 vs agent3...
   agent2 vs Random Baseline...
   agent3 vs Random Baseline...

   Tournament complete!

======================================================================
EVALUATION RESULTS
======================================================================

Rank   Agent                     W-L-D        Points   ELO
----------------------------------------------------------------------
1      agent3                    120-30-0     120.0    1650
2      agent1                    90-60-0      90.0     1520
3      agent2                    60-90-0      60.0     1380
4      Random Baseline           30-120-0     30.0     1200
======================================================================
```

---

## transfer_learning.py

Transfer knowledge from small to large board sizes.

### Basic Usage

```bash
# Transfer 9x9 to 19x19
python examples/transfer_learning.py \
    --source models/go_9x9.h5 \
    --source-size 9 \
    --target-size 19 \
    --fine-tune-games 50 \
    --evaluate

# Transfer 9x9 to 13x13 without fine-tuning
python examples/transfer_learning.py \
    --source models/go_9x9.h5 \
    --target-size 13 \
    --fine-tune-games 0 \
    --output models/go_13x13_base.h5
```

### All Options

```bash
python examples/transfer_learning.py \
    --source models/go_9x9.h5   # Source model
    --source-size 9              # Source board size
    --target-size 19             # Target board size
    --fine-tune-games 50         # Fine-tuning games
    --output models/go_19.h5     # Output path
    --evaluate                   # Evaluate before/after
```

### Example Output

```
======================================================================
TRANSFER LEARNING PIPELINE
======================================================================

1. Loading source model...
   Source: models/go_9x9.h5
   Board size: 9x9
   ✓ Loaded: 513,602 parameters

2. Transferring to 19x19...
  Transferring model: 9x9 → 19x19
  ✓ Transferred: conv2d_1
  ✓ Transferred: batch_normalization_1
  ...
  ○ Skipped (incompatible): policy_head
  ✓ Transfer complete
  ✓ Target model: 2,103,482 parameters

3. Creating target agent...
   ✓ Agent created

4. Evaluating before fine-tuning...
   Before fine-tuning:
   Win rate: 62.0%
   ELO: 1280

5. Fine-tuning (50 games)...
   Progress: 10/50 games
   ...
   ✓ Fine-tuning complete
   ✓ Generation: 50

6. Evaluating after fine-tuning...
   After fine-tuning:
   Win rate: 74.0%
   ELO: 1420

   Improvement:
   ELO: +140
   Win rate: +12.0%

7. Saving model...
   ✓ Saved: models/go_19x19_transferred.h5

======================================================================
TRANSFER COMPLETE
======================================================================
Source: 9x9
Target: 19x19
Output: models/go_19x19_transferred.h5

Performance:
  Before: 62.0% win rate, 1280 ELO
  After:  74.0% win rate, 1420 ELO
  Gain:   +12.0% win rate, +140 ELO
```

---

## Tips & Tricks

### 1. Quick Testing

```bash
# Test with minimal resources
python examples/train_go_agent.py --num-games 10 --board-size 9
```

### 2. Production Training

```bash
# High-quality agent (may take hours)
python examples/train_go_agent.py \
    --board-size 19 \
    --strength strong \
    --num-games 1000 \
    --mcts \
    --mcts-sims 800 \
    --evaluate \
    --visualize
```

### 3. Batch Evaluation

```bash
# Evaluate all models in directory
python examples/evaluate_agents.py \
    --agents models/*.h5 \
    --tournament \
    --include-random
```

### 4. Progressive Training

```bash
# 1. Train on 9x9
python examples/train_go_agent.py \
    --board-size 9 \
    --num-games 200 \
    --output models/go_9.h5

# 2. Transfer to 13x13
python examples/transfer_learning.py \
    --source models/go_9.h5 \
    --target-size 13 \
    --fine-tune-games 100 \
    --output models/go_13.h5

# 3. Transfer to 19x19
python examples/transfer_learning.py \
    --source models/go_13.h5 \
    --source-size 13 \
    --target-size 19 \
    --fine-tune-games 200 \
    --output models/go_19.h5
```

---

## Integration with Other Tools

### Use with Deployment Scripts

```bash
# Train and deploy
python examples/train_go_agent.py --output models/my_bot.h5
python scripts/deploy_ogs_bot.py --model models/my_bot.h5 --mcts
```

### Use with Analysis Tools

```python
# In Python script or notebook
from prometheus.analysis import GoGameAnalyzer, BatchAnalyzer
import tensorflow as tf

# Load your trained model
agent = PrometheusGoAgent(board_size=9)
agent.model = tf.keras.models.load_model('models/my_agent.h5')

# Analyze games
analyzer = GoGameAnalyzer(agent=agent)
batch = BatchAnalyzer(analyzer)

# Add games from training
for game in training_games:
    batch.add_game(game)

# Get aggregate report
batch.print_aggregate_report()
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'prometheus'"

**Fix**: Run from project root or install in development mode

```bash
cd Prometheus_v0_PoC
pip install -e .
# OR
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### "FileNotFoundError: models/go_agent.h5"

**Fix**: Create models directory

```bash
mkdir -p models
```

### "Out of memory" during training

**Fix**: Reduce batch size or use smaller model

```bash
# Use light model instead of medium/strong
python examples/train_go_agent.py --strength light
```

### Script hangs during MCTS

**Fix**: Reduce MCTS simulations

```bash
# Use fewer simulations
python examples/train_go_agent.py --mcts --mcts-sims 100
```

---

## Advanced Usage

### Custom Training Loop

```python
# examples/custom_training.py
from prometheus.configs import ModelBuilder
from prometheus.training.go_training import train_go_agent
from prometheus.visualization.training_dashboard import TrainingDashboard

# Create agent
agent = (ModelBuilder()
    .go(board_size=9)
    .strength('medium')
    .prometheus()
    .build())

# Setup dashboard
dashboard = TrainingDashboard()

# Custom training with checkpoints
for generation in range(10):
    # Train 10 games
    agent = train_go_agent(agent, num_games=10)

    # Update dashboard
    dashboard.update({
        'generation': agent.generation,
        'elo': estimate_elo(agent),
        'win_rate': measure_win_rate(agent)
    })

    # Save checkpoint
    agent.model.save(f'models/checkpoint_gen{generation}.h5')

# Show results
dashboard.plot()
```

---

## Creating Your Own Examples

Template for new example scripts:

```python
#!/usr/bin/env python3
"""
Example: Your Feature Name

Description of what this demonstrates.

Usage:
    python examples/your_example.py [options]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Your imports here
from prometheus.models.go_models import PrometheusGoAgent

def main():
    """Main pipeline."""
    parser = argparse.ArgumentParser(description='Your description')
    parser.add_argument('--your-arg', type=str, help='Description')
    args = parser.parse_args()

    print("="*70)
    print("YOUR EXAMPLE NAME")
    print("="*70)

    # Your code here
    print("\nDone!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
```

---

## Next Steps

- **Notebooks**: Interactive alternatives to these scripts
- **Documentation**: See [README.md](../README.md) for full documentation
- **Deployment**: Use [scripts/](../scripts/) for bot deployment
- **Contribute**: Add your own examples!

---

## License

MIT License - same as main Prometheus project
