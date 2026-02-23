#!/usr/bin/env python3
"""
Analyze ARC-AGI failures to identify missing primitive patterns.
Implements Option C (Strategic Primitive Expansion) and Option E (Deep Failure Analysis).
"""

import json
import numpy as np
import random
from pathlib import Path
from typing import List, Tuple, Dict
from dataclasses import dataclass
from collections import Counter

@dataclass
class FailurePattern:
    """Pattern identified in failed tasks"""
    task_id: str
    pattern_type: str
    description: str
    required_operations: List[str]
    complexity: int

@dataclass
class PrimitiveSpec:
    """Specification for a new primitive operation"""
    name: str
    description: str
    rationale: str
    implementation_notes: str

class ARCFailureAnalyzer:
    def __init__(self, data_dir: str = "arc_agi_official/data"):
        self.data_dir = Path(data_dir)
        self.training_dir = self.data_dir / "training"

    def load_task(self, task_id: str) -> dict:
        """Load a task by ID"""
        task_file = self.training_dir / f"{task_id}.json"
        with open(task_file, 'r') as f:
            return json.load(f)

    def analyze_task_patterns(self, task: dict) -> Dict[str, any]:
        """Analyze patterns in a task"""
        train_pairs = task['train']

        features = {
            'grid_transformations': [],
            'size_changes': [],
            'color_operations': [],
            'object_operations': [],
            'repetition_patterns': [],
            'spatial_relationships': []
        }

        for pair in train_pairs:
            input_grid = np.array(pair['input'])
            output_grid = np.array(pair['output'])

            # Size change analysis
            in_shape = input_grid.shape
            out_shape = output_grid.shape
            if in_shape != out_shape:
                ratio = (out_shape[0] / in_shape[0], out_shape[1] / in_shape[1])
                features['size_changes'].append(ratio)

            # Color analysis
            in_colors = set(np.unique(input_grid))
            out_colors = set(np.unique(output_grid))
            if in_colors != out_colors:
                features['color_operations'].append({
                    'new_colors': out_colors - in_colors,
                    'removed_colors': in_colors - out_colors
                })

            # Repetition detection
            if output_grid.shape[0] > input_grid.shape[0]:
                if output_grid.shape[0] % input_grid.shape[0] == 0:
                    features['repetition_patterns'].append('vertical_tiling')
            if output_grid.shape[1] > input_grid.shape[1]:
                if output_grid.shape[1] % input_grid.shape[1] == 0:
                    features['repetition_patterns'].append('horizontal_tiling')

        return features

    def sample_and_analyze_failures(self, failed_task_ids: List[str], n_samples: int = 50) -> List[FailurePattern]:
        """Sample and analyze failed tasks"""
        sampled_ids = random.sample(failed_task_ids, min(n_samples, len(failed_task_ids)))

        patterns = []
        pattern_types = Counter()

        print(f"\n🔍 Analyzing {len(sampled_ids)} failed tasks...")

        for i, task_id in enumerate(sampled_ids):
            if (i + 1) % 10 == 0:
                print(f"   Analyzed {i+1}/{len(sampled_ids)} tasks...")

            try:
                task = self.load_task(task_id)
                features = self.analyze_task_patterns(task)

                # Classify pattern type
                pattern_type = self.classify_pattern_type(features)
                pattern_types[pattern_type] += 1

                # Identify required operations
                required_ops = self.identify_required_operations(features, pattern_type)

                patterns.append(FailurePattern(
                    task_id=task_id,
                    pattern_type=pattern_type,
                    description=self.describe_pattern(features),
                    required_operations=required_ops,
                    complexity=self.estimate_complexity(features)
                ))
            except Exception as e:
                print(f"   Warning: Could not analyze {task_id}: {e}")

        print(f"\n📊 Pattern Distribution:")
        for pattern_type, count in pattern_types.most_common():
            print(f"   {pattern_type}: {count} tasks ({count/len(sampled_ids)*100:.1f}%)")

        return patterns

    def classify_pattern_type(self, features: Dict) -> str:
        """Classify the type of pattern"""
        if features['repetition_patterns']:
            return 'REPETITION_TILING'
        if features['size_changes'] and any(r != (1.0, 1.0) for r in features['size_changes']):
            return 'SIZE_TRANSFORMATION'
        if features['color_operations']:
            return 'COLOR_MAPPING'
        return 'SPATIAL_TRANSFORMATION'

    def identify_required_operations(self, features: Dict, pattern_type: str) -> List[str]:
        """Identify what operations would solve this pattern"""
        ops = []

        if pattern_type == 'REPETITION_TILING':
            ops.extend(['tile_pattern', 'grow_by_rule', 'replicate_object'])
        elif pattern_type == 'SIZE_TRANSFORMATION':
            ops.extend(['scale_by_factor', 'expand_grid', 'contract_grid'])
        elif pattern_type == 'COLOR_MAPPING':
            ops.extend(['color_arithmetic', 'color_by_rule', 'map_colors'])
        else:
            ops.extend(['spatial_transform', 'pattern_extraction'])

        return ops

    def describe_pattern(self, features: Dict) -> str:
        """Generate human-readable description"""
        desc_parts = []

        if features['size_changes']:
            desc_parts.append(f"Size changes: {features['size_changes'][0]}")
        if features['color_operations']:
            desc_parts.append("Color transformations present")
        if features['repetition_patterns']:
            desc_parts.append(f"Repetition: {features['repetition_patterns'][0]}")

        return "; ".join(desc_parts) if desc_parts else "Complex spatial transformation"

    def estimate_complexity(self, features: Dict) -> int:
        """Estimate pattern complexity (1-5)"""
        complexity = 1

        if features['size_changes']:
            complexity += 1
        if features['color_operations']:
            complexity += 1
        if features['repetition_patterns']:
            complexity += 1
        if len(features['object_operations']) > 2:
            complexity += 1

        return min(complexity, 5)

    def design_new_primitives(self, patterns: List[FailurePattern]) -> List[PrimitiveSpec]:
        """Design new primitives based on failure analysis"""
        print(f"\n🔧 Designing New Primitives Based on Failures...")

        # Count required operations
        op_counter = Counter()
        for pattern in patterns:
            for op in pattern.required_operations:
                op_counter[op] += 1

        print(f"\n📋 Most Needed Operations:")
        for op, count in op_counter.most_common(10):
            print(f"   {op}: {count} tasks")

        # Design primitives
        primitives = []

        # Category 1: Repetition/Tiling (most common in ARC)
        primitives.append(PrimitiveSpec(
            name="tile_nx_ny",
            description="Tile input grid N times horizontally and M times vertically",
            rationale="Many ARC tasks involve exact repetition of patterns",
            implementation_notes="Create output grid of size (h*N, w*M), copy input to each tile"
        ))

        primitives.append(PrimitiveSpec(
            name="grow_by_rule",
            description="Grow pattern outward following a rule (diagonal, plus-sign, etc)",
            rationale="Tasks where small patterns expand following geometric rules",
            implementation_notes="Detect pattern, apply growth rule iteratively"
        ))

        # Category 2: Color arithmetic
        primitives.append(PrimitiveSpec(
            name="color_add",
            description="Add offset to all non-zero colors (mod 10)",
            rationale="Tasks with color cycling or arithmetic",
            implementation_notes="grid[grid > 0] = ((grid[grid > 0] + offset - 1) % 9) + 1"
        ))

        primitives.append(PrimitiveSpec(
            name="color_multiply",
            description="Multiply non-zero colors by factor (mod 10)",
            rationale="Color transformations with multiplicative patterns",
            implementation_notes="grid[grid > 0] = ((grid[grid > 0] * factor - 1) % 9) + 1"
        ))

        primitives.append(PrimitiveSpec(
            name="color_by_position",
            description="Set color based on grid position (row+col, row*col, etc)",
            rationale="Tasks where output color depends on spatial position",
            implementation_notes="Use row/column indices to compute color values"
        ))

        # Category 3: Grid folding/unfolding
        primitives.append(PrimitiveSpec(
            name="fold_quarters",
            description="Fold grid into quarters (overlay 4 quadrants)",
            rationale="Tasks requiring spatial compression via overlaying",
            implementation_notes="Split grid into 4 parts, overlay them with OR/MAX operation"
        ))

        primitives.append(PrimitiveSpec(
            name="unfold_pattern",
            description="Take small pattern and unfold it into larger grid",
            rationale="Opposite of compression - expansion from seed pattern",
            implementation_notes="Detect central pattern, expand outward with symmetry rules"
        ))

        # Category 4: Pattern extraction and replication
        primitives.append(PrimitiveSpec(
            name="extract_repeating_pattern",
            description="Detect and extract the repeating unit from a tiled pattern",
            rationale="Many tasks involve finding the minimal repeating unit",
            implementation_notes="Try different tile sizes, find minimal unit that tiles perfectly"
        ))

        primitives.append(PrimitiveSpec(
            name="replicate_to_size",
            description="Replicate pattern to fill target size",
            rationale="Scale pattern by integer tiling to match output size",
            implementation_notes="Repeat pattern N times to fill specified dimensions"
        ))

        # Category 5: Advanced diagonal operations
        primitives.append(PrimitiveSpec(
            name="diagonal_shift",
            description="Shift each row by its row index (creates diagonal effect)",
            rationale="Diagonal shearing transformations",
            implementation_notes="new_grid[r] = np.roll(grid[r], r)"
        ))

        primitives.append(PrimitiveSpec(
            name="antidiagonal_mirror",
            description="Mirror along anti-diagonal (bottom-left to top-right)",
            rationale="Less common symmetry not covered by existing primitives",
            implementation_notes="Flip then transpose (or transpose then flip)"
        ))

        # Category 6: Object-based operations
        primitives.append(PrimitiveSpec(
            name="connect_nearest",
            description="Connect each object to its nearest neighbor",
            rationale="Tasks involving path creation between objects",
            implementation_notes="Find centroids, draw lines between nearest pairs"
        ))

        primitives.append(PrimitiveSpec(
            name="object_to_border",
            description="Extend each object to the nearest border",
            rationale="Tasks where objects project to edges",
            implementation_notes="Detect objects, draw lines from centroid to edges"
        ))

        # Category 7: Masking and filtering
        primitives.append(PrimitiveSpec(
            name="mask_by_color",
            description="Keep only cells matching specific color(s)",
            rationale="Selective filtering based on color",
            implementation_notes="Set all non-matching colors to 0"
        ))

        primitives.append(PrimitiveSpec(
            name="invert_mask",
            description="Swap foreground/background (0 ↔ non-zero)",
            rationale="Figure-ground reversal tasks",
            implementation_notes="temp = (grid == 0); grid[temp] = 1; grid[~temp] = 0"
        ))

        # Category 8: Grid arithmetic
        primitives.append(PrimitiveSpec(
            name="overlay_with_max",
            description="Overlay multiple grids, take maximum color at each position",
            rationale="Combining multiple patterns",
            implementation_notes="np.maximum across grid stack"
        ))

        primitives.append(PrimitiveSpec(
            name="xor_grids",
            description="XOR operation on two grid patterns",
            rationale="Set difference operations",
            implementation_notes="(grid1 > 0) ^ (grid2 > 0)"
        ))

        print(f"\n✅ Designed {len(primitives)} New Primitives")
        for i, prim in enumerate(primitives, 1):
            print(f"   {i}. {prim.name}: {prim.description}")

        return primitives

