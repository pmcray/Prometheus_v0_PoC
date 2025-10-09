"""
Enhanced FreeCiv Game Simulator v2.0
- Earth map with realistic geography
- 7 simultaneous civilizations
- Rich strategy genomes
- Realistic game mechanics
"""

import random
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum

class VictoryType(Enum):
    """Victory conditions in FreeCiv"""
    DOMINATION = "Domination"  # Conquered all capitals
    SPACE_RACE = "Space Race"  # Built spaceship first
    DIPLOMATIC = "Diplomatic"  # UN victory
    CULTURAL = "Cultural"  # Cultural dominance
    MILITARY = "Military"  # Destroyed all opponents
    TIME_LIMIT = "Time Limit"  # Highest score at year 2050
    DEFEAT = "Defeat"  # Lost all cities

class BuildPriority(Enum):
    """What to prioritize building"""
    EXPANSION = "expansion"  # Settlers, explorers
    MILITARY = "military"  # Units, barracks
    ECONOMY = "economy"  # Markets, banks
    SCIENCE = "science"  # Libraries, universities
    CULTURE = "culture"  # Temples, wonders
    DEFENSE = "defense"  # Walls, fortifications

class DiplomacyStance(Enum):
    """Diplomatic strategies"""
    AGGRESSIVE = "aggressive"  # Warlike
    PEACEFUL = "peaceful"  # Trade-focused
    NEUTRAL = "neutral"  # Balanced
    ISOLATIONIST = "isolationist"  # Avoid contact

@dataclass
class StrategyGenome:
    """Rich strategy genome for evolutionary learning"""
    # Build priorities (weights sum to 1.0)
    expansion_weight: float = 0.2
    military_weight: float = 0.2
    economy_weight: float = 0.2
    science_weight: float = 0.2
    culture_weight: float = 0.1
    defense_weight: float = 0.1

    # Tech tree priorities
    tech_path: str = "balanced"  # "military", "science", "culture", "balanced"

    # Diplomacy
    diplomacy_stance: DiplomacyStance = DiplomacyStance.NEUTRAL
    alliance_tendency: float = 0.5  # 0.0 = never ally, 1.0 = always ally

    # Military tactics
    aggression_level: float = 0.5  # 0.0 = passive, 1.0 = very aggressive
    defense_ratio: float = 0.3  # fraction of military for defense

    # Expansion
    city_spacing: int = 4  # Tiles between cities
    max_cities: int = 10

    # Economy
    tax_rate: float = 0.5  # Balance between gold and science
    luxury_rate: float = 0.1  # Keep citizens happy

    def mutate(self, rate: float = 0.1):
        """Mutate genome for evolution"""
        if random.random() < rate:
            self.expansion_weight = max(0.0, min(1.0, self.expansion_weight + random.gauss(0, 0.1)))
        if random.random() < rate:
            self.military_weight = max(0.0, min(1.0, self.military_weight + random.gauss(0, 0.1)))
        if random.random() < rate:
            self.economy_weight = max(0.0, min(1.0, self.economy_weight + random.gauss(0, 0.1)))
        if random.random() < rate:
            self.science_weight = max(0.0, min(1.0, self.science_weight + random.gauss(0, 0.1)))
        if random.random() < rate:
            self.aggression_level = max(0.0, min(1.0, self.aggression_level + random.gauss(0, 0.1)))
        if random.random() < rate:
            self.tax_rate = max(0.0, min(1.0, self.tax_rate + random.gauss(0, 0.1)))

        # Normalize weights
        total = (self.expansion_weight + self.military_weight + self.economy_weight +
                self.science_weight + self.culture_weight + self.defense_weight)
        if total > 0:
            self.expansion_weight /= total
            self.military_weight /= total
            self.economy_weight /= total
            self.science_weight /= total
            self.culture_weight /= total
            self.defense_weight /= total

    @classmethod
    def random(cls):
        """Create random genome"""
        weights = np.random.dirichlet([1, 1, 1, 1, 1, 1])
        return cls(
            expansion_weight=weights[0],
            military_weight=weights[1],
            economy_weight=weights[2],
            science_weight=weights[3],
            culture_weight=weights[4],
            defense_weight=weights[5],
            tech_path=random.choice(["military", "science", "culture", "balanced"]),
            diplomacy_stance=random.choice(list(DiplomacyStance)),
            alliance_tendency=random.random(),
            aggression_level=random.random(),
            defense_ratio=random.uniform(0.2, 0.5),
            city_spacing=random.randint(3, 6),
            max_cities=random.randint(6, 15),
            tax_rate=random.uniform(0.3, 0.7),
            luxury_rate=random.uniform(0.0, 0.2)
        )

