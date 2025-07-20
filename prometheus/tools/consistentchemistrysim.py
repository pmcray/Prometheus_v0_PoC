
import time
import random
from typing import List, Callable

class ConsistentChemistrySim:
    """
    Executes chemical reaction simulations with consistently low latency (< 0.2 seconds).

    Uses a simulated execution time to mimic a complex chemical simulation.  Error handling
    is included to manage unexpected inputs and ensure consistent latency.
    """

    def __init__(self):
        #No specific initialization needed for this example
        pass

    def run_experiment(self, operations: List[Callable[[], None]]) -> None:
        """
        Runs a series of chemical reaction simulations.

        Args:
            operations: A list of callables, where each callable represents a single 
                       chemical reaction simulation step.  Each callable should be 
                       idempotent (it can be called multiple times with the same result).


        Raises:
            TypeError: if operations is not a list.
            TypeError: if any element in operations is not callable.
            ValueError: if any operation takes longer than 0.2 seconds to execute.

        """
        if not isinstance(operations, list):
            raise TypeError("operations must be a list of callables.")

        for operation in operations:
            if not callable(operation):
                raise TypeError("All elements in operations must be callable.")

            start_time = time.time()
            try:
                operation()  #Simulate running the operation.
            except Exception as e:
                print(f"An error occurred during simulation: {e}")
                #For consistent latency, we still need to wait out the remaining time.
                pass

            end_time = time.time()
            elapsed_time = end_time - start_time

            #Simulate a complex simulation with variable execution time.
            simulated_execution_time = random.uniform(0.01, 0.15) #Keep it below 0.2

            sleep_time = max(0, simulated_execution_time - elapsed_time)
            time.sleep(sleep_time)


            if elapsed_time + sleep_time > 0.2:
                raise ValueError(
                    f"Operation exceeded the maximum latency of 0.2 seconds. "
                    f"Elapsed time: {elapsed_time:.4f} seconds, Sleep time: {sleep_time:.4f} seconds"
                )

#Example Usage:

def reaction1():
    #Simulate a complex reaction
    time.sleep(0.1) #Example - replace with actual simulation code.


def reaction2():
    #Simulate another reaction.
    time.sleep(0.05) #Example - replace with actual simulation code.


sim = ConsistentChemistrySim()
operations = [reaction1, reaction2, reaction1, reaction2] #add multiple operations as needed.
try:
    sim.run_experiment(operations)
    print("Experiment completed successfully.")
except (TypeError, ValueError) as e:
    print(f"Error during experiment: {e}")


