#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARC Parametric Operations Library (v0.96 - Option E Phase 1)

This module provides a clean, unified library of parametric operations for
ARC-AGI program synthesis. Each operation supports flexible parameters and
can be composed into programs.

Key Features:
- 25 parametric operations (15 base + 10 Phase 1 new)
- Type-checked parameter validation
- Comprehensive operation catalog
- Integration with ARCProgram execution

Phase 1 New Operations (Option E):
- 5 Size operations: expand_to_size, compress_to_fit, crop_to_content, resize_with_padding, fit_to_canvas
- 5 Color filtering operations: isolate_color, extract_color, filter_by_color, remove_color, keep_colors

Based on failed task analysis showing 44% of unsolved tasks need size operations
and 33% need color filtering operations.

Version History:
- v0.95: 15 base operations
- v0.96: +10 Phase 1 operations (Option E) - targeting 10% → 15-18% solve rate
"""

import numpy as np
from typing import Dict, List, Callable, Any, Tuple
from scipy import ndimage


# ============================================================================
# PARAMETRIC OPERATIONS
# ============================================================================

def rotate(grid: np.ndarray, angle: int = 90, **kwargs) -> np.ndarray:
    """
    Rotate grid by specified angle (90, 180, 270 degrees).
    
    Args:
        grid: Input grid
        angle: Rotation angle in degrees (must be 90, 180, or 270)
    
    Returns:
        Rotated grid
    """
    k = angle // 90
    return np.rot90(grid, k=k % 4)


def flip(grid: np.ndarray, axis: str = 'horizontal', **kwargs) -> np.ndarray:
    """
    Flip grid along specified axis.
    
    Args:
        grid: Input grid
        axis: 'horizontal' or 'vertical'
    
    Returns:
        Flipped grid
    """
    if axis == 'horizontal' or axis == 'h':
        return np.flip(grid, axis=1)
    elif axis == 'vertical' or axis == 'v':
        return np.flip(grid, axis=0)
    else:
        return grid.copy()


def scale(grid: np.ndarray, factor: int = 2, **kwargs) -> np.ndarray:
    """
    Scale grid by integer factor (repeat each cell).
    
    Args:
        grid: Input grid
        factor: Scale factor (2, 3, 4, 5, etc.)
    
    Returns:
        Scaled grid
    """
    return np.repeat(np.repeat(grid, factor, axis=0), factor, axis=1)


def filter_color(grid: np.ndarray, color: int = 1, **kwargs) -> np.ndarray:
    """
    Keep only specified color, zero out all others.
    
    Args:
        grid: Input grid
        color: Color to keep (0-9)
    
    Returns:
        Filtered grid
    """
    output = np.zeros_like(grid)
    output[grid == color] = color
    return output


def map_color(grid: np.ndarray, from_color: int = 0, to_color: int = 1, **kwargs) -> np.ndarray:
    """
    Map one color to another.
    
    Args:
        grid: Input grid
        from_color: Source color (0-9)
        to_color: Destination color (0-9)
    
    Returns:
        Grid with colors mapped
    """
    output = grid.copy()
    output[grid == from_color] = to_color
    return output


def swap_colors(grid: np.ndarray, color_a: int = 0, color_b: int = 1, **kwargs) -> np.ndarray:
    """
    Swap two colors.
    
    Args:
        grid: Input grid
        color_a: First color (0-9)
        color_b: Second color (0-9)
    
    Returns:
        Grid with colors swapped
    """
    output = grid.copy()
    mask_a = grid == color_a
    mask_b = grid == color_b
    output[mask_a] = color_b
    output[mask_b] = color_a
    return output


def pad(grid: np.ndarray, size: int = 1, value: int = 0, **kwargs) -> np.ndarray:
    """
    Add border padding around grid.
    
    Args:
        grid: Input grid
        size: Padding size in pixels (1, 2, 3, 4)
        value: Fill value for padding (0-9)
    
    Returns:
        Padded grid
    """
    return np.pad(grid, pad_width=size, mode='constant', constant_values=value)


def crop(grid: np.ndarray, mode: str = 'content', **kwargs) -> np.ndarray:
    """
    Crop grid according to mode.
    
    Args:
        grid: Input grid
        mode: 'content' (non-zero bounding box), 'border' (remove border), 'center' (central region)
    
    Returns:
        Cropped grid
    """
    if mode == 'content':
        # Crop to bounding box of non-zero content
        rows, cols = np.where(grid != 0)
        if len(rows) == 0:
            return grid.copy()
        return grid[rows.min():rows.max()+1, cols.min():cols.max()+1].copy()
    
    elif mode == 'border':
        # Remove one-pixel border
        if grid.shape[0] <= 2 or grid.shape[1] <= 2:
            return grid.copy()
        return grid[1:-1, 1:-1].copy()
    
    elif mode == 'center':
        # Extract center half
        h, w = grid.shape
        h_quarter, w_quarter = h // 4, w // 4
        if h_quarter == 0 or w_quarter == 0:
            return grid.copy()
        return grid[h_quarter:-h_quarter, w_quarter:-w_quarter].copy()
    
    else:
        return grid.copy()


def tile(grid: np.ndarray, times_h: int = 2, times_v: int = 2, **kwargs) -> np.ndarray:
    """
    Tile grid horizontally and vertically.
    
    Args:
        grid: Input grid
        times_h: Number of horizontal tiles (1-5)
        times_v: Number of vertical tiles (1-5)
    
    Returns:
        Tiled grid
    """
    return np.tile(grid, (times_v, times_h))


def replicate(grid: np.ndarray, times: int = 2, direction: str = 'horizontal', **kwargs) -> np.ndarray:
    """
    Replicate grid in specified direction.
    
    Args:
        grid: Input grid
        times: Number of replications (2-5)
        direction: 'horizontal' or 'vertical'
    
    Returns:
        Replicated grid
    """
    if direction in ['horizontal', 'h']:
        return np.concatenate([grid] * times, axis=1)
    elif direction in ['vertical', 'v']:
        return np.concatenate([grid] * times, axis=0)
    else:
        return grid.copy()


def detect_objects(grid: np.ndarray, **kwargs) -> List[np.ndarray]:
    """
    Detect connected components (objects) in grid.
    
    Args:
        grid: Input grid
    
    Returns:
        List of object masks
    """
    objects = []
    for color in np.unique(grid):
        if color == 0:
            continue
        mask = (grid == color).astype(int)
        labeled, num_features = ndimage.label(mask)
        for i in range(1, num_features + 1):
            obj_mask = (labeled == i)
            objects.append(obj_mask)
    return objects


def sort_objects(grid: np.ndarray, objects: List[np.ndarray], key: str = 'size', **kwargs) -> List[np.ndarray]:
    """
    Sort objects by specified key.
    
    Args:
        grid: Input grid
        objects: List of object masks
        key: 'size' (area), 'position' (top-left), 'color'
    
    Returns:
        Sorted list of objects
    """
    if key == 'size':
        return sorted(objects, key=lambda obj: np.sum(obj), reverse=True)
    elif key == 'position':
        def get_position(obj):
            rows, cols = np.where(obj)
            if len(rows) == 0:
                return (999, 999)
            return (rows.min(), cols.min())
        return sorted(objects, key=get_position)
    else:
        return objects


def extract_nth(grid: np.ndarray, objects: List[np.ndarray], n: int = 0, **kwargs) -> np.ndarray:
    """
    Extract nth object from list.
    
    Args:
        grid: Input grid
        objects: List of object masks
        n: Object index (0-based)
    
    Returns:
        Grid with only nth object
    """
    output = np.zeros_like(grid)
    if 0 <= n < len(objects):
        output[objects[n]] = grid[objects[n]]
    return output


def symmetrize(grid: np.ndarray, axis: str = 'horizontal', **kwargs) -> np.ndarray:
    """
    Make grid symmetric along axis.
    
    Args:
        grid: Input grid
        axis: 'horizontal', 'vertical', or 'both'
    
    Returns:
        Symmetrized grid
    """
    output = grid.copy()
    
    if axis in ['horizontal', 'h']:
        mid = output.shape[1] // 2
        output[:, mid:] = np.flip(output[:, :mid], axis=1)
    elif axis in ['vertical', 'v']:
        mid = output.shape[0] // 2
        output[mid:, :] = np.flip(output[:mid, :], axis=0)
    elif axis == 'both':
        mid_h = output.shape[0] // 2
        mid_v = output.shape[1] // 2
        output[mid_h:, :] = np.flip(output[:mid_h, :], axis=0)
        output[:, mid_v:] = np.flip(output[:, :mid_v], axis=1)
    
    return output


def border_operation(grid: np.ndarray, operation: str = 'extract', value: int = 0, **kwargs) -> np.ndarray:
    """
    Perform operation on border.

    Args:
        grid: Input grid
        operation: 'extract' (get border only), 'fill' (set border to value), 'remove' (crop border)
        value: Fill value for 'fill' operation

    Returns:
        Modified grid
    """
    if operation == 'extract':
        output = np.zeros_like(grid)
        if grid.shape[0] > 0 and grid.shape[1] > 0:
            output[0, :] = grid[0, :]
            output[-1, :] = grid[-1, :]
            output[:, 0] = grid[:, 0]
            output[:, -1] = grid[:, -1]
        return output

    elif operation == 'fill':
        output = grid.copy()
        if grid.shape[0] > 0 and grid.shape[1] > 0:
            output[0, :] = value
            output[-1, :] = value
            output[:, 0] = value
            output[:, -1] = value
        return output

    elif operation == 'remove':
        if grid.shape[0] <= 2 or grid.shape[1] <= 2:
            return grid.copy()
        return grid[1:-1, 1:-1].copy()

    else:
        return grid.copy()


# ============================================================================
# PHASE 1 NEW OPERATIONS (Option E)
# ============================================================================

# --- Size Operations (Priority: HIGH) ---

def expand_to_size(grid: np.ndarray, target_h: int = 10, target_w: int = 10,
                   fill: str = 'tile', **kwargs) -> np.ndarray:
    """
    Expand grid to target size using specified fill method.

    Args:
        grid: Input grid
        target_h: Target height
        target_w: Target width
        fill: 'tile' (repeat pattern), 'background' (fill with 0), 'border' (repeat border)

    Returns:
        Expanded grid
    """
    h, w = grid.shape

    # If already larger or equal, return copy
    if h >= target_h and w >= target_w:
        return grid.copy()

    if fill == 'tile':
        # Tile pattern to fill target size
        times_h = (target_h + h - 1) // h
        times_w = (target_w + w - 1) // w
        tiled = np.tile(grid, (times_h, times_w))
        return tiled[:target_h, :target_w].copy()

    elif fill == 'background':
        # Fill with background (0)
        output = np.zeros((target_h, target_w), dtype=grid.dtype)
        output[:min(h, target_h), :min(w, target_w)] = grid[:min(h, target_h), :min(w, target_w)]
        return output

    elif fill == 'border':
        # Repeat border pixels
        output = np.zeros((target_h, target_w), dtype=grid.dtype)
        output[:h, :w] = grid

        # Fill right side with rightmost column
        if w < target_w:
            output[:h, w:] = grid[:, -1:].repeat(target_w - w, axis=1)

        # Fill bottom with bottom row
        if h < target_h:
            output[h:, :w] = grid[-1:, :].repeat(target_h - h, axis=0)

        # Fill bottom-right corner
        if h < target_h and w < target_w:
            output[h:, w:] = grid[-1, -1]

        return output

    else:
        return grid.copy()


def compress_to_fit(grid: np.ndarray, target_h: int = 5, target_w: int = 5,
                    method: str = 'downsample', **kwargs) -> np.ndarray:
    """
    Compress grid to fit target size.

    Args:
        grid: Input grid
        target_h: Target height
        target_w: Target width
        method: 'downsample' (subsample), 'select' (select representative cells), 'max' (max pooling)

    Returns:
        Compressed grid
    """
    h, w = grid.shape

    # If already smaller or equal, return copy
    if h <= target_h and w <= target_w:
        return grid.copy()

    if method == 'downsample':
        # Simple downsampling - take every nth pixel
        step_h = max(1, h // target_h)
        step_w = max(1, w // target_w)
        return grid[::step_h, ::step_w][:target_h, :target_w].copy()

    elif method == 'select':
        # Select evenly distributed cells
        indices_h = np.linspace(0, h-1, target_h, dtype=int)
        indices_w = np.linspace(0, w-1, target_w, dtype=int)
        return grid[np.ix_(indices_h, indices_w)].copy()

    elif method == 'max':
        # Max pooling - take most frequent non-zero value in each region
        output = np.zeros((target_h, target_w), dtype=grid.dtype)

        for i in range(target_h):
            for j in range(target_w):
                # Define region
                row_start = i * h // target_h
                row_end = (i + 1) * h // target_h
                col_start = j * w // target_w
                col_end = (j + 1) * w // target_w

                region = grid[row_start:row_end, col_start:col_end]

                # Get most common non-zero value
                values, counts = np.unique(region, return_counts=True)
                non_zero_mask = values != 0

                if np.any(non_zero_mask):
                    non_zero_values = values[non_zero_mask]
                    non_zero_counts = counts[non_zero_mask]
                    output[i, j] = non_zero_values[np.argmax(non_zero_counts)]
                else:
                    output[i, j] = 0

        return output

    else:
        return grid.copy()


def crop_to_content(grid: np.ndarray, margin: int = 0, preserve_aspect: bool = False, **kwargs) -> np.ndarray:
    """
    Crop grid to minimal bounding box of non-background content.

    Args:
        grid: Input grid
        margin: Additional margin around content (0-3 pixels)
        preserve_aspect: If True, pad to square

    Returns:
        Cropped grid
    """
    # Find bounding box of non-zero pixels
    rows, cols = np.where(grid != 0)

    if len(rows) == 0:
        # Empty grid
        return grid.copy()

    # Get bounds with margin
    min_row = max(0, rows.min() - margin)
    max_row = min(grid.shape[0], rows.max() + 1 + margin)
    min_col = max(0, cols.min() - margin)
    max_col = min(grid.shape[1], cols.max() + 1 + margin)

    cropped = grid[min_row:max_row, min_col:max_col].copy()

    if preserve_aspect:
        # Pad to square
        h, w = cropped.shape
        if h > w:
            # Pad width
            pad_left = (h - w) // 2
            pad_right = h - w - pad_left
            cropped = np.pad(cropped, ((0, 0), (pad_left, pad_right)), constant_values=0)
        elif w > h:
            # Pad height
            pad_top = (w - h) // 2
            pad_bottom = w - h - pad_top
            cropped = np.pad(cropped, ((pad_top, pad_bottom), (0, 0)), constant_values=0)

    return cropped


def resize_with_padding(grid: np.ndarray, target_h: int = 10, target_w: int = 10,
                        padding_color: int = 0, **kwargs) -> np.ndarray:
    """
    Resize grid and add padding to reach target size.

    Args:
        grid: Input grid
        target_h: Target height
        target_w: Target width
        padding_color: Color for padding (0-9)

    Returns:
        Resized and padded grid
    """
    h, w = grid.shape

    # If already target size, return copy
    if h == target_h and w == target_w:
        return grid.copy()

    output = np.full((target_h, target_w), padding_color, dtype=grid.dtype)

    # Center the original grid
    start_h = (target_h - h) // 2
    start_w = (target_w - w) // 2

    # Handle cases where grid is larger than target
    copy_h = min(h, target_h)
    copy_w = min(w, target_w)

    if start_h < 0:
        # Grid is taller than target - crop it
        crop_start_h = -start_h
        start_h = 0
        output[:copy_h, start_w:start_w+copy_w] = grid[crop_start_h:crop_start_h+copy_h, :copy_w]
    elif start_w < 0:
        # Grid is wider than target - crop it
        crop_start_w = -start_w
        start_w = 0
        output[start_h:start_h+copy_h, :copy_w] = grid[:copy_h, crop_start_w:crop_start_w+copy_w]
    else:
        # Normal case - grid fits with padding
        output[start_h:start_h+copy_h, start_w:start_w+copy_w] = grid[:copy_h, :copy_w]

    return output


def fit_to_canvas(grid: np.ndarray, canvas_h: int = 10, canvas_w: int = 10,
                  align: str = 'center', **kwargs) -> np.ndarray:
    """
    Fit content onto canvas of specified size.

    Args:
        grid: Input grid
        canvas_h: Canvas height
        canvas_w: Canvas width
        align: 'center', 'topleft', 'topright', 'bottomleft', 'bottomright'

    Returns:
        Grid fitted to canvas
    """
    h, w = grid.shape

    output = np.zeros((canvas_h, canvas_w), dtype=grid.dtype)

    # Calculate placement based on alignment
    if align == 'center':
        start_h = max(0, (canvas_h - h) // 2)
        start_w = max(0, (canvas_w - w) // 2)
    elif align == 'topleft':
        start_h, start_w = 0, 0
    elif align == 'topright':
        start_h = 0
        start_w = max(0, canvas_w - w)
    elif align == 'bottomleft':
        start_h = max(0, canvas_h - h)
        start_w = 0
    elif align == 'bottomright':
        start_h = max(0, canvas_h - h)
        start_w = max(0, canvas_w - w)
    else:
        start_h, start_w = 0, 0

    # Copy grid to canvas
    copy_h = min(h, canvas_h - start_h)
    copy_w = min(w, canvas_w - start_w)

    output[start_h:start_h+copy_h, start_w:start_w+copy_w] = grid[:copy_h, :copy_w]

    return output


# --- Color Filtering Operations (Priority: HIGH) ---

def isolate_color(grid: np.ndarray, color: int = 1, background: int = 0, **kwargs) -> np.ndarray:
    """
    Keep only specified color, set everything else to background.

    Args:
        grid: Input grid
        color: Color to isolate (0-9)
        background: Background color (0-9)

    Returns:
        Grid with only specified color
    """
    output = np.full_like(grid, background)
    output[grid == color] = color
    return output


def extract_color(grid: np.ndarray, color: int = 1, **kwargs) -> np.ndarray:
    """
    Extract objects of specified color (same as isolate but clearer name).

    Args:
        grid: Input grid
        color: Color to extract (0-9)

    Returns:
        Grid with only specified color objects
    """
    output = np.zeros_like(grid)
    output[grid == color] = color
    return output


def filter_by_color(grid: np.ndarray, colors: tuple = (1, 2), **kwargs) -> np.ndarray:
    """
    Keep only objects with specified colors.

    Args:
        grid: Input grid
        colors: Tuple of colors to keep (e.g., (1, 2, 3))

    Returns:
        Grid with only specified colors
    """
    output = np.zeros_like(grid)

    if isinstance(colors, int):
        colors = (colors,)

    for color in colors:
        output[grid == color] = color

    return output


def remove_color(grid: np.ndarray, color: int = 1, background: int = 0, **kwargs) -> np.ndarray:
    """
    Remove all pixels of specified color.

    Args:
        grid: Input grid
        color: Color to remove (0-9)
        background: Replacement color (0-9)

    Returns:
        Grid with color removed
    """
    output = grid.copy()
    output[grid == color] = background
    return output


def keep_colors(grid: np.ndarray, colors: tuple = (1,), background: int = 0, **kwargs) -> np.ndarray:
    """
    Keep multiple specified colors, set rest to background.

    Args:
        grid: Input grid
        colors: Tuple of colors to keep (e.g., (1, 2, 3))
        background: Background color for removed colors (0-9)

    Returns:
        Grid with only specified colors kept
    """
    output = np.full_like(grid, background)

    if isinstance(colors, int):
        colors = (colors,)

    for color in colors:
        output[grid == color] = color

    return output


# ============================================================================
# OPERATION CATALOG
# ============================================================================

PARAMETRIC_OPERATIONS = {
    # --- Original Operations ---
    'rotate': {
        'function': rotate,
        'params': {
            'angle': {'type': int, 'values': [90, 180, 270], 'default': 90}
        },
        'description': 'Rotate grid by angle (90, 180, 270 degrees)'
    },
    'flip': {
        'function': flip,
        'params': {
            'axis': {'type': str, 'values': ['horizontal', 'vertical', 'h', 'v'], 'default': 'horizontal'}
        },
        'description': 'Flip grid along axis'
    },
    'scale': {
        'function': scale,
        'params': {
            'factor': {'type': int, 'values': [2, 3, 4, 5], 'default': 2}
        },
        'description': 'Scale grid by integer factor'
    },
    'filter_color': {
        'function': filter_color,
        'params': {
            'color': {'type': int, 'values': list(range(10)), 'default': 1}
        },
        'description': 'Keep only specified color'
    },
    'map_color': {
        'function': map_color,
        'params': {
            'from_color': {'type': int, 'values': list(range(10)), 'default': 0},
            'to_color': {'type': int, 'values': list(range(10)), 'default': 1}
        },
        'description': 'Map one color to another'
    },
    'swap_colors': {
        'function': swap_colors,
        'params': {
            'color_a': {'type': int, 'values': list(range(10)), 'default': 0},
            'color_b': {'type': int, 'values': list(range(10)), 'default': 1}
        },
        'description': 'Swap two colors'
    },
    'pad': {
        'function': pad,
        'params': {
            'size': {'type': int, 'values': [1, 2, 3, 4], 'default': 1},
            'value': {'type': int, 'values': list(range(10)), 'default': 0}
        },
        'description': 'Add border padding'
    },
    'crop': {
        'function': crop,
        'params': {
            'mode': {'type': str, 'values': ['content', 'border', 'center'], 'default': 'content'}
        },
        'description': 'Crop grid according to mode'
    },
    'tile': {
        'function': tile,
        'params': {
            'times_h': {'type': int, 'values': [1, 2, 3, 4, 5], 'default': 2},
            'times_v': {'type': int, 'values': [1, 2, 3, 4, 5], 'default': 2}
        },
        'description': 'Tile grid horizontally and vertically'
    },
    'replicate': {
        'function': replicate,
        'params': {
            'times': {'type': int, 'values': [2, 3, 4, 5], 'default': 2},
            'direction': {'type': str, 'values': ['horizontal', 'vertical', 'h', 'v'], 'default': 'horizontal'}
        },
        'description': 'Replicate grid in direction'
    },
    'symmetrize': {
        'function': symmetrize,
        'params': {
            'axis': {'type': str, 'values': ['horizontal', 'vertical', 'both', 'h', 'v'], 'default': 'horizontal'}
        },
        'description': 'Make grid symmetric'
    },
    'border': {
        'function': border_operation,
        'params': {
            'operation': {'type': str, 'values': ['extract', 'fill', 'remove'], 'default': 'extract'},
            'value': {'type': int, 'values': list(range(10)), 'default': 0}
        },
        'description': 'Border operations'
    },
    
    # Non-parametric operations (included for completeness)
    'transpose': {
        'function': lambda grid, **kwargs: grid.T,
        'params': {},
        'description': 'Transpose grid (swap rows and columns)'
    },
    'identity': {
        'function': lambda grid, **kwargs: grid.copy(),
        'params': {},
        'description': 'Return copy of grid'
    },
    'gravity_down': {
        'function': lambda grid, **kwargs: _apply_gravity(grid, direction='down'),
        'params': {},
        'description': 'Apply gravity downward (non-zero cells fall)'
    },

    # --- Phase 1 New Operations (Option E) ---

    # Size operations
    'expand_to_size': {
        'function': expand_to_size,
        'params': {
            'target_h': {'type': int, 'values': [5, 10, 15, 20, 30], 'default': 10},
            'target_w': {'type': int, 'values': [5, 10, 15, 20, 30], 'default': 10},
            'fill': {'type': str, 'values': ['tile', 'background', 'border'], 'default': 'tile'}
        },
        'description': 'Expand grid to target size with specified fill'
    },
    'compress_to_fit': {
        'function': compress_to_fit,
        'params': {
            'target_h': {'type': int, 'values': [3, 5, 7, 10], 'default': 5},
            'target_w': {'type': int, 'values': [3, 5, 7, 10], 'default': 5},
            'method': {'type': str, 'values': ['downsample', 'select', 'max'], 'default': 'downsample'}
        },
        'description': 'Compress grid to fit target size'
    },
    'crop_to_content': {
        'function': crop_to_content,
        'params': {
            'margin': {'type': int, 'values': [0, 1, 2, 3], 'default': 0},
            'preserve_aspect': {'type': bool, 'values': [True, False], 'default': False}
        },
        'description': 'Crop to minimal bounding box of content'
    },
    'resize_with_padding': {
        'function': resize_with_padding,
        'params': {
            'target_h': {'type': int, 'values': [5, 10, 15, 20, 30], 'default': 10},
            'target_w': {'type': int, 'values': [5, 10, 15, 20, 30], 'default': 10},
            'padding_color': {'type': int, 'values': list(range(10)), 'default': 0}
        },
        'description': 'Resize with padding to reach target size'
    },
    'fit_to_canvas': {
        'function': fit_to_canvas,
        'params': {
            'canvas_h': {'type': int, 'values': [5, 10, 15, 20, 30], 'default': 10},
            'canvas_w': {'type': int, 'values': [5, 10, 15, 20, 30], 'default': 10},
            'align': {'type': str, 'values': ['center', 'topleft', 'topright', 'bottomleft', 'bottomright'], 'default': 'center'}
        },
        'description': 'Fit content onto canvas with alignment'
    },

    # Color filtering operations
    'isolate_color': {
        'function': isolate_color,
        'params': {
            'color': {'type': int, 'values': list(range(10)), 'default': 1},
            'background': {'type': int, 'values': list(range(10)), 'default': 0}
        },
        'description': 'Keep only specified color, set rest to background'
    },
    'extract_color': {
        'function': extract_color,
        'params': {
            'color': {'type': int, 'values': list(range(10)), 'default': 1}
        },
        'description': 'Extract objects of specified color'
    },
    'filter_by_color': {
        'function': filter_by_color,
        'params': {
            'colors': {'type': tuple, 'values': [(1,), (2,), (1, 2), (1, 2, 3)], 'default': (1, 2)}
        },
        'description': 'Keep only objects with specified colors'
    },
    'remove_color': {
        'function': remove_color,
        'params': {
            'color': {'type': int, 'values': list(range(10)), 'default': 1},
            'background': {'type': int, 'values': list(range(10)), 'default': 0}
        },
        'description': 'Remove all pixels of specified color'
    },
    'keep_colors': {
        'function': keep_colors,
        'params': {
            'colors': {'type': tuple, 'values': [(1,), (2,), (1, 2), (1, 2, 3)], 'default': (1,)},
            'background': {'type': int, 'values': list(range(10)), 'default': 0}
        },
        'description': 'Keep multiple specified colors'
    }
}


# Helper function for gravity
def _apply_gravity(grid: np.ndarray, direction: str = 'down') -> np.ndarray:
    """Apply gravity to non-zero cells"""
    output = grid.copy()
    for j in range(output.shape[1]):
        col = output[:, j]
        nonzero = col[col != 0]
        if direction == 'down':
            output[:, j] = np.concatenate([
                np.zeros(output.shape[0] - len(nonzero), dtype=np.int32),
                nonzero
            ])
        else:  # up
            output[:, j] = np.concatenate([
                nonzero,
                np.zeros(output.shape[0] - len(nonzero), dtype=np.int32)
            ])
    return output


# ============================================================================
# OPERATION MAP BUILDER
# ============================================================================

def build_operation_map() -> Dict[str, Callable]:
    """Build dictionary mapping operation names to functions"""
    return {
        name: spec['function']
        for name, spec in PARAMETRIC_OPERATIONS.items()
    }


def get_parameter_candidates(op_name: str, task: Dict = None, constraints: Dict = None) -> List[Dict]:
    """
    Get parameter candidates for operation.
    
    Args:
        op_name: Operation name
        task: Task data (optional, for extracting task-specific values)
        constraints: Task constraints (optional, for filtering)
    
    Returns:
        List of parameter dictionaries
    """
    if op_name not in PARAMETRIC_OPERATIONS:
        return [{}]
    
    spec = PARAMETRIC_OPERATIONS[op_name]
    
    if not spec['params']:
        return [{}]
    
    # Generate all combinations (limited to top-k to avoid explosion)
    candidates = []
    
    # For now, generate default + a few variations
    # In full implementation, this would use constraints and task data
    
    # Always include default
    default_params = {
        name: param_spec['default']
        for name, param_spec in spec['params'].items()
    }
    candidates.append(default_params)
    
    # Add a few variations for each parameter
    for param_name, param_spec in spec['params'].items():
        for value in param_spec['values'][:3]:  # Limit to first 3 values
            if value != param_spec['default']:
                variant = default_params.copy()
                variant[param_name] = value
                candidates.append(variant)
    
    # Limit total candidates
    return candidates[:5]


# ============================================================================
# TESTING
# ============================================================================

def test_parametric_operations():
    """Test parametric operations"""
    print("Testing Parametric Operations...")
    
    # Create test grid
    test_grid = np.array([
        [1, 2, 0],
        [3, 1, 2],
        [0, 3, 1]
    ])
    
    # Test each operation
    operation_map = build_operation_map()
    
    print(f"\nTest grid:\n{test_grid}\n")
    
    # Test rotate
    result = operation_map['rotate'](test_grid, angle=90)
    print(f"rotate(angle=90):\n{result}\n")
    
    # Test flip
    result = operation_map['flip'](test_grid, axis='horizontal')
    print(f"flip(axis='horizontal'):\n{result}\n")
    
    # Test scale
    result = operation_map['scale'](test_grid, factor=2)
    print(f"scale(factor=2):\n{result}\n")
    
    # Test filter_color
    result = operation_map['filter_color'](test_grid, color=1)
    print(f"filter_color(color=1):\n{result}\n")
    
    # Test pad
    result = operation_map['pad'](test_grid, size=1, value=0)
    print(f"pad(size=1, value=0):\n{result}\n")
    
    # Test parameter candidates
    print("\nParameter candidates for 'rotate':")
    candidates = get_parameter_candidates('rotate')
    for i, params in enumerate(candidates):
        print(f"  {i+1}. {params}")
    
    print("\nAll tests passed!")


if __name__ == "__main__":
    test_parametric_operations()
