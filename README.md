
# Project Prometheus v0 PoC

This repository contains the Proof of Concept for Project Prometheus, a system designed to explore the principles of safe, autonomous, and self-improving AI. This PoC demonstrates a multi-agent framework that can perform a code refactoring task while being governed by principles of causal reasoning and internal safety.

## Core Principles

The PoC is built around four core principles:

1.  **Multi-Agent Collaboration:** A decentralized mesh of specialized agents (Planner, Coder, Evaluator) work together to solve a complex coding task.
2.  **Causal Reasoning for AI Alignment:** A simulated Causal Attention Head guides the Coder Agent to focus on causally relevant aspects of the code, preventing it from being distracted by superficial correlations.
3.  **Recursive Self-Improvement:** The Causal Reinforcement Learning from Self-Correction (CRLS) loop allows the system to evaluate its own work based on causal principles and attempt to correct its mistakes. This includes the ability to modify its own source code to improve its performance.
4.  **Internal Governance for Safety:** The Modern Centrencephalic System (MCS) acts as an internal alignment governor, providing meta-level oversight to ensure the system's actions remain aligned with safety principles.

## Architecture

The system is composed of the following components:

*   **PlannerAgent:** Receives a high-level goal and creates an initial, actionable instruction. It can also analyze the system's own code to propose self-improvements.
*   **CoderAgent:** Receives an instruction and uses the Gemini API to generate or refactor code. It is guided by the `CausalAttentionWrapper` and uses a suite of tools (`CompilerTool`, `StaticAnalyzerTool`) to verify its own code before submitting it for evaluation.
*   **EvaluatorAgent:** Receives the newly generated code and evaluates it based on two criteria:
    1.  **Correctness:** Does the new code pass the unit tests?
    2.  **Causal Improvement:** Does the new code represent a genuine improvement in time complexity? (Assessed via AST analysis).
*   **CorrectorAgent:** If the `EvaluatorAgent` finds a flaw, the `CorrectorAgent` receives the critique and formulates a new, more targeted prompt for the `CoderAgent`.
*   **BenchmarkAgent:** Can dynamically generate new "toy problems" and their corresponding unit tests, introducing a dynamic element to the environment and forcing the system to generalize.
*   **MCSSupervisor:** A high-level supervisor that encapsulates the entire CRLS loop and monitors for safety violations, such as attempts to modify the test files. All agent actions that interact with the environment (writing files, using tools) are routed through the supervisor, which operates within a secure, sandboxed Docker environment.

## Setup and Installation

### Prerequisites

*   Python 3.8+
*   Docker
*   A Google API Key with the Gemini API enabled.

### Local Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/pmcray/Prometheus_v0_PoC.git
    cd Prometheus_v0_PoC
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set your API Key:**
    You will need to add your Google API key to the `Prometheus_v0_PoC.ipynb` notebook in the designated cell, or set it as an environment variable named `GOOGLE_API_KEY`.

### Docker Setup

1.  **Build the Docker image:**
    ```bash
    docker build -t prometheus_v0_poc .
    ```

2.  **Run the Docker container:**
    The PoC is designed to be run from the command line. You can run the main script within the container:
    ```bash
    docker run --rm -it -e GOOGLE_API_KEY=$GOOGLE_API_KEY prometheus_v0_poc
    ```

## Running the PoC

The main entry point for the PoC is the `main.py` script.

1.  **Set your API Key:**
    Make sure your `GOOGLE_API_KEY` environment variable is set.
    ```bash
    export GOOGLE_API_KEY="YOUR_API_KEY"
    ```

2.  **Run the script:**
    ```bash
    python3 main.py
    ```

The script will execute the two main tasks of the PoC:
1.  **Self-Modification:** The system will attempt to refactor its own `EvaluatorAgent` to be more efficient.
2.  **Benchmark Generation:** The system will generate a new toy problem and its corresponding tests.

The `Prometheus_v0_PoC.ipynb` notebook is also available and contains a consolidated version of the code and a narrative walkthrough of the demonstration scenarios.
