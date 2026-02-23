#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Populate Hierarchical Template Library with Fundamental ARC Patterns.

This script manually seeds the hierarchical library with successful patterns
from ARC-AGI research, categorized by complexity and type.
"""

import json
from arc_hierarchical_templates import HierarchicalTemplateLibrary
from arc_program import ARCProgram

def populate_library():
    # Initialize library
    lib = HierarchicalTemplateLibrary()
    
    # Define common successful ARC patterns
    # Format: (ops_list, avg_fitness, count)
    seed_patterns = [
        # --- Simple (1-op) ---
        (['crop'], 0.65, 45),
        (['rotate'], 0.55, 30),
        (['flip'], 0.58, 28),
        (['transpose'], 0.60, 20),
        (['filter_color'], 0.52, 25),
        (['scale'], 0.48, 15),
        (['tile'], 0.50, 18),
        (['pad'], 0.45, 12),
        
        # --- Medium (2-ops) ---
        (['crop', 'rotate'], 0.58, 12),
        (['crop', 'flip'], 0.56, 10),
        (['crop', 'filter_color'], 0.62, 15),
        (['scale', 'tile'], 0.42, 8),
        (['filter_color', 'rotate'], 0.45, 7),
        (['rotate', 'flip'], 0.48, 9),
        (['transpose', 'flip'], 0.52, 11),
        (['crop', 'pad'], 0.40, 6),
        
        # --- Complex (3+ ops) ---
        (['crop', 'filter_color', 'rotate'], 0.54, 5),
        (['crop', 'rotate', 'flip'], 0.51, 4),
        (['filter_color', 'scale', 'tile'], 0.47, 3),
        (['crop', 'transpose', 'flip'], 0.55, 6),
    ]
    
    print(f"Seeding {len(seed_patterns)} patterns into hierarchical library...")
    
    for ops, fitness, count in seed_patterns:
        # Create a program with default params for template extraction
        program = ARCProgram([(op, {}) for op in ops])
        pattern_str = " -> ".join([f"{op}()" for op in ops])
        
        # Manually construct template info
        complexity_tier = lib._get_complexity_tier(len(ops))
        category = lib._infer_category(ops)
        success_tier = lib._get_success_tier(fitness)
        
        template = {
            'pattern': ops,
            'pattern_str': pattern_str,
            'count': count,
            'avg_fitness': fitness,
            'task_ids': [f"seed_{i}" for i in range(count)],
            'complexity': len(ops),
            'category': category,
            'success_tier': success_tier,
            'size_behavior': 'unknown'
        }
        
        # Index in library
        lib.by_complexity[complexity_tier][category].append(template)
        lib.by_success_rate[success_tier].append(template)
        lib.by_pattern[pattern_str] = template
        lib.total_templates += 1
        lib.total_programs += count

    # Save to disk
    output_path = 'arc_hierarchical_templates_v096.json'
    lib.save(output_path)
    
    # Also save a standard template database for compatibility
    compat_data = {
        'templates': {
            t['pattern_str']: {
                'count': t['count'],
                'avg_fitness': t['avg_fitness'],
                'tasks': t['task_ids']
            }
            for t in lib.by_pattern.values()
        },
        'successful_programs': [],
        'stats': {
            'total_templates': lib.total_templates,
            'total_successes': lib.total_programs
        }
    }
    
    with open('arc_templates_v095.json', 'w') as f:
        json.dump(compat_data, f, indent=2)
    
    print(f"Successfully seeded hierarchical library and compatible database.")

if __name__ == '__main__':
    populate_library()
