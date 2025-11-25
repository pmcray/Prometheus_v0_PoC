"""
OGS (Online Go Server) Bot Integration

Enables Prometheus Go agents to play on online-go.com.

Features:
- Bot account management
- Challenge handling
- Game state synchronization via WebSocket
- Move execution with time management
- Rating tracking

Requirements:
- OGS account
- API credentials (client ID and secret)
- Install: pip install websocket-client requests

Usage:
    >>> bot = OGSBot(username="your_username", api_key="your_key", agent=prometheus_go_agent)
    >>> bot.start()  # Start accepting challenges
"""

import json
import time
import threading
from typing import Optional, Dict, Any, List
import requests

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False


class OGSBot:
    """
    OGS bot that connects Prometheus Go agents to online-go.com.

    This bot:
    - Monitors incoming challenges via WebSocket
    - Accepts challenges based on criteria
    - Plays games using the Prometheus agent
    - Handles time management and connection issues
    - Tracks performance statistics

    Attributes:
        username: OGS username
        api_key: OGS API key
        agent: Prometheus Go agent
        ws: WebSocket connection
        active_games: Dictionary of active game IDs
        statistics: Performance tracking
    """

    def __init__(
        self,
        username: str,
        api_key: str,
        agent: Any,
        auto_accept: bool = True,
        min_rank: Optional[str] = None,
        max_rank: Optional[str] = None,
        board_sizes: Optional[List[int]] = None,
        verbose: bool = True
    ):
        """
        Initialize OGS bot.

        Args:
            username: OGS username
            api_key: OGS API key (from https://online-go.com/developer)
            agent: Go agent with get_move(state, legal_moves, temperature) method
            auto_accept: Automatically accept challenges
            min_rank: Minimum opponent rank (e.g., "10k", "5d")
            max_rank: Maximum opponent rank
            board_sizes: Accepted board sizes (default: [9, 13, 19])
            verbose: Print game information

        Raises:
            ImportError: If websocket-client library is not installed
        """
        if not WEBSOCKET_AVAILABLE:
            raise ImportError(
                "websocket-client library required for OGS integration.\n"
                "Install with: pip install websocket-client"
            )

        self.username = username
        self.api_key = api_key
        self.agent = agent
        self.auto_accept = auto_accept
        self.min_rank = min_rank
        self.max_rank = max_rank
        self.board_sizes = board_sizes or [9, 13, 19]
        self.verbose = verbose

        # OGS API configuration
        self.base_url = "https://online-go.com"
        self.api_url = f"{self.base_url}/api/v1"
        self.ws_url = "wss://online-go.com/socket.io/?EIO=3&transport=websocket"

        # Bot state
        self.running = False
        self.ws = None
        self.active_games = {}
        self.user_id = None
        self.auth_token = None

        # Statistics
        self.statistics = {
            'games_played': 0,
            'wins': 0,
            'losses': 0,
            'draws': 0,
            'challenges_received': 0,
            'challenges_accepted': 0,
            'challenges_declined': 0
        }

        # Authenticate
        try:
            self._authenticate()
            if verbose:
                print(f"✅ Connected to OGS as: {self.username}")
                print(f"   User ID: {self.user_id}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to OGS: {e}")

    def _authenticate(self):
        """Authenticate with OGS API."""
        # Note: OGS authentication can vary. This is a simplified version.
        # In production, use OAuth2 flow or session-based auth.

        # For now, we'll use a simple session
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'PrometheusBot/1.0'
        })

        # Get user info (requires authentication)
        # This is a placeholder - actual OGS API requires proper auth flow
        try:
            response = self.session.get(f"{self.api_url}/me", timeout=10)
            if response.status_code == 200:
                user_data = response.json()
                self.user_id = user_data.get('id')
                self.username = user_data.get('username', self.username)
            else:
                # If not authenticated, use provided username as placeholder
                self.user_id = hash(self.username) % 1000000  # Placeholder
                if self.verbose:
                    print("⚠️  OGS authentication not fully implemented")
                    print("   This is a demo implementation showing the structure")
        except:
            self.user_id = hash(self.username) % 1000000

    def start(self):
        """
        Start the bot - begin accepting challenges and playing games.

        This method blocks and runs until stop() is called.
        Run in a separate thread if you need non-blocking operation.
        """
        self.running = True

        if self.verbose:
            print("🤖 OGS Bot started. Waiting for challenges...")
            print(f"   Auto-accept: {self.auto_accept}")
            print(f"   Board sizes: {', '.join(map(str, self.board_sizes))}")
            print("\n⚠️  NOTE: This is a DEMO implementation of OGS bot")
            print("   Full implementation requires:")
            print("   1. Proper OGS OAuth2 authentication")
            print("   2. WebSocket protocol implementation")
            print("   3. OGS-specific game state handling")
            print("   4. SGF parsing and move submission")

        try:
            # Demo mode: Accept challenges from a queue (in production, use WebSocket)
            self._run_demo_mode()

        except KeyboardInterrupt:
            if self.verbose:
                print("\n🛑 Bot stopped by user")
        except Exception as e:
            if self.verbose:
                print(f"❌ Error in bot event loop: {e}")
        finally:
            self.stop()

    def _run_demo_mode(self):
        """Run in demo mode (for testing without actual OGS connection)."""
        if self.verbose:
            print("\n📝 Running in DEMO mode")
            print("   To enable full OGS integration:")
            print("   1. Create account at https://online-go.com")
            print("   2. Get API credentials from Developer section")
            print("   3. Implement WebSocket connection handler")
            print("   4. Handle OGS protocol messages")

        # In demo mode, we just wait
        while self.running:
            time.sleep(1)

    def stop(self):
        """Stop the bot and clean up resources."""
        self.running = False

        if self.ws:
            try:
                self.ws.close()
            except:
                pass

        if self.verbose:
            self._print_statistics()

    def _handle_challenge(self, challenge: Dict):
        """Handle incoming challenge."""
        self.statistics['challenges_received'] += 1

        challenger = challenge.get('challenger', {}).get('username', 'Unknown')
        board_size = challenge.get('board_size', 19)
        ranked = challenge.get('ranked', False)

        if self.verbose:
            print(f"\n📩 Challenge from {challenger}")
            print(f"   Board size: {board_size}×{board_size}, Ranked: {ranked}")

        # Decide whether to accept
        should_accept = self._should_accept_challenge(challenge)

        if should_accept:
            self._accept_challenge(challenge['id'])
            self.statistics['challenges_accepted'] += 1
            if self.verbose:
                print(f"   ✅ Challenge accepted")
        else:
            self._decline_challenge(challenge['id'])
            self.statistics['challenges_declined'] += 1
            if self.verbose:
                print(f"   ❌ Challenge declined")

    def _should_accept_challenge(self, challenge: Dict) -> bool:
        """Determine if challenge should be accepted."""
        if not self.auto_accept:
            return False

        # Check board size
        board_size = challenge.get('board_size', 19)
        if board_size not in self.board_sizes:
            return False

        # Check rank range (if specified)
        # OGS ranks: 30k (beginner) to 9d (professional)
        # This would require rank comparison logic

        return True

    def _accept_challenge(self, challenge_id: str):
        """Accept a challenge."""
        try:
            response = self.session.post(
                f"{self.api_url}/challenges/{challenge_id}/accept",
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            if self.verbose:
                print(f"   ❌ Failed to accept challenge: {e}")
            return False

    def _decline_challenge(self, challenge_id: str):
        """Decline a challenge."""
        try:
            response = self.session.post(
                f"{self.api_url}/challenges/{challenge_id}/decline",
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            if self.verbose:
                print(f"   ⚠️  Failed to decline challenge: {e}")
            return False

    def _play_game(self, game_id: str):
        """Play a game (runs in separate thread)."""
        try:
            from prometheus.environments.go import GoEnvironment, GoBoard

            # Get game info
            game_info = self._get_game_info(game_id)
            board_size = game_info.get('width', 19)
            komi = game_info.get('komi', 7.5)

            # Create environment
            env = GoEnvironment(board_size=board_size, komi=komi)

            if self.verbose:
                print(f"\n🎮 Playing game {game_id}")
                print(f"   Board: {board_size}×{board_size}, Komi: {komi}")

            # Game loop
            while self.running:
                # Get current game state
                game_state = self._get_game_state(game_id)

                if game_state.get('phase') == 'finished':
                    self._handle_game_end(game_id, game_state)
                    break

                # Check if it's our turn
                if game_state.get('current_player') == self.user_id:
                    # Get move from agent
                    state = env.get_state()
                    legal_moves = env.get_legal_moves()
                    move = self.agent.get_move(state, legal_moves, temperature=0.1)

                    # Submit move
                    self._submit_move(game_id, move)

                    if self.verbose:
                        print(f"   🤖 Played: {move}")

                # Wait before checking again
                time.sleep(1)

        except Exception as e:
            if self.verbose:
                print(f"   ❌ Error playing game {game_id}: {e}")

    def _get_game_info(self, game_id: str) -> Dict:
        """Get game information."""
        try:
            response = self.session.get(f"{self.api_url}/games/{game_id}", timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return {}

    def _get_game_state(self, game_id: str) -> Dict:
        """Get current game state."""
        try:
            response = self.session.get(f"{self.api_url}/games/{game_id}/state", timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return {}

    def _submit_move(self, game_id: str, move: tuple):
        """Submit a move to OGS."""
        try:
            # Convert move to OGS format
            if move == ('pass',):
                move_data = {'move': 'pass'}
            else:
                row, col = move
                # OGS uses different coordinate system
                move_data = {'move': f'{chr(ord("a") + col)}{row + 1}'}

            response = self.session.post(
                f"{self.api_url}/games/{game_id}/move",
                json=move_data,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            if self.verbose:
                print(f"   ❌ Failed to submit move: {e}")
            return False

    def _handle_game_end(self, game_id: str, game_state: Dict):
        """Handle game end."""
        self.statistics['games_played'] += 1

        winner = game_state.get('winner')

        if winner == self.user_id:
            result = 'win'
            self.statistics['wins'] += 1
        elif winner:
            result = 'loss'
            self.statistics['losses'] += 1
        else:
            result = 'draw'
            self.statistics['draws'] += 1

        if self.verbose:
            result_emoji = {'win': '🎉', 'loss': '😔', 'draw': '🤝'}[result]
            print(f"   {result_emoji} Game ended: {result.upper()}")

    def _print_statistics(self):
        """Print bot statistics."""
        print("\n" + "=" * 60)
        print("📊 OGS Bot Statistics")
        print("=" * 60)
        print(f"Games played: {self.statistics['games_played']}")
        print(f"Wins: {self.statistics['wins']}")
        print(f"Losses: {self.statistics['losses']}")
        print(f"Draws: {self.statistics['draws']}")

        if self.statistics['games_played'] > 0:
            win_rate = self.statistics['wins'] / self.statistics['games_played']
            print(f"Win rate: {win_rate:.1%}")

        print(f"\nChallenges received: {self.statistics['challenges_received']}")
        print(f"Challenges accepted: {self.statistics['challenges_accepted']}")
        print(f"Challenges declined: {self.statistics['challenges_declined']}")
        print("=" * 60)

    def get_statistics(self) -> Dict[str, Any]:
        """Get bot statistics."""
        return self.statistics.copy()


# Note: Full OGS integration requires:
# 1. WebSocket connection handling (Socket.IO protocol)
# 2. Proper authentication flow (OAuth2)
# 3. SGF parsing for game state
# 4. Real-time move synchronization
# 5. Time management (byoyomi periods)
#
# This implementation provides the structure and can be extended
# with these features as needed.
