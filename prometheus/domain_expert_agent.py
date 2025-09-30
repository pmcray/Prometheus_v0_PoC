"""
DomainExpertAgent Template v0.1
Generic agent template that serves as the evolutionary target for RSI

This template provides a basic structure that can be evolved by the SMM
to create specialized agents for different domains (GGP, conversational AI, etc.)
"""

import random
from typing import Dict, List, Any, Optional, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class AgentDomain(Enum):
    """Supported agent domains"""
    GENERAL_GAME_PLAYING = "general_game_playing"
    CONVERSATIONAL_AI = "conversational_ai"
    CODE_OPTIMIZATION = "code_optimization"
    MULTIMODAL_GENERATION = "multimodal_generation"
    MATHEMATICAL_REASONING = "mathematical_reasoning"


@dataclass
class AgentMetadata:
    """Metadata about an agent instance"""
    agent_id: str
    domain: AgentDomain
    generation: int
    parent_ids: List[str]
    fitness_history: List[float]
    created_timestamp: str


class DomainExpertAgent(ABC):
    """
    Base template for domain-specific agents

    This class provides the minimal interface that all domain experts must implement.
    The SMM will evolve concrete implementations of this template for specific tasks.
    """

    def __init__(self, agent_id: str = "agent_000", domain: AgentDomain = AgentDomain.GENERAL_GAME_PLAYING):
        self.agent_id = agent_id
        self.domain = domain
        self.metadata = AgentMetadata(
            agent_id=agent_id,
            domain=domain,
            generation=0,
            parent_ids=[],
            fitness_history=[],
            created_timestamp=""
        )

    @abstractmethod
    def perceive(self, environment_state: Dict[str, Any]) -> Any:
        """
        Perceive and process the current environment state

        Args:
            environment_state: Current state of the environment

        Returns:
            Processed perception data
        """
        pass

    @abstractmethod
    def act(self, perception: Any = None) -> Any:
        """
        Take an action based on perception

        Args:
            perception: Processed perception data from perceive()

        Returns:
            Action to take in the environment
        """
        pass

    def update_metadata(self, fitness_score: float):
        """Update agent metadata with new fitness score"""
        self.metadata.fitness_history.append(fitness_score)

    def get_fitness_trend(self) -> str:
        """Get fitness trend over time"""
        if len(self.metadata.fitness_history) < 2:
            return "insufficient_data"

        recent = self.metadata.fitness_history[-3:]
        if all(recent[i] <= recent[i+1] for i in range(len(recent)-1)):
            return "improving"
        elif all(recent[i] >= recent[i+1] for i in range(len(recent)-1)):
            return "declining"
        else:
            return "stable"


