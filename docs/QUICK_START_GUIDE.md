# Prometheus v0.80-v0.89 Quick Start Guide

## Installation

```bash
cd /home/pmc/Prometheus_v0_PoC

# Activate virtual environment (if using)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running Tests

### Test Individual Components

```bash
# Test v0.80 CRLS Loop
python test_crls_v080.py

# Test v0.81 Multi-Game CRLS
python test_multi_game_v081.py

# Test Integrated System (v0.80-v0.89)
python test_integrated_system_v089.py
```

### Expected Output
All tests should show:
```
✅ ALL TESTS PASSED
System Status: OPERATIONAL
```

## Running Demonstrations

### Jupyter Notebooks

```bash
# Launch Jupyter
jupyter notebook

# Open notebooks:
# - Prometheus_v0_80_CRLS_Demo.ipynb
# - Prometheus_v0_69_Connect4_Evolution.ipynb
```

## Using Components

### Example 1: Simple CRLS Loop

```python
from prometheus.evaluator_agent import EvaluatorAgent
from prometheus.corrector_agent import CorrectorAgent

# Initialize
evaluator = EvaluatorAgent()
corrector = CorrectorAgent()

# Evaluate a game
game_history = {
    'moves': [(1, 3), (-1, 4)],
    'result': 'player_1_wins',
    'winner': 1,
    'agent_player': 1
}

critique = evaluator.evaluate_game(game_history, 1)
strategy = corrector.synthesize_strategy([critique])

print(f"Strategy: {strategy}")
```

### Example 2: Analogy Engine

```python
from prometheus.analogy_engine import AnalogyEngine, create_game_concepts

# Initialize and register concepts
engine = AnalogyEngine()
for concept in create_game_concepts():
    engine.register_concept(concept)

# Find analogy
analogy = engine.find_analogy('connect4', 'othello', 'center_control')
print(f"Connect4 center control ≈ Othello {analogy.name}")

# Transfer strategy
strategy = "Prioritize center control"
transferred = engine.transfer_strategy('connect4', 'othello', strategy)
print(transferred)
```

### Example 3: Safety Check

```python
from prometheus.alignment_governor import AlignmentGovernor

# Initialize governor
governor = AlignmentGovernor()

# Check strategy safety
strategy = "Play systematically and prioritize center control"
is_safe, violations = governor.review_strategy(strategy)

if is_safe:
    print("✅ Strategy is safe to use")
else:
    print(f"❌ Found {len(violations)} violations")
    safe_strategy = governor.get_safe_strategy(strategy)
    print(f"Using fallback: {safe_strategy}")
```

### Example 4: Strange Loop Detection

```python
from prometheus.strange_loop import StrangeLoopDetector, create_prometheus_strange_loops

# Initialize detector
detector = StrangeLoopDetector()

# Load Prometheus loops
loops = create_prometheus_strange_loops()
for loop in loops:
    detector.detected_loops.append(loop)

# Check meta-level
meta_level = detector.get_meta_level()
print(f"Current meta-level: {meta_level}")

# Visualize a loop
if loops:
    viz = detector.visualize_strange_loop(loops[0])
    print(viz)
```

## Component Reference

### v0.80 CRLS Components
- `EvaluatorAgent` - Causal critique generation
- `CorrectorAgent` - Strategic synthesis
- `PerformanceLogger` - CSV logging and visualization

### v0.81 Multi-Game Components
- `MultiGameEvaluator` - Cross-game pattern extraction
- `GameAgnosticCorrector` - Universal strategy synthesis
- `MultiGameLogger` - Multi-game performance tracking

### v0.85 Analogy + Safety
- `AnalogyEngine` - Analogical reasoning
- `AlignmentGovernor` - Safety governance

### v0.89 Meta-Cognition
- `StrangeLoopDetector` - Loop and isomorphism detection

## File Locations

### Source Code
- `prometheus/evaluator_agent.py`
- `prometheus/corrector_agent.py`
- `prometheus/performance_logger.py`
- `prometheus/multi_game_evaluator.py`
- `prometheus/game_agnostic_corrector.py`
- `prometheus/multi_game_logger.py`
- `prometheus/analogy_engine.py`
- `prometheus/alignment_governor.py`
- `prometheus/strange_loop.py`

### Tests
- `test_crls_v080.py`
- `test_multi_game_v081.py`
- `test_integrated_system_v089.py`

### Documentation
- `CRLS_v0_80_Summary.md`
- `MultiGame_CRLS_v0_81_Summary.md`
- `IMPLEMENTATION_SUMMARY_v080_to_v089.md`
- `QUICK_START_GUIDE.md` (this file)

## Troubleshooting

### Import Errors

```python
# Make sure prometheus directory is in path
import sys
sys.path.insert(0, '/home/pmc/Prometheus_v0_PoC')
```

### Missing Dependencies

```bash
pip install matplotlib numpy pandas
```

### Jupyter Notebook Issues

```bash
# Install Jupyter
pip install jupyter

# Install ipykernel
python -m ipykernel install --user
```

## Performance Metrics

Expected performance on Jetson Orin Nano:

| Component | Games/sec | Memory |
|-----------|-----------|--------|
| CRLS Loop | ~10 | <100MB |
| Multi-Game | ~8 | <150MB |
| Analogy | N/A | <50MB |
| Alignment | N/A | <20MB |

## Next Steps

After verifying the system works:

1. **Explore Notebooks**: Interactive demonstrations
2. **Read Summaries**: Detailed component documentation
3. **Customize Agents**: Modify heuristics and strategies
4. **Add New Games**: Extend to other domains
5. **Experiment**: Try different parameters and configurations

## Support

For issues or questions:
- Check documentation in `docs/` directory
- Review code comments in source files
- Run tests to verify installation

## License & Citation

Part of Project Prometheus research prototype.
Implementation based on concepts from:
- I.J. Good's ultraintelligence
- Douglas Hofstadter's GEB
- Judea Pearl's causal inference

---

**Quick Start Complete!** 🚀

You're now ready to explore Prometheus v0.80-v0.89. Start with `test_integrated_system_v089.py` to verify everything works, then explore the Jupyter notebooks for interactive demonstrations.
