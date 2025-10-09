"""
FreeCiv AI vs AI game controller
Uses freeciv-server with proper AI client connections
"""

import subprocess
import time
import os
import signal
from typing import Dict

class FreeCivAIGame:
    """Runs FreeCiv AI vs AI games"""

    def __init__(self, ai_difficulty: int = 3, num_players: int = 7):
        """
        ai_difficulty: 1-5 (novice, easy, normal, hard, cheating)
        num_players: 2-30 (number of AI players)
        """
        self.ai_difficulty = min(5, max(1, ai_difficulty))
        self.num_players = min(30, max(2, num_players))
        self.server_process = None
        self.port = 5556

    def create_server_script(self) -> str:
        """Create FreeCiv server startup script"""
        difficulty_names = {
            1: "novice",
            2: "easy",
            3: "normal",
            4: "hard",
            5: "cheating"
        }

        script_lines = [
            "# FreeCiv AI vs AI game",
            "# Wait for players",
            "set timeout 30",
            f"set endturn 100",  # Shorter games
            f"set aifill {self.num_players}",
            f"set skillevel {difficulty_names[self.ai_difficulty]}",
            "set minplayers 1",
            f"set maxplayers {self.num_players}",
            "set autotoggle enabled",  # Auto-start when ready
            "set size 2",  # Small map for speed
            "# Game will start automatically when all AI players ready",
        ]

        script_path = f"/tmp/freeciv_ai_game_{os.getpid()}.serv"
        with open(script_path, 'w') as f:
            f.write('\n'.join(script_lines))

        return script_path

    def play_game(self, verbose: bool = False) -> Dict:
        """
        Play complete AI vs AI game
        Returns: game statistics
        """
        if verbose:
            print(f"🏛️  Starting FreeCiv AI vs AI game...")
            print(f"   Difficulty: {self.ai_difficulty}/5")
            print(f"   Players: {self.num_players} AI")

        script_path = self.create_server_script()

        try:
            # Start server
            cmd = [
                "freeciv-server",
                "--read", script_path,
                "--exit-on-end",
                "--port", str(self.port),
                "--Announce", "none"
            ]

            if verbose:
                print(f"   Starting server on port {self.port}...")

            start_time = time.time()

            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            # Wait for server to start
            time.sleep(2)

            # Monitor game progress
            output_lines = []
            game_started = False
            game_ended = False
            turn_count = 0

            # Read output with timeout
            timeout = 300  # 5 minutes max
            while time.time() - start_time < timeout:
                # Check if process ended
                if self.server_process.poll() is not None:
                    if verbose:
                        print("   Server process ended")
                    game_ended = True
                    break

                # Try to read a line (non-blocking)
                try:
                    line = self.server_process.stdout.readline()
                    if line:
                        output_lines.append(line.strip())

                        # Check for game start
                        if not game_started and ('Game started' in line or 'Starting game' in line):
                            game_started = True
                            if verbose:
                                print("   ✅ Game started!")

                        # Track turns
                        if 'Beginning turn' in line or 'Turn' in line:
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if part.isdigit():
                                    turn_count = max(turn_count, int(part))
                                    if verbose and turn_count % 10 == 0:
                                        print(f"   📅 Turn {turn_count}")
                                    break

                        # Check for game end
                        if 'won the game' in line.lower() or 'game ended' in line.lower():
                            game_ended = True
                            if verbose:
                                print(f"   🏆 Game ended!")
                            break
                except:
                    pass

                time.sleep(0.1)

            # Force kill if still running
            if self.server_process.poll() is None:
                if verbose:
                    print("   ⏱️  Timeout - terminating server...")
                self.server_process.terminate()
                time.sleep(1)
                if self.server_process.poll() is None:
                    self.server_process.kill()

            # Get remaining output
            try:
                remaining, _ = self.server_process.communicate(timeout=2)
                if remaining:
                    output_lines.extend(remaining.split('\n'))
            except:
                pass

            elapsed = time.time() - start_time

            # Parse results
            result = self._parse_results(output_lines, turn_count, elapsed, verbose)

            return result

        finally:
            # Cleanup
            if os.path.exists(script_path):
                os.remove(script_path)
            if self.server_process:
                try:
                    self.server_process.kill()
                except:
                    pass

    def _parse_results(self, lines: list, turn_count: int, elapsed: float, verbose: bool) -> Dict:
        """Parse game output for results"""
        all_output = '\n'.join(lines)

        # Find winner
        winner = "Unknown"
        for line in lines:
            if 'won the game' in line.lower():
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'won' in part.lower() and i > 0:
                        winner = parts[i-1]
                        break
                break

        # Estimate year from turns (rough approximation)
        if turn_count > 0:
            # FreeCiv starts at 4000 BC, roughly 50 years per turn early game
            years_passed = turn_count * 40
            year = -4000 + years_passed
            if year < 0:
                final_year = f"{abs(year)} BC"
            else:
                final_year = f"{year} AD"
        else:
            final_year = "Unknown"

        result = {
            'winner': winner,
            'turns_played': turn_count,
            'final_year': final_year,
            'game_time': elapsed,
            'ai_difficulty': self.ai_difficulty,
            'num_players': self.num_players,
            'game_started': 'game started' in all_output.lower(),
            'player_won': 'AI*1' in winner or 'Player' in winner,
        }

        if verbose:
            print("\n" + "="*70)
            print("🏆 GAME RESULTS")
            print("="*70)
            print(f"Winner: {result['winner']}")
            print(f"Turns: {result['turns_played']}")
            print(f"Final Year: {result['final_year']}")
            print(f"Game Time: {result['game_time']:.1f}s")
            print(f"Game Started: {result['game_started']}")
            print("="*70)

        return result


def test_freeciv_ai():
    """Test FreeCiv AI vs AI"""
    print("="*70)
    print("🌟 TESTING FREECIV AI VS AI")
    print("="*70)
    print()

    for difficulty in [1, 3, 5]:
        print(f"\n{'='*70}")
        print(f"Testing difficulty {difficulty}/5 (7 AI players)")
        print('='*70)

        game = FreeCivAIGame(
            ai_difficulty=difficulty,
            num_players=7
        )

        result = game.play_game(verbose=True)
        print()

    print("="*70)
    print("✅ FreeCiv AI testing complete!")
    print("="*70)


if __name__ == "__main__":
    test_freeciv_ai()
