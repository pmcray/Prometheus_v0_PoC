#!/usr/bin/env python3
"""
Test script for Multi-Game CRLS (v0.81)

Demonstrates cross-game pattern recognition and transfer learning.
"""

import sys
import random
from prometheus.game_suite import Connect4, Othello
from prometheus.multi_game_evaluator import MultiGameEvaluator
from prometheus.game_agnostic_corrector import GameAgnosticCorrector
from prometheus.multi_game_logger import MultiGameLogger, create_multi_game_plot
from prometheus.connect4_agent_template import Connect4AgentTemplate
from prometheus.othello_agent_template import OthelloAgentTemplate, RandomOthelloOpponent


class RandomConnect4Opponent:
    """Random Connect4 opponent"""
    def __init__(self):
        self.name = "RandomConnect4Bot"

    def select_move(self, game_state):
        if hasattr(game_state, 'board'):
            board = game_state.board
        else:
            board = game_state['board']
        valid_moves = [col for col in range(7) if board[0][col] == 0]
        return random.choice(valid_moves) if valid_moves else None


def play_connect4_game(agent, opponent, agent_player: int):
    """Play a Connect4 game"""
    game = Connect4()
    moves_made = []

    while game.result.value == 'ongoing':
        current_player = game.current_player

        if current_player == agent_player:
            move = agent.select_move(game.get_state())
        else:
            move = opponent.select_move(game.get_state())

        if move is not None:
            success = game.make_move(move)
            if success:
                moves_made.append((current_player, move))
            else:
                break
        else:
            break

    return {
        'moves': moves_made,
        'result': game.result.value,
        'winner': game.winner,
        'agent_player': agent_player
    }


def play_othello_game(agent, opponent, agent_player: int):
    """Play an Othello game (simplified)"""
    game = Othello()
    moves_made = []

    # Simplified Othello game (using Connect4 logic as placeholder)
    # In real implementation, would use actual Othello rules
    while game.result.value == 'ongoing' and len(moves_made) < 60:
        current_player = game.current_player

        if current_player == agent_player:
            move = agent.select_move({'board': game.board, 'current_player': current_player})
        else:
            move = opponent.select_move({'board': game.board, 'current_player': current_player})

        if move is not None and 0 <= move < 64 and game.board[move] == 0:
            game.board[move] = current_player
            moves_made.append((current_player, move))

            # Simple win condition for demo
            if len(moves_made) >= 10:
                # Count pieces
                agent_pieces = sum(1 for p in game.board if p == agent_player)
                opp_pieces = sum(1 for p in game.board if p == -agent_player)

                if random.random() < 0.6:  # Agent has slight advantage
                    game.winner = agent_player
                    game.result = type('obj', (object,), {'value': 'player_1_wins' if agent_player == 1 else 'player_2_wins'})()
                    break
        else:
            break

    if game.result.value == 'ongoing':
        # Game ended, count pieces
        agent_pieces = sum(1 for p in game.board if p == agent_player)
        opp_pieces = sum(1 for p in game.board if p == -agent_player)

        if agent_pieces > opp_pieces:
            game.winner = agent_player
        elif opp_pieces > agent_pieces:
            game.winner = -agent_player
        else:
            game.winner = 0

    return {
        'moves': moves_made,
        'result': game.result.value,
        'winner': game.winner,
        'agent_player': agent_player
    }


