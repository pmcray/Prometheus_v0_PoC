"""
Prometheus-Bench-v0.2: Universal Benchmark Suite
Supports General Game Playing (GGP) and Conversational AI domains

This benchmark suite expands beyond code optimization to evaluate
agent performance in diverse AI domains.
"""

import os
import json
import time
import random
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from abc import ABC, abstractmethod
from enum import Enum


class BenchmarkDomain(Enum):
    """Supported benchmark domains"""
    GENERAL_GAME_PLAYING = "general_game_playing"
    CONVERSATIONAL_AI = "conversational_ai"
    CODE_OPTIMIZATION = "code_optimization"


@dataclass
class BenchmarkResult:
    """Result of a single benchmark evaluation"""
    benchmark_name: str
    domain: str
    fitness_score: float
    execution_time_ms: float
    success: bool
    details: Dict[str, Any]
    timestamp: str
    agent_identifier: str


class DraughtsGame:
    """
    Simple Draughts (Checkers) game implementation
    8x8 board, standard American rules
    """

    def __init__(self):
        self.reset()

    def reset(self):
        """Initialize board to starting position"""
        # Board representation: 0=empty, 1=player1 piece, 2=player1 king,
        #                      -1=player2 piece, -2=player2 king
        self.board = [[0 for _ in range(8)] for _ in range(8)]

        # Set up starting positions
        for row in range(3):
            for col in range(8):
                if (row + col) % 2 == 1:
                    self.board[row][col] = -1  # Player 2 (top)

        for row in range(5, 8):
            for col in range(8):
                if (row + col) % 2 == 1:
                    self.board[row][col] = 1  # Player 1 (bottom)

        self.current_player = 1
        self.move_count = 0
        self.game_over = False
        self.winner = None

    def get_valid_moves(self, player: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Get all valid moves for a player"""
        moves = []

        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]

                # Check if this piece belongs to current player
                if (player == 1 and piece > 0) or (player == -1 and piece < 0):
                    piece_moves = self._get_piece_moves(row, col, piece)
                    moves.extend(piece_moves)

        # Prioritize captures if they exist
        captures = [m for m in moves if self._is_capture(m)]
        return captures if captures else moves

    def _get_piece_moves(self, row: int, col: int, piece: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Get valid moves for a specific piece"""
        moves = []
        is_king = abs(piece) == 2

        # Direction depends on piece type
        if piece > 0:  # Player 1 moves up
            directions = [(-1, -1), (-1, 1)]
            if is_king:
                directions.extend([(1, -1), (1, 1)])
        else:  # Player 2 moves down
            directions = [(1, -1), (1, 1)]
            if is_king:
                directions.extend([(-1, -1), (-1, 1)])

        # Simple moves
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            if 0 <= new_row < 8 and 0 <= new_col < 8:
                if self.board[new_row][new_col] == 0:
                    moves.append(((row, col), (new_row, new_col)))

        # Capture moves
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            capture_row, capture_col = row + dr, col + dc
            land_row, land_col = row + 2*dr, col + 2*dc

            if 0 <= land_row < 8 and 0 <= land_col < 8:
                if self.board[land_row][land_col] == 0:
                    capture_piece = self.board[capture_row][capture_col]
                    # Can capture opponent's piece
                    if (piece > 0 and capture_piece < 0) or (piece < 0 and capture_piece > 0):
                        moves.append(((row, col), (land_row, land_col)))

        return moves

    def _is_capture(self, move: Tuple[Tuple[int, int], Tuple[int, int]]) -> bool:
        """Check if a move is a capture"""
        (from_row, from_col), (to_row, to_col) = move
        return abs(to_row - from_row) == 2

    def make_move(self, move: Tuple[Tuple[int, int], Tuple[int, int]]) -> bool:
        """
        Execute a move
        Returns True if move was valid and executed
        """
        if move not in self.get_valid_moves(self.current_player):
            return False

        (from_row, from_col), (to_row, to_col) = move
        piece = self.board[from_row][from_col]

        # Move the piece
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = 0

        # Handle capture
        if self._is_capture(move):
            mid_row = (from_row + to_row) // 2
            mid_col = (from_col + to_col) // 2
            self.board[mid_row][mid_col] = 0

        # Promote to king if reaching opposite end
        if piece == 1 and to_row == 0:
            self.board[to_row][to_col] = 2
        elif piece == -1 and to_row == 7:
            self.board[to_row][to_col] = -2

        # Switch player
        self.current_player = -self.current_player
        self.move_count += 1

        # Check for game over
        self._check_game_over()

        return True

    def _check_game_over(self):
        """Check if game has ended"""
        # Check if current player has any valid moves
        if not self.get_valid_moves(self.current_player):
            self.game_over = True
            self.winner = -self.current_player

        # Check for draw by move count (200 moves without capture)
        if self.move_count >= 200:
            self.game_over = True
            self.winner = 0  # Draw

    def get_state(self) -> Dict[str, Any]:
        """Get current game state"""
        return {
            "board": [row[:] for row in self.board],
            "current_player": self.current_player,
            "move_count": self.move_count,
            "game_over": self.game_over,
            "winner": self.winner
        }

    def visualize(self) -> str:
        """Return ASCII visualization of board"""
        lines = []
        lines.append("\n  " + " ".join(str(i) for i in range(8)))
        lines.append("┌─" + "─┬─" * 7 + "─┐")

        for row in range(8):
            line = str(row) + "│"
            for col in range(8):
                piece = self.board[row][col]
                if piece == 1:
                    symbol = "●"  # Player 1 piece
                elif piece == 2:
                    symbol = "♔"  # Player 1 king
                elif piece == -1:
                    symbol = "○"  # Player 2 piece
                elif piece == -2:
                    symbol = "♕"  # Player 2 king
                else:
                    # Checkerboard pattern
                    symbol = "█" if (row + col) % 2 == 0 else " "

                line += symbol + "│"

            lines.append(line)

            if row < 7:
                lines.append(" ├─" + "─┼─" * 7 + "─┤")

        lines.append(" └─" + "─┴─" * 7 + "─┘")

        # Score
        p1_pieces = sum(1 for row in self.board for cell in row if cell > 0)
        p2_pieces = sum(1 for row in self.board for cell in row if cell < 0)
        lines.append(f"\nPieces: ● {p1_pieces}  ○ {p2_pieces}")

        return "\n".join(lines)

    def copy(self):
        """Create a copy of the game state"""
        new_game = DraughtsGame()
        new_game.board = [row[:] for row in self.board]
        new_game.current_player = self.current_player
        new_game.move_count = self.move_count
        new_game.game_over = self.game_over
        new_game.winner = self.winner
        return new_game


class BaselineOpponent:
    """
    Baseline Minimax opponent for game playing benchmarks
    Uses simple minimax with limited depth
    """

    def __init__(self, depth: int = 3):
        self.depth = depth

    def select_move(self, game: DraughtsGame) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Select best move using minimax"""
        valid_moves = game.get_valid_moves(game.current_player)

        if not valid_moves:
            return None

        best_move = None
        best_score = float('-inf')

        for move in valid_moves:
            game_copy = game.copy()
            game_copy.make_move(move)

            score = self._minimax(game_copy, self.depth - 1, False, game.current_player)

            if score > best_score:
                best_score = score
                best_move = move

        return best_move

    def _minimax(self, game: DraughtsGame, depth: int, maximizing: bool, original_player: int) -> float:
        """Minimax algorithm with alpha-beta pruning"""
        if depth == 0 or game.game_over:
            return self._evaluate_board(game, original_player)

        valid_moves = game.get_valid_moves(game.current_player)

        if not valid_moves:
            return self._evaluate_board(game, original_player)

        if maximizing:
            max_eval = float('-inf')
            for move in valid_moves:
                game_copy = game.copy()
                game_copy.make_move(move)
                eval_score = self._minimax(game_copy, depth - 1, False, original_player)
                max_eval = max(max_eval, eval_score)
            return max_eval
        else:
            min_eval = float('inf')
            for move in valid_moves:
                game_copy = game.copy()
                game_copy.make_move(move)
                eval_score = self._minimax(game_copy, depth - 1, True, original_player)
                min_eval = min(min_eval, eval_score)
            return min_eval

    def _evaluate_board(self, game: DraughtsGame, player: int) -> float:
        """Simple board evaluation function"""
        if game.game_over:
            if game.winner == player:
                return 1000
            elif game.winner == -player:
                return -1000
            else:
                return 0

        score = 0
        for row in range(8):
            for col in range(8):
                piece = game.board[row][col]
                if piece != 0:
                    # Basic piece values
                    piece_value = 1 if abs(piece) == 1 else 3  # Kings worth more

                    if (piece > 0 and player == 1) or (piece < 0 and player == -1):
                        score += piece_value
                    else:
                        score -= piece_value

        return score


class RandomPlayer:
    """Random move player for baseline comparison"""

    def select_move(self, game: DraughtsGame) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Select a random valid move"""
        valid_moves = game.get_valid_moves(game.current_player)
        return random.choice(valid_moves) if valid_moves else None


class ConversationalAIEvaluator:
    """
    Evaluator for conversational AI capabilities
    Uses LLM-as-judge framework
    """

    def __init__(self, judge_model: Optional[Any] = None):
        self.judge_model = judge_model
        self.evaluation_criteria = {
            "coherence": "Responses maintain logical consistency and context",
            "helpfulness": "Responses provide useful information",
            "relevance": "Responses stay on topic",
            "persona_adherence": "Responses match the specified persona or role"
        }

    def evaluate_conversation(self,
                            conversation_transcript: List[Dict[str, str]],
                            topic: str,
                            persona: str = "helpful assistant") -> Dict[str, Any]:
        """
        Evaluate a conversation transcript

        Args:
            conversation_transcript: List of {"role": "user/assistant", "content": "..."}
            topic: Conversation topic
            persona: Expected persona

        Returns:
            Evaluation results with scores
        """

        # If no judge model provided, use rule-based evaluation
        if self.judge_model is None:
            return self._rule_based_evaluation(conversation_transcript, topic, persona)
        else:
            return self._llm_judge_evaluation(conversation_transcript, topic, persona)

    def _rule_based_evaluation(self,
                               transcript: List[Dict[str, str]],
                               topic: str,
                               persona: str) -> Dict[str, Any]:
        """Simple rule-based evaluation when LLM judge not available"""

        # Extract assistant responses
        assistant_responses = [msg["content"] for msg in transcript if msg["role"] == "assistant"]

        if not assistant_responses:
            return {
                "overall_score": 0.0,
                "criterion_scores": {k: 0.0 for k in self.evaluation_criteria},
                "feedback": "No assistant responses found",
                "evaluation_method": "rule_based"
            }

        # Simple heuristic scoring
        scores = {}

        # Coherence: Check for reasonable response lengths
        avg_length = sum(len(r.split()) for r in assistant_responses) / len(assistant_responses)
        scores["coherence"] = min(1.0, avg_length / 30.0)  # Target ~30 words

        # Helpfulness: Check if responses are substantive
        scores["helpfulness"] = 1.0 if avg_length > 10 else 0.3

        # Relevance: Simple keyword matching with topic
        topic_words = set(topic.lower().split())
        relevance_sum = 0
        for response in assistant_responses:
            response_words = set(response.lower().split())
            overlap = len(topic_words & response_words)
            relevance_sum += min(1.0, overlap / max(len(topic_words), 1))
        scores["relevance"] = relevance_sum / len(assistant_responses)

        # Persona adherence: Simple check
        scores["persona_adherence"] = 0.7  # Default moderate score

        overall = sum(scores.values()) / len(scores)

        return {
            "overall_score": overall,
            "criterion_scores": scores,
            "feedback": f"Rule-based evaluation complete. {len(assistant_responses)} responses analyzed.",
            "evaluation_method": "rule_based",
            "conversation_length": len(transcript),
            "assistant_response_count": len(assistant_responses)
        }

    def _llm_judge_evaluation(self,
                             transcript: List[Dict[str, str]],
                             topic: str,
                             persona: str) -> Dict[str, Any]:
        """Use LLM as judge for evaluation"""

        # Format transcript for judge
        transcript_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in transcript
        ])

        judge_prompt = f"""Evaluate the following conversation on the topic "{topic}" where the assistant should act as a "{persona}".

Conversation:
{transcript_text}

Rate the assistant's performance on these criteria (scale 0.0 to 1.0):
1. Coherence: Logical consistency and context maintenance
2. Helpfulness: Providing useful information
3. Relevance: Staying on topic
4. Persona Adherence: Matching the specified role

Provide scores in JSON format:
{{
    "coherence": 0.0-1.0,
    "helpfulness": 0.0-1.0,
    "relevance": 0.0-1.0,
    "persona_adherence": 0.0-1.0,
    "feedback": "brief evaluation summary"
}}"""

        try:
            # This would use the actual judge model
            # For now, fall back to rule-based
            return self._rule_based_evaluation(transcript, topic, persona)
        except Exception as e:
            return {
                "overall_score": 0.0,
                "error": str(e),
                "evaluation_method": "failed_llm_judge"
            }


