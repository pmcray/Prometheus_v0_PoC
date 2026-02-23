"""
Enhanced FreeCiv Game Simulator
Simulates realistic FreeCiv gameplay with civilizations, cities, years, victory conditions
"""

import random
from dataclasses import dataclass
from typing import List, Dict, Tuple
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

@dataclass
class City:
    """A city in FreeCiv"""
    name: str
    population: int
    buildings: List[str]
    production: str

@dataclass
class Civilization:
    """A civilization in the game"""
    name: str
    leader: str
    cities: List[City]
    technology_level: int  # Number of techs researched
    military_power: int
    gold: int
    culture: int

    @property
    def total_population(self):
        return sum(city.population for city in self.cities)

    @property
    def total_cities(self):
        return len(self.cities)

# Civilization database (like Civ I/II)
CIVILIZATIONS = [
    ("Romans", "Caesar", ["Rome", "Veii", "Neapolis", "Ravenna", "Pompeii"]),
    ("Egyptians", "Ramesses", ["Thebes", "Memphis", "Heliopolis", "Alexandria", "Pi-Ramesses"]),
    ("Greeks", "Pericles", ["Athens", "Sparta", "Corinth", "Delphi", "Knossos"]),
    ("Babylonians", "Hammurabi", ["Babylon", "Ur", "Nineveh", "Akkad", "Eridu"]),
    ("Germans", "Bismarck", ["Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt"]),
    ("Chinese", "Qin Shi Huang", ["Beijing", "Shanghai", "Xi'an", "Nanjing", "Guangzhou"]),
    ("English", "Elizabeth", ["London", "York", "Canterbury", "Nottingham", "Oxford"]),
    ("French", "Napoleon", ["Paris", "Orleans", "Lyon", "Marseille", "Rouen"]),
    ("Mongols", "Genghis Khan", ["Karakorum", "Samarkand", "Bukhara", "Turfan", "Kashgar"]),
    ("Vikings", "Ragnar", ["Stockholm", "Uppsala", "Visby", "Aarhus", "Birka"]),
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


class FreeCivGame:
    """Simulates a complete FreeCiv game"""

    def __init__(self, ai_difficulty: int = 1):
        """
        Initialize game
        ai_difficulty: 1-10, affects opponent strength
        """
        self.ai_difficulty = ai_difficulty
        self.current_year = -4000  # Start in 4000 BC
        self.max_turns = 400
        self.current_turn = 0

        # Select civilizations
        player_civ_data = random.choice(CIVILIZATIONS)
        opponent_civ_data = random.choice([c for c in CIVILIZATIONS if c != player_civ_data])

        # Create player civilization
        self.player = Civilization(
            name=player_civ_data[0],
            leader=player_civ_data[1],
            cities=[City(player_civ_data[2][0], 1, ["Palace"], "Settler")],
            technology_level=1,
            military_power=10,
            gold=50,
            culture=0
        )

        # Create opponent civilization
        self.opponent = Civilization(
            name=opponent_civ_data[0],
            leader=opponent_civ_data[1],
            cities=[City(opponent_civ_data[2][0], 1, ["Palace"], "Settler")],
            technology_level=ai_difficulty,  # Stronger AI has more techs
            military_power=10 * ai_difficulty,
            gold=50 * ai_difficulty,
            culture=0
        )

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

        # Player development (basic simulation)
        for city in self.player.cities:
            city.population += random.randint(0, 1)
            if random.random() < 0.1 and len(city.buildings) < 5:
                city.buildings.append(random.choice(BUILDINGS))

        # Opponent development (scales with AI difficulty)
        for city in self.opponent.cities:
            city.population += random.randint(0, self.ai_difficulty // 3 + 1)
            if random.random() < 0.15 and len(city.buildings) < 5:
                city.buildings.append(random.choice(BUILDINGS))

        # City growth
        if random.random() < 0.05 and len(self.player.cities) < 5:
            civ_data = next(c for c in CIVILIZATIONS if c[0] == self.player.name)
            city_name = civ_data[2][len(self.player.cities)]
            self.player.cities.append(City(city_name, 1, [], "Warrior"))

        if random.random() < 0.07 and len(self.opponent.cities) < 5:
            civ_data = next(c for c in CIVILIZATIONS if c[0] == self.opponent.name)
            city_name = civ_data[2][len(self.opponent.cities)]
            self.opponent.cities.append(City(city_name, 1, [], "Warrior"))

        # Tech advancement
        if random.random() < 0.1:
            self.player.technology_level += 1
        if random.random() < 0.12:
            self.opponent.technology_level += 1

        # Military power
        self.player.military_power += random.randint(0, 5)
        self.opponent.military_power += random.randint(0, 5 + self.ai_difficulty)

        # Culture
        self.player.culture += len(self.player.cities) * 2
        self.opponent.culture += len(self.opponent.cities) * (2 + self.ai_difficulty // 3)

    def check_victory(self) -> Tuple[bool, bool, VictoryType]:
        """
        Check for victory conditions
        Returns: (game_over, player_won, victory_type)
        """
        # Defeat: Lost all cities
        if len(self.player.cities) == 0:
            return (True, False, VictoryType.DEFEAT)
        if len(self.opponent.cities) == 0:
            return (True, True, VictoryType.MILITARY)

        # Space Race: High tech level
        if self.player.technology_level >= 20:
            return (True, True, VictoryType.SPACE_RACE)
        if self.opponent.technology_level >= 20:
            return (True, False, VictoryType.SPACE_RACE)

        # Time limit: Year 2050
        if self.current_year >= 2050:
            player_score = (self.player.total_population * 10 +
                          self.player.culture +
                          self.player.technology_level * 50)
            opponent_score = (self.opponent.total_population * 10 +
                            self.opponent.culture +
                            self.opponent.technology_level * 50)
            return (True, player_score > opponent_score, VictoryType.TIME_LIMIT)

        # Max turns
        if self.current_turn >= self.max_turns:
            player_score = (self.player.total_population * 10 +
                          self.player.culture +
                          self.player.technology_level * 50)
            opponent_score = (self.opponent.total_population * 10 +
                            self.opponent.culture +
                            self.opponent.technology_level * 50)
            return (True, player_score > opponent_score, VictoryType.TIME_LIMIT)

        return (False, False, None)

    def play_game(self, verbose=False) -> Dict:
        """
        Play a complete game
        Returns: game statistics
        """
        if verbose:
            print(f"\n🏛️  NEW GAME: {self.player.name} ({self.player.leader}) vs "
                  f"{self.opponent.name} ({self.opponent.leader})")
            print(f"Starting year: {self.format_year()}")
            print(f"AI Difficulty: {self.ai_difficulty}/10\n")

        while True:
            self.simulate_turn()

            game_over, player_won, victory_type = self.check_victory()

            if game_over:
                break

        # Game statistics
        result = {
            'player_civ': self.player.name,
            'opponent_civ': self.opponent.name,
            'player_leader': self.player.leader,
            'opponent_leader': self.opponent.leader,
            'winner': self.player.name if player_won else self.opponent.name,
            'victory_type': victory_type.value,
            'final_year': self.format_year(),
            'turns_played': self.current_turn,
            'player_cities': self.player.total_cities,
            'opponent_cities': self.opponent.total_cities,
            'player_population': self.player.total_population,
            'opponent_population': self.opponent.total_population,
            'player_tech_level': self.player.technology_level,
            'opponent_tech_level': self.opponent.technology_level,
            'player_culture': self.player.culture,
            'opponent_culture': self.opponent.culture,
            'player_won': player_won,
            'ai_difficulty': self.ai_difficulty
        }

        if verbose:
            self._print_results(result)

        return result

    def _print_results(self, result: Dict):
        """Print detailed game results"""
        print("="*70)
        print(f"🏆 GAME COMPLETE: {result['victory_type']} Victory!")
        print("="*70)
        print(f"Winner: {result['winner']}")
        print(f"Final Year: {result['final_year']} (Turn {result['turns_played']})")
        print()
        print("Final Standings:")
        print("-"*70)
        print(f"{'Civilization':<20} {'Cities':<8} {'Pop':<8} {'Tech':<8} {'Culture':<10}")
        print("-"*70)
        print(f"{result['player_civ']:<20} {result['player_cities']:<8} "
              f"{result['player_population']:<8} {result['player_tech_level']:<8} "
              f"{result['player_culture']:<10}")
        print(f"{result['opponent_civ']:<20} {result['opponent_cities']:<8} "
              f"{result['opponent_population']:<8} {result['opponent_tech_level']:<8} "
              f"{result['opponent_culture']:<10}")
        print("-"*70)
        print()


if __name__ == "__main__":
    # Test the simulator
    print("Testing FreeCiv Simulator\n")

    for difficulty in [1, 3, 5, 8]:
        print(f"\n{'='*70}")
        print(f"Testing AI Difficulty: {difficulty}/10")
        print('='*70)

        game = FreeCivGame(ai_difficulty=difficulty)
        result = game.play_game(verbose=True)
