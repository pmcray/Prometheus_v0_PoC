#!/usr/bin/env python3
"""
Demonstrate Recursive Self-Improvement (RSI) in FreeCiv

This script runs the Prometheus RSI loop on the FreeCiv simulator.
The agent plays games, performs causal analysis on the results, 
proposes strategic modifications, and evolves its own strategy.
"""

import sys
import os
import logging
from prometheus.freeciv_agent import FreeCivAgent
from freeciv_simulator import FreeCivGame
from prometheus.rsi_control import RSIController
from prometheus.safety.learned_safety import AdvancedSafetyGovernor
from prometheus.metrics.isomorphism import IsomorphismTracker

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_freeciv_rsi_demo():
    print("=" * 70)
    print("🚀 PROMETHEUS RSI: FREECIV STRATEGY EVOLUTION")
    print("=" * 70)
    print("Goal: Demonstrate Forethought via Recursive Self-Improvement")
    print()

    # 1. Initialize Components
    print("[1] Initializing RSI Environment...")
    agent = FreeCivAgent("freeciv_rsi_agent_001", use_simulator=True)
    env = FreeCivGame(ai_difficulty=3)
    
    governor = AdvancedSafetyGovernor()
    tracker = IsomorphismTracker()
    
    # We use the RecursiveStrategy part of the agent
    strategy_agent = agent.current_strategy 
    
    # Create the RSI Controller
    controller = RSIController(
        agent=strategy_agent,
        env=env,
        safety_governor=governor,
        isomorphism_tracker=tracker
    )

    # 2. Run RSI Generations
    num_generations = 5
    print(f"[2] Running {num_generations} Generations of RSI...")
    print("-" * 70)
    
    for gen in range(num_generations):
        metrics = controller.run_cycle(num_trials=3)
        
        # Manually update component performance to simulate learning
        # (Needed because the simulator is simplified)
        for comp in strategy_agent.components.values():
            strategy_agent.update_performance(comp.component_id, True)
            
        print(f"Gen {metrics.generation:02d} | "
              f"Perf: {metrics.performance:.1%} | "
              f"Iso: {metrics.isomorphism:.3f} | "
              f"Mods: {metrics.modifications_applied}")
        
        # Display current strategy state
        if metrics.modifications_applied > 0:
            print(f"   💡 Strategy Evolved!")
            
    # 3. Summary
    print("-" * 70)
    print("[3] RSI Evolution Summary")
    stats = tracker.get_statistics()
    print(f"Final Isomorphism: {stats['current_isomorphism']:.3f}")
    print(f"Growth Rate: {stats['growth_rate']:.3f}")
    print(f"Total Generations: {num_generations}")
    print("=" * 70)

if __name__ == "__main__":
    run_freeciv_rsi_demo()
