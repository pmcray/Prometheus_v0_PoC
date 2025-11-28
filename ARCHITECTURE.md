# Prometheus Architecture Documentation

Complete system design and module interactions for v0.69.

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Architecture](#core-architecture)
3. [Module Descriptions](#module-descriptions)
4. [Data Flow](#data-flow)
5. [Design Decisions](#design-decisions)
6. [Extension Points](#extension-points)

---

## System Overview

Prometheus is designed as a **modular, production-ready AI system** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interfaces                          │
│  Notebooks │ CLI Scripts │ Python API │ Web Dashboard       │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                   Core Prometheus Library                    │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐    │
│  │   Models    │  │ Environments │  │   Training     │    │
│  │  Agents     │  │  Games       │  │  Self-Play     │    │
│  └─────────────┘  └──────────────┘  └────────────────┘    │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐    │
│  │ Evaluation  │  │  Analysis    │  │ Visualization  │    │
│  │  ELO, Stats │  │  Position    │  │  Dashboards    │    │
│  └─────────────┘  └──────────────┘  └────────────────┘    │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐    │
│  │  Transfer   │  │Optimization  │  │    Config      │    │
│  │   Learning  │  │  Quantize    │  │   Presets      │    │
│  └─────────────┘  └──────────────┘  └────────────────┘    │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                  External Services                           │
│  Lichess │ OGS │ Stockfish │ KataGo │ Cloud Storage        │
└─────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Modularity**: Each module has a single, well-defined responsibility
2. **Extensibility**: Easy to add new games, agents, or features
3. **Production-Ready**: Complete testing, logging, error handling
4. **Research-Friendly**: Clean APIs for experimentation

---

## Core Architecture

### 1. Agent Hierarchy

```
                    BaseAgent (Abstract)
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   StaticAgent    PrometheusAgent    RandomAgent
        │                 │
        │                 │
   (Frozen weights)  (Online learning)
        │                 │
        └────────┬────────┘
                 │
            MCTS Wrapper
        (Tree search enhancement)
```

**Key Differences**:
- **Static**: Weights frozen after pretraining (like GPT-4)
- **Prometheus**: Continues learning during deployment
- **MCTS**: Wraps any agent, adds tree search (+500 ELO)

### 2. Environment Interface

```python
class GameEnvironment:
    """Standard RL interface for all games."""

    def reset() -> state:
        """Start new game, return initial state."""

    def step(action) -> (state, reward, done, info):
        """Execute action, return next state."""

    def get_legal_moves() -> List[action]:
        """Return all legal actions."""

    def get_state() -> np.ndarray:
        """Return current state as neural network input."""
```

**Supported Games**:
- Chess (8x8, UCI interface)
- Go (9x9, 13x13, 19x19, capture/ko/superko rules)

### 3. Training Pipeline

```
Self-Play Loop:
┌──────────────────────────────────────────────────┐
│ 1. Agent plays against itself                    │
│ 2. Collect (state, policy, value) tuples         │
│ 3. Store in replay buffer                        │
│ 4. Train on batch from buffer                    │
│ 5. Update agent weights                          │
│ 6. Increment generation → Go to 1               │
└──────────────────────────────────────────────────┘
```

**Features**:
- Experience replay for stability
- Temperature annealing for exploration
- Automatic checkpointing
- Real-time visualization

---

## Module Descriptions

### prometheus/models/

**Purpose**: Neural network architectures and agent implementations

**Files**:
- `architectures.py` - Base CNN/ResNet builders, Static/Prometheus agents
- `go_models.py` - Go-specific policy-value networks
- `go_mcts.py` - Monte Carlo Tree Search implementation

**Key Classes**:

```python
class StaticAgent:
    """Frozen-weight agent (Foundation Model style)."""
    def __init__(self, input_shape, num_classes):
        self.model = create_resnet(...)
        self.trainable = False

    def pretrain(self, X_train, y_train):
        """One-time pretraining."""
        self.model.fit(X_train, y_train)
        self.trainable = False  # Freeze weights

    def predict(self, state):
        """Inference only."""
        return self.model.predict(state)

class PrometheusAgent(StaticAgent):
    """Online learning agent (recursive self-improvement)."""
    def __init__(self, input_shape, num_classes):
        super().__init__(input_shape, num_classes)
        self.trainable = True
        self.generation = 0

    def online_learning_round(self, X_new, y_new):
        """Continue learning on new data."""
        self.model.fit(X_new, y_new)
        self.generation += 1
```

### prometheus/environments/

**Purpose**: Game rules and RL interfaces

**Files**:
- `chess.py` - Chess board, UCI interface, Stockfish integration
- `go.py` - Go board with complete rules (capture, ko, superko, scoring)

**Key Features**:
- Complete rule implementation
- Illegal move detection
- Game state encoding for neural networks
- Efficient board representation

**Example**:

```python
class GoEnvironment:
    def __init__(self, board_size=9, komi=7.5):
        self.board = GoBoard(size=board_size, komi=komi)

    def step(self, move):
        """Execute move, return (state, reward, done, info)."""
        if not self.is_legal(move):
            return state, -1, True, {'illegal': True}

        self.board.play_move(*move)
        state = self.get_state()
        done = self.board.is_game_over()
        reward = self._calculate_reward()

        return state, reward, done, {}
```

### prometheus/training/

**Purpose**: Training loops and self-play

**Files**:
- `loops.py` - Generic training utilities
- `chess_training.py` - Chess self-play
- `go_training.py` - Go self-play and matchmaking

**Key Functions**:

```python
def train_go_agent(agent, num_games=100, verbose=True):
    """
    Train via self-play.

    Pipeline:
    1. Play game (agent vs self)
    2. Collect (state, policy, value) samples
    3. Train on samples
    4. Repeat
    """
    for game_num in range(num_games):
        # Self-play
        states, policies, values = play_self_play_game(agent)

        # Train
        agent.model.fit(states, [policies, values])
        agent.generation += 1

    return agent
```

### prometheus/evaluation/

**Purpose**: Benchmarking and performance measurement

**Files**:
- `benchmark.py` - ELO ratings, tournaments, statistical tests

**Key Classes**:

```python
class ELOCalculator:
    """Standard ELO rating system."""
    def expected_score(self, rating_a, rating_b):
        return 1.0 / (1.0 + 10**((rating_b - rating_a) / 400))

    def update_ratings(self, agent_a, agent_b, score_a):
        """Update after game (score_a: 1=win, 0.5=draw, 0=loss)."""
        expected = self.expected_score(rating_a, rating_b)
        new_rating = rating_a + K * (score_a - expected)
        return new_rating

class GoEvaluator:
    """Comprehensive agent evaluation."""
    def evaluate_matchup(self, agent1, agent2, env, num_games):
        """Play num_games, return stats."""

    def calculate_statistical_significance(self, results):
        """Wilson score, z-test, confidence intervals."""

    def tournament(self, agents, env):
        """Round-robin tournament."""
```

### prometheus/analysis/

**Purpose**: Post-game analysis and insights

**Files**:
- `game_analyzer.py` - Position evaluation, mistake detection

**Features**:
- Move-by-move evaluation
- Critical moment identification
- Mistake/blunder classification
- Opening/middlegame/endgame analysis

```python
class GoGameAnalyzer:
    def analyze_game(self, game_result):
        """
        Analyze complete game.

        Returns:
        - critical_moments: Large evaluation swings
        - mistakes: Suboptimal moves
        - statistics: Overall metrics
        """
```

### prometheus/visualization/

**Purpose**: Real-time dashboards and plots

**Files**:
- `plots.py` - Performance comparisons
- `training_dashboard.py` - 8-panel real-time monitoring
- `chess_viz.py` - Chess board rendering
- `attention.py` - GradCAM attention maps

**Features**:
- Live training metrics
- Multi-agent comparison
- Move heatmaps
- Evaluation graphs

### prometheus/transfer/

**Purpose**: Knowledge transfer across domains

**Files**:
- `transfer_learning.py` - Board size, domain, cross-game transfer

**Techniques**:
- Layer weight copying
- Progressive fine-tuning
- Knowledge distillation
- Feature extraction

```python
class BoardSizeTransfer:
    def transfer(self, source_model, source_size, target_size):
        """
        Transfer from small to large board.

        Process:
        1. Copy convolutional layers (size-independent)
        2. Reinitialize policy/value heads (size-dependent)
        3. Fine-tune on target size
        """
```

### prometheus/optimization/

**Purpose**: Performance and efficiency

**Files**:
- `performance.py` - Quantization, caching, batch inference

**Features**:
- INT8/FLOAT16 quantization (2-4x faster)
- Position caching for MCTS
- Batch processing for parallel games
- GPU memory management

```python
class PositionCache:
    """LRU cache for position evaluations."""
    def get(self, state):
        """Return cached (policy, value) or None."""

class ModelOptimizer:
    """Model compression and speedup."""
    def quantize_int8(self, model):
        """Convert to INT8 (4x smaller, faster)."""
```

### prometheus/configs/

**Purpose**: Preset configurations

**Files**:
- `pretrained_models.py` - Model presets, hyperparameters, ModelBuilder API

**Presets**:
- Model architectures (light/medium/strong)
- Training schedules (quick/standard/extensive)
- MCTS settings (fast/standard/strong/alphazero)

```python
class ModelBuilder:
    """Fluent API for creating configured agents."""
    def go(self, board_size=9):
        """Configure for Go."""
        return self

    def strength(self, level='medium'):
        """Set strength level."""
        return self

    def with_mcts(self, preset='standard'):
        """Add MCTS."""
        return self

    def build(self):
        """Create configured agent."""
        return agent
```

---

## Data Flow

### 1. Training Data Flow

```
Game Play
   ↓
State Encoding (GoEnvironment.get_state())
   ↓
Neural Network (Agent.model.predict())
   ↓
Policy + Value Predictions
   ↓
Move Selection (with temperature)
   ↓
Game Outcome
   ↓
Experience Replay Buffer
   ↓
Batch Sampling
   ↓
Network Training (Agent.model.fit())
   ↓
Weight Update
   ↓
Generation Increment
```

### 2. MCTS Search Flow

```
Root Position
   ↓
Selection (PUCT formula)
   ↓
Expansion (add children)
   ↓
Evaluation (neural network)
   ↓
Backpropagation (update ancestors)
   ↓
Repeat N simulations
   ↓
Return visit counts as policy
```

### 3. Deployment Flow

```
Trained Model (.h5 file)
   ↓
Load into Agent
   ↓
Deploy Script (deploy_ogs_bot.py)
   ↓
Connect to Platform (Lichess/OGS)
   ↓
Receive Game Challenge
   ↓
Accept → Create Game State
   ↓
Loop:
  Receive Opponent Move
  Update State
  Get Agent Move (with MCTS if enabled)
  Send Move
  Until game ends
   ↓
Report Result
```

---

## Design Decisions

### 1. Why Separate Static and Prometheus Agents?

**Decision**: Create two agent classes instead of a single configurable agent.

**Rationale**:
- Clear distinction between frozen and online learning paradigms
- Prevents accidental weight updates in production
- Makes comparison experiments explicit
- Matches real-world deployment patterns (FM vs adaptive systems)

### 2. Why Standard RL Interface?

**Decision**: Use standard `reset()`, `step()`, `get_state()` interface.

**Rationale**:
- Familiar to RL researchers
- Compatible with OpenAI Gym, Gymnasium
- Easy to add new games
- Clean separation of game rules and agent logic

### 3. Why Policy-Value Network Architecture?

**Decision**: Two-headed network (policy + value) instead of separate networks.

**Rationale**:
- Shared representation learning (AlphaGo Zero-style)
- More efficient than separate networks
- Proven effective in AlphaGo/AlphaZero
- Natural fit for MCTS

### 4. Why Modular MCTS Implementation?

**Decision**: MCTS as wrapper that enhances any agent.

**Rationale**:
- Reusable across different base agents
- Clear performance attribution
- Easy to compare with/without MCTS
- Flexible hyperparameter tuning

### 5. Why Comprehensive Test Suite?

**Decision**: Unit tests for all game rules and agent behaviors.

**Rationale**:
- Catch regressions early
- Document expected behavior
- Enable confident refactoring
- Production-quality code

---

## Extension Points

### Adding a New Game

```python
# 1. Create environment
class NewGameEnvironment:
    def __init__(self, ...):
        self.state = ...

    def reset(self):
        return initial_state

    def step(self, action):
        return next_state, reward, done, info

    def get_legal_moves(self):
        return legal_actions

    def get_state(self):
        return neural_network_input

# 2. Create agent (reuse architectures)
class NewGameAgent(PrometheusAgent):
    def __init__(self):
        super().__init__(input_shape=..., num_classes=...)

# 3. Add training script
def train_new_game_agent(agent, num_games):
    # Reuse training loop patterns
    ...

# 4. Add tests
class TestNewGameEnvironment:
    def test_rules(self):
        ...
```

### Adding a New Agent Type

```python
class MyCustomAgent:
    """Your custom agent implementation."""

    def get_move(self, state, legal_moves, temperature=1.0):
        """Required: return selected move."""

    def predict(self, state):
        """Optional: return (policy, value)."""

    def train(self, data):
        """Optional: update weights."""
```

### Adding a New Optimization

```python
# In prometheus/optimization/performance.py

class MyOptimizer:
    """Your optimization technique."""

    def optimize(self, model):
        """Apply optimization."""
        ...
        return optimized_model
```

---

## Performance Characteristics

### Model Sizes

| Configuration | Parameters | Memory | Inference (CPU) | Inference (GPU) |
|---------------|------------|---------|-----------------|-----------------|
| Go 9x9 Light | ~100K | 400 KB | 5 ms | 1 ms |
| Go 9x9 Medium | ~500K | 2 MB | 15 ms | 3 ms |
| Go 9x9 Strong | ~2M | 8 MB | 50 ms | 8 ms |
| Go 19x19 Strong | ~10M | 40 MB | 200 ms | 30 ms |

### Training Times

| Task | Games | Time (CPU) | Time (GPU) |
|------|-------|------------|------------|
| Quick test | 10 | 2 min | 30 sec |
| Standard | 100 | 20 min | 5 min |
| Production | 1000 | 3 hours | 45 min |

### MCTS Impact

| Simulations | Time/Move | ELO Gain |
|-------------|-----------|----------|
| 100 | 1-2s | +200 |
| 400 | 5-10s | +350 |
| 800 | 10-20s | +500 |
| 1600 | 30-60s | +600 |

---

## Security Considerations

1. **Input Validation**: All user inputs validated before processing
2. **Model Loading**: Only load models from trusted sources
3. **API Tokens**: Never commit tokens to version control
4. **Network Access**: Bot credentials stored in environment variables
5. **Resource Limits**: Timeouts prevent infinite loops

---

## Future Architecture

Planned improvements for v1.0:

1. **Distributed Training**: Multi-GPU, multi-machine support
2. **Model Zoo**: Central repository of pretrained models
3. **REST API**: HTTP interface for model serving
4. **Streaming**: Real-time game streaming and analysis
5. **Cloud Deployment**: Docker containers, Kubernetes orchestration

---

## References

- **AlphaGo Zero**: Silver et al. (2017) - Policy-value network architecture
- **MCTS**: Browne et al. (2012) - Monte Carlo Tree Search survey
- **ELO System**: Elo (1978) - Rating system for chess
- **Transfer Learning**: Yosinski et al. (2014) - How transferable are features

---

## Contributing to Architecture

When proposing architectural changes:

1. **Document**: Explain rationale and trade-offs
2. **Test**: Add comprehensive tests
3. **Benchmark**: Measure performance impact
4. **Discuss**: Open GitHub issue for feedback
5. **Iterate**: Incorporate review feedback

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

<div align="center">

**Clean Architecture → Powerful Results**

*Well-designed systems enable great research.*

</div>
