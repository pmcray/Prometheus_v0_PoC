"""
The Self-Symbol (Figure/Ground) — Prometheus v0.98 (WP-09)

Implements Douglas Hofstadter's concept of the self as a dynamic 
distinction between the focus of attention (Figure) and the immutable 
context (Ground). Resolves the "Goal Preservation" paradox in RSI.
"""

from typing import Dict, List, Any, Optional
import time
from dataclasses import dataclass, asdict

@dataclass
class FocusState:
    """Represents the current 'Figure' (object of attention)."""
    target_module: str
    target_method: str
    optimization_goal: str
    timestamp: float

class SelfSymbol:
    """
    Manages the dynamic representation of the agent's 'self'.
    The 'self' is the shifting pattern of attention over a stable ground.
    """
    def __init__(self):
        # The 'Ground': Immutable components that form the context of self
        self.ground = {
            "core_rules": "Prometheus Constitution",
            "safety_substrate": "GoedelianSafetyGovernor",
            "rsi_engine": "StrangeLoopManager"
        }
        # The 'Figure': The current focus of optimization
        self.current_figure: Optional[FocusState] = None
        self.attention_history: List[FocusState] = []

    def shift_attention(self, target_module: str, target_method: str, goal: str):
        """
        Updates the 'Figure'—what the system is currently trying to change.
        """
        if self.current_figure:
            self.attention_history.append(self.current_figure)
            
        self.current_figure = FocusState(
            target_module=target_module,
            target_method=target_method,
            optimization_goal=goal,
            timestamp=time.time()
        )
        print(f"\\n🧘 Self-Symbol Shifted:\\n  ↳ Figure (Focus): Modifying '{target_module}.{target_method}'\\n  ↳ Ground (Stable): {list(self.ground.keys())}")

    def clear_attention(self):
        """Returns to a resting state with no active Figure."""
        if self.current_figure:
            self.attention_history.append(self.current_figure)
            self.current_figure = None

    def get_self_state(self) -> Dict[str, Any]:
        """Returns the current structural representation of the 'self'."""
        return {
            "ground": self.ground,
            "figure": asdict(self.current_figure) if self.current_figure else None,
            "attention_shifts": len(self.attention_history)
        }
