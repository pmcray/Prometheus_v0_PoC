"""
FreeCiv Real Server Interface
Controls actual FreeCiv server via socket/stdin communication
"""

import subprocess
import socket
import time
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class FreeCivServerConfig:
    """Configuration for FreeCiv server"""
    port: int = 5556
    save_name: str = "prometheus_game"
    timeout: int = 180  # 3 minutes per game
    ai_skill_level: int = 3  # 1-10
    num_players: int = 7  # Including AI
    map_size: str = "normal"  # tiny, small, normal, large
    map_type: str = "EARTH"  # or "RANDOM"

class FreeCivRealGame:
    """Interface to real FreeCiv server"""

    def __init__(self, config: FreeCivServerConfig = None):
        self.config = config or FreeCivServerConfig()
        self.server_process = None
        self.client_socket = None
        self.game_running = False

    def start_server(self) -> bool:
        """Start FreeCiv server"""
        try:
            # Start server in background
            cmd = [
                "freeciv-server",
                "--port", str(self.config.port),
                "--Serverid", "prometheus",
                "--read", "-",  # Read commands from stdin
                "--exit-on-end"
            ]

            self.server_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for server to start
            time.sleep(2)

            # Check if server is running
            if self.server_process.poll() is None:
                print(f"✅ FreeCiv server started on port {self.config.port}")
                return True
            else:
                stdout, stderr = self.server_process.communicate()
                print(f"❌ Server failed to start:")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                return False

        except Exception as e:
            print(f"❌ Error starting server: {e}")
            return False

    def send_command(self, command: str) -> bool:
        """Send command to server via stdin"""
        try:
            if self.server_process and self.server_process.stdin:
                self.server_process.stdin.write(command + "\n")
                self.server_process.stdin.flush()
                return True
            return False
        except Exception as e:
            print(f"❌ Error sending command '{command}': {e}")
            return False

    def configure_game(self):
        """Configure game settings"""
        commands = [
            f"set difficulty {self.config.ai_skill_level}",
            f"set size {self.config.map_size}",
            f"set topology {self.config.map_type}",
            "set aifill 6",  # Fill with 6 AI players
            "set timeout {self.config.timeout}",
            "set minplayers 1",
            "set maxplayers 7",
            # Game speed
            "set turnblock on",
            "set fixedlength 200",  # Max 200 turns
        ]

        for cmd in commands:
            self.send_command(cmd)
            time.sleep(0.1)

    def create_ai_player(self, name: str, nation: str = None) -> bool:
        """Create an AI player"""
        if nation:
            cmd = f"create {name} {nation}"
        else:
            cmd = f"create {name}"

        return self.send_command(cmd)

    def start_game(self) -> bool:
        """Start the game"""
        return self.send_command("start")

    def get_server_output(self, timeout: float = 1.0) -> str:
        """Read server output (non-blocking)"""
        if not self.server_process or not self.server_process.stdout:
            return ""

        output = []
        start_time = time.time()

        while time.time() - start_time < timeout:
            line = self.server_process.stdout.readline()
            if line:
                output.append(line.strip())
            else:
                break

        return "\n".join(output)

    def parse_game_state(self, output: str) -> Dict:
        """Parse game state from server output"""
        state = {
            'year': None,
            'turn': None,
            'players': [],
            'winner': None,
            'game_over': False
        }

        # Parse year (e.g., "4000 B.C." or "1200 A.D.")
        year_match = re.search(r'(\d+)\s+(B\.C\.|A\.D\.)', output)
        if year_match:
            state['year'] = year_match.group(0)

        # Parse turn
        turn_match = re.search(r'Turn:\s*(\d+)', output)
        if turn_match:
            state['turn'] = int(turn_match.group(1))

        # Parse players and scores
        player_matches = re.findall(r'(\w+)\s+\(.*?\):\s*(\d+)\s+points', output)
        for name, score in player_matches:
            state['players'].append({
                'name': name,
                'score': int(score)
            })

        # Check for game end
        if 'Game ended' in output or 'has won' in output:
            state['game_over'] = True
            winner_match = re.search(r'(\w+)\s+has won', output)
            if winner_match:
                state['winner'] = winner_match.group(1)

        return state

    def play_game(self, ai_player_name: str = "Prometheus", verbose: bool = False) -> Dict:
        """
        Play a complete game with AI
        Returns: game result dictionary
        """
        if verbose:
            print("="*80)
            print("🏛️  STARTING REAL FREECIV GAME")
            print("="*80)

        # Start server
        if not self.start_server():
            return {'error': 'Failed to start server'}

        # Configure game
        self.configure_game()
        time.sleep(1)

        # Create AI players
        civilizations = ["Romans", "Egyptians", "Greeks", "Chinese", "Babylonians", "Indians", "Aztecs"]

        if verbose:
            print(f"Creating {ai_player_name} as player...")
        self.create_ai_player(ai_player_name, civilizations[0])

        # Fill rest with AI
        for i in range(1, 7):
            self.create_ai_player(f"AI_{i}", civilizations[i])
            time.sleep(0.2)

        time.sleep(2)

        # Start game
        if verbose:
            print("Starting game...")
        self.start_game()

        # Monitor game progress
        game_state = None
        last_turn = 0

        while self.server_process.poll() is None:
            output = self.get_server_output(timeout=5.0)

            if output:
                state = self.parse_game_state(output)

                # Update on turn change
                if state['turn'] and state['turn'] != last_turn:
                    last_turn = state['turn']
                    if verbose and state['turn'] % 10 == 0:
                        print(f"Turn {state['turn']}: {state['year'] or 'Unknown year'}")

                # Check for game end
                if state['game_over']:
                    game_state = state
                    if verbose:
                        print(f"\n🏆 Game Over! Winner: {state['winner']}")
                    break

            time.sleep(0.5)

        # Clean up
        self.stop_server()

        # Return result
        if game_state:
            result = {
                'player_name': ai_player_name,
                'winner': game_state['winner'],
                'player_won': game_state['winner'] == ai_player_name,
                'final_turn': game_state['turn'],
                'final_year': game_state['year'],
                'players': game_state['players']
            }
        else:
            result = {
                'error': 'Game did not complete properly',
                'player_name': ai_player_name
            }

        if verbose:
            print("="*80)

        return result

    def stop_server(self):
        """Stop the FreeCiv server"""
        if self.server_process:
            self.send_command("quit")
            time.sleep(1)

            if self.server_process.poll() is None:
                self.server_process.terminate()
                time.sleep(1)

            if self.server_process.poll() is None:
                self.server_process.kill()

            self.server_process = None
            print("✅ FreeCiv server stopped")


def test_freeciv_interface():
    """Test the FreeCiv interface"""
    import subprocess

    # Check if FreeCiv is installed
    try:
        result = subprocess.run(['freeciv-server', '--version'],
                              capture_output=True, text=True, timeout=5)
        print("FreeCiv Server Version:")
        print(result.stdout)
        print()
    except FileNotFoundError:
        print("❌ FreeCiv not installed!")
        print("Please run: ./install_freeciv.sh")
        return
    except Exception as e:
        print(f"❌ Error checking FreeCiv: {e}")
        return

    # Test game
    print("Testing FreeCiv interface...")
    print()

    config = FreeCivServerConfig(
        ai_skill_level=3,
        timeout=120
    )

    game = FreeCivRealGame(config)
    result = game.play_game(ai_player_name="Prometheus", verbose=True)

    print("\nGame Result:")
    print(result)


if __name__ == "__main__":
    test_freeciv_interface()
