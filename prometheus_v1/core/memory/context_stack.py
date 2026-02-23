
import json
import os
from typing import List, Optional
from datetime import datetime
from prometheus_v1.core.data_models import ContextFrame

class ContextStack:
    """
    Implements a recursive context stack for managing agent reasoning state.
    Inspired by Douglas Hofstadter's "pushed" and "popped" contexts.
    """
    def __init__(self, persistence_path: str = "state_history.json"):
        self.stack: List[ContextFrame] = []
        self.persistence_path = persistence_path
        self._ensure_persistence_dir()

    def _ensure_persistence_dir(self):
        directory = os.path.dirname(self.persistence_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

    def push(self, frame: ContextFrame):
        """Push a new context onto the stack with recursion check."""
        if self._epimenides_check(frame):
            raise RecursionError(f"Strange Loop detected! Semantic isomorphism with existing goal: {frame.goal}")
        
        self.stack.append(frame)
        self._persist()
        print(f"ContextStack: Pushed goal '{frame.goal}' (Depth: {len(self.stack)})")

    def pop(self) -> Optional[ContextFrame]:
        """Pop the current context and return it."""
        if not self.stack:
            return None
        frame = self.stack.pop()
        self._persist()
        print(f"ContextStack: Popped goal '{frame.goal}' (Depth: {len(self.stack)})")
        return frame

    def peek(self) -> Optional[ContextFrame]:
        """Return the current top of the stack without removing it."""
        return self.stack[-1] if self.stack else None

    def _epimenides_check(self, new_frame: ContextFrame) -> bool:
        """
        Recursion Guard (Epimenides Check).
        Prevents infinite regress by checking for semantically isomorphic goals.
        For Phase 1, we use simple string normalization and inclusion check.
        """
        new_goal_norm = new_frame.goal.lower().strip()
        for frame in self.stack:
            existing_goal_norm = frame.goal.lower().strip()
            # Simple check: is the new goal a substring or exact match of an existing one?
            if new_goal_norm in existing_goal_norm or existing_goal_norm in new_goal_norm:
                return True
        return False

    def _persist(self):
        """Save the current stack state to disk for visualization and debugging."""
        try:
            with open(self.persistence_path, "w") as f:
                json_data = [frame.model_dump(mode='json') for frame in self.stack]
                json.dump(json_data, f, indent=2)
        except Exception as e:
            print(f"ContextStack: Error persisting state: {e}")

    def get_depth(self) -> int:
        return len(self.stack)
