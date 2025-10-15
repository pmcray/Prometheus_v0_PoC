#!/usr/bin/env python3
"""
ARC-AGI Transfer Learner (v0.79)
Cluster tasks by similarity and share patterns within clusters
"""

import json
import numpy as np
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Set
import os
from pathlib import Path

class ARCTransferLearner:
    """Transfer learning across task clusters"""

    def __init__(self):
        self.clusters = {}  # cluster_id -> list of task_ids
        self.task_features = {}  # task_id -> feature dict
        self.cluster_patterns = defaultdict(lambda: defaultdict(list))  # cluster -> {task -> patterns}
        self.cluster_primitives = defaultdict(Counter)  # cluster -> primitive frequencies
        self.cluster_success_primitives = defaultdict(set)  # cluster -> successful primitives

    def extract_task_features(self, task_data: Dict) -> Dict:
        """
        Extract similarity features from a task

        Features:
        - Grid size (input)
        - Color count
        - Object count (connected components)
        - Transformation type hints
        """
        features = {}

        # Use training examples
        train_examples = task_data.get('train', [])
        if not train_examples:
            return features

        # Analyze first training example
        input_grid = np.array(train_examples[0]['input'])
        output_grid = np.array(train_examples[0]['output'])

        # Grid size features
        features['input_height'] = input_grid.shape[0]
        features['input_width'] = input_grid.shape[1]
        features['output_height'] = output_grid.shape[0]
        features['output_width'] = output_grid.shape[1]
        features['grid_size_bucket'] = self._size_bucket(input_grid.shape)

        # Size change type
        if output_grid.shape == input_grid.shape:
            features['size_change'] = 'same'
        elif output_grid.shape[0] > input_grid.shape[0] or output_grid.shape[1] > input_grid.shape[1]:
            features['size_change'] = 'larger'
        else:
            features['size_change'] = 'smaller'

        # Color features
        input_colors = set(input_grid.flatten())
        output_colors = set(output_grid.flatten())
        features['input_color_count'] = len(input_colors)
        features['output_color_count'] = len(output_colors)
        features['color_count_bucket'] = self._color_bucket(len(input_colors))

        # Simple object count (non-zero regions)
        features['input_nonzero_count'] = np.sum(input_grid != 0)
        features['output_nonzero_count'] = np.sum(output_grid != 0)
        features['density_bucket'] = self._density_bucket(
            features['input_nonzero_count'] / (input_grid.shape[0] * input_grid.shape[1])
        )

        return features

    def _size_bucket(self, shape: Tuple[int, int]) -> str:
        """Bucket grid sizes"""
        h, w = shape
        if h <= 3 and w <= 3:
            return 'tiny'
        elif h <= 10 and w <= 10:
            return 'small'
        elif h <= 20 and w <= 20:
            return 'medium'
        else:
            return 'large'

    def _color_bucket(self, count: int) -> str:
        """Bucket color counts"""
        if count <= 2:
            return 'few'
        elif count <= 5:
            return 'some'
        else:
            return 'many'

    def _density_bucket(self, density: float) -> str:
        """Bucket grid density"""
        if density < 0.2:
            return 'sparse'
        elif density < 0.6:
            return 'medium'
        else:
            return 'dense'

    def compute_similarity(self, features1: Dict, features2: Dict) -> float:
        """
        Compute similarity score between two tasks (0-1)
        Higher = more similar
        """
        score = 0.0
        weight_sum = 0.0

        # Grid size similarity (weight: 3)
        if features1.get('grid_size_bucket') == features2.get('grid_size_bucket'):
            score += 3.0
        weight_sum += 3.0

        # Size change similarity (weight: 2)
        if features1.get('size_change') == features2.get('size_change'):
            score += 2.0
        weight_sum += 2.0

        # Color count similarity (weight: 2)
        if features1.get('color_count_bucket') == features2.get('color_count_bucket'):
            score += 2.0
        weight_sum += 2.0

        # Density similarity (weight: 1)
        if features1.get('density_bucket') == features2.get('density_bucket'):
            score += 1.0
        weight_sum += 1.0

        return score / weight_sum if weight_sum > 0 else 0.0

    def cluster_tasks(self, task_data: Dict[str, Dict], num_clusters: int = 10) -> Dict[int, List[str]]:
        """
        Cluster tasks by similarity

        Simple approach: K-means-like clustering based on feature similarity
        """
        # Extract features for all tasks
        task_ids = list(task_data.keys())
        for task_id in task_ids:
            self.task_features[task_id] = self.extract_task_features(task_data[task_id])

        # Initialize clusters with random seeds
        np.random.seed(42)
        cluster_seeds = np.random.choice(task_ids, min(num_clusters, len(task_ids)), replace=False)

        # Simple clustering: assign each task to most similar seed
        for task_id in task_ids:
            best_cluster = 0
            best_similarity = -1.0

            for cluster_id, seed_id in enumerate(cluster_seeds):
                sim = self.compute_similarity(
                    self.task_features[task_id],
                    self.task_features[seed_id]
                )

                if sim > best_similarity:
                    best_similarity = sim
                    best_cluster = cluster_id

            if best_cluster not in self.clusters:
                self.clusters[best_cluster] = []
            self.clusters[best_cluster].append(task_id)

        return self.clusters

    def add_attempt(self, task_id: str, pattern: List[str], success: bool, fitness: float = 0.0):
        """
        Record an attempted pattern for a task

        Args:
            task_id: Task identifier
            pattern: Sequence of primitives tried
            success: Whether it solved the task
            fitness: Fitness score (higher = better)
        """
        # Find cluster for this task
        cluster_id = self._get_cluster_id(task_id)
        if cluster_id is None:
            return

        # Record pattern
        self.cluster_patterns[cluster_id][task_id].append({
            'pattern': pattern,
            'success': success,
            'fitness': fitness
        })

        # Update primitive statistics
        if success:
            for primitive in pattern:
                self.cluster_primitives[cluster_id][primitive] += 1
                self.cluster_success_primitives[cluster_id].add(primitive)

    def _get_cluster_id(self, task_id: str) -> int:
        """Find which cluster a task belongs to"""
        for cluster_id, task_list in self.clusters.items():
            if task_id in task_list:
                return cluster_id
        return None

    def get_cluster_knowledge(self, task_id: str) -> Dict:
        """
        Get accumulated knowledge for a task's cluster

        Returns:
            - successful_patterns: Patterns that worked for similar tasks
            - attempted_patterns: All patterns tried (success + failures)
            - success_primitives: Primitives that led to solutions
            - primitive_frequencies: How often each primitive succeeded
        """
        cluster_id = self._get_cluster_id(task_id)
        if cluster_id is None:
            return {
                'successful_patterns': [],
                'attempted_patterns': [],
                'success_primitives': set(),
                'primitive_frequencies': Counter()
            }

        # Gather successful patterns from cluster
        successful_patterns = []
        attempted_patterns = []

        for other_task_id, attempts in self.cluster_patterns[cluster_id].items():
            # Don't include current task (that would be cheating)
            if other_task_id == task_id:
                continue

            for attempt in attempts:
                attempted_patterns.append(attempt['pattern'])
                if attempt['success']:
                    successful_patterns.append({
                        'pattern': attempt['pattern'],
                        'fitness': attempt['fitness'],
                        'task_id': other_task_id
                    })

        return {
            'successful_patterns': successful_patterns,
            'attempted_patterns': attempted_patterns,
            'success_primitives': self.cluster_success_primitives[cluster_id],
            'primitive_frequencies': self.cluster_primitives[cluster_id]
        }

    def seed_population_with_transfer(self, task_id: str, population_size: int,
                                     all_primitives: List[str], max_length: int = 5) -> List[List[str]]:
        """
        Seed population using transfer learning from similar tasks

        Strategy:
        - 15% exact copies of successful patterns from cluster
        - 15% variations of successful patterns
        - 40% biased random using cluster's successful primitives
        - 30% standard random (exploration)
        """
        population = []
        knowledge = self.get_cluster_knowledge(task_id)

        successful_patterns = knowledge['successful_patterns']
        success_prims = list(knowledge['success_primitives']) if knowledge['success_primitives'] else all_primitives

        # 1. Exact copies of successful patterns (15%)
        exact_count = int(population_size * 0.15)
        for _ in range(exact_count):
            if successful_patterns:
                # Weight by fitness
                weights = [p['fitness'] for p in successful_patterns]
                if sum(weights) > 0:
                    weights = np.array(weights) / sum(weights)
                else:
                    weights = None

                idx = np.random.choice(len(successful_patterns), p=weights)
                pattern = list(successful_patterns[idx]['pattern'])
                population.append(pattern)

        # 2. Variations of successful patterns (15%)
        variation_count = int(population_size * 0.15)
        for _ in range(variation_count):
            if successful_patterns:
                idx = np.random.randint(len(successful_patterns))
                pattern = list(successful_patterns[idx]['pattern'])

                # Mutate
                mutation = np.random.choice(['add', 'remove', 'replace', 'swap'])

                if mutation == 'add' and len(pattern) < max_length:
                    pattern.append(np.random.choice(success_prims if success_prims else all_primitives))
                elif mutation == 'remove' and len(pattern) > 1:
                    pattern.pop(np.random.randint(len(pattern)))
                elif mutation == 'replace' and pattern:
                    idx = np.random.randint(len(pattern))
                    pattern[idx] = np.random.choice(success_prims if success_prims else all_primitives)
                elif mutation == 'swap' and len(pattern) >= 2:
                    i, j = np.random.choice(len(pattern), 2, replace=False)
                    pattern[i], pattern[j] = pattern[j], pattern[i]

                population.append(pattern)

        # 3. Biased random using cluster primitives (40%)
        biased_count = int(population_size * 0.40)
        for _ in range(biased_count):
            length = np.random.randint(1, max_length + 1)

            # Use successful primitives with weighted sampling
            if success_prims and knowledge['primitive_frequencies']:
                # Weight by frequency
                prims = list(knowledge['primitive_frequencies'].keys())
                weights = [knowledge['primitive_frequencies'][p] for p in prims]
                weights = np.array(weights) / sum(weights)

                sequence = list(np.random.choice(prims, size=length, replace=True, p=weights))
            elif success_prims:
                sequence = [np.random.choice(success_prims) for _ in range(length)]
            else:
                sequence = [np.random.choice(all_primitives) for _ in range(length)]

            population.append(sequence)

        # 4. Standard random exploration (30%)
        remaining = population_size - len(population)
        for _ in range(remaining):
            length = np.random.randint(1, max_length + 1)
            sequence = [np.random.choice(all_primitives) for _ in range(length)]
            population.append(sequence)

        return population

    def save_state(self, filename: str):
        """Save transfer learner state"""
        data = {
            'clusters': self.clusters,
            'task_features': self.task_features,
            'cluster_patterns': {
                cluster_id: {
                    task_id: patterns
                    for task_id, patterns in tasks.items()
                }
                for cluster_id, tasks in self.cluster_patterns.items()
            },
            'cluster_primitives': {
                cluster_id: dict(counter)
                for cluster_id, counter in self.cluster_primitives.items()
            },
            'cluster_success_primitives': {
                cluster_id: list(prims)
                for cluster_id, prims in self.cluster_success_primitives.items()
            }
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

    def load_state(self, filename: str) -> bool:
        """Load transfer learner state"""
        if not os.path.exists(filename):
            return False

        with open(filename, 'r') as f:
            data = json.load(f)

        self.clusters = {int(k): v for k, v in data['clusters'].items()}
        self.task_features = data['task_features']

        # Reconstruct cluster_patterns
        for cluster_id, tasks in data['cluster_patterns'].items():
            for task_id, patterns in tasks.items():
                self.cluster_patterns[int(cluster_id)][task_id] = patterns

        # Reconstruct counters and sets
        for cluster_id, prims in data['cluster_primitives'].items():
            self.cluster_primitives[int(cluster_id)] = Counter(prims)

        for cluster_id, prims in data['cluster_success_primitives'].items():
            self.cluster_success_primitives[int(cluster_id)] = set(prims)

        return True

    def get_statistics(self) -> Dict:
        """Get transfer learning statistics"""
        stats = {
            'num_clusters': len(self.clusters),
            'cluster_sizes': {cid: len(tasks) for cid, tasks in self.clusters.items()},
            'total_tasks': len(self.task_features),
            'patterns_per_cluster': {
                cid: sum(len(patterns) for patterns in tasks.values())
                for cid, tasks in self.cluster_patterns.items()
            },
            'success_primitives_per_cluster': {
                cid: len(prims)
                for cid, prims in self.cluster_success_primitives.items()
            }
        }
        return stats


if __name__ == "__main__":
    print("="*70)
    print("🔄 ARC-AGI Transfer Learner v0.79")
    print("="*70)

    # Load ARC dataset - try multiple paths
    dataset_path = None
    for path in [Path("arc_data/ARC-AGI/data/training"),
                 Path("arc-agi/data/training"),
                 Path("ARC-AGI/data/training")]:
        if path.exists():
            dataset_path = path
            break

    if not dataset_path:
        print(f"❌ Dataset not found in any standard location")
        exit(1)

    print(f"\n📂 Loading tasks from: {dataset_path}")

    # Load all tasks
    task_data = {}
    for task_file in dataset_path.glob("*.json"):
        task_id = task_file.stem
        with open(task_file) as f:
            task_data[task_id] = json.load(f)

    print(f"✅ Loaded {len(task_data)} tasks")

    # Create transfer learner
    learner = ARCTransferLearner()

    # Cluster tasks
    print(f"\n🔬 Clustering tasks...")
    clusters = learner.cluster_tasks(task_data, num_clusters=10)

    print(f"\n✅ Created {len(clusters)} clusters:")
    for cluster_id, task_list in clusters.items():
        print(f"  Cluster {cluster_id}: {len(task_list)} tasks")

    # Show example cluster features
    if clusters:
        cluster_id = list(clusters.keys())[0]
        example_tasks = clusters[cluster_id][:3]
        print(f"\n📊 Example cluster {cluster_id} features:")
        for task_id in example_tasks:
            features = learner.task_features[task_id]
            print(f"\n  {task_id}:")
            print(f"    Size: {features.get('grid_size_bucket', 'unknown')}")
            print(f"    Colors: {features.get('color_count_bucket', 'unknown')}")
            print(f"    Density: {features.get('density_bucket', 'unknown')}")
            print(f"    Change: {features.get('size_change', 'unknown')}")

    # Save state
    output_file = "arc_transfer_learner_clusters.json"
    learner.save_state(output_file)
    print(f"\n💾 Saved cluster state to: {output_file}")

    # Test seeding
    print(f"\n🧪 Testing transfer-based seeding...")
    all_prims = ['rotate_90', 'flip_h', 'flip_v', 'checkerboard', 'scale_2x',
                 'downsample', 'fill_zeros', 'border', 'crop', 'scale_3x']

    if task_data:
        test_task = list(task_data.keys())[0]
        test_pop = learner.seed_population_with_transfer(test_task, 10, all_prims, max_length=3)

        print(f"\nSample seeded population for {test_task} (10 individuals):")
        for i, individual in enumerate(test_pop, 1):
            print(f"  {i}. {individual}")

    print(f"\n✅ Transfer learner ready!")
    print(f"📈 Expected improvement: 1.25% → 2.0-2.5%")
