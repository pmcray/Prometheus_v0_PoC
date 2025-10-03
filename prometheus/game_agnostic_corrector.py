"""
Game-Agnostic Corrector for Multi-Game CRLS (v0.81)

Synthesizes strategic improvements that transfer across multiple game types.
Identifies abstract patterns and generates universal strategic principles.
"""

from typing import Dict, Any, List, Optional
from prometheus.evaluator_agent import CausalCritique
from prometheus.multi_game_evaluator import GameAgnosticPattern


class GameAgnosticCorrector:
    """
    Corrector that identifies universal strategic patterns across games

    Builds on single-game CorrectorAgent to find abstract principles
    that apply regardless of specific game mechanics.
    """

    def __init__(self, corrector_id: str = "game_agnostic_corrector_001"):
        self.corrector_id = corrector_id
        self.corrections_generated = 0
        self.strategy_history_by_game = {
            'connect4': [],
            'othello': [],
            'draughts': []
        }
        self.universal_strategies = []

    def synthesize_game_strategy(self, critiques: List[CausalCritique],
                                 game_type: str) -> str:
        """
        Synthesize strategy for a specific game type

        Args:
            critiques: List of critiques for this game
            game_type: Type of game

        Returns:
            Game-specific strategic prompt
        """
        if not critiques:
            return f"Play systematically in {game_type}."

        # Count outcomes and issues
        wins = sum(1 for c in critiques if c.game_result == "win")
        losses = sum(1 for c in critiques if c.game_result == "loss")
        draws = sum(1 for c in critiques if c.game_result == "draw")
        total = len(critiques)
        win_rate = wins / total if total > 0 else 0.0

        # Analyze patterns
        blocking_issues = sum(1 for c in critiques if "block" in c.reason.lower())
        center_issues = sum(1 for c in critiques if "center" in c.reason.lower() or "corner" in c.reason.lower())
        tactical_issues = sum(1 for c in critiques if "tactical" in c.reason.lower())
        material_issues = sum(1 for c in critiques if "material" in c.reason.lower())

        # Build strategy
        parts = [f"{game_type.upper()} Strategy Analysis: {wins}W-{losses}L-{draws}D (Win rate: {win_rate:.1%})"]

        priorities = []

        # Game-specific priorities
        if game_type == "connect4":
            if blocking_issues > total * 0.3:
                priorities.append("CRITICAL: Scan all columns for opponent 3-in-a-row threats and block immediately")
            if center_issues > 0:
                priorities.append("Priority: Prefer center columns (2-4) for better positioning")

        elif game_type == "othello":
            if center_issues > 0:
                priorities.append("CRITICAL: Secure corners (0, 7, 56, 63) and avoid adjacent squares")
            if material_issues > 0:
                priorities.append("Priority: Maximize piece flips while maintaining edge control")

        elif game_type == "draughts":
            if material_issues > total * 0.3:
                priorities.append("CRITICAL: Protect pieces and avoid unnecessary trades")
            if tactical_issues > 0:
                priorities.append("Priority: Advance pieces toward king row systematically")

        # Universal priorities based on performance
        if win_rate < 0.3:
            priorities.append("FUNDAMENTAL: Focus on defensive play and avoiding mistakes")
        elif win_rate < 0.7:
            priorities.append("ADVANCED: Balance aggressive and defensive tactics")

        if priorities:
            parts.append("\n".join(priorities))

        strategy = "\n\n".join(parts)

        # Store in history
        if game_type in self.strategy_history_by_game:
            self.strategy_history_by_game[game_type].append({
                'generation': len(self.strategy_history_by_game[game_type]),
                'win_rate': win_rate,
                'strategy': strategy
            })

        self.corrections_generated += 1
        return strategy

    def synthesize_universal_strategy(self, patterns: List[GameAgnosticPattern],
                                      game_stats: Dict[str, Any]) -> str:
        """
        Synthesize universal strategy from cross-game patterns

        Args:
            patterns: List of GameAgnosticPattern objects
            game_stats: Statistics by game type

        Returns:
            Universal strategic prompt applicable to all games
        """
        if not patterns:
            return "Apply systematic strategic thinking across all games."

        # Filter for cross-game patterns (appear in 2+ games)
        cross_game_patterns = [p for p in patterns if len(p.games_observed) >= 2]

        if not cross_game_patterns:
            return "Continue learning game-specific patterns."

        # Build universal strategy
        parts = ["UNIVERSAL STRATEGIC PRINCIPLES (Cross-Game Learning):"]
        parts.append("=" * 60)

        # Overall performance
        total_games = sum(stats['total_games'] for stats in game_stats.values())
        total_wins = sum(stats['wins'] for stats in game_stats.values())
        overall_win_rate = total_wins / total_games if total_games > 0 else 0.0

        parts.append(f"Overall Performance: {total_wins}/{total_games} games won ({overall_win_rate:.1%})")
        parts.append("")

        # Universal patterns discovered
        parts.append("Discovered Universal Patterns:")

        for pattern in sorted(cross_game_patterns, key=lambda p: p.effectiveness, reverse=True):
            games_str = ", ".join(pattern.games_observed)
            parts.append(
                f"  • {pattern.description} "
                f"(Observed in: {games_str}) "
                f"[Effectiveness: {pattern.effectiveness:.1%}, Frequency: {pattern.frequency}]"
            )

        parts.append("")
        parts.append("Strategic Priorities:")

        # Generate priorities based on most effective patterns
        effective_patterns = sorted(cross_game_patterns, key=lambda p: p.effectiveness, reverse=True)

        for i, pattern in enumerate(effective_patterns[:3], 1):  # Top 3
            if pattern.pattern_type == "blocking":
                parts.append(f"  {i}. THREAT PREVENTION: Always identify and neutralize opponent threats before attacking")
            elif pattern.pattern_type == "center_control":
                parts.append(f"  {i}. KEY POSITION CONTROL: Secure strategically important positions (centers, corners, edges)")
            elif pattern.pattern_type == "material":
                parts.append(f"  {i}. RESOURCE ADVANTAGE: Maintain and expand material/positional advantages")
            elif pattern.pattern_type == "tactics":
                parts.append(f"  {i}. TACTICAL PRECISION: Execute combinations that create multiple threats")

        # Add learning insight
        parts.append("")
        parts.append("Learning Insight:")
        if overall_win_rate > 0.7:
            parts.append("  Strong performance across games. Continue refining advanced tactics.")
        elif overall_win_rate > 0.5:
            parts.append("  Moderate performance. Focus on consistent application of discovered patterns.")
        else:
            parts.append("  Building foundation. Prioritize defensive play and pattern recognition.")

        universal_strategy = "\n".join(parts)

        # Store in history
        self.universal_strategies.append({
            'generation': len(self.universal_strategies),
            'overall_win_rate': overall_win_rate,
            'patterns_count': len(cross_game_patterns),
            'strategy': universal_strategy
        })

        return universal_strategy

    def get_strategy_evolution(self, game_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get strategy evolution history

        Args:
            game_type: Specific game type, or None for universal strategies

        Returns:
            List of strategy history entries
        """
        if game_type is None:
            return self.universal_strategies.copy()
        elif game_type in self.strategy_history_by_game:
            return self.strategy_history_by_game[game_type].copy()
        else:
            return []

    def get_transfer_learning_score(self, patterns: List[GameAgnosticPattern]) -> float:
        """
        Calculate transfer learning score

        Measures how well patterns generalize across games.

        Returns:
            Score from 0.0 to 1.0 indicating transfer learning quality
        """
        if not patterns:
            return 0.0

        cross_game_patterns = [p for p in patterns if len(p.games_observed) >= 2]

        if not cross_game_patterns:
            return 0.0

        # Score based on:
        # 1. Proportion of patterns that generalize
        generalization_ratio = len(cross_game_patterns) / len(patterns)

        # 2. Average effectiveness of cross-game patterns
        avg_effectiveness = sum(p.effectiveness for p in cross_game_patterns) / len(cross_game_patterns)

        # 3. Average number of games per pattern
        avg_games_per_pattern = sum(len(p.games_observed) for p in cross_game_patterns) / len(cross_game_patterns)
        games_diversity = min(1.0, avg_games_per_pattern / 3.0)  # Normalize to max 3 games

        # Weighted combination
        transfer_score = (
            0.4 * generalization_ratio +
            0.4 * avg_effectiveness +
            0.2 * games_diversity
        )

        return transfer_score

    def get_stats(self) -> Dict[str, Any]:
        """Get corrector statistics"""
        return {
            'corrector_id': self.corrector_id,
            'corrections_generated': self.corrections_generated,
            'universal_strategies_count': len(self.universal_strategies),
            'game_strategies': {
                game: len(history)
                for game, history in self.strategy_history_by_game.items()
            }
        }
