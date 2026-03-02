"""
Prometheus Attention Visualization

Explainability tools using attention/saliency maps:
- GradCAM: Gradient-weighted Class Activation Mapping
- Saliency maps: Show what the network "looks at"
- Attribution overlays: Highlight important squares
- Heatmap visualization: See decision-making process

Makes AI decisions interpretable and builds client trust.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.patheffects as patheffects
import tensorflow as tf
from tensorflow import keras
import chess
from typing import Optional, Tuple, Any
from IPython.display import display, HTML


def compute_gradcam(
    model: keras.Model,
    input_data: np.ndarray,
    layer_name: Optional[str] = None,
    class_idx: Optional[int] = None
) -> np.ndarray:
    """
    Compute GradCAM (Gradient-weighted Class Activation Mapping).

    GradCAM highlights which regions of the input the model focuses on
    when making predictions. For chess, this shows which squares matter.

    Args:
        model: Keras model
        input_data: Input board state (8×8×19)
        layer_name: Target convolutional layer (None = last conv layer)
        class_idx: Output class to visualize (None = predicted class)

    Returns:
        8×8 heatmap showing attention
    """
    # Find last convolutional layer if not specified
    if layer_name is None:
        for layer in reversed(model.layers):
            if 'conv' in layer.name.lower():
                layer_name = layer.name
                break

    if layer_name is None:
        raise ValueError("No convolutional layer found in model")

    # Create gradient model
    grad_model = keras.Model(
        inputs=model.input,
        outputs=[model.get_layer(layer_name).output, model.output]
    )

    # Compute gradients
    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(input_data)

        # If multi-output model (policy, value), use policy
        if isinstance(predictions, list):
            predictions = predictions[0]  # Use policy head

        # Get class of interest
        if class_idx is None:
            class_idx = tf.argmax(predictions[0])

        # Get prediction for class
        class_channel = predictions[:, class_idx]

    # Compute gradients of class with respect to feature map
    grads = tape.gradient(class_channel, conv_outputs)

    # Global average pooling of gradients
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    # Weight feature maps by gradients
    conv_outputs = conv_outputs[0]
    pooled_grads = pooled_grads.numpy()

    # Create heatmap
    heatmap = np.zeros(conv_outputs.shape[:2])
    for i, weight in enumerate(pooled_grads):
        heatmap += weight * conv_outputs[:, :, i]

    # Normalize to [0, 1]
    heatmap = np.maximum(heatmap, 0)  # ReLU
    if np.max(heatmap) > 0:
        heatmap /= np.max(heatmap)

    # Resize to 8×8 if needed
    if heatmap.shape != (8, 8):
        from scipy.ndimage import zoom
        factors = (8 / heatmap.shape[0], 8 / heatmap.shape[1])
        heatmap = zoom(heatmap, factors, order=1)

    return heatmap


def compute_saliency_map(
    model: keras.Model,
    input_data: np.ndarray,
    class_idx: Optional[int] = None
) -> np.ndarray:
    """
    Compute saliency map using input gradients.

    Shows which input features (squares/pieces) most influence the prediction.

    Args:
        model: Keras model
        input_data: Input board state
        class_idx: Output class (None = predicted class)

    Returns:
        8×8×19 gradient map (same shape as input)
    """
    input_tensor = tf.Variable(input_data, dtype=tf.float32)

    with tf.GradientTape() as tape:
        tape.watch(input_tensor)
        predictions = model(input_tensor)

        # Handle multi-output
        if isinstance(predictions, list):
            predictions = predictions[0]

        if class_idx is None:
            class_idx = tf.argmax(predictions[0])

        class_channel = predictions[:, class_idx]

    # Compute gradients
    grads = tape.gradient(class_channel, input_tensor)
    grads = grads.numpy()[0]

    # Take absolute value and sum across channels
    saliency = np.abs(grads).sum(axis=-1)

    # Normalize
    if np.max(saliency) > 0:
        saliency /= np.max(saliency)

    return saliency


class ChessAttentionVisualizer:
    """
    Visualize attention/saliency for chess positions.

    Makes neural network decisions interpretable by showing:
    - Which squares the network focuses on
    - How piece positions influence decisions
    - What the AI "sees" when evaluating positions
    """

    def __init__(self, agent: Any):
        """
        Initialize attention visualizer.

        Args:
            agent: Chess agent with Keras model
        """
        self.agent = agent
        self.model = agent.model

    def visualize_attention(
        self,
        board: chess.Board,
        method: str = 'gradcam',
        move_idx: Optional[int] = None,
        save_path: Optional[str] = None
    ) -> Tuple[np.ndarray, plt.Figure]:
        """
        Visualize attention for a chess position.

        Args:
            board: Chess board to visualize
            method: 'gradcam' or 'saliency'
            move_idx: Move to visualize (None = best move)
            save_path: Path to save figure

        Returns:
            Tuple of (attention_map, matplotlib_figure)
        """
        from prometheus.environments.chess import ChessBoardEncoder

        # Encode board
        encoder = ChessBoardEncoder()
        board_state = encoder.encode_full(board)
        board_state_batch = np.expand_dims(board_state, axis=0)

        # Compute attention
        if method == 'gradcam':
            attention = compute_gradcam(self.model, board_state_batch, class_idx=move_idx)
        elif method == 'saliency':
            attention = compute_saliency_map(self.model, board_state_batch, class_idx=move_idx)
        else:
            raise ValueError(f"Unknown method: {method}")

        # Create visualization
        fig = self._plot_attention_overlay(board, attention, method)

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')

        return attention, fig

    def _plot_attention_overlay(
        self,
        board: chess.Board,
        attention: np.ndarray,
        method: str
    ) -> plt.Figure:
        """
        Plot attention heatmap overlaid on chess board.

        Args:
            board: Chess board
            attention: 8×8 attention map
            method: Visualization method name

        Returns:
            Matplotlib figure
        """
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))

        # Left: Original board
        self._draw_board(ax1, board)
        ax1.set_title('Chess Position', fontsize=14, fontweight='bold')

        # Middle: Attention heatmap
        im = ax2.imshow(attention, cmap='hot', interpolation='bilinear', vmin=0, vmax=1)
        ax2.set_title(f'Attention Map ({method.upper()})', fontsize=14, fontweight='bold')
        ax2.set_xticks(range(8))
        ax2.set_yticks(range(8))
        ax2.set_xticklabels(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'])
        ax2.set_yticklabels(['1', '2', '3', '4', '5', '6', '7', '8'])
        ax2.grid(True, color='white', linewidth=0.5, alpha=0.5)
        plt.colorbar(im, ax=ax2, label='Attention Intensity')

        # Right: Overlay
        self._draw_board_with_attention(ax3, board, attention)
        ax3.set_title('Attention Overlay', fontsize=14, fontweight='bold')

        plt.tight_layout()
        return fig

    def _draw_board(self, ax: plt.Axes, board: chess.Board):
        """Draw chess board with pieces."""
        # Draw squares
        for rank in range(8):
            for file in range(8):
                color = 'wheat' if (rank + file) % 2 == 0 else 'tan'
                ax.add_patch(patches.Rectangle(
                    (file, 7-rank), 1, 1,
                    facecolor=color, edgecolor='black', linewidth=1
                ))

                # Draw piece if present
                square = chess.square(file, rank)
                piece = board.piece_at(square)
                if piece:
                    symbol = piece.unicode_symbol()
                    ax.text(file + 0.5, 7-rank + 0.5, symbol,
                           fontsize=32, ha='center', va='center')

        ax.set_xlim(0, 8)
        ax.set_ylim(0, 8)
        ax.set_aspect('equal')
        ax.set_xticks(range(8))
        ax.set_yticks(range(8))
        ax.set_xticklabels(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'])
        ax.set_yticklabels(['1', '2', '3', '4', '5', '6', '7', '8'])
        ax.invert_yaxis()

    def _draw_board_with_attention(
        self,
        ax: plt.Axes,
        board: chess.Board,
        attention: np.ndarray
    ):
        """Draw board with attention heatmap overlay."""
        # Draw attention heatmap
        ax.imshow(attention, cmap='hot', interpolation='bilinear',
                 alpha=0.6, extent=[0, 8, 0, 8], vmin=0, vmax=1)

        # Draw board squares and pieces
        for rank in range(8):
            for file in range(8):
                # Light border for squares
                ax.add_patch(patches.Rectangle(
                    (file, 7-rank), 1, 1,
                    facecolor='none', edgecolor='gray',
                    linewidth=1, alpha=0.3
                ))

                # Draw piece
                square = chess.square(file, rank)
                piece = board.piece_at(square)
                if piece:
                    symbol = piece.unicode_symbol()
                    # Add white outline for visibility
                    ax.text(file + 0.5, 7-rank + 0.5, symbol,
                           fontsize=32, ha='center', va='center',
                           color='white', weight='bold',
                           path_effects=[
                               patheffects.withStroke(
                                   linewidth=3, foreground='black'
                               )
                           ])

        ax.set_xlim(0, 8)
        ax.set_ylim(0, 8)
        ax.set_aspect('equal')
        ax.set_xticks(range(8))
        ax.set_yticks(range(8))
        ax.set_xticklabels(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'])
        ax.set_yticklabels(['1', '2', '3', '4', '5', '6', '7', '8'])
        ax.invert_yaxis()

    def compare_move_attention(
        self,
        board: chess.Board,
        moves: list,
        method: str = 'gradcam'
    ) -> plt.Figure:
        """
        Compare attention for different moves.

        Args:
            board: Chess board
            moves: List of moves to compare
            method: Attention method

        Returns:
            Matplotlib figure comparing attention for each move
        """
        from prometheus.environments.chess import ChessMoveEncoder

        encoder = ChessMoveEncoder()

        n_moves = len(moves)
        fig, axes = plt.subplots(2, n_moves, figsize=(6*n_moves, 12))

        if n_moves == 1:
            axes = axes.reshape(2, 1)

        for i, move in enumerate(moves):
            move_idx = encoder.move_to_index(move)

            # Get attention
            attention, _ = self.visualize_attention(
                board, method=method, move_idx=move_idx, save_path=None
            )

            # Top: board
            self._draw_board(axes[0, i], board)
            axes[0, i].set_title(f'Move: {move.uci()}', fontsize=12, fontweight='bold')

            # Bottom: attention
            im = axes[1, i].imshow(attention, cmap='hot', interpolation='bilinear')
            axes[1, i].set_title(f'Attention for {move.uci()}', fontsize=12, fontweight='bold')
            axes[1, i].set_xticks(range(8))
            axes[1, i].set_xticklabels(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'])
            axes[1, i].set_yticks(range(8))
            axes[1, i].set_yticklabels(['1', '2', '3', '4', '5', '6', '7', '8'])
            plt.colorbar(im, ax=axes[1, i])

        plt.tight_layout()
        return fig


def explain_position(
    agent: Any,
    board: chess.Board,
    top_k: int = 3
) -> dict:
    """
    Generate comprehensive explanation of agent's position evaluation.

    Args:
        agent: Chess agent
        board: Board position to explain
        top_k: Number of top moves to explain

    Returns:
        Dictionary with explanation data
    """
    from prometheus.environments.chess import ChessBoardEncoder, ChessMoveEncoder

    # Get predictions
    encoder = ChessBoardEncoder()
    move_encoder = ChessMoveEncoder()

    state = encoder.encode_full(board)
    state_batch = np.expand_dims(state, axis=0)

    policy, value = agent.model.predict(state_batch, verbose=0)
    policy = policy[0]
    value = value[0, 0]

    # Get top moves
    legal_moves = list(board.legal_moves)
    move_probs = []

    for move in legal_moves:
        idx = move_encoder.move_to_index(move)
        prob = policy[idx]
        move_probs.append((move, prob))

    move_probs.sort(key=lambda x: x[1], reverse=True)
    top_moves = move_probs[:top_k]

    # Generate explanation
    explanation = {
        'position_value': float(value),
        'position_assessment': _assess_position(value),
        'top_moves': [
            {
                'move': move.uci(),
                'probability': float(prob),
                'confidence': _confidence_level(prob)
            }
            for move, prob in top_moves
        ],
        'decision_clarity': _decision_clarity(policy, legal_moves, move_encoder)
    }

    return explanation


def _assess_position(value: float) -> str:
    """Convert value to human-readable assessment."""
    if value > 0.5:
        return "Strong advantage for White"
    elif value > 0.2:
        return "Slight advantage for White"
    elif value > -0.2:
        return "Balanced position"
    elif value > -0.5:
        return "Slight advantage for Black"
    else:
        return "Strong advantage for Black"


def _confidence_level(prob: float) -> str:
    """Convert probability to confidence level."""
    if prob > 0.5:
        return "Very High"
    elif prob > 0.3:
        return "High"
    elif prob > 0.15:
        return "Medium"
    else:
        return "Low"


def _decision_clarity(
    policy: np.ndarray,
    legal_moves: list,
    encoder: Any
) -> str:
    """Assess how clear the decision is."""
    # Get probabilities for legal moves
    probs = []
    for move in legal_moves:
        idx = encoder.move_to_index(move)
        probs.append(policy[idx])

    probs = np.array(probs)
    if len(probs) > 0:
        probs = probs / np.sum(probs)  # Normalize

    # Check entropy
    if len(probs) > 0:
        max_prob = np.max(probs)
        if max_prob > 0.6:
            return "Clear (strong preference for one move)"
        elif max_prob > 0.3:
            return "Moderate (several good options)"
        else:
            return "Unclear (many similar options)"
    else:
        return "Unknown"
