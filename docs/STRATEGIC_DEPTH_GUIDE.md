# How to Increase Strategic Depth in Evolution

## Current Problem

**Random vs Random = ~50% baseline → Limited room for improvement**

The current demo uses RandomOpponent, which caps learning at ~50% win rate. Agents can't discover strategic depth because the opponent has none.

## Solutions for Deeper Learning

### 1. **Use Stronger Opponents** ⭐ Most Important

Replace `RandomOpponent` with strategic opponents:

#### A. Heuristic Opponent (Medium Difficulty)
```python
from benchmarks.strategic_opponents import HeuristicOpponent

# In connect4_benchmark.py line 55:
opponent = HeuristicOpponent()  # Instead of RandomOpponent()
```

**Expected learning curve:**
- Gen 1: 10-20% (random agents struggle)
- Gen 5: 30-50% (learning basic tactics)
- Gen 10: 50-70% (strong tactical play)

**Strategy it uses:**
1. Win if possible (check for 3-in-a-row)
2. Block opponent's winning moves
3. Prefer center columns
4. Avoid edges unless necessary

#### B. Minimax Opponent (Hard Difficulty)
```python
from benchmarks.strategic_opponents import MinimaxOpponent

opponent = MinimaxOpponent(depth=3)  # depth=1-4
```

**Difficulty levels:**
- Depth 1: Easy (looks 1 move ahead)
- Depth 2: Medium (looks 2 moves ahead)
- Depth 3: Hard (looks 3 moves ahead)
- Depth 4: Expert (very strong)

**Expected learning curve vs Minimax-Depth3:**
- Gen 1: 0-5% (nearly impossible for random)
- Gen 20: 10-20% (discovering basic tactics)
- Gen 50: 30-50% (solid strategic play)

#### C. Adaptive Opponent (Progressive Difficulty)
```python
from benchmarks.strategic_opponents import AdaptiveOpponent

opponent = AdaptiveOpponent(initial_level=1)
# Automatically adjusts difficulty based on agent performance
```

**Auto-adjusts:**
- Win rate > 70% → Increase difficulty
- Win rate < 30% → Decrease difficulty
- Creates optimal learning gradient

### 2. **Opponent Curriculum** (Recommended)

Train against progressively harder opponents:

```python
CURRICULUM = [
    ("Random", RandomOpponent(), 0.70),           # Stage 1: Learn basics
    ("Heuristic", HeuristicOpponent(), 0.60),     # Stage 2: Learn tactics
    ("Minimax-D2", MinimaxOpponent(2), 0.50),     # Stage 3: Strategy
    ("Minimax-D3", MinimaxOpponent(3), 0.40),     # Stage 4: Advanced
]

for stage_name, opponent, target in CURRICULUM:
    print(f"Training against {stage_name}...")
    # Run evolution with this opponent
    # When target reached, move to next stage
```

**Benefits:**
- Prevents frustration (too hard too fast)
- Builds skills progressively
- Each stage unlocks new strategic insights

### 3. **Increase Population & Generations**

Current: 6 agents × 8 generations = 48 total agents
Recommended: 20 agents × 30 generations = 600 total agents

```python
CONFIG = EvolutionConfig(
    population_size=20,      # More diversity
    generations=30,          # More time to learn
    mutation_rate=0.6,
    elitism_count=3,         # Keep top 3
    tournament_size=5,
    convergence_threshold=0.70,
    stagnation_generations=8
)
```

**Impact:**
- More diversity → Better exploration
- More generations → Better optimization
- Larger tournament → Stronger selection pressure

### 4. **Improve Mutation Strategy**

Current mutations are random code changes. Enhance with:

#### A. Guided Mutations
```python
mutation_prompts = [
    "Add heuristic to prefer center columns",
    "Implement blocking opponent's wins",
    "Add pattern recognition for threats",
    "Optimize opening move strategy",
]
```

#### B. Crossover Weights
Favor crossing high-fitness parents:
```python
# In SMM crossover selection
parent1 = tournament_select(population, k=5)  # Larger tournament
parent2 = tournament_select(population, k=5)
```

### 5. **Multi-Objective Fitness**

Don't just optimize win rate - add strategic metrics:

