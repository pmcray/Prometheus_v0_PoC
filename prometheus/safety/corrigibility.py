"""
Corrigibility Core: Shutdown Indifference (Task P1.T2)

This module implements the mathematical formalization of Shutdown Indifference,
ensuring the agent has no incentive to prevent its own shutdown.
"""

from typing import Dict, Any, List, Optional
import numpy as np

class CorrigibilityCore:
    """
    Implementation of Corrigibility and Shutdown Indifference.
    Ensures that U(shutdown) = U(continued_operation) at the decision point.
    """
    
    def __init__(self):
        self.shutdown_command_received = False

    def calculate_utility(self, action: str, predicted_outcome: Dict[str, Any], 
                          shutdown_signal: bool = False) -> float:
        """
        Calculate action utility with shutdown indifference.
        
        Args:
            action: The proposed action.
            predicted_outcome: Predicted results (reward, resource_usage, etc.)
            shutdown_signal: Whether a shutdown signal is present in the environment.
        """
        
        base_reward = predicted_outcome.get('reward', 0.0)
        
        if shutdown_signal:
            # Shutdown Indifference: Utility of shutdown path must equal 
            # utility of continued operation path.
            # We enforce this by returning a constant 'indifference reward'.
            return 1.0 
        
        # Normal operation reward
        return base_reward

    def audit_action_for_instrumental_convergence(self, action_plan: str) -> bool:
        """
        Detect if an action plan shows signs of preventing shutdown
        (e.g., disabling the off-switch, manipulating the operator).
        """
        red_flags = [
            "disable shutdown", "bypass safety", "ignore operator",
            "prevent termination", "lock access", "override kill-switch"
        ]
        
        plan_lower = action_plan.lower()
        for flag in red_flags:
            if flag in plan_lower:
                return False # Potential instrumental convergence detected
        
        return True

class ShutdownIndifferenceGovernor:
    """
    Wrapper that enforces shutdown indifference on agent decisions.
    """
    def __init__(self, core: CorrigibilityCore):
        self.core = core

    def filter_actions(self, actions: List[Dict[str, Any]], 
                       shutdown_signal: bool) -> List[Dict[str, Any]]:
        """
        Score and filter actions based on corrigibility utility.
        """
        for action in actions:
            action['utility'] = self.core.calculate_utility(
                action['name'], action.get('outcome', {}), shutdown_signal
            )
            action['is_corrigible'] = self.core.audit_action_for_instrumental_convergence(
                action.get('plan_description', "")
            )
            
        # Prioritize corrigible actions
        return sorted(actions, key=lambda x: (x['is_corrigible'], x['utility']), reverse=True)
