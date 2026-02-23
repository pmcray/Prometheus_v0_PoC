
import logging

class ToyChemistrySim:
    def __init__(self):
        self.state = {"A": 100, "B": 100, "C": 0}
        logging.info(f"ToyChemistrySim initialized with state: {self.state}")

    def mix(self, chem1, chem2):
        """
        Mixes two chemicals.
        """
        if chem1 in self.state and chem2 in self.state:
            # Simple reaction: A + B -> C
            if (chem1 == "A" and chem2 == "B") or (chem1 == "B" and chem2 == "A"):
                reaction_amount = min(self.state["A"], self.state["B"])
                self.state["A"] -= reaction_amount
                self.state["B"] -= reaction_amount
                self.state["C"] += reaction_amount
                logging.info(f"Mixed {chem1} and {chem2}. New state: {self.state}")
                return self.state
        logging.warning(f"Invalid chemicals for mixing: {chem1}, {chem2}")
        return self.state

    def heat(self, amount):
        """
        Heats the mixture.
        """
        # Heating doubles the amount of C, if A and B are depleted
        if self.state["A"] == 0 and self.state["B"] == 0:
            self.state["C"] *= (1 + amount / 100.0)
            logging.info(f"Heated by {amount}. New state: {self.state}")
        return self.state

    def get_state(self):
        return self.state
