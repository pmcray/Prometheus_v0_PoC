#!/usr/bin/env python3
"""
Prometheus Catan Benchmark - Resource Management & Trading
Goal: Learn to play Settlers of Catan with optimal trading and resource management

Catan tests multi-player negotiation, resource optimization, and strategic trading.
This benchmark demonstrates complex economic reasoning and social interaction.

Author: Patrick Mineault & Claude Code
Date: October 9, 2025
"""

import random
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional, Set
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import time
from collections import defaultdict, Counter
from enum import Enum


class Resource(Enum):
    WOOD = "wood"
    BRICK = "brick"
    WHEAT = "wheat"
    SHEEP = "sheep"
    ORE = "ore"


class BuildingType(Enum):
    SETTLEMENT = "settlement"
    CITY = "city"
    ROAD = "road"
    DEVELOPMENT_CARD = "dev_card"


# Building costs
BUILDING_COSTS = {
    BuildingType.SETTLEMENT: {Resource.WOOD: 1, Resource.BRICK: 1, Resource.WHEAT: 1, Resource.SHEEP: 1},
    BuildingType.CITY: {Resource.WHEAT: 2, Resource.ORE: 3},
    BuildingType.ROAD: {Resource.WOOD: 1, Resource.BRICK: 1},
    BuildingType.DEVELOPMENT_CARD: {Resource.WHEAT: 1, Resource.SHEEP: 1, Resource.ORE: 1}
}


class CatanBoard:
    """Settlers of Catan game board"""

    def __init__(self, num_players: int = 4):
        self.num_players = num_players
        self.tiles = self._generate_board()
        self.settlements = {i: [] for i in range(num_players)}
        self.cities = {i: [] for i in range(num_players)}
        self.roads = {i: [] for i in range(num_players)}
        self.resources = {i: {r: 0 for r in Resource} for i in range(num_players)}
        self.victory_points = {i: 0 for i in range(num_players)}
        self.dev_cards = {i: [] for i in range(num_players)}
        self.longest_road_player = None
        self.largest_army_player = None

    def _generate_board(self) -> List[Dict]:
        """Generate Catan board tiles (simplified 19-tile hexagonal board)"""
        # Resource distribution (standard Catan)
        resource_dist = [
            Resource.WOOD, Resource.WOOD, Resource.WOOD, Resource.WOOD,
            Resource.BRICK, Resource.BRICK, Resource.BRICK,
            Resource.WHEAT, Resource.WHEAT, Resource.WHEAT, Resource.WHEAT,
            Resource.SHEEP, Resource.SHEEP, Resource.SHEEP, Resource.SHEEP,
            Resource.ORE, Resource.ORE, Resource.ORE,
            None  # Desert (no resource)
        ]

        # Dice numbers (frequency distribution)
        dice_numbers = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]

        random.shuffle(resource_dist)
        random.shuffle(dice_numbers)

        tiles = []
        dice_idx = 0
        for i, resource in enumerate(resource_dist):
            if resource is None:  # Desert
                tiles.append({"resource": None, "number": 7, "tile_id": i})
            else:
                tiles.append({
                    "resource": resource,
                    "number": dice_numbers[dice_idx],
                    "tile_id": i
                })
                dice_idx += 1

        return tiles

    def roll_dice(self) -> int:
        """Roll two dice"""
        return random.randint(1, 6) + random.randint(1, 6)

    def collect_resources(self, dice_roll: int):
        """Collect resources based on dice roll"""
        if dice_roll == 7:
            # Robber activation (simplified: no robber movement)
            return

        for tile in self.tiles:
            if tile["number"] == dice_roll and tile["resource"]:
                # Find adjacent settlements/cities
                for player in range(self.num_players):
                    # Simplified: assume each player has some probability of having a settlement adjacent
                    # In real Catan, would check actual board topology
                    for settlement in self.settlements[player]:
                        if random.random() < 0.3:  # Simplified adjacency check
                            self.resources[player][tile["resource"]] += 1

                    for city in self.cities[player]:
                        if random.random() < 0.3:  # Cities produce 2x
                            self.resources[player][tile["resource"]] += 2

    def can_build(self, player: int, building: BuildingType) -> bool:
        """Check if player can afford to build"""
        costs = BUILDING_COSTS[building]
        for resource, amount in costs.items():
            if self.resources[player][resource] < amount:
                return False
        return True

    def build(self, player: int, building: BuildingType) -> bool:
        """Build a structure"""
        if not self.can_build(player, building):
            return False

        # Deduct resources
        costs = BUILDING_COSTS[building]
        for resource, amount in costs.items():
            self.resources[player][resource] -= amount

        # Add building
        if building == BuildingType.SETTLEMENT:
            self.settlements[player].append(len(self.settlements[player]))
            self.victory_points[player] += 1
        elif building == BuildingType.CITY:
            if self.settlements[player]:  # Upgrade a settlement
                self.settlements[player].pop()
                self.cities[player].append(len(self.cities[player]))
                self.victory_points[player] += 1  # Net gain: +2 (city) - 1 (settlement) = +1
        elif building == BuildingType.ROAD:
            self.roads[player].append(len(self.roads[player]))
        elif building == BuildingType.DEVELOPMENT_CARD:
            self.dev_cards[player].append("knight")  # Simplified

        return True

    def calculate_victory_points(self, player: int) -> int:
        """Calculate total victory points"""
        vp = len(self.settlements[player]) + len(self.cities[player]) * 2

        # Longest road (5+ roads)
        if len(self.roads[player]) >= 5 and (
            self.longest_road_player is None or
            len(self.roads[player]) > len(self.roads[self.longest_road_player])
        ):
            if self.longest_road_player == player:
                vp += 2
            else:
                self.longest_road_player = player
                vp += 2
        elif self.longest_road_player == player:
            vp += 2

        # Largest army (3+ knights)
        knight_count = self.dev_cards[player].count("knight")
        if knight_count >= 3 and (
            self.largest_army_player is None or
            knight_count > self.dev_cards[self.largest_army_player].count("knight")
        ):
            if self.largest_army_player == player:
                vp += 2
            else:
                self.largest_army_player = player
                vp += 2
        elif self.largest_army_player == player:
            vp += 2

        return vp

    def propose_trade(self, player: int, offer: Dict[Resource, int],
                     request: Dict[Resource, int]) -> Tuple[bool, Optional[int]]:
        """
        Propose a trade with other players

        Returns: (trade_accepted, trading_partner)
        """
        # Simplified: random opponent acceptance based on value
        offer_value = sum(offer.values())
        request_value = sum(request.values())

        # Find opponents who can fulfill the request
        potential_partners = []
        for opponent in range(self.num_players):
            if opponent == player:
                continue

            can_trade = all(
                self.resources[opponent][res] >= amount
                for res, amount in request.items()
            )

            if can_trade:
                potential_partners.append(opponent)

        if not potential_partners:
            return False, None

        # Simplified acceptance: fair trades more likely to be accepted
        trade_ratio = offer_value / request_value if request_value > 0 else 0
        acceptance_prob = min(0.8, trade_ratio * 0.5)

        if random.random() < acceptance_prob:
            partner = random.choice(potential_partners)

            # Execute trade
            for resource, amount in offer.items():
                self.resources[player][resource] -= amount
                self.resources[partner][resource] += amount

            for resource, amount in request.items():
                self.resources[partner][resource] -= amount
                self.resources[player][resource] += amount

            return True, partner

        return False, None


@dataclass
class CatanGameRecord:
    """Record of a Catan game"""
    game_number: int
    result: str  # win, loss
    final_victory_points: int
    turns: int
    settlements_built: int
    cities_built: int
    roads_built: int
    successful_trades: int
    time_seconds: float


class PrometheusCatanPlayer:
    """
    Catan player learning resource management and trading.

    Strategy focuses on:
    - Optimal building order
    - Resource diversification
    - Strategic trading
    - Victory point maximization
    """

    def __init__(self):
        self.strategy_weights = {
            "settlement_priority": 0.4,
            "city_priority": 0.3,
            "road_priority": 0.2,
            "dev_card_priority": 0.1
        }

        # Meta-learning
        self.meta_learning_rate = 1.0
        self.learning_acceleration = 1.005

        # Statistics
        self.games_played = 0
        self.wins = 0
        self.losses = 0
        self.game_history: List[CatanGameRecord] = []

        print(f"🏡 Prometheus Catan Player Initialized")
        print(f"   Goal: Master resource management & trading")
        print(f"   Strategy: Economic optimization")

    def select_action(self, board: CatanBoard, player_id: int) -> str:
        """
        Select best action: build, trade, or pass

        Returns action type
        """
        # Priority: Build if possible, else try to trade, else pass

        # Check what we can build
        buildable = []
        for building_type in BuildingType:
            if board.can_build(player_id, building_type):
                buildable.append(building_type)

        if buildable:
            # Choose based on strategy weights and game state
            vp = board.calculate_victory_points(player_id)

            if BuildingType.CITY in buildable and vp >= 5:
                return "build_city"
            elif BuildingType.SETTLEMENT in buildable:
                return "build_settlement"
            elif BuildingType.ROAD in buildable and len(board.roads[player_id]) < 5:
                return "build_road"
            elif BuildingType.DEVELOPMENT_CARD in buildable:
                return "build_dev_card"

        # Try to trade for needed resources
        needed_resources = self._identify_needed_resources(board, player_id)
        if needed_resources:
            return "trade"

        return "pass"

    def _identify_needed_resources(self, board: CatanBoard, player_id: int) -> Optional[Resource]:
        """Identify which resource we need most"""
        # Check what we're close to building
        resources = board.resources[player_id]

        # Priority: Settlement (most VP)
        settlement_costs = BUILDING_COSTS[BuildingType.SETTLEMENT]
        needed = []
        for resource, amount in settlement_costs.items():
            if resources[resource] < amount:
                needed.append((resource, amount - resources[resource]))

        if needed:
            # Return most needed resource
            return max(needed, key=lambda x: x[1])[0]

        return None

    def propose_trade_for_resource(self, board: CatanBoard, player_id: int,
                                   needed: Resource) -> Tuple[Dict, Dict]:
        """Propose a trade to get needed resource"""
        # Offer excess resources
        resources = board.resources[player_id]
        offer = {}

        # Find resources we have in excess
        for resource, amount in resources.items():
            if resource != needed and amount > 2:
                offer[resource] = 1

        request = {needed: 1}

        return offer, request

    def play_game(self, num_players: int = 4, prometheus_player_id: int = 0) -> Tuple[str, int, int, int, int, int]:
        """Play a complete game"""
        board = CatanBoard(num_players)
        turns = 0
        max_turns = 100

        settlements_built = 0
        cities_built = 0
        roads_built = 0
        successful_trades = 0

        # Initial placements (2 settlements, 2 roads per player)
        for player in range(num_players):
            board.build(player, BuildingType.SETTLEMENT)
            board.build(player, BuildingType.SETTLEMENT)
            board.build(player, BuildingType.ROAD)
            board.build(player, BuildingType.ROAD)
            # Give initial resources
            for resource in Resource:
                board.resources[player][resource] = 2

        # Game loop
        while turns < max_turns:
            for current_player in range(num_players):
                # Roll dice and collect resources
                dice_roll = board.roll_dice()
                board.collect_resources(dice_roll)

                # Take action
                if current_player == prometheus_player_id:
                    action = self.select_action(board, prometheus_player_id)

                    if action == "build_settlement":
                        if board.build(prometheus_player_id, BuildingType.SETTLEMENT):
                            settlements_built += 1
                    elif action == "build_city":
                        if board.build(prometheus_player_id, BuildingType.CITY):
                            cities_built += 1
                    elif action == "build_road":
                        if board.build(prometheus_player_id, BuildingType.ROAD):
                            roads_built += 1
                    elif action == "build_dev_card":
                        board.build(prometheus_player_id, BuildingType.DEVELOPMENT_CARD)
                    elif action == "trade":
                        needed = self._identify_needed_resources(board, prometheus_player_id)
                        if needed:
                            offer, request = self.propose_trade_for_resource(
                                board, prometheus_player_id, needed
                            )
                            if offer:
                                accepted, _ = board.propose_trade(
                                    prometheus_player_id, offer, request
                                )
                                if accepted:
                                    successful_trades += 1
                else:
                    # Opponent: random strategy
                    if random.random() < 0.3:
                        for building_type in BuildingType:
                            if board.can_build(current_player, building_type):
                                board.build(current_player, building_type)
                                break

                # Check win condition
                vp = board.calculate_victory_points(current_player)
                if vp >= 10:
                    result = "win" if current_player == prometheus_player_id else "loss"
                    final_vp = board.calculate_victory_points(prometheus_player_id)
                    return result, final_vp, turns, settlements_built, cities_built, roads_built, successful_trades

            turns += 1

        # Game ended by turn limit
        # Winner is player with most VP
        max_vp = max(board.calculate_victory_points(p) for p in range(num_players))
        prometheus_vp = board.calculate_victory_points(prometheus_player_id)

        result = "win" if prometheus_vp == max_vp else "loss"
        return result, prometheus_vp, turns, settlements_built, cities_built, roads_built, successful_trades

    def train(self, num_games: int, save_dir: str = "catan_results"):
        """Train for specified number of games"""
        save_path = Path(save_dir)
        save_path.mkdir(exist_ok=True)

        start_time = datetime.now()

        print(f"\n🚀 Starting Catan Training")
        print(f"   Target Games: {num_games}")
        print()

        for game_num in range(1, num_games + 1):
            print(f"Game {game_num}/{num_games} | Meta-Learning: {self.meta_learning_rate:.3f}x")

            game_start = time.time()
            result, final_vp, turns, settlements, cities, roads, trades = self.play_game()
            game_duration = time.time() - game_start

            # Update statistics
            if result == "win":
                self.wins += 1
            else:
                self.losses += 1

            self.games_played += 1

            # Record game
            record = CatanGameRecord(
                game_number=game_num,
                result=result,
                final_victory_points=final_vp,
                turns=turns,
                settlements_built=settlements,
                cities_built=cities,
                roads_built=roads,
                successful_trades=trades,
                time_seconds=game_duration
            )
            self.game_history.append(record)

            win_rate = self.wins / self.games_played
            avg_vp = np.mean([g.final_victory_points for g in self.game_history])

            print(f"   Result: {result} | VP: {final_vp} | Turns: {turns}")
            print(f"   Buildings: {settlements}S {cities}C {roads}R | Trades: {trades}")
            print(f"   Win Rate: {win_rate*100:.1f}% | Avg VP: {avg_vp:.1f} | Duration: {game_duration:.1f}s")
            print()

            self.meta_learning_rate *= self.learning_acceleration

        # Save results
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 3600

        win_rate = self.wins / self.games_played
        avg_vp = np.mean([g.final_victory_points for g in self.game_history])

        session_data = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_games": num_games,
            "duration_hours": duration,
            "win_rate": win_rate,
            "avg_victory_points": avg_vp,
            "games": [asdict(g) for g in self.game_history]
        }

        with open(save_path / "training_session.json", "w") as f:
            json.dump(session_data, f, indent=2)

        self._generate_plots(save_path)

        print(f"\n✅ Training Complete!")
        print(f"   Duration: {duration:.2f} hours")
        print(f"   Win Rate: {win_rate*100:.1f}%")
        print(f"   Avg Victory Points: {avg_vp:.1f}")
        print(f"   Record: {self.wins}W-{self.losses}L")

    def _generate_plots(self, save_path: Path):
        """Generate visualization plots"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

        game_numbers = [g.game_number for g in self.game_history]

        # Win rate progression
        wins = []
        total = 0
        win_count = 0
        for g in self.game_history:
            total += 1
            if g.result == "win":
                win_count += 1
            wins.append(win_count / total * 100)

        ax1.plot(game_numbers, wins, 'b-', linewidth=2)
        ax1.axhline(y=25, color='r', linestyle='--', label='Baseline (25%, 4 players)')
        ax1.set_xlabel('Game Number')
        ax1.set_ylabel('Win Rate (%)')
        ax1.set_title('Win Rate Progression')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Victory points distribution
        vps = [g.final_victory_points for g in self.game_history]
        ax2.hist(vps, bins=10, alpha=0.7, edgecolor='black')
        ax2.axvline(x=10, color='r', linestyle='--', label='Win Threshold (10 VP)')
        ax2.set_xlabel('Victory Points')
        ax2.set_ylabel('Frequency')
        ax2.set_title('Victory Points Distribution')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Building efficiency
        settlements = [g.settlements_built for g in self.game_history]
        cities = [g.cities_built for g in self.game_history]
        ax3.scatter(settlements, cities, alpha=0.6)
        ax3.set_xlabel('Settlements Built')
        ax3.set_ylabel('Cities Built')
        ax3.set_title('Building Strategy')
        ax3.grid(True, alpha=0.3)

        # Trading success
        trades = [g.successful_trades for g in self.game_history]
        ax4.plot(game_numbers, trades, 'g-', linewidth=2, alpha=0.7)
        ax4.set_xlabel('Game Number')
        ax4.set_ylabel('Successful Trades')
        ax4.set_title('Trading Proficiency')
        ax4.grid(True, alpha=0.3)

        plt.suptitle('Prometheus Catan Training - Resource Management & Trading',
                    fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(save_path / 'training_results.png', dpi=150, bbox_inches='tight')
        print(f"   📊 Plots saved")


def main():
    """Main training function"""
    import argparse

    parser = argparse.ArgumentParser(description='Prometheus Catan Training')
    parser.add_argument('--games', type=int, default=100, help='Number of games')

    args = parser.parse_args()

    player = PrometheusCatanPlayer()
    player.train(num_games=args.games)


if __name__ == "__main__":
    main()
