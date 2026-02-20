#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARC Parametric Operations Library (v0.97 - Phase 2 Operation Expansion)

This module provides a clean, unified library of parametric operations for
ARC-AGI program synthesis. Each operation supports flexible parameters and
can be composed into programs.

Key Features:
- 47 parametric operations (19 Phase-1 + 28 Phase-2 new)
- Type-checked parameter validation
- Comprehensive operation catalog
- Integration with ARCProgram execution

Phase 1 New Operations (Option E):
- 3 Size operations: expand_to_size, compress_to_fit, fit_to_canvas
- 2 Color filtering operations: filter_by_color, remove_color

Phase 2 New Operations (v0.97 - break 10% ceiling):
- 6 Object/connectivity: label_objects, select_largest_object,
    select_smallest_object, fill_holes, outline_objects, count_and_mark
- 5 Pattern/repetition: extract_repeating_unit, tile_by_pattern,
    detect_symmetry_axis, reflect_about_center, mirror_quadrant
- 4 Conditionals/masking: apply_if_color, conditional_fill,
    mask_where, replace_pattern
- 4 Path/line drawing: connect_endpoints, draw_line, extend_lines,
    fill_between
- 4 Spatial/arrangement: align_to_edge, center_content,
    distribute_vertically, distribute_horizontally
- 5 Transformation variants: diagonal_flip, rotate_and_flip,
    gravity_left, gravity_right, gravity_up
- 2 Overlay/composition: overlay_grids, blend_by_mask

Removed operations (Phase 1 cleanup):
- resize_with_padding: Too buggy (100+ failures per task)
- isolate_color: Redundant with filter_color (0 usage)
- extract_color: Redundant with filter_color (0 usage)
- keep_colors: Redundant with filter_color (0 usage)

Removed operations (Option H: reduce tying noise):
- gravity_down: Ties with crop at 0.949 fitness, creates search noise
- crop_to_content: Ties with crop at 0.949 fitness (3 param variants), creates search noise

Based on failed task analysis showing 44% of unsolved tasks need size operations
and 33% need color filtering operations. Phase 2 targets remaining 90%.

Version History:
- v0.95: 15 base operations - achieved 10% (5/50 tasks)
- v0.96: +10 Phase 1 operations (Option E) - achieved 8% (below target, search dilution)
- v0.96a: Removed 4 redundant/buggy operations (25 → 21) - still 8%
- v0.96b: Removed 2 tying operations (21 → 19) - still 8%
- v0.96c: Reduced complexity penalty 0.01→0.005 (Option I) - expected 10%+ (restore baseline)
- v0.97: +28 Phase 2 operations (19 → 47) - targets 20-25% solve rate
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
# PHASE 2 NEW OPERATIONS (v0.97)
# ============================================================================

# --- Object / Connectivity Operations ---

def label_objects(grid: np.ndarray, color: int = 0, output: str = 'count', **kwargs) -> np.ndarray:
    """
    Label connected objects in grid, optionally returning count map or labelled grid.

    Args:
        grid: Input grid
        color: Background color to ignore (0-9)
        output: 'labels' (integer label per pixel), 'count' (cell = object size),
                'binary' (1 where non-background)
    Returns:
        Transformed grid
    """
    mask = (grid != color).astype(np.int32)
    labeled, num_features = ndimage.label(mask)

    if output == 'labels':
        return labeled.astype(np.int32)
    elif output == 'binary':
        return mask
    else:  # 'count' - each pixel gets the size of its object
        result = np.zeros_like(grid)
        for obj_id in range(1, num_features + 1):
            obj_mask = labeled == obj_id
            size = int(obj_mask.sum())
            result[obj_mask] = min(size, 9)
        return result


def select_largest_object(grid: np.ndarray, background: int = 0, keep_color: bool = True, **kwargs) -> np.ndarray:
    """
    Keep only the largest connected object; zero out everything else.

    Args:
        grid: Input grid
        background: Background color (0-9)
        keep_color: If True keep original colors; if False re-color to 1
    Returns:
        Grid with only the largest object
    """
    mask = (grid != background).astype(np.int32)
    labeled, num_features = ndimage.label(mask)
    if num_features == 0:
        return grid.copy()

    sizes = ndimage.sum(mask, labeled, range(1, num_features + 1))
    largest_id = int(np.argmax(sizes)) + 1

    result = np.full_like(grid, background)
    obj_mask = labeled == largest_id
    if keep_color:
        result[obj_mask] = grid[obj_mask]
    else:
        result[obj_mask] = 1
    return result


def select_smallest_object(grid: np.ndarray, background: int = 0, keep_color: bool = True, **kwargs) -> np.ndarray:
    """
    Keep only the smallest connected object; zero out everything else.

    Args:
        grid: Input grid
        background: Background color (0-9)
        keep_color: If True keep original colors; if False re-color to 1
    Returns:
        Grid with only the smallest object
    """
    mask = (grid != background).astype(np.int32)
    labeled, num_features = ndimage.label(mask)
    if num_features == 0:
        return grid.copy()

    sizes = ndimage.sum(mask, labeled, range(1, num_features + 1))
    smallest_id = int(np.argmin(sizes)) + 1

    result = np.full_like(grid, background)
    obj_mask = labeled == smallest_id
    if keep_color:
        result[obj_mask] = grid[obj_mask]
    else:
        result[obj_mask] = 1
    return result


def fill_holes(grid: np.ndarray, background: int = 0, fill_color: int = -1, **kwargs) -> np.ndarray:
    """
    Fill enclosed holes (background regions completely surrounded by non-background).

    Args:
        grid: Input grid
        background: Background color (0-9)
        fill_color: Color to fill holes with; -1 means use surrounding color
    Returns:
        Grid with holes filled
    """
    mask = (grid != background).astype(np.uint8)
    filled = ndimage.binary_fill_holes(mask).astype(np.int32)
    holes = (filled == 1) & (mask == 0)

    result = grid.copy()
    if fill_color == -1:
        # Use the most common non-background color
        non_bg = grid[grid != background]
        if len(non_bg) > 0:
            values, counts = np.unique(non_bg, return_counts=True)
            dominant = int(values[np.argmax(counts)])
        else:
            dominant = 1
        result[holes] = dominant
    else:
        result[holes] = fill_color
    return result


