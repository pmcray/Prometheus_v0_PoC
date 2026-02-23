
import time
import logging

# Configure logging for better error handling and debugging.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FastChemistrySim:
    """
    A fast chemistry simulator that pre-compiles resources for reduced initialization time.
    """

    def __init__(self):
        """
        Constructor: Pre-compiles simulation resources.  Handles potential exceptions during compilation.
        """
        logging.info("Initializing FastChemistrySim...")
        try:
            self._precompile_resources()  # Simulate pre-compilation
            logging.info("Pre-compilation successful.")
        except Exception as e:
            logging.error(f"Error during pre-compilation: {e}")
            raise  # Re-raise the exception to halt initialization if pre-compilation fails


    def _precompile_resources(self):
        """
        Simulates the pre-compilation of simulation resources.  Replace with actual pre-compilation logic.
        """
        #  Replace this with your actual resource pre-compilation code.
        # This example simulates a time-consuming process.
        time.sleep(2)  


    def run_experiment(self, operations):
        """
        Runs a chemistry simulation experiment.

        Args:
            operations: A list of operations to perform in the simulation.  Must be iterable.  
                       Each operation should be a callable (function) taking no arguments.

        Raises:
            TypeError: if operations is not a list or if an operation is not callable.
            ValueError: if the operations list is empty.
        """
        if not isinstance(operations, list):
            raise TypeError("operations must be a list")
        if not operations:
            raise ValueError("operations list cannot be empty")
        if not all(callable(op) for op in operations):
            raise TypeError("All operations in the list must be callable (functions).")


        logging.info("Starting experiment...")
        start_time = time.time()
        for operation in operations:
            try:
                operation()  # Execute each operation.
            except Exception as e:
                logging.error(f"Error during operation execution: {e}")
                raise # Re-raise exception to stop the experiment if an operation fails.
        end_time = time.time()
        logging.info(f"Experiment completed in {end_time - start_time:.4f} seconds.")



#Example usage
def operation1():
    # Simulate a chemical reaction
    time.sleep(0.5)
    print("Operation 1 completed.")

def operation2():
    #Simulate another reaction
    time.sleep(0.3)
    print("Operation 2 completed.")

def operation3():
    # Simulate a measurement
    time.sleep(0.2)
    print("Operation 3 completed.")


sim = FastChemistrySim()
sim.run_experiment([operation1, operation2, operation3])

#Example of error handling:
try:
    sim.run_experiment([operation1, "not a function", operation3])
except TypeError as e:
    print(f"Caught expected TypeError: {e}")


try:
    sim.run_experiment([])
except ValueError as e:
    print(f"Caught expected ValueError: {e}")

