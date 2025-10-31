# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Project Prometheus v0.17+ is a research prototype exploring safe, autonomous, self-improving AI systems based on I.J. Good's ultraintelligence concepts. The system demonstrates internal governance, resource management, ultraparallelism, toolmaking, and strategic reflection capabilities through a modular Python architecture.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install git+https://github.com/cmu-phil/causal-learn.git

# Set API key for Google Gemini
export GOOGLE_API_KEY="YOUR_API_KEY"
```

### Testing
```bash
# Run tests with pytest
pytest

# Run specific test files
pytest tests/test_causal_attention.py

# Run verification scripts
python verify_imports.py
python verify_visualization.py
python verify_causal_inference.py
python verify_auditor.py
python verify_benchmark.py
python verify_budget.py
python verify_interactive.py
```

### Docker Operations
```bash
# Build Docker image (NVIDIA L4T base)
docker build -t prometheus-v0 .

# Run container
docker run --gpus all prometheus-v0
```

### Lean Theorem Prover
```bash
# Build Lean project
lake build

# Update dependencies
lake update
```

## Architecture

The system is built around a modular `prometheus` Python package with the following core components:

### Core Agents
- **MCSSupervisor**: Orchestrates multi-agent operations and resource allocation
- **PlannerAgent**: Generates cost-estimated plans and resource bids
- **ResourceManager**: Manages computational budget and agent reputations
- **CoderAgent**: Handles code generation and synthesis
- **EvaluatorAgent**: Assesses performance and outcomes
- **CorrectorAgent**: Implements error correction and refinement

### Knowledge & Learning Systems
- **KnowledgeAgent**: Manages domain knowledge and learning
- **GeneArchive**: Stores genetic algorithms and evolutionary strategies
- **StrategyArchive**: Maintains strategy patterns and meta-learning
- **BrainMap**: Visualizes system architecture and agent relationships

### Tools & Simulation
- **ToyChemistrySim**: Chemistry simulation environment for testing
- **Tool hierarchy**: Compiler, static analyzer, proof tree, and audit tools
- **AuditorAgent**: Provides safety verification and compliance checking

### Key Design Patterns
- **Resource-aware computation**: All agents operate within budget constraints
- **Reputation-based allocation**: Past performance influences resource access
- **Parallel hypothesis testing**: Multiple competing approaches run simultaneously
- **Tool synthesis**: System can create new tools to improve capabilities
- **Safety-first architecture**: Immutable safety framework prevents harmful modifications

## File Structure

- `prometheus/` - Core Python package with all agent and tool classes
- `main.py` - Primary execution script
- `main_v018.py` - Version 0.18 demonstration script
- `Prometheus_v0.17.ipynb`, `Prometheus_v0.18.ipynb` - Jupyter notebook interfaces
- `tests/` - Test suite with pytest framework
- `toy_problem/` - Example problems for testing algorithms
- `simulation_cache/` - Cached simulation results
- `docs/` - Documentation files
- `venv/` - Python virtual environment

## Safety Considerations

The system includes multiple safety mechanisms:
- Immutable safety framework preventing core safety rule modifications
- Resource budget constraints limiting computational scope
- Audit trail logging for all operations
- Reputation system discouraging harmful behavior
- Strategic reflection limited to capability improvement, not goal modification

## Dependencies

Primary dependencies include:
- google-generativeai (for LLM integration)
- numpy, pandas (data processing)
- pytest (testing)
- pydantic (data validation)
- causallearn (causal inference)
- pyvis (visualization)
- Lean 4 with mathlib (theorem proving)

The system is designed to run in Google Colab with GPU support or locally with NVIDIA Docker containers.