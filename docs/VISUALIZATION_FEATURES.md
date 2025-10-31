# Project Prometheus - Visualization Features (v0.69-v0.75)

## Overview

This document describes the comprehensive visualization capabilities implemented for Project Prometheus, enabling rich interactive demonstrations of cognitive architecture, game playing, and causal reasoning.

## Features Implemented

### 1. Game Suite (`prometheus/game_suite.py`)

Three games with increasing complexity:

- **Connect 4** (Simple)
  - 7×6 grid, drop tokens
  - Win condition: 4 in a row (horizontal, vertical, diagonal)
  - ASCII and matplotlib visualizations

- **Othello/Reversi** (Intermediate)
  - 8×8 grid, flip opponent pieces
  - Strategy: corners are strong, edges are dangerous
  - Valid move highlighting

- **Draughts** (Complex) (in `benchmarks/prometheus_bench_v0_2.py`)
  - 8×8 grid, captures and kings
  - Forced captures, multi-jumps
  - King promotion on back rank

### 2. Notebook Visualization Library (`prometheus/notebook_viz.py`)

Rich Jupyter notebook visualizations with full color:

#### GameBoardViz
- `visualize_connect4()` - Red/blue tokens, green win highlights
- `visualize_othello()` - Black/white pieces, purple valid moves
- `visualize_draughts()` - Checkerboard with pieces and kings

#### AgentThinkingViz
- `show_thinking()` - Flowchart of agent's decision process
- Purple thought boxes → Green decision box

#### EvolutionViz
- `plot_fitness_evolution()` - Fitness curves over generations
- `show_gene_tree()` - Genealogy tree of evolved agents
- `plot_fitness_heatmap()` - 2D fitness landscape

### 3. Brain Map with Cell Assemblies (`prometheus/brain_map.py`)

Hierarchical cognitive architecture visualization:

#### Cell Assemblies
Five functional assemblies inspired by Hebb's neuroscience theory:

1. **Planning & Strategy** (Red) - `PlannerAgent`, `ExperimentOrchestrator`
2. **Execution & Implementation** (Green) - `CoderAgent`
3. **Evaluation & Analysis** (Blue) - `EvaluatorAgent`, `ResultsSynthesizer`
4. **Knowledge & Memory** (Orange) - `KnowledgeAgent`
5. **Safety & Auditing** (Purple) - `AuditorAgent`

#### Features
- Real-time activation tracking (0.0-1.0 levels)
- Visual activation indicators (⚡ percentages)
- Information flow arrows between assemblies
- Both PyVis (interactive HTML) and matplotlib (static) outputs

### 4. Causal Agentic Mesh (`prometheus/causal_agentic_mesh.py`)

