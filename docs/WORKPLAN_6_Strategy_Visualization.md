# Workplan 6: Build a Strategy Visualization Tool

## Goal

To create a tool that helps researchers understand and interpret the strategies learned by the PrometheusStar agents, making the AI's decision-making process more transparent.

## Phase 1: Research and Design (1 week)

*   **Task 1.1: Choose a Visualization Library:** Select a suitable Python library for creating interactive web-based visualizations. Streamlit is a good candidate due to its simplicity and ease of use.
*   **Task 1.2: Design the Dashboard:** Design the layout and features of the visualization dashboard. It should include:
    *   A plot of win rates over generations.
    *   A parallel coordinates plot to visualize the evolution of strategy parameters (e.g., aggression, economy focus).
    *   A way to select and view the details of a specific agent or generation.
    *   (Optional) A simple 2D visualization of the agent's behavior in a game, if feasible.

## Phase 2: Implementation (2-3 weeks)

*   **Task 2.1: Implement the Dashboard:** Create a new file, `prometheus_dashboard.py`, that implements the visualization dashboard using the chosen library.
*   **Task 2.2: Integrate with PrometheusStar Data:** Write code to read the data from the `StrategyArchive`, performance logs, and other relevant files, and format it for display in the dashboard.

## Phase 3: Evaluation and Integration (1 week)

*   **Task 3.1: Test the Dashboard:** Test the dashboard with data from the MicroRTS and FreeCiv benchmarks to ensure it is working correctly and providing useful insights.
*   **Task 3.2: Document the Tool:** Add a section to the `PROMETHEUSSTAR_README.md` explaining how to launch and use the dashboard.

## Deliverables

*   `prometheus_dashboard.py`: The new strategy visualization tool.
*   Updated documentation.
