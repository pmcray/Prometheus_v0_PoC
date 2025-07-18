
# Project Prometheus v0 PoC

This repository contains the Proof of Concept for Project Prometheus, a system designed to explore the principles of safe, autonomous, and self-improving AI. This PoC demonstrates a multi-agent framework that can perform code refactoring, tackle formal mathematical reasoning, and demonstrate superior performance on a causal reasoning benchmark.

## Core Principles

The PoC is built around four core principles from I.J. Good's paper:

1.  **Multi-Agent Collaboration (Causal Agentic Mesh):** A decentralized mesh of specialized agents work together to solve complex tasks.
2.  **Causal Reasoning for AI Alignment:** The system now implements a **Causal Attention Head v0.2**, which uses a "causal calculus" to build a causal graph of a system and reason about it. This provides a measurable performance advantage over standard, correlation-based models.
3.  **Recursive Self-Improvement:** The system uses a CRLS loop, an adaptive curriculum, and strategic reflection to learn and improve.
4.  **Internal Governance for Safety:** The MCS acts as an internal alignment governor, using a constitution and resource budgets to ensure safety and efficiency.

## Architecture

The system is composed of the following components:

*   **PlannerAgent:** A high-level strategic agent that can form "expert circuits," generate hypotheses, and, in the causal domain, use a `CausalGraphTool` to build a causal model and form a reasoning strategy.
*   **CoderAgent:** Generates Python code, Lean proofs, and can now perform causal reasoning when guided by a Causal Attention Prompt from the `PlannerAgent`.
*   **EvaluatorAgent:** Evaluates code, verifies proofs, and generates critiques of failed strategies.
*   **KnowledgeAgent:** Ingests and structures knowledge from formal proofs and scientific papers.
*   **MCSSupervisor:** Orchestrates the main work loops and monitors for safety, constitutional, and budget violations.
*   **Tools:** A suite of tools including a `CompilerTool`, `StaticAnalyzerTool`, `LeanTool`, `PDFTool`, `AuditTool`, a `ToyChemistrySim`, and a `CausalGraphTool`.
*   **Archives & Logs:** `GeneArchive`, `StrategyArchive`, and `PerformanceLogger` to enable learning and memory.

## Setup and Installation

### Prerequisites

*   Python 3.8+
*   Docker
*   A Google API Key with the Gemini API enabled.
*   The Lean 4 proof assistant.
*   Pandoc.

### Local Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/pmcray/Prometheus_v0_PoC.git
    cd Prometheus_v0_PoC
    ```

2.  **Install System Dependencies (Lean & Pandoc):**
    ```bash
    # Install Lean
    curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh
    # Install Pandoc (on Debian/Ubuntu)
    sudo apt-get update && sudo apt-get install pandoc -y
    ```

3.  **Create a virtual environment and install Python packages:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    pip install git+https://github.com/cmu-phil/causal-learn.git
    ```

4.  **Set your API Key:**
    ```bash
    export GOOGLE_API_KEY="YOUR_API_KEY"
    ```

## Running the PoC

The main entry point is `main.py`. It is currently configured to run the latest task, **Causal Reasoning Verification**.

```bash
python3 main.py
```

The script will:
1.  Generate a dataset with a known causal structure.
2.  Pose a counterfactual question to a standard LLM, which will likely answer incorrectly based on correlation.
3.  The Prometheus system will then build a causal graph of the data, use it to form a Causal Attention Prompt, and correctly answer the question, demonstrating superior causal reasoning.

You can modify `main.py` and the various `verify_*.py` scripts to run the other implemented tasks.