Explainable AI through causal tracking (based on Judea Pearl's framework):

#### Node Types
- `agent` - AI agents making decisions
- `tool` - Helper tools and analyzers
- `decision` - Decision points
- `observation` - Observations and actions

#### Edge Types
- `causes` - Direct causal relationship
- `informs` - Information flow
- `depends_on` - Dependency relationship
- `observes` - Observation relationship

#### Analysis Capabilities
- **Critical Path Finding** - Identify most important causal chain
- **Bottleneck Detection** - Find nodes with high betweenness centrality
- **Causal Chain Tracing** - Trace all paths leading to a decision
- **Export to JSON** - Save for post-analysis

### 5. Heuristic Agents (`demo_game_visualization.py`)

Better-than-random agents with visible thinking:

#### Connect 4 Strategy
1. Win if possible
2. Block opponent wins
3. Prefer center columns
4. Random from remaining

#### Othello Strategy
1. Take corners (strongest positions)
2. Avoid squares next to corners (danger zones)
3. Maximize flipped pieces

#### Draughts Strategy
1. Prefer captures
2. Advance toward opponent side
3. Protect back rank
4. Pursue kingship

## Interactive Notebooks

### `Game_Demo_Interactive.ipynb`
- Three game demos (Connect4, Othello, Draughts)
- Full color board rendering
- Agent thinking display
- Move-by-move visualization

### `Architecture_Demo_Interactive.ipynb`
- Brain map with cell assemblies
- Causal agentic mesh
- Real-time activation patterns
- Critical path analysis
- Bottleneck detection
- Integration with game playing

## Usage Examples

### Brain Map Activation
```python
from prometheus.brain_map import BrainMap

brain = BrainMap()
brain.activate_node('PlannerAgent', level=0.9)
brain.activate_node('CoderAgent', level=1.0)

fig = brain.visualize_assemblies(title="Active Cognitive Architecture")
plt.show()
```

### Causal Mesh Tracking
```python
from prometheus.causal_agentic_mesh import CausalAgenticMesh

mesh = CausalAgenticMesh()
mesh.add_node("observation", "observation", 1.0)
mesh.add_node("planner", "agent", 0.9)
mesh.add_edge("observation", "planner", "causes", 1.0)

critical_path = mesh.find_critical_path("observation", "action")
bottlenecks = mesh.identify_bottlenecks()
```

### Game Visualization
```python
from prometheus.notebook_viz import GameBoardViz
from prometheus.game_suite import Connect4

game = Connect4()
game.make_move(3)

fig = GameBoardViz.visualize_connect4(
    game.board,
    last_move=(5, 3),
    title="Connect 4 - Move 1"
)
plt.show()
```

## Technical Stack

- **Matplotlib** - Static visualizations with full color
- **PyVis** - Interactive network graphs (HTML output)
- **NetworkX** - Graph analysis and layout
- **Jupyter** - Interactive notebook environment
- **NumPy** - Array operations for game boards

## Applications

1. **Debugging** - Trace agent decision-making step-by-step
2. **Explainability** - Generate human-readable explanations via causal chains
3. **Optimization** - Identify bottlenecks and critical paths
4. **Education** - Demonstrate AI concepts visually
5. **Research** - Analyze cognitive architecture patterns
6. **Safety** - Verify decision chains align with constraints

## Files Modified/Created

### New Files
- `prometheus/game_suite.py` - Connect4 and Othello games
- `prometheus/notebook_viz.py` - Rich Jupyter visualizations
- `prometheus/causal_agentic_mesh.py` - Causal inference tracking
- `demo_game_visualization.py` - Heuristic agents with visible thinking
- `Game_Demo_Interactive.ipynb` - Game playing demos
- `Architecture_Demo_Interactive.ipynb` - Cognitive architecture demos
- `test_brain_assemblies.png` - Test output
- `test_causal_mesh.png` - Test output

### Modified Files
- `prometheus/brain_map.py` - Enhanced with cell assemblies
- `benchmarks/prometheus_bench_v0_2.py` - Added visualization to Draughts

## Next Steps

Potential future enhancements:

1. **Animation** - Animate game playback and activation patterns
2. **3D Visualization** - 3D causal mesh for complex systems
3. **Real-time Dashboard** - Live dashboard during evolution
4. **Comparative Analysis** - Side-by-side agent comparison
5. **Transfer Learning Viz** - Show knowledge transfer between domains
6. **Attention Maps** - Visualize what agents "pay attention to"
7. **Fitness Landscape** - 3D fitness landscape with gradient flow

## Testing

All visualizations tested with:
```bash
python -c "from prometheus.brain_map import BrainMap; ..."
python -c "from prometheus.causal_agentic_mesh import CausalAgenticMesh; ..."
```

Generate test images:
- `test_brain_assemblies.png` - Cell assembly visualization
- `test_causal_mesh.png` - Causal network visualization

---

**Project Prometheus v0.69-v0.75**
*Recursive Self-Improvement through Explainable Cognitive Architecture*
*Running on Jetson Orin Nano with Local GPU Inference*
