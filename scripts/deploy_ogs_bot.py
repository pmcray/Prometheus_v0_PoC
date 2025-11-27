#!/usr/bin/env python3
"""
OGS (Online Go Server) Bot Deployment Script

Deploys a trained Prometheus Go agent to OGS.

Usage:
    python scripts/deploy_ogs_bot.py --username YOUR_USERNAME --password YOUR_PASSWORD --model path/to/model.h5

Requirements:
    - OGS account
    - Trained Go model
    - gtp2ogs bridge (recommended) or direct Socket.IO connection

Features:
    - Automatic game acceptance
    - Configurable board sizes
    - ELO tracking
    - Graceful shutdown

Note:
    For production deployment, see prometheus/online_play/OGS_INTEGRATION_GUIDE.md
    This script provides basic demo functionality.
"""

import argparse
import sys
import os
import signal
from pathlib import Path
from typing import Optional, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from prometheus.online_play.ogs import OGSBot
from prometheus.models.go_models import PrometheusGoAgent, StaticGoAgent
from prometheus.models.go_mcts import GoMCTSAgent
from prometheus.environments.go import GoEnvironment
import tensorflow as tf


class OGSDeployment:
    """Manages OGS bot deployment and lifecycle."""

    def __init__(self, username: str, password: str,
                 model_path: Optional[str] = None,
                 agent_type: str = 'prometheus',
                 board_sizes: Optional[List[int]] = None,
                 use_mcts: bool = False,
                 mcts_simulations: int = 800):
        """
        Initialize OGS deployment.

        Args:
            username: OGS username
            password: OGS password
            model_path: Path to trained model (optional)
            agent_type: 'prometheus' or 'static'
            board_sizes: Accepted board sizes (e.g., [9, 13, 19])
            use_mcts: Whether to enhance agent with MCTS
            mcts_simulations: Number of MCTS simulations per move
        """
        self.username = username
        self.password = password
        self.model_path = model_path
        self.agent_type = agent_type
        self.board_sizes = board_sizes or [9, 13, 19]
        self.use_mcts = use_mcts
        self.mcts_simulations = mcts_simulations

        self.bot = None
        self.agent = None
        self.running = False

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\nReceived shutdown signal. Stopping bot...")
        self.stop()
        sys.exit(0)

    def create_agent(self, board_size: int = 9) -> Any:
        """
        Create Go agent for specified board size.

        Args:
            board_size: Board size

        Returns:
            Go agent instance
        """
        print(f"Creating {self.agent_type} agent for {board_size}x{board_size}...")

        # Create base agent
        if self.agent_type == 'prometheus':
            agent = PrometheusGoAgent(board_size=board_size)
        else:
            agent = StaticGoAgent(board_size=board_size)

        # Load model if provided
        if self.model_path:
            model_file = self.model_path.replace('SIZE', str(board_size))
            if os.path.exists(model_file):
                print(f"Loading model from {model_file}")
                agent.model = tf.keras.models.load_model(model_file)
                agent.trainable = False  # Freeze for deployment
            else:
                print(f"Warning: Model file not found: {model_file}")
                print("Using random initialization")

        # Enhance with MCTS if requested
        if self.use_mcts:
            print(f"Enhancing with MCTS ({self.mcts_simulations} simulations)...")
            agent = GoMCTSAgent(
                base_agent=agent,
                num_simulations=self.mcts_simulations
            )

        return agent

    def start(self):
        """Start the OGS bot."""
        print("="*60)
        print("OGS BOT DEPLOYMENT")
        print("="*60)
        print("\nNOTE: This is a demo implementation.")
        print("For production deployment, see:")
        print("  prometheus/online_play/OGS_INTEGRATION_GUIDE.md")
        print()

        # Create agents for each board size
        agents = {}
        for size in self.board_sizes:
            agents[size] = self.create_agent(board_size=size)

        # Create bot
        print("Connecting to OGS...")
        try:
            self.bot = OGSBot(
                username=self.username,
                password=self.password,
                agents=agents
            )

            # Connect
            if self.bot.connect():
                print(f"Connected as: {self.username}")
            else:
                print("Error: Could not connect to OGS")
                return False

        except Exception as e:
            print(f"Error creating bot: {e}")
            print("\nNote: OGSBot requires Socket.IO or GTP bridge.")
            print("See OGS_INTEGRATION_GUIDE.md for setup instructions.")
            return False

        print(f"\nAccepting board sizes: {', '.join(map(str, self.board_sizes))}")
        if self.use_mcts:
            print(f"MCTS enabled: {self.mcts_simulations} simulations per move")
        print("\nBot is now running. Press Ctrl+C to stop.\n")

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
                print("Disconnecting from OGS...")
                self.bot.disconnect()

            print("Bot stopped successfully")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Deploy Prometheus Go agent to OGS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy with default random agent (demo mode)
  python scripts/deploy_ogs_bot.py --username YOUR_USERNAME --password YOUR_PASSWORD

  # Deploy with trained model
  python scripts/deploy_ogs_bot.py --username USER --password PASS --model models/go_SIZE.h5

  # Deploy with MCTS enhancement
  python scripts/deploy_ogs_bot.py --username USER --password PASS --mcts --simulations 400

  # Accept only 9x9 games
  python scripts/deploy_ogs_bot.py --username USER --password PASS --sizes 9

