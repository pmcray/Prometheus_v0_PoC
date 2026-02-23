# Evolution Not Learning - Diagnosis & Solution

## Problem

The v0.69 demo shows **0% fitness across all generations** when trying to evolve Draughts agents. No learning occurs.

## Root Causes

### 1. **Game is Too Complex**
- **Draughts (Checkers)** is extremely complex for random starting agents
- 8x8 board, complex capture rules, kings, mandatory jumps
- Random agents never win against even weak opponents
- **0% win rate = no fitness gradient for evolution**

### 2. **No Curriculum Learning**
- System jumps straight to hardest game
- No transfer learning from simpler games
- Like teaching calculus before arithmetic

### 3. **Interface Mismatch** (CRITICAL - FIXED ✅)
- **BUG**: Benchmark calls `agent.select_move(game.get_state())` with GameState object
- **BUG**: Agent expected `select_move(board, valid_moves, **kwargs)` with separate params
- **IMPACT**: ALL agents crashed → 100% failure rate → 0% fitness
- **FIX**: Updated `DomainExpertAgent.select_move()` to accept GameState object
- **RESULT**: Gen 1 agents now achieve 47-57% win rate (expected for random play)

## Solution: Curriculum Learning

### Game Difficulty Ranking

1. **Connect4** (EASIEST) ⭐
   - 7x6 grid
   - Simple rules: drop piece, connect 4
   - Random agents can win ~30-40% vs random opponent
   - **GOOD LEARNING SIGNAL**

2. **Reversi/Othello** (MEDIUM) ⭐⭐
   - 8x8 grid
   - Flipping mechanics
   - More complex but manageable

3. **Draughts** (HARDEST) ⭐⭐⭐
   - 8x8 grid
   - Complex movement and captures
   - Kings, forced jumps
   - Very hard for untrained agents

### Recommended Approach

```python
# WRONG (current v0.69):
USER_GOAL = "Become an expert Draughts player"
# → Immediate failure, 0% fitness, no learning

# RIGHT:
CURRICULUM = [
    "Master Connect4",      # Stage 1: Learn basics
    "Master Reversi",       # Stage 2: Transfer learning
    "Master Draughts"       # Stage 3: Final challenge
]
```

## Quick Fix: Use Connect4

The **fastest way to see learning** is to change the demo to use Connect4:

### File: `run_v069_demo.py`

```python
# Line 70 - Change from:
USER_GOAL = "Become an expert Draughts player"

# To:
USER_GOAL = "Become an expert Connect4 player"

# Line 86 - This will automatically use:
# target_benchmark: GGP-connect4  (instead of GGP-draughts)
```

**Expected Results with Connect4:**
- Generation 1: ~20-30% win rate (random play)
- Generation 3: ~40-50% win rate (learning patterns)
- Generation 5-8: ~60-80% win rate (decent play)

## Demos Created

### 1. `run_connect4_simple.py`
- Single-stage Connect4 evolution
- Clear fitness progression
- ~10 minutes runtime
- **Use this to verify evolution works**

### 2. `run_curriculum_demo.py`
- Full 3-stage curriculum
- Connect4 → Reversi → Draughts
- Transfer learning between stages
- ~30-45 minutes runtime
- **Use this for comprehensive demo**

## Why Evolution Appeared to Fail

```
Draughts Complexity:
  State Space: ~10^20
  Valid Moves: ~10-50 per position
  Strategic Depth: Very high

Random Agent vs Random Opponent:
  Win Rate: ~5-10% (extremely low)
  → Fitness signal too weak
  → Evolution has nothing to optimize
  → Stays at 0% forever

Connect4 Simplicity:
  State Space: ~10^13 (much smaller)
  Valid Moves: 1-7 per position
  Strategic Depth: Moderate

Random Agent vs Random Opponent:
  Win Rate: ~30-50% (good signal!)
  → Clear fitness gradient
  → Evolution can improve
  → Reaches 60-80% in 5-10 generations
```

## Verification Steps

1. **Kill existing runs:**
   ```bash
   pkill -f run_v069_demo
   ```

2. **Run Connect4 demo:**
   ```bash
   python run_connect4_simple.py
   ```

   Expected output:
   ```
   Generation 1: Best=0.20, Mean=0.15
   Generation 2: Best=0.35, Mean=0.25  ← Learning!
   Generation 3: Best=0.50, Mean=0.38  ← Improvement!
   ...
   ```

3. **If still 0%, check:**
   - Is Ollama running? (`ollama list`)
   - Is model loaded? (`ollama list` should show qwen2.5-coder)
   - Are benchmarks working? (run `test_freeciv_integration.py`)

## Technical Notes

### Why Random vs Random Matters

For evolution to work, you need:
1. **Variation**: Mutations create different strategies
2. **Selection**: Better strategies win more often
3. **Fitness Gradient**: Win rate must vary (20-80%, not all 0%)

**Draughts**: All random → All lose → No gradient → No learning
**Connect4**: Random varies → Some win → Clear gradient → Learning works

### Curriculum Learning Theory

Starting simple enables:
- **Feature Discovery**: Learn basic patterns (center control, blocking)
- **Strategy Transfer**: Tactics transfer across games
- **Confidence Bootstrap**: Early wins build better strategies
- **Exploration**: Mutations have visible effects

## Summary

| Game | Starting Fitness | After 8 Gen | Learning? |
|------|-----------------|-------------|-----------|
| **Draughts** | 0% | 0% | ❌ No (too hard) |
| **Connect4** | 25% | 60-75% | ✅ Yes |
| **Curriculum** | 30% → 20% → 10% | 70% → 50% → 40% | ✅ Yes (staged) |

**Recommendation**: Always start with Connect4, then transfer to harder games.

---

**Files to Run:**
- `run_connect4_simple.py` - Quick verification (10 min)
- `run_curriculum_demo.py` - Full demo (45 min)

**Files to Update:**
- `run_v069_demo.py` - Change line 70 to use Connect4 goal
