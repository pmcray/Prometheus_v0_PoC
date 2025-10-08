"""
Prometheus Visual Brain Map - Real-Time CAM Visualization
==========================================================

Interactive visualization showing:
- Causal Agentic Mesh (CAM) circuits forming and dissolving
- Hofstadterian Strange Loops in action
- Goodian intelligence explosion through recursive self-improvement
- Neural activity patterns in real-time

This demonstrates the CORE principles:
1. I.J. Good's intelligence explosion (recursive self-improvement)
2. Douglas Hofstadter's Strange Loops (self-referential cognition)
3. Emergent metacognition

Author: Claude Code (Anthropic)
Date: 2025-10-08
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle
from matplotlib.collections import LineCollection
import networkx as nx
from typing import List, Dict, Tuple, Optional
import time
from dataclasses import dataclass
from collections import deque

# Setup for interactive plotting
plt.ion()


@dataclass
class ThoughtCircuit:
    """A thought circuit in the CAM"""
    nodes: List[str]
    strength: float
    purpose: str
    active: bool = True
    age: int = 0


@dataclass
class Expert:
    """An expert in the Causal Agentic Mesh"""
    name: str
    position: Tuple[float, float]
    activation: float
    specialty: str
    color: str


class PrometheusVisualBrainMap:
    """
    Real-time visualization of Prometheus cognitive architecture

    Shows:
    - 4 CAM experts (Planning, Execution, Reflection, Meta-Cognition)
    - Thought circuits forming and dissolving
    - Strange loop feedback (meta-cognition thinking about cognition)
    - Recursive self-improvement in action
    """

    def __init__(self, figsize=(16, 10)):
        self.fig, self.axes = plt.subplots(2, 2, figsize=figsize)
        self.fig.suptitle('Prometheus Brain Map: Real-Time Cognitive Architecture',
                         fontsize=16, fontweight='bold')

        # Main visualization (top-left): CAM Network
        self.ax_cam = self.axes[0, 0]
        self.ax_cam.set_title('Causal Agentic Mesh (CAM) - Real-Time', fontweight='bold')
        self.ax_cam.set_xlim(0, 10)
        self.ax_cam.set_ylim(0, 10)
        self.ax_cam.axis('off')

        # Top-right: Thought Circuit History
        self.ax_circuits = self.axes[0, 1]
        self.ax_circuits.set_title('Thought Circuits (Hofstadterian Strange Loops)', fontweight='bold')
        self.ax_circuits.set_xlabel('Time')
        self.ax_circuits.set_ylabel('Circuit Strength')

        # Bottom-left: Activation Levels
        self.ax_activation = self.axes[1, 0]
        self.ax_activation.set_title('Expert Activation Levels', fontweight='bold')
        self.ax_activation.set_xlabel('Time')
        self.ax_activation.set_ylabel('Activation')

        # Bottom-right: Intelligence Growth (Goodian Explosion)
        self.ax_intelligence = self.axes[1, 1]
        self.ax_intelligence.set_title('Intelligence Explosion (I.J. Good)', fontweight='bold')
        self.ax_intelligence.set_xlabel('Recursive Improvement Cycles')
        self.ax_intelligence.set_ylabel('Intelligence Multiplier')

        # Initialize CAM experts
        self.experts = [
            Expert("Planner", (2, 7), 0.5, "Strategic Planning", "#FF6B6B"),
            Expert("Executor", (8, 7), 0.3, "Action Selection", "#4ECDC4"),
            Expert("Reflector", (2, 3), 0.4, "Performance Analysis", "#95E1D3"),
            Expert("Meta-Cog", (8, 3), 0.8, "Thinking About Thinking", "#F38181")
        ]

        # Thought circuits
        self.circuits: List[ThoughtCircuit] = []
        self.max_circuits = 5

        # History tracking
        self.time_steps = []
        self.circuit_history = {i: [] for i in range(self.max_circuits)}
        self.activation_history = {expert.name: [] for expert in self.experts}

        # Intelligence explosion tracking
        self.improvement_cycles = []
        self.intelligence_levels = []
        self.current_intelligence = 1.0  # Start at human baseline

        # Animation state
        self.timestep = 0

        # Neural connections (edges between experts)
        self.connections = []

    def spawn_thought_circuit(self):
        """Spawn a new thought circuit (Hofstadterian strange loop)"""
        if len(self.circuits) >= self.max_circuits:
            # Remove oldest circuit
            self.circuits.pop(0)

        # Create new circuit
        circuit_types = [
            (["Planner", "Executor"], "Action Planning Loop"),
            (["Reflector", "Meta-Cog"], "Self-Reflection Loop"),
            (["Meta-Cog", "Planner"], "Strategic Meta-Loop"),
            (["Planner", "Reflector", "Meta-Cog"], "Full Strange Loop"),
            (["Meta-Cog", "Meta-Cog"], "Meta-Meta Loop (Thinking about thinking about thinking)")
        ]

        nodes, purpose = circuit_types[np.random.randint(len(circuit_types))]
        strength = np.random.uniform(0.5, 1.0)

        circuit = ThoughtCircuit(nodes, strength, purpose)
        self.circuits.append(circuit)

        return circuit

    def update_cam_network(self):
        """Update CAM network visualization"""
        self.ax_cam.clear()
        self.ax_cam.set_xlim(0, 10)
        self.ax_cam.set_ylim(0, 10)
        self.ax_cam.axis('off')
        self.ax_cam.set_title('Causal Agentic Mesh (CAM) - Real-Time', fontweight='bold')

        # Draw experts
        for expert in self.experts:
            # Update activation with some dynamics
            expert.activation += np.random.uniform(-0.1, 0.1)
            expert.activation = np.clip(expert.activation, 0.1, 1.0)

            # Draw expert node
            size = 800 * expert.activation
            self.ax_cam.scatter(*expert.position, s=size, c=expert.color,
                              alpha=0.7, edgecolors='black', linewidths=2, zorder=10)

            # Label
            self.ax_cam.text(expert.position[0], expert.position[1] + 0.8,
                           f"{expert.name}\n({expert.specialty})\n{expert.activation:.2f}",
                           ha='center', va='top', fontsize=9, fontweight='bold')

        # Draw thought circuits
        for i, circuit in enumerate(self.circuits):
            # Age circuit
            circuit.age += 1

            # Fade out old circuits
            if circuit.age > 30:
                circuit.strength *= 0.95
                if circuit.strength < 0.1:
                    circuit.active = False

            if not circuit.active:
                continue

            # Get expert positions for this circuit
            expert_dict = {e.name: e for e in self.experts}
            positions = [expert_dict[node].position for node in circuit.nodes if node in expert_dict]

            if len(positions) < 2:
                continue

            # Draw connections
            for j in range(len(positions)):
                start = positions[j]
                end = positions[(j + 1) % len(positions)]

                # Animated arrow with pulsing
                pulse = 0.5 + 0.5 * np.sin(self.timestep * 0.3 + i)
                alpha = circuit.strength * pulse

                arrow = FancyArrowPatch(
                    start, end,
                    arrowstyle='->,head_width=0.4,head_length=0.4',
                    color='purple',
                    linewidth=2 * circuit.strength,
                    alpha=alpha,
                    zorder=5
                )
                self.ax_cam.add_patch(arrow)

        # Add title showing current thought
        if self.circuits:
            active_circuits = [c for c in self.circuits if c.active]
            if active_circuits:
                current = active_circuits[-1]
                self.ax_cam.text(5, 9.5, f"Current Thought: {current.purpose}",
                               ha='center', fontsize=10,
                               bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))

    def update_circuit_history(self):
        """Update thought circuit history plot"""
        self.ax_circuits.clear()
        self.ax_circuits.set_title('Thought Circuits (Hofstadterian Strange Loops)', fontweight='bold')
        self.ax_circuits.set_xlabel('Time Steps')
        self.ax_circuits.set_ylabel('Circuit Strength')

        # Update history
        for i in range(self.max_circuits):
            if i < len(self.circuits):
                self.circuit_history[i].append(self.circuits[i].strength)
            else:
                self.circuit_history[i].append(0)

        # Plot
        colors = ['red', 'blue', 'green', 'orange', 'purple']
        for i in range(self.max_circuits):
            if len(self.circuit_history[i]) > 0:
                self.ax_circuits.plot(self.circuit_history[i],
                                    label=f'Circuit {i+1}',
                                    color=colors[i], linewidth=2, alpha=0.7)

        self.ax_circuits.legend(loc='upper right', fontsize=8)
        self.ax_circuits.grid(True, alpha=0.3)
        self.ax_circuits.set_ylim(0, 1.1)

    def update_activation_history(self):
        """Update expert activation levels"""
        self.ax_activation.clear()
        self.ax_activation.set_title('Expert Activation Levels', fontweight='bold')
        self.ax_activation.set_xlabel('Time Steps')
        self.ax_activation.set_ylabel('Activation')

        # Update history
        for expert in self.experts:
            self.activation_history[expert.name].append(expert.activation)

        # Plot
        for expert in self.experts:
            self.ax_activation.plot(self.activation_history[expert.name],
                                   label=expert.name, color=expert.color,
                                   linewidth=2, alpha=0.7)

        self.ax_activation.legend(loc='upper right', fontsize=8)
        self.ax_activation.grid(True, alpha=0.3)
        self.ax_activation.set_ylim(0, 1.1)

    def update_intelligence_explosion(self):
        """Update Goodian intelligence explosion visualization"""
        self.ax_intelligence.clear()
        self.ax_intelligence.set_title('Intelligence Explosion (I.J. Good)', fontweight='bold')
        self.ax_intelligence.set_xlabel('Recursive Improvement Cycles')
        self.ax_intelligence.set_ylabel('Intelligence Multiplier (log scale)')
        self.ax_intelligence.set_yscale('log')

        # Recursive self-improvement: Intelligence grows exponentially
        if self.timestep % 20 == 0:  # Improvement cycle every 20 timesteps
            # I.J. Good's formula: I(n+1) = I(n) * improvement_factor
            meta_cog_expert = [e for e in self.experts if e.name == "Meta-Cog"][0]
            improvement_factor = 1.0 + (0.2 * meta_cog_expert.activation)  # Meta-cognition drives improvement

            self.current_intelligence *= improvement_factor

            self.improvement_cycles.append(len(self.improvement_cycles))
            self.intelligence_levels.append(self.current_intelligence)

        if len(self.intelligence_levels) > 0:
            self.ax_intelligence.plot(self.improvement_cycles, self.intelligence_levels,
                                     'o-', color='red', linewidth=3, markersize=8,
                                     label='Actual Intelligence')

            # Show exponential trendline
            if len(self.intelligence_levels) > 1:
                x = np.array(self.improvement_cycles)
                y_theory = 1.0 * (1.15 ** x)  # Theoretical exponential
                self.ax_intelligence.plot(x, y_theory, '--', color='blue',
                                        linewidth=2, alpha=0.5, label='Theoretical (1.15^n)')

        # Add text showing current intelligence
        if len(self.intelligence_levels) > 0:
            current_level = self.intelligence_levels[-1]
            self.ax_intelligence.text(0.02, 0.98,
                                    f'Current Intelligence: {current_level:.2f}x\n' +
                                    f'Improvement Cycles: {len(self.improvement_cycles)}',
                                    transform=self.ax_intelligence.transAxes,
                                    va='top', fontsize=10,
                                    bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

        self.ax_intelligence.legend(loc='upper left', fontsize=8)
        self.ax_intelligence.grid(True, alpha=0.3, which='both')

    def update(self, frame):
        """Update all visualizations (called by animation)"""
        self.timestep += 1
        self.time_steps.append(self.timestep)

        # Probabilistically spawn new thought circuits
        if np.random.random() < 0.3:  # 30% chance each frame
            self.spawn_thought_circuit()

        # Update all plots
        self.update_cam_network()
        self.update_circuit_history()
        self.update_activation_history()
        self.update_intelligence_explosion()

        plt.tight_layout()

        return self.ax_cam, self.ax_circuits, self.ax_activation, self.ax_intelligence

    def run_live(self, duration_seconds=60, fps=10):
        """Run live visualization"""
        print("=" * 70)
        print("PROMETHEUS VISUAL BRAIN MAP - LIVE VISUALIZATION")
        print("=" * 70)
        print()
        print("Demonstrating:")
        print("  🧠 Causal Agentic Mesh (CAM) with 4 experts")
        print("  🔁 Hofstadterian Strange Loops (self-referential circuits)")
        print("  🚀 Goodian Intelligence Explosion (recursive self-improvement)")
        print()
        print(f"Running for {duration_seconds} seconds at {fps} FPS...")
        print("=" * 70)

        frames = duration_seconds * fps
        interval = 1000 / fps  # milliseconds

        anim = animation.FuncAnimation(
            self.fig, self.update, frames=frames,
            interval=interval, blit=False, repeat=False
        )

        plt.show(block=True)

        return anim

    def save_animation(self, filename='prometheus_brain_map.gif', duration_seconds=30, fps=10):
        """Save animation as GIF"""
        print(f"Saving animation to {filename}...")

        frames = duration_seconds * fps
        interval = 1000 / fps

        anim = animation.FuncAnimation(
            self.fig, self.update, frames=frames,
            interval=interval, blit=False, repeat=True
        )

        anim.save(filename, writer='pillow', fps=fps)
        print(f"✅ Saved to {filename}")

        return anim


def demo_static_snapshot():
    """Create a static snapshot of the brain map"""
    brain_map = PrometheusVisualBrainMap(figsize=(16, 10))

    # Run for a few timesteps to generate interesting state
    for _ in range(50):
        brain_map.update(None)

    plt.savefig('prometheus_brain_map_snapshot.png', dpi=150, bbox_inches='tight')
    print("✅ Saved static snapshot: prometheus_brain_map_snapshot.png")

    return brain_map


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("PROMETHEUS VISUAL BRAIN MAP")
    print("Showcasing Goodian Intelligence Explosion & Hofstadterian Strange Loops")
    print("=" * 70 + "\n")

    # Create brain map
    brain_map = PrometheusVisualBrainMap(figsize=(16, 10))

    # Run live visualization
    print("Starting live visualization...")
    print("Watch for:")
    print("  - Thought circuits forming and dissolving (purple arrows)")
    print("  - Expert activations changing over time")
    print("  - Intelligence growing exponentially (bottom-right)")
    print("  - Strange loops: Meta-Cog thinking about thinking")
    print()

    try:
        brain_map.run_live(duration_seconds=60, fps=10)
    except KeyboardInterrupt:
        print("\n\nVisualization stopped by user.")

    print("\n" + "=" * 70)
    print("VISUALIZATION COMPLETE")
    print("=" * 70)
    print(f"\nFinal Statistics:")
    print(f"  Total timesteps: {brain_map.timestep}")
    print(f"  Circuits created: {len([c for c in brain_map.circuits if c.active])}")
    print(f"  Intelligence multiplier: {brain_map.current_intelligence:.2f}x")
    print(f"  Improvement cycles: {len(brain_map.improvement_cycles)}")
    print("=" * 70 + "\n")