@dataclass
class City:
    """A city in FreeCiv"""
    name: str
    population: int
    x: int
    y: int
    buildings: List[str] = field(default_factory=list)
    production: str = "Warrior"

@dataclass
class Civilization:
    """A civilization in the game"""
    name: str
    leader: str
    cities: List[City]
    technology_level: int = 0
    military_power: int = 10
    gold: int = 50
    culture: int = 0
    strategy: Optional[StrategyGenome] = None
    is_player: bool = False

    @property
    def total_population(self):
        return sum(city.population for city in self.cities)

    @property
    def total_cities(self):
        return len(self.cities)

# Earth map starting positions (approximate historical locations)
EARTH_STARTING_POSITIONS = {
    "Romans": (50, 40),  # Mediterranean
    "Egyptians": (52, 35),  # Nile
    "Greeks": (51, 39),  # Aegean
    "Chinese": (75, 45),  # Yellow River
    "Babylonians": (55, 38),  # Mesopotamia
    "Indians": (65, 35),  # Indus
    "Aztecs": (20, 35),  # Central America
}

# Civilization database - 7 major civilizations
CIVILIZATIONS = [
    ("Romans", "Caesar", ["Rome", "Veii", "Neapolis", "Ravenna", "Pompeii", "Capua", "Mediolanum"]),
    ("Egyptians", "Ramesses", ["Thebes", "Memphis", "Heliopolis", "Alexandria", "Pi-Ramesses", "Giza", "Karnak"]),
    ("Greeks", "Pericles", ["Athens", "Sparta", "Corinth", "Delphi", "Knossos", "Thebes", "Argos"]),
    ("Chinese", "Qin Shi Huang", ["Beijing", "Xi'an", "Luoyang", "Nanjing", "Guangzhou", "Chengdu", "Shanghai"]),
    ("Babylonians", "Hammurabi", ["Babylon", "Ur", "Nineveh", "Akkad", "Eridu", "Uruk", "Lagash"]),
    ("Indians", "Ashoka", ["Delhi", "Pataliputra", "Varanasi", "Ujjain", "Taxila", "Kanchi", "Madurai"]),
    ("Aztecs", "Montezuma", ["Tenochtitlan", "Texcoco", "Tlacopan", "Cholula", "Tlaxcala", "Xochicalco", "Tula"]),
]

BUILDINGS = [
    "Granary", "Barracks", "Library", "Marketplace", "Temple",
    "Aqueduct", "City Walls", "Colosseum", "University", "Bank",
    "Factory", "Harbor", "Airport", "Research Lab", "Space Component"
]

TECHNOLOGIES = [
    "Alphabet", "Bronze Working", "Pottery", "The Wheel", "Writing",
    "Mathematics", "Iron Working", "Currency", "Construction", "Philosophy",
    "Feudalism", "Engineering", "Gunpowder", "Navigation", "Chemistry",
    "Steam Engine", "Railroad", "Electricity", "Automobile", "Flight",
    "Computers", "Robotics", "Space Flight", "Fusion Power"
]