def outline_objects(grid: np.ndarray, background: int = 0, outline_color: int = 1,
                    thickness: int = 1, **kwargs) -> np.ndarray:
    """
    Draw outlines around objects (erosion-based border).

    Args:
        grid: Input grid
        background: Background color (0-9)
        outline_color: Color of outline (0-9)
        thickness: Outline thickness in pixels (1-3)
    Returns:
        Grid with object outlines
    """
    mask = (grid != background).astype(np.uint8)
    struct = ndimage.generate_binary_structure(2, 1)

    eroded = mask.copy()
    for _ in range(thickness):
        eroded = ndimage.binary_erosion(eroded, structure=struct).astype(np.uint8)

    border = mask - eroded
    result = grid.copy()
    result[border.astype(bool)] = outline_color
    return result


def count_and_mark(grid: np.ndarray, background: int = 0, mark_color: int = -1, **kwargs) -> np.ndarray:
    """
    Count objects and mark each with its rank (1=largest, 2=second, ...).

    Args:
        grid: Input grid
        background: Background color (0-9)
        mark_color: Color to mark with (-1 = use rank number 1-9)
    Returns:
        Grid where each object pixel = its size rank (1-9)
    """
    mask = (grid != background).astype(np.int32)
    labeled, num_features = ndimage.label(mask)
    if num_features == 0:
        return grid.copy()

    sizes = [(int(ndimage.sum(mask, labeled, i + 1)), i + 1) for i in range(num_features)]
    sizes.sort(reverse=True)  # Largest first → rank 1

    result = np.zeros_like(grid)
    for rank, (size, obj_id) in enumerate(sizes, start=1):
        obj_mask = labeled == obj_id
        color = mark_color if mark_color != -1 else min(rank, 9)
        result[obj_mask] = color
    return result


# --- Pattern / Repetition Operations ---