class RandomDomainExpertAgent(DomainExpertAgent):
    """
    Initial random implementation of DomainExpertAgent

    This serves as the starting point for evolution. It implements random
    behavior that should achieve near-zero fitness, providing a baseline
    for the evolutionary process to improve upon.
    """

    def __init__(self, agent_id: str = "random_agent_000", domain: AgentDomain = AgentDomain.GENERAL_GAME_PLAYING):
        super().__init__(agent_id, domain)
        self.action_history = []

    def perceive(self, environment_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Basic perception: just pass through the environment state

        A more evolved agent might extract relevant features, build a mental model,
        or perform strategic analysis here.
        """
        return {
            "raw_state": environment_state,
            "features": {},  # Placeholder for extracted features
            "analysis": {}   # Placeholder for strategic analysis
        }

    def act(self, perception: Any = None) -> Any:
        """
        Random action selection

        An evolved agent should use perception data to make informed decisions.
        The SMM will evolve this method to implement domain-specific strategies.
        """
        # For GGP domain (like Draughts)
        if self.domain == AgentDomain.GENERAL_GAME_PLAYING:
            if perception and "raw_state" in perception:
                state = perception["raw_state"]

                # Extract valid moves if available
                if "valid_moves" in state:
                    valid_moves = state["valid_moves"]
                    if valid_moves:
                        action = random.choice(valid_moves)
                    else:
                        action = None
                else:
                    # Try to infer valid moves from board state
                    action = self._random_game_action(state)
            else:
                action = None

        # For Conversational AI domain
        elif self.domain == AgentDomain.CONVERSATIONAL_AI:
            action = self._random_conversation_response(perception)

        # Default: random action
        else:
            action = None

        # Record action
        self.action_history.append(action)

        return action

    def _random_game_action(self, game_state: Dict[str, Any]) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Generate a random valid game move for Draughts

        This is a placeholder implementation. An evolved agent should implement
        strategic game-playing logic like minimax, alpha-beta pruning, or MCTS.
        """
        try:
            if "board" not in game_state or "current_player" not in game_state:
                return None

            board = game_state["board"]
            current_player = game_state["current_player"]

            # Find all pieces belonging to current player
            valid_moves = []

            for from_row in range(8):
                for from_col in range(8):
                    piece = board[from_row][from_col]

                    # Check if this piece belongs to current player
                    if (current_player == 1 and piece > 0) or (current_player == -1 and piece < 0):
                        # Check all possible directions
                        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                            new_row, new_col = from_row + dr, from_col + dc

                            # Simple move
                            if 0 <= new_row < 8 and 0 <= new_col < 8:
                                if board[new_row][new_col] == 0:
                                    valid_moves.append(((from_row, from_col), (new_row, new_col)))

                            # Capture move
                            capture_row, capture_col = from_row + dr, from_col + dc
                            land_row, land_col = from_row + 2*dr, from_col + 2*dc

                            if 0 <= land_row < 8 and 0 <= land_col < 8:
                                if 0 <= capture_row < 8 and 0 <= capture_col < 8:
                                    if board[land_row][land_col] == 0:
                                        capture_piece = board[capture_row][capture_col]
                                        if (piece > 0 and capture_piece < 0) or (piece < 0 and capture_piece > 0):
                                            valid_moves.append(((from_row, from_col), (land_row, land_col)))

            return random.choice(valid_moves) if valid_moves else None

        except Exception as e:
            return None

    def _random_conversation_response(self, perception: Any) -> str:
        """
        Generate a random conversation response

        This is a placeholder. An evolved agent should implement sophisticated
        NLU, dialogue management, and response generation.
        """
        generic_responses = [
            "That's interesting. Could you tell me more?",
            "I understand. Let me think about that.",
            "That's a good point. Here's what I think...",
            "I see what you mean. Let me help with that.",
            "Interesting question. Let me provide some information."
        ]

        return random.choice(generic_responses)

    # Evolution target methods
    # These methods are placeholders that the SMM can evolve to add strategic capabilities

    def evaluate_position(self, state: Dict[str, Any]) -> float:
        """
        Evaluate the quality of a game position

        EVOLUTION TARGET: SMM should evolve this to implement domain-specific
        evaluation functions (e.g., piece counting, positional advantage, etc.)
        """
        return random.random()  # Random evaluation

    def search(self, state: Dict[str, Any], depth: int = 1) -> Any:
        """
        Perform lookahead search

        EVOLUTION TARGET: SMM should evolve this to implement search algorithms
        like minimax, MCTS, or beam search
        """
        return self.act(self.perceive(state))  # No search, just random

    def learn_from_experience(self, state: Dict[str, Any], action: Any, reward: float):
        """
        Learn from experience (optional)

        EVOLUTION TARGET: SMM could evolve online learning capabilities
        """
        pass  # No learning in base template


class GamePlayingExpertAgent(RandomDomainExpertAgent):
    """
    Specialized template for game-playing agents

    This provides a slightly more structured starting point for game-playing evolution.
    Still performs randomly but with clearer separation of concerns.
    """

    def __init__(self, agent_id: str = "game_agent_000"):
        super().__init__(agent_id, AgentDomain.GENERAL_GAME_PLAYING)

    def perceive(self, environment_state: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced perception for game playing"""
        perception = super().perceive(environment_state)

        # Add game-specific feature extraction
        if "board" in environment_state:
            perception["features"] = {
                "piece_count": self._count_pieces(environment_state["board"]),
                "mobility": self._estimate_mobility(environment_state),
            }

        return perception

    def _count_pieces(self, board: List[List[int]]) -> Dict[str, int]:
        """Count pieces on the board"""
        counts = {"player1": 0, "player2": 0, "player1_kings": 0, "player2_kings": 0}

        for row in board:
            for piece in row:
                if piece == 1:
                    counts["player1"] += 1
                elif piece == 2:
                    counts["player1_kings"] += 1
                elif piece == -1:
                    counts["player2"] += 1
                elif piece == -2:
                    counts["player2_kings"] += 1

        return counts

    def _estimate_mobility(self, game_state: Dict[str, Any]) -> int:
        """Estimate number of possible moves (mobility heuristic)"""
        # This is a placeholder - evolved agents should implement proper mobility calculation
        return random.randint(5, 15)


class ConversationalExpertAgent(RandomDomainExpertAgent):
    """
    Specialized template for conversational AI agents

    Provides structure for dialogue management and response generation.
    """

    def __init__(self, agent_id: str = "chat_agent_000"):
        super().__init__(agent_id, AgentDomain.CONVERSATIONAL_AI)
        self.conversation_context = []

    def perceive(self, environment_state: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced perception for conversation"""
        perception = super().perceive(environment_state)

        # Extract conversation history if available
        if "conversation_history" in environment_state:
            self.conversation_context = environment_state["conversation_history"]
            perception["features"] = {
                "conversation_length": len(self.conversation_context),
                "last_user_message": self._get_last_user_message(),
                "topic_keywords": self._extract_keywords()
            }

        return perception

    def _get_last_user_message(self) -> str:
        """Get the last user message from context"""
        for msg in reversed(self.conversation_context):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return ""

    def _extract_keywords(self) -> List[str]:
        """Extract keywords from conversation (placeholder)"""
        # Evolved agents should implement proper NLU
        return []

    def generate_response(self, conversation_history: List[Dict[str, str]]) -> str:
        """
        Generate conversational response

        This is the main interface for conversational agents.
        EVOLUTION TARGET: SMM should evolve sophisticated response generation.
        """
        environment_state = {"conversation_history": conversation_history}
        perception = self.perceive(environment_state)
        return self.act(perception)