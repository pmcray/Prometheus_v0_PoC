# Contributing to Prometheus

Thank you for your interest in contributing to Prometheus! This document provides guidelines and instructions for contributing to the project.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Adding New Features](#adding-new-features)

---

## Code of Conduct

This project follows a simple code of conduct:

- **Be respectful** and considerate in all interactions
- **Be collaborative** - we're all here to learn and build together
- **Be patient** with newcomers and help them learn
- **Be constructive** in criticism and feedback

---

## Getting Started

### Prerequisites

- **Python 3.10+** (3.11 or 3.12 recommended)
- **Git** for version control
- **TensorFlow 2.15+** for model training
- (Optional) **CUDA 11.8+** for GPU acceleration

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Prometheus_v0_PoC.git
   cd Prometheus_v0_PoC
   ```

3. Add upstream remote:
   ```bash
   git remote add upstream https://github.com/pmcray/Prometheus_v0_PoC.git
   ```

---

## Development Setup

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest black isort flake8 mypy

# Install package in editable mode
pip install -e .
```

### 3. Verify Installation

```bash
# Run verification script
python scripts/verify_end_to_end.py --quick

# Or manual checks
python -c "import prometheus; print('✓ OK')"
prometheus --version
```

---

## How to Contribute

### Types of Contributions

We welcome many types of contributions:

- 🐛 **Bug fixes** - Fix issues in existing code
- ✨ **New features** - Add new games, models, or capabilities
- 📝 **Documentation** - Improve guides, tutorials, or API docs
- 🧪 **Tests** - Add unit tests or integration tests
- 🎨 **Refactoring** - Improve code quality or structure
- 🌍 **Examples** - Add new notebooks or example scripts
- 🚀 **Performance** - Optimize speed or memory usage

###  Finding Issues

- Check [GitHub Issues](https://github.com/pmcray/Prometheus_v0_PoC/issues)
- Look for issues labeled `good-first-issue` or `help-wanted`
- Or create a new issue describing what you'd like to work on

---

## Code Style

### Python Style

We follow **PEP 8** with some modifications:

```bash
# Format code with Black
black prometheus/ scripts/ tests/

# Sort imports with isort
isort prometheus/ scripts/ tests/

# Lint with flake8
flake8 prometheus/ scripts/ tests/ --max-line-length=127
```

### Style Guidelines

#### Naming Conventions

- **Functions/methods**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_CASE`
- **Private methods**: `_leading_underscore`

```python
# Good
class PrometheusGoAgent:
    DEFAULT_TEMPERATURE = 0.7

    def select_move(self, state):
        return self._compute_best_move(state)

    def _compute_best_move(self, state):
        pass
```

#### Docstrings

Use Google-style docstrings:

```python
def calculate_elo_difference(win_rate: float) -> float:
    """
    Calculate ELO difference from win rate.

    Args:
        win_rate: Win rate as fraction (0.0 to 1.0)

    Returns:
        ELO difference (positive = stronger)

    Example:
        >>> calculate_elo_difference(0.75)
        193.0
    """
    return -400 * np.log10((1 / win_rate) - 1)
```

#### Type Hints

Add type hints to all public functions:

```python
from typing import List, Dict, Optional, Tuple

def train_agent(
    agent: Agent,
    num_games: int,
    verbose: bool = False
) -> Tuple[Agent, Dict[str, float]]:
    """Train agent and return trained agent with metrics."""
    ...
```

#### Imports

Organize imports in this order:

```python
# 1. Standard library
import sys
from pathlib import Path

# 2. Third-party
import numpy as np
import tensorflow as tf

# 3. Local
from prometheus.models import PrometheusGoAgent
from prometheus.environments.go import GoEnvironment
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_environments.py

# Run with coverage
pytest --cov=prometheus tests/

# Run with verbose output
pytest -v tests/
```

### Writing Tests

Create tests in `tests/` directory:

```python
# tests/test_go_environment.py
import pytest
from prometheus.environments.go import GoEnvironment


class TestGoEnvironment:
    def test_reset(self):
        """Test environment reset."""
        env = GoEnvironment(board_size=9)
        state = env.reset()

        assert state.shape == (9, 9, 1)
        assert np.all(state == 0)  # Empty board

    def test_legal_moves(self):
        """Test legal moves on empty board."""
        env = GoEnvironment(board_size=9)
        env.reset()

        legal_moves = env.get_legal_actions()

        assert len(legal_moves) == 81  # All positions legal
        assert (4, 4) in legal_moves  # Center is legal
```

### Test Requirements

- All new features should include tests
- Bug fixes should include regression tests
- Maintain >80% code coverage
- Tests should be fast (<1s per test when possible)

---

## Pull Request Process

### 1. Create a Branch

```bash
# Update main
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

### 2. Make Changes

- Write code following style guidelines
- Add/update tests
- Update documentation
- Run tests locally

### 3. Commit Changes

Use clear, descriptive commit messages:

```bash
# Good commit messages
git commit -m "feat: Add MCTS parallelization support"
git commit -m "fix: Resolve memory leak in Go environment"
git commit -m "docs: Add transfer learning tutorial"
git commit -m "test: Add unit tests for Chess environment"

# Bad commit messages (avoid these)
git commit -m "fix bug"
git commit -m "updates"
git commit -m "WIP"
```

**Commit Message Format**:
```
<type>: <short description>

<detailed description if needed>

<footer: issue references, breaking changes, etc.>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

### 4. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Then create Pull Request on GitHub
```

### 5. PR Guidelines

Your PR should include:

✅ **Clear title** describing the change
✅ **Description** explaining what and why
✅ **Tests** for new functionality
✅ **Documentation** updates if needed
✅ **No merge conflicts** with main branch
✅ **Passing CI checks**

**PR Template**:
```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement

## Testing
- [ ] Added/updated unit tests
- [ ] Manual testing completed
- [ ] All tests pass locally

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No breaking changes (or documented)
```

### 6. Code Review

- Be responsive to feedback
- Make requested changes
- Discuss disagreements constructively
- Be patient - reviews may take time

---

## Adding New Features

### Adding a New Game

To add support for a new game (e.g., Shogi):

1. **Create environment** in `prometheus/environments/shogi.py`:
   ```python
   class ShogiEnvironment(BaseEnvironment):
       def __init__(self):
           self.board_size = 9

       def reset(self):
           """Reset to starting position."""
           ...

       def step(self, action):
           """Make a move."""
           ...

       def get_legal_actions(self):
           """Get legal moves."""
           ...

       def is_terminal(self):
           """Check if game is over."""
           ...
   ```

2. **Create model** in `prometheus/models/shogi_models.py`:
   ```python
   class ShogiAgent(BaseAgent):
       def __init__(self, model):
           self.model = model

       def select_move(self, state):
           """Select move using policy network."""
           ...
   ```

3. **Add training** in `prometheus/training/shogi_training.py`:
   ```python
   def train_shogi_agent(agent, num_games=100, verbose=True):
       """Train Shogi agent via self-play."""
       ...
   ```

4. **Add tests** in `tests/test_shogi.py`:
   ```python
   class TestShogiEnvironment:
       def test_reset(self):
           ...

       def test_legal_moves(self):
           ...
   ```

5. **Add CLI support** in `prometheus_cli.py`:
   ```python
   parser.add_argument('--game', choices=['go', 'chess', 'shogi'])
   ```

6. **Add documentation**:
   - Update README.md
   - Add example notebook
   - Update FAQ.md

### Adding New Functionality

For other features:

1. **Plan** the design - discuss in an issue first
2. **Implement** with tests
3. **Document** the feature
4. **Add examples** showing how to use it
5. **Submit PR** following guidelines above

---

## Development Tips

### Useful Commands

```bash
# Format code
black .

# Type checking
mypy prometheus/

# Run single test
pytest tests/test_go_environment.py::TestGoEnvironment::test_reset -v

# Watch mode (auto-run tests on file change)
pytest-watch tests/

# Profile code
python -m cProfile -o profile.stats your_script.py
python -m pstats profile.stats
```

### Debugging

```bash
# Add breakpoint in code
import pdb; pdb.set_trace()

# Run pytest with debugger
pytest --pdb tests/

# Verbose TensorFlow logging
export TF_CPP_MIN_LOG_LEVEL=0
```

### Performance

- Use profiling to identify bottlenecks
- Prefer NumPy operations over Python loops
- Cache expensive computations
- Use generators for large datasets
- Enable XLA compilation for TensorFlow

---

## Questions?

- **Documentation**: Check README.md, FAQ.md, TROUBLESHOOTING.md
- **Issues**: Search [existing issues](https://github.com/pmcray/Prometheus_v0_PoC/issues)
- **Discussion**: Open a new issue for questions
- **Email**: Contact maintainers (see README)

---

## License

By contributing to Prometheus, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to Prometheus! 🔥**

Every contribution, no matter how small, makes a difference.
