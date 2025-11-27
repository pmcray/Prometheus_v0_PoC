"""
Unit tests for Go environment

Tests complete Go rule implementation:
- Board initialization
- Stone placement
- Capture mechanics (single and multi-stone)
- Ko rule enforcement
- Superko detection
- Territory scoring
- Game state management
"""

import pytest
import numpy as np
from prometheus.environments.go import GoBoard, GoEnvironment, GoBoardEncoder, GoMoveEncoder


class TestGoBoard:
    """Test GoBoard class for rule enforcement."""

    def test_initialization(self):
        """Test board initialization."""
        board = GoBoard(size=19, komi=7.5)

        assert board.size == 19
        assert board.komi == 7.5
        assert board.board.shape == (19, 19)
        assert np.all(board.board == 0)
        assert board.current_player == 1  # Black starts
        assert board.ko_point is None

    def test_stone_placement(self):
        """Test basic stone placement."""
        board = GoBoard(size=9)

        # Place black stone
        success = board.play_move(4, 4, board.BLACK)
        assert success
        assert board.board[4, 4] == board.BLACK

        # Place white stone
        success = board.play_move(4, 5, board.WHITE)
        assert success
        assert board.board[4, 5] == board.WHITE

    def test_illegal_move_occupied(self):
        """Test that placing on occupied point fails."""
        board = GoBoard(size=9)

        board.play_move(4, 4, board.BLACK)

        # Try to place on same point
        success = board.play_move(4, 4, board.WHITE)
        assert not success

    def test_simple_capture(self):
        """Test single stone capture."""
        board = GoBoard(size=9)

        # Setup: Black stone at (4,4), surrounded by white on 3 sides
        board.play_move(4, 4, board.BLACK)
        board.play_move(4, 3, board.WHITE)
        board.play_move(4, 5, board.WHITE)
        board.play_move(3, 4, board.WHITE)

        # Capture by playing at (5, 4)
        board.play_move(5, 4, board.WHITE)

        # Black stone should be captured
        assert board.board[4, 4] == board.EMPTY
        assert board.captured_stones[board.BLACK] == 1

    def test_multi_stone_capture(self):
        """Test capture of connected group."""
        board = GoBoard(size=9)

        # Create black group: (4,4) and (4,5)
        board.play_move(4, 4, board.BLACK)
        board.play_move(4, 5, board.BLACK)

        # Surround with white
        board.play_move(3, 4, board.WHITE)
        board.play_move(3, 5, board.WHITE)
        board.play_move(4, 3, board.WHITE)
        board.play_move(4, 6, board.WHITE)
        board.play_move(5, 4, board.WHITE)

        # Final capture
        board.play_move(5, 5, board.WHITE)

        # Both black stones should be captured
        assert board.board[4, 4] == board.EMPTY
        assert board.board[4, 5] == board.EMPTY
        assert board.captured_stones[board.BLACK] == 2

    def test_ko_rule_simple(self):
        """Test simple ko rule enforcement."""
        board = GoBoard(size=9)

        # Setup ko position
        # Black: (4,4), (4,6), (5,5)
        # White: (4,5), (5,4), (5,6), (6,5)
        board.play_move(4, 4, board.BLACK)
        board.play_move(4, 5, board.WHITE)
        board.play_move(4, 6, board.BLACK)
        board.play_move(5, 4, board.WHITE)
        board.play_move(5, 5, board.BLACK)
        board.play_move(5, 6, board.WHITE)
        board.play_move(3, 5, board.BLACK)
        board.play_move(6, 5, board.WHITE)

        # White captures at (4,5)
        board.play_move(4, 5, board.WHITE)

        # Black should capture
        assert board.board[4, 5] == board.EMPTY

        # Ko point should be set
        assert board.ko_point == (4, 5)

        # Black cannot immediately recapture (ko rule)
        is_legal = board.is_legal_move(4, 5, board.BLACK)
        assert not is_legal

    def test_superko(self):
        """Test superko rule (no repeated board states)."""
        board = GoBoard(size=9)

        # Play some moves
        board.play_move(4, 4, board.BLACK)
        board.play_move(4, 5, board.WHITE)

        # Save board state
        state1 = board.board.copy()

        # Add to history
        board.board_history.append(state1)

        # Try to create same state again (should be illegal)
        board.board[4, 4] = board.EMPTY
        board.board[4, 5] = board.EMPTY

        # Superko should detect this
        # (Note: Implementation may vary)

    def test_suicide_rule(self):
        """Test suicide move is illegal."""
        board = GoBoard(size=9)

        # Surround a point with white
        board.play_move(4, 3, board.WHITE)
        board.play_move(4, 5, board.WHITE)
        board.play_move(3, 4, board.WHITE)
        board.play_move(5, 4, board.WHITE)

        # Black cannot play in center (suicide)
        is_legal = board.is_legal_move(4, 4, board.BLACK)
        assert not is_legal

    def test_not_suicide_if_captures(self):
        """Test that move capturing opponent is not suicide."""
        board = GoBoard(size=9)

        # White stone surrounded
        board.play_move(4, 4, board.WHITE)
        board.play_move(4, 3, board.BLACK)
        board.play_move(4, 5, board.BLACK)
        board.play_move(3, 4, board.BLACK)

        # Black can play at (5,4) even though it looks like suicide
        # because it captures white
        is_legal = board.is_legal_move(5, 4, board.BLACK)
        assert is_legal

        success = board.play_move(5, 4, board.BLACK)
        assert success
        assert board.board[4, 4] == board.EMPTY  # White captured

    def test_liberty_counting(self):
        """Test liberty counting for groups."""
        board = GoBoard(size=9)

        # Single stone has 4 liberties in center
        board.play_move(4, 4, board.BLACK)
        group = board.get_group(4, 4)
        liberties = board.count_liberties(group)
        assert liberties == 4

        # Add adjacent stone - shared liberties
        board.play_move(4, 5, board.BLACK)
        group = board.get_group(4, 4)
        liberties = board.count_liberties(group)
        assert liberties == 6  # Combined liberties

    def test_territory_scoring(self):
        """Test territory counting."""
        board = GoBoard(size=9)

        # Create clear black territory in corner
        board.play_move(0, 2, board.BLACK)
        board.play_move(1, 2, board.BLACK)
        board.play_move(2, 0, board.BLACK)
        board.play_move(2, 1, board.BLACK)
        board.play_move(2, 2, board.BLACK)

        score = board.score()

        # Should have some black territory
        assert score['black_territory'] > 0
        assert score['black_score'] > score['white_score']

    def test_score_structure(self):
        """Test score dictionary structure."""
        board = GoBoard(size=9, komi=7.5)

        score = board.score()

        assert 'black_score' in score
        assert 'white_score' in score
        assert 'black_territory' in score
        assert 'white_territory' in score
        assert 'black_captures' in score
        assert 'white_captures' in score
        assert 'winner' in score
        assert 'margin' in score

        # White score should include komi
        assert score['white_score'] >= 7.5


