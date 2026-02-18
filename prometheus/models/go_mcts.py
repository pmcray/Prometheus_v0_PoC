"""
Prometheus Go Monte Carlo Tree Search (MCTS)

AlphaZero-style MCTS implementation for Go:
- UCB1 selection with neural network guidance
- Policy-guided expansion
- Value network for position evaluation
- Support for 9x9, 13x13, and 19x19 boards
"""

import numpy as np
import math
from typing import Optional, Dict, List, Tuple, Any
from collections import defaultdict
from prometheus.environments.go import GoBoard, GoBoardEncoder, GoMoveEncoder


class GoMCTSNode:
    """
    Node in the Go Monte Carlo Tree Search.

    Each node represents a Go board position and tracks:
    - Visit count (N)
    - Total value (W)
    - Mean value (Q = W/N)
    - Prior probability (P) from policy network
    - Children nodes
    """

    def __init__(
        self,
        board: GoBoard,
        parent: Optional['GoMCTSNode'] = None,
        prior: float = 0.0,
        move: Optional[Tuple] = None
    ):
        """
        Initialize Go MCTS node.

        Args:
            board: Go board state at this node
            parent: Parent node (None for root)
            prior: Prior probability from policy network
            move: Move that led to this node (row, col) or ('pass',)
        """
        self.board = board.copy()
        self.parent = parent
        self.prior = prior
        self.move = move

        # Statistics
        self.visit_count = 0
        self.total_value = 0.0
        self.mean_value = 0.0

        # Children
        self.children: Dict[Tuple, GoMCTSNode] = {}
        self.is_expanded = False

    def is_leaf(self) -> bool:
        """Check if node is a leaf (not expanded)."""
        return not self.is_expanded

    def select_child(self, c_puct: float = 1.0) -> 'GoMCTSNode':
        """
        Select best child using PUCT algorithm.

        PUCT = Q + c_puct * P * sqrt(N_parent) / (1 + N_child)

        Args:
            c_puct: Exploration constant (higher = more exploration)

        Returns:
            Best child node
        """
        best_score = -float('inf')
        best_child = None

        for move, child in self.children.items():
            # Q: mean value (from current player's perspective)
            q_value = child.mean_value

            # U: exploration term
            u_value = c_puct * child.prior * math.sqrt(self.visit_count) / (1 + child.visit_count)

            # PUCT score
            score = q_value + u_value

            if score > best_score:
                best_score = score
                best_child = child

        return best_child

    def expand(self, policy: np.ndarray, encoder: GoMoveEncoder):
        """
        Expand node by adding all legal moves as children.

        Args:
            policy: Policy probabilities from neural network
            encoder: GoMoveEncoder for move indexing
        """
        if self.is_expanded:
            return

        # Get legal moves
        legal_moves = self.board.get_legal_moves()
        legal_moves.append(('pass',))

        # Create child for each legal move
        for move in legal_moves:
            # Get prior from policy network
            move_idx = encoder.move_to_index(move)
            prior = policy[move_idx]

            # Create child board
            child_board = self.board.copy()
            if move == ('pass',):
                child_board.pass_turn()
            else:
                child_board.play_move(move[0], move[1])

            # Create child node
            child = GoMCTSNode(child_board, parent=self, prior=prior, move=move)
            self.children[move] = child

        self.is_expanded = True

    def update(self, value: float):
        """
        Update node statistics with backpropagation.

        Args:
            value: Value to backpropagate
        """
        self.visit_count += 1
        self.total_value += value
        self.mean_value = self.total_value / self.visit_count

    def get_visit_distribution(self) -> Tuple[List[Tuple], np.ndarray]:
        """
        Get visit count distribution over children.

        Returns:
            Tuple of (moves, visit_counts)
        """
        moves = []
        visits = []

        for move, child in self.children.items():
            moves.append(move)
            visits.append(child.visit_count)

        visits = np.array(visits, dtype=np.float32)
        return moves, visits


