"""
Monte Carlo Tree Search for Go

Adapts MCTS from chess to Go with Go-specific considerations:
- Larger action space (19×19 + pass = 362 actions)
- Territory evaluation
- Ko and superko rules
- Different endgame conditions

Based on AlphaGo/AlphaZero approach.
"""

import numpy as np
from typing import Optional, Dict, Tuple, Any
import copy


class GoMCTSNode:
    """
    Node in the MCTS tree for Go.

    Each node represents a board state and stores:
    - Visit counts
    - Value estimates
    - Prior probabilities from policy network
    - Children (next board states)
    """

    def __init__(
        self,
        board_state: Any,  # GoBoard object
        parent: Optional['GoMCTSNode'] = None,
        prior: float = 0.0,
        move: Optional[Tuple] = None
    ):
        """
        Initialize MCTS node.

        Args:
            board_state: Go board state
            parent: Parent node
            prior: Prior probability from policy network
            move: Move that led to this state
        """
        self.board_state = board_state
        self.parent = parent
        self.prior = prior
        self.move = move

        # MCTS statistics
        self.visit_count = 0
        self.total_value = 0.0
        self.mean_value = 0.0

        # Children nodes
        self.children: Dict[Tuple, 'GoMCTSNode'] = {}
        self.is_expanded = False

    def select_child(self, c_puct: float = 1.0) -> 'GoMCTSNode':
        """
        Select best child using PUCT algorithm (AlphaGo Zero).

        PUCT = Q + c_puct * P * sqrt(N_parent) / (1 + N_child)

        Where:
        - Q: Mean action value
        - P: Prior probability from policy network
        - N: Visit count

        Args:
            c_puct: Exploration constant (higher = more exploration)

        Returns:
            Best child node
        """
        best_score = -float('inf')
        best_child = None

        for child in self.children.values():
            # Q-value (from child's perspective)
            q_value = -child.mean_value if child.visit_count > 0 else 0.0

            # U-value (exploration bonus)
            u_value = c_puct * child.prior * np.sqrt(self.visit_count) / (1 + child.visit_count)

            # PUCT score
            puct_score = q_value + u_value

            if puct_score > best_score:
                best_score = puct_score
                best_child = child

        return best_child

    def expand(self, policy_probs: np.ndarray, legal_moves: list, board_size: int):
        """
        Expand node by adding all legal move children.

        Args:
            policy_probs: Policy network output (move probabilities)
            legal_moves: List of legal moves [(row, col), ...] or [('pass',)]
            board_size: Size of Go board
        """
        if self.is_expanded:
            return

        # Create child for each legal move
        for move in legal_moves:
            # Get prior probability for this move
            if move == ('pass',):
                move_idx = board_size * board_size  # Pass is last action
            else:
                row, col = move
                move_idx = row * board_size + col

            prior = policy_probs[move_idx]

            # Create child board state
            child_board = copy.deepcopy(self.board_state)

            # Execute move on child board
            if move == ('pass',):
                # Pass doesn't change board, just switches player
                child_board.current_player *= -1
            else:
                row, col = move
                child_board.play_move(row, col, child_board.current_player)

            # Create child node
            child_node = GoMCTSNode(
                board_state=child_board,
                parent=self,
                prior=prior,
                move=move
            )

            self.children[move] = child_node

        self.is_expanded = True

    def update(self, value: float):
        """
        Update node statistics with backpropagation.

        Args:
            value: Value to backpropagate (from leaf evaluation)
        """
        self.visit_count += 1
        self.total_value += value
        self.mean_value = self.total_value / self.visit_count

    def is_leaf(self) -> bool:
        """Check if node is a leaf (not expanded)."""
        return not self.is_expanded


