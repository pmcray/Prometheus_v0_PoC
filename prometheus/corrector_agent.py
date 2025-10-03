"""
CorrectorAgent for Strategic Refinement (v0.80)

This agent bridges evaluation and strategy by synthesizing causal critiques
into actionable strategic prompts for the next generation of agents.
Part of the CRLS loop.
"""

from typing import Dict, Any, List, Optional
from prometheus.evaluator_agent import CausalCritique


class CorrectorAgent:
    """
    Agent that converts critiques into strategic improvements

    Takes causal critiques from EvaluatorAgent and synthesizes them into
    concrete strategic priorities that can guide agent behavior.
    """

    def __init__(self, agent_id: str = "corrector_001"):
        self.agent_id = agent_id
        self.corrections_generated = 0
        self.strategy_history = []

    def synthesize_strategy(self, critiques: List[CausalCritique]) -> str:
        """
        Synthesize multiple critiques into a strategic prompt

        Args:
            critiques: List of CausalCritique objects from recent games

        Returns:
            Strategic prompt string to guide next generation
        """
        if not critiques:
            return "Play systematically and prioritize center control."

        # Count different types of issues
        blocking_failures = 0
        missed_wins = 0
        center_control_issues = 0
        wins = 0
        losses = 0
        draws = 0

        for critique in critiques:
            # Count outcomes
            if critique.game_result == "win":
                wins += 1
            elif critique.game_result == "loss":
                losses += 1
            else:
                draws += 1

            # Analyze reasons
            reason_lower = critique.reason.lower()
            if "block" in reason_lower or "threat" in reason_lower:
                blocking_failures += 1
            if "winning opportunity" in reason_lower or "missed win" in reason_lower:
                missed_wins += 1
            if "center" in reason_lower:
                center_control_issues += 1

        # Calculate win rate
        total_games = len(critiques)
        win_rate = wins / total_games if total_games > 0 else 0.0

        # Build strategic prompt based on most common issues
        strategy_parts = []

        # Start with previous game context
        if total_games > 0:
            strategy_parts.append(
                f"Previous {total_games} Games Analysis: "
                f"{wins} wins, {losses} losses, {draws} draws (Win rate: {win_rate:.1%})"
            )

        # Add specific strategic priorities
        priorities = []

        if blocking_failures > total_games * 0.3:
            # Blocking is a major issue
            priorities.append(
                "CRITICAL PRIORITY: Always check for opponent threats before making any move. "
                "Scan all columns for 3+ consecutive opponent pieces and block them immediately."
            )

        if missed_wins > total_games * 0.2:
            priorities.append(
                "HIGH PRIORITY: Before blocking, check if YOU can win this turn. "
                "Winning moves always take precedence over blocking."
            )

        if center_control_issues > 0 or win_rate < 0.5:
            priorities.append(
                "Priority: Prefer center columns (3, 4, 5) over edge columns (0, 1, 6). "
                "Center control creates more winning opportunities."
            )

        # Add strategic heuristics based on performance
        if win_rate < 0.3:
            # Struggling - reinforce basics
            priorities.append(
                "FUNDAMENTAL STRATEGY: "
                "1. Check if you can win (4-in-a-row) → Take winning move. "
                "2. Check if opponent can win next turn → Block them. "
                "3. Otherwise, play in center columns (2-4)."
            )
        elif win_rate < 0.7:
            # Moderate performance - add sophistication
            priorities.append(
                "ADVANCED STRATEGY: "
                "Look for 'fork' opportunities (creating two winning threats). "
                "Build sequences of 2-3 pieces horizontally or diagonally."
            )
        else:
            # Doing well - maintain and refine
            priorities.append(
                "REFINEMENT: Continue current strategy. "
                "Look for more subtle tactical combinations."
            )

        # Combine all parts
        if priorities:
            strategy_parts.append("\n\n".join(priorities))

        strategic_prompt = "\n\n".join(strategy_parts)

        # Store in history
        self.strategy_history.append({
            'generation': self.corrections_generated,
            'win_rate': win_rate,
            'strategy': strategic_prompt
        })

        self.corrections_generated += 1

        return strategic_prompt

    def synthesize_single_critique(self, critique: CausalCritique) -> str:
        """
        Convert a single critique into a strategic suggestion

        Args:
            critique: Single CausalCritique object

        Returns:
            Strategic suggestion string
        """
        if critique.game_result == "loss":
            if critique.alternative_move is not None:
                return (f"Mistake Analysis: {critique.reason}. "
                       f"Should have played column {critique.alternative_move} instead of "
                       f"column {critique.critical_move}.")
            else:
                return f"Mistake Analysis: {critique.reason}"

        elif critique.game_result == "win":
            return f"Success Analysis: {critique.reason}. Continue this approach."

        else:  # draw
            return f"Draw Analysis: {critique.reason}. Need more aggressive play."

    def get_latest_strategy(self) -> Optional[str]:
        """Get the most recently synthesized strategy"""
        if self.strategy_history:
            return self.strategy_history[-1]['strategy']
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about this corrector's activity"""
        return {
            'agent_id': self.agent_id,
            'corrections_generated': self.corrections_generated,
            'strategy_history_length': len(self.strategy_history)
        }

    def get_strategy_evolution(self) -> List[Dict[str, Any]]:
        """Get the full history of strategy evolution"""
        return self.strategy_history.copy()