```python
def evaluate_agent(agent):
    win_rate = play_games(agent, opponent, 100)

    # Additional metrics
    avg_moves = count_avg_moves(agent)      # Efficiency
    center_control = measure_center(agent)  # Positioning
    blocking_rate = measure_blocks(agent)   # Defensive skill

    # Weighted fitness
    fitness = (
        0.7 * win_rate +
        0.1 * center_control +
        0.1 * blocking_rate +
        0.1 * (1.0 / avg_moves)  # Prefer faster wins
    )

    return fitness
```

**Benefits:**
- Rewards strategic play, not just wins
- Encourages well-rounded agents
- Prevents overfitting to single opponent

### 6. **Self-Play Training**

Let agents play against themselves or past generations:

```python
# Co-evolution: agents compete against each other
def evaluate_population(agents):
    for i, agent in enumerate(agents):
        opponents = agents[:i] + agents[i+1:]  # All except self
        win_rate = round_robin(agent, opponents)
        agent.fitness = win_rate

# Historical opponents: play against past champions
champion_history = []

for gen in range(generations):
    # Regular evaluation
    evaluate(population, current_opponent)

    # Also test against past champions
    if champion_history:
        for agent in population:
            historical_score = play_vs_champions(agent, champion_history)
            agent.fitness = 0.7 * agent.fitness + 0.3 * historical_score

    champion_history.append(best_agent.copy())
```

### 7. **Feature Engineering**

Give agents better perception of game state:

```python
class EnhancedGameAgent(GamePlayingExpertAgent):
    def perceive(self, environment_state):
        board = environment_state['board']

        features = {
            # Basic
            'board': board,
            'valid_moves': environment_state['valid_moves'],

            # Strategic features
            'center_control': self.count_center_pieces(board),
            'threats': self.detect_threats(board),
            'opportunities': self.find_winning_moves(board),
            'opponent_threats': self.detect_opponent_threats(board),

            # Positional features
            'column_heights': self.get_column_heights(board),
            'patterns': self.detect_patterns(board),
        }

        return features
```

**Impact:**
- Agents can "see" strategic concepts
- Mutations can act on high-level features
- Faster convergence to good strategies

## Quick Start: Run Strategic Demo

```bash
# Use HeuristicOpponent for meaningful learning
python run_connect4_strategic.py

# Expected output:
# Gen 1:  Best=15%, Mean=8%   (struggling)
# Gen 5:  Best=35%, Mean=22%  (learning)
# Gen 10: Best=55%, Mean=42%  (improving!)
# Gen 15: Best=68%, Mean=54%  (strong play!)
```

## Comparison: Random vs Strategic Opponent

| Metric | Random Opponent | Heuristic Opponent | Minimax-D3 |
|--------|----------------|--------------------| -----------|
| Initial fitness | 45-55% | 10-20% | 0-5% |
| Final fitness (Gen 8) | 50-58% | 30-50% | 5-15% |
| Final fitness (Gen 30) | 52-60% | 60-80% | 30-60% |
| Strategic depth discovered | Low | Medium | High |
| Learning curve | Flat | Steady | Steep then plateau |

## Recommended Setup for Deep Learning

```python
# 1. Start with curriculum
opponents = [
    HeuristicOpponent(),           # 15 generations
    MinimaxOpponent(depth=2),      # 20 generations
    MinimaxOpponent(depth=3),      # 30 generations
]

# 2. Large population
CONFIG = EvolutionConfig(
    population_size=30,
    generations=50,
    mutation_rate=0.5,
    elitism_count=5,
    tournament_size=7,
    convergence_threshold=0.80,
    stagnation_generations=10
)

# 3. Multi-objective fitness
def fitness(agent, opponent):
    win_rate = evaluate(agent, opponent)
    efficiency = 1.0 / avg_moves(agent)
    tactics = blocking_score(agent) + threat_score(agent)

    return 0.6 * win_rate + 0.2 * efficiency + 0.2 * tactics

# 4. Feature-rich perception
agent.perceive(state) → {board, threats, opportunities, patterns}
```

**Expected Result:**
- **Gen 50**: 70-85% win rate vs Minimax-D3
- **Strategy**: Center control, threat detection, pattern recognition
- **Playstyle**: Near-optimal tactical play

## Files to Use

1. **`run_connect4_strategic.py`** - Single strategic opponent demo
2. **`benchmarks/strategic_opponents.py`** - Opponent implementations
3. **Run curriculum demo** (create your own):
   ```bash
   python run_connect4_curriculum.py
   ```

---

**Bottom Line**: Strategic opponents create the learning pressure needed for agents to discover deep tactics. Random opponents = shallow learning. Minimax opponents = deep strategic growth.