Environment Variables:
  OGS_USERNAME    OGS username (alternative to --username)
  OGS_PASSWORD    OGS password (alternative to --password)

Production Deployment:
  For production use, please see prometheus/online_play/OGS_INTEGRATION_GUIDE.md
  This script is for testing and demonstration purposes.

  Recommended approach: Use gtp2ogs bridge with GTP protocol
  See: https://github.com/online-go/gtp2ogs
        """
    )

    parser.add_argument(
        '--username',
        type=str,
        help='OGS username (or set OGS_USERNAME env var)'
    )

    parser.add_argument(
        '--password',
        type=str,
        help='OGS password (or set OGS_PASSWORD env var)'
    )

    parser.add_argument(
        '--model',
        type=str,
        help='Path to trained model file (.h5). Use SIZE placeholder for board size (e.g., go_SIZE.h5)'
    )

    parser.add_argument(
        '--agent',
        type=str,
        choices=['prometheus', 'static'],
        default='prometheus',
        help='Agent type (default: prometheus)'
    )

    parser.add_argument(
        '--sizes',
        type=int,
        nargs='+',
        choices=[9, 13, 19],
        help='Accepted board sizes (default: 9 13 19)'
    )

    parser.add_argument(
        '--mcts',
        action='store_true',
        help='Enable MCTS enhancement'
    )

    parser.add_argument(
        '--simulations',
        type=int,
        default=800,
        help='MCTS simulations per move (default: 800)'
    )

    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run in demo mode (no actual OGS connection)'
    )

    args = parser.parse_args()

    # Get credentials
    username = args.username or os.environ.get('OGS_USERNAME')
    password = args.password or os.environ.get('OGS_PASSWORD')

    if not username or not password:
        print("Error: OGS credentials required")
        print("Provide via --username/--password or OGS_USERNAME/OGS_PASSWORD env vars")
        print("\nTo create an OGS account:")
        print("1. Go to https://online-go.com/")
        print("2. Create a free account")
        print("3. Use those credentials here")
        return 1

    # Demo mode warning
    if args.demo:
        print("\n" + "="*60)
        print("DEMO MODE - No actual OGS connection will be made")
        print("="*60 + "\n")

        # Create and test agent
        deployment = OGSDeployment(
            username=username,
            password=password,
            model_path=args.model,
            agent_type=args.agent,
            board_sizes=args.sizes,
            use_mcts=args.mcts,
            mcts_simulations=args.simulations
        )

        # Just create agent to verify setup
        agent = deployment.create_agent(board_size=9)
        print(f"\nAgent created successfully: {agent.name}")
        print("To deploy for real, remove --demo flag")
        print("\nSee prometheus/online_play/OGS_INTEGRATION_GUIDE.md for production deployment")
        return 0

    # Create deployment
    deployment = OGSDeployment(
        username=username,
        password=password,
        model_path=args.model,
        agent_type=args.agent,
        board_sizes=args.sizes,
        use_mcts=args.mcts,
        mcts_simulations=args.simulations
    )

    # Start bot
    success = deployment.start()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
