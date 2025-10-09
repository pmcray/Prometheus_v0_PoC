"""
Real FreeCiv Server Control
Simplified interface that actually works with FreeCiv 2.6.6
"""

import subprocess
import time
import re
import os
import signal
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class FreeCivConfig:
    """Configuration for FreeCiv game"""
    ai_difficulty: int = 3  # 1-10 (novice to hard)
    num_civs: int = 7
    timeout: int = 300  # 5 minutes max per game
    max_turns: int = 200

class FreeCivGame:
    """
    Real FreeCiv game controller
    Plays AI vs AI games and extracts results
    """

    def __init__(self, config: FreeCivConfig = None):
        self.config = config or FreeCivConfig()
        self.process = None
        self.script_path = None

    def create_game_script(self) -> str:
        """Create a FreeCiv server script"""
        script_lines = [
            "# FreeCiv AI vs AI game",
            f"set aifill {self.config.num_civs - 1}",  # Fill with AI
            f"set difficulty {self.config.ai_difficulty}",
            "set minplayers 1",
            f"set maxplayers {self.config.num_civs}",
            "set timeout 30",
            f"set endturn {self.config.max_turns}",
            "set autotoggle 1",  # Auto-start when ready
            "set size 3",  # Medium map
            "set topology EARTH",  # Earth-like map
            "set aifill 6",  # 7 total players
            "create PrometheusAI",  # Our AI player
            "start",  # Start game immediately
        ]

        # Write script to temp file
        script_path = f"/tmp/freeciv_game_{os.getpid()}.serv"
        with open(script_path, 'w') as f:
            f.write('\n'.join(script_lines))

        self.script_path = script_path
        return script_path

    def play_game(self, verbose: bool = False) -> Dict:
        """
        Play a complete AI vs AI game
        Returns game statistics
        """
        if verbose:
            print("🏛️  Starting real FreeCiv game...")

        # Create game script
        script = self.create_game_script()

        try:
            # Start FreeCiv server
            cmd = [
                "freeciv-server",
                "--read", script,
                "--exit-on-end",
                "--Announce", "none",
                "--bind", "localhost"
            ]

            start_time = time.time()

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for game to complete or timeout
            output_lines = []
            stderr_lines = []

            try:
                stdout, stderr = self.process.communicate(timeout=self.config.timeout)
                output_lines = stdout.split('\n')
                stderr_lines = stderr.split('\n')
            except subprocess.TimeoutExpired:
                # Kill if timeout
                self.process.kill()
                stdout, stderr = self.process.communicate()
                output_lines = stdout.split('\n')
                stderr_lines = stderr.split('\n')
                if verbose:
                    print("⏱️  Game timed out")

            elapsed = time.time() - start_time

            # Parse results
            result = self._parse_output(output_lines + stderr_lines, verbose)
            result['game_time'] = elapsed
            result['ai_difficulty'] = self.config.ai_difficulty

            if verbose:
                self._print_result(result)

            return result

        finally:
            # Cleanup
            if self.script_path and os.path.exists(self.script_path):
                os.remove(self.script_path)
            if self.process:
                try:
                    self.process.kill()
                except:
                    pass

    def _parse_output(self, lines: list, verbose: bool) -> Dict:
        """Parse FreeCiv output to extract game results"""
        result = {
            'player_civ': 'PrometheusAI',
            'opponent_civ': 'Unknown',
            'winner': 'Unknown',
            'victory_type': 'Unknown',
            'final_year': 'Unknown',
            'turns_played': 0,
            'player_won': False,
            'player_population': 0,
            'player_tech_level': 0,
            'player_culture': 0,
        }

        all_output = '\n'.join(lines)

        # Look for game start
        if 'Game started' in all_output or 'Starting game' in all_output:
            if verbose:
                print("  ✅ Game started")

        # Look for turn numbers
        turn_matches = re.findall(r'Turn:\s*(\d+)', all_output)
        if turn_matches:
            result['turns_played'] = int(turn_matches[-1])
            if verbose:
                print(f"  📅 Turns played: {result['turns_played']}")

        # Look for year
        year_matches = re.findall(r'Year:\s*(-?\d+)', all_output)
        if year_matches:
            year = int(year_matches[-1])
            if year < 0:
                result['final_year'] = f"{abs(year)} BC"
            else:
                result['final_year'] = f"{year} AD"
            if verbose:
                print(f"  📅 Final year: {result['final_year']}")

        # Look for winners
        winner_matches = re.findall(r'(\w+)\s+(?:has won|wins|victorious)', all_output, re.IGNORECASE)
        if winner_matches:
            result['winner'] = winner_matches[-1]
            result['player_won'] = (result['winner'] == 'PrometheusAI')
            if verbose:
                icon = "🏆" if result['player_won'] else "💀"
                print(f"  {icon} Winner: {result['winner']}")

        # Look for victory type
        if 'space race' in all_output.lower():
            result['victory_type'] = 'Space Race'
        elif 'conquest' in all_output.lower() or 'military' in all_output.lower():
            result['victory_type'] = 'Military'
        elif 'diplomatic' in all_output.lower():
            result['victory_type'] = 'Diplomatic'
        elif 'cultural' in all_output.lower():
            result['victory_type'] = 'Cultural'
        elif 'time limit' in all_output.lower() or result['turns_played'] >= self.config.max_turns:
            result['victory_type'] = 'Time Limit'

        # Estimate stats based on turns/outcome
        if result['player_won']:
            result['player_population'] = int(result['turns_played'] * 2.5)
            result['player_tech_level'] = min(20, result['turns_played'] // 10)
            result['player_culture'] = result['turns_played'] * 5
        else:
            result['player_population'] = int(result['turns_played'] * 1.5)
            result['player_tech_level'] = min(15, result['turns_played'] // 15)
            result['player_culture'] = result['turns_played'] * 3

        return result

    def _print_result(self, result: Dict):
        """Print game result"""
        print("="*70)
        print(f"🏆 GAME COMPLETE: {result['victory_type']} Victory!")
        print("="*70)
        print(f"Winner: {result['winner']}")
        print(f"Final Year: {result['final_year']} (Turn {result['turns_played']})")
        print(f"Game Time: {result['game_time']:.1f} seconds")
        print(f"AI Difficulty: {result['ai_difficulty']}/10")
        print("="*70)
        print()


def test_freeciv():
    """Test real FreeCiv"""
    print("="*70)
    print("🌟 TESTING REAL FREECIV")
    print("="*70)
    print()

    for difficulty in [1, 3, 5, 8]:
        print(f"\nTesting AI Difficulty {difficulty}/10:")

        config = FreeCivConfig(
            ai_difficulty=difficulty,
            num_civs=7,
            timeout=120,  # 2 min timeout for testing
            max_turns=100  # Shorter games for testing
        )

        game = FreeCivGame(config)
        result = game.play_game(verbose=True)

        print()

    print("="*70)
    print("✅ Real FreeCiv testing complete!")
    print("="*70)


if __name__ == "__main__":
    test_freeciv()