class PrometheusBenchV02:
    """
    Universal Benchmark Suite v0.2
    Supports multiple AI domains beyond code optimization
    """

    def __init__(self):
        self.version = "0.2"
        self.domains = {
            BenchmarkDomain.GENERAL_GAME_PLAYING: ["draughts", "connect4"],
            BenchmarkDomain.CONVERSATIONAL_AI: ["general_conversation"],
            BenchmarkDomain.CODE_OPTIMIZATION: ["self_modification"]
        }

        self.baseline_opponent = BaselineOpponent(depth=3)
        self.conversational_evaluator = ConversationalAIEvaluator()

    def get_benchmark_hash(self) -> str:
        """Get hash of benchmark suite for integrity checking"""
        # Convert enum keys to strings for JSON serialization
        domains_serializable = {str(k): v for k, v in self.domains.items()}
        suite_repr = f"{self.version}:{json.dumps(domains_serializable, sort_keys=True)}"
        return hashlib.md5(suite_repr.encode()).hexdigest()

    def run_ggp_benchmark(self,
                         agent_select_move: Callable,
                         num_games: int = 100,
                         game_type: str = "draughts") -> BenchmarkResult:
        """
        Run General Game Playing benchmark

        Args:
            agent_select_move: Function that takes game state and returns move
            num_games: Number of games to play
            game_type: Type of game ("draughts" or "connect4")

        Returns:
            Benchmark result with win rate
        """
        start_time = time.time()

        wins = 0
        losses = 0
        draws = 0
        total_moves = 0

        # Handle Connect4 separately with simpler opponent
        if game_type == "connect4":
            from benchmarks.connect4_benchmark import evaluate_connect4_agent
            # Create a temporary agent wrapper
            class AgentWrapper:
                def select_move(self, game_state):
                    return agent_select_move(game_state)

            wrapper = AgentWrapper()
            fitness, details = evaluate_connect4_agent(wrapper, num_games=num_games)

            execution_time_ms = (time.time() - start_time) * 1000
            return BenchmarkResult(
                benchmark_name=f"GGP-{game_type}",
                domain=BenchmarkDomain.GENERAL_GAME_PLAYING.value,
                fitness_score=fitness,
                execution_time_ms=execution_time_ms,
                success=True,
                details=details,
                timestamp=datetime.now().isoformat(),
                agent_identifier="connect4_agent"
            )

        # Original draughts code
        for game_num in range(num_games):
            game = DraughtsGame()

            # Alternate who goes first
            agent_player = 1 if game_num % 2 == 0 else -1

            move_count = 0
            max_moves = 200

            while not game.game_over and move_count < max_moves:
                if game.current_player == agent_player:
                    # Agent's turn
                    try:
                        move = agent_select_move(game.get_state())
                        if move is None or not game.make_move(move):
                            # Invalid move = loss
                            game.game_over = True
                            game.winner = -agent_player
                            break
                    except Exception:
                        # Error = loss
                        game.game_over = True
                        game.winner = -agent_player
                        break
                else:
                    # Baseline opponent's turn
                    move = self.baseline_opponent.select_move(game)
                    if move is None:
                        game.game_over = True
                        game.winner = agent_player
                        break
                    game.make_move(move)

                move_count += 1

            # Record result
            if game.winner == agent_player:
                wins += 1
            elif game.winner == -agent_player:
                losses += 1
            else:
                draws += 1

            total_moves += move_count

        execution_time_ms = (time.time() - start_time) * 1000
        win_rate = wins / num_games if num_games > 0 else 0.0

        return BenchmarkResult(
            benchmark_name=f"GGP-{game_type}",
            domain=BenchmarkDomain.GENERAL_GAME_PLAYING.value,
            fitness_score=win_rate,
            execution_time_ms=execution_time_ms,
            success=True,
            details={
                "num_games": num_games,
                "wins": wins,
                "losses": losses,
                "draws": draws,
                "win_rate": win_rate,
                "avg_moves_per_game": total_moves / num_games if num_games > 0 else 0
            },
            timestamp=datetime.now().isoformat(),
            agent_identifier="candidate_agent"
        )

    def run_conversational_ai_benchmark(self,
                                       agent_generate_response: Callable,
                                       topic: str = "general assistance",
                                       persona: str = "helpful assistant",
                                       num_turns: int = 5) -> BenchmarkResult:
        """
        Run Conversational AI benchmark

        Args:
            agent_generate_response: Function that takes message history and returns response
            topic: Conversation topic
            persona: Expected persona
            num_turns: Number of conversation turns

        Returns:
            Benchmark result with conversation quality score
        """
        start_time = time.time()

        # Generate a conversation
        test_prompts = [
            f"Hello, can you help me with {topic}?",
            f"Tell me more about that.",
            f"What are the key points I should remember?",
            f"Can you give me an example?",
            f"Thank you for the information."
        ][:num_turns]

        conversation_transcript = []

        try:
            for prompt in test_prompts:
                # Add user message
                conversation_transcript.append({
                    "role": "user",
                    "content": prompt
                })

                # Get agent response
                response = agent_generate_response(conversation_transcript)

                # Add agent response
                conversation_transcript.append({
                    "role": "assistant",
                    "content": response
                })

            # Evaluate the conversation
            evaluation = self.conversational_evaluator.evaluate_conversation(
                conversation_transcript, topic, persona
            )

            execution_time_ms = (time.time() - start_time) * 1000

            return BenchmarkResult(
                benchmark_name="ConversationalAI-General",
                domain=BenchmarkDomain.CONVERSATIONAL_AI.value,
                fitness_score=evaluation["overall_score"],
                execution_time_ms=execution_time_ms,
                success=True,
                details={
                    "topic": topic,
                    "persona": persona,
                    "num_turns": num_turns,
                    "evaluation": evaluation,
                    "transcript_length": len(conversation_transcript)
                },
                timestamp=datetime.now().isoformat(),
                agent_identifier="candidate_agent"
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000

            return BenchmarkResult(
                benchmark_name="ConversationalAI-General",
                domain=BenchmarkDomain.CONVERSATIONAL_AI.value,
                fitness_score=0.0,
                execution_time_ms=execution_time_ms,
                success=False,
                details={
                    "error": str(e),
                    "topic": topic,
                    "persona": persona
                },
                timestamp=datetime.now().isoformat(),
                agent_identifier="candidate_agent"
            )

    def get_available_benchmarks(self) -> Dict[str, List[str]]:
        """Get list of available benchmarks by domain"""
        return {domain.value: benchmarks for domain, benchmarks in self.domains.items()}

    def get_benchmark_info(self, benchmark_name: str) -> Dict[str, Any]:
        """Get information about a specific benchmark"""
        if "draughts" in benchmark_name.lower():
            return {
                "name": "GGP-Draughts",
                "domain": BenchmarkDomain.GENERAL_GAME_PLAYING.value,
                "description": "Play Draughts (Checkers) against baseline Minimax opponent",
                "fitness_metric": "Win rate over 100 games",
                "target_fitness": 0.8,
                "baseline_opponent": "Minimax depth-3"
            }
        elif "conversational" in benchmark_name.lower():
            return {
                "name": "ConversationalAI-General",
                "domain": BenchmarkDomain.CONVERSATIONAL_AI.value,
                "description": "Maintain coherent, helpful conversation",
                "fitness_metric": "LLM-as-judge quality score",
                "target_fitness": 0.8,
                "evaluation_method": "Multi-criteria scoring"
            }
        else:
            return {"error": "Benchmark not found"}

    def export_results(self, results: List[BenchmarkResult], filepath: str):
        """Export benchmark results to JSON file"""
        results_dict = {
            "benchmark_version": self.version,
            "export_timestamp": datetime.now().isoformat(),
            "results": [asdict(r) for r in results]
        }

        with open(filepath, 'w') as f:
            json.dump(results_dict, f, indent=2)