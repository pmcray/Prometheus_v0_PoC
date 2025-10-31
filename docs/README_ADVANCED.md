# Prometheus Advanced Implementation (v0.19+)

A comprehensive implementation of the advanced features outlined in the Project Prometheus workplans, spanning versions v0.19 through v0.44.

## 🚀 Features Implemented

### ✅ v0.19: Foundation Features
- **Robust JSON Communication Protocol**: Schema-driven inter-agent messaging
- **AST-Based Causal Attention**: Sophisticated code complexity analysis
- **Enhanced Performance Logging**: Run-based aggregation with profiling

### ✅ v0.20-v0.21: Memory & Causal Analysis
- **Memory Agent with Vector Storage**: Persistent experiential knowledge using FAISS
- **Dynamic Performance Analysis**: Runtime profiling and comparison
- **Self-Referential Critique System**: Meta-level evaluation feedback

### ✅ v0.22-v0.23: Metacognition & Governance
- **Meta-Correction Capabilities**: Strategy modification based on failure patterns
- **Constitutional Governance**: Principle-based review system
- **Cyclical Failure Detection**: Pattern recognition and intervention

### ✅ v0.25-v0.29: Cognitive Architecture
- **Strange Loop Implementation**: Self-referential cognitive processes
- **Analogical Search**: Solution pattern transfer across problems
- **Attention Logging**: Figure/ground cognitive focus tracking
- **Gene Bank System**: Versioned code storage and retrieval

### ✅ v0.30-v0.34: Visualization & Brain Map
- **Real-time Brain Map**: WebSocket-based cognitive state visualization
- **Interactive Dashboard**: HTML interface with D3.js visualizations
- **RSI Loop Visualization**: Intelligence explosion demonstration
- **Performance Curve Tracking**: Real-time capability growth monitoring

### ✅ v0.40-v0.44: Full RSI Cycle
- **Dynamic Module Reloading**: Hot-swapping of agent code
- **Self-Modification Engine**: Complete patch application and validation
- **Stateless Agent Management**: Safe instantiation patterns
- **Constitutional Oversight**: Governance of self-improvement process

### 🔧 v0.35-v0.39: Meta-Learning (Partial)
- Framework established for fine-tuning and LoRA adapter management
- Synthetic data generation capabilities designed
- Mixture-of-experts architecture planned

## 📁 Project Structure

```
prometheus/
├── schemas/                    # Communication protocol definitions
│   ├── __init__.py
│   └── communication.py       # Pydantic schemas for all message types
├── causal_attention.py        # AST-based causal analysis
├── enhanced_performance_logger.py  # Advanced logging and profiling
├── memory_agent.py            # Memory and gene bank systems
├── enhanced_planner.py        # Strategic planning with causal focus
├── enhanced_coder.py          # Code generation with retry logic
├── enhanced_evaluator.py      # Multi-modal evaluation system
├── enhanced_corrector.py      # Meta-reasoning and correction
├── enhanced_mcs.py           # Modern Centrencephalic System
├── brain_visualizer.py       # Real-time visualization system
├── enhanced_reloader.py      # Dynamic module reloading
└── ...

prometheus_orchestrator.py    # Main system orchestrator
test_prometheus_advanced.py   # Comprehensive test suite
requirements_advanced.txt     # Enhanced dependencies
README_ADVANCED.md            # This file
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- Google Gemini API key (optional for mock testing)
- Git (for patch application)

### Installation

1. **Install dependencies**:
```bash
pip install -r requirements_advanced.txt
```

2. **Set up API key** (optional):
```bash
export GOOGLE_API_KEY="your_gemini_api_key"
```

3. **Install additional dependencies** for full functionality:
```bash
# For memory system (sentence transformers)
pip install sentence-transformers faiss-cpu

# For visualization
pip install websockets fastapi uvicorn

# For profiling
pip install memory-profiler psutil
```

## 🚀 Quick Start

### Basic Usage

```python
import asyncio
from prometheus_orchestrator import PrometheusOrchestrator

async def main():
    # Initialize the orchestrator
    orchestrator = PrometheusOrchestrator(
        enable_visualization=True,
        enable_memory=True,
        enable_rsi=True
    )

    # Start the system
    await orchestrator.start_system()

    # Run a code optimization task
    task = "Optimize this nested loop for better time complexity"
    code = """
def find_duplicates(nums):
    duplicates = []
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] == nums[j] and nums[i] not in duplicates:
                duplicates.append(nums[i])
    return duplicates
"""

    result = orchestrator.run_crls_loop(task, code)

    if result['success']:
        print("✅ Optimization successful!")
        print(f"Final code:\n{result['final_code']}")
    else:
        print(f"❌ Optimization failed: {result['reason']}")

    # View system status
    status = orchestrator.get_system_status()
    print(f"System Status: {status}")

    await orchestrator.stop_system()

