
from .toy_chemistry_sim import ToyChemistrySim
import logging

def run_tool_benchmark(sim: ToyChemistrySim, n_steps=500):
    """
    Runs a benchmark that is deliberately inefficient with the current toolset.
    """
    logging.info(f"--- Running Tool Benchmark (Inefficient) ---")
    for i in range(n_steps):
        sim.mix("A", "B")
    logging.info(f"--- Tool Benchmark Finished ---")
    return sim.get_state()
