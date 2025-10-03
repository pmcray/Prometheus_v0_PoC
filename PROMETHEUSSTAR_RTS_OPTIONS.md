# PrometheusStar: Free RTS Alternatives to StarCraft

## Overview

You asked about creating a "PrometheusStar" version similar to DeepMind's AlphaStar, but using free/open-source RTS games. Here are the best options:

---

## 🏆 Top Recommendation: **OpenRA + MicroRTS**

### Option 1: **OpenRA** (Open Red Alert) ⭐ **BEST CHOICE**

**What it is**: Open-source engine for Command & Conquer, Red Alert, and Dune 2000

**Why it's perfect for Prometheus**:
- ✅ **Free & Open Source** (GPL-3.0)
- ✅ **Active development** (2023+)
- ✅ **Python API available** via mod system
- ✅ **Similar complexity to StarCraft** (resource management, unit control, fog of war)
- ✅ **Built-in AI** with different skill levels
- ✅ **Replay system** for analysis
- ✅ **Large community** with maps and mods

**Technical Details**:
- Engine: C# (with Python bindings possible)
- API: Lua + Python wrappers
- Maps: 100+ official maps
- Game speed: Adjustable (can run 10-100x faster for training)
- Observation space: Full game state access
- Action space: Unit commands, building placement, resource management

**Getting Started**:
```bash
# Install OpenRA
sudo add-apt-repository ppa:openra/release
sudo apt update
sudo apt install openra

# Python bindings
git clone https://github.com/OpenRA/OpenRA
# Custom mod for Prometheus integration
```

**Curriculum Path**:
1. **Stage 1**: Beat Easy AI (basic unit control)
2. **Stage 2**: Beat Medium AI (resource management)
3. **Stage 3**: Beat Hard AI (multi-tasking)
4. **Stage 4**: Beat Expert AI (strategic depth)
5. **Stage 5**: Beat human players (transfer learning)

**Estimated Training Time**:
- Quick test: 4 agents × 10 gens × 5 games = ~20 hours
- Full training: 20 agents × 50 gens × 10 games = ~500 hours (21 days)

---

### Option 2: **MicroRTS** ⭐ **EASIEST TO START**

**What it is**: Lightweight RTS specifically designed for AI research

**Why it's great**:
- ✅ **Built for AI/ML** research
- ✅ **Python gymnasium environment** ready to use
- ✅ **Fast execution** (1000s of games/hour)
- ✅ **Simple but strategic**
- ✅ **Active research community**
- ✅ **Perfect for curriculum learning**

**Technical Details**:
- Engine: Java + Python
- API: OpenAI Gym interface
- State space: 2D grid (8x8 to 64x64)
- Action space: Move, attack, harvest, build
- Speed: 100-1000x faster than real-time

**Installation**:
```bash
pip install gym-microrts
```

**Usage**:
```python
import gym
from gym_microrts import microrts_ai

env = gym.make("MicrortsMining4x4-v0")
obs = env.reset()

# Your Prometheus agent here
action = agent.select_action(obs)
obs, reward, done, info = env.step(action)
```

**Perfect for PrometheusStar because**:
- Already has gym interface (easy integration)
- Fast training (can run full curriculum in days, not weeks)
- Good complexity for demonstrating strategic learning
- Built-in opponents of varying difficulty

**Curriculum Path**:
1. **Stage 1**: RandomAI (learn basics)
2. **Stage 2**: PassiveAI (resource management)
3. **Stage 3**: RushAI (tactical responses)
4. **Stage 4**: MixedAI (strategic depth)
5. **Stage 5**: Tournament play

---

### Option 3: **0 A.D.** (Zero Anno Domini)

**What it is**: Historical RTS similar to Age of Empires

**Why it's interesting**:
- ✅ **Beautiful graphics** (great for demos)
- ✅ **Active development**
- ✅ **Complex economy** (4 resources, 100+ units)
- ✅ **Historical accuracy** (educational value)
- ⚠️ **Harder to integrate** (less AI-focused)

**Technical Details**:
- Engine: C++ (Pyrogenesis)
- AI: JavaScript (can be extended)
- Complexity: High (similar to Age of Empires II)

**Best for**: Impressive demos, but harder to train

---

### Option 4: **Spring RTS** (Balanced Annihilation, Zero-K)

