"""
Online Play Manager

Unified interface for managing Prometheus bots on multiple platforms.

Features:
- Manage both Lichess (chess) and OGS (Go) bots
- Start/stop bots programmatically
- Track aggregate statistics
- Thread-safe concurrent bot operation
"""

import threading
from typing import Optional, Dict, Any, List
from prometheus.online_play.lichess import LichessBot
from prometheus.online_play.ogs import OGSBot


class OnlinePlayManager:
    """
    Unified manager for Prometheus online play bots.

    This manager:
    - Coordinates multiple bots (Lichess, OGS)
    - Provides simple start/stop interface
    - Aggregates statistics across platforms
    - Handles threading for concurrent operation

    Usage:
        >>> manager = OnlinePlayManager()
        >>> manager.add_lichess_bot(token="...", agent=chess_agent)
        >>> manager.add_ogs_bot(username="...", api_key="...", agent=go_agent)
        >>> manager.start_all()  # Start both bots concurrently
        >>> # ... bots run in background ...
        >>> manager.stop_all()
        >>> manager.print_statistics()
    """

    def __init__(self, verbose: bool = True):
        """
        Initialize online play manager.

        Args:
            verbose: Print bot status messages
        """
        self.verbose = verbose
        self.bots = {}
        self.bot_threads = {}
        self.running = False

    def add_lichess_bot(
        self,
        api_token: str,
        agent: Any,
        bot_name: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Add a Lichess chess bot.

        Args:
            api_token: Lichess API token
            agent: Chess agent with get_move() method
            bot_name: Optional name for this bot (default: "lichess_bot")
            **kwargs: Additional arguments for LichessBot

        Returns:
            Bot identifier
        """
        bot_name = bot_name or f"lichess_bot_{len([b for b in self.bots if b.startswith('lichess')])}"

        bot = LichessBot(
            api_token=api_token,
            agent=agent,
            verbose=self.verbose,
            **kwargs
        )

        self.bots[bot_name] = {
            'type': 'lichess',
            'bot': bot,
            'thread': None
        }

        if self.verbose:
            print(f"✅ Added Lichess bot: {bot_name}")

        return bot_name

    def add_ogs_bot(
        self,
        username: str,
        api_key: str,
        agent: Any,
        bot_name: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Add an OGS Go bot.

        Args:
            username: OGS username
            api_key: OGS API key
            agent: Go agent with get_move() method
            bot_name: Optional name for this bot (default: "ogs_bot")
            **kwargs: Additional arguments for OGSBot

        Returns:
            Bot identifier
        """
        bot_name = bot_name or f"ogs_bot_{len([b for b in self.bots if b.startswith('ogs')])}"

        bot = OGSBot(
            username=username,
            api_key=api_key,
            agent=agent,
            verbose=self.verbose,
            **kwargs
        )

        self.bots[bot_name] = {
            'type': 'ogs',
            'bot': bot,
            'thread': None
        }

        if self.verbose:
            print(f"✅ Added OGS bot: {bot_name}")

        return bot_name

    def start_bot(self, bot_name: str):
        """
        Start a specific bot.

        Args:
            bot_name: Bot identifier returned from add_*_bot()
        """
        if bot_name not in self.bots:
            raise ValueError(f"Bot not found: {bot_name}")

        if self.bots[bot_name]['thread'] is not None:
            if self.verbose:
                print(f"⚠️  Bot {bot_name} is already running")
            return

        # Start bot in separate thread
        bot = self.bots[bot_name]['bot']
        thread = threading.Thread(target=bot.start, daemon=True)
        thread.start()

        self.bots[bot_name]['thread'] = thread

        if self.verbose:
            print(f"▶️  Started bot: {bot_name}")

    def start_all(self):
        """Start all registered bots concurrently."""
        self.running = True

        if self.verbose:
            print(f"\n🚀 Starting {len(self.bots)} bot(s)...")

        for bot_name in self.bots.keys():
            self.start_bot(bot_name)

        if self.verbose:
            print("✅ All bots started")
            print("   Press Ctrl+C to stop")

    def stop_bot(self, bot_name: str):
        """
        Stop a specific bot.

        Args:
            bot_name: Bot identifier
        """
        if bot_name not in self.bots:
            raise ValueError(f"Bot not found: {bot_name}")

        bot = self.bots[bot_name]['bot']
        thread = self.bots[bot_name]['thread']

        if thread is None:
            if self.verbose:
                print(f"⚠️  Bot {bot_name} is not running")
            return

        # Stop bot
        bot.stop()

        # Wait for thread to finish
        if thread.is_alive():
            thread.join(timeout=5)

        self.bots[bot_name]['thread'] = None

        if self.verbose:
            print(f"⏹️  Stopped bot: {bot_name}")

    def stop_all(self):
        """Stop all running bots."""
        self.running = False

        if self.verbose:
            print(f"\n🛑 Stopping {len(self.bots)} bot(s)...")

        for bot_name in list(self.bots.keys()):
            if self.bots[bot_name]['thread'] is not None:
                self.stop_bot(bot_name)

        if self.verbose:
            print("✅ All bots stopped")

    def get_bot_statistics(self, bot_name: str) -> Dict[str, Any]:
        """
        Get statistics for a specific bot.

        Args:
            bot_name: Bot identifier

        Returns:
            Dictionary with bot statistics
        """
        if bot_name not in self.bots:
            raise ValueError(f"Bot not found: {bot_name}")

        bot = self.bots[bot_name]['bot']
        return bot.get_statistics()

    def get_aggregate_statistics(self) -> Dict[str, Any]:
        """
        Get aggregate statistics across all bots.

        Returns:
            Dictionary with combined statistics
        """
        aggregate = {
            'total_games': 0,
            'total_wins': 0,
            'total_losses': 0,
            'total_draws': 0,
            'total_challenges_received': 0,
            'total_challenges_accepted': 0,
            'total_challenges_declined': 0,
            'by_platform': {}
        }

        for bot_name, bot_data in self.bots.items():
            bot = bot_data['bot']
            bot_type = bot_data['type']
            stats = bot.get_statistics()

            # Aggregate totals
            aggregate['total_games'] += stats.get('games_played', 0)
            aggregate['total_wins'] += stats.get('wins', 0)
            aggregate['total_losses'] += stats.get('losses', 0)
            aggregate['total_draws'] += stats.get('draws', 0)
            aggregate['total_challenges_received'] += stats.get('challenges_received', 0)
            aggregate['total_challenges_accepted'] += stats.get('challenges_accepted', 0)
            aggregate['total_challenges_declined'] += stats.get('challenges_declined', 0)

            # Per-platform statistics
            if bot_type not in aggregate['by_platform']:
                aggregate['by_platform'][bot_type] = {
                    'games': 0,
                    'wins': 0,
                    'losses': 0,
                    'draws': 0
                }

            aggregate['by_platform'][bot_type]['games'] += stats.get('games_played', 0)
            aggregate['by_platform'][bot_type]['wins'] += stats.get('wins', 0)
            aggregate['by_platform'][bot_type]['losses'] += stats.get('losses', 0)
            aggregate['by_platform'][bot_type]['draws'] += stats.get('draws', 0)

        # Calculate win rates
        if aggregate['total_games'] > 0:
            aggregate['overall_win_rate'] = aggregate['total_wins'] / aggregate['total_games']
        else:
            aggregate['overall_win_rate'] = 0.0

        for platform in aggregate['by_platform'].values():
            if platform['games'] > 0:
                platform['win_rate'] = platform['wins'] / platform['games']
            else:
                platform['win_rate'] = 0.0

        return aggregate

    def print_statistics(self):
        """Print comprehensive statistics for all bots."""
        print("\n" + "=" * 70)
        print("📊 ONLINE PLAY STATISTICS")
        print("=" * 70)

        # Per-bot statistics
        for bot_name, bot_data in self.bots.items():
            bot_type = bot_data['type']
            bot = bot_data['bot']
            stats = bot.get_statistics()

            platform_name = "Lichess (Chess)" if bot_type == 'lichess' else "OGS (Go)"

            print(f"\n🤖 {bot_name} [{platform_name}]")
            print(f"   Games played: {stats.get('games_played', 0)}")
            print(f"   Record: {stats.get('wins', 0)}W - {stats.get('losses', 0)}L - {stats.get('draws', 0)}D")

            if stats.get('games_played', 0) > 0:
                win_rate = stats.get('wins', 0) / stats['games_played']
                print(f"   Win rate: {win_rate:.1%}")

        # Aggregate statistics
        aggregate = self.get_aggregate_statistics()

        print(f"\n{'─' * 70}")
        print("📈 AGGREGATE STATISTICS")
        print(f"{'─' * 70}")
        print(f"Total games: {aggregate['total_games']}")
        print(f"Total record: {aggregate['total_wins']}W - {aggregate['total_losses']}L - {aggregate['total_draws']}D")
        if aggregate['total_games'] > 0:
            print(f"Overall win rate: {aggregate['overall_win_rate']:.1%}")

        # Per-platform breakdown
        if aggregate['by_platform']:
            print(f"\n📊 By Platform:")
            for platform, stats in aggregate['by_platform'].items():
                platform_name = "Lichess (Chess)" if platform == 'lichess' else "OGS (Go)"
                print(f"   {platform_name}:")
                print(f"      Games: {stats['games']}, Win rate: {stats['win_rate']:.1%}")

        print("=" * 70)

    def list_bots(self):
        """List all registered bots with their status."""
        print("\n" + "=" * 70)
        print("🤖 REGISTERED BOTS")
        print("=" * 70)

        for bot_name, bot_data in self.bots.items():
            bot_type = bot_data['type']
            is_running = bot_data['thread'] is not None and bot_data['thread'].is_alive()
            status = "🟢 RUNNING" if is_running else "⚪ STOPPED"

            platform_name = "Lichess" if bot_type == 'lichess' else "OGS"

            print(f"{status} | {bot_name} [{platform_name}]")

        print("=" * 70)

    def wait_until_stopped(self):
        """Block until all bots are stopped (e.g., by Ctrl+C)."""
        try:
            while self.running:
                # Check if any bots are still running
                any_running = any(
                    bot_data['thread'] is not None and bot_data['thread'].is_alive()
                    for bot_data in self.bots.values()
                )

                if not any_running:
                    break

                import time
                time.sleep(1)

        except KeyboardInterrupt:
            if self.verbose:
                print("\n🛑 Stopping bots...")
            self.stop_all()
