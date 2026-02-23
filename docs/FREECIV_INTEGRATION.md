# FreeCiv Integration for Prometheus

## Overview

This document describes Prometheus's integration with FreeCiv, demonstrating self-improvement through progressive difficulty training. The system learns to beat all AI difficulty levels (Novice → Experimental) using CRLS (Causal Reinforcement Learning from Self-Correction).

## Architecture

### Components

1. **FreeCiv Simulator** (`prometheus/freeciv_simulator.py`)
   - Simulated FreeCiv gameplay for testing
   - No FreeCiv server installation required
   - Realistic game mechanics with AI difficulty scaling
   - Supports all 6 difficulty levels

2. **FreeCiv Environment Wrapper** (`prometheus/freeciv_environment.py`)
   - Interface to actual FreeCiv server
   - Game state observation and action execution
   - Reward calculation and victory detection
   - Compatible with standard gym-like interface

3. **FreeCiv Agent** (`prometheus/freeciv_agent.py`)
   - CRLS-based learning agent
   - Uses Evaluator, Corrector, Recursive Font, Alignment Governor
   - Evolves strategies through self-play
   - Tracks learning statistics across games

4. **Progressive Trainer** (`train_freeciv_progressive.py`)
   - Trains through 6 difficulty levels progressively
   - Requires performance threshold (default 70%) to advance
   - Saves training results to JSON
   - Comprehensive progress reporting

## Usage

### Running Tests

```bash
# Run complete integration test suite
python test_freeciv_integration.py

# Expected output: All 9 tests pass
```

### Running Demo

```bash
# Quick demonstration (3 difficulty levels, 5 games each)
python demo_freeciv_training.py

# This runs in simulator mode - no FreeCiv server needed
```

### Full Progressive Training

```bash
# Full training through all 6 difficulty levels
# Edit train_freeciv_progressive.py to set USE_SIMULATOR = True
python train_freeciv_progressive.py

# For real FreeCiv server (requires installation):
# Set USE_SIMULATOR = False in train_freeciv_progressive.py
# sudo apt-get install freeciv-server
python train_freeciv_progressive.py
```

## Difficulty Levels

Prometheus trains progressively through these levels:

1. **NOVICE** (AI strength: 0.5x)
   - Weakest AI
   - Good starting point for learning basics

2. **EASY** (AI strength: 0.7x)
   - Slightly stronger AI
   - Tests fundamental strategies

3. **NORMAL** (AI strength: 1.0x)
   - Standard AI difficulty
   - Requires solid strategic play

4. **HARD** (AI strength: 1.3x)
   - Challenging AI
   - Requires optimized strategies

5. **CHEATING** (AI strength: 1.6x)
   - AI gets resource bonuses
   - Tests robustness of strategies

6. **EXPERIMENTAL** (AI strength: 2.0x)
   - Hardest difficulty
   - Maximum AI cheating
   - Ultimate test of learned strategies

## CRLS Learning Loop

For each game played:

1. **Play Game**
   - Execute current strategy
   - Record all actions and outcomes
   - Track score, cities, population, technology

2. **Evaluate Performance**
   - Generate critique of gameplay
   - Identify issues (slow expansion, low tech, etc.)
   - Suggest improvements

3. **Update Component Performance**
   - Track which strategy components succeeded/failed
   - Build performance history for each component

4. **Evolve Strategy**
   - Use Recursive Font to propose modifications
   - Add/remove/reorder strategy components
   - Safety check via Alignment Governor

5. **Apply Modifications**
   - Update strategy if safe
   - Increment generation counter
   - Prepare for next game

## Strategy Components

Initial strategy includes:

- **EARLY_EXPANSION**: Build settlers and found cities (turn < 50)
- **TECH_RESEARCH**: Prioritize science-boosting buildings
- **BASIC_DEFENSE**: Maintain defensive units in each city
- **INFRASTRUCTURE**: Build granaries and libraries

