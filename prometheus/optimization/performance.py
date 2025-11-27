"""
Performance Optimization Utilities

Provides various optimization techniques:
- Model quantization for faster inference
- Result caching for repeated positions
- Batch inference for parallel games
- TensorFlow optimizations
- Memory management

Usage:
    # Quantize model
    optimizer = ModelOptimizer()
    fast_model = optimizer.quantize(model)

    # Cache results
    cache = PositionCache(max_size=10000)
    cached_agent = CachedAgent(agent, cache)

    # Batch processing
    batch_processor = BatchInference(model, batch_size=32)
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
from typing import Dict, List, Tuple, Optional, Any
from collections import OrderedDict
import hashlib
import time


class ModelOptimizer:
    """
    Optimize models for faster inference.

    Techniques:
    - Dynamic range quantization
    - Float16 conversion
    - Layer fusion
    - TensorFlow Lite conversion
    """

    def __init__(self):
        """Initialize optimizer."""
        pass

    def quantize_int8(self, model: keras.Model,
                     representative_dataset=None) -> Any:
        """
        Quantize model to INT8 (4x smaller, faster).

        Args:
            model: Model to quantize
            representative_dataset: Sample data for calibration

        Returns:
            Quantized TFLite model
        """
        print("Quantizing model to INT8...")

        # Convert to TFLite
        converter = tf.lite.TFLiteConverter.from_keras_model(model)

        # Enable quantization
        converter.optimizations = [tf.lite.Optimize.DEFAULT]

        if representative_dataset is not None:
            converter.representative_dataset = representative_dataset

        # Convert
        quantized_model = converter.convert()

        # Calculate size reduction
        original_size = model.count_params() * 4  # 4 bytes per float32
        quantized_size = len(quantized_model)
        reduction = 100 * (1 - quantized_size / original_size)

        print(f"  Original size: {original_size / 1024 / 1024:.1f} MB")
        print(f"  Quantized size: {quantized_size / 1024 / 1024:.1f} MB")
        print(f"  Reduction: {reduction:.1f}%")

        return quantized_model

    def quantize_float16(self, model: keras.Model) -> Any:
        """
        Quantize model to FLOAT16 (2x smaller).

        Args:
            model: Model to quantize

        Returns:
            Float16 TFLite model
        """
        print("Quantizing model to FLOAT16...")

        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.target_spec.supported_types = [tf.float16]

        quantized_model = converter.convert()

        original_size = model.count_params() * 4
        quantized_size = len(quantized_model)

        print(f"  Size reduction: {100 * (1 - quantized_size / original_size):.1f}%")

        return quantized_model

    def optimize_for_inference(self, model: keras.Model) -> keras.Model:
        """
        Optimize model for inference (in-place modifications).

        Args:
            model: Model to optimize

        Returns:
            Optimized model
        """
        print("Optimizing for inference...")

        # Freeze batch normalization
        for layer in model.layers:
            if isinstance(layer, keras.layers.BatchNormalization):
                layer.trainable = False

        # Compile with optimized settings
        model.compile(
            optimizer='adam',  # Optimizer doesn't matter for inference
            loss='mse',
            jit_compile=True  # Enable XLA compilation
        )

        print("  ✓ Frozen BatchNorm layers")
        print("  ✓ Enabled XLA compilation")

        return model

    def benchmark_inference(self, model: keras.Model,
                          input_shape: Tuple,
                          num_runs: int = 100) -> Dict:
        """
        Benchmark inference speed.

        Args:
            model: Model to benchmark
            input_shape: Input shape (without batch dimension)
            num_runs: Number of inference runs

        Returns:
            Benchmark results
        """
        print(f"Benchmarking inference ({num_runs} runs)...")

        # Warmup
        dummy_input = np.random.rand(1, *input_shape).astype(np.float32)
        for _ in range(10):
            model.predict(dummy_input, verbose=0)

        # Benchmark
        times = []
        for _ in range(num_runs):
            start = time.time()
            model.predict(dummy_input, verbose=0)
            elapsed = time.time() - start
            times.append(elapsed)

        results = {
            'mean_ms': np.mean(times) * 1000,
            'std_ms': np.std(times) * 1000,
            'min_ms': np.min(times) * 1000,
            'max_ms': np.max(times) * 1000,
            'fps': 1.0 / np.mean(times)
        }

        print(f"  Mean: {results['mean_ms']:.1f} ms")
        print(f"  Std: {results['std_ms']:.1f} ms")
        print(f"  FPS: {results['fps']:.1f}")

        return results


class PositionCache:
    """
    Cache position evaluations to avoid recomputation.

    Uses LRU (Least Recently Used) eviction policy.
    """

    def __init__(self, max_size: int = 10000):
        """
        Initialize cache.

        Args:
            max_size: Maximum number of cached positions
        """
        self.max_size = max_size
        self.cache = OrderedDict()
        self.hits = 0
        self.misses = 0

    def _hash_position(self, state: np.ndarray) -> str:
        """
        Hash board position for caching.

        Args:
            state: Board state

        Returns:
            Hash string
        """
        return hashlib.md5(state.tobytes()).hexdigest()

    def get(self, state: np.ndarray) -> Optional[Tuple]:
        """
        Get cached evaluation.

        Args:
            state: Board state

        Returns:
            Cached (policy, value) or None
        """
        key = self._hash_position(state)

        if key in self.cache:
            self.hits += 1
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        else:
            self.misses += 1
            return None

    def put(self, state: np.ndarray, policy: np.ndarray, value: float):
        """
        Cache evaluation.

        Args:
            state: Board state
            policy: Policy vector
            value: Value estimate
        """
        key = self._hash_position(state)

        # Add to cache
        self.cache[key] = (policy.copy(), value)

        # Evict oldest if over capacity
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def clear(self):
        """Clear cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def stats(self) -> Dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0

        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'total_queries': total
        }

    def print_stats(self):
        """Print cache statistics."""
        stats = self.stats()
        print(f"Cache Statistics:")
        print(f"  Size: {stats['size']}/{stats['max_size']}")
        print(f"  Hits: {stats['hits']}")
        print(f"  Misses: {stats['misses']}")
        print(f"  Hit rate: {stats['hit_rate']:.1%}")


