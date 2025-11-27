#!/usr/bin/env python3
"""
Lichess Bot Deployment Script

Deploys a trained Prometheus chess agent to Lichess as a bot account.

Usage:
    python scripts/deploy_lichess_bot.py --token YOUR_TOKEN --model path/to/model.h5

Requirements:
    - Lichess BOT account (upgrade regular account at lichess.org/account/bot)
    - API token with bot:play scope
    - Trained chess model

Features:
    - Automatic game acceptance
    - Configurable time controls
    - ELO tracking
    - Graceful shutdown
"""

import argparse
import sys
import os
import signal
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from prometheus.online_play.lichess import LichessBot
from prometheus.models.architectures import PrometheusChessAgent, StaticChessAgent
from prometheus.environments.chess import ChessEnvironment
import tensorflow as tf


class BotDeployment:
    """Manages bot deployment and lifecycle."""

    def __init__(self, token: str, model_path: Optional[str] = None,
                 agent_type: str = 'prometheus',
                 time_controls: Optional[List[str]] = None):
        """
        Initialize deployment.

        Args:
            token: Lichess API token
            model_path: Path to trained model (optional)
            agent_type: 'prometheus' or 'static'
            time_controls: List of accepted time controls (e.g., ['blitz', 'rapid'])
        """
        self.token = token
        self.model_path = model_path
        self.agent_type = agent_type
        self.time_controls = time_controls or ['blitz', 'rapid', 'classical']

        self.bot = None
        self.agent = None
        self.running = False

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\nReceived shutdown signal. Stopping bot...")
        self.stop()
        sys.exit(0)

    def create_agent(self) -> Any:
        """
        Create chess agent.

        Returns:
            Chess agent instance
        """
        print(f"Creating {self.agent_type} agent...")

        if self.agent_type == 'prometheus':
            agent = PrometheusChessAgent()
        else:
            agent = StaticChessAgent()

        # Load model if provided
        if self.model_path:
            if os.path.exists(self.model_path):
                print(f"Loading model from {self.model_path}")
                agent.model = tf.keras.models.load_model(self.model_path)
                agent.trainable = False  # Freeze for deployment
            else:
                print(f"Warning: Model file not found: {self.model_path}")
                print("Using random initialization")

        return agent

    def start(self):
        """Start the bot."""
        print("="*60)
        print("LICHESS BOT DEPLOYMENT")
        print("="*60)

        # Create agent
        self.agent = self.create_agent()

        # Create bot
        print("Connecting to Lichess...")
        self.bot = LichessBot(
            token=self.token,
            agent=self.agent
        )

        # Verify account
        account_info = self.bot.get_account_info()
        if account_info:
            print(f"Connected as: {account_info.get('username', 'Unknown')}")
            print(f"Rating: {account_info.get('perfs', {}).get('blitz', {}).get('rating', '?')}")
        else:
            print("Error: Could not connect to Lichess")
            return False

        print(f"\nAccepting time controls: {', '.join(self.time_controls)}")
        print("Bot is now running. Press Ctrl+C to stop.\n")

        # Start bot
        self.running = True
        try:
            self.bot.start()
        except KeyboardInterrupt:
            print("\nBot stopped by user")
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            self.stop()

        return True

    def stop(self):
        """Stop the bot."""
        if self.running:
            print("Stopping bot...")
            self.running = False

            if self.bot:
                # Resign any active games
                print("Resigning active games...")
                # (LichessBot would handle this)

            print("Bot stopped successfully")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Deploy Prometheus chess agent to Lichess',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy with default random agent
  python scripts/deploy_lichess_bot.py --token YOUR_TOKEN

  # Deploy with trained model
  python scripts/deploy_lichess_bot.py --token YOUR_TOKEN --model models/chess_agent.h5

  # Deploy Prometheus agent (online learning)
  python scripts/deploy_lichess_bot.py --token YOUR_TOKEN --agent prometheus

  # Accept only blitz games
  python scripts/deploy_lichess_bot.py --token YOUR_TOKEN --time blitz

Environment Variables:
  LICHESS_TOKEN    Lichess API token (alternative to --token)
        """
    )

    parser.add_argument(
        '--token',
        type=str,
        help='Lichess API token (or set LICHESS_TOKEN env var)'
    )

    parser.add_argument(
        '--model',
        type=str,
        help='Path to trained model file (.h5)'
    )

    parser.add_argument(
        '--agent',
        type=str,
        choices=['prometheus', 'static'],
        default='prometheus',
        help='Agent type (default: prometheus)'
    )

    parser.add_argument(
        '--time',
        type=str,
        nargs='+',
        choices=['bullet', 'blitz', 'rapid', 'classical'],
        help='Accepted time controls (default: blitz rapid classical)'
    )

    parser.add_argument(
        '--max-games',
        type=int,
        default=None,
        help='Maximum number of games to play (default: unlimited)'
    )

    args = parser.parse_args()

    # Get token
    token = args.token or os.environ.get('LICHESS_TOKEN')
    if not token:
        print("Error: Lichess API token required")
        print("Provide via --token argument or LICHESS_TOKEN environment variable")
        print("\nTo get a token:")
        print("1. Go to https://lichess.org/account/oauth/token")
        print("2. Create token with 'bot:play' scope")
        print("3. Make sure your account is upgraded to BOT status")
        return 1

    # Create deployment
    deployment = BotDeployment(
        token=token,
        model_path=args.model,
        agent_type=args.agent,
        time_controls=args.time
    )

    # Start bot
    success = deployment.start()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
