#!/usr/bin/env python3
"""
Prometheus 30-Second Quick Demo

Impressive instant demonstration showing AI learning and playing.
Perfect for first impressions, presentations, and README demos.

Usage:
    python scripts/quick_demo.py

    # Choose game
    python scripts/quick_demo.py --game chess

    # Skip delays
    python scripts/quick_demo.py --fast
"""

import argparse
import sys
import time
from typing import Tuple

def print_slow(text: str, delay: float = 0.03, fast: bool = False):
    """Print text with typewriter effect."""
    if fast:
        print(text)
        return

    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()


def print_header(text: str, fast: bool = False):
    """Print formatted header."""
    if not fast:
        time.sleep(0.3)
    print("\n" + "=" * 70)
    print_slow(f"  {text}", fast=fast)
    print("=" * 70 + "\n")


def animate_progress(task: str, duration: float = 1.0, fast: bool = False):
    """Show progress animation."""
    if fast:
        print(f"✓ {task}")
        return

    print(f"{task}...", end='', flush=True)
    time.sleep(duration)
    print(" ✓")


def demo_go(fast: bool = False):
    """Run Go demo."""
    print_header("🔥 PROMETHEUS AI - GO DEMONSTRATION", fast)

    print_slow("Creating lightweight AI agent...", fast=fast)
    animate_progress("Initializing neural network", 0.5, fast)
    animate_progress("Loading Go rules engine", 0.3, fast)

    try:
        from prometheus.models.go_models import create_go_agent, RandomGoAgent
        from prometheus.environments.go import GoEnvironment

        # Create agents
        env = GoEnvironment(board_size=9)
        ai_agent = create_go_agent(board_size=9, strength='weak')
        random_agent = RandomGoAgent()

        print_slow("\n✓ AI Agent ready!", fast=fast)

        if not fast:
            time.sleep(0.5)

        print_header("PLAYING: AI vs Random (3 moves)", fast)

        state = env.reset()

        for move_num in range(3):
            # AI move
            if not fast:
                time.sleep(0.3)

            try:
                ai_move = ai_agent.select_move(state)
                print(f"Move {move_num + 1} - AI plays: {ai_move}")

                state, _, done, _ = env.step(ai_move)
                if done:
                    break

                # Random move
                random_move = random_agent.select_move(state)
                print(f"Move {move_num + 1} - Random plays: {random_move}")

                state, _, done, _ = env.step(random_move)
                if done:
                    break

            except Exception as e:
                print(f"  (Game ended: {e})")
                break

        print_slow("\n✓ Demo complete!", fast=fast)

    except ImportError as e:
        print(f"\n⚠️  Could not import Prometheus modules: {e}")
        print("   Install with: pip install -e .")
        return False

    return True


def demo_chess(fast: bool = False):
    """Run Chess demo."""
    print_header("♟️  PROMETHEUS AI - CHESS DEMONSTRATION", fast)

    print_slow("Creating chess AI...", fast=fast)
    animate_progress("Initializing neural network", 0.5, fast)
    animate_progress("Loading chess rules", 0.3, fast)

    try:
        from prometheus.models.chess_models import create_chess_agent, RandomChessAgent
        from prometheus.environments.chess_env import ChessEnvironment

        # Create agents
        env = ChessEnvironment()
        ai_agent = create_chess_agent(strength='weak')
        random_agent = RandomChessAgent()

        print_slow("\n✓ AI Agent ready!", fast=fast)

        if not fast:
            time.sleep(0.5)

        print_header("PLAYING: AI vs Random (3 moves)", fast)

        state = env.reset()

        for move_num in range(3):
            # AI move
            if not fast:
                time.sleep(0.3)

            try:
                ai_move = ai_agent.select_move(state)
                print(f"Move {move_num + 1} - AI (White) plays: {ai_move}")

                state, _, done, _ = env.step(ai_move)
                if done:
                    break

                # Random move
                random_move = random_agent.select_move(state)
                print(f"Move {move_num + 1} - Random (Black) plays: {random_move}")

                state, _, done, _ = env.step(random_move)
                if done:
                    break

            except Exception as e:
                print(f"  (Game ended: {e})")
                break

        print_slow("\n✓ Demo complete!", fast=fast)

    except ImportError as e:
        print(f"\n⚠️  Could not import Prometheus modules: {e}")
        print("   Install with: pip install -e .")
        return False

    return True