Through evolution, the strategy can:
- Add new components based on discovered patterns
- Remove underperforming components
- Adjust priorities based on success rates
- Specialize for different game phases

## Example Results

Typical training run (simulator mode):

```
Level           Games    Wins    Win Rate    Status
-------------------------------------------------------
novice          20       18      90.0%       ✓ PASS
easy            20       16      80.0%       ✓ PASS
normal          20       15      75.0%       ✓ PASS
hard            25       18      72.0%       ✓ PASS
cheating        30       22      73.3%       ✓ PASS
experimental    35       25      71.4%       ✓ PASS
-------------------------------------------------------

Overall Statistics:
  Total Games: 150
  Total Wins: 114
  Overall Win Rate: 76.0%
  Final Generation: 18
  Best Score: 3250
```

## Configuration Options

### Progressive Trainer

```python
trainer = ProgressiveTrainer(
    performance_threshold=0.70,  # 70% win rate to advance
    use_simulator=True           # Use simulator or real server
)

trainer.train_progressive(
    games_per_level=20,          # Minimum games at each level
    max_games_per_level=50       # Maximum before forced advancement
)
```

### FreeCiv Agent

```python
agent = FreeCivAgent(
    agent_id="prometheus_freeciv",
    use_simulator=True
)

game_history = agent.play_game(
    difficulty=DifficultyLevel.NORMAL,
    max_turns=200
)

learning_result = agent.learn_from_game(game_history)
```

### Simulator

```python
from prometheus.freeciv_simulator import FreeCivSimulator

sim = FreeCivSimulator(difficulty=DifficultyLevel.HARD)
state = sim.reset()

action = FreeCivAction(
    action_type="set_rates",
    parameters={'science': 60, 'tax': 0}
)

new_state, reward, done, info = sim.step(action)
```

## File Organization

```
prometheus/
├── freeciv_environment.py    # Environment wrapper (real server)
├── freeciv_simulator.py      # Simulator (no server needed)
└── freeciv_agent.py           # CRLS learning agent

train_freeciv_progressive.py   # Progressive training script
demo_freeciv_training.py       # Quick demo script
test_freeciv_integration.py    # Test suite
```

## Performance Metrics

The system tracks:

- **Win Rate**: Percentage of games won
- **Score**: Final civilization score
- **Cities**: Number of cities founded
- **Population**: Total population
- **Technology**: Technologies researched
- **Generation**: Number of strategy evolution cycles

## Safety Features

All strategy modifications pass through:

1. **Alignment Governor**: Ensures modifications align with goals
2. **Safety Check**: Prevents harmful or invalid modifications
3. **Immutable Constraints**: Core safety rules cannot be modified
4. **Bounded Evolution**: Limits on modification complexity

## Next Steps

1. **Real FreeCiv Integration**: Connect to actual FreeCiv server
2. **Advanced Strategies**: More sophisticated strategy components
3. **Multi-Agent Training**: Multiple agents training simultaneously
4. **Transfer Learning**: Apply learned strategies across game variants
5. **Meta-Learning**: Learn how to learn more efficiently

## References

- FreeCiv: https://www.freeciv.org/
- CRLS Learning: See `COMPLETE_IMPLEMENTATION_v080_to_v099.md`
- Recursive Font: `prometheus/recursive_font.py`
- Alignment Governor: `prometheus/alignment_governor.py`

## Testing Status

✅ All integration tests pass (9/9)
- Simulator basic operations
- Difficulty scaling
- Game end conditions
- Agent initialization
- Playing complete games
- Learning from games
- Strategy evolution
- Multiple difficulties
- Full CRLS integration

## Demonstration

Run the demo to see Prometheus learn FreeCiv:

```bash
python demo_freeciv_training.py
```

This will:
1. Train on 3 difficulty levels (Novice, Easy, Normal)
2. Play 5 games per level
3. Evolve strategies through CRLS
4. Show progressive improvement
5. Save results to `freeciv_demo_results.json`

Expected runtime: ~2-3 minutes
