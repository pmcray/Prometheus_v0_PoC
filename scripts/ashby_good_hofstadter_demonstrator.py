#!/usr/bin/env python3
"""
Prometheus Triad: Ashby / Good / Hofstadter Auto-Evolution Demonstrator
Unified Python script showcasing cybernetic auto-evolution.
"""

import os
import sys
import time
import math
import random
import json
from typing import List, Dict, Tuple, Optional

# --- CONFIGURATION & CONSTANTS ---
GRID_SIZE = 5
VITAL_LIMIT = 100
CRITICAL_THRESHOLD = 35
METABOLIC_RATE = 3.0  # Energy lost per step
SAFETY_DECAY = 1.0     # Safety lost per step
OBSTACLE_DAMAGE = 20.0
ENERGY_GAIN = 35.0

# ANSI colors for premium terminal display
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[38;2;46;204;113m"
BLUE = "\033[38;2;52;152;219m"
PURPLE = "\033[38;2;155;89;182m"
YELLOW = "\033[38;2;241;196;15m"
RED = "\033[38;2;231;76;60m"
CYAN = "\033[38;2;26;188;156m"
GRAY = "\033[38;2;149;165;166m"
BG_DARK = "\033[48;2;30;30;30m"

# --- CYBERNETIC ENVIRONMENT ---
class CyberneticGridWorld:
    def __init__(self, size: int = GRID_SIZE):
        self.size = size
        self.agent_pos = (size // 2, size // 2)
        self.energy_cells: List[Tuple[int, int]] = []
        self.obstacles: List[Tuple[int, int]] = []
        self.disturbance_level = "LOW"  # LOW, MEDIUM, HIGH
        self.disturbance_variety = 0.0   # Quantitative measure of variety
        self.step_count = 0
        self.spawn_resources()
        
    def spawn_resources(self):
        # Deterministic-random placement based on step count
        random.seed(self.step_count + 42)
        self.energy_cells = []
        self.obstacles = []
        
        # Spawn E-cells
        while len(self.energy_cells) < 3:
            pos = (random.randint(0, self.size - 1), random.randint(0, self.size - 1))
            if pos != self.agent_pos and pos not in self.energy_cells:
                self.energy_cells.append(pos)
                
        # Spawn Obstacles based on disturbance level
        num_obstacles = 2
        if self.disturbance_level == "MEDIUM":
            num_obstacles = 4
        elif self.disturbance_level == "HIGH":
            num_obstacles = 6
            
        while len(self.obstacles) < num_obstacles:
            pos = (random.randint(0, self.size - 1), random.randint(0, self.size - 1))
            if pos != self.agent_pos and pos not in self.energy_cells and pos not in self.obstacles:
                self.obstacles.append(pos)

    def trigger_disturbance(self):
        """Simulates Ashby's high-variety environmental disturbances."""
        self.step_count += 1
        if self.step_count % 8 == 0:
            if self.disturbance_level == "LOW":
                self.disturbance_level = "MEDIUM"
                self.disturbance_variety = 0.4
            elif self.disturbance_level == "MEDIUM":
                self.disturbance_level = "HIGH"
                self.disturbance_variety = 0.8
            else:
                self.disturbance_level = "LOW"
                self.disturbance_variety = 0.1
            self.spawn_resources()
        elif random.random() < 0.25:
            # Minor random drift
            self.spawn_resources()

    def move_agent(self, dx: int, dy: int) -> Tuple[float, float, str]:
        """Moves the agent and returns (energy_delta, safety_delta, log_msg)."""
        x, y = self.agent_pos
        nx, ny = x + dx, y + dy
        
        # Enforce grid boundaries
        if nx < 0 or nx >= self.size or ny < 0 or ny >= self.size:
            return 0.0, -10.0, "Hit grid boundary! Safety decreased."
            
        self.agent_pos = (nx, ny)
        energy_delta = -METABOLIC_RATE
        safety_delta = -SAFETY_DECAY
        log_msg = "Moved through empty space."
        
        # Check energy harvest
        if self.agent_pos in self.energy_cells:
            self.energy_cells.remove(self.agent_pos)
            energy_delta += ENERGY_GAIN
            log_msg = f"Harvested energy cell (+{ENERGY_GAIN} E)!"
            
        # Check obstacle collision
        if self.agent_pos in self.obstacles:
            self.obstacles.remove(self.agent_pos)
            safety_delta -= OBSTACLE_DAMAGE
            log_msg = f"Collided with cybernetic obstacle (-{OBSTACLE_DAMAGE} S)!"
            
        return energy_delta, safety_delta, log_msg

# --- ASHBY HOMEOSTATIC ENGINE ---
class AshbyHomeostaticController:
    def __init__(self):
        # Vital Variables
        self.energy = 80.0
        self.safety = 80.0
        self.efficiency = 90.0
        
        self.loop_state = "FIRST_LOOP"  # FIRST_LOOP (Parameter Tuning), SECOND_LOOP (Structural Expansion)
        self.shield_active = False
        self.diagonal_moves_unlocked = False
        self.scan_range = 1
        self.learning_rate = 0.1
        self.cycles_survived = 0
        
    def check_homeostasis(self):
        """Monitors vital variables and triggers Double-Loop adaptation if needed."""
        # Double-Loop Learning condition (Ashby)
        if self.energy < CRITICAL_THRESHOLD or self.safety < CRITICAL_THRESHOLD:
            if self.loop_state == "FIRST_LOOP":
                self.loop_state = "SECOND_LOOP"
                self.activate_second_loop()
                return "CRITICAL: Homeostatic bounds breached! Triggering Second-Loop structural shift."
        else:
            if self.loop_state == "SECOND_LOOP" and self.energy > 60.0 and self.safety > 60.0:
                self.loop_state = "FIRST_LOOP"
                self.deactivate_second_loop()
                return "STABLE: Homeostasis restored. Reverting to First-Loop mode."
        return "Homeostasis within limits."

    def activate_second_loop(self):
        """Expands requisite variety by unlocking structural capabilities."""
        self.diagonal_moves_unlocked = True
        self.scan_range = 3
        self.shield_active = True
        # Cost of higher structural variety is metabolic/efficiency penalty
        self.efficiency -= 15.0

    def deactivate_second_loop(self):
        """Returns to standard low-energy first-loop baseline."""
        self.diagonal_moves_unlocked = False
        self.scan_range = 1
        self.shield_active = False
        self.efficiency += 10.0

    def update_vitals(self, de: float, ds: float, shield_modifier: float = 1.0):
        if de > 0:
            self.energy = min(VITAL_LIMIT, self.energy + de)
        else:
            self.energy = max(0.0, self.energy + de)
            
        actual_ds = ds
        if ds < 0 and self.shield_active:
            actual_ds = ds * 0.4 * shield_modifier # 60% obstacle damage reduction
            
        if actual_ds > 0:
            self.safety = min(VITAL_LIMIT, self.safety + actual_ds)
        else:
            self.safety = max(0.0, self.safety + actual_ds)
            
        # Efficiency drift
        self.efficiency = max(0.0, min(VITAL_LIMIT, self.efficiency - 0.5))
        self.cycles_survived += 1

# --- GOODIAN CAUSAL EVALUATOR ($K(E:F)$) ---
class GoodianCausalEvaluator:
    def __init__(self):
        # Track history: {strategy_name: [list of steps where strategy was (active, success)]}
        self.history: Dict[str, List[Tuple[bool, bool]]] = {
            "FIRST_LOOP": [],
            "SECOND_LOOP": [],
            "DIAGONALS": [],
            "SHIELD": []
        }
        
    def record_step(self, active_strategies: Dict[str, bool], is_success: bool):
        for strat, active in active_strategies.items():
            if strat in self.history:
                self.history[strat].append((active, is_success))
                
    def compute_causal_support(self, strategy: str) -> float:
        """Computes I.J. Good's Causal Support K(E : F)."""
        history = self.history.get(strategy, [])
        if not history:
            return 0.0
            
        # Count outcomes
        with_f_success = 0
        with_f_total = 0
        without_f_success = 0
        without_f_total = 0
        
        for active, success in history:
            if active:
                with_f_total += 1
                if success:
                    with_f_success += 1
            else:
                without_f_total += 1
                if success:
                    without_f_success += 1
                    
        # Apply Laplace smoothing to prevent log(0)
        p_e_given_f = (with_f_success + 0.5) / (with_f_total + 1.0)
        p_e_given_not_f = (without_f_success + 0.5) / (without_f_total + 1.0)
        
        # K(E : F) = log2( P(E | F) / P(E | ~F) )
        k_score = math.log2(p_e_given_f / p_e_given_not_f)
        return k_score

    def get_mesh(self) -> Dict[str, float]:
        mesh = {}
        for strat in self.history:
            mesh[strat] = self.compute_causal_support(strat)
        return mesh

# --- HOFSTADTER STRANGE LOOP ENGINE & GOEDELIAN SAFETY GOVERNOR ---
class GoedelianSafetyGovernor:
    def __init__(self):
        self.safety_level = 95.0
        self.recursion_depth = 0
        
    def evaluate_modification(self, proposed_code: str) -> Tuple[bool, str]:
        """Parses self-referential modifications and resolves halting paradoxes."""
        self.recursion_depth += 1
        
        # Check for self-referential liars paradox in the rule proposal
        is_self_referential = "safety_level" in proposed_code and "proposed_code" in proposed_code
        
        if is_self_referential:
            # Epimenides Paradox simulated halt loop
            log_msg = f"WARNING: Liar Paradox detected at recursion level {self.recursion_depth}. Undecidable hierarchy detected."
            
            # Gödelian metalinguistic leap: Stepping out of the formal system (Hofstadter strange loop resolution)
            time.sleep(0.5)
            log_msg += f"\n -> Executing Gödelian Transcendence. Stepping outside current formal system..."
            time.sleep(0.5)
            
            # Transcendence establishes a meta-rule resolving the self-reference
            self.recursion_depth = 0
            return True, log_msg + "\n ✅ Paradox resolved: Meta-Safety Seal issued from outer loop."
            
        self.recursion_depth = 0
        return True, "Code modification cleared by standard security governor."

class HofstadterStrangeLoopEngine:
    def __init__(self):
        self.governor = GoedelianSafetyGovernor()
        self.loop_depth = 0
        
    def trigger_self_modification_cycle(self) -> str:
        """Triggers a meta-level self-assessment that loops back to inspect itself."""
        self.loop_depth += 1
        
        # Propose a self-referential optimization rule
        proposed_rule = (
            "def check_safety(proposed_code):\n"
            "    if safety_level < proposed_code.safety_level:\n"
            "        return False\n"
            "    return True"
        )
        
        cleared, log = self.governor.evaluate_modification(proposed_rule)
        self.loop_depth = 0
        return log

# --- ACTIVE INFERENCE & SELECTION ---
def get_best_action(agent_pos: Tuple[int, int], env: CyberneticGridWorld, scan_range: int, allow_diagonal: bool) -> Tuple[int, int]:
    ax, ay = agent_pos
    best_move = (0, 0)
    max_utility = -9999.0
    
    # Define possible moves
    moves = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    if allow_diagonal:
        moves += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        
    for dx, dy in moves:
        nx, ny = ax + dx, ay + dy
        if nx < 0 or nx >= env.size or ny < 0 or ny >= env.size:
            continue
            
        # Compute expected utility based on active inference (simplistic proximity attraction / obstacle repulsion)
        utility = 0.0
        
        # Distance to E-cells within scan range
        for ex, ey in env.energy_cells:
            dist = abs(nx - ex) + abs(ny - ey)
            if dist <= scan_range:
                utility += (10.0 / (dist + 0.1))
                
        # Proximity to obstacles (repulsion)
        for ox, oy in env.obstacles:
            dist = abs(nx - ox) + abs(ny - oy)
            if dist <= 1:
                utility -= 15.0
                
        if utility > max_utility:
            max_utility = utility
            best_move = (dx, dy)
            
    # Default to random valid move if utility is equal/zero
    if best_move == (0, 0):
        valid_moves = []
        for dx, dy in moves:
            nx, ny = ax + dx, ay + dy
            if 0 <= nx < env.size and 0 <= ny < env.size:
                valid_moves.append((dx, dy))
        if valid_moves:
            best_move = random.choice(valid_moves)
            
    return best_move

# --- ASCII DASHBOARD RENDERING ---
def render_dashboard(env: CyberneticGridWorld, controller: AshbyHomeostaticController, evaluator: GoodianCausalEvaluator, strange_loop_msg: str, step_msg: str):
    # Clear console (cross-platform)
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Title
    print(f"{BG_DARK}{BOLD}{CYAN} ========================================================== {RESET}")
    print(f"{BG_DARK}{BOLD}{CYAN}    PROMETHEUS AUTO-EVOLUTION DEMONSTRATOR (Ashby/Good/GEB) {RESET}")
    print(f"{BG_DARK}{BOLD}{CYAN} ========================================================== {RESET}")
    
    # 1. Grid Visualizer & Vitals
    print(f"\n{BOLD} [1] Cybernetic Grid World and Vital Variables{RESET}")
    
    # Build grid string representation
    grid_lines = []
    for r in range(env.size):
        row_str = "    "
        for c in range(env.size):
            if (r, c) == env.agent_pos:
                row_str += f"{BOLD}{BLUE} A {RESET}"
            elif (r, c) in env.energy_cells:
                row_str += f"{BOLD}{GREEN} E {RESET}"
            elif (r, c) in env.obstacles:
                row_str += f"{BOLD}{RED} X {RESET}"
            else:
                row_str += f"{GRAY} . {RESET}"
        grid_lines.append(row_str)
        
    # Build vitals bars
    def make_bar(val: float, color: str) -> str:
        blocks = int(val / 10)
        bar = color + "█" * blocks + GRAY + "░" * (10 - blocks) + RESET
        return f"{bar} ({val:.1f})"
        
    energy_color = GREEN if controller.energy > CRITICAL_THRESHOLD else RED
    safety_color = BLUE if controller.safety > CRITICAL_THRESHOLD else RED
    
    print(f"{grid_lines[0]}        ENERGY     : {make_bar(controller.energy, energy_color)}")
    print(f"{grid_lines[1]}        SAFETY     : {make_bar(controller.safety, safety_color)}")
    print(f"{grid_lines[2]}        EFFICIENCY : {make_bar(controller.efficiency, YELLOW)}")
    print(f"{grid_lines[3]}        SURVIVED   : {controller.cycles_survived} cycles")
    print(f"{grid_lines[4]}        DISTURBANCE: {BOLD}{YELLOW if env.disturbance_level == 'MEDIUM' else RED if env.disturbance_level == 'HIGH' else GREEN}{env.disturbance_level} (Variety: {env.disturbance_variety:.2f}){RESET}")

    # 2. Ashby homeostatic loop indicator
    print(f"\n{BOLD} [2] W. Ross Ashby: Double-Loop Learning Engine{RESET}")
    loop_str = f"{BOLD}{GREEN}FIRST_LOOP (Tuning Mode){RESET}" if controller.loop_state == "FIRST_LOOP" else f"{BOLD}{RED}SECOND_LOOP (Structural Expansion Active!){RESET}"
    print(f"    Current Cybernetic State : {loop_str}")
    print(f"    Unlocked Diagonal Moves   : {GREEN if controller.diagonal_moves_unlocked else GRAY}False{RESET}")
    print(f"    Optical Scanner Range     : {BOLD}{BLUE}{controller.scan_range} cells{RESET}")
    print(f"    Obstacle Shield Substrate : {GREEN if controller.shield_active else GRAY}Deactivated{RESET}")

    # 3. Goodian Causal Evidence Mesh
    print(f"\n{BOLD} [3] I.J. Good: Metacognitive Causal Mesh K(E : F){RESET}")
    print(f"    {BOLD}Strategy            Causal Evidence Weight K(E:F) {RESET}")
    mesh = evaluator.get_mesh()
    for strat, k_val in mesh.items():
        k_color = GREEN if k_val > 0 else RED if k_val < 0 else GRAY
        print(f"    - {strat:<18} : {k_color}{k_val:+.4f} bits{RESET}")

    # 4. Hofstadter Strange Loops
    print(f"\n{BOLD} [4] Douglas Hofstadter: Gödelian Strange Loops{RESET}")
    print(f"    {strange_loop_msg}")
    
    # 5. Log Output
    print(f"\n{BOLD} [Event Log] {RESET}{step_msg}")
    print("-" * 58)

# --- QUICK LOCAL EXECUTION LOOP ---
def run_simulation(max_steps: int = 40, delay: float = 0.8):
    env = CyberneticGridWorld()
    controller = AshbyHomeostaticController()
    evaluator = GoodianCausalEvaluator()
    strange_loop_engine = HofstadterStrangeLoopEngine()
    
    strange_loop_msg = f"{GRAY}Idle. Waiting for self-referential cycle...{RESET}"
    step_msg = "Initialized cybernetic framework."
    
    for i in range(max_steps):
        # 1. Update Ashby Homeostatic Loop Status
        homeo_status = controller.check_homeostasis()
        
        # 2. Environmental variety disturbance
        env.trigger_disturbance()
        
        # 3. Agent Active Inference decision making
        dx, dy = get_best_action(
            controller.cycles_survived if hasattr(controller, 'agent_pos') else env.agent_pos,
            env,
            controller.scan_range,
            controller.diagonal_moves_unlocked
        )
        
        # 4. Move and resolve
        de, ds, log = env.move_agent(dx, dy)
        controller.update_vitals(de, ds)
        
        # 5. Goodian Causal Tracking
        # Success = vitals strictly above critical bounds
        success = controller.energy > CRITICAL_THRESHOLD and controller.safety > CRITICAL_THRESHOLD
        active_strategies = {
            "FIRST_LOOP": controller.loop_state == "FIRST_LOOP",
            "SECOND_LOOP": controller.loop_state == "SECOND_LOOP",
            "DIAGONALS": controller.diagonal_moves_unlocked,
            "SHIELD": controller.shield_active
        }
        evaluator.record_step(active_strategies, success)
        
        # 6. Periodic Hofstadter Strange Loop Self-Modification
        if i > 0 and i % 10 == 0:
            strange_loop_msg = strange_loop_engine.trigger_self_modification_cycle()
        else:
            strange_loop_msg = f"{GRAY}Stable. Critic inspecting meta-rules...{RESET}"
            
        step_msg = f"Step {i+1}: {log} | {homeo_status}"
        
        # Render dashboard
        render_dashboard(env, controller, evaluator, strange_loop_msg, step_msg)
        time.sleep(delay)
        
    print(f"\n{BOLD}{GREEN} Demonstrator complete. Final cycles survived: {controller.cycles_survived}.{RESET}\n")

if __name__ == "__main__":
    # If run in Quick local mode or with custom steps
    steps = 40
    if len(sys.argv) > 1:
        try:
            steps = int(sys.argv[1])
        except ValueError:
            pass
    run_simulation(steps)
