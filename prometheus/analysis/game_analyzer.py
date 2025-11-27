"""
Game Analysis Tools

Provides post-game analysis for Chess and Go:
- Position evaluation
- Critical moments identification
- Mistake detection
- Opening/middlegame/endgame analysis
- Suggested improvements

Usage:
    analyzer = GoGameAnalyzer(agent=trained_agent)
    analysis = analyzer.analyze_game(game_history)
    analyzer.print_report(analysis)
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict


class PositionEvaluator:
    """
    Evaluate board positions using agent's value network.

    Provides numerical evaluation of positions for analysis.
    """

    def __init__(self, agent):
        """
        Initialize evaluator with agent.

        Args:
            agent: Agent with predict() method that returns (policy, value)
        """
        self.agent = agent

    def evaluate(self, state: np.ndarray) -> float:
        """
        Evaluate position.

        Args:
            state: Board state

        Returns:
            Evaluation score (-1 to +1, positive favors current player)
        """
        try:
            policy, value = self.agent.predict(state)
            return float(value)
        except Exception as e:
            # Fallback for agents without predict method
            return 0.0


class GoGameAnalyzer:
    """
    Analyze Go games for insights and improvements.

    Features:
    - Move-by-move evaluation
    - Critical moments identification
    - Territory gain/loss tracking
    - Opening analysis
    - Endgame efficiency
    """

    def __init__(self, agent=None):
        """
        Initialize analyzer.

        Args:
            agent: Optional agent for position evaluation
        """
        self.agent = agent
        self.evaluator = PositionEvaluator(agent) if agent else None

    def analyze_game(self, game_result: Dict) -> Dict:
        """
        Analyze complete game.

        Args:
            game_result: Game result dictionary with history

        Returns:
            Analysis dictionary with insights
        """
        history = game_result.get('history', [])

        analysis = {
            'total_moves': len(history),
            'winner': game_result.get('winner', 'unknown'),
            'margin': game_result.get('margin', 0),
            'black_score': game_result.get('black_score', 0),
            'white_score': game_result.get('white_score', 0),
            'evaluations': [],
            'critical_moments': [],
            'mistakes': [],
            'phases': {}
        }

        # Evaluate each position
        if self.evaluator:
            for i, move_data in enumerate(history):
                state = move_data.get('state')
                if state is not None:
                    eval_score = self.evaluator.evaluate(state)
                    analysis['evaluations'].append({
                        'move_number': i,
                        'evaluation': eval_score,
                        'move': move_data.get('move'),
                        'player': move_data.get('player')
                    })

            # Find critical moments (large evaluation swings)
            analysis['critical_moments'] = self._find_critical_moments(
                analysis['evaluations']
            )

            # Find mistakes
            analysis['mistakes'] = self._find_mistakes(
                analysis['evaluations']
            )

        # Phase analysis
        analysis['phases'] = self._analyze_phases(history)

        # Overall statistics
        analysis['statistics'] = self._calculate_statistics(history)

        return analysis

    def _find_critical_moments(self, evaluations: List[Dict],
                               threshold: float = 0.3) -> List[Dict]:
        """
        Identify moments where evaluation changed significantly.

        Args:
            evaluations: List of position evaluations
            threshold: Minimum change to be considered critical

        Returns:
            List of critical moments
        """
        critical = []

        for i in range(1, len(evaluations)):
            prev_eval = evaluations[i-1]['evaluation']
            curr_eval = evaluations[i]['evaluation']

            change = abs(curr_eval - prev_eval)

            if change >= threshold:
                critical.append({
                    'move_number': evaluations[i]['move_number'],
                    'move': evaluations[i]['move'],
                    'player': evaluations[i]['player'],
                    'eval_before': prev_eval,
                    'eval_after': curr_eval,
                    'change': change,
                    'type': 'advantage_shift'
                })

        return critical

    def _find_mistakes(self, evaluations: List[Dict],
                       mistake_threshold: float = 0.2,
                       blunder_threshold: float = 0.4) -> List[Dict]:
        """
        Find mistakes and blunders.

        Args:
            evaluations: List of position evaluations
            mistake_threshold: Evaluation drop for mistake
            blunder_threshold: Evaluation drop for blunder

        Returns:
            List of mistakes
        """
        mistakes = []

        for i in range(1, len(evaluations)):
            prev_eval = evaluations[i-1]['evaluation']
            curr_eval = evaluations[i]['evaluation']

            # For alternating players, flip sign
            if evaluations[i]['player'] != evaluations[i-1]['player']:
                curr_eval = -curr_eval

            drop = prev_eval - curr_eval

            if drop >= mistake_threshold:
                severity = 'blunder' if drop >= blunder_threshold else 'mistake'

                mistakes.append({
                    'move_number': evaluations[i]['move_number'],
                    'move': evaluations[i]['move'],
                    'player': evaluations[i]['player'],
                    'severity': severity,
                    'eval_loss': drop
                })

        return mistakes

    def _analyze_phases(self, history: List[Dict]) -> Dict:
        """
        Analyze opening, middlegame, and endgame.

        Args:
            history: Game history

        Returns:
            Phase analysis
        """
        total_moves = len(history)

        # Simple division: first 25%, middle 50%, last 25%
        opening_end = total_moves // 4
        middlegame_end = 3 * total_moves // 4

        phases = {
            'opening': {
                'moves': history[:opening_end],
                'length': opening_end,
                'analysis': 'Opening phase'
            },
            'middlegame': {
                'moves': history[opening_end:middlegame_end],
                'length': middlegame_end - opening_end,
                'analysis': 'Middlegame phase'
            },
            'endgame': {
                'moves': history[middlegame_end:],
                'length': total_moves - middlegame_end,
                'analysis': 'Endgame phase'
            }
        }

        return phases

    def _calculate_statistics(self, history: List[Dict]) -> Dict:
        """
        Calculate game statistics.

        Args:
            history: Game history

        Returns:
            Statistics dictionary
        """
        stats = {
            'total_moves': len(history),
            'passes': 0,
            'black_moves': 0,
            'white_moves': 0,
        }

        for move_data in history:
            move = move_data.get('move')
            player = move_data.get('player')

            if move == ('pass',):
                stats['passes'] += 1

            if player == 1:  # Black
                stats['black_moves'] += 1
            else:  # White
                stats['white_moves'] += 1

        return stats

    def print_report(self, analysis: Dict, verbose: bool = True):
        """
        Print formatted analysis report.

        Args:
            analysis: Analysis dictionary
            verbose: Include detailed information
        """
        print("="*70)
        print("GAME ANALYSIS REPORT")
        print("="*70)

        # Game summary
        print(f"\nGame Summary:")
        print(f"  Winner: {analysis['winner']}")
        print(f"  Score: Black {analysis['black_score']:.1f}, "
              f"White {analysis['white_score']:.1f}")
        print(f"  Margin: {analysis['margin']:.1f}")
        print(f"  Total moves: {analysis['total_moves']}")

        # Statistics
        if 'statistics' in analysis:
            stats = analysis['statistics']
            print(f"\nStatistics:")
            print(f"  Black moves: {stats['black_moves']}")
            print(f"  White moves: {stats['white_moves']}")
            print(f"  Passes: {stats['passes']}")

        # Phases
        if 'phases' in analysis:
            phases = analysis['phases']
            print(f"\nGame Phases:")
            print(f"  Opening: {phases['opening']['length']} moves")
            print(f"  Middlegame: {phases['middlegame']['length']} moves")
            print(f"  Endgame: {phases['endgame']['length']} moves")

        # Critical moments
        if analysis['critical_moments']:
            print(f"\nCritical Moments ({len(analysis['critical_moments'])}):")
            for moment in analysis['critical_moments'][:5]:  # Show top 5
                print(f"  Move {moment['move_number']}: "
                      f"{moment['move']} by player {moment['player']}")
                print(f"    Evaluation: {moment['eval_before']:.2f} → "
                      f"{moment['eval_after']:.2f} "
                      f"(Δ {moment['change']:.2f})")

        # Mistakes
        if analysis['mistakes']:
            print(f"\nMistakes ({len(analysis['mistakes'])}):")

            blunders = [m for m in analysis['mistakes'] if m['severity'] == 'blunder']
            mistakes = [m for m in analysis['mistakes'] if m['severity'] == 'mistake']

            if blunders:
                print(f"  Blunders: {len(blunders)}")
                for blunder in blunders[:3]:
                    print(f"    Move {blunder['move_number']}: "
                          f"{blunder['move']} by player {blunder['player']} "
                          f"(Δ {blunder['eval_loss']:.2f})")

            if mistakes:
                print(f"  Mistakes: {len(mistakes)}")
                if verbose:
                    for mistake in mistakes[:3]:
                        print(f"    Move {mistake['move_number']}: "
                              f"{mistake['move']} by player {mistake['player']} "
                              f"(Δ {mistake['eval_loss']:.2f})")

        # Evaluation graph
        if verbose and analysis['evaluations']:
            print(f"\nEvaluation Graph:")
            self._print_eval_graph(analysis['evaluations'])

        print("="*70 + "\n")

    def _print_eval_graph(self, evaluations: List[Dict], width: int = 60):
        """
        Print ASCII evaluation graph.

        Args:
            evaluations: List of evaluations
            width: Graph width in characters
        """
        if not evaluations:
            return

        # Sample evaluations if too many
        if len(evaluations) > width:
            step = len(evaluations) // width
            sampled = [evaluations[i] for i in range(0, len(evaluations), step)]
        else:
            sampled = evaluations

        # Normalize to [-1, 1] range
        values = [e['evaluation'] for e in sampled]
        min_val = min(values)
        max_val = max(values)

        if max_val == min_val:
            return

        # Create graph
        graph_height = 11  # -1.0 to 1.0 in 0.2 increments
        lines = []

        for level in np.linspace(1.0, -1.0, graph_height):
            line = f"{level:5.1f} |"

            for val in values:
                if abs(val - level) < 0.15:
                    line += "*"
                elif level == 0:
                    line += "-"
                else:
                    line += " "

            lines.append(line)

        # Print graph
        for line in lines:
            print(line)

        print("      +" + "-" * len(values))
        print(f"       Move 0{' ' * (len(values) - 10)}Move {len(evaluations)}")


class ChessGameAnalyzer:
    """
    Analyze Chess games.

    Similar to Go analyzer but for chess-specific features:
    - Material balance
    - King safety
    - Piece activity
    - Pawn structure
    """

    def __init__(self, agent=None):
        """
        Initialize chess analyzer.

        Args:
            agent: Optional agent for position evaluation
        """
        self.agent = agent
        self.evaluator = PositionEvaluator(agent) if agent else None

    def analyze_game(self, game_result: Dict) -> Dict:
        """
        Analyze chess game.

        Args:
            game_result: Game result dictionary

        Returns:
            Analysis dictionary
        """
        # Similar structure to Go analyzer
        # Would implement chess-specific analysis

        analysis = {
            'moves': game_result.get('moves', 0),
            'result': game_result.get('result', 'unknown'),
            'material_balance': [],
            'king_safety': [],
            'tactical_moments': []
        }

        return analysis

    def print_report(self, analysis: Dict):
        """Print chess analysis report."""
        print("="*70)
        print("CHESS GAME ANALYSIS")
        print("="*70)
        print(f"Result: {analysis['result']}")
        print(f"Moves: {analysis['moves']}")
        print("="*70 + "\n")


class BatchAnalyzer:
    """
    Analyze multiple games for aggregate insights.

    Provides:
    - Common mistakes across games
    - Positional weaknesses
    - Time management
    - Opening repertoire
    """

    def __init__(self, analyzer):
        """
        Initialize batch analyzer.

        Args:
            analyzer: Game analyzer instance
        """
        self.analyzer = analyzer
        self.game_analyses = []

    def add_game(self, game_result: Dict):
        """
        Add game for batch analysis.

        Args:
            game_result: Game result dictionary
        """
        analysis = self.analyzer.analyze_game(game_result)
        self.game_analyses.append(analysis)

    def get_aggregate_report(self) -> Dict:
        """
        Generate aggregate analysis across all games.

        Returns:
            Aggregate statistics and insights
        """
        if not self.game_analyses:
            return {}

        total_games = len(self.game_analyses)

        # Aggregate statistics
        report = {
            'total_games': total_games,
            'wins': 0,
            'losses': 0,
            'draws': 0,
            'avg_moves': 0,
            'total_mistakes': 0,
            'total_blunders': 0,
            'common_mistakes': defaultdict(int),
            'phase_performance': {
                'opening': 0,
                'middlegame': 0,
                'endgame': 0
            }
        }

        for analysis in self.game_analyses:
            # Count results
            winner = analysis.get('winner', 'unknown')
            if winner == 'black':
                report['wins'] += 1
            elif winner == 'white':
                report['losses'] += 1
            else:
                report['draws'] += 1

            # Average moves
            report['avg_moves'] += analysis.get('total_moves', 0)

            # Mistakes
            mistakes = analysis.get('mistakes', [])
            for mistake in mistakes:
                if mistake['severity'] == 'blunder':
                    report['total_blunders'] += 1
                else:
                    report['total_mistakes'] += 1

        # Calculate averages
        report['avg_moves'] /= total_games
        report['win_rate'] = report['wins'] / total_games
        report['avg_mistakes_per_game'] = report['total_mistakes'] / total_games
        report['avg_blunders_per_game'] = report['total_blunders'] / total_games

        return report

    def print_aggregate_report(self):
        """Print aggregate analysis report."""
        report = self.get_aggregate_report()

        print("="*70)
        print("AGGREGATE ANALYSIS REPORT")
        print("="*70)
        print(f"\nGames analyzed: {report['total_games']}")
        print(f"\nResults:")
        print(f"  Wins: {report['wins']} ({report['win_rate']:.1%})")
        print(f"  Losses: {report['losses']}")
        print(f"  Draws: {report['draws']}")
        print(f"\nPerformance:")
        print(f"  Average moves: {report['avg_moves']:.1f}")
        print(f"  Mistakes per game: {report['avg_mistakes_per_game']:.1f}")
        print(f"  Blunders per game: {report['avg_blunders_per_game']:.1f}")
        print("="*70 + "\n")
