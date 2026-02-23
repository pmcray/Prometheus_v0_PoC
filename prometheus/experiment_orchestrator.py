
import logging
from concurrent.futures import ProcessPoolExecutor
from .toy_chemistry_sim import ToyChemistrySim

class ExperimentOrchestrator:
    def __init__(self, n_workers=4):
        self.n_workers = n_workers
        logging.info(f"ExperimentOrchestrator initialized with {n_workers} workers.")

    def run_parallel_experiments(self, hypotheses: list):
        """
        Runs a list of experiments in parallel.
        """
        logging.info(f"Running {len(hypotheses)} experiments in parallel.")
        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            results = list(executor.map(self._run_single_experiment, hypotheses))
        return results

    def _run_single_experiment(self, hypothesis: str):
        """
        Runs a single experiment in a separate process.
        """
        sim = ToyChemistrySim()
        
        # A simple parser to translate the hypothesis into a sequence of operations.
        operations = hypothesis.lower().replace(",", "").split(" then ")
        for op in operations:
            if "mix" in op:
                parts = op.split()
                sim.mix(parts[1].upper(), parts[2].upper())
            elif "heat" in op:
                sim.heat(50)
                
        return {"hypothesis": hypothesis, "result": sim.get_state()}