class FreeCivGameEnhanced:
    """Enhanced FreeCiv game with Earth map and 7 civilizations"""

    def __init__(self, ai_difficulty: int = 1, player_strategy: Optional[StrategyGenome] = None,
                 num_opponents: int = 6, use_earth_map: bool = True):
        """
        Initialize game
        ai_difficulty: 1-10, affects opponent strength
        player_strategy: Strategy genome for player (None = random)
        num_opponents: 1-6 opponents (7 civs total including player)
        use_earth_map: Use Earth map with historical starting positions
        """
        self.ai_difficulty = ai_difficulty
        self.current_year = -4000  # Start in 4000 BC
        self.max_turns = 400
        self.current_turn = 0
        self.use_earth_map = use_earth_map

        # Earth map (100x50 grid)
        if use_earth_map:
            self.map_width = 100
            self.map_height = 50
        else:
            self.map_width = 80
            self.map_height = 50

        # Select civilizations - player + opponents
        all_civs = CIVILIZATIONS.copy()
        random.shuffle(all_civs)

        selected_civs = all_civs[:num_opponents + 1]
        player_civ_data = selected_civs[0]
        opponent_civ_data = selected_civs[1:]

        # Player civilization
        if use_earth_map:
            start_x, start_y = EARTH_STARTING_POSITIONS.get(player_civ_data[0], (50, 25))
        else:
            start_x, start_y = random.randint(5, self.map_width-5), random.randint(5, self.map_height-5)

        self.player = Civilization(
            name=player_civ_data[0],
            leader=player_civ_data[1],
            cities=[City(player_civ_data[2][0], 1, start_x, start_y, ["Palace"], "Settler")],
            technology_level=1,
            military_power=10,
            gold=50,
            culture=0,
            strategy=player_strategy if player_strategy else StrategyGenome.random(),
            is_player=True
        )

        # Opponent civilizations
        self.opponents = []
        for opp_data in opponent_civ_data:
            if use_earth_map:
                start_x, start_y = EARTH_STARTING_POSITIONS.get(opp_data[0], (50, 25))
            else:
                start_x, start_y = random.randint(5, self.map_width-5), random.randint(5, self.map_height-5)

            opp = Civilization(
                name=opp_data[0],
                leader=opp_data[1],
                cities=[City(opp_data[2][0], 1, start_x, start_y, ["Palace"], "Settler")],
                technology_level=ai_difficulty,
                military_power=10 * ai_difficulty,
                gold=50 * ai_difficulty,
                culture=0,
                strategy=StrategyGenome.random(),
                is_player=False
            )
            self.opponents.append(opp)

        self.all_civs = [self.player] + self.opponents

    def advance_year(self):
        """Advance game calendar"""
        self.current_turn += 1

        # Year advancement (follows Civ-style calendar)
        if self.current_year < -1000:
            self.current_year += 50  # 50 years per turn in ancient era
        elif self.current_year < 0:
            self.current_year += 25
        elif self.current_year < 1000:
            self.current_year += 20
        elif self.current_year < 1500:
            self.current_year += 10
        elif self.current_year < 1800:
            self.current_year += 5
        elif self.current_year < 1900:
            self.current_year += 2
        else:
            self.current_year += 1

    def format_year(self):
        """Format year as BC/AD"""
        if self.current_year < 0:
            return f"{abs(self.current_year)} BC"
        else:
            return f"{self.current_year} AD"

    def simulate_turn(self):
        """Simulate one turn of gameplay"""
        self.advance_year()

        # Simulate each civilization
        for civ in self.all_civs:
            if len(civ.cities) == 0:
                continue  # Defeated

            strategy = civ.strategy
            skill_multiplier = self.ai_difficulty if not civ.is_player else 1

            # City development
            for city in civ.cities:
                # Population growth (affected by strategy)
                growth_rate = 0.3 + strategy.economy_weight * 0.5
                if random.random() < growth_rate * skill_multiplier * 0.3:
                    city.population += 1

                # Building construction (strategy-based)
                if random.random() < 0.15 * skill_multiplier and len(city.buildings) < 10:
                    # Choose building based on strategy
                    if strategy.science_weight > 0.3 and "Library" not in city.buildings:
                        city.buildings.append("Library")
                    elif strategy.military_weight > 0.3 and "Barracks" not in city.buildings:
                        city.buildings.append("Barracks")
                    elif strategy.economy_weight > 0.3 and "Marketplace" not in city.buildings:
                        city.buildings.append("Marketplace")
                    else:
                        city.buildings.append(random.choice(BUILDINGS))

            # Expansion (new cities)
            expansion_chance = strategy.expansion_weight * 0.1
            if random.random() < expansion_chance * skill_multiplier and len(civ.cities) < strategy.max_cities:
                civ_data = next(c for c in CIVILIZATIONS if c[0] == civ.name)
                if len(civ.cities) < len(civ_data[2]):
                    city_name = civ_data[2][len(civ.cities)]
                    # Place near existing city
                    parent_city = random.choice(civ.cities)
                    new_x = parent_city.x + random.randint(-strategy.city_spacing, strategy.city_spacing)
                    new_y = parent_city.y + random.randint(-strategy.city_spacing, strategy.city_spacing)
                    new_x = max(0, min(self.map_width-1, new_x))
                    new_y = max(0, min(self.map_height-1, new_y))
                    civ.cities.append(City(city_name, 1, new_x, new_y, [], "Warrior"))

            # Technology advancement (strategy-based)
            tech_chance = 0.08 + strategy.science_weight * 0.15
            if random.random() < tech_chance * skill_multiplier:
                civ.technology_level += 1

            # Military power (strategy-based)
            military_growth = int(strategy.military_weight * 10 * skill_multiplier)
            civ.military_power += random.randint(0, military_growth)

            # Culture (strategy-based)
            culture_growth = int(len(civ.cities) * (2 + strategy.culture_weight * 5) * skill_multiplier)
            civ.culture += culture_growth

            # Gold (strategy-based)
            gold_growth = int(len(civ.cities) * strategy.economy_weight * 10 * skill_multiplier)
            civ.gold += gold_growth

    def check_victory(self) -> Tuple[bool, Optional[Civilization], VictoryType]:
        """
        Check for victory conditions
        Returns: (game_over, winning_civ, victory_type)
        """
        # Count alive civilizations
        alive_civs = [civ for civ in self.all_civs if len(civ.cities) > 0]

        # Defeat: Lost all cities
        if self.player not in alive_civs:
            winner = max(alive_civs, key=lambda c: c.culture) if alive_civs else None
            return (True, winner, VictoryType.DEFEAT)

        # Military: Only one civ left
        if len(alive_civs) == 1:
            return (True, alive_civs[0], VictoryType.MILITARY)

        # Space Race: High tech level
        for civ in alive_civs:
            if civ.technology_level >= 20:
                return (True, civ, VictoryType.SPACE_RACE)

        # Time limit: Year 2050
        if self.current_year >= 2050 or self.current_turn >= self.max_turns:
            # Calculate scores
            scores = []
            for civ in alive_civs:
                score = (civ.total_population * 10 +
                        civ.culture +
                        civ.technology_level * 50 +
                        civ.gold * 0.1)
                scores.append((civ, score))
            winner = max(scores, key=lambda x: x[1])[0]
            return (True, winner, VictoryType.TIME_LIMIT)

        return (False, None, None)

    def play_game(self, verbose=False) -> Dict:
        """
        Play a complete game
        Returns: game statistics
        """
        if verbose:
            print(f"\n🌍 NEW GAME ON EARTH MAP" if self.use_earth_map else "\n🏛️  NEW GAME")
            print(f"Player: {self.player.name} ({self.player.leader})")
            print(f"Opponents: {', '.join([o.name for o in self.opponents])}")
            print(f"Starting year: {self.format_year()}")
            print(f"AI Difficulty: {self.ai_difficulty}/10\n")

        while True:
            self.simulate_turn()

            game_over, winner, victory_type = self.check_victory()

            if game_over:
                break

        # Game statistics
        player_won = (winner == self.player)

        result = {
            'player_civ': self.player.name,
            'player_leader': self.player.leader,
            'opponents': [{'name': o.name, 'leader': o.leader} for o in self.opponents],
            'winner': winner.name if winner else "None",
            'victory_type': victory_type.value,
            'final_year': self.format_year(),
            'turns_played': self.current_turn,
            'player_cities': self.player.total_cities,
            'player_population': self.player.total_population,
            'player_tech_level': self.player.technology_level,
            'player_culture': self.player.culture,
            'player_won': player_won,
            'ai_difficulty': self.ai_difficulty,
            'num_opponents': len(self.opponents),
            'earth_map': self.use_earth_map,
            'final_standings': [
                {
                    'civ': civ.name,
                    'cities': civ.total_cities,
                    'population': civ.total_population,
                    'tech': civ.technology_level,
                    'culture': civ.culture,
                    'alive': len(civ.cities) > 0
                }
                for civ in self.all_civs
            ]
        }

        if verbose:
            self._print_results(result)

        return result

    def _print_results(self, result: Dict):
        """Print detailed game results"""
        print("="*80)
        print(f"🏆 GAME COMPLETE: {result['victory_type']} Victory!")
        print("="*80)
        print(f"Winner: {result['winner']}")
        print(f"Final Year: {result['final_year']} (Turn {result['turns_played']})")
        print(f"Earth Map: {'Yes' if result['earth_map'] else 'No'}")
        print()
        print("Final Standings:")
        print("-"*80)
        print(f"{'Civilization':<20} {'Cities':<8} {'Pop':<10} {'Tech':<8} {'Culture':<12} {'Status':<10}")
        print("-"*80)
        for standing in result['final_standings']:
            status = "🏆 Winner" if standing['civ'] == result['winner'] else ("✅ Alive" if standing['alive'] else "💀 Defeated")
            print(f"{standing['civ']:<20} {standing['cities']:<8} {standing['population']:<10} "
                  f"{standing['tech']:<8} {standing['culture']:<12} {status:<10}")
        print("-"*80)
        print()


if __name__ == "__main__":
    # Test the enhanced simulator
    print("Testing Enhanced FreeCiv Simulator with Earth Map & 7 Civilizations\n")

    for difficulty in [1, 3, 5, 8]:
        print(f"\n{'='*80}")
        print(f"Testing AI Difficulty: {difficulty}/10")
        print('='*80)

        game = FreeCivGameEnhanced(
            ai_difficulty=difficulty,
            num_opponents=6,  # 7 total civs
            use_earth_map=True
        )
        result = game.play_game(verbose=True)
