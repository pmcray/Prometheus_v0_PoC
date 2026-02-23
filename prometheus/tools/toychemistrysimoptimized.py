
import time
import copy

class ToyChemistrySimOptimized:
    """
    A chemistry simulation tool that pre-compiles resources for faster execution.
    Handles invalid input gracefully and provides informative error messages.
    """

    def __init__(self):
        """
        Pre-compiles simulation resources during initialization.  
        This example simulates pre-compilation with a short sleep.  
        In a real application, this would involve loading large data files, 
        compiling code, or other resource-intensive tasks.
        """
        print("Pre-compiling simulation resources...")
        time.sleep(1)  # Simulate pre-compilation time
        self.resources_compiled = True
        self.default_parameters = {"temperature": 298, "pressure": 1.0}
        self.simulation_history = []


    def run_experiment(self, operations):
        """
        Runs a chemistry simulation with a given list of operations.

        Args:
            operations: A list of dictionaries, where each dictionary represents an operation 
                       and must contain at least a 'type' key specifying the operation type.
                       Additional keys might be required based on operation type.  Improperly 
                       formatted input will raise a ValueError.


        Returns:
            A list of results from each operation in the experiment.  Returns an empty list
            if the input operations list is empty or contains invalid operations.
        """

        if not self.resources_compiled:
            raise RuntimeError("Simulation resources have not been compiled.  Please re-initialize.")

        if not isinstance(operations, list):
            raise ValueError("Invalid input: 'operations' must be a list.")

        if not operations:  #Handle empty list
            print("Warning: Empty operations list provided.  Returning empty results.")
            return []

        results = []
        for op in operations:
            if not isinstance(op, dict) or 'type' not in op:
                raise ValueError(f"Invalid operation: {op}. Each operation must be a dictionary with a 'type' key.")

            op_type = op['type']
            try:
                if op_type == "heat":
                    temp_change = op.get("temp_change", 10) #Provide a default temp change if missing
                    if not isinstance(temp_change, (int, float)):
                        raise ValueError("Invalid 'temp_change' value. Must be a number.")

                    new_temp = self.default_parameters["temperature"] + temp_change
                    self.default_parameters["temperature"] = new_temp
                    results.append({"operation": "heat", "new_temperature": new_temp})

                elif op_type == "add_reactant":
                    reactant = op.get("reactant", None)
                    if reactant is None:
                        raise ValueError("'add_reactant' operation requires a 'reactant' key.")
                    results.append({"operation": "add_reactant", "reactant": reactant})

                # Add more operation types here as needed.

                else:
                    raise ValueError(f"Unknown operation type: {op_type}")

            except ValueError as e:
                print(f"Error processing operation {op}: {e}")
                #Optionally: Choose to continue or stop on error. Here we continue
                continue

        self.simulation_history.append({"operations": copy.deepcopy(operations), "results": copy.deepcopy(results)})
        return results



#Example usage
sim = ToyChemistrySimOptimized()
ops = [{"type": "heat", "temp_change": 20}, {"type": "add_reactant", "reactant": "H2O"}]
results = sim.run_experiment(ops)
print(f"Experiment results: {results}")
print(f"Simulation history: {sim.simulation_history}")

# Example of invalid input handling
invalid_ops = [{"type": "heat"}, {"type": "invalid_op"}]
try:
    sim.run_experiment(invalid_ops)
except ValueError as e:
    print(f"Caught expected error: {e}")

invalid_ops2 = [1,2,3]
try:
    sim.run_experiment(invalid_ops2)
except ValueError as e:
    print(f"Caught expected error: {e}")
