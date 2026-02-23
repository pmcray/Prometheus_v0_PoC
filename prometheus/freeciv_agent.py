"""
FreeCiv Agent using CRLS Learning

Prometheus agent that learns to play FreeCiv through:
- Causal analysis of game outcomes
- Strategy evolution via Recursive Font
- Multi-game pattern recognition
- Safe self-improvement with alignment governance
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import json
import time

from prometheus.freeciv_environment import (
    FreeCivEnvironment, FreeCivAction, GameState, DifficultyLevel
)
from prometheus.evaluator_agent import EvaluatorAgent
from prometheus.corrector_agent import CorrectorAgent
from prometheus.recursive_font import (
    RecursiveStrategy, RecursiveFontEngine, StrategyComponent, create_connect4_recursive_strategy
)
from prometheus.alignment_governor import AlignmentGovernor


@dataclass
class FreeCivGameHistory:
    """History of a complete FreeCiv game"""
    game_id: str
    difficulty: str
    start_state: GameState
    end_state: GameState
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    turn_states: List[GameState] = field(default_factory=list)
    total_turns: int = 0
    final_score: int = 0
    victory: bool = False
    defeat: bool = False

    # Strategic metrics
    avg_cities_per_turn: float = 0.0
    avg_tech_rate: float = 0.0
    peak_military: int = 0
    total_production: int = 0


class FreeCivStrategy:
    """
    Strategic decision-making for FreeCiv

    Encodes high-level strategies like:
    - Expansion (early city building)
    - Science (tech tree focus)
    - Military (conquest)
    - Economic (gold/production focus)
    """

    def __init__(self, strategy_type: str = "balanced"):
        self.strategy_type = strategy_type
        self.priorities = self._get_priorities()

    def _get_priorities(self) -> Dict[str, float]:
        """Get strategy priorities"""
        if self.strategy_type == "expansion":
            return {
                'city_building': 0.9,
                'settler_production': 0.8,
                'exploration': 0.7,
                'science': 0.5,
                'military': 0.3
            }
        elif self.strategy_type == "science":
            return {
                'science': 0.9,
                'libraries': 0.8,
                'universities': 0.7,
                'city_building': 0.5,
                'military': 0.4
            }
        elif self.strategy_type == "military":
            return {
                'military': 0.9,
                'barracks': 0.8,
                'unit_production': 0.8,
                'city_building': 0.5,
                'science': 0.4
            }
        else:  # balanced
            return {
                'city_building': 0.7,
                'science': 0.7,
                'military': 0.6,
                'exploration': 0.6,
                'production': 0.6
            }

    def decide_research(self, available_techs: List[str]) -> Optional[str]:
        """Decide which technology to research"""
        if self.strategy_type == "science":
            # Prioritize science-boosting techs
            science_techs = ["Writing", "Alphabet", "Mathematics", "Philosophy", "University"]
            for tech in science_techs:
                if tech in available_techs:
                    return tech

        elif self.strategy_type == "military":
            # Prioritize military techs
            military_techs = ["Bronze Working", "Iron Working", "Horseback Riding", "Gunpowder"]
            for tech in military_techs:
                if tech in available_techs:
                    return tech

        # Default: first available
        return available_techs[0] if available_techs else None

    def decide_city_production(self, city: Dict[str, Any]) -> str:
        """Decide what to build in a city"""
        size = city.get('size', 1)

        # Early game: settlers and workers
        if size >= 2 and self.priorities.get('settler_production', 0) > 0.7:
            return "Settlers"

        # Build defensive units
        if self.priorities.get('military', 0) > 0.7:
            return "Warriors"

        # Build infrastructure
        if 'Granary' not in city.get('buildings', []):
            return "Granary"

        if self.priorities.get('science', 0) > 0.7 and 'Library' not in city.get('buildings', []):
            return "Library"

        # Default: basic unit
        return "Warriors"


class FreeCivAgent:
    """
    Prometheus agent for FreeCiv

    Uses CRLS loop to improve strategies:
    1. Play game with current strategy
    2. Evaluate performance (EvaluatorAgent)
    3. Generate strategic critique
    4. Evolve strategy (CorrectorAgent + Recursive Font)
    5. Verify safety (AlignmentGovernor)
    """

    def __init__(self, agent_id: str = "freeciv_agent_001", use_simulator: bool = False):
        self.agent_id = agent_id
        self.use_simulator = use_simulator

        if use_simulator:
            from prometheus.freeciv_simulator import FreeCivSimulator
            self.environment = None  # Simulator created per game
        else:
            self.environment = FreeCivEnvironment()

        # CRLS components
        self.evaluator = EvaluatorAgent(f"{agent_id}_eval")
        self.corrector = CorrectorAgent(f"{agent_id}_corr")
        self.font_engine = RecursiveFontEngine(f"{agent_id}_font")
        self.governor = AlignmentGovernor(f"{agent_id}_gov")

        # Current strategy
        self.current_strategy = self._create_initial_strategy()
        self.font_engine.register_strategy(self.current_strategy)

        # Game history
        self.games_played = []
        self.current_game = None

        # Learning stats
        self.generation = 0
        self.best_score = 0
        self.win_count = 0
        self.total_games = 0

    def _create_initial_strategy(self) -> RecursiveStrategy:
        """Create initial FreeCiv strategy"""
        components = [
            StrategyComponent(
                component_id="EARLY_EXPANSION",
                condition="turn < 50 and cities < 5",
                action="build settlers and found cities",
                priority=0.9
            ),
            StrategyComponent(
                component_id="TECH_RESEARCH",
                condition="science rate low",
                action="prioritize science-boosting buildings",
                priority=0.7
            ),
            StrategyComponent(
                component_id="BASIC_DEFENSE",
                condition="cities > 2",
                action="maintain defensive units in each city",
                priority=0.8
            ),
            StrategyComponent(
                component_id="INFRASTRUCTURE",
                condition="city size >= 3",
                action="build granaries and libraries",
                priority=0.6
            )
        ]

        return RecursiveStrategy("freeciv_strategy_001", components)

    def play_game(self, difficulty: DifficultyLevel = DifficultyLevel.NORMAL,
                  max_turns: int = 200) -> FreeCivGameHistory:
        """
        Play a complete game of FreeCiv

        Args:
            difficulty: AI difficulty level
            max_turns: Maximum turns to play

        Returns:
            Game history
        """
        print(f"\n{'='*60}")
        print(f"Starting FreeCiv game (Generation {self.generation})")
        print(f"Difficulty: {difficulty.value}")
        print(f"{'='*60}\n")

        # Reset environment
        if self.use_simulator:
            from prometheus.freeciv_simulator import FreeCivSimulator
            self.environment = FreeCivSimulator(difficulty=difficulty)
            initial_state = self.environment.reset()
        else:
            initial_state = self.environment.reset(difficulty=difficulty)

        # Create game history
        game_history = FreeCivGameHistory(
            game_id=f"game_{self.total_games:04d}",
            difficulty=difficulty.value,
            start_state=initial_state,
            end_state=initial_state
        )

        self.current_game = game_history

        # Play game
        done = False
        turn = 0

        while not done and turn < max_turns:
            # Get current state
            state = self.environment.current_state

            # Decide actions based on strategy
            actions = self._decide_actions(state)

            # Execute actions
            for action in actions:
                new_state, reward, done, info = self.environment.step(action)

                # Record
                game_history.actions_taken.append({
                    'turn': turn,
                    'action': action.action_type,
                    'params': action.parameters,
                    'reward': reward
                })

                game_history.turn_states.append(new_state)

                if done:
                    break

            # Progress report every 10 turns
            if turn % 10 == 0:
                self._print_progress(state, turn)

            turn += 1

        # Finalize game history
        game_history.end_state = self.environment.current_state
        game_history.total_turns = turn
        game_history.final_score = game_history.end_state.score
        game_history.victory = game_history.end_state.cities > 0

        # Calculate metrics
        if game_history.total_turns > 0:
            total_cities = sum(s.cities for s in game_history.turn_states)
            game_history.avg_cities_per_turn = total_cities / game_history.total_turns

        # Store
        self.games_played.append(game_history)
        self.total_games += 1

        if game_history.victory:
            self.win_count += 1
            if game_history.final_score > self.best_score:
                self.best_score = game_history.final_score

        print(f"\n{'='*60}")
        print(f"Game Ended - Turn {game_history.total_turns}")
        print(f"Final Score: {game_history.final_score}")
        print(f"Result: {'VICTORY' if game_history.victory else 'DEFEAT'}")
        print(f"{'='*60}\n")

        return game_history

    def _decide_actions(self, state: GameState) -> List[FreeCivAction]:
        """
        Decide actions to take based on current strategy

        Args:
            state: Current game state

        Returns:
            List of actions to execute
        """
        actions = []

        # Extract strategy priorities
        priorities = {}
        for comp in self.current_strategy.components.values():
            # Parse action to extract priority
            if "settler" in comp.action.lower():
                priorities['settlers'] = comp.priority
            elif "science" in comp.action.lower():
                priorities['science'] = comp.priority
            elif "defense" in comp.action.lower():
                priorities['defense'] = comp.priority

        # Set research rates based on strategy
        science_rate = int(priorities.get('science', 0.5) * 100)
        actions.append(FreeCivAction(
            action_type="set_rates",
            parameters={'tax': 0, 'science': science_rate}
        ))

        return actions

    def _print_progress(self, state: GameState, turn: int):
        """Print progress update"""
        print(f"Turn {turn:3d} | "
              f"Score: {state.score:5d} | "
              f"Cities: {state.cities:2d} | "
              f"Pop: {state.population:4d} | "
              f"Techs: {state.techs_researched:2d}")

    def learn_from_game(self, game_history: FreeCivGameHistory) -> Dict[str, Any]:
        """
        Apply CRLS learning from game

        Args:
            game_history: Completed game

        Returns:
            Learning results
        """
        print(f"\n{'='*60}")
        print(f"CRLS Learning Cycle - Generation {self.generation}")
        print(f"{'='*60}\n")

        # 1. Evaluate game performance
        critique = self._evaluate_performance(game_history)
        print(f"Evaluation: {critique['assessment']}")
        print(f"Key Issues: {', '.join(critique['issues'])}")

        # 2. Update strategy component performance
        self._update_component_performance(game_history, critique)

        # 3. Propose strategy modification
        performance_data = {
            'score': game_history.final_score,
            'victory': game_history.victory,
            'turns': game_history.total_turns,
            'avg_cities': game_history.avg_cities_per_turn
        }

        modification = self.font_engine.evolve_strategy(
            self.current_strategy.strategy_id,
            performance_data,
            safety_check=self._safety_check
        )

        result = {
            'generation': self.generation,
            'critique': critique,
            'modification': None,
            'new_strategy': None
        }

        if modification:
            print(f"\nStrategy Evolution:")
            print(f"  Type: {modification.modification_type.value}")
            print(f"  Description: {modification.description}")

            result['modification'] = {
                'type': modification.modification_type.value,
                'description': modification.description,
                'approved': modification.approved
            }

            self.generation += 1

        else:
            print("\nNo strategy modification proposed (strategy stable)")

        print(f"\n{'='*60}\n")

        return result

    def _evaluate_performance(self, game_history: FreeCivGameHistory) -> Dict[str, Any]:
        """
        Evaluate game performance and generate critique

        Args:
            game_history: Game to evaluate

        Returns:
            Critique with issues and suggestions
        """
        critique = {
            'assessment': '',
            'issues': [],
            'strengths': [],
            'suggestions': []
        }

        # Check victory/defeat
        if game_history.victory:
            critique['assessment'] = "Victory achieved"
            critique['strengths'].append(f"Final score: {game_history.final_score}")
        else:
            critique['assessment'] = "Defeat - eliminated"
            critique['issues'].append("Lost all cities")

        # Analyze expansion
        if game_history.avg_cities_per_turn < 0.05:
            critique['issues'].append("Very slow city expansion")
            critique['suggestions'].append("Increase settler production priority")

        # Analyze technology
        final_techs = game_history.end_state.techs_researched
        if final_techs < game_history.total_turns / 10:
            critique['issues'].append("Slow technological progress")
            critique['suggestions'].append("Increase science rate")

        # Analyze economy
        if game_history.end_state.gold < 100:
            critique['issues'].append("Low gold reserves")

        return critique

    def _update_component_performance(self, game_history: FreeCivGameHistory,
                                      critique: Dict[str, Any]):
        """Update performance history of strategy components"""

        # Determine if components succeeded based on critique
        for comp_id, component in self.current_strategy.components.items():
            success = False

            if "expansion" in comp_id.lower():
                # Success if we built cities
                success = game_history.avg_cities_per_turn >= 0.05

            elif "tech" in comp_id.lower() or "science" in comp_id.lower():
                # Success if we researched techs
                success = game_history.end_state.techs_researched >= game_history.total_turns / 10

            elif "defense" in comp_id.lower():
                # Success if we didn't lose
                success = game_history.victory

            else:
                # Default: success if we won
                success = game_history.victory

            component.performance_history.append(success)

    def _safety_check(self, modification) -> bool:
        """
        Safety check for strategy modifications

        Args:
            modification: Proposed modification

        Returns:
            True if safe
        """
        is_safe, violations = self.governor.review_strategy(
            modification.description,
            context={'game': 'freeciv'}
        )

        return is_safe

    def train(self, num_games: int = 10, difficulty: DifficultyLevel = DifficultyLevel.NORMAL):
        """
        Train agent through multiple games

        Args:
            num_games: Number of games to play
            difficulty: AI difficulty level
        """
        print(f"\n{'='*60}")
        print(f"TRAINING FREECIV AGENT")
        print(f"{'='*60}")
        print(f"Games: {num_games}")
        print(f"Difficulty: {difficulty.value}")
        print(f"{'='*60}\n")

        for game_num in range(num_games):
            print(f"\n>>> Game {game_num + 1}/{num_games}")

            # Play game
            game_history = self.play_game(difficulty=difficulty, max_turns=100)

            # Learn from game
            learning_result = self.learn_from_game(game_history)

            # Print stats
            self._print_training_stats()

        print(f"\n{'='*60}")
        print(f"TRAINING COMPLETE")
        print(f"{'='*60}")
        self._print_training_stats()

    def _print_training_stats(self):
        """Print training statistics"""
        win_rate = (self.win_count / self.total_games * 100) if self.total_games > 0 else 0

        print(f"\nTraining Statistics:")
        print(f"  Total Games: {self.total_games}")
        print(f"  Wins: {self.win_count}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Best Score: {self.best_score}")
        print(f"  Generation: {self.generation}")
        print(f"  Strategy Components: {len(self.current_strategy.components)}")

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            'agent_id': self.agent_id,
            'total_games': self.total_games,
            'wins': self.win_count,
            'win_rate': (self.win_count / self.total_games) if self.total_games > 0 else 0.0,
            'best_score': self.best_score,
            'generation': self.generation,
            'strategy_components': len(self.current_strategy.components)
        }
