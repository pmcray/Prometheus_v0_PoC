
# Project Prometheus v0.14: The Strategic Learner

This repository contains the Proof of Concept for Project Prometheus, a system designed to explore the principles of safe, autonomous, and self-improving AI. This version (v0.14) demonstrates **Strategic Reflection and Capability Acquisition**. The system can now analyze its own patterns of failure, identify high-level strategic weaknesses, and execute a multi-step "research project" to design and synthesize new agents, thereby acquiring entirely new capabilities.

## Core Principles

The PoC is built around four core principles from I.J. Good's paper:

1.  **Strategic Reflection & Meta-Learning:** The system can now perform a full, end-to-end meta-learning cycle. It analyzes its own critique history to identify strategic weaknesses and then plans and executes a multi-step process to design and integrate new agents to overcome those weaknesses.
2.  **Architectural Self-Modification:** The system can design and synthesize entirely new agents to augment its own intelligence. This is visualized through the **Brain Map**, which now shows the permanent addition of new, self-designed agents to the mesh.
3.  **Multi-Agent Collaboration (Causal Agentic Mesh):** A decentralized mesh of specialized agents work together to achieve these complex goals.
4.  **Internal Governance for Safety:** The MCS acts as an internal alignment governor, using a constitution and resource budgets to ensure safety and efficiency.

## Architecture

The system is composed of the following components:

*   **`prometheus` library:** A modular Python package containing all the core agent and tool classes.
*   **`Prometheus_v0.14.ipynb`:** A Jupyter Notebook that serves as the primary interface for demonstrating the system's capabilities. It includes a series of self-contained test cells and a final, powerful demonstration of the meta-learning cycle.
*   **`PlannerAgent`:** A high-level strategic agent that can now perform **strategic reflection** by analyzing its own critique history to generate **meta-critiques**. It can then use these meta-critiques to generate multi-step **research proposals** for acquiring new capabilities.
*   **`CoderAgent`:** Can synthesize new agent classes from natural-language blueprints.
*   **`MCSSupervisor`:** Orchestrates the main work loops, including the new `run_meta_learning_cycle` method that demonstrates the full, end-to-end self-teaching loop.

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

The entire PoC is now consolidated into a single, executable Jupyter Notebook: `Prometheus_v0.14.ipynb`.

1.  Open the `Prometheus_v0.14.ipynb` notebook in Google Colab.
2.  Ensure you have selected a **GPU runtime** (`Runtime -> Change runtime type -> T4 GPU`).
3.  Add your Google API key to the designated cell.
4.  Run the cells sequentially to execute the verification tests and the final, powerful demonstration of the meta-learning cycle.
