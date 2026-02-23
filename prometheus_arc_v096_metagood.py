#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus ARC v0.96: Meta-Goodian Synthesis + Hierarchical Expansion + LLM

Implements I.J. Good's "Probabilistic Synaptic Mutation" (1965) within the 
ARC-AGI program synthesis pipeline.

Key Innovations:
- Contextual MetaLearner: Adapts operation weights per constraint pattern.
- Hierarchical Template Expansion: Organized library for fast retrieval.
- LLM-Guided Search: Gemini suggestions seed the search space.
- RSI Loop: The system becomes "ultraintelligent" by refining its search priors.

Author: Prometheus v0.96
Date: 2025-10-24
"""

import os
import json
import time
import argparse
import random
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import numpy as np

# Import v0.95 as baseline
from prometheus_arc_v095_synthesis import PrometheusARC_v095_Synthesis

# Import MetaLearner from the prometheus package
from prometheus.meta_learner import MetaLearner

# Import ARC components
from arc_program import ARCProgram
from arc_parametric_operations import PARAMETRIC_OPERATIONS, build_operation_map
from arc_program_synthesizer import ProgramSynthesizer

# v0.96 Enhanced Components
from arc_hierarchical_templates import HierarchicalTemplateLibrary
from arc_llm_analyzer_v096 import GeminiTaskAnalyzerV096


class PrometheusARC_v096_MetaGood(PrometheusARC_v095_Synthesis):
    """
    v0.96: ARC Solver with I.J. Good's Meta-Learning.
    
    Integrates MetaLearner, Hierarchical Templates, and LLM-guided suggestions.
    """

    def __init__(self,
                 template_db_path: str = 'arc_templates_v095.json',
                 param_db_path: str = 'arc_params_v095.json',
                 metagood_db_path: str = 'arc_metagood_v096.json',
                 hierarchical_db_path: str = 'arc_hierarchical_templates_v096.json',
                 use_llm: bool = False,
                 beam_width: int = 50,
                 max_depth: int = 5,
                 max_synthesis_time: int = 30):
        """Initialize v0.96 with Meta-Goodian learning and hierarchical expansion."""
        super().__init__(
            template_db_path=template_db_path,
            param_db_path=param_db_path,
            use_llm=use_llm,
            beam_width=beam_width,
            max_depth=max_depth,
            max_synthesis_time=max_synthesis_time
        )
        
        self.metagood_db_path = metagood_db_path
        self.all_ops = list(PARAMETRIC_OPERATIONS.keys())
        
        # 1. Meta-Learning (I.J. Good)
        self.contextual_learners = {}
        self.global_learner = MetaLearner(strategies=self.all_ops)
        self._load_metagood_database()
        
        # 2. Hierarchical Template Library
        self.hierarchical_lib = HierarchicalTemplateLibrary()
        if os.path.exists(hierarchical_db_path):
            self.hierarchical_lib.load(hierarchical_db_path)
            print(f"  [v0.96] Loaded {self.hierarchical_lib.total_templates} hierarchical templates")
        
        # 3. LLM Task Analyzer
        self.llm_analyzer = None
        if use_llm:
            try:
                self.llm_analyzer = GeminiTaskAnalyzerV096()
                print(f"  [v0.96] LLM Analyzer initialized")
            except Exception as e:
                print(f"  [v0.96] LLM Analyzer init failed: {e}")

    def solve_task(self,
                   train_examples: List[Dict],
                   test_examples: List[Dict],
                   task_id: str) -> Dict:
        """
        Solve task using Meta-Goodian search + Hierarchical Templates + LLM.
        """
        print(f"\n[v0.96] Solving task {task_id}")
        start_time = time.time()
        
        # Step 1: Constraints
        constraints = self._extract_simple_constraints(train_examples)
        print(f"  [Constraints] {constraints}")
        
        # Step 2: Hierarchical Template Transfer (v0.96 Expansion)
        print(f"  [v0.96] Attempting hierarchical template transfer...")
        recommended_templates = self.hierarchical_lib.recommend_for_task(
            {'train': train_examples}, constraints, n=15
        )
        
        result = None
        method_used = None
        
        # Try hierarchical templates
        for template_info in recommended_templates:
            ops = template_info['pattern']
            program = ARCProgram([(op, {}) for op in ops])
            fitness = self._evaluate_program(program, train_examples)
            
            if fitness >= 0.95:
                print(f"  [v0.96 Hierarchical] ✅ Solved via template! ({template_info['pattern_str']})")
                result = self._build_result(program, fitness, train_examples, test_examples)
                method_used = 'hierarchical_transfer'
                break
        
        # Step 3: LLM Suggestions (if available)
        if result is None and self.llm_analyzer:
            print(f"  [v0.96] Consulting LLM for suggestions...")
            llm_analysis = self.llm_analyzer.analyze_task(task_id, train_examples)
            if llm_analysis.suggested_program:
                print(f"  [v0.96 LLM] Suggestion: {llm_analysis.suggested_program}")
                program = ARCProgram(llm_analysis.suggested_program)
                fitness = self._evaluate_program(program, train_examples)
                if fitness >= 0.95:
                    print(f"  [v0.96 LLM] ✅ Solved via LLM suggestion!")
                    result = self._build_result(program, fitness, train_examples, test_examples)
                    method_used = 'llm_guided'
        
        # Step 4: Beam Search with Meta-Goodian Biasing
        if result is None and (time.time() - start_time) < self.max_synthesis_time:
            print(f"  [v0.96] Trying Meta-Goodian beam search...")
            biased_ops = self._get_biased_operations(constraints)
            
            try:
                program = self.synthesizer.synthesize(
                    task={'train': train_examples, 'test': test_examples},
                    constraints=constraints,
                    biased_operations=biased_ops
                )
                fitness = self._evaluate_program(program, train_examples)
                
                if fitness >= 0.95:
                    print(f"  [v0.96 Beam] ✅ Solved via synthesis! (fitness={fitness:.3f})")
                    result = self._build_result(program, fitness, train_examples, test_examples)
                    method_used = 'meta_beam_search'
            except Exception as e:
                print(f"  [v0.96 Beam] Error: {e}")
        
        # Step 5: v0.92 Fallback (FAST)
        if result is None:
            print(f"  [v0.96] Synthesis failed, falling back to v0.92 baseline...")
            v092_result = super(PrometheusARC_v095_Synthesis, self).solve_task(train_examples, test_examples, task_id)
            result = v092_result
            method_used = 'v092_fallback'
            
        # Step 6: Learning (I.J. Good Synaptic Mutation)
        self._perform_synaptic_mutation(result, constraints, method_used)
        
        # Add metadata
        result['v096_method'] = method_used
        result['total_time'] = time.time() - start_time
        
        # Periodic Save
        if random.random() < 0.2: # 20% chance to save after each task
            self._save_metagood_database()
            
        return result

    def _perform_synaptic_mutation(self, result: Dict, constraints: Dict, method_used: str):
        """Perform upward/downward mutation based on result."""
        constraint_hash = self._hash_constraints(constraints)
        if constraint_hash not in self.contextual_learners:
            self.contextual_learners[constraint_hash] = MetaLearner(self.all_ops)
        
        ctx_learner = self.contextual_learners[constraint_hash]
        fitness = result.get('fitness', 0.0)
        
        if fitness >= 0.95:
            # UPWARD MUTATION for used operations
            ops_used = []
            if 'program' in result and result['program']:
                ops_used = [op[0] for op in result['program'].get('operations', [])]
            elif 'pattern' in result:
                ops_used = result['pattern']
            
            for op in set(ops_used):
                if op in self.all_ops:
                    print(f"  [v0.96] Upward mutation: {op}")
                    ctx_learner.update_on_success(op)
                    self.global_learner.update_on_success(op)
        elif method_used in ['meta_beam_search', 'v092_fallback']:
            # DOWNWARD MUTATION for top priors that failed
            top_priors = self._get_biased_operations(constraints)[:3]
            for op in top_priors:
                print(f"  [v0.96] Downward mutation: {op}")
                ctx_learner.update_on_failure(op)

    def _get_biased_operations(self, constraints: Dict[str, str]) -> List[str]:
        """Get operations sorted by contextual + global MetaLearner probabilities."""
        constraint_hash = self._hash_constraints(constraints)
        if constraint_hash not in self.contextual_learners:
            self.contextual_learners[constraint_hash] = MetaLearner(self.all_ops)
            
        ctx_probs = self.contextual_learners[constraint_hash].get_strategy_probabilities()
        global_probs = self.global_learner.get_strategy_probabilities()
        
        combined = {op: (ctx_probs[op] * 0.7) + (global_probs[op] * 0.3) for op in self.all_ops}
        return sorted(combined.keys(), key=lambda x: combined[x], reverse=True)

    def _hash_constraints(self, constraints: Dict[str, str]) -> str:
        return "|".join([f"{k}:{v}" for k, v in sorted(constraints.items())])

    def _load_metagood_database(self):
        if os.path.exists(self.metagood_db_path):
            with open(self.metagood_db_path, 'r') as f:
                data = json.load(f)
            self.global_learner.probabilities = data.get('global', self.global_learner.probabilities)
            for h, probs in data.get('contextual', {}).items():
                l = MetaLearner(self.all_ops)
                l.probabilities = probs
                self.contextual_learners[h] = l

    def _save_metagood_database(self):
        data = {
            'global': self.global_learner.get_strategy_probabilities(),
            'contextual': {h: l.get_strategy_probabilities() for h, l in self.contextual_learners.items()}
        }
        with open(self.metagood_db_path, 'w') as f:
            json.dump(data, f, indent=2)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--num-tasks', type=int, default=5)
    parser.add_argument('--use-llm', action='store_true')
    args = parser.parse_args()
    
    solver = PrometheusARC_v096_MetaGood(use_llm=args.use_llm)
    print(f"v0.96 Meta-Goodian Solver initialized. Ready for ARC-AGI Breakthrough.")
