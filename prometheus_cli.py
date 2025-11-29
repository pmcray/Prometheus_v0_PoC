#!/usr/bin/env python3
"""
Prometheus CLI - Command-line interface for Prometheus AI system

Usage:
    prometheus train --game go --board-size 9 --games 100
    prometheus evaluate --model1 models/a.h5 --model2 models/b.h5
    prometheus deploy --platform ogs --model models/go_9x9.h5
    prometheus benchmark --model models/go_9x9.h5
    prometheus quickstart
"""

import argparse
import sys
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description='Prometheus AI - Recursive Self-Improvement Framework',
        epilog='For detailed help on each command, use: prometheus <command> --help'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # ========== TRAIN COMMAND ==========
    train_parser = subparsers.add_parser('train', help='Train a new agent')
    train_parser.add_argument('--game', required=True, choices=['go', 'chess'],
                             help='Game to train on')
    train_parser.add_argument('--board-size', type=int, default=9,
                             choices=[9, 13, 19],
                             help='Board size (for Go)')
    train_parser.add_argument('--num-games', type=int, default=100,
                             help='Number of training games')
    train_parser.add_argument('--strength', default='medium',
                             choices=['light', 'medium', 'strong', 'ultra'],
                             help='Model size/strength')
    train_parser.add_argument('--mcts', action='store_true',
                             help='Enable MCTS during training')
    train_parser.add_argument('--mcts-sims', type=int, default=400,
                             help='MCTS simulations per move')
    train_parser.add_argument('--output', type=str,
                             help='Output model path')
    train_parser.add_argument('--evaluate', action='store_true',
                             help='Evaluate after training')
    train_parser.add_argument('--visualize', action='store_true',
                             help='Show training visualization')
    train_parser.add_argument('--gpu', action='store_true',
                             help='Use GPU if available')

    # ========== EVALUATE COMMAND ==========
    eval_parser = subparsers.add_parser('evaluate', help='Evaluate agents')
    eval_parser.add_argument('--model1', required=True,
                            help='Path to first model')
    eval_parser.add_argument('--model2',
                            help='Path to second model (or "random")')
    eval_parser.add_argument('--num-games', type=int, default=50,
                            help='Number of evaluation games')
    eval_parser.add_argument('--game', choices=['go', 'chess'],
                            help='Game type (auto-detected if not specified)')
    eval_parser.add_argument('--board-size', type=int,
                            help='Board size (for Go, auto-detected if not specified)')
    eval_parser.add_argument('--tournament', action='store_true',
                            help='Run round-robin tournament')
    eval_parser.add_argument('--visualize', action='store_true',
                            help='Show evaluation results')

    # ========== DEPLOY COMMAND ==========
    deploy_parser = subparsers.add_parser('deploy', help='Deploy bot to online platform')
    deploy_parser.add_argument('--platform', required=True,
                               choices=['ogs', 'lichess'],
                               help='Platform to deploy to')
    deploy_parser.add_argument('--model', required=True,
                               help='Path to trained model')
    deploy_parser.add_argument('--board-sizes', nargs='+', type=int,
                               help='Board sizes to accept (Go only)')
    deploy_parser.add_argument('--mcts', action='store_true',
                               help='Enable MCTS')
    deploy_parser.add_argument('--mcts-sims', type=int, default=400,
                               help='MCTS simulations')
    deploy_parser.add_argument('--time-control', nargs='+',
                               choices=['bullet', 'blitz', 'rapid', 'classical', 'correspondence'],
                               help='Time controls to accept')
    deploy_parser.add_argument('--auto-accept', action='store_true',
                               help='Auto-accept challenges')
    deploy_parser.add_argument('--max-games', type=int, default=5,
                               help='Maximum concurrent games')

    # ========== BENCHMARK COMMAND ==========
    benchmark_parser = subparsers.add_parser('benchmark', help='Benchmark model performance')
    benchmark_parser.add_argument('--model', required=True,
                                 help='Path to model to benchmark')
    benchmark_parser.add_argument('--metric', nargs='+',
                                 choices=['inference', 'mcts', 'memory', 'all'],
                                 default=['all'],
                                 help='Metrics to benchmark')
    benchmark_parser.add_argument('--num-runs', type=int, default=100,
                                 help='Number of benchmark runs')
    benchmark_parser.add_argument('--mcts-sims', nargs='+', type=int,
                                 default=[100, 400, 800],
                                 help='MCTS simulation counts to test')
    benchmark_parser.add_argument('--output', type=str,
                                 help='Save results to file')

    # ========== COMPARE COMMAND ==========
    compare_parser = subparsers.add_parser('compare', help='Compare two models head-to-head')
    compare_parser.add_argument('--model1', required=True,
                               help='Path to first model (or "random")')
    compare_parser.add_argument('--model2', required=True,
                               help='Path to second model (or "random")')
    compare_parser.add_argument('--game', choices=['go', 'chess'],
                               help='Game type (auto-detected if not specified)')
    compare_parser.add_argument('--board-size', type=int, default=9,
                               help='Board size (for Go)')
    compare_parser.add_argument('--num-games', type=int, default=50,
                               help='Number of games to play')
    compare_parser.add_argument('--mcts1', type=int, default=0,
                               help='MCTS simulations for model1 (0 = no MCTS)')
    compare_parser.add_argument('--mcts2', type=int, default=0,
                               help='MCTS simulations for model2 (0 = no MCTS)')
    compare_parser.add_argument('--output', type=str,
                               help='Save comparison results to file')

    # ========== TRANSFER COMMAND ==========
    transfer_parser = subparsers.add_parser('transfer', help='Transfer learning between board sizes')
    transfer_parser.add_argument('--source', required=True,
                                help='Source model path')
    transfer_parser.add_argument('--source-size', type=int, required=True,
                                help='Source board size')
    transfer_parser.add_argument('--target-size', type=int, required=True,
                                help='Target board size')
    transfer_parser.add_argument('--fine-tune-games', type=int, default=100,
                                help='Fine-tuning games')
    transfer_parser.add_argument('--output', type=str,
                                help='Output model path')
    transfer_parser.add_argument('--evaluate', action='store_true',
                                help='Evaluate before and after')

    # ========== QUICKSTART COMMAND ==========
    quickstart_parser = subparsers.add_parser('quickstart',
                                             help='Quick start guide and demos')
    quickstart_parser.add_argument('--download-models', action='store_true',
                                  help='Download pre-trained models')
    quickstart_parser.add_argument('--run-demo', action='store_true',
                                  help='Run interactive demo')
    quickstart_parser.add_argument('--game', choices=['go', 'chess'],
                                  default='go',
                                  help='Game for demo')

    # ========== VERSION COMMAND ==========
    version_parser = subparsers.add_parser('version', help='Show version information')

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to appropriate handler
    if args.command == 'train':
        handle_train(args)
    elif args.command == 'evaluate':
        handle_evaluate(args)
    elif args.command == 'deploy':
        handle_deploy(args)
    elif args.command == 'benchmark':
        handle_benchmark(args)
    elif args.command == 'compare':
        handle_compare(args)
    elif args.command == 'transfer':
        handle_transfer(args)
    elif args.command == 'quickstart':
        handle_quickstart(args)
    elif args.command == 'version':
        handle_version(args)


