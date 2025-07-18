
# Project Prometheus v0 PoC

This repository contains the Proof of Concept for Project Prometheus, a system designed to explore the principles of safe, autonomous, and self-improving AI. This PoC demonstrates a multi-agent framework that can perform code refactoring, tackle formal mathematical reasoning, and begin to conduct autonomous experiments in a simulated environment.

## Core Principles

The PoC is built around four core principles:

1.  **Multi-Agent Collaboration:** A decentralized mesh of specialized agents work together to solve complex tasks.
2.  **Causal Reasoning for AI Alignment:** A simulated Causal Attention Head guides the Coder Agent to focus on causally relevant aspects of the code.
3.  **Recursive Self-Improvement:** The system uses a Causal Reinforcement Learning from Self-Correction (CRLS) loop, an adaptive curriculum, and strategic reflection to learn and improve.
4.  **Internal Governance for Safety:** The Modern Centrencephalic System (MCS) acts as an internal alignment governor to ensure the system's actions remain aligned with safety principles.

## Architecture

The system is composed of the following components:

*   **PlannerAgent:** Proposes high-level goals, guides proof searches, and generates scientific hypotheses.
*   **CoderAgent:** Generates Python code, Lean proofs, and translates natural-language hypotheses into executable experiments.
*   **EvaluatorAgent:** Evaluates code, verifies proofs, and generates critiques of failed strategies.
*   **KnowledgeAgent:** Ingests and structures knowledge from formal proofs and scientific papers.
*   **MCSSupervisor:** Orchestrates the main work loops (self-modification, evolution, theorem proving, experimentation) and monitors for safety violations.
*   **Tools:** A suite of tools including a `CompilerTool`, `StaticAnalyzerTool`, `LeanTool`, `PDFTool`, and a `ToyChemistrySim` for simulated experiments.
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
    ```

4.  **Set your API Key:**
    ```bash
    export GOOGLE_API_KEY="YOUR_API_KEY"
    ```

## Running the PoC

The main entry point is `main.py`. It is currently configured to run the latest task, **Simulated Laboratory Environment**.

```bash
python3 main.py
```

The script will:
1.  Initialize a simulated chemistry environment.
2.  The `PlannerAgent` will propose hypotheses to maximize a target chemical.
3.  The `CoderAgent` will translate these hypotheses into experiments.
4.  The `MCSSupervisor` will run the experiments and feed the results back to the `PlannerAgent`, demonstrating a closed-loop scientific discovery process.

You can modify `main.py` to run the other implemented tasks.
