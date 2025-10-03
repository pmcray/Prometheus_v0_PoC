"""
EvaluatorAgent with Causal Critique Capability (v0.80)

This agent performs post-mortem analysis after each game to identify
critical mistakes using causal reasoning. Part of the CRLS
(Causal Reinforcement Learning from Self-Correction) loop.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import random


@dataclass
class CausalCritique:
    """Causal analysis of game outcome"""
    game_result: str  # "win", "loss", "draw"
    critique_type: str  # "causal"
    critical_move: Optional[int] = None  # Column number for Connect4
    critical_turn: Optional[int] = None  # Turn number when mistake occurred
    reason: str = ""  # Explanation of mistake
    alternative_move: Optional[int] = None  # Better move that should have been made
    confidence: float = 1.0  # How certain we are about this critique


class EvaluatorAgent:
    """
    Agent that evaluates game outcomes and provides causal critiques

    This agent analyzes game histories to identify critical mistakes
    and provides actionable feedback for improvement.
    """

    def __init__(self, agent_id: str = "evaluator_001"):
        self.agent_id = agent_id
        self.critiques_generated = 0

    def evaluate_game(self, game_history: Dict[str, Any], agent_player: int) -> CausalCritique:
        """
        Perform post-mortem analysis on a game

        Args:
            game_history: Dict with 'moves', 'result', 'winner', 'agent_player'
            agent_player: Which player the agent was (1 or -1)

        Returns:
            CausalCritique with identified mistake and suggestion
        """
        result = game_history['result']
        winner = game_history['winner']
        moves = game_history['moves']  # List of (player, column) tuples

        # Determine game outcome from agent's perspective
        if winner == agent_player:
            game_result = "win"
        elif winner == -agent_player:
            game_result = "loss"
        else:
            game_result = "draw"

        # For losses, analyze what went wrong
        if game_result == "loss":
            critique = self._analyze_loss(moves, agent_player)
        elif game_result == "draw":
            critique = self._analyze_draw(moves, agent_player)
        else:
            # Even wins can be analyzed for improvement
            critique = self._analyze_win(moves, agent_player)

        critique.game_result = game_result
        self.critiques_generated += 1

        return critique

    def _analyze_loss(self, moves: List[Tuple[int, int]], agent_player: int) -> CausalCritique:
        """
        Analyze a loss to identify critical mistake

        Key patterns to detect:
        1. Failed to block opponent's winning threat
        2. Missed own winning opportunity
        3. Created opportunity for opponent
        4. Ignored center control
        """
        # Reconstruct board state to analyze
        board = [[0] * 7 for _ in range(6)]

        # Find the last few moves before game ended
        agent_moves = []
        opponent_moves = []

        for turn_num, (player, col) in enumerate(moves):
            # Place piece on board
            for row in range(5, -1, -1):
                if board[row][col] == 0:
                    board[row][col] = player
                    break

            if player == agent_player:
                agent_moves.append((turn_num, col))
            else:
                opponent_moves.append((turn_num, col))

        # Check if opponent won and we could have blocked
        if len(opponent_moves) >= 2:
            # Get opponent's last move (winning move)
            last_opp_turn, last_opp_col = opponent_moves[-1]

            # Check if we had a chance to block before that
            if len(agent_moves) > 0:
                last_agent_turn, last_agent_col = agent_moves[-1]

                if last_agent_turn == last_opp_turn - 1:
                    # We moved right before opponent won
                    return CausalCritique(
                        game_result="loss",
                        critique_type="causal",
                        critical_move=last_agent_col,
                        critical_turn=last_agent_turn,
                        reason=f"Failed to block opponent's winning threat at column {last_opp_col}",
                        alternative_move=last_opp_col,
                        confidence=0.9
                    )

        # Generic loss critique
        return CausalCritique(
            game_result="loss",
            critique_type="causal",
            reason="Failed to prevent opponent victory",
            confidence=0.5
        )

    def _analyze_draw(self, moves: List[Tuple[int, int]], agent_player: int) -> CausalCritique:
        """Analyze a draw"""
        return CausalCritique(
            game_result="draw",
            critique_type="causal",
            reason="Missed opportunities to create winning positions",
            confidence=0.3
        )

    def _analyze_win(self, moves: List[Tuple[int, int]], agent_player: int) -> CausalCritique:
        """Analyze a win to identify what went well"""
        agent_moves = [col for player, col in moves if player == agent_player]

        # Check if we controlled center
        center_moves = sum(1 for col in agent_moves if 2 <= col <= 4)
        total_moves = len(agent_moves)

        if total_moves > 0 and center_moves / total_moves > 0.6:
            reason = "Good center control led to victory"
        else:
            reason = "Successfully created winning position"

        return CausalCritique(
            game_result="win",
            critique_type="causal",
            reason=reason,
            confidence=0.6
        )

    def evaluate_multiple_games(self, game_histories: List[Dict[str, Any]],
                               agent_player_list: List[int]) -> List[CausalCritique]:
        """
        Evaluate multiple games and return list of critiques

        Args:
            game_histories: List of game history dicts
            agent_player_list: List of which player agent was in each game

        Returns:
            List of CausalCritique objects
        """
        critiques = []
        for game_hist, agent_player in zip(game_histories, agent_player_list):
            critique = self.evaluate_game(game_hist, agent_player)
            critiques.append(critique)
        return critiques

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about this evaluator's activity"""
        return {
            'agent_id': self.agent_id,
            'critiques_generated': self.critiques_generated
        }
