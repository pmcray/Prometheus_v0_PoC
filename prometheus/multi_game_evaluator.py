"""
Multi-Game Evaluator for CRLS Loop (v0.81)

Extends EvaluatorAgent to support multiple game types with
game-agnostic pattern recognition. Prepares for v0.85 analogy-based learning.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from prometheus.evaluator_agent import CausalCritique


class GameType(Enum):
    """Supported game types"""
    CONNECT4 = "connect4"
    OTHELLO = "othello"
    DRAUGHTS = "draughts"


@dataclass
class GameAgnosticPattern:
    """
    Abstract strategic pattern that applies across games

    These patterns enable transfer learning and analogical reasoning.
    """
    pattern_id: str
    pattern_type: str  # "blocking", "center_control", "tempo", "material_advantage"
    description: str
    games_observed: List[str] = field(default_factory=list)
    frequency: int = 0
    effectiveness: float = 0.0  # How often following this pattern leads to wins


class MultiGameEvaluator:
    """
    Evaluator that identifies patterns across multiple game types

    Extends single-game causal critique to detect abstract strategic
    patterns that generalize across games.
    """

    def __init__(self, evaluator_id: str = "multi_evaluator_001"):
        self.evaluator_id = evaluator_id
        self.critiques_by_game = {
            GameType.CONNECT4.value: [],
            GameType.OTHELLO.value: [],
            GameType.DRAUGHTS.value: []
        }
        self.patterns_discovered = []
        self.total_critiques = 0

    def evaluate_game(self, game_history: Dict[str, Any],
                     agent_player: int,
                     game_type: str = "connect4") -> CausalCritique:
        """
        Evaluate game with game-type-specific logic

        Args:
            game_history: Game history dict
            agent_player: Which player the agent was
            game_type: Type of game ("connect4", "othello", "draughts")

        Returns:
            CausalCritique with game-specific analysis
        """
        if game_type == "connect4":
            critique = self._evaluate_connect4(game_history, agent_player)
        elif game_type == "othello":
            critique = self._evaluate_othello(game_history, agent_player)
        elif game_type == "draughts":
            critique = self._evaluate_draughts(game_history, agent_player)
        else:
            # Fallback generic evaluation
            critique = self._evaluate_generic(game_history, agent_player)

        # Store critique
        if game_type in self.critiques_by_game:
            self.critiques_by_game[game_type].append(critique)

        self.total_critiques += 1

        # Extract patterns
        self._extract_patterns(critique, game_type)

        return critique

    def _evaluate_connect4(self, game_history: Dict[str, Any],
                          agent_player: int) -> CausalCritique:
        """Connect4-specific evaluation"""
        result = game_history['result']
        winner = game_history['winner']
        moves = game_history.get('moves', [])

        if winner == agent_player:
            game_result = "win"
        elif winner == -agent_player:
            game_result = "loss"
        else:
            game_result = "draw"

        # Connect4-specific patterns
        if game_result == "loss":
            # Check for blocking failures
            return CausalCritique(
                game_result="loss",
                critique_type="causal",
                reason="Failed to block opponent threat (Connect4)",
                confidence=0.7
            )
        elif game_result == "win":
            # Analyze winning strategy
            center_moves = sum(1 for p, col in moves if p == agent_player and 2 <= col <= 4)
            total_moves = sum(1 for p, col in moves if p == agent_player)

            if total_moves > 0 and center_moves / total_moves > 0.6:
                return CausalCritique(
                    game_result="win",
                    critique_type="causal",
                    reason="Center control led to victory (Connect4)",
                    confidence=0.8
                )
            else:
                return CausalCritique(
                    game_result="win",
                    critique_type="causal",
                    reason="Tactical execution successful (Connect4)",
                    confidence=0.6
                )
        else:
            return CausalCritique(
                game_result="draw",
                critique_type="causal",
                reason="Missed winning opportunities (Connect4)",
                confidence=0.5
            )

    def _evaluate_othello(self, game_history: Dict[str, Any],
                         agent_player: int) -> CausalCritique:
        """Othello-specific evaluation"""
        result = game_history['result']
        winner = game_history['winner']
        moves = game_history.get('moves', [])

        if winner == agent_player:
            game_result = "win"
        elif winner == -agent_player:
            game_result = "loss"
        else:
            game_result = "draw"

        # Othello-specific patterns
        if game_result == "loss":
            return CausalCritique(
                game_result="loss",
                critique_type="causal",
                reason="Poor edge and corner control (Othello)",
                confidence=0.7
            )
        elif game_result == "win":
            # Check for corner control
            corner_moves = sum(1 for p, pos in moves
                             if p == agent_player and pos in [0, 7, 56, 63])
            if corner_moves > 0:
                return CausalCritique(
                    game_result="win",
                    critique_type="causal",
                    reason="Corner control secured victory (Othello)",
                    confidence=0.9
                )
            else:
                return CausalCritique(
                    game_result="win",
                    critique_type="causal",
                    reason="Superior positioning (Othello)",
                    confidence=0.7
                )
        else:
            return CausalCritique(
                game_result="draw",
                critique_type="causal",
                reason="Equal material advantage (Othello)",
                confidence=0.5
            )

    def _evaluate_draughts(self, game_history: Dict[str, Any],
                          agent_player: int) -> CausalCritique:
        """Draughts-specific evaluation"""
        result = game_history['result']
        winner = game_history['winner']

        if winner == agent_player:
            game_result = "win"
        elif winner == -agent_player:
            game_result = "loss"
        else:
            game_result = "draw"

        if game_result == "loss":
            return CausalCritique(
                game_result="loss",
                critique_type="causal",
                reason="Material disadvantage or poor piece positioning (Draughts)",
                confidence=0.6
            )
        elif game_result == "win":
            return CausalCritique(
                game_result="win",
                critique_type="causal",
                reason="Material advantage maintained (Draughts)",
                confidence=0.7
            )
        else:
            return CausalCritique(
                game_result="draw",
                critique_type="causal",
                reason="Balanced endgame (Draughts)",
                confidence=0.5
            )

    def _evaluate_generic(self, game_history: Dict[str, Any],
                         agent_player: int) -> CausalCritique:
        """Generic game evaluation fallback"""
        result = game_history['result']
        winner = game_history['winner']

        if winner == agent_player:
            return CausalCritique(
                game_result="win",
                critique_type="causal",
                reason="Strategic advantage maintained",
                confidence=0.5
            )
        else:
            return CausalCritique(
                game_result="loss",
                critique_type="causal",
                reason="Strategic disadvantage",
                confidence=0.5
            )

    def _extract_patterns(self, critique: CausalCritique, game_type: str):
        """
        Extract game-agnostic patterns from critique

        Identifies abstract patterns like:
        - Blocking/threat prevention
        - Center/key position control
        - Material/tempo advantage
        """
        reason_lower = critique.reason.lower()

        # Pattern: Blocking
        if "block" in reason_lower or "threat" in reason_lower:
            self._update_pattern("blocking", "Prevent opponent threats", game_type,
                               critique.game_result == "win")

        # Pattern: Center Control
        if "center" in reason_lower or "corner" in reason_lower:
            self._update_pattern("center_control", "Control key positions", game_type,
                               critique.game_result == "win")

        # Pattern: Material Advantage
        if "material" in reason_lower or "advantage" in reason_lower:
            self._update_pattern("material", "Maintain resource advantage", game_type,
                               critique.game_result == "win")

        # Pattern: Tactical Execution
        if "tactical" in reason_lower or "execution" in reason_lower:
            self._update_pattern("tactics", "Execute tactical combinations", game_type,
                               critique.game_result == "win")

    def _update_pattern(self, pattern_type: str, description: str,
                       game_type: str, was_successful: bool):
        """Update or create a pattern"""
        # Find existing pattern
        pattern = None
        for p in self.patterns_discovered:
            if p.pattern_type == pattern_type:
                pattern = p
                break

        if pattern is None:
            # Create new pattern
            pattern = GameAgnosticPattern(
                pattern_id=f"pattern_{len(self.patterns_discovered)}",
                pattern_type=pattern_type,
                description=description,
                games_observed=[game_type],
                frequency=1,
                effectiveness=1.0 if was_successful else 0.0
            )
            self.patterns_discovered.append(pattern)
        else:
            # Update existing pattern
            pattern.frequency += 1
            if game_type not in pattern.games_observed:
                pattern.games_observed.append(game_type)

            # Update effectiveness (running average)
            success_val = 1.0 if was_successful else 0.0
            pattern.effectiveness = (
                (pattern.effectiveness * (pattern.frequency - 1) + success_val)
                / pattern.frequency
            )

    def get_cross_game_patterns(self, min_games: int = 2) -> List[GameAgnosticPattern]:
        """
        Get patterns that appear in multiple game types

        These patterns are candidates for analogical transfer.

        Args:
            min_games: Minimum number of game types pattern must appear in

        Returns:
            List of cross-game patterns
        """
        return [p for p in self.patterns_discovered
                if len(p.games_observed) >= min_games]

    def get_game_stats(self) -> Dict[str, Any]:
        """Get statistics by game type"""
        stats = {}

        for game_type, critiques in self.critiques_by_game.items():
            if critiques:
                wins = sum(1 for c in critiques if c.game_result == "win")
                losses = sum(1 for c in critiques if c.game_result == "loss")
                draws = sum(1 for c in critiques if c.game_result == "draw")
                total = len(critiques)

                stats[game_type] = {
                    'total_games': total,
                    'wins': wins,
                    'losses': losses,
                    'draws': draws,
                    'win_rate': wins / total if total > 0 else 0.0
                }
            else:
                stats[game_type] = {
                    'total_games': 0,
                    'wins': 0,
                    'losses': 0,
                    'draws': 0,
                    'win_rate': 0.0
                }

        return stats

    def get_pattern_summary(self) -> Dict[str, Any]:
        """Get summary of discovered patterns"""
        return {
            'total_patterns': len(self.patterns_discovered),
            'cross_game_patterns': len(self.get_cross_game_patterns()),
            'patterns': [
                {
                    'type': p.pattern_type,
                    'description': p.description,
                    'games': p.games_observed,
                    'frequency': p.frequency,
                    'effectiveness': f"{p.effectiveness:.1%}"
                }
                for p in self.patterns_discovered
            ]
        }
