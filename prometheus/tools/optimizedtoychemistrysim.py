
import time
import random

class OptimizedToyChemistrySim:
    """
    A toy chemistry simulator that pre-compiles resources for consistent execution times.
    """

    def __init__(self):
        """
        Pre-compiles simulation resources during initialization.  Handles potential exceptions during resource compilation.
        """
        self.resources = self._compile_resources()
        if self.resources is None:
            raise RuntimeError("Failed to compile simulation resources. Check resource availability and validity.")

    def _compile_resources(self):
        """
        Simulates compiling simulation resources.  Replace with actual resource compilation logic.
        Returns the compiled resources or None if compilation fails.
        """
        try:
            # Simulate resource-intensive compilation (replace with actual code)
            time.sleep(2)  # Simulate compilation time
            #Example resource data structure. Replace with your actual resources.
            return {"constants": {"avogadro": 6.022e23, "boltzmann": 1.38e-23}, "tables": [1,2,3]}
        except Exception as e:
            print(f"Error compiling resources: {e}")
            return None

    def run_experiment(self, operations):
        """
        Runs a chemistry simulation experiment.

        Args:
            operations: A list of operations to perform in the simulation.  Must be a list of strings.  
                       Invalid operations will raise exceptions with informative error messages.

        Returns:
            A dictionary containing the experiment results.  Returns None if an error occurs.

        Raises:
            TypeError: if operations is not a list.
            ValueError: if operations contains non-string elements, or if the operations are invalid.
        """
        if not isinstance(operations, list):
            raise TypeError("Operations must be a list.")
        if not all(isinstance(op, str) for op in operations):
            raise ValueError("All operations must be strings.")

        results = {}
        try:
            for op in operations:
                if op == "mix":
                    #Simulate mixing operation. Replace with actual simulation logic.
                    results[op] = self._simulate_mixing()
                elif op == "heat":
                    #Simulate heating operation. Replace with actual simulation logic.
                    results[op] = self._simulate_heating()
                elif op == "react":
                    #Simulate reaction operation. Replace with actual simulation logic.
                    results[op] = self._simulate_reaction()
                else:
                    raise ValueError(f"Invalid operation: {op}")
            return results
        except Exception as e:
            print(f"Error during experiment: {e}")
            return None



    def _simulate_mixing(self):
        # Replace with your actual mixing simulation logic.
        time.sleep(random.uniform(0.1, 0.5)) #Simulate variable execution time.
        return {"mixed": True}

    def _simulate_heating(self):
        # Replace with your actual heating simulation logic.
        time.sleep(random.uniform(0.2, 0.7)) #Simulate variable execution time.
        return {"temperature_increase": random.uniform(10, 50)}

    def _simulate_reaction(self):
        # Replace with your actual reaction simulation logic.
        time.sleep(random.uniform(0.3, 1.0)) #Simulate variable execution time.
        return {"products": ["product_A", "product_B"]}


# Example usage
sim = OptimizedToyChemistrySim()
operations = ["mix", "heat", "react"]
results = sim.run_experiment(operations)
print(f"Experiment results: {results}")

#Example of error handling
invalid_operations = ["mix", 123, "react"]
try:
    results = sim.run_experiment(invalid_operations)
    print(f"Experiment results: {results}")
except (TypeError, ValueError) as e:
    print(f"Caught expected error: {e}")

