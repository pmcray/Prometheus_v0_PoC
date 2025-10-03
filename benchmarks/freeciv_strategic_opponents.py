"""
FreeCiv Strategic Opponents
Maps to built-in AI difficulty levels for objective skill measurement
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class FreeCivOpponentConfig:
    """Configuration for FreeCiv AI opponent"""
    name: str
    skill_level: int  # 0-10 scale for comparison
    ai_level: str  # FreeCiv AI level identifier
    description: str
    expected_win_rate_random: float  # Expected win rate for random agent


# FreeCiv built-in AI levels (from easiest to hardest)
# Reference: https://freeciv.fandom.com/wiki/AI
FREECIV_AI_LEVELS = {
    "novice": FreeCivOpponentConfig(
        name="Novice AI",
        skill_level=1,
        ai_level="novice",
        description="Weakest AI - makes obvious mistakes, poor city placement",
        expected_win_rate_random=0.05  # Even random agent might win 5%
    ),

    "easy": FreeCivOpponentConfig(
        name="Easy AI",
        skill_level=3,
        ai_level="easy",
        description="Basic AI - understands fundamentals but weak tactics",
        expected_win_rate_random=0.01  # Very unlikely for random to win
    ),

    "normal": FreeCivOpponentConfig(
        name="Normal AI",
        skill_level=5,
        ai_level="normal",
        description="Standard AI - competent play, balanced strategy",
        expected_win_rate_random=0.001  # Almost impossible for random
    ),

    "hard": FreeCivOpponentConfig(
        name="Hard AI",
        skill_level=7,
        ai_level="hard",
        description="Strong AI - aggressive expansion, good tactics",
        expected_win_rate_random=0.0001  # Effectively impossible
    ),

    "cheating": FreeCivOpponentConfig(
        name="Cheating AI",
        skill_level=9,
        ai_level="cheating",
        description="Expert AI with resource bonuses - very challenging",
        expected_win_rate_random=0.0  # Impossible for random agent
    ),

    "experimental": FreeCivOpponentConfig(
        name="Experimental AI",
        skill_level=10,
        ai_level="experimental",
        description="Cutting-edge AI with advanced strategies",
        expected_win_rate_random=0.0
    ),
}


# Curriculum for progressive training
FREECIV_CURRICULUM = [
    {
        "stage": 1,
        "opponent": "novice",
        "target_win_rate": 0.30,
        "min_games": 10,
        "max_games": 30,
        "description": "Learn basic mechanics and city management"
    },
    {
        "stage": 2,
        "opponent": "easy",
        "target_win_rate": 0.20,
        "min_games": 20,
        "max_games": 50,
        "description": "Develop tactical awareness and unit control"
    },
    {
        "stage": 3,
        "opponent": "normal",
        "target_win_rate": 0.15,
        "min_games": 30,
        "max_games": 100,
        "description": "Master strategic planning and resource management"
    },
    {
        "stage": 4,
        "opponent": "hard",
        "target_win_rate": 0.10,
        "min_games": 50,
        "max_games": 200,
        "description": "Refine advanced tactics and long-term strategy"
    },
]


class FreeCivOpponentManager:
    """
    Manages FreeCiv opponent selection and difficulty progression
    """

    def __init__(self, initial_level: str = "novice"):
        self.current_level = initial_level
        self.level_history = [initial_level]
        self.performance_history = []

    def get_current_opponent(self) -> FreeCivOpponentConfig:
        """Get current opponent configuration"""
        return FREECIV_AI_LEVELS[self.current_level]

    def update_performance(self, win_rate: float, games_played: int):
        """Record performance and potentially adjust difficulty"""
        self.performance_history.append({
            'level': self.current_level,
            'win_rate': win_rate,
            'games': games_played
        })

    def should_advance(self, win_rate: float, games_played: int, min_games: int = 20) -> bool:
        """
        Check if agent should advance to next difficulty

        Criteria:
        - Played minimum number of games
        - Achieved target win rate for current level
        """
        if games_played < min_games:
            return False

        current_stage = self._get_current_curriculum_stage()
        if current_stage and win_rate >= current_stage['target_win_rate']:
            return True

        return False

    def advance_difficulty(self) -> Optional[str]:
        """
        Advance to next difficulty level

        Returns:
            New level name, or None if already at max
        """
        levels = list(FREECIV_AI_LEVELS.keys())
        current_idx = levels.index(self.current_level)

        if current_idx < len(levels) - 1:
            self.current_level = levels[current_idx + 1]
            self.level_history.append(self.current_level)
            return self.current_level

        return None

    def get_curriculum_progress(self) -> Dict[str, Any]:
        """Get current curriculum stage progress"""
        stage = self._get_current_curriculum_stage()

        if not stage:
            return {"stage": "max", "progress": 1.0}

        if not self.performance_history:
            return {"stage": stage["stage"], "progress": 0.0}

        recent = [p for p in self.performance_history if p['level'] == self.current_level]
        if not recent:
            return {"stage": stage["stage"], "progress": 0.0}

        total_games = sum(p['games'] for p in recent)
        avg_win_rate = sum(p['win_rate'] * p['games'] for p in recent) / total_games if total_games > 0 else 0

        # Progress is combination of games played and win rate achieved
        games_progress = min(total_games / stage['max_games'], 1.0)
        winrate_progress = min(avg_win_rate / stage['target_win_rate'], 1.0) if stage['target_win_rate'] > 0 else 1.0

        return {
            "stage": stage["stage"],
            "progress": (games_progress + winrate_progress) / 2,
            "games_played": total_games,
            "target_games": stage['max_games'],
            "win_rate": avg_win_rate,
            "target_win_rate": stage['target_win_rate'],
            "description": stage['description']
        }

    def _get_current_curriculum_stage(self) -> Optional[Dict[str, Any]]:
        """Get curriculum stage for current level"""
        for stage in FREECIV_CURRICULUM:
            if stage['opponent'] == self.current_level:
                return stage
        return None


def get_opponent_config(level: str = "novice") -> FreeCivOpponentConfig:
    """Get opponent configuration by level name"""
    return FREECIV_AI_LEVELS.get(level, FREECIV_AI_LEVELS["novice"])


def estimate_training_time(
    population_size: int,
    generations: int,
    games_per_eval: int = 5,
    minutes_per_game: float = 30.0
) -> Dict[str, float]:
    """
    Estimate total training time for FreeCiv evolution

    Args:
        population_size: Number of agents in population
        generations: Number of generations
        games_per_eval: Games played per agent evaluation
        minutes_per_game: Average minutes per FreeCiv game

    Returns:
        Time estimates in various units
    """
    total_evaluations = population_size * generations
    total_games = total_evaluations * games_per_eval
    total_minutes = total_games * minutes_per_game

    return {
        'total_games': total_games,
        'total_minutes': total_minutes,
        'total_hours': total_minutes / 60,
        'total_days': total_minutes / (60 * 24),
        'per_generation_hours': (population_size * games_per_eval * minutes_per_game) / 60,
    }


# Example usage and time estimates
if __name__ == "__main__":
    print("=" * 70)
    print("FreeCiv Strategic Training - Time Estimates")
    print("=" * 70)

    # Quick test configuration
    print("\n📊 QUICK TEST (Proof of Concept):")
    quick = estimate_training_time(
        population_size=4,
        generations=5,
        games_per_eval=3,
        minutes_per_game=20  # Fast game settings
    )
    print(f"  Population: 4 agents")
    print(f"  Generations: 5")
    print(f"  Total time: {quick['total_hours']:.1f} hours ({quick['total_days']:.1f} days)")

    # Full training configuration
    print("\n📊 FULL TRAINING (Novice AI):")
    full = estimate_training_time(
        population_size=10,
        generations=20,
        games_per_eval=5,
        minutes_per_game=30
    )
    print(f"  Population: 10 agents")
    print(f"  Generations: 20")
    print(f"  Total time: {full['total_hours']:.1f} hours ({full['total_days']:.1f} days)")

    # Curriculum training
    print("\n📊 CURRICULUM TRAINING (All 4 stages):")
    curriculum_time = 0
    for stage in FREECIV_CURRICULUM:
        stage_est = estimate_training_time(
            population_size=10,
            generations=stage['max_games'] // (10 * 5),  # Rough estimate
            games_per_eval=5,
            minutes_per_game=30
        )
        curriculum_time += stage_est['total_hours']
        print(f"  Stage {stage['stage']} ({stage['opponent']}): {stage_est['total_hours']:.1f} hours")

    print(f"\n  📅 Total curriculum time: {curriculum_time:.1f} hours ({curriculum_time/24:.1f} days)")

    print("\n" + "=" * 70)
    print("💡 RECOMMENDATIONS:")
    print("=" * 70)
    print("  • Start with quick test (4 agents, 5 gens) to verify pipeline")
    print("  • Use parallel evaluation if possible (multiple game servers)")
    print("  • Run overnight/weekend for longer training runs")
    print("  • Consider cloud compute for curriculum training")
    print("  • Save checkpoints every generation (can take days!)")
    print()