def handle_train(args):
    """Handle train command."""
    print(f"🎯 Training {args.game} agent...")
    print(f"   Board size: {args.board_size}")
    print(f"   Games: {args.num_games}")
    print(f"   Strength: {args.strength}")
    print(f"   MCTS: {'Yes' if args.mcts else 'No'}")

    if args.game == 'go':
        from prometheus.models.go_models import PrometheusGoAgent
        from prometheus.environments.go import GoEnvironment
        from prometheus.training.go_training import train_go_agent
        from prometheus.configs import ModelBuilder

        # Create agent
        agent = (
            ModelBuilder()
            .go(board_size=args.board_size)
            .strength(args.strength)
            .prometheus()
            .build()
        )

        # Add MCTS if requested
        if args.mcts:
            from prometheus.mcts import add_mcts
            agent = add_mcts(agent, num_simulations=args.mcts_sims)

        # Train
        trained_agent = train_go_agent(
            agent,
            num_games=args.num_games,
            verbose=True
        )

        # Save
        output_path = args.output or f'models/{args.game}_{args.board_size}x{args.board_size}.h5'
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        trained_agent.model.save(output_path)
        print(f"\n✓ Model saved: {output_path}")

        # Evaluate
        if args.evaluate:
            from prometheus.evaluation.benchmark import GoEvaluator
            from prometheus.models.go_models import RandomGoAgent

            evaluator = GoEvaluator(board_size=args.board_size)
            env = GoEnvironment(board_size=args.board_size)
            baseline = RandomGoAgent(board_size=args.board_size)

            result = evaluator.evaluate_matchup(
                trained_agent,
                baseline,
                env,
                num_games=20,
                verbose=True
            )
            print(f"\n✓ Win rate: {result['agent1_win_rate']:.1%}")
            print(f"✓ ELO: {result['agent1_elo']:.0f}")

        # Visualize
        if args.visualize:
            # TODO: Add visualization
            print("\n📊 Visualization coming soon...")

    elif args.game == 'chess':
        print("Chess training not fully implemented yet")
        print("Use: python examples/train_chess_agent.py")

    print("\n✓ Training complete!")