**What it is**: Open-source engine with multiple RTS games

**Why it's powerful**:
- ✅ **Very active modding** community
- ✅ **Multiple game types** (Zero-K, Balanced Annihilation, etc.)
- ✅ **Lua scripting** for AI
- ✅ **3D graphics** (impressive visuals)
- ⚠️ **Complex setup**

**Best for**: Advanced projects after proving concept

---

## 📊 Comparison Table

| Game | Complexity | Training Speed | AI Integration | Community | Best For |
|------|-----------|---------------|----------------|-----------|----------|
| **MicroRTS** | ⭐⭐ Low | ⭐⭐⭐⭐⭐ Fast | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Good | **Quick proof-of-concept** |
| **OpenRA** | ⭐⭐⭐⭐ High | ⭐⭐⭐ Medium | ⭐⭐⭐⭐ Very Good | ⭐⭐⭐⭐⭐ Excellent | **Full PrometheusStar demo** |
| **0 A.D.** | ⭐⭐⭐⭐⭐ Very High | ⭐⭐ Slow | ⭐⭐ Fair | ⭐⭐⭐⭐ Very Good | **Impressive visuals** |
| **Spring RTS** | ⭐⭐⭐⭐ High | ⭐⭐⭐ Medium | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Very Good | **Advanced mods** |

---

## 🚀 Recommended Path for PrometheusStar

### Phase 1: Proof of Concept (1-2 weeks)
**Game**: MicroRTS
**Goal**: Demonstrate curriculum learning on fast RTS

**Curriculum**:
1. Mining task (learn resource gathering)
2. Combat task (learn unit control)
3. Full game vs RandomAI
4. Full game vs RushAI

**Why**: Fast iteration, proves concept quickly

### Phase 2: Full Demo (1-2 months)
**Game**: OpenRA (Command & Conquer)
**Goal**: AlphaStar-style demonstration

**Curriculum**:
1. Easy AI (25% win rate target)
2. Medium AI (40% win rate target)
3. Hard AI (30% win rate target)
4. Expert AI (20% win rate target)
5. Human players (10-15% win rate target)

**Why**: Impressive, recognizable, good complexity

### Phase 3: Research Publication (3-6 months)
**Game**: Both MicroRTS (fast experiments) + OpenRA (impressive results)
**Goal**: Demonstrate generalization across RTS games

---

## 🎯 PrometheusStar Unique Features

What makes PrometheusStar different from AlphaStar:

### 1. **Curriculum Learning** (AlphaStar used self-play)
- Progressive difficulty through AI levels
- Observable skill emergence
- Objective measurement via opponent strength

### 2. **Meta-Learning** (AlphaStar was game-specific)
- GeneralistPlanner creates training strategy
- Transferable across different RTS games
- Domain-general capability acquisition

### 3. **Introspection** (AlphaStar was black-box)
- IEE provides interpretable evaluation
- Strategy Archive tracks learned tactics
- Explainable decision-making

### 4. **Resource-Aware** (AlphaStar used massive compute)
- Budget constraints force efficiency
- Reputation system for agent quality
- Scales from Jetson to cluster

### 5. **Open-Source** (AlphaStar proprietary)
- Free games (MicroRTS, OpenRA)
- Open-source framework
- Reproducible research

---

## 📦 Implementation Plan

### Week 1-2: MicroRTS Integration
```python
# File: benchmarks/microrts_benchmark.py

from gym_microrts import microrts_ai
import gym

class MicroRTSBenchmark:
    def __init__(self, opponent='passive'):
        self.env = gym.make(f"Microrts-{opponent}-v0")

    def evaluate_agent(self, agent, num_games=5):
        wins = 0
        for _ in range(num_games):
            obs = self.env.reset()
            done = False

            while not done:
                action = agent.select_action(obs)
                obs, reward, done, info = self.env.step(action)

            if reward > 0:
                wins += 1

        return wins / num_games
```

### Week 3-4: OpenRA Integration
```python
# File: benchmarks/openra_benchmark.py

class OpenRABenchmark:
    def __init__(self, difficulty='easy'):
        self.game = OpenRAGame(difficulty=difficulty)

    def evaluate_agent(self, agent, num_games=3):
        # OpenRA integration
        # Similar to FreeCiv but faster games
        pass
```