def demo_stats(fast: bool = False):
    """Show system stats."""
    print_header("📊 SYSTEM STATUS", fast)

    # Check for models
    from pathlib import Path

    models_dir = Path("models/pretrained")
    if models_dir.exists():
        models = list(models_dir.glob("*.h5"))
        print(f"✓ Trained Models: {len(models)}")
        for model in models[:3]:
            print(f"   • {model.name}")
    else:
        print("✓ Trained Models: 0 (run training to create)")

    # Check for benchmarks
    benchmarks_dir = Path("benchmarks")
    if benchmarks_dir.exists():
        benchmarks = list(benchmarks_dir.glob("*.json"))
        print(f"✓ Benchmark Results: {len(benchmarks)}")
    else:
        print("✓ Benchmark Results: 0")

    # Check Python version
    import sys
    print(f"✓ Python: {sys.version.split()[0]}")

    # Check TensorFlow
    try:
        import tensorflow as tf
        print(f"✓ TensorFlow: {tf.__version__}")

        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            print(f"✓ GPU: {len(gpus)} device(s) detected")
        else:
            print("✓ GPU: CPU mode (no GPU detected)")
    except ImportError:
        print("⚠️  TensorFlow: Not installed")


def show_next_steps(fast: bool = False):
    """Show next steps."""
    print_header("🚀 NEXT STEPS", fast)

    print_slow("Train your first model:", fast=fast)
    print("  $ prometheus train --game go --board-size 9 --games 50\n")

    print_slow("Compare models:", fast=fast)
    print("  $ prometheus compare --model1 A.h5 --model2 B.h5 --num-games 20\n")

    print_slow("Deploy a bot:", fast=fast)
    print("  $ docker-compose up -d\n")

    print_slow("Explore tutorials:", fast=fast)
    print("  • notebooks/mcts_deep_dive.ipynb")
    print("  • notebooks/transfer_learning_tutorial.ipynb\n")

    print_slow("Get help:", fast=fast)
    print("  • FAQ.md - Frequently asked questions")
    print("  • TROUBLESHOOTING.md - Common issues\n")


def main():
    parser = argparse.ArgumentParser(
        description="Prometheus 30-second quick demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--game', default='go', choices=['go', 'chess'],
                        help='Game to demonstrate (default: go)')
    parser.add_argument('--fast', action='store_true',
                        help='Skip animation delays')

    args = parser.parse_args()

    # ASCII art
    print("""
    ██████╗ ██████╗  ██████╗ ███╗   ███╗███████╗████████╗██╗  ██╗███████╗██╗   ██╗███████╗
    ██╔══██╗██╔══██╗██╔═══██╗████╗ ████║██╔════╝╚══██╔══╝██║  ██║██╔════╝██║   ██║██╔════╝
    ██████╔╝██████╔╝██║   ██║██╔████╔██║█████╗     ██║   ███████║█████╗  ██║   ██║███████╗
    ██╔═══╝ ██╔══██╗██║   ██║██║╚██╔╝██║██╔══╝     ██║   ██╔══██║██╔══╝  ██║   ██║╚════██║
    ██║     ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗   ██║   ██║  ██║███████╗╚██████╔╝███████║
    ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚══════╝
    """)

    print_slow("        Recursive Self-Improvement AI Framework", fast=args.fast)
    print_slow("        🔬 Research • 🎮 Play • 🚀 Deploy\n", fast=args.fast)

    if not args.fast:
        time.sleep(1)

    # Run demo
    if args.game == 'go':
        success = demo_go(fast=args.fast)
    else:
        success = demo_chess(fast=args.fast)

    if not success:
        return 1

    # Show stats
    demo_stats(fast=args.fast)

    # Next steps
    show_next_steps(fast=args.fast)

    # Footer
    print("=" * 70)
    print_slow("Thank you for trying Prometheus! ⭐ Star us on GitHub!", fast=args.fast)
    print("=" * 70)

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nFor help, see:")
        print("  • FAQ.md")
        print("  • TROUBLESHOOTING.md")
        print("  • python scripts/verify_phase_b_readiness.py")
        sys.exit(1)
