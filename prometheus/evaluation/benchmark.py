"""
Model Evaluation and Benchmarking Suite

Comprehensive evaluation tools for Go agents:
- ELO rating calculation
- Win rate analysis
- Performance metrics
- Statistical significance testing
- Cross-agent comparisons
- Benchmark against known positions

Usage:
    evaluator = GoEvaluator()
    results = evaluator.evaluate_agent(agent, opponent, num_games=100)
    elo = evaluator.calculate_elo(results)
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
import time
from scipy import stats


class ELOCalculator:
    """
    Calculate ELO ratings for Go agents.

    Uses standard ELO formula with K-factor adjustment.
    """

    def __init__(self, k_factor: int = 32, initial_rating: int = 1200):
        """
        Initialize ELO calculator.

        Args:
            k_factor: Maximum rating change per game
            initial_rating: Starting rating for new players
        """
        self.k_factor = k_factor
        self.initial_rating = initial_rating
        self.ratings = {}

    def get_rating(self, agent_name: str) -> int:
        """Get current rating for agent."""
        return self.ratings.get(agent_name, self.initial_rating)

    def expected_score(self, rating_a: float, rating_b: float) -> float:
        """
        Calculate expected score for player A.

        Args:
            rating_a: Rating of player A
            rating_b: Rating of player B

        Returns:
            Expected score (0-1)
        """
        return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))

    def update_ratings(self, agent_a: str, agent_b: str, score_a: float):
        """
        Update ratings after game.

        Args:
            agent_a: Name of first agent
            agent_b: Name of second agent
            score_a: Score for agent A (1.0 = win, 0.5 = draw, 0.0 = loss)
        """
        rating_a = self.get_rating(agent_a)
        rating_b = self.get_rating(agent_b)

        expected_a = self.expected_score(rating_a, rating_b)
        expected_b = 1.0 - expected_a

        # Update ratings
        new_rating_a = rating_a + self.k_factor * (score_a - expected_a)
        new_rating_b = rating_b + self.k_factor * ((1.0 - score_a) - expected_b)

        self.ratings[agent_a] = new_rating_a
        self.ratings[agent_b] = new_rating_b

    def calculate_rating_change(self, current_rating: int, opponent_rating: int,
                               score: float) -> float:
        """
        Calculate rating change without updating.

        Args:
            current_rating: Current player rating
            opponent_rating: Opponent rating
            score: Game score (1.0, 0.5, or 0.0)

        Returns:
            Rating change
        """
        expected = self.expected_score(current_rating, opponent_rating)
        return self.k_factor * (score - expected)


class GoEvaluator:
    """
    Comprehensive evaluation suite for Go agents.

    Provides:
    - Head-to-head matchups
    - Win rate calculation
    - ELO rating estimation
    - Performance metrics
    - Statistical analysis
    """

    def __init__(self, board_size: int = 9, komi: float = 7.5):
        """
        Initialize evaluator.

        Args:
            board_size: Board size
            komi: Komi compensation for white
        """
        self.board_size = board_size
        self.komi = komi
        self.elo_calculator = ELOCalculator()

    def play_game(self, agent1, agent2, env,
                  verbose: bool = False) -> Dict:
        """
        Play single game between two agents.

        Args:
            agent1: First agent (plays black)
            agent2: Second agent (plays white)
            env: Go environment
            verbose: Print game progress

        Returns:
            Game result dictionary
        """
        state = env.reset()
        done = False
        moves = 0
        game_history = []
        consecutive_passes = 0
        max_moves = self.board_size * self.board_size * 2

        while not done and moves < max_moves:
            # Get current player
            current_agent = agent1 if env.board.current_player == 1 else agent2

            # Get legal moves
            legal_moves = env.get_legal_moves()

            # Get move from agent
            move = current_agent.get_move(state, legal_moves, temperature=0.1)

            # Track passes
            if move == ('pass',):
                consecutive_passes += 1
            else:
                consecutive_passes = 0

            # Game ends after two consecutive passes
            if consecutive_passes >= 2:
                done = True

            # Make move
            state, reward, done, info = env.step(move)
            game_history.append({
                'move': move,
                'player': env.board.current_player,
                'state': state.copy()
            })
            moves += 1

            if verbose and moves % 20 == 0:
                print(f"  Move {moves}...")

        # Get final score
        score = env.board.score()

        result = {
            'winner': score['winner'],
            'black_score': score['black_score'],
            'white_score': score['white_score'],
            'margin': score['margin'],
            'moves': moves,
            'history': game_history
        }

        return result

    def evaluate_matchup(self, agent1, agent2, env,
                        num_games: int = 100,
                        verbose: bool = True) -> Dict:
        """
        Evaluate head-to-head matchup.

        Args:
            agent1: First agent
            agent2: Second agent
            env: Go environment
            num_games: Number of games to play
            verbose: Print progress

        Returns:
            Evaluation results
        """
        if verbose:
            print(f"Evaluating matchup: {agent1.name} vs {agent2.name}")
            print(f"Playing {num_games} games...")

        results = {
            'agent1_wins': 0,
            'agent2_wins': 0,
            'draws': 0,
            'games': [],
            'agent1_black_wins': 0,
            'agent1_white_wins': 0,
            'agent2_black_wins': 0,
            'agent2_white_wins': 0,
        }

        start_time = time.time()

        for game_num in range(num_games):
            # Alternate colors
            if game_num % 2 == 0:
                # agent1 plays black
                game_result = self.play_game(agent1, agent2, env, verbose=False)

                if game_result['winner'] == 'black':
                    results['agent1_wins'] += 1
                    results['agent1_black_wins'] += 1
                elif game_result['winner'] == 'white':
                    results['agent2_wins'] += 1
                    results['agent2_white_wins'] += 1
                else:
                    results['draws'] += 1
            else:
                # agent2 plays black
                game_result = self.play_game(agent2, agent1, env, verbose=False)

                if game_result['winner'] == 'black':
                    results['agent2_wins'] += 1
                    results['agent2_black_wins'] += 1
                elif game_result['winner'] == 'white':
                    results['agent1_wins'] += 1
                    results['agent1_white_wins'] += 1
                else:
                    results['draws'] += 1

            results['games'].append(game_result)

            if verbose and (game_num + 1) % 10 == 0:
                elapsed = time.time() - start_time
                games_per_sec = (game_num + 1) / elapsed
                eta = (num_games - game_num - 1) / games_per_sec
                print(f"  Progress: {game_num + 1}/{num_games} "
                      f"({games_per_sec:.1f} games/s, ETA: {eta:.0f}s)")

        # Calculate statistics
        total_games = results['agent1_wins'] + results['agent2_wins'] + results['draws']
        results['agent1_win_rate'] = results['agent1_wins'] / total_games
        results['agent2_win_rate'] = results['agent2_wins'] / total_games
        results['draw_rate'] = results['draws'] / total_games

        # Update ELO ratings
        for game in results['games']:
            if game['winner'] == 'black':
                score_a = 1.0
            elif game['winner'] == 'white':
                score_a = 0.0
            else:
                score_a = 0.5

            # Note: This is simplified - in full implementation,
            # would need to track which agent had which color
            self.elo_calculator.update_ratings(agent1.name, agent2.name, score_a)

        results['agent1_elo'] = self.elo_calculator.get_rating(agent1.name)
        results['agent2_elo'] = self.elo_calculator.get_rating(agent2.name)
        results['elapsed_time'] = time.time() - start_time

        if verbose:
            self._print_matchup_results(results, agent1.name, agent2.name)

        return results

    def _print_matchup_results(self, results: Dict, name1: str, name2: str):
        """Print formatted matchup results."""
        print("\n" + "="*60)
        print("MATCHUP RESULTS")
        print("="*60)
        print(f"{name1} vs {name2}")
        print("-"*60)
        print(f"Total Games: {len(results['games'])}")
        print(f"\n{name1}:")
        print(f"  Wins: {results['agent1_wins']} ({results['agent1_win_rate']:.1%})")
        print(f"  As Black: {results['agent1_black_wins']}")
        print(f"  As White: {results['agent1_white_wins']}")
        print(f"  ELO: {results['agent1_elo']:.0f}")
        print(f"\n{name2}:")
        print(f"  Wins: {results['agent2_wins']} ({results['agent2_win_rate']:.1%})")
        print(f"  As Black: {results['agent2_black_wins']}")
        print(f"  As White: {results['agent2_white_wins']}")
        print(f"  ELO: {results['agent2_elo']:.0f}")
        print(f"\nDraws: {results['draws']} ({results['draw_rate']:.1%})")
        print(f"Time: {results['elapsed_time']:.1f}s")
        print("="*60 + "\n")

    def calculate_statistical_significance(self, results: Dict,
                                          confidence: float = 0.95) -> Dict:
        """
        Calculate statistical significance of results.

        Args:
            results: Matchup results
            confidence: Confidence level (e.g., 0.95 for 95%)

        Returns:
            Statistical analysis
        """
        total = results['agent1_wins'] + results['agent2_wins'] + results['draws']
        p1 = results['agent1_win_rate']
        p2 = results['agent2_win_rate']

        # Wilson score interval for win rates
        z = stats.norm.ppf((1 + confidence) / 2)

        def wilson_interval(p, n):
            if n == 0:
                return (0, 1)
            denominator = 1 + z**2 / n
            center = (p + z**2 / (2*n)) / denominator
            margin = z * np.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denominator
            return (center - margin, center + margin)

        ci1 = wilson_interval(p1, total)
        ci2 = wilson_interval(p2, total)

        # Two-proportion z-test
        p_pooled = (results['agent1_wins'] + results['agent2_wins']) / (2 * total)
        se = np.sqrt(2 * p_pooled * (1 - p_pooled) / total)

        if se > 0:
            z_score = (p1 - p2) / se
            p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        else:
            z_score = 0
            p_value = 1.0

        return {
            'agent1_ci': ci1,
            'agent2_ci': ci2,
            'z_score': z_score,
            'p_value': p_value,
            'significant': p_value < (1 - confidence),
            'confidence_level': confidence
        }

    def tournament(self, agents: List, env, games_per_matchup: int = 50,
                  verbose: bool = True) -> Dict:
        """
        Run round-robin tournament.

        Args:
            agents: List of agents
            env: Go environment
            games_per_matchup: Games between each pair
            verbose: Print progress

        Returns:
            Tournament results
        """
        if verbose:
            print(f"Running tournament with {len(agents)} agents")
            print(f"Games per matchup: {games_per_matchup}")
            print()

        results = {
            'matchups': {},
            'standings': defaultdict(lambda: {
                'wins': 0,
                'losses': 0,
                'draws': 0,
                'points': 0,
                'elo': self.elo_calculator.initial_rating
            })
        }

        # Play all matchups
        for i, agent1 in enumerate(agents):
            for j, agent2 in enumerate(agents):
                if i < j:  # Avoid duplicate matchups
                    if verbose:
                        print(f"Matchup {i+1}-{j+1}: {agent1.name} vs {agent2.name}")

                    matchup_result = self.evaluate_matchup(
                        agent1, agent2, env,
                        num_games=games_per_matchup,
                        verbose=verbose
                    )

                    # Store matchup result
                    key = f"{agent1.name}_vs_{agent2.name}"
                    results['matchups'][key] = matchup_result

                    # Update standings
                    results['standings'][agent1.name]['wins'] += matchup_result['agent1_wins']
                    results['standings'][agent1.name]['losses'] += matchup_result['agent2_wins']
                    results['standings'][agent1.name]['draws'] += matchup_result['draws']
                    results['standings'][agent1.name]['points'] += (
                        matchup_result['agent1_wins'] * 1.0 +
                        matchup_result['draws'] * 0.5
                    )
                    results['standings'][agent1.name]['elo'] = matchup_result['agent1_elo']

                    results['standings'][agent2.name]['wins'] += matchup_result['agent2_wins']
                    results['standings'][agent2.name]['losses'] += matchup_result['agent1_wins']
                    results['standings'][agent2.name]['draws'] += matchup_result['draws']
                    results['standings'][agent2.name]['points'] += (
                        matchup_result['agent2_wins'] * 1.0 +
                        matchup_result['draws'] * 0.5
                    )
                    results['standings'][agent2.name]['elo'] = matchup_result['agent2_elo']

        if verbose:
            self._print_tournament_standings(results['standings'])

        return results

    def _print_tournament_standings(self, standings: Dict):
        """Print formatted tournament standings."""
        print("\n" + "="*70)
        print("TOURNAMENT STANDINGS")
        print("="*70)
        print(f"{'Rank':<6} {'Agent':<25} {'W-L-D':<12} {'Points':<8} {'ELO':<6}")
        print("-"*70)

        # Sort by points, then ELO
        sorted_agents = sorted(
            standings.items(),
            key=lambda x: (x[1]['points'], x[1]['elo']),
            reverse=True
        )

        for rank, (name, stats) in enumerate(sorted_agents, 1):
            wld = f"{stats['wins']}-{stats['losses']}-{stats['draws']}"
            print(f"{rank:<6} {name:<25} {wld:<12} "
                  f"{stats['points']:<8.1f} {stats['elo']:<6.0f}")

        print("="*70 + "\n")


class PerformanceAnalyzer:
    """
    Analyze agent performance characteristics.

    Provides:
    - Move time analysis
    - Decision quality metrics
    - Opening/middlegame/endgame strength
    - Tactical vs positional play
    """

    def __init__(self):
        """Initialize performance analyzer."""
        self.metrics = defaultdict(list)

    def analyze_game(self, game_result: Dict, agent_name: str) -> Dict:
        """
        Analyze single game performance.

        Args:
            game_result: Game result dictionary
            agent_name: Name of agent to analyze

        Returns:
            Performance metrics
        """
        analysis = {
            'total_moves': len(game_result['history']),
            'avg_move_time': 0.0,  # Would need timing data
            'opening_strength': 0.0,
            'middlegame_strength': 0.0,
            'endgame_strength': 0.0,
        }

        # Analyze by game phase
        total_moves = len(game_result['history'])
        opening_end = total_moves // 4
        middlegame_end = 3 * total_moves // 4

        # This is simplified - full analysis would evaluate position quality
        analysis['opening_strength'] = self._evaluate_phase(
            game_result['history'][:opening_end]
        )
        analysis['middlegame_strength'] = self._evaluate_phase(
            game_result['history'][opening_end:middlegame_end]
        )
        analysis['endgame_strength'] = self._evaluate_phase(
            game_result['history'][middlegame_end:]
        )

        return analysis

    def _evaluate_phase(self, moves: List[Dict]) -> float:
        """
        Evaluate play quality in game phase.

        Args:
            moves: List of moves in phase

        Returns:
            Quality score (0-1)
        """
        # Simplified evaluation - would use position analysis in full version
        if len(moves) == 0:
            return 0.5

        # For now, return random score
        # In full implementation, would analyze:
        # - Territory gained/lost
        # - Groups saved/killed
        # - Efficiency of moves
        return 0.5

    def compare_agents(self, agent1_metrics: List[Dict],
                      agent2_metrics: List[Dict]) -> Dict:
        """
        Compare performance characteristics of two agents.

        Args:
            agent1_metrics: List of game metrics for agent 1
            agent2_metrics: List of game metrics for agent 2

        Returns:
            Comparison results
        """
        def avg_metric(metrics, key):
            values = [m[key] for m in metrics if key in m]
            return np.mean(values) if values else 0.0

        comparison = {
            'agent1_opening': avg_metric(agent1_metrics, 'opening_strength'),
            'agent2_opening': avg_metric(agent2_metrics, 'opening_strength'),
            'agent1_middlegame': avg_metric(agent1_metrics, 'middlegame_strength'),
            'agent2_middlegame': avg_metric(agent2_metrics, 'middlegame_strength'),
            'agent1_endgame': avg_metric(agent1_metrics, 'endgame_strength'),
            'agent2_endgame': avg_metric(agent2_metrics, 'endgame_strength'),
        }

        return comparison
