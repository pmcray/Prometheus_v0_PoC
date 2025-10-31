# Strategic Roadmap: Prometheus v0.70+ (Post-ARC Phase)

## Date: October 10, 2025

---

## Executive Summary

Having established ARC-AGI baselines and discovered fundamental overfitting limits in pure symbolic evolution (Phase 3), we now pivot to **domain-specific ultraintelligence** across multiple cognitive domains:

1. **Olympiad-level reasoning** (Math, Physics, CS)
2. **Universal game-playing** (demonstrating Good's ultraintelligence)
3. **Theorem proving** (formal verification)
4. **Scientific discovery** (physics simulation learning)

**Core principle**: Each domain requires **domain-specific primitives + meta-learning**, not general AGI.

---

## Phase 4: Olympiad-Level Reasoning Systems

### Goal
Solve IMO (Math), IPhO (Physics), and IOI (CS) problems through recursive self-improvement.

### Architecture: Multi-Stage Reasoning Pipeline

```
Problem → Understanding → Strategy → Execution → Verification → Feedback
   ↓           ↓             ↓           ↓            ↓            ↓
Gemini      Symbolic      Heuristic   Code/Proof   Formal       Meta-
Parser      Extraction    Search      Synthesis    Check        Learning
```

### 4.1 Mathematical Olympiad System (IMO)

**Problem**: Solve competition-level math (geometry, algebra, number theory, combinatorics)

**Approach**: Domain-specific primitives + proof search

#### Primitives Library (Math)
```python
# Algebraic operations
- factor_polynomial
- expand_expression
- substitute_variable
- solve_equation
- simplify_radical

# Geometric operations
- construct_auxiliary_line
- apply_similarity
- use_angle_chasing
- pythagorean_theorem
- coordinate_geometry

# Number theory
- prime_factorization
- modular_arithmetic
- gcd_lcm
- diophantine_solve
- induction_base_step

# Combinatorics
- counting_principle
- inclusion_exclusion
- pigeonhole
- generating_functions
- recursion_relation
```

#### Meta-Learning Strategy
1. **Problem classification**: Identify domain (algebra/geometry/NT/combinatorics)
2. **Strategy selection**: Choose proof technique (induction/contradiction/construction)
3. **Tactic evolution**: Genetic search over proof steps
4. **Formal verification**: Use Lean 4 to verify correctness
5. **Curriculum learning**: Start with easy problems, increase difficulty

#### Implementation Plan

**v0.70: IMO Bronze (Easy Problems)**
- File: `prometheus_imo_bronze.py`
- Target: 30% of IMO P1/P4 (easiest problems)
- Primitives: 50 math operations
- Search: Beam search (width 10, depth 20)
- Verification: Symbolic math (SymPy)
- Duration: 1 week implementation + 1 week testing

**v0.71: IMO Silver (Medium Problems)**
- Add: 30 advanced tactics
- Search: Monte Carlo Tree Search
- Verification: Lean 4 integration
- Target: 50% of P1/P4, 20% of P2/P5
- Duration: 2 weeks

**v0.72: IMO Gold (Hard Problems)**
- Add: 50 expert tactics
- Meta-learning: Learn tactic sequences from human proofs
- Target: 70% P1/P4, 40% P2/P5, 10% P3/P6
- Duration: 1 month

**Success Metric**: Medal threshold (7+ points = Bronze, 16+ = Silver, 29+ = Gold)

---

### 4.2 Physics Olympiad System (IPhO)

**Problem**: Solve theoretical and experimental physics problems

**Approach**: Symbolic equations + numerical simulation + dimensional analysis

#### Primitives Library (Physics)
```python
# Mechanics
- newton_second_law
- energy_conservation
- momentum_conservation
- torque_equilibrium
- harmonic_oscillator
- lagrangian_formulation

# Electromagnetism
- coulomb_law
- gauss_law
- ampere_law
- faraday_law
- maxwell_equations
- lorentz_force

# Thermodynamics
- ideal_gas_law
- first_law_thermo
- carnot_efficiency
- entropy_calculation
- phase_transitions

# Optics & Waves
- snell_law
- interference_pattern
- diffraction_grating
- doppler_effect
- wave_equation

# Modern Physics
- photoelectric_effect
- compton_scattering
- bohr_model
- schrodinger_equation
- relativistic_kinematics
```

#### Implementation Plan

**v0.73: IPhO Problem Solver**
- File: `prometheus_ipho.py`
- Symbolic solver: SymPy for equations
- Numerical solver: SciPy for differential equations
- Dimensional analysis: Automatic unit checking
- Diagram understanding: Parse problem diagrams
- Target: 40% of IPhO theoretical problems
- Duration: 2 weeks

**v0.74: Experimental Physics Learner**
- Simulation: Physics engine (PyBullet)
- Data analysis: Fit curves, extract laws
- Uncertainty propagation
- Target: Design and analyze virtual experiments
- Duration: 2 weeks

---

### 4.3 Computer Science Olympiad System (IOI)

**Problem**: Solve algorithmic programming challenges

**Approach**: Algorithm library + code synthesis + verification

#### Primitives Library (Algorithms)
```python
# Data Structures
- array, linked_list, stack, queue
- binary_tree, heap, hash_table
- disjoint_set (union-find)
- segment_tree, fenwick_tree
- trie, suffix_array

# Graph Algorithms
- dfs, bfs, dijkstra, bellman_ford
- kruskal_mst, prim_mst
- topological_sort
- strongly_connected_components
- max_flow (ford_fulkerson, dinic)
- bipartite_matching

# Dynamic Programming
- knapsack, longest_common_subsequence
- edit_distance, coin_change
- matrix_chain_multiplication
- traveling_salesman (DP + bitmask)

# Number Theory & Math
- sieve_of_eratosthenes
- fast_exponentiation
- extended_gcd
- chinese_remainder_theorem
- fft (fast_fourier_transform)

# String Algorithms
- kmp, rabin_karp
- z_algorithm
- suffix_automaton
- aho_corasick
```

#### Implementation Plan

**v0.75: IOI Bronze (Easy Problems)**
- File: `prometheus_ioi_bronze.py`
- Code synthesis: Template-based generation
- Pattern matching: Recognize problem types
- Testing: Auto-generate test cases
- Target: 40% of IOI easy subtasks
- Duration: 2 weeks

**v0.76: IOI Silver (Optimization)**
- Meta-learning: Learn from editorial solutions
- Complexity analysis: Prune inefficient approaches
- Target: 60% of medium subtasks
- Duration: 2 weeks

**v0.77: IOI Gold (Advanced)**
- Novel algorithm synthesis
- Combine multiple techniques
- Target: 30% of hard subtasks
- Duration: 1 month

---

## Phase 5: Universal Game-Playing Ultraintelligence

### Goal
Demonstrate Good's ultraintelligence through **meta-learning across game domains**.

**Key Insight**: Don't just play games well—**learn to learn** game strategies faster.

### 5.1 Game Taxonomy & Target Domains

| Category | Games | Key Challenges | Target Performance |
|----------|-------|----------------|-------------------|
| **Perfect Info, Zero-Sum** | Chess, Go, Checkers, Othello | Deep search, evaluation | Top 1% humans |
| **Imperfect Info, Zero-Sum** | Poker, Bridge, Stratego | Belief states, bluffing | Professional level |
| **Perfect Info, Multi-agent** | Diplomacy, Settlers of Catan | Negotiation, alliances | Expert level |
| **Real-time Strategy** | StarCraft, Warcraft, Age of Empires | Speed, macro/micro | Master league |
| **Open-world Sandbox** | Minecraft, Terraria, Factorio | Creativity, long-term planning | Human expert |
| **Physics-based** | Angry Birds, Portal, Besiege | Intuitive physics | Above human |

### 5.2 Universal Game-Playing Architecture

**Core Idea**: Meta-learn a **game representation language** + **strategy learner**

```python
class UniversalGamePlayer:
    def __init__(self):
        self.representation_learner = RepresentationNet()  # Learn state encoding
        self.strategy_learner = MetaStrategyNet()          # Learn policy network
        self.model_learner = WorldModelNet()               # Learn environment dynamics
        self.meta_optimizer = MetaGradientOptimizer()      # Meta-learn learning rate

    def play_new_game(self, game_rules, num_trials=100):
        """Meta-learning: Learn to play a new game quickly"""
        # Phase 1: Learn representation (10 trials)
        representation = self.representation_learner.encode(game_rules)

        # Phase 2: Learn strategy (50 trials) - faster than training from scratch
        strategy = self.strategy_learner.meta_adapt(representation, num_trials=50)

        # Phase 3: Refine via self-play (40 trials)
        refined_strategy = self.self_play_improve(strategy, num_trials=40)

        return refined_strategy
```

### 5.3 Implementation Plan

**v0.78: Meta-Learning for Board Games**
- File: `prometheus_universal_boardgames.py`
- Domains: Chess, Go, Checkers, Othello, Connect-4
- Architecture: AlphaZero-style MCTS + meta-learned value network
- Meta-learning: Train on Chess → Transfer to Go in 10x fewer games
- Duration: 3 weeks

**v0.79: Imperfect Information Games**
- File: `prometheus_poker_bridge.py`
- Domains: Texas Hold'em, Bridge
- Techniques: CFR (Counterfactual Regret Minimization) + meta-learning
- Target: Beat professional-level bots
- Duration: 3 weeks

**v0.80: Real-Time Strategy (already implemented!)**
- File: `prometheus_freeciv_curriculum.py` (exists)
- Status: COMPLETED in earlier phase
- Performance: Curriculum learning from easy → hard AIs

**v0.81: Physics-Based Puzzle Games**
- File: `prometheus_physics_games.py`
- Domains: Angry Birds, Cut the Rope, Portal
- Approach: Learn intuitive physics model + planning
- Duration: 2 weeks

**v0.82: Open-World Sandbox**
- File: `prometheus_minecraft.py`
- Domain: Minecraft
- Tasks: Mining, building, survival, redstone circuits
- Approach: Hierarchical RL + language-guided goals
- Duration: 1 month

---

## Phase 6: Scientific Discovery & Theorem Proving

### 6.1 Automated Theorem Proving (Lean 4)

**Goal**: Prove mathematical theorems automatically

**Approach**: Tactic search + meta-learning over proofs

#### Implementation Plan

**v0.83: Lean 4 Tactic Learner**
- File: `prometheus_lean4_prover.py`
- Integration: Use Lean 4 API
- Tactics: 50 common tactics (rw, simp, ring, field_simp, etc.)
- Search: Beam search over tactic sequences
- Target: Prove 30% of mathlib beginner theorems
- Duration: 3 weeks

**v0.84: Meta-Learning for Proofs**
- Learn tactic patterns from human proofs
- Transfer learning: Algebra → Number Theory
- Target: 50% of mathlib theorems
- Duration: 1 month

### 6.2 Physics Law Discovery

**Goal**: Discover physical laws from simulation data (like Feynman AI Physicist)

**Approach**: Symbolic regression + dimensional analysis

#### Implementation Plan

**v0.85: Symbolic Physics Learner**
- File: `prometheus_physics_discovery.py`
- Input: Simulation data (positions, velocities, forces)
- Output: Symbolic equations (F = ma, E = ½mv², etc.)
- Method: Genetic programming over equation space
- Constraints: Dimensional consistency
- Target: Rediscover classical mechanics laws
- Duration: 2 weeks

**v0.86: Causal Discovery**
- Use existing causal inference code (already implemented!)
- Discover causal relationships in physical systems
- Duration: 1 week

---

## Phase 7: Integration & Benchmarking

### 7.1 Unified Architecture

**Goal**: Single system that can switch between domains

```python
class PrometheusUnified:
    def __init__(self):
        self.domain_detector = DomainClassifier()
        self.domain_agents = {
            'math': IMOSolver(),
            'physics': IPhOSolver(),
            'coding': IOISolver(),
            'board_games': UniversalBoardGamePlayer(),
            'rts': FreecivPlayer(),
            'theorem_proving': Lean4Prover(),
        }
        self.meta_learner = CrossDomainMetaLearner()

    def solve(self, problem):
        domain = self.domain_detector.classify(problem)
        agent = self.domain_agents[domain]
        solution = agent.solve(problem)

        # Meta-learning: Transfer knowledge across domains
        self.meta_learner.update(domain, solution)

        return solution
```

**v0.90: Prometheus Unified**
- Integration of all domain agents
- Cross-domain meta-learning
- Benchmark on all tasks simultaneously
- Duration: 2 weeks

### 7.2 Comprehensive Benchmarking

| Domain | Benchmark | Current | Target v0.90 |
|--------|-----------|---------|--------------|
| ARC-AGI | Training/Eval | 8.0% / 1.0% | 10% / 3% (regularized) |
| IMO | Points (0-42) | 0 | 7+ (Bronze) |
| IPhO | Points (0-50) | 0 | 20+ (Bronze) |
| IOI | Points (0-600) | 0 | 240+ (Bronze) |
| Chess | Elo | 0 | 2000+ |
| Go | Rank | 0 | 5 kyu |
| Poker | GTO distance | - | <5% exploitability |
| Minecraft | Task completion | 0% | 40% |
| Lean 4 | Theorems proved | 0 | 30% mathlib easy |

---

## Resource Requirements

### Computational
- **Current**: ARM Cortex (Jetson Orin Nano), 8GB RAM
- **Needed for olympiads**: Same (symbolic + search is CPU-bound)
- **Needed for games**:
  - Board games: GPU helpful but not required
  - RTS: Already working on current hardware
  - Minecraft: Need stronger GPU (RTX 3060+) OR cloud instance

### Data
- **IMO**: 500+ problems with solutions (available online)
- **IPhO**: 300+ problems (available)
- **IOI**: 1000+ problems (available)
- **Games**: Self-play generates unlimited data
- **Lean 4**: mathlib (100K+ theorems)

### Time Estimates
- **Phase 4 (Olympiads)**: 3 months (parallel development)
- **Phase 5 (Games)**: 2 months (some already done)
- **Phase 6 (Discovery)**: 1 month
- **Phase 7 (Integration)**: 1 month
- **Total**: 6-7 months to v0.90

---

## Strategic Priorities (Recommended Order)

### Immediate (Next 2 weeks)
1. ✅ Complete ARC Phase 3 analysis (in progress)
2. **Start IOI Bronze** (easiest to implement, fastest feedback)
   - Algorithmic primitives are well-defined
   - Can use LLM for code synthesis
   - Clear correctness metric (passes test cases)

### Short-term (Months 1-2)
3. **IMO Bronze** (parallel with IOI)
4. **Universal Board Game Player**
   - Demonstrates meta-learning most clearly
   - Can show transfer learning

### Medium-term (Months 3-4)
5. **IPhO Bronze**
6. **Lean 4 Prover**
7. **Physics Discovery**

### Long-term (Months 5-6)
8. **Advanced games** (Poker, Minecraft)
9. **Integration** (v0.90)
10. **Paper writing** & documentation

---

## Key Research Questions

### 1. Does meta-learning transfer across domains?
- **Hypothesis**: Math → Physics transfer (both use equations)
- **Test**: Train on IMO algebra, test on IPhO mechanics
- **Metric**: Convergence speed (problems to reach 50% accuracy)

### 2. What representations generalize best?
- **Options**: Symbolic (equations), neural (embeddings), hybrid
- **Test**: Try all three on olympiad problems
- **Metric**: Accuracy + interpretability

### 3. How much domain-specific knowledge is needed?
- **Hypothesis**: Need domain primitives, but meta-learner is universal
- **Test**: Same meta-learner on Math/Physics/CS
- **Metric**: Performance with varying primitive counts

### 4. Can we discover novel strategies?
- **Hypothesis**: Evolution can find non-human strategies
- **Test**: Compare to human solutions
- **Metric**: % solutions not in training data

---

## Alignment with Good's Ultraintelligence

**I.J. Good (1965)**:
> "An ultraintelligent machine could design even better machines; there would then unquestionably be an 'intelligence explosion.'"

**Our interpretation**:
1. **Machine designs better machines** → Meta-learning improves learning algorithm
2. **Recursion** → Each domain makes next domain easier (transfer)
3. **Intelligence explosion** → Exponential improvement in learning speed

**Evidence we're building**:
- ARC-AGI: 0.25% → 7.5% → ? (30x improvement via evolution)
- Games: Learn Go in 10x fewer games than AlphaGo (transfer from Chess)
- Olympiads: Learn physics in 5x fewer examples (transfer from math)
- Theorem proving: Learn new tactics from successful proofs

**Key metric**: **Time to learn new domain**
- v0.69: ~1 week to add new game
- v0.90: ~1 day to add new game (meta-learned setup)
- v1.00: ~1 hour to add new domain (fully automated)

---

## Success Criteria for v0.90

**Minimum viable ultraintelligence**:

1. **Breadth**: Solve problems in 5+ domains (Math, Physics, CS, Games, Proofs)
2. **Depth**: Bronze-level performance in each domain (top 30%)
3. **Meta-learning**: Demonstrate transfer (new game in 10x less time)
4. **Recursion**: System improves its own learning algorithm
5. **Transparency**: All solutions are interpretable (no black-box)

**Stretch goals**:
- Silver-level in any olympiad (top 10%)
- Master-level in any game (top 1%)
- Discover a novel theorem in Lean 4
- Publish multi-domain paper

---

## Next Steps (After Current ARC Runs Complete)

### Immediate actions:
1. Document ARC Phase 3 results
2. Commit all code and analysis
3. **Choose starting point**: IOI Bronze OR IMO Bronze
   - **Recommendation**: IOI Bronze (easier, faster feedback)
4. Design primitive library for chosen domain
5. Implement v0.75 or v0.70

### Files to create:
- `prometheus_ioi_bronze.py` (if starting with CS)
- `prometheus_imo_bronze.py` (if starting with Math)
- `OLYMPIAD_PRIMITIVES.md` (primitive library documentation)
- `v0_70_ARCHITECTURE.md` (system design)

---

## Questions for Discussion

1. **Which domain should we start with?** (IOI, IMO, or IPhO)
2. **Should we use LLMs for code synthesis?** (Gemini for IOI)
3. **GPU priority**: Keep Jetson, or upgrade for games?
4. **Timeline**: Aggressive (6 months) or conservative (12 months)?
5. **Publication strategy**: Incremental papers or one big paper?

---

*Generated: October 10, 2025*
*Prometheus v0.69 → v0.90 Strategic Roadmap*
