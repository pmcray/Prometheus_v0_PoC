
import time
import resource  # For resource usage monitoring (optional)

class FastToyChemistrySim:
    """
    FastToyChemistrySim: A tool for chemical simulations minimizing initialization overhead.

    Pre-loads necessary resources to ensure consistent execution times.  Includes optional 
    resource usage monitoring.
    """

    def __init__(self):
        """Constructor. Pre-loads resources (replace with your actual resource loading)."""
        print("FastToyChemistrySim initializing...")
        self.preloaded_resources = self._load_resources()  #Simulate resource loading
        print("FastToyChemistrySim initialization complete.")


    def _load_resources(self):
        """Simulates loading resources - replace with your actual resource loading logic."""
        #Example:  Loading large datasets, initializing libraries etc.
        #This could involve file I/O, database connections, etc.
        time.sleep(1) # Simulate loading time
        return {"data": "Simulated data", "constants": {"avogadro": 6.022e23}}


    def run_experiment(self, operations):
        """
        Runs a series of chemical simulation operations.

        Args:
            operations: A list of functions representing the simulation operations.
                        Each function should take self.preloaded_resources as input and return a result.

        Returns:
            A list of results from each operation.  Raises exceptions if operations are invalid.

        Raises:
            TypeError: If operations is not a list.
            TypeError: If any element in operations is not callable.
        """

        if not isinstance(operations, list):
            raise TypeError("operations must be a list of callable functions.")
        for op in operations:
            if not callable(op):
                raise TypeError("All elements in operations must be callable functions.")


        results = []
        start_time = time.time()
        for operation in operations:
            #Optional resource usage monitoring:
            ru_before = resource.getrusage(resource.RUSAGE_SELF)

            result = operation(self.preloaded_resources)
            results.append(result)

            ru_after = resource.getrusage(resource.RUSAGE_SELF)
            print(f"Operation completed.  Resource usage: {ru_after.ru_utime - ru_before.ru_utime:.2f}s user, {ru_after.ru_stime - ru_before.ru_stime:.2f}s system") #Example output

        end_time = time.time()
        total_time = end_time - start_time
        print(f"Experiment completed in {total_time:.2f} seconds.")
        return results


# Example usage:
def operation1(resources):
    #Simulate some computation using pre-loaded resources
    time.sleep(0.5)
    return f"Result from operation 1 using {resources['data']}"

def operation2(resources):
    #Simulate some computation using pre-loaded resources
    time.sleep(0.2)
    return f"Result from operation 2 using Avogadro's number: {resources['constants']['avogadro']}"


sim = FastToyChemistrySim()
operations = [operation1, operation2, operation1]
results = sim.run_experiment(operations)
print(results)

#Example of error handling:
try:
    bad_operations = [operation1, "not a function", operation2]
    sim.run_experiment(bad_operations)
except TypeError as e:
    print(f"Caught expected TypeError: {e}")