def handle_evaluate(args):
    """Handle evaluate command."""
    print(f"📊 Evaluating models...")
    print(f"   Model 1: {args.model1}")
    print(f"   Model 2: {args.model2 or 'random'}")
    print(f"   Games: {args.num_games}")

    # TODO: Implement full evaluation
    print("\n✓ Evaluation would run here")
    print("For now, use: python examples/evaluate_agents.py")


def handle_deploy(args):
    """Handle deploy command."""
    print(f"🚀 Deploying to {args.platform}...")
    print(f"   Model: {args.model}")
    print(f"   MCTS: {'Yes' if args.mcts else 'No'}")
    print(f"   Max games: {args.max_games}")

    if args.platform == 'ogs':
        print("\n📝 Deployment steps:")
        print("1. Create OGS bot account at https://online-go.com")
        print("2. Get API token from Profile → Settings → API Access")
        print("3. Add token to .env file:")
        print("   OGS_API_TOKEN=your_token_here")
        print(f"4. Run: python scripts/deploy_ogs_bot.py --model {args.model}")

    elif args.platform == 'lichess':
        print("\n📝 Deployment steps:")
        print("1. Create Lichess account at https://lichess.org")
        print("2. Get API token from https://lichess.org/account/oauth/token")
        print("3. Upgrade account to BOT (irreversible!)")
        print("4. Add token to .env file:")
        print("   LICHESS_TOKEN=your_token_here")
        print(f"5. Run: python scripts/deploy_lichess_bot.py --model {args.model}")

    print("\n✓ See deployment guide in notebooks/deployment_workshop.ipynb")


def handle_benchmark(args):
    """Handle benchmark command."""
    print(f"⚡ Benchmarking model: {args.model}")
    print(f"   Metrics: {', '.join(args.metric)}")
    print(f"   Runs: {args.num_runs}")

    # TODO: Implement benchmarking
    print("\n✓ Benchmark results would appear here")
    print("For now, see: notebooks/performance_optimization.ipynb")


