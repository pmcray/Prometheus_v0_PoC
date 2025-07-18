# Project Prometheus v0 PoC

This repository contains the Proof of Concept for Project Prometheus, a system designed to explore the principles of safe, autonomous, and self-improving AI. This PoC demonstrates a multi-agent framework that can perform code refactoring, tackle formal mathematical reasoning, and conduct autonomous experiments. The latest version (v0.9) introduces a dynamic agent mesh, GPU acceleration, and a unified Colab notebook for demonstration.

## Core Principles

The PoC is built around four core principles from I.J. Good's paper:

1.  **Multi-Agent Collaboration (Causal Agentic Mesh):** A decentralized mesh of specialized agents work together. This is now demonstrated through **Dynamic Subassembly**, where the system can form and dissolve temporary "expert circuits" to solve specific sub-problems.
2.  **Recursive Self-Improvement:** The system uses a CRLS loop, an adaptive curriculum, and strategic reflection to learn and improve.
3.  **Ultraparallelism:** The system can entertain and test multiple, competing hypotheses in parallel, a key to rapid discovery.
4.  **Internal Governance for Safety:** The MCS acts as an internal alignment governor, using a constitution and resource budgets to ensure safety and efficiency.

## Architecture

The system is composed of the following components:

*   **PlannerAgent:** A high-level strategic agent that can form "expert circuits" of other agents, generate multiple competing hypotheses, and guide the overall reasoning process.
*   **Agent Templates:** A set of blueprint agents (e.g., `HypothesisGenerator`, `DataAnalyzer`, `CodeImplementer`) that can be dynamically instantiated by the `MCSSupervisor` as part of an expert circuit.
*   **CoderAgent:** Translates natural-language plans into executable code or formal proofs.
*   **EvaluatorAgent:** Evaluates the results of experiments, now with the ability to perform comparative analysis across multiple parallel runs.
*   **MCSSupervisor:** Orchestrates the main work loops, including the dynamic formation and dissolution of agent circuits and the execution of parallel experiments.
*   **Tools & Archives:** A suite of tools and archives that provide the agents with capabilities and memory.

## Setup and Installation

### Prerequisites

*   Python 3.8+
*   Docker (with NVIDIA container toolkit for GPU support)
*   A Google API Key with the Gemini API enabled.
*   The Lean 4 proof assistant & Pandoc.

### Local Setup (with GPU on Jetson Orin Nano)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/pmcray/Prometheus_v0_PoC.git
    cd Prometheus_v0_PoC
    ```
2.  **Build the Docker image:**
    ```bash
    docker build -t prometheus_v0.9 .
    ```
3.  **Run the Docker container:**
    ```bash
    docker run --rm -it --gpus all \
      -e GOOGLE_API_KEY="YOUR_API_KEY" \
      prometheus_v0.9
    ```

## Running the PoC in Google Colab

The entire PoC is now consolidated into a single, executable Jupyter Notebook: `Prometheus_v0.9.ipynb`.

1.  Open the `Prometheus_v0.9.ipynb` notebook in Google Colab.
2.  Ensure you have selected a **GPU runtime** (`Runtime -> Change runtime type -> T4 GPU`).
3.  Add your Google API key to the designated cell.
4.  Run the cells sequentially to execute the full demonstration of the Dynamic Mesh.