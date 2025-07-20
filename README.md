# Project Prometheus v0.17: The Economist

This repository contains the Proof of Concept for Project Prometheus, a system designed to explore the principles of safe, autonomous, and self-improving AI. This version (v0.17) demonstrates **Internal Governance and Resource Management**. The system now operates within a finite "computational budget," and agents must compete for resources in an internal market. The system learns to allocate its budget intelligently, rewarding efficient agents and penalizing wasteful ones, a critical step towards building a safe and practical ultraintelligent machine.

## Core Principles

The PoC is built around four core principles from I.J. Good's paper:

1.  **Internal Governance & Economics:** The system now manages a finite computational budget. Agents must bid for resources, and an "auctioneer" allocates the budget to the most cost-effective and reliable plans. A reputation-based reward system incentivizes efficiency and success.
2.  **Ultraparallelism:** The system can generate and test a diverse portfolio of competing hypotheses in parallel, dramatically accelerating the process of scientific discovery.
3.  **Toolmaking:** The system can analyze the performance of its own tools, identify bottlenecks, and design and synthesize entirely new, superior tools to improve its own capabilities.
4.  **Strategic Reflection & Meta-Learning:** The system can analyze its own critique history to identify strategic weaknesses and then plan and execute a multi-step process to design and integrate new agents to overcome those weaknesses.

## Architecture

The system is composed of the following components:

*   **`prometheus` library:** A modular Python package containing all the core agent and tool classes.
*   **`Prometheus_v0.17.ipynb`:** A Jupyter Notebook that serves as the primary interface for demonstrating the system's capabilities. It includes a series of self-contained test cells and a final, powerful demonstration of the internal economy in action.
*   **`ResourceManager`:** A new agent that manages the global computational budget and tracks agent reputations.
*   **`PlannerAgent`:** Can now estimate the cost of its plans and generate "bids" for resources.
*   **`MCSSupervisor`:** Acts as an "auctioneer," selecting the most promising bid based on a combination of cost and the past performance of the agents involved.

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

The entire PoC is now consolidated into a single, executable Jupyter Notebook: `Prometheus_v0.17.ipynb`.

1.  Open the `Prometheus_v0.17.ipynb` notebook in Google Colab.
2.  Ensure you have selected a **GPU runtime** (`Runtime -> Change runtime type -> T4 GPU`).
3.  Add your Google API key to the designated cell.
4.  Run the cells sequentially to execute the verification tests and the final, powerful demonstration of the internal economy.