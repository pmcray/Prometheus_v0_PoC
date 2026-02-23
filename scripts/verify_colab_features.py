#!/usr/bin/env python3
"""
Verify Prometheus New Features (v0.96+)

Automated test suite for:
1. ARC v0.96 Meta-Goodian Synthesis
2. Go MCTS Implementation
3. RSI Control Loop (CRLS)
4. Safety & Causal Calculus
"""

import sys
import os
import numpy as np
import logging

# Add project root to path
sys.path.insert(0, os.getcwd())

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_arc_v096():
    print("\n--- [1/4] Testing ARC v0.96 Meta-Goodian ---")
    try:
        from prometheus_arc_v096_metagood import PrometheusARC_v096_MetaGood
        solver = PrometheusARC_v096_MetaGood()
        print("✅ ARC v0.96 Solver initialized successfully.")
        
        # Test meta-biasing
        constraints = {'size': 'fixed', 'color': 'simple'}
        biased_ops = solver._get_biased_operations(constraints)
        print(f"✅ Meta-biasing works. Top op: {biased_ops[0]}")
        return True
    except Exception as e:
        print(f"❌ ARC v0.96 Test Failed: {e}")
        return False

def test_go_mcts():
    print("\n--- [2/4] Testing Go MCTS ---")
    try:
        from prometheus.models.go_models import RandomGoAgent
        from prometheus.models.go_mcts import GoMCTSAgent
        from prometheus.environments.go import GoBoard
        
        base_agent = RandomGoAgent(board_size=9)
        mcts_agent = GoMCTSAgent(base_agent, num_simulations=10)
        board = GoBoard(size=9)
        
        move = mcts_agent.get_move_from_board(board)
        print(f"✅ Go MCTS Move Decision: {move}")
        return True
    except Exception as e:
        print(f"❌ Go MCTS Test Failed: {e}")
        return False

def test_rsi_loop():
    print("\n--- [3/4] Testing RSI Control Loop ---")
    try:
        from prometheus.rsi_control import RSIController, RSIMetrics
        from freeciv_simulator import FreeCivGame
        from prometheus.recursive_font import create_connect4_recursive_strategy
        
        env = FreeCivGame()
        agent = create_connect4_recursive_strategy() # Using compatible strategy object
        controller = RSIController(agent=agent, env=env)
        
        metrics = controller.run_cycle(num_trials=1)
        print(f"✅ RSI Cycle completed. Generation: {metrics.generation}")
        return True
    except Exception as e:
        print(f"❌ RSI Loop Test Failed: {e}")
        return False

def test_causal_safety():
    print("\n--- [4/4] Testing Causal & Safety ---")
    try:
        from causal_attention_enhanced import WeightOfEvidenceCalculus
        from prometheus.safety.learned_safety import AdvancedSafetyGovernor
        
        calc = WeightOfEvidenceCalculus()
        k_e_f = calc.calculate_k_e_f('nested_loops', 'quadratic_complexity')
        print(f"✅ Causal Support K(E:F): {k_e_f:.3f}")
        
        gov = AdvancedSafetyGovernor()
        status, reason = gov.evaluate_modification({'type': 'learning_rate', 'old_lr': 0.001, 'new_lr': 0.002})
        print(f"✅ Safety Governor check: {status.value}")
        return True
    except Exception as e:
        print(f"❌ Causal/Safety Test Failed: {e}")
        return False

def main():
    print("=" * 70)
    print("🌟 PROMETHEUS FEATURE VERIFICATION SUITE")
    print("=" * 70)
    
    results = [
        test_arc_v096(),
        test_go_mcts(),
        test_rsi_loop(),
        test_causal_safety()
    ]
    
    print("\n" + "=" * 70)
    if all(results):
        print("🎉 ALL FEATURES VERIFIED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("⚠️  SOME FEATURES FAILED VERIFICATION.")
        sys.exit(1)

if __name__ == "__main__":
    main()