# Run the system
asyncio.run(main())
```

### Running the Full Demonstrator

```bash
python prometheus_orchestrator.py
```

This will:
1. Start the complete Prometheus system
2. Initialize the brain map visualization
3. Run a demonstration task
4. Show the results and system status
5. Generate `prometheus_brain_map.html` for visualization

### Running Tests

```bash
# Quick validation
python test_prometheus_advanced.py

# Full test suite
pytest test_prometheus_advanced.py -v

# With coverage
pytest test_prometheus_advanced.py --cov=prometheus
```

## 🧠 Brain Map Visualization

The system generates a real-time visualization showing:

- **Agent Assemblies**: Core cognitive components (Planner, Coder, Evaluator, etc.)
- **Activation Levels**: Visual representation of agent activity
- **Causal Flows**: Information flow between agents
- **MCS Interventions**: Governance actions and safety measures
- **Performance Curves**: Intelligence explosion tracking

Open `prometheus_brain_map.html` in a web browser after running the system.

## 🔄 Recursive Self-Improvement (RSI)

The system demonstrates true RSI capabilities:

1. **Failure Detection**: Identifies when standard optimization fails
2. **Self-Analysis**: Analyzes its own correction strategies
3. **Code Generation**: Generates patches to improve its own logic
4. **Verification**: Tests modifications in sandboxed environment
5. **Hot-Swapping**: Dynamically reloads improved components
6. **Performance Tracking**: Monitors improvement across generations

## 🧪 Key Components

### Causal Attention Head
- AST-based complexity analysis
- Structural change detection
- Optimization hint generation

### Memory Agent
- Vector-based similarity search
- Failure/success pattern storage
- Analogical reasoning support

### Enhanced MCS
- Constitutional principle enforcement
- Attention auditing
- Cyclical failure detection
- Meta-causal analysis

### Brain Visualizer
- Real-time WebSocket communication
- Interactive D3.js interface
- State change animations
- Performance curve plotting

## 🔧 Configuration

### Feature Toggles
```python
orchestrator = PrometheusOrchestrator(
    enable_visualization=True,   # Real-time brain map
    enable_memory=True,         # Persistent memory system
    enable_rsi=True            # Recursive self-improvement
)
```

### Memory System
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Vector store: FAISS (CPU optimized)
- Similarity threshold: 0.7 (configurable)

### Visualization
- WebSocket server: `localhost:8765`
- Update rate: Real-time
- Supported browsers: Modern browsers with WebSocket support

## 📊 Performance Metrics

The system tracks:
- **Success Rate**: Percentage of problems solved
- **Efficiency**: Average attempts per solution
- **RSI Generation**: Self-improvement cycles completed
- **Attention Distribution**: Cognitive focus patterns
- **Memory Utilization**: Pattern retrieval effectiveness

## 🚨 Safety Features

### Constitutional Governance
- Principle-based review of all modifications
- Reward hacking detection
- Meta-causal path analysis

### Stability Monitoring
- Cyclical failure detection
- Cortical activity limits
- RSI stability thresholds

### Rollback Capabilities
- Automatic backup creation
- Syntax validation
- Verification testing
- Safe rollback on failure

## 🔮 Future Extensions

The architecture supports planned features:

### v0.35-v0.39: Meta-Learning
- Fine-tuning infrastructure ready
- LoRA adapter management framework
- Synthetic data generation pipeline

### Advanced Features
- Multiple LLM backend support
- Distributed agent execution
- Advanced optimization algorithms
- Enhanced visualization effects

## 🤝 Contributing

When extending the system:

1. Follow the established patterns in `schemas/communication.py`
2. Implement proper error handling and logging
3. Add visualization updates for new components
4. Include comprehensive tests
5. Update the brain map interface as needed

## 📚 References

- [Project Prometheus Workplans](./workplan_files/)
- [I.J. Good's 1965 Paper on Ultraintelligence](https://www.stat.vt.edu/tech_reports/2005/GoodTechReport.pdf)
- [Hofstadter's Strange Loops](https://en.wikipedia.org/wiki/Strange_loop)

## 📄 License

This implementation is part of the Project Prometheus research prototype. See main project documentation for licensing details.

---

*This implementation represents the state-of-the-art in autonomous self-improving AI systems as of 2025, incorporating cutting-edge research in causal reasoning, metacognition, and recursive self-improvement.*