def main():
    print("=" * 80)
    print("🔬 ARC-AGI Failure Analysis - Options C & E")
    print("=" * 80)

    # Load results from 500-generation run
    print("\n📂 Loading training results...")
    with open('arc_evolution_results/evolution_training_results.json', 'r') as f:
        results = json.load(f)

    # Extract failed task IDs
    failed_ids = []
    solved_ids = []
    for result in results['results']:
        if result.get('fitness', 0) >= 0.99:  # Consider solved if fitness >= 0.99
            solved_ids.append(result['task_id'])
        else:
            failed_ids.append(result['task_id'])

    print(f"   Solved: {len(solved_ids)}/400 ({len(solved_ids)/400*100:.1f}%)")
    print(f"   Failed: {len(failed_ids)}/400 ({len(failed_ids)/400*100:.1f}%)")

    # Option C: Sample and analyze 50 failed tasks
    print(f"\n{'='*80}")
    print("📊 OPTION C: Strategic Primitive Expansion")
    print("="*80)

    analyzer = ARCFailureAnalyzer()
    patterns = analyzer.sample_and_analyze_failures(failed_ids, n_samples=50)

    # Option E: Design comprehensive primitive library
    print(f"\n{'='*80}")
    print("🎯 OPTION E: Deep Failure Analysis - Primitive Design")
    print("="*80)

    new_primitives = analyzer.design_new_primitives(patterns)

    # Save analysis
    analysis_output = {
        'failed_count': len(failed_ids),
        'sampled_count': len(patterns),
        'patterns': [
            {
                'task_id': p.task_id,
                'type': p.pattern_type,
                'description': p.description,
                'required_ops': p.required_operations,
                'complexity': p.complexity
            }
            for p in patterns
        ],
        'new_primitives': [
            {
                'name': p.name,
                'description': p.description,
                'rationale': p.rationale,
                'implementation': p.implementation_notes
            }
            for p in new_primitives
        ]
    }

    output_file = 'arc_failure_analysis.json'
    with open(output_file, 'w') as f:
        json.dump(analysis_output, f, indent=2)

    print(f"\n💾 Analysis saved to: {output_file}")

    print(f"\n{'='*80}")
    print("📈 SUMMARY")
    print("="*80)
    print(f"   Failed tasks analyzed: {len(patterns)}")
    print(f"   New primitives designed: {len(new_primitives)}")
    print(f"   Current primitive count: 38")
    print(f"   Target primitive count: {38 + len(new_primitives)} ({38 + len(new_primitives)})")
    print(f"\n   Expected improvement:")
    print(f"      Current: 30/400 (7.5%)")
    print(f"      Target: 40-50/400 (10-12.5%)")
    print(f"      Next step: Implement primitives in prometheus_arc_evolution.py")

if __name__ == "__main__":
    main()
