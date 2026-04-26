# -- Prometheus ARC-AGI-3 Bridge v18 (Production Module) ---------------------
# Neural Latent Reasoning Architecture
# Build: 2026-04-20 23:55:00 (v0.95)
# ---------------------------------------------------------------------------
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import random, time, math, json, collections, heapq, os
from typing import Optional, Dict, Any, List, Tuple, Set
from collections import deque

try:
    import arc_agi
    from arcengine import GameAction, GameState
    TOOLKIT_AVAILABLE = True
except ImportError:
    TOOLKIT_AVAILABLE = False

from prometheus.wp71_arc_agi3 import (
    ARC3Action, ARC3Observation, ARC3Episode,
    ARC3WorldModel, ARC3GoalInferrer,
    ARC3ExplorationPolicy, ARC3StrangeLoopAgent,
    _SyntheticARCGame,
)

class ARC3VisionTransformer(nn.Module):
    """Temporal Transformer for pattern recognition and object permanence."""
    def __init__(self, n_colors=16, latent_dim=64, frame_stack=4, nhead=4, num_layers=2):
        super().__init__()
        self.frame_stack = frame_stack
        self.latent_dim = latent_dim
        
        # CNN backbone for spatial feature extraction
        self.conv1 = nn.Conv2d(n_colors, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.pool  = nn.MaxPool2d(2, 2)
        self.gap   = nn.AdaptiveAvgPool2d((4, 4)) # Global Average Pooling to 4x4
        
        # Transformer for temporal reasoning across frames
        self.feature_extractor = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 4 * 4, 128),
            nn.ReLU()
        )
        
        encoder_layer = nn.TransformerEncoderLayer(d_model=128, nhead=nhead, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        self.fc = nn.Linear(128, latent_dim)
        
        # [M] Phase 1: Deep Isomorphism Pre-training Transfer
        # Leverage ARC-AGI-1/2 operations as a seeded motif vocabulary
        try:
            from arc_parametric_operations import PARAMETRIC_OPERATIONS
            self.motifs = list(PARAMETRIC_OPERATIONS.keys())
        except ImportError:
            self.motifs = ["copy", "reflect", "rotate", "scale", "color_map", "fill"]
        
        self.motif_classifier = nn.Sequential(
            nn.Linear(latent_dim, len(self.motifs)),
            nn.Sigmoid()
        )
        
        # Imagination: transition model (latent, action) -> next_latent
        self.action_embedding = nn.Embedding(8, 32) # 7 types + 1 padding
        self.transition = nn.Sequential(
            nn.Linear(latent_dim + 32, 128),
            nn.ReLU(),
            nn.Linear(128, latent_dim)
        )
        
        # Step 1: Success Simulation (Reward Predictor)
        self.reward_predictor = nn.Sequential(
            nn.Linear(latent_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
        
        # [M] Step 2: Latent Sequence Completer
        self.sequence_completer = nn.Sequential(
            nn.Linear(latent_dim * 2, 128),
            nn.ReLU(),
            nn.Linear(128, latent_dim)
        )
        
        self.optimizer = None
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.to(self._device)

    def predict_next_in_sequence(self, latent_history):
        """Pattern completion: predict next latent based on recent trajectory."""
        if len(latent_history) < 2: return latent_history[-1]
        # Simple linear extrapolation in latent space for pattern completion
        last = latent_history[-1]
        prev = latent_history[-2]
        combined = torch.cat([last, prev], dim=1)
        return self.sequence_completer(combined)

    def forward(self, stack_list):
        # stack_list is (4, 64, 64)
        stack = torch.tensor(np.array(stack_list), dtype=torch.long, device=self._device)
        
        # One-hot encode each frame separately
        one_hot = F.one_hot(stack % 16, num_classes=16).permute(0, 3, 1, 2).float()
        
        # Spatial encoding
        x = self.pool(F.relu(self.conv1(one_hot))) # (4, 32, 32, 32)
        x = self.pool(F.relu(self.conv2(x)))       # (4, 64, 16, 16)
        x = self.gap(x)                            # (4, 64, 4, 4)
        
        # Temporal encoding
        features = self.feature_extractor(x)       # (4, 128)
        features = features.unsqueeze(0)           # (1, 4, 128)
        
        transformed = self.transformer(features)   # (1, 4, 128)
        
        # Use the latest frame's representation
        out = self.fc(transformed[:, -1, :])       # (1, 64)
        return out

    def imagine(self, latent, action_type_idx):
        """Predict the next latent state and extrinsic reward."""
        idx = min(action_type_idx, self.action_embedding.num_embeddings - 1)
        a_emb = self.action_embedding(torch.tensor([idx], device=self._device))
        combined = torch.cat([latent, a_emb], dim=1)
        next_lat = self.transition(combined)
        pred_rew = self.reward_predictor(next_lat)
        return next_lat, pred_rew.item()

    def train_step(self, obs_stack, next_obs_stack, action_type_idx=None, extrinsic_reward=0.0):
        if self.optimizer is None: 
            self.to(self._device)
            self.optimizer = torch.optim.Adam(self.parameters(), lr=1e-3)
            
        curr_lat = self.forward(obs_stack)
        next_lat = self.forward(next_obs_stack).detach()
        
        # Loss 1: Temporal Consistency (Physics learning)
        loss_cons = F.mse_loss(curr_lat, next_lat)
        
        # Loss 3: Spatial Consistency Loss (Consistency with reward signal)
        pred_rew = self.reward_predictor(curr_lat)
        rew_target = torch.tensor([[float(extrinsic_reward)]], device=self._device)
        # Weighted loss for sparse rewards: 500x weight on positive rewards (Phase 1 reinforcement)
        if extrinsic_reward > 0:
            loss_rew = 500.0 * F.mse_loss(pred_rew, rew_target)
        else:
            loss_rew = F.mse_loss(pred_rew, rew_target)
        
        # Loss 2: Transition (Imagination training)
        if action_type_idx is not None:
            imag_next_lat, _ = self.imagine(curr_lat, action_type_idx)
            loss_trans = F.mse_loss(imag_next_lat, next_lat)
            loss = loss_cons + loss_trans + loss_rew
        else:
            loss = loss_cons + loss_rew

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return min(1.0, loss_cons.item()) # Return capped surprise for curiosity

_vision_model = ARC3VisionTransformer()

def save_vision_weights(path="arc3_vision_transformer.pth"):
    """Persist the world-model weights."""
    torch.save(_vision_model.state_dict(), path)
    return os.path.abspath(path)

def load_vision_weights(path="arc3_vision_transformer.pth"):
    """Restore the world-model weights."""
    if os.path.exists(path):
        _vision_model.load_state_dict(torch.load(path))
        return True
    return False

def visualize_latent_space(episodes):
    """[M] Step 3: Latent Space Visualization using PCA."""
    import matplotlib.pyplot as plt
    from sklearn.decomposition import PCA
    
    latents = []
    colors = []
    
    for ep in episodes:
        for obs, action, reward in ep.history:
            # Reconstruct frame stack from history if possible, or just use grid
            # For simplicity, we'll just run forward on the single grid repeated
            g = [obs.grid] * 4
            with torch.no_grad():
                lat = _vision_model(g).cpu().numpy().flatten()
            latents.append(lat)
            # Use max color in grid as a proxy for 'object type'
            colors.append(np.max(obs.grid))
            
    if not latents: return
    
    pca = PCA(n_components=2)
    reduced = pca.fit_transform(latents)
    
    plt.figure(figsize=(10, 8))
    scatter = plt.scatter(reduced[:, 0], reduced[:, 1], c=colors, cmap='tab10', alpha=0.6)
    plt.colorbar(scatter, label='Max Grid Color')
    plt.title('ARC-AGI-3 Latent Space (Transformer Embeddings)')
    plt.xlabel('PCA 1')
    plt.ylabel('PCA 2')
    plt.grid(True, alpha=0.3)
    plt.show()

_TO_GA = {"move_up":"ACTION1","move_down":"ACTION2","move_left":"ACTION3","move_right":"ACTION4","rotate":"ACTION5","place":"ACTION6","undo":"ACTION7"}

def _frame_to_grid(frame):
    raw = getattr(frame, "frame", None)
    if raw is None or not hasattr(raw, "__len__") or len(raw) == 0: 
        return [[0]*64 for _ in range(64)], 64, 64
    first = raw[0] if (hasattr(raw[0], "__len__") and len(raw[0]) > 0 and hasattr(raw[0][0], "__len__")) else raw
    h = len(first)
    w = len(first[0]) if h > 0 else 0
    grid = [[int(first[r][c]) % 16 for c in range(min(w, 64))] for r in range(min(h, 64))]
    actual_h, actual_w = len(grid), len(grid[0]) if len(grid) > 0 else 0
    for row in grid:
        while len(row) < 64: row.append(0)
    while len(grid) < 64: grid.append([0]*64)
    return grid, actual_h, actual_w


class ObjectExtractor:
    """Extract discrete objects (background, agent, targets) from pixel grids.

    ARC-AGI-3 tasks are fundamentally about objects: an agent coloured X moves
    to reach a target coloured Y. Reasoning at raw-pixel level misses this
    structure. This extractor turns consecutive frames into a compact
    object-level dictionary that downstream policy code can act on directly.

    Returned dict from extract():
        background        : int            most-common colour (playfield)
        agent_colour      : Optional[int]  colour of the agent (motion-inferred)
        agent_pos         : Optional[(y,x)] centroid of the agent object
        objects_by_colour : {colour: [(y,x), ...]} non-background pixels grouped
        target_positions  : [(y,x), ...]   non-agent non-background pixels
    """

    def __init__(self):
        self._motion_history: dict = collections.defaultdict(list)
        self._background_colour: int = 0

    def extract(self, current_grid, prev_grid=None, actual_h: int = 64, actual_w: int = 64):
        # Restrict attention to the true game viewport, not the 64x64 padded frame.
        h = max(1, min(int(actual_h), 64))
        w = max(1, min(int(actual_w), 64))
        grid = np.array(current_grid)[:h, :w]

        counts = collections.Counter(grid.flatten().tolist())
        self._background_colour = int(counts.most_common(1)[0][0]) if counts else 0

        if prev_grid is not None:
            prev = np.array(prev_grid)[:h, :w]
            if prev.shape == grid.shape:
                changed = np.argwhere(grid != prev)
                # Cap by size: huge diffs are usually level transitions, not agent motion
                if 0 < len(changed) < 100:
                    for r, c in changed:
                        col = int(grid[r, c])
                        if col != self._background_colour and col != 0:
                            self._motion_history[col].append((int(r), int(c)))
                            if len(self._motion_history[col]) > 20:
                                self._motion_history[col].pop(0)

        objects_by_colour: dict = {}
        for col in range(1, 16):
            if col == self._background_colour:
                continue
            pos = np.argwhere(grid == col)
            if len(pos) > 0:
                objects_by_colour[col] = [(int(r), int(c)) for r, c in pos]

        # Agent = colour with the most recent motion and a small footprint
        agent_colour = None
        agent_pos = None
        active = [c for c in self._motion_history if self._motion_history[c]]
        active.sort(key=lambda c: len(self._motion_history[c]), reverse=True)
        for col in active:
            if col in objects_by_colour and len(objects_by_colour[col]) < 50:
                agent_colour = col
                positions = objects_by_colour[col]
                ay = sum(p[0] for p in positions) / len(positions)
                ax = sum(p[1] for p in positions) / len(positions)
                agent_pos = (ay, ax)
                break

        target_positions: list = []
        for col, positions in objects_by_colour.items():
            if col == agent_colour:
                continue
            target_positions.extend(positions)

        return {
            "background": self._background_colour,
            "agent_colour": agent_colour,
            "agent_pos": agent_pos,
            "objects_by_colour": objects_by_colour,
            "target_positions": target_positions,
            "viewport": (h, w),
        }


class GameTypeClassifier:
    """Classify a game family from the first few frames.

    Replaces the brittle ``"ls20" in game_id`` string match with frame-based
    heuristics that work on the full ARC-AGI-3 catalogue.

    Returns one of: ``"navigation"``, ``"sorting"``, ``"pattern"``, ``"unknown"``.
    """

    def __init__(self, window: int = 10):
        self.window = window
        self._frames: list = []
        self._family: str = "unknown"
        self._locked: bool = False

    @property
    def family(self) -> str:
        return self._family

    def observe(self, grid, actual_h: int = 64, actual_w: int = 64) -> str:
        if self._locked:
            return self._family
        h = max(1, min(int(actual_h), 64))
        w = max(1, min(int(actual_w), 64))
        snapshot = np.array(grid)[:h, :w].copy()
        self._frames.append(snapshot)
        if len(self._frames) < self.window:
            return self._family
        family = self._classify()
        if family != "unknown":
            # Lock only once we have a meaningful signal
            self._family = family
            self._locked = True
        else:
            # Slide the window — keep accumulating frames until we get motion
            self._frames = self._frames[-(self.window // 2):]
        return self._family

    def _classify(self) -> str:
        grids = self._frames
        colour_counts = [len(np.unique(g)) for g in grids]
        avg_colours = sum(colour_counts) / max(1, len(colour_counts))

        motion_ratios = []
        for i in range(1, len(grids)):
            if grids[i].shape != grids[i-1].shape:
                continue
            diff = int(np.sum(grids[i] != grids[i-1]))
            total = max(1, grids[i].size)
            motion_ratios.append(diff / total)
        motion = sum(motion_ratios) / max(1, len(motion_ratios)) if motion_ratios else 0.0

        # No motion yet → defer classification until we actually see the game respond
        if motion < 1e-6:
            return "unknown"
        # Any detectable localised motion → navigation (one object moved)
        if motion < 0.10:
            return "navigation"
        # Large-scale grid changes with many colours → sorting / placement
        if avg_colours > 8:
            return "sorting"
        # Moderate change, few colours → pattern
        if avg_colours <= 5:
            return "pattern"
        return "unknown"



class NavigationSolver:
    """[M] Navigation solver - Goal-Aware (Appearance Matching)."""
    def __init__(self, game_id="generic"):
        self._game_id = game_id
        self._agent_color = None
        self._last_pos = None
        self._steps_no_progress = 0
        self._current_direction = random.choice(["move_up", "move_down", "move_left", "move_right"])
        self._dir_steps = 0
        self._known_goal_color = None
        self._motion_history = collections.defaultdict(list) # Color -> positions
        self._background_color = 0
        self._confidence = 0.0

    def next_action(self, env, reward) -> Optional[str]:
        grid = np.array(env.frame_stack[-1])
        prev_grid = np.array(env.frame_stack[-2])
        
        # Detect background color if not already known
        self._background_color = env._scanner._background_color
        
        # [M] Motion tracking to identify agent
        changed_pixels = np.argwhere(grid != prev_grid)
        if len(changed_pixels) > 0 and len(changed_pixels) < 100: # Reasonable change size
             for r, c in changed_pixels:
                 color = grid[r, c]
                 if color != self._background_color and color != 0: # Not background
                     self._motion_history[color].append((r, c))
                     # Keep recent history
                     if len(self._motion_history[color]) > 20:
                         self._motion_history[color].pop(0)

        # Detect Goal Preview in common ARC-AGI-3 UI locations
        goal_areas = [
            grid[52:64, 0:32],   # Bottom left
            grid[0:16, 52:64],   # Top right
            grid[52:64, 52:64],  # Bottom right
        ]
        
        found_goal = None
        for goal_area in goal_areas:
            goal_pixels = goal_area[(goal_area != 0) & (goal_area != 1) & (goal_area != 3) & (goal_area != 4)]
            if len(goal_pixels) > 0:
                 counts = collections.Counter(goal_pixels.flatten())
                 found_goal = counts.most_common(1)[0][0]
                 break
        
        if found_goal is not None:
            self._known_goal_color = found_goal

        # Identify agent candidate
        field = grid # Full 64x64 field
        agent_candidates = []
        
        # If we have motion history, prefer the most recently moved color
        active_colors = [c for c in self._motion_history if len(self._motion_history[c]) > 0]
        if active_colors:
            # Sort by frequency of motion
            active_colors.sort(key=lambda c: len(self._motion_history[c]), reverse=True)
            for c in active_colors:
                pos = np.argwhere(field == c)
                if len(pos) > 0:
                    agent_candidates.append((len(pos), c, pos))
                    break
        
        # Fallback to any non-static color if no motion history
        if not agent_candidates:
            for c in range(1, 16):
                if c == self._background_color: continue
                pos = np.argwhere(field == c)
                if 0 < len(pos) < 50: # Agents are usually small
                    agent_candidates.append((len(pos), c, pos))
        
        if not agent_candidates:
            return self._random_fallback()
            
        agent_candidates.sort(key=lambda x: x[0]) # Smallest object is likely agent
        _, self._agent_color, agent_pos = agent_candidates[0]
        ay, ax = np.mean(agent_pos, axis=0)
        
        # Appearance Matching: does agent color match goal color?
        needs_change = False
        if self._known_goal_color is not None and self._agent_color != self._known_goal_color:
            needs_change = True
            
        # Navigation logic
        target = None
        if needs_change:
            # Seek "Switchers": objects that match the goal color
            switchers = np.argwhere(field == self._known_goal_color)
            if len(switchers) > 0:
                target = switchers[np.argmin(np.sum(np.abs(switchers - [ay, ax]), axis=1))]
        
        if target is None:
            # Seek "Targets": Often color 5 or 2 or 8
            for t_color in [self._known_goal_color, 5, 2, 8]:
                if t_color is None or t_color == self._agent_color: continue
                targets = np.argwhere(field == t_color)
                if len(targets) > 0:
                    target = targets[np.argmin(np.sum(np.abs(targets - [ay, ax]), axis=1))]
                    break
            
        if target is None:
            # Fallback to any interactive object
            others = np.argwhere((field != self._background_color) & (field != 0) & (field != self._agent_color))
            if len(others) > 0:
                target = others[np.argmin(np.sum(np.abs(others - [ay, ax]), axis=1))]

        if target is None:
            return self._random_fallback()

        # Pathfinding to target
        ty, tx = target
        dy, dx = ty - ay, tx - ax
        
        if self._last_pos is not None and np.allclose([ay, ax], self._last_pos, atol=0.1):
            self._steps_no_progress += 1
        else:
            self._steps_no_progress = 0
            self._last_pos = (ay, ax)

        # If navigation is consistently failing (stalled), return None to let scanner take over
        if self._steps_no_progress > 15:
            return None

        # [M] Inject small chance of rotation to break movement loops
        if random.random() < 0.05:
            return "rotate"

        if abs(dy) > abs(dx):
            return "move_up" if dy < 0 else "move_down"
        else:
            return "move_left" if dx < 0 else "move_right"

    _DIRS = ["move_up", "move_right", "move_down", "move_left"]  # clockwise cycle

    def _random_fallback(self):
        self._dir_steps += 1
        # Rotate through all four directions in 25-step blocks so the agent
        # systematically covers every axis within a 100-step span, regardless of
        # which initial direction was chosen at construction.  A small random
        # perturbation prevents pure grid-aligned marching.
        if self._dir_steps % 25 == 0:
            curr_idx = (self._DIRS.index(self._current_direction)
                        if self._current_direction in self._DIRS else 0)
            self._current_direction = self._DIRS[(curr_idx + 1) % 4]
            self._dir_steps = 0
        elif random.random() < 0.08:
            self._current_direction = random.choice(self._DIRS)
        return self._current_direction

class _GridScanner:
    def __init__(self, divisions=32):
        self.divisions, self.stalled_count, self._idx = divisions, 0, 0
        self._centres = []
        self.grid_h, self.grid_w = 64, 64
        self._last_grid_hash = None
        self._click_history = collections.Counter()
        self._param_history = collections.defaultdict(set) # (x, y) -> {params tried}
        self._recent_changes = set()
        self._reactive_pixels = collections.Counter() # Pixels that caused changes
        self._visit_count = np.zeros((64, 64))
        self._background_color = 0

    def reset_coverage(self):
        """Reset click history to force re-exploration."""
        self._click_history.clear()
        self._visit_count.fill(0)
        self.stalled_count = 0

    def _build(self, grid=None, h=64, w=64):
        self.grid_h, self.grid_w = h, w
        grid_np = np.array(grid) if grid is not None else np.zeros((h, w))
        
        # [M] Detect background color (most frequent in the grid)
        counts = collections.Counter(grid_np.flatten())
        if counts:
            self._background_color = counts.most_common(1)[0][0]
        
        # Comprehensive list of all pixels
        all_pixels = [(x, y) for y in range(h) for x in range(w)]
        scored = []
        
        # Find objects (non-background, non-black)
        objs = np.argwhere((grid_np != self._background_color) & (grid_np != 0))
        obj_set = set((int(o[1]), int(o[0])) for o in objs)
        
        # Priority 1: Objects (non-zero)
        # Priority 2: Neighbors of objects
        # Priority 3: Reactive pixels (ones that worked before)
        # Priority 4: Systematic sweep
        
        targets = set()
        for oy, ox in objs:
            for dy in [-2, -1, 0, 1, 2]:
                for dx in [-2, -1, 0, 1, 2]:
                    ny, nx = oy+dy, ox+dx
                    if 0 <= ny < h and 0 <= nx < w: 
                        targets.add((nx, ny))
        
        for x, y in all_pixels:
            dist_sq = 4000.0
            if targets:
                dist_sq = min((x-tx)**2 + (y-ty)**2 for tx, ty in targets)
            
            # Huge boost for objects, significant boost for neighbors
            obj_boost = 1200.0 if (x, y) in obj_set else 0.0
            neighbor_boost = 300.0 if (x, y) in targets else 0.0
            
            # Change-affinity: prefer areas that recently changed
            change_boost = 800.0 if (x, y) in self._recent_changes else 0.0
            
            # Reactive boost: prefer pixels that have reacted to clicks before
            reactive_boost = self._reactive_pixels[(x, y)] * 1000.0
            
            # Novelty: penalize frequent clicks heavily
            clicks = self._click_history[(x, y)]
            novelty_penalty = clicks * 150.0 + (500.0 if clicks > 0 else 0.0)
            
            # Systematic bonus: use larger primes for better 64x64 coverage
            systematic_bonus = ( (x % 7) * 10.0 + (y % 11) * 10.0 )
            
            # Random jitter to avoid getting stuck in patterns
            jitter = random.random() * 20.0
            
            score = obj_boost + neighbor_boost + change_boost + reactive_boost - novelty_penalty + (150.0 / (dist_sq + 1.0)) + systematic_bonus + jitter
            scored.append((score, (x, y)))
            
        scored.sort(key=lambda x: x[0], reverse=True)
        self._centres = [s[1] for s in scored]
        self._idx = 0

    def refine(self, grid=None):
        self._build(grid, self.grid_h, self.grid_w)
        # Occasionally jump to a completely random low-click area
        if random.random() < 0.2:
            self._idx = random.randint(len(self._centres)//2, len(self._centres)-1)
        else:
            self._idx = random.randint(0, min(10, len(self._centres)-1))

    def next_click(self):
        if not self._centres: return ARC3Action(action_type="place", x=random.randint(0, self.grid_w-1), y=random.randint(0, self.grid_h-1))
        
        # Occasionally suggest a rotation before clicking to try different selections
        if random.random() < 0.05:
            return ARC3Action(action_type="rotate", param=random.randint(0, 15))
            
        if self._idx >= len(self._centres):
            self.refine()
            
        x, y = self._centres[self._idx]; self._idx += 1
        self._click_history[(x, y)] += 1
        
        # Systematic param exploration: 0-15
        tried = self._param_history[(x, y)]
        if len(tried) >= 16:
            tried.clear() # Reset if all tried
            
        if self._reactive_pixels[(x, y)] > 0:
            # High priority: try all colors systematically on reactive pixels
            for p in range(16):
                if p not in tried:
                    param = p
                    break
            else: param = random.randint(0, 15)
        else:
            # Low priority: 70% chance no param, 30% random new param
            if random.random() < 0.7:
                param = None
            else:
                available = [p for p in range(16) if p not in tried]
                param = random.choice(available) if available else random.randint(0, 15)

        if param is not None:
            tried.add(param)
            
        return ARC3Action(action_type="place", x=x, y=y, param=param)

class PrometheusARC3LiveEnv:
    def __init__(self, env_wrapper, game_id):
        self._env, self.game_type = env_wrapper, game_id
        self.frame_stack = deque([[[0]*64 for _ in range(64)]]*4, maxlen=4)
        # [M] NavigationSolver is now initialized for all games to catch any movement tasks
        self._navigation_solver = NavigationSolver(game_id=game_id)
        self._scanner = _GridScanner(); self.total_actions, self.total_levels = 0, 0
        self.state_novelty_buffer = set()
        self.actual_h, self.actual_w = 64, 64
        # Tier 2: object-level abstraction + game-family classification
        self._extractor = ObjectExtractor()
        self._classifier = GameTypeClassifier(window=10)
        self._extracted: dict = {}
        self._start_session()
    def _start_session(self):
        f = self._env.reset(); g, h, w = _frame_to_grid(f)
        self.actual_h, self.actual_w = h, w
        for _ in range(4): self.frame_stack.append(g)
        self.total_levels = int(getattr(f, "levels_completed", 0) or 0)
        self._scanner._build(g, h, w) # Pass grid and dims to scanner
        self._extracted = self._extractor.extract(g, prev_grid=None, actual_h=h, actual_w=w)
        self._classifier.observe(g, actual_h=h, actual_w=w)

    def begin_window(self):
        # Reset the game to initial state for every window.
        # Previously only _start_session() (called from __init__) called env.reset().
        # From window 2 onwards the game was never reset, so the agent kept
        # exploring a stuck position with all states already in the novelty buffer.
        self._start_session()
        # Reset per-window state: novelty buffer and scanner coverage.
        # NOTE: we intentionally keep _motion_history and _agent_color on the
        # NavigationSolver so that agent-colour knowledge learned in window N
        # carries over to window N+1. Only the position-tracking state is reset
        # so the solver re-establishes target proximity from the new start pos.
        self.state_novelty_buffer.clear()
        self._navigation_solver._steps_no_progress = 0
        self._navigation_solver._last_pos = None
        self._scanner.stalled_count = 0
        return ARC3Observation.from_grid_list(self.frame_stack[-1], score=float(self.total_levels), step=0)

    @property
    def game_family(self) -> str:
        return self._classifier.family

    def extract_objects(self) -> dict:
        """Return the most recent object-level extraction dict."""
        return self._extracted

    def solver_action(self, reward) -> Optional[ARC3Action]:
        """Restored logic: only returns an action if solver is confident."""
        family = self._classifier.family
        # Trust the navigation solver for navigation/unknown families, or for any
        # family while it hasn't repeatedly failed (steps_no_progress < 10).
        # The old threshold of 3 was too aggressive: the solver was abandoned after
        # just 3 unproductive steps even though the game might legitimately need
        # several moves before progress is visible.
        act_name = self._navigation_solver.next_action(self, reward)
        if act_name:
             nav_trust = (family in ("navigation", "unknown")
                          or self._navigation_solver._steps_no_progress < 10)
             if nav_trust:
                 if act_name == "rotate":
                     return ARC3Action(action_type="rotate", param=random.randint(0, 15))
                 return ARC3Action(action_type=act_name)

        # Grid scanner only runs if we haven't seen any changes or stalled
        if self._scanner.stalled_count > 3:
            return self._scanner.next_click()

        return None

    def step(self, action):
        prev_stack = list(self.frame_stack); prev_lvl = self.total_levels
        prev_h, prev_w = self.actual_h, self.actual_w
        ga_name = _TO_GA.get(action.action_type, "ACTION1")
        
        # Ensure action coordinates are valid
        ax, ay = int(action.x), int(action.y)
        if action.action_type == "place":
            ax = max(0, min(ax, self.actual_w - 1))
            ay = max(0, min(ay, self.actual_h - 1))

        # [M] Improved data payload to pass params for rotate/selection
        data = {}
        if "ACTION6" in ga_name:
            data = {"x": ax, "y": ay}
        if action.param is not None:
            # Pass param as both 'value' and 'param' for compatibility
            data["value"] = action.param
            data["param"] = action.param

        f = self._env.step(getattr(GameAction, ga_name), data=data if data else None)

        grid, h, w = _frame_to_grid(f); self.frame_stack.append(grid); next_stack = list(self.frame_stack)
        self.actual_h, self.actual_w = h, w
        self.total_actions += 1

        # Tier 2: refresh object extraction & game-family classification
        self._extracted = self._extractor.extract(grid, prev_grid=prev_stack[-1], actual_h=h, actual_w=w)
        self._classifier.observe(grid, actual_h=h, actual_w=w)

        # Check if grid changed for the scanner
        if h != prev_h or w != prev_w:
            self._scanner._build(grid, h, w)
            self._scanner.stalled_count = 0
        elif np.array_equal(prev_stack[-1], grid):
            self._scanner.stalled_count += 1
            if self._scanner.stalled_count % 30 == 0: # More frequent refinement
                self._scanner.refine(grid)
        else:
            self._scanner.stalled_count = 0
            # Identify changed pixels for the scanner
            changed = np.argwhere(np.array(prev_stack[-1]) != np.array(grid))
            self._scanner._recent_changes = set((int(p[1]), int(p[0])) for p in changed)
            # [M] Track reactive pixels (ones that were actually clicked when a change happened)
            if action.action_type == "place" and len(changed) > 0:
                self._scanner._reactive_pixels[(action.x, action.y)] += 1
            
            # If place resulted in change, refine to prioritize near the change
            if action.action_type == "place": self._scanner.refine(grid)
        
        # [M] Step 4: Curiosity (Intrinsic Reward from prediction surprise)
        from prometheus.wp71_arc_agi3 import _ACTION_TYPES
        try: atype_idx = _ACTION_TYPES.index(action.action_type)
        except: atype_idx = 7
        
        # Combine rewards: Extrinsic (Levels) + Intrinsic (Surprise + Change + Novelty)
        self.total_levels = int(getattr(f, "levels_completed", prev_lvl) or prev_lvl)
        extrinsic = float(self.total_levels - prev_lvl)
        
        # Surprise from world model
        surprise = _vision_model.train_step(prev_stack, next_stack, action_type_idx=atype_idx, extrinsic_reward=extrinsic)
        
        # Grid change reward
        changed_pixels = not np.array_equal(prev_stack[-1], grid)
        change_reward = 0.40 if changed_pixels else 0.0 # Doubled change reward
        
        # State novelty reward — hash the RAW grid, not the latent.
        # The latent is non-stationary (model trains every step), so hashing it
        # makes every state appear novel regardless of whether the grid changed.
        # Using the grid values directly gives a stable, meaningful novelty signal.
        lhash = hash(tuple(int(v) for row in grid for v in row))
        novelty_reward = 0.0
        if extrinsic > 0: self.state_novelty_buffer.clear() # Reset on reward

        if lhash not in self.state_novelty_buffer:
            self.state_novelty_buffer.add(lhash)
            novelty_reward = 0.30
            if len(self.state_novelty_buffer) > 2000: self.state_novelty_buffer.clear()
            
        intrinsic = min(1.0, (surprise * 1.0) + change_reward + novelty_reward)
        
        # [M] Return extra metadata for boredom detection (avoiding noisy surprise)
        meta = {"change": change_reward, "novelty": novelty_reward}
        
        return ARC3Observation.from_grid_list(grid, score=float(self.total_levels), step=self.total_actions), extrinsic, intrinsic, meta


class PrometheusARC3SyntheticEnv:
    """Fallback environment for when arc_agi toolkit is missing."""
    def __init__(self, synth_game):
        self._env = synth_game
        self.game_type = synth_game.game_type
        self.total_levels, self.total_actions = 0, 0
        self.frame_stack = deque([[[0]*64 for _ in range(64)]]*4, maxlen=4)
        self.actual_h, self.actual_w = 64, 64
        self._scanner = _GridScanner()
        # Tier 2: object-level abstraction (synthetic games have known family
        # from the underlying game_type so we skip GameTypeClassifier here).
        self._extractor = ObjectExtractor()
        self._extracted: dict = {}
        # Initialize frame stack
        obs = self._env.observation()
        g, h, w = self._grid_to_64x64(obs.grid)
        for _ in range(4): self.frame_stack.append(g)
        self.actual_h, self.actual_w = h, w
        self._scanner._build(g, h, w)
        self._extracted = self._extractor.extract(g, prev_grid=None, actual_h=h, actual_w=w)

    def _grid_to_64x64(self, grid_tuple):
        grid = [list(row) for row in grid_tuple]
        h, w = len(grid), len(grid[0]) if len(grid) > 0 else 0
        padded = [[grid[r][c] if r < h and c < w else 0 for c in range(64)] for r in range(64)]
        return padded, h, w

    @property
    def game_family(self) -> str:
        # Map synthetic game types to the classifier's family labels.
        return {"navigate": "navigation", "sort": "sorting",
                "count": "pattern", "mirror": "pattern"}.get(self.game_type, "unknown")

    def extract_objects(self) -> dict:
        return self._extracted

    def begin_window(self):
        obs = self._env.reset() if hasattr(self._env, "reset") else self._env.observation()
        g, h, w = self._grid_to_64x64(obs.grid)
        for _ in range(4): self.frame_stack.append(g)
        self._scanner._build(g, h, w)
        self._extracted = self._extractor.extract(g, prev_grid=None, actual_h=h, actual_w=w)
        self.total_levels = int(obs.score) if hasattr(obs, "score") else 0
        return obs

    def solver_action(self, reward) -> Optional[ARC3Action]:
        return None
    def step(self, action):
        prev_grid = list(self.frame_stack[-1])
        self.total_actions += 1
        obs, extrinsic = self._env.step(action)
        self.total_levels = int(obs.score)

        # Update frame stack
        g, h, w = self._grid_to_64x64(obs.grid)
        self.frame_stack.append(g)
        self._extracted = self._extractor.extract(g, prev_grid=prev_grid, actual_h=h, actual_w=w)

        intrinsic = 0.0 # Curiosity still 0 for synthetic without vision model training
        meta = {"change": 0.0, "novelty": 0.0}
        return obs, extrinsic, intrinsic, meta


class PatchedExplorationPolicy(ARC3ExplorationPolicy):
    def select_action(self, obs, world_model, goal_inferrer, solved_episodes=None, strategy=None, extracted=None):
        # Stash the object-extraction dict so private helpers can see it without
        # changing their signatures (ARC3ExplorationPolicy dispatches internally).
        self._extracted = extracted or {}
        if strategy:
            old_strat = self.active_strategy
            self._active_strategy = strategy
            res = super().select_action(obs, world_model, goal_inferrer, solved_episodes)
            self._active_strategy = old_strat
            return res
        return super().select_action(obs, world_model, goal_inferrer, solved_episodes)

    def _place_at(self, y: int, x: int, w: int, h: int) -> ARC3Action:
        return ARC3Action(action_type="place",
                          x=int(max(0, min(x, w - 1))),
                          y=int(max(0, min(y, h - 1))))

    def _goal_directed_action(self, obs: ARC3Observation, goal_inferrer: ARC3GoalInferrer) -> ARC3Action:
        """Goal-directed action: use extracted objects to pick concrete place coords.

        Previous version picked an action *type* via imagination and then
        sampled random coordinates. That made ``place`` effectively random even
        when the goal was "reach_target". This version first dispatches on the
        inferred goal, then uses ObjectExtractor output to pick a meaningful
        coordinate.
        """
        goal = goal_inferrer.most_likely_goal
        if goal == "exploration":
            return self._random_action(obs)

        extracted = getattr(self, "_extracted", {}) or {}
        objects_by_colour: dict = extracted.get("objects_by_colour", {})
        agent_pos = extracted.get("agent_pos")
        target_positions: list = extracted.get("target_positions", [])
        vh, vw = extracted.get("viewport", (obs.height, obs.width))

        # --- Goal: reach a target ---------------------------------------------
        # If we know where the agent is and where the targets are, step the agent
        # one grid cell toward the nearest target. No agent info → click the
        # nearest target (many games accept a click to move/select).
        if goal == "reach_target":
            if target_positions:
                if agent_pos is not None:
                    ay, ax = agent_pos
                    ty, tx = min(target_positions, key=lambda p: abs(p[0]-ay) + abs(p[1]-ax))
                    dy, dx = ty - ay, tx - ax
                    if abs(dy) > abs(dx):
                        return ARC3Action(action_type="move_up" if dy < 0 else "move_down")
                    if abs(dx) > 0:
                        return ARC3Action(action_type="move_left" if dx < 0 else "move_right")
                ty, tx = target_positions[random.randint(0, len(target_positions) - 1)]
                return self._place_at(ty, tx, vw, vh)

        # --- Goal: clear one colour -------------------------------------------
        # Click every instance of the most-common non-background colour.
        if goal == "clear_colour" and objects_by_colour:
            dominant = max(objects_by_colour.items(), key=lambda kv: len(kv[1]))[0]
            positions = objects_by_colour[dominant]
            ty, tx = positions[random.randint(0, len(positions) - 1)]
            return self._place_at(ty, tx, vw, vh)

        # --- Goal: fill pattern -----------------------------------------------
        # Click on empty cells adjacent to existing objects (grows the pattern).
        if goal == "fill_pattern" and target_positions:
            ty, tx = target_positions[random.randint(0, len(target_positions) - 1)]
            dy, dx = random.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
            return self._place_at(ty + dy, tx + dx, vw, vh)

        # --- Goal: maximise score (no spatial prior) --------------------------
        # Fall back to 1-step imagination lookahead to pick the best action
        # type, using object-centric coords for ``place``.
        best_action = self._random_action(obs)
        max_val = -1.0
        try:
            g = [list(obs.grid)] * 4
            with torch.no_grad():
                curr_lat = _vision_model(g)
            from prometheus.wp71_arc_agi3 import _ACTION_TYPES
            for sim_idx, sim_atype in enumerate(_ACTION_TYPES):
                imag_lat, pred_extrinsic = _vision_model.imagine(curr_lat, sim_idx)
                if goal == "maximise_score":
                    val = pred_extrinsic
                else:
                    val = F.mse_loss(curr_lat, imag_lat).item()
                if val > max_val:
                    max_val = val
                    if sim_atype == "place":
                        if target_positions:
                            ty, tx = target_positions[random.randint(0, len(target_positions) - 1)]
                            best_action = self._place_at(ty, tx, vw, vh)
                        else:
                            grid = np.array(obs.grid)
                            objects = np.argwhere(grid > 0)
                            if len(objects) > 0:
                                t = objects[random.randint(0, len(objects) - 1)]
                                best_action = self._place_at(int(t[0]), int(t[1]), vw, vh)
                            else:
                                best_action = self._place_at(random.randint(0, vh-1), random.randint(0, vw-1), vw, vh)
                    else:
                        best_action = ARC3Action(action_type=sim_atype)
        except Exception:
            pass
        return best_action

class PatchedStrangeLoopAgent(ARC3StrangeLoopAgent):
    def __init__(self, window_steps=100, mutation_rate=0.05, fitness_threshold=0.5):
        super().__init__(max_steps_per_episode=window_steps, mutation_rate=mutation_rate, fitness_threshold=fitness_threshold)
        self.policy, self.episode_logs = PatchedExplorationPolicy(mutation_rate=mutation_rate), []
        # Tier 2.3b: track how many reward-bearing transitions the vision model
        # has seen so we can discount its predicted-extrinsic signal when it is
        # still untrained. Ramps from 0 → 1 over the first ~5 rewards.
        self._reward_transitions_seen: int = 0
    def run_episode(self, env):
        self._episode_count += 1; obs = env.begin_window(); episode = ARC3Episode(game_id=env.game_type, level=self._episode_count)
        strat, reward = self.policy.active_strategy, 0.0
        
        # Step 3: Hypothesis-driven exploration
        _ = self.goal_inferrer.get_hypothesis_for_test()
        
        actionable_curiosity_history = deque(maxlen=10)
        latent_history = deque(maxlen=5)
        action_history = collections.Counter()
        failure_buffer = set() # (x, y) coordinates that failed to react
        strat_reward = 0.0
        frame_stack_history: list = []  # parallel to episode.history; stores real 4-frame stacks
        
        for step_idx in range(self.max_steps_per_episode):
            s_act = env.solver_action(reward)
            if s_act: 
                action = s_act
                # Ensure bounded place
                if action.action_type == "place":
                    action = ARC3Action(action_type="place", 
                                      x=max(0, min(action.x, env.actual_w - 1)),
                                      y=max(0, min(action.y, env.actual_h - 1)))
            else:
                # [M] Step 2: Latent Sequence Completion
                curr_lat = _vision_model(list(env.frame_stack))
                latent_history.append(curr_lat)

                # Step 3: Beam Search Simulation (wider + deeper than before)
                from prometheus.wp71_arc_agi3 import _ACTION_TYPES

                # Tier 2.3b: discount pred_extrinsic when the model is untrained.
                # Ramps 0→1 over the first 5 reward-bearing transitions.
                w_extrinsic = min(1.0, self._reward_transitions_seen / 5.0)

                extracted = env.extract_objects() if hasattr(env, "extract_objects") else {}
                target_positions = extracted.get("target_positions", []) if extracted else []
                vh, vw = (extracted.get("viewport") if extracted else (env.actual_h, env.actual_w)) \
                         or (env.actual_h, env.actual_w)

                # (total_score, action_type, place_coord_or_None, sequence, current_latent)
                beam = [(0.0, None, None, [], curr_lat)]
                # Deep beam is only worthwhile once the reward model has real signal.
                # When completely untrained (w_extrinsic=0) it adds latency with noise.
                beam_depth = 2 if w_extrinsic < 0.2 else 5
                beam_width = 4 if w_extrinsic < 0.2 else 6

                for _ in range(beam_depth):
                    new_candidates = []
                    for b_score, b_act, b_coord, b_seq, b_lat in beam:
                        for sim_idx, sim_atype in enumerate(_ACTION_TYPES):
                            imag_lat, pred_extrinsic = _vision_model.imagine(b_lat, sim_idx)
                            curiosity = F.mse_loss(b_lat, imag_lat).item()

                            if len(latent_history) >= 2:
                                pattern_lat = _vision_model.predict_next_in_sequence(list(latent_history))
                                pattern_score = 1.0 / (F.mse_loss(imag_lat, pattern_lat).item() + 1e-6)
                            else:
                                pattern_score = 0.0

                            novelty_score = 1.0 / (action_history[sim_atype] + 1.0)

                            step_score = (w_extrinsic * pred_extrinsic * 100.0
                                          + curiosity * 5.0
                                          + pattern_score * 0.5
                                          + novelty_score * 2.0)
                            new_score = b_score + step_score
                            new_seq = b_seq + [sim_atype]
                            head_act = new_seq[0]
                            # For ``place`` heads, sample an object-centric coordinate
                            # so the beam reasons about *where* to click, not just
                            # whether to click.
                            if head_act == "place" and b_coord is None:
                                if target_positions:
                                    ty, tx = target_positions[random.randint(0, len(target_positions) - 1)]
                                    coord = (int(ty), int(tx))
                                else:
                                    coord = None
                            else:
                                coord = b_coord
                            new_candidates.append((new_score, head_act, coord, new_seq, imag_lat))

                    new_candidates.sort(key=lambda x: x[0], reverse=True)
                    beam = new_candidates[:beam_width]

                best_sim_act = beam[0][1] if beam else None
                best_sim_coord = beam[0][2] if beam else None

                # For navigation games with an untrained reward model, the beam
                # systematically over-selects "place" due to random pattern-score
                # bias. Override ~70 % of those cases with a cardinal move so the
                # agent actually explores the map.
                _nav_game = hasattr(env, "game_family") and env.game_family == "navigation"
                if (best_sim_act == "place" and _nav_game and w_extrinsic < 0.2
                        and random.random() < 0.70):
                    best_sim_act = random.choice(["move_up","move_down","move_left","move_right"])
                    best_sim_coord = None

                if best_sim_act and random.random() < 0.9:
                    if best_sim_act == "place":
                        failure_buffer.clear()
                        if best_sim_coord is not None:
                            ty, tx = best_sim_coord
                            action = ARC3Action(action_type="place",
                                                x=int(max(0, min(tx, vw - 1))),
                                                y=int(max(0, min(ty, vh - 1))))
                        else:
                            action = env._scanner.next_click()
                    else:
                        action = ARC3Action(action_type=best_sim_act)
                else:
                    action = self.policy.select_action(
                        obs, self.world_model, self.goal_inferrer,
                        strategy=strat, extracted=extracted,
                    )
                    # The goal-directed path already picks object-centric coords
                    # for place; only fall through to the scanner when we have
                    # no object info at all (empty extraction).
                    if action.action_type == "place" and not target_positions:
                        action = env._scanner.next_click()
            
            # Step 3: Failure buffering and strategic reset
            # Strategic Reset on Boredom / Stagnation
            # Bored if no grid changes or novelty for 10 steps
            is_bored = len(actionable_curiosity_history) == 10 and sum(actionable_curiosity_history) < 0.01

            # Only burst when genuinely stalled (no grid changes for 10 steps).
            # The old condition also fired on "reward == 0" which is always true,
            # causing ~22 unneeded bursts per window (each adding 15 extra steps).
            if is_bored:
                _fam = env.game_family if hasattr(env, "game_family") else "unknown"
                if random.random() < 0.8:
                    for _ in range(15):
                        p = random.random()
                        if _fam == "navigation":
                            # Navigation: 70% move, 20% place/interact, 10% rotate
                            if p < 0.70:
                                reset_action = ARC3Action(action_type=random.choice(["move_up","move_down","move_left","move_right"]))
                            elif p < 0.90:
                                reset_action = env._scanner.next_click()
                            else:
                                reset_action = ARC3Action(action_type="rotate", param=random.randint(0, 15))
                        else:
                            if p < 0.6:
                                reset_action = (ARC3Action(action_type="place", x=random.randint(0, env.actual_w-1), y=random.randint(0, env.actual_h-1))
                                                if random.random() < 0.3 else env._scanner.next_click())
                            elif p < 0.9:
                                reset_action = ARC3Action(action_type=random.choice(["move_up","move_down","move_left","move_right"]))
                            else:
                                reset_action = ARC3Action(action_type="rotate", param=random.randint(0, 15))
                            
                        prev_obs_for_update = obs
                        obs, extrinsic, intrinsic, meta = env.step(reset_action)
                        frame_stack_history.append(list(env.frame_stack))
                        if extrinsic > 0:
                            self._reward_transitions_seen += 1
                        reward = extrinsic + 0.05 * intrinsic
                        self.world_model.update(prev_obs_for_update, reset_action, obs, reward)
                        self.goal_inferrer.observe(obs, prev_obs_for_update, reward)
                        episode.record(obs, reset_action, reward, extrinsic=extrinsic, intrinsic=intrinsic)
                        if extrinsic > 0: break
                
                if sum(h[2] for h in episode.history[-10:]) == 0:
                    self.goal_inferrer.reject_current_hypothesis()
                # Mutation and coverage reset
                self.policy.mutate(0.0)
                env._scanner.refine(obs.grid)
                if is_bored: 
                    env._scanner.reset_coverage()
                    failure_buffer.clear()
                
                strat = self.policy.active_strategy
                actionable_curiosity_history.clear()
            
            prev_obs_in_loop = obs
            obs, extrinsic, intrinsic, meta = env.step(action)
            frame_stack_history.append(list(env.frame_stack))
            if extrinsic > 0:
                self._reward_transitions_seen += 1
            action_history[action.action_type] += 1
            reward = extrinsic + 0.05 * intrinsic
            strat_reward += reward
            
            # [M] Refined Boredom: only track grid changes and state novelty
            actionable_curiosity_history.append(meta["change"] + meta["novelty"])
            
            # Step 3: Failure buffering logic
            if action.action_type == "place" and intrinsic < 0.01:
                failure_buffer.add((action.x, action.y))
            
            # [M] Step 1: Counterfactual Goal Analysis (every 50 steps)
            if step_idx % 50 == 0:
                self.goal_inferrer.counterfactual_analysis(episode.history)
            
            self.world_model.update(prev_obs_in_loop, action, obs, reward)
            self.goal_inferrer.observe(obs, prev_obs_in_loop, reward)
            episode.record(obs, action, reward, extrinsic=extrinsic, intrinsic=intrinsic)
            
        self.policy.record_episode(strat, strat_reward)
        avg_surprise = episode.total_intrinsic / max(1, len(episode.history))
        self.policy.mutate(avg_surprise)
        self.episode_logs.append({"episode":self._episode_count, "strategy":strat, "total_reward":sum(h[2] for h in episode.history)})
        
        # [M] Post-Episode Experience Replay (Focus on extrinsic rewards)
        if len(episode.history) > 1:
            # Increase passes if we found a reward
            n_passes = 10 if episode.total_extrinsic > 0 else 3
            for _ in range(n_passes): 
                # Sample 16 transitions or all if less
                batch_size = min(16, len(episode.history) - 1)
                indices = list(range(len(episode.history) - 1))
                # Oversample reward transitions
                reward_indices = [i for i in indices if episode.history[i+1][2] > 0]
                if reward_indices:
                    indices.extend(reward_indices * 5)
                
                batch = random.sample(indices, batch_size)
                for i in batch:
                    obs_h, act_h, rew_h = episode.history[i]
                    next_obs_h, _, _ = episode.history[i+1]

                    from prometheus.wp71_arc_agi3 import _ACTION_TYPES
                    try: atype_idx = _ACTION_TYPES.index(act_h.action_type)
                    except: atype_idx = 7

                    # Use real temporal frame stacks recorded during the episode so the
                    # transformer learns genuine motion rather than zero-velocity repeats.
                    g1 = frame_stack_history[i] if i < len(frame_stack_history) else [list(obs_h.grid)] * 4
                    g2 = frame_stack_history[i+1] if i+1 < len(frame_stack_history) else [list(next_obs_h.grid)] * 4
                    _vision_model.train_step(g1, g2, action_type_idx=atype_idx, extrinsic_reward=rew_h)

        return episode

def run_live_game(game_id="ls20", n_windows=40, window_steps=120, mutation_rate=0.10, fitness_threshold=0.5, verbose=True):
    load_vision_weights()
    if not TOOLKIT_AVAILABLE:
        print(f"Toolkit missing: Falling back to Synthetic ARC-AGI-3 [{game_id}]")
        synth_type = "navigate" if "ls" in game_id else "sort" if "ft" in game_id else "count"
        env = PrometheusARC3SyntheticEnv(_SyntheticARCGame(game_type=synth_type))
    else:
        print(f"Connecting to ARC-AGI-3 API [{game_id}]...")
        try:
            arc = arc_agi.Arcade(); env_w = arc.make(game_id, render_mode=None)
            if not env_w: return None
            env = PrometheusARC3LiveEnv(env_w, game_id)
        except:
            print(f"Failed to connect to ARC-AGI-3 API for {game_id}")
            return None

    agent = PatchedStrangeLoopAgent(window_steps=window_steps)
    episodes = []
    for win in range(n_windows):
        t0, ep = time.time(), agent.run_episode(env); episodes.append(ep)
        if verbose:
            # Count steps where the grid changed (change_reward > 0)
            chg = sum(1 for _, _, r in ep.history
                      if r > ep.total_extrinsic / max(1, len(ep.history)))
            # Action-type breakdown (top 2)
            act_counts: dict = {}
            for _, act, _ in ep.history:
                act_counts[act.action_type] = act_counts.get(act.action_type, 0) + 1
            top2 = sorted(act_counts.items(), key=lambda kv: kv[1], reverse=True)[:2]
            top2_str = " ".join(f"{k}={v}" for k, v in top2)
            fam = env.game_family
            print(f"  Win {win+1:>2}/{n_windows}: levels=+{ep.total_extrinsic:.0f}"
                  f" curiosity={ep.total_intrinsic:.1f}"
                  f" family={fam}"
                  f" acts=[{top2_str}]"
                  f" ({time.time()-t0:.1f}s)")
    save_vision_weights()
    try:
        family = env.game_family
    except AttributeError:
        family = "unknown"
    return {
        "game_id":game_id,
        "solve_rate":sum(1 for e in episodes if e.total_extrinsic > 0)/len(episodes),
        "mean_score":sum(e.total_score for e in episodes)/len(episodes),
        "last_episode": episodes[-1] if episodes else None,
        "game_family": family,
    }
