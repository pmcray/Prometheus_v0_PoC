
# Project Prometheus v0 PoC

This repository contains the Proof of Concept for Project Prometheus, a system designed to explore the principles of safe, autonomous, and self-improving AI. This PoC demonstrates a multi-agent framework that can perform code refactoring, tackle formal mathematical reasoning, conduct autonomous experiments, and collaborate with human operators.

## Core Principles

The PoC is built around four core principles:

1.  **Multi-Agent Collaboration:** A decentralized mesh of specialized agents work together to solve complex tasks. This now includes an `AuditorAgent` for AI-assisted oversight.
2.  **Causal Reasoning for AI Alignment:** A simulated Causal Attention Head guides the Coder Agent to focus on causally relevant aspects of the code.
3.  **Recursive Self-Improvement:** The system uses a Causal Reinforcement Learning from Self-Correction (CRLS) loop, an adaptive curriculum, and strategic reflection to learn and improve.
4.  **Internal Governance for Safety:** The Modern Centrencephalic System (MCS) acts as an internal alignment governor, using a "Prometheus Constitution" and resource budgets to ensure the system's actions remain aligned with safety and efficiency principles.

## Architecture

The system is composed of the following components:

*   **PlannerAgent:** Proposes high-level goals, guides proof searches, generates scientific hypotheses, and interacts with the user to clarify ambiguous goals. It is also capable of budget-aware reasoning.
*   **CoderAgent:** Generates Python code and Lean proofs, and translates hypotheses into experiments.
*   **EvaluatorAgent:** Evaluates code, verifies proofs, and generates critiques of failed strategies.
*   **KnowledgeAgent:** Ingests and structures knowledge from formal proofs and scientific papers.
*   **AuditorAgent:** Provides AI-assisted auditing by summarizing the system's complex actions into human-readable audit trails.
*   **MCSSupervisor:** Orchestrates the main work loops and monitors for safety, constitutional, and budget violations.
*   **Tools:** A suite of tools including a `CompilerTool`, `StaticAnalyzerTool`, `LeanTool`, `PDFTool`, `AuditTool`, and a `ToyChemistrySim`.
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

The main entry point is `main.py`. It is currently configured to run the latest task, **Interactive Goal Setting Verification**.

```bash
python3 main.py
```

The script will demonstrate the `PlannerAgent`'s ability to ask clarifying questions when given an ambiguous goal.

You can modify `main.py` and the various `verify_*.py` scripts to run the other implemented tasks.
