
# Project Prometheus v0 PoC

This repository contains the Proof of Concept for Project Prometheus, a system designed to explore the principles of safe, autonomous, and self-improving AI. This PoC demonstrates a multi-agent framework that can perform code refactoring and tackle formal mathematical reasoning using a multi-step, self-correcting search process.

## Core Principles

The PoC is built around four core principles:

1.  **Multi-Agent Collaboration:** A decentralized mesh of specialized agents work together to solve complex tasks.
2.  **Causal Reasoning for AI Alignment:** A simulated Causal Attention Head guides the Coder Agent to focus on causally relevant aspects of the code.
3.  **Recursive Self-Improvement:** The system uses a Causal Reinforcement Learning from Self-Correction (CRLS) loop to modify its own source code, and an adaptive curriculum to generate progressively harder challenges. This now includes a basic form of **meta-learning**, where the system learns from its mistakes in the theorem-proving domain.
4.  **Internal Governance for Safety:** The Modern Centrencephalic System (MCS) acts as an internal alignment governor to ensure the system's actions remain aligned with safety principles.

## Architecture

The system is composed of the following components:

*   **PlannerAgent:** Proposes self-improvement plans or evolutionary goals. In the theorem-proving domain, it acts as a **search strategist**, analyzing a `ProofTree` to guide the search and avoid repeating failed strategies.
*   **CoderAgent:** Generates and refactors Python code or generates tactics in the Lean language. It uses tools to verify its own output.
*   **EvaluatorAgent:** Evaluates generated code for correctness and causal improvement. It can also analyze a failed proof attempt to generate a natural-language **critique**, which is used by the `PlannerAgent` to improve its strategy.
*   **CorrectorAgent:** Formulates new prompts to correct failed attempts.
*   **CurriculumAgent:** Dynamically generates new coding benchmarks or simple mathematical theorems.
*   **MCSSupervisor:** A high-level supervisor that orchestrates the main work loops (self-modification, evolution, theorem proving) and monitors for safety violations. It now manages a **proof tree search**, allowing the agent to backtrack from failed attempts.
*   **Tools:** A suite of tools the agent can use, including a `CompilerTool`, `StaticAnalyzerTool`, and a `LeanTool` for interacting with the Lean proof assistant.
*   **ProofTree:** A data structure that represents the agent's reasoning process, allowing for strategic search and backtracking.

## Setup and Installation

### Prerequisites

*   Python 3.8+
*   Docker
*   A Google API Key with the Gemini API enabled.
*   The Lean 4 proof assistant.

### Local Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/pmcray/Prometheus_v0_PoC.git
    cd Prometheus_v0_PoC
    ```

2.  **Install Lean:**
    Follow the official instructions at [https://leanprover.github.io/lean4/doc/setup.html](https://leanprover.github.io/lean4/doc/setup.html). The simplest method is:
    ```bash
    curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh
    ```

3.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

4.  **Install the Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Set your API Key:**
    Set it as an environment variable named `GOOGLE_API_KEY`.
    ```bash
    export GOOGLE_API_KEY="YOUR_API_KEY"
    ```

## Running the PoC

The main entry point for the PoC is the `main.py` script. It is currently configured to run the latest task, **Meta-Learning Verification**.

```bash
python3 main.py
```

The script will:
1.  Attempt to prove a theorem, intentionally failing on the first try.
2.  The `EvaluatorAgent` will generate a critique of the failed attempt.
3.  The system will re-attempt the proof, using the critique to guide its search and find the correct solution.

You can modify `main.py` to run the other implemented tasks.