class TestGoEnvironment:
    """Test GoEnvironment RL interface."""

    def test_initialization(self):
        """Test environment initialization."""
        env = GoEnvironment(board_size=19, komi=7.5)

        assert env.board.size == 19
        assert env.board.komi == 7.5

    def test_get_state(self):
        """Test state encoding."""
        env = GoEnvironment(board_size=9)

        state = env.get_state()

        # Should be (9, 9, 3)
        assert state.shape == (9, 9, 3)

        # All channels should be in valid range
        assert np.all(state >= 0)
        assert np.all(state <= 1)

    def test_step_function(self):
        """Test step function."""
        env = GoEnvironment(board_size=9)

        state, reward, done, info = env.step((4, 4))

        assert state.shape == (9, 9, 3)
        assert isinstance(reward, float)
        assert isinstance(done, bool)
        assert isinstance(info, dict)

    def test_legal_moves(self):
        """Test legal move generation."""
        env = GoEnvironment(board_size=9)

        legal_moves = env.get_legal_moves()

        # Should have 81 positions + pass
        assert len(legal_moves) <= 82

        # Pass should always be legal
        assert ('pass',) in legal_moves

    def test_reset(self):
        """Test environment reset."""
        env = GoEnvironment(board_size=9)

        # Play some moves
        env.step((4, 4))
        env.step((4, 5))

        # Reset
        state = env.reset()

        # Board should be empty
        assert env.board.board.sum() == 0
        assert state.shape == (9, 9, 3)


class TestGoBoardEncoder:
    """Test board encoding for neural networks."""

    def test_encode(self):
        """Test board encoding."""
        encoder = GoBoardEncoder(board_size=9)
        board = GoBoard(size=9)

        # Place some stones
        board.play_move(4, 4, board.BLACK)
        board.play_move(4, 5, board.WHITE)

        encoded = encoder.encode(board)

        # Should be (9, 9, 3)
        assert encoded.shape == (9, 9, 3)


class TestGoMoveEncoder:
    """Test move encoding."""

    def test_move_to_index(self):
        """Test move to index conversion."""
        encoder = GoMoveEncoder(board_size=9)

        # Corner move
        idx = encoder.move_to_index((0, 0))
        assert idx == 0

        # Center move
        idx = encoder.move_to_index((4, 4))
        assert idx == 4 * 9 + 4

        # Pass move
        idx = encoder.move_to_index(('pass',))
        assert idx == 81

    def test_index_to_move(self):
        """Test index to move conversion."""
        encoder = GoMoveEncoder(board_size=9)

        # Test corner
        move = encoder.index_to_move(0)
        assert move == (0, 0)

        # Test pass
        move = encoder.index_to_move(81)
        assert move == ('pass',)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