def handle_compare(args):
    """Handle model comparison command."""
    import subprocess

    print(f"🔬 Comparing models head-to-head...")
    print(f"   Model 1: {args.model1}")
    print(f"   Model 2: {args.model2}")
    print(f"   Games: {args.num_games}")
    if args.mcts1 > 0:
        print(f"   MCTS 1: {args.mcts1} simulations")
    if args.mcts2 > 0:
        print(f"   MCTS 2: {args.mcts2} simulations")
    print()

    # Build command for compare_models.py
    cmd = [
        sys.executable,
        'scripts/compare_models.py',
        '--model1', args.model1,
        '--model2', args.model2,
        '--num-games', str(args.num_games),
    ]

    if args.game:
        cmd.extend(['--game', args.game])

    if args.board_size:
        cmd.extend(['--board-size', str(args.board_size)])

    if args.mcts1 > 0:
        cmd.extend(['--mcts1', str(args.mcts1)])

    if args.mcts2 > 0:
        cmd.extend(['--mcts2', str(args.mcts2)])

    if args.output:
        cmd.extend(['--output', args.output])

    # Run comparison
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


def handle_transfer(args):
    """Handle transfer learning command."""
    print(f"🔄 Transfer learning: {args.source_size}×{args.source_size} → {args.target_size}×{args.target_size}")
    print(f"   Source: {args.source}")
    print(f"   Fine-tune games: {args.fine_tune_games}")

    # TODO: Implement transfer
    print("\n✓ Transfer learning would run here")
    print("For now, use: python examples/transfer_learning.py")
    print("Or see: notebooks/transfer_learning_tutorial.ipynb")


def handle_quickstart(args):
    """Handle quickstart command."""
    print("=" * 70)
    print("🚀 PROMETHEUS QUICKSTART")
    print("=" * 70)
    print()

    print("Welcome to Prometheus - Recursive Self-Improvement Framework!")
    print()

    if args.download_models:
        print("📥 Downloading pre-trained models...")
        print()
        print("Models will be downloaded to: ./models/")
        print()
        print("Available models:")
        print("  - go_9x9.h5 (9×9 Go, ~1200 ELO)")
        print("  - go_19x19.h5 (19×19 Go, ~1400 ELO)")
        print("  - chess.h5 (Chess, ~1300 ELO)")
        print()
        print("⚠️  Model zoo not yet implemented")
        print("Train your own: prometheus train --game go --board-size 9 --games 100")

    elif args.run_demo:
        print(f"🎮 Running {args.game} demo...")
        print()
        print("This would launch an interactive demo")
        print()
        print("For now, open a notebook:")
        print("  jupyter notebook notebooks/good_notebook_5_executive_demo.ipynb")

    else:
        print("📚 Quick Start Guide")
        print()
        print("1. Train your first agent (3 minutes):")
        print("   $ prometheus train --game go --board-size 9 --games 50")
        print()
        print("2. Evaluate against random player:")
        print("   $ prometheus evaluate --model1 models/go_9x9.h5 --model2 random")
        print()
        print("3. Deploy to online server:")
        print("   $ prometheus deploy --platform ogs --model models/go_9x9.h5")
        print()
        print("4. Run benchmarks:")
        print("   $ prometheus benchmark --model models/go_9x9.h5")
        print()
        print("📖 For detailed tutorials, open the notebooks:")
        print("   - notebooks/transfer_learning_tutorial.ipynb")
        print("   - notebooks/deployment_workshop.ipynb")
        print("   - notebooks/performance_optimization.ipynb")
        print()
        print("💡 Try: prometheus quickstart --run-demo")

    print()
    print("✓ Ready to go! Need help? prometheus <command> --help")


def handle_version(args):
    """Handle version command."""
    print("Prometheus v0.69")
    print("Empirical Validation of Recursive Self-Improvement")
    print()
    print("Components:")
    print("  - Core Framework: v0.69")
    print("  - Go Engine: MCTS + Neural Network")
    print("  - Chess Engine: UCI-compatible")
    print("  - Transfer Learning: Board size transfer")
    print("  - Deployment: OGS, Lichess")
    print()
    print("GitHub: https://github.com/pmcray/Prometheus_v0_PoC")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
