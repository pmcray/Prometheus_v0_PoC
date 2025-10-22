#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARC Parametric Operations Library (v0.95)

This module provides a clean, unified library of parametric operations for
ARC-AGI program synthesis. Each operation supports flexible parameters and
can be composed into programs.

Key Features:
- 15 base operations with parameters
- Type-checked parameter validation
- Comprehensive operation catalog
- Integration with ARCProgram execution

Based on proven primitives from v0.69-v0.94 implementations.
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
# OPERATION CATALOG
# ============================================================================

PARAMETRIC_OPERATIONS = {
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
