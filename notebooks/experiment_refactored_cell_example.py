#!/usr/bin/env python3
"""
REFACTORED EXPERIMENT CELL - Example of cleaner notebook structure

This shows how the experiment cell should look after refactoring to use
prometheus/ imports instead of embedded classes.

BEFORE: ~400 lines of embedded PatternGenerator, ResNet, Agent classes
AFTER:  ~50 lines with clean imports

This makes the notebook:
- Much shorter and easier to read
- Focus on the demonstration, not implementation
- Professional and maintainable
- Easy to update (change one file, all notebooks benefit)
"""

# ============================================================================
# IMPORTS FROM PROMETHEUS PACKAGE
# ============================================================================

from prometheus.data.generators import PatternGenerator
from prometheus.models.architectures import StaticAgent, PrometheusAgent
from prometheus.training.loops import pretrain_model, online_train_model, print_performance_summary
from prometheus.visualization.plots import plot_performance_comparison
from prometheus.metrics.performance import compute_advantage_gap, summarize_experiment_results

import numpy as np
import time

# ============================================================================
# EXPERIMENT CONFIGURATION
# ============================================================================

QUICK_DEMO_MODE = True  # Toggle for Quick vs Full validation

if QUICK_DEMO_MODE:
    GENERATIONS = 8
    TASKS_PER_GENERATION = 50
    PRETRAIN_EPOCHS = 20
    ONLINE_EPOCHS = 5
else:
    GENERATIONS = 50
    TASKS_PER_GENERATION = 200
    PRETRAIN_EPOCHS = 40
    ONLINE_EPOCHS = 10

print(f"🎯 MODE: {'QUICK DEMO' if QUICK_DEMO_MODE else 'FULL VALIDATION'}")
print(f"   Generations: {GENERATIONS}, Tasks/gen: {TASKS_PER_GENERATION}")
print(f"   Expected runtime: {'10-15 minutes' if QUICK_DEMO_MODE else '3-4 hours'}")
print("="*70)

# ============================================================================
# EXPERIMENT EXECUTION
# ============================================================================

print("\n🧪 Running Intelligence Explosion Experiment...")

# Initialize generator
generator = PatternGenerator(grid_size=64, seed=42)

# Initialize agents with ResNet architecture
static_agent = StaticAgent(
    input_shape=(64, 64, 1),
    num_classes=generator.num_classes,
    architecture='resnet',
    name="Static"
)

prometheus_agent = PrometheusAgent(
    input_shape=(64, 64, 1),
    num_classes=generator.num_classes,
    architecture='resnet',
    learning_rate=0.0003,
    name="Prometheus"
)

# ========================================================================
# PHASE 1: PRE-TRAINING
# ========================================================================

print("\n🔧 Phase 1: Pre-Training")
print("="*70)

# Initial balanced distribution
initial_dist = {pattern: 1.0/generator.num_classes for pattern in generator.pattern_types}

# Generate pre-training data
X_pretrain, y_pretrain = generator.generate_batch(2000, initial_dist)

# Pre-train both agents
static_agent.pretrain(X_pretrain, y_pretrain, epochs=PRETRAIN_EPOCHS)
prometheus_agent.pretrain(X_pretrain, y_pretrain, epochs=PRETRAIN_EPOCHS)

# ========================================================================
# PHASE 2: GENERATIONAL EVOLUTION
# ========================================================================

print("\n🔄 Phase 2: Generational Evolution")
print("="*70)

# Distribution shifts (simple → complex patterns)
distributions = [
    {'horizontal_stripes': 0.30, 'vertical_stripes': 0.30, 'diagonal_lines': 0.20,
     'checkerboard': 0.10, 'concentric_circles': 0.05, 'spiral': 0.03,
     'maze': 0.01, 'fractal_tree': 0.01},
    # ... (distributions evolve toward complex patterns)
    {'horizontal_stripes': 0.03, 'vertical_stripes': 0.03, 'diagonal_lines': 0.04,
     'checkerboard': 0.08, 'concentric_circles': 0.07, 'spiral': 0.10,
     'maze': 0.30, 'fractal_tree': 0.35},
]

static_results = []
prometheus_results = []

start_time = time.time()

for gen in range(GENERATIONS):
    dist_idx = min(gen, len(distributions) - 1)
    dist = distributions[dist_idx]

    print(f"\n📊 Generation {gen}:")

    # Generate test batch
    X_test, y_test = generator.generate_batch(TASKS_PER_GENERATION, dist)

    # Evaluate both agents
    static_metrics = static_agent.evaluate(X_test, y_test)
    prometheus_metrics = prometheus_agent.evaluate(X_test, y_test)

    static_results.append(static_metrics['accuracy'])
    prometheus_results.append(prometheus_metrics['accuracy'])

    print(f"   Static:      {static_metrics['accuracy']:.1f}% (frozen)")
    print(f"   Prometheus:  {prometheus_metrics['accuracy']:.1f}% (adaptive)")
    print(f"   Δ:           {prometheus_metrics['accuracy'] - static_metrics['accuracy']:+.1f}%")

    # Prometheus online learning (Static stays frozen)
    if gen < GENERATIONS - 1:
        X_online, y_online = generator.generate_batch(300, dist)
        prometheus_agent.online_learn(X_online, y_online, epochs=ONLINE_EPOCHS)

total_time = time.time() - start_time

# ========================================================================
# RESULTS & VISUALIZATION
# ========================================================================

print(f"\n⏱️  Total runtime: {total_time/60:.1f} minutes")

# Performance summary
print_performance_summary(static_results, prometheus_results, "Intelligence Explosion")

# Statistical analysis
summary = summarize_experiment_results(static_results, prometheus_results, "Intelligence Explosion")

# Visualization
fig, axes = plot_performance_comparison(
    static_results,
    prometheus_results,
    title="Intelligence Explosion: Static vs Prometheus",
    xlabel="Generation",
    show_distribution_shifts=[2, 4, 6]
)

print("\n✅ Experiment Complete!")
print(f"   {summary['conclusion_icon']} {summary['conclusion']}")
print(f"   Average advantage: {summary['advantage_gap']['average_gap']:+.1f}%")

# ============================================================================
# KEY IMPROVEMENTS FROM REFACTORING:
# ============================================================================
#
# BEFORE (Embedded Code):
# - ~400 lines of PatternGenerator class with 8 pattern methods
# - ~200 lines of ResNet architecture + Agent classes
# - Total: ~600 lines of implementation details
# - Hard to maintain (changes need to be made in 3 notebooks)
# - Mixes implementation with demonstration
#
# AFTER (Clean Imports):
# - ~50 lines of experiment logic
# - Clear focus on the demonstration
# - DRY principle: change prometheus/, all notebooks benefit
# - Professional appearance for clients
# - Easy to understand the experiment flow
#
# RESULT:
# - 92% reduction in notebook length
# - Much more readable and maintainable
# - Professional quality suitable for client demonstrations
# ============================================================================
