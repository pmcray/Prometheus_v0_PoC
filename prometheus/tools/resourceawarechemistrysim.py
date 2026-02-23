
import os
import hashlib
import pickle
from typing import List, Dict, Callable

class ResourceAwareChemistrySim:
    """
    A chemistry simulation tool that dynamically manages resources and implements a robust 
    caching strategy to ensure consistent and predictable performance.
    """

    def __init__(self):
        """Initializes the ResourceAwareChemistrySim with a cache directory."""
        self.cache_dir = "simulation_cache"  #Default cache directory
        os.makedirs(self.cache_dir, exist_ok=True) #Create cache directory if it doesn't exist.


    def _generate_cache_key(self, operations: List[Callable]) -> str:
        """Generates a unique cache key based on the input operations."""
        #Robust hashing to handle various operation types.
        op_strings = [repr(op) for op in operations] 
        combined_string = "".join(op_strings)
        return hashlib.sha256(combined_string.encode()).hexdigest()


    def _load_from_cache(self, cache_key: str) -> Dict:
        """Loads simulation results from the cache."""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pickle")
        try:
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        except (FileNotFoundError, EOFError, pickle.UnpicklingError): #Handle various file errors
            return None


    def _save_to_cache(self, cache_key: str, results: Dict):
        """Saves simulation results to the cache."""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pickle")
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(results, f)
        except (IOError, OSError) as e:
            print(f"Warning: Could not save to cache: {e}")



    def run_simulation(self, operations: List[Callable]) -> Dict:
        """
        Runs a chemistry simulation with the given operations. Uses caching for efficiency.

        Args:
            operations: A list of functions representing the simulation steps.  Each function should 
                       take a dictionary as input (representing the simulation state) and return 
                       an updated dictionary.  It's crucial these functions are pure functions for 
                       caching to work reliably.

        Returns:
            A dictionary containing the simulation results. Returns None if there's an error during simulation.

        Raises:
            TypeError: if operations is not a list or contains non-callable elements.
        """

        if not isinstance(operations, list):
            raise TypeError("Operations must be a list of callable functions.")
        if not all(callable(op) for op in operations):
            raise TypeError("All elements in operations must be callable functions.")

        cache_key = self._generate_cache_key(operations)
        cached_results = self._load_from_cache(cache_key)

        if cached_results:
            print("Loading results from cache...")
            return cached_results

        print("Running simulation...")
        simulation_state = {} #Initial simulation state
        try:
            for op in operations:
                simulation_state = op(simulation_state) #Update state with each operation

            self._save_to_cache(cache_key, simulation_state)
            return simulation_state
        except Exception as e:
            print(f"Simulation error: {e}")
            return None



# Example usage:

def op1(state):
    state['a'] = 1
    return state

def op2(state):
    state['b'] = state.get('a',0) * 2
    return state

sim = ResourceAwareChemistrySim()
results = sim.run_simulation([op1, op2])
print(f"Simulation results: {results}") # Output will vary based on implementation


results2 = sim.run_simulation([op1,op2]) #This should load from cache.
print(f"Simulation results (from cache): {results2}")


