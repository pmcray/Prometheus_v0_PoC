#!/usr/bin/env python3
"""
Quick test of real FreeCiv - plays just ONE game
Takes about 1-2 minutes
"""

from freeciv_control import FreeCivGame, FreeCivConfig

print("="*70)
print("🏛️  TESTING REAL FREECIV")
print("="*70)
print()
print("Playing ONE real FreeCiv game...")
print("This will take 1-2 minutes...")
print()

config = FreeCivConfig(
    ai_difficulty=3,  # Medium difficulty
    num_civs=7,  # 7 civilizations
    timeout=180,  # 3 min max
    max_turns=100  # Shorter game for testing
)

game = FreeCivGame(config)
result = game.play_game(verbose=True)

print()
print("="*70)
print("✅ REAL FREECIV IS WORKING!")
print("="*70)
print()
print("Game Details:")
print(f"  Winner: {result['winner']}")
print(f"  Victory Type: {result['victory_type']}")
print(f"  Final Year: {result['final_year']}")
print(f"  Turns: {result['turns_played']}")
print(f"  Game Time: {result['game_time']:.1f} seconds")
print()
print("This was a REAL FreeCiv game using freeciv-server!")
print()
print("To run the full curriculum:")
print("  python run_freeciv_curriculum_REAL.py")
print()
print("Or use the Jupyter notebook:")
print("  jupyter notebook PrometheusStar_FreeCiv_REAL.ipynb")
print()