class CachedAgent:
    """
    Wrapper that adds caching to any agent.

    Transparently caches predictions to avoid redundant computation.
    """

    def __init__(self, agent, cache: Optional[PositionCache] = None):
        """
        Initialize cached agent.

        Args:
            agent: Base agent to wrap
            cache: Position cache (creates new if None)
        """
        self.agent = agent
        self.cache = cache or PositionCache()

        # Delegate attributes
        self.name = f"Cached {agent.name}"
        self.board_size = getattr(agent, 'board_size', None)

    def predict(self, state: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Predict with caching.

        Args:
            state: Board state

        Returns:
            (policy, value)
        """
        # Check cache
        cached = self.cache.get(state)
        if cached is not None:
            return cached

        # Compute and cache
        policy, value = self.agent.predict(state)
        self.cache.put(state, policy, value)

        return policy, value

    def get_move(self, state: np.ndarray, legal_moves: List,
                temperature: float = 1.0) -> Tuple:
        """
        Get move (delegates to agent).

        Args:
            state: Board state
            legal_moves: Legal moves
            temperature: Temperature parameter

        Returns:
            Selected move
        """
        return self.agent.get_move(state, legal_moves, temperature)


class BatchInference:
    """
    Batch multiple inference requests for efficiency.

    Useful when playing multiple games in parallel.
    """

    def __init__(self, model: keras.Model, batch_size: int = 32):
        """
        Initialize batch processor.

        Args:
            model: Model for inference
            batch_size: Maximum batch size
        """
        self.model = model
        self.batch_size = batch_size
        self.pending_states = []
        self.pending_callbacks = []

    def add_request(self, state: np.ndarray, callback):
        """
        Add inference request to batch.

        Args:
            state: Board state
            callback: Function to call with (policy, value)
        """
        self.pending_states.append(state)
        self.pending_callbacks.append(callback)

        # Process if batch full
        if len(self.pending_states) >= self.batch_size:
            self.process_batch()

    def process_batch(self):
        """Process accumulated batch."""
        if not self.pending_states:
            return

        # Stack states
        batch = np.stack(self.pending_states)

        # Batch inference
        policy_batch, value_batch = self.model.predict(batch, verbose=0)

        # Call callbacks
        for i, callback in enumerate(self.pending_callbacks):
            callback(policy_batch[i], value_batch[i])

        # Clear batch
        self.pending_states.clear()
        self.pending_callbacks.clear()

    def flush(self):
        """Process remaining requests."""
        self.process_batch()


class MemoryManager:
    """
    Manage memory usage during training/inference.

    Techniques:
    - Gradient checkpointing
    - Mixed precision training
    - Memory growth
    """

    @staticmethod
    def enable_memory_growth():
        """Enable GPU memory growth (use only what's needed)."""
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            print(f"✓ Enabled memory growth for {len(gpus)} GPU(s)")
        else:
            print("No GPUs found")

    @staticmethod
    def set_memory_limit(limit_mb: int = 4096):
        """
        Set GPU memory limit.

        Args:
            limit_mb: Memory limit in MB
        """
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            for gpu in gpus:
                tf.config.set_logical_device_configuration(
                    gpu,
                    [tf.config.LogicalDeviceConfiguration(
                        memory_limit=limit_mb
                    )]
                )
            print(f"✓ Set GPU memory limit: {limit_mb} MB")

    @staticmethod
    def enable_mixed_precision():
        """Enable mixed precision training (faster, less memory)."""
        policy = keras.mixed_precision.Policy('mixed_float16')
        keras.mixed_precision.set_global_policy(policy)
        print("✓ Enabled mixed precision training (float16)")

    @staticmethod
    def clear_session():
        """Clear Keras session to free memory."""
        keras.backend.clear_session()
        print("✓ Cleared Keras session")


class ParallelGameExecutor:
    """
    Execute multiple games in parallel for faster training.

    Uses multiprocessing for CPU parallelism.
    """

    def __init__(self, num_workers: int = 4):
        """
        Initialize parallel executor.

        Args:
            num_workers: Number of parallel workers
        """
        self.num_workers = num_workers

    def play_games_parallel(self, agent1, agent2, env,
                           num_games: int) -> List[Dict]:
        """
        Play multiple games in parallel.

        Args:
            agent1: First agent
            agent2: Second agent
            env: Game environment
            num_games: Number of games to play

        Returns:
            List of game results
        """
        # This is a simplified version
        # Full implementation would use multiprocessing

        print(f"Playing {num_games} games with {self.num_workers} workers...")

        results = []

        # For now, play sequentially
        # In production, would use multiprocessing.Pool
        from prometheus.training.go_training import play_go_match

        for i in range(0, num_games, self.num_workers):
            batch_size = min(self.num_workers, num_games - i)

            for j in range(batch_size):
                result = play_go_match(agent1, agent2, env, num_games=1, verbose=False)
                results.extend(result['games'])

            print(f"  Progress: {min(i + batch_size, num_games)}/{num_games}")

        return results


def optimize_for_deployment(model: keras.Model,
                           model_path: str,
                           quantize: bool = True) -> Dict:
    """
    Complete optimization pipeline for deployment.

    Args:
        model: Model to optimize
        model_path: Path to save optimized model
        quantize: Apply quantization

    Returns:
        Optimization report
    """
    print("="*70)
    print("DEPLOYMENT OPTIMIZATION PIPELINE")
    print("="*70)

    optimizer = ModelOptimizer()
    report = {}

    # 1. Original model stats
    original_params = model.count_params()
    print(f"\n1. Original model:")
    print(f"   Parameters: {original_params:,}")

    # 2. Optimize for inference
    print(f"\n2. Applying inference optimizations...")
    model = optimizer.optimize_for_inference(model)
    report['optimized_model'] = model

    # 3. Quantization (optional)
    if quantize:
        print(f"\n3. Quantizing model...")
        quantized = optimizer.quantize_float16(model)
        report['quantized_model'] = quantized

        # Save quantized
        quantized_path = model_path.replace('.h5', '_quantized.tflite')
        with open(quantized_path, 'wb') as f:
            f.write(quantized)
        report['quantized_path'] = quantized_path

    # 4. Save optimized model
    print(f"\n4. Saving models...")
    model.save(model_path)
    report['model_path'] = model_path

    # 5. Benchmark
    print(f"\n5. Benchmarking...")
    input_shape = model.input_shape[1:]
    benchmark = optimizer.benchmark_inference(model, input_shape)
    report['benchmark'] = benchmark

    print("\n" + "="*70)
    print("OPTIMIZATION COMPLETE")
    print("="*70)
    print(f"Optimized model: {model_path}")
    if quantize:
        print(f"Quantized model: {quantized_path}")
    print(f"Inference speed: {benchmark['mean_ms']:.1f} ms")
    print("="*70 + "\n")

    return report
