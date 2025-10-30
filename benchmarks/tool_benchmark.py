
"""
A challenging benchmark for the ToyChemistrySim tool.
This benchmark is designed to be solvable but highly inefficient
with the base tool, requiring many steps.
"""

def get_inefficient_benchmark():
    """
    Returns a list of operations that are inefficient to perform
    with the base ToyChemistrySim.
    """
    operations = []
    for i in range(100):
        operations.append(("mix", ("reagent_a", "reagent_b")))
        operations.append(("heat", ("reagent_a", 50)))
    return operations
