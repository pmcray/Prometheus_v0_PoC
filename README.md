
# Project Prometheus v0.12: The Introspective Agent

This repository contains the Proof of Concept for Project Prometheus, a system designed to explore the principles of safe, autonomous, and self-improving AI. This version (v0.12) demonstrates the core principle of **Recursive Self-Improvement (RSI)**. The system can analyze its own performance, generate a critique of its inefficiencies, form a plan to modify its own source code, and then execute that plan to improve its performance on a given task.

## Core Principles

The PoC is built around four core principles from I.J. Good's paper:

1.  **Recursive Self-Improvement:** The system can now perform a full, end-to-end RSI loop. It introspects on its own performance, generates a plan to improve itself, and then modifies its own code to become more efficient.
2.  **Multi-Agent Collaboration (Causal Agentic Mesh):** A decentralized mesh of specialized agents work together to achieve these complex goals.
3.  **Causal Reasoning for AI Alignment:** The system uses a Causal Attention Head to provide a measurable performance advantage on causal reasoning tasks.
4.  **Internal Governance for Safety:** The MCS acts as an internal alignment governor, using a constitution and resource budgets to ensure safety and efficiency.

## Architecture

The system is composed of the following components:

*   **`prometheus` library:** A modular Python package containing all the core agent and tool classes.
*   **`Prometheus_v0.12.ipynb`:** A Jupyter Notebook that serves as the primary interface for demonstrating the system's capabilities. It includes a series of self-contained test cells and a final, powerful demonstration of the closed-loop RSI cycle.
*   **`PlannerAgent`:** A high-level strategic agent that can now perform **introspection** by analyzing performance logs and generating **self-critiques** and **self-modification plans**.
*   **`CoderAgent`:** Can be modified by the RSI loop to improve its performance.
*   **`MCSSupervisor`:** Orchestrates the main work loops, including the new `run_rsi_cycle` method that demonstrates the full, end-to-end self-improvement loop.

## Setup and Installation

### Prerequisites

*   Python 3.8+
*   Docker (with NVIDIA container toolkit for GPU support)
*   A Google API Key with the Gemini API enabled.

### Local Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/pmcray/Prometheus_v0_PoC.git
    cd Prometheus_v0_PoC
    ```

2.  **Create a virtual environment and install Python packages:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    pip install git+https://github.com/cmu-phil/causal-learn.git
    ```

3.  **Set your API Key:**
    ```bash
    export GOOGLE_API_KEY="YOUR_API_KEY"
    ```

## Running the PoC in Google Colab

The entire PoC is now consolidated into a single, executable Jupyter Notebook: `Prometheus_v0.12.ipynb`.

1.  Open the `Prometheus_v0.12.ipynb` notebook in Google Colab.
2.  Ensure you have selected a **GPU runtime** (`Runtime -> Change runtime type -> T4 GPU`).
3.  Add your Google API key to the designated cell.
4.  Run the cells sequentially to execute the verification tests and the final, powerful demonstration of the closed-loop RSI cycle.