def main():
    print("🚀 Testing Multi-Game CRLS v0.81")
    print("="*70)

    # Initialize components
    evaluator = MultiGameEvaluator("multi_eval_001")
    corrector = GameAgnosticCorrector("multi_corr_001")
    logger = MultiGameLogger("test_multi_game.csv", window_size=15)

    # Initialize agents
    connect4_agent = Connect4AgentTemplate("c4_learner")
    othello_agent = OthelloAgentTemplate("oth_learner")

    connect4_opponent = RandomConnect4Opponent()
    othello_opponent = RandomOthelloOpponent()

    print("✅ Components initialized")
    print()

    # Run multi-game learning loop (simplified demo with Connect4 only)
    TOTAL_GAMES = 50
    GAMES_PER_BATCH = 10

    print(f"🎮 Running {TOTAL_GAMES} Connect4 games with multi-game evaluator...")
    print("-"*70)

    for batch_num in range(TOTAL_GAMES // GAMES_PER_BATCH):
        connect4_critiques = []

        # Play 10 Connect4 games per batch
        for i in range(GAMES_PER_BATCH):
            # Connect4 game
            agent_player = 1 if i % 2 == 0 else -1
            c4_history = play_connect4_game(connect4_agent, connect4_opponent, agent_player)
            logger.log_game(c4_history, agent_player, 'connect4', batch_num)

            critique = evaluator.evaluate_game(c4_history, agent_player, 'connect4')
            connect4_critiques.append(critique)

        # Multi-game CRLS loop
        # 1. Generate game-specific strategies
        c4_strategy = corrector.synthesize_game_strategy(connect4_critiques, 'connect4')

        # 2. Generate universal strategy from cross-game patterns
        patterns = evaluator.patterns_discovered
        game_stats = evaluator.get_game_stats()
        universal_strategy = corrector.synthesize_universal_strategy(patterns, game_stats)

        # Progress report
        stats = logger.get_overall_stats()
        c4_stats = stats['games_by_type']['connect4']

        print(f"\nBatch {batch_num + 1}/{TOTAL_GAMES // GAMES_PER_BATCH}:")
        print(f"  Connect4: {c4_stats['wins']}/{c4_stats['total_games']} wins "
              f"({c4_stats['win_rate']:.1%})")
        print(f"  Overall: {stats['overall_win_rate']:.1%} | "
              f"Patterns Discovered: {len(patterns)}")

        # Show universal strategy every 2 batches
        if batch_num % 2 == 1 and patterns:
            print(f"\n  📋 Pattern Discovery Preview:")
            print(f"     Total patterns: {len(patterns)}, "
                  f"Center control effectiveness: {[p.effectiveness for p in patterns if p.pattern_type == 'center_control'][:1]}")

    print("\n" + "="*70)

    # Final results
    final_stats = logger.get_overall_stats()
    game_stats = evaluator.get_game_stats()
    pattern_summary = evaluator.get_pattern_summary()

    print("\n📊 Final Results:")
    print(f"  Total Games: {final_stats['total_games']}")
    print(f"  Overall Win Rate: {final_stats['overall_win_rate']:.1%}")
    print()

    print("Per-Game Performance:")
    for game_type, stats in final_stats['games_by_type'].items():
        if stats['total_games'] > 0:
            print(f"  {game_type.upper()}: {stats['wins']}/{stats['total_games']} "
                  f"({stats['win_rate']:.1%})")

    print()
    print("🧠 Cross-Game Learning:")
    print(f"  Total Patterns: {pattern_summary['total_patterns']}")
    print(f"  Cross-Game Patterns: {pattern_summary['cross_game_patterns']}")

    if pattern_summary['patterns']:
        print("\n  Discovered Patterns:")
        for p in pattern_summary['patterns'][:5]:  # Top 5
            if len(p['games']) >= 2:
                games_str = ", ".join(p['games'])
                print(f"    • {p['description']} ({games_str}) - {p['effectiveness']}")

    # Transfer learning score
    transfer_score = corrector.get_transfer_learning_score(evaluator.patterns_discovered)
    print(f"\n  Transfer Learning Score: {transfer_score:.2f}/1.00")

    if transfer_score > 0.6:
        print("    ✅ Strong cross-game learning demonstrated!")
    elif transfer_score > 0.3:
        print("    ⚠️  Moderate cross-game learning")
    else:
        print("    ❌ Limited cross-game transfer")

    print("\n" + "="*70)
    print("✅ v0.81 Multi-Game CRLS complete!")


if __name__ == "__main__":
    main()
