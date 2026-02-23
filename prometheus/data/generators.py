"""
Prometheus Data Generators

This module contains data generation classes for the Prometheus experiments:
- PatternGenerator: 64×64 visual patterns (Experiment 1 - Intelligence Explosion)
- ARCGenerator: 64×64 geometric transformations (Experiment 2 - Dynamic ARC)
- TaskGenerator: 32×32 multi-class patterns (Experiment 3 - CRLS Strange Loop)

All generators support:
- Configurable distributions for data generation
- Noise injection for realistic difficulty
- Reproducible random seeds
"""

import numpy as np
from typing import Tuple, Dict
from abc import ABC, abstractmethod


class BaseGenerator(ABC):
    """
    Base class for all data generators.

    Provides common functionality:
    - Random seed management
    - Distribution normalization
    - Noise injection
    """

    def __init__(self, grid_size: int, seed: int = 42):
        """
        Initialize base generator.

        Args:
            grid_size: Size of grid (width and height)
            seed: Random seed for reproducibility
        """
        self.grid_size = grid_size
        self.seed = seed
        np.random.seed(seed)

    def _normalize_distribution(self, distribution: Dict[str, float]) -> Dict[str, float]:
        """Normalize distribution to sum to 1.0."""
        total = sum(distribution.values())
        return {k: v/total for k, v in distribution.items()}

    def _add_noise(self, grid: np.ndarray, noise_level: float = 0.05) -> np.ndarray:
        """Add Gaussian noise to grid."""
        noise = np.random.normal(0, noise_level, grid.shape)
        return np.clip(grid + noise, 0, 1)

    @abstractmethod
    def generate_batch(self, n: int, distribution: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate batch of samples according to distribution.

        Args:
            n: Number of samples
            distribution: Dictionary mapping class names to probabilities

        Returns:
            Tuple of (patterns, labels)
        """
        pass


class PatternGenerator(BaseGenerator):
    """
    Generates complex 64×64 visual patterns for Intelligence Explosion experiment.

    Pattern types:
    - horizontal_stripes: Horizontal stripe pattern
    - vertical_stripes: Vertical stripe pattern
    - diagonal_lines: Diagonal line pattern
    - checkerboard: Checkerboard pattern
    - concentric_circles: Concentric circle pattern
    - spiral: Spiral pattern
    - maze: Maze-like pattern
    - fractal_tree: Fractal tree pattern

    Example:
        >>> generator = PatternGenerator(grid_size=64)
        >>> distribution = {'horizontal_stripes': 0.3, 'spiral': 0.7}
        >>> X, y = generator.generate_batch(100, distribution)
        >>> X.shape  # (100, 64, 64, 1)
    """

    def __init__(self, grid_size: int = 64, seed: int = 42):
        super().__init__(grid_size, seed)

        self.pattern_types = [
            'horizontal_stripes',
            'vertical_stripes',
            'diagonal_lines',
            'checkerboard',
            'concentric_circles',
            'spiral',
            'maze',
            'fractal_tree'
        ]
        self.num_classes = len(self.pattern_types)

    def _generate_horizontal_stripes(self) -> np.ndarray:
        """Generate horizontal stripe pattern."""
        grid = np.zeros((self.grid_size, self.grid_size))
        stripe_width = np.random.randint(2, 6)
        for i in range(0, self.grid_size, stripe_width * 2):
            grid[i:i+stripe_width, :] = 1.0
        return grid

    def _generate_vertical_stripes(self) -> np.ndarray:
        """Generate vertical stripe pattern."""
        grid = np.zeros((self.grid_size, self.grid_size))
        stripe_width = np.random.randint(2, 6)
        for i in range(0, self.grid_size, stripe_width * 2):
            grid[:, i:i+stripe_width] = 1.0
        return grid

    def _generate_diagonal_lines(self) -> np.ndarray:
        """Generate diagonal line pattern."""
        grid = np.zeros((self.grid_size, self.grid_size))
        spacing = np.random.randint(4, 8)
        for offset in range(-self.grid_size, self.grid_size, spacing):
            for i in range(self.grid_size):
                j = i + offset
                if 0 <= j < self.grid_size:
                    grid[i, j] = 1.0
        return grid

    def _generate_checkerboard(self) -> np.ndarray:
        """Generate checkerboard pattern."""
        grid = np.zeros((self.grid_size, self.grid_size))
        square_size = np.random.randint(3, 8)
        for i in range(0, self.grid_size, square_size):
            for j in range(0, self.grid_size, square_size):
                if ((i // square_size) + (j // square_size)) % 2 == 0:
                    grid[i:i+square_size, j:j+square_size] = 1.0
        return grid

    def _generate_concentric_circles(self) -> np.ndarray:
        """Generate concentric circles pattern."""
        grid = np.zeros((self.grid_size, self.grid_size))
        center = self.grid_size // 2
        num_rings = np.random.randint(4, 8)
        for ring in range(num_rings):
            radius = (ring + 1) * (self.grid_size // (2 * num_rings))
            y, x = np.ogrid[:self.grid_size, :self.grid_size]
            mask = np.abs(np.sqrt((x - center)**2 + (y - center)**2) - radius) < 2
            grid[mask] = 1.0
        return grid

    def _generate_spiral(self) -> np.ndarray:
        """Generate spiral pattern."""
        grid = np.zeros((self.grid_size, self.grid_size))
        center = self.grid_size // 2
        for angle in np.linspace(0, 8*np.pi, 1000):
            r = angle * 2
            if r < self.grid_size // 2:
                x = int(center + r * np.cos(angle))
                y = int(center + r * np.sin(angle))
                if 0 <= x < self.grid_size and 0 <= y < self.grid_size:
                    grid[y, x] = 1.0
        return grid

    def _generate_maze(self) -> np.ndarray:
        """Generate maze-like pattern."""
        grid = np.random.rand(self.grid_size, self.grid_size)
        grid = (grid > 0.6).astype(float)
        # Add some structure
        for i in range(0, self.grid_size, 8):
            grid[i, :] = 1.0
        for j in range(0, self.grid_size, 8):
            grid[:, j] = 1.0
        return grid

    def _generate_fractal_tree(self) -> np.ndarray:
        """Generate fractal tree pattern."""
        grid = np.zeros((self.grid_size, self.grid_size))

        def draw_branch(x, y, angle, length, depth):
            if depth == 0 or length < 2:
                return
            x2 = int(x + length * np.cos(angle))
            y2 = int(y + length * np.sin(angle))

            # Draw line
            steps = max(abs(x2-x), abs(y2-y))
            if steps > 0:
                for t in np.linspace(0, 1, steps):
                    xi = int(x + t * (x2 - x))
                    yi = int(y + t * (y2 - y))
                    if 0 <= xi < self.grid_size and 0 <= yi < self.grid_size:
                        grid[yi, xi] = 1.0

            # Recursive branches
            draw_branch(x2, y2, angle - 0.5, length * 0.7, depth - 1)
            draw_branch(x2, y2, angle + 0.5, length * 0.7, depth - 1)

        # Start from bottom center
        start_x = self.grid_size // 2
        start_y = self.grid_size - 5
        draw_branch(start_x, start_y, -np.pi/2, 15, 5)

        return grid

    def generate_pattern(self, pattern_type: str) -> np.ndarray:
        """
        Generate pattern of specified type.

        Args:
            pattern_type: Name of pattern type

        Returns:
            Grid with pattern
        """
        if pattern_type == 'horizontal_stripes':
            return self._generate_horizontal_stripes()
        elif pattern_type == 'vertical_stripes':
            return self._generate_vertical_stripes()
        elif pattern_type == 'diagonal_lines':
            return self._generate_diagonal_lines()
        elif pattern_type == 'checkerboard':
            return self._generate_checkerboard()
        elif pattern_type == 'concentric_circles':
            return self._generate_concentric_circles()
        elif pattern_type == 'spiral':
            return self._generate_spiral()
        elif pattern_type == 'maze':
            return self._generate_maze()
        elif pattern_type == 'fractal_tree':
            return self._generate_fractal_tree()
        else:
            return np.zeros((self.grid_size, self.grid_size))

    def generate_batch(self, n: int, distribution: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate batch of patterns with noise and augmentation.

        Args:
            n: Number of samples
            distribution: Dictionary mapping pattern types to probabilities

        Returns:
            Tuple of (patterns, labels)
            - patterns: shape (n, grid_size, grid_size, 1)
            - labels: shape (n,)
        """
        patterns = []
        labels = []

        # Normalize distribution
        dist = self._normalize_distribution(distribution)

        for _ in range(n):
            # Sample pattern type
            pattern_type = np.random.choice(
                list(dist.keys()),
                p=list(dist.values())
            )

            # Generate pattern
            pattern = self.generate_pattern(pattern_type)

            # Add noise
            pattern = self._add_noise(pattern, noise_level=0.05)

            patterns.append(pattern)
            label = self.pattern_types.index(pattern_type)
            labels.append(label)

        patterns = np.array(patterns)
        patterns = patterns[..., np.newaxis]
        labels = np.array(labels)

        return patterns, labels


class ARCGenerator(BaseGenerator):
    """
    Generates complex 64×64 patterns and applies geometric transformations.

    Transformation types:
    - rotate_90: Rotate 90 degrees clockwise
    - rotate_180: Rotate 180 degrees
    - rotate_270: Rotate 270 degrees clockwise
    - flip_horizontal: Flip horizontally
    - flip_vertical: Flip vertically
    - flip_diagonal: Flip both horizontally and vertically
    - transpose: Matrix transpose
    - identity: No transformation

    Example:
        >>> generator = ARCGenerator(grid_size=64)
        >>> distribution = {'rotate_90': 0.5, 'flip_horizontal': 0.5}
        >>> X, y = generator.generate_batch(100, distribution)
        >>> X.shape  # (100, 64, 64, 1)
    """

    def __init__(self, grid_size: int = 64, seed: int = 42):
        super().__init__(grid_size, seed)

        self.transformations = [
            'rotate_90',
            'rotate_180',
            'rotate_270',
            'flip_horizontal',
            'flip_vertical',
            'flip_diagonal',
            'transpose',
            'identity'
        ]
        self.num_classes = len(self.transformations)

    def _generate_complex_pattern(self) -> np.ndarray:
        """Generate complex asymmetric pattern with multiple shape types."""
        grid = np.zeros((self.grid_size, self.grid_size))

        # Multiple shape types
        num_elements = np.random.randint(5, 10)
        for _ in range(num_elements):
            shape = np.random.choice(['rect', 'circle', 'line', 'cross', 'L'])

            if shape == 'rect':
                h = np.random.randint(4, 12)
                w = np.random.randint(4, 12)
                y = np.random.randint(0, self.grid_size - h)
                x = np.random.randint(0, self.grid_size - w)
                grid[y:y+h, x:x+w] = 1.0

            elif shape == 'circle':
                cy = np.random.randint(8, self.grid_size - 8)
                cx = np.random.randint(8, self.grid_size - 8)
                radius = np.random.randint(3, 8)
                y, x = np.ogrid[:self.grid_size, :self.grid_size]
                mask = (x - cx)**2 + (y - cy)**2 <= radius**2
                grid[mask] = 1.0

            elif shape == 'line':
                if np.random.random() > 0.5:  # Horizontal
                    y = np.random.randint(0, self.grid_size)
                    x1 = np.random.randint(0, self.grid_size - 10)
                    length = np.random.randint(8, 20)
                    grid[y, x1:min(x1+length, self.grid_size)] = 1.0
                else:  # Vertical
                    x = np.random.randint(0, self.grid_size)
                    y1 = np.random.randint(0, self.grid_size - 10)
                    length = np.random.randint(8, 20)
                    grid[y1:min(y1+length, self.grid_size), x] = 1.0

            elif shape == 'cross':
                cy = np.random.randint(5, self.grid_size - 5)
                cx = np.random.randint(5, self.grid_size - 5)
                size = np.random.randint(4, 10)
                grid[cy-size:cy+size, cx] = 1.0
                grid[cy, cx-size:cx+size] = 1.0

            elif shape == 'L':
                y = np.random.randint(0, self.grid_size - 10)
                x = np.random.randint(0, self.grid_size - 10)
                h = np.random.randint(6, 12)
                w = np.random.randint(6, 12)
                grid[y:y+h, x] = 1.0
                grid[y+h-1, x:x+w] = 1.0

        return np.clip(grid, 0, 1)

    def apply_transformation(self, grid: np.ndarray, transformation: str) -> np.ndarray:
        """
        Apply geometric transformation to grid.

        Args:
            grid: Input grid
            transformation: Transformation name

        Returns:
            Transformed grid
        """
        if transformation == 'rotate_90':
            return np.rot90(grid, k=-1)
        elif transformation == 'rotate_180':
            return np.rot90(grid, k=2)
        elif transformation == 'rotate_270':
            return np.rot90(grid, k=1)
        elif transformation == 'flip_horizontal':
            return np.fliplr(grid)
        elif transformation == 'flip_vertical':
            return np.flipud(grid)
        elif transformation == 'flip_diagonal':
            return np.fliplr(np.flipud(grid))
        elif transformation == 'transpose':
            return grid.T
        elif transformation == 'identity':
            return grid.copy()
        return grid

    def generate_batch(self, n: int, distribution: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate batch of transformed patterns.

        Args:
            n: Number of samples
            distribution: Dictionary mapping transformation types to probabilities

        Returns:
            Tuple of (patterns, labels)
            - patterns: shape (n, grid_size, grid_size, 1)
            - labels: shape (n,)
        """
        patterns = []
        labels = []

        dist = self._normalize_distribution(distribution)

        for _ in range(n):
            # Generate base pattern
            base = self._generate_complex_pattern()

            # Sample transformation
            transformation = np.random.choice(
                list(dist.keys()),
                p=list(dist.values())
            )

            # Apply transformation
            transformed = self.apply_transformation(base, transformation)

            # Add noise
            transformed = self._add_noise(transformed, noise_level=0.03)

            patterns.append(transformed)
            label = self.transformations.index(transformation)
            labels.append(label)

        patterns = np.array(patterns)
        patterns = patterns[..., np.newaxis]
        labels = np.array(labels)

        return patterns, labels


class TaskGenerator(BaseGenerator):
    """
    Generates 32×32 multi-class pattern classification tasks for CRLS loop.

    Task types:
    - grid_A: Horizontal bands
    - grid_B: Vertical bands
    - grid_C: Diagonal pattern
    - grid_D: Checkerboard
    - grid_E: Concentric squares
    - grid_F: Center cross

    Example:
        >>> generator = TaskGenerator(grid_size=32)
        >>> distribution = {'grid_A': 0.4, 'grid_B': 0.3, 'grid_C': 0.3}
        >>> X, y = generator.generate_batch(100, distribution)
        >>> X.shape  # (100, 32, 32, 1)
    """

    def __init__(self, grid_size: int = 32, num_classes: int = 6, seed: int = 42):
        super().__init__(grid_size, seed)

        self.num_classes = num_classes
        self.task_types = ['grid_A', 'grid_B', 'grid_C', 'grid_D', 'grid_E', 'grid_F']

    def _generate_pattern(self, task_type: str) -> np.ndarray:
        """
        Generate pattern for task type.

        Args:
            task_type: Task type name

        Returns:
            Pattern grid
        """
        grid = np.zeros((self.grid_size, self.grid_size))

        if task_type == 'grid_A':
            # Horizontal bands
            for i in range(0, self.grid_size, 4):
                grid[i:i+2, :] = 1.0

        elif task_type == 'grid_B':
            # Vertical bands
            for j in range(0, self.grid_size, 4):
                grid[:, j:j+2] = 1.0

        elif task_type == 'grid_C':
            # Diagonal
            np.fill_diagonal(grid, 1.0)

        elif task_type == 'grid_D':
            # Checkerboard
            for i in range(0, self.grid_size, 4):
                for j in range(0, self.grid_size, 4):
                    if (i//4 + j//4) % 2 == 0:
                        grid[i:i+4, j:j+4] = 1.0

        elif task_type == 'grid_E':
            # Concentric squares
            for k in range(4, self.grid_size//2, 4):
                grid[k:self.grid_size-k, k:self.grid_size-k] = 1.0

        elif task_type == 'grid_F':
            # Center cross
            mid = self.grid_size // 2
            grid[mid-2:mid+2, :] = 1.0
            grid[:, mid-2:mid+2] = 1.0

        return grid

    def generate_batch(self, n: int, distribution: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate batch according to distribution.

        Args:
            n: Number of samples
            distribution: Dictionary mapping task types to probabilities

        Returns:
            Tuple of (patterns, labels)
            - patterns: shape (n, grid_size, grid_size, 1)
            - labels: shape (n,)
        """
        patterns = []
        labels = []

        dist = self._normalize_distribution(distribution)

        for _ in range(n):
            # Sample task type
            task_type = np.random.choice(
                list(dist.keys()),
                p=list(dist.values())
            )

            # Generate pattern
            pattern = self._generate_pattern(task_type)

            # Add noise
            pattern = self._add_noise(pattern, noise_level=0.05)

            patterns.append(pattern)
            label = self.task_types.index(task_type)
            labels.append(label)

        patterns = np.array(patterns)
        patterns = patterns[..., np.newaxis]
        labels = np.array(labels)

        return patterns, labels