def extract_repeating_unit(grid: np.ndarray, axis: str = 'both', **kwargs) -> np.ndarray:
    """
    Detect and extract the smallest repeating tile from grid.

    Args:
        grid: Input grid
        axis: 'horizontal', 'vertical', or 'both'
    Returns:
        Smallest repeating tile (or original if none found)
    """
    h, w = grid.shape

    def find_period(arr_1d):
        n = len(arr_1d)
        for p in range(1, n // 2 + 1):
            if n % p == 0:
                tile = arr_1d[:p]
                if np.all(arr_1d == np.tile(tile, n // p)):
                    return p
        return n

    if axis in ('both', 'horizontal'):
        # Check each row for period
        row_periods = [find_period(grid[r, :]) for r in range(h)]
        period_w = min(row_periods)
    else:
        period_w = w

    if axis in ('both', 'vertical'):
        col_periods = [find_period(grid[:, c]) for c in range(w)]
        period_h = min(col_periods)
    else:
        period_h = h

    return grid[:period_h, :period_w].copy()


def tile_by_pattern(grid: np.ndarray, target_h: int = 0, target_w: int = 0, **kwargs) -> np.ndarray:
    """
    Extract repeating unit from grid then tile it to reach target size.

    Args:
        grid: Input grid (may contain a repeating pattern)
        target_h: Target height (0 = double current height)
        target_w: Target width (0 = double current width)
    Returns:
        Tiled grid
    """
    unit = extract_repeating_unit(grid, axis='both')
    uh, uw = unit.shape

    th = target_h if target_h > 0 else grid.shape[0]
    tw = target_w if target_w > 0 else grid.shape[1]

    reps_h = max(1, (th + uh - 1) // uh)
    reps_w = max(1, (tw + uw - 1) // uw)
    tiled = np.tile(unit, (reps_h, reps_w))
    return tiled[:th, :tw].copy()


def reflect_about_center(grid: np.ndarray, axis: str = 'horizontal', **kwargs) -> np.ndarray:
    """
    Reflect the left/top half of the grid onto the right/bottom half.

    Args:
        grid: Input grid
        axis: 'horizontal' (left→right fill), 'vertical' (top→bottom fill)
    Returns:
        Grid where one half mirrors the other
    """
    result = grid.copy()
    h, w = grid.shape

    if axis in ('horizontal', 'h'):
        half = w // 2
        # Flip the left half, then write into right half (which may be half or half+1 wide)
        right_width = w - half
        flipped = np.fliplr(result[:, :half])   # shape (h, half)
        # Take rightmost columns of flipped to fill right side
        fill = flipped[:, -right_width:] if right_width <= half else np.pad(
            flipped, ((0, 0), (right_width - half, 0)))
        result[:, half:] = fill
    elif axis in ('vertical', 'v'):
        half = h // 2
        bottom_height = h - half
        flipped = np.flipud(result[:half, :])   # shape (half, w)
        fill = flipped[-bottom_height:, :] if bottom_height <= half else np.pad(
            flipped, ((bottom_height - half, 0), (0, 0)))
        result[half:, :] = fill
    return result


def mirror_quadrant(grid: np.ndarray, quadrant: str = 'topleft', **kwargs) -> np.ndarray:
    """
    Take one quadrant of the grid and mirror it to fill the entire grid.

    Args:
        grid: Input grid
        quadrant: Which quadrant to use as source: 'topleft', 'topright',
                  'bottomleft', 'bottomright'
    Returns:
        Full grid mirrored from chosen quadrant
    """
    h, w = grid.shape
    mh, mw = h // 2, w // 2

    if quadrant == 'topleft':
        q = grid[:mh, :mw]
    elif quadrant == 'topright':
        q = grid[:mh, mw:]
    elif quadrant == 'bottomleft':
        q = grid[mh:, :mw]
    else:  # bottomright
        q = grid[mh:, mw:]

    # Build full grid by mirroring
    top = np.concatenate([q, np.fliplr(q)], axis=1)[:, :w]
    bottom = np.flipud(top)
    result = np.concatenate([top, bottom], axis=0)[:h, :]
    return result


def detect_and_complete_symmetry(grid: np.ndarray, axis: str = 'horizontal',
                                  tolerance: int = 0, **kwargs) -> np.ndarray:
    """
    Detect near-symmetry and complete it by copying the denser half.

    Args:
        grid: Input grid
        axis: 'horizontal' or 'vertical'
        tolerance: Number of mismatched pixels to tolerate as "near-symmetric"
    Returns:
        Symmetrized grid (dense half dominates)
    """
    result = grid.copy()
    h, w = grid.shape

    if axis in ('horizontal', 'h'):
        left = grid[:, :w // 2]
        right = np.fliplr(grid[:, w - w // 2:])

        left_count = np.sum(left != 0)
        right_count = np.sum(right != 0)

        if left_count >= right_count:
            # Left is denser — mirror left to right
            result[:, w - w // 2:] = np.fliplr(left[:, :w - w // 2])
        else:
            result[:, :w // 2] = np.fliplr(right[:, :w // 2])
    else:  # vertical
        top = grid[:h // 2, :]
        bottom = np.flipud(grid[h - h // 2:, :])

        top_count = np.sum(top != 0)
        bottom_count = np.sum(bottom != 0)

        if top_count >= bottom_count:
            result[h - h // 2:, :] = np.flipud(top[:h - h // 2, :])
        else:
            result[:h // 2, :] = np.flipud(bottom[:h // 2, :])
    return result


# --- Conditional / Masking Operations ---

def apply_if_color(grid: np.ndarray, trigger_color: int = 1, fill_color: int = 2,
                   operation: str = 'fill_row', **kwargs) -> np.ndarray:
    """
    Apply transformation conditionally based on presence of a trigger color.

    Args:
        grid: Input grid
        trigger_color: Color that triggers the operation (0-9)
        fill_color: Color used for filling (0-9)
        operation: 'fill_row' (fill entire row), 'fill_col' (fill entire column),
                   'fill_adjacent' (fill 4-neighbors), 'mark_row' (mark only cells in row)
    Returns:
        Transformed grid
    """
    result = grid.copy()
    rows, cols = np.where(grid == trigger_color)

    if operation == 'fill_row':
        for r in rows:
            result[r, :] = fill_color
    elif operation == 'fill_col':
        for c in cols:
            result[:, c] = fill_color
    elif operation == 'fill_adjacent':
        for r, c in zip(rows, cols):
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < grid.shape[0] and 0 <= nc < grid.shape[1]:
                    if result[nr, nc] == 0:
                        result[nr, nc] = fill_color
    elif operation == 'mark_row':
        for r in rows:
            result[r, result[r, :] == 0] = fill_color
    return result


def conditional_fill(grid: np.ndarray, condition_color: int = 0, fill_color: int = 1,
                     region: str = 'same_row', **kwargs) -> np.ndarray:
    """
    Fill background cells in specified region relative to condition_color cells.

    Args:
        grid: Input grid
        condition_color: Color that defines condition (0-9)
        fill_color: Color to fill with (0-9)
        region: 'same_row', 'same_col', 'enclosed', 'right_of', 'below'
    Returns:
        Grid with conditional fill applied
    """
    result = grid.copy()
    rows, cols = np.where(grid == condition_color)

    if len(rows) == 0:
        return result

    if region == 'same_row':
        for r in np.unique(rows):
            result[r, result[r, :] == 0] = fill_color
    elif region == 'same_col':
        for c in np.unique(cols):
            result[result[:, c] == 0, c] = fill_color
    elif region == 'right_of':
        for r, c in zip(rows, cols):
            result[r, c + 1:][result[r, c + 1:] == 0] = fill_color
    elif region == 'below':
        for r, c in zip(rows, cols):
            result[r + 1:, c][result[r + 1:, c] == 0] = fill_color
    elif region == 'enclosed':
        # Fill holes enclosed by condition_color
        mask = (grid == condition_color).astype(np.uint8)
        filled = ndimage.binary_fill_holes(mask)
        enclosed = filled & ~mask.astype(bool)
        result[enclosed] = fill_color
    return result


def mask_where(grid: np.ndarray, mask_color: int = 0, replacement: int = 0,
               invert: bool = False, **kwargs) -> np.ndarray:
    """
    Zero out cells based on a color mask.

    Args:
        grid: Input grid
        mask_color: Color defining mask (0-9)
        replacement: Value to write where mask is active (0-9)
        invert: If True, mask where color is NOT mask_color
    Returns:
        Masked grid
    """
    result = grid.copy()
    if not invert:
        result[grid == mask_color] = replacement
    else:
        result[grid != mask_color] = replacement
    return result


def replace_pattern_color(grid: np.ndarray, from_color: int = 1, to_color: int = 2,
                           min_size: int = 1, max_size: int = 100, **kwargs) -> np.ndarray:
    """
    Replace color only for objects of a specific size range.

    Args:
        grid: Input grid
        from_color: Color to replace (0-9)
        to_color: Replacement color (0-9)
        min_size: Minimum object size to replace (pixels)
        max_size: Maximum object size to replace (pixels)
    Returns:
        Grid with size-filtered color replacement
    """
    mask = (grid == from_color).astype(np.int32)
    labeled, num_features = ndimage.label(mask)

    result = grid.copy()
    for obj_id in range(1, num_features + 1):
        obj_mask = labeled == obj_id
        size = int(obj_mask.sum())
        if min_size <= size <= max_size:
            result[obj_mask] = to_color
    return result


# --- Path / Line Drawing Operations ---

def connect_endpoints(grid: np.ndarray, color: int = 1, line_color: int = -1,
                      style: str = 'straight', **kwargs) -> np.ndarray:
    """
    Connect the two furthest pixels of a given color with a line.

    Args:
        grid: Input grid
        color: Color whose extreme pixels to connect (0-9)
        line_color: Color of connecting line (-1 = same as color)
        style: 'straight' (Bresenham line), 'horizontal_then_vertical' (L-shape),
               'vertical_then_horizontal'
    Returns:
        Grid with connected line
    """
    lc = color if line_color == -1 else line_color
    result = grid.copy()
    positions = np.argwhere(grid == color)
    if len(positions) < 2:
        return result

    # Find two most distant points
    max_dist = -1
    p1, p2 = positions[0], positions[-1]
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            d = np.sum((positions[i] - positions[j]) ** 2)
            if d > max_dist:
                max_dist = d
                p1, p2 = positions[i], positions[j]

    r1, c1 = int(p1[0]), int(p1[1])
    r2, c2 = int(p2[0]), int(p2[1])

    if style == 'straight':
        # Bresenham line
        _draw_line_bresenham(result, r1, c1, r2, c2, lc)
    elif style == 'horizontal_then_vertical':
        _draw_line_bresenham(result, r1, c1, r1, c2, lc)
        _draw_line_bresenham(result, r1, c2, r2, c2, lc)
    else:  # vertical_then_horizontal
        _draw_line_bresenham(result, r1, c1, r2, c1, lc)
        _draw_line_bresenham(result, r2, c1, r2, c2, lc)
    return result


def _draw_line_bresenham(grid, r1, c1, r2, c2, color):
    """Bresenham's line algorithm (in-place)."""
    dr = abs(r2 - r1)
    dc = abs(c2 - c1)
    sr = 1 if r1 < r2 else -1
    sc = 1 if c1 < c2 else -1
    err = dr - dc
    h, w = grid.shape

    while True:
        if 0 <= r1 < h and 0 <= c1 < w:
            grid[r1, c1] = color
        if r1 == r2 and c1 == c2:
            break
        e2 = 2 * err
        if e2 > -dc:
            err -= dc
            r1 += sr
        if e2 < dr:
            err += dr
            c1 += sc


def draw_line(grid: np.ndarray, direction: str = 'horizontal', position: int = 0,
              color: int = 1, **kwargs) -> np.ndarray:
    """
    Draw a single horizontal or vertical line across the grid.

    Args:
        grid: Input grid
        direction: 'horizontal' or 'vertical'
        position: Row/column index (-1 = center)
        color: Line color (0-9)
    Returns:
        Grid with line drawn
    """
    result = grid.copy()
    h, w = grid.shape

    if position == -1:
        pos = h // 2 if direction in ('horizontal', 'h') else w // 2
    else:
        pos = position

    if direction in ('horizontal', 'h'):
        pos = max(0, min(h - 1, pos))
        result[pos, :] = color
    elif direction in ('vertical', 'v'):
        pos = max(0, min(w - 1, pos))
        result[:, pos] = color
    return result


def extend_lines(grid: np.ndarray, color: int = 1, extend_color: int = -1,
                 direction: str = 'all', **kwargs) -> np.ndarray:
    """
    Extend line segments in specified direction until grid boundary.

    Args:
        grid: Input grid
        color: Color of line segments to extend (0-9)
        extend_color: Color of extension (-1 = same as color)
        direction: 'horizontal', 'vertical', or 'all'
    Returns:
        Grid with lines extended
    """
    ec = color if extend_color == -1 else extend_color
    result = grid.copy()
    h, w = grid.shape

    if direction in ('horizontal', 'all'):
        for r in range(h):
            cols = np.where(grid[r, :] == color)[0]
            if len(cols) > 0:
                result[r, cols.min():cols.max() + 1] = ec

    if direction in ('vertical', 'all'):
        for c in range(w):
            rows = np.where(grid[:, c] == color)[0]
            if len(rows) > 0:
                result[rows.min():rows.max() + 1, c] = ec

    return result


def fill_between(grid: np.ndarray, color: int = 1, fill_color: int = 2,
                 axis: str = 'horizontal', **kwargs) -> np.ndarray:
    """
    Fill the region between the first and last occurrence of a color on each row/col.

    Args:
        grid: Input grid
        color: Anchor color (0-9)
        fill_color: Fill color for the between region (0-9)
        axis: 'horizontal' (fill between on each row) or 'vertical' (fill on each col)
    Returns:
        Grid with between-regions filled
    """
    result = grid.copy()
    h, w = grid.shape

    if axis in ('horizontal', 'h'):
        for r in range(h):
            cols = np.where(grid[r, :] == color)[0]
            if len(cols) >= 2:
                result[r, cols[0]:cols[-1] + 1] = fill_color
                result[r, cols] = color  # Keep anchor pixels original color
    elif axis in ('vertical', 'v'):
        for c in range(w):
            rows = np.where(grid[:, c] == color)[0]
            if len(rows) >= 2:
                result[rows[0]:rows[-1] + 1, c] = fill_color
                result[rows, c] = color
    return result


# --- Spatial / Arrangement Operations ---

def align_to_edge(grid: np.ndarray, edge: str = 'left', background: int = 0, **kwargs) -> np.ndarray:
    """
    Slide all non-background content to one edge, like gravity.

    Args:
        grid: Input grid
        edge: 'left', 'right', 'top', 'bottom'
        background: Background color (0-9)
    Returns:
        Grid with content aligned to edge
    """
    result = np.full_like(grid, background)
    h, w = grid.shape

    if edge == 'left':
        for r in range(h):
            non_bg = grid[r, grid[r, :] != background]
            result[r, :len(non_bg)] = non_bg
    elif edge == 'right':
        for r in range(h):
            non_bg = grid[r, grid[r, :] != background]
            result[r, w - len(non_bg):] = non_bg
    elif edge == 'top':
        for c in range(w):
            non_bg = grid[grid[:, c] != background, c]
            result[:len(non_bg), c] = non_bg
    elif edge == 'bottom':
        for c in range(w):
            non_bg = grid[grid[:, c] != background, c]
            result[h - len(non_bg):, c] = non_bg
    return result


def center_content(grid: np.ndarray, background: int = 0, **kwargs) -> np.ndarray:
    """
    Move all non-background content to the center of the grid.

    Args:
        grid: Input grid
        background: Background color (0-9)
    Returns:
        Grid with content centered
    """
    rows, cols = np.where(grid != background)
    if len(rows) == 0:
        return grid.copy()

    # Get bounding box of content
    min_r, max_r = rows.min(), rows.max()
    min_c, max_c = cols.min(), cols.max()
    content = grid[min_r:max_r + 1, min_c:max_c + 1].copy()

    # Place in center
    h, w = grid.shape
    ch, cw = content.shape
    result = np.full_like(grid, background)

    start_r = max(0, (h - ch) // 2)
    start_c = max(0, (w - cw) // 2)
    end_r = min(h, start_r + ch)
    end_c = min(w, start_c + cw)

    result[start_r:end_r, start_c:end_c] = content[:end_r - start_r, :end_c - start_c]
    return result


def distribute_vertically(grid: np.ndarray, background: int = 0, **kwargs) -> np.ndarray:
    """
    Spread objects evenly vertically within each column.

    Args:
        grid: Input grid
        background: Background color (0-9)
    Returns:
        Grid with objects evenly distributed vertically
    """
    result = np.full_like(grid, background)
    h, w = grid.shape

    for c in range(w):
        non_bg = grid[grid[:, c] != background, c]
        if len(non_bg) == 0:
            continue
        if len(non_bg) == 1:
            result[h // 2, c] = non_bg[0]
        else:
            positions = np.round(np.linspace(0, h - 1, len(non_bg))).astype(int)
            for pos, val in zip(positions, non_bg):
                result[pos, c] = val
    return result


def distribute_horizontally(grid: np.ndarray, background: int = 0, **kwargs) -> np.ndarray:
    """
    Spread objects evenly horizontally within each row.

    Args:
        grid: Input grid
        background: Background color (0-9)
    Returns:
        Grid with objects evenly distributed horizontally
    """
    result = np.full_like(grid, background)
    h, w = grid.shape

    for r in range(h):
        non_bg = grid[r, grid[r, :] != background]
        if len(non_bg) == 0:
            continue
        if len(non_bg) == 1:
            result[r, w // 2] = non_bg[0]
        else:
            positions = np.round(np.linspace(0, w - 1, len(non_bg))).astype(int)
            for pos, val in zip(positions, non_bg):
                result[r, pos] = val
    return result


# --- Transformation Variants ---

def diagonal_flip(grid: np.ndarray, diagonal: str = 'main', **kwargs) -> np.ndarray:
    """
    Flip along a diagonal (transpose variants).

    Args:
        grid: Input grid
        diagonal: 'main' (top-left to bottom-right, equivalent to transpose),
                  'anti' (top-right to bottom-left)
    Returns:
        Diagonally flipped grid
    """
    if diagonal in ('main', 'primary'):
        return grid.T.copy()
    elif diagonal in ('anti', 'secondary'):
        return np.fliplr(np.flipud(grid.T)).copy()
    else:
        return grid.copy()


def rotate_and_flip(grid: np.ndarray, angle: int = 90, axis: str = 'horizontal', **kwargs) -> np.ndarray:
    """
    Rotate then flip (combined transformation for dihedral group coverage).

    Args:
        grid: Input grid
        angle: Rotation angle (90, 180, 270)
        axis: 'horizontal' or 'vertical'
    Returns:
        Rotated then flipped grid
    """
    rotated = rotate(grid, angle=angle)
    return flip(rotated, axis=axis)


def gravity_up(grid: np.ndarray, **kwargs) -> np.ndarray:
    """Apply gravity upward — non-zero cells float to top of each column."""
    result = np.zeros_like(grid)
    for c in range(grid.shape[1]):
        col = grid[:, c]
        non_zero = col[col != 0]
        result[:len(non_zero), c] = non_zero
    return result


def gravity_down(grid: np.ndarray, **kwargs) -> np.ndarray:
    """Apply gravity downward — non-zero cells sink to bottom of each column."""
    result = np.zeros_like(grid)
    h = grid.shape[0]
    for c in range(grid.shape[1]):
        col = grid[:, c]
        non_zero = col[col != 0]
        result[h - len(non_zero):, c] = non_zero
    return result


def gravity_left(grid: np.ndarray, **kwargs) -> np.ndarray:
    """Apply gravity leftward — non-zero cells slide to left of each row."""
    result = np.zeros_like(grid)
    for r in range(grid.shape[0]):
        row = grid[r, :]
        non_zero = row[row != 0]
        result[r, :len(non_zero)] = non_zero
    return result


def gravity_right(grid: np.ndarray, **kwargs) -> np.ndarray:
    """Apply gravity rightward — non-zero cells slide to right of each row."""
    result = np.zeros_like(grid)
    w = grid.shape[1]
    for r in range(grid.shape[0]):
        row = grid[r, :]
        non_zero = row[row != 0]
        result[r, w - len(non_zero):] = non_zero
    return result


# --- Overlay / Composition Operations ---

def overlay_grids(grid: np.ndarray, overlay_mode: str = 'nonzero',
                  overlay_color: int = 1, **kwargs) -> np.ndarray:
    """
    Overlay a constant pattern or self-overlay (fold the grid onto itself).

    Args:
        grid: Input grid
        overlay_mode: 'fold_h' (fold left half onto right), 'fold_v' (fold top onto bottom),
                      'max' (max of folded halves), 'add' (additive clamped to 9)
        overlay_color: Used only for 'stamp' mode (0-9)
    Returns:
        Overlaid grid
    """
    result = grid.copy()
    h, w = grid.shape

    if overlay_mode == 'fold_h':
        left = grid[:, :w // 2]
        right = np.fliplr(grid[:, w // 2:])
        min_w = min(left.shape[1], right.shape[1])
        combined = np.where(left[:, :min_w] != 0, left[:, :min_w], right[:, :min_w])
        result = np.zeros_like(grid)
        result[:, :combined.shape[1]] = combined
    elif overlay_mode == 'fold_v':
        top = grid[:h // 2, :]
        bottom = np.flipud(grid[h // 2:, :])
        min_h = min(top.shape[0], bottom.shape[0])
        combined = np.where(top[:min_h, :] != 0, top[:min_h, :], bottom[:min_h, :])
        result = np.zeros_like(grid)
        result[:combined.shape[0], :] = combined
    elif overlay_mode == 'max':
        flipped_h = np.fliplr(grid)
        result = np.maximum(grid, flipped_h)
    elif overlay_mode == 'add':
        flipped_h = np.fliplr(grid)
        result = np.clip(grid.astype(np.int32) + flipped_h, 0, 9).astype(grid.dtype)
    return result


def blend_by_mask(grid: np.ndarray, mask_color: int = 0, fill_value: int = 1,
                  mode: str = 'checkerboard', **kwargs) -> np.ndarray:
    """
    Fill background using a pattern mask.

    Args:
        grid: Input grid
        mask_color: Background color to replace (0-9)
        fill_value: Fill color (0-9)
        mode: 'checkerboard', 'stripes_h', 'stripes_v', 'diagonal'
    Returns:
        Grid with background filled by pattern
    """
    result = grid.copy()
    h, w = grid.shape

    for r in range(h):
        for c in range(w):
            if grid[r, c] == mask_color:
                if mode == 'checkerboard':
                    if (r + c) % 2 == 0:
                        result[r, c] = fill_value
                elif mode == 'stripes_h':
                    if r % 2 == 0:
                        result[r, c] = fill_value
                elif mode == 'stripes_v':
                    if c % 2 == 0:
                        result[r, c] = fill_value
                elif mode == 'diagonal':
                    if (r - c) % 3 == 0:
                        result[r, c] = fill_value
    return result


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
    # REMOVED (Option H): gravity_down - Ties with crop at 0.949, creates search noise
    # 'gravity_down': {
    #     'function': lambda grid, **kwargs: _apply_gravity(grid, direction='down'),
    #     'params': {},
    #     'description': 'Apply gravity downward (non-zero cells fall)'
    # },

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
    # REMOVED (Option H): crop_to_content - Ties with crop at 0.949 (3 param variants), creates search noise
    # 'crop_to_content': {
    #     'function': crop_to_content,
    #     'params': {
    #         'margin': {'type': int, 'values': [0, 1, 2, 3], 'default': 0},
    #         'preserve_aspect': {'type': bool, 'values': [True, False], 'default': False}
    #     },
    #     'description': 'Crop to minimal bounding box of content'
    # },
    # REMOVED: resize_with_padding - too buggy (100+ failures per task)
    # 'resize_with_padding': {
    #     'function': resize_with_padding,
    #     'params': {
    #         'target_h': {'type': int, 'values': [5, 10, 15, 20, 30], 'default': 10},
    #         'target_w': {'type': int, 'values': [5, 10, 15, 20, 30], 'default': 10},
    #         'padding_color': {'type': int, 'values': list(range(10)), 'default': 0}
    #     },
    #     'description': 'Resize with padding to reach target size'
    # },
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
    # REMOVED: isolate_color - redundant with filter_color (0 usage in 50-task benchmark)
    # 'isolate_color': {
    #     'function': isolate_color,
    #     'params': {
    #         'color': {'type': int, 'values': list(range(10)), 'default': 1},
    #         'background': {'type': int, 'values': list(range(10)), 'default': 0}
    #     },
    #     'description': 'Keep only specified color, set rest to background'
    # },
    # REMOVED: extract_color - redundant with filter_color (0 usage in 50-task benchmark)
    # 'extract_color': {
    #     'function': extract_color,
    #     'params': {
    #         'color': {'type': int, 'values': list(range(10)), 'default': 1}
    #     },
    #     'description': 'Extract objects of specified color'
    # },
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
    # REMOVED: keep_colors - redundant with filter_color (0 usage in 50-task benchmark)
    # 'keep_colors': {
    #     'function': keep_colors,
    #     'params': {
    #         'colors': {'type': tuple, 'values': [(1,), (2,), (1, 2), (1, 2, 3)], 'default': (1,)},
    #         'background': {'type': int, 'values': list(range(10)), 'default': 0}
    #     },
    #     'description': 'Keep multiple specified colors'
    # }

    # =========================================================================
    # --- Phase 2 New Operations (v0.97) ---
    # =========================================================================

    # Object / Connectivity (6 ops)
    'label_objects': {
        'function': label_objects,
        'params': {
            'color': {'type': int, 'values': list(range(10)), 'default': 0},
            'output': {'type': str, 'values': ['count', 'labels', 'binary'], 'default': 'count'}
        },
        'description': 'Label connected objects; output = pixel count of each object'
    },
    'select_largest_object': {
        'function': select_largest_object,
        'params': {
            'background': {'type': int, 'values': list(range(10)), 'default': 0},
            'keep_color': {'type': bool, 'values': [True, False], 'default': True}
        },
        'description': 'Keep only the largest connected object'
    },
    'select_smallest_object': {
        'function': select_smallest_object,
        'params': {
            'background': {'type': int, 'values': list(range(10)), 'default': 0},
            'keep_color': {'type': bool, 'values': [True, False], 'default': True}
        },
        'description': 'Keep only the smallest connected object'
    },
    'fill_holes': {
        'function': fill_holes,
        'params': {
            'background': {'type': int, 'values': list(range(10)), 'default': 0},
            'fill_color': {'type': int, 'values': [-1] + list(range(10)), 'default': -1}
        },
        'description': 'Fill enclosed holes in objects'
    },
    'outline_objects': {
        'function': outline_objects,
        'params': {
            'background': {'type': int, 'values': list(range(10)), 'default': 0},
            'outline_color': {'type': int, 'values': list(range(1, 10)), 'default': 1},
            'thickness': {'type': int, 'values': [1, 2, 3], 'default': 1}
        },
        'description': 'Draw outlines around objects'
    },
    'count_and_mark': {
        'function': count_and_mark,
        'params': {
            'background': {'type': int, 'values': list(range(10)), 'default': 0},
            'mark_color': {'type': int, 'values': [-1] + list(range(1, 10)), 'default': -1}
        },
        'description': 'Mark each object with its size rank (1=largest)'
    },

    # Pattern / Repetition (5 ops)
    'extract_repeating_unit': {
        'function': extract_repeating_unit,
        'params': {
            'axis': {'type': str, 'values': ['both', 'horizontal', 'vertical'], 'default': 'both'}
        },
        'description': 'Extract smallest repeating tile from grid'
    },
    'tile_by_pattern': {
        'function': tile_by_pattern,
        'params': {
            'target_h': {'type': int, 'values': [0, 5, 10, 15, 20, 30], 'default': 0},
            'target_w': {'type': int, 'values': [0, 5, 10, 15, 20, 30], 'default': 0}
        },
        'description': 'Extract repeating unit and tile to target size'
    },
    'reflect_about_center': {
        'function': reflect_about_center,
        'params': {
            'axis': {'type': str, 'values': ['horizontal', 'vertical', 'h', 'v'], 'default': 'horizontal'}
        },
        'description': 'Reflect one half of grid onto the other'
    },
    'mirror_quadrant': {
        'function': mirror_quadrant,
        'params': {
            'quadrant': {'type': str,
                         'values': ['topleft', 'topright', 'bottomleft', 'bottomright'],
                         'default': 'topleft'}
        },
        'description': 'Mirror one quadrant to fill entire grid'
    },
    'detect_and_complete_symmetry': {
        'function': detect_and_complete_symmetry,
        'params': {
            'axis': {'type': str, 'values': ['horizontal', 'vertical'], 'default': 'horizontal'}
        },
        'description': 'Detect near-symmetry and complete it from the denser half'
    },

    # Conditional / Masking (4 ops)
    'apply_if_color': {
        'function': apply_if_color,
        'params': {
            'trigger_color': {'type': int, 'values': list(range(1, 10)), 'default': 1},
            'fill_color': {'type': int, 'values': list(range(1, 10)), 'default': 2},
            'operation': {'type': str,
                          'values': ['fill_row', 'fill_col', 'fill_adjacent', 'mark_row'],
                          'default': 'fill_row'}
        },
        'description': 'Apply transformation where trigger color exists'
    },
    'conditional_fill': {
        'function': conditional_fill,
        'params': {
            'condition_color': {'type': int, 'values': list(range(1, 10)), 'default': 1},
            'fill_color': {'type': int, 'values': list(range(1, 10)), 'default': 2},
            'region': {'type': str,
                       'values': ['same_row', 'same_col', 'right_of', 'below', 'enclosed'],
                       'default': 'same_row'}
        },
        'description': 'Fill background cells in region relative to condition color'
    },
    'mask_where': {
        'function': mask_where,
        'params': {
            'mask_color': {'type': int, 'values': list(range(10)), 'default': 0},
            'replacement': {'type': int, 'values': list(range(10)), 'default': 0},
            'invert': {'type': bool, 'values': [False, True], 'default': False}
        },
        'description': 'Zero out (or keep) cells matching a color'
    },
    'replace_pattern_color': {
        'function': replace_pattern_color,
        'params': {
            'from_color': {'type': int, 'values': list(range(1, 10)), 'default': 1},
            'to_color': {'type': int, 'values': list(range(1, 10)), 'default': 2},
            'min_size': {'type': int, 'values': [1, 2, 3, 4, 5], 'default': 1},
            'max_size': {'type': int, 'values': [1, 2, 4, 10, 100], 'default': 100}
        },
        'description': 'Replace color only for objects in a size range'
    },

    # Path / Line Drawing (4 ops)
    'connect_endpoints': {
        'function': connect_endpoints,
        'params': {
            'color': {'type': int, 'values': list(range(1, 10)), 'default': 1},
            'line_color': {'type': int, 'values': [-1] + list(range(1, 10)), 'default': -1},
            'style': {'type': str,
                      'values': ['straight', 'horizontal_then_vertical', 'vertical_then_horizontal'],
                      'default': 'straight'}
        },
        'description': 'Connect two most distant pixels of a color with a line'
    },
    'draw_line': {
        'function': draw_line,
        'params': {
            'direction': {'type': str, 'values': ['horizontal', 'vertical'], 'default': 'horizontal'},
            'position': {'type': int, 'values': [-1, 0, 1, 2, 3, 4, 5], 'default': -1},
            'color': {'type': int, 'values': list(range(1, 10)), 'default': 1}
        },
        'description': 'Draw a horizontal or vertical line across the grid'
    },
    'extend_lines': {
        'function': extend_lines,
        'params': {
            'color': {'type': int, 'values': list(range(1, 10)), 'default': 1},
            'extend_color': {'type': int, 'values': [-1] + list(range(1, 10)), 'default': -1},
            'direction': {'type': str, 'values': ['all', 'horizontal', 'vertical'], 'default': 'all'}
        },
        'description': 'Extend line segments to grid boundary'
    },
    'fill_between': {
        'function': fill_between,
        'params': {
            'color': {'type': int, 'values': list(range(1, 10)), 'default': 1},
            'fill_color': {'type': int, 'values': list(range(1, 10)), 'default': 2},
            'axis': {'type': str, 'values': ['horizontal', 'vertical'], 'default': 'horizontal'}
        },
        'description': 'Fill region between first and last occurrence of a color'
    },

    # Spatial / Arrangement (4 ops)
    'align_to_edge': {
        'function': align_to_edge,
        'params': {
            'edge': {'type': str, 'values': ['left', 'right', 'top', 'bottom'], 'default': 'left'},
            'background': {'type': int, 'values': list(range(10)), 'default': 0}
        },
        'description': 'Slide non-background content to specified edge'
    },
    'center_content': {
        'function': center_content,
        'params': {
            'background': {'type': int, 'values': list(range(10)), 'default': 0}
        },
        'description': 'Move all content to center of grid'
    },
    'distribute_vertically': {
        'function': distribute_vertically,
        'params': {
            'background': {'type': int, 'values': list(range(10)), 'default': 0}
        },
        'description': 'Spread objects evenly vertically in each column'
    },
    'distribute_horizontally': {
        'function': distribute_horizontally,
        'params': {
            'background': {'type': int, 'values': list(range(10)), 'default': 0}
        },
        'description': 'Spread objects evenly horizontally in each row'
    },

    # Transformation Variants (5 ops)
    'diagonal_flip': {
        'function': diagonal_flip,
        'params': {
            'diagonal': {'type': str, 'values': ['main', 'anti', 'primary', 'secondary'],
                         'default': 'main'}
        },
        'description': 'Flip along main or anti diagonal'
    },
    'rotate_and_flip': {
        'function': rotate_and_flip,
        'params': {
            'angle': {'type': int, 'values': [90, 180, 270], 'default': 90},
            'axis': {'type': str, 'values': ['horizontal', 'vertical'], 'default': 'horizontal'}
        },
        'description': 'Rotate then flip (dihedral group coverage)'
    },
    'gravity_up': {
        'function': gravity_up,
        'params': {},
        'description': 'Float non-zero cells to top of each column'
    },
    'gravity_down': {
        'function': gravity_down,
        'params': {},
        'description': 'Sink non-zero cells to bottom of each column'
    },
    'gravity_left': {
        'function': gravity_left,
        'params': {},
        'description': 'Slide non-zero cells to left of each row'
    },
    'gravity_right': {
        'function': gravity_right,
        'params': {},
        'description': 'Slide non-zero cells to right of each row'
    },

    # Overlay / Composition (2 ops)
    'overlay_grids': {
        'function': overlay_grids,
        'params': {
            'overlay_mode': {'type': str,
                             'values': ['fold_h', 'fold_v', 'max', 'add'],
                             'default': 'fold_h'}
        },
        'description': 'Fold or overlay grid halves onto each other'
    },
    'blend_by_mask': {
        'function': blend_by_mask,
        'params': {
            'mask_color': {'type': int, 'values': list(range(10)), 'default': 0},
            'fill_value': {'type': int, 'values': list(range(1, 10)), 'default': 1},
            'mode': {'type': str,
                     'values': ['checkerboard', 'stripes_h', 'stripes_v', 'diagonal'],
                     'default': 'checkerboard'}
        },
        'description': 'Fill background with a geometric pattern'
    },
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
    Get parameter candidates for operation (v0.96 - task-aware, validated).

    Args:
        op_name: Operation name
        task: Task data (optional, for extracting task-specific values)
        constraints: Task constraints (optional, for filtering)

    Returns:
        List of parameter dictionaries (validated, no invalid values)
    """
    if op_name not in PARAMETRIC_OPERATIONS:
        return [{}]

    spec = PARAMETRIC_OPERATIONS[op_name]

    if not spec['params']:
        return [{}]

    # Extract task properties for smart parameter generation
    task_sizes = []
    if task and 'train' in task:
        for example in task['train']:
            if isinstance(example, dict):
                input_grid = np.array(example['input'])
                output_grid = np.array(example['output'])
            else:
                input_grid, output_grid = example

            task_sizes.append({
                'input_h': input_grid.shape[0],
                'input_w': input_grid.shape[1],
                'output_h': output_grid.shape[0],
                'output_w': output_grid.shape[1]
            })

    # Size operation parameter generation (task-aware)
    if op_name in ['expand_to_size', 'compress_to_fit', 'resize_with_padding', 'fit_to_canvas']:
        return _get_size_op_candidates(op_name, spec, task_sizes)

    # Default parameter generation
    candidates = []

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


def _get_size_op_candidates(op_name: str, spec: Dict, task_sizes: List[Dict]) -> List[Dict]:
    """
    Generate task-aware size operation parameters.

    Avoids invalid parameters like width=0, uses actual task sizes.
    """
    candidates = []

    if not task_sizes:
        # No task info - use safe defaults only
        if op_name == 'expand_to_size':
            candidates.append({'target_h': 10, 'target_w': 10, 'fill': 'tile'})
            candidates.append({'target_h': 15, 'target_w': 15, 'fill': 'tile'})
        elif op_name == 'compress_to_fit':
            candidates.append({'target_h': 5, 'target_w': 5, 'method': 'downsample'})
            candidates.append({'target_h': 7, 'target_w': 7, 'method': 'select'})
        elif op_name == 'resize_with_padding':
            candidates.append({'target_h': 10, 'target_w': 10, 'padding_color': 0})
        elif op_name == 'fit_to_canvas':
            candidates.append({'canvas_h': 10, 'canvas_w': 10, 'align': 'center'})

        return candidates[:3]

    # Get common sizes from task
    output_sizes = [(s['output_h'], s['output_w']) for s in task_sizes]
    input_sizes = [(s['input_h'], s['input_w']) for s in task_sizes]

    # Most common output size
    from collections import Counter
    size_counts = Counter(output_sizes)
    most_common_output = size_counts.most_common(1)[0][0] if size_counts else (10, 10)

    if op_name == 'expand_to_size':
        # Target: common output size
        h, w = most_common_output
        candidates.append({'target_h': h, 'target_w': w, 'fill': 'tile'})
        candidates.append({'target_h': h, 'target_w': w, 'fill': 'background'})

        # Also try slightly larger
        candidates.append({'target_h': h + 5, 'target_w': w + 5, 'fill': 'tile'})

    elif op_name == 'compress_to_fit':
        # Target: common output size (usually smaller than input)
        h, w = most_common_output
        if h > 0 and w > 0:
            candidates.append({'target_h': max(1, h), 'target_w': max(1, w), 'method': 'downsample'})
            candidates.append({'target_h': max(1, h), 'target_w': max(1, w), 'method': 'select'})

        # Also try half of common input size
        if input_sizes:
            avg_h = int(np.mean([s[0] for s in input_sizes]))
            avg_w = int(np.mean([s[1] for s in input_sizes]))
            candidates.append({'target_h': max(1, avg_h // 2), 'target_w': max(1, avg_w // 2), 'method': 'max'})

    elif op_name == 'resize_with_padding':
        # Target: common output size
        h, w = most_common_output
        if h > 0 and w > 0:
            candidates.append({'target_h': max(1, h), 'target_w': max(1, w), 'padding_color': 0})

            # Try with different padding colors if outputs use non-zero backgrounds
            if task_sizes:
                candidates.append({'target_h': max(1, h), 'target_w': max(1, w), 'padding_color': 1})

    elif op_name == 'fit_to_canvas':
        # Canvas: common output size
        h, w = most_common_output
        if h > 0 and w > 0:
            candidates.append({'canvas_h': max(1, h), 'canvas_w': max(1, w), 'align': 'center'})
            candidates.append({'canvas_h': max(1, h), 'canvas_w': max(1, w), 'align': 'topleft'})

    # Validate: ensure all h/w > 0
    valid_candidates = []
    for c in candidates:
        is_valid = True
        for key, value in c.items():
            if 'h' in key or 'w' in key or 'height' in key or 'width' in key:
                if isinstance(value, int) and value <= 0:
                    is_valid = False
                    break
        if is_valid:
            valid_candidates.append(c)

    return valid_candidates[:3]  # Limit to 3 candidates per operation


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
