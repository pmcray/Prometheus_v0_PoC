import logging
from typing import List
from src.critique import CausalCritique

class MemoryAgent:
    def __init__(self):
        self.critique_history: List[CausalCritique] = []
        logging.info("MemoryAgent initialized.")

    def add_critique(self, critique: CausalCritique):
        """Adds a critique to the history."""
        self.critique_history.append(critique)
        logging.info(f"MemoryAgent: Added critique to history. Total critiques: {len(self.critique_history)}")

    def get_historical_context(self, limit: int = 2) -> List[dict]:
        """
        Retrieves the most recent critiques to serve as historical context.
        """
        if not self.critique_history:
            return []

        # Get the most recent critiques
        recent_critiques = self.critique_history[-limit:]

        # Format them as specified in the work plan
        # We need a unique run_id, but for this mock, index is not sufficient as it resets.
        # Let's use the object id for a mock unique id.
        formatted_context = [
            {
                "run_id": f"run_{id(c)}",
                "critique_summary": c.reason
            }
            for c in recent_critiques
        ]
        logging.info(f"MemoryAgent: Retrieved {len(formatted_context)} critiques for historical context.")
        return formatted_context