### Week 5-8: Curriculum Training
- Stage 1: MicroRTS PassiveAI
- Stage 2: MicroRTS RushAI
- Stage 3: OpenRA Easy AI
- Stage 4: OpenRA Medium AI

---

## 📊 Expected Results

### MicroRTS (Fast Validation)
```
Stage 1 (PassiveAI):   Gen 1:  30% → Gen 20:  85%  (learn basics)
Stage 2 (RushAI):      Gen 1:  10% → Gen 30:  60%  (learn tactics)
Total time: ~24 hours on Jetson
```

### OpenRA (Full Demo)
```
Stage 1 (Easy AI):     Gen 1:  15% → Gen 30:  50%  (learn mechanics)
Stage 2 (Medium AI):   Gen 1:   5% → Gen 40:  35%  (learn strategy)
Stage 3 (Hard AI):     Gen 1:   1% → Gen 50:  20%  (master game)
Total time: ~2 weeks on Jetson, ~3 days on GPU cluster
```

---

## 🎓 Why This Demonstrates Prometheus Better Than AlphaStar

1. **Curriculum Learning**: Progressive difficulty shows observable intelligence emergence
2. **Multiple Games**: MicroRTS → OpenRA shows domain generalization
3. **Resource Efficiency**: Trains on Jetson, not Google datacenter
4. **Open Science**: Fully reproducible with free tools
5. **Interpretability**: Strategy Archive shows *what* it learned
6. **Meta-Learning**: GeneralistPlanner adapts training to game

---

## 🚀 Quick Start: MicroRTS Integration

Create this file now:

```bash
# File: run_prometheusstar_microrts.py
```

```python
#!/usr/bin/env python3
\"\"\"
PrometheusStar - MicroRTS Demo
Demonstrates curriculum learning on RTS games
\"\"\"

import gym
from gym_microrts import microrts_ai

from prometheus.smm import EvolutionaryOrchestratorAgent, EvolutionConfig
from prometheus.iee import IntrospectionEvaluationEngine
from benchmarks.microrts_benchmark import MicroRTSBenchmark

# Curriculum
CURRICULUM = [
    {"opponent": "passive", "target": 0.80, "gens": 20},
    {"opponent": "rush", "target": 0.60, "gens": 30},
    {"opponent": "mixed", "target": 0.50, "gens": 40},
]

# Run curriculum training
for stage in CURRICULUM:
    benchmark = MicroRTSBenchmark(opponent=stage['opponent'])
    # Train agents...
    # Evolve through curriculum...
```

---

## 📚 Resources

### MicroRTS:
- GitHub: https://github.com/Farama-Foundation/MicroRTS-Py
- Docs: https://github.com/Farama-Foundation/MicroRTS-Py/wiki
- Papers: Multiple AIIDE/CoG publications

### OpenRA:
- Website: https://www.openra.net/
- GitHub: https://github.com/OpenRA/OpenRA
- Modding SDK: https://github.com/OpenRA/OpenRAModSDK

### 0 A.D.:
- Website: https://play0ad.com/
- GitHub: https://github.com/0ad/0ad

---

## 💡 Recommendation

**Start with MicroRTS for quick validation (this week!)**
- Fast iteration
- Proves curriculum learning works on RTS
- Easy to integrate

**Then scale to OpenRA for impressive demo (next month)**
- Recognizable gameplay
- AlphaStar-like wow factor
- Good research story

**This gives you**:
- ✅ Quick proof-of-concept
- ✅ Impressive full demo
- ✅ Research publication potential
- ✅ Better than AlphaStar story (curriculum learning + meta-learning + interpretability)

---

## 🎉 Summary

**PrometheusStar = Prometheus + RTS Games**

**Best games**:
1. **MicroRTS** - Quick start
2. **OpenRA** - Full demo

**Unique advantages over AlphaStar**:
- Curriculum learning (not just self-play)
- Domain generalization (multiple games)
- Resource efficiency (Jetson, not datacenter)
- Interpretability (Strategy Archive)
- Open-source (free games, reproducible)

**Ready to implement now with existing Prometheus infrastructure!**

---

Would you like me to:
1. Create the MicroRTS benchmark integration?
2. Build the OpenRA integration framework?
3. Create a Colab notebook for PrometheusStar training?

All the pieces are in place - we just need to connect Prometheus to the RTS games! 🚀
