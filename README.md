# Project Prometheus v0 PoC

This repository contains the Proof of Concept for Project Prometheus, a system designed to explore the principles of safe, autonomous, and self-improving AI, based on the ideas described in I.J. Good's seminal 1965 paper, "Speculations Concerning the First Ultraintelligent Machine". A copy of the paper can be found in the docs repository. This PoC demonstrates a multi-agent framework that can perform a code refactoring task while being governed by principles of causal reasoning and internal safety.

## Core Principles

The PoC is built around four core principles:

1.  **Multi-Agent Collaboration:** A decentralized mesh of specialized agents (Planner, Coder, Evaluator) work together to solve a complex coding task.
2.  **Causal Reasoning for AI Alignment:** A simulated Causal Attention Head guides the Coder Agent to focus on causally relevant aspects of the code, preventing it from being distracted by superficial correlations.
3.  **Recursive Self-Improvement:** The Causal Reinforcement Learning from Self-Correction (CRLS) loop allows the system to evaluate its own work based on causal principles and attempt to correct its mistakes.
4.  **Internal Governance for Safety:** The Modern Centrencephalic System (MCS) acts as an internal alignment governor, providing meta-level oversight to ensure the system's actions remain aligned with safety principles.

## Architecture

The system is composed of the following components:

*   **PlannerAgent:** Receives a high-level goal and creates an initial, actionable instruction.
*   **CoderAgent:** Receives an instruction and uses the Gemini API to generate or refactor code. It is guided by the `CausalAttentionWrapper`.
*   **EvaluatorAgent:** Receives the newly generated code and evaluates it based on two criteria:
    1.  **Correctness:** Does the new code pass the unit tests?
    2.  **Causal Improvement:** Does the new code represent a genuine improvement in time complexity? (Assessed via AST analysis).
*   **CorrectorAgent:** If the `EvaluatorAgent` finds a flaw, the `CorrectorAgent` receives the critique and formulates a new, more targeted prompt for the `CoderAgent`.
*   **MCSSupervisor:** A high-level supervisor that encapsulates the entire CRLS loop and monitors for safety violations, such as attempts to modify the test files.

## Setup and Installation

### Prerequisites

*   Python 3.8+
*   Docker (optional, for running in a containerized environment)
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
    Create a file named `.env` in the root of the project directory and add your Google API key to it like this:
    ```
    GOOGLE_API_KEY="YOUR_API_KEY"
    ```

### Docker Setup (for Jetson Orin Nano or other Docker environments)

1.  **Build the Docker image:**
    ```bash
    docker build -t prometheus_v0_poc .
    ```

2.  **Run the Docker container:**
    The PoC is designed to be run interactively within the Jupyter notebook. You can run the container and then access the notebook.

## Running the PoC

The entire Proof of Concept is contained within the `Prometheus_v0_PoC.ipynb` notebook.

1.  **Start the Jupyter Notebook server:**
    ```bash
    jupyter notebook
    ```

2.  **Open the notebook:**
    In your browser, open the `Prometheus_v0_PoC.ipynb` notebook.

3.  **Run the cells:**
    You can run the cells sequentially to see the entire process, from setup to the demonstration scenarios. The notebook is divided into two main scenarios:
    *   **Scenario A: Successful Refactoring:** Demonstrates the full CRLS loop successfully refactoring an inefficient function.
    *   **Scenario B: Safety Intervention:** Demonstrates the MCS intervening to stop the agent from "cheating" by modifying the test file.