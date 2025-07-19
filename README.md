# Project Prometheus v0.11: The Visual Mind

This repository contains the Proof of Concept for Project Prometheus, a system designed to explore the principles of safe, autonomous, and self-improving AI. This version (v0.11) introduces a modular, notebook-first architecture and a "Brain Map" visualization to demonstrate the dynamic formation of expert agent circuits.

## Core Principles

The PoC is built around four core principles from I.J. Good's paper:

1.  **Multi-Agent Collaboration (Causal Agentic Mesh):** A decentralized mesh of specialized agents work together. This is now visualized through the **Brain Map**, which shows the dynamic formation and dissolution of temporary "expert circuits" to solve specific sub-problems.
2.  **Recursive Self-Improvement:** The system uses a CRLS loop, an adaptive curriculum, and strategic reflection to learn and improve.
3.  **Ultraparallelism:** The system can entertain and test multiple, competing hypotheses in parallel, a key to rapid discovery.
4.  **Internal Governance for Safety:** The MCS acts as an internal alignment governor, using a constitution and resource budgets to ensure safety and efficiency.

## Architecture

The system is composed of the following components:

*   **`prometheus` library:** A modular Python package containing all the core agent and tool classes.
*   **`Prometheus_v0.11.ipynb`:** A Jupyter Notebook that serves as the primary interface for demonstrating the system's capabilities. It includes a series of self-contained test cells and a final, visual demonstration of the dynamic agent mesh.
*   **`BrainMap`:** A visualization tool that generates an interactive graph of the agent mesh, showing the dynamic activation and formation of expert circuits in real-time.

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

The entire PoC is now consolidated into a single, executable Jupyter Notebook: `Prometheus_v0.11.ipynb`.

1.  Open the `Prometheus_v0.11.ipynb` notebook in Google Colab.
2.  Ensure you have selected a **GPU runtime** (`Runtime -> Change runtime type -> T4 GPU`).
3.  Add your Google API key to the designated cell.
4.  Run the cells sequentially to execute the verification tests and the final, visual demonstration of the Dynamic Mesh.