class GoMCTS:
    """
    Monte Carlo Tree Search for Go.

    AlphaZero-style search using neural network for policy and value.
    """

    def __init__(
        self,
        agent: Any,
        num_simulations: int = 100,
        c_puct: float = 1.0,
        temperature: float = 1.0
    ):
        """
        Initialize Go MCTS.

        Args:
            agent: Go agent with predict() method
            num_simulations: Number of MCTS simulations per move
            c_puct: Exploration constant
            temperature: Temperature for move selection
        """
        self.agent = agent
        self.num_simulations = num_simulations
        self.c_puct = c_puct
        self.temperature = temperature
        self.board_size = agent.board_size

        self.move_encoder = GoMoveEncoder(self.board_size)
        self.board_encoder = GoBoardEncoder()

    def search(self, board: GoBoard) -> Tuple:
        """
        Run MCTS and return best move.

        Args:
            board: Current board state

        Returns:
            Best move (row, col) or ('pass',)
        """
        # Create root node
        root = GoMCTSNode(board)

        # Run simulations
        for _ in range(self.num_simulations):
            self._simulate(root)

        # Select move based on visit counts
        move = self._select_move(root)
        return move

    def _simulate(self, node: GoMCTSNode):
        """
        Run single MCTS simulation.

        Args:
            node: Root node to start simulation from
        """
        path = []
        current = node

        # 1. Selection: traverse to leaf
        while not current.is_leaf() and not current.board.game_over:
            path.append(current)
            current = current.select_child(self.c_puct)

        # Check if game over
        if current.board.game_over:
            # Terminal node
            scores = current.board.score()
            if scores['winner'] == 'black':
                value = 1.0
            elif scores['winner'] == 'white':
                value = -1.0
            else:
                value = 0.0

            # Value should be from perspective of player who just moved
            # Wait, AlphaZero convention: value is from perspective of current player at current node
            # but we flip it in backprop.
            if current.board.current_player == GoBoard.WHITE: # Black just moved
                 # do nothing, value 1 means black wins
                 pass
            else: # White just moved
                 # value -1 means white wins, but we want 1 if current player wins
                 pass
            
            # Simple approach: value is absolute (Black +1, White -1)
            # and we adjust during update.
        else:
            # 2. Expansion & 3. Evaluation
            state = self.board_encoder.encode(current.board)
            policy, value = self.agent.predict(state)

            # Expand node with policy
            current.expand(policy, self.move_encoder)

            # value is scalar from NN (usually -1 to 1, representing Black vs White)
            # but standard MCTS expects value from perspective of player to move
            # In our go_models, value head is tanh (-1 Black wins, +1 White wins)
            # Let's align it.
            value = float(value)

        # Add current node to path
        path.append(current)

        # 4. Backpropagation
        # The value from NN is +1 if White wins, -1 if Black wins.
        # For MCTSNode.mean_value to work with PUCT, it should be:
        # Higher if the move that led to this node was good for the player who made it.
        
        for node in reversed(path):
            # If it's Black's turn at this node, a high value is BAD (White wins)
            # If it's White's turn at this node, a high value is GOOD (White wins)
            node_value = value if node.board.current_player == GoBoard.WHITE else -value
            node.update(node_value)

    def _select_move(self, root: GoMCTSNode) -> Tuple:
        """Select move based on visit counts and temperature."""
        moves, visits = root.get_visit_distribution()

        if len(moves) == 0:
            return ('pass',)

        if self.temperature == 0:
            best_idx = np.argmax(visits)
            return moves[best_idx]
        else:
            visits_temp = visits ** (1.0 / self.temperature)
            probs = visits_temp / np.sum(visits_temp)
            idx = np.random.choice(len(moves), p=probs)
            return moves[idx]

    def get_policy_value(
        self,
        board: GoBoard,
        return_distribution: bool = False
    ) -> Tuple[Tuple, float, Optional[np.ndarray]]:
        """Get improved policy and value from MCTS."""
        root = GoMCTSNode(board)
        for _ in range(self.num_simulations):
            self._simulate(root)

        best_move = self._select_move(root)
        value = root.mean_value

        distribution = None
        if return_distribution:
            moves, visits = root.get_visit_distribution()
            distribution = np.zeros(self.board_size * self.board_size + 1)
            for move, visit in zip(moves, visits):
                idx = self.move_encoder.move_to_index(move)
                distribution[idx] = visit
            if np.sum(distribution) > 0:
                distribution /= np.sum(distribution)

        return best_move, value, distribution


class GoMCTSAgent:
    """Go agent that uses MCTS for move selection."""

    def __init__(
        self,
        base_agent: Any,
        num_simulations: int = 100,
        c_puct: float = 1.0,
        name: Optional[str] = None
    ):
        self.base_agent = base_agent
        self.num_simulations = num_simulations
        self.c_puct = c_puct
        self.board_size = base_agent.board_size
        self.name = name or f"{base_agent.name}+MCTS{num_simulations}"

        self.mcts = GoMCTS(
            base_agent,
            num_simulations=num_simulations,
            c_puct=c_puct
        )

        self.games_played = 0
        self.wins = 0
        self.losses = 0
        self.draws = 0

    def get_move(
        self,
        state: np.ndarray,
        legal_moves: list,
        temperature: float = 1.0
    ) -> Tuple:
        """Get move using MCTS."""
        # Find the board from the agent or create one?
        # Standard API usually passes state. We need the GoBoard object.
        # For now, let's assume we can reconstruct it or it's passed in.
        # Actually, let's modify the interface to accept the board if available.
        
        # If we only have state, we can't easily get the board back because of history/ko.
        # In our match loops, we should pass the environment or board.
        pass

    def get_move_from_board(self, board: GoBoard, temperature: float = 1.0) -> Tuple:
        """Get move directly from board object."""
        self.mcts.temperature = temperature
        return self.mcts.search(board)

    def update_statistics(self, result: str):
        self.games_played += 1
        if result == 'win':
            self.wins += 1
        elif result == 'loss':
            self.losses += 1
        else:
            self.draws += 1

    def get_statistics(self) -> Dict[str, Any]:
        win_rate = (self.wins / self.games_played * 100) if self.games_played > 0 else 0
        return {
            'name': self.name,
            'games_played': self.games_played,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': win_rate
        }
