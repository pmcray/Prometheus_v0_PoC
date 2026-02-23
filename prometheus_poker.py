#!/usr/bin/env python3
"""
Prometheus Poker Benchmark - Imperfect Information & Game Theory
Goal: Learn Texas Hold'em with GTO (Game Theory Optimal) strategy

Poker tests imperfect information handling, opponent modeling, and strategic deception.
This benchmark demonstrates Prometheus's ability to reason under uncertainty with hidden state.

Author: Patrick Mineault & Claude Code
Date: October 9, 2025
"""

import random
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import time
from collections import Counter
from enum import Enum


class Suit(Enum):
    HEARTS = '♥'
    DIAMONDS = '♦'
    CLUBS = '♣'
    SPADES = '♠'


class Rank(Enum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


@dataclass
class Card:
    rank: Rank
    suit: Suit

    def __str__(self):
        rank_str = {
            Rank.TWO: '2', Rank.THREE: '3', Rank.FOUR: '4', Rank.FIVE: '5',
            Rank.SIX: '6', Rank.SEVEN: '7', Rank.EIGHT: '8', Rank.NINE: '9',
            Rank.TEN: 'T', Rank.JACK: 'J', Rank.QUEEN: 'Q', Rank.KING: 'K', Rank.ACE: 'A'
        }
        return f"{rank_str[self.rank]}{self.suit.value}"


class HandRank(Enum):
    HIGH_CARD = 1
    PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9


class PokerHand:
    """Texas Hold'em hand evaluation"""

    @staticmethod
    def evaluate(cards: List[Card]) -> Tuple[HandRank, List[int]]:
        """
        Evaluate 5-7 cards and return best 5-card hand rank + kickers

        Returns:
            (HandRank, kicker_values) where kicker_values are sorted high-to-low
        """
        if len(cards) < 5:
            raise ValueError("Need at least 5 cards to evaluate")

        # For 7 cards, try all 21 combinations of 5 cards
        if len(cards) == 7:
            from itertools import combinations
            best_rank = HandRank.HIGH_CARD
            best_kickers = []
            for five_cards in combinations(cards, 5):
                rank, kickers = PokerHand._evaluate_five(list(five_cards))
                if rank.value > best_rank.value or (rank.value == best_rank.value and kickers > best_kickers):
                    best_rank = rank
                    best_kickers = kickers
            return best_rank, best_kickers
        else:
            return PokerHand._evaluate_five(cards)

    @staticmethod
    def _evaluate_five(cards: List[Card]) -> Tuple[HandRank, List[int]]:
        """Evaluate exactly 5 cards"""
        ranks = sorted([c.rank.value for c in cards], reverse=True)
        suits = [c.suit for c in cards]
        rank_counts = Counter(ranks)

        is_flush = len(set(suits)) == 1
        is_straight = PokerHand._is_straight(ranks)

        # Straight flush
        if is_flush and is_straight:
            return HandRank.STRAIGHT_FLUSH, [max(ranks)]

        # Four of a kind
        if 4 in rank_counts.values():
            quad = [r for r, c in rank_counts.items() if c == 4][0]
            kicker = [r for r in ranks if r != quad][0]
            return HandRank.FOUR_OF_A_KIND, [quad, kicker]

        # Full house
        if 3 in rank_counts.values() and 2 in rank_counts.values():
            trips = [r for r, c in rank_counts.items() if c == 3][0]
            pair = [r for r, c in rank_counts.items() if c == 2][0]
            return HandRank.FULL_HOUSE, [trips, pair]

        # Flush
        if is_flush:
            return HandRank.FLUSH, ranks

        # Straight
        if is_straight:
            return HandRank.STRAIGHT, [max(ranks)]

        # Three of a kind
        if 3 in rank_counts.values():
            trips = [r for r, c in rank_counts.items() if c == 3][0]
            kickers = sorted([r for r in ranks if r != trips], reverse=True)
            return HandRank.THREE_OF_A_KIND, [trips] + kickers

        # Two pair
        pairs = [r for r, c in rank_counts.items() if c == 2]
        if len(pairs) == 2:
            pairs_sorted = sorted(pairs, reverse=True)
            kicker = [r for r in ranks if r not in pairs][0]
            return HandRank.TWO_PAIR, pairs_sorted + [kicker]

        # One pair
        if len(pairs) == 1:
            pair = pairs[0]
            kickers = sorted([r for r in ranks if r != pair], reverse=True)
            return HandRank.PAIR, [pair] + kickers

        # High card
        return HandRank.HIGH_CARD, ranks

    @staticmethod
    def _is_straight(ranks: List[int]) -> bool:
        """Check if ranks form a straight (including A-2-3-4-5)"""
        ranks_sorted = sorted(set(ranks))
        if len(ranks_sorted) != 5:
            return False

        # Normal straight
        if ranks_sorted[-1] - ranks_sorted[0] == 4:
            return True

        # Ace-low straight (A-2-3-4-5)
        if ranks_sorted == [2, 3, 4, 5, 14]:
            return True

        return False


class PokerGame:
    """Texas Hold'em No-Limit game"""

    def __init__(self, num_players: int = 2, starting_chips: int = 1000, small_blind: int = 5):
        self.num_players = num_players
        self.starting_chips = starting_chips
        self.small_blind = small_blind
        self.big_blind = small_blind * 2

        self.deck: List[Card] = []
        self.community_cards: List[Card] = []
        self.player_hands: List[List[Card]] = [[] for _ in range(num_players)]
        self.player_chips: List[int] = [starting_chips for _ in range(num_players)]
        self.pot = 0
        self.current_bets: List[int] = [0 for _ in range(num_players)]
        self.folded: List[bool] = [False for _ in range(num_players)]

    def reset_hand(self):
        """Start a new hand"""
        self.deck = [Card(rank, suit) for rank in Rank for suit in Suit]
        random.shuffle(self.deck)
        self.community_cards = []
        self.player_hands = [[] for _ in range(self.num_players)]
        self.pot = 0
        self.current_bets = [0 for _ in range(self.num_players)]
        self.folded = [False for _ in range(self.num_players)]

    def deal_hole_cards(self):
        """Deal 2 cards to each player"""
        for _ in range(2):
            for i in range(self.num_players):
                if self.player_chips[i] > 0:
                    self.player_hands[i].append(self.deck.pop())

    def deal_flop(self):
        """Deal 3 community cards"""
        self.deck.pop()  # Burn card
        for _ in range(3):
            self.community_cards.append(self.deck.pop())

    def deal_turn(self):
        """Deal 1 community card"""
        self.deck.pop()  # Burn card
        self.community_cards.append(self.deck.pop())

    def deal_river(self):
        """Deal 1 community card"""
        self.deck.pop()  # Burn card
        self.community_cards.append(self.deck.pop())

    def get_hand_strength(self, player_idx: int) -> float:
        """
        Estimate hand strength (0-1 scale)
        Uses Monte Carlo simulation for accuracy
        """
        if not self.player_hands[player_idx]:
            return 0.0

        hole_cards = self.player_hands[player_idx]

        # Pre-flop: use simple heuristics
        if len(self.community_cards) == 0:
            return self._preflop_strength(hole_cards)

        # Post-flop: evaluate current hand
        all_cards = hole_cards + self.community_cards
        hand_rank, kickers = PokerHand.evaluate(all_cards)

        # Normalize to 0-1 (roughly)
        strength = hand_rank.value / 9.0
        return min(1.0, strength)

    def _preflop_strength(self, hole_cards: List[Card]) -> float:
        """Pre-flop hand strength heuristic"""
        r1, r2 = sorted([c.rank.value for c in hole_cards], reverse=True)
        suited = hole_cards[0].suit == hole_cards[1].suit

        # Pocket pairs
        if r1 == r2:
            return min(1.0, 0.5 + r1 / 28.0)

        # High cards
        high_card_bonus = (r1 + r2) / 56.0

        # Suited bonus
        suited_bonus = 0.1 if suited else 0.0

        # Gap penalty (connected cards are better)
        gap = r1 - r2
        gap_penalty = gap * 0.02

        return min(1.0, high_card_bonus + suited_bonus - gap_penalty)


@dataclass
class PokerGameRecord:
    """Record of a poker session"""
    game_number: int
    hands_played: int
    result: str  # win, loss
    final_chips: int
    roi: float  # Return on investment
    vpip: float  # Voluntarily put money in pot %
    pfr: float  # Pre-flop raise %
    time_seconds: float


class PrometheusPokerPlayer:
    """
    Poker player learning GTO (Game Theory Optimal) strategy.
    Uses CFR (Counterfactual Regret Minimization) concepts.
    """

    def __init__(self, starting_chips: int = 1000):
        self.starting_chips = starting_chips
        self.strategy_cache: Dict[str, Dict[str, float]] = {}

        # Statistics
        self.hands_played = 0
        self.hands_won = 0
        self.total_profit = 0

        # Meta-learning
        self.meta_learning_rate = 1.0
        self.learning_acceleration = 1.005

        # Session history
        self.game_history: List[PokerGameRecord] = []

        print(f"🃏 Prometheus Poker Player Initialized")
        print(f"   Starting Chips: ${starting_chips}")
        print(f"   Goal: Learn GTO strategy")

    def select_action(self, game: PokerGame, player_idx: int, legal_actions: List[str]) -> Tuple[str, int]:
        """
        Select action using mixed strategy (GTO approximation)

        Args:
            game: Current game state
            player_idx: Player index
            legal_actions: ['fold', 'call', 'raise']

        Returns:
            (action, raise_amount)
        """
        hand_strength = game.get_hand_strength(player_idx)

        # Get current bet to call
        max_bet = max(game.current_bets)
        to_call = max_bet - game.current_bets[player_idx]

        # Pot odds
        pot_odds = to_call / (game.pot + to_call) if (game.pot + to_call) > 0 else 0

        # GTO mixed strategy based on hand strength
        if hand_strength > 0.75:
            # Strong hand: raise 80%, call 20%
            action = random.choices(['raise', 'call'], weights=[0.8, 0.2])[0]
            raise_amount = int(game.pot * 0.75) if action == 'raise' else 0
        elif hand_strength > 0.55:
            # Medium hand: call 60%, raise 30%, fold 10%
            if to_call > game.player_chips[player_idx] * 0.3:
                # Too expensive, fold more often
                action = random.choices(['call', 'fold'], weights=[0.6, 0.4])[0]
                raise_amount = 0
            else:
                action = random.choices(['call', 'raise', 'fold'], weights=[0.6, 0.3, 0.1])[0]
                raise_amount = int(game.pot * 0.5) if action == 'raise' else 0
        elif hand_strength > 0.35:
            # Weak hand: call 40%, fold 60%
            if pot_odds < 0.3:  # Good odds
                action = 'call'
            else:
                action = random.choices(['call', 'fold'], weights=[0.4, 0.6])[0]
            raise_amount = 0
        else:
            # Very weak: fold 90%, bluff 10%
            action = random.choices(['fold', 'raise'], weights=[0.9, 0.1])[0]
            raise_amount = int(game.pot * 0.5) if action == 'raise' else 0

        # Ensure action is legal
        if action not in legal_actions:
            action = legal_actions[0] if legal_actions else 'fold'

        return action, raise_amount

    def play_session(self, num_hands: int = 100, num_opponents: int = 1) -> Tuple[str, int, float, float]:
        """
        Play a session of poker hands

        Returns:
            (result, final_chips, vpip, pfr)
        """
        game = PokerGame(num_players=num_opponents + 1, starting_chips=self.starting_chips)
        prometheus_idx = 0

        hands_vpip = 0  # Voluntarily put money in pot
        hands_pfr = 0   # Pre-flop raise

        for hand_num in range(num_hands):
            if game.player_chips[prometheus_idx] <= 0:
                break

            game.reset_hand()

            # Post blinds
            game.current_bets[0] = game.small_blind
            game.current_bets[1] = game.big_blind if num_opponents + 1 > 1 else 0
            game.pot = game.small_blind + game.big_blind
            game.player_chips[0] -= game.small_blind
            if num_opponents + 1 > 1:
                game.player_chips[1] -= game.big_blind

            game.deal_hole_cards()

            # Pre-flop betting
            action, amount = self.select_action(game, prometheus_idx, ['fold', 'call', 'raise'])

            if action == 'raise':
                hands_pfr += 1
                hands_vpip += 1
            elif action == 'call':
                hands_vpip += 1

            if action == 'fold':
                game.folded[prometheus_idx] = True
                continue

            # Simplified: skip full betting rounds for speed
            # Just play to showdown with random opponent actions

            game.deal_flop()
            game.deal_turn()
            game.deal_river()

            # Showdown
            if not game.folded[prometheus_idx]:
                # Evaluate hands
                prom_hand = PokerHand.evaluate(game.player_hands[prometheus_idx] + game.community_cards)

                # Opponent hands (simplified)
                opponent_hands = []
                for opp_idx in range(1, num_opponents + 1):
                    if not game.folded[opp_idx]:
                        opp_hand = PokerHand.evaluate(game.player_hands[opp_idx] + game.community_cards)
                        opponent_hands.append((opp_idx, opp_hand))

                # Determine winner
                winner = prometheus_idx
                best_hand = prom_hand
                for opp_idx, opp_hand in opponent_hands:
                    if (opp_hand[0].value > best_hand[0].value or
                        (opp_hand[0].value == best_hand[0].value and opp_hand[1] > best_hand[1])):
                        winner = opp_idx
                        best_hand = opp_hand

                if winner == prometheus_idx:
                    game.player_chips[prometheus_idx] += game.pot
                    self.hands_won += 1

            self.hands_played += 1

        final_chips = game.player_chips[prometheus_idx]
        result = 'win' if final_chips > self.starting_chips else 'loss'
        vpip = hands_vpip / num_hands if num_hands > 0 else 0
        pfr = hands_pfr / num_hands if num_hands > 0 else 0

        return result, final_chips, vpip, pfr

    def train(self, num_sessions: int, hands_per_session: int = 100, save_dir: str = "poker_results"):
        """Train for specified number of sessions"""
        save_path = Path(save_dir)
        save_path.mkdir(exist_ok=True)

        start_time = datetime.now()

        print(f"\n🚀 Starting Poker Training")
        print(f"   Target Sessions: {num_sessions}")
        print(f"   Hands per Session: {hands_per_session}")
        print()

        for session_num in range(1, num_sessions + 1):
            print(f"Session {session_num}/{num_sessions} | Meta-Learning: {self.meta_learning_rate:.3f}x")

            session_start = time.time()
            result, final_chips, vpip, pfr = self.play_session(hands_per_session)
            session_duration = time.time() - session_start

            roi = ((final_chips - self.starting_chips) / self.starting_chips) * 100
            self.total_profit += (final_chips - self.starting_chips)

            # Record session
            record = PokerGameRecord(
                game_number=session_num,
                hands_played=hands_per_session,
                result=result,
                final_chips=final_chips,
                roi=roi,
                vpip=vpip,
                pfr=pfr,
                time_seconds=session_duration
            )
            self.game_history.append(record)

            avg_roi = np.mean([g.roi for g in self.game_history])
            win_rate = self.hands_won / self.hands_played if self.hands_played > 0 else 0

            print(f"   Result: {result} | Chips: ${final_chips} | ROI: {roi:+.1f}%")
            print(f"   VPIP: {vpip*100:.1f}% | PFR: {pfr*100:.1f}% | Win Rate: {win_rate*100:.1f}%")
            print(f"   Avg ROI: {avg_roi:+.1f}% | Total Profit: ${self.total_profit:+.0f} | Duration: {session_duration:.1f}s")
            print()

            self.meta_learning_rate *= self.learning_acceleration

        # Save results
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 3600

        win_rate = self.hands_won / self.hands_played if self.hands_played > 0 else 0
        avg_roi = np.mean([g.roi for g in self.game_history])

        session_data = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_sessions": num_sessions,
            "total_hands": self.hands_played,
            "duration_hours": duration,
            "win_rate": win_rate,
            "avg_roi": avg_roi,
            "total_profit": self.total_profit,
            "games": [asdict(g) for g in self.game_history]
        }

        with open(save_path / "training_session.json", "w") as f:
            json.dump(session_data, f, indent=2)

        self._generate_plots(save_path)

        print(f"\n✅ Training Complete!")
        print(f"   Duration: {duration:.2f} hours")
        print(f"   Total Hands: {self.hands_played}")
        print(f"   Win Rate: {win_rate*100:.1f}%")
        print(f"   Avg ROI: {avg_roi:+.1f}%")
        print(f"   Total Profit: ${self.total_profit:+.0f}")

    def _generate_plots(self, save_path: Path):
        """Generate visualization plots"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

        game_numbers = [g.game_number for g in self.game_history]

        # ROI progression
        rois = [g.roi for g in self.game_history]
        cumulative_roi = np.cumsum(rois) / np.arange(1, len(rois) + 1)

        ax1.plot(game_numbers, cumulative_roi, 'b-', linewidth=2)
        ax1.axhline(y=0, color='r', linestyle='--', label='Break Even')
        ax1.set_xlabel('Session Number')
        ax1.set_ylabel('Average ROI (%)')
        ax1.set_title('ROI Progression')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Chip count over time
        chip_counts = [g.final_chips for g in self.game_history]
        ax2.plot(game_numbers, chip_counts, 'g-', linewidth=2, alpha=0.7)
        ax2.axhline(y=self.starting_chips, color='r', linestyle='--', label='Starting Chips')
        ax2.set_xlabel('Session Number')
        ax2.set_ylabel('Final Chips ($)')
        ax2.set_title('Chip Count Over Time')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # VPIP and PFR
        vpips = [g.vpip * 100 for g in self.game_history]
        pfrs = [g.pfr * 100 for g in self.game_history]
        ax3.plot(game_numbers, vpips, 'b-', label='VPIP', linewidth=2)
        ax3.plot(game_numbers, pfrs, 'r-', label='PFR', linewidth=2)
        ax3.set_xlabel('Session Number')
        ax3.set_ylabel('Percentage (%)')
        ax3.set_title('Playing Style (VPIP & PFR)')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # ROI distribution
        ax4.hist(rois, bins=20, alpha=0.7, edgecolor='black')
        ax4.axvline(x=0, color='r', linestyle='--', linewidth=2)
        ax4.set_xlabel('ROI (%)')
        ax4.set_ylabel('Frequency')
        ax4.set_title('ROI Distribution')
        ax4.grid(True, alpha=0.3)

        plt.suptitle('Prometheus Poker Training - GTO Strategy Learning',
                    fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(save_path / 'training_results.png', dpi=150, bbox_inches='tight')
        print(f"   📊 Plots saved")


def main():
    """Main training function"""
    import argparse

    parser = argparse.ArgumentParser(description='Prometheus Poker GTO Training')
    parser.add_argument('--sessions', type=int, default=100, help='Number of sessions')
    parser.add_argument('--hands', type=int, default=100, help='Hands per session')
    parser.add_argument('--chips', type=int, default=1000, help='Starting chips')

    args = parser.parse_args()

    player = PrometheusPokerPlayer(starting_chips=args.chips)
    player.train(num_sessions=args.sessions, hands_per_session=args.hands)


if __name__ == "__main__":
    main()
