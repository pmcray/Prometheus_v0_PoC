
# Project Prometheus v0.16: The Parallel Mind

This repository contains the Proof of Concept for Project Prometheus, a system designed to explore the principles of safe, autonomous, and self-improving AI. This version (v0.16) demonstrates **Ultraparallelism**. The system can now generate a diverse portfolio of competing hypotheses, test them simultaneously in a parallelized simulation environment, and use causal inference to analyze the results and discover the underlying rules of its environment.

## Core Principles

The PoC is built around four core principles from I.J. Good's paper:

1.  **Ultraparallelism:** The system can now generate and test a diverse portfolio of competing hypotheses in parallel, dramatically accelerating the process of scientific discovery. This is visualized on the **Brain Map** as a burst of concurrent agent activity.
2.  **Toolmaking:** The system can analyze the performance of its own tools, identify bottlenecks, and design and synthesize entirely new, superior tools to improve its own capabilities.
3.  **Strategic Reflection & Meta-Learning:** The system can analyze its own critique history to identify strategic weaknesses and then plan and execute a multi-step process to design and integrate new agents to overcome those weaknesses.
4.  **Internal Governance for Safety:** The MCS acts as an internal alignment governor, using a constitution and resource budgets to ensure safety and efficiency.

## Architecture

The system is composed of the following components:

*   **`prometheus` library:** A modular Python package containing all the core agent and tool classes.
*   **`Prometheus_v0.16.ipynb`:** A Jupyter Notebook that serves as the primary interface for demonstrating the system's capabilities. It includes a series of self-contained test cells and a final, powerful demonstration of the ultraparallel discovery cycle.
*   **`PlannerAgent`:** Can now generate a diverse portfolio of competing hypotheses for a single goal.
*   **`ExperimentOrchestrator`:** A new agent that manages the parallel execution of experiments.
*   **`ResultsSynthesizer`:** A new agent that analyzes the results of parallel experiments and uses causal inference to discover the underlying rules of the environment.
*   **`MCSSupervisor`:** Orchestrates the main work loops, including the new `run_discovery_cycle` method that demonstrates the full, end-to-end automated scientist loop.

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

The entire PoC is now consolidated into a single, executable Jupyter Notebook: `Prometheus_v0.16.ipynb`.

1.  Open the `Prometheus_v0.16.ipynb` notebook in Google Colab.
2.  Ensure you have selected a **GPU runtime** (`Runtime -> Change runtime type -> T4 GPU`).
3.  Add your Google API key to the designated cell.
4.  Run the cells sequentially to execute the verification tests and the final, powerful demonstration of the ultraparallel discovery cycle.
