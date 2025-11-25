"""
Lichess Bot Integration

Enables Prometheus chess agents to play on Lichess.org.

Features:
- Bot account management
- Challenge handling (accept/decline)
- Game state synchronization
- Move execution with time management
- Rating tracking

Requirements:
- Lichess account upgraded to BOT status
- API token with bot:play scope
- Install: pip install berserk (Lichess API client)

Usage:
    >>> bot = LichessBot(api_token="your_token", agent=prometheus_chess_agent)
    >>> bot.start()  # Start accepting challenges
"""

import chess
import time
import threading
from typing import Optional, Dict, Any, Callable
from collections import deque
import requests
import json

try:
    import berserk
    BERSERK_AVAILABLE = True
except ImportError:
    BERSERK_AVAILABLE = False


class LichessBot:
    """
    Lichess bot that connects Prometheus chess agents to Lichess.org.

    This bot:
    - Monitors incoming challenges
    - Accepts challenges based on criteria (time control, opponent rating, etc.)
    - Plays games using the Prometheus agent
    - Handles time management and connection issues
    - Tracks performance statistics

    Attributes:
        api_token: Lichess API token with bot:play scope
        agent: Prometheus chess agent with get_move() method
        session: Berserk client session
        active_games: Dictionary of active game IDs
        statistics: Performance tracking
    """

    def __init__(
        self,
        api_token: str,
        agent: Any,
        auto_accept: bool = True,
        min_rating: Optional[int] = None,
        max_rating: Optional[int] = None,
        accepted_time_controls: Optional[list] = None,
        verbose: bool = True
    ):
        """
        Initialize Lichess bot.

        Args:
            api_token: Lichess API token (from https://lichess.org/account/oauth/token)
            agent: Chess agent with get_move(state, board, temperature) method
            auto_accept: Automatically accept challenges
            min_rating: Minimum opponent rating to accept
            max_rating: Maximum opponent rating to accept
            accepted_time_controls: List of accepted time controls (e.g., ['blitz', 'rapid'])
            verbose: Print game information

        Raises:
            ImportError: If berserk library is not installed
        """
        if not BERSERK_AVAILABLE:
            raise ImportError(
                "berserk library required for Lichess integration.\n"
                "Install with: pip install berserk"
            )

        self.api_token = api_token
        self.agent = agent
        self.auto_accept = auto_accept
        self.min_rating = min_rating
        self.max_rating = max_rating
        self.accepted_time_controls = accepted_time_controls or ['blitz', 'rapid', 'classical']
        self.verbose = verbose

        # Initialize Lichess session
        session = berserk.TokenSession(api_token)
        self.client = berserk.Client(session=session)

        # Bot state
        self.running = False
        self.active_games = {}
        self.game_threads = {}

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

        # Verify bot account
        try:
            account = self.client.account.get()
            if verbose:
                print(f"✅ Connected to Lichess as: {account['username']}")
                print(f"   Rating: {account.get('perfs', {}).get('blitz', {}).get('rating', 'N/A')}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Lichess: {e}")

    def start(self):
        """
        Start the bot - begin accepting challenges and playing games.

        This method blocks and runs until stop() is called.
        Run in a separate thread if you need non-blocking operation.
        """
        self.running = True

        if self.verbose:
            print("🤖 Lichess Bot started. Waiting for challenges...")
            print(f"   Auto-accept: {self.auto_accept}")
            if self.min_rating or self.max_rating:
                print(f"   Rating range: {self.min_rating or '?'} - {self.max_rating or '?'}")
            print(f"   Time controls: {', '.join(self.accepted_time_controls)}")

        try:
            # Monitor event stream
            for event in self.client.bots.stream_incoming_events():
                if not self.running:
                    break

                event_type = event.get('type')

                if event_type == 'challenge':
                    self._handle_challenge(event['challenge'])

                elif event_type == 'gameStart':
                    self._start_game(event['game']['id'])

                elif event_type == 'gameFinish':
                    self._finish_game(event['game']['id'])

        except KeyboardInterrupt:
            if self.verbose:
                print("\n🛑 Bot stopped by user")
        except Exception as e:
            if self.verbose:
                print(f"❌ Error in bot event loop: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop the bot and clean up resources."""
        self.running = False

        # Wait for active games to finish
        if self.game_threads:
            if self.verbose:
                print(f"⏳ Waiting for {len(self.game_threads)} active games to finish...")

            for thread in self.game_threads.values():
                thread.join(timeout=5)

        if self.verbose:
            self._print_statistics()

    def _handle_challenge(self, challenge: Dict):
        """Handle incoming challenge."""
        self.statistics['challenges_received'] += 1

        challenger = challenge['challenger']['name']
        challenger_rating = challenge['challenger'].get('rating', 'N/A')
        time_control = challenge['timeControl']['type']
        rated = challenge['rated']

        if self.verbose:
            print(f"\n📩 Challenge from {challenger} (rating: {challenger_rating})")
            print(f"   Time control: {time_control}, Rated: {rated}")

        # Decide whether to accept
        should_accept = self._should_accept_challenge(challenge)

        if should_accept:
            try:
                self.client.bots.accept_challenge(challenge['id'])
                self.statistics['challenges_accepted'] += 1
                if self.verbose:
                    print(f"   ✅ Challenge accepted")
            except Exception as e:
                if self.verbose:
                    print(f"   ❌ Failed to accept challenge: {e}")
        else:
            try:
                self.client.bots.decline_challenge(challenge['id'])
                self.statistics['challenges_declined'] += 1
                if self.verbose:
                    print(f"   ❌ Challenge declined")
            except Exception as e:
                if self.verbose:
                    print(f"   ⚠️  Failed to decline challenge: {e}")

    def _should_accept_challenge(self, challenge: Dict) -> bool:
        """Determine if challenge should be accepted."""
        if not self.auto_accept:
            return False

        # Check time control
        time_control = challenge['timeControl']['type']
        if time_control not in self.accepted_time_controls:
            return False

        # Check rating range
        challenger_rating = challenge['challenger'].get('rating')
        if challenger_rating:
            if self.min_rating and challenger_rating < self.min_rating:
                return False
            if self.max_rating and challenger_rating > self.max_rating:
                return False

        # Check variant (only accept standard chess)
        if challenge.get('variant', {}).get('key') != 'standard':
            return False

        return True

    def _start_game(self, game_id: str):
        """Start playing a game."""
        if self.verbose:
            print(f"\n🎮 Game started: {game_id}")

        # Create thread for game
        thread = threading.Thread(target=self._play_game, args=(game_id,), daemon=True)
        self.game_threads[game_id] = thread
        self.active_games[game_id] = {'status': 'active'}
        thread.start()

    def _play_game(self, game_id: str):
        """Play a game (runs in separate thread)."""
        try:
            board = chess.Board()

            # Stream game state
            for event in self.client.bots.stream_game_state(game_id):
                if not self.running:
                    break

                event_type = event.get('type')

                if event_type == 'gameFull':
                    # Initial game state
                    state = event['state']
                    board = self._update_board_from_state(board, state)
                    game_info = {
                        'white': event.get('white', {}).get('name', 'Unknown'),
                        'black': event.get('black', {}).get('name', 'Unknown')
                    }
                    self.active_games[game_id]['info'] = game_info

                    if self.verbose:
                        print(f"   White: {game_info['white']}")
                        print(f"   Black: {game_info['black']}")

                    # Make move if it's our turn
                    if self._is_our_turn(board, event):
                        self._make_move(game_id, board)

                elif event_type == 'gameState':
                    # Game state update
                    board = self._update_board_from_state(board, event)

                    # Check if game is over
                    if event['status'] != 'started':
                        self._handle_game_end(game_id, event['status'], event.get('winner'))
                        break

                    # Make move if it's our turn
                    if board.turn == self._get_our_color(game_id):
                        self._make_move(game_id, board)

        except Exception as e:
            if self.verbose:
                print(f"   ❌ Error playing game {game_id}: {e}")
        finally:
            # Clean up
            if game_id in self.active_games:
                del self.active_games[game_id]
            if game_id in self.game_threads:
                del self.game_threads[game_id]

    def _update_board_from_state(self, board: chess.Board, state: Dict) -> chess.Board:
        """Update board from game state."""
        moves_uci = state.get('moves', '').split()

        # Reset board and replay moves
        new_board = chess.Board()
        for move_uci in moves_uci:
            try:
                move = chess.Move.from_uci(move_uci)
                new_board.push(move)
            except:
                if self.verbose:
                    print(f"   ⚠️  Invalid move: {move_uci}")

        return new_board

    def _is_our_turn(self, board: chess.Board, game_full_event: Dict) -> bool:
        """Check if it's our turn in initial game state."""
        # Determine our color from the gameFull event
        account = self.client.account.get()
        our_username = account['username'].lower()

        white_name = game_full_event.get('white', {}).get('name', '').lower()
        black_name = game_full_event.get('black', {}).get('name', '').lower()

        if our_username == white_name:
            return board.turn == chess.WHITE
        elif our_username == black_name:
            return board.turn == chess.BLACK
        else:
            return False

    def _get_our_color(self, game_id: str) -> chess.Color:
        """Get our color in a game."""
        account = self.client.account.get()
        our_username = account['username'].lower()

        game_info = self.active_games[game_id].get('info', {})
        white_name = game_info.get('white', '').lower()

        return chess.WHITE if our_username == white_name else chess.BLACK

    def _make_move(self, game_id: str, board: chess.Board):
        """Make a move using the agent."""
        if board.is_game_over():
            return

        try:
            # Get move from agent
            from prometheus.environments.chess import ChessEnvironment
            env = ChessEnvironment()
            env.board = board.copy()
            state = env.get_state()

            move = self.agent.get_move(state, board, temperature=0.1)

            # Submit move
            self.client.bots.make_move(game_id, move.uci())

            if self.verbose:
                print(f"   🤖 Played: {move.uci()}")

        except Exception as e:
            if self.verbose:
                print(f"   ❌ Error making move: {e}")

    def _handle_game_end(self, game_id: str, status: str, winner: Optional[str]):
        """Handle game end."""
        self.statistics['games_played'] += 1

        if winner:
            account = self.client.account.get()
            our_username = account['username'].lower()

            if winner.lower() == our_username:
                result = 'win'
                self.statistics['wins'] += 1
            else:
                result = 'loss'
                self.statistics['losses'] += 1
        else:
            result = 'draw'
            self.statistics['draws'] += 1

        if self.verbose:
            result_emoji = {'win': '🎉', 'loss': '😔', 'draw': '🤝'}[result]
            print(f"   {result_emoji} Game ended: {result.upper()} (status: {status})")

    def _finish_game(self, game_id: str):
        """Clean up finished game."""
        if game_id in self.active_games:
            if self.verbose:
                print(f"✅ Game finished: {game_id}")

    def _print_statistics(self):
        """Print bot statistics."""
        print("\n" + "=" * 60)
        print("📊 Lichess Bot Statistics")
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
