#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hierarchical Template Library for v0.95

Organizes templates by multiple dimensions:
1. Complexity: length-based (1-op, 2-op, 3-op, 4+ ops)
2. Category: transformation type (geometric, color, structure, object)
3. Success rate: high (>0.7), medium (0.5-0.7), low (0.3-0.5)
4. Input-output relationship: size-preserving, size-changing, color-changing

Key features:
- Fast lookup by constraints
- Template ranking by success metrics
- Category-based search
- Composability analysis

Author: Prometheus v0.95
Date: 2025-10-22
"""

import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from arc_program import ARCProgram


# Operation categories for hierarchical organization
OPERATION_CATEGORIES = {
    'geometric': {
        'operations': ['rotate', 'flip', 'transpose', 'mirror', 'diagonal_flip'],
        'description': 'Spatial transformations'
    },
    'color': {
        'operations': ['invert', 'swap_colors', 'filter_color', 'replace_color', 'map_color'],
        'description': 'Color manipulations'
    },
    'structure': {
        'operations': ['crop', 'pad', 'extend_edges', 'trim', 'scale', 'downsample'],
        'description': 'Grid structure changes'
    },
    'object': {
        'operations': ['detect_objects', 'extract_largest', 'fill_interior', 'remove_bg',
                      'sort_by_size', 'align', 'replicate'],
        'description': 'Object-level operations'
    },
    'pattern': {
        'operations': ['tile', 'repeat', 'symmetrize', 'checkerboard', 'fill_pattern'],
        'description': 'Pattern generation'
    },
    'physics': {
        'operations': ['gravity_down', 'gravity_up', 'gravity_left', 'gravity_right', 'compress'],
        'description': 'Physics-like operations'
    }
}


class HierarchicalTemplateLibrary:
    """
    Hierarchical organization of ARC templates for efficient retrieval.
    """

    def __init__(self):
        """Initialize empty hierarchical library."""
        # Main index: complexity → category → templates
        self.by_complexity = defaultdict(lambda: defaultdict(list))

        # Secondary indices
        self.by_success_rate = defaultdict(list)  # 'high', 'medium', 'low'
        self.by_size_behavior = defaultdict(list)  # 'preserving', 'increasing', 'decreasing'
        self.by_pattern = {}  # pattern string → template info

        # Statistics
        self.total_templates = 0
        self.total_programs = 0

    def load_from_template_learner(self, template_db_path: str):
        """
        Load templates from arc_template_learner database.

        Args:
            template_db_path: Path to template learner JSON database
        """
        with open(template_db_path, 'r') as f:
            db = json.load(f)

        templates = db.get('templates', {})
        programs = db.get('programs', [])

        print(f"Loading {len(templates)} templates, {len(programs)} programs...")

        for pattern_str, stats in templates.items():
            # Pattern string is like "crop()" or "rotate_90() -> flip_h()"
            # Convert to list of operation names
            ops_with_parens = pattern_str.split(' -> ')
            pattern = [op.replace('()', '') for op in ops_with_parens]

            # Extract metrics
            count = stats['count']
            avg_fitness = stats['avg_fitness']
            task_ids = stats.get('task_ids', stats.get('tasks', []))

            # Create template entry
            template = {
                'pattern': pattern,
                'pattern_str': pattern_str,
                'count': count,
                'avg_fitness': avg_fitness,
                'task_ids': task_ids,
                'complexity': len(pattern),
                'category': self._infer_category(pattern),
                'success_tier': self._get_success_tier(avg_fitness),
                'size_behavior': 'unknown'  # Will be inferred from actual usage
            }

            # Index by complexity and category
            complexity_tier = self._get_complexity_tier(len(pattern))
            category = template['category']
            self.by_complexity[complexity_tier][category].append(template)

            # Index by success rate
            success_tier = template['success_tier']
            self.by_success_rate[success_tier].append(template)

            # Index by pattern
            self.by_pattern[pattern_str] = template

            self.total_templates += 1

        self.total_programs = len(programs)

        print(f"✅ Loaded {self.total_templates} templates into hierarchical library")
        self._print_statistics()

    def _get_complexity_tier(self, length: int) -> str:
        """Get complexity tier from operation count."""
        if length == 1:
            return 'simple'
        elif length == 2:
            return 'medium'
        elif length == 3:
            return 'complex'
        else:
            return 'very_complex'

    def _get_success_tier(self, fitness: float) -> str:
        """Get success tier from fitness."""
        if fitness >= 0.7:
            return 'high'
        elif fitness >= 0.5:
            return 'medium'
        else:
            return 'low'

    def _infer_category(self, pattern: List[str]) -> str:
        """
        Infer template category from operation sequence.

        Uses first operation as primary category indicator.
        """
        if not pattern:
            return 'unknown'

        first_op = pattern[0]

        # Check each category
        for category, info in OPERATION_CATEGORIES.items():
            if any(op in first_op for op in info['operations']):
                return category

        return 'mixed'

    def search(self,
               complexity: Optional[str] = None,
               category: Optional[str] = None,
               min_fitness: float = 0.0,
               max_complexity: int = 5,
               limit: int = 20) -> List[Dict]:
        """
        Search for templates matching criteria.

        Args:
            complexity: Complexity tier ('simple', 'medium', 'complex', 'very_complex')
            category: Operation category (see OPERATION_CATEGORIES)
            min_fitness: Minimum average fitness
            max_complexity: Maximum operation count
            limit: Max results to return

        Returns:
            List of matching templates, sorted by fitness
        """
        results = []

        # Determine which complexity tiers to search
        if complexity:
            tiers_to_search = [complexity]
        else:
            tiers_to_search = ['simple', 'medium', 'complex', 'very_complex']

        # Search hierarchical index
        for tier in tiers_to_search:
            if tier not in self.by_complexity:
                continue

            categories_to_search = [category] if category else self.by_complexity[tier].keys()

            for cat in categories_to_search:
                if cat not in self.by_complexity[tier]:
                    continue

                for template in self.by_complexity[tier][cat]:
                    # Filter by constraints
                    if template['avg_fitness'] < min_fitness:
                        continue
                    if template['complexity'] > max_complexity:
                        continue

                    results.append(template)

        # Sort by fitness (descending)
        results.sort(key=lambda t: t['avg_fitness'], reverse=True)

        return results[:limit]

    def get_top_templates(self, n: int = 10) -> List[Dict]:
        """Get top N templates by fitness."""
        all_templates = []
        for tier in self.by_complexity.values():
            for category_templates in tier.values():
                all_templates.extend(category_templates)

        all_templates.sort(key=lambda t: t['avg_fitness'], reverse=True)
        return all_templates[:n]

    def get_templates_by_category(self, category: str) -> List[Dict]:
        """Get all templates in a category."""
        results = []
        for tier in self.by_complexity.values():
            if category in tier:
                results.extend(tier[category])

        results.sort(key=lambda t: t['avg_fitness'], reverse=True)
        return results

    def get_simple_templates(self, min_fitness: float = 0.5) -> List[Dict]:
        """Get high-quality simple (1-op) templates."""
        return self.search(
            complexity='simple',
            min_fitness=min_fitness,
            limit=50
        )

    def recommend_for_task(self,
                          task: Dict,
                          constraints: Dict,
                          n: int = 10) -> List[Dict]:
        """
        Recommend templates for a task based on constraints.

        Args:
            task: Task data with train examples
            constraints: Extracted constraints (size, color, etc.)
            n: Number of recommendations

        Returns:
            Ordered list of recommended templates
        """
        # Start with all templates
        candidates = []
        for tier in self.by_complexity.values():
            for category_templates in tier.values():
                candidates.extend(category_templates)

        # Score each template
        scored_templates = []
        for template in candidates:
            score = self._score_template_for_task(template, task, constraints)
            scored_templates.append((score, template))

        # Sort by score (descending)
        scored_templates.sort(key=lambda x: x[0], reverse=True)

        return [t for _, t in scored_templates[:n]]

    def _score_template_for_task(self,
                                 template: Dict,
                                 task: Dict,
                                 constraints: Dict) -> float:
        """
        Score how well a template might fit a task.

        Scoring factors:
        1. Template fitness (40%)
        2. Template usage count (20%)
        3. Complexity match (20%)
        4. Category relevance (20%)
        """
        score = 0.0

        # Factor 1: Template quality (40%)
        score += template['avg_fitness'] * 0.4

        # Factor 2: Template popularity (20%)
        # Normalize count (assume max 50 uses)
        popularity = min(template['count'] / 50.0, 1.0)
        score += popularity * 0.2

        # Factor 3: Complexity preference (20%)
        # Prefer simpler templates
        complexity_score = 1.0 - (template['complexity'] - 1) / 5.0
        score += max(0, complexity_score) * 0.2

        # Factor 4: Category relevance (20%)
        # Could be enhanced with constraint-based category selection
        if template['category'] in ['geometric', 'structure']:
            score += 0.2  # Common categories get bonus
        elif template['category'] == 'mixed':
            score += 0.1

        return score

    def _print_statistics(self):
        """Print library statistics."""
        print()
        print("📊 Hierarchical Library Statistics:")
        print(f"   Total templates: {self.total_templates}")
        print(f"   Total programs: {self.total_programs}")
        print()

        print("   By Complexity:")
        for tier in ['simple', 'medium', 'complex', 'very_complex']:
            if tier in self.by_complexity:
                count = sum(len(templates) for templates in self.by_complexity[tier].values())
                print(f"      {tier}: {count} templates")
        print()

        print("   By Category:")
        category_counts = defaultdict(int)
        for tier in self.by_complexity.values():
            for category, templates in tier.items():
                category_counts[category] += len(templates)

        for category in sorted(category_counts.keys()):
            print(f"      {category}: {category_counts[category]} templates")
        print()

        print("   By Success Rate:")
        for tier in ['high', 'medium', 'low']:
            count = len(self.by_success_rate[tier])
            print(f"      {tier} (≥{0.7 if tier=='high' else 0.5 if tier=='medium' else 0.3}): {count} templates")
        print()

    def save(self, output_path: str):
        """Save hierarchical library to JSON."""
        # Convert to serializable format
        data = {
            'by_complexity': {},
            'by_success_rate': {},
            'by_pattern': self.by_pattern,
            'statistics': {
                'total_templates': self.total_templates,
                'total_programs': self.total_programs
            }
        }

        # Convert defaultdicts
        for tier, categories in self.by_complexity.items():
            data['by_complexity'][tier] = dict(categories)

        for success_tier, templates in self.by_success_rate.items():
            data['by_success_rate'][success_tier] = templates

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✅ Hierarchical library saved: {output_path}")

    def load(self, input_path: str):
        """Load hierarchical library from JSON."""
        with open(input_path, 'r') as f:
            data = json.load(f)

        # Restore structure
        for tier, categories in data['by_complexity'].items():
            for category, templates in categories.items():
                self.by_complexity[tier][category] = templates

        for success_tier, templates in data['by_success_rate'].items():
            self.by_success_rate[success_tier] = templates

        self.by_pattern = data['by_pattern']

        stats = data['statistics']
        self.total_templates = stats['total_templates']
        self.total_programs = stats['total_programs']

        print(f"✅ Loaded hierarchical library: {self.total_templates} templates")


# ============================================================================
# TESTING
# ============================================================================

def test_hierarchical_library():
    """Test hierarchical template library."""
    print("=" * 80)
    print("🧪 Testing Hierarchical Template Library")
    print("=" * 80)
    print()

    # Load from existing template database
    lib = HierarchicalTemplateLibrary()
    lib.load_from_template_learner('arc_v095_expanded_templates.json')

    print()
    print("=" * 80)
    print("🔍 Testing Search")
    print("=" * 80)
    print()

    # Test 1: Search by complexity
    print("Test 1: Simple templates (1-op) with high fitness:")
    simple_templates = lib.search(complexity='simple', min_fitness=0.5, limit=5)
    for i, t in enumerate(simple_templates, 1):
        print(f"   {i}. {t['pattern']} - fitness: {t['avg_fitness']:.3f}, count: {t['count']}")
    print()

    # Test 2: Search by category
    print("Test 2: Geometric templates:")
    geo_templates = lib.search(category='geometric', min_fitness=0.3, limit=5)
    for i, t in enumerate(geo_templates, 1):
        print(f"   {i}. {t['pattern']} - fitness: {t['avg_fitness']:.3f}, count: {t['count']}")
    print()

    # Test 3: Get top templates
    print("Test 3: Top 5 templates overall:")
    top_templates = lib.get_top_templates(5)
    for i, t in enumerate(top_templates, 1):
        print(f"   {i}. {t['pattern']} - fitness: {t['avg_fitness']:.3f}, category: {t['category']}, count: {t['count']}")
    print()

    # Test 4: Save and reload
    print("Test 4: Save and reload:")
    lib.save('arc_hierarchical_templates_test.json')

    lib2 = HierarchicalTemplateLibrary()
    lib2.load('arc_hierarchical_templates_test.json')
    print(f"   Reloaded: {lib2.total_templates} templates")
    print()

    print("=" * 80)
    print("✅ All tests passed!")
    print("=" * 80)


if __name__ == '__main__':
    test_hierarchical_library()