class GoMCTS:
    """
    Monte Carlo Tree Search for Go.

    Combines neural network guidance with tree search:
    1. Selection: Traverse tree using PUCT
    2. Expansion: Add new nodes using policy network
    3. Evaluation: Evaluate leaf using value network
    4. Backpropagation: Update all ancestor nodes

    This is the AlphaGo Zero / AlphaZero algorithm.
    """

    def __init__(
        self,
        agent: Any,  # Go agent with policy-value network
        num_simulations: int = 800,
        c_puct: float = 1.0,
        temperature: float = 1.0
    ):
        """
        Initialize MCTS.

        Args:
            agent: Go agent with predict() method returning (policy, value)
            num_simulations: Number of MCTS simulations per move
            c_puct: Exploration constant for PUCT
            temperature: Temperature for move selection
        """
        self.agent = agent
        self.num_simulations = num_simulations
        self.c_puct = c_puct
        self.temperature = temperature

    def search(self, board_state: Any) -> Tuple:
        """
        Run MCTS search and return best move.

        Args:
            board_state: Current Go board state

        Returns:
            Best move as (row, col) or ('pass',)
        """
        from prometheus.environments.go import GoEnvironment

        # Create root node
        root = GoMCTSNode(board_state=copy.deepcopy(board_state))

        # Run simulations
        for _ in range(self.num_simulations):
            node = root

            # 1. SELECTION: Traverse tree to leaf
            while not node.is_leaf():
                node = node.select_child(self.c_puct)

            # 2. EXPANSION: Expand leaf node
            if node.visit_count > 0:  # Only expand visited nodes
                # Get policy and value from neural network
                env = GoEnvironment(board_size=board_state.size)
                env.board = node.board_state
                state_array = env.get_state()

                policy, value = self.agent.predict(state_array)

                # Get legal moves
                legal_moves = env.get_legal_moves()

                # Expand node with legal moves
                node.expand(policy, legal_moves, board_state.size)

                # If no children (game over), use terminal value
                if not node.children:
                    score_dict = node.board_state.score()
                    # Value from current player's perspective
                    if node.board_state.current_player == 1:  # Black
                        value = 1.0 if score_dict['black_score'] > score_dict['white_score'] else -1.0
                    else:  # White
                        value = 1.0 if score_dict['white_score'] > score_dict['black_score'] else -1.0
            else:
                # First visit: evaluate with neural network
                env = GoEnvironment(board_size=board_state.size)
                env.board = node.board_state
                state_array = env.get_state()

                _, value = self.agent.predict(state_array)

            # 3. BACKPROPAGATION: Update all ancestors
            while node is not None:
                node.update(value)
                value = -value  # Flip value for parent (alternating players)
                node = node.parent

        # 4. MOVE SELECTION: Choose best move from root
        return self._select_move(root)

    def _select_move(self, root: GoMCTSNode) -> Tuple:
        """
        Select move from root node based on visit counts.

        Uses temperature for exploration vs exploitation:
        - temperature=0: Always pick most visited (greedy)
        - temperature=1: Sample proportional to visits
        - temperature>1: More exploration

        Args:
            root: Root node after search

        Returns:
            Selected move
        """
        if not root.children:
            return ('pass',)

        # Get visit counts
        moves = list(root.children.keys())
        visit_counts = np.array([root.children[move].visit_count for move in moves])

        if self.temperature < 0.01:  # Greedy
            best_idx = np.argmax(visit_counts)
            return moves[best_idx]
        else:  # Temperature sampling
            # Apply temperature
            visit_counts = visit_counts ** (1.0 / self.temperature)
            probs = visit_counts / visit_counts.sum()

            # Sample move
            move_idx = np.random.choice(len(moves), p=probs)
            return moves[move_idx]

    def get_policy(self, board_state: Any) -> np.ndarray:
        """
        Get improved policy from MCTS search.

        The MCTS-improved policy is often better than the raw
        neural network policy, especially in tactical positions.

        Args:
            board_state: Current board state

        Returns:
            Policy array (move probabilities)
        """
        # Run search
        root = GoMCTSNode(board_state=copy.deepcopy(board_state))

        for _ in range(self.num_simulations):
            node = root

            # Selection
            while not node.is_leaf():
                node = node.select_child(self.c_puct)

            # Expansion & Evaluation
            if node.visit_count > 0:
                from prometheus.environments.go import GoEnvironment
                env = GoEnvironment(board_size=board_state.size)
                env.board = node.board_state
                state_array = env.get_state()

                policy, value = self.agent.predict(state_array)
                legal_moves = env.get_legal_moves()
                node.expand(policy, legal_moves, board_state.size)
            else:
                from prometheus.environments.go import GoEnvironment
                env = GoEnvironment(board_size=board_state.size)
                env.board = node.board_state
                state_array = env.get_state()
                _, value = self.agent.predict(state_array)

            # Backpropagation
            while node is not None:
                node.update(value)
                value = -value
                node = node.parent

        # Extract policy from visit counts
        policy = np.zeros(board_state.size * board_state.size + 1)

        for move, child in root.children.items():
            if move == ('pass',):
                move_idx = board_state.size * board_state.size
            else:
                row, col = move
                move_idx = row * board_state.size + col

            policy[move_idx] = child.visit_count

        # Normalize
        if policy.sum() > 0:
            policy /= policy.sum()

        return policy


class GoMCTSAgent:
    """
    Go agent that uses MCTS to enhance a base neural network agent.

    This wraps any Go agent (Static or Prometheus) with MCTS search
    for stronger play. Expected improvement: +300-500 ELO.

    Usage:
        >>> base_agent = PrometheusGoAgent(board_size=19)
        >>> mcts_agent = GoMCTSAgent(base_agent, num_simulations=800)
        >>> move = mcts_agent.get_move(state, legal_moves)
    """

    def __init__(
        self,
        base_agent: Any,
        num_simulations: int = 800,
        c_puct: float = 1.0,
        temperature: float = 1.0
    ):
        """
        Initialize MCTS-enhanced agent.

        Args:
            base_agent: Base Go agent with policy-value network
            num_simulations: Number of MCTS simulations per move
            c_puct: Exploration constant
            temperature: Move selection temperature
        """
        self.base_agent = base_agent
        self.mcts = GoMCTS(
            agent=base_agent,
            num_simulations=num_simulations,
            c_puct=c_puct,
            temperature=temperature
        )
        self.name = f"MCTS_{base_agent.name}"

    def get_move(self, state: np.ndarray, legal_moves: list, temperature: float = 1.0) -> Tuple:
        """
        Get move using MCTS search.

        Args:
            state: Board state array
            legal_moves: List of legal moves
            temperature: Move selection temperature (overrides constructor)

        Returns:
            Best move from MCTS
        """
        # Update temperature if specified
        self.mcts.temperature = temperature

        # Reconstruct board from state
        from prometheus.environments.go import GoBoard
        board_size = state.shape[0]
        board = GoBoard(size=board_size)

        # Decode state into board
        # State format: (board_size, board_size, 3)
        # Channel 0: Current player's stones
        # Channel 1: Opponent's stones
        # Channel 2: Current player indicator

        current_player = 1 if state[0, 0, 2] > 0.5 else -1
        board.board = state[:, :, 0] - state[:, :, 1]  # Combine channels
        board.current_player = current_player

        # Run MCTS
        return self.mcts.search(board)

    def predict(self, state: np.ndarray) -> Tuple[np.ndarray, float]:
        """Use base agent's predict method."""
        return self.base_agent.predict(state)

    def evaluate(self, state: np.ndarray) -> float:
        """Use base agent's evaluate method."""
        return self.base_agent.evaluate(state)
