# Workplan 4: Integrate More Games into PrometheusStar

## Goal

To further demonstrate the generality of the PrometheusStar curriculum learning approach by integrating a new Real-Time Strategy (RTS) game, OpenRA.

## Phase 1: Research and Design (1-2 weeks)

*   **Task 1.1: Research OpenRA Integration:** Investigate how to programmatically interact with OpenRA. Look for existing APIs, scripting interfaces (e.g., Lua), or memory-reading techniques that would allow a Python-based agent to observe the game state and issue commands.
*   **Task 1.2: Design the OpenRA Benchmark:** Design a new benchmark file, `benchmarks/openra_benchmark.py`, that defines a curriculum of opponents with increasing difficulty. This might involve scripting different AI behaviors in OpenRA itself.

## Phase 2: Implementation (3-4 weeks)

*   **Task 2.1: Implement the OpenRA Environment:** Create a new file, `prometheus/openra_environment.py`, that provides a Python interface to the OpenRA game, allowing the agent to get observations and send actions.
*   **Task 2.2: Implement the OpenRA Benchmark:** Implement the curriculum of opponents in `benchmarks/openra_benchmark.py` as designed in Phase 1.
*   **Task 2.3: Adapt the PrometheusStar Agent:** Create a new agent, `prometheus/openra_agent.py`, that can play OpenRA. This will likely involve adapting the existing `MicroRTSStrategyAgent` to the specific units, resources, and strategies of OpenRA.

## Phase 3: Evaluation and Integration (2-3 weeks)

*   **Task 3.1: Run the OpenRA Curriculum:** Run the full curriculum training for OpenRA, collecting data on win rates and strategy evolution.
*   **Task 3.2: Analyze the Results:** Analyze the results to determine if the system can successfully learn to play OpenRA and to compare its learning curve to the other integrated games.
*   **Task 3.3: Document the New Integration:** Update the `PROMETHEUSSTAR_README.md` to include instructions for setting up and running the OpenRA benchmark.

## Deliverables

*   `prometheus/openra_environment.py`: The OpenRA game interface.
*   `benchmarks/openra_benchmark.py`: The OpenRA benchmark and curriculum.
*   `prometheus/openra_agent.py`: The OpenRA agent.
*   A Jupyter notebook demonstrating the OpenRA training process.
*   Updated documentation